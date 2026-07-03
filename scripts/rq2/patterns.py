"""
RQ2 Analysis — CI Usage Patterns in GHA Workflows
===================================================
Outputs
-------
  construct_frequency.csv        — how often each semantic label appears (global + per-lang)
  top10_sequences.csv            — top-10 full sequences overall and per language
  common_sequences.csv           — full sequences meeting >=5% threshold (overall + per-lang)
  sequence_ngrams.csv            — most frequent 2-, 3-, 4-step prefixes / suffixes
  step_transitions.csv           — pairwise step-transition frequencies (Markov-style)
  step_cooccurrence.csv          — label pairs that appear together most often
  construct_absence.csv          — workflows with build but no test, etc.
  non_checkout_workflows.csv     — workflows whose first step is not Checkout Repository
  trigger_x_construct.csv        — trigger type vs construct presence rates
  modularity_x_complexity.csv    — modularity adoption vs sequence length / completeness
  pinning_by_language.csv        — version-pinning breakdown per language
  language_summary.csv           — structural summary per language
  rq2_summary.csv                — one-row global metrics
  rq2_summary.txt                — human-readable narrative report
"""

import pandas as pd
import itertools
from collections import Counter
from pathlib import Path

from repo_paths import RQ2_MANUAL_CODING_DIR, RQ2_PATTERN_ANALYSIS_DIR
from stats_utils import run_continuous_tests, run_proportion_tests

# ─────────────────────────────────────────────────────────────
# CONFIGURATION
# ─────────────────────────────────────────────────────────────
INPUT_PATH = RQ2_MANUAL_CODING_DIR / "processed_workflows.csv"
OUTPUT_DIR = RQ2_PATTERN_ANALYSIS_DIR
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

SEQ_SEP   = " -> "    # arrow token used in the CSV
THRESHOLD = 0.05      # 5% commonality threshold
TOP_N     = 10        # top-N sequences / constructs to report

# ─────────────────────────────────────────────────────────────
# LOAD & NORMALISE
# ─────────────────────────────────────────────────────────────
df = pd.read_csv(INPUT_PATH, encoding="utf-8-sig")

ARROW = " \u2192 "    # display arrow: →

def normalise_arrow(text) -> str:
    """Standardise arrow separator regardless of encoding artefacts."""
    if pd.isna(text):
        return ""
    text = str(text)
    # Fix UTF-8 mis-decoded as Latin-1
    text = text.replace("\u00e2\u0086\u0092", "\u2192")
    # Normalise all variants to the canonical arrow
    for variant in [" -> ", "->", " => ", "=>", " > "]:
        text = text.replace(variant, "\u2192")
    parts = [p.strip() for p in text.split("\u2192")]
    return ARROW.join(p for p in parts if p)

df["sequence_id"]   = df["sequence_id"].apply(normalise_arrow)
df["job_sequences"] = df["job_sequences"].apply(normalise_arrow)


def split_seq(seq: str) -> list:
    """Split a normalised sequence string into individual label tokens."""
    if not seq:
        return []
    return [s.strip() for s in seq.split("\u2192") if s.strip()]


# Derived columns — always use sequence_id (not job_sequences)
df["steps_list"]           = df["sequence_id"].apply(split_seq)
df["starts_with_checkout"] = df["steps_list"].apply(
    lambda s: s[0] == "Checkout Repository" if s else False
)
df["first_step"] = df["steps_list"].apply(lambda s: s[0] if s else "")
df["last_step"]  = df["steps_list"].apply(lambda s: s[-1] if s else "")

total = len(df)


# ─────────────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────────────
def safe_pct(series) -> float:
    """Mean of a 0/1 or bool column expressed as a percentage."""
    return round(pd.to_numeric(series, errors="coerce").mean() * 100, 2)


def top_n_sequences(frame: pd.DataFrame, scope: str, n: int = TOP_N) -> pd.DataFrame:
    """
    Top-N most frequent full sequence strings for a given frame.
    Always returns up to N rows regardless of the 5% threshold,
    so per-language rankings are always present.
    """
    total_n = len(frame)
    counts  = frame["sequence_id"].value_counts().head(n)
    rows = []
    for rank, (seq, cnt) in enumerate(counts.items(), 1):
        rows.append({
            "scope":           scope,
            "rank":            rank,
            "sequence_id":     seq,
            "count":           cnt,
            "percentage":      round(cnt / total_n * 100, 2),
            "meets_5pct":      cnt / total_n >= THRESHOLD,
            "sequence_length": len(split_seq(seq)),
        })
    return pd.DataFrame(rows)


