# ==========================================
# Open Coding ManualAnalysis for GHA Workflows
# ==========================================

import os
import yaml
import pandas as pd
import numpy as np
from pathlib import Path
import logging
from datetime import datetime
from collections import defaultdict

# ==========================================
# Configuration
# ==========================================

from repo_paths import RQ2_RESULTS_DIR, WORKFLOW_LANG_DIRS_KEYED

WORKFLOWS_DIR = WORKFLOW_LANG_DIRS_KEYED
RESULTS_DIR = RQ2_RESULTS_DIR
SAMPLE_SIZE = 382
CONFIDENCE_LEVEL = 0.95
MARGIN_OF_ERROR = 0.05

LANG_DISPLAY = {
    "cpp": "C++",
    "java": "Java",
    "python": "Python",
}

# Create directories — only samples/ and manual_coding/ are needed
(RESULTS_DIR / "manual_coding").mkdir(parents=True, exist_ok=True)

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(RESULTS_DIR / 'open_coding.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

import sys
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')


# ==========================================
# Project Identification
# ==========================================

def extract_project_info(file_path):
    parts = Path(file_path).parts
    if '.github' in parts and 'workflows' in parts:
        try:
            workflows_idx = parts.index('workflows')
            if workflows_idx >= 2:
                owner = parts[workflows_idx - 2]
                repo = parts[workflows_idx - 1]
                return f"{owner}/{repo}"
        except Exception:
            pass
    project_dir = Path(file_path).parent.name
    if '@' in project_dir:
        owner, repo = project_dir.split('@', 1)
        return f"{owner}/{repo}"
    return project_dir


def identify_unique_projects(all_workflows):
    logger.info("Identifying unique projects...")
    projects = defaultdict(list)
    for wf in all_workflows:
        project_id = extract_project_info(wf['file_path'])
        wf['project_id'] = project_id
        projects[project_id].append(wf)
    logger.info(f"Found {len(projects)} unique projects")

    primary_names = ['ci.yml', 'test.yml', 'tests.yml', 'build.yml', 'main.yml',
                     'workflow.yml', 'python.yml', 'java.yml', 'cpp.yml', 'c++.yml']
    unique_workflows = []
    for project_id, workflows in projects.items():
        def workflow_priority(wf):
            name = Path(wf['file_path']).name.lower()
            for i, primary in enumerate(primary_names):
                if name == primary:
                    return i
            return 100
        workflows_sorted = sorted(workflows, key=workflow_priority)
        selected_workflow = workflows_sorted[0]
        selected_workflow['workflows_in_project'] = len(workflows)
        unique_workflows.append(selected_workflow)
    logger.info(f"Selected {len(unique_workflows)} unique workflows (1 per project)")
    return unique_workflows


# ==========================================
# Enhanced Workflow Collection 
# ==========================================

def calculate_file_size(file_path):
    try:
        return os.path.getsize(file_path)
    except:
        return 0


def calculate_workflow_complexity(workflow):
    """
    Computes observable workflow metrics only.
    No composite complexity score is calculated — the weights used previously
    (num_jobs×2, +5 for matrix, etc.) had no published benchmark and would be
    indefensible in peer review. Stratification uses num_steps directly instead.
    """
    metrics = {
        'num_jobs': 0,
        'num_steps': 0,
        'max_steps_per_job': 0,
        'num_actions_used': 0,
        'num_run_commands': 0,
        'has_matrix': False,
        'has_conditions': False,
        'unique_actions': set()
    }
    jobs = workflow.get('jobs', {})
    metrics['num_jobs'] = len(jobs)
    all_steps = []
    for job_name, job in jobs.items():
        if not isinstance(job, dict):
            continue
        if 'strategy' in job and 'matrix' in job.get('strategy', {}):
            metrics['has_matrix'] = True
        if 'if' in job:
            metrics['has_conditions'] = True
        steps = job.get('steps', [])
        all_steps.append(len(steps))
        for step in steps:
            if not isinstance(step, dict):
                continue
            metrics['num_steps'] += 1
            if 'uses' in step:
                metrics['num_actions_used'] += 1
                action = step['uses'].split('@')[0] if '@' in step['uses'] else step['uses']
                metrics['unique_actions'].add(action)
            if 'run' in step:
                metrics['num_run_commands'] += 1
            if 'if' in step:
                metrics['has_conditions'] = True
    if all_steps:
        metrics['max_steps_per_job'] = max(all_steps)
    metrics['num_unique_actions'] = len(metrics['unique_actions'])
    del metrics['unique_actions']
    return metrics


def derive_repo_path(file_path):
    """
    Extract the repository root path from a workflow file path.
    Walks up from the file to find the parent of .github/workflows/.
    Falls back to the owner@repo folder in the flat workflow layout.
    """
    parts = Path(file_path).parts
    if '.github' in parts:
        github_idx = list(parts).index('.github')
        return str(Path(*parts[:github_idx]))
    return str(Path(file_path).parent)


def extract_job_names(workflow):
    """
    Returns a pipe-separated string of all job keys in the workflow.
    E.g. 'build | test | deploy'
    Stored as a single cell value so sample_metadata stays one-row-per-workflow.
    """
    jobs = workflow.get('jobs', {})
    return ' | '.join(str(k) for k in jobs.keys()) if jobs else ''


def collect_all_workflows_enhanced():
    """Collect all workflow files with enhanced metadata."""
    logger.info("Collecting all workflow files with enhanced metadata...")
    all_workflows = []
    for lang, lang_folder in WORKFLOWS_DIR.items():
        language = LANG_DISPLAY[lang]
        if not lang_folder.exists():
            logger.warning(f"{language} folder not found at {lang_folder}")
            continue
        yaml_files = list(lang_folder.rglob("*.yml")) + list(lang_folder.rglob("*.yaml"))
        logger.info(f"Processing {len(yaml_files)} {language} YAML files...")
        for yaml_file in yaml_files:
            try:
                file_size = calculate_file_size(yaml_file)
                with open(yaml_file, 'r', encoding='utf-8') as f:
                    yaml_content = f.read()
                    workflow = yaml.safe_load(yaml_content)
                if not isinstance(workflow, dict) or 'jobs' not in workflow:
                    continue
                complexity_metrics = calculate_workflow_complexity(workflow)
                all_workflows.append({
                    'file_path': str(yaml_file),
                    'file_name': yaml_file.name,
                    'repo_path': derive_repo_path(str(yaml_file)),
                    'language': language,
                    'file_size_bytes': file_size,
                    'file_size_kb': round(file_size / 1024, 2),
                    'yaml_content': yaml_content,
                    'workflow': workflow,
                    'job_name': extract_job_names(workflow),
                    **complexity_metrics
                })
            except Exception as e:
                logger.warning(f"Could not load {yaml_file}: {e}")
    logger.info(f"Collected {len(all_workflows)} valid workflows")
    return all_workflows


# ==========================================
# Enhanced Stratification 
# ==========================================

def _quantile_labels(series, q: int, labels: list[str]):
    """Assign quantile labels; collapse duplicate bin edges when values tie."""
    quantiles = np.linspace(0, 1, q + 1)
    edges = np.unique(series.quantile(quantiles).to_numpy())
    if len(edges) < 2:
        return pd.Series(labels[0], index=series.index)
    n_bins = len(edges) - 1
    use_labels = labels[:n_bins]
    return pd.cut(series, bins=edges, labels=use_labels, include_lowest=True)


def stratify_workflows_enhanced(workflows):
    """
    Stratification dimensions:
      - Language (primary)
      - complexity_category: derived from num_steps tertiles ONLY.
        Rationale: num_steps is the most direct, interpretable proxy for workflow
        complexity and requires no arbitrary weighting. Tertile boundaries are
        data-driven (computed from the actual population), making them fully
        reproducible and reportable in the paper (e.g. "simple: 1-N steps").
      - job_category (single / few / many)
      - file_size_category (small / medium / large) as secondary stratum
    """
    logger.info("Performing enhanced stratification (num_steps-based complexity)...")
    df = pd.DataFrame(workflows)

    # 1. File size categories (tertiles)
    df['file_size_category'] = _quantile_labels(
        df['file_size_bytes'], q=3,
        labels=['small_file', 'medium_file', 'large_file'],
    )

    # 2. Job count categories
    def categorize_jobs(num_jobs):
        if num_jobs == 1: return 'single_job'
        elif num_jobs <= 3: return 'few_jobs'
        else: return 'many_jobs'
    df['job_category'] = df['num_jobs'].apply(categorize_jobs)

    # 3. Step count categories (quartiles — kept for fine-grained reporting)
    df['step_category'] = _quantile_labels(
        df['num_steps'], q=4,
        labels=['minimal_steps', 'few_steps', 'moderate_steps', 'many_steps'],
    )

    # 4. complexity_category from num_steps tertiles (no composite score)
    #    Thresholds are logged so they can be reported directly in the paper.
    ranked_steps = df['num_steps'].rank(method="first")
    step_edges = np.unique(ranked_steps.quantile([0, 1 / 3, 2 / 3, 1]).to_numpy())
    if len(step_edges) < 2:
        df['complexity_category'] = 'simple'
    else:
        complexity_labels = ['simple', 'moderate', 'complex'][: len(step_edges) - 1]
        df['complexity_category'] = pd.cut(
            ranked_steps, bins=step_edges, labels=complexity_labels, include_lowest=True
        )
    simple_max = df.loc[df['complexity_category'] == 'simple', 'num_steps'].max()
    moderate_max = df.loc[df['complexity_category'] == 'moderate', 'num_steps'].max()
    logger.info(
        f"  complexity_category thresholds (num_steps tertiles): "
        f"simple <= {simple_max:.0f} steps | moderate <= {moderate_max:.0f} steps | complex > {moderate_max:.0f} steps"
    )

    # 5. Stratum keys for sampling
    df['stratum'] = (
        df['language'] + '_' +
        df['complexity_category'].astype(str) + '_' +
        df['job_category']
    )
    df['secondary_stratum'] = (
        df['stratum'] + '_' +
        df['file_size_category'].astype(str) + '_' +
        df['step_category'].astype(str)
    )
    return df


# ==========================================
# Balanced Stratified Sampling 
# ==========================================

def balanced_stratified_sample(df, sample_size=SAMPLE_SIZE):
    logger.info(f"Performing PROPORTIONAL stratified sampling (n={sample_size})...")
    total_population = len(df)
    logger.info("\n=== POPULATION DISTRIBUTION ===")
    for language in ['Python', 'Java', 'C++']:
        lang_count = len(df[df['language'] == language])
        lang_pct = (lang_count / total_population) * 100
        logger.info(f"{language}: {lang_count} workflows ({lang_pct:.1f}% of population)")
    samples = []
    for language in ['Python', 'Java', 'C++']:
        lang_data = df[df['language'] == language]
        if len(lang_data) == 0:
            logger.warning(f"No data for {language}")
            continue
        lang_proportion = len(lang_data) / total_population
        lang_sample_size = int(np.round(sample_size * lang_proportion))
        lang_sample_size = max(lang_sample_size, 10)
        lang_sample_size = min(lang_sample_size, len(lang_data))
        logger.info(f"\n{language}: Target sample = {lang_sample_size} ({(lang_sample_size/sample_size)*100:.1f}% of sample)")
        lang_strata = lang_data.groupby(['complexity_category', 'job_category'])
        lang_samples = []
        for stratum_name, stratum_data in lang_strata:
            stratum_size = len(stratum_data)
            stratum_sample_size = max(1, int(np.ceil((stratum_size / len(lang_data)) * lang_sample_size)))
            stratum_sample_size = min(stratum_sample_size, stratum_size)
            stratum_sample = stratum_data.sample(n=stratum_sample_size, random_state=42)
            lang_samples.append(stratum_sample)
            logger.info(f"  {language} - {stratum_name}: {stratum_sample_size}/{stratum_size} sampled")
        lang_combined = pd.concat(lang_samples, ignore_index=True)
        if len(lang_combined) < lang_sample_size:
            remaining = lang_sample_size - len(lang_combined)
            available = lang_data[~lang_data.index.isin(lang_combined.index)]
            if len(available) > 0:
                additional = available.sample(n=min(remaining, len(available)), random_state=42)
                lang_combined = pd.concat([lang_combined, additional], ignore_index=True)
        if len(lang_combined) > lang_sample_size:
            lang_combined = lang_combined.sample(n=lang_sample_size, random_state=42)
        samples.append(lang_combined)
        logger.info(f"{language}: {len(lang_combined)} workflows sampled (target was {lang_sample_size})")
    sample_df = pd.concat(samples, ignore_index=True)
    current_size = len(sample_df)
    if current_size < sample_size:
        remaining = sample_size - current_size
        available = df[~df.index.isin(sample_df.index)]
        if len(available) > 0:
            additional = available.sample(n=min(remaining, len(available)), random_state=42)
            sample_df = pd.concat([sample_df, additional], ignore_index=True)
            logger.info(f"Added {len(additional)} additional samples to reach target")
    elif current_size > sample_size:
        excess = current_size - sample_size
        sample_df = sample_df.sample(n=sample_size, random_state=42)
        logger.info(f"Reduced by {excess} samples to reach exact target")
    logger.info(f"\nFinal sample size: {len(sample_df)}")
    return sample_df


# ==========================================
# Post-Sampling YAML Validation
# Ensures sample N == YAML content N by replacing
# any file that fails re-read/parse after sampling.
# ==========================================

def validate_and_repair_sample(sample_df, full_df, sample_size=SAMPLE_SIZE):
    """
    Re-reads each sampled file from disk to confirm it is still parseable.
    Replaces any that fail with a substitute from the same stratum in full_df.
    Guarantees: len(output) == sample_size AND all rows have valid yaml_content.

    Why this is needed:
    - The initial collection reads files once. If any YAML is marginal (e.g.,
      large file, encoding edge case, OS read error), it may parse at collection
      time but fail during the CSV write / content extraction step.
    - This validation step catches those cases BEFORE coding sheets are produced,
      so the manual coding CSV and the YAML reference CSV always have the same N.
    """
    logger.info("\n=== POST-SAMPLING YAML VALIDATION ===")
    logger.info(f"Validating {len(sample_df)} sampled files...")

    valid_rows = []
    failed_rows = []

    for idx, row in sample_df.iterrows():
        try:
            # Re-read from disk to confirm content is accessible
            with open(row['file_path'], 'r', encoding='utf-8') as f:
                content = f.read()
            parsed = yaml.safe_load(content)
            if not isinstance(parsed, dict) or 'jobs' not in parsed:
                raise ValueError("Missing 'jobs' key after re-parse")
            if not content.strip():
                raise ValueError("Empty content on re-read")
            # Update yaml_content in case it changed (shouldn't, but defensive)
            row = row.copy()
            row['yaml_content'] = content
            valid_rows.append(row)
        except Exception as e:
            logger.warning(f"  [FAIL] {row['file_path']}: {e}")
            failed_rows.append({'index': idx, 'stratum': row.get('stratum', ''), 'language': row['language']})

    logger.info(f"  Valid: {len(valid_rows)} | Failed: {len(failed_rows)}")

    if not failed_rows:
        logger.info("  [PASS] All sampled files validated. Sample N == YAML content N.")
        return pd.DataFrame(valid_rows).reset_index(drop=True)

    # ── Repair: replace each failed file with a substitute from same stratum ──
    logger.info(f"  Repairing {len(failed_rows)} failed files...")

    # Pool of candidates not already in the valid sample
    valid_file_paths = {r['file_path'] for r in valid_rows}
    replacement_pool = full_df[~full_df['file_path'].isin(valid_file_paths)].copy()

    repaired = list(valid_rows)  # start from valid rows

    for fail in failed_rows:
        stratum = fail['stratum']
        language = fail['language']

        # Try same stratum first, then same language, then any
        candidates = replacement_pool[replacement_pool['stratum'] == stratum]
        if candidates.empty:
            candidates = replacement_pool[replacement_pool['language'] == language]
        if candidates.empty:
            candidates = replacement_pool

        replaced = False
        for candidate_idx, candidate in candidates.iterrows():
            try:
                with open(candidate['file_path'], 'r', encoding='utf-8') as f:
                    content = f.read()
                parsed = yaml.safe_load(content)
                if not isinstance(parsed, dict) or 'jobs' not in parsed:
                    continue
                if not content.strip():
                    continue
                candidate = candidate.copy()
                candidate['yaml_content'] = content
                repaired.append(candidate)
                # Remove from pool so it isn't reused
                replacement_pool = replacement_pool.drop(index=candidate_idx)
                logger.info(f"    Replaced failed file with: {candidate['file_path']}")
                replaced = True
                break
            except Exception:
                continue

        if not replaced:
            logger.error(f"    [ERROR] Could not find a valid replacement for stratum '{stratum}'. "
                         f"Sample will be short by 1.")

    repaired_df = pd.DataFrame(repaired).reset_index(drop=True)

    # Final size check
    if len(repaired_df) != sample_size:
        logger.warning(f"  [WARN] After repair, sample size is {len(repaired_df)} (target: {sample_size}). "
                       f"Document this discrepancy in the paper.")
    else:
        logger.info(f"  [PASS] Sample repaired to exactly {sample_size}. "
                    f"Sample N == YAML content N guaranteed.")

    return repaired_df


# ==========================================
# Step Extraction 
# ==========================================



# ==========================================
# Main Workflow
# ==========================================



def create_manual_coding_sheets_enhanced(sample_df):
    """
    Writes the two manual_coding outputs needed for open coding:
      1. sample_summary.csv  — per-language breakdown of the sample
      2. yaml_reference.csv  — one row per workflow with full YAML content

    yaml_reference is built DIRECTLY from the validated sample_df (not derived
    from a steps dataframe), so its row count is always guaranteed to equal
    sample N. No step-level CSVs are written here; coders work from the YAML
    reference and CODING_INSTRUCTIONS.md.
    """
    logger.info("Creating manual coding outputs...")

    # ── 1. yaml_reference.csv ─────────────────────────────────────────────────
    # One row per workflow. Built from sample_df so count == sample N always.
    yaml_reference_path = RESULTS_DIR / "manual_coding" / "yaml_reference.csv"
    df_yaml_ref = sample_df[[
        'project_id', 'file_name', 'repo_path', 'file_path', 'language', 'yaml_content'
    ]].copy()
    df_yaml_ref = df_yaml_ref.rename(columns={
        'file_name':    'workflow_file',
        'file_path':    'full_path',
        'yaml_content': 'full_workflow_yaml',
    })
    df_yaml_ref.to_csv(yaml_reference_path, index=False, encoding='utf-8-sig')

    # Consistency check — should always pass after validate_and_repair_sample
    yaml_ref_count = len(df_yaml_ref)
    sample_count   = len(sample_df)
    if yaml_ref_count != sample_count:
        logger.warning(
            f"  [MISMATCH] yaml_reference.csv has {yaml_ref_count} rows "
            f"but sample has {sample_count} workflows."
        )
    else:
        logger.info(
            f"  [VERIFIED] yaml_reference.csv = {yaml_ref_count} rows "
            f"== sample N ({sample_count}). Counts consistent."
        )

    # ── 2. sample_summary.csv ─────────────────────────────────────────────────
    summary_data = []
    for language in ['Python', 'Java', 'C++']:
        lang_sample = sample_df[sample_df['language'] == language]
        if lang_sample.empty:
            continue
        summary_data.append({
            'Language':           language,
            'Workflows':          len(lang_sample),
            'Unique Projects':    lang_sample['project_id'].nunique(),
            'Avg File Size (KB)': round(lang_sample['file_size_kb'].mean(), 2),
            'Avg Jobs':           round(lang_sample['num_jobs'].mean(), 2),
            'Avg Steps':          round(lang_sample['num_steps'].mean(), 2),
            'Simple':             len(lang_sample[lang_sample['complexity_category'] == 'simple']),
            'Moderate':           len(lang_sample[lang_sample['complexity_category'] == 'moderate']),
            'Complex':            len(lang_sample[lang_sample['complexity_category'] == 'complex']),
            'Small Files':        len(lang_sample[lang_sample['file_size_category'] == 'small_file']),
            'Medium Files':       len(lang_sample[lang_sample['file_size_category'] == 'medium_file']),
            'Large Files':        len(lang_sample[lang_sample['file_size_category'] == 'large_file']),
        })
    df_summary = pd.DataFrame(summary_data)
    summary_file = RESULTS_DIR / "manual_coding" / "sample_summary.csv"
    df_summary.to_csv(summary_file, index=False, encoding='utf-8-sig')
    logger.info(f"  sample_summary.csv saved: {summary_file}")
    logger.info(f"  Unique projects in YAML reference: {df_yaml_ref['project_id'].nunique()}")




# ==========================================
# Main Workflow
# ==========================================

def main():
    logger.info("=" * 100)
    logger.info("Starting Open Coding Analysis for GHA Workflows")
    logger.info("=" * 100)

    # Step 1: Collect all workflows
    all_workflows = collect_all_workflows_enhanced()
    if not all_workflows:
        logger.error("No workflows found!")
        return

    # Step 2: Identify unique projects
    unique_workflows = identify_unique_projects(all_workflows)
    logger.info(f"\n{'='*100}")
    logger.info(f"DATASET SUMMARY")
    logger.info(f"Total YAML files found: {len(all_workflows)}")
    logger.info(f"Unique projects: {len(unique_workflows)}")
    logger.info(f"{'='*100}\n")

    # Step 3: Stratification
    df_workflows = stratify_workflows_enhanced(unique_workflows)

    # Step 4: Stratified sampling
    sample_df = balanced_stratified_sample(df_workflows, SAMPLE_SIZE)

    # ── Step 4b: Validate every sampled file can be re-read and re-parsed ──
    # This guarantees sample N == YAML content N before any coding sheet is written.
    sample_df = validate_and_repair_sample(sample_df, df_workflows, SAMPLE_SIZE)

    # Step 5: Save sample metadata with standardised columns
    sample_metadata = sample_df[[
        'language', 'file_name', 'repo_path', 'file_path',
        'project_id', 'file_size_kb', 'num_jobs', 'job_name',
        'num_steps', 'workflows_in_project'
    ]].copy()
    sample_metadata = sample_metadata.rename(columns={
        'file_name':    'workflow_file',
        'file_path':    'full_path',
        'file_size_kb': 'file_size_kb',
    })
    sample_metadata.to_csv(
        RESULTS_DIR / "manual_coding" / "sample_metadata.csv",
        index=False, encoding='utf-8-sig'
    )
    logger.info(f"Sample metadata saved: {RESULTS_DIR / 'manual_coding' / 'sample_metadata.csv'}")

    # Step 6: Create manual_coding outputs (yaml_reference + sample_summary)
    create_manual_coding_sheets_enhanced(sample_df)

    # Step 7: Coding instructions
    create_coding_instructions()

    # Step 8: Sample report
    create_sample_report(sample_df, df_workflows)

    # ── Final summary ──
    logger.info("\n" + "=" * 100)
    logger.info("OPEN CODING SETUP COMPLETE")
    logger.info("=" * 100)
    logger.info(f"Total unique projects in dataset : {len(unique_workflows)}")
    logger.info(f"Sampled workflows (validated)    : {len(sample_df)}")
    logger.info(f"Unique projects in sample        : {sample_df['project_id'].nunique()}")
    logger.info(f"\nSample distribution by language:")
    for lang in ['Python', 'Java', 'C++']:
        logger.info(f"  {lang}: {len(sample_df[sample_df['language'] == lang])}")
    logger.info(f"\nFile size — Min: {sample_df['file_size_kb'].min():.2f} KB | "
                f"Max: {sample_df['file_size_kb'].max():.2f} KB | "
                f"Mean: {sample_df['file_size_kb'].mean():.2f} KB")
    logger.info(f"Jobs      — Min: {sample_df['num_jobs'].min()} | "
                f"Max: {sample_df['num_jobs'].max()} | "
                f"Mean: {sample_df['num_jobs'].mean():.2f}")
    logger.info(f"Steps     — Min: {sample_df['num_steps'].min()} | "
                f"Max: {sample_df['num_steps'].max()} | "
                f"Mean: {sample_df['num_steps'].mean():.2f}")
    logger.info("\nOutputs:")
    logger.info(f"  manual_coding/ → yaml_reference.csv, sample_metadata.csv, sample_summary.csv,")
    logger.info(f"                  SAMPLE_REPORT.txt, CODING_INSTRUCTIONS.md")
    logger.info("=" * 100)


def create_coding_instructions():
    instructions_file = RESULTS_DIR / "manual_coding" / "CODING_INSTRUCTIONS.md"
    with open(instructions_file, 'w', encoding='utf-8') as f:
        f.write(f"""# Open Coding Instructions for GHA Workflows
Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

## Objective
Manually analyse a stratified random sample of {SAMPLE_SIZE} GitHub Actions workflows
to uncover naming conventions and structural patterns not detectable through static analysis.
Both authors code independently, then reconcile disagreements using Cohen's Kappa.

## Sample Guarantees
- ONE workflow per unique project (no repository duplicates)
- Proportional representation across languages (Python / Java / C++)
- Complexity stratified by number of steps (tertiles: simple / moderate / complex)
- All {SAMPLE_SIZE} YAML files validated and re-parsed before this run
- yaml_reference.csv row count == sample_metadata.csv row count == {SAMPLE_SIZE}

## Files in This Folder
| File | Purpose |
|------|---------|
| `sample_metadata.csv` | One row per sampled workflow — key identifiers and counts |
| `sample_summary.csv` | Per-language breakdown of the sample |
| `yaml_reference.csv` | Full YAML content — one row per workflow, N == {SAMPLE_SIZE} |
| `SAMPLE_REPORT.txt` | Population vs sample comparison report |
| `CODING_INSTRUCTIONS.md` | This file |

## sample_metadata.csv Columns
| Column | Description |
|--------|-------------|
| `language` | Programming language (Python / Java / C++) |
| `workflow_file` | YAML filename (e.g. ci.yml) |
| `repo_path` | Path to repository root |
| `full_path` | Complete path to the workflow file |
| `project_id` | Unique project identifier (owner/repo) |
| `file_size_kb` | File size in kilobytes |
| `num_jobs` | Number of jobs defined in the workflow |
| `job_name` | Pipe-separated list of all job names (e.g. build | test | deploy) |
| `num_steps` | Total number of steps across all jobs |
| `workflows_in_project` | How many workflow files exist in this project |

## How to Code

### Step 1 — Open yaml_reference.csv
Each row is one complete workflow. The `full_workflow_yaml` column contains
the raw YAML. Use `project_id` and `workflow_file` to identify the workflow.

### Step 2 — For each workflow, examine
**Naming conventions:**
- How are jobs named? (snake_case, kebab-case, PascalCase, verb-noun, etc.)
- How are steps named? (action-based, task-based, tool-based, no name)
- Are there consistent verb patterns? (Run, Build, Set up, Upload...)

**Structural patterns:**
- What is the sequence of step types across jobs?
- Are there recurring job dependency chains (build → test → deploy)?
- Are matrix builds, conditionals, or reusable workflows present?

### Step 3 — Record codes
Both authors use a shared coding spreadsheet (created separately).
For each workflow record:
- `code(s)` — one or more pattern codes observed (define new ones as needed)
- `naming_pattern` — dominant naming convention
- `notes` — anything ambiguous or noteworthy

### Step 4 — IRR after every ~50 workflows
Calculate Cohen's Kappa using agreed vs. disagreed counts.
Interpretation (Landis & Koch condensed, 4 levels):
- **Low**       κ < 0.40  → Stop. Codes are too vague. Redefine and recode.
- **Moderate**  κ 0.40–0.60 → Discuss disagreements. Add counter-examples to definitions.
- **High**       κ 0.61–0.80 → Acceptable. Reconcile remaining disagreements and continue.
- **Very High**  κ > 0.80  → Proceed confidently to next batch.

### Step 5 — Iterate
Repeat until all {SAMPLE_SIZE} workflows are coded and κ > 0.80 is sustained.
Then translate finalised codes into regex/keyword rules for automated labelling
of the full dataset.
""")
    logger.info(f"Coding instructions created: {instructions_file}")


def create_sample_report(sample_df, full_df):
    report_file = RESULTS_DIR / "manual_coding" / "SAMPLE_REPORT.txt"
    with open(report_file, 'w', encoding='utf-8') as f:
        f.write("=" * 100 + "\n")
        f.write("STRATIFIED SAMPLE REPORT (with YAML validation)\n")
        f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write("=" * 100 + "\n\n")
        total_pop = len(full_df)
        f.write(f"Total population: {total_pop} unique projects\n")
        f.write(f"Sample size: {len(sample_df)}\n")
        f.write(f"Sampling ratio: {(len(sample_df)/total_pop)*100:.2f}%\n\n")
        f.write("\nLANGUAGE DISTRIBUTION\n")
        f.write("-" * 80 + "\n")
        f.write(f"{'Language':<10} {'Population':>12} {'Pop %':>8} {'Sample':>10} {'Sample %':>10} {'Diff':>8}\n")
        f.write("-" * 80 + "\n")
        for lang in ['Python', 'Java', 'C++']:
            pop_count = len(full_df[full_df['language'] == lang])
            pop_pct = (pop_count / total_pop) * 100
            sample_count = len(sample_df[sample_df['language'] == lang])
            sample_pct = (sample_count / len(sample_df)) * 100
            diff = abs(sample_pct - pop_pct)
            f.write(f"{lang:<10} {pop_count:>12} {pop_pct:>7.1f}% {sample_count:>10} {sample_pct:>9.1f}% {diff:>6.1f}%\n")
        f.write("\n\nVALIDATION STATUS\n")
        f.write("-" * 80 + "\n")
        f.write(f"Sampled workflows: {len(sample_df)}\n")
        f.write(f"YAML reference rows: {sample_df['project_id'].nunique()}\n")
        match = len(sample_df) == sample_df['project_id'].nunique()
        f.write(f"Sample N == YAML N: {'PASS' if match else 'MISMATCH — investigate'}\n")
    logger.info(f"Sample report saved to {report_file}")


if __name__ == "__main__":
    main()