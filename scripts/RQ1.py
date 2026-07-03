# ==========================================
# RQ1 – Comprehensive GHA Workflow Complexity Analysis
#
# workflow_content is saved to a SEPARATE file (workflow_content.csv)
# keyed by full_path. It is NOT included in the main metrics CSV so it
# can never distort or overflow any column there.
#
# INTERPRETATION: 70/80/90 percentile VALUE-threshold
#   low (≤P70) | moderate (P70–P80) | high (P80–P90) | very high (>P90)
#   Identical metric values always land in the same band.
# ==========================================

import os
import yaml
import pandas as pd
import numpy as np
import seaborn as sns
import matplotlib.pyplot as plt
from scipy.stats import mannwhitneyu, kruskal
from itertools import combinations
from pathlib import Path
import logging
from datetime import datetime
import re
from collections import Counter
import csv

# ==========================================
# Configuration
# ==========================================

from repo_paths import RQ1_RESULTS_DIR, WORKFLOW_LANG_DIRS

RESULTS_DIR = RQ1_RESULTS_DIR

LANG_ORDER = ["Python", "Java", "C++"]

CORE_METRICS = [
    "lines_of_yaml", "num_jobs", "num_steps", "max_nesting_depth",
    "job_parallelism", "max_sequential_steps", "vertical_depth", "matrix_size",
    "num_conditionals", "num_job_dependencies", "num_reusable_workflows",
    "num_unique_external_actions", "num_local_actions", "num_marketplace_actions",
]

DERIVED_METRICS = [
    "avg_steps_per_job", "dependency_ratio",
    "external_action_diversity", "conditional_density",
]

BINARY_METRICS = [
    "has_matrix", "has_conditionals", "uses_reusable_workflows",
    "uses_external_actions", "uses_local_actions", "has_job_dependencies",
]

INTERPRETATION_LABELS = ["low", "moderate", "high", "very high"]

# Create output directories
for sub in ["figures/individual", "tables", "stats", "interpretations"]:
    (RESULTS_DIR / sub).mkdir(parents=True, exist_ok=True)

sns.set_style("whitegrid")
sns.set_palette("Set2")

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(RESULTS_DIR / 'rq1_analysis.log', encoding='utf-8'),
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger(__name__)

import sys
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')



# ==========================================
# Utilities
# ==========================================

def count_lines(fp):
    try:
        with open(fp, encoding="utf-8") as f:
            return sum(1 for _ in f)
    except Exception as e:
        logger.warning(f"Could not count lines in {fp}: {e}")
        return 0


def calculate_nesting_depth(obj, depth=0):
    if not isinstance(obj, dict):
        return depth
    max_depth = depth
    for v in obj.values():
        if isinstance(v, (dict, list)):
            max_depth = max(max_depth, calculate_nesting_depth(v, depth + 1))
    return max_depth


def calculate_job_parallelism(wf):
    if not isinstance(wf, dict) or 'jobs' not in wf:
        return 0
    return len(wf.get('jobs', {}))


def calculate_max_sequential_steps(wf):
    if not isinstance(wf, dict) or 'jobs' not in wf:
        return 0
    max_steps = 0
    for job in wf.get('jobs', {}).values():
        if isinstance(job, dict):
            steps = len(job.get('steps', []))
            max_steps = max(max_steps, steps)
    return max_steps


def calculate_vertical_depth(wf):
    if not isinstance(wf, dict) or 'jobs' not in wf:
        return 0
    jobs = wf.get('jobs', {})
    dependencies = {}
    for job_name, job in jobs.items():
        if isinstance(job, dict):
            needs = job.get('needs', [])
            if isinstance(needs, str):
                needs = [needs]
            elif not isinstance(needs, list):
                needs = []
            dependencies[job_name] = needs

    def dfs_depth(job_name, visited=None):
        if visited is None:
            visited = set()
        if job_name in visited:
            return 0
        visited.add(job_name)
        deps = dependencies.get(job_name, [])
        if not deps:
            return 1
        max_dep_depth = 0
        for dep in deps:
            if dep in dependencies:
                max_dep_depth = max(max_dep_depth, dfs_depth(dep, visited.copy()))
        return max_dep_depth + 1

    return max(dfs_depth(j) for j in jobs.keys()) if jobs else 0


# ==========================================
# Feature Detectors
# ==========================================

def analyze_matrix(wf):
    has_matrix = False
    total_combinations = 0
    for job in wf.get('jobs', {}).values():
        if not isinstance(job, dict):
            continue
        if 'strategy' in job and isinstance(job['strategy'], dict):
            matrix = job['strategy'].get('matrix', {})
            if matrix and isinstance(matrix, dict):
                has_matrix = True
                dimensions = [
                    len(v) for k, v in matrix.items()
                    if k not in ('include', 'exclude') and isinstance(v, list)
                ]
                if dimensions:
                    job_combos = 1
                    for d in dimensions:
                        job_combos *= d
                    if 'include' in matrix and isinstance(matrix['include'], list):
                        job_combos += len(matrix['include'])
                    if 'exclude' in matrix and isinstance(matrix['exclude'], list):
                        job_combos -= len(matrix['exclude'])
                    total_combinations += max(0, job_combos)
    return has_matrix, total_combinations


def count_conditionals(wf):
    count = 0
    for job in wf.get('jobs', {}).values():
        if not isinstance(job, dict):
            continue
        if 'if' in job:
            count += 1
        for step in job.get('steps', []):
            if isinstance(step, dict) and 'if' in step:
                count += 1
    return count


def count_job_dependencies(wf):
    count = 0
    for job in wf.get('jobs', {}).values():
        if not isinstance(job, dict):
            continue
        needs = job.get('needs', [])
        if isinstance(needs, str):
            count += 1
        elif isinstance(needs, list):
            count += len(needs)
    return count


def analyze_action_usage(wf):
    local_actions       = set()
    reusable_workflows  = set()
    external_actions    = set()
    marketplace_actions = set()

    for job_name, job in wf.get('jobs', {}).items():
        if not isinstance(job, dict):
            continue
        if 'uses' in job:
            reusable_workflows.add(job['uses'])
        for step in job.get('steps', []):
            if not isinstance(step, dict):
                continue
            if 'uses' in step:
                action = step['uses']
                if action.startswith('./') or action.startswith('.\\'):
                    local_actions.add(action)
                elif '/' in action:
                    action_name = action.split('@')[0] if '@' in action else action
                    external_actions.add(action_name)
                    if action_name.count('/') == 1 and not action_name.startswith('actions/'):
                        marketplace_actions.add(action_name)

    return {
        'num_local_actions':            len(local_actions),
        'num_reusable_workflows':       len(reusable_workflows),
        'num_unique_external_actions':  len(external_actions),
        'num_marketplace_actions':      len(marketplace_actions),
        'uses_local_actions':           len(local_actions) > 0,
        'uses_reusable_workflows':      len(reusable_workflows) > 0,
        'uses_external_actions':        len(external_actions) > 0,
        'local_actions_list':           list(local_actions),
        'reusable_workflows_list':      list(reusable_workflows),
        'external_actions_list':        list(external_actions),
    }


