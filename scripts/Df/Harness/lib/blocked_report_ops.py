# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from pathlib import Path
from typing import Any
from Df.Harness.lib.hook_addon_ops import dfh_check_runner_addon_observability
from Df.Harness.lib.hook_crash_ops import dfh_check_runner_hook_crashes
from Df.Harness.lib.hook_verif_ops import dfh_check_runner_verification_observability
import re
# 2026-11-26 "Move turn lifecycle subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/383
_BLOCKER_HINT_RE = re.compile(r'(?i)(?:block(?:er|ed|ing)?|error|fail(?:ed|ure)?|pause[d]?|interrupt(?:ed)?|unavailab\w*|timeout|expired|mismatch|\u0431\u043b\u043e\u043a\u0435\u0440\w*|\u0437\u0430\u0431\u043b\u043e\u043a\u0438\u0440\w*|\u043e\u0448\u0438\u0431\u043a\w*|\u0441\u0431\u043e[\u0439\u0435\u0432\u044f]\w*|\u043f\u0440\u0435\u0440\u0432\u0430\u043d\w*|\u043d\u0435\u0434\u043e\u0441\u0442\u0443\u043f\w*)')
_CLIENT_HM_CLAIM_RE = re.compile(r'\b(?:H|M)-(?:SITE|IDENTITY|CONCERN|MISC|CAUSE|METHOD|CLIENT|RF)-[A-Za-z0-9-]*\b', re.I)
_DOC5_HEADER_RE = re.compile(r'(?m)^#\s+0\b')
_DOC5_SECTIONS_RE = re.compile(r'(?m)^#\s+([1-4])\b')
_FENCED_RE = re.compile(r'```[\s\S]*?```')
_HM_CLAIM_RE = re.compile(r'\b(?:H|M)-(?:[A-Za-z0-9]+-)*\d+\b')
_STAGE_HEADING_RE = re.compile(r'(?im)^#{1,3}\s+(?:\d+\.\s+)?(?:client identification|client concerns|possible misconceptions|causes of the problem|solution methods|\u0438\u0434\u0435\u043d\u0442\u0438\u0444\u0438\u043a\u0430\u0446\u0438\u044f\s+\u043a\u043b\u0438\u0435\u043d\u0442\u0430|\u0447\u0442\u043e\s+\u0432\u043e\u043b\u043d\u0443\u0435\u0442|\u0432\u043e\u0437\u043c\u043e\u0436\u043d\u044b\u0435\s+\u0437\u0430\u0431\u043b\u0443\u0436\u0434\u0435\u043d\u0438\u044f|\u043f\u0440\u0438\u0447\u0438\u043d\u044b\s+\u043f\u0440\u043e\u0431\u043b\u0435\u043c\w*|\u043c\u0435\u0442\u043e\u0434\u044b\s+\u0440\u0435\u0448\u0435\u043d\u0438\u044f)\b')
# @used-by :func:`_standard_workflow_errors()`
def _authorize_workflow_errors(root_p: Path, pp: Any, wf_state: dict, wf_ids: set, wf_cov: set, is_fin: bool, substantive_hm: bool, requests_list: list, response: str, *, conversation_id: str | None=None) -> list[str]:
	errs: list[str] = []
	if wf_cov and wf_cov != wf_ids:
		errs.append('Adopt all exact current requests before preparing a tracked analysis response')
	elif _needs_upwork_adoption(pp, wf_cov, requests_list, is_fin, substantive_hm):
		errs.append('REVIEW-3 / REVIEW-4: Adopt current requests (adopt-requests) and complete review authorization before preparing a substantive response in a tracked Upwork project')
	elif wf_cov and (not is_fin or substantive_hm):
		from agent_tools.review import authorize
		try:
			authorize(root_p, wf_state, response=response, request_ids=wf_ids)
		except (OSError, ValueError) as exc:
			errs.append(str(exc))
		errs.extend(dfh_pending_workflow_alignment_issues(wf_state, conversation_id, wf_ids))
	return errs
# @used-by :func:`dfh_evaluate_check_workflow_errors()`
def _check_text_workflow_gate(root_p: Path, pp: Any, value_obj: dict, journal_directory: Any, requests_list: list, response: str, dir_fn) -> list[str]:
	errs: list[str] = []
	if (pp.data_dir / 'client-text/index.json').is_file():
		from agent_tools.text_workflow import gate_requests
		try:
			gate_requests([root_p, dir_fn(root_p, value_obj.get('journal') or journal_directory)], [req['text'] for req in requests_list], response, capture=False)
		except (OSError, ValueError) as exc:
			errs.append(str(exc))
	return errs
