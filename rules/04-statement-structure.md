---
trigger: always_on
description: "Typed facts, mandatory multi-hypothesis/method /df-analysis, DOC-4 layout, and DOC-5 problem analysis"
---
# Statements
## DOC-1
Separate observation, source wording, hypothesis, implication, and recommended action; co-occurrence never proves causation, and an agent KB entry or high expert score never promotes a supposition to a fact.  
Every number, count, date, or interval in a verified `observation` or `client_report` must appear literally in the primary quote or follow from a verified calculation; frame inferred scope qualifiers as hypotheses (`H-*`).  
## DOC-2
Every analytical task lacks a single unambiguous solution: autonomously present competing hypotheses (`>= 2`) and/or solution methods ([DOC-3](#doc-3)) per [df-analysis](../skills/df-analysis/SKILL.md) (read when structuring analytical or complex problem reports).  
Frame each hypothesis with **essence** (plus primary link), **arguments for**, **arguments against**, and **expert plausibility in %** with explicit basis, grounded in concrete evidence per [LINK-1](02-link-standards.md#link-1).  
Distinguish found counterevidence, absence of counterevidence (`not_found`, capped at `<= 75%`), and unavailable checks; `"no misconceptions established"` and `"cause not established"` are valid outcomes.  
Never assume `50/50` equiprobability from lack of data without an explicit prior assumption, and never artificially normalize scores to `100%`.  
## DOC-3
Evaluate competing candidate solution methods (`>= 2`) with **essence**, **arguments for**, **arguments against**, **score in %** with explicit criterion and basis, applicability conditions, and an observable verification criterion.  
Link methods to causes or tasks via ID; unavailability of a private console restricts only console-internal steps and never downgrades proven public storefront or API facts to `limited` or conditional `if`.  
Any method or recommendation proposing files outside the project root must begin immediately with the mandatory warning banner in [FILE-6](01-file-boundaries.md#file-6).  
## DOC-4
Do not use Markdown tables; start every sentence on a new line ended with two trailing spaces (`  \n`, CommonMark hard break) without blank lines inside a paragraph.  
Use lists only for genuine enumerations of homogeneous items or when instructed; keep stable IDs unrenumbered when sorting, accompany verification code with its actual output, and extract reusable code into shared tools.  
## DOC-5
For any defect, failure, error, or architectural problem, autonomously apply [df-analysis](../skills/df-analysis/SKILL.md) as **four separate five-section (`# 0`..`# 4`) analyses** (never merging them):  
1. Primary Problem (`§1`): the failure, defect, hook denial, regression, or architectural problem itself.  
1. Culprit and Provenance (`§2`): who or what introduced or triggered it (agent/profile/model/turn/step, commit SHA, external change, ignored warnings, failed guardrails).  
1. Test and Verification Escape (`§3`): why existing tests, linters, hooks, CI, and gates failed to catch and block it.  
1. Journal and Reporting Integrity (`§4`): whether outputs bypassed Unified Journal `ꙮ` ([FILE-3](01-file-boundaries.md#file-3)), left unrecorded turns, failed-open in `Stop Gate`, or broke observability.  
Each analysis includes `# 0` Problem Metadata (tab-indented `json` with mandatory `"Issue"` key via `harness.py problem-metadata`, dedicated parent issue per defect track or `--no-issue`/`null` only for non-GitHub workspaces or verified-clean audits), `# 1` Problem Description (verbatim diagnostics), `# 2` Root Cause Analysis (`>= 2` hypotheses per [DOC-2](#doc-2)), `# 3` Source Project Attribution (true architectural owner, often Harness), and `# 4` Permanent Systemic Solutions (`>= 2` methods targeting `# 3` per [DOC-3](#doc-3)).  