def common_sequences(frame: pd.DataFrame, scope: str) -> pd.DataFrame:
    """Full sequence strings that appear in >=5% of the frame's workflows."""
    total_n = len(frame)
    counts  = frame["sequence_id"].value_counts()
    common  = counts[counts >= THRESHOLD * total_n]
    if common.empty:
        return pd.DataFrame(columns=["scope", "sequence_id", "count",
                                     "percentage", "sequence_length"])
    rows = [{
        "scope":           scope,
        "sequence_id":     seq,
        "count":           cnt,
        "percentage":      round(cnt / total_n * 100, 2),
        "sequence_length": len(split_seq(seq)),
    } for seq, cnt in common.items()]
    return pd.DataFrame(rows)


def construct_frequencies(frame: pd.DataFrame, scope: str) -> pd.DataFrame:
    """
    For each semantic label, count how many distinct workflows contain it.
    One count per workflow (set membership), not per occurrence.
    This is the primary operationalisation of 'frequently occurring constructs'.
    """
    n = len(frame)
    label_counts: Counter = Counter()
    for steps in frame["steps_list"]:
        for label in set(steps):
            label_counts[label] += 1
    rows = [{
        "scope":      scope,
        "construct":  label,
        "count":      cnt,
        "percentage": round(cnt / n * 100, 2),
        "is_common":  cnt / n >= THRESHOLD,
    } for label, cnt in label_counts.most_common()]
    return pd.DataFrame(rows)


# ─────────────────────────────────────────────────────────────
# 1. CONSTRUCT FREQUENCY  global + per-language
# ─────────────────────────────────────────────────────────────
cf_frames = [construct_frequencies(df, "global")]
for lang, grp in df.groupby("language"):
    cf_frames.append(construct_frequencies(grp, lang))
construct_freq_df = pd.concat(cf_frames, ignore_index=True)
construct_freq_df.to_csv(OUTPUT_DIR / "construct_frequency.csv", index=False,
                         encoding="utf-8-sig")


# ─────────────────────────────────────────────────────────────
# 2. TOP-10 SEQUENCES  global + per-language
# Decoupled from the 5% threshold — always shows TOP_N rows.
# ─────────────────────────────────────────────────────────────
top10_frames = [top_n_sequences(df, "global")]
for lang, grp in df.groupby("language"):
    top10_frames.append(top_n_sequences(grp, lang))
top10_df = pd.concat(top10_frames, ignore_index=True)
top10_df.to_csv(OUTPUT_DIR / "top10_sequences.csv", index=False, encoding="utf-8-sig")


# ─────────────────────────────────────────────────────────────
# 3. COMMON SEQUENCES >=5%  global + per-language
# ─────────────────────────────────────────────────────────────
cs_frames = [common_sequences(df, "global")]
for lang, grp in df.groupby("language"):
    cs_frames.append(common_sequences(grp, lang))
common_seq_df = pd.concat(cs_frames, ignore_index=True)
common_seq_df.sort_values(["scope", "percentage"], ascending=[True, False],
                          inplace=True)
common_seq_df.to_csv(OUTPUT_DIR / "common_sequences.csv", index=False, encoding="utf-8-sig")


# ─────────────────────────────────────────────────────────────
# 4. SEQUENCE N-GRAMS  (prefix & suffix, length 2-4)
# Captures sub-sequence patterns without requiring a full-string match.
# Answers: "What are the most common ways workflows START and END?"
# ─────────────────────────────────────────────────────────────
def ngram_counts(frame: pd.DataFrame, n: int,
                 position: str, scope: str) -> pd.DataFrame:
    total_n = len(frame)
    counter: Counter = Counter()
    for steps in frame["steps_list"]:
        if len(steps) >= n:
            gram = steps[:n] if position == "prefix" else steps[-n:]
            counter[ARROW.join(gram)] += 1
    rows = [{
        "scope":      scope,
        "position":   position,
        "n":          n,
        "ngram":      gram,
        "count":      cnt,
        "percentage": round(cnt / total_n * 100, 2),
    } for gram, cnt in counter.most_common(TOP_N)]
    return pd.DataFrame(rows)

ngram_frames = []
for n in (2, 3, 4):
    for pos in ("prefix", "suffix"):
        ngram_frames.append(ngram_counts(df, n, pos, "global"))
        for lang, grp in df.groupby("language"):
            ngram_frames.append(ngram_counts(grp, n, pos, lang))

ngram_df = pd.concat(ngram_frames, ignore_index=True)
ngram_df.to_csv(OUTPUT_DIR / "sequence_ngrams.csv", index=False, encoding="utf-8-sig")


