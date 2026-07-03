import pandas as pd
import yaml
import re

# =========================
# CONFIG
# =========================
from pathlib import Path

from repo_paths import RQ2_MANUAL_CODING_DIR

INPUT_PATH = RQ2_MANUAL_CODING_DIR / "yaml_reference.csv"
OUTPUT_PATH = RQ2_MANUAL_CODING_DIR / "processed_workflows.csv"

SEQ_SEP = " \u2192 "   # Unicode right arrow: →
JOB_SEP = " || "

# =========================
# SEMANTIC LABEL SETS
# Used for presence flags and sequence normalisation.
# =========================

USE_DISPLAY_NAME_LABELS = frozenset({"other", "external_action", "composite"})

BUILD_LABELS = frozenset({
    "build_project", "build_package", "build_application",
    "build_container_image", "build_static_site", "build_documentation",
    "compile_source_code", "build_firmware", "build_python_wheel",
    "build_library",
})

SETUP_LABELS = frozenset({
    "setup_runtime_environment", "setup_build_environment",
    "setup_package_manager", "configure_build_profile",
    "setup_virtual_environment", "setup_base_environment",
    "setup_local_environment", "setup_cache_service",
    "setup_network_connectivity", "setup_runtime_tool",
})

# =========================
# LABEL DISPLAY NAMES
# Maps internal snake_case labels → "Title Case" tokens in sequence_id.
# =========================
LABEL_DISPLAY_NAMES = {
    # ── Core workflow ──────────────────────────────────────────────────────
    "checkout_repository":                      "Checkout Repository",
    "setup_runtime_environment":                "Setup Runtime Environment",
    "setup_build_environment":                  "Setup Build Environment",
    "setup_package_manager":                    "Setup Package Manager",
    "configure_build_profile":                  "Configure Build Profile",
    "install_project_dependencies":             "Install Project Dependencies",
    "download_external_resources":              "Download External Resources",
    "download_build_artifacts":                 "Download Build Artifacts",
    "compile_source_code":                      "Build Source Code",
    "build_container_image":                    "Build Container Image",
    "build_documentation":                      "Build Documentation",
    "build_static_site":                        "Build Static Site",
    "build_package":                            "Build Package",
    "build_application":                        "Build Application",
    "build_project":                            "Build Project",
    "build_firmware":                           "Build Firmware",
    "build_python_wheel":                       "Build Python Wheel",
    "build_library":                            "Build Library",
    "execute_tests":                            "Execute Tests",
    "execute_cli_tests":                        "Execute CLI Tests",
    "execute_benchmarks":                       "Execute Benchmarks",
    "execute_network_test":                     "Execute Network Test",
    "execute_script":                           "Execute Script",
    "execute_automation_script":                "Execute Automation Script",
    "generate_test_coverage":                   "Generate Test Coverage",
    "upload_build_artifacts":                   "Upload Build Artifacts",
    "publish_release_assets":                   "Publish Release Assets",
    "publish_release":                          "Publish Release",
    "publish_package":                          "Publish Package",
    "publish_test_results":                     "Publish Test Results",
    "publish_artifacts":                        "Publish Artifacts",
    "deploy_documentation":                     "Deploy Documentation",
    "deploy_application":                       "Deploy Application",
    "deploy_infrastructure":                    "Deploy Infrastructure",
    "destroy_infrastructure":                   "Destroy Infrastructure",
    "static_analysis":                          "Run Static Analysis",
    "run_security_analysis":                    "Run Security Analysis",
    "initialize_security_analysis":             "Initialize Security Analysis",
    "perform_security_analysis":                "Perform Security Analysis",
    "automated_code_fix":                       "Automated Code Fix",
    "inspect_environment":                      "Inspect Runtime Environment",
    "inspect_logs":                             "Inspect Logs",
    "inspect_platform_architecture":            "Inspect Platform Architecture",
    "inspect_repository_state":                 "Inspect Repository State",
    "extract_version_metadata":                 "Generate Version Metadata",
    "extract_version_tag":                      "Extract Version Tag",
    "extract_tool_version":                     "Extract Tool Version",
    "extract_dependency_metadata":              "Extract Dependency Metadata",
    "export_environment_configuration":         "Export Environment Configuration",
    "configure_secrets":                        "Configure Secure Access",
    "configure_secure_access":                  "Configure Secure Access",
    "configure_cloud_resources":                "Configure Cloud Resources",
    "configure_git_behavior":                   "Configure Git Behavior",
    "configure_git_access":                     "Configure Git Access",
    "configure_documentation":                  "Configure Documentation",
    "verify_build_integrity":                   "Verify Build Integrity",
    "validate_outputs":                         "Validate Outputs",
    "send_notification":                        "Send Notification",
    "generate_changelog":                       "Generate Changelog",
    "generate_examples":                        "Generate Examples",
    "generate_documentation":                   "Generate Documentation",
    "generate_build_configuration":             "Generate Build Configuration",
    "generate_build_files":                     "Generate Build Files",
    "generate_network_model":                   "Generate Network Model",
    "generate_access_token":                    "Generate Access Token",
    "generate_filename":                        "Generate Filename",
    "generate_contribution_graph":              "Generate Contribution Graph",
    "determine_release_status":                 "Determine Release Status",
    "manage_labels":                            "Manage Labels",
    "manage_workflow_automation":               "Manage Workflow Automation",
    "manage_build_cache":                       "Manage Build Cache",
    "clean_project_artifacts":                  "Clean Project Artifacts",
    "start_services":                           "Start Services",
    "stop_services":                            "Stop Services",
    "provision_runner":                         "Provision Runner",
    "decommission_runner":                      "Decommission Runner",
    "orchestrate_workflow":                     "Orchestrate Workflow",
    "log_information":                          "Log Information",
    "log_system_output":                        "Log System Output",
    "log_workflow_message":                     "Log Workflow Message",
    "log_package_manager_info":                 "Log Package Manager Info",
    "log_toolkit_message":                      "Log Toolkit Message",
    # ── New labels ────────────────────────────────────────────────────────
    "rename_build_artifact":                    "Rename Build Artifact",
    "rename_artifact":                          "Rename Artifact",
    "read_artifact_metadata":                   "Read Artifact Metadata",
    "install_external_tool":                    "Install External Tool",
    "install_system_dependencies":              "Install System Dependencies",
    "install_dependencies_via_package_manager": "Install Dependencies via Package Manager",
    "setup_virtual_environment":                "Setup Virtual Environment",
    "setup_base_environment":                   "Setup Base Environment",
    "setup_local_environment":                  "Setup Local Environment",
    "setup_cache_service":                      "Setup Cache Service",
    "setup_network_connectivity":               "Setup Network Connectivity",
    "setup_runtime_tool":                       "Setup Runtime Tool",
    "archive_tool_cache":                       "Archive Tool Cache",
    "transform_domain_data":                    "Transform Domain Data",
    "process_configuration":                    "Process Configuration",
    "process_support_package":                  "Process Support Package",
    "process_output_files":                     "Process Output Files",
    "terminate_session":                        "Terminate Session",
    "inject_cache_into_container":              "Inject Cache into Container",
    "check_version_consistency":                "Check Version Consistency",
    "compare_version_metadata":                 "Compare Version Metadata",
    "switch_git_reference":                     "Switch Git Reference",
    "split_artifacts":                          "Split Artifacts",
    "adjust_file_permissions":                  "Adjust File Permissions",
    "transfer_container_artifacts":             "Transfer Container Artifacts",
    "define_helper_function":                   "Define Helper Function",
    "define_target_platform":                   "Define Target Platform",
    "define_target_platforms":                  "Define Target Platforms",
    "capture_test_output":                      "Capture Test Output",
    "capture_messages":                         "Capture Messages",
    "collect_logs":                             "Collect Logs",
    "collect_debug_logs":                       "Collect Debug Logs",
    "collect_service_logs":                     "Collect Service Logs",
    "collect_application_logs":                 "Collect Application Logs",
    "update_repository":                        "Update Repository",
    "update_external_service":                  "Update External Service",
    "retrieve_dependency_metadata":             "Retrieve Dependency Metadata",
    "retrieve_toolchain_metadata":              "Retrieve Toolchain Metadata",
    "record_commit_metadata":                   "Record Commit Metadata",
    "report_job_status":                        "Report Job Status",
    "report_coverage":                          "Report Coverage",
    "report_failure_information":               "Report Failure Information",
    "upload_coverage":                          "Upload Coverage",
    "run_link_check":                           "Run Link Check",
    "notify_configuration_change":              "Notify Configuration Change",
    "display_compiler_information":             "Display Compiler Information",
    "display_system_information":               "Display System Information",
    "display_help_information":                 "Display Help Information",
    "prepare_build_artifacts":                  "Prepare Build Artifacts",
    "trigger_release_upload":                   "Trigger Release Upload",
    "trigger_external_upload_workflow":         "Trigger External Upload Workflow",
    "verify_build":                             "Verify Build",
    "run_benchmarks":                           "Execute Benchmarks",
    "skip_workflow":                            "Skip Workflow",
    "prepare_build_environment":                "Prepare Build Environment",
    "configure_system_timezone":                "Configure System Timezone",
    "validate_release_consistency":             "Validate Release Consistency",
}


def display_label(lbl):
    """Convert internal snake_case label to display name for sequence_id."""
    if lbl in LABEL_DISPLAY_NAMES:
        return LABEL_DISPLAY_NAMES[lbl]
    # Fallback: convert snake_case to Title Case
    if "_" in lbl and lbl == lbl.lower():
        return lbl.replace("_", " ").title()
    return lbl  # already a step display name (other/composite/external)


