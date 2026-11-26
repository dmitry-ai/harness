# 2026-11-24 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
import json
from pathlib import Path
import re
import sys
ABBREVIATIONS = '\\b(?:\\u0433|\\u0433\\u0433|\\u0442\\.\\u0434|\\u0442\\.\\u043f|\\u0441\\u043c|\\u0438\\u043c|\\u0434\\u0440|\\u043f\\u0440|\\u0443\\u043b|\\u0434|\\u043a\\u0432|\\u0440\\u0438\\u0441|\\u0442\\u0430\\u0431\\u043b|\\u0441\\u0442|\\u043f|\\u0447|\\u0440\\u0443\\u0431|\\u0442\\u044b\\u0441|\\u043c\\u043b\\u043d|\\u043c\\u043b\\u0440\\u0434|\\u0430\\u043d\\u0433\\u043b|\\u0440\\u0443\\u0441|\\u043d\\u0430\\u043f\\u0440|\\u043e\\u043a|vs|Mr|Mrs|Ms|Dr|St|Inc|Ltd|Co|Jr|Sr|e\\.g|i\\.e)\\.'
ABBR_RE = re.compile(ABBREVIATIONS, re.IGNORECASE)
MULTI_SENT_RE = re.compile('(?:[\\u0410-\\u044f\\u0401\\u0451A-Za-z0-9\\u00ab\\u00bb"(),:-]+\\s+){2,}[\\u0410-\\u044f\\u0401\\u0451A-Za-z0-9]+[.!?]\\s+[\\u0410-\\u042f\\u0401A-Z][a-z\\u0430-\\u044f\\u0451A-Za-z0-9]')
# 2026-11-25
# "Add auditable mechanical replacement recipe exemption for TDD and per-file issue gates":
# https://github.com/dmitry-ai/harness/issues/239
# 2026-11-26 "Bound synchronous foreign turn reconciliation with pending-sync index": https://github.com/dmitry-ai/harness/issues/341
# 2026-11-26 "Add incremental transcript event cache and single-process hook watchdog": https://github.com/dmitry-ai/harness/issues/356
_AUX_TURN_SUFFIXES = ('-recovery.json', '-checkpoint-recovery.json', '-violation-recovery.json', '-similar-exemptions.json', '-ratchet-ok.json', '-mechanical-exempt.json', 'pending-sync.json', '-trace-index.json')
_FENCE_RE = re.compile('^(`{3,}|~{3,})')
_WF_BOLD_BULLET_RE = re.compile('^[-*]\\s+\\*\\*[^*]+\\*\\*')
_WF_BOLD_SENT_RE = re.compile('[A-Za-z\\u0410-\\u042f\\u0430-\\u044f\\u0401\\u0451]{3,}[.!?]\\s+[A-Z\\u0410-\\u042f\\u0401][a-z\\u0430-\\u044f\\u0451]{2,}\\s+\\S+.*[.!?]\\s*$')
_WF_PROSE_SENT_RE = re.compile('(?:[\\u0410-\\u042f\\u0430-\\u044f\\u0401\\u0451A-Za-z0-9\\u00ab\\u00bb"(),:-]+\\s+){3,}[\\u0410-\\u042f\\u0430-\\u044f\\u0401\\u0451A-Za-z]{3,}[.!?]\\s+[A-Z\\u0410-\\u042f\\u0401][a-z\\u0430-\\u044f\\u0451]{2,}\\s+[\\u0410-\\u042f\\u0430-\\u044f\\u0401\\u0451A-Za-z0-9]+\\s+[\\u0410-\\u042f\\u0430-\\u044f\\u0401\\u0451A-Za-z0-9]+')
# @used-by :func:`_scan_hook_line()`
# @used-by :func:`_scan_workflow_line()`
def _clean_doc4_line(text: str, *, ignore_case: bool) -> str:
	cleaned = re.sub('`[^`]*`', 'code', text)
	cleaned = re.sub('\\[([^\\]]+)\\]\\([^)]+\\)', '\\1', cleaned)
	cleaned = re.sub('\\u00ab[^\\u00bb]*\\u00bb', '\u00abquote\u00bb', cleaned)
	return re.sub(ABBREVIATIONS, 'abbr', cleaned, flags=re.IGNORECASE if ignore_case else 0)