# ─────────────────────────────────────────────────────────────
# 5. STEP TRANSITION MATRIX  (Markov-style)
# "After step A, what step most commonly follows?"
# Gives directional relationships between constructs and surfaces
# canonical sub-sequences (e.g. Checkout -> Setup -> Build).
# ─────────────────────────────────────────────────────────────
def transition_counts(frame: pd.DataFrame, scope: str,
                      top: int = 50) -> pd.DataFrame:
    trans: Counter = Counter()
    for steps in frame["steps_list"]:
        for a, b in zip(steps, steps[1:]):
            trans[(a, b)] += 1
    total_trans = sum(trans.values())
    rows = [{
        "scope":                   scope,
        "from_step":               a,
        "to_step":                 b,
        "count":                   cnt,
        "pct_of_all_transitions":  round(cnt / total_trans * 100, 3)
                                   if total_trans else 0,
    } for (a, b), cnt in trans.most_common(top)]
    return pd.DataFrame(rows)

trans_frames = [transition_counts(df, "global")]
for lang, grp in df.groupby("language"):
    trans_frames.append(transition_counts(grp, lang))
transitions_df = pd.concat(trans_frames, ignore_index=True)
transitions_df.to_csv(OUTPUT_DIR / "step_transitions.csv", index=False, encoding="utf-8-sig")


# ─────────────────────────────────────────────────────────────
# 6. STEP CO-OCCURRENCE
# "Which construct pairs appear together in the same workflow?"
# Indicates functional coupling independent of sequence order.
# ─────────────────────────────────────────────────────────────
def cooccurrence_counts(frame: pd.DataFrame, scope: str,
                        top: int = 30) -> pd.DataFrame:
    pair_counter: Counter = Counter()
    for steps in frame["steps_list"]:
        unique = sorted(set(steps))
        for a, b in itertools.combinations(unique, 2):
            pair_counter[(a, b)] += 1
    n = len(frame)
    rows = [{
        "scope":      scope,
        "step_a":     a,
        "step_b":     b,
        "count":      cnt,
        "percentage": round(cnt / n * 100, 2),
    } for (a, b), cnt in pair_counter.most_common(top)]
    return pd.DataFrame(rows)

coocc_frames = [cooccurrence_counts(df, "global")]
for lang, grp in df.groupby("language"):
    coocc_frames.append(cooccurrence_counts(grp, lang))
cooccurrence_df = pd.concat(coocc_frames, ignore_index=True)
cooccurrence_df.to_csv(OUTPUT_DIR / "step_cooccurrence.csv", index=False, encoding="utf-8-sig")


# ─────────────────────────────────────────────────────────────
# 7. CONSTRUCT ABSENCE ANALYSIS
# Flags workflows that have one construct but are MISSING another
# that is canonically expected alongside it.
# "Build without test", "test without checkout", etc.
# Deviations from canonical sequences per the methodology.
# ─────────────────────────────────────────────────────────────
BUILD_LABELS = {
    "Build Project", "Build Package", "Build Application",
    "Build Container Image", "Build Static Site", "Build Documentation",
    "Build Source Code", "Build Firmware", "Build Python Wheel", "Build Library",
}
SETUP_LABELS = {
    "Setup Runtime Environment", "Setup Build Environment",
    "Setup Package Manager", "Configure Build Profile",
    "Setup Virtual Environment", "Setup Base Environment",
    "Setup Local Environment", "Setup Cache Service",
    "Setup Network Connectivity", "Setup Runtime Tool",
}

def has_any(steps: list, label_set: set) -> bool:
    return bool(set(steps) & label_set)

df["_has_build"]    = df["steps_list"].apply(lambda s: has_any(s, BUILD_LABELS))
df["_has_setup"]    = df["steps_list"].apply(lambda s: has_any(s, SETUP_LABELS))
df["_has_test"]     = df["steps_list"].apply(lambda s: "Execute Tests" in s)
df["_has_checkout"] = df["steps_list"].apply(lambda s: "Checkout Repository" in s)

absence_defs = {
    "build_no_test":         df["_has_build"]    & ~df["_has_test"],
    "test_no_build":         df["_has_test"]     & ~df["_has_build"],
    "test_no_checkout":      df["_has_test"]     & ~df["_has_checkout"],
    "build_no_checkout":     df["_has_build"]    & ~df["_has_checkout"],
    "build_no_setup":        df["_has_build"]    & ~df["_has_setup"],
    "test_no_setup":         df["_has_test"]     & ~df["_has_setup"],
    "checkout_only":         df["_has_checkout"] & ~df["_has_build"] & ~df["_has_test"],
    "no_checkout_no_setup":  ~df["_has_checkout"] & ~df["_has_setup"],
}

absence_rows = []
for lang, grp in df.groupby("language"):
    n_lang = len(grp)
    for pname, mask in absence_defs.items():
        cnt = int(mask[grp.index].sum())
        absence_rows.append({
            "scope": lang, "pattern": pname,
            "count": cnt,
            "percentage": round(cnt / n_lang * 100, 2),
        })
for pname, mask in absence_defs.items():
    cnt = int(mask.sum())
    absence_rows.append({
        "scope": "global", "pattern": pname,
        "count": cnt,
        "percentage": round(cnt / total * 100, 2),
    })

