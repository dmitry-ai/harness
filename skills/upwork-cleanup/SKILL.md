---
name: upwork-cleanup
description: "Cleans Antigravity and both Codex profiles of /upwork-init projects older than 72 hours with zero conversations while preserving all on-disk history; use for /upwork-cleanup or requests to clean up empty auto-created Upwork projects."
---
# Cleaning Up Empty Upwork Projects

Format the authored response and any text reports from all workers with human-readable links without URL encoding per [LINK-5](../../rules/02-link-standards.md#link-5); do not reformat internal registration URIs.  

A standard `/upwork-cleanup` invocation cleans both platforms regardless of which UI launched it.  
In Codex, `$upwork-cleanup` is also available.  
If the user asks for a preview or dry run only, run the check without `--apply`.  

Shared tool: `C:/work/research/provision/code/AI/harness/code/scripts/upwork_project.py`.  
Determine the active platform from the conversation and pass `--platform codex` or `--platform antigravity`.  

1. Run `cleanup --platform <platform>` and inspect the JSON output.  
2. For a normal run, execute `cleanup --apply --platform <platform>` for eligible projects; no extra confirmation prompt is needed.  
   Individual blocked projects do not prevent cleaning the remaining eligible projects.  
3. Report the count of removed projects and folders, preserved projects with conversations, and any material blockers.  
   State the `discovery` scope and any discovery `issues`: lack of confirmation for an early project does not mean the entire archive was verified or that no old projects exist.  
   Report projects with confirmed conversations only by their aggregate preserved count; do not list them individually or present them as blockers due to incomplete legacy metadata.  
   The tool excludes them from `unresolved_entries` prior to reporting (`excluded_with_conversations`).  
   A follow-up `cleanup` check confirms that removed registrations are gone.  
4. Before publishing, compose the complete final response without a date header and pipe it via stdin to `cleanup-report --answer - --platform <platform>` using the same shared tool.  
   Publish the verbatim `answer` field returned by the command: it contains the exact bytes written and verified by read-back.  
   Logging is mandatory even for dry-run previews, zero candidates, waiting on a closed profile, or cleanup errors; intermediate JSON dumps never substitute for the final response.  

The response log is saved to `C:/work/upwork/code/AI/log/cleanup/YYYY/MM/DD--HH-mm.md`.  
The first line is the `Europe/Istanbul` timestamp in `2026-10-18 00:49 UTC+3` format, followed by a blank line and the full response.  
Both the first-line timestamp and the file path derive from the same instant; subsequent reports within the same minute receive suffixes `--2`, `--3`, etc., without overwriting existing logs.  
If writing the log fails, report the write error; never claim that the log was saved when it failed.  

Only confirmed `/upwork-init` projects strictly older than 72 hours with zero conversations across Antigravity, C1, and C2 may be removed.  
Archived, child, and still-empty conversations all count as conversations; both project bindings and working directories (including subdirectories) are checked.  
Whenever history is unavailable or unknown, registration is ambiguous, or data is changing concurrently, preserve the project and state the reason.  
An unknown conversation count must never be treated as zero.  
New projects record `created_at` in `ꘖ/project.json`; for legacy projects, the tool uses the Windows directory creation time or falls back to the end of the request date in `Europe/Istanbul`.  
Absence of `ꘖ/project.json` in early projects does not exempt them from inspection: legacy `/upwork-init` provenance is confirmed by the three shared `.agents` manifests, the local project rule, and a matching job URL in `KB/Project.md`.  
Folder names and the `U.P.YYYY.MM.DD` suffix alone do not prove `/upwork-init` provenance; corrupted or contradictory evidence is preserved with diagnostics.  

Cleanup removes native Antigravity registrations, the shared catalog entry and native Codex C1/C2 registrations, Folders bindings, and only those empty folder branches that became empty as a result of this cleanup.  
Codex is updated exclusively through the installed Shared-Projects UI helper; direct writes to its JSON or SQLite stores are prohibited.  
If a required Codex profile is closed, the project is marked `pending` without queuing a deferred deletion; name the profiles that need to be opened and re-run the command once they are open.  
After a partial failure, a temporary `cleanupHold` prevents automatic re-registration; the next run resumes by the same ID after re-checking conversations.  
If a conversation appeared in the meantime, the tool clears the hold and restores any missing registrations with their original IDs.  
In Antigravity, an in-progress cleanup is tracked in `.gemini/config/projects/ꘖ/data/cleanup-pending.json` and removed once cleanup is confirmed.  
That temporary receipt stores the registration JSON and Folders branch needed for rollback on cancellation; no permanent ledger of deleted projects is kept.  
Codex removes native registrations first and deletes their shared metadata after Antigravity confirmation; if commit completion is interrupted, re-run the command.  

All files and subdirectories under `C:/work/upwork/code/proposals/daily` are preserved in full, including `.md`, `KB`, `source`, journals, agent KBs, and metadata.  
`proposals/daily/ꘖ/data/projects.json` is the permanent Upwork ID → historical folder index required for repeat inquiries and is never treated as disposable state.  
Registration receipts inside the archive are historical records of past actions rather than proof that a project is currently registered in the UI.  
Never delete native conversations, their attachments or logs, folder trust settings, shared backups, or unfinished staging directories.  
