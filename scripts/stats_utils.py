"""Shared statistical helpers for RQ1-style cross-language comparisons."""

from __future__ import annotations

from itertools import combinations

import numpy as np
import pandas as pd
from scipy.stats import chi2_contingency, fisher_exact, kruskal, mannwhitneyu


def cliffs_delta(x, y) -> float:
    """Cliff's delta between two samples."""
    x = np.asarray(x, dtype=float)
    y = np.asarray(y, dtype=float)
    if len(x) == 0 or len(y) == 0:
        return float("nan")
    diff = np.subtract.outer(x, y)
    return float(np.sign(diff).sum() / diff.size)


def interpret_cliffs_delta(delta: float) -> str:
    magnitude = abs(delta)
    if magnitude < 0.147:
        return "negligible"
    if magnitude < 0.33:
        return "small"
    if magnitude < 0.474:
        return "medium"
    return "large"


def cohens_h(p1: float, p2: float) -> float:
    """Cohen's h for two proportions."""
    return 2.0 * (np.arcsin(np.sqrt(p1)) - np.arcsin(np.sqrt(p2)))


def interpret_cohens_h(h: float) -> str:
    magnitude = abs(h)
    if magnitude < 0.2:
        return "negligible"
    if magnitude < 0.5:
        return "small"
    if magnitude < 0.8:
        return "medium"
    return "large"


def format_p_value(p: float) -> str:
    if p < 0.0001:
        return f"{p:.4e}"
    return f"{p:.4f}"


def run_continuous_tests(
    df: pd.DataFrame,
    metrics: list[str],
    language_col: str = "language",
) -> pd.DataFrame:
    """Kruskal-Wallis omnibus and pairwise Mann-Whitney U with Cliff's delta."""
    rows = []
    languages = sorted(df[language_col].dropna().unique())

    for metric in metrics:
        if metric not in df.columns:
            continue
        series = pd.to_numeric(df[metric], errors="coerce")
        work = df.assign(_metric=series).dropna(subset=["_metric"])
        if work.empty:
            continue

        if len(languages) > 2:
            groups = [work.loc[work[language_col] == lang, "_metric"].values for lang in languages]
            H, p_overall = kruskal(*groups)
            rows.append(
                {
                    "metric": metric,
                    "test": "Kruskal-Wallis",
                    "comparison": "All languages",
                    "statistic": round(H, 3),
                    "p_value": p_overall,
                    "p_formatted": format_p_value(p_overall),
                    "significant": p_overall < 0.05,
                    "effect_size": "N/A",
                    "interpretation": "Overall difference detected" if p_overall < 0.05 else "No overall difference",
                }
            )

        for l1, l2 in combinations(languages, 2):
            g1 = work.loc[work[language_col] == l1, "_metric"].values
            g2 = work.loc[work[language_col] == l2, "_metric"].values
            if len(g1) == 0 or len(g2) == 0:
                continue
            _, p = mannwhitneyu(g1, g2, alternative="two-sided")
            delta = cliffs_delta(g1, g2)
            rows.append(
                {
                    "metric": metric,
                    "test": "Mann-Whitney U",
                    "comparison": f"{l1} vs {l2}",
                    "statistic": np.nan,
                    "p_value": p,
                    "p_formatted": format_p_value(p),
                    "significant": p < 0.05,
                    "effect_size": round(delta, 3),
                    "interpretation": interpret_cliffs_delta(delta),
                    "n1": len(g1),
                    "n2": len(g2),
                    "median1": float(np.median(g1)),
                    "median2": float(np.median(g2)),
                }
            )

    return pd.DataFrame(rows)


def run_proportion_tests(
    df: pd.DataFrame,
    binary_cols: list[str],
    language_col: str = "language",
) -> pd.DataFrame:
    """Chi-square omnibus and pairwise Fisher's exact tests for binary features."""
    rows = []
    languages = sorted(df[language_col].dropna().unique())

    for feature in binary_cols:
        if feature not in df.columns:
            continue
        work = df[[language_col, feature]].copy()
        work[feature] = work[feature].astype(int)

        contingency = pd.crosstab(work[language_col], work[feature])
        for col in (0, 1):
            if col not in contingency.columns:
                contingency[col] = 0
        contingency = contingency[[0, 1]]

        if contingency[1].sum() == 0 or contingency[0].sum() == 0:
            rows.append(
                {
                    "feature": feature,
                    "test": "Chi-square",
                    "comparison": "All languages",
                    "statistic": 0.0,
                    "p_value": 1.0,
                    "p_formatted": "1.0000",
                    "significant": False,
                    "effect_size": "N/A",
                    "interpretation": "No variation (all pass or all fail)",
                }
            )
        else:
            chi2, p_overall, _, expected = chi2_contingency(contingency.values)
            if (expected < 5).any():
                p_overall = float("nan")
                interpretation = "Expected count < 5; use pairwise Fisher tests"
            else:
                interpretation = (
                    "Overall difference detected" if p_overall < 0.05 else "No overall difference"
                )
            rows.append(
                {
                    "feature": feature,
                    "test": "Chi-square",
                    "comparison": "All languages",
                    "statistic": round(chi2, 3) if p_overall == p_overall else 0.0,
                    "p_value": p_overall,
                    "p_formatted": format_p_value(p_overall) if p_overall == p_overall else "N/A",
                    "significant": p_overall == p_overall and p_overall < 0.05,
                    "effect_size": "N/A",
                    "interpretation": interpretation,
                }
            )

        for l1, l2 in combinations(languages, 2):
            sub = work[work[language_col].isin([l1, l2])]
            table = pd.crosstab(sub[language_col], sub[feature])
            for col in (0, 1):
                if col not in table.columns:
                    table[col] = 0
            table = table.reindex(index=[l1, l2], columns=[0, 1], fill_value=0)
            if table[1].sum() == 0 or table[0].sum() == 0:
                continue
            _, p = fisher_exact(table.values)
            p1 = table.loc[l1, 1] / table.loc[l1].sum()
            p2 = table.loc[l2, 1] / table.loc[l2].sum()
            h = cohens_h(p1, p2)
            rows.append(
                {
                    "feature": feature,
                    "test": "Fisher's exact",
                    "comparison": f"{l1} vs {l2}",
                    "statistic": np.nan,
                    "p_value": p,
                    "p_formatted": format_p_value(p),
                    "significant": p < 0.05,
                    "effect_size": round(h, 3),
                    "interpretation": interpret_cohens_h(h),
                    "prop1_pct": round(100 * p1, 1),
                    "prop2_pct": round(100 * p2, 1),
                }
            )

    return pd.DataFrame(rows)
