# Independent Review of a Specific Text Version

`review-prepare` freezes the verbatim requests, goal, baseline, candidate, diff, full block map, KB claims, primary artifacts, and their SHA256 digests.  
The package does not require five-stage initial analysis state.  
The A.A reviewer runs with a fresh context and receives this package and the text profile; the prompt must not suggest a desired outcome.  
The reviewer loads the package via `review-input` and then reads the exact source bytes.  
Being read-only on project files does not restrict independent search, HTTP checks, or inspection of a permitted browser session.  
The reviewer never modifies the draft, KB, package, or other reviewers' verdicts.  
Do not pass the author's self-assessment to the reviewer as an established result.  

1. Compare the candidate against the exact instruction, mode, and permitted changes.  
Compare against the actual baseline rather than Git.  
1. Audit every substantive block, including `nonfactual`: role, factual assertions, scope, modality, and quantifiers.  
1. For each claim, state what is observed, what is inferred, the actual method, alternatives, limitations, and the disconfirming check.  
`test_alignment` records the exact target claim, the property actually tested, the relationship (`direct|proxy|irrelevant`), and a concrete counterexample.  
Compatibility with an explanation does not distinguish it from alternatives; a `proxy` test cannot receive `supported` for a broader claim.  
1. Verify the product, version, conditions, and meaning of every cited source.  
Read the primary ground, check the anchor and quote, and independently look up any missing confirmation.  
General product documentation does not establish a site's configuration, and a login page does not establish report contents.  
For every external URL, populate `source_reviews`: exact URL, verifiable `receipt`, substantive `assessment`, and outcome (`supported|unsupported`).  
The reviewer may generate its own receipt for the same candidate; an `approved` verdict requires full URL coverage and `supported` outcomes for all cited URLs.  
Primary file hashes are recorded in the verdict proof.  
See [review fields and limits](sources.md#review-and-limits).  
1. Recompute numbers from their operands, units, and formula; verify the property, filters, date range, denominator, and full sample coverage.  
1. Check for circular reasoning, refuted or stale grounds, and prior conclusions in the KB or text that were repeated after a correction.  
1. Explain what new substance each block adds toward the goal and which conclusion or recommendation it supports.  
Eliminate semantic repetition and restatement of the client brief.  
A technical property does not by itself establish business harm, necessity of a fix, or commercial impact.  
1. Verify medium formatting and the suitability of proposed actions for the actual system state; any promised result must be compatible with the documented conditions.  
Audit recommendation conditions (`if`): check whether any condition is already refuted by primary evidence in `Evidence/` (`dead-end condition`).  
If the catalog or network response already refutes the premise (e.g., presence of restricted products or parameters), return `needs_changes` with defect `REC-DEAD-END`.  
Never defer a check to subjective external moderation discretion when the storefront fact is already proven.  

The final native reply is the reviewer's authored JSON conforming to `report_contract` from `review-input`.  
Every block receives substantive evaluation fields and six `text_checks`; for each finding, specify the exact block, defect code, severity, and required action.  
Do not fill fields with generic placeholders like `"verified"`.  
A `needs_changes` verdict, including a prior unresolved verdict, cannot be overridden by author approval or by re-packaging the same bytes under a new name.  
Resolving a material finding requires a new independent verdict backed by a substantive basis and evidence; the revised candidate goes through a new `check` and review.  

Native provenance is verified by the shared infrastructure: `upwork_project.py native-review-proof` records the actual parent, child chat, read package, and final message, while `review-record` matches that proof against the submitted report.  
The parent never writes a verdict on behalf of the reviewer.  
An ordinary substantive text requires one independent A.A reviewer; material causal, architectural, financial, or administrative claims—or any significant finding—require two.  
Any change to the request, candidate, map, evidence, or KB invalidates the corresponding clearance.  
A mechanical edit does not certify semantic readiness for delivery.  
