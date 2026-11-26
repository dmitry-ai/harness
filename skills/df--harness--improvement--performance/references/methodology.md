<!-- 2026-11-24 "Add /df--harness--improvement--performance skill and update platform adapters": https://github.com/dmitry-ai/harness/issues/193 -->  
# Performance Audit and Optimization Methodology

This reference details the dual-track measurement, root-cause attribution, microbenchmarking, and scoring methodology behind [SKILL.md](../SKILL.md) (distilled from Harness journal audits `206` and `224`).  

## 1. Track A — Turn and Agent Latency Chronometry

Run `harness.py perf-timesheet` on the target conversation or journal step to extract deterministic primary telemetry before forming any hypotheses.  

1. **Exact Wall-Clock Boundaries:** Distinguish `total_span_to_last_step_s` (from the turn's first step timestamp to the start of the final response step) from `total_span_to_last_modified_s` (to `conversation_summaries.db` `last_modified_time`, capturing final response streaming duration), and state the timezone explicitly when reporting local wall times.  
1. **Continuous Phase Partition (`P1..PN`):** When explaining a full turn, partition `100%` of elapsed wall time into consecutive non-overlapping phases summing exactly to the measured total, separating four top-level buckets:  
   - Useful domain work and standard response preparation.  
   - Primary external evidence collection and anchor verification.  
   - Known or external root causes already scoped outside Harness overhead.  
   - Newly attributed Harness overhead categories (`C-1`, `C-2`, …).  
1. **Model Switching and Prompt-Cache Accounting:** Inspect `models.planner_steps_by_model`, `models.model_switches`, `models.cold_switch_count`, `models.cold_switch_uncached_input_tokens` (model transitions where `cache_read_tokens == 0`), `models.same_model_cache_misses` (TTL expiries or post-compaction resets), `models.peak_context_tokens`, and `tokens.plan_mode_output_tokens` (`exit_plan_mode` planning overhead).  
1. **Compaction and Output Truncation Cascades:** Inspect every `CHECKPOINT` event (`step`, `at`, `dur_s`, `pre_step_tokens`), measure post-checkpoint primary-source re-reads caused by context eviction, and inspect `tools.truncated_outputs` (`>= 15000` characters or truncation notices) that inflate context or hide diagnostics.  
1. **Command Buckets and Background Wait Accounting:** Inspect `commands.categories` (`test_runs`, `github_issue_cli`, `answer_check_prepare`, `git_commit_push`, `harness_cli_other`, `inspection_shell`) and `commands.bg_test_waits`, explicitly separating total background `wall_s`, `overlapped_work_s` performed while the task ran, pure agent `idle_wait_s`, and `net_wall_time_blocked_on_tests_s` (sync test time plus background idle waits).  
1. **Top Inter-Step Gaps:** Inspect `top_gaps` to verify that no silent planning stall, user-question wait (`ask_question`), polling loop (`manage_task`), or CLI retry goes unaccounted for.  

## 2. Track B — Test-Suite and Runtime Hot-Path Profiling

Run `harness.py perf-profile-tests` (adding `--cprofile` for CPU/syscall hotspot attribution) whenever tests, hooks, or shared Harness modules account for significant latency.  

1. **Wall Time vs Total CPU Budget:** Always report both `parallel_wall_s` (actual wall-clock duration on `workers` processes out of `cpu_count` logical CPUs) and `sum_file_run_s` (total single-threaded execution budget across all files), noting the indivisible tail bound set by the single slowest file or test method.  
1. **Pareto Concentration:** Quantify what percentage of `sum_file_run_s` is concentrated in the top `5` and top `15` files (`top_files`) and in the slowest individual test methods (`top_tests`).  
1. **Subprocess and Sleep Accounting:** Inspect `totals` for `Popen` volume and time broken down into `git` (`git_count`/`git_s`), `python` (`python_count`/`python_s`), and `other_proc`, plus `sleep_count`/`sleep_s`, distinguishing module import overhead (`import_stats`, `load_s`) from test execution.  
1. **Targeted `cProfile` Attribution:** Use `--cprofile --cprofile-top 25` (or filter to top slow files with `--module <file>`) to isolate top cumulative (`cumtime`) and self (`tottime`) functions and filesystem syscall storms (`nt.stat`, `nt.lstat`, `nt._getfinalpathname`, `nt.scandir`, `nt.fsync`).  
1. **Measurement Integrity Caveats:** Explicitly document any concurrent dirty working-tree edits, parallel CPU contention, second-boundary clock races, or Windows Defender NTFS overhead observed during profiling rather than omitting failed or noisy measurements ([VERIFY-1](../../../rules/05-verification-audit.md#verify-1), [VERIFY-4](../../../rules/05-verification-audit.md#verify-4)).  

## 3. Recurring Harness Bottleneck Taxonomy

Check candidate delays against these proven Harness bottleneck classes before inventing speculative causes:  

1. **Filesystem Scan Leakage:** Unpruned recursive `Path.glob('**/...')` traversing `.git`/`node_modules`, or `%TEMP%` test sandboxes falling back to scanning real host roots (`code_repo_search_roots` or `project_overlays`).  
1. **Hot-Path Syscall Storms:** Repeated `stat`/`lstat`/`resolve` or overlay refreshes inside `project_paths()` / `resolve_project_root()` without fast-path or TTL/mtime validation.  
1. **Windows Subprocess Churn:** Cold `python.exe` launches per test case in hook/CLI tests (reducible via in-process `main()` plus `1` real CLI smoke test per file), repeated `git.exe` fixture setup calls (reducible via `git init -b main`, `git -c`, or `setUpClass` snapshot copy), and uncached read-only `git` calls inside lifecycle checks.  
1. **Combinatorial Fixture Rebuilds and Temp `fsync`:** Rebuilding identical multi-artifact states across dozens of `subTest` iterations instead of snapshot-and-restore, or forcing synchronous `os.fsync()` on ephemeral `TemporaryDirectory` paths without a `%TEMP%`-guarded test opt-out.  
1. **Runner and Inner-Loop Friction:** Running strictly single-threaded `unittest discover` on multi-core hosts instead of `pytest -n auto --dist worksteal -x` or `harness.py run-tests`, re-running slow unrelated files during intermediate Red/Green iterations instead of narrow `pytest <file> -k <test> -x`, or missing `stdout` offloading on compacted turns.  
1. **Hook Cold-Start and Validator Reverse-Engineering:** Heavy eager imports in `PreToolUse`/`Stop` hooks on every tool call, or missing read-only pre-flight/query commands causing agents to read validator source files repeatedly.  

## 4. Controlled Read-Only Microbenchmark Protocol

Before claiming a projected speedup multiplier (`Nx`) for a proposed optimization:  

1. Execute an isolated read-only microbenchmark (using in-memory monkeypatching or an ephemeral `TemporaryDirectory`, leaving `0` repository modifications) comparing the unpatched baseline against the candidate optimization on the exact slow test or hot function.  
1. Verify `0` test failures and identical behavioral assertions on both baseline and candidate runs.  
1. Persist raw baseline timings, optimized timings, speedup ratios (`baseline / optimized`), and environment parameters in `ꘖ/KB/Evidence/<Audit-Slug>/microbenchmarks.json` and cite that file verbatim.  

## 5. Evidence Grounding, Scoring Rubric, and Deduplication

1. **Cross-Audit Deduplication:** Always check `ꘖ/KB/` and recent closed issues in `dmitry-ai/harness` (including `#114`–`#119` from audit `206` and `#171`–`#178`, `#183` from audit `224`) before recommending an optimization; mark already-landed mechanisms as verified baseline or explicitly document a regression if they regressed.  
1. **External Documentation Verification:** Collect every cited external documentation page (`docs.python.org`, `docs.pytest.org`, `pytest-xdist.readthedocs.io`, `git-scm.com`, etc.) via `harness.py collect-http`, inspect exact titles, valid `#anchor` IDs, and verbatim quotes via `harness.py evidence-query`, and document an explicit `anchor_exception` whenever no section anchor exists ([LINK-2](../../../rules/02-link-standards.md#link-2)).  
1. **Unified Suitability Scoring Criterion (`DOC-3`):** State one explicit scoring criterion at the top of the solutions section: reduction in wall-clock latency, CPU budget, and/or uncached tokens across realistic Harness turns and test runs, with zero weakening of verification invariants (`EXEC-2` Test Ratchet, `EXEC-5` Issue-First, `COMPACT-1`, `VERIFY-1`), bounded maintenance complexity under [CODE-4](../../../rules/11-code-formatting.md#code-4) (`<= 20` function SLOC, `<= 8` McCabe, `<= 300` file SLOC), and low regression/invalidation risk.  
1. **Required Elements per Method (`M-*`):** Every candidate method must state its concrete mechanism (linked to cause IDs `C-*` / `H-*`), applicability conditions, observable quantitative verification criterion, arguments for (backed by telemetry, microbenchmarks, and doc quotes), arguments against (trade-offs, cache invalidation or concurrency risks, and invariant safeguards), and analyst suitability score in `%` with its basis.  
1. **Post-Implementation Verification (Implementation Mode Only):** After implementing selected recommendations under parent/child GitHub issues (`EXEC-5`) and full parallel tests (`EXEC-2`), re-run `perf-profile-tests` and/or `perf-timesheet` and record measured before/after numbers in both the closing issue comment and `ꘖ/KB/<Audit-Slug>.md`.  