# =========================
# STEP NAME PATTERNS
# =========================
STEP_NAME_PATTERNS = {

    # ── checkout_repository ────────────────────────────────────────────────
    "checkout_repository": [
        r"\bcheckout\b", r"\bclone\b",
        r"fetch.*(?:source|repo|code)",
        r"checkout\s+(?:pr|tip|develop|main|master|sources?)",
    ],

    # ── switch_git_reference ───────────────────────────────────────────────
    "switch_git_reference": [
        r"git\s+checkout\s+head\^2\b",
        r"switch\s+git\s+reference\b",
    ],

    # ── setup_runtime_environment ─────────────────────────────────────────
    "setup_runtime_environment": [
        r"set\s+up\s+(?:python|java|jdk|node|go|ruby|dotnet|r\b)",
        r"setup\s+(?:python|java|jdk|node|go|ruby|dotnet|r\b)",
        r"install\s+(?:python|java|jdk|node)\b",
        r"set\s+up\s+(?:test|build)\s+java",
        r"setup\s+(?:conda|miniconda|micromamba)\b",
        r"setup\s+conda\s+environment",
        r"setup\s+micromamba",
        r"add\s+conda\s+to\s+system\s+path",
        r"build\s+python\s+environment",
        r"create\s+(?:final\s+)?images?\s+directory",
        r"install\s+(?:gnu\s+)?fortran\b",
        r"setup\s+(?:gnu\s+)?fortran\s+compiler",
        r"install\s+nodejs",
        r"install\s+jdk\b",
        r"install\s+miniforge",
        r"^setup\s+runtime\b",
    ],

    # ── setup_runtime_tool ────────────────────────────────────────────────
    "setup_runtime_tool": [
        r"^setup\s+uv\b",
        r"setup\s+runtime\s+tool\b",
    ],

    # ── setup_build_environment ───────────────────────────────────────────
    "setup_build_environment": [
        r"(?:set\s+up|setup)\s+(?:msvc|msbuild|mingw|gcc|llvm|clang|cmake|ninja|xcode)\b",
        r"generate\s+cmake\s+project",
        r"create\s+build\s+environment",
        r"setup\s+(?:xmake|sam|emsdk|tools)\b",
        r"setup\s+(?:gnu\s+)?fortran\s+compiler",
        r"install\s+(?:llvm|clang|gcc|g\+\+)\b",
        r"set\s+up\s+ccache",
        r"setup\s+ccache",
        r"enable\s+ccache",
        r"install\s+(?:openmp|ninja|cmake)\b",
        r"setup\s+boost",
        r"msbuild\b",
        r"configure\s+cmake\b",
        r"configure\s+xmake",
        r"install\s+dpc\+\+",
        r"install\s+mkl\b",
    ],

    # ── setup_package_manager ─────────────────────────────────────────────
    "setup_package_manager": [
        r"setup\s+vcpkg",
        r"install\s+conan\b",
        r"conan\s+(?:install|profile)",
    ],

    # ── configure_build_profile ───────────────────────────────────────────
    "configure_build_profile": [
        r"lnst\s+setup",
        r"setup\s+catkin",
        r"set\s+up\s+flathub",
        r"set\s+flatpak\s+arch",
        r"setup\s+unity\s+catalog\s+test\s+server",
        r"setup\s+ros\s+environment",
        r"prepare\s+action\b",
        r"prebuild\s+actions?",
        r"pre.?build\s+actions?",
        r"set\s+up\s+the\s+stack\b",
        r"setup\s+(?:the\s+)?stack\b",
        r"setup\s+workspace\b",
        r"make\s+build\s+directory",
        r"create\s+(?:temp|build)\s+dir",
        r"set\s+up\s+(?:git|mysql|postgres|mongodb|redis|localstack|memcached|chromadb)\b",
        r"start\s+(?:mysql|postgres|mongodb|memcached|redis|localstack|chromadb)\b",
        r"configure\s+openssl",
        r"fix\s+checkout\s+ownership",
        r"git\s+nonsense",
        r"configure\s+git\b",
        r"set\s+timezone\b",
        r"configure\s+(?:ubuntu|macos|build\s+java|test\s+java)",
        r"stash\s+\w+\s+java",
        r"setup\s+test\s+db",
        r"make\s+init\b",
        r"create\s+(?:dockerfile|vcpkg\.json)",
        r"enable\s+deploy\s+steps",
        r"disable\s+dry-run",
        r"copy\s+test[_\s]?resources?",
        r"set\s+dynamic\s+matrix",
    ],

    # ── configure_documentation ───────────────────────────────────────────
    "configure_documentation": [
        r"upgrade\s+doxygen\s+conf\b",
        r"configure\s+documentation\b",
    ],

    # ── configure_git_behavior ────────────────────────────────────────────
    "configure_git_behavior": [
        r"allow\s+file://\s+clones?\b",
        r"configure\s+git\s+behavior\b",
    ],

    # ── configure_git_access ──────────────────────────────────────────────
    "configure_git_access": [
        r"git\s+config.*global.*url.*https://ease-lab\b",
        r"git\s+config.*global.*url.*goprivate\b",
        r"configure\s+git\s+access\b",
    ],

    # ── setup_virtual_environment ─────────────────────────────────────────
    "setup_virtual_environment": [
        r"create\s+virtual\s+environment\b",
        r"setup\s+virtual\s+environment\b",
    ],

    # ── setup_base_environment ────────────────────────────────────────────
    "setup_base_environment": [
        r"^base\s+setup\b",
        r"setup\s+base\s+environment\b",
    ],

    # ── setup_local_environment ───────────────────────────────────────────
    "setup_local_environment": [
        r"^local\s+setup\b",
        r"setup\s+local\s+environment\b",
    ],

    # ── setup_network_connectivity ────────────────────────────────────────
    "setup_network_connectivity": [
        r"\btailscale\b",
        r"setup\s+network\s+connectivity\b",
    ],

    # ── setup_cache_service ───────────────────────────────────────────────
    "setup_cache_service": [
        r"setup\s+memcached\b",
        r"setup\s+cache\s+service\b",
    ],

    # ── install_project_dependencies ──────────────────────────────────────
    "install_project_dependencies": [
        r"install\s+(?:project\s+)?dep(?:endencies)?\b",
        r"install\s+(?:remaining|extra|linux|system)\s+dep",
        r"install.*platformio",
        r"enable.*esp.*platform",
        r"install\s+littlefs\s+tool",
        r"download\s+(?:and\s+install\s+)?sdl",
        r"download\s+(?:and\s+install\s+)?premake",
        r"install\s+opengl\s+and\s+sdl",
        r"install\s+compilers?\s+for\s+macos",
        r"install\s+(?:at-spi|scrot|wxpython|ffmpeg|ssl)\b",
        r"install\s+android\s+sdk",
        r"install\s+ndk\b",
        r"install\s+(?:system|example-robot-data|mc_rtc)",
        r"install\s+(?:openmp|lcov|pandoc|doxygen|eatmydata)",
        r"install\s+(?:poetry|nox|hatch|pdm|uv)\b",
        r"install\s+(?:linux|mesa|microsoft\s+fonts)",
        r"install\s+(?:wxpython\s+)?(?:from\s+wagon|dep)",
        r"install\s+(?:phoebe|pynucastro|jktebop)\b",
        r"install\s+(?:amreX|microphysics)",
        r"prepare\s+org\.flatpak",
        r"install\s+(?:auto-cpufreq|nimble\s+packages?)",
        r"collect\s+requirements?\b",
        r"rename\s+conda-forge\s+packages?",
        r"install\s+requirements?\b",
        r"upgrade\s+pip\b",
        r"update\s+npm\b",
        r"install\s+npm\s+dep",
        r"install\s+python\s+librairies?",
        r"install\s+python\s+package",
        r"install\s+dev.*req",
        r"install\s+test.*data",
        r"install\s+ros\b",
        r"downgrade\s+pthread",
        r"install\s+(?:at-spi2|doxygen)\b",
    ],

    # ── install_external_tool ─────────────────────────────────────────────
    "install_external_tool": [
        r"install\s+qt\b",
        r"install\s+(?:latest\s+)?rust\s+toolchain\b",
        r"install\s+external\s+tool\b",
    ],

    # ── install_dependencies_via_package_manager ──────────────────────────
    "install_dependencies_via_package_manager": [
        r"use\s+package\s+manager\b",
        r"install\s+dependencies\s+via\s+package\s+manager\b",
    ],

    # ── install_system_dependencies ───────────────────────────────────────
    "install_system_dependencies": [
        r"rosdep\s+install\b",
        r"install\s+system\s+dependencies?\b",
    ],

    # ── download_external_resources ───────────────────────────────────────
    "download_external_resources": [
        r"download\s+(?:mfw|external|spec\s+file)",
        r"download\s+(?:source\s+file|release\s+asset)",
        r"download\s+ndk\b",
        r"get\s+amreX",
        r"get\s+microphysics",
        r"run\s+download-archives\.sh\b",
    ],

    # ── download_build_artifacts ──────────────────────────────────────────
    "download_build_artifacts": [
        r"download\s+(?:all\s+sharded|merged|coverage|linux|macos?|windows|x86|arm)\s+(?:support\s+)?(?:packages?|artifacts?|builds?)",
        r"download\s+(?:linux|macos?|windows)\s+artifact",
        r"download\s+build-\d+\s+artifacts?",
        r"download\s+html\s+documentation",
        r"download\s+documentation\s+archive",
        r"get\s+wheels?\s+from\s+cache",
        r"get\s+conda\s+environment\s+from\s+cache",
        r"download\s+(?:master|release)\s+(?:server\s+)?(?:binary|data|artifacts?)",
        r"download\s+(?:release\s+)?(?:data\s+)?artifacts?",
        r"download\s+(?:release\s+)?binaries?",
        r"download\s+(?:toolkit|fonts?|doc)\s+(?:build\s+)?artifacts?",
        r"get\s+(?:conda|python)\s+environment",
        r"manually\s+download\s+jdk\b",
    ],

    # ── compile_source_code ───────────────────────────────────────────────
    "compile_source_code": [
        r"\bcompile\b",
        r"make\s+(?:daal|onedal)\b",
        r"compile\s+burn_cell",
        r"compile\s+nse_net_cell",
        r"compile\s+(?:library|binding|python\s+binding)",
    ],

    # ── build_container_image ─────────────────────────────────────────────
    "build_container_image": [
        r"build\s+(?:the\s+)?(?:test\s+)?(?:docker\s+)?image\b",
        r"build\s+(?:and\s+test\s+)?udmis",
        r"run\s+image\b",
        r"create\s+littlefs\s+image",
    ],

    # ── build_documentation ───────────────────────────────────────────────
    "build_documentation": [
        r"build\s+(?:the\s+)?documentation",
        r"build\s+docs?\b",
        r"generate\s+javadoc",
        r"openupgrade\s+docs?",
        r"make\s+docs?\b",
        r"build\s+openems\s+ui",
        r"build\s+(?:and\s+)?deploy\b",
        r"build\s+jupyter\s+book",
    ],

    # ── build_static_site ─────────────────────────────────────────────────
    "build_static_site": [
        r"build\s+(?:with\s+)?jekyll",
        r"build\s+pages?\b",
        r"mkdocs\s+build",
    ],

    # ── build_package ─────────────────────────────────────────────────────
    "build_package": [
        r"build\s+(?:manylinux\s+)?wheel",
        r"build\s+(?:windows|mac|linux|arm)\s+wheel",
        r"build\s+clean\s+packages?",
        r"build\s+dev\s+packages?",
        r"build\s+source\s+and\s+wheel",
        r"build\s+(?:extension|package)\b",
        r"pack\s+tool\b",
        r"build\s+dist(?:ribution)?\b",
        r"eatmydata\s+debuild\b",
        r"yes\s+y\s*\|\s*eatmydata\b",
    ],

    # ── build_python_wheel ────────────────────────────────────────────────
    "build_python_wheel": [
        r"build\s+manylinux\s+wheel\b",
        r"build\s+python\s+wheel\b",
    ],

    # ── build_firmware ────────────────────────────────────────────────────
    "build_firmware": [
        r"esp32\w*\s+build\b",
        r"build\s+firmware\b",
    ],

    # ── build_library ─────────────────────────────────────────────────────
    "build_library": [
        r"ansys/actions/build-library\b",
        r"build\s+library\b",
    ],

    # ── build_application ─────────────────────────────────────────────────
    "build_application": [
        r"build\s+app\b",
        r"build\s+android",
        r"create\s+universal\s+app",
        r"build\s+(?:with\s+)?xcode",
        r"build\s+(?:binary|installer|exe|disk\s+image)\b",
        r"build\s+(?:the\s+)?sam\s+project",
        r"collect\s+static\s+assets?",
    ],

    # ── build_project ─────────────────────────────────────────────────────
    "build_project": [
        r"^build\b",
        r"build\s+(?:release|debug)\b",
        r"build\s+(?:swss|udmis|crocoddyl)",
        r"build\s+(?:all\s+)?java\s+packages?",
        r"build\s+(?:and\s+test\s+)?org\.flatpak",
        r"build\s+with\s+(?:cmake|gradle|maven|make)\b",
        r"build\s+(?:clean|c\+\+|fbneo|meson)\b",
        r"configure\s+and\s+build",
        r"msbuild\b",
        r"run\s+platformio",
        r"prepare\s+files?\s+for\s+(?:publish|release)",
        r"compress.*image",
        r"update.*colou?rs?",
        r"generate\s+(?:multi-language\s+)?examples?",
        r"generate\s+stls?",
        r"generate\s+headers?",
        r"generate\s+(?:python\s+)?client\b",
        r"generate\s+code\b",
        r"generate\s+collection\b",
        r"extract\s+ipynb\s+examples",
        r"gencode\b",
        r"build\s+library\b",
        r"build\s+(?:swss|one[Dd][Aa][Ll])\b",
        r"make\s+(?:daal|onedal)\b",
        r"pack\b",
        r"add\s+known\s+hosts?\b",
        r"msbuild\.exe\b",
        r"meson\s+build\b",
        r"check\s+build\b",
        r"verify\s+build\b",
    ],

    # ── deploy_infrastructure ─────────────────────────────────────────────
    "deploy_infrastructure": [
        r"pulumi\s*up\b",
        r"pulumiup\b",
    ],

    # ── destroy_infrastructure ────────────────────────────────────────────
    "destroy_infrastructure": [
        r"pulumi\s*down\b",
        r"pulumidown\b",
    ],

    # ── generate_examples ─────────────────────────────────────────────────
    "generate_examples": [
        r"generate\s+multi.?language\s+examples?\b",
        r"generate\s+examples?\b",
    ],

    # ── generate_build_configuration ──────────────────────────────────────
    "generate_build_configuration": [
        r"create\s+user-config\.jam\b",
        r"generate\s+build\s+configuration\b",
    ],

    # ── generate_build_files ──────────────────────────────────────────────
    "generate_build_files": [
        r"run\s+premake\b",
        r"generate\s+build\s+files?\b",
    ],

    # ── generate_network_model ────────────────────────────────────────────
    "generate_network_model": [
        r"regenerate\s+(?:he-burn|ecsn|ase)\S*\s+network\b",
        r"generate\s+network\s+model\b",
    ],

    # ── generate_documentation ────────────────────────────────────────────
    "generate_documentation": [
        r"convert\s+output\.md\s+to\s+pages?\b",
        r"generate\s+documentation\b",
    ],

    # ── generate_access_token ─────────────────────────────────────────────
    "generate_access_token": [
        r"generate\s+temporary\s+access\s+token\b",
        r"generate\s+access\s+token\b",
    ],

    # ── generate_contribution_graph ───────────────────────────────────────
    "generate_contribution_graph": [
        r"platane/snk\b",
        r"generate\s+contribution\s+graph\b",
    ],

    # ── generate_filename ─────────────────────────────────────────────────
    "generate_filename": [
        r"echo.*filename=jwql\b",
        r'echo.*filename=',
        r"generate\s+filename\b",
    ],

    # ── prepare_build_artifacts ───────────────────────────────────────────
    "prepare_build_artifacts": [
        r"copy\s+artifacts?\s+for\s+docker\s+build\b",
        r"copy\s+build\s+into\s+temp_dir\b",
        r"prepare\s+build\s+artifacts?\b",
    ],

    # ── execute_tests ─────────────────────────────────────────────────────
    "execute_tests": [
        r"run\s+\w+\s+unit\s+tests?",
        r"run\s+\w+\s+tests?\b",
        r"run\s+standalone\s+tests?",
        r"run\s+ninja\s+",
        r"run\s+json\s+dump",
        r"smoke\s*test",
        r"\bunit\s*test\b",
        r"test\s+if\s+publishing\s+works",
        r"run\s+integration\s+tests?",
        r"run\s+ui\s+tests?",
        r"run\s+non-ui\s+tests?",
        r"run\s+(?:all\s+)?tests?\b",
        r"run\s+python\s+tests?",
        r"run\s+c\+\+\s+tests?",
        r"test\s+extension\b",
        r"run\s+burn_cell",
        r"compare\s+to\s+stored\s+output",
        r"run\s+(?:django|flask)\s+test",
        r"test\s+(?:transport|eos|integration|ignition|jacobian|crypto|connection)\b",
        r"tck\s+report",
        r"verify\s+sorted\s+imports",
        r"check\s+launcher",
        r"start\s+and\s+test\s+local\s+servers?",
        r"run\s+all\s+enrt\s+recipes",
        r"test\s+with\s+(?:pytest|unittest|java)",
        r"run\s+tests?\s+on\s+browserstack",
        r"run\s+module\s+tests?",
        r"run\s+interactor\s+tests?",
        r"run\s+(?:coverage|unit|functional|server|django)\s+tests?",
        r"build\s+and\s+(?:unit\s+)?test\b",
        r"run\s+(?:test\s+)?suite\b",
        r"test\s+--dump-config",
        r"run\s+coverage\s+tests?",
        r"run\s+nox\b",
        r"(?:bin/)?run_tests\b",
        r"bin/test_\w+",
        r"sequence\s+tests?\s+alpha",
        r"itemized\s+sequencer\s+tests?",
        r"run\s+tests?\s+with\s+the\s+test\s+docker",
        r"applying\s+fixes?\b",
        r"catkin\s+build",
        r"test\s+image\b",
        r"test\s+notebooks?",
        r"simpleNetworkRecipe.*ping",
        r"trigger\s+tests?\s+in\s+readthedocs",
        r"fedora\s+tox\s+with\b",
    ],

    # ── execute_cli_tests ─────────────────────────────────────────────────
    "execute_cli_tests": [
        r"test\s+cli\s+commands?\b",
        r"execute\s+cli\s+tests?\b",
    ],

    # ── execute_network_test ──────────────────────────────────────────────
    "execute_network_test": [
        r"simplenetworkrecipe\s+ping\s+test\b",
        r"execute\s+network\s+test\b",
    ],

    # ── execute_benchmarks ────────────────────────────────────────────────
    "execute_benchmarks": [
        r"run\s+benchmarks?\b",
        r"execute\s+benchmarks?\b",
    ],

    # ── execute_script ────────────────────────────────────────────────────
    "execute_script": [
        r"run\s+\w+\s+script\b",
        r"execute\s+script\b",
    ],

    # ── execute_automation_script ─────────────────────────────────────────
    "execute_automation_script": [
        r"\[approve\].*actions/github-script\b",
        r"execute\s+automation\s+script\b",
    ],

    # ── generate_test_coverage ────────────────────────────────────────────
    "generate_test_coverage": [
        r"generate\s+(?:coverage\s+)?reports?",
        r"generate\s+(?:coveralls|jacoco|lcov)",
        r"collect\s+coverage\s+report",
        r"generate\s+coverage\s+(?:percent|failing)\s+badge",
        r"run\s+coverage\b",
        r"generate\s+jacoco",
        r"combine\s+coverage",
        r"create\s+coverage\s+report",
    ],

    # ── upload_coverage ───────────────────────────────────────────────────
    "upload_coverage": [
        r"upload\s+coverage\b",
    ],

    # ── report_coverage ───────────────────────────────────────────────────
    "report_coverage": [
        r"report\s+coverage\b",
    ],

    # ── upload_build_artifacts ────────────────────────────────────────────
    "upload_build_artifacts": [
        r"^commit\s+files?\b",
        r"^push\s+changes?\b",
        r"^commit\b",
        r"save\s+(?:the\s+)?compiled\s+libraries?",
        r"archive\s+littlefs\s+image",
        r"collect\s+test\s+reports?",
        r"store\s+test\s+results?",
        r"upload\s+documentation\s+archive",
        r"auto\s+commit\s+changes",
        r"upload\s+(?:screenshot|core\s+dump)",
        r"save\s+worker\s+image",
        r"move\s+cache",
        r"upload\s+(?:js|font)\s+build",
        r"copy\s+(?:toolkit|fonts?)\s+artifacts?",
        r"upload\s+doxygen",
        r"commit\s+docs?\b",
        r"commit\s+json\s+files?",
        r"upload\s+(?:win|linux|arm|macos?)\s+build",
        r"upload\s+(?:artifacts?|binary|installer|tool\s+cache|app\s+artifact)\b",
        r"archive\s+(?:firmware|binary|merged|usermode|kernelmode|build)",
        r"save\s+(?:compiled|cached)\s+\w+",
        r"upload\s+server\s+binary",
        r"upload\s+game\s+binary",
        r"upload\s+data\s+files?",
        r"archive\s+(?:oneDAL|daal|onedal)\b",
        r"prepare\s+outputs?\s+for\s+caching",
        r"cache\s+outputs?\s+for\s+universal",
        r"upload\s+(?:sdist|wheel)\b",
        r"upload\s+merged\s+support\s+package",
        r"upload\s+fabric\b",
        r"upload\s+forge\b",
        r"push\s+code\b",
        r"push\s+binary\b",
        r"copy\s+the\s+(?:toolkit|fonts?)\s+artifacts?\s+to\s+gh-pages\b",
    ],

    # ── publish_artifacts ─────────────────────────────────────────────────
    "publish_artifacts": [
        r"copy\s+the\s+\w+\s+artifacts?\s+to\s+gh-pages\b",
        r"publish\s+artifacts?\b",
    ],

    # ── publish_release_assets ────────────────────────────────────────────
    "publish_release_assets": [
        r"upload\s+firmware\b",
        r"upload\s+release\s+asset",
        r"update\s+gist",
        r"upload\s+(?:to\s+)?pypi\b",
    ],

    # ── trigger_release_upload ────────────────────────────────────────────
    "trigger_release_upload": [
        r"trigger\s+release\s+upload\b",
    ],

    # ── publish_release ────────────────────────────────────────────────────
    "publish_release": [
        r"create\s+release\b",
        r"release\s+to\s+github",
        r"tag\s+release\b",
        r"perform\s+release\b",
        r"create\s+sentry\s+release",
        r"increment\s+build\s+number",
    ],

    # ── publish_package ────────────────────────────────────────────────────
    "publish_package": [
        r"publish\s+to\s+maven",
        r"publish\s+(?:development|release)\s+doc(?:umentation)?",
        r"publish\s+(?:python\s+)?distribution",
        r"release\s+to\s+(?:the\s+public\s+)?pypi",
        r"publish\s+python.*distribution.*pypi\b",
    ],

    # ── deploy_documentation ───────────────────────────────────────────────
    "deploy_documentation": [
        r"push\s+to\s+gh-?pages",
        r"push\s+changes?\s+to\s+(?:gh-?pages|doxygen)",
        r"push\s+the\s+built",
        r"deploy\s+documentation\s+sphinx",
        r"publish\s+(?:development|release)\s+doc",
        r"deploy\s+(?:javadoc|docs?|documentation)\b",
        r"publish\s+(?:test\s+)?results?\b",
        r"publish\s+(?:checkstyle|spotbugs)\s+report",
    ],

    # ── deploy_application ────────────────────────────────────────────────
    "deploy_application": [
        r"deploy\s+to\s+(?:github|gh)\s+pages",
        r"deploy\s+to\s+(?:server|worker)",
        r"deploy\s+to\s+elastic\s+beanstalk",
        r"refresh\s+cdn\b",
        r"deploy\s+to\s+worker\s+server",
    ],

    # ── static_analysis ────────────────────────────────────────────────────
    "static_analysis": [
        r"ensure\s+no\s+tabs?",
        r"ensure.*(?:no\s+)?trailing\s+whitespace",
        r"source\s+review",
        r"check\s+for\s+showstopper",
        r"formatting\s+with\s+black",
        r"sort\s+imports\s+with\s+isort",
        r"lint\s+with\s+flake8",
        r"check\s+(?:code\s+)?format(?:ting)?\b",
        r"check\s+python\s+types?",
        r"check\s+imports?\b",
        r"check\s+docstrings?",
        r"check\s+comment\s+format",
        r"run\s+ruff",
        r"json5-lint",
        r"renovate-config-validator",
        r"run\s+(?:detekt|spotless)",
        r"imports?\s+check",
        r"download\s+actionlint",
        r"check\s+workflow\s+files",
        r"look\s+for\s+changes\s+to",
        r"comment\s+if\s+\w+\s+changed",
        r"fail\s+on\s+banned\s+file",
        r"check\s+that\s+all\s+files\s+generated",
        r"verify\s+boilerplate",
        r"run\s+pre-commit\b",
        r"run\s+(?:golangci|golangci-lint)",
        r"run\s+linters?\b",
        r"run\s+clang-format",
        r"run\s+flake8\b",
        r"run\s+codespell",
        r"check\s+with\s+ruff",
        r"run\s+mypy\s+type\s+checking",
        r"run\s+pylint\b",
        r"lint\s+(?:the\s+)?files?\b",
        r"run\s+package\s+safety",
        r"checkstyle\b",
        r"resolve\s+openems\s+bundles?",
        r"validate\s+(?:backend|edge)app\.bndrun",
        r"run\s+flatmanager\s+checks?",
        r"sanity\s+check\s+on",
        r"run\s+checks?\s+other\s+than\s+tests?",
        r"qa\s+check",
        r"run\s+format\s+check",
        r"run\s+isort\s+check",
        r"check\s+appstream",
        r"check\s+user\s+exceptions?",
        r"check\s+(?:app|ref)\s+override",
        r"^lint\b",
        r"^static\s+analysis\b",
        r"codespell\b",
        r"run\s+static\s+analysis\b",
    ],

    # ── run_security_analysis ─────────────────────────────────────────────
    "run_security_analysis": [
        r"bandit\s+security\s+check\b",
        r"run\s+security\s+analysis\b",
    ],

    # ── initialize_security_analysis ─────────────────────────────────────
    "initialize_security_analysis": [
        r"init(?:ializ[e]?)?\s+codeql",
        r"initialize\s+codeql",
    ],

    # ── perform_security_analysis ─────────────────────────────────────────
    "perform_security_analysis": [
        r"perform\s+codeql\s+analysis",
        r"codeql\s+(?:scan|analyze|analysis)",
        r"run\s+(?:snyk|trivy|grype|semgrep)\b",
        r"dependency\s+review",
        r"security\s+scan",
    ],

    # ── run_link_check ────────────────────────────────────────────────────
    "run_link_check": [
        r"run\s+markdown\s+link\s+check\b",
        r"run\s+link\s+check\b",
    ],

    # ── automated_code_fix ────────────────────────────────────────────────
    "automated_code_fix": [
        r"autofix\b",
        r"auto.?fix\b",
        r"automated\s+fix",
    ],

    # ── publish_test_results ──────────────────────────────────────────────
    "publish_test_results": [
        r"publish\s+test\s+report",
        r"publish\s+test\s+results?",
    ],

    # ── inspect_environment ────────────────────────────────────────────────
    # NOTE: the tag=... && ... conditional variant lives here (not extract_version_tag)
    "inspect_environment": [
        r"^list\s+all\s+files",
        r"^cat\s+\w",
        r"system\s+inform",
        r"check\s+settings?\b",
        r"environment\s+information",
        r"display.*inno\s+setup",
        r"check\s+deployment\s+settings",
        r"dump\s+conda\s+environment",
        r"list\s+installed\s+packages?",
        r"get\s+file\s+changes",
        r"get\s+number\s+of\s+git\s+commits",
        r"print\s+(?:disk|docker)\s+(?:usage|details)",
        r"display\s+(?:sqlite|python)\s+version",
        r"display\s+structure",
        r"show\s+distributions?",
        r"check\s+for\s+output\.md",
        r"display\s+content\s+of",
        r"display\s+working\s+code\s+directory",
        # julia versioninfo run as step name
        r"julia\s+-e\s+.*versioninfo\b",
        r"julia\s+-e\s+.*interactiveutils\b",
        # tag conditional — checking existence of release, not extracting it
        r"tag=.*github\.event\.release\s*&&",
    ],

    # ── inspect_logs ──────────────────────────────────────────────────────
    "inspect_logs": [
        r"printing\s+(?:short)?log\b",
        r"inspect\s+logs?\b",
    ],

    # ── inspect_platform_architecture ─────────────────────────────────────
    "inspect_platform_architecture": [
        r"binaryplatforms.*hostplatform\b",
        r"inspect\s+platform\s+architecture\b",
    ],

    # ── inspect_repository_state ──────────────────────────────────────────
    "inspect_repository_state": [
        r"check\s+git\s+status\s+before\s+commit\b",
        r"inspect\s+repository\s+state\b",
    ],

    # ── extract_version_metadata ──────────────────────────────────────────
    "extract_version_metadata": [
        r"extract\s+version\s+number",
        r"set\s+build\s+version",
        r"retrieve\s+(?:package\s+)?version",
        r"set\s+tag\s+name",
        r"set\s+version\s+output",
        r"get\s+tag\b",
        r"clean\s+github\.ref_name",
        r"patch\s+package\s+versions?",
        r"read\s+version",
        r"get\s+draft\s+release\s+id",
        r"parse\s+latest\s+clone\s+count",
        r"generate\s+release\s+body",
        r"get\s+commit\s+message",
        r"get\s+current\s+date",
        r"\bgit\s+describe\b",
    ],

    # ── extract_version_tag ───────────────────────────────────────────────
    "extract_version_tag": [
        r"tag=.*github\.event\.release\b",
        r"extract\s+version\s+tag\b",
    ],

    # ── extract_dependency_metadata ───────────────────────────────────────
    "extract_dependency_metadata": [
        r"dependabot\s+metadata\b",
        r"extract\s+dependency\s+metadata\b",
    ],

    # ── extract_tool_version ──────────────────────────────────────────────
    "extract_tool_version": [
        r"echo.*sam_cli_version.*curl\b",
        r'echo.*sam_cli_version=\$\(curl\b',
        r"arduino\s+recent\s+cores?\s+versions?\s+info\b",
        r"extract\s+tool\s+version\b",
    ],

    # ── retrieve_dependency_metadata ──────────────────────────────────────
    "retrieve_dependency_metadata": [
        r"retrieve\s+dependencies?\s+hash\b",
        r"retrieve\s+dependency\s+metadata\b",
    ],

    # ── retrieve_toolchain_metadata ───────────────────────────────────────
    "retrieve_toolchain_metadata": [
        r"retrieve\s+toolchain\s+metadata\b",
    ],

    # ── record_commit_metadata ────────────────────────────────────────────
    "record_commit_metadata": [
        r"echo.*llvm_commit.*git\s+rev-parse\b",
        r'echo.*llvm_commit=\$\(git\b',
        r"record\s+commit\s+metadata\b",
    ],

    # ── export_environment_configuration ─────────────────────────────────
    "export_environment_configuration": [
        r"set\s+version\s+environment",
        r"set\s+xmake\s+env",
        r"set\s+\w+\s+environment\s+variable",
        r"set\s+ros\s+version",
        r"export\s+env",
        r"set\s+environment\s+variables?\b",
        r"update\s+path\b",
        r"create\s+env\s+file",
        r"phoebe\s+environment\s+variables",
    ],

    # ── configure_secrets ─────────────────────────────────────────────────
    "configure_secrets": [
        r"inject\s+(?:access\s*)?key",
        r"inject\s+android\s+keystore",
        r"setup\s+android\s+keystore",
        r"setup\s+git\s+credentials?",
        r"import\s+gpg\s+key",
        r"install\s+ssh\s+key",
        r"grant\s+execute\s+permission",
        r"chmod.*gradlew",
    ],

    # ── configure_cloud_resources ─────────────────────────────────────────
    "configure_cloud_resources": [
        r"configure\s+aws\s+credentials?",
        r"setup\s+aws\s+security\s+group",
        r"whitelist\s+runner\s+ip",
        r"get\s+runner\s+ip\s+address",
        r"login\s+to\s+(?:docker|registry|github\s+container)",
        r"gh\s+login",
        r"gcloud\s+auth",
    ],

    # ── verify_build_integrity ─────────────────────────────────────────────
    "verify_build_integrity": [
        r"check\s+matrix\s+definition",
        r"validate\s+exceptions?(?:\.json)?",
        r"check\s+if\s+fork",
        r"check\s+(?:status\s+of\s+)?containers?",
        r"check\s+distribution\s+descriptions?",
        r"install\s+(?:wheel|source)\s+distributions?",
        r"check\s+(?:wheel|source)\s+distributions?",
        r"test\s+jktebop\s+install",
        r"verify\s+matrix\s+jobs\s+succeeded",
        r"check\s+if\s+branch\s+existed",
        r"move\s+ssl\s+certificate",
        r"build\s+and\s+test\s+with\s+java",
    ],

    # ── check_version_consistency ─────────────────────────────────────────
    "check_version_consistency": [
        r"check.*patch\s+code\s+version\b",
        r"check\s+version\s+consistency\b",
    ],

    # ── compare_version_metadata ──────────────────────────────────────────
    "compare_version_metadata": [
        r"compare\s+version\s+from\s+json\b",
        r"compare\s+version\s+metadata\b",
    ],

    # ── validate_outputs ──────────────────────────────────────────────────
    "validate_outputs": [
        r"compare\s+(?:and\s+handle\s+)?(?:files?|output)",
        r"check\s+for\s+changes\b",
        r"diff\s+output",
        r"check\s+pr_title",
        r"validator\s+result\b",
    ],

    # ── capture_test_output ───────────────────────────────────────────────
    "capture_test_output": [
        r"all\s+test\s+output\b",
        r"capture\s+test\s+output\b",
    ],

    # ── capture_messages ──────────────────────────────────────────────────
    "capture_messages": [
        r"message\s+captures?\b",
        r"capture\s+messages?\b",
    ],

    # ── process_output_files ──────────────────────────────────────────────
    "process_output_files": [
        r"output\s+files?\b",
        r"process\s+output\s+files?\b",
    ],

    # ── collect_logs ──────────────────────────────────────────────────────
    "collect_logs": [
        r"pubber\s+logs?\b",
        r"collect\s+logs?\b",
    ],

    # ── collect_debug_logs ────────────────────────────────────────────────
    "collect_debug_logs": [
        r"mosquitto\s+debug\b",
        r"collect\s+debug\s+logs?\b",
    ],

    # ── collect_service_logs ──────────────────────────────────────────────
    "collect_service_logs": [
        r"mosquitto\s+logs?\b",
        r"collect\s+service\s+logs?\b",
    ],

    # ── collect_application_logs ──────────────────────────────────────────
    "collect_application_logs": [
        r"pubber\.log\b",
        r"collect\s+application\s+logs?\b",
    ],

    # ── log_system_output ─────────────────────────────────────────────────
    "log_system_output": [
        r"udmis\s+log\b",
        r"log\s+system\s+output\b",
    ],

    # ── log_workflow_message ──────────────────────────────────────────────
    "log_workflow_message": [
        r"^congratulations\b",
        r"^skipped\b",
        r"log\s+workflow\s+message\b",
    ],

    # ── log_toolkit_message ───────────────────────────────────────────────
    "log_toolkit_message": [
        r"matrix\.toolkit\.message\b",
        r"log\s+toolkit\s+message\b",
    ],

    # ── log_package_manager_info ──────────────────────────────────────────
    "log_package_manager_info": [
        r"echo\s+package\s+manager\b",
        r"log\s+package\s+manager\s+info\b",
    ],

    # ── report_job_status ─────────────────────────────────────────────────
    "report_job_status": [
        r"echo.*this\s+job.*status\b",
        # emoji variant: echo "🍏 This job's status is ..."
        r"echo.*job.{0,10}status\s+is\b",
        r"report\s+job\s+status\b",
    ],

    # ── report_failure_information ────────────────────────────────────────
    "report_failure_information": [
        r"failure\s+display\s+(?:selected|default)\s+compiler\b",
        r"failure\s+display\s+env\b",
        r"report\s+failure\s+information\b",
    ],

    # ── display_compiler_information ──────────────────────────────────────
    "display_compiler_information": [
        r"display\s+compiler\s+details?\b",
        r"display\s+compiler\s+information\b",
    ],

    # ── display_system_information ────────────────────────────────────────
    "display_system_information": [
        r"display\s+cpu\s+details?\b",
        r"display\s+system\s+information\b",
    ],

    # ── display_help_information ──────────────────────────────────────────
    "display_help_information": [
        r"^run\s+help\b",
        r"display\s+help\s+information\b",
    ],

    # ── send_notification ─────────────────────────────────────────────────
    "send_notification": [
        r"notify\s+discord",
        r"send\s+(?:custom\s+)?message",
        r"notify\s+slack\s+on\s+build\s+failure",
        r"create\s+or\s+update\s+issue\s+card",
        r"create\s+or\s+update\s+pull\s+request\s+card",
        r"update\s+project\s+card",
        r"commit\s+and\s+push\s+results?",
        r"crawl\s+steam\s+discount",
    ],

    # ── notify_configuration_change ───────────────────────────────────────
    "notify_configuration_change": [
        r"comment\s+if\s+\.github\s+changed\b",
        r"comment\s+if\s+(?:license_policy|repolinter|sonar-project).*changed\b",
        # generic: "comment if <anything> changed"
        r"comment\s+if\s+\S+.*changed\b",
        r"notify\s+configuration\s+change\b",
    ],

    # ── generate_changelog ────────────────────────────────────────────────
    "generate_changelog": [
        r"generate\s+(?:a\s+)?changelog",
        r"create\s+changelog",
        r"update\s+changelog",
        r"./hack/changelog\.sh\b",
    ],

    # ── determine_release_status ──────────────────────────────────────────
    "determine_release_status": [
        r"is_release\b",
        r"check\s+(?:if\s+)?release",
        r"determine\s+release",
        r"tag\s*=\s*\$\{\{\s*github\.event\.release",
    ],

    # ── manage_labels ─────────────────────────────────────────────────────
    "manage_labels": [
        r"run\s+labeler",
        r"android.*label",
        r"backend.*label",
        r"all.*label",
        r"\bgh.*add.*label\b",
        r"\badd-label\b",
        r"\blabel\b.*pr",
        r"^copy-labels\b",
    ],

    # ── manage_workflow_automation ────────────────────────────────────────
    "manage_workflow_automation": [
        r"enable\s+auto-merge\s+for\s+dependabot",
        r"assign\s+(?:new\s+)?issues?\s+and",
        r"generate\s+versions?\b",
        r"create\s+pull\s+request\b",
        r"set\s+pr_title\s+outputs?",
    ],

    # ── clean_project_artifacts ───────────────────────────────────────────
    "clean_project_artifacts": [
        r"remove\s+dockerfile",
        r"revoke\s+runner\s+ip",
        r"clean\s+up\s+docker\s+space",
        r"remove\s+old\s+data\b",
        r"remove\s+(?:pr\s+)?container\s+image",
        r"removes\s+all\s+generated\s+code",
        r"remove\s+lucee\s+build\s+artifacts?",
        r"clean\s+up\s+docker",
        r"clean-up\s+working\s+directory",
        r"delete\s+clockwork",
        r"delete\s+(?:liquibase|dry-run)\s+tag",
        r"delete\s+the\s+dry-run\s+draft\s+release",
        r"register\s+clean\b",
        r"sequence\s+tests?\s+clean\b",
        r"execute\s+clean\s+script",
        r"clean\s+script",
        # conditional expression used as step name: ${{ contains(needs.*.result,'failure') && ...
        r"contains\(needs\.\*\.result.*failure\b",
        r"\$\{\{.*contains.*needs.*result.*failure",
    ],

    # ── trigger_external_upload_workflow ──────────────────────────────────
    "trigger_external_upload_workflow": [
        # "MirrorChyanUploading" lowercases to one word without spaces
        r"trigger\s+mirrorchyanuploading\b",
        r"trigger\s+mirrorchyan\s+uploading\b",
        r"trigger\s+external\s+upload\s+workflow\b",
    ],

    # ── skip_workflow ─────────────────────────────────────────────────────
    "skip_workflow": [
        r"^exit\s+0\b",
        r"skip\s+workflow\b",
    ],

    # ── prepare_build_environment ─────────────────────────────────────────
    # Distinct from setup_build_environment; covers local composite prep actions
    "prepare_build_environment": [
        r"prepare\s+build\s+environment\b",
        r"prepare\s+buildozer\b",
        r"prepare_buildozer\b",
    ],

    # ── configure_system_timezone ─────────────────────────────────────────
    "configure_system_timezone": [
        r"set.?timezone\b",
        r"configure\s+system\s+timezone\b",
    ],

    # ── validate_release_consistency ──────────────────────────────────────
    "validate_release_consistency": [
        r"check.?release.?match\b",
        r"validate\s+release\s+consistency\b",
    ],

    # ── rename_build_artifact ─────────────────────────────────────────────
    "rename_build_artifact": [
        r"rename.*dll\b",
        r"rename\s+build\s+artifact\b",
    ],

    # ── rename_artifact ───────────────────────────────────────────────────
    "rename_artifact": [
        r"rename\s+(?:user\s+)?jar\s+to\s+app\b",
        r"rename\s+tool\b",
        r"rename\s+artifact\b",
    ],

    # ── read_artifact_metadata ────────────────────────────────────────────
    "read_artifact_metadata": [
        r"cat\s+.*steps\.filename\b",
        r"read\s+artifact\s+metadata\b",
    ],

    # ── adjust_file_permissions ───────────────────────────────────────────
    "adjust_file_permissions": [
        r"chmod.*file\s+ops\b",
        r"adjust\s+file\s+permissions?\b",
    ],

    # ── transfer_container_artifacts ──────────────────────────────────────
    "transfer_container_artifacts": [
        r"^docker\s+cp\b",
        r"transfer\s+container\s+artifacts?\b",
    ],

    # ── define_helper_function ────────────────────────────────────────────
    "define_helper_function": [
        r"define\s+show_file_content\s+function\b",
        r"define\s+helper\s+function\b",
    ],

    # ── define_target_platform ────────────────────────────────────────────
    "define_target_platform": [
        r"add\s+macos\s+target\b",
        r"define\s+target\s+platform\b",
    ],

    # ── define_target_platforms ───────────────────────────────────────────
    "define_target_platforms": [
        r'platforms\s*=\s*"\{\}"',
        r'platforms\s*=\s*\{\}',
        r"define\s+target\s+platforms?\b",
    ],

    # ── split_artifacts ───────────────────────────────────────────────────
    "split_artifacts": [
        r"jungwinter/split\b",
        r"split\s+artifacts?\b",
    ],

    # ── inject_cache_into_container ───────────────────────────────────────
    "inject_cache_into_container": [
        r"inject\s+cache\s+into\s+docker\b",
        r"inject\s+cache\s+into\s+container\b",
    ],

    # ── archive_tool_cache ────────────────────────────────────────────────
    "archive_tool_cache": [
        r"core\s+dump.*archive\s+tool\s+cache\b",
        r"archive\s+tool\s+cache\b",
    ],

    # ── transform_domain_data ─────────────────────────────────────────────
    "transform_domain_data": [
        r"convert\s+(?:air|lidryer)\s+mechanism\b",
        r"transform\s+domain\s+data\b",
    ],

    # ── process_configuration ─────────────────────────────────────────────
    "process_configuration": [
        r"run\s+ipv6\s+config\s+filter\s+script\b",
        r"process\s+configuration\b",
    ],

    # ── process_support_package ───────────────────────────────────────────
    "process_support_package": [
        r"processing\s+support\s+package\b",
        r"process\s+support\s+package\b",
    ],

    # ── terminate_session ─────────────────────────────────────────────────
    "terminate_session": [
        r"logout\s+hub-tool\b",
        r"terminate\s+session\b",
    ],

    # ── update_repository ─────────────────────────────────────────────────
    "update_repository": [
        r"update\s+xmake\s+repository\b",
        r"update\s+repository\b",
    ],

    # ── update_external_service ───────────────────────────────────────────
    "update_external_service": [
        r"mongodb\s+update\s+bing\b",
        r"update\s+external\s+service\b",
    ],

    # ── start_services ────────────────────────────────────────────────────
    "start_services": [
        r"start\s+services?\b",
        r"bring\s+up\s+containers?",
        r"start\s+udmis\s+container",
        r"start\s+test\s+db",
    ],

    # ── stop_services ─────────────────────────────────────────────────────
    "stop_services": [
        r"stop\s+services?\b",
        r"docker-compose\s+down",
        r"stop\s+(?:instances|containers?)\b",
    ],

    # ── provision_runner ──────────────────────────────────────────────────
    "provision_runner": [
        r"start\s+(?:aws\s+)?runner",
        r"create\s+cloud\s+runner",
        r"provision\s+runner",
    ],

    # ── decommission_runner ───────────────────────────────────────────────
    "decommission_runner": [
        r"stop\s+(?:aws\s+)?runner",
        r"stop\s+instances?\b",
        r"decommission\s+runner",
    ],

    # ── manage_build_cache ─────────────────────────────────────────────────
    "manage_build_cache": [
        r"save\s+time\s+for\s+cache",
        r"restore\s+(?:cached|cache)\b",
        r"cache\s+(?:docker|pip|npm|maven|bazel|pip)\b",
        r"scons.*cache",
        r"^ccache\b",
    ],

    # ── orchestrate_workflow ───────────────────────────────────────────────
    "orchestrate_workflow": [
        r"report-failure",
        r"report-success",
        r"do\s+something\s+so\s+that\s+gha",
        r"decide\s+short-circuit",
        r"cancel\s+previous\s+runs?",
    ],

    # ── log_information ───────────────────────────────────────────────────
    "log_information": [
        r"save\s+logs?",
        r"print\s+logs?",
        r"dump\s+threads?",
        r"capture\s+(?:messages?|logs?)",
    ],
}


