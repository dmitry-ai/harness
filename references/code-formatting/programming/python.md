<!-- 2026-11-23 "Add Python and INI formatting standards derived from reference pipelines": https://github.com/dmitry-ai/harness/issues/156 -->  
# Python Formatting Standard

Inherits all general rules from [CODE-1](../../../rules/11-code-formatting.md#code-1) (tab indentation, zero blank lines, single return point, variable `r`, Yoda comparisons, shorter `if` branch above longer `else` branch, single quotes by default, alphabetical ordering, no unrequested comments).  
Derived from `google-ads-negative-keywords-pipeline/main.py` (primary hand-authored reference) and the Arturo Navarro Python scripts and AI instruction logs (`Code/Current` and `AI/**/req/*.md`), aligned with current Harness Python conventions.  

## Indentation, Blank Lines, and Imports

1. Indent all new Python code with tab characters (`\t`) and never mix tabs and spaces within a file (Python 3 raises `TabError` on mixed indentation); when editing a legacy space-indented file (such as `main.py`), preserve its existing indentation per [CODE-1](../../../rules/11-code-formatting.md#code-1).  
1. Write zero completely blank lines anywhere in new Python files (including between imports, top-level `def` / `class` definitions, and statements), honoring the explicit zero-blank-line requirement from `P.md` and the Arturo Navarro instruction logs.  
1. Group imports with `from ... import ...` statements first (sorted alphabetically), immediately followed by `import ...` statements (sorted alphabetically), without blank lines between groups.  
1. Use UTF-8 encoding and LF line endings.  

## Quotes, Comparisons, and Control Flow

1. Use single quotes (`'...'`) for all string literals and f-strings (`f'...'`); use double quotes (`"..."`) only when the string contains an unescaped single quote or avoids awkward escaping.  
1. Place constants, literals, and types on the left in comparisons and identity checks (`None is tz_env`, `None is not x`, `200 != response.status_code`, `200 == response.status_code`, `1 == len(items)`, `0 < len(summaries)`, `dict == type(err)`, `'' != asin`, `'__main__' == __name__`).  
1. Place the shorter branch above the longer branch in `if` / `else` blocks, and prefer concise conditional expressions (`a if cond else b`), comprehensions, and `list(dict.fromkeys(r))` for order-preserving deduplication.  
1. Keep at most one `return` statement per function and name the accumulated result variable `r`, omitting `r` whenever `return <expression>` directly suffices; bare `return` to terminate a generator loop (`yield`) is permissible where Python generator semantics require it.  
1. Keep functions modular rather than monolithic, and maintain alphabetical order for top-level constants, functions at the same scope level, methods within a class, and non-ordered dict keys.  

## Literals, Helpers, I/O, and Identifiers

1. In multi-line dicts and lists of hand-authored scripts, place a leading comma `,` at the start of continuation lines (`'DE': 'A1PA6795UKMFR9'\n\t,'ES': 'A1RKKUPIHCS9HS'`); preserve existing comma style when modifying existing files.  
1. Use concise one-line `lambda` helpers for tiny local transformations (`fp = lambda v: os.path.join(os.path.dirname(__file__), v)`) and nested `def` helpers when logic belongs strictly to one enclosing function.  
1. Always pass `encoding='utf-8'` explicitly on text file I/O (`open(..., encoding='utf-8')`, `Path(...).read_text(encoding='utf-8')`).  
1. When serializing JSON output files, format with `indent='\t'`, `ensure_ascii=False`, and `sort_keys=True` where deterministic alphabetical key ordering is required (see [JSON](../other/json.md)).  
1. Determine local timezones programmatically from the runtime environment rather than hardcoding UTC offsets.  
1. Guard script entry points with `if '__main__' == __name__:`.  
1. Historical note on `main.py` Unicode sigils: the hand-authored `main.py` reference uses personal Unicode identifier prefixes (`ⵗ` for imported callables such as `ⵗenv` / `ⵗchunked` and `ᛡ` for local client or config bindings such as `ᛡmax` / `ᛡopenai`); default to plain ASCII `snake_case` identifiers in general code unless the user requests sigil prefixes or an existing file already uses them.  

## Illustrative Example

This example illustrates formatting only and is not part of any target program; never copy it into answers or target files.  

```python
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo
import json
import os
def load_config():
	cfg_path = Path(os.path.dirname(__file__)) / '.ini'
	return {
		k.strip(): v.strip().strip('\'"') for k, v in (
			line.split('=', 1) for line in cfg_path.read_text(encoding='utf-8').splitlines() if '=' in line
		)
	}
def normalize_items(items):
	r = []
	for item in items:
		if 'attributes' in item:
			item['attributes'] = dict(sorted(item['attributes'].items()))
		r.append(item)
	r.sort(key=lambda x: x.get('sku', ''))
	return r
def save_report(data, error_content):
	os.makedirs('res', exist_ok=True)
	tz_env = os.environ.get('TZ')
	stamp = datetime.now(None if None is tz_env else ZoneInfo(tz_env)).strftime('%Y-%m-%d--%H-%M')
	if None is error_content:
		target, payload = f'res/{stamp}.json', data
	else:
		target, payload = (f'res/{stamp}--error.json', error_content) if dict == type(error_content) else (f'res/{stamp}--error.log', str(error_content))
	with open(target, 'w', encoding='utf-8') as f:
		if dict != type(payload):
			f.write(payload)
		else:
			json.dump(payload, f, ensure_ascii=False, indent='\t', sort_keys=True)
if '__main__' == __name__:
	save_report({'items': normalize_items([])}, None)
```
