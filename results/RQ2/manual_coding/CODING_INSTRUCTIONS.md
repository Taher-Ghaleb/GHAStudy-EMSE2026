# Open Coding Instructions for GHA Workflows
Generated: 2026-07-03 01:55:53

## Objective
Manually analyse a stratified random sample of 382 GitHub Actions workflows
to uncover naming conventions and structural patterns not detectable through static analysis.
Both authors code independently, then reconcile disagreements using Cohen's Kappa.

## Sample Guarantees
- ONE workflow per unique project (no repository duplicates)
- Proportional representation across languages (Python / Java / C++)
- Complexity stratified by number of steps (tertiles: simple / moderate / complex)
- All 382 YAML files validated and re-parsed before this run
- yaml_reference.csv row count == sample_metadata.csv row count == 382

## Files in This Folder
| File | Purpose |
|------|---------|
| `sample_metadata.csv` | One row per sampled workflow — key identifiers and counts |
| `sample_summary.csv` | Per-language breakdown of the sample |
| `yaml_reference.csv` | Full YAML content — one row per workflow, N == 382 |
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
Repeat until all 382 workflows are coded and κ > 0.80 is sustained.
Then translate finalised codes into regex/keyword rules for automated labelling
of the full dataset.
