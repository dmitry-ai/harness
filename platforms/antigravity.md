# Antigravity Adapter

New investigations and reviews use the shared [evidence contract](../skills/upwork-init/references/evidence-contract.md) and [workflow](../skills/upwork-init/references/workflow.md).  
A review package binds the current requests, exact response bytes, and claim map to KB/Evidence; `routine` requires a justified basis, while `significant` requires two independent A.A reviewers.  
The auditor returns the original JSON verdict in its final native message; the post-completion launch receipt is passed separately, and parent dispositions of findings are recorded as separate entries.  
Metadata for primary/A.A/A.F is saved via `native-executor-metadata`: `requested`/`observed`, sources, and verification status are tracked separately; inheritance or tier does not prove the actual runtime mode.  

Every internal command accepts `--platform antigravity`; it is the backward-compatible default.  
The `runtime.json` profile defines A.A inheritance, the A.F preset/tier, the browser, and the Folders path.  
The model for the primary `/upwork-init` chat is selected in the UI; the A.A role does not switch it.  
Delegate via `invoke_subagent` in the current UI conversation: A.A uses `self` with `Model: inherit`, and A.F uses `af-worker` with its configured tier.  
A tier does not prove the exact model or effort; verify the available actual metadata.  
Do not launch models via hidden CLI sessions.  
Shared rules and skills are connected via existing `.agents/{rules,skills,agents}.json` manifests.  
After establishing the root of the primary conversation, execute `turn-begin <root> --conversation <native-uuid> --platform antigravity`; routine analysis of rules also follows the [turn completion contract](../references/turn-completion.md#turn-begin).  
Before publishing the final response, write the UTF-8 response text via `write_file` to `<root>/ꘖ/data/scratch/answer.md`, run `answer-prepare <root> --response-file "<root>/ꘖ/data/scratch/answer.md" --consume-input --conversation <native-uuid> --platform antigravity` (do not pipe Cyrillic or `ꘖ`/`ꙮ` through a PowerShell `| python` pipeline without `[System.Text.UTF8Encoding]::new($false)`), and [publish the saved bytes](../references/turn-completion.md#answer-preparation).  
`/upwork-cleanup` executes the shared skill `skills/upwork-cleanup/SKILL.md`: it cleans both systems of empty projects older than 72 hours while preserving all of `proposals/daily`.  
`/df-article` executes the article profile, and `/df-proposal` executes the Upwork proposal profile.  
The shared procedure and review contract reside in `references/client-text/`; A.A uses `self` with `Model: inherit`.  
Standard `init`/`register` request registration of the same directory in both systems; `--platform` indicates the executing environment, while `--target` on `register` repairs a single registration.  
In Antigravity, native IDs and settings are saved and the Folders branch is assigned; Codex uses the separate Shared-Projects adapter.  
A secondary error or pending state does not block the active registration; check the individual receipts, `complete`, and `all_registered`.  
Without `CODEX_HOME`, the source profile for Codex registration alone is taken from `runtime.platforms.codex.registration_profile`; it is never used as a chat history source.  
`adopt-requests` reads the exact `USER_INPUT` steps of the current parent chat from the native store.  
In a new chat without a job URL, request ownership is confirmed by a single exact project `workspace_uri` or an explicit `"Project root: <absolute path>"` in the user message; a shared repository root or ambiguous multi-workspace is insufficient.  
`native-review-proof` verifies the parent, child `self`/`inherit`, prompt neutrality (absence of pre-filled `approved`/`supported`/`direct`/`findings: []`), read-only operation of the reviewer inside the current project root without accessing neighboring projects, successful completion, and the assigned KB package (`review-input`).  
If the native store format is unavailable, record the exact current request via `resume --request-file`; do not reconstruct historical texts from summaries.  
Creation, research, continuation, review, and completion behavior are governed by the shared skill.  
