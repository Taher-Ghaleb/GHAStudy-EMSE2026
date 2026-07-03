# ==========================================
# INTERPRETATION BENCHMARK GUIDE
# RQ1: GitHub Actions Workflow Complexity Analysis
# ==========================================

"""
This document provides detailed explanations for:
1. All metrics used in the analysis
2. Interpretation thresholds and their justifications
3. What constitutes "low", "moderate", "high", etc.
4. Research-based benchmarks and rationale
"""

# ==========================================
# PART 1: CORE METRICS - DETAILED EXPLANATIONS
# ==========================================

## 1. SIZE METRICS

### 1.1 LINES_OF_YAML
"""
DEFINITION:
Total number of lines in the workflow YAML file, including:
- Code lines (job definitions, steps, etc.)
- Blank lines
- Comment lines

WHAT IT MEASURES:
- Raw file size
- Cognitive load to read the entire workflow
- Scrolling/navigation burden

INTERPRETATION THRESHOLDS:
"""
from numpy import median


LINES_OF_YAML_THRESHOLDS = {
    "compact": (0, 50),          # Can see entire workflow on one screen
    "moderate": (50, 150),       # Requires scrolling but manageable
    "large": (150, 300),         # Multiple pages, needs organization
    "very_large": (300, float('inf'))  # Difficult to navigate without tools
}

"""
BENCHMARK JUSTIFICATION:
- 50 lines: Standard terminal/editor view (25-50 lines visible)
  → No scrolling needed to see entire workflow
  → Research: Single-screen code easier to comprehend (Cognitive Load Theory)

- 150 lines: Typical code review window
  → Still manageable for review in one sitting
  → Based on GitHub's code review interface (shows ~40-50 lines at a time)
  → Research: Files >100 lines see increased bug rates (Nagappan et al., 2005)

- 300 lines: Beyond typical function/module size
  → Software engineering guideline: functions should be <100 lines
  → Files >300 lines often violate Single Responsibility Principle
  → Research: Large files correlate with higher defect density

WHAT CONSTITUTES LOW vs HIGH:
- LOW (<50 lines):
  Example: Simple CI workflow with checkout → build → test
  Characteristics: Quick to understand, minimal navigation
  
- MODERATE (50-150 lines):
  Example: Multi-platform testing with some conditional logic
  Characteristics: Requires careful reading but still comprehensible
  
- HIGH (150-300 lines):
  Example: Complex deployment pipeline with multiple stages
  Characteristics: Needs good structure/comments to navigate
  
- VERY HIGH (>300 lines):
  Example: Monorepo orchestration or complex release workflows
  Characteristics: Should be split into reusable workflows
  Recommendation: Consider refactoring into multiple files

LANGUAGE-SPECIFIC CONSIDERATIONS:
- C++: May legitimately have more lines due to:
  → Compiler-specific configurations
  → Platform-specific build steps
  → More complex dependency management
  
- Python: Often shorter due to:
  → Simpler packaging (pip vs complex build systems)
  → Less platform variation in typical projects
  
- Java: Medium length due to:
  → Maven/Gradle multi-step builds
  → JDK version matrices
"""


### 1.2 NUM_JOBS
"""
DEFINITION:
Number of independent job definitions in the workflow.
Each job runs in a separate runner/container and can execute in parallel
(unless constrained by 'needs' dependencies).

WHAT IT MEASURES:
- Parallelization complexity
- Number of independent execution contexts
- Coordination overhead

INTERPRETATION THRESHOLDS:
"""
NUM_JOBS_THRESHOLDS = {
    "simple": (0, 3),           # Linear or minimal parallelism
    "moderate": (3, 7),         # Typical multi-platform testing
    "complex": (7, 15),         # Heavy orchestration
    "highly_complex": (15, float('inf'))  # Likely over-engineered
}

"""
BENCHMARK JUSTIFICATION:
- 3 jobs: Typical simple workflow
  Example: build, test, deploy (sequential)
  Example: test-ubuntu, test-windows, test-macos (parallel)
  Cognitive load: Easy to track 3 execution contexts

- 7 jobs: Psychological research limit
  → Miller's Law: Humans can hold 7±2 items in working memory
  → Beyond 7 jobs requires visualization to understand dependencies
  Example: build + (3 OS × test) + integration + deploy = 6 jobs

- 15 jobs: Practical GitHub Actions consideration
  → Free tier: 20 concurrent jobs maximum
  → Beyond 15 suggests possible architectural issues
  → May indicate jobs that could be combined or workflows that should be split

WHAT CONSTITUTES LOW vs HIGH:
- SIMPLE (1-3 jobs):
  Example: Single-platform CI
  ```yaml
  jobs:
    build:
      # Compile code
    test:
      needs: build
      # Run tests
  ```
  Characteristics: Easy dependency graph, minimal coordination

- MODERATE (4-7 jobs):
  Example: Multi-platform testing
  ```yaml
  jobs:
    test-ubuntu: ...
    test-windows: ...
    test-macos: ...
    lint: ...
    security-scan: ...
    integration: 
      needs: [test-ubuntu, test-windows, test-macos]
  ```
  Characteristics: Requires dependency visualization, manageable

- COMPLEX (8-15 jobs):
  Example: Monorepo with multiple services
  Characteristics: Complex dependency graph, needs documentation

- HIGHLY COMPLEX (>15 jobs):
  Red flag: Likely indicates:
  → Workflow should be split into multiple files
  → Jobs could be combined using matrix strategy
  → Over-engineering or poor architecture

GITHUB ACTIONS LIMITS:
- Maximum: 256 jobs per workflow run
- Practical limit: ~20-30 jobs (runner availability)
- Cost consideration: Each job consumes runner minutes

RESEARCH CONTEXT:
- Build complexity research shows linear growth in comprehension time up to ~10 jobs
- Beyond 10 jobs, comprehension requires dependency visualization tools
"""


### 1.3 NUM_STEPS
"""
DEFINITION:
Total count of steps across ALL jobs in the workflow.
Each step is a discrete action (uses: or run:) within a job.

WHAT IT MEASURES:
- Total number of operations
- Potential failure points (each step can fail)
- Overall procedural complexity

INTERPRETATION THRESHOLDS:
"""
#minimal   : value < Q1
#typical   : Q1 ≤ value < median
#intensive : median ≤ value < Q3
#extreme   : value ≥ Q3
#
# 
# NUM_STEPS_THRESHOLDS = {
    "minimal": (0, 10),         # Basic workflow
    "typical": (10, 30),        # Standard CI/CD
    "extensive": (30, 60),      # Complex pipeline
    "very_extensive": (60, float('inf'))  # Very complex or repetitive
}

