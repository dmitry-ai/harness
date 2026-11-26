# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Trigger DOC-5 four-track validation from active-turn bug-report signals":
# https://github.com/dmitry-ai/harness/issues/294
from __future__ import annotations
from pathlib import Path
from typing import Any
import re
from Df.Harness.lib.trace import dfh_cmd_from_call, dfh_row_outputs
from .cli_output_json import top_level_json_has_failure
from .hook_crash_audit import _load_turn_rows
from .tdd_gate import _BG_TASK_FINISHED_RE, parse_command_outcome
# 2026-11-26 "Fix top-level JSON parsing and workspace repo scoping in doc5_context.py": https://github.com/dmitry-ai/harness/issues/368
_EXCLUDED_CLI_RE = re.compile(r'\b(?:pytest|unittest|run-tests|test-watchdog|perf-profile-tests|answer-check|answer-prepare|tdd-check|issue-first-check|analysis-check|rules-audit|collect|collect-http|collect-browser|xref-check|git-read)\b', re.IGNORECASE)
_HARNESS_CLI_RE = re.compile(r'(?:harness|upwork_project|df_github_issue|validate_step)\.py', re.IGNORECASE)
# 2026-11-26 "Create Df/Harness library for shared Harness helpers": https://github.com/dmitry-ai/harness/issues/379
# @used-by :func:`_inspect_call_failure()`
# @used-by :meth:`test_df_harness_lib_s10.DfHarnessLibS10Tests.test_harness_callers_delegate_to_df_harness_helpers()`
def _cmd_from_call(call: dict[str, Any]) -> str:
	return dfh_cmd_from_call(call)
# 2026-11-26 "Fix top-level JSON parsing and workspace repo scoping in doc5_context.py": https://github.com/dmitry-ai/harness/issues/368
# @used-by :func:`_inspect_call_failure()`
# @used-by :func:`_record_bg_cli_failures()`
# @used-by :meth:`test_turn_begin_status_and_auditors.TurnBeginStatusAndAuditorsTests.test_all_trace_auditors_ignore_nested_foreign_reconciliation_and_flag_top_level_failure()`
def _is_failed_cli_output(text: str) -> bool:
	out = parse_command_outcome(text)
	rc = out.get('exit_code')
	if None is not rc:
		r = (0 != rc) or top_level_json_has_failure(text)
	else:
		low = (text or '').lower()
		r = ('fail' == out.get('status')) or top_level_json_has_failure(text) or ('valueerror:' in low) or ('traceback (most recent call last)' in low)
	return r
# @used-by :func:`_earliest_cli_failure_step()`
# @used-by :meth:`test_df_harness_lib_s10.DfHarnessLibS10Tests.test_harness_callers_delegate_to_df_harness_helpers()`
def _row_outputs(rows: list[dict[str, Any]], pos: int) -> list[str]:
	return dfh_row_outputs(rows, pos)
# @used-by :func:`_earliest_cli_failure_step()`
def _record_bg_cli_failures(rows: list[dict[str, Any]], bg_steps: dict[str, int], hits: list[int]) -> None:
	for row in rows:
		if row.get('type') in ('EPHEMERAL_MESSAGE', 'SYSTEM_MESSAGE', 'GENERIC') and row.get('content'):
			m_fin = _BG_TASK_FINISHED_RE.search(str(row.get('content')))
			if None is not m_fin and m_fin.group(1).strip() in bg_steps and _is_failed_cli_output(m_fin.group(2)):
				hits.append(bg_steps[m_fin.group(1).strip()])
# @used-by :func:`_earliest_cli_failure_step()`
def _inspect_call_failure(call: dict[str, Any], matched: str, step_idx: int, bg_steps: dict[str, int], hits: list[int]) -> None:
	cmd = _cmd_from_call(call)
	if cmd and _HARNESS_CLI_RE.search(cmd) and (not _EXCLUDED_CLI_RE.search(cmd)):
		out_info = parse_command_outcome(matched)
		if out_info.get('background_task_id'):
			bg_steps[str(out_info['background_task_id'])] = step_idx
		elif _is_failed_cli_output(matched):
			hits.append(step_idx)
