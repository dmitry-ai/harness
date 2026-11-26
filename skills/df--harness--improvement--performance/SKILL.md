---
name: df--harness--improvement--performance
description: "Conducts evidence-driven Harness performance audits and optimization plans (turn chronometry timesheets, prompt-cache/compaction diagnostics, test-suite and hot-path profiling, and controlled microbenchmarks) with ranked systemic recommendations; use for /df--harness--improvement--performance and Harness performance investigations."
---
<!-- 2026-11-24 "Add /df--harness--improvement--performance skill and update platform adapters": https://github.com/dmitry-ai/harness/issues/193 -->  
# Harness Performance Improvement Audit and Optimization

This skill codifies the repeatable Harness performance-audit and optimization procedure distilled from Harness journal audits `206` (agent turn latency) and `224` (test-suite and runtime hot-path profiling).  
Users invoke it via `/df--harness--improvement--performance` (or `$df--harness--improvement--performance` in Codex), and agents also follow it whenever investigating slow Harness turns, CLI/hook latency, or test-suite regressions.  
It extends the mandatory analytical structure of [df-analysis](../df-analysis/SKILL.md) ([DOC-2](../../rules/04-statement-structure.md#doc-2), [DOC-3](../../rules/04-statement-structure.md#doc-3), [DOC-4](../../rules/04-statement-structure.md#doc-4), [DOC-5](../../rules/04-statement-structure.md#doc-5)) with deterministic Harness telemetry commands.  

## 1. Execution Modes

Determine the mode strictly from the user instruction per [SCOPE-2](../../rules/00-scope.md#scope-2):  

1. **Audit-Only Mode (Default):** Perform read-only telemetry extraction, suite/hot-path profiling, and controlled read-only microbenchmarks, persist primary artifacts in `ꘖ/KB/Evidence/<Audit-Slug>/` and `ꘖ/KB/<Audit-Slug>.md`, file or link the parent problem GitHub issue per [EXEC-5](../../rules/08-execution-and-tools.md#exec-5), and deliver ranked proposed solutions without editing production code.  
1. **Implementation Mode (Explicit Instruction Only):** When explicitly instructed to implement recommendations (from the current audit or a prior journal response), follow strict `Issue-First` parent/child decomposition (`--parent <N>` per autonomous optimization via [df-github-issue](../df-github-issue/SKILL.md)), `EXEC-2` Red-First TDD ([EXEC-2](../../rules/08-execution-and-tools.md#exec-2)), `CODE-4` module/function size limits ([CODE-4](../../rules/11-code-formatting.md#code-4)), parallel full-suite verification (`pytest -n auto --dist worksteal -x` or `harness.py run-tests`), and before/after telemetry proof.  

## 2. Dual-Track Diagnostic Scope

Select one or both diagnostic tracks automatically based on the symptom:  

1. **Track A — Turn and Agent Latency Timesheet Audit:** Apply when an agent turn took unexpectedly long, hit `CHECKPOINT` context compaction, suffered cold model switches (`cache_read_tokens == 0`), repeated internal validator reads, Plan Mode bounce-backs, CLI flag errors, or background task idle waits.  
   Build deterministic chronometry using `harness.py perf-timesheet` instead of writing ad-hoc trace parsers ([EXEC-1](../../rules/08-execution-and-tools.md#exec-1)):  

```text
python <scripts>/harness.py perf-timesheet --conversation <uuid> [--instance <id>] [--output <audit-dir>/timesheet.json]
python <scripts>/harness.py perf-timesheet --project <root> --journal-step <N> [--output <audit-dir>/timesheet.json]
python <scripts>/harness.py perf-timesheet --trace <transcript_full.jsonl|rollout.jsonl> [--summary-db <db>] [--turn-start-step <S>] [--turn-end-step <E>] [--output <audit-dir>/timesheet.json]
```

1. **Track B — Test-Suite and Runtime Hot-Path Profiling Audit:** Apply when test executions (`unittest`/`pytest`), `PreToolUse`/`Stop` hooks, `answer-check`/`answer-prepare`, `path_registry`, Git lifecycle checks, or `df_github_issue.py` dominate elapsed time.  
   Build deterministic parallel per-file, per-test, `subprocess.Popen`, `time.sleep`, and optional `cProfile` telemetry using `harness.py perf-profile-tests`:  

```text
python <scripts>/harness.py perf-profile-tests [<tests-dir>] [--workers <N>] [--module <name>] [--cprofile] [--top 15] [--cprofile-top 25] [--output <audit-dir>/suite-profile.json]
```

1. **Combined Mode (Track A + Track B):** Whenever Track A reveals significant wall-clock time spent in `test_runs`, `answer_check_prepare`, `github_issue_cli`, or `harness_cli_other`, immediately follow up with Track B on the implicated tests or hot functions so orchestration overhead and runtime/test bottlenecks are attributed separately.  

## 3. Step-by-Step Procedure

1. **Scope and Prior-Audit Deduplication:** Resolve the target project, journal step, conversation UUID, or test suite, and inspect `ꘖ/KB/` and recent Git history via `harness.py git-read` so previously implemented fixes (for example, `#114`–`#119` from audit `206` and `#171`–`#178`, `#183` from audit `224`) are treated as baseline context rather than re-recommended.  
1. **Primary Telemetry Persistence:** Run `perf-timesheet` and/or `perf-profile-tests` with `--output` into `ꘖ/KB/Evidence/<Audit-Slug>/`, preserving raw measurements, environment versions, and exact caveats without creating one-off `.py` scripts in project directories ([FILE-5](../../rules/01-file-boundaries.md#file-5)).  
1. **Bottleneck Attribution and Microbenchmarks:** Follow [methodology.md](references/methodology.md) to partition wall time across useful domain work, external/known causes, and distinct Harness bottlenecks (`C-1`, `C-2`, …), collect normative external documentation with exact `#anchor` targets via `harness.py collect-http` and `harness.py evidence-query` ([LINK-2](../../rules/02-link-standards.md#link-2), [VERIFY-1](../../rules/05-verification-audit.md#verify-1)), and validate high-impact optimization claims with controlled read-only microbenchmarks saved in `microbenchmarks.json`.  
1. **Knowledge Base, GitHub Issue, and Report Assembly:** Record the audit summary and every cited external URL in `ꘖ/KB/<Audit-Slug>.md`, link it in `ꘖ/KB/Progress.md`, file or link the parent problem GitHub issue via [df-github-issue](../df-github-issue/SKILL.md), generate `# 0` metadata via `harness.py problem-metadata`, and structure the response per [report-template.md](references/report-template.md).  
1. **Deterministic Pre-Flight Validation:** Before final publication, validate the candidate draft with `harness.py analysis-check` and `harness.py answer-check`, then record and publish via `harness.py answer-prepare`.  

## 4. Reference Map

1. Detailed Track A/B chronometry, profiling, bottleneck taxonomy, microbenchmark protocol, and scoring rubric: [methodology.md](references/methodology.md).  
1. Required five-section `/df-analysis` performance report structure and pre-flight checklist: [report-template.md](references/report-template.md).  
1. Full Harness CLI documentation for `perf-timesheet`, `perf-profile-tests`, `problem-metadata`, `analysis-check`, and `evidence-query`: [README-agent-tools.md](../../scripts/README-agent-tools.md#additional-tools).  
