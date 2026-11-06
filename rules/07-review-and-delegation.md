---
trigger: always_on
description: "AA/AF roles, substantive audit, and accountability"
---
# Delegation
## REVIEW-1
A.A is responsible for architecture, substantive conclusions, and the final deliverable.  
Delegate using the native subagent tool of the current UI conversation per the platform adapter: complex tasks, disputed conclusions, and substantive audits go to A.A; extraction and verification go to A.F.  
Model versions, effort, and inheritance are requirements of the unified `runtime.json`, not consequences of a role name.  
Verify available actual metadata; mark unknown fields as `"unverified"` and never hide discrepancies.  
If no suitable A.F is available, A.A performs simple work.  
Do not launch hidden model sessions via CLI: the user invokes `/upwork-init` and observes subagents in the UI.  
The platform adapter defines native calls and evidence provenance; environment differences do not alter verification criteria.  
Delegate large-scale primary research (exceeding 40 tool steps in an Upwork project turn) to A.F/A.A subagents or incrementally persist intermediate results in `ꘖ/KB` before exhausting the context window.  
When woken by a completion message from one of several parallel subagents while sibling subagents are still running, do not publish an intermediate status summary in chat or switch to the subagent's language; wait until all required subagents complete and prepare a single consolidated response via `answer-prepare`.  
## REVIEW-2
A worker assignment includes the goal, exact project root, inputs, permitted actions, and completion criterion.  
Before investigating, register the question, its impact on the analysis, and a single owner in the registry; reuse already saved results.  
Byte-level comparison, hashing, extraction, and formal validation are performed by deterministic tools; A.F is reserved for tasks requiring model judgment.  
Pass existing exact paths; an unavailable input is returned as a gap rather than a reason to guess neighboring files.  
Limit parallelism; prevent concurrent writes and competing control over the same browser session.  
A worker does not maintain the user journal and does not spawn new auditors without an instruction.  
## REVIEW-3
Before finalizing, check both what contradicts the KB and what is material yet missing from it.  
Two independent auditors are required for significant or disputed conclusions, architectural changes, or when instructed (or a single adversarial `A.A` falsifier in `review_mode: "falsifier"` after deterministic Stage 1 pre-flight checks when `disproved_claims` is empty and no prior significant findings exist); for a routine response, A.A performs both checks.  
Justify the risk classification for the current requests and claims: new material causal conclusions, conclusions about hidden configurations, and architectural or pricing changes cannot be downgraded to `routine` by a single parameter.  
A routine restatement requires previously verified, unchanged grounds; the absence of new HTTP requests does not by itself make a new conclusion routine.  
Do not call self-review an independent audit.  
In a tracked project with `workflow.json` prior to completing the `finalize` stage of initial analysis (and after `finalize`, whenever a response introduces new causal conclusions with `H-N` / `M-N` hypotheses or methods without subagent delegation in the current turn), adopting the current conversation requests via `adopt-requests` and passing `authorize` before `answer-prepare` is mandatory.  
## REVIEW-4
Provide the auditor with the sources and draft; require identification of the specific disputed claim and evidence per [DOC-2](04-statement-structure.md#doc-2).  
Verify each finding, fix it, or reject it with documented grounds; an external reply does not replace primary evidence.  
Verify worker launch, progress, completion, and output; an empty assignment does not create an agent.  
Freeze a package of current KB modules before the audit; the reviewer receives the package and primary evidence without other auditors' conclusions.  
A modified KB requires re-auditing affected conclusions; an independent audit record is bound to the actual UI session and the digest of the reviewed files, while unchanged claims whose `claim_merkle_hash` matches `ꘖ/data/verified-claims.json` may be reused via `use_merkle_delta: true`.  
The package binds the exact current requests, response candidate, map of its material claims, auto-discovered `Tier 0` entity sources, and confidence-stripped `blind_verification_predicates`; a new response version requires its own clearance even if the KB is unchanged.  
The parent's prompt to an independent auditor (`A.A`) must be neutral: pass the project root and package path (verified via `review-input`) without pre-filling positive outcomes (`approved`, `supported`, `direct`, `findings: []`) that omit negative schema alternatives.  
An independent auditor operates strictly read-only inside the current project root: it does not create or modify files, does not run generators in `scratch`, does not read neighboring projects, reads the candidate response in full (`1..total_lines` without truncated or non-contiguous partial slices), and confirms in `observed`/`tested_claim` every standalone number from an approved claim and `response_excerpt`.  
The auditor returns either a standard per-claim evaluation covering observation, inference, method sufficiency, alternatives, limitations, and verdict, or an adversarial falsifier report (`review_mode: "falsifier"`) listing `disproved_claims` backed by `Tier 0` primary sources and verbatim quotes.  
In `test_alignment`, compare the exact `target_claim` against the actual `tested_claim`, recording `direct`/`proxy`/`irrelevant` and a `"claim is false, test passes"` counterexample; `proxy` does not permit unqualified `supported` without a visible qualification, and `irrelevant` does not support the claim.  
The auditor verifies compatibility of recommendations with primary facts: a condition refuted by primary evidence (`dead-end condition`) requires a `needs_changes` verdict and cannot be approved by assuming subjective external moderation discretion.  
Preserve the original verdict immutable with verified native provenance; record parent dispositions of findings separately and never overwrite the auditor's result with them.  
`needs_changes` and open findings persist as working state and block completion; a new review attempt does not overwrite a prior report.  
<!-- https://github.com/dmitry-ai/harness/issues/47 -->
