# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from pathlib import Path
from Df.Harness.Project.FinalizeDriftGuard import FinalizeDriftGuard
from Df.Harness.Review.ReviewAuthorizer import ReviewAuthorizer
# 2026-11-26 "Move analysis workflow classes into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/380
class FinalizeStageRunner:
	# @used-by :meth:`Df.Harness.Workflow.StageCompleter.StageCompleter.__run_approval_gate()`
	# @used-by :meth:`test_df_harness_s11_wave2a_workflow.DfHarnessS11Wave2aWorkflowTests._exercise_stage_completer_and_auditors()`
	def __init__(self, root, state: dict, out_hashes: dict, outputs: list, *, authorize_fn=None, drift_fn=None) -> None:
		self.__root = Path(root).resolve()
		self.__state = state
		self.__out_hashes = out_hashes
		self.__outputs = outputs
		self.__authorize_fn = authorize_fn
		self.__drift_fn = drift_fn
	# @used-by :meth:`FinalizeStageRunner.run()`
	def __load_latest_reply(self) -> tuple[Path, str]:
		from agent_tools.journal import journal_pair_dirs, resolve_journal_dir, step_file
		from agent_tools.journal_integrity import validate_finalize_journal
		from agent_tools.metadata import strip_leading_metadata_header
		prepared = self.__state['requests'][-1].get('response_prepared', {}) if self.__state['requests'] else {}
		journal = resolve_journal_dir(self.__root, prepared.get('journal'))
		ids = validate_finalize_journal(self.__root, journal, self.__state)
		req_dir, res_dir = journal_pair_dirs(journal)
		latest = max(ids)
		reply = step_file(res_dir, latest, directory=journal)
		reply_body = strip_leading_metadata_header(reply.read_bytes().decode('utf-8'))
		if self.__state['requests'] and step_file(req_dir, latest, directory=journal).read_bytes().decode('utf-8') != self.__state['requests'][-1]['text']:
			raise ValueError('Latest journal request differs from the recorded current continuation request')
		return (reply, reply_body)
	# @used-by :meth:`Df.Harness.Workflow.StageCompleter.StageCompleter.__run_approval_gate()`
	# @used-by :meth:`test_df_harness_s11_wave2a_workflow.DfHarnessS11Wave2aWorkflowTests._exercise_stage_completer_and_auditors()`
	def run(self) -> dict:
		from agent_tools.links import chat_reply_link_issues
		from agent_tools.text_workflow import gate_paths
		FinalizeDriftGuard(self.__root, drift_fn=self.__drift_fn).require()
		gate_paths([self.__root / name for name in self.__outputs])
		reply, reply_body = self.__load_latest_reply()
		link_issues = chat_reply_link_issues(reply_body)
		if link_issues:
			raise ValueError('\n'.join(link_issues))
		if reply.relative_to(self.__root).as_posix() not in self.__out_hashes:
			raise ValueError('Declare the actual final reply file as a finalize output')
		r = ReviewAuthorizer(self.__root, self.__state, response=reply_body).authorize() if None is self.__authorize_fn else self.__authorize_fn(self.__root, self.__state, response=reply_body)
		if any((not request.get('response_prepared') for request in self.__state['requests'])) or not self.__state['requests'] or self.__state['requests'][-1]['response_prepared'].get('sha256') != r['response_sha256']:
			raise ValueError('Record the exact approved answer for current requests before finalizing')
		return r
