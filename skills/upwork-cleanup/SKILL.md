---
name: upwork-cleanup
description: "Cleans enabled Antigravity and Codex instances declared in runtime.json of /upwork-init projects older than 72 hours with zero conversations while preserving all on-disk history; use for /upwork-cleanup or requests to clean up empty auto-created Upwork projects."
---
# Cleaning Up Empty Upwork Projects

Format the authored response and any text reports from all workers with human-readable links without URL encoding per [LINK-5](../../rules/02-link-standards.md#link-5); do not reformat internal registration URIs.  

A standard `/upwork-cleanup` invocation cleans all environments and instances that are enabled (`enabled: true`) in `runtime.json` regardless of which UI launched it; disabled environments or instances are skipped automatically without requiring Codex Desktop or missing sessions.  
In Codex, `$upwork-cleanup` is also available when Codex instances are enabled.  
If the user asks for a preview or dry run only, run the check without `--apply`.  

Shared tool: `C:/work/research/provision/code/AI/harness/Ⰿ/≻/♕/⛯/scripts/harness.py` (`upwork_project.py` remains a compatibility alias).  
Determine the active platform from the conversation and pass `--platform codex` or `--platform antigravity`.  

1. Run `cleanup --platform <platform>` and inspect the JSON output.  
2. For a normal run, execute `cleanup --apply --platform <platform>` for eligible projects; no extra confirmation prompt is needed.  
   Individual blocked projects do not prevent cleaning the remaining eligible projects.  
<!-- 2026-11-26 "Persist cleanup audit manifests and metadata headers aligned with FILE-3": https://github.com/dmitry-ai/harness/issues/308 -->  
3. Report the count of removed projects and folders, preserved projects with conversations or post-initialization work, any material blockers, and either the list of removed projects or a summary with a direct readable link to the sidecar audit manifest (`audit_manifest`, `.json`) saved by `cleanup --apply`.  
   State the `discovery` scope and any discovery `issues`: lack of confirmation for an early project does not mean the entire archive was verified or that no old projects exist.  
   Report projects with confirmed conversations only by their aggregate preserved count; do not list them individually or present them as blockers due to incomplete legacy metadata.  
   The tool excludes them from `unresolved_entries` prior to reporting (`excluded_with_conversations`).  
   A follow-up `cleanup` check confirms that removed registrations are gone.  
4. Before publishing, write the complete UTF-8-no-BOM final response (without a manual date header) to a project scratch file under `ꘖ/data/scratch/` per [FILE-5](../../rules/01-file-boundaries.md#file-5) and record it via `cleanup-report --answer-file <scratch-path> --consume-input [--manifest <audit_manifest>] [--project <root>] --platform <platform>` (avoid raw PowerShell stdin pipes for Cyrillic or Unicode text).  
   In every tracked workspace, also complete [FILE-3](../../rules/01-file-boundaries.md#file-3) (`answer-prepare`) with the exact clean response body returned in `answer` before publishing in chat.  
   Logging is mandatory even for dry-run previews, zero candidates, waiting on a closed profile, or cleanup errors; intermediate JSON dumps never substitute for the final response.  

The response log is saved to `C:/work/research/provision/code/AI/harness/Ⰿ/≺/Logs/Cleanup/☰/YYYY/MM/DD--HH-mm.md` with a standard tab-indented Harness JSON metadata header (`Time`, `Project`, `Journal`, `Agent`, `Trace`, and `Trace["Cleanup Manifest"]` linking the sidecar `.json` manifest), while `answer` returns the clean body for chat publication.  
On every `cleanup --apply` run, Harness also writes an immutable structured sidecar JSON audit manifest `YYYY/MM/DD--HH-mm.json` in the same log directory containing `metadata`, `cutoff`, `active_instances`, `history_instances`, `skipped_disabled_instances`, `counts`, `discovery`, and detailed `removed_projects` records (`root`, `job_id`, `project_id`, per-instance IDs and base64 native registration snapshots, pruned `Folders` IDs and ancestry snapshots for one-step rollback, `created_at`, `effective_activity_at`, `age_basis`, and `conversations`).  
Both the metadata `Time` (`Europe/Istanbul`, `2026-10-18 00:49 UTC+3`) and the file path derive from the same instant; subsequent reports or manifests within the same minute receive suffixes `--2`, `--3`, etc., without overwriting existing logs.  
If writing the log fails, report the write error; never claim that the log was saved when it failed.  

Only confirmed `/upwork-init` projects whose latest lifecycle activity (`effective_activity_at = max(created_at, workflow.stages.finalize.time, renamed_from[*].at, handed_off_conversation, latest_journal_pair)`) is strictly older than 72 hours, with zero conversations across all declared local instances (including read-only scanning of readable `state_*.sqlite` and `conversation_summaries.db` files of temporarily disabled instances) across both current `root` and historical `renamed_from` paths, and with no post-initialization deliverables (`result/`, `Letters/`, `Ⰿ/≻/♕/🖂`) or multi-turn journal work beyond initial `/upwork-init`, may be removed.  
Archived, child, and still-empty conversations all count as conversations; both project bindings (including `registrations.json` native IDs) and working directories (current and `renamed_from`, including subdirectories) are checked.  
Whenever history is unavailable or unknown, an existing disabled-instance database is corrupt or linked, registration is ambiguous, or data is changing concurrently, preserve the project and state the reason.  
An unknown conversation count must never be treated as zero.  
New projects record `created_at` in `ꘖ/project.json`; for legacy projects, the tool uses the Windows directory creation time or falls back to the end of the request date in `Europe/Istanbul`, then promotes `effective_activity_at` from any newer lifecycle event (`workflow.finalize`, `project.renamed_from`, `handed_off_conversation`, `journal.latest_pair`).  
Absence of `ꘖ/project.json` in early projects does not exempt them from inspection: legacy `/upwork-init` provenance is confirmed by the three shared `.agents` manifests, the local project rule, and a matching job URL in `KB/Project.md`.  
Folder names and the `U.P.YYYY.MM.DD` suffix alone do not prove `/upwork-init` provenance; corrupted or contradictory evidence is preserved with diagnostics.  

Cleanup removes native registrations across enabled Antigravity instances (and when Codex is enabled, the shared catalog entry and native Codex registrations), Folders bindings, and only those empty folder branches that became empty as a result of this cleanup.  
Codex is updated exclusively through the installed Shared-Projects UI helper; direct writes to its JSON or SQLite stores are prohibited.  
If a required Codex profile is closed, the project is marked `pending` without queuing a deferred deletion; name the profiles that need to be opened and re-run the command once they are open.  
After a partial failure, a temporary `cleanupHold` prevents automatic re-registration; the next run resumes by the same ID after re-checking conversations.  
If a conversation appeared in the meantime, the tool clears the hold and restores any missing registrations with their original IDs.  
In Antigravity, an in-progress cleanup is tracked in `.gemini/config/projects/ꘖ/data/cleanup-pending.json` and removed once cleanup is confirmed.  
That temporary receipt stores the registration JSON and Folders branch needed for atomic in-flight rollback, while the permanent sidecar manifest `Logs/Cleanup/☰/YYYY/MM/DD--HH-mm.json` preserves the full audit trail and base64 rollback snapshots after completion.  
Codex removes native registrations first and deletes their shared metadata after Antigravity confirmation; if commit completion is interrupted, re-run the command.  

All files and subdirectories under `C:/work/upwork/code/proposals/daily` are preserved in full, including `.md`, `KB`, `source`, journals, agent KBs, and metadata.  
`proposals/daily/ꘖ/data/projects.json` is the permanent Upwork ID → historical folder index required for repeat inquiries and is never treated as disposable state.  
Registration receipts inside the archive are historical records of past actions rather than proof that a project is currently registered in the UI.  
Never delete native conversations, their attachments or logs, folder trust settings, shared backups, or unfinished staging directories.  
