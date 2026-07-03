"""Shared repository paths for the EMSE replication package."""

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"
ARCHIVES_DIR = DATA_DIR / "archives"
WORKFLOWS_DIR = DATA_DIR / "workflows"
RESULTS_DIR = PROJECT_ROOT / "results"

WORKFLOW_LANG_DIRS = {
    "Python": WORKFLOWS_DIR / "python_yml_files",
    "Java": WORKFLOWS_DIR / "java_yml_files",
    "C++": WORKFLOWS_DIR / "c++_yml_files",
}

WORKFLOW_LANG_DIRS_KEYED = {
    "python": WORKFLOWS_DIR / "python_yml_files",
    "java": WORKFLOWS_DIR / "java_yml_files",
    "cpp": WORKFLOWS_DIR / "c++_yml_files",
}

ARCHIVE_FILES = {
    "python_yml_files.zip": WORKFLOWS_DIR / "python_yml_files",
    "java_yml_files.zip": WORKFLOWS_DIR / "java_yml_files",
    "c++_yml_files.zip": WORKFLOWS_DIR / "c++_yml_files",
}

# Inner folder name inside each ZIP (removed after extraction).
ARCHIVE_INNER_FOLDERS = {
    "python_yml_files.zip": "python",
    "java_yml_files.zip": "java",
    "c++_yml_files.zip": "c++",
}

RQ1_RESULTS_DIR = RESULTS_DIR / "RQ1"
RQ2_RESULTS_DIR = RESULTS_DIR / "RQ2"
RQ2_MANUAL_CODING_DIR = RQ2_RESULTS_DIR / "manual_coding"
RQ2_PATTERN_ANALYSIS_DIR = RQ2_RESULTS_DIR / "pattern_analysis"
RQ3_RESULTS_DIR = RESULTS_DIR / "RQ3"
