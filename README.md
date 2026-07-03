# Replication Package for the paper *"An Empirical Study of Complexity, Heterogeneity, and Compliance of GitHub Actions Workflows"* (submitted to *EMSE)

This package provides scripts, data layout, and raw results needed to reproduce the analyses reported in the paper.

## Package Structure

```
project-root/
├── data/
│   ├── archives/                 # ZIP archives of workflow YAML files (per language)
│   └── workflows/                # Extracted YAML tree (generated — see below)
├── scripts/
│   ├── extract_workflows.py      # Step 0: unpack archives into data/workflows/
│   ├── extract_workflows.sh      # Bash alternative for Step 0
│   ├── repo_paths.py             # Shared path configuration
│   ├── stats_utils.py            # Shared statistical helpers
│   ├── RQ1.py                    # RQ1: workflow complexity
│   ├── RQ2.py                    # RQ2: patterns + statistics (full pipeline)
│   ├── rq2/                      # RQ2 pipeline stages (called by RQ2.py)
│   │   ├── sample.py
│   │   ├── semantic.py
│   │   └── patterns.py
│   ├── RQ3.py                    # RQ3: compliance + statistics
│   └── interpretation_benchmark_guide.py
├── results/
│   ├── RQ1/                      # metrics, tables/, stats/, figures/, interpretations/
│   ├── RQ2/
│   │   ├── manual_coding/        # sample, yaml_reference, processed_workflows, manual checks
│   │   └── pattern_analysis/     # pattern tables + stats/
│   └── RQ3/                      # compliance outputs + stats/
├── requirements.txt
├── LICENSE
└── README.md
```

## Installation

This package was developed and tested with **Python 3.11+**.

Clone the repository and install dependencies from the project root:

```bash
pip install -r requirements.txt
```

## Usage

All commands below are run from the **repository root**.

### Step 0 — Extract workflow YAML files

Place the three language archives in `data/archives/` (see `data/archives/README.md`), then extract them:

```bash
python scripts/extract_workflows.py
```

or:

```bash
bash scripts/extract_workflows.sh
```

This creates `data/workflows/<language>_yml_files/` with repository folders (`owner@repo/`) directly underneath. You only need to run extraction once (use `--force` to re-extract).

### Step 1 — RQ1: Workflow complexity

```bash
python scripts/RQ1.py
```

**RQ1:** How complex are GHA workflows in open-source projects?

Outputs are written to `results/RQ1/` (metrics tables, statistical tests, figures, and interpretation summaries).

### Step 2 — RQ2: Structure and usage patterns

```bash
python scripts/RQ2.py
```

This runs the full RQ2 pipeline: stratified sampling, semantic step labeling, pattern grouping, and cross-language statistical tests.

**RQ2:** What are the common and diverse structures and usage patterns in GHA workflows?

Outputs: `results/RQ2/manual_coding/` (including `yaml_reference.csv` and `processed_workflows.csv`) and `results/RQ2/pattern_analysis/` (including `stats/`).

- **Open coding and manual review:**
  - RQ2 open-coding followed `results/RQ2/manual_coding/CODING_INSTRUCTIONS.md`.
  - Both authors independently coded the stratified sample (N=382), reconciled disagreements, and refined semantic labels (agreement κ = 0.82).
  - Automated classifier output: `processed_workflows.csv` (from `scripts/rq2/semantic.py`).
  - Manual review results: `processed_workflows_manual checks.csv` (records reconciled labels and decisions in the `NOTES` column).
  - Pattern analysis and statistics use `processed_workflows.csv`; manual-checks file is included for transparency and is not overwritten by the script.
  - RQ3 uses `yaml_reference.csv` from the same folder.

### Step 3 — RQ3: Compliance with best practices

```bash
python scripts/RQ3.py
```

**RQ3:** To what extent do GHA workflows comply with official documentation and best practices?

Outputs: `results/RQ3/` (including `results/RQ3/stats/` for cross-language tests).

## Data

| Path | Description |
|------|-------------|
| `data/archives/*.zip` | Per-language archives of GHA workflow YAML files collected from GitHub (Java, Python, C++) |
| `data/workflows/` | Extracted workflow files used as input to RQ1 and RQ2 sampling (`<language>_yml_files/owner@repo/*.yml`) |

Dataset selection criteria (≥10 stars, non-fork, ≥50 GHA runs, etc.) are described in the paper. The archives contain **27,863** workflow YAML files from **7,668** repositories.

## Results

The `results/` folder contains pre-computed outputs matching the paper:

- **RQ1:** Descriptive statistics, complexity interpretations, statistical tests, and figures
- **RQ2:** Stratified sample metadata, semantic sequences, pattern-analysis tables, and `processed_workflows_manual checks.csv` (manual-review `NOTES` for the N=382 sample)
- **RQ3:** Per-rule compliance detail, workflow summaries, and ranked bad-practice tables

Re-running the scripts will regenerate these outputs (figures in RQ1 may vary slightly across matplotlib versions).

## License

Code in this repository is licensed under the MIT License. See the [LICENSE](LICENSE) file.

Data files are licensed under the [Creative Commons Attribution 4.0 International (CC BY 4.0)](https://creativecommons.org/licenses/by/4.0/) license unless otherwise noted.

## How to Cite

If you use this package, please cite our paper:

```bibtex
@article{abrokwah2026gha,
  title={An Empirical Study of Complexity, Heterogeneity, and Compliance of GitHub Actions Workflows},
  author={Abrokwah, Edward and Ghaleb, Taher A.},
  journal={Empirical Software Engineering},
  year={2026},
  publisher={Springer}
}
```


