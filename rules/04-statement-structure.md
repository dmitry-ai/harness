---
trigger: always_on
description: "Facts, hypotheses, solution methods, and compact documents"
---
# Statements
## DOC-1
Separate observation, source wording, hypothesis, implication, and recommended action.  
A fact requires primary evidence; co-occurrence of events does not prove causation, and a discovered defect does not prove client ignorance.  
For new publications, use typed F/H/M claims with observation scope, verification status, primary grounds, and dependency versions per the skill contract.  
Every number, count, date, or interval in a verified `observation`/`client_report` (`essence` and `response_excerpt`) must appear literally in the primary quote or follow from a verified calculation; frame any scope qualifiers inferred beyond the verbatim quote as a hypothesis (`H-*`) rather than a fact (`F-*`).  
An agent's own KB entry or a high expert score does not promote a supposition to a fact.  
## DOC-2
Frame any unknown or unproven explanation as a hypothesis: **essence**, **arguments for**, **arguments against**, and **expert plausibility in %** with the assessment basis.  
Cite concrete data from the specific client, alternatives, and missing checks; provide evidence per [LINK-1](02-link-standards.md#link-1).  
The finding `"no misconceptions established"` is valid; the template does not require inventing theories or objections.  
Distinguish found counterevidence, absence of found counterevidence, and unavailability of verification.  
An empty `against` list is permissible with `counterevidence`: `status` (`not_found`/`unavailable`), reviewed sources, and limitations; a dummy or confirming quote does not fill the gap, and the score of an unverified hypothesis without a counter-observation cannot exceed `75%`.  
For causal explanations and misconception hypotheses (`causes`, `misconceptions`), record the considered alternatives (including a literal reading of the client's words) and the discriminating check; matching symptoms do not establish a specific hidden setting or mechanism.  
Restating a failure does not establish its cause; without discriminating evidence, retain the conclusion `"cause not established"`.  
Having no grounds to prefer one version over another does not establish equiprobability or `50/50`; equal prior estimates require an explicitly stated assumption, while other percentages require their own expert basis without artificial normalization to 100%.  
## DOC-3
For each solution method, state: **essence**, **arguments for**, **arguments against**, and **score in %** with an explicit criterion and basis.  
Link the method to a cause or task via ID; state material applicability conditions and limitations.  
Unavailability of a client's private system (admin panel, ad account, logs) does not allow declaring the status of facts about a public system (storefront, public API, DNS) confirmed by deterministic observation to be incomplete, hypothetical, or conditional (`limited`/`if`).  
A missing check of a private console restricts only the steps inside that console (availability of permissions/buttons), and strictly forbids assuming that already proven properties of the public storefront might be false; an `if` clause does not replace inspecting the observable catalog.  
A method's score represents expert suitability under the named criterion, not a promise of success or the probability of a hypothesis.  
State applicability conditions and an observable verification criterion for the result; justify defect severity by impact while preserving sample boundaries.  
## DOC-4
Do not use Markdown tables; start every sentence on a new line.  
In Markdown, end every sentence inside a paragraph with two trailing spaces before the newline (CommonMark hard line break: `  \n`) so lines do not collapse into a single run-on paragraph when rendered; do not insert blank lines between sentences of the same block.  
Do not turn ordinary connected prose into bulleted or numbered lists just to get line breaks: lists are permissible only for genuine enumerations of homogeneous items or when explicitly instructed.  
Connect compact numbered claims with links to their premises; do not fragment a causal chain into independent defects.  
Preserve hierarchy, format, and boundaries between analysis and recommendations; do not renumber stable IDs when sorting.  
Repeated `1.` markers are permissible for ordinary lists; addressable paragraphs carry explicit numbers.  
Accompany verification code with its actual output; extract large reusable code into a shared tool.  
