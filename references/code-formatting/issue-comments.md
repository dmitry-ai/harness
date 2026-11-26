# Issue URL Comment Placement Standard

Defines contextual placement, formatting, and author-header rules for required [EXEC-5](../../rules/08-execution-and-tools.md#exec-5) GitHub Issue URL references exempt from the no-agent-comments rule in [CODE-1](../../rules/11-code-formatting.md#code-1) and [CODE-3](../../rules/11-code-formatting.md#code-3).  
Derived from the author's production convention in `mage2pro/core` (`925` of `926` PHP issue comments placed directly at the modified block, function/method, class, constant, or statement; `757` of `766` multi-date stacks ordered oldest-first).  

## File Author Header

1. Write `YYYY-MM-DD Dmitrii Fediuk https://github.com/dmitrii-fediuk` at most **once per file**, in the file header with the file's creation date (`YYYY-MM-DD`), immediately after any mandatory line-1 preamble (`#!/...` shebang, `<?php`, `<?xml ...?>`, `@echo off`, or Windhawk `==WindhawkMod==` metadata).  
1. Never repeat `Dmitrii Fediuk https://github.com/dmitrii-fediuk` inside subsequent issue comments or below the file header.  
1. Omit all comments in RFC 8259 JSON files (see [JSON](other/json.md)) and omit HTML comments in shared `rules/*.md` files.  

## Contextual Issue Comment Placement

1. **Before the modified block (primary rule):** Place each GitHub Issue URL comment immediately before the specific modified code block — statement, `if`/`else`/`try`/`catch` branch, boolean operand, dict/array/config entry, CSS selector/rule, XML element, HTML tag, or test case — matching the target block's tab indentation (column 0 for XML `<!-- ... -->` per [XML](markup/xml.md)).  
1. **Function, method, or class header:** When an entire function, method, class, or test method is added or changed as a unit, place the issue comment immediately above its declaration (or inside its docblock header in PHP, Java, or JSDoc-documented JavaScript).  
1. **Other valid `mage2pro/core` placements:**  
   - Immediately before or trailing inline on a changed import/`use` line or short single-line statement (`use \Throwable as Th; # 2023-08-02 "Treat \Throwable similar to \Exception": https://github.com/mage2pro/core/issues/311`).  
   - Immediately before a newly added or changed constant, field, or module-level configuration object.  
   - Inside multi-line conditions, call argument lists, or object literals immediately before the added or fixed operand/entry.  
   - In the file header strictly when an entire file is newly created or rewritten wholesale as one indivisible unit.  
1. **Prohibited file-header dumping:** Never prepend or append issue URL comments to the top-of-file header above unchanged imports, package declarations, pragmas, or unrelated code during a partial edit; Harness enforces this deterministically in `PreToolUse` (`ISSUE-COMMENT-GATE`) and Git `pre-commit`.  

## Format, Chronology, and Historical Survival

1. Omit the author name and profile URL from issue comments; write the ISO date, optional quoted issue title, and exact GitHub Issue URL on one line when concise or wrapped across consecutive comment lines when long:  
   - Single-line form: `# 2026-11-26 "Short title": https://github.com/<owner>/<repo>/issues/<N>`  
   - Wrapped form: `# 2026-11-26` followed by `# "<Title>":` and `# https://github.com/<owner>/<repo>/issues/<N>`  
1. When multiple issues affect the same block, function, or class, order them chronologically **oldest-first** (ascending by date, then issue number).  
1. When backfilling historical commits in reverse chronological order and an older commit's original lines no longer exist verbatim in current code:  
   - If the code changed completely while the underlying idea survived, place the historical issue comment on the surviving block, function, or class that implements that idea so the original motivation remains traceable.  
   - If both the code and the underlying idea were completely replaced, omit the obsolete issue comment.  

## Language Comment Syntax

1. Python, Bash, PowerShell, INI, YAML, and PHP inline blocks: `# ...`  
1. JavaScript, TypeScript, Java, C, C++, C#, and LESS: `// ...` (or `/** ... */` docblocks for PHP/Java/JS class and method headers)  
1. CSS: `/* ... */`  
1. XML and HTML: `<!-- ... -->` (aligned at column 0 in XML per [XML](markup/xml.md))  
1. Windows Batch (`.cmd`, `.bat`): `REM ...`  
1. VBScript (`.vbs`): `' ...`  

## Illustrative Example

This example illustrates issue-comment placement only and is not part of any target program; never copy it into answers or target files.  

```python
# 2026-11-10 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from pathlib import Path
# 2026-11-20 "Add helper for resolving canonical project paths": https://github.com/example/repo/issues/14
def resolve_target(root: Path, rel: str) -> Path:
	base = root.resolve()
	# 2026-11-26
	# "Reject path traversal outside repository root":
	# https://github.com/example/repo/issues/42
	cand = (base / rel).resolve()
	if not cand.is_relative_to(base):
		raise ValueError(f'Path escapes root: {rel}')
	return cand
```
