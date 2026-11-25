# Legacy V1 Compatibility Reference

Read this reference only when inspecting, resuming, or migrating a legacy `V1` project (`fs_version: 1` or `journal_version: 1`/`2`).  
New projects use the `V2` layout (`fs_version: 2`, `journal_version: 3`) defined in [paths.json](../paths.json).  

## Shared Toolkit and CLI Aliases

1. Canonical shared source: `AI/harness/Ⰿ/≻/♕/⛯`; legacy `V1` shared path was `AI/harness/code`.  
1. Canonical CLI entry point: `scripts/harness.py`; `scripts/upwork_project.py` remains a backward-compatible alias.  

## Project Directory Layout (`fs_version: 1` vs `fs_version: 2`)

1. Root project overview card: `readme.md` in `V2`, `.md` in legacy `V1` `upwork` projects.  
1. Manual user KB directory: `🕮/Project.md` in `V2`, `KB/Project.md` in legacy `V1`.  
1. Proposal and letter deliverables: `Ⰿ/≻/♕/🖂/Letters/**` in `V2`, `result/**` in legacy `V1`.  
1. External DeepThink context export: `Ⰿ/≻/♙/Context/output/Context.md` in `V2`, `ꙮ/0/Context.md` in legacy `V1`.  

## Journal Layout (`journal_version: 1`/`2` vs `3`)

1. Current `O-ꙮ` (`journal_version: 3`) stores verbatim requests in `ꙮ/≻/<range>/<N>.md` and responses in `ꙮ/≺/<range>/<N>.md` using 20-entry range subfolders (`1–20`, `21–40`, … with `U+2013` `–`).  
1. Legacy `journal_version: 2` used flat `ꙮ/{≻,≺}/<N>.md`, and `journal_version: 1` used `ꙮ/1 - Analysis/{req,res}/<N>.md` or `ꙮ/{req,res}/<N>.md`.  
1. Legacy `ꙮ` layouts upgrade automatically in place inside `ꙮ` on the next project operation (or via `harness.py journal-upgrade`) without altering `V1` project directories outside `ꙮ`.  