# @used-by :func:`dfh_blocked_report_issues()`
def _continuation_blocker_issue(cont_path: Path) -> str | None:
	r: str | None = None
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
# @used-by :func:`dfh_evaluate_runner_code_hygiene()`
def _fail_hygiene_gates(runner: Any, if_chk: dict, lc_chk: dict, tdd_chk: dict) -> None:
	if not if_chk['verified']:
		runner._fail_gate('issue_first', '; '.join(if_chk['violations']))
	if not lc_chk['verified']:
		runner._fail_gate('code_lifecycle', 'EXEC-5 violation in active turn (code/issue lifecycle incomplete): ' + '; '.join(lc_chk['violations']))
	if not tdd_chk['verified']:
		runner._fail_gate('tdd', '; '.join(tdd_chk['violations']))
# @used-by :func:`_standard_workflow_errors()`
# @used-by :func:`dfh_audit_runner_workflow_scope()`
def _has_substantive_hm(kb_scan: dict, turn_obj: dict, value_obj: dict, response: str, del_chk: dict, is_fin: bool, root_p: Path, is_deliv_fn) -> bool:
	has_kb_mut = kb_scan['has_normative'] or bool(turn_obj.get('issue_actions')) or bool(value_obj.get('github_issues'))
	touches_deliv = any((is_deliv_fn(tf, root_p) for tf in (turn_obj.get('touched_files') or ())))
	has_hm = bool(_HM_CLAIM_RE.search(response))
	if is_fin:
		r = bool(kb_scan['has_analysis'] or (has_hm and 0 == del_chk.get('aa_subagent_step_count', 0)))
	else:
		r = bool(has_hm or has_kb_mut or touches_deliv)
	return r
# @used-by :func:`dfh_blocked_report_issues()`
def _is_doc5_blocker_analysis(response: str) -> bool:
	txt = response or ''
	has_meta = bool(_DOC5_HEADER_RE.search(txt)) and ('"Issue"' in txt or '"Source Project"' in txt)
	has_sections = 4 <= len(set(_DOC5_SECTIONS_RE.findall(txt)))
	return has_meta and has_sections
# @used-by :func:`_authorize_workflow_errors()`
# @used-by :func:`dfh_audit_runner_workflow_scope()`
def _needs_upwork_adoption(pp: Any, wf_cov: set, requests_list: list, is_fin: bool, substantive_hm: bool) -> bool:
	is_client_text = any((re.search('(?:^|\\s)/df-(?:article|proposal)\\b', req.get('text', '')) for req in requests_list))
	return (not wf_cov) and pp.project_json.is_file() and (not is_client_text) and (not is_fin or substantive_hm)
# @used-by :func:`dfh_pending_workflow_alignment_issues()`
# @used-by :func:`dfh_sync_authorized_workflow_requests()`
def _pending_workflow_ids(wf_state: dict, conversation_id: str | None, wf_identifiers: set) -> set:
	reqs = wf_state.get('requests') or []
	return {req['id'] for req in reqs if not req.get('response_prepared') and (req.get('native_conversation_id') in (None, conversation_id) or req['id'] in wf_identifiers)}
# @used-by :func:`dfh_evaluate_runner_code_hygiene()`
def _run_runner_audits(runner: Any) -> None:
	from agent_tools.arch.evaluator import check_runner_architecture
	dfh_check_runner_hook_crashes(runner)
	dfh_check_runner_addon_observability(runner)
	dfh_check_runner_verification_observability(runner)
	check_runner_architecture(runner)
# @used-by :func:`dfh_evaluate_check_workflow_errors()`
def _standard_workflow_errors(root_p: Path, pp: Any, response: str, requests_list: list, turn_obj: dict, value_obj: dict, del_chk: dict, *, factual_kb_fn, is_deliv_fn) -> list[str]:
	from agent_tools.workflow import load
	wf_state = load(root_p)
	wf_ids = {req['id'] for req in requests_list}
	wf_cov = {req['id'] for req in wf_state.get('requests') or []} & wf_ids
	is_fin = 'complete' == wf_state.get('stages', {}).get('finalize', {}).get('status')
	kb_scan = factual_kb_fn(root_p, turn_obj)
	wf_errs = [f'KB-2 / DOC-1 violation in factual research note: {e}' for e in kb_scan['issues']]
	substantive_hm = _has_substantive_hm(kb_scan, turn_obj, value_obj, response, del_chk, is_fin, root_p, is_deliv_fn)
	wf_errs.extend(_authorize_workflow_errors(root_p, pp, wf_state, wf_ids, wf_cov, is_fin, substantive_hm, requests_list, response, conversation_id=value_obj.get('conversation_id')))
	return wf_errs