absence_df = pd.DataFrame(absence_rows)
absence_df.to_csv(OUTPUT_DIR / "construct_absence.csv", index=False, encoding="utf-8-sig")

# Drop temp columns
df.drop(columns=["_has_build", "_has_setup", "_has_test", "_has_checkout"],
        inplace=True, errors="ignore")


# ─────────────────────────────────────────────────────────────
# 8. NON-CHECKOUT-FIRST WORKFLOWS
# Workflows whose merged sequence_id does not start with
# "Checkout Repository" — candidates for deviation analysis.
# ─────────────────────────────────────────────────────────────
export_cols = [c for c in df.columns
               if c not in ("steps_list",)]
non_checkout_df = df[~df["starts_with_checkout"]][export_cols].copy()
non_checkout_df.to_csv(OUTPUT_DIR / "non_checkout_workflows.csv", index=False,
                       encoding="utf-8-sig")


# ─────────────────────────────────────────────────────────────
# 9. TRIGGER x CONSTRUCT CROSS-ANALYSIS
# "Do push-triggered workflows look structurally different
#  from PR-triggered or scheduled ones?"
# Surfaces whether trigger type correlates with pipeline shape.
# ─────────────────────────────────────────────────────────────
trigger_map = {
    "push":              "has_push",
    "pull_request":      "has_pull_request",
    "schedule":          "has_schedule",
    "workflow_dispatch": "has_workflow_dispatch",
}
construct_map = {
    "checkout":  "has_checkout",
    "setup":     "has_setup",
    "build":     "has_build",
    "test":      "has_test",
    "cache":     "uses_cache",
    "reusable":  "uses_reusable_workflows",
    "composite": "uses_composite_actions",
}

trig_rows = []
for trig_name, trig_col in trigger_map.items():
    if trig_col not in df.columns:
        continue
    mask      = pd.to_numeric(df[trig_col], errors="coerce") == 1
    trig_grp  = df[mask]
    notrig    = df[~mask]
    for c_name, c_col in construct_map.items():
        if c_col not in df.columns:
            continue
        trig_rows.append({
            "trigger":          trig_name,
            "construct":        c_name,
            "pct_with_trigger": safe_pct(trig_grp[c_col]),
            "pct_without":      safe_pct(notrig[c_col]),
            "n_with":           len(trig_grp),
            "n_without":        len(notrig),
            "diff":             round(safe_pct(trig_grp[c_col]) -
                                      safe_pct(notrig[c_col]), 2),
        })

trigger_x_construct_df = pd.DataFrame(trig_rows)
trigger_x_construct_df.to_csv(OUTPUT_DIR / "trigger_x_construct.csv", index=False,
                               encoding="utf-8-sig")


# ─────────────────────────────────────────────────────────────
# 10. MODULARITY x COMPLEXITY
# "Are workflows using reusable workflows or composite actions
#  longer / more complete / better pinned?"
# ─────────────────────────────────────────────────────────────
mod_map = {
    "reusable_workflow": "uses_reusable_workflows",
    "composite_action":  "uses_composite_actions",
}

mod_rows = []
for mod_name, mod_col in mod_map.items():
    if mod_col not in df.columns:
        continue
    mask = pd.to_numeric(df[mod_col], errors="coerce") == 1
    for label, grp in (("uses", df[mask]), ("no_use", df[~mask])):
        mod_rows.append({
            "modularity_type":      mod_name,
            "group":                label,
            "n":                    len(grp),
            "avg_sequence_length":  round(grp["sequence_length"].mean(), 2),
            "avg_completeness":     round(grp["completeness_score"].mean(), 3),
            "pct_sha_pinned":       round((pd.to_numeric(
                grp["pinned_to_sha"], errors="coerce") > 0).mean() * 100, 2),
            "pct_uses_cache":       safe_pct(grp["uses_cache"]),
            "pct_has_test":         safe_pct(grp["has_test"]),
            "pct_has_build":        safe_pct(grp["has_build"]),
        })

modularity_x_complexity_df = pd.DataFrame(mod_rows)
modularity_x_complexity_df.to_csv(OUTPUT_DIR / "modularity_x_complexity.csv", index=False,
                                   encoding="utf-8-sig")


