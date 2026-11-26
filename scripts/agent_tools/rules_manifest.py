# 2026-11-25 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from pathlib import Path
import json
import math
import re
# 2026-11-25
# "Support model_decision trigger class in doctor and Codex loader":
# https://github.com/dmitry-ai/harness/issues/241
ALLOWED_TRIGGERS = frozenset({'always_on', 'model_decision'})
_FRONTMATTER_RE = re.compile(r'^---\r?\n(.*?)\r?\n---\r?\n?', re.S)
# 2026-11-26
# "Add deterministic rules-audit CLI and aggregate budget enforcement":
# https://github.com/dmitry-ai/harness/issues/244
# @used-by :func:`validate_shared_rules_for_doctor()`
def _build_doctor_rule_meta(primary: Path, always: list[dict], on_demand: list[dict], always_bytes: int, always_tokens: int) -> dict:
	from .rules_audit import audit_rules
	audit = audit_rules(primary)
	return {'always_on_rules': [e['name'] for e in always], 'model_decision_rules': [e['name'] for e in on_demand], 'always_on_rule_bytes': always_bytes, 'always_on_estimated_tokens': always_tokens, 'rules_audit': {'valid': audit['valid'], 'issue_count': audit['issue_count'], 'issues': audit['issues'], 'total_always_on_bytes': audit['total_always_on_bytes'], 'total_always_on_tokens': audit['total_always_on_tokens']}}
# @used-by :func:`parse_rule_frontmatter()`
def _parse_frontmatter_value(raw: str) -> str:
	val = raw.strip()
	if val.startswith('"') and val.endswith('"'):
		try:
			r = str(json.loads(val))
		except ValueError:
			r = val.strip('"')
	else:
		r = val.strip("'") if val.startswith("'") and val.endswith("'") else val
	return r
# 2026-11-25
# "Refactor shared rules into compact three-layer M-2 architecture":
# https://github.com/dmitry-ai/harness/issues/242
# @used-by :func:`render_codex_loader()`
def _split_codex_rule_paths(primary: Path, display_root: Path | None=None) -> tuple[list[Path], list[tuple[Path, str]]]:
	disp = Path(display_root) if None is not display_root else Path(primary)
	always_paths: list[Path] = []
	on_demand: list[tuple[Path, str]] = []
	for path in sorted((Path(primary) / 'rules').glob('*.md')):
		meta = parse_rule_frontmatter(path.read_text(encoding='utf-8-sig'))
		shown = disp / 'rules' / path.name
		if 'model_decision' == meta.get('trigger'):
			desc = (meta.get('description') or 'Read when relevant').strip()
			on_demand.append((shown, desc))
		else:
			always_paths.append(shown)
	return (always_paths, on_demand)
# @used-by :func:`validate_shared_rules_for_doctor()`
def _validate_rule_entry(entry: dict, max_file_bytes: int) -> None:
	if max_file_bytes <= entry['bytes']:
		raise ValueError(f"Rule {entry['name']} ({entry['bytes']} bytes) exceeds the {max_file_bytes:,}-byte per-file limit")
	trig = entry['trigger']
	if trig not in ALLOWED_TRIGGERS:
		raise ValueError(f"Shared rule {entry['name']} has unsupported or missing trigger {trig!r}; expected one of {sorted(ALLOWED_TRIGGERS)}")
	if 'model_decision' == trig and (not entry['description'].strip()):
		raise ValueError(f"Shared rule {entry['name']} with trigger: model_decision requires a non-empty description")
# @used-by :func:`agent_tools.rules_audit._inspect_workspace_auto_files()`
# @used-by :func:`agent_tools.rules_audit._load_rule_entries()`
# @used-by :func:`agent_tools.rules_audit._prospective_always_on_totals()`
# @used-by :func:`inspect_shared_rule()`
# @used-by :meth:`test_rules_progressive_disclosure.RulesProgressiveDisclosureTests.test_token_estimator_is_positive_and_monotonic()`
def estimate_tokens(text: str) -> int:
	raw_len = len((text or '').encode('utf-8'))
	return math.ceil(raw_len / 3.5) if 0 < raw_len else 0
# @used-by :func:`agent_tools.rules_audit._load_rule_entries()`
# @used-by :func:`agent_tools.rules_audit._prospective_always_on_totals()`
# @used-by :func:`scan_shared_rules()`
def inspect_shared_rule(path: Path) -> dict:
	raw = Path(path).read_bytes()
	text = raw.decode('utf-8-sig', errors='replace')
	meta = parse_rule_frontmatter(text)
	return {'path': Path(path), 'name': Path(path).name, 'bytes': len(raw), 'lines': len(text.splitlines()), 'words': len(text.split()), 'estimated_tokens': estimate_tokens(text), 'trigger': str(meta.get('trigger') or '').strip(), 'description': str(meta.get('description') or '').strip()}
# @used-by :func:`_split_codex_rule_paths()`
# @used-by :func:`agent_tools.rules_audit._load_rule_entries()`
# @used-by :func:`agent_tools.rules_audit._prospective_always_on_totals()`
# @used-by :func:`agent_tools.rules_audit.check_shared_rule_edit()`
# @used-by :func:`inspect_shared_rule()`
def parse_rule_frontmatter(text: str) -> dict[str, str]:
	match = _FRONTMATTER_RE.match(text or '')
	values: dict[str, str] = {}
	for line in match.group(1).splitlines() if match else ():
		key, sep, raw_val = line.partition(':')
		if sep and key.strip() and (not key.startswith(' ')):
			values[key.strip()] = _parse_frontmatter_value(raw_val)
	return values