# ==========================================
# Metric Extraction
# ==========================================

def read_workflow_content(fp):
    try:
        with open(fp, encoding='utf-8', errors='replace') as f:
            return f.read()
    except Exception as e:
        logger.warning(f"Could not read workflow content from {fp}: {e}")
        return ""


def extract_metrics(wf, fp):
    try:
        lines = count_lines(fp)
        jobs  = wf.get('jobs', {})

        num_jobs  = sum(1 for job in jobs.values() if isinstance(job, dict))
        num_steps = sum(
            len(job.get('steps', []))
            for job in jobs.values()
            if isinstance(job, dict) and isinstance(job.get('steps', []), list)
        )

        max_nesting          = calculate_nesting_depth(wf)
        job_parallelism      = calculate_job_parallelism(wf)
        max_sequential_steps = calculate_max_sequential_steps(wf)
        vertical             = calculate_vertical_depth(wf)
        has_matrix, matrix_size = analyze_matrix(wf)
        num_conditionals     = count_conditionals(wf)
        num_dependencies     = count_job_dependencies(wf)
        has_dependencies     = num_dependencies > 0
        action_analysis      = analyze_action_usage(wf)

        avg_steps_per_job         = num_steps / num_jobs if num_jobs > 0 else 0
        dependency_ratio          = num_dependencies / num_jobs if num_jobs > 0 else 0
        external_action_diversity = (
            len(action_analysis['external_actions_list']) / num_steps
            if num_steps > 0 else 0
        )
        conditional_density = (
            num_conditionals / (num_jobs + num_steps)
            if (num_jobs + num_steps) > 0 else 0
        )

        return {
            "lines_of_yaml":                lines,
            "num_jobs":                     num_jobs,
            "num_steps":                    num_steps,
            "max_nesting_depth":            max_nesting,
            "job_parallelism":              job_parallelism,
            "max_sequential_steps":         max_sequential_steps,
            "vertical_depth":               vertical,
            "has_matrix":                   has_matrix,
            "matrix_size":                  matrix_size,
            "has_conditionals":             num_conditionals > 0,
            "num_conditionals":             num_conditionals,
            "has_job_dependencies":         has_dependencies,
            "num_job_dependencies":         num_dependencies,
            "uses_reusable_workflows":      action_analysis['uses_reusable_workflows'],
            "num_reusable_workflows":       action_analysis['num_reusable_workflows'],
            "uses_external_actions":        action_analysis['uses_external_actions'],
            "num_unique_external_actions":  action_analysis['num_unique_external_actions'],
            "uses_local_actions":           action_analysis['uses_local_actions'],
            "num_local_actions":            action_analysis['num_local_actions'],
            "num_marketplace_actions":      action_analysis['num_marketplace_actions'],
            "avg_steps_per_job":            round(avg_steps_per_job, 2),
            "dependency_ratio":             round(dependency_ratio, 3),
            "external_action_diversity":    round(external_action_diversity, 3),
            "conditional_density":          round(conditional_density, 3),
        }

    except Exception as e:
        logger.error(f"Error extracting metrics from {fp}: {e}")
        return None


# ==========================================
# Collection
# ==========================================

def collect_workflows(base_path, language):
    records, errors, skipped, content_records = [], [], [], []
    base_path = Path(base_path)
    logger.info(f"Scanning {base_path} for {language} workflows...")

    yaml_files = list(base_path.rglob("*.yml")) + list(base_path.rglob("*.yaml"))
    logger.info(f"Found {len(yaml_files)} YAML files")

    for fp in yaml_files:
        try:
            with open(fp, encoding="utf-8") as f:
                wf = yaml.safe_load(f)

            if not isinstance(wf, dict):
                skipped.append({"file": str(fp), "reason": "Not a dictionary"})
                continue
            if "jobs" not in wf:
                skipped.append({"file": str(fp), "reason": "Missing 'jobs' key"})
                continue

            metrics = extract_metrics(wf, fp)
            if metrics is None:
                skipped.append({"file": str(fp), "reason": "Metric extraction failed"})
                continue

            raw_content = read_workflow_content(fp)
            # Escape the content so it always occupies exactly ONE cell / ONE row.
            # Strategy:
            #   1. Normalise all line endings to \n
            #   2. Replace every real newline with the two-char literal \n
            #      → the entire YAML becomes a single line; no row bleed possible
            #   3. Replace every " with '' (two single-quotes)
            #      → no embedded double-quote can confuse the CSV cell boundary
            # Recovery: cell.replace('\\n', '\n').replace("''", '"')
            safe_content = raw_content.replace('\r\n', '\n').replace('\r', '\n')
            safe_content = safe_content.replace('\n', '\\n')   # literal backslash-n
            safe_content = safe_content.replace('"', "''")      # two single-quotes
            content_records.append({
                "full_path":        str(fp),
                "workflow_content": safe_content,
            })
            metrics.update({
                "language":      language,
                "workflow_file": fp.name,
                "repo_path":     str(fp.parent),
                "full_path":     str(fp),
            })
            records.append(metrics)

        except yaml.YAMLError as e:
            errors.append({"file": str(fp), "error": f"YAML error: {e}"})
        except Exception as e:
            errors.append({"file": str(fp), "error": str(e)})

    logger.info(f"Successfully processed {len(records)} {language} workflows")
    if errors:
        pd.DataFrame(errors).to_csv(RESULTS_DIR / f"parsing_errors_{language}.csv", index=False)
    if skipped:
        pd.DataFrame(skipped).to_csv(RESULTS_DIR / f"skipped_files_{language}.csv", index=False)

    return pd.DataFrame(records), pd.DataFrame(content_records)


# ==========================================
# CSV Save — strict validation
# ==========================================

def save_dataframe_to_csv_strict(df: pd.DataFrame, filepath, logger_obj=None):
    """
    Write df to CSV with column/row count validation after write.

    workflow_content is NOT present in the main metrics DataFrame — it lives
    in its own separate CSV.  This function strips bare newlines from every
    text column (belt-and-suspenders), then validates the file after writing.
    """
    log = logger_obj or logger

    if df.empty:
        raise ValueError("DataFrame is empty — cannot save.")

    df = df.copy()
    df.columns = [str(c) for c in df.columns]

    if df.columns.duplicated().any():
        dupes = df.columns[df.columns.duplicated()].tolist()
        raise ValueError(f"Duplicate columns: {dupes}")

    for col in df.columns:
        if df[col].dtype == object:
            # Strip bare newlines from all text columns so they cannot
            # bleed into the next CSV row.
            df[col] = df[col].apply(
                lambda x: x.replace('\r\n', ' ').replace('\r', ' ').replace('\n', ' ')
                if isinstance(x, str) else x
            )

    filepath = Path(filepath)
    df.to_csv(
        filepath,
        index=False,
        encoding='utf-8',
        quoting=csv.QUOTE_ALL,
        quotechar='"',
        lineterminator='\n',
        doublequote=True,
    )

    # Post-write validation
    df_check = pd.read_csv(filepath, encoding='utf-8')

    if len(df_check.columns) != len(df.columns):
        raise ValueError(
            f"Column count mismatch after write! "
            f"Expected {len(df.columns)}, got {len(df_check.columns)}.\n"
            f"Expected: {list(df.columns)}\nGot: {list(df_check.columns)}"
        )
    if len(df_check) != len(df):
        raise ValueError(
            f"Row count mismatch! Expected {len(df)}, got {len(df_check)}."
        )
    if not all(df_check.columns == df.columns):
        raise ValueError(
            f"Column name mismatch!\nExpected: {list(df.columns)}\nGot: {list(df_check.columns)}"
        )

    log.info(f"[OK] {filepath.name}  —  {len(df):,} rows x {len(df.columns)} columns (validated)")
    return True