# =========================
# LANGUAGE-SPECIFIC PATTERNS
# =========================
LANGUAGE_PATTERNS = {
    "python": {
        "inspect_environment": [
            r"pip install.*twine",
            r"install.*twine\b",
        ],
        "generate_test_coverage": [
            r"\bcoverage run\b", r"\bcoverage report\b",
            r"\bcoverage xml\b", r"\bcoverage html\b",
            r"pytest.*--cov\b", r"\bpytest-cov\b",
            r"\bcoverage-badge\b",
            r"\bcodecov\b", r"\bcoveralls\b",
            r"upload.*coverage", r"coverage.*upload",
        ],
        "download_build_artifacts": [r"actions/download-artifact"],
        "install_project_dependencies": [
            r"pip install", r"pip3 install", r"poetry install",
            r"conda install", r"pip install -r", r"pipenv install",
            r"source.*activate", r"\..*activate\b", r"activate.*venv",
        ],
        "execute_tests": [
            r"\bpytest\b", r"\bunittest\b", r"\btox\b", r"\bnose2?\b",
            r"python -m pytest", r"python -m unittest",
            r"\bbehave\b",
            r"\bmpirun\b.*pytest", r"\bmpiexec\b.*pytest",
        ],
        "build_package": [
            r"setup\.py build", r"python -m build", r"pyproject",
            r"wheel", r"flit build", r"hatch build",
        ],
        "static_analysis": [
            r"\bflake8\b", r"\bpylint\b", r"\bblack\b",
            r"\bisort\b", r"\bmypy\b", r"\bbandit\b",
            r"\bruff\b", r"\bpycodestyle\b", r"\bautoflake\b",
            r"\bpytype\b", r"\bpyink\b", r"\bflynt\b",
            r"\bpyupgrade\b", r"\bcodespell\b",
            r"\bformat\b",
        ],
        "publish_package": [r"twine upload", r"poetry publish", r"flit publish"],
    },

    "java": {
        "install_project_dependencies": [
            r"mvn install", r"gradle dependencies", r"mvn dependency",
            r"gradle --refresh-dependencies",
        ],
        "execute_tests": [
            r"\bmvn test\b", r"gradle.* test", r"gradlew.* test",
            r"mvn verify", r"gradle.* check", r"gradlew.* check",
            r"mvn surefire", r"junit",
        ],
        "build_project": [
            r"mvn package", r"mvn compile", r"gradle build",
            r"gradle assemble", r"gradle jar", r"mvn clean install",
            r"\bgradlew?\b.*build", r"gradle.*build",
        ],
        "static_analysis": [
            r"checkstyle", r"spotbugs", r"pmd\b", r"spotless",
            r"errorprone", r"google-java-format",
        ],
        "publish_package": [
            r"mvn deploy", r"gradle publish", r"gradle uploadArchives",
            r"nexus", r"artifactory",
        ],
    },

    "c++": {
        "install_project_dependencies": [
            r"apt-get install", r"apt install", r"vcpkg install",
            r"brew install", r"conan install", r"dnf install", r"yum install",
        ],
        "execute_tests": [
            r"\bctest\b", r"make test", r"ninja test", r"googletest",
            r"gtest", r"catch2", r"boost.*test",
        ],
        "setup_build_environment": [
            r"cmake -[BS]", r"cmake -G",
            r"cmake --preset (?!.*build|.*release|.*conan-r)",
            r"\bconfigure\b.*cmake", r"cmake.*configure",
            r"^cmake\s+\.{1,2}$", r"^cmake\s+\.{1,2}\s",
        ],
        "compile_source_code": [
            r"\bcmake\b", r"\bmake\b", r"\bninja\b", r"\bg\+\+\b",
            r"\bclang\+\+\b", r"meson build", r"bazel build",
            r"cmake --build", r"make -j",
        ],
        "static_analysis": [
            r"clang-format", r"clang-tidy", r"cppcheck",
            r"cpplint", r"iwyu", r"include-what-you-use",
        ],
        "publish_release_assets": [
            r"cmake --install", r"make install", r"cpack", r"conan upload",
        ],
    },

    "julia": {
        "inspect_environment": [
            r"versioninfo", r"binaryplatforms", r"hostplatform",
            r"interactiveutils", r"base\.",
        ],
        "inspect_platform_architecture": [
            r"binaryplatforms.*hostplatform\b",
            r"@show\s+base\.binaryplatforms\.hostplatform\b",
        ],
        "execute_tests": [
            r"pkg\.test", r"\bjulia\b.*test", r"using test",
            r"julia.*runtests",
        ],
        "build_project": [
            r"packagecompiler", r"pkg\.build", r"\bjulia\b.*build",
            r"julia.*compile", r"make\.jl",
        ],
        "install_project_dependencies": [
            r"pkg\.add", r"pkg\.instantiate", r"pkg\.resolve",
            r"install.*julia", r"\bjulia\b.*pkg",
        ],
        "deploy_documentation": [
            r"julia.*register", r"localregistry", r"registrator",
            r"docs/make\.jl",
            r"\bdeploydocs\b",
            r"documenter",
        ],
    },
}