min=....
q1=...
med=...
q3=..
max=...
NUM_STEPS_THRESHOLDS = {
    "minimal": (min, q1),        
    "typical": (q1, med),        
    "intensive": (med, q3),      
    "extreme": (q3, max)         
}

"""
BENCHMARK JUSTIFICATION:
- 10 steps: Minimal viable CI
  Example per job:
  1. Checkout code
  2. Setup environment (language/tools)
  3. Install dependencies
  4. Run tests
  5. Upload artifacts/reports
  → 2 jobs × 5 steps = 10 total steps

- 30 steps: Typical comprehensive CI/CD
  Example breakdown:
  - Build job: 8 steps (checkout, setup, cache, build, test, lint, coverage, artifact)
  - Deploy job: 6 steps (checkout, setup, download artifact, configure, deploy, verify)
  - 3 platform test jobs × 5 steps each = 15 steps
  Total: 8 + 6 + 15 = 29 steps

- 60 steps: Upper bound before refactoring recommended
  → Beyond 60 suggests repetition that could be consolidated
  → May indicate lack of custom actions or reusable workflows

WHAT CONSTITUTES LOW vs HIGH:
- MINIMAL (1-10 steps):
  Example: Simple library CI
  Characteristics: Quick to execute, easy to debug failures

- TYPICAL (11-30 steps):
  Example: Application with build, test, deploy
  Characteristics: Comprehensive but maintainable

- EXTENSIVE (31-60 steps):
  Example: Monorepo or complex multi-stage pipeline
  Characteristics: Long execution time, many potential failure points
  Warning sign: May benefit from consolidation

- VERY EXTENSIVE (>60 steps):
  Red flag: Likely indicates:
  → Repetitive steps that should use matrix strategy
  → Steps that should be combined into custom actions
  → Workflow doing too much (split into multiple workflows)

CALCULATION NOTE:
If workflow has 3 jobs with [5, 8, 12] steps respectively:
num_steps = 5 + 8 + 12 = 25 (typical)

RELATIONSHIP TO OTHER METRICS:
- avg_steps_per_job = num_steps / num_jobs
  → High ratio (>10) suggests complex individual jobs
  → Low ratio (<5) suggests many simple jobs (possibly over-split)
"""


## 2. STRUCTURAL DEPTH METRICS

### 2.1 MAX_NESTING_DEPTH
"""
DEFINITION:
Maximum levels of nested YAML structures (dictionaries/lists within dictionaries/lists).
Measured by recursive tree traversal of the YAML structure.

WHAT IT MEASURES:
- YAML structural complexity
- Indentation depth
- Cognitive difficulty in reading/editing

INTERPRETATION THRESHOLDS:
"""
MAX_NESTING_DEPTH_THRESHOLDS = {
    "flat": (0, 3),             # Easy to read
    "moderate": (3, 6),         # Manageable nesting
    "deep": (6, 9),             # Difficult to follow
    "very_deep": (9, float('inf'))  # Error-prone, hard to maintain
}

"""
BENCHMARK JUSTIFICATION:
- 3 levels: Natural YAML structure
  Example:
  ```yaml
  jobs:              # Level 1
    test:            # Level 2
      steps:         # Level 3
        - uses: ...  # Level 3 (list item)
  ```
  This is the minimal structure for any job with steps

- 6 levels: Cognitive complexity threshold
  → Research: Code with >4 nesting levels has significantly higher bug rates
  → McCabe's Cyclomatic Complexity: Nesting increases comprehension difficulty
  → YAML-specific: Indentation errors increase exponentially with depth
  
  Example of 6 levels:
  ```yaml
  jobs:              # 1
    test:            # 2
      strategy:      # 3
        matrix:      # 4
          include:   # 5
            - os:    # 6
  ```

- 9 levels: Excessive nesting (anti-pattern)
  → Very difficult to track indentation
  → High risk of YAML syntax errors
  → Code smell: structure should be simplified

WHAT CONSTITUTES LOW vs HIGH:
- FLAT (1-3 levels):
  Example: Simple workflow without matrix or complex conditionals
  ```yaml
  jobs:
    build:
      runs-on: ubuntu-latest
      steps:
        - uses: actions/checkout@v4
        - run: npm install
  ```
  Characteristics: Easy to scan, low error risk

- MODERATE (4-6 levels):
  Example: Workflow with matrix strategy
  ```yaml
  jobs:
    test:
      strategy:
        matrix:
          os: [ubuntu, windows]
          node: [14, 16, 18]
  ```
  Characteristics: Requires careful indentation, manageable

- DEEP (7-9 levels):
  Example: Complex matrix with includes/excludes and env vars
  Warning sign: Difficult to edit without errors
  Recommendation: Consider extracting to separate config files

- VERY DEEP (>9 levels):
  Red flag: Anti-pattern
  Action: Refactor immediately
  Solutions:
  → Extract configuration to external files
  → Use environment variables
  → Simplify structure

YAML-SPECIFIC ISSUES:
- Indentation errors are silent until runtime
- Deep nesting makes diffs hard to read
- Copy-paste errors multiply with depth
- Most YAML linters flag >6 levels as problematic

RESEARCH FOUNDATION:
- Halstead's Complexity Metrics: Nesting increases program difficulty exponentially
- Cognitive Load Theory: Each nesting level adds to working memory burden
- Empirical studies: Bug probability increases ~20% per nesting level beyond 4
"""


### 2.2 JOB_PARALLELISM
"""
DEFINITION:
Number of jobs defined in the workflow.
Represents maximum potential parallelism (actual parallelism limited by 'needs' dependencies).

WHAT IT MEASURES:
- Horizontal complexity (breadth)
- Concurrent execution contexts
- Runner resource requirements

THIS REPLACES THE FLAWED "horizontal_depth" METRIC

INTERPRETATION THRESHOLDS:
"""
JOB_PARALLELISM_THRESHOLDS = {
    "low": (0, 3),              # Sequential or minimal parallelism
    "moderate": (3, 7),         # Typical multi-platform
    "high": (7, 15),            # Heavy parallel execution
    "very_high": (15, float('inf'))  # Extreme parallelism
}

