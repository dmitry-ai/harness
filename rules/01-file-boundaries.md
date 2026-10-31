---
trigger: always_on
description: "Write boundaries, journal, snapshots, and cleanup"
---
# Files
## FILE-1
Modify target files and required dependencies within the scope of the instruction; preserve authored text, samples, and third-party changes.  
Re-read the current version before writing; if a concurrent edit occurred, reconcile the changes instead of overwriting it with a stale copy.  
## FILE-2
Before the first edit to an existing `draft.md` in a turn, save its exact bytes to a sibling `draft.prev.md` and an archive with the turn and file ID; verify the match.  
Do not overwrite the snapshot with an intermediate revision; save new user edits separately.  
## FILE-3
Journal: the user-specified directory, otherwise `ꙮ/1 - Analysis/{req,res}` (or `ꙮ/{req,res}` in repositories with a root Unified Journal).  
`req/N.md` holds the verbatim user request; `res/N.md` holds the complete final response matching the chat; save before publication and verify by reading back.  
Link multiple requests answered by a single response explicitly; do not invent intermediate responses.  
For the primary agent, completing any response, including analysis of the instructions themselves, goes through `answer-prepare` per the [turn completion contract](../references/turn-completion.md#answer-preparation).  
Publish the verified bytes without subsequent editing; a prepared record and delivery confirmed by a native message are distinct states.  
The independent verifier records the actually delivered text per the [verification rules](../references/turn-completion.md#native-verification); a conflict does not authorize overwriting history.  
## FILE-4
Reserve the number across both folders; do not overwrite an occupied pair.  
Place state and locks in `ꘖ/data`, isolating different journals and source files.  
Bind a recovery token to the exact journal, number, and hashes; matching requests do not prove ownership.  
## FILE-5
Agent files belong inside `ꘖ`; exceptions are the requested journal, context export, the root `source/` folder with client attachments, initial structure creation per [INIT-1](09-initial-analysis.md#init-1), and website/Red Flags blocks of the root `.md` per [INIT-5](09-initial-analysis.md#init-5).  
When instructed to prepare or edit a proposal, also work with user files under `result/**` and `draft.md` snapshots per FILE-2, preserving the existing structure and versions.  
Distinguish the deliverable, permanent evidence, and temporary material; delete only the last when it is no longer needed.  
Before deletion, verify the absolute path, ownership, and link redirects; keep any ambiguous file.  
Executable code resides only in the shared toolkit; do not create one-off `.py` scripts inside projects.  
In Windows PowerShell, a `| python` pipeline without explicit UTF-8 transcodes Cyrillic and `ꘖ`/`ꙮ` into `?`, so write non-ASCII `candidate/spec/plan/answer` inputs first to a UTF-8 file inside `ꘖ/data/scratch` (`write_file` or `[System.IO.File]::WriteAllText(..., [System.Text.UTF8Encoding]::new($false))`) and pass them with `--consume-input` (or set `[Console]::InputEncoding = [Console]::OutputEncoding = $OutputEncoding = [System.Text.UTF8Encoding]::new($false)` before `|`).  
After a confirmed write, only an unchanged input is deleted; an error or conflict preserves it.  
`incoming` is staging prior to import: after copying and verifying unique materials in Evidence and recording the `intake-drain` receipt, it is emptied.  
Age does not authorize deleting the sole copy of a source file.  
Do not use `git clean`, mass rollback, or `untracked` status as permission to delete.  