# =========================
# GENERIC PATTERNS
# =========================
GENERIC_PATTERNS = {

    # ── static_analysis ───────────────────────────────────────────────────────
    "static_analysis": [
        r"\bsnyk\b", r"\btrivy\b", r"\bgrype\b",
        r"\bpre-commit\b", r"\bpre_commit\b",
        r"\bsuper-linter\b", r"\bsuperlinter\b",
        r"\bsonarscanner\b", r"\bsonar-scanner\b",
        r"\bcodeclimate\b", r"\bsemgrep\b", r"\bdeepsource\b",
        r"\blint\b", r"\bformat\b", r"\bstyle\b",
        r"\bautoflake\b", r"\bflynt\b", r"\bpyupgrade\b",
        r"\bcodespell\b", r"\bisort\b",
        r"grep -rn.*&&.*exit 1",
        r"\bclang-format\b.*--dry-run",
        r"\bcommitlint\b",
        r"\bpytype\b", r"\bpyink\b", r"\bmypy\b", r"\bruff\b",
        r"find.*\.py.*xargs.*lint",
        r"xargs.*pylint",
        r"\bcodeql\b",
        r"\bshowstopper\b",
        r"no.?tab\b", r"no.*trailing.?whitespace",
        r"\bfind\b.*-name.*\.py",
        r"\bpylint\b", r"\bflake8\b",
        r"\bblack\b.*--check",
        r"\bclang-format\b",
        r"\bqa\b.*check", r"\bqa\s+check",
        r"run.*format.*check",
        r"run.*isort.*check",
    ],

    # ── publish_test_results ──────────────────────────────────────────────────
    "publish_test_results": [
        r"publish.*test.*result", r"publish.*unit.*test",
        r"\bjunit.*report\b", r"\ballure.*report\b",
        r"\bdangerjs\b",
    ],

    # ── generate_test_coverage ────────────────────────────────────────────────
    "generate_test_coverage": [
        r"\bcodecov\b", r"\bcoveralls\b",
        r"upload.*coverage", r"coverage.*upload",
        r"\bcoverage run\b", r"\bcoverage report\b",
        r"\bcoverage xml\b", r"\bcoverage html\b",
        r"\bpytest.*--cov\b", r"\bcov.*report\b",
        r"\bjacoco\b", r"\blcov\b", r"\bgenhtml\b",
        r"coverage.*badge",
        r"\bcoverage-badge\b",
    ],

    # ── upload_build_artifacts ────────────────────────────────────────────────
    "upload_build_artifacts": [
        r"\bsonar\b.*upload", r"sonarcloud",
        r"upload.*report", r"submit.*coverage",
        r"\btar (c|r)f\b", r"\bzip -r\b",
        r"gh release (upload|create)",
        r"git.*add.*&&.*git commit.*&&.*git push",
        r"git push.*data",
        r"s3.*sync", r"aws s3 cp",
        r"\bdocker push\b",
        r"\bmerge.*artifact\b", r"\bartifact.*merge\b",
        r"store.*distribution",
        r"actions/upload-artifact",
        r"\bupload.*build.*artifact\b",
        r"uploading.*artifact",
        r"\besp\d+.*build\b",
        r"\barchive.*firmware\b",
        r"\barchive.*(?:merged|binary)\b",
        r"push.*binary.*data",
        r"push.*data.*branch",
    ],

    # ── download_build_artifacts ──────────────────────────────────────────────
    "download_build_artifacts": [
        r"gh release download",
        r"\bwget\b.*artifact",
        r"\bcurl\b.*artifact",
        r"\bdownload.*_data\b",
        r"\bdownload.*cross.?platform\b",
    ],

    # ── download_external_resources ───────────────────────────────────────────
    "download_external_resources": [
        r"\bwget\b.*http(?!.*artifact)",
        r"\bcurl\b.*-[Oo].*http(?!.*artifact)",
        r"\bfreshclam\b",
    ],

    # ── inspect_environment ───────────────────────────────────────────────────
    "inspect_environment": [
        r"--version$", r"\s--version\b",
        r"\bprintenv\b",
        r"python -c.*(?:version|platform|sqlite)",
        r"\bjstack\b", r"\bjps\b",
        r"\bpip\s+freeze\b", r"\bpip\s+list\b",
        r"display.*python.*version",
        r"display.*sqlite",
        r"\bplatforms.*=.*{}\b",
        r"--dump-config",
        r"^ls\b", r"^cat\s+[a-z\$]",
    ],

    # ── inspect_platform_architecture ─────────────────────────────────────────
    "inspect_platform_architecture": [
        r"julia.*binaryplatforms.*hostplatform\b",
    ],

    # ── extract_version_metadata ──────────────────────────────────────────────
    "extract_version_metadata": [
        r"\bgit describe\b",
        r"\bsha256sum\b", r"\bmd5sum\b",
        r"echo.*set-output",
        r"get.*commit.*message",
        r"\breplace.*version\b",
        r"\btagging\b.*version",
        r"git tag\b",
        r"update.*version.*file",
        r"read.*changelog",
        r"\bdocker.*metadata\b", r"\bextract.*metadata\b",
    ],

    # ── extract_dependency_metadata ───────────────────────────────────────────
    "extract_dependency_metadata": [
        r"\bdependabot\b.*metadata",
    ],

    # ── export_environment_configuration ──────────────────────────────────────
    "export_environment_configuration": [
        r"echo.*>>.*github_env",
        r"echo.*>>.*.env",
        r"set.*output.*status",
        r"update.*changelog",
    ],

    # ── configure_secrets ─────────────────────────────────────────────────────
    "configure_secrets": [
        r"inject.*key(?:store)?",
        r"setup.*keystore",
        r"git.*credential",
        r"git config.*credential",
    ],

    # ── configure_cloud_resources ─────────────────────────────────────────────
    "configure_cloud_resources": [
        r"configure.*aws.*credentials",
        r"\bgh auth\b",
        r"\bgcloud auth\b",
        r"\blogin.*registry\b", r"\blog.*in.*registry\b",
        r"docker.*login",
        r"create.*bing.*auth", r"bing.*authentif",
    ],

    # ── log_information ───────────────────────────────────────────────────────
    "log_information": [
        r"summariz.*fail", r"reportfailed",
        r"dump.*thread",
    ],

    # ── setup_build_environment ───────────────────────────────────────────────
    "setup_build_environment": [
        r"cmake\s+-[bBsS](?!.*build)", r"cmake.*-[gG]\s",
        r"cmake\b.*\s-[bBsS](?!.*build)",
        r"^cmake\s+\.+",
        r"add.*msbuild.*path", r"msbuild.*path",
        r"\bchmod\b.*\+x",
        r"\bccache\b",
        r"\bfortran\b.*compil", r"setup.*fortran",
        r"\bodbc\b",
        r"\brust.*toolchain\b", r"rustup.*toolchain",
    ],

    # ── setup_package_manager ─────────────────────────────────────────────────
    "setup_package_manager": [
        r"\bconan.*profile.*detect\b",
        r"\bdetect.*profile\b",
        r"conan.*install",
    ],

    # ── configure_build_profile ───────────────────────────────────────────────
    "configure_build_profile": [
        r"configure.*bazel", r"bazel.*configure",
        r"mkdir.*build", r"make.*build.*dir",
        r"pre.?build.*action", r"prebuild.*action",
        r"pre.?build.*step",
        r"set[\s\-]?up.*stack",
        r"generate.*collection",
        r"prepare.*buildozer", r"buildozer.*prepare",
        r"source.*profile",
        r"prepare.*action",
        r"git.*config.*autocrlf",
        r"fetch.*unshallow", r"git fetch.*unshallow",
        r"git fetch.*tags",
        r"\btouch\b",
        r"\btest -[fde]\b",
        r"\bsed -i\b",
        r"\bmkdir -p\b",
        r"source.*venv.*activate", r"\..*venv.*activate",
        r"\bapt-get upgrade\b",
        r"\btimedatectl\b",
        r"readthedocs",
    ],

    # ── setup_runtime_environment ─────────────────────────────────────────────
    "setup_runtime_environment": [
        r"\bapt-get update\b", r"\bapt update\b",
        r"update.*package.*database",
    ],

    # ── setup_network_connectivity ────────────────────────────────────────────
    "setup_network_connectivity": [
        r"\btailscale\b",
    ],

    # ── install_project_dependencies ──────────────────────────────────────────
    "install_project_dependencies": [
        r"\bnpm (ci|install)\b", r"\byarn( install)?\b", r"\bpnpm install\b",
        r"\bbundle install\b", r"\bgo get\b",
        r"\bapt-get install\b", r"\bapt install\b",
        r"\bbrew install\b",
        r"\bpacman -[SU]\b",
        r"\bdnf install\b", r"\byum install\b",
        r"\bchoco install\b", r"\bscoop install\b",
        r"\bvcpkg install\b",
        r"\badd-apt-repository\b",
        r"astral\.sh/uv", r"\buv pip install\b", r"\buv install\b",
        r"install\.python-poetry\.org",
        r"\bpipx install\b",
        r"\bpdm\b.*install",
        r"sh\.rustup\.rs", r"\brustup-init\b",
        r"\bemsdk\b",
        r"\bcargo install\b", r"\bgem install\b",
        r"\bcomposer install\b", r"\bconan install\b",
        r"source.*activate", r"\..*activate\b", r"activate.*venv",
        r"install.*\bninja\b", r"\bninja\b.*install",
        r"install.*\bmake\b",
        r"\bsphinx\b.*install", r"install.*\bsphinx\b",
        r"appcenter.*cli", r"install.*appcenter",
        r"pip3?\s+install\s+requests",
        r"\bgfortran\b", r"\bifort\b",
        r"install.*python.*package",
        r"install.*dev.*req",
        r"install.*test.*data",
        r"\bpy4dgeo\b",
        r"enable.*esp.*platform",
        r"install.*platformio", r"pip.*platformio",
    ],

    # ── install_system_dependencies ───────────────────────────────────────────
    "install_system_dependencies": [
        r"\brosdep\b.*install",
    ],

    # ── checkout_repository ───────────────────────────────────────────────────
    "checkout_repository": [
        r"\bgit clone\b", r"\bgit fetch\b(?!.*unshallow)",
        r"\bgit submodule\b",
    ],

    # ── switch_git_reference ──────────────────────────────────────────────────
    "switch_git_reference": [
        r"git\s+checkout\s+head\^2\b",
    ],

    # ── build_container_image ─────────────────────────────────────────────────
    "build_container_image": [
        r"\bdocker build\b", r"\bdocker-compose build\b",
        r"\bdocker run\b",
    ],

    # ── build_documentation ───────────────────────────────────────────────────
    "build_documentation": [
        r"\bjupyter.?book\b", r"\bjb\s+build\b",
        r"jupyter-book.*build",
        r"make.*doc", r"\bsphinxbuild\b",
        r"sphinx.*build",
        r"mkdocs.*build",
    ],

    # ── build_static_site ─────────────────────────────────────────────────────
    "build_static_site": [
        r"jekyll.*build",
        r"bundle\s+exec\s+jekyll",
    ],

    # ── build_package ─────────────────────────────────────────────────────────
    "build_package": [
        r"\bgradlew?\b.*build", r"gradle.*build",
        r"gradlew\s+assemble",
        r"gradlew.*androidtest",
    ],

    # ── compile_source_code ───────────────────────────────────────────────────
    "compile_source_code": [
        r"\bemcc\b",
        r"\bg\+\+\b", r"\bclang\+\+\b",
        r"meson build",
        r"\bjava -jar\b.*bnd",
    ],

    # ── build_application ─────────────────────────────────────────────────────
    "build_application": [
        r"\bplatformio\b", r"\bpio\s+run\b",
        r"\bbuildozer\b",
        r"configure.*build.*cmake",
        r"cmake.*configure.*build",
    ],

    # ── deploy_infrastructure ─────────────────────────────────────────────────
    "deploy_infrastructure": [
        r"\bpulumi\b.*up\b",
        r"\bpulumiup\b",
    ],

    # ── destroy_infrastructure ────────────────────────────────────────────────
    "destroy_infrastructure": [
        r"\bpulumi\b.*down\b",
        r"\bpulumidown\b",
    ],

    # ── build_project ─────────────────────────────────────────────────────────
    "build_project": [
        r"\bbuild\b", r"\bcompile\b", r"\bassemble\b",
        r"\bcmake\b", r"\bmake\b", r"\bninja\b",
        r"\bcmake --build\b",
        r"\bbazel build\b",
        r"\bgenerat.*example\b",
        r"example.*build", r"\bbuild.*example\b",
        r"\bprepare.*artifact\b",
    ],

    # ── execute_tests ─────────────────────────────────────────────────────────
    "execute_tests": [
        r"python -m tox", r"^tox\b", r"^python.*tox\b",
        r"\btest\b", r"\btesting\b", r"\bspec\b",
        r"\bmake check\b",
        r"python -m doctest", r"\bdoctest\b",
        r"\bbehave\b", r"\btox\b",
        r"\bmpirun\b", r"\bmpiexec\b",
        r"\bbazel test\b", r"bazel.*//",
        r"curl.*localhost.*\d+/",
        r"\bnotebook\b.*exec", r"nbconvert.*execute",
        r"jupyter.*execute",
        r"browserstack",
        r"\bruntest\b",
        r"\btest[-_]\w",
        r"make.*request.*endpoint",
        r"request.*endpoint",
        r"run\s+tests?\b",
        r"run.*samples.*test",
        r"\bintegration\s+test",
        r"\bunit\s+and\s+integration",
        r"\bunit\s+test",
        r"\bworkspace.*integr",
        r"\bexample.*integr",
        r"\baspect.*integr",
        r"applying.*fix", r"apply.*fix",
    ],

    # ── deploy_documentation ──────────────────────────────────────────────────
    "deploy_documentation": [
        r"\bsphinx.*deploy\b", r"deploy.*sphinx",
        r"push.*gh.?pages",
        r"mkdocs.*deploy",
    ],

    # ── deploy_application ────────────────────────────────────────────────────
    "deploy_application": [
        r"\bheroku\b", r"\bkubectl\b", r"\bterraform\b",
        r"\bansible\b", r"\bcapistrano\b",
        r"\baws.*deploy\b", r"\beb deploy\b",
        r"\bfly deploy\b", r"\brailway\b",
        r"\bdocker-compose up\b",
    ],

    # ── publish_package ───────────────────────────────────────────────────────
    "publish_package": [
        r"\bnpm publish\b",
        r"\btwine upload\b",
        r"semantic.*release",
        r"\bpublish\b",
        r"\bmodrinth\b", r"\bcurseforge\b",
    ],

    # ── publish_release ───────────────────────────────────────────────────────
    "publish_release": [
        r"gh release create",
        r"^git\s+push\b",
        r"\bpush.*changes\b",
    ],

    # ── publish_release_assets ────────────────────────────────────────────────
    "publish_release_assets": [
        r"upload.*pypi", r"pypi.*upload",
        r"coveralls.*finish",
        r"create.*release.*(?:upload|firmware)",
        r"update.*gist", r"\bgist\b",
    ],

    # ── manage_build_cache ────────────────────────────────────────────────────
    "manage_build_cache": [
        r"\bcache.*hit\b", r"\brestore.*cache\b",
        r"\bsave.*cache\b", r"scons.*cache",
        r"cache.*docker", r"docker.*cache",
        r"\bcache\b.*image",
        r"\bpip.*cache\b",
    ],

    # ── send_notification ─────────────────────────────────────────────────────
    "send_notification": [
        r"\bslack\b", r"\bteams\b", r"\bemail\b", r"\bnotif",
        r"\bcurl\b.*slack", r"\bcurl\b.*webhook",
        r"close.*stale", r"stale.*issue",
        r"create.*issue.*card", r"update.*issue.*card",
        r"create.*pull.*request.*card",
        r"update.*project.*card",
    ],

    # ── run_security_analysis ─────────────────────────────────────────────────
    "run_security_analysis": [
        r"\bbandit\b",
    ],

    # ── perform_security_analysis ─────────────────────────────────────────────
    "perform_security_analysis": [
        r"\bsast\b",
        r"\bscan\b.*vuln", r"\bossf\b",
        r"\bowasp\b", r"\bgrype\b", r"\bsyft\b",
        r"dependabot.*scan", r"dependabot.*alert",
    ],

    # ── manage_workflow_automation ────────────────────────────────────────────
    "manage_workflow_automation": [
        r"\brelease-please\b", r"\bauto-merge\b",
        r"\bdependabot\b",
        r"enable.*auto-merge", r"approve.*pr",
        r"\bgh pr\b",
        r"assign.*issue", r"assign.*reviewer",
        r"\bcopy-labels\b",
    ],

    # ── manage_labels ─────────────────────────────────────────────────────────
    "manage_labels": [
        r"android.*label", r"backend.*label", r"all.*label",
        r"\bgh.*add.*label\b", r"\badd-label\b",
    ],

    # ── verify_build_integrity ────────────────────────────────────────────────
    "verify_build_integrity": [
        r"python -c.*assert", r"\bassert\b",
        r"\bverify\b", r"\bvalidate\b",
        r"compare.*output", r"check.*checksum",
        r"diff.*output", r"check.*for.*output",
        r"check.*if.*branch", r"check.*pr.*title",
        r"check.*matrix", r"check.*engine",
        r"check.*fork", r"\bchange.*detect\b",
        r"look.*for.*change", r"fail.*if.*change",
        r"\bsanity.*check\b", r"check.*exception",
    ],

    # ── clean_project_artifacts ───────────────────────────────────────────────
    "clean_project_artifacts": [
        r"\bdocker.*prune\b", r"\bdocker system\b",
        r"\bclean.*docker\b", r"\bdocker.*clean\b",
        r"gh release delete",
        r"\bgh.*delete\b",
        r"delete.*old.*nightly", r"\buninstall\b",
        r"\bclean.*workspace\b", r"clean-up.*working",
        r"remove.*old.*data", r"\bstop.*service\b",
        r"\bteardown\b", r"revoke.*runner.*ip",
        r"\bdelete.*tag\b", r"\bdelete.*draft\b",
        r"remove.*artifacts",
        r"^rm -rf\b", r"^rm -f\b",
        r"execute.*clean.*script",
        r"\bdelete.*_data\b", r"rm\s+.*_data",
        r"delete.*workflow.*run",
    ],

    # ── start_services ────────────────────────────────────────────────────────
    "start_services": [
        r"\bdocker-compose up\b",
    ],

    # ── stop_services ─────────────────────────────────────────────────────────
    "stop_services": [
        r"stop.*instances",
        r"\bdocker-compose down\b",
    ],

    # ── orchestrate_workflow ──────────────────────────────────────────────────
    "orchestrate_workflow": [
        r"\bcancel.*previous\b", r"cancel.*previous.*run",
        r"\btrigger.*workflow\b",
        r"trigger.*push.*data",
        r"decide.*short-circuit",
        r"report-failure", r"report-success",
        r"\breport.*failure\b", r"\breport.*success\b",
    ],

    # ── generate_changelog ────────────────────────────────────────────────────
    "generate_changelog": [
        r"hack/changelog\.sh\b",
    ],

    # ── notify_configuration_change ───────────────────────────────────────────
    "notify_configuration_change": [
        r"comment.*if.*changed\b",
    ],
}