# @used-by :func:`turn_requires_doc5_problem_analysis()`
def _earliest_cli_failure_step(turn: dict[str, Any], native: dict[str, Any] | None) -> int | None:
	rows = _load_turn_rows(native, turn)
	bg_steps: dict[str, int] = {}
	hits: list[int] = []
	for pos, row in enumerate(rows):
		calls = [c for c in (row.get('tool_calls') or ()) if isinstance(c, dict)]
		if not calls:
			continue
		step_idx = row['step_index'] if isinstance(row.get('step_index'), int) else pos
		outs = _row_outputs(rows, pos)
		joined = '\n'.join(outs)
		for idx, call in enumerate(calls):
			_inspect_call_failure(call, outs[idx] if idx < len(outs) else joined, step_idx, bg_steps, hits)
	_record_bg_cli_failures(rows, bg_steps, hits)
	return min(hits) if hits else None
# 2026-11-26 "Fix top-level JSON parsing and workspace repo scoping in doc5_context.py": https://github.com/dmitry-ai/harness/issues/368
# @used-by :func:`turn_requires_doc5_problem_analysis()`
def _has_post_failure_parent_issue(turn: dict[str, Any], fail_step: int, local_repos: set[str] | None=None) -> bool:
	r = False
	for act in turn.get('issue_actions') or ():
		if isinstance(act, dict) and 'create' == str(act.get('action') or '').lower() and None is act.get('parent_number'):
			repo = str(act.get('repo') or '').strip().lower()
			act_step = act.get('step')
			repo_ok = (not local_repos) or (repo in local_repos)
			if repo_ok and (None is act_step or (isinstance(act_step, int) and act_step >= fail_step)):
				r = True
				break
	return r
# 2026-11-26 "Fix top-level JSON parsing and workspace repo scoping in doc5_context.py": https://github.com/dmitry-ai/harness/issues/368
# @used-by :func:`turn_requires_doc5_problem_analysis()`
def _workspace_repo_slugs(root: Any) -> set[str]:
	slugs: set[str] = set()
	if None is not root and str(root).strip():
		from .issues.repo_locator import _V2_CODE_RELS, origin_repo_slug
		from .path_registry import project_paths
		root_p = Path(root).resolve()
		cands: list[Path] = [root_p, root_p / 'code', *(root_p / rel for rel in _V2_CODE_RELS)]
		try:
			cands = [*project_paths(root_p).code_repos, *cands]
		except (OSError, ValueError):
			pass
		for cand in cands:
			if (cand / '.git').exists():
				slug = origin_repo_slug(cand)
				if slug:
					slugs.add(slug.lower())
	return slugs
# @used-by :func:`agent_tools.statements._detect_mode()`
# @used-by :mod:`agent_tools.doc5_context`
def detect_df_analysis_mode(text: str, blocks: list[dict], requests: list | tuple, mode: str, *, turn_context: dict | None, prob_head_re, req_cmd_fn, explicit_fn) -> str:
	if mode in ('general', 'problem'):
		r = mode
	else:
		has_s0_meta = any((0 in b['sections'] and bool(prob_head_re.search(b['sections'][0][0])) for b in blocks))
		has_s1_prob = any((1 in b['sections'] and bool(prob_head_re.search(b['sections'][1][0])) and bool({2, 3, 4} & set(b['sections'])) for b in blocks))
		if has_s0_meta or has_s1_prob or turn_requires_doc5_problem_analysis(turn_context):
			r = 'problem'
		elif req_cmd_fn(requests):
			r = 'problem' if any((0 in b['sections'] for b in blocks)) else 'general'
		else:
			hyps, mets = explicit_fn(text)
			r = 'general' if hyps or mets else 'none'
	return r
# 2026-11-26 "Fix top-level JSON parsing and workspace repo scoping in doc5_context.py": https://github.com/dmitry-ai/harness/issues/368
# @used-by :func:`detect_df_analysis_mode()`
# @used-by :meth:`test_cli_output_json.CliOutputJsonAndDoc5Tests.test_excluded_fetchers_and_readonly_linters_do_not_trigger_doc5()`
# @used-by :meth:`test_cli_output_json.CliOutputJsonAndDoc5Tests.test_local_repo_scoping_ignores_external_upstream_issues_and_preserves_fallback()`
# @used-by :mod:`agent_tools.doc5_context`
def turn_requires_doc5_problem_analysis(turn_context: dict | None) -> bool:
	r = False
	if isinstance(turn_context, dict):
		if turn_context.get('bug_report_signal'):
			r = True
		else:
			turn = turn_context.get('turn')
			if isinstance(turn, dict) and 'standalone' != turn.get('turn_id'):
				fail_step = _earliest_cli_failure_step(turn, turn_context.get('native'))
				if None is not fail_step:
					r = _has_post_failure_parent_issue(turn, fail_step, _workspace_repo_slugs(turn_context.get('root')))
	return r
__all__ = ['detect_df_analysis_mode', 'turn_requires_doc5_problem_analysis']