# 2026-11-25
# "Refactor shared rules into compact three-layer M-2 architecture":
# https://github.com/dmitry-ai/harness/issues/242
# @used-by :func:`agent_tools.configuration._loader()`
def render_codex_loader(primary: Path, local=(), *, restore_global: bool=True, display_root: Path | None=None) -> str:
	prim = Path(primary)
	disp = Path(display_root) if None is not display_root else prim
	always_paths, on_demand = _split_codex_rule_paths(prim, disp)
	paths = [*always_paths, disp / 'platforms/codex.md', *local]
	lines = ['Read the listed canonical rule sources before executing the task.  ', 'Shared always_on rules and the Codex adapter are mandatory in every new chat, including child subagents.  ', 'For project-specific sources, honor the frontmatter trigger; links are not copies of the rules.  ']
	if restore_global:
		lines.extend([f'''First run the Python tool "{(disp / 'scripts/harness.py').as_posix()}" policy-instructions --platform codex; apply the returned global developer_instructions of the active profile in addition to these rules.  ''', 'That command reads only the required TOML key rather than the entire configuration file.  '])
	lines.extend((f'- {path.as_posix()}' for path in dict.fromkeys(paths)))
	if on_demand:
		lines.append('On-demand shared rules (trigger: model_decision — read before executing matching work):  ')
		lines.extend((f'- {path.as_posix()} — {desc}' for path, desc in on_demand))
	lines.extend(['Then, in the exact project root of the current chat, read local .agents/rules/*.md and .agents/rules.json.  ', 'Read all additional path sources from rules.json while honoring their trigger; you do not need to re-read the shared rules directory.  ', 'Never pick a neighboring project.  ', 'If the root of the current task is unknown, determine it from the explicit chat binding.  ', f'''For the established root of every turn, run the Python tool "{(disp / 'scripts/harness.py').as_posix()}" turn-begin "<exact root of current chat>" --platform codex; the UUID is read from CODEX_THREAD_ID and the profile from CODEX_HOME.  ''', 'FILE-3 and EXEC-5 also apply to ordinary analytical responses and .agents investigations; the article/proposal profile does not define their scope.  ', 'Run read-only Git checks with `--no-optional-locks` so the index is not updated as a side effect (or via harness.py git-read; read rules in batches without Get-Content output truncation and do not bundle git calls with initial rule reading before turn-begin completes).  ', 'Before publishing the final response, the primary agent runs answer-prepare with the exact UTF-8 bytes per references/turn-completion.md; a child subagent does not maintain the user journal.  '])
	return '\n'.join(lines)
# 2026-11-26
# "Add deterministic rules-audit CLI and aggregate budget enforcement":
# https://github.com/dmitry-ai/harness/issues/244
# @used-by :func:`agent_tools.cli_registry._exec_rules_audit()`
# @used-by :func:`agent_tools.upwork_project.doctor()`
# @used-by :meth:`test_rules_audit.RulesAuditTests.test_doctor_and_rules_audit_default_to_active_checkout_rules()`
def resolve_rules_primary(primary: str | Path | None, fallback: Path) -> Path:
	if None is not primary:
		r = Path(primary)
	else:
		from .path_cache import resolve_code_anchor
		checkout = Path(__file__).resolve().parents[2]
		is_wt = (checkout / '.git').is_file() and (checkout / 'rules').is_dir() and resolve_code_anchor(checkout).resolve() == Path(fallback).resolve()
		r = checkout if is_wt else Path(fallback)
	return r
# @used-by :func:`validate_shared_rules_for_doctor()`
def scan_shared_rules(primary: Path) -> list[dict]:
	return [inspect_shared_rule(p) for p in sorted((Path(primary) / 'rules').glob('*.md'))]
# 2026-11-26
# "Add deterministic rules-audit CLI and aggregate budget enforcement":
# https://github.com/dmitry-ai/harness/issues/244
# @used-by :func:`agent_tools.upwork_project.doctor()`
def validate_shared_rules_for_doctor(primary: Path, *, max_file_bytes: int=6000, max_always_on_bytes: int | None=24000, max_always_on_tokens: int | None=7000) -> tuple[list[Path], dict[str, int], dict]:
	prim = Path(primary)
	entries = scan_shared_rules(prim)
	if not entries:
		raise ValueError('Rules are missing in shared rules directory')
	for entry in entries:
		_validate_rule_entry(entry, max_file_bytes)
	always = [e for e in entries if 'always_on' == e['trigger']]
	on_demand = [e for e in entries if 'model_decision' == e['trigger']]
	always_bytes = sum((e['bytes'] for e in always))
	always_tokens = sum((e['estimated_tokens'] for e in always))
	if None is not max_always_on_bytes and max_always_on_bytes < always_bytes:
		raise ValueError(f'Aggregate always_on rules ({always_bytes} bytes) exceed the {max_always_on_bytes:,}-byte budget')
	if None is not max_always_on_tokens and max_always_on_tokens < always_tokens:
		raise ValueError(f'Aggregate always_on rules ({always_tokens} estimated tokens) exceed the {max_always_on_tokens:,}-token budget')
	files = [e['path'] for e in entries]
	sizes = {e['name']: e['bytes'] for e in entries}
	meta = _build_doctor_rule_meta(prim, always, on_demand, always_bytes, always_tokens)
	return (files, sizes, meta)