# =========================
# KNOWN ACTIONS TABLE
# =========================
KNOWN_ACTIONS = {

    # ── Universal ─────────────────────────────────────────────────────────────
    "actions/checkout":                      "checkout_repository",
    "actions/cache":                         "manage_build_cache",
    "actions/upload-artifact":               "upload_build_artifacts",
    "actions/download-artifact":             "download_build_artifacts",
    "actions/create-release":                "publish_release",
    "actions/github-script":                 "execute_automation_script",
    "actions/labeler":                       "manage_labels",
    "actions/upload-pages-artifact":         "upload_build_artifacts",
    "actions/deploy-pages":                  "deploy_documentation",
    "actions/configure-pages":               "configure_build_profile",

    # ── Language runtimes ─────────────────────────────────────────────────────
    "actions/setup-python":                  "setup_runtime_environment",
    "actions/setup-java":                    "setup_runtime_environment",
    "actions/setup-node":                    "setup_runtime_environment",
    "actions/setup-go":                      "setup_runtime_environment",
    "actions/setup-dotnet":                  "setup_runtime_environment",
    "actions/setup-ruby":                    "setup_runtime_environment",

    # ── Build toolchain ───────────────────────────────────────────────────────
    "step-security/harden-runner":           "setup_build_environment",
    "jwlawson/actions-setup-cmake":          "setup_build_environment",
    "seanmiddleditch/gha-setup-ninja":       "setup_build_environment",
    "kylemayers/install-llvm-action":        "setup_build_environment",
    "ilammy/msvc-dev-cmd":                   "setup_build_environment",
    "egor-tensin/setup-mingw":               "setup_build_environment",
    "egor-tensin/setup-gcc":                 "setup_build_environment",
    "microsoft/setup-msbuild":               "setup_build_environment",
    "docker/setup-buildx-action":            "setup_build_environment",
    "docker/setup-qemu-action":              "setup_build_environment",
    "sigstore/cosign-installer":             "setup_build_environment",
    "hondro/gtest-installer":                "setup_build_environment",
    "lukka/get-cmake":                       "setup_build_environment",
    "mymindstorm/setup-emsdk":               "setup_build_environment",
    "browser-actions/setup-chrome":          "setup_runtime_environment",
    "nttld/setup-ndk":                       "setup_build_environment",

    # ── Package managers ──────────────────────────────────────────────────────
    "lukka/run-vcpkg":                       "setup_package_manager",
    "aminya/setup-vcpkg":                    "setup_package_manager",
    "seanmiddleditch/vcpkg-action":          "setup_package_manager",

    # ── Build execution ───────────────────────────────────────────────────────
    "lukka/run-cmake":                       "build_project",
    "gradle/gradle-build-action":            "build_project",
    "ralfg/python-wheels-manylinux-build":   "build_python_wheel",
    "calibreapp/image-actions":              "build_project",
    "actions/jekyll-build-pages":            "build_static_site",
    "ansys/actions/build-library":           "build_library",

    # ── Package manager installers ────────────────────────────────────────────
    "snok/install-poetry":                   "install_project_dependencies",
    "abatilo/actions-poetry":                "install_project_dependencies",

    # ── Test execution ────────────────────────────────────────────────────────
    "pytest-dev/pytest-action":              "execute_tests",

    # ── Validation ────────────────────────────────────────────────────────────
    "gradle/wrapper-validation-action":      "verify_build_integrity",

    # ── Static analysis ───────────────────────────────────────────────────────
    "github/super-linter":                   "static_analysis",
    "github/codeql-action/init":             "initialize_security_analysis",
    "github/codeql-action/autobuild":        "build_project",
    "github/codeql-action/analyze":          "perform_security_analysis",
    "github/codeql-action/upload-sarif":     "perform_security_analysis",
    "sonarsource/sonarcloud-github-action":  "perform_security_analysis",

    # ── Security scanning ─────────────────────────────────────────────────────
    "snyk/actions":                          "perform_security_analysis",
    "aquasecurity/trivy-action":             "perform_security_analysis",
    "actions/dependency-review-action":      "perform_security_analysis",

    # ── Coverage & test reporting ─────────────────────────────────────────────
    "codecov/codecov-action":                "generate_test_coverage",
    "coverallsapp/github-action":            "publish_release_assets",

    # ── Timezone ──────────────────────────────────────────────────────────
    "szenius/set-timezone":                  "configure_system_timezone",

    # ── Release validation ────────────────────────────────────────────────
    "jupyter-server/jupyter_releaser/.github/actions/check-release-match": "validate_release_consistency",

    # ── JupyterLab maintainer tools ───────────────────────────────────────────
    "jupyterlab/maintainer-tools/.github/actions/upload-coverage":  "upload_coverage",
    "jupyterlab/maintainer-tools/.github/actions/report-coverage":  "report_coverage",
    "jupyterlab/maintainer-tools/.github/actions/base-setup":       "setup_base_environment",
    "jupyterlab/maintainer-tools/.github/actions/make-sdist":       "setup_base_environment",
    "jupyterlab/maintainer-tools/.github/actions/test-sdist":       "setup_base_environment",
    "jupyterlab/maintainer-tools/.github/actions/check-links":      "run_link_check",

    # ── Release management ────────────────────────────────────────────────────
    "softprops/action-gh-release":           "publish_release",
    "goreleaser/goreleaser-action":          "publish_release",
    "release-drafter/release-drafter":       "publish_release",
    "svenstaro/upload-release-action":       "publish_release_assets",
    "marvinpinto/action-automatic-releases": "publish_release",
    "spring-io/nexus-sync-action":           "publish_package",
    "casperdcl/deploy-pypi":                 "publish_package",
    "pypa/gh-action-pypi-publish":           "publish_package",

    # ── Deployment ────────────────────────────────────────────────────────────
    "google-github-actions/deploy-cloudrun": "deploy_application",
    "hashicorp/terraform-github-actions":    "deploy_application",
    "appleboy/ssh-action":                   "deploy_application",
    "peaceiris/actions-gh-pages":            "deploy_documentation",
    "jamesives/github-pages-deploy-action":  "deploy_documentation",
    "crazy-max/ghaction-github-pages":       "deploy_documentation",
    "sphinx-notes/pages":                    "deploy_documentation",
    "docker/build-push-action":              "publish_release_assets",

    # ── Authentication / cloud ────────────────────────────────────────────────
    "google-github-actions/auth":            "configure_cloud_resources",
    "aws-actions/configure-aws-credentials": "configure_cloud_resources",
    "azure/login":                           "configure_cloud_resources",
    "docker/login-action":                   "configure_cloud_resources",

    # ── Container metadata ────────────────────────────────────────────────────
    "docker/metadata-action":                "extract_version_metadata",

    # ── Infrastructure setup ──────────────────────────────────────────────────
    "hashicorp/setup-terraform":             "setup_build_environment",

    # ── Artifact persistence ──────────────────────────────────────────────────
    "andrew-chen-wang/github-wiki-action":   "upload_build_artifacts",
    "stefanzweifel/git-auto-commit-action":  "upload_build_artifacts",

    # ── Contribution graph ────────────────────────────────────────────────────
    "platane/snk":                           "generate_contribution_graph",

    # ── Split artifacts ───────────────────────────────────────────────────────
    "jungwinter/split":                      "split_artifacts",

    # ── Collaboration / workflow ───────────────────────────────────────────────
    "peter-evans/create-pull-request":       "manage_workflow_automation",
    "slackapi/slack-github-action":          "send_notification",

    # ── Repo management ───────────────────────────────────────────────────────
    "kolpav/purge-artifacts-action":         "clean_project_artifacts",
    "mattraks/delete-workflow-runs":         "clean_project_artifacts",
    "geekyeggo/delete-artifact":             "clean_project_artifacts",
    "actions/stale":                         "manage_workflow_automation",
    "actions/first-interaction":             "manage_workflow_automation",
    "8bitjonny/gh-get-current-pr":           "inspect_environment",
    "cloudposse/github-action-matrix-outputs-read": "inspect_environment",
    "scientific-python/action-towncrier-changelog": "generate_changelog",
}

