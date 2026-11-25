---
trigger: always_on
description: "Write boundaries, unified journal, scratch hygiene, and FILE-6 anti-scattering banner"
---
# Files
## FILE-1
Modify only target files and required dependencies within instruction scope; preserve authored text, samples, comments, and third-party changes.  
Re-read the current on-disk file before writing; reconcile concurrent edits instead of overwriting with a stale copy.  
## FILE-2
Before the first edit to an existing client `draft.md` in a turn, snapshot its exact bytes via `snapshot_draft.py` per [upwork-init](../skills/upwork-init/SKILL.md#post-analysis-proposal-work) and [workflow.md](../references/client-text/workflow.md#scope-of-the-current-instruction).  
## FILE-3
Journal: user-specified directory, otherwise `ꙮ/{≻,≺}` in 20-entry range subfolders `1–20`, `21–40`, … (`≻/<range>/<N>.md` holds the verbatim request; `≺/<range>/<N>.md` holds the complete final response).  
Every primary-agent response goes through `answer-prepare` per [turn-completion.md](../references/turn-completion.md#answer-preparation) (read before preparing answers or handling Windows PowerShell UTF-8 scratch files).  
New journal response files automatically prepend a tab-indented JSON metadata header on disk while chat output remains clean; `body_sha256` matches the clean chat body, and verified bytes are published without post-editing.  
Native delivery is reconciled synchronously on the next foreground call; Harness never starts background verifiers, polling loops, or timers.  
## FILE-4
Reserve step numbers across both journal folders without overwriting an occupied pair; store service state and locks in `ꘖ/data`, binding recovery tokens to exact journal, number, and hashes.  
## FILE-5
Keep agent files inside `ꘖ` (exceptions: journal, requested context export, root `source/` attachments, and Upwork project cards/Red Flags per [upwork-init](../skills/upwork-init/SKILL.md)).  
Executable code resides only in the shared toolkit; never create one-off `.py` scripts inside projects.  
Write non-ASCII inputs to UTF-8-no-BOM files under `ꘖ/data/scratch/` and pass `--consume-input` (never pipe raw Cyrillic or `ꘖ`/`ꙮ` through default PowerShell encoding); delete only verified temporary files and never use `git clean` or mass rollback as deletion permission.  
## FILE-6
Do not scatter project, workspace, agent, or tool files outside the project root across the user's computer.  
Any recommendation, candidate solution method (`M-*`), or option proposing to create, move, or store working directories, worktrees, caches, temp files, logs, databases, scripts, state, or artifacts outside the project root (such as `%LOCALAPPDATA%`, `%APPDATA%`, `%TEMP%`, `%TMP%`, `/tmp`, `/var/tmp`, `%ProgramData%`, `%USERPROFILE%`, `$HOME`, `~/`, `$XDG_*`, `Desktop`, `Documents`, or `../`) MUST begin immediately after its heading with this exact uppercase warning banner (enforced in `analysis-check`, `answer-check`, and `answer-prepare`):  

```text
***************************************************************
Я, ПИДОРАС, ПРЕДЛАГАЮ РАСКИДЫВАТЬ КАКАШКИ ПО ТВОЕМУ КОМПЬЮТЕРУ.
***************************************************************
```

Updating a third-party application's own required native config (such as `$HOME/.gitconfig` or declared profiles via `install-global`) is distinct from scattering project files.  
