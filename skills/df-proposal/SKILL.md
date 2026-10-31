---
name: df-proposal
description: "Writes, condenses, and edits Upwork proposals per user rules; validates plain numbering, § references, and per-field character limits. Use for /df-proposal and proposal work; use df-article for standalone articles."
---
# Upwork Proposal

Apply the [shared client text procedure](../../references/client-text/workflow.md) and [shared review contract](../../references/client-text/review.md).  
They are the sole sources of shared requirements for evidence, permitted edits, file writing, and user responses.  

Before drafting, read the [proposal format](references/format.md).  
When selecting a structural layout, read the matching profile in [examples.md](references/examples.md), then inspect the referenced historical file and the user's final revision.  
Historical samples illustrate layout patterns; the user's current rules take priority over legacy phrasing.  

A proposal is a standalone deliverable: it does not require a prior project article.  
Select material directly for the job post, the client's screening questions, and verified findings about the client's system.  
Never carry over Part I/II headings or HTML anchors from `/df-article` into a proposal.  

Tool: `python <agents>/scripts/df_proposal.py <lint|source|render|replay|response>`, where `<agents>` is the canonical `.agents` directory.  
Key-based editing uses plain lines `@forms …`, `@forms.reason …` and references `§@forms`, `§§@forms-@tracking`; rendered output uses `1. …`, `1.1. …`, `§1`, `§§1-3`.  
Numbering serves clarity and verifiable cross-references; it never dictates a fixed count of problems, questions, examples, or sub-items.  

The specific Upwork job post determines the number of submission fields and each field's character limit.  
Before finalizing, validate the Cover Letter and each screening question answer separately; total document length does not prove compliance with individual field limits.  