# =========================
# KNOWN LOCAL ACTIONS
# Specific ./ or .github/actions/ paths that should resolve to a semantic label
# rather than the generic "composite" fallback.
# Keys are matched as substrings of the lowercased uses slug (without @ref).
# =========================
KNOWN_LOCAL_ACTIONS = {
    ".github/actions/prepare_buildozer": "prepare_build_environment",
    "prepare_buildozer":                 "prepare_build_environment",
}


# =========================
# STEP CLASSIFIER
# Priority order:
#   1. Step name  (STEP_NAME_PATTERNS)
#   2. uses: slug (KNOWN_ACTIONS → KNOWN_LOCAL_ACTIONS → keyword fallbacks)
#   3. run: text  (LANGUAGE_PATTERNS then GENERIC_PATTERNS)
#   4. "other"    → replaced by display name in sequence builder
# =========================
def classify_step(step, language=""):
    if not isinstance(step, dict):
        return "other"

    # ── 1. Step name ──────────────────────────────────────────────────────────
    if step.get("name"):
        step_name = str(step["name"]).lower().strip()
        for role, patterns in STEP_NAME_PATTERNS.items():
            for pattern in patterns:
                if re.search(pattern, step_name):
                    return role

    # ── 2. uses: action slug ──────────────────────────────────────────────────
    if "uses" in step:
        uses_raw  = step["uses"]
        uses_slug = uses_raw.split("@")[0].lower().strip()

        # Exact KNOWN_ACTIONS match
        if uses_slug in KNOWN_ACTIONS:
            return KNOWN_ACTIONS[uses_slug]

        # Prefix KNOWN_ACTIONS match
        for known_slug, label in KNOWN_ACTIONS.items():
            if uses_slug.startswith(known_slug):
                return label

        # Local / composite path — check named local actions first
        if uses_slug.startswith("./") or ".github/actions/" in uses_slug:
            for local_slug, label in KNOWN_LOCAL_ACTIONS.items():
                if local_slug in uses_slug:
                    return label
            return "composite"

        # Keyword fallbacks — ordered most-specific first
        if any(k in uses_slug for k in ("pre-commit", "super-linter",
                                         "semgrep", "sonar-scanner")):
            return "static_analysis"
        if any(k in uses_slug for k in ("setup-", "/setup", "install-llvm",
                                         "install-gcc", "install-cmake",
                                         "get-cmake", "get-ninja")):
            return "setup_runtime_environment"
        if any(k in uses_slug for k in ("install-poetry", "install-uv",
                                         "install-pdm", "install-rust")):
            return "install_project_dependencies"
        if "auto-commit" in uses_slug or "github-wiki" in uses_slug:
            return "upload_build_artifacts"
        if "ghaction-github-pages" in uses_slug:
            return "deploy_documentation"
        if any(k in uses_slug for k in ("upload-release", "release-drafter",
                                         "nexus-sync", "deploy-pypi")):
            return "publish_release"
        if any(k in uses_slug for k in ("release", "publish")):
            return "publish_release"
        if any(k in uses_slug for k in ("manylinux-build", "build-wheels",
                                         "cibuildwheel")):
            return "build_python_wheel"
        if "deploy" in uses_slug:
            return "deploy_application"
        if any(k in uses_slug for k in ("test", "spec")):
            return "execute_tests"
        if any(k in uses_slug for k in ("lint", "format", "style")):
            return "static_analysis"
        if any(k in uses_slug for k in ("scan", "security", "vuln", "sast")):
            return "perform_security_analysis"
        if any(k in uses_slug for k in ("notify", "slack", "teams")):
            return "send_notification"
        if any(k in uses_slug for k in ("codecov", "coveralls", "coverall",
                                         "coverage-upload", "upload-coverage")):
            return "generate_test_coverage"
        if "coverage" in uses_slug:
            return "generate_test_coverage"
        if "upload-artifact" in uses_slug:
            return "upload_build_artifacts"
        if "download-artifact" in uses_slug:
            return "download_build_artifacts"

        return "external_action"

    # ── 3. run: command text ──────────────────────────────────────────────────
    if "run" in step:
        cmd = step["run"].lower()
        for role, rules in LANGUAGE_PATTERNS.get(language, {}).items():
            for rule in rules:
                if re.search(rule, cmd):
                    return role
        for role, rules in GENERIC_PATTERNS.items():
            for rule in rules:
                if re.search(rule, cmd):
                    return role

    return "other"