# @used-by :func:`scan_doc4_sentence_issues()`
def _dispatch_doc4_line(mode: str, idx: int, line: str, stripped: str, lines: list[str], issues: list[str]) -> None:
	if 'hook' == mode and (not stripped.startswith(('#', '|', '---', '===', '>'))):
		_scan_hook_line(idx, line, stripped, lines, issues)
	elif 'workflow' == mode and (not stripped.startswith(('#', '>', '|'))):
		_scan_workflow_line(idx + 1, stripped, issues)
# @used-by :func:`agent_tools.turn_routing.read_optional_transcript_rows()`
# @used-by :func:`read_last_user_segment()`
def _read_jsonl_dicts(path: Path) -> list[dict]:
	rows: list[dict] = []
	if path.is_file():
		try:
			for line in path.read_text(encoding='utf-8', errors='replace').splitlines():
				if line.strip():
					obj = json.loads(line)
					if isinstance(obj, dict):
						rows.append(obj)
		except (OSError, ValueError):
			rows = []
	return rows
# @used-by :func:`_dispatch_doc4_line()`
def _scan_hook_line(idx: int, line: str, stripped: str, lines: list[str], issues: list[str]) -> None:
	cleaned = _clean_doc4_line(line, ignore_case=True)
	if MULTI_SENT_RE.search(cleaned):
		issues.append(f'DOC-4 Line {idx + 1}: multiple sentences detected on a single line (rule DOC-4). Every sentence must start on a new physical line.\nFragment: {stripped[:80]}')
	if idx + 1 < len(lines):
		next_s = lines[idx + 1].strip()
		if next_s and (not next_s.startswith(('#', '```', '~~~', '---', '===', '>', '|'))) and (not re.match('^(?:[-*+]|\\d+\\.)\\s+', next_s)) and (not (line.endswith('  ') or line.endswith('\\'))):
			issues.append(f"DOC-4 Line {idx + 1}: run-on text without a CommonMark hard line break detected. The line continues to the next without a blank line or two trailing spaces ('  \\n').\nLine: {stripped[:70]}")
# @used-by :func:`_dispatch_doc4_line()`
def _scan_workflow_line(lineno: int, stripped: str, issues: list[str]) -> None:
	cleaned = _clean_doc4_line(stripped, ignore_case=False)
	if _WF_BOLD_BULLET_RE.match(stripped) and _WF_BOLD_SENT_RE.search(cleaned):
		issues.append(f'DOC-4 violation on line {lineno}: multiple sentences on a single bullet line (place each sentence on its own line or use sub-bullets)')
	elif _WF_PROSE_SENT_RE.search(cleaned):
		issues.append(f'DOC-4 violation on line {lineno}: multiple sentences on a single line (place each sentence on its own line)')
# @used-by :func:`read_last_user_segment()`
def _slice_after_last_user(rows: list[dict], by_step_index: bool) -> tuple[int | None, list[dict]]:
	if by_step_index:
		steps = [row['step_index'] for row in rows if 'USER_INPUT' == row.get('type') and isinstance(row.get('step_index'), int)]
		last_ref: int | None = steps[-1] if steps else None
		seg = [row for row in rows if isinstance(row.get('step_index'), int) and row['step_index'] > last_ref] if None is not last_ref else []
	else:
		last_idx = max((idx for idx, row in enumerate(rows) if 'USER_INPUT' == row.get('type')), default=-1)
		last_ref = last_idx if 0 <= last_idx else None
		seg = rows[last_idx + 1:]
	return (last_ref, seg)
# @used-by :func:`scan_doc4_sentence_issues()`
def _update_fence(stripped: str, in_fence: bool, marker: str) -> tuple[bool, str, bool]:
	m_fence = _FENCE_RE.match(stripped)
	if not m_fence:
		r = (in_fence, marker, False)
	elif not in_fence:
		r = (True, m_fence.group(1)[0], True)
	elif stripped.startswith(marker * 3):
		r = (False, '', True)
	else:
		r = (in_fence, marker, True)
	return r