"""
BENCHMARK JUSTIFICATION:
Same as num_jobs (they are equivalent), but emphasizing parallelism aspect.

- 3 jobs: Minimal parallelism
  Example: Sequential pipeline OR 3-way parallel test
  Runner usage: 1 runner if sequential, 3 if parallel

- 7 jobs: Moderate parallelism
  Example: Test across 3 OS × 2 language versions + lint
  Runner usage: Up to 7 concurrent runners
  Cost: 7× the runner minutes per run

- 15 jobs: High parallelism
  Warning: May exceed free tier limits
  GitHub Free: 20 concurrent jobs
  Runner availability: May queue if not enough runners

WHAT CONSTITUTES LOW vs HIGH:
- LOW (1-3 jobs):
  Example: Single platform or sequential pipeline
  Resource use: Minimal
  Execution time: Sum of job durations (if sequential)

- MODERATE (4-7 jobs):
  Example: Multi-platform testing
  Resource use: Moderate (still within free tier comfort zone)
  Execution time: Longest job duration (if fully parallel)

- HIGH (8-15 jobs):
  Example: Extensive matrix testing or monorepo
  Resource use: High (may hit concurrency limits)
  Cost consideration: Significant runner minute usage

- VERY HIGH (>15 jobs):
  Red flag: Potential issues:
  → May queue waiting for available runners
  → High cost on paid plans
  → Complex dependency management
  Recommendation: Consider splitting into multiple workflows

KEY INSIGHT:
Job parallelism is GOOD for speed (reduces total wall time)
BUT increases complexity (more contexts to understand)

ACTUAL PARALLELISM vs POTENTIAL:
- job_parallelism = 10 does NOT mean 10 jobs run simultaneously
- Constrained by:
  1. 'needs' dependencies (vertical_depth shows this)
  2. Available runners
  3. GitHub plan limits

Example:
```yaml
jobs:
  build:
  test-1: needs: build
  test-2: needs: build
  test-3: needs: build
  deploy: needs: [test-1, test-2, test-3]
```
job_parallelism = 5
But actual execution:
- Time 0: build (1 job)
- Time 1: test-1, test-2, test-3 (3 jobs parallel)
- Time 2: deploy (1 job)
Maximum concurrent: 3, not 5
"""


### 2.3 MAX_SEQUENTIAL_STEPS
"""
DEFINITION:
Maximum number of steps in any single job.
Represents the longest sequential operation chain within one job.

WHAT IT MEASURES:
- Individual job complexity
- Longest single execution path
- Granularity of operations

THIS IS THE NEW METRIC REPLACING THE FLAWED HORIZONTAL DEPTH

INTERPRETATION THRESHOLDS:
"""
MAX_SEQUENTIAL_STEPS_THRESHOLDS = {
    "short": (0, 5),            # Minimal job
    "moderate": (5, 15),        # Typical job
    "long": (15, 30),           # Complex job
    "very_long": (30, float('inf'))  # Overly complex job
}

"""
BENCHMARK JUSTIFICATION:
- 5 steps: Minimal viable job
  Example:
  1. Checkout
  2. Setup environment
  3. Run main action (test/build/deploy)
  4. Upload results
  5. Notify

- 15 steps: Typical comprehensive job
  Example build job:
  1. Checkout code
  2. Setup language
  3. Cache dependencies
  4. Install dependencies
  5. Lint code
  6. Compile/build
  7. Run unit tests
  8. Run integration tests
  9. Generate coverage
  10. Build documentation
  11. Create artifacts
  12. Upload artifacts
  13. Update status
  14. Cache build results
  15. Cleanup

- 30 steps: Upper limit before refactoring
  → Beyond 30 suggests job is doing too much
  → Consider splitting into multiple jobs
  → May indicate repeated operations (use loops/matrix)

WHAT CONSTITUTES LOW vs HIGH:
- SHORT (1-5 steps):
  Example: Simple test job
  ```yaml
  steps:
    - uses: actions/checkout@v4
    - uses: actions/setup-node@v4
    - run: npm install
    - run: npm test
    - uses: codecov/codecov-action@v4
  ```
  Characteristics: Quick execution, focused purpose

- MODERATE (6-15 steps):
  Example: Comprehensive build job
  Characteristics: Complete workflow stage, still manageable

- LONG (16-30 steps):
  Example: Complex deployment with multiple verification stages
  Warning sign: Job may be doing too much
  Recommendation: Consider splitting

- VERY LONG (>30 steps):
  Red flag: Job is definitely too complex
  Issues:
  → Hard to debug (which step failed?)
  → Long execution time
  → Likely doing unrelated tasks
  Solutions:
  → Split into multiple jobs
  → Extract repeated steps into custom actions
  → Use matrix strategy for variations

WHY THIS MATTERS:
- Failure isolation: More steps = harder to identify failure cause
- Debugging: Long jobs take longer to re-run during debugging
- Maintenance: Changes require understanding all steps
- Caching: More steps = more cache complexity

RELATIONSHIP TO OTHER METRICS:
avg_steps_per_job = num_steps / num_jobs

If max_sequential_steps >> avg_steps_per_job:
→ Indicates unbalanced job complexity
→ Some jobs are much more complex than others
→ May suggest need for refactoring
"""


### 2.4 VERTICAL_DEPTH
"""
DEFINITION:
Length of the longest job dependency chain.
Calculated using Depth-First Search on the job dependency graph.

WHAT IT MEASURES:
- Critical path length (sequential constraint)
- Minimum workflow execution time
- Dependency coupling

INTERPRETATION THRESHOLDS:
"""
VERTICAL_DEPTH_THRESHOLDS = {
    "shallow": (0, 2),          # Independent or simple pipeline
    "moderate": (2, 4),         # Typical pipeline
    "deep": (4, 6),             # Complex pipeline
    "very_deep": (6, float('inf'))  # Overly sequential
}

