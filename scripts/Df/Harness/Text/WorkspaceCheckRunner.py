# 2026-11-27 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
import difflib
from Df.Harness.Text.ClaimMapValidator import ClaimMapValidator
from Df.Harness.Text.CommandReplayer import CommandReplayer
from Df.Harness.Text.SourceCheckValidator import SourceCheckValidator
from Df.Harness.lib.research import dfh_inside, dfh_json_data
from Df.Harness.lib.text_claims import dfh_claim_subset, dfh_registry_path, dfh_text_digest
from Df.Harness.lib.text_core import dfh_changed_command_lines
from Df.Harness.lib.text_sections import dfh_lint_document
from Df.Harness.lib.text_workflow import dfh_hash_or_none, dfh_immutable_text, dfh_read_json_sig, dfh_target_bytes
from agent_tools.storage import read_addressed_json
# 2026-11-27 "Move repository and grounding subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/382
class WorkspaceCheckRunner:
	# @used-by :meth:`Df.Harness.Text.Workspace.Workspace.check()`
	# @used-by :meth:`test_df_harness_s11_wave2c_text_flow.DfHarnessS11Wave2CTextFlowTests.test_workspace_integrity_and_review_classes()`
	def __init__(self, workspace, ident: str, candidate: str, manifest=None, *, run_replay: bool=False, replay_record=None, warning_dispositions=None, applied: bool=False, return_op: bool=False) -> None:
		self.__ws = workspace
		self.__ident = ident
		self.__candidate = candidate
		self.__manifest = manifest
		self.__run_replay = run_replay
		self.__replay_record = replay_record
		self.__warnings = warning_dispositions or {}
		self.__applied = applied
		self.__return_op = return_op
	# @used-by :meth:`WorkspaceCheckRunner.run()`
	def __check_replay(self, op: dict, candidate_sha: str, changed: list[int]) -> tuple[str | None, list[dict]]:
		issues, replay_data, replay_record = ([], [], self.__replay_record)
		if changed:
			if not self.__run_replay and (not replay_record):
				issues.append({'code': 'text.replay_missing', 'message': 'New/changed commands require an explicit replay of exactly these blocks', 'lines': changed})
			elif not self.__run_replay:
				_, stored = read_addressed_json(dfh_inside(self.__ws.root, replay_record), suffix='-replay.json', error_msg='Replay receipt does not cover the exact changed command blocks')
				if stored.get('operation') != self.__ident or stored.get('candidate_sha256') != candidate_sha or (stored.get('lines') != changed):
					raise ValueError('Replay receipt does not cover the exact changed command blocks')
				replay_data = stored['results']
			else:
				replay_data = CommandReplayer(self.__candidate, only=changed, contracts=(self.__manifest or {}).get('commands'), shell=op.get('shell')).replay()
				payload = dfh_json_data({'schema_version': 1, 'operation': self.__ident, 'candidate_sha256': candidate_sha, 'lines': changed, 'results': replay_data})
				replay_record = dfh_immutable_text(self.__ws.folder / 'operations' / self.__ident / (dfh_text_digest(payload) + '-replay.json'), payload).relative_to(self.__ws.root).as_posix()
			if replay_data and (len(replay_data) != len(changed) or any(('match' != item.get('status') for item in replay_data))):
				issues.append({'code': 'text.replay', 'message': 'Changed command coverage or execution failed', 'results': replay_data})
		return (replay_record, issues)
	# @used-by :meth:`WorkspaceCheckRunner.run()`
	def __collect_target_and_lint_issues(self, op: dict, target, candidate_sha: str, issues: list[dict]) -> None:
		expected_target = candidate_sha if self.__applied else op['base_sha256']
		if dfh_hash_or_none(dfh_target_bytes(target)) != expected_target:
			issues.append({'code': 'text.conflict', 'message': 'User target changed after capture; reconcile without overwriting it'})
		for name, sha in op['protected_versions'].items():
			if dfh_hash_or_none(dfh_target_bytes(dfh_inside(self.__ws.root, name))) != sha:
				issues.append({'code': 'text.protected', 'message': 'Protected file changed: ' + name})
		findings = dfh_lint_document(self.__candidate, op['kind'], target, op.get('profile'))
		issues.extend(({'code': f.rule, 'message': f.message, 'line': f.line} for f in findings if 'error' == f.severity))
		for finding in findings:
			basis = self.__warnings.get(f'{finding.rule}:{finding.line}')
			if 'warning' == finding.severity and (not isinstance(basis, str) or not basis.strip()):
				issues.append({'code': 'text.warning', 'message': 'Resolve or substantively explain warning: ' + finding.format()})
	# @used-by :meth:`WorkspaceCheckRunner.run()`
	def __persist_check(self, result: dict, candidate_bytes: bytes, candidate_sha: str) -> dict:
		if result['claim_versions']:
			registry = dfh_registry_path(self.__ws.root, (self.__manifest or {}).get('registry'))
			result['claim_snapshot'] = dfh_claim_subset(dfh_read_json_sig(registry), result['claim_versions'])
		op_folder = self.__ws.folder / 'operations' / self.__ident
		source = dfh_immutable_text(op_folder / (candidate_sha + '.md'), candidate_bytes)
		result['candidate'] = source.relative_to(self.__ws.root).as_posix()
		payload = dfh_json_data(result)
		receipt = dfh_immutable_text(op_folder / (dfh_text_digest(payload) + '-check.json'), payload)
		return {**result, 'check': receipt.relative_to(self.__ws.root).as_posix()}
	# @used-by :meth:`Df.Harness.Text.Workspace.Workspace.check()`
	# @used-by :meth:`test_df_harness_s11_wave2c_text_flow.DfHarnessS11Wave2CTextFlowTests.test_workspace_integrity_and_review_classes()`
	def run(self):
		op, base = self.__ws.operation(self.__ident)
		if not isinstance(self.__candidate, str):
			raise ValueError('Candidate must be exact UTF-8 text')
		base_text, candidate_bytes = (base.decode('utf-8'), self.__candidate.encode('utf-8'))
		candidate_sha, target = (dfh_text_digest(candidate_bytes), self.__ws.document(op['target']))
		scoped = self.__ws.scope_issues(op, base_text, self.__candidate)
		issues = list(scoped)
		self.__collect_target_and_lint_issues(op, target, candidate_sha, issues)
		mechanical = op['changes'] in ('links', 'renumber') and (not scoped)
		mapped = {'valid': True, 'issues': [], 'inputs': {}, 'claims': [], 'claim_versions': {}} if mechanical or 'inspect' == op['mode'] else ClaimMapValidator(self.__ws.root, self.__candidate, op['kind'], self.__manifest).validate()
		issues.extend(mapped['issues'])
		sources = SourceCheckValidator(self.__ws.root, self.__candidate, (self.__manifest or {}).get('source_checks', [])).validate()
		issues.extend(sources['issues'])
		replay_record, replay_issues = self.__check_replay(op, candidate_sha, dfh_changed_command_lines(self.__candidate, base_text))
		issues.extend(replay_issues)
		diff = ''.join(difflib.unified_diff(base_text.splitlines(True), self.__candidate.splitlines(True), fromfile='before/' + op['target'], tofile='after/' + op['target']))
		result = {'schema_version': 1, 'operation': self.__ident, 'root': str(self.__ws.root), 'target': op['target'], 'kind': op['kind'], 'base_sha256': op['base_sha256'], 'candidate_sha256': candidate_sha, 'valid': not issues, 'issues': issues, 'coverage': 'mechanical' if mechanical else 'semantic', 'inputs': {**mapped['inputs'], **sources['inputs']}, 'claims': mapped['claims'], 'claim_versions': mapped['claim_versions'], 'source_checks': sources['checks'], 'manifest': self.__manifest, 'replay_record': replay_record, 'warning_dispositions': self.__warnings, 'diff': diff}
		out = self.__persist_check(result, candidate_bytes, candidate_sha)
		return (out, op) if self.__return_op else out