# ─────────────────────────────────────────────────────────────
# 11. VERSION PINNING BY LANGUAGE
# Which language communities are most / least security-conscious?
# ─────────────────────────────────────────────────────────────
pin_rows = []
for lang, grp in df.groupby("language"):
    def _pct_any(col):
        return round((pd.to_numeric(grp[col], errors="coerce") > 0
                      ).mean() * 100, 2) if col in grp.columns else None
    def _avg(col):
        return round(pd.to_numeric(grp[col], errors="coerce"
                                   ).mean(), 2) if col in grp.columns else None
    pin_rows.append({
        "language":           lang,
        "n":                  len(grp),
        "pct_any_sha":        _pct_any("pinned_to_sha"),
        "pct_any_tag":        _pct_any("pinned_to_tag"),
        "pct_any_branch":     _pct_any("pinned_to_branch"),
        "pct_any_unpinned":   _pct_any("unpinned"),
        "avg_sha_count":      _avg("pinned_to_sha"),
        "avg_tag_count":      _avg("pinned_to_tag"),
        "avg_unpinned_count": _avg("unpinned"),
    })
pin_df = pd.DataFrame(pin_rows)
pin_df.to_csv(OUTPUT_DIR / "pinning_by_language.csv", index=False, encoding="utf-8-sig")


# ─────────────────────────────────────────────────────────────
# 12. PER-LANGUAGE SUMMARY
# ─────────────────────────────────────────────────────────────
lang_rows = []
for lang, grp in df.groupby("language"):
    n    = len(grp)
    top  = top_n_sequences(grp, lang)
    comm = common_sequences(grp, lang)
    lang_rows.append({
        "language":                  lang,
        "workflow_count":            n,
        "avg_sequence_length":       round(grp["sequence_length"].mean(), 2),
        "median_sequence_length":    grp["sequence_length"].median(),
        "max_sequence_length":       int(grp["sequence_length"].max()),
        "pct_has_checkout":          safe_pct(grp["has_checkout"]),
        "pct_has_setup":             safe_pct(grp["has_setup"]),
        "pct_has_build":             safe_pct(grp["has_build"]),
        "pct_has_test":              safe_pct(grp["has_test"]),
        "avg_completeness_score":    round(grp["completeness_score"].mean(), 3),
        "pct_starts_with_checkout":  safe_pct(grp["starts_with_checkout"]),
        "pct_push":                  safe_pct(grp["has_push"]),
        "pct_pull_request":          safe_pct(grp["has_pull_request"]),
        "pct_schedule":              safe_pct(grp["has_schedule"]),
        "pct_workflow_dispatch":     safe_pct(grp["has_workflow_dispatch"]),
        "pct_uses_cache":            safe_pct(grp["uses_cache"]),
        "pct_reusable_workflows":    safe_pct(grp["uses_reusable_workflows"]),
        "pct_composite_actions":     safe_pct(grp["uses_composite_actions"]),
        "avg_modularity_constructs": round(pd.to_numeric(
            grp["total_modularity_constructs"],
            errors="coerce").mean(), 2),
        "pct_any_sha_pinned":        round((pd.to_numeric(
            grp["pinned_to_sha"], errors="coerce") > 0).mean() * 100, 2),
        "pct_any_tag_pinned":        round((pd.to_numeric(
            grp["pinned_to_tag"], errors="coerce") > 0).mean() * 100, 2),
        "pct_any_unpinned":          round((pd.to_numeric(
            grp["unpinned"], errors="coerce") > 0).mean() * 100, 2),
        "top1_sequence":             top.iloc[0]["sequence_id"]
                                     if not top.empty else "",
        "top1_pct":                  top.iloc[0]["percentage"]
                                     if not top.empty else 0.0,
        "common_seq_count_5pct":     len(comm),
    })

lang_summary_df = pd.DataFrame(lang_rows)
lang_summary_df.to_csv(OUTPUT_DIR / "language_summary.csv", index=False, encoding="utf-8-sig")


# ─────────────────────────────────────────────────────────────
# 13. GLOBAL SUMMARY (one-row CSV)
# ─────────────────────────────────────────────────────────────
gc     = construct_frequencies(df, "global")
gc_top = top_n_sequences(df, "global")
gc_com = common_sequences(df, "global")

summary = {
    "total_workflows":             total,
    "avg_sequence_length":         round(df["sequence_length"].mean(), 2),
    "median_sequence_length":      df["sequence_length"].median(),
    "pct_has_checkout":            safe_pct(df["has_checkout"]),
    "pct_has_setup":               safe_pct(df["has_setup"]),
    "pct_has_build":               safe_pct(df["has_build"]),
    "pct_has_test":                safe_pct(df["has_test"]),
    "avg_completeness_score":      round(df["completeness_score"].mean(), 3),
    "pct_starts_with_checkout":    safe_pct(df["starts_with_checkout"]),
    "non_checkout_first_count":    int((~df["starts_with_checkout"]).sum()),
    "pct_push":                    safe_pct(df["has_push"]),
    "pct_pull_request":            safe_pct(df["has_pull_request"]),
    "pct_schedule":                safe_pct(df["has_schedule"]),
    "pct_workflow_dispatch":       safe_pct(df["has_workflow_dispatch"]),
    "pct_uses_cache":              safe_pct(df["uses_cache"]),
    "pct_reusable_workflows":      safe_pct(df["uses_reusable_workflows"]),
    "pct_composite_actions":       safe_pct(df["uses_composite_actions"]),
    "pct_any_sha_pinned":          round((pd.to_numeric(
        df["pinned_to_sha"], errors="coerce") > 0).mean() * 100, 2),
    "pct_any_tag_pinned":          round((pd.to_numeric(
        df["pinned_to_tag"], errors="coerce") > 0).mean() * 100, 2),
    "pct_any_unpinned":            round((pd.to_numeric(
        df["unpinned"], errors="coerce") > 0).mean() * 100, 2),
    "common_constructs_count":     int(gc["is_common"].sum()),
    "common_full_sequences_count": len(gc_com),
}
pd.DataFrame([summary]).to_csv(OUTPUT_DIR / "rq2_summary.csv", index=False,
                                encoding="utf-8-sig")


