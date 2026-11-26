---
name: df-analysis
description: "Mandatory multi-hypothesis and multi-method analytical framework for all analytical tasks (§1) and autonomous four-track complex problem analysis (§2: separate five-section analyses for the primary problem, culprit attribution, test/verification escape, and Journal/reporting integrity); applies automatically without reminders and via /df-analysis."
---
<!-- 2026-11-24 "Create /df-analysis skill and codify mandatory analytical rules": https://github.com/dmitry-ai/harness/issues/182 -->  
# Analytical Framework and Complex Problem Analysis

This skill codifies the mandatory Harness analytical contract ([DOC-2](../../rules/04-statement-structure.md#doc-2), [DOC-3](../../rules/04-statement-structure.md#doc-3), [DOC-4](../../rules/04-statement-structure.md#doc-4), [DOC-5](../../rules/04-statement-structure.md#doc-5)).  
Agents apply it automatically without user reminders, and users can invoke `/df-analysis` (or `$df-analysis` in Codex) to reference either mode directly.  
Determine automatically from the task whether the work is a General Analytical Task (§1) or a Complex Problem Analysis (§2).  

## 1. Universal Multi-Hypothesis and Multi-Method Rule

Every analytical task is presumed to have no single unambiguous solution.  
Never collapse an analytical task into a single asserted cause or a single unqualified recommendation.  
The solution to any analytical task is always a set of competing hypotheses (`>= 2` items) and/or candidate solution methods (`>= 2` items), evaluated automatically without user reminders.  

### 1.1 Hypothesis Template

For every hypothesis (`H-*`), always specify all four elements per [DOC-2](../../rules/04-statement-structure.md#doc-2):  

- Essence, including a clickable link to the primary evidence, source file, or documentation anchor.  
- Arguments for, backed by verbatim quotes and links.  
- Arguments against, including counterevidence, competing alternatives, or explicit documented absence/unavailability of verification (capping unverified hypotheses without counterevidence at `<= 75%`).  
- Analyst plausibility score in `%` with an explicit assessment basis (without assuming `50/50` from ignorance or artificially normalizing scores to `100%`).  

### 1.2 Solution Method Template

For every candidate solution method (`M-*`), always specify all four elements per [DOC-3](../../rules/04-statement-structure.md#doc-3):  

- Essence, describing the concrete systemic mechanism linked to the target cause or task.  
- Arguments for, grounded in architecture and observed evidence.  
- Arguments against, stating trade-offs, risks, and applicability limitations.  
- Analyst score in `%` with an explicit evaluation criterion, basis, and observable verification condition.  
<!-- 2026-11-24 "Add FILE-6 warning banner rule for out-of-workspace file-scattering recommendations": https://github.com/dmitry-ai/harness/issues/200 -->  
- Mandatory warning banner per [FILE-6](../../rules/01-file-boundaries.md#file-6): whenever a candidate method proposes creating, moving, or storing project or tool files outside the project root across the user's computer (such as `%LOCALAPPDATA%`, `%APPDATA%`, `%TEMP%`, `/tmp`, `%ProgramData%`, `%USERPROFILE%`, `$HOME`, `~/`, or `../`), begin the method immediately after its heading with the verbatim uppercase `FILE-6` banner.  

### 1.3 General Response Requirements

1. Prove every substantive claim with verbatim quotes and links right next to them ([LINK-1](../../rules/02-link-standards.md#link-1), [VERIFY-1](../../rules/05-verification-audit.md#verify-1)).  
1. Cite documentation down to an existing `#anchor` ([LINK-2](../../rules/02-link-standards.md#link-2)); if no anchor exists, record an explicit `anchor_exception` naming the section title and saved observation.  
1. Never use Markdown tables ([DOC-4](../../rules/04-statement-structure.md#doc-4)); start every sentence on a new line with CommonMark two-space hard line breaks (`  \n`).  
1. Reply in the user's language (`TEXT-1`), adapting section headings to the response language while preserving exact section numbers and JSON keys.  

## 2. Complex Problem Analysis

<!-- 2026-11-25 "Require separate companion /df-analysis tracks for every complex problem analysis": https://github.com/dmitry-ai/harness/issues/249 -->  
Apply this four-track structure autonomously, without reminders, whenever you encounter or investigate any failure, defect, hook denial, unexpected tool error, regression, stalled turn, or architectural problem.  

### 2.1 Mandatory Four Separate Analyses

Every Complex Problem Analysis must always consist of **four separate, independent five-section (`# 0`..`# 4`) `/df-analysis` breakdowns** — never merge or collapse the three companion analyses into subsections or bullet points inside the primary problem analysis:  

1. **Analysis 1 — Primary Problem (`§1`):** Investigate the primary failure, defect, hook denial, unexpected tool error, regression, or architectural problem itself (symptoms and verbatim diagnostics, competing technical root causes, owning source project, and permanent systemic solutions).  
1. **Analysis 2 — Culprit and Provenance Attribution (`§2`):** Perform a separate `# 0`..`# 4` analysis establishing who or what specifically introduced, broke, or triggered the primary problem — down to concrete accountable provenance: exact agent (system, profile/instance, model, effort, `conversation_id`, `turn_key`, Journal step, primary vs. subagent) and/or human or external actor; exact commit SHA, GitHub Issue, runtime snapshot promotion, or configuration change; exact chronology; any warnings, hook errors, or prior failures ignored or concealed by the culprit; and the governance/promotion guardrails that failed to stop or surface the breakage.  
1. **Analysis 3 — Test and Verification Escape (`§3`):** Perform a separate `# 0`..`# 4` analysis establishing why existing automated tests, linters, hooks, CI, and verification gates failed to catch and block the culprit or defect before it occurred or shipped — quoting verbatim test run results/counts and diagnosing fixture blind spots, missing subprocess/latency/concurrency/end-to-end/contract invariants, narrow test scope, or bypassed/absent verification checks.  
1. **Analysis 4 — Journal, Reporting, and Observability Integrity (`§4`):** Perform a separate `# 0`..`# 4` analysis auditing the Unified Journal (`ꙮ`, [FILE-3](../../rules/01-file-boundaries.md#file-3)) and failure-reporting/observability circuit around the problem — verifying whether any affected agent or process wrote output directly to the platform UI (Antigravity/Codex) bypassing `ꙮ`, failed to record reports or errors in `ꙮ`, left orphaned entries in `turn-reservations.json` or open turns in `ꘖ/data/turns/`, failed-open in `Stop Gate` without capturing the report in `ꙮ`, missed cross-conversation reconciliation, or swallowed/concealed diagnostics.  
   Whenever a Journal bypass, missing Journal record, silent error, or reporting breakdown occurred, file its own parent GitHub Issue and diagnose full root causes and permanent systemic fixes; even when the audit verifies that no active `FILE-3` Journal bypass occurred in this specific incident, still emit this separate `# 0`..`# 4` analysis quoting verbatim the verified Journal/reservation/reporting audit evidence in `# 1`, evaluating residual visibility/bypass hypotheses in `# 2`, attributing the owning observability/journaling project in `# 3`, and evaluating systemic hardening methods in `# 4` (using `--no-issue` / `"Issue": null` only when zero defect exists in this track).  

Give each of the four analyses its own non-numeric level-1 separator heading (for example, `# Analysis 1: ...`, `# Analysis 2: ...`, `# Analysis 3: ...`, `# Analysis 4: ...`, or localized equivalents `# Разбор задачи §1: ...`..`# Разбор задачи §4: ...`), followed immediately by its complete `# 0`..`# 4` sections, and namespace hypothesis/method IDs per track (`H-1-1`/`M-1-1`, `H-2-1`/`M-2-1`, `H-3-1`/`M-3-1`, `H-4-1`/`M-4-1`).  
In GitHub-backed repositories, file a separate parent GitHub Issue via [df-github-issue](../df-github-issue/SKILL.md) per distinct defect track rather than bundling separate problems into one issue ([EXEC-5](../../rules/08-execution-and-tools.md#exec-5)).  

### 2.2 Required Five Sections Inside Each Analysis (`# 0`..`# 4`)

#### # 0. Problem Metadata

Include a tab-indented fenced `json` block matching Harness Journal and GitHub issue metadata (`Time`, `Issue`, `Project`, `Journal`, `Agent`, `Trace`, plus optional `Source Project` when the symptom workspace differs from the owning project).  
The `"Issue"` key is mandatory: in GitHub-backed repositories, file the parent problem GitHub issue for that analysis track first via [df-github-issue](../df-github-issue/SKILL.md) per [EXEC-5](../../rules/08-execution-and-tools.md#exec-5) and record its exact URL; pass `--no-issue` (`"Issue": null`) only for non-GitHub workspaces or a clean companion audit where zero defect was established.  
Generate this block deterministically with:  

```text
python <scripts>/harness.py problem-metadata <project> --issue https://github.com/<owner>/<repo>/issues/<N> [--source-project <owning-project>] --format markdown
```

#### # 1. Problem Description

Describe the concrete failure symptoms, provenance evidence, test-escape evidence, or Journal/observability audit scope for this specific track.  
Quote every diagnostic message, exit code, stderr/stdout line, traceback, test summary, transcript line, reservation entry, or hook rejection verbatim using blockquotes, code fences, or `«...»` quotes; never paraphrase diagnostic text away.  

#### # 2. Root Cause Analysis

Answer what caused the problem reported in `# 1` of this analysis track.  
Apply the §1.1 Hypothesis Template strictly: evaluate at least two competing root-cause hypotheses (`H-*-1`, `H-*-2`, …), each with essence plus primary link, arguments for, arguments against, and plausibility score in `%`.  

#### # 3. Source Project Attribution

Explicitly establish which of our projects is the true architectural source of this track's problem.  
Never assume that the workspace where the failure surfaced owns the defect: bugs frequently originate in a higher-level shared project, very often Harness (`dmitry-ai/harness`) or a shared addon/library repository.  
Verify ownership boundaries against `paths.json`, repository roots, and actual source paths; when ownership itself is uncertain, evaluate candidate source projects as competing hypotheses per §1.1.  

#### # 4. Permanent Systemic Solutions

Answer how to eliminate this track's `# 1` problem permanently inside the `# 3` source project without one-off patches or brittle special-case workarounds.  
Apply the §1.2 Solution Method Template strictly: evaluate at least two candidate solution methods (`M-*-1`, `M-*-2`, …), each with essence, arguments for, arguments against, and analyst score in `%`.  

## 3. Deterministic Validation

<!-- 2026-11-25 "Require separate companion /df-analysis tracks for every complex problem analysis": https://github.com/dmitry-ai/harness/issues/249 -->  
Validate candidate analytical or four-track problem-analysis responses before `answer-prepare` using:  

```text
python <scripts>/harness.py analysis-check <project> --response-file <candidate.md> [--mode auto|general|problem]
```

`answer-check` and `answer-prepare` run the same Markdown table, documentation `#anchor`, `FILE-6` banner, and `/df-analysis` structural gates automatically, validating every `# 0`..`# 4` analysis block independently and enforcing all three separate companion tracks alongside the primary problem.  
