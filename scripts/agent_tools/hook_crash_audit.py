# 2026-11-25 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Add PreToolUse canary probe to runtime snapshot validation and turn hook-crash audit":
# https://github.com/dmitry-ai/harness/issues/251
from __future__ import annotations
from pathlib import Path
from typing import Any
import json
import re
_HOOK_CRASH_RE = re.compile(r'JSON hook "([^"]+)" failed[^\r\n]*', re.IGNORECASE)
_HOOK_FAILURE_WORD_RE = re.compile(r'(?i)(?:fail(?:ed|ure)?|crash\w*|timeout|exit\s+status\s+[1-9]\d*|таймаут\w*|падени\w*|сбо[йяею]\w*|упал\w*|ошибк\w*|обрыв\w*)')
_HOOK_TOPIC_RE = re.compile(r'(?i)(?:json\s+hook|pretooluse|stop\s+gate|preinvocation|rules-and-server-gate|doc4-anti-slop-gate|final-turn-gate|harness_hook_runner|хук[а-я]*)')
def _collect_issue_refs(turn: dict[str, Any], value: dict[str, Any] | None) -> list[tuple[str, int]]:
	raw_items: list[Any] = list(turn.get('issue_actions') or ())
	gh_raw = (value or {}).get('github_issues')
	if isinstance(gh_raw, dict):
		raw_items.extend(gh_raw.values())
	elif isinstance(gh_raw, list):
		raw_items.extend(gh_raw)
	refs: list[tuple[str, int]] = []
	for it in raw_items:
		if isinstance(it, dict):
			slug, num = (str(it.get('repo') or '').strip(), it.get('number'))
			if slug and isinstance(num, int) and (not isinstance(num, bool)):
				refs.append((slug, num))
	return refs
def _extract_hook_error(row: dict[str, Any]) -> tuple[str, str] | None:
	r: tuple[str, str] | None = None
	if 'ERROR' == str(row.get('status') or '').strip().upper():
		for raw in (row.get('error'), row.get('content')):
			m = _HOOK_CRASH_RE.search(str(raw or ''))
			if None is not m:
				r = (m.group(1), m.group(0).strip())
				break
	return r
def _has_recorded_hook_issue(root: Path, turn: dict[str, Any], value: dict[str, Any] | None, crashes: list[dict[str, Any]]) -> bool:
	from .issue_lifecycle import evidence_issue_files
	return any((_issue_evidence_mentions_crash(evidence_issue_files(root, slug, f'issue-{num}.json'), crashes) for slug, num in _collect_issue_refs(turn, value)))
def _issue_evidence_mentions_crash(files: list[Path], crashes: list[dict[str, Any]]) -> bool:
	r = False
	for fpath in files[:1]:
		try:
			data = json.loads(fpath.read_text(encoding='utf-8'))
			obj = data.get('issue') if isinstance(data.get('issue'), dict) else data
			blob = f"{obj.get('title') or ''}\n{obj.get('body') or ''}" if isinstance(obj, dict) else ''
			r = _text_documents_hook_crash(blob, crashes)
		except (OSError, ValueError):
			r = False
	return r
def _load_turn_rows(native: dict[str, Any] | None, turn: dict[str, Any] | None) -> list[dict[str, Any]]:
	src = Path(str((native or {}).get('source_file') or '')) if (native or {}).get('source_file') else None
	r: list[dict[str, Any]] = []
	if None is not src and src.is_file():
		try:
			all_rows = [json.loads(ln) for ln in src.read_text(encoding='utf-8', errors='replace').splitlines() if ln.strip()]
		except (OSError, ValueError):
			all_rows = []
		r = _slice_turn_rows(all_rows, turn or {})
	return r
def _load_violation_receipt(root: Path, turn_key: str) -> dict[str, Any]:
	from .path_registry import project_paths
	r: dict[str, Any] = {}
	if turn_key:
		rf = project_paths(root, exact_root=True).turns_dir / f'{turn_key}-violation-recovery.json'
		if rf.is_file():
			try:
				parsed = json.loads(rf.read_text(encoding='utf-8'))
				if isinstance(parsed, dict):
					r = parsed
			except (OSError, ValueError):
				r = {}
	return r
