---
trigger: always_on
description: "Typed facts, mandatory multi-hypothesis/method /df-analysis, DOC-4 layout, and DOC-5 problem analysis"
---
# Statements
## DOC-1
Separate observation, source wording, hypothesis, implication, and recommended action; co-occurrence never proves causation, and an agent KB entry or high expert score never promotes a supposition to a fact.  
Every number, count, date, or interval in a verified `observation` or `client_report` must appear literally in the primary quote or follow from a verified calculation; frame inferred scope qualifiers as hypotheses (`H-*`).  
## DOC-2
Every analytical task has no single unambiguous solution: autonomously present competing hypotheses (`>= 2`) and/or solution methods ([DOC-3](#doc-3)) per [df-analysis](../skills/df-analysis/SKILL.md) (read when structuring analytical or complex problem reports).  
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
For any defect, failure, error, or architectural problem, autonomously apply [df-analysis](../skills/df-analysis/SKILL.md) using strict hierarchical Markdown headings (flat level-1 `# 0`..`# 4` subsection flattening is forbidden):  
1. Mixed task-plus-defect turns (new problems discovered while executing a user task): split the response into exactly two level-1 parts — `# 𝙸. Что сделано` (or `# I. Completed Work`) with `##` / `###` task results, and `# 𝙸𝙸. Новые проблемы` (or `# II. New Problems`) with each distinct defect as `## N. <Problem>` and six nested subsections `### N.1` Metadata, `### N.2` Description (verbatim diagnostics), `### N.3` Causes (`>= 2` hypotheses per [DOC-2](#doc-2) plus source-project attribution), `### N.4` Culprit (provenance, test escape, and Journal `ꙮ` integrity), `### N.5` Solutions (`>= 2` methods per [DOC-3](#doc-3) with [FILE-6](01-file-boundaries.md#file-6) banner when applicable), and `### N.6` Recommended Remediation Plan.  
1. Standalone complex problem analyses: emit **four separate hierarchical analyses** (`# <Track>` -> `## 0`..`## 4` or `## N.1`..`## N.6`, never merging them): Primary Problem (`§1`), Culprit and Provenance (`§2`), Test and Verification Escape (`§3`), and Journal and Reporting Integrity (`§4`, auditing Unified Journal `ꙮ` under [FILE-3](01-file-boundaries.md#file-3), `Stop Gate`, and observability).  
Every defect metadata block (`### N.1` / `## 0`) contains tab-indented `json` generated via `harness.py problem-metadata` with a mandatory `"Issue"` key pointing to a unique, saved, `open`, unparented (`parent_number is None`), non-foreign parent GitHub issue created for that specific defect in the active turn (never duplicating one issue across problems, never linking closed, child, fabricated, or foreign-conversation issues; `--no-issue`/`null` is permitted only for non-GitHub workspaces or verified-clean companion audits).  