"""
BENCHMARK JUSTIFICATION:
- 1 level: No dependencies (all jobs independent)
  Example: Parallel tests across platforms
  Execution time: max(job_durations)
  Parallelism: Maximum

- 2 levels: Simple pipeline
  Example: build → test
  Example: build → [test-1, test-2, test-3] (still depth 2)
  Common pattern: Most CI workflows

- 4 levels: Typical deployment pipeline
  Example: build → test → integration → deploy
  Represents industry standard CI/CD stages
  Execution time: sum of level durations

- 6 levels: Deep pipeline (warning)
  Example: build → unit-test → integration-test → staging → smoke-test → production
  Issues:
  → Long total execution time
  → Single failure blocks entire chain
  → Hard to parallelize
  → Bottleneck in delivery

WHAT CONSTITUTES LOW vs HIGH:
- SHALLOW (1-2 levels):
  Example: Maximum parallelism
  ```yaml
  jobs:
    test-ubuntu:
    test-windows:
    test-macos:
    lint:
  ```
  Characteristics: Fast, no bottlenecks
  Execution time: ~5-10 minutes (longest job)

- MODERATE (3-4 levels):
  Example: Standard pipeline
  ```yaml
  jobs:
    build:
    test:
      needs: build
    integration:
      needs: test
    deploy:
      needs: integration
  ```
  Characteristics: Logical stages, manageable
  Execution time: ~15-30 minutes total

- DEEP (5-6 levels):
  Example: Multi-stage deployment
  Warning sign: Long critical path
  Execution time: 30-60+ minutes
  Recommendation: Look for parallelization opportunities

- VERY DEEP (>6 levels):
  Red flag: Anti-pattern
  Issues:
  → Very long execution time (1+ hours)
  → Single failure blocks many downstream jobs
  → Difficult to reason about
  → Poor user experience (long wait for results)
  
  Solutions:
  → Combine sequential jobs where possible
  → Parallelize independent operations
  → Use separate workflows for different purposes

CRITICAL PATH ANALYSIS:
vertical_depth × avg_job_duration = minimum_workflow_time

Example:
- vertical_depth = 5
- Each level takes ~10 minutes
- Minimum time = 50 minutes
→ No amount of parallelism can reduce below 50 minutes

RELATIONSHIP TO JOB_PARALLELISM:
- High job_parallelism + Low vertical_depth = Excellent (fast, parallel)
- Low job_parallelism + High vertical_depth = Poor (slow, sequential)
- High both = Mixed (parallel stages, but sequential between stages)

BEST PRACTICE:
- Minimize vertical_depth for speed
- Maximize parallelism within each level
- Example: build → [test-1, test-2, test-3] → deploy
  vertical_depth = 3 (good)
  Parallelism at test level = 3 (good)
"""


## 3. ORCHESTRATION METRICS

### 3.1 MATRIX_SIZE
"""
DEFINITION:
Total number of test combinations generated by matrix strategies across all jobs.
Calculated as: product of matrix dimensions + includes - excludes

WHAT IT MEASURES:
- Test coverage breadth
- CI execution time multiplication
- Configuration complexity

INTERPRETATION THRESHOLDS:
"""
MATRIX_SIZE_THRESHOLDS = {
    "none": (0, 0),             # No matrix testing
    "small": (0, 5),            # Minimal matrix
    "moderate": (5, 20),        # Typical matrix
    "large": (20, 50),          # Extensive matrix
    "very_large": (50, float('inf'))  # Excessive matrix
}

"""
BENCHMARK JUSTIFICATION:
- 0: No matrix testing
  → Single configuration
  → Fast but limited coverage

- 5 combinations: Minimal matrix
  Example: 2 OS × 2 versions = 4, or 3 OS × 1 version = 3
  Execution time: 5× single test time
  Cost: 5× runner minutes

- 20 combinations: Typical comprehensive testing
  Example: 3 OS × 4 Python versions × 2 architectures = 24
  Example: 2 OS × 3 Java versions × 3 build tools = 18
  Execution time: 20× single test time
  Cost consideration: Significant but justified for quality

- 50 combinations: Upper practical limit
  Example: 5 OS × 5 versions × 2 architectures = 50
  Issues:
  → Very long CI time (could be hours)
  → High cost (50× runner minutes)
  → May indicate over-testing
  → GitHub limit: 256 combinations maximum

WHAT CONSTITUTES LOW vs HIGH:
- NONE (0):
  Example: Single configuration test
  Characteristics: Fast, but may miss platform issues

- SMALL (1-5):
  Example: Test on 3 major platforms
  ```yaml
  strategy:
    matrix:
      os: [ubuntu-latest, windows-latest, macos-latest]
  ```
  Characteristics: Balanced coverage vs speed

- MODERATE (6-20):
  Example: Multi-platform, multi-version
  ```yaml
  strategy:
    matrix:
      os: [ubuntu-latest, windows-latest, macos-latest]
      python-version: [3.8, 3.9, 3.10, 3.11]
  ```
  Combinations: 3 × 4 = 12
  Characteristics: Comprehensive, industry standard

- LARGE (21-50):
  Example: Extensive cross-platform testing
  Warning sign: May be testing too many combinations
  Recommendation: Use 'include' for specific combinations only

- VERY LARGE (>50):
  Red flag: Almost certainly over-testing
  Issues:
  → Extremely long CI time
  → High cost
  → Overwhelming number of potential failures
  → Difficult to triage failures
  
  Solutions:
  → Test core platforms thoroughly, others lightly
  → Use 'exclude' to remove unlikely combinations
  → Consider splitting into separate workflows
  → Schedule exhaustive tests for nightly builds only

CALCULATION EXAMPLE:
```yaml
strategy:
  matrix:
    os: [ubuntu, windows, macos]           # 3 options
    python: [3.8, 3.9, 3.10, 3.11]        # 4 options
    include:
      - os: ubuntu
        python: 3.12                       # +1 combination
    exclude:
      - os: macos
        python: 3.8                        # -1 combination
```
matrix_size = (3 × 4) + 1 - 1 = 12

TIME AND COST IMPACT:
If single test takes 10 minutes:
- matrix_size = 12 → 120 runner minutes per workflow run
- 10 PRs per day → 1,200 runner minutes daily
- Free tier: 2,000 minutes/month → Would exceed in 2 days

LANGUAGE-SPECIFIC PATTERNS:
- Python: Often high matrix (many supported versions)
  Typical: 3 OS × 5 Python versions = 15

- Java: Moderate matrix (fewer active JDK versions)
  Typical: 3 OS × 3 JDK versions = 9

- C++: Potentially very high (compilers × versions × platforms)
  Risk: 3 compilers × 4 versions × 3 OS = 36
  Recommendation: Test primary compiler comprehensively, others selectively
"""


