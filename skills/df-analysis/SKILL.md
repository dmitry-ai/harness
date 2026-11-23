---
name: df-analysis
description: "Mandatory multi-hypothesis and multi-method analytical framework for all analytical tasks (§1) and autonomous five-part complex problem analysis (§2) with structured problem metadata, verbatim diagnostics, root-project attribution, and systemic solutions; applies automatically without reminders and via /df-analysis."
---
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

### 1.3 General Response Requirements

1. Prove every substantive claim with verbatim quotes and links right next to them ([LINK-1](../../rules/02-link-standards.md#link-1), [VERIFY-1](../../rules/05-verification-audit.md#verify-1)).  
1. Cite documentation down to an existing `#anchor` ([LINK-2](../../rules/02-link-standards.md#link-2)); if no anchor exists, record an explicit `anchor_exception` naming the section title and saved observation.  
1. Never use Markdown tables ([DOC-4](../../rules/04-statement-structure.md#doc-4)); start every sentence on a new line with CommonMark two-space hard line breaks (`  \n`).  
1. Reply in the user's language (`TEXT-1`), adapting section headings to the response language while preserving exact section numbers and JSON keys.  

## 2. Complex Problem Analysis

Apply this five-section structure autonomously, without reminders, whenever you encounter or investigate any failure, defect, hook denial, unexpected tool error, regression, or architectural problem.  

### # 0. Problem Metadata

Include a tab-indented fenced `json` block matching Harness Journal and GitHub issue metadata (`Time`, `Issue`, `Project`, `Journal`, `Agent`, `Trace`, plus optional `Source Project` when the symptom workspace differs from the owning project).  
The `"Issue"` key is mandatory: in GitHub-backed repositories, file the parent problem GitHub issue first via [df-github-issue](../df-github-issue/SKILL.md) per [EXEC-5](../../rules/08-execution-and-tools.md#exec-5) and record its exact URL; pass `--no-issue` (`"Issue": null`) only for non-GitHub workspaces.  
Generate this block deterministically with:  

```text
python <scripts>/harness.py problem-metadata <project> --issue https://github.com/<owner>/<repo>/issues/<N> [--source-project <owning-project>] --format markdown
```

### # 1. Problem Description

Describe the concrete failure symptoms, triggering command or workflow, and affected scope.  
Quote every diagnostic message, exit code, stderr/stdout line, traceback, or hook rejection verbatim using blockquotes, code fences, or `«...»` quotes; never paraphrase diagnostic text away.  

### # 2. Root Cause Analysis

Answer what caused the problem reported in `# 1`.  
Apply the §1.1 Hypothesis Template strictly: evaluate at least two competing root-cause hypotheses (`H-1`, `H-2`, …), each with essence plus primary link, arguments for, arguments against, and plausibility score in `%`.  

### # 3. Source Project Attribution

Explicitly establish which of our projects is the true architectural source of the problem.  
Never assume that the workspace where the failure surfaced owns the defect: bugs frequently originate in a higher-level shared project, very often Harness (`dmitry-ai/harness`) or a shared addon/library repository.  
Verify ownership boundaries against `paths.json`, repository roots, and actual source paths; when ownership itself is uncertain, evaluate candidate source projects as competing hypotheses per §1.1.  

### # 4. Permanent Systemic Solutions

Answer how to eliminate the `# 1` problem permanently inside the `# 3` source project without one-off patches or brittle special-case workarounds.  
Apply the §1.2 Solution Method Template strictly: evaluate at least two candidate solution methods (`M-1`, `M-2`, …), each with essence, arguments for, arguments against, and analyst score in `%`.  

## 3. Deterministic Validation

Validate candidate analytical or problem-analysis responses before `answer-prepare` using:  

```text
python <scripts>/harness.py analysis-check <project> --response-file <candidate.md> [--mode auto|general|problem]
```

`answer-check` and `answer-prepare` run the same Markdown table, documentation `#anchor`, and `/df-analysis` structural gates automatically.  
<!-- https://github.com/dmitry-ai/harness/issues/182 -->  