# ==========================================
# Interpretation — value-threshold 70/80/90
# ==========================================

def compute_percentile_thresholds(series: pd.Series) -> dict:
    return {
        "p70": series.quantile(0.70),
        "p80": series.quantile(0.80),
        "p90": series.quantile(0.90),
    }


def _value_threshold_labels(series: pd.Series, p70, p80, p90) -> pd.Series:
    result = pd.Series("", index=series.index, dtype=str)
    result[series <= p70]                         = "low"
    result[(series > p70) & (series <= p80)]      = "moderate"
    result[(series > p80) & (series <= p90)]      = "high"
    result[series > p90]                          = "very high"
    return result


def add_interpretation_columns(df: pd.DataFrame):
    logger.info("Adding value-threshold interpretation columns...")
    all_metrics        = CORE_METRICS + DERIVED_METRICS
    interpretation_cols = {}
    thresholds_log      = {}

    for metric in all_metrics:
        if metric not in df.columns:
            continue
        series   = df[metric]
        non_null = series.dropna()
        if non_null.empty:
            continue

        thresholds = compute_percentile_thresholds(non_null)
        thresholds["n_unique"] = non_null.nunique()
        thresholds_log[metric] = thresholds

        p70, p80, p90 = thresholds["p70"], thresholds["p80"], thresholds["p90"]
        logger.info(
            f"  {metric:35s} | low <= {p70:.3f} | moderate ({p70:.3f},{p80:.3f}] "
            f"| high ({p80:.3f},{p90:.3f}] | very high > {p90:.3f}"
        )

        interp_col = f"{metric}_interpretation"
        labels = _value_threshold_labels(series, p70, p80, p90)
        labels[series.isna()] = ""
        df[interp_col] = labels
        interpretation_cols[metric] = interp_col

    logger.info(f"Interpretation columns added for {len(interpretation_cols)} metrics.")
    return df, interpretation_cols, thresholds_log


def save_thresholds_log(thresholds_log: dict, output_path: Path):
    rows = []
    for metric, t in thresholds_log.items():
        rows.append({
            "metric":            metric,
            "p70_cutpoint":      round(t["p70"], 4),
            "p80_cutpoint":      round(t["p80"], 4),
            "p90_cutpoint":      round(t["p90"], 4),
            "n_unique_values":   t.get("n_unique", "?"),
            "assignment_method": "value-threshold (identical values same band)",
            "band_low":          "value <= p70",
            "band_moderate":     "p70 < value <= p80",
            "band_high":         "p80 < value <= p90",
            "band_very_high":    "value > p90",
        })
    pd.DataFrame(rows).to_csv(output_path, index=False, encoding='utf-8')
    logger.info(f"[OK] Thresholds saved to {output_path}")


# ==========================================
# Descriptive Statistics
# ==========================================

def compute_comprehensive_descriptives(df):
    logger.info("Computing descriptive statistics...")
    all_metrics = CORE_METRICS + DERIVED_METRICS
    rows = []

    for scope, group in [("Overall", df)] + list(df.groupby("language")):
        for metric in all_metrics:
            if metric not in group.columns:
                continue
            s = group[metric]
            rows.append({
                "language": scope,
                "metric":   metric,
                "n":        len(group),
                "mean":     round(s.mean(),  2),
                "median":   round(s.median(), 2),
                "std":      round(s.std(),   2),
                "min":      round(s.min(),   2),
                "p70":      round(s.quantile(0.70), 2),
                "p80":      round(s.quantile(0.80), 2),
                "p90":      round(s.quantile(0.90), 2),
                "max":      round(s.max(),   2),
                "iqr":      round(s.quantile(0.75) - s.quantile(0.25), 2),
                "cv":       round(s.std() / s.mean(), 3) if s.mean() != 0 else 0,
            })

    return pd.DataFrame(rows)


def compute_binary_statistics(df):
    rows = []
    for scope, group in [("Overall", df)] + list(df.groupby("language")):
        for metric in BINARY_METRICS:
            if metric not in group.columns:
                continue
            count = group[metric].sum()
            total = len(group)
            rows.append({
                "language":   scope,
                "feature":    metric,
                "count":      count,
                "total":      total,
                "proportion": round(count / total, 3),
                "percentage": round((count / total) * 100, 1),
            })
    return pd.DataFrame(rows)


def compute_interpretation_distributions(df, interpretation_cols):
    rows = []
    for metric, interp_col in interpretation_cols.items():
        if interp_col not in df.columns:
            continue
        for scope, group in [("Overall", df)] + list(df.groupby("language")):
            dist = group[interp_col].value_counts()
            for category in INTERPRETATION_LABELS:
                count = dist.get(category, 0)
                rows.append({
                    "language":       scope,
                    "metric":         metric,
                    "interpretation": category,
                    "count":          count,
                    "percentage":     round((count / len(group)) * 100, 1),
                })
    return pd.DataFrame(rows)


# ==========================================
# Statistical Tests
# ==========================================

def cliffs_delta(x, y):
    """Vectorised Cliff's Delta with sampling guard for large arrays."""
    MAX_N = 5000
    rng   = np.random.default_rng(seed=42)
    x     = np.asarray(x, dtype=float)
    y     = np.asarray(y, dtype=float)
    if len(x) > MAX_N:
        x = rng.choice(x, size=MAX_N, replace=False)
    if len(y) > MAX_N:
        y = rng.choice(y, size=MAX_N, replace=False)
    diff  = np.subtract.outer(x, y)
    return float(np.sign(diff).sum() / diff.size)


def interpret_cliffs_delta(delta):
    a = abs(delta)
    if a < 0.147:  return "negligible"
    if a < 0.33:   return "small"
    if a < 0.474:  return "medium"
    return "large"