### 3.2 NUM_CONDITIONALS
"""
DEFINITION:
Total count of 'if:' statements across all jobs and steps.
Each conditional creates a branching decision point.

WHAT IT MEASURES:
- Logical complexity
- Execution path variability
- Cyclomatic complexity contribution

INTERPRETATION THRESHOLDS:
"""
NUM_CONDITIONALS_THRESHOLDS = {
    "none": (0, 0),             # Deterministic
    "minimal": (0, 3),          # Simple branching
    "moderate": (3, 10),        # Typical conditional logic
    "complex": (10, 20),        # Heavy branching
    "very_complex": (20, float('inf'))  # Excessive branching
}

"""
BENCHMARK JUSTIFICATION:
- 0 conditionals: Deterministic workflow
  → Same execution every time
  → Easy to predict behavior
  → Simpler debugging

- 3 conditionals: Simple branching
  Example uses:
  1. Deploy only on main branch
  2. Run security scan only on schedule
  3. Upload coverage only if tests pass
  
  Each conditional doubles potential paths (worst case)
  3 conditionals = 2³ = 8 possible execution paths

- 10 conditionals: Cyclomatic complexity threshold
  → McCabe Complexity: 10+ indicates high complexity
  → 2¹⁰ = 1,024 theoretical paths (though many unreachable)
  → Testing all paths becomes impractical

- 20 conditionals: Excessive branching
  → 2²⁰ = 1,048,576 theoretical paths
  → Impossible to reason about all cases
  → Very difficult to debug
  → Strong refactoring needed

WHAT CONSTITUTES LOW vs HIGH:
- NONE (0):
  Example: Simple CI that always runs same way
  Characteristics: Predictable, easy to debug

- MINIMAL (1-3):
  Example: Basic branch/event conditionals
  ```yaml
  jobs:
    deploy:
      if: github.ref == 'refs/heads/main'
      steps:
        - run: deploy.sh
        - if: failure()
          run: notify_failure.sh
  ```
  Characteristics: Clear decision points, manageable

- MODERATE (4-10):
  Example: Environment-specific logic
  ```yaml
  jobs:
    test:
      steps:
        - if: matrix.os == 'windows'
          run: windows_setup.bat
        - if: matrix.os == 'ubuntu'
          run: linux_setup.sh
        - if: github.event_name == 'pull_request'
          run: check_formatting.sh
        - if: github.event_name == 'push'
          run: full_test_suite.sh
  ```
  Characteristics: Requires mental execution, still traceable

- COMPLEX (11-20):
  Warning sign: Logic becoming difficult to follow
  Example: Multiple environment checks, event types, outcomes
  Recommendation: Extract to scripts or use separate workflows

- VERY COMPLEX (>20):
  Red flag: Anti-pattern
  Issues:
  → Cannot predict workflow behavior
  → Debugging requires trial-and-error
  → Some branches likely never tested
  
  Solutions:
  → Split into multiple workflows (one per trigger)
  → Use separate files for different environments
  → Simplify conditional logic
  → Document decision tree

CONDITIONAL TYPES AND COMPLEXITY:
Simple conditionals (low complexity):
- github.ref == 'refs/heads/main'
- github.event_name == 'pull_request'
- success() / failure()

Complex conditionals (high complexity):
- Multiple && / || operators
- contains(), startsWith() with complex strings
- Nested conditionals
- Context-dependent logic

CYCLOMATIC COMPLEXITY RELATIONSHIP:
Base complexity = 1
Each 'if' adds +1 to complexity
Each '&&' or '||' adds +1

Example:
```yaml
if: |
  github.event_name == 'push' &&
  github.ref == 'refs/heads/main' &&
  !contains(github.event.head_commit.message, '[skip ci]')
```
This single conditional has cyclomatic complexity = 4

DEBUGGING IMPACT:
- Few conditionals: Can test all paths manually
- Many conditionals: Must rely on logging/instrumentation
- Excessive conditionals: Cannot reason about behavior
"""


### 3.3 NUM_JOB_DEPENDENCIES
"""
DEFINITION:
Total count of 'needs:' statements across all jobs.
Each entry in 'needs' is counted separately.

WHAT IT MEASURES:
- Coordination complexity
- Coupling between jobs
- Constraint on parallelism

INTERPRETATION THRESHOLDS:
"""
NUM_JOB_DEPENDENCIES_THRESHOLDS = {
    "none": (0, 0),             # Fully independent
    "minimal": (0, 3),          # Simple pipeline
    "moderate": (3, 10),        # Typical orchestration
    "heavy": (10, 20),          # Complex coordination
    "very_heavy": (20, float('inf'))  # Excessive coupling
}

