---
name: df-article
description: "Writes and edits standalone technical articles in the df.tips/t/2725 format: two parts, addressable claims, reproducible evidence, and recommendations. Use for /df-article and work on such articles; use df-proposal for Upwork proposals."
---
# Article in the df.tips/t/2725 Format

Apply the [shared client text procedure](../../references/client-text/workflow.md) and [shared review contract](../../references/client-text/review.md).  
Shared contracts for evidence, permitted edits, file writing, and user responses reside exclusively there.  
Before drafting, read the [gold sample](references/2725.md) and [article format grammar](references/format.md) in full.  
The sample defines structural mechanics; never copy its facts or domain vocabulary into another project.  

Establish the goal: what the reader must understand or execute.  
Select the recommendations first, and then the observations and inferences required to support them.  
Part I contains those premises and the facts that directly answer the goal; Part II contains actionable steps backed by Part I premises.  
Do not dump the entire KB into the article.  
Every paragraph must contribute necessary new substance.  

Tool: `python <agents>/scripts/df_article.py`, where `<agents>` is the canonical `.agents` directory.  
`source` converts numbered headings into symbolic keys: headings `## @routes`, children `### @routes.invalid`, references `§@routes`, ranges `§§@routes-@crawl`, and anchor links `(#@routes)`.  
`render` computes numbers and links, preserves the existing anchor style including `<a name='§I.4.1'></a>`, and fails if any reference points to a deleted key.  
References to external standards, code literals, and verbatim quotes remain untouched.  
Use `render --diff` to preview a proposal and `render -o` to write a separate candidate file; the shared `apply` operation writes the registered target document.  

Upwork proposals use their own skill [df-proposal](../df-proposal/SKILL.md); letters use the shared procedure with `kind=letter` and the user-specified layout.  
Validate the deliverable and journal per the shared contract, then persist them as instructed by the user.  