# ─────────────────────────────────────────────────────────────
# 14. HUMAN-READABLE REPORT
# ─────────────────────────────────────────────────────────────
def section(f, title):
    f.write(f"\n{'='*65}\n{title}\n{'='*65}\n")


with open(OUTPUT_DIR / "rq2_summary.txt", "w", encoding="utf-8") as f:

    section(f, "RQ2 Overall Summary")
    for k, v in summary.items():
        f.write(f"  {k:<44} {v}\n")

    # ── Common constructs globally ─────────────────────────────
    section(f, f"Common Step Constructs (>={THRESHOLD:.0%} of {total} workflows)")
    common_c = gc[gc["is_common"]].sort_values("percentage", ascending=False)
    for _, row in common_c.iterrows():
        f.write(f"  {row['construct']:<50} {row['count']:>5}  "
                f"({row['percentage']:.1f}%)\n")

    # ── Top-10 globally ────────────────────────────────────────
    section(f, f"Top-{TOP_N} Full Sequences — GLOBAL (all languages)")
    f.write("  (* = meets >=5% threshold)\n\n")
    for _, row in gc_top.iterrows():
        star = " *" if row["meets_5pct"] else "  "
        f.write(f"  #{int(row['rank']):<2}{star} [{row['count']:>4} | "
                f"{row['percentage']:>5.1f}%]  len={row['sequence_length']}\n"
                f"       {row['sequence_id']}\n\n")

    # ── Common full sequences globally ─────────────────────────
    section(f, f"Full Sequences Meeting >={THRESHOLD:.0%} — GLOBAL")
    if gc_com.empty:
        f.write("  None reached 5%.\n")
        f.write("  Full sequences are almost always unique.\n")
        f.write("  Use construct frequency as the primary pattern metric.\n")
    else:
        for _, row in gc_com.iterrows():
            f.write(f"  [{row['count']} | {row['percentage']:.1f}%]  "
                    f"{row['sequence_id']}\n")

    # ── Top-10 per language ────────────────────────────────────
    section(f, f"Top-{TOP_N} Sequences Per Language")
    for lang in sorted(df["language"].unique()):
        grp  = df[df["language"] == lang]
        top  = top_n_sequences(grp, lang)
        comm = common_sequences(grp, lang)
        f.write(f"\n  ── {lang.upper()}  (n={len(grp)}, "
                f">=5% patterns: {len(comm)}) ──\n")
        f.write("    (* = meets >=5% threshold for this language)\n\n")
        for _, row in top.iterrows():
            star = " *" if row["meets_5pct"] else "  "
            f.write(f"    #{int(row['rank']):<2}{star}"
                    f" [{row['count']:>4} | {row['percentage']:>5.1f}%]"
                    f"  len={row['sequence_length']}\n"
                    f"         {row['sequence_id']}\n\n")

    # ── Top transitions globally ───────────────────────────────
    section(f, "Top-20 Step Transitions (globally)")
    global_trans = transitions_df[
        transitions_df["scope"] == "global"].head(20)
    for _, row in global_trans.iterrows():
        f.write(f"  {row['from_step']:<42} -> {row['to_step']:<42}"
                f"  {row['count']:>5}  ({row['pct_of_all_transitions']:.2f}%)\n")

    # ── Top co-occurrence globally ─────────────────────────────
    section(f, "Top-20 Co-occurring Construct Pairs (globally)")
    global_coocc = cooccurrence_df[
        cooccurrence_df["scope"] == "global"].head(20)
    for _, row in global_coocc.iterrows():
        f.write(f"  {row['step_a']:<42} + {row['step_b']:<42}"
                f"  {row['count']:>5}  ({row['percentage']:.1f}%)\n")

    # ── Prefix n-grams globally ────────────────────────────────
    section(f, "Most Common Sequence Prefixes (global, length 2-4)")
    for n in (2, 3, 4):
        sub = ngram_df[
            (ngram_df["scope"] == "global") &
            (ngram_df["n"] == n) &
            (ngram_df["position"] == "prefix")
        ].head(5)
        f.write(f"\n  {n}-step prefixes:\n")
        for _, row in sub.iterrows():
            f.write(f"    [{row['count']:>4} | {row['percentage']:>5.1f}%]"
                    f"  {row['ngram']}\n")

    # ── Suffix n-grams globally ────────────────────────────────
    section(f, "Most Common Sequence Suffixes (global, length 2-4)")
    for n in (2, 3, 4):
        sub = ngram_df[
            (ngram_df["scope"] == "global") &
            (ngram_df["n"] == n) &
            (ngram_df["position"] == "suffix")
        ].head(5)
        f.write(f"\n  {n}-step suffixes:\n")
        for _, row in sub.iterrows():
            f.write(f"    [{row['count']:>4} | {row['percentage']:>5.1f}%]"
                    f"  {row['ngram']}\n")

    # ── Construct absence globally ─────────────────────────────
    section(f, "Construct Absence Patterns (global)")
    global_abs = absence_df[absence_df["scope"] == "global"].sort_values(
        "percentage", ascending=False)
    for _, row in global_abs.iterrows():
        f.write(f"  {row['pattern']:<35}  {row['count']:>5}  "
                f"({row['percentage']:.1f}%)\n")

    # ── Non-checkout first ─────────────────────────────────────
    section(f, "Non-Checkout-First Workflows")
    nc = summary["non_checkout_first_count"]
    f.write(f"  Count: {nc} / {total}  ({nc/total:.1%})\n\n")
    f.write("  Top-20 actual first steps in these workflows:\n")
    for step, cnt in (non_checkout_df["first_step"]
                      .value_counts().head(20).items()):
        f.write(f"    {step:<50} {cnt:>5}  ({cnt/total:.1%})\n")

    # ── Trigger x construct ────────────────────────────────────
    section(f, "Trigger x Construct: presence % by trigger type")
    try:
        pivot = trigger_x_construct_df.pivot_table(
            index="construct", columns="trigger",
            values="pct_with_trigger", aggfunc="first"
        )
        f.write(pivot.to_string())
        f.write("\n\n  (diff = pct_with_trigger minus pct_without_trigger)\n")
        diff_pivot = trigger_x_construct_df.pivot_table(
            index="construct", columns="trigger",
            values="diff", aggfunc="first"
        )
        f.write(diff_pivot.to_string())
        f.write("\n")
    except Exception as e:
        f.write(f"  Could not pivot: {e}\n")

    # ── Modularity x complexity ────────────────────────────────
    section(f, "Modularity x Complexity")
    for _, row in modularity_x_complexity_df.iterrows():
        f.write(f"  [{row['modularity_type']} | {row['group']}]"
                f"  n={row['n']}"
                f"  avg_len={row['avg_sequence_length']}"
                f"  completeness={row['avg_completeness']}"
                f"  SHA-pinned={row['pct_sha_pinned']}%"
                f"  cache={row['pct_uses_cache']}%\n")

    # ── Pinning by language ────────────────────────────────────
    section(f, "Version Pinning by Language")
    for _, row in pin_df.sort_values(
            "pct_any_unpinned", ascending=False).iterrows():
        f.write(f"  {row['language']:<14}  n={row['n']:<5}  "
                f"SHA={row['pct_any_sha']:.1f}%  "
                f"tag={row['pct_any_tag']:.1f}%  "
                f"branch={row['pct_any_branch']:.1f}%  "
                f"unpinned={row['pct_any_unpinned']:.1f}%\n")


