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
For any defect, failure, or architectural problem, apply [df-analysis](../skills/df-analysis/SKILL.md) with hierarchical headings (flat `# 0`..`# 4` is forbidden):  
1. Mixed task+defect turns: split into `# 𝙸. Что сделано` (`# I. Completed Work`) and `# 𝙸𝙸. Новые проблемы` (`# II. New Problems`), with each defect as `## N. <Problem>` and `### N.1` Metadata, `### N.2` Description (verbatim diagnostics), `### N.3` Causes ([DOC-2](#doc-2) + owner), `### N.4` Culprit (provenance, test escape, Journal `ꙮ`), `### N.5` Solutions ([DOC-3](#doc-3), [FILE-6](01-file-boundaries.md#file-6)), `### N.6` Plan.  
1. Standalone analyses: emit four separate hierarchical tracks (`# <Track>` -> `## 0`..`## 4`, never merged): Primary (`§1`), Culprit (`§2`), Test Escape (`§3`), and Journal `ꙮ` / `Stop Gate` ([FILE-3](01-file-boundaries.md#file-3), `§4`).  
Each metadata block (`### N.1` / `## 0`) uses tab-indented `json` from `harness.py problem-metadata` with `"Issue"` set to a unique, saved, `open`, unparented, non-foreign parent GitHub issue for that defect (`--no-issue`/`null` only for non-GitHub workspaces or verified-clean audits).  
