---
trigger: always_on
description: "Software design pattern grounding and independent architecture auditor invariants"
---
# Architecture
## ARCH-1
Ground every software architecture decision, design proposal, structural parent GitHub issue, and structural code change in established Software design or architecture patterns per [df-architecture](../skills/df-architecture/SKILL.md) (read when proposing architectures or structural code) and [patterns-catalog.json](../references/architecture/patterns-catalog.json) (canonical Wikipedia taxonomy).  
Specify `Pattern`, `Category`, `Intent`, `Participants`, `Collaboration`, and `Consequences`, or a justified `idiom_exception` when native language constructs remove GoF boilerplate.  
## ARCH-2
Significant architectural proposals and structural code changes require independent read-only falsifier verification by `arch-auditor` (`arch-prepare`, `arch-review-input`, `arch-record-review`), enforced via `ARCH-AUDIT-GATE`, `IssueMarkdownLinter`, `ANSWER_GATES`, `STOP_GATES`, and Git `pre-commit`.  
Never bypass `arch-auditor` via pattern-washing or disguised refactors; resolve `needs_changes` findings before coding, committing, or publishing.  
