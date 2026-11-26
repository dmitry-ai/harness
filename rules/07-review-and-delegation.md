---
trigger: model_decision
description: "Read when delegating work to A.A/A.F subagents, preparing or auditing independent reviews (prepare-review, falsifier mode), or authorizing workflow.json stages"
---
# Delegation
## REVIEW-1
A.A owns architecture, substantive conclusions, and the final deliverable; delegate via the native UI subagent tool (complex/disputed audits to A.A, extraction/verification to A.F, falling back to A.A when no A.F is available).  
Select subagent model and effort per [runtime.json](../runtime.json) policy (defaulting to parent inheritance when no switch is needed) without hardcoding model versions or launching hidden CLI model sessions; mark unverified runtime metadata `"unverified"`.  
In Upwork projects, delegate large-scale primary research (`> 40` tool steps) or persist intermediate `ꘖ/KB` findings incrementally; when parallel subagents finish one by one, wait for all siblings before publishing a single consolidated response via `answer-prepare`.  
When an implementation request spans `>= 3` independent tracks, open the parent and per-track child GitHub issues first, assign disjoint file boundaries to parallel `self` subagents in separate linked worktrees (or land each track individually via short-lived worktrees instead of a long-lived monolithic branch), and land each verified worktree sequentially onto `main` per [worktrees-and-testing.md](../scripts/docs/worktrees-and-testing.md).  
## REVIEW-2
Every worker assignment states goal, exact project root, existing exact inputs, permitted actions, and completion criterion; register each question and single owner before investigating and reuse saved results.  
Use deterministic tools for hashing, byte comparison, extraction, and schema checks, reserving A.F for model judgment; limit parallelism to avoid concurrent writes or browser contention, and never let workers maintain the user journal or spawn auditors uninstructed.  
## REVIEW-3
Before finalizing, check both contradictions against `ꘖ/KB` and material omissions; never label self-review an independent audit.  
Significant conclusions default to one adversarial A.A auditor in `review_mode: "falsifier"` (`prepare-review` after Stage 1 pre-flight checks) when `disproved_claims` is empty and no prior significant findings exist, escalating to two independent A.A auditors on `disproved_claims`, `needs_changes`, disputed conclusions, architectural changes, or explicit instruction.  
Justify risk classification explicitly (new causal, hidden-config, architectural, or pricing claims cannot be downgraded to `routine`; `routine` requires unchanged verified grounds).  
In tracked `workflow.json` projects before `finalize` (and afterward whenever introducing new `H-N`/`M-N` causal conclusions without subagent delegation), `adopt-requests` and `authorize` are mandatory before `answer-prepare`.  
## REVIEW-4
Freeze a `prepare-review` package binding current requests, candidate response, material claim map, auto-discovered `Tier 0` sources, and `blind_verification_predicates` (unchanged `claim_merkle_hash` entries may reuse `ꘖ/data/verified-claims.json` via `use_merkle_delta: true`); re-audit after any KB or response revision.  
Keep the parent prompt to A.A neutral (pass project root and package path verified via `review-input` without pre-filling positive verdict fields); never share another auditor's report.  
Independent auditors operate strictly read-only inside the current project root, read the full candidate response (`1..total_lines`), verify every standalone number in `observed`/`tested_claim`, evaluate `test_alignment` (`direct`/`proxy`/`irrelevant` plus counterexample), flag refuted `dead-end condition` recommendations as `needs_changes`, and emit the JSON verdict (`package`, `package_sha256`) once in their final native message without duplicating it via `send_message`.  
Preserve original verdicts immutably with verified native provenance, record parent dispositions separately, and keep `needs_changes` / open findings blocking until resolved.  