# =========================
# STEP NAME EXTRACTOR
# =========================
def get_step_display_name(step):
    if not isinstance(step, dict):
        return "unknown"
    if step.get("name"):
        return str(step["name"]).strip()
    if "uses" in step:
        return step["uses"].split("@")[0].strip()
    if "run" in step:
        first_line = str(step["run"]).strip().splitlines()[0]
        return first_line[:60] + ("..." if len(first_line) > 60 else "")
    return "unnamed_step"


# =========================
# TOPOLOGICAL SORT
# =========================
def topological_sort(jobs):
    visited = set()
    order   = []

    def visit(job_id, ancestors=None):
        if ancestors is None:
            ancestors = set()
        if job_id in ancestors:
            return
        if job_id in visited:
            return
        ancestors = ancestors | {job_id}
        needs = jobs.get(job_id, {}).get("needs", [])
        if isinstance(needs, str):
            needs = [needs]
        for dep in needs:
            if dep in jobs:
                visit(dep, ancestors)
        visited.add(job_id)
        order.append(job_id)

    for job_id in jobs:
        visit(job_id)
    return order


# =========================
# WORKFLOW-LEVEL MERGED SEQUENCE
#
# Returns:
#   merged_seq  — list of internal snake_case labels (for flag checks)
#   job_seqs_str — job-level detail string
# =========================
def build_workflow_sequence(jobs, language):
    ordered_job_ids = topological_sort(jobs)
    seen_labels     = set()
    merged_seq      = []   # internal labels
    job_seq_parts   = []

    for job_id in ordered_job_ids:
        job   = jobs.get(job_id, {})
        steps = job.get("steps") or []
        if not isinstance(job, dict):
            continue

        exact_names = [get_step_display_name(step) for step in steps]
        job_seq_parts.append(
            f"[{job_id}]: {SEQ_SEP.join(exact_names)}"
            if exact_names else f"[{job_id}]: (empty)"
        )

        roles = []
        for step in steps:
            role = classify_step(step, language)
            # For non-semantic labels use the step's own display name
            effective = (
                get_step_display_name(step)
                if role in USE_DISPLAY_NAME_LABELS
                else role
            )
            if not roles or roles[-1] != effective:
                roles.append(effective)

        for label in roles:
            if label not in seen_labels:
                seen_labels.add(label)
                merged_seq.append(label)

    return merged_seq, JOB_SEP.join(job_seq_parts)


