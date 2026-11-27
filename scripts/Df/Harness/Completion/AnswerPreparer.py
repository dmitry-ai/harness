# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from pathlib import Path
from typing import Any
from Df.Harness.lib.blocked_report_ops import dfh_audit_runner_workflow_scope, dfh_evaluate_runner_code_hygiene, dfh_prepare_and_sync_authorized_workflow, dfh_record_blocked_report_entry
from Df.Harness.lib.completion_checks import dfh_factual_kb_note_issues, dfh_intermediate_or_language_issues, dfh_is_client_deliverable_path, dfh_issue_first_status, dfh_tdd_status
from Df.Harness.lib.completion_compaction import dfh_compact_compaction_check, dfh_find_evicted_cited_files, dfh_write_compaction_index_file
from Df.Harness.lib.completion_core import dfh_hash, dfh_json, dfh_now, dfh_persist, dfh_recorded, dfh_sync_antigravity_conversation_title, dfh_turns_folder
from Df.Harness.lib.completion_record import dfh_matches_recorded_response, dfh_record
from Df.Harness.lib.completion_state import dfh_load_turn_state, dfh_unchanged
from Df.Harness.lib.path_resolve import dfh_project_paths
import sqlite3
# 2026-11-26 "Move turn lifecycle subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/383
class AnswerPreparer:
	# @used-by :func:`Df.Harness.lib.completion_commands.dfh_prepare_once()`
	# @used-by :meth:`test_df_harness_s11_wave2d_tail_cov.DfHarnessS11Wave2dTailCovTests.test_completion_tail()`
	# @used-by :meth:`test_turn_completion.AnswerPreparationRunnerTests.test_gate_id_auto_clearing_and_resolve_journal_dir()`
	def __init__(self, root: str | Path, response: str, result: dict, native: dict, turn: dict, *, blocked_report: bool=False, _ops: dict[str, Any] | None=None) -> None:
		self.__ops = _ops or {}
		self.pp = dfh_project_paths(root, exact_root=True)
		self.root, self.response, self.blocked_report = (self.pp.root, response, bool(blocked_report))
		self.sha = (self.__ops.get('hash') or dfh_hash)(response.encode('utf-8'))
		self.result = result
		self.native = native
		self.turn = turn
		state_fn = self.__ops.get('state') or (lambda r, n, t: dfh_load_turn_state(r, n, t, ops=self.__ops))
		self.path, self.value = state_fn(self.root, native, turn)
		self.allow_reprepare = False
		self.workflow_path = self.pp.workflow_json
		self.wf_state: dict | None = None
		self.wf_identifiers: set = set()
		self.wf_covered: set = set()
		self.is_finalized = False
		self.has_substantive_hm = False
		self.admission_check: dict | None = None
	# @used-by :meth:`AnswerPreparer.run()`
	def __audit_workflow_scope(self) -> None:
		if self.workflow_path.exists():
			from agent_tools.workflow import load
			self.wf_state = load(self.root)
			self.wf_identifiers = {req['id'] for req in self.turn['requests']}
			self.wf_covered = {req['id'] for req in self.wf_state['requests']} & self.wf_identifiers
			self.is_finalized = 'complete' == self.wf_state.get('stages', {}).get('finalize', {}).get('status')
		dfh_audit_runner_workflow_scope(self, factual_kb_fn=dfh_factual_kb_note_issues, is_deliv_fn=dfh_is_client_deliverable_path)
	# @used-by :meth:`AnswerPreparer.run()`
	def __authorize_and_sync_workflow(self) -> None:
		now_fn = self.__ops.get('now') or dfh_now
		if self.blocked_report:
			dfh_record_blocked_report_entry(self)
		elif None is self.wf_state or (not self.wf_covered):
			self._record_journal_entry()
		elif self.is_finalized and (not self.has_substantive_hm):
			self.__post_finalize_workflow(now_fn)
		else:
			from agent_tools.review import authorize
			try:
				approval = authorize(self.root, self.wf_state, response=self.response, request_ids=self.wf_identifiers)
			except (OSError, ValueError) as exc:
				self._fail_gate('review_authorize', str(exc), cause=exc)
			dfh_prepare_and_sync_authorized_workflow(self, approval, now_fn)
	# @used-by :meth:`AnswerPreparer.__check_turn_hygiene()`
	def __check_evicted_citations(self) -> None:
		unreread_cited = dfh_find_evicted_cited_files(self.root, self.pp, self.result['turn_key'], self.value['compaction_check'], self.response)
		if unreread_cited:
			detail = 'COMPACT-1 / KB-3 violation in active turn: primary source file(s) read before CHECKPOINT were evicted from context and cited in response without re-reading after checkpoint: ' + ', '.join(unreread_cited)
			self._fail_gate('evicted_citations', detail, extra={'cited_files': unreread_cited})
	# @used-by :meth:`AnswerPreparer.__check_turn_hygiene()`
	def __check_reprepare_and_conflict(self) -> None:
		if self.value['prepared'] and (not dfh_matches_recorded_response(self.value['prepared'], self.response, self.sha, ops=self.__ops)):
			if None is not self.value.get('delivery') or 'delivered' == self.value.get('status') or self.turn.get('completed'):
				raise ValueError('Prepared response bytes are immutable after delivery; preserve the earlier version and reconcile before a corrective turn')
			self.allow_reprepare = True
		if 'conflict' == self.value['status']:
			raise ValueError('Resolve the native delivery conflict without overwriting journal history')
		aa_part_errs = self.value['delegation_check'].get('aa_partial_read_violations') or []
		if aa_part_errs:
			self._fail_gate('aa_partial_read', 'REVIEW-3 / REVIEW-4: Independent A.A reviewer subagent performed a partial/truncated read of the candidate response: ' + '; '.join(aa_part_errs))
	# @used-by :meth:`AnswerPreparer.run()`
	def __check_source_grounding(self) -> None:
		from agent_tools.response_grounding import response_source_and_kb_issues
		source_issues = response_source_and_kb_issues(self.root, self.response, self.turn['requests'], touched_files=self.turn.get('touched_files'), turn=self.turn, native=self.native)
		self.value['source_kb_check'] = {'verified': not source_issues, 'issues': source_issues}
		if source_issues:
			self._fail_gate('source_grounding', '; '.join(source_issues))
	# @used-by :meth:`AnswerPreparer.run()`
	def __check_turn_hygiene(self) -> None:
		from agent_tools.issue_lifecycle import code_and_issue_lifecycle_status
		self.__check_violation_gates()
		self.__check_evicted_citations()
		if not self.value['delegation_check']['verified']:
			dc = self.value['delegation_check']
			detail = f"REVIEW-1 / KB-3 violation in active turn: bulk primary-agent research (tool_steps={dc['tool_step_count']}, max_streak={dc.get('max_unpersisted_step_streak', 0)} > {dc['max_unpersisted_steps']}, or unpersisted_source_reads={dc.get('max_unpersisted_source_reads', 0)} >= {dc.get('max_allowed_unpersisted_source_reads', 10)}) executed without A.F/A.A subagent delegation or incremental \ua616/KB persistence"
			self._fail_gate('delegation', detail)
		dfh_evaluate_runner_code_hygiene(self, issue_first_fn=self.__ops.get('issue_first_status') or dfh_issue_first_status, lifecycle_fn=self.__ops.get('code_lifecycle_status') or code_and_issue_lifecycle_status, tdd_fn=self.__ops.get('tdd_status') or dfh_tdd_status)
		lang_issues = (self.__ops.get('lang_issues') or (lambda reqs, resp: dfh_intermediate_or_language_issues(reqs, resp, ops=self.__ops)))(self.turn['requests'], self.response)
		self.value['language_and_stub_check'] = {'verified': not lang_issues, 'issues': lang_issues}
		if lang_issues:
			self._fail_gate('language_and_stub', '; '.join(lang_issues))
		self.__check_reprepare_and_conflict()
	# @used-by :meth:`AnswerPreparer.__check_turn_hygiene()`
	def __check_violation_gates(self) -> None:
		if not self.value['exec5_check']['verified']:
			commands = [cmd for item in self.value['exec5_check']['violations'] for cmd in item.get('commands', [])]
			self._fail_gate('exec5', 'EXEC-5 violation in active turn (git read command without --no-optional-locks; run recover-turn-violation to record retrospective violation receipt before answer-prepare): ' + '; '.join(commands))
		if not self.value['http_fetch_check']['verified']:
			commands = [cmd for item in self.value['http_fetch_check']['violations'] for cmd in item.get('commands', [])]
			self._fail_gate('http_fetch', 'KB-3 / EXEC-1 violation in active turn (ad-hoc HTTP fetch in shell without persistent Evidence collection; use collect/collect-http or run recover-turn-violation to record retrospective violation receipt before answer-prepare): ' + '; '.join(commands))
		if not self.value['compaction_check']['verified']:
			unreread_src = self.value['compaction_check'].get('unreread_analysis_sources') or []
			detail = ('COMPACT-1 / KB-3 violation in active turn: analysis.md written after CHECKPOINT without re-reading evicted sibling source.md: ' + ', '.join(unreread_src)) if unreread_src else 'COMPACT-1 / KB-3 violation in active turn: context compaction (CHECKPOINT) occurred after tool calls without post-checkpoint recovery; run recover-checkpoint or inspect transcript_full.jsonl before answer-prepare'
			self._fail_gate('compaction', detail)
	# @used-by :meth:`AnswerPreparer.run()`
	def __finalize_prepared_state(self) -> dict[str, Any]:
		now_fn = self.__ops.get('now') or dfh_now
		persist_fn = self.__ops.get('persist') or (lambda p, v: dfh_persist(p, v, ops=self.__ops))
		self.value['status'] = 'prepared'
		self.value.pop('reserved_journal_steps', None)
		if not self.value.get('readiness_check', {}).get('verified'):
			self.value['readiness_check'] = {'verified': True, 'checked_at': now_fn()}
		if self.value.get('compaction_check', {}).get('occurred') and (not self.turn.get('completed')):
			self.value['compaction_check']['index_file'] = dfh_write_compaction_index_file(self.root, self.value['key'], self.turn, self.value['compaction_check'], folder_fn=self.__ops.get('folder') or dfh_turns_folder, now_fn=now_fn, json_fn=self.__ops.get('json') or dfh_json, hash_fn=self.__ops.get('hash') or dfh_hash)
		persist_fn(self.path, self.value)
		title_sync = dfh_sync_antigravity_conversation_title(self.root, self.native, self.value['journal'], ops=self.__ops)
		r = {**self.result, 'compaction_check': dfh_compact_compaction_check(self.value['compaction_check']), **self.value['prepared'], 'ready': True, 'status': 'prepared', 'delivery_verified': False, 'admission_verification': self.admission_check}
		if None is not title_sync:
			r['conversation_title_sync'] = title_sync
		return r
	# @used-by :meth:`AnswerPreparer.__authorize_and_sync_workflow()`
	def __post_finalize_workflow(self, now_fn) -> None:
		from agent_tools.workflow import update
		self._record_journal_entry()
		# @used-by :meth:`AnswerPreparer.__post_finalize_workflow()`
		def _change(state: dict) -> None:
			for req in state.get('requests', []):
				if req['id'] in self.wf_identifiers and (not req.get('response_prepared') or self.allow_reprepare):
					req['response_prepared'] = {'sha256': self.sha, 'prepared_at': now_fn()}
		update(self.root, {'action': 'post_finalize_answer', 'request_ids': sorted(self.wf_identifiers)}, _change)
	# @used-by :meth:`AnswerPreparer.run()`
	def __verify_delivered_fast_path(self) -> dict[str, Any] | None:
		if 'delivered' != self.value['status']:
			r: dict[str, Any] | None = None
		else:
			recorded = dfh_recorded(self.value)
			if not recorded or (not dfh_matches_recorded_response(recorded, self.response, self.sha, ops=self.__ops)):
				raise ValueError('Delivered response bytes are immutable; preserve the completed turn')
			hash_fn = self.__ops.get('hash') or dfh_hash
			if not self.turn.get('completed') or self.value['delivery'].get('native_response_sha256') != hash_fn(self.turn['response'].encode('utf-8')):
				raise ValueError('The saved native delivery requires foreground reconciliation before preparation')
			record_fn = self.__ops.get('record') or (lambda r_p, n, t, resp, d, **kw: dfh_record(r_p, n, t, resp, d, ops=self.__ops, **kw))
			recorded, admission_check = record_fn(self.root, self.native, self.turn, self.response, self.value['journal'], existing=recorded, purpose='observation')
			r = {**self.result, **recorded, 'ready': True, 'status': 'delivered', 'delivery_verified': True, 'preparation_verified': self.value['delivery'].get('preparation_verified', False), 'admission_verification': admission_check}
		return r
	# @used-by :func:`Df.Harness.lib.blocked_report_ops._fail_hygiene_gates()`
	# @used-by :func:`Df.Harness.lib.blocked_report_ops.dfh_audit_runner_workflow_scope()`
	# @used-by :func:`Df.Harness.lib.blocked_report_ops.dfh_prepare_and_sync_authorized_workflow()`
	# @used-by :func:`Df.Harness.lib.hook_addon_ops.dfh_check_runner_addon_observability()`
	# @used-by :func:`Df.Harness.lib.hook_crash_ops.dfh_check_runner_hook_crashes()`
	# @used-by :func:`Df.Harness.lib.hook_verif_ops.dfh_check_runner_verification_observability()`
	# @used-by :func:`agent_tools.scope_deferral.check_runner_scope_deferral()`
	# @used-by :meth:`AnswerPreparer.__authorize_and_sync_workflow()`
	# @used-by :meth:`AnswerPreparer.__check_evicted_citations()`
	# @used-by :meth:`AnswerPreparer.__check_reprepare_and_conflict()`
	# @used-by :meth:`AnswerPreparer.__check_source_grounding()`
	# @used-by :meth:`AnswerPreparer.__check_turn_hygiene()`
	# @used-by :meth:`AnswerPreparer.__check_violation_gates()`
	# @used-by :meth:`AnswerPreparer._record_journal_entry()`
	# @used-by :meth:`AnswerPreparer.run()`
	# @used-by :meth:`Df.Harness.Arch.Evaluator.Evaluator.check_runner()`
	def _fail_gate(self, gate_id: str, detail: str, *, admission_failed: bool=False, status: str | None=None, extra: dict | None=None, cause: BaseException | None=None) -> None:
		now_fn = self.__ops.get('now') or dfh_now
		persist_fn = self.__ops.get('persist') or (lambda p, v: dfh_persist(p, v, ops=self.__ops))
		if admission_failed:
			self.value['admission_failure'] = {'detail': detail, 'checked_at': now_fn()}
		if None is not status:
			self.value['status'] = status
		rc: dict[str, Any] = {'verified': False, 'gate_id': gate_id, 'checked_at': now_fn(), 'detail': detail}
		if extra:
			rc.update(extra)
		self.value['readiness_check'] = rc
		persist_fn(self.path, self.value)
		if None is cause:
			raise ValueError(detail)
		raise cause
	# @used-by :func:`Df.Harness.lib.blocked_report_ops.dfh_prepare_and_sync_authorized_workflow()`
	# @used-by :func:`Df.Harness.lib.blocked_report_ops.dfh_record_blocked_report_entry()`
	# @used-by :meth:`AnswerPreparer.__authorize_and_sync_workflow()`
	# @used-by :meth:`AnswerPreparer.__post_finalize_workflow()`
	def _record_journal_entry(self) -> None:
		record_fn = self.__ops.get('record') or (lambda r_p, n, t, resp, d, **kw: dfh_record(r_p, n, t, resp, d, ops=self.__ops, **kw))
		try:
			self.value['prepared'], self.admission_check = record_fn(self.root, self.native, self.turn, self.response, self.value['journal'], existing=None if self.allow_reprepare else dfh_recorded(self.value), allow_reprepare=self.allow_reprepare)
		except (OSError, ValueError) as exc:
			self._fail_gate('journal_admission', str(exc), admission_failed=True, cause=exc)
		self.value.pop('admission_failure', None)
	# @used-by :func:`Df.Harness.lib.completion_commands.dfh_prepare_once()`
	# @used-by :meth:`test_turn_completion.AnswerPreparationRunnerTests.test_gate_id_auto_clearing_and_resolve_journal_dir()`
	def run(self) -> dict[str, Any]:
		delivered = self.__verify_delivered_fast_path()
		if None is not delivered:
			r = delivered
		else:
			self.__check_turn_hygiene()
			self.__audit_workflow_scope()
			self.__check_source_grounding()
			self.__authorize_and_sync_workflow()
			try:
				dfh_unchanged(self.root, self.native, self.turn, ops=self.__ops)
			except (OSError, ValueError, sqlite3.Error) as exc:
				self._fail_gate('turn_unchanged', str(exc), status='preparation_unverified', cause=exc)
			r = self.__finalize_prepared_state()
		return r