def run_statistical_tests(df):
    logger.info("Running statistical tests...")
    results     = []
    all_metrics = CORE_METRICS + DERIVED_METRICS
    languages   = sorted(df.language.unique())

    for metric in all_metrics:
        if metric not in df.columns:
            continue

        if len(languages) > 2:
            groups       = [df[df.language == lang][metric].values for lang in languages]
            H, p_overall = kruskal(*groups)
            results.append({
                "metric":         metric,
                "test":           "Kruskal-Wallis",
                "comparison":     "All languages",
                "statistic":      round(H, 3),
                "p_value":        p_overall,
                "p_formatted":    f"{p_overall:.4e}" if p_overall < 0.0001 else f"{p_overall:.4f}",
                "significant":    p_overall < 0.05,
                "effect_size":    "N/A",
                "interpretation": "Overall difference detected" if p_overall < 0.05 else "No overall difference",
            })

        for l1, l2 in combinations(languages, 2):
            g1    = df[df.language == l1][metric].values
            g2    = df[df.language == l2][metric].values
            U, p  = mannwhitneyu(g1, g2, alternative='two-sided')
            delta = cliffs_delta(g1, g2)
            interp = interpret_cliffs_delta(delta)
            results.append({
                "metric":         metric,
                "test":           "Mann-Whitney U",
                "comparison":     f"{l1} vs {l2}",
                "n1":             len(g1),
                "n2":             len(g2),
                "median1":        round(np.median(g1), 2),
                "median2":        round(np.median(g2), 2),
                "median_diff":    round(np.median(g2) - np.median(g1), 2),
                "statistic":      round(U, 2),
                "p_value":        p,
                "p_formatted":    f"{p:.4e}" if p < 0.0001 else f"{p:.4f}",
                "significant":    p < 0.05,
                "cliffs_delta":   round(delta, 3),
                "effect_size":    interp,
                "interpretation": (
                    f"{l2} {'higher' if delta > 0 else 'lower'} than {l1} ({interp} effect)"
                    if p < 0.05 else "No significant difference"
                ),
            })

    return pd.DataFrame(results)


# ==========================================
# Visualizations
# ==========================================

INTERP_COLORS = {
    "low":       "#4CAF50",
    "moderate":  "#2196F3",
    "high":      "#FF9800",
    "very high": "#F44336",
}

METRIC_LABELS = {
    "lines_of_yaml":               "Lines of YAML",
    "num_jobs":                    "Number of Jobs",
    "num_steps":                   "Number of Steps",
    "max_nesting_depth":           "Max Nesting Depth",
    "job_parallelism":             "Job Parallelism",
    "max_sequential_steps":        "Max Sequential Steps",
    "vertical_depth":              "Vertical Depth",
    "matrix_size":                 "Matrix Size",
    "num_conditionals":            "Number of Conditionals",
    "num_job_dependencies":        "Job Dependencies",
    "num_reusable_workflows":      "Reusable Workflows",
    "num_unique_external_actions": "Unique External Actions",
    "num_local_actions":           "Local Actions",
    "num_marketplace_actions":     "Marketplace Actions",
    "avg_steps_per_job":           "Avg Steps per Job",
    "dependency_ratio":            "Dependency Ratio",
    "external_action_diversity":   "External Action Diversity",
    "conditional_density":         "Conditional Density",
    "has_matrix":                  "Has Matrix",
    "has_conditionals":            "Has Conditionals",
    "uses_reusable_workflows":     "Uses Reusable Workflows",
    "uses_external_actions":       "Uses External Actions",
    "uses_local_actions":          "Uses Local Actions",
    "has_job_dependencies":        "Has Job Dependencies",
}


def _mlabel(metric: str) -> str:
    return METRIC_LABELS.get(metric, metric.replace("_", " ").title())


LOG_SCALE_METRICS = {
    "lines_of_yaml", "num_jobs", "num_steps", "job_parallelism",
    "max_sequential_steps", "vertical_depth", "matrix_size",
    "num_conditionals", "num_job_dependencies", "num_reusable_workflows",
    "num_unique_external_actions", "num_local_actions",
    "num_marketplace_actions", "avg_steps_per_job", "dependency_ratio",
}

FS_TITLE    = 14
FS_SUPTITLE = 16
FS_AXIS     = 12
FS_TICK     = 11
FS_ANNOT    = 10
FS_LEGEND   = 11


def _save_fig(fig, combined_path: Path, individual_name: str):
    individual_path = RESULTS_DIR / "figures" / "individual" / individual_name

    def _try_save(fig, path):
        try:
            fig.savefig(path, bbox_inches='tight', format='pdf')
            return path
        except PermissionError:
            stamp    = datetime.now().strftime("%Y%m%d_%H%M%S")
            fallback = path.with_stem(path.stem + f"_{stamp}")
            logger.warning(f"PermissionError on '{path.name}' — saving to {fallback.name}")
            fig.savefig(fallback, bbox_inches='tight', format='pdf')
            return fallback

    saved_c = _try_save(fig, combined_path)
    saved_i = _try_save(fig, individual_path)
    logger.info(f"[OK] {saved_c.name}  +  individual/{saved_i.name}")


def _apply_log_scale(ax, metric: str, orient: str = 'y'):
    import matplotlib.ticker as ticker
    if metric not in LOG_SCALE_METRICS:
        return

    def _fmt(v, _):
        if v >= 1000: return f'{int(v):,}'
        if v >= 1:    return str(int(v))
        if v >= 0.1:  return f'{v:.1f}'
        return f'{v:.2f}'

    if orient == 'y':
        ax.set_yscale('log')
        ax.set_ylim(bottom=0.01)
        ax.yaxis.set_major_locator(ticker.LogLocator(base=10, numticks=8))
        ax.yaxis.set_minor_locator(ticker.LogLocator(base=10, subs=tuple(i/10 for i in range(2,10)), numticks=50))
        ax.yaxis.set_major_formatter(ticker.FuncFormatter(_fmt))
        ax.yaxis.set_minor_formatter(ticker.NullFormatter())
        ax.grid(which='minor', axis='y', linestyle=':', linewidth=0.4, alpha=0.4)
        ax.grid(which='major', axis='y', linestyle='-',  linewidth=0.6, alpha=0.5)
        ax.set_ylabel(f"{_mlabel(metric)}\n(log scale)", fontsize=FS_AXIS)
    else:
        ax.set_xscale('log')
        ax.set_xlim(left=0.01)
        ax.xaxis.set_major_locator(ticker.LogLocator(base=10, numticks=8))
        ax.xaxis.set_minor_locator(ticker.LogLocator(base=10, subs=tuple(i/10 for i in range(2,10)), numticks=50))
        ax.xaxis.set_major_formatter(ticker.FuncFormatter(_fmt))
        ax.xaxis.set_minor_formatter(ticker.NullFormatter())
        ax.grid(which='minor', axis='x', linestyle=':', linewidth=0.4, alpha=0.4)
        ax.grid(which='major', axis='x', linestyle='-',  linewidth=0.6, alpha=0.5)
        ax.set_xlabel(f"{_mlabel(metric)} (log scale)", fontsize=FS_AXIS)


def _draw_median_lines(ax, df, metric, orient: str = 'y'):
    palette = sns.color_palette("Set2")
    langs   = sorted(df['language'].unique())
    col_map = {lang: palette[i] for i, lang in enumerate(langs)}

    for i, lang in enumerate(langs):
        vals = df[df['language'] == lang][metric].dropna()
        if vals.empty:
            continue
        med    = vals.median()
        half_w = 0.38
        if orient == 'y':
            ax.hlines(med, i - half_w, i + half_w,
                      colors=col_map[lang], linewidths=3.0, linestyles='solid', zorder=5)
        else:
            ax.vlines(med, i - half_w, i + half_w,
                      colors=col_map[lang], linewidths=3.0, linestyles='solid', zorder=5)