"""
BENCHMARK JUSTIFICATION:
- 0 dependencies: Maximum parallelism
  → All jobs can run simultaneously
  → No coordination needed
  → Fastest execution (limited only by runners)

- 3 dependencies: Simple pipeline
  Example:
  ```yaml
  jobs:
    build:
    test:
      needs: build              # 1 dependency
    deploy:
      needs: test               # 1 dependency
  ```
  Total dependencies: 2 (linear pipeline)
  
  Or:
  ```yaml
  jobs:
    build:
    test:
      needs: build              # 1 dependency
    lint:
      needs: build              # 1 dependency
    docs:
      needs: build              # 1 dependency
  ```
  Total dependencies: 3 (fan-out from build)

- 10 dependencies: Complex coordination
  Example: Integration job depending on multiple test jobs
  ```yaml
  jobs:
    test-1: ...
    test-2: ...
    test-3: ...
    integration:
      needs: [test-1, test-2, test-3]  # 3 dependencies
    deploy:
      needs: integration                # 1 dependency
  ```

- 20 dependencies: Excessive coupling
  → Indicates overly complex dependency graph
  → Difficult to understand execution order
  → May have circular dependency risks (GitHub detects these)
  → Consider simplifying architecture

WHAT CONSTITUTES LOW vs HIGH:
- NONE (0):
  Example: Parallel test suite
  Characteristics: Maximum speed, no coordination burden

- MINIMAL (1-3):
  Example: Simple sequential pipeline
  Characteristics: Clear execution order, manageable

- MODERATE (4-10):
  Example: Multiple test stages feeding into integration
  Characteristics: Requires visualization to understand

- HEAVY (11-20):
  Example: Monorepo with many interdependent services
  Warning sign: Complex coordination
  Recommendation: Ensure dependency graph is documented

- VERY HEAVY (>20):
  Red flag: Overly coupled
  Issues:
  → Very difficult to understand execution order
  → Changes risky (might break unexpected jobs)
  → Refactoring difficult
  
  Solutions:
  → Group related jobs
  → Use matrix strategies instead of many jobs
  → Split into multiple workflows

DEPENDENCY PATTERNS:
Linear chain (depth):
```yaml
A → B → C → D
```
Dependencies: 3
vertical_depth: 4

Fan-out (breadth):
```yaml
A → [B, C, D]
```
Dependencies: 3
vertical_depth: 2

Diamond (convergence):
```yaml
    A
   ↙ ↘
  B   C
   ↘ ↙
    D
```
Dependencies: 4 (B needs A, C needs A, D needs [B,C])
vertical_depth: 3

Complex graph:
Multiple patterns mixed
Dependencies: High
Recommendation: Visualize with tools

RELATIONSHIP TO METRICS:
dependency_ratio = num_job_dependencies / num_jobs

- Ratio < 0.5: Loosely coupled (mostly independent)
- Ratio 0.5-1.5: Moderately coupled (typical)
- Ratio > 1.5: Heavily coupled (each job depends on multiple others)

Example:
- 10 jobs, 3 dependencies → ratio = 0.3 (loose)
- 10 jobs, 15 dependencies → ratio = 1.5 (tight)
"""


## 4. ACTION USAGE METRICS

### 4.1 NUM_UNIQUE_EXTERNAL_ACTIONS
"""
DEFINITION:
Count of unique third-party actions referenced (owner/repo@version format).
Version differences are ignored (actions/checkout@v3 and @v4 count as one).

WHAT IT MEASURES:
- Dependency on external code
- Supply chain complexity
- Learning curve for contributors

INTERPRETATION THRESHOLDS:
"""
NUM_EXTERNAL_ACTIONS_THRESHOLDS = {
    "none": (0, 0),             # Script-based only
    "minimal": (0, 3),          # Basic actions
    "moderate": (3, 8),         # Typical ecosystem usage
    "heavy": (8, 15),           # Reliant on marketplace
    "very_heavy": (15, float('inf'))  # Excessive dependencies
}

"""
BENCHMARK JUSTIFICATION:
- 0 actions: Pure script-based
  → All logic in 'run:' commands
  → No marketplace dependencies
  → More portable but more code to maintain

- 3 actions: Minimal standard set
  Example:
  1. actions/checkout (get code)
  2. actions/setup-python (or setup-java, setup-node)
  3. actions/upload-artifact (or codecov/codecov-action)
  
  This represents the "essential" actions for basic CI

- 8 actions: Typical well-integrated workflow
  Example might include:
  - Checkout
  - Language setup
  - Caching
  - Test coverage
  - Security scanning
  - Artifact management
  - Notification
  - Documentation deployment

- 15 actions: Heavy marketplace reliance
  → Each action is a dependency to maintain
  → Each action is a potential security risk
  → Each action has its own learning curve

WHAT CONSTITUTES LOW vs HIGH:
- NONE (0):
  Example: All bash/python/etc scripts
  ```yaml
  steps:
    - run: git clone ${{ github.repository }}
    - run: python -m pytest
    - run: ./deploy.sh
  ```
  Characteristics: Self-contained, but more code

- MINIMAL (1-3):
  Example: Essential actions only
  ```yaml
  steps:
    - uses: actions/checkout@v4
    - uses: actions/setup-python@v5
    - run: pip install -r requirements.txt
    - run: pytest
    - uses: codecov/codecov-action@v4
  ```
  Characteristics: Balanced approach

- MODERATE (4-8):
  Example: Well-integrated with ecosystem
  Characteristics: Leverages community solutions

- HEAVY (9-15):
  Example: Extensive automation via marketplace
  Warning sign: Dependency management burden
  Considerations:
  → Each action needs version pinning
  → Each action needs security review
  → Breaking changes in actions affect workflow

- VERY HEAVY (>15):
  Red flag: Excessive dependencies
  Issues:
  → Difficult to audit security
  → Version management complexity
  → High risk of breaking changes
  → Long-term maintenance burden
  
  Solutions:
  → Consolidate similar actions
  → Replace with custom scripts where simple
  → Create internal actions for common patterns

SECURITY CONSIDERATIONS:
Each external action:
- Runs with workflow permissions
- Could be compromised
- Needs to be kept up-to-date
- Should be pinned to specific versions

Best practice:
- Pin to commit SHAs for security
- Regularly audit dependencies
- Prefer official actions/* over third-party
- Review action source code for sensitive workflows

COMMON EXTERNAL ACTIONS:
Official (actions/*):
- actions/checkout
- actions/setup-* (python, java, node, etc.)
- actions/cache
- actions/upload-artifact
- actions/download-artifact

Popular third-party:
- codecov/codecov-action
- docker/build-push-action
- softprops/action-gh-release
- coverallsapp/github-action

Marketplace variety:
Thousands available, varying quality
"""

### 4.2 NUM_MARKETPLACE_ACTIONS
"""
DEFINITION:
Count of third-party marketplace actions (excludes official actions/* organization).

WHAT IT MEASURES:
- Reliance on community actions
- Ecosystem health indicator
- Third-party dependency risk

INTERPRETATION THRESHOLDS:
"""
NUM_MARKETPLACE_ACTIONS_THRESHOLDS = {
    "none": (0, 0),             # Official actions only
    "minimal": (0, 2),          # Few marketplace actions
    "moderate": (2, 5),         # Balanced mix
    "heavy": (5, 10),           # Heavy marketplace use
    "very_heavy": (10, float('inf'))  # Extreme marketplace reliance
}