print("RQ2 analysis complete. Files written:")
outputs = [
    ("construct_frequency.csv",     "per-construct frequency, global + per-language"),
    ("top10_sequences.csv",         f"top-{TOP_N} full sequences, global + per-language"),
    ("common_sequences.csv",        "full sequences meeting >=5% threshold"),
    ("sequence_ngrams.csv",         "2/3/4-step prefix and suffix n-grams"),
    ("step_transitions.csv",        "step-to-step transition counts"),
    ("step_cooccurrence.csv",       "pairwise construct co-occurrence"),
    ("construct_absence.csv",       "canonical absence flags per language + global"),
    ("non_checkout_workflows.csv",  "workflows not starting with Checkout Repository"),
    ("trigger_x_construct.csv",     "trigger type x construct presence cross-table"),
    ("modularity_x_complexity.csv", "modularity vs complexity comparison"),
    ("pinning_by_language.csv",     "version-pinning breakdown per language"),
    ("language_summary.csv",        "structural summary per language"),
    ("rq2_summary.csv",             "one-row global metrics"),
    ("rq2_summary.txt",             "full narrative report"),
]
for fname, desc in outputs:
    print(f"  {fname:<40} {desc}")


# ─────────────────────────────────────────────────────────────
# CROSS-LANGUAGE STATISTICAL TESTS
# ─────────────────────────────────────────────────────────────

