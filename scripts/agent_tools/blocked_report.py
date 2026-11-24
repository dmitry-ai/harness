# 2026-11-24 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Add blocked-report mode to answer-prepare for pre-finalize workflow blockers":
# https://github.com/dmitry-ai/harness/issues/213
from __future__ import annotations
from pathlib import Path
import re
_BLOCKER_HINT_RE = re.compile(r'(?i)(?:block(?:er|ed|ing)?|error|fail(?:ed|ure)?|pause[d]?|interrupt(?:ed)?|unavailab\w*|timeout|expired|mismatch|\u0431\u043b\u043e\u043a\u0435\u0440\w*|\u0437\u0430\u0431\u043b\u043e\u043a\u0438\u0440\w*|\u043e\u0448\u0438\u0431\u043a\w*|\u0441\u0431\u043e[\u0439\u0435\u0432\u044f]\w*|\u043f\u0440\u0435\u0440\u0432\u0430\u043d\w*|\u043d\u0435\u0434\u043e\u0441\u0442\u0443\u043f\w*)')
_FENCED_RE = re.compile(r'```[\s\S]*?```')
_HM_CLAIM_RE = re.compile(r'\b(?:H|M)-(?:[A-Za-z0-9]+-)*\d+\b')
_STAGE_HEADING_RE = re.compile(r'(?im)^#{1,3}\s+(?:\d+\.\s+)?(?:client identification|client concerns|possible misconceptions|causes of the problem|solution methods|\u0438\u0434\u0435\u043d\u0442\u0438\u0444\u0438\u043a\u0430\u0446\u0438\u044f\s+\u043a\u043b\u0438\u0435\u043d\u0442\u0430|\u0447\u0442\u043e\s+\u0432\u043e\u043b\u043d\u0443\u0435\u0442|\u0432\u043e\u0437\u043c\u043e\u0436\u043d\u044b\u0435\s+\u0437\u0430\u0431\u043b\u0443\u0436\u0434\u0435\u043d\u0438\u044f|\u043f\u0440\u0438\u0447\u0438\u043d\u044b\s+\u043f\u0440\u043e\u0431\u043b\u0435\u043c\w*|\u043c\u0435\u0442\u043e\u0434\u044b\s+\u0440\u0435\u0448\u0435\u043d\u0438\u044f)\b')
def _authorize_workflow_errors(root_p: Path, pp, wf_state: dict, wf_ids: set, wf_cov: set, is_fin: bool, substantive_hm: bool, requests_list: list, response: str) -> list[str]:
	errs: list[str] = []
	if wf_cov and wf_cov != wf_ids:
		errs.append('Adopt all exact current requests before preparing a tracked analysis response')
	elif not wf_cov and pp.project_json.is_file() and (not any((re.search('(?:^|\\s)/df-(?:article|proposal)\\b', req.get('text', '')) for req in requests_list))) and (not is_fin or substantive_hm):
		errs.append('REVIEW-3 / REVIEW-4: Adopt current requests (adopt-requests) and complete review authorization before preparing a substantive response in a tracked Upwork project')
	elif wf_cov and (not is_fin or substantive_hm):
		from .review import authorize
		try:
			authorize(root_p, wf_state, response=response, request_ids=wf_ids)
		except (OSError, ValueError) as exc:
			errs.append(str(exc))
	return errs
def _continuation_blocker_issue(cont_path: Path) -> str | None:
	r = None
	if not cont_path.is_file():
		r = 'FILE-3 / REVIEW-3 blocked-report: save the active blocker and next step in \ua616/data/continuation.md before calling answer-prepare --blocked-report'
	else:
		try:
			text = cont_path.read_text(encoding='utf-8', errors='replace').strip()
		except OSError:
			text = ''
		if 20 > len(text) or (not _BLOCKER_HINT_RE.search(text)):
			r = 'FILE-3 / REVIEW-3 blocked-report: \ua616/data/continuation.md must explicitly document the active blocker before calling answer-prepare --blocked-report'
	return r
def _standard_workflow_errors(root_p: Path, pp, response: str, requests_list: list, turn_obj: dict, value_obj: dict, del_chk: dict, *, factual_kb_fn, is_deliv_fn) -> list[str]:
	from .workflow import load
	wf_state = load(root_p)
	wf_ids = {req['id'] for req in requests_list}
	wf_cov = {req['id'] for req in wf_state.get('requests') or []} & wf_ids
	is_fin = 'complete' == wf_state.get('stages', {}).get('finalize', {}).get('status')
	kb_scan = factual_kb_fn(root_p, turn_obj)
	wf_errs = [f'KB-2 / DOC-1 violation in factual research note: {e}' for e in kb_scan['issues']]
	has_kb_mut = kb_scan['has_normative'] or bool(turn_obj.get('issue_actions')) or bool(value_obj.get('github_issues'))
	touches_deliv = any((is_deliv_fn(tf, root_p) for tf in (turn_obj.get('touched_files') or ())))
	has_hm = bool(_HM_CLAIM_RE.search(response))
	substantive_hm = (kb_scan['has_analysis'] or (has_hm and 0 == del_chk.get('aa_subagent_step_count', 0))) if is_fin else (has_hm or has_kb_mut or touches_deliv)
	wf_errs.extend(_authorize_workflow_errors(root_p, pp, wf_state, wf_ids, wf_cov, is_fin, substantive_hm, requests_list, response))
	return wf_errs
