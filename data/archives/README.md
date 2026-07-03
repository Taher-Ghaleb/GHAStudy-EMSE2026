# GHA Workflow YAML archives

| Archive | Language | Approx. workflows |
|---------|----------|-------------------|
| `python_yml_files.zip` | Python | ~15k YAML files |
| `java_yml_files.zip` | Java | ~5.7k YAML files |
| `c++_yml_files.zip` | C++ | ~6.7k YAML files |


## Extracting workflows:

```bash
python scripts/extract_workflows.py
```

or (Git Bash / Linux / macOS):

```bash
bash scripts/extract_workflows.sh
```

Extracted YAML files are written to `data/workflows/` (one folder per language). Each archive contains a nested `python/`, `java/`, or `c++/` folder; the extraction scripts flatten this so repository folders (`owner@repo/`) sit directly under each `*_yml_files/` directory.