RQ2_LANG_MAP = {"java": "Java", "python": "Python", "c++": "C++"}

RQ2_CONTINUOUS_METRICS = [
    "sequence_length",
    "num_steps_total",
    "completeness_score",
    "num_jobs",
    "avg_steps_per_job",
    "dependency_depth",
    "external_actions_count",
    "sha_percentage",
]

RQ2_BINARY_FEATURES = [
    "has_checkout",
    "has_setup",
    "has_test",
    "has_build",
    "uses_cache",
    "uses_reusable_workflows",
    "uses_composite_actions",
    "has_push",
    "has_pull_request",
    "has_schedule",
    "has_workflow_dispatch",
]


def run_statistical_tests() -> None:
    """Cross-language tests on the stratified sample (N=382)."""
    stats_dir = RQ2_PATTERN_ANALYSIS_DIR / "stats"
    stats_dir.mkdir(parents=True, exist_ok=True)

    proc = pd.read_csv(RQ2_MANUAL_CODING_DIR / "processed_workflows.csv", encoding="utf-8-sig")
    proc["language"] = proc["language"].map(RQ2_LANG_MAP).fillna(proc["language"])
    proc["any_sha_pinned"] = (proc["pinned_to_sha"].fillna(0) > 0).astype(int)

    continuous = run_continuous_tests(proc, RQ2_CONTINUOUS_METRICS)
    proportions = run_proportion_tests(proc, RQ2_BINARY_FEATURES + ["any_sha_pinned"])

    if continuous.empty:
        continuous = pd.DataFrame(columns=[
            "metric", "test", "comparison", "statistic", "p_value", "p_formatted",
            "effect_size", "interpretation", "significant",
        ])
    if proportions.empty:
        proportions = pd.DataFrame(columns=[
            "feature", "test", "comparison", "statistic", "p_value", "p_formatted",
            "effect_size", "interpretation", "significant",
        ])

    continuous.to_csv(stats_dir / "continuous_statistical_tests.csv", index=False)
    proportions.to_csv(stats_dir / "proportion_statistical_tests.csv", index=False)

    if continuous.empty and proportions.empty:
        print("Statistical tests skipped: no valid metrics in processed_workflows.csv")
        return

    if "test" in continuous.columns:
        notable_c = continuous[
            (continuous["test"] == "Mann-Whitney U")
            & continuous["interpretation"].isin(["small", "medium", "large"])
        ]
    else:
        notable_c = continuous.iloc[0:0]
    if "test" in proportions.columns:
        notable_p = proportions[
            (proportions["test"] == "Fisher's exact")
            & proportions["interpretation"].isin(["small", "medium", "large"])
        ]
    else:
        notable_p = proportions.iloc[0:0]

    summary_path = stats_dir / "statistical_tests_summary.txt"
    with summary_path.open("w", encoding="utf-8") as handle:
        handle.write("RQ2 Statistical Tests Summary (N=382)\n")
        handle.write("=" * 60 + "\n\n")
        if "test" in continuous.columns and "significant" in continuous.columns:
            kw_sig = (continuous["test"] == "Kruskal-Wallis") & continuous["significant"]
            mw_sig = (continuous["test"] == "Mann-Whitney U") & continuous["significant"]
        else:
            kw_sig = mw_sig = pd.Series(dtype=bool)
        if "test" in proportions.columns and "significant" in proportions.columns:
            chi_sig = (proportions["test"] == "Chi-square") & proportions["significant"]
            fisher_sig = (proportions["test"] == "Fisher's exact") & proportions["significant"]
        else:
            chi_sig = fisher_sig = pd.Series(dtype=bool)
        handle.write(f"Significant Kruskal-Wallis tests: {kw_sig.sum()}\n")
        handle.write(f"Significant Mann-Whitney tests: {mw_sig.sum()}\n")
        handle.write(f"Significant chi-square tests: {chi_sig.sum()}\n")
        handle.write(f"Significant Fisher tests: {fisher_sig.sum()}\n\n")
        handle.write("Notable continuous comparisons:\n")
        for _, row in notable_c.iterrows():
            handle.write(
                f"  {row['metric']}: {row['comparison']} "
                f"delta={row['effect_size']} p={row['p_formatted']}\n"
            )
        handle.write("\nNotable proportion comparisons:\n")
        for _, row in notable_p.iterrows():
            handle.write(
                f"  {row['feature']}: {row['comparison']} "
                f"{row['prop1_pct']}% vs {row['prop2_pct']}% "
                f"h={row['effect_size']} p={row['p_formatted']}\n"
            )

    print(f"\nStatistical tests written to {stats_dir}")


run_statistical_tests()