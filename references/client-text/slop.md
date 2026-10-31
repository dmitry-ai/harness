# Substantive Defects and Their Surface Signals

The lexicon in [lexicon.json](lexicon.json) is shared across articles, proposals, letters, and chat responses; each pattern records its underlying cause, remedy, and source.  
`text_core.py` checks shared prose, commands, and responses; `article.py` checks article parts, anchors, and premise graphs; `proposal.py` checks flat/nested items and Upwork submission fields.  
Do not "fix" a finding merely by swapping a connective or deleting a hedge: an unverified claim does not become a fact by removing a qualifier.  

[Signs of AI writing](https://en.wikipedia.org/wiki/Wikipedia:Signs_of_AI_writing) catalogs observable stylistic patterns rather than proof of authorship or a list of universal bans.  
In this project, lexicon linting is an auxiliary check.  
Sufficiency of evidence, paragraph necessity, and accuracy of conclusions are verified through the block map and [independent review](review.md).  

1. `ARROW-CONNECTIVE`, `EN-*/RU-*`, `BOLD-LEADIN`, `APP-*`, and `SENT-*` flag redundant connectives after arrows, evaluative labels, leaked internal analysis scaffolding, and overloaded prose.  
1. `TEXT-OWNER` flags authored `your`; verbatim quotes and code blocks are exempt.  
The subject of technical analysis is the client's actual system.  
1. `STRUCT-*`, `ANCHOR-*`, `REF-*`, and `KEY-*` validate addressing; `GRAPH-*` validates article premise links and cycles.  
An unreferenced item may still serve the document's goal directly; that requires an explicit substantive disposition.  
1. `CODE-VOLATILE`, `CODE-UNREADABLE`, and `CODE-DUP-OUTPUT` flag volatile bundle filenames, unreadable extraction one-liners, and duplicated command output.  
Citing a historical bundle is permissible when the claim's scope is explicitly restricted to that capture.  
1. `SOURCE-UNVERIFIED` does not declare a page false: it means HTTP/anchor confirmation is missing and a real source capture or DOM observation is required.  
1. `RESP-DUP` flags high similarity to a prior response; `RESP-CLAIM` cross-checks claims about deleted fragments against the actual files; `RESP-PROCEDURAL` flags internal procedural narration in place of the deliverable.  

Project-specific regressions remain project data.  
Historical incidents: `proactivsports` req/res 4–5 — `→ because` and response repetition; `materaprima` req 4–6 — raw hashes and five-stage labels instead of a useful article; `wayse` req 219–487 — evidence and edit-scope boundaries; `adorncroft` req 1–168 — proposal structure, field limits, exact component names, and re-introduction of refuted claims.  
The presence of a lexicon token does not prove a substantive defect, and zero linter errors do not prove that the meaning is sound.  