# @used-by :func:`dfh_sync_authorized_workflow_requests()`
def _update_reprepared_workflow(runner: Any, now_fn) -> None:
	from agent_tools.workflow import update
	# @used-by :func:`_update_reprepared_workflow()`
	def _mutate(state: dict) -> None:
		for req in state.get('requests', []):
			if req['id'] in runner.wf_identifiers:
				req['response_prepared'] = {'sha256': runner.sha, 'prepared_at': now_fn()}
	update(runner.root, {'action': 'reprepare_before_delivery', 'request_ids': sorted(runner.wf_identifiers)}, _mutate)
# @used-by :meth:`Df.Harness.Completion.AnswerPreparer.AnswerPreparer.__audit_workflow_scope()`
def dfh_audit_runner_workflow_scope(runner: Any, *, factual_kb_fn, is_deliv_fn) -> None:
	if runner.blocked_report:
		issues = dfh_blocked_report_issues(runner.pp, runner.response, workflow_exists=runner.workflow_path.exists(), is_finalized=runner.is_finalized)
		if issues:
			runner._fail_gate('blocked_report', '; '.join(issues))
	elif runner.workflow_path.exists():
		kb_scan = factual_kb_fn(runner.root, runner.turn)
		if kb_scan['issues']:
			runner._fail_gate('factual_kb_note', 'KB-2 / DOC-1 violation in factual research note: ' + '; '.join(kb_scan['issues']))
		runner.has_substantive_hm = _has_substantive_hm(kb_scan, runner.turn, runner.value, runner.response, runner.value['delegation_check'], runner.is_finalized, runner.root, is_deliv_fn)
		if runner.wf_covered and runner.wf_covered != runner.wf_identifiers:
			raise ValueError('Adopt all exact current requests before preparing a tracked analysis response')
		if _needs_upwork_adoption(runner.pp, runner.wf_covered, runner.turn['requests'], runner.is_finalized, runner.has_substantive_hm):
			runner._fail_gate('workflow_adoption', 'REVIEW-3 / REVIEW-4: Adopt current requests (adopt-requests) and complete review authorization before preparing a substantive response in a tracked Upwork project')
# @used-by :func:`dfh_audit_runner_workflow_scope()`
# @used-by :func:`dfh_evaluate_check_workflow_errors()`
# @used-by :meth:`Df.Harness.Completion.BlockedReportAuditor.BlockedReportAuditor.run()`
def dfh_blocked_report_issues(pp: Any, response: str, *, workflow_exists: bool, is_finalized: bool) -> list[str]:
	issues: list[str] = []
	if not workflow_exists or is_finalized:
		issues.append('FILE-3 / REVIEW-3 blocked-report: --blocked-report applies only to pre-finalize tracked workflow projects')
	cont_err = _continuation_blocker_issue(pp.continuation_md)
	if None is not cont_err:
		issues.append(cont_err)
	prose = _FENCED_RE.sub('', response or '')
	has_client_hm = bool(_CLIENT_HM_CLAIM_RE.search(prose))
	has_generic_hm = bool(_HM_CLAIM_RE.search(prose)) and (not _is_doc5_blocker_analysis(response or ''))
	if has_client_hm or has_generic_hm:
		issues.append('REVIEW-3 blocked-report: analytical H-*/M-* claims are prohibited in --blocked-report; complete A.A review authorization instead')
	if _STAGE_HEADING_RE.search(prose):
		issues.append('REVIEW-3 blocked-report: five-stage analysis sections are prohibited in --blocked-report; complete A.A review authorization instead')
	return issues
# @used-by :func:`Df.Harness.lib.completion_commands._collect_check_payload()`
def dfh_evaluate_check_workflow_errors(root_p: Path, pp: Any, role: str, response: str, requests_list: list, turn_obj: dict, value_obj: dict, del_chk: dict, *, blocked_report: bool, journal_directory: Any, factual_kb_fn, is_deliv_fn, dir_fn) -> list[str]:
	wf_errs: list[str] = []
	if 'primary' == role:
		if blocked_report:
			wf_exists = pp.workflow_json.is_file()
			from agent_tools.workflow import load
			is_fin = 'complete' == load(root_p).get('stages', {}).get('finalize', {}).get('status') if wf_exists else False
			wf_errs.extend(dfh_blocked_report_issues(pp, response, workflow_exists=wf_exists, is_finalized=is_fin))
		elif pp.workflow_json.is_file():
			wf_errs.extend(_standard_workflow_errors(root_p, pp, response, requests_list, turn_obj, value_obj, del_chk, factual_kb_fn=factual_kb_fn, is_deliv_fn=is_deliv_fn))
		if not blocked_report:
			wf_errs.extend(_check_text_workflow_gate(root_p, pp, value_obj, journal_directory, requests_list, response, dir_fn))
	return wf_errs
