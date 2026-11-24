# Antigravity Adapter

New investigations and reviews use the shared [evidence contract](../skills/upwork-init/references/evidence-contract.md) and [workflow](../skills/upwork-init/references/workflow.md).  
A review package binds the current requests, exact response bytes, and claim map to KB/Evidence; `routine` requires a justified basis, while `significant` defaults to one adversarial A.A reviewer in `review_mode: "falsifier"` per REVIEW-3 and escalates to two independent A.A reviewers on findings or `needs_changes`.  
The auditor returns the original JSON verdict once in its final native `PLANNER_RESPONSE` message without duplicating the full JSON payload via `send_message` beforehand; the post-completion launch receipt is passed separately, and parent dispositions of findings are recorded as separate entries.  
Metadata for primary/A.A/A.F is saved via `native-executor-metadata`: `requested`/`observed`, sources, and verification status are tracked separately; a requested inheritance or tier does not prove the actual runtime mode.  

Every internal command accepts `--platform antigravity`; it is the backward-compatible default.  
The `runtime.json` profile defines the parent-driven subagent selection policy, agent roles (`self` for A.A, `af-worker` for A.F), the browser, and the Folders path without hardcoding model versions.  
The model for the primary `/upwork-init` chat is selected in the UI; the A.A role is a responsibility boundary rather than a fixed model name.  
Delegate via `invoke_subagent` in the current UI conversation: A.A uses `self`, A.F uses `af-worker`, and the parent agent selects the subagent's `Model` option based on task complexity and the options currently offered by the tool (defaulting to `inherit` when no switch is needed).  
A requested option or tier does not prove the exact runtime model or effort; verify the available actual metadata.  
Do not launch models via hidden CLI sessions.  
Shared rules and skills are connected via existing `.agents/{rules,skills,agents}.json` manifests.  
Every Antigravity instance (`A0`, `A6`, …) has its own `home` (`USERPROFILE`), `user_data_dir`, `.gemini/config`, and `.gemini/antigravity` backend; declare each instance with `enabled` and `system_paths` in `runtime.json` `platforms.antigravity.instances`, run `harness.py install-global`, and verify with `harness.py install-global --check` (also part of `doctor`), since manifests in one instance do not load rules in another.  
Use `harness.py instances [--conversation <uuid>]` or `harness.py metrics --conversation <uuid> [--instance <id>]` to resolve peer instance `system_paths` directly from `runtime.json` during quota/usage-limit handoffs and cross-instance audits without scanning the filesystem.  
After establishing the root of the primary conversation, execute `turn-begin <root> --conversation <native-uuid> --platform antigravity` (or `turn-begin <root> --conversation <native-uuid> --dry-run` for a read-only ownership check); in globally configured Antigravity instances, the `PreInvocation` handler (`check_pre_invocation.py` in `platforms/antigravity/hooks.json`) automatically initializes `turn-begin` on the first invocation of a primary turn in tracked workspaces, reserves the turn's Journal `ꙮ` step number(s) and updates the conversation title via the active instance's local `LanguageServerService/UpdateConversationAnnotations` RPC (`211` for a new conversation, `191, 204` when a new request is added to an existing conversation), injects the resolved `turn_key` via `injectSteps`, and terminates genuine project-binding errors immediately via `"terminationBehavior": "terminate"`, while routine analysis of rules also follows the [turn completion contract](../references/turn-completion.md#turn-begin).  
Before publishing the final response, write the UTF-8 response text via `write_file` to `<root>/ꘖ/data/scratch/answer.md`, run `answer-prepare <root> --response-file "<root>/ꘖ/data/scratch/answer.md" --consume-input --conversation <native-uuid> --platform antigravity` (do not pipe Cyrillic or `ꘖ`/`ꙮ` through a PowerShell `| python` pipeline without `[System.Text.UTF8Encoding]::new($false)`), and [publish the saved bytes](../references/turn-completion.md#answer-preparation).  
`/upwork-cleanup` executes the shared skill `skills/upwork-cleanup/SKILL.md`: it cleans all enabled instances of empty projects older than 72 hours while preserving all of `proposals/daily`.  
`/df-article` executes the article profile, `/df-proposal` executes the Upwork proposal profile, `/df-analysis` codifies the mandatory multi-hypothesis analytical framework and autonomous five-section complex problem analysis (`DOC-2`, `DOC-3`, `DOC-5`), and `/df--harness--improvement--performance` runs evidence-driven Harness performance audits and optimization plans via `perf-timesheet` and `perf-profile-tests`.  
The shared procedure and review contract reside in `references/client-text/`; A.A uses `self` with the parent-selected `Model` (defaulting to `inherit`).  
Standard `init`/`register` request registration of the same directory across all enabled platforms in `runtime.registration.targets` and all enabled Antigravity instances; `--platform` indicates the executing environment, while `--target` on `register` repairs a single registration.  
In Antigravity, native IDs and settings are saved and the Folders branch is assigned; Codex uses the separate Shared-Projects adapter.  
A secondary error or pending state does not block the active registration; check the individual receipts, `complete`, and `all_registered`.  
Without `CODEX_HOME`, the source profile for Codex registration alone is taken from `runtime.platforms.codex.registration_profile`; it is never used as a chat history source.  
`adopt-requests` reads the exact `USER_INPUT` steps of the current parent chat from the native store.  
In a new chat without a job URL, request ownership is confirmed by a single exact project `workspace_uri` (or single-folder `project_id` resource); a shared repository root or ambiguous multi-workspace is insufficient.  
`native-review-proof` verifies the parent, child `self` invocation and parent-selected model/inheritance consistency, prompt neutrality (absence of pre-filled `approved`/`supported`/`direct`/`findings: []`), read-only operation of the reviewer inside the current project root without accessing neighboring projects, successful completion, and the assigned KB package (`review-input`).  
If the native store format is unavailable, record the exact current request via `resume --request-file`; do not reconstruct historical texts from summaries.  
Creation, research, continuation, review, and completion behavior are governed by the shared skill.  
<!-- https://github.com/dmitry-ai/harness/issues/112 -->  
<!-- https://github.com/dmitry-ai/harness/issues/116 -->  
<!-- https://github.com/dmitry-ai/harness/issues/120 -->  
<!-- https://github.com/dmitry-ai/harness/issues/133 -->  
<!-- https://github.com/dmitry-ai/harness/issues/182 -->  
<!-- https://github.com/dmitry-ai/harness/issues/193 -->  
<!-- https://github.com/dmitry-ai/harness/issues/215 -->  