def generate_comprehensive_visualizations(df):
    logger.info("Generating visualizations...")
    indiv = RESULTS_DIR / "figures" / "individual"

    # ------------------------------------------------------------------
    # 1. Core metrics (2x4 boxplots)
    # ------------------------------------------------------------------
    core_viz = CORE_METRICS[:8]
    fig, axes = plt.subplots(2, 4, figsize=(24, 10))
    for ax, metric in zip(axes.flat, core_viz):
        if metric not in df.columns:
            continue
        sns.boxplot(data=df, x="language", y=metric, order=LANG_ORDER,
                    ax=ax, palette="Set2")
        _apply_log_scale(ax, metric)
        _draw_median_lines(ax, df, metric)
        ax.set_title(_mlabel(metric), fontsize=FS_TITLE, fontweight='bold')
        ax.set_xlabel("Language", fontsize=FS_AXIS)
        if metric not in LOG_SCALE_METRICS:
            ax.set_ylabel(_mlabel(metric), fontsize=FS_AXIS)
        ax.tick_params(axis='both', labelsize=FS_TICK)
        medians = df.groupby('language')[metric].median()
        ylim = ax.get_ylim()
        for i, (lang, med) in enumerate(medians.items()):
            ax.text(i, ylim[1] * 0.97, f'M={med:.1f}',
                    ha='center', va='top', fontsize=FS_ANNOT, fontweight='bold')
    plt.suptitle("Core Workflow Complexity Metrics by Language",
                 fontsize=FS_SUPTITLE, fontweight='bold', y=1.00)
    plt.tight_layout(pad=0.5, h_pad=0.4, w_pad=0.4)
    _save_fig(fig, RESULTS_DIR / "figures" / "core_metrics_comparison.pdf",
              "core_metrics_comparison.pdf")
    plt.close()

    for metric in core_viz:
        if metric not in df.columns:
            continue
        fig_i, ax_i = plt.subplots(figsize=(7, 5))
        sns.boxplot(data=df, x="language", y=metric, order=LANG_ORDER,
                    ax=ax_i, palette="Set2")
        _apply_log_scale(ax_i, metric)
        _draw_median_lines(ax_i, df, metric)
        ax_i.set_title(_mlabel(metric), fontsize=FS_TITLE, fontweight='bold')
        ax_i.set_xlabel("Language", fontsize=FS_AXIS)
        if metric not in LOG_SCALE_METRICS:
            ax_i.set_ylabel(_mlabel(metric), fontsize=FS_AXIS)
        ax_i.tick_params(axis='both', labelsize=FS_TICK)
        medians = df.groupby('language')[metric].median()
        ylim = ax_i.get_ylim()
        for i, (lang, med) in enumerate(medians.items()):
            ax_i.text(i, ylim[1] * 0.97, f'M={med:.1f}',
                      ha='center', va='top', fontsize=FS_ANNOT, fontweight='bold')
        plt.tight_layout(pad=0.5)
        fig_i.savefig(indiv / f"core_{metric}.pdf", format='pdf', bbox_inches='tight')
        plt.close(fig_i)
    logger.info("[OK] Core metrics figures saved")

    # ------------------------------------------------------------------
    # 2. Depth analysis (violins)
    # ------------------------------------------------------------------
    depth_metrics = ['max_nesting_depth', 'job_parallelism',
                     'max_sequential_steps', 'vertical_depth']
    fig, axes = plt.subplots(1, 4, figsize=(22, 5))
    for ax, metric in zip(axes, depth_metrics):
        if metric not in df.columns:
            continue
        sns.violinplot(data=df, x="language", y=metric, order=LANG_ORDER,
                       inner="quartile", ax=ax, palette="Set2")
        _apply_log_scale(ax, metric)
        _draw_median_lines(ax, df, metric)
        ax.set_title(_mlabel(metric), fontsize=FS_TITLE, fontweight='bold')
        ax.set_xlabel("Language", fontsize=FS_AXIS)
        if metric not in LOG_SCALE_METRICS:
            ax.set_ylabel(_mlabel(metric), fontsize=FS_AXIS)
        ax.tick_params(axis='both', labelsize=FS_TICK)
    plt.suptitle("Workflow Structural Depth Analysis",
                 fontsize=FS_SUPTITLE, fontweight='bold')
    plt.tight_layout(pad=0.5, h_pad=0.4, w_pad=0.4)
    _save_fig(fig, RESULTS_DIR / "figures" / "depth_analysis.pdf", "depth_analysis.pdf")
    plt.close()

    for metric in depth_metrics:
        if metric not in df.columns:
            continue
        fig_i, ax_i = plt.subplots(figsize=(7, 5))
        sns.violinplot(data=df, x="language", y=metric, order=LANG_ORDER,
                       inner="quartile", ax=ax_i, palette="Set2")
        _apply_log_scale(ax_i, metric)
        _draw_median_lines(ax_i, df, metric)
        ax_i.set_title(_mlabel(metric), fontsize=FS_TITLE, fontweight='bold')
        ax_i.set_xlabel("Language", fontsize=FS_AXIS)
        if metric not in LOG_SCALE_METRICS:
            ax_i.set_ylabel(_mlabel(metric), fontsize=FS_AXIS)
        ax_i.tick_params(axis='both', labelsize=FS_TICK)
        plt.tight_layout(pad=0.5)
        fig_i.savefig(indiv / f"depth_{metric}.pdf", format='pdf', bbox_inches='tight')
        plt.close(fig_i)
    logger.info("[OK] Depth analysis figures saved")

    # ------------------------------------------------------------------
    # 3. Derived metrics (boxplots)
    # ------------------------------------------------------------------
    fig, axes = plt.subplots(1, 4, figsize=(24, 5))
    for ax, metric in zip(axes.flat, DERIVED_METRICS):
        if metric not in df.columns:
            continue
        sns.boxplot(data=df, x="language", y=metric, order=LANG_ORDER,
                    ax=ax, palette="Set2")
        _apply_log_scale(ax, metric)
        _draw_median_lines(ax, df, metric)
        ax.set_title(_mlabel(metric), fontsize=FS_TITLE, fontweight='bold')
        ax.set_xlabel("Language", fontsize=FS_AXIS)
        if metric not in LOG_SCALE_METRICS:
            ax.set_ylabel(_mlabel(metric), fontsize=FS_AXIS)
        ax.tick_params(axis='both', labelsize=FS_TICK)
        medians = df.groupby('language')[metric].median()
        ylim = ax.get_ylim()
        for i, (lang, med) in enumerate(medians.items()):
            ax.text(i, ylim[1] * 0.97, f'M={med:.3f}',
                    ha='center', va='top', fontsize=FS_ANNOT, fontweight='bold')
    plt.suptitle("Derived Complexity Metrics", fontsize=FS_SUPTITLE, fontweight='bold')
    plt.tight_layout(pad=0.5, h_pad=0.4, w_pad=0.4)
    _save_fig(fig, RESULTS_DIR / "figures" / "derived_metrics.pdf", "derived_metrics.pdf")
    plt.close()

    for metric in DERIVED_METRICS:
        if metric not in df.columns:
            continue
        fig_i, ax_i = plt.subplots(figsize=(7, 5))
        sns.boxplot(data=df, x="language", y=metric, order=LANG_ORDER,
                    ax=ax_i, palette="Set2")
        _apply_log_scale(ax_i, metric)
        _draw_median_lines(ax_i, df, metric)
        ax_i.set_title(_mlabel(metric), fontsize=FS_TITLE, fontweight='bold')
        ax_i.set_xlabel("Language", fontsize=FS_AXIS)
        if metric not in LOG_SCALE_METRICS:
            ax_i.set_ylabel(_mlabel(metric), fontsize=FS_AXIS)
        ax_i.tick_params(axis='both', labelsize=FS_TICK)
        medians = df.groupby('language')[metric].median()
        ylim = ax_i.get_ylim()
        for i, (lang, med) in enumerate(medians.items()):
            ax_i.text(i, ylim[1] * 0.97, f'M={med:.3f}',
                      ha='center', va='top', fontsize=FS_ANNOT, fontweight='bold')
        plt.tight_layout(pad=0.5)
        fig_i.savefig(indiv / f"derived_{metric}.pdf", format='pdf', bbox_inches='tight')
        plt.close(fig_i)
    logger.info("[OK] Derived metrics figures saved")

    # ------------------------------------------------------------------
    # 4. Feature adoption heatmap
    # ------------------------------------------------------------------
    fig, ax = plt.subplots(figsize=(11, 7))
    feature_usage = df.groupby("language")[BINARY_METRICS].mean() * 100
    feature_usage.columns = [_mlabel(m) for m in feature_usage.columns]
    sns.heatmap(feature_usage.T, annot=True, fmt=".1f", cmap="YlOrRd",
                cbar_kws={'label': 'Adoption Rate (%)'},
                vmin=0, vmax=100, ax=ax, annot_kws={"size": FS_TICK})
    ax.set_title("Feature Adoption by Language (%)",
                 fontsize=FS_SUPTITLE, fontweight='bold')
    ax.set_xlabel("Language", fontsize=FS_AXIS)
    ax.set_ylabel("Feature",  fontsize=FS_AXIS)
    ax.tick_params(axis='both', labelsize=FS_TICK)
    cbar = ax.collections[0].colorbar
    cbar.ax.tick_params(labelsize=FS_TICK)
    cbar.set_label('Adoption Rate (%)', fontsize=FS_AXIS)
    plt.tight_layout(pad=0.5)
    _save_fig(fig, RESULTS_DIR / "figures" / "feature_adoption.pdf", "feature_adoption.pdf")
    plt.close()

    for metric in BINARY_METRICS:
        if metric not in df.columns:
            continue
        fig_i, ax_i = plt.subplots(figsize=(7, 5))
        feat_pct = df.groupby("language")[metric].mean() * 100
        feat_pct.plot(kind='bar', ax=ax_i,
                      color=sns.color_palette("Set2", len(feat_pct)),
                      edgecolor='black')
        ax_i.set_title(_mlabel(metric), fontsize=FS_TITLE, fontweight='bold')
        ax_i.set_xlabel("Language", fontsize=FS_AXIS)
        ax_i.set_ylabel("Adoption Rate (%)", fontsize=FS_AXIS)
        ax_i.set_ylim(0, 100)
        ax_i.tick_params(axis='both', labelsize=FS_TICK)
        ax_i.set_xticklabels(ax_i.get_xticklabels(), rotation=30, ha='right')
        for bar in ax_i.patches:
            ax_i.text(bar.get_x() + bar.get_width() / 2,
                      bar.get_height() + 1, f'{bar.get_height():.1f}%',
                      ha='center', va='bottom', fontsize=FS_ANNOT)
        plt.tight_layout(pad=0.5)
        fig_i.savefig(indiv / f"adoption_{metric}.pdf", format='pdf', bbox_inches='tight')
        plt.close(fig_i)
    logger.info("[OK] Feature adoption figures saved")

    # ------------------------------------------------------------------
    # 5. Action analysis
    # ------------------------------------------------------------------
    action_metrics = ['num_unique_external_actions', 'num_marketplace_actions',
                      'num_local_actions', 'num_reusable_workflows']
    fig, axes = plt.subplots(1, 2, figsize=(16, 6))

    action_data = [df.groupby('language')[m].median()
                   for m in action_metrics if m in df.columns]
    if action_data:
        action_df = pd.DataFrame(
            action_data,
            index=[_mlabel(m) for m in action_metrics if m in df.columns],
        )
        sns.heatmap(action_df, annot=True, fmt='.1f', cmap='Blues', ax=axes[0],
                    cbar_kws={'label': 'Median Count'}, annot_kws={"size": FS_TICK})
        axes[0].set_title("Action Usage (Median Counts)", fontsize=FS_TITLE, fontweight='bold')
        axes[0].set_xlabel("Language", fontsize=FS_AXIS)
        axes[0].set_ylabel("Action Type", fontsize=FS_AXIS)
        axes[0].tick_params(axis='both', labelsize=FS_TICK)
        axes[0].collections[0].colorbar.ax.tick_params(labelsize=FS_TICK)

    if 'external_action_diversity' in df.columns:
        sns.boxplot(data=df, x='language', y='external_action_diversity', order=LANG_ORDER,
                    ax=axes[1], palette='Set2')
        _draw_median_lines(axes[1], df, 'external_action_diversity')
        axes[1].set_title("External Action Diversity", fontsize=FS_TITLE, fontweight='bold')
        axes[1].set_xlabel("Language", fontsize=FS_AXIS)
        axes[1].set_ylabel("Unique Actions / Total Steps", fontsize=FS_AXIS)
        axes[1].tick_params(axis='both', labelsize=FS_TICK)

    plt.suptitle("Action Ecosystem Composition", fontsize=FS_SUPTITLE, fontweight='bold')
    plt.tight_layout(pad=0.5, h_pad=0.4, w_pad=0.4)
    _save_fig(fig, RESULTS_DIR / "figures" / "action_analysis.pdf", "action_analysis.pdf")
    plt.close()
    logger.info("[OK] Action analysis figures saved")

    # ------------------------------------------------------------------
    # 6. Distribution plots (KDE on log1p scale, P70/P80/P90 lines)
    # ------------------------------------------------------------------
    key_metrics = ['lines_of_yaml', 'num_jobs', 'matrix_size', 'vertical_depth']
    lang_colors = {'Python': '#66c2a5', 'Java': '#fc8d62', 'C++': '#8da0cb'}
    lang_order  = ['Python', 'Java', 'C++']
    pct_styles  = {
        'P70': dict(color='#e41a1c', lw=1.2, ls='--',  label='P70 (low | mod.)'),
        'P80': dict(color='#ff7f00', lw=1.2, ls=':',   label='P80 (mod. | high)'),
        'P90': dict(color='#984ea3', lw=1.2, ls='-.',  label='P90 (high | v.high)'),
    }

    def _make_dist_ax(ax, metric, df_plot):
        from scipy.stats import gaussian_kde
        col_data     = df_plot[metric].dropna()
        log_data_all = np.log1p(col_data.values)
        x_min  = max(log_data_all.min() - 0.1, 0)
        x_max  = log_data_all.max() + 0.3
        x_grid = np.linspace(x_min, x_max, 400)

        for lang in lang_order:
            vals = df_plot[df_plot['language'] == lang][metric].dropna().values
            if len(vals) < 10:
                continue
            log_vals = np.log1p(vals)
            try:
                kde = gaussian_kde(log_vals, bw_method='scott')
                ax.plot(x_grid, kde(x_grid), color=lang_colors.get(lang), lw=2.0, label=lang)
                ax.fill_between(x_grid, kde(x_grid), color=lang_colors.get(lang), alpha=0.12)
            except Exception:
                pass

        for pct_label, q in [('P70', 0.70), ('P80', 0.80), ('P90', 0.90)]:
            pct_val = col_data.quantile(q)
            ax.axvline(np.log1p(pct_val), **pct_styles[pct_label])

        tick_log    = np.linspace(x_min, x_max, 6)
        tick_orig   = np.expm1(tick_log)
        tick_labels = [str(int(round(v))) if v >= 1 else f'{v:.1f}' for v in tick_orig]
        ax.set_xticks(tick_log)
        ax.set_xticklabels(tick_labels, fontsize=8)
        ax.set_title(metric.replace('_', ' ').title(), fontsize=11, fontweight='bold')
        ax.set_xlabel('Value (log scale, ticks show original units)', fontsize=8)
        ax.set_ylabel('Density', fontsize=9)
        ax.grid(alpha=0.25)
        ax.set_xlim(x_min, x_max)
        ax.set_ylim(bottom=0)

    fig, axes = plt.subplots(2, 2, figsize=(14, 10))
    for ax, metric in zip(axes.flat, key_metrics):
        if metric in df.columns:
            _make_dist_ax(ax, metric, df)
    handles, labels = axes.flat[0].get_legend_handles_labels()
    fig.legend(handles, labels, loc='lower center', ncol=6, fontsize=9,
               title='Language  /  Complexity threshold', bbox_to_anchor=(0.5, -0.01))
    plt.suptitle(
        'Distributions of Key Complexity Metrics by Language\n'
        '(KDE on log scale; dashed lines mark P70/P80/P90 thresholds)',
        fontsize=13, fontweight='bold'
    )
    plt.tight_layout(rect=[0, 0.06, 1, 1], pad=0.5, h_pad=0.4, w_pad=0.4)
    _save_fig(fig, RESULTS_DIR / "figures" / "metric_distributions.pdf",
              "metric_distributions.pdf")
    plt.close()

    for metric in key_metrics:
        if metric not in df.columns:
            continue
        fig_i, ax_i = plt.subplots(figsize=(7, 4))
        _make_dist_ax(ax_i, metric, df)
        handles, labels = ax_i.get_legend_handles_labels()
        ax_i.legend(handles, labels, fontsize=8, loc='upper right',
                    title='Language / threshold', framealpha=0.85)
        plt.tight_layout(pad=0.5)
        fig_i.savefig(indiv / f"dist_{metric}.pdf", format='pdf', bbox_inches='tight')
        plt.close(fig_i)
    logger.info("[OK] Distribution figures saved")

    # ------------------------------------------------------------------
    # 7. Interpretation band distributions (stacked bars)
    # ------------------------------------------------------------------
    all_metrics = CORE_METRICS + DERIVED_METRICS
    interp_cols = [f"{m}_interpretation" for m in all_metrics
                   if f"{m}_interpretation" in df.columns]

    if interp_cols:
        n_metrics = len(interp_cols)
        n_cols    = 4
        n_rows    = (n_metrics + n_cols - 1) // n_cols
        fig, axes = plt.subplots(n_rows, n_cols, figsize=(20, 5 * n_rows))
        axes_flat = axes.flat

        for ax, interp_col in zip(axes_flat, interp_cols):
            metric = interp_col.replace("_interpretation", "")
            pivot  = (
                df.groupby(["language", interp_col])
                  .size()
                  .unstack(fill_value=0)
                  .reindex(columns=INTERPRETATION_LABELS, fill_value=0)
            )
            pivot_pct = pivot.div(pivot.sum(axis=1), axis=0) * 100
            pivot_pct.plot(kind="bar", stacked=True, ax=ax,
                           color=[INTERP_COLORS[c] for c in INTERPRETATION_LABELS],
                           legend=False)
            ax.set_title(_mlabel(metric), fontsize=FS_TITLE, fontweight='bold')
            ax.set_xlabel("")
            ax.set_ylabel("% of workflows")
            ax.set_xticklabels(ax.get_xticklabels(), rotation=30, ha='right')
            ax.set_ylim(0, 100)

        for ax in list(axes_flat)[len(interp_cols):]:
            ax.set_visible(False)

        from matplotlib.patches import Patch
        legend_elements = [Patch(facecolor=INTERP_COLORS[lbl], label=lbl.capitalize())
                           for lbl in INTERPRETATION_LABELS]
        fig.legend(handles=legend_elements, loc='lower center', ncol=4,
                   fontsize=FS_LEGEND, title="Interpretation Band",
                   bbox_to_anchor=(0.5, 0.0))
        plt.suptitle("Interpretation Band Distribution by Language and Metric",
                     fontsize=14, fontweight='bold')
        plt.tight_layout(rect=[0, 0.04, 1, 1], pad=0.5, h_pad=0.4, w_pad=0.4)
        _save_fig(fig, RESULTS_DIR / "figures" / "interpretation_distributions.pdf",
                  "interpretation_distributions.pdf")
        plt.close()
        logger.info("[OK] Interpretation distribution figures saved")