# @used-by :meth:`Df.Harness.Completion.AnswerPreparer.AnswerPreparer.__check_turn_hygiene()`
def dfh_evaluate_runner_code_hygiene(runner: Any, *, issue_first_fn, lifecycle_fn, tdd_fn) -> None:
	from agent_tools.scope_deferral import check_runner_scope_deferral
	_run_runner_audits(runner)
	if_chk = issue_first_fn(runner.root, runner.turn)
	lc_chk = lifecycle_fn(runner.root, runner.turn, runner.value, response=runner.response)
	tdd_chk = tdd_fn(runner.root, runner.turn)
	runner.value['issue_first_check'] = if_chk
	runner.value['code_lifecycle_check'] = lc_chk
	runner.value['tdd_check'] = tdd_chk
	check_runner_scope_deferral(runner, lc_chk)
	if runner.blocked_report:
		runner.value['blocked_hygiene_diagnostics'] = {k: list(chk.get('violations') or []) for k, chk in (('issue_first', if_chk), ('code_lifecycle', lc_chk), ('tdd', tdd_chk)) if not chk.get('verified', True)}
	else:
		_fail_hygiene_gates(runner, if_chk, lc_chk, tdd_chk)
# @used-by :func:`_authorize_workflow_errors()`
# @used-by :func:`dfh_prepare_and_sync_authorized_workflow()`
def dfh_pending_workflow_alignment_issues(wf_state: dict, conversation_id: str | None, wf_identifiers: set, *, response_sha: str | None=None, allow_reprepare: bool=False) -> list[str]:
	errs: list[str] = []
	reqs = wf_state.get('requests') or []
	pending = _pending_workflow_ids(wf_state, conversation_id, wf_identifiers)
	if pending and pending != wf_identifiers:
		errs.append('Align unanswered tracked requests with the exact current native turn before preparation')
	elif not pending and None is not response_sha and (not allow_reprepare) and any(((req.get('response_prepared') or {}).get('sha256') != response_sha for req in reqs if req['id'] in wf_identifiers)):
		errs.append('Tracked analysis requests already have different prepared response bytes')
	return errs
# @used-by :meth:`Df.Harness.Completion.AnswerPreparer.AnswerPreparer.__authorize_and_sync_workflow()`
def dfh_prepare_and_sync_authorized_workflow(runner: Any, approval: dict, now_fn) -> None:
	align_errs = dfh_pending_workflow_alignment_issues(runner.wf_state, runner.native['conversation_id'], runner.wf_identifiers, response_sha=runner.sha, allow_reprepare=runner.allow_reprepare)
	if align_errs:
		runner._fail_gate('review_authorize', '; '.join(align_errs))
	runner._record_journal_entry()
	dfh_sync_authorized_workflow_requests(runner, approval, now_fn)
# @used-by :meth:`Df.Harness.Completion.AnswerPreparer.AnswerPreparer.__authorize_and_sync_workflow()`
def dfh_record_blocked_report_entry(runner: Any) -> None:
	runner._record_journal_entry()
	runner.value['completion_kind'] = 'blocked_report'
	if isinstance(runner.value.get('prepared'), dict):
		runner.value['prepared']['completion_kind'] = 'blocked_report'
# @used-by :func:`dfh_prepare_and_sync_authorized_workflow()`
def dfh_sync_authorized_workflow_requests(runner: Any, approval: dict, now_fn) -> None:
	pending = _pending_workflow_ids(runner.wf_state, runner.native['conversation_id'], runner.wf_identifiers)
	if pending:
		if pending != runner.wf_identifiers:
			raise ValueError('Align unanswered tracked requests with the exact current native turn before preparation')
		from agent_tools.workflow import record_current_answer
		prep = runner.value['prepared']
		record_current_answer(runner.root, runner.response, journal_directory=runner.value['journal'], request_ids=runner.wf_identifiers, preauthorized=approval, recorded_steps=prep['journal_steps'], turn_token=Path(prep['group_file']).stem)
	elif any((req['response_prepared']['sha256'] != runner.sha for req in runner.wf_state['requests'] if req['id'] in runner.wf_identifiers)):
		if not runner.allow_reprepare:
			raise ValueError('Tracked analysis requests already have different prepared response bytes')
		_update_reprepared_workflow(runner, now_fn)