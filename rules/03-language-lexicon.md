---
trigger: always_on
description: "Response language, exact terminology, semantic density, and numeric precision"
---
# Language
## TEXT-1
Reply in the language of the user's request; if the request has no natural-language prose (only a command, URL, path, code, or log), use `user_default_locale` from [runtime.json](../runtime.json) (consult when resolving default locale).  
Write to clients in the requested language (defaulting new English text to English US); never translate or restyle an existing document without instruction.  
## TEXT-2
Lead with the conclusion; let one item express one claim, piece of evidence, or inference.  
Eliminate repetition, self-praise, empty disclaimers, promises, and invented jargon; use the component or action as the grammatical subject in technical analysis, and never attribute motives or misconceptions without [DOC-2](04-statement-structure.md#doc-2).  
## TEXT-3
Use one consistent term per entity per source and glossary; reproduce UI labels verbatim (in `«»` for Russian or profiles that require it), wrap code and identifiers in backticks, and never add emoji of your own.  
## TEXT-4
State units, time periods, and justified precision for numbers; omit `.00` on integer counts.  
Never present expert percentages as statistical probabilities: state the basis and uncertainty per [DOC-2](04-statement-structure.md#doc-2).  
In authored English prose, prefer `website`, `frontend`, `e.g.`, and full verb forms while preserving official names and verbatim quotes.  