# @used-by :func:`agent_tools.gates.external_write._check_df_issue_turn_intent()`
# @used-by :func:`agent_tools.issue_first_inherit._iter_candidate_issue_nums()`
# @used-by :func:`agent_tools.repo_wait._active_turn_touched_paths()`
# @used-by :func:`agent_tools.turn_routing._collect_turn_candidates()`
# @used-by :func:`check_markdown_slop._check_turn_budget_gate()`
# @used-by :meth:`test_hook_trace_cache_and_watchdog.HookTraceCacheAndWatchdogTests.test_incremental_disk_cache_appends_and_invalidation()`
# @used-by :meth:`test_hook_unification.HookUnificationTests.test_iter_turn_state_files_skips_aux_files()`
# @used-by :meth:`test_stop_gate_contract.StopGateContractTests.test_continuation_active_guards_against_unchanged_readiness_loops_but_allows_progress()`
def iter_turn_state_files(turns_dir: Path, *, exclude_hyphen: bool=False) -> list[tuple[Path, dict]]:
	items: list[tuple[Path, dict]] = []
	if turns_dir.is_dir():
		for tfile in turns_dir.glob('*.json'):
			if (exclude_hyphen and '-' in tfile.stem) or tfile.name.endswith(_AUX_TURN_SUFFIXES):
				continue
			try:
				data = json.loads(tfile.read_text(encoding='utf-8'))
			except (OSError, ValueError):
				continue
			if isinstance(data, dict):
				items.append((tfile, data))
	return items
# @used-by :func:`agent_tools.gates.bulk_source_read._recent_segment_rows()`
# @used-by :func:`check_stop_gate.evaluate_stop_payload()`
# @used-by :meth:`test_hook_unification.HookUnificationTests.test_read_last_user_segment_positional_and_by_step()`
def read_last_user_segment(t_path: Path, *, prefer_full: bool=False, by_step_index: bool=False) -> tuple[list[dict], int | None, list[dict]]:
	full_cand = t_path.parent / 'transcript_full.jsonl'
	eff_path = full_cand if prefer_full and 'transcript.jsonl' == t_path.name and full_cand.is_file() else t_path
	rows = _read_jsonl_dicts(eff_path)
	last_ref, seg = _slice_after_last_user(rows, by_step_index)
	return (rows, last_ref, seg)
# 2026-11-24
# "Unify PreToolUse/Stop JSON hook harnesses, turns/*.json iterators, DOC-4 sentence scanning, and GitHub Evidence resolvers":
# https://github.com/dmitry-ai/harness/issues/79
# @used-by :func:`check_markdown_slop.main()`
# @used-by :func:`check_rules_and_server_gate.main()`
# @used-by :func:`check_stop_gate.main()`
# @used-by :meth:`test_hook_unification.HookUnificationTests.test_run_json_hook_dispatches_and_fails_open()`
def run_json_hook(handler, *, stdin=None, stdout=None) -> dict:
	in_stream = stdin if None is not stdin else sys.stdin
	out_stream = stdout if None is not stdout else sys.stdout
	decision: dict = {'decision': 'allow'}
	try:
		raw = in_stream.read()
		if raw and raw.strip():
			decision = handler(json.loads(raw))
	except Exception:
		decision = {'decision': 'allow'}
	out_stream.write(json.dumps(decision, ensure_ascii=False))
	return decision
# @used-by :func:`agent_tools.workflow.doc4_sentence_issues()`
# @used-by :func:`check_markdown_slop.markdown_slop_issues()`
# @used-by :meth:`test_hook_unification.HookUnificationTests.test_doc4_scanner_supports_hook_and_workflow_modes()`
def scan_doc4_sentence_issues(text: str, *, mode: str='hook') -> list[str]:
	from .statements import markdown_table_issues
	issues: list[str] = []
	if text and isinstance(text, str):
		lines = text.split('\n') if 'hook' == mode else text.splitlines()
		in_fence, marker, in_fm = (False, '', False)
		for idx, line in enumerate(lines):
			stripped = line.strip()
			if 'hook' == mode and (in_fm or (0 == idx and '---' == stripped)):
				in_fm = not (in_fm and '---' == stripped)
				continue
			in_fence, marker, toggled = _update_fence(stripped, in_fence, marker)
			if not (toggled or in_fence or (not stripped)):
				_dispatch_doc4_line(mode, idx, line, stripped, lines, issues)
		# 2026-11-24
		# "Enforce Markdown table ban and /df-analysis structural validation across response gates":
		# https://github.com/dmitry-ai/harness/issues/181
		issues.extend(markdown_table_issues(text))
	return issues