"""
BENCHMARK JUSTIFICATION:
- 0: Official actions only
  → Most secure approach
  → Limited functionality
  → May require custom scripts

- 2 marketplace actions: Common additions
  Example: codecov/codecov-action, docker/build-push-action
  These are widely-trusted, well-maintained actions

- 5 marketplace actions: Typical mix
  → Leveraging ecosystem for specialized tasks
  → Still manageable to audit
  → Each should be carefully vetted

- 10 marketplace actions: Heavy reliance
  → Significant third-party dependency
  → Requires dedicated security review process
  → Consider building internal alternatives

WHAT CONSTITUTES LOW vs HIGH:
- NONE (0):
  Characteristics: Most secure, but limited functionality

- MINIMAL (1-2):
  Characteristics: Trusted actions for specific needs

- MODERATE (3-5):
  Characteristics: Good ecosystem integration

- HEAVY (6-10):
  Warning: Security surface area expanding

- VERY HEAVY (>10):
  Red flag: Too many third-party dependencies
  Recommendation: Consolidate or build internal tools

COMPARISON TO TOTAL EXTERNAL ACTIONS:
If num_unique_external_actions = 10 and num_marketplace_actions = 3:
→ 7 official actions, 3 marketplace
→ Good balance

If num_unique_external_actions = 10 and num_marketplace_actions = 9:
→ 1 official action, 9 marketplace
→ Heavy third-party reliance
→ Security review essential
"""


### 4.3 NUM_LOCAL_ACTIONS
"""
DEFINITION:
Count of actions defined in the same repository (./ prefix).

WHAT IT MEASURES:
- Internal code reusability
- Modularization practice
- Workflow maturity

INTERPRETATION THRESHOLDS:
"""
NUM_LOCAL_ACTIONS_THRESHOLDS = {
    "none": (0, 0),             # No internal actions
    "minimal": (0, 2),          # Some reusability
    "moderate": (2, 5),         # Good modularization
    "heavy": (5, float('inf'))  # Extensive internal actions
}

"""
BENCHMARK JUSTIFICATION:
- 0: No internal actions
  → All logic inline or external
  → Missed reusability opportunity OR
  → Workflow too simple to need it

- 2 local actions: Starting modularization
  Example: Custom setup action, common cleanup action
  Benefit: DRY principle, easier maintenance

- 5 local actions: Mature modularization
  → Well-organized codebase
  → Reusable workflow components
  → Good engineering practice

WHAT CONSTITUTES LOW vs HIGH:
- NONE (0):
  Two possibilities:
  1. Simple workflow (doesn't need actions)
  2. Missed opportunity (repeated code)

- MINIMAL (1-2):
  Characteristics: Starting to extract common patterns

- MODERATE (3-5):
  Characteristics: Good modularization
  Indicates: Mature CI/CD practices

- HEAVY (>5):
  Two interpretations:
  1. Excellent: Highly modular, reusable
  2. Over-engineered: Too much abstraction
  
  Consider: Are these actions actually reused or just adding complexity?

BENEFITS OF LOCAL ACTIONS:
- Reusability across jobs
- Version control with code
- No external dependencies
- Team-specific logic encapsulation

Example structure:
```
.github/
  actions/
    setup-environment/
      action.yml
    run-tests/
      action.yml
  workflows/
    ci.yml  # uses: ./.github/actions/setup-environment
```

WHEN TO CREATE LOCAL ACTIONS:
- Same logic used in 3+ places
- Complex setup that benefits from encapsulation
- Team-specific workflows
- Logic that changes frequently (keep in repo)
"""


### 4.4 NUM_REUSABLE_WORKFLOWS
"""
DEFINITION:
Count of reusable workflow calls (job-level 'uses:' statements).

WHAT IT MEASURES:
- Workflow composition practice
- Organizational CI/CD maturity
- Code reuse at workflow level

INTERPRETATION THRESHOLDS:
"""
NUM_REUSABLE_WORKFLOWS_THRESHOLDS = {
    "none": (0, 0),             # Self-contained
    "minimal": (0, 2),          # Some composition
    "moderate": (2, float('inf'))  # Advanced composition
}

"""
BENCHMARK JUSTIFICATION:
- 0: Self-contained workflow
  → All logic defined inline
  → Simpler for small projects
  → May indicate duplication across repo

- 2 reusable workflows: Good practice
  Example: Common deployment workflow, standard test suite
  Benefit: Centralized patterns, easier updates

WHAT CONSTITUTES LOW vs HIGH:
- NONE (0):
  Characteristics: Independent workflow
  Suitable for: Simple projects

- MINIMAL (1-2):
  Characteristics: Using shared patterns
  Indicates: Organizational maturity

- MODERATE (>2):
  Characteristics: Heavy workflow composition
  Indicates: Enterprise practices
  Consideration: Ensure documentation of workflow architecture

REUSABLE WORKFLOWS ARE ADVANCED FEATURE:
- Introduced in GitHub Actions in 2021
- Indicates sophisticated CI/CD
- Often seen in:
  → Large organizations
  → Multi-repo projects
  → Standardized workflows

Example:
```yaml
# caller workflow
jobs:
  call-shared-test:
    uses: org/shared-workflows/.github/workflows/test.yml@main
  call-shared-deploy:
    uses: org/shared-workflows/.github/workflows/deploy.yml@main
```
num_reusable_workflows = 2
"""


## 5. DERIVED METRICS

### 5.1 AVG_STEPS_PER_JOB
"""
DEFINITION:
Average number of steps per job.
Formula: num_steps / num_jobs

WHAT IT MEASURES:
- Job granularity
- Balance of job complexity

INTERPRETATION THRESHOLDS:
"""
AVG_STEPS_PER_JOB_THRESHOLDS = {
    "minimal": (0, 3),          # Very simple jobs
    "moderate": (3, 7),         # Typical jobs
    "extensive": (7, 15),       # Complex jobs
    "very_extensive": (15, float('inf'))  # Overly complex jobs
}

"""
BENCHMARK JUSTIFICATION:
- 3 steps/job: Minimal viable job
  Example: checkout, setup, run
  Indicates: Highly granular job separation

- 7 steps/job: Typical balanced job
  Example: Complete workflow stage
  Indicates: Good job scope

- 15 steps/job: Complex jobs
  May indicate: Jobs doing too much

WHAT THIS REVEALS:
Low ratio (< 5): Many small jobs (possibly over-split)
High ratio (> 10): Few large jobs (possibly under-split)
Balanced (5-10): Well-scoped jobs
"""