# ==========================================
# Summary reports
# ==========================================

def generate_comprehensive_summary(df, stats_df, binary_stats, test_results, interpretation_dist):
    report_path = RESULTS_DIR / "COMPREHENSIVE_SUMMARY.txt"
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write("=" * 100 + "\n")
        f.write("RQ1: COMPREHENSIVE GITHUB ACTIONS WORKFLOW COMPLEXITY ANALYSIS\n")
        f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write("=" * 100 + "\n\n")
        f.write("workflow_content: stored separately in workflow_content.csv\n")
        f.write("  Join on: full_path\n\n")
        f.write("INTERPRETATION: value-threshold 70/80/90 pct bands\n")
        f.write("  low <= P70 | moderate P70-P80 | high P80-P90 | very high > P90\n\n")
        f.write(f"Total workflows: {len(df):,}\n")
        for lang, count in df['language'].value_counts().sort_index().items():
            f.write(f"  {lang:8s}: {count:5,} ({(count/len(df))*100:.1f}%)\n")
    logger.info(f"[OK] Summary saved to {report_path}")


def generate_per_language_summaries(df, stats_df, interpretation_dist):
    for lang in sorted(df['language'].unique()):
        path   = RESULTS_DIR / "interpretations" / f"{lang}_detailed_summary.txt"
        lang_df = df[df['language'] == lang]
        with open(path, 'w', encoding='utf-8') as f:
            f.write("=" * 100 + "\n")
            f.write(f"{lang.upper()} WORKFLOW COMPLEXITY ANALYSIS\n")
            f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write("=" * 100 + "\n\n")
            f.write(f"Total workflows: {len(lang_df):,}\n")
        logger.info(f"[OK] {lang} summary saved")