# =========================
# DEPTH CALCULATION
# =========================
def compute_depth(jobs):
    def depth(job_id, visited=None):
        if visited is None:
            visited = set()
        if job_id in visited:
            return 1
        visited.add(job_id)
        needs = jobs.get(job_id, {}).get("needs", [])
        if isinstance(needs, str):
            needs = [needs]
        if not needs:
            return 1
        return 1 + max(depth(dep, visited.copy()) for dep in needs if dep in jobs)
    if not jobs:
        return 0
    return max(depth(j) for j in jobs)


# =========================
# ACTION PINNING
# =========================
SHA_RE    = re.compile(r"@([0-9a-f]{40})$", re.IGNORECASE)
TAG_RE    = re.compile(r"@(v\d[\w.\-]*)$",  re.IGNORECASE)
BRANCH_RE = re.compile(r"@([a-zA-Z][\w.\-/]*)$")

def classify_pin(uses_str):
    ref = uses_str.split("@", 1)
    if len(ref) < 2:
        return "unpinned"
    pin = ref[1].strip()
    if SHA_RE.match("@" + pin):    return "sha"
    if TAG_RE.match("@" + pin):    return "tag"
    if BRANCH_RE.match("@" + pin): return "branch"
    return "unpinned"


# =========================
# TRIGGER / EVENT PARSING
# =========================
def parse_events(workflow):
    raw = workflow.get("on", workflow.get(True, {}))
    if raw is None:
        return {"events": "", "num_events": 0, "has_push": 0,
                "has_pull_request": 0, "has_schedule": 0,
                "has_workflow_dispatch": 0, "schedule_pattern": ""}

    if isinstance(raw, str):    raw = {raw: None}
    elif isinstance(raw, list): raw = {e: None for e in raw}
    elif not isinstance(raw, dict): raw = {}

    event_names = [str(k).lower() for k in raw.keys()]

    schedule_pattern = ""
    if "schedule" in raw and isinstance(raw["schedule"], list):
        crons = [e.get("cron", "") for e in raw["schedule"]
                 if isinstance(e, dict) and "cron" in e]
        schedule_pattern = " | ".join(crons)

    return {
        "events":                ", ".join(sorted(event_names)),
        "num_events":            len(event_names),
        "has_push":              int("push" in event_names),
        "has_pull_request":      int("pull_request" in event_names),
        "has_schedule":          int("schedule" in event_names),
        "has_workflow_dispatch": int("workflow_dispatch" in event_names),
        "schedule_pattern":      schedule_pattern,
    }


# =========================
# CACHE ANALYSIS
# =========================
def parse_cache(all_steps_flat):
    cache_steps = [
        s for s in all_steps_flat
        if isinstance(s, dict)
        and "actions/cache" in s.get("uses", "").lower()
    ]
    cache_keys = [
        str((s.get("with") or {}).get("key", "")).strip()
        for s in cache_steps
        if (s.get("with") or {}).get("key")
    ]
    return {
        "uses_cache":     int(len(cache_steps) > 0),
        "cache_count":    len(cache_steps),
        "num_cache_keys": len(cache_keys),
        "cache_keys":     " | ".join(cache_keys),
    }


# =========================
# MODULARITY ANALYSIS
# =========================
def parse_modularity(jobs, all_steps_flat):
    reusable_count  = 0
    composite_count = 0
    local_count     = 0

    for job in jobs.values():
        if isinstance(job, dict) and "uses" in job:
            uses_val = str(job["uses"])
            if ".github/workflows" in uses_val or "@" in uses_val:
                reusable_count += 1

    for step in all_steps_flat:
        if not isinstance(step, dict) or "uses" not in step:
            continue
        uses_val = step["uses"].lower()
        if uses_val.startswith("./"):
            local_count += 1
        elif ".github/actions" in uses_val:
            composite_count += 1

    return {
        "uses_reusable_workflows":     int(reusable_count > 0),
        "uses_composite_actions":      int(composite_count > 0),
        "uses_local_actions":          int(local_count > 0),
        "reusable_workflow_count":     reusable_count,
        "composite_action_count":      composite_count,
        "local_action_count":          local_count,
        "total_modularity_constructs": reusable_count + composite_count + local_count,
    }


# =========================
# ACTION PINNING METRICS
# =========================
def parse_pinning(all_steps_flat):
    unique_uses = {
        step["uses"].strip()
        for step in all_steps_flat
        if isinstance(step, dict)
        and "uses" in step
        and not step["uses"].strip().startswith("./")
    }

    pin_counts = {"sha": 0, "tag": 0, "branch": 0, "unpinned": 0}
    for uses_str in unique_uses:
        pin_counts[classify_pin(uses_str)] += 1

    total = sum(pin_counts.values())
    pct   = lambda n: round(100 * n / total, 1) if total else 0.0

    return {
        "total_actions":       total,
        "pinned_to_sha":       pin_counts["sha"],
        "pinned_to_tag":       pin_counts["tag"],
        "pinned_to_branch":    pin_counts["branch"],
        "unpinned":            pin_counts["unpinned"],
        "sha_percentage":      pct(pin_counts["sha"]),
        "tag_percentage":      pct(pin_counts["tag"]),
        "branch_percentage":   pct(pin_counts["branch"]),
        "unpinned_percentage": pct(pin_counts["unpinned"]),
    }


# =========================
# PROCESS ONE WORKFLOW
# =========================
def process_workflow(row):
    try:
        workflow = yaml.safe_load(row["full_workflow_yaml"])
        if not isinstance(workflow, dict):
            return None

        jobs = workflow.get("jobs", {})
        if not jobs:
            return None

        language = str(row.get("language", "")).lower().strip()

        # Skip pure reusable workflows
        triggers = workflow.get("on", {})
        if isinstance(triggers, str):    triggers = {triggers: None}
        elif isinstance(triggers, list): triggers = {e: None for e in triggers}
        if isinstance(triggers, dict):
            if [str(k).lower() for k in triggers.keys()] == ["workflow_call"]:
                return None

        # Flatten all steps
        all_steps_flat = []
        for job in jobs.values():
            if isinstance(job, dict):
                all_steps_flat.extend(job.get("steps", []) or [])
        if not all_steps_flat:
            return None

        # Build sequences — merged_seq holds internal snake_case labels
        merged_seq, job_seqs_str = build_workflow_sequence(jobs, language)

        # ── Presence flags (use internal labels) ──────────────────────────────
        has_checkout = int("checkout_repository" in merged_seq)
        has_setup    = int(any(lbl in merged_seq for lbl in SETUP_LABELS))
        has_test     = int("execute_tests" in merged_seq)
        has_build    = int(any(lbl in merged_seq for lbl in BUILD_LABELS))

        # ── Build display sequence (Title Case, → separator) ──────────────────
        sequence_id = SEQ_SEP.join(display_label(lbl) for lbl in merged_seq)

        chained_commands = int(any(
            isinstance(s, dict) and "run" in s
            and ("&&" in s["run"] or ";" in s["run"])
            for s in all_steps_flat
        ))

        unique_external_actions = {
            step["uses"].strip()
            for step in all_steps_flat
            if isinstance(step, dict)
            and "uses" in step
            and not step["uses"].strip().startswith("./")
        }
        external_actions_count = len(unique_external_actions)

        num_jobs    = len(jobs)
        total_steps = sum(
            len(job.get("steps") or [])
            for job in jobs.values()
            if isinstance(job, dict)
        )

        event_info   = parse_events(workflow)
        cache_info   = parse_cache(all_steps_flat)
        modular_info = parse_modularity(jobs, all_steps_flat)
        pin_info     = parse_pinning(all_steps_flat)

        return {
            "project_id":             row["project_id"],
            "language":               language,
            "num_jobs":               num_jobs,
            "num_steps_total":        total_steps,
            "avg_steps_per_job":      round(total_steps / num_jobs, 2) if num_jobs else 0,
            "dependency_depth":       compute_depth(jobs),
            "sequence_id":            sequence_id,
            "sequence_length":        len(merged_seq),
            "job_sequences":          job_seqs_str,
            "has_checkout":           has_checkout,
            "has_setup":              has_setup,
            "has_test":               has_test,
            "has_build":              has_build,
            "completeness_score":     round((has_checkout + has_setup + has_test + has_build) / 4, 2),
            "external_actions_count": external_actions_count,
            "has_chained_commands":   chained_commands,
            **event_info,
            **cache_info,
            **modular_info,
            **pin_info,
        }

    except Exception:
        return None


# =========================
# MAIN
# =========================
def main():
    df = pd.read_csv(INPUT_PATH, encoding="utf-8-sig")

    results = []
    skipped = 0
    for i, row in df.iterrows():
        res = process_workflow(row)
        if res:
            results.append(res)
        else:
            skipped += 1
        if i % 100 == 0:
            print(f"Processed {i} / {len(df)}")

    out = pd.DataFrame(results)
    for col in out.select_dtypes(include="object").columns:
        out[col] = out[col].fillna("").astype(str)

    out.to_csv(OUTPUT_PATH, index=False, encoding="utf-8-sig")
    print(f"\nDone. {len(results)} workflows processed, {skipped} skipped.")
    print(f"Output: {OUTPUT_PATH}")


if __name__ == "__main__":
    main()