def _slice_turn_rows(all_rows: list[Any], turn: dict[str, Any]) -> list[dict[str, Any]]:
	start_i = turn['start_step'] if isinstance(turn.get('start_step'), int) else 0
	final_i = turn['final_step'] if isinstance(turn.get('final_step'), int) and turn.get('completed') else None
	out: list[dict[str, Any]] = []
	for pos, row in enumerate(all_rows):
		if isinstance(row, dict):
			s_idx = row['step_index'] if isinstance(row.get('step_index'), int) else pos
			if ('USER_INPUT' == row.get('type') and s_idx > start_i) or (None is not final_i and s_idx > final_i):
				break
			if s_idx >= start_i:
				out.append(row)
	return out
def _text_documents_hook_crash(text: str | None, crashes: list[dict[str, Any]]) -> bool:
	raw = str(text or '')
	if not raw.strip():
		r = False
	else:
		low = raw.lower()
		named = any((str(c.get('hook') or '').lower() in low for c in crashes if c.get('hook')))
		r = (named or bool(_HOOK_TOPIC_RE.search(raw))) and bool(_HOOK_FAILURE_WORD_RE.search(raw))
	return r
def build_violation_recovery_receipt(root_p: Path, key: str, turn: dict[str, Any], reason: str | None, now_fn, *, native: dict[str, Any] | None=None) -> tuple[dict[str, Any], Any]:
	exec5_v = list(turn.get('exec5_violations') or [])
	http_v = list(turn.get('http_fetch_violations') or [])
	hook_v = detect_hook_crashes(native, turn)
	receipt = {
		'covered_exec5_steps': [it.get('step') for it in exec5_v if None is not it.get('step')],
		'covered_hook_crash_steps': [it.get('step') for it in hook_v if None is not it.get('step')],
		'covered_http_fetch_steps': [it.get('step') for it in http_v if None is not it.get('step')],
		'exec5_violations': exec5_v,
		'hook_crash_violations': hook_v,
		'http_fetch_violations': http_v,
		'reason': (reason or 'Retrospective turn violation acknowledged for journal completion').strip(),
		'recovered_at': now_fn(),
		'turn_key': key,
	}
	return (receipt, lambda value: {'exec5_check': value['exec5_check'], 'http_fetch_check': value['http_fetch_check']})
def check_runner_hook_crashes(runner) -> None:
	chk = evaluate_hook_crash_check(runner.root, runner.native, runner.turn, runner.value, runner.response)
	runner.value['hook_crash_check'] = chk
	if not chk['verified']:
		runner._fail_gate('hook_crash', chk['detail'])
def detect_hook_crashes(native: dict[str, Any] | None, turn: dict[str, Any] | None) -> list[dict[str, Any]]:
	explicit = (turn or {}).get('hook_crashes')
	if isinstance(explicit, list):
		r = [dict(it) for it in explicit if isinstance(it, dict)]
	else:
		r = []
		for pos, row in enumerate(_load_turn_rows(native, turn)):
			hit = _extract_hook_error(row)
			if None is not hit:
				step_idx = row.get('step_index') if isinstance(row.get('step_index'), int) else pos
				r.append({'error': hit[1], 'hook': hit[0], 'step': step_idx})
	return r
def evaluate_hook_crash_check(root: Path, native: dict[str, Any] | None, turn: dict[str, Any] | None, value: dict[str, Any] | None, response: str | None) -> dict[str, Any]:
	crashes = detect_hook_crashes(native, turn)
	if not crashes:
		r: dict[str, Any] = {'crashes': [], 'verified': True}
	else:
		key = str((value or {}).get('key') or '')
		covered = set(_load_violation_receipt(Path(root), key).get('covered_hook_crash_steps') or ())
		if all((c.get('step') in covered for c in crashes)):
			r = {'crashes': crashes, 'recovered_via_receipt': True, 'resolution': 'recovered_via_receipt', 'verified': True}
		elif _has_recorded_hook_issue(Path(root), turn or {}, value, crashes):
			r = {'crashes': crashes, 'resolution': 'github_issue_recorded', 'verified': True}
		elif _text_documents_hook_crash(response, crashes):
			r = {'crashes': crashes, 'resolution': 'disclosed_in_response', 'verified': True}
		else:
			summary = ', '.join((f"{c['hook']}@step {c['step']}" for c in crashes[:4]))
			r = {'crashes': crashes, 'detail': f'DOC-5 / EXEC-5 hook_crash_check: unhandled JSON hook failure(s) occurred during the active turn ({summary}). File a parent GitHub issue about the hook failure, explicitly analyze the hook failure in the response, or record recover-turn-violation before answer-prepare.', 'verified': False}
	return r
__all__ = ['build_violation_recovery_receipt', 'check_runner_hook_crashes', 'detect_hook_crashes', 'evaluate_hook_crash_check']
