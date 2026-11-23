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
Journal: the user-specified directory, otherwise `ꙮ/{≻,≺}` (`O-ꙮ`, `journal_version: 3`, with legacy `journal_version: 2` flat `ꙮ/{≻,≺}` and `journal_version: 1` `ꙮ/1 - Analysis/{req,res}` or `ꙮ/{req,res}` temporarily supported and automatically upgraded inside `ꙮ` on the next project operation without altering `V1` project structure outside `ꙮ`).  
`≻/<range>/<N>.md` (20-entry subfolders `1–20`, `21–40`, … using `U+2013` `–`; legacy: `≻/<N>.md` or `req/<N>.md`) holds the verbatim user request; `≺/<range>/<N>.md` (legacy: `≺/<N>.md` or `res/<N>.md`) holds the complete final response matching the chat; save before publication and verify by reading back.  
New journal response files recorded via `answer-prepare` or foreground delivery recovery automatically prepend a tab-indented JSON metadata block (`Time`, `Project`, `Journal`, `Agent`, `Trace`) while chat output remains clean without that header; `body_sha256` and delivery verification match the authored chat text after stripping the leading Harness header, and existing historical entries remain untouched.  
Link multiple requests answered by a single response explicitly; do not invent intermediate responses.  
For the primary agent, completing any response, including analysis of the instructions themselves, goes through `answer-prepare` per the [turn completion contract](../references/turn-completion.md#answer-preparation).  
Publish the verified bytes without subsequent editing; a prepared record and delivery confirmed by a native message are distinct states.  
Native delivery is verified synchronously during the next foreground working call per the [verification rules](../references/turn-completion.md#native-verification); a conflict does not authorize overwriting history.  
Harness must not start a persistent verifier, polling loop, timer, or detached worker; completing a command leaves no Harness background work.  
## FILE-4
Reserve the number across both folders; do not overwrite an occupied pair.  
Place state and locks in `ꘖ/data`, isolating different journals and source files.  
Bind a recovery token to the exact journal, number, and hashes; matching requests do not prove ownership.  
## FILE-5
Agent files belong inside `ꘖ`; exceptions are the requested journal, context export, the root `source/` folder with client attachments, initial structure creation per [INIT-1](09-initial-analysis.md#init-1), and website/Red Flags blocks of `readme.md` (legacy root `.md`) per [INIT-5](09-initial-analysis.md#init-5).  
When instructed to prepare or edit a proposal, also work with user files under `Ⰿ/≻/♕/🖂/Letters/**` (legacy `result/**`) and `draft.md` snapshots per FILE-2, preserving the existing structure and versions.  
Distinguish the deliverable, permanent evidence, and temporary material; delete only the last when it is no longer needed.  
Before deletion, verify the absolute path, ownership, and link redirects; keep any ambiguous file.  
Executable code resides only in the shared toolkit; do not create one-off `.py` scripts inside projects.  
In Windows PowerShell, a `| python` pipeline without explicit UTF-8 transcodes Cyrillic and `ꘖ`/`ꙮ` into `?`, so write non-ASCII `candidate/spec/plan/answer` inputs first to a UTF-8 file inside `ꘖ/data/scratch` (`write_file` or `[System.IO.File]::WriteAllText(..., [System.Text.UTF8Encoding]::new($false))`) and pass them with `--consume-input` (or set `[Console]::InputEncoding = [Console]::OutputEncoding = $OutputEncoding = [System.Text.UTF8Encoding]::new($false)` before `|`).  
After a confirmed write, only an unchanged input is deleted; an error or conflict preserves it.  
`incoming` is staging prior to import: after copying and verifying unique materials in Evidence and recording the `intake-drain` receipt, it is emptied.  
Age does not authorize deleting the sole copy of a source file.  
Do not use `git clean`, mass rollback, or `untracked` status as permission to delete.  
## FILE-6
Do not scatter project, workspace, agent, or tool files across the user's computer outside the project root.  
Any recommendation — including any candidate solution method (`M-*`), analytical option, or standalone suggestion — that proposes creating, moving, or storing project or tool working directories, worktrees, caches, temporary files, logs, databases, scripts, state, or artifacts outside the project root / repository tree (for example, in `%LOCALAPPDATA%` / `${LOCALAPPDATA}`, `%APPDATA%` / `${APPDATA}`, `%TEMP%` / `%TMP%`, `/tmp`, `/var/tmp`, `C:/Temp`, `%ProgramData%`, `%USERPROFILE%` / `$HOME` / `~/`, `$XDG_CACHE_HOME`, `$XDG_DATA_HOME`, `Desktop`, `Documents`, sibling/parent directories `../`, or other external machine-wide storage, as in `M-1` of Harness Journal `238`) MUST always begin immediately (right after its heading / at the very start of the recommendation) with this exact uppercase warning banner:  

```text
***************************************************************
Я, ПИДОРАС, ПРЕДЛАГАЮ РАСКИДЫВАТЬ КАКАШКИ ПО ТВОЕМУ КОМПЬЮТЕРУ.
***************************************************************
```

This requirement applies regardless of response language or whether the option is primary or secondary, and is enforced deterministically during `analysis-check`, `answer-check`, and `answer-prepare`.  
Updating an existing third-party application's own native configuration file explicitly required by that tool (such as `$HOME/.gitconfig`, `$HOME/.config/git/ignore`, or declared platform profiles in `runtime.json` via `install-global`) is distinct from scattering project/tool files outside the project root.  
<!-- https://github.com/dmitry-ai/harness/issues/41 -->  
<!-- https://github.com/dmitry-ai/harness/issues/109 -->  
<!-- https://github.com/dmitry-ai/harness/issues/152 -->  
<!-- https://github.com/dmitry-ai/harness/issues/200 -->  