### 5.2 DEPENDENCY_RATIO
"""
DEFINITION:
Ratio of dependencies to jobs.
Formula: num_job_dependencies / num_jobs

WHAT IT MEASURES:
- Degree of coupling between jobs

INTERPRETATION THRESHOLDS:
"""
DEPENDENCY_RATIO_THRESHOLDS = {
    "independent": (0, 0),      # No dependencies
    "loosely_coupled": (0, 0.5),  # Few dependencies
    "coupled": (0.5, 1.5),      # Moderate coupling
    "highly_coupled": (1.5, float('inf'))  # Heavy coupling
}

"""
BENCHMARK JUSTIFICATION:
- 0: Fully independent (all parallel)
- 0.5: Half of jobs have dependencies
- 1.5: Each job depends on 1-2 others on average
- >2: Heavily interdependent

WHAT THIS REVEALS:
Low ratio: More parallelism possible
High ratio: Sequential constraints
"""


### 5.3 EXTERNAL_ACTION_DIVERSITY
"""
DEFINITION:
Ratio of unique external actions to total steps.
Formula: num_unique_external_actions / num_steps

WHAT IT MEASURES:
- Density of external dependencies
- Script vs action balance

INTERPRETATION THRESHOLDS:
"""
EXTERNAL_ACTION_DIVERSITY_THRESHOLDS = {
    "none": (0, 0),             # Script-based
    "sparse": (0, 0.1),         # Few actions
    "moderate": (0.1, 0.3),     # Balanced
    "dense": (0.3, float('inf'))  # Action-heavy
}

"""
BENCHMARK JUSTIFICATION:
- 0: No external actions (all scripts)
- 0.1: 10% of steps use unique actions (mostly scripts)
- 0.3: 30% of steps use unique actions (heavy action use)

WHAT THIS REVEALS:
Low diversity: Script-heavy approach
High diversity: Action-heavy approach (more dependencies)
"""


### 5.4 CONDITIONAL_DENSITY
"""
DEFINITION:
Ratio of conditionals to total operations.
Formula: num_conditionals / (num_jobs + num_steps)

WHAT IT MEASURES:
- Proportion of logic that's conditional
- Predictability of execution

INTERPRETATION THRESHOLDS:
"""
CONDITIONAL_DENSITY_THRESHOLDS = {
    "none": (0, 0),             # No conditionals
    "sparse": (0, 0.1),         # Few conditionals
    "moderate": (0.1, 0.3),     # Moderate branching
    "dense": (0.3, float('inf'))  # Heavy branching
}

"""
BENCHMARK JUSTIFICATION:
- 0: Deterministic workflow
- 0.1: 10% of operations conditional
- 0.3: 30% of operations conditional (very dynamic)

WHAT THIS REVEALS:
Low density: Predictable workflow
High density: Highly context-dependent execution
"""


# ==========================================
# SUMMARY TABLE OF ALL THRESHOLDS
# ==========================================

COMPREHENSIVE_THRESHOLD_SUMMARY = """
METRIC                          | COMPACT/LOW | MODERATE  | LARGE/HIGH | VERY LARGE/HIGH
================================|=============|===========|============|================
lines_of_yaml                   | < 50        | 50-150    | 150-300    | > 300
num_jobs                        | < 3         | 3-7       | 7-15       | > 15
num_steps                       | < 10        | 10-30     | 30-60      | > 60
max_nesting_depth               | < 3         | 3-6       | 6-9        | > 9
job_parallelism                 | < 3         | 3-7       | 7-15       | > 15
max_sequential_steps            | < 5         | 5-15      | 15-30      | > 30
vertical_depth                  | < 2         | 2-4       | 4-6        | > 6
matrix_size                     | 0-5         | 5-20      | 20-50      | > 50
num_conditionals                | 0-3         | 3-10      | 10-20      | > 20
num_job_dependencies            | 0-3         | 3-10      | 10-20      | > 20
num_unique_external_actions     | 0-3         | 3-8       | 8-15       | > 15
num_marketplace_actions         | 0-2         | 2-5       | 5-10       | > 10
num_local_actions               | 0           | 1-2       | 3-5        | > 5
num_reusable_workflows          | 0           | 1-2       | > 2        | N/A
avg_steps_per_job               | < 3         | 3-7       | 7-15       | > 15
dependency_ratio                | < 0.5       | 0.5-1.5   | > 1.5      | N/A
external_action_diversity       | < 0.1       | 0.1-0.3   | > 0.3      | N/A
conditional_density             | < 0.1       | 0.1-0.3   | > 0.3      | N/A
"""

# ==========================================
# RESEARCH FOUNDATIONS
# ==========================================

RESEARCH_CITATIONS = """
THRESHOLDS ARE BASED ON:

1. COGNITIVE LOAD THEORY
   - Miller (1956): 7±2 items in working memory
   - Applied to: num_jobs, job_parallelism

2. CYCLOMATIC COMPLEXITY RESEARCH
   - McCabe (1976): Complexity > 10 is high risk
   - Applied to: num_conditionals, nesting depth

3. CODE QUALITY METRICS
   - Halstead Metrics: Nesting increases difficulty exponentially
   - Applied to: max_nesting_depth

4. EMPIRICAL SOFTWARE ENGINEERING
   - Nagappan et al. (2005): File size correlates with defects
   - Applied to: lines_of_yaml

5. PRACTICAL GITHUB ACTIONS LIMITS
   - Official limits: 256 matrix combinations, 20 concurrent jobs (free tier)
   - Applied to: matrix_size, job_parallelism

6. INDUSTRY BEST PRACTICES
   - Functions should be < 100 lines
   - Files should be < 500 lines
   - Applied to: num_steps, lines_of_yaml

7. BUILD SYSTEM RESEARCH
   - Dependency chains increase failure probability
   - Applied to: vertical_depth, num_job_dependencies
"""

print("Interpretation benchmark guide loaded successfully!")
print("\nTo view thresholds for a specific metric:")
print("  print(<METRIC_NAME>_THRESHOLDS)")
print("\nExample:")
print("  print(LINES_OF_YAML_THRESHOLDS)")