# ==========================================
# Main
# ==========================================

def main():
    logger.info("=" * 100)
    logger.info("RQ1 - GHA Workflow Complexity Analysis  (workflow_content: separate file)")
    logger.info("=" * 100)

    all_data, all_content = [], []
    for language, lang_path in WORKFLOW_LANG_DIRS.items():
        lang_path = Path(lang_path)
        if not lang_path.exists():
            logger.error(
                f"{language} workflows not found at {lang_path}. "
                "Run scripts/extract_workflows.py first."
            )
            continue
        df_chunk, content_chunk = collect_workflows(lang_path, language)
        if not df_chunk.empty:
            all_data.append(df_chunk)
            all_content.append(content_chunk)
            logger.info(f"[OK] {language}: {len(df_chunk):,} workflows")
        else:
            logger.warning(f"No workflows found for {language}")

    if not all_data:
        logger.error("No data collected -- exiting.")
        return

    df = pd.concat(all_data, ignore_index=True)
    logger.info(f"Total: {len(df):,} workflows -- {df['language'].value_counts().to_dict()}")

    # Save workflow content to its own separate 2-column CSV.
    # workflow_content is escaped (newlines → \n literal, " → '') so every
    # workflow occupies exactly ONE row and ONE cell — no column bleed possible.
    # Recovery: cell.replace('\\n', '\n').replace("''", '"')
    if all_content:
        content_df   = pd.concat(all_content, ignore_index=True)
        content_path = RESULTS_DIR / "workflow_content.csv"
        logger.info(f"Saving workflow content to separate file: {content_path.name}")

        # Verify no real newlines remain before writing
        bad = content_df['workflow_content'].astype(str).str.contains(r'[\r\n]', regex=True, na=False)
        if bad.any():
            logger.warning(f"{bad.sum()} content cells still contain newlines — force-stripping.")
            content_df.loc[bad, 'workflow_content'] = (
                content_df.loc[bad, 'workflow_content']
                .str.replace('\r\n', '\\n', regex=False)
                .str.replace('\r',   '\\n', regex=False)
                .str.replace('\n',   '\\n', regex=False)
            )

        content_df.to_csv(
            content_path,
            index=False,
            encoding='utf-8',
            quoting=csv.QUOTE_ALL,
            quotechar='"',
            lineterminator='\n',
            doublequote=True,
        )

        # Post-write validation: row and column count must match exactly
        check = pd.read_csv(content_path, encoding='utf-8')
        if len(check) != len(content_df) or len(check.columns) != 2:
            logger.error(
                f"workflow_content.csv validation FAILED: "
                f"expected {len(content_df)} rows x 2 cols, "
                f"got {len(check)} rows x {len(check.columns)} cols"
            )
        else:
            logger.info(f"[OK] workflow_content.csv  — {len(content_df):,} rows x 2 columns (validated)")

    df, interpretation_cols, thresholds_log = add_interpretation_columns(df)
    save_thresholds_log(thresholds_log, RESULTS_DIR / "stats" / "percentile_thresholds.csv")

    # Column ordering -- workflow_content always last
    fixed_order = [
        'language', 'workflow_file', 'repo_path', 'full_path',
        'lines_of_yaml',            'lines_of_yaml_interpretation',
        'num_jobs',                 'num_jobs_interpretation',
        'num_steps',                'num_steps_interpretation',
        'max_nesting_depth',        'max_nesting_depth_interpretation',
        'job_parallelism',          'job_parallelism_interpretation',
        'max_sequential_steps',     'max_sequential_steps_interpretation',
        'vertical_depth',           'vertical_depth_interpretation',
        'has_matrix',  'matrix_size', 'matrix_size_interpretation',
        'has_conditionals', 'num_conditionals', 'num_conditionals_interpretation',
        'has_job_dependencies', 'num_job_dependencies', 'num_job_dependencies_interpretation',
        'uses_reusable_workflows', 'num_reusable_workflows', 'num_reusable_workflows_interpretation',
        'uses_external_actions', 'num_unique_external_actions', 'num_unique_external_actions_interpretation',
        'uses_local_actions', 'num_local_actions', 'num_local_actions_interpretation',
        'num_marketplace_actions', 'num_marketplace_actions_interpretation',
        'avg_steps_per_job',         'avg_steps_per_job_interpretation',
        'dependency_ratio',          'dependency_ratio_interpretation',
        'external_action_diversity', 'external_action_diversity_interpretation',
        'conditional_density',       'conditional_density_interpretation',
    ]
    ordered  = [c for c in fixed_order if c in df.columns]
    leftover = [c for c in df.columns  if c not in ordered]
    df = df[ordered + leftover]

    # Save main dataset (NO workflow_content column — lives in separate file)
    output_path = RESULTS_DIR / "workflow_metrics_with_interpretations.csv"
    logger.info("Saving main metrics dataset (workflow_content excluded)...")
    try:
        save_dataframe_to_csv_strict(df, output_path, logger)
    except Exception as e:
        logger.error(f"Save failed: {e}")
        raise

    # Statistics
    stats_df            = compute_comprehensive_descriptives(df)
    binary_stats        = compute_binary_statistics(df)
    interpretation_dist = compute_interpretation_distributions(df, interpretation_cols)
    test_results        = run_statistical_tests(df)

    save_dataframe_to_csv_strict(
        stats_df, RESULTS_DIR / "tables" / "comprehensive_descriptive_statistics.csv", logger)
    save_dataframe_to_csv_strict(
        binary_stats, RESULTS_DIR / "tables" / "binary_feature_statistics.csv", logger)
    save_dataframe_to_csv_strict(
        interpretation_dist, RESULTS_DIR / "tables" / "interpretation_distributions.csv", logger)
    save_dataframe_to_csv_strict(
        test_results, RESULTS_DIR / "stats" / "statistical_tests.csv", logger)
    logger.info("[OK] All tables saved")

    generate_comprehensive_visualizations(df)
    generate_comprehensive_summary(df, stats_df, binary_stats, test_results, interpretation_dist)
    generate_per_language_summaries(df, stats_df, interpretation_dist)

    logger.info("=" * 100)
    logger.info("RQ1 Analysis Complete!")
    logger.info(f"Results: {RESULTS_DIR.absolute()}")
    logger.info("=" * 100)

    print(f"\nTotal: {len(df):,} workflows")
    print("\nMedian values by language:")
    key  = ['lines_of_yaml', 'num_jobs', 'max_nesting_depth', 'vertical_depth', 'matrix_size']
    rows = []
    for lang in sorted(df['language'].unique()):
        row = {'Language': lang}
        for m in key:
            if m in df.columns:
                row[m] = df[df['language'] == lang][m].median()
        rows.append(row)
    print(pd.DataFrame(rows).to_string(index=False))


if __name__ == "__main__":
    main()