def audit_runner_workflow_scope(runner, *, factual_kb_fn, is_deliv_fn) -> None:
	if runner.blocked_report:
		issues = blocked_report_issues(runner.pp, runner.response, workflow_exists=runner.workflow_path.exists(), is_finalized=runner.is_finalized)
		if issues:
			runner._fail_gate('blocked_report', '; '.join(issues))
	elif runner.workflow_path.exists():
		kb_scan = factual_kb_fn(runner.root, runner.turn)
		if kb_scan['issues']:
			runner._fail_gate('factual_kb_note', 'KB-2 / DOC-1 violation in factual research note: ' + '; '.join(kb_scan['issues']))
		has_kb_mut = kb_scan['has_normative'] or bool(runner.turn.get('issue_actions')) or bool(runner.value.get('github_issues'))
		touches_deliv = any((is_deliv_fn(tf, runner.root) for tf in (runner.turn.get('touched_files') or ())))
		has_hm = bool(_HM_CLAIM_RE.search(runner.response))
		runner.has_substantive_hm = (kb_scan['has_analysis'] or (has_hm and 0 == runner.value['delegation_check'].get('aa_subagent_step_count', 0))) if runner.is_finalized else (has_hm or has_kb_mut or touches_deliv)
		if runner.wf_covered and runner.wf_covered != runner.wf_identifiers:
			raise ValueError('Adopt all exact current requests before preparing a tracked analysis response')
		if not runner.wf_covered and runner.pp.project_json.is_file() and (not any((re.search('(?:^|\\s)/df-(?:article|proposal)\\b', req.get('text', '')) for req in runner.turn['requests']))) and (not runner.is_finalized or runner.has_substantive_hm):
			runner._fail_gate('workflow_adoption', 'REVIEW-3 / REVIEW-4: Adopt current requests (adopt-requests) and complete review authorization before preparing a substantive response in a tracked Upwork project')
def blocked_report_issues(pp, response: str, *, workflow_exists: bool, is_finalized: bool) -> list[str]:
	issues: list[str] = []
	if not workflow_exists or is_finalized:
		issues.append('FILE-3 / REVIEW-3 blocked-report: --blocked-report applies only to pre-finalize tracked workflow projects')
	cont_err = _continuation_blocker_issue(pp.continuation_md)
	if None is not cont_err:
		issues.append(cont_err)
	prose = _FENCED_RE.sub('', response or '')
	if _HM_CLAIM_RE.search(prose):
		issues.append('REVIEW-3 blocked-report: analytical H-*/M-* claims are prohibited in --blocked-report; complete A.A review authorization instead')
	if _STAGE_HEADING_RE.search(prose):
		issues.append('REVIEW-3 blocked-report: five-stage analysis sections are prohibited in --blocked-report; complete A.A review authorization instead')
	return issues
def evaluate_check_workflow_errors(root_p: Path, pp, role: str, response: str, requests_list: list, turn_obj: dict, value_obj: dict, del_chk: dict, *, blocked_report: bool, journal_directory, factual_kb_fn, is_deliv_fn, dir_fn) -> list[str]:
	wf_errs: list[str] = []
	if 'primary' == role and blocked_report:
		wf_exists = pp.workflow_json.is_file()
		is_fin = False
		if wf_exists:
			from .workflow import load
			is_fin = 'complete' == load(root_p).get('stages', {}).get('finalize', {}).get('status')
		wf_errs.extend(blocked_report_issues(pp, response, workflow_exists=wf_exists, is_finalized=is_fin))
	elif 'primary' == role and pp.workflow_json.is_file():
		wf_errs.extend(_standard_workflow_errors(root_p, pp, response, requests_list, turn_obj, value_obj, del_chk, factual_kb_fn=factual_kb_fn, is_deliv_fn=is_deliv_fn))
	if 'primary' == role and (not blocked_report) and (pp.data_dir / 'client-text/index.json').is_file():
		from .text_workflow import gate_requests
		try:
			gate_requests([root_p, dir_fn(root_p, value_obj.get('journal') or journal_directory)], [r['text'] for r in requests_list], response, capture=False)
		except (OSError, ValueError) as exc:
			wf_errs.append(str(exc))
	return wf_errs
def record_blocked_report_entry(runner) -> None:
	runner._record_journal_entry()
	runner.value['completion_kind'] = 'blocked_report'
	if isinstance(runner.value.get('prepared'), dict):
		runner.value['prepared']['completion_kind'] = 'blocked_report'
def sync_authorized_workflow_requests(runner, approval: dict, now_fn) -> None:
	pending = {req['id'] for req in runner.wf_state['requests'] if not req.get('response_prepared') and (req.get('native_conversation_id') in (None, runner.native['conversation_id']) or req['id'] in runner.wf_identifiers)}
	if pending:
		if pending != runner.wf_identifiers:
			raise ValueError('Align unanswered tracked requests with the exact current native turn before preparation')
		from .workflow import record_current_answer
		prep = runner.value['prepared']
		record_current_answer(runner.root, runner.response, journal_directory=runner.value['journal'], request_ids=runner.wf_identifiers, preauthorized=approval, recorded_steps=prep['journal_steps'], turn_token=Path(prep['group_file']).stem)
	elif any((req['response_prepared']['sha256'] != runner.sha for req in runner.wf_state['requests'] if req['id'] in runner.wf_identifiers)):
		if not runner.allow_reprepare:
			raise ValueError('Tracked analysis requests already have different prepared response bytes')
		from .workflow import update
		def update_reprepared(s):
			for req in s.get('requests', []):
				if req['id'] in runner.wf_identifiers:
					req['response_prepared'] = {'sha256': runner.sha, 'prepared_at': now_fn()}
		update(runner.root, {'action': 'reprepare_before_delivery', 'request_ids': sorted(runner.wf_identifiers)}, update_reprepared)
