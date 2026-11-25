# Codex Adapter

These instructions apply in Codex within the Upwork workspace.  
The unified configuration for environments, roles, and models is `AI/harness/Ⰿ/≻/♕/⛯/runtime.json` relative to the repository root.  
The shared skill and workflow are in `AI/harness/Ⰿ/≻/♕/⛯/skills/upwork-init/SKILL.md`.  
The shared tool is `AI/harness/Ⰿ/≻/♕/⛯/scripts/harness.py` (`upwork_project.py` remains a compatibility alias).  
Pass `--platform codex` to every internal command; declared Codex instances and their `enabled` flags and `system_paths` live under `platforms.codex.instances` in `runtime.json`, and the active profile is determined from `CODEX_HOME` or passed explicitly via `--codex-profile` / `--instance` when ambiguous.  
`doctor --platform codex` reports role configuration, subagent selection policy, configured environments/instances, and verification limits; do not substitute its output for actual session metadata.  
The global profile `AGENTS.md` preserves personal instructions and points to the common `platforms/codex/AGENTS.md` bootstrap, which lists mandatory canonical sources.  
The bootstrap and role definitions are generated once by `build-native`; `install-global` connects enabled Codex instances with skill-directory links and individual file symlinks from `agents/<name>.toml` to the shared role definitions (disabled instances are skipped unless targeted explicitly with `--target-profile`).  
The installer retires its former owned `agents.<name>.config_file` block while preserving other profile configuration; role discovery through that block alone failed in the installed C1 session.  
Shared generation uses the central native-profile ownership receipt and lock from both entry points; project-specific loaders retain separate project ownership.  
After changing the set of paths, roles, or runtime configuration, run `build-native`, `build-native --check`, and `install-global --check`; use repeated `--target-profile` options for a scoped migration.  
Do not generate per-project skill wrappers or role copies; retire only exact receipt-owned legacy files while preserving manual changes and backups.  
Once the root of the primary conversation is established, run `turn-begin <root> --platform codex`; routine inspection of rules is also covered by the [turn completion contract](../references/turn-completion.md#turn-begin).  
Read rules in batches without output truncation from the `exec` token budget (do not concatenate all `rules/*.md` into a single `Get-Content` subcommand) and do not bundle `git` calls into a single `Promise.allSettled` batch before `turn-begin` completes and rule texts are loaded.  
Native instructions and role TOML files are generated; edit their canonical sources instead.  

A new analysis starts with the `/upwork-init <URL>` or `$upwork-init <URL>` skill.  
Cleanup of empty auto-created projects starts with `/upwork-cleanup` or `$upwork-cleanup`; the shared skill `skills/upwork-cleanup/SKILL.md` cleans enabled environments/instances while preserving all of `proposals/daily`.  
Articles use `/df-article` or `$df-article`, Upwork proposals use `/df-proposal` or `$df-proposal` (shared procedure `references/client-text/workflow.md`), analytical tasks or autonomous four-track separate complex problem analyses use `/df-analysis` or `$df-analysis` (`DOC-2`, `DOC-3`, `DOC-5`: Primary Problem plus separate Culprit/Provenance, Test & Verification Escape, and Journal & Reporting Integrity analyses), and Harness performance audits/optimization plans use `/df--harness--improvement--performance` or `$df--harness--improvement--performance` with `perf-timesheet` and `perf-profile-tests`.  
The workflow and five stages are shared across configured environments; the agent runs the commands while the user enters only requests.  
For A.A/A.F, use the native subagent tools of the current chat; check roles and subagent selection policy via `runtime`/`doctor`.  
If the tool supports selecting a named agent type, use the native role from `runtime`; if the API lacks that parameter, pass the role and shared `agents/worker.md` in the prompt without inventing unsupported arguments.  
The parent selects the subagent's model and effort based on task complexity, available models, and `runtime` policy.  
The model of the primary `/upwork-init` chat is determined by the current UI session; A.A is a responsibility role rather than a mandatory model name.  
Obtain available model identifiers and effort modes from the active environment rather than guessing them from memory.  
For straightforward extraction, a lighter available model may be chosen; for ambiguous substantive verification, choose sufficient depth.  
When there is no reason to switch models, fall back to inheriting the current model and effort.  
State the role, brief selection rationale, and required deliverable in the subagent prompt.  
When selecting a different model, pass its identifier and `reasoning_effort` explicitly to `spawn_agent`; in collaboration mode, use `fork_turns: none` and supply the required inputs.  
When inheriting, omit model and effort overrides.  
The native adapter verifies the parameters chosen by the parent against the child agent's actual `turn_context`.  
In an assignment to an independent auditor, explicitly specify role A.A, the exact `prepare-review` package path, sources, output report path, and completion criterion.  
The package binds the current requests, exact response bytes, claim map, KB, and Evidence; the risk category is defined by a justified specification without a default `routine`, while `significant` defaults to one adversarial A.A auditor in `review_mode: "falsifier"` per REVIEW-3 (escalating to two independent A.A auditors on `disproved_claims`, `needs_changes`, or prior significant findings; launch a fresh A.A subagent rather than reusing a session near context compaction).  
The child auditor first runs `review-input <project> --package <package-path> --platform codex` using the shared tool and prints the full JSON output to the native tool log.  
That command verifies package digests; the auditor then reads its modules and primary sources and performs the substantive review.  
A native assignment payload may be encrypted: the adapter links the parent and child ciphertext and confirms the specific package via the actual `review-input` call and its output.  
Ciphertext is never treated as human-readable text.  
Wait for completion using the native wait tool; use valid parent and child chat UUIDs for the `native-review-proof` receipt.  
The auditor returns the original `schema_version: 2` JSON verdict (with `package` and `package_sha256`) once in its final native message without duplicating the full JSON via intermediate messaging; `record-review` verifies the report file against that message and receives the launch receipt as a separate argument after completion.  
Record actual metadata for the primary executor, A.A, and A.F via `native-executor-metadata`; `requested` and `observed` are tracked separately, and unknown values are never backfilled from `runtime` defaults.  
Do not create user chats via `codex exec`, SDKs, or hidden model execution APIs.  

Codex registration uses only the existing Shared-Projects UI helper through its named pipe when Codex instances are enabled in `runtime.json`.  
Standard `init`/`register` service enabled targets from `runtime.registration.targets`; `--platform` indicates the executing environment, while `--target` on `register` selects a single registration to repair.  
`registrations` stores separate platform receipts; the Codex receipt records the shared ID, folder, and native profile IDs.  
`complete` refers to the active environment, and `all_registered` refers to all configured registration targets; preserve any secondary error or pending state and retry `register` when the application becomes available.  
`status: pending`/`complete: false` represents a saved request, not a completed registration.  
Wait for registration of the source profile using repeated idempotent `register` calls; verify `profiles` and `folder_path`.  
If the application is waiting for native folder trust confirmation, inform the user, save state, and resume after their reply.  
Do not write directly to `catalog.json`, `ui-folders.json`, SQLite databases, or global Codex registrations; do not forge `approvedBy`.  
The folder tree and project are shared across C1/C2, whereas collapsed branches and chats belong to the individual profile.  
When invoked from Antigravity without `CODEX_HOME`, `runtime.platforms.codex.registration_profile` defines the source profile for registration only; no such fallback applies when reading native evidence.  
`configure` maintains local `.agents` manifests; the shared workspace loader reads the project's `.agents/rules` and additional path bindings in `rules.json`.  
A local `developer_instructions` key is not created unless a prior manual override exists, so parent instructions continue to be inherited; `configure --check` verifies all configured environments.  
Native `developer_instructions` supplements standard instructions; `model_instructions_file` is not used.  
`inherits` and filters in `rules.json` are currently diagnosed as unsupported; do not declare such a configuration compatible until explicitly resolved.  
A shared Harness skill is discovered through the profile's link to its canonical `skills/<name>` folder; do not duplicate same-named skills across subprojects.  

The Codex adapter reads exact requests and review provenance from the selected profile in read-only mode.  
`adopt-requests` uses the UUID of the current chat (`CODEX_THREAD_ID`); before the final response, write the UTF-8 text to `<root>/ꘖ/data/scratch/answer-<turn_key>.md` via `[System.IO.File]::WriteAllText(..., [System.Text.UTF8Encoding]::new($false))` and run `answer-prepare <root> --response-file "<root>/ꘖ/data/scratch/answer-<turn_key>.md" --consume-input --platform codex` (do not pipe Cyrillic or `ꘖ`/`ꙮ` through a PowerShell `| python` pipeline without `[System.Text.UTF8Encoding]::new($false)`) per the [unified contract](../references/turn-completion.md#answer-preparation).  
Low-level `record-answer` is retained for compatibility and recovery, but does not by itself confirm delivery.  
In a new chat without a URL, request ownership is confirmed by the exact native project `cwd`; a shared repository `cwd` is insufficient.  
When continuing from the other platform, preserve its journal and evidence; the prior receipt platform remains part of provenance.  
Do not reconstruct requests from summaries and do not declare an unverified receipt confirmed.  
<!-- https://github.com/dmitry-ai/harness/issues/112 -->  
<!-- https://github.com/dmitry-ai/harness/issues/133 -->  
<!-- https://github.com/dmitry-ai/harness/issues/182 -->  
<!-- https://github.com/dmitry-ai/harness/issues/193 -->  
<!-- https://github.com/dmitry-ai/harness/issues/226 -->  
<!-- https://github.com/dmitry-ai/harness/issues/249 -->  
