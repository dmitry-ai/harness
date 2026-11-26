# 2026-10-16 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from contextlib import contextmanager
from typing import override
import json
import os
from pathlib import Path
import sqlite3
import uuid
from unittest.mock import patch
from test_analysis_workflow import ProjectCase
from agent_tools import runtime, workflow as flow
from agent_tools.analysis import SECTIONS
from agent_tools.platforms import codex, antigravity
# 2026-10-16
# "Unify Antigravity and OpenAI Codex adapters with build-native projections, parent-driven model selection, and cross-system continuation":
# https://github.com/dmitry-ai/harness/issues/6
# 2026-10-31
# "Reorganize AI into universal harness repository, translate rules and documentation to English, format per P.md, and enforce issue-driven Git workflow":
# https://github.com/dmitry-ai/harness/issues/26
class CodexContinuationTests(ProjectCase):
	# 2026-10-18
	# "Enforce pre-registered experiment plans, claim-to-test alignment, native reviewer provenance, and executor metadata verification":
	# https://github.com/dmitry-ai/harness/issues/10
	# 2026-11-26
	# "Apply cross-reference annotations across Harness Python and JavaScript":
	# https://github.com/dmitry-ai/harness/issues/305
	# @used-by :mod:`unittest`
	# @see :meth:`test_analysis_workflow.ProjectCase.setUp()`
	@override
	def setUp(self):
		super().setUp()
		self.home = self.root / 'codex'
		self.home.mkdir()
		self.parent, self.child = (str(uuid.uuid4()), str(uuid.uuid4()))
		flow.resume(self.project, 'native fixture', '  Continue analysis.\nAfter outage.  ')
		self.package = self.review_package(self.parent)
		self.parent_rows = [self.meta(self.parent, self.project), self.context(self.project), self.message('  Continue analysis.\nAfter outage.  '), {'type': 'response_item', 'payload': {'type': 'function_call', 'name': 'collaboration.spawn_agent', 'call_id': 'spawn', 'arguments': json.dumps({'task_name': 'audit', 'message': 'Review ' + self.package['package']})}}]
		with patch.dict(os.environ, {'CODEX_THREAD_ID': self.child}):
			receipt = flow.review_input(self.project, self.package['package'])
		self.child_rows = [self.meta(self.child, self.project, parent=self.parent), self.context(self.project), {'type': 'response_item', 'payload': {'type': 'custom_tool_call', 'name': 'exec', 'call_id': 'read-package', 'input': 'review-input --package ' + self.package['package']}}, {'type': 'response_item', 'payload': {'type': 'custom_tool_call_output', 'call_id': 'read-package', 'output': json.dumps(receipt)}}, {'type': 'event_msg', 'payload': {'type': 'task_complete', 'last_agent_message': 'Reviewed'}}]
		self.write(self.parent, self.parent_rows)
		self.write(self.child, self.child_rows)
	# @used-by :meth:`CodexContinuationTests.setUp()`
	# @used-by :meth:`CodexContinuationTests.test_changed_cwd_before_and_after_user_input_does_not_import_foreign_turn()`
	# @used-by :meth:`CodexContinuationTests.test_injected_rules_and_environment_are_excluded_but_user_text_is_unchanged()`
	# @used-by :meth:`CodexContinuationTests.test_missing_native_root_keeps_legacy_job_id_but_foreign_root_does_not()`
	# @used-by :meth:`CodexContinuationTests.test_same_words_in_another_native_root_do_not_establish_ownership()`
	def meta(self, ident, cwd, parent=None):
		return {'type': 'session_meta', 'payload': {'id': ident, 'cwd': str(cwd), 'source': {'subagent': {'thread_spawn': {'parent_thread_id': parent, 'agent_path': '/root/audit'}}} if parent else 'vscode'}}
	# @used-by :meth:`CodexContinuationTests.setUp()`
	# @used-by :meth:`CodexContinuationTests.test_changed_cwd_before_and_after_user_input_does_not_import_foreign_turn()`
	# @used-by :meth:`CodexContinuationTests.test_explicit_other_job_stays_foreign_despite_repeated_cwd_and_blocks_reviews()`
	# @used-by :meth:`CodexContinuationTests.test_injected_rules_and_environment_are_excluded_but_user_text_is_unchanged()`
	# @used-by :meth:`CodexContinuationTests.test_same_words_in_another_native_root_do_not_establish_ownership()`
	def context(self, cwd, turn='turn-a'):
		return {'type': 'turn_context', 'payload': {'model': 'fixture-model', 'effort': 'max', 'cwd': str(cwd), 'turn_id': turn}}
	# @used-by :meth:`CodexContinuationTests.setUp()`
	# @used-by :meth:`CodexContinuationTests.test_changed_cwd_before_and_after_user_input_does_not_import_foreign_turn()`
	# @used-by :meth:`CodexContinuationTests.test_explicit_other_job_stays_foreign_despite_repeated_cwd_and_blocks_reviews()`
	# @used-by :meth:`CodexContinuationTests.test_injected_rules_and_environment_are_excluded_but_user_text_is_unchanged()`
	# @used-by :meth:`CodexContinuationTests.test_missing_native_root_keeps_legacy_job_id_but_foreign_root_does_not()`
	# @used-by :meth:`CodexContinuationTests.test_same_words_in_another_native_root_do_not_establish_ownership()`
	def message(self, text, kinds=('user.text',), turn='turn-a'):
		payload = {'type': 'message', 'role': 'user', 'content': [{'type': 'input_text', 'text': text}]}
		if None is not kinds:
			payload['internal_chat_message_metadata_passthrough'] = {'content_item_kinds': list(kinds), 'turn_id': turn}
		r = {'type': 'response_item', 'payload': payload}
		return r
	# @used-by :meth:`CodexContinuationTests.setUp()`
	# @used-by :meth:`CodexContinuationTests.test_changed_cwd_before_and_after_user_input_does_not_import_foreign_turn()`
	# @used-by :meth:`CodexContinuationTests.test_explicit_other_job_stays_foreign_despite_repeated_cwd_and_blocks_reviews()`
	# @used-by :meth:`CodexContinuationTests.test_injected_rules_and_environment_are_excluded_but_user_text_is_unchanged()`
	# @used-by :meth:`CodexContinuationTests.test_missing_native_root_keeps_legacy_job_id_but_foreign_root_does_not()`
	# @used-by :meth:`CodexContinuationTests.test_same_words_in_another_native_root_do_not_establish_ownership()`
	def write(self, ident, rows):
		path = self.home / 'sessions' / (ident + '.jsonl')
		path.parent.mkdir(exist_ok=True)
		path.write_text('\n'.join((json.dumps(item, ensure_ascii=False) for item in rows)) + '\n', encoding='utf-8')
		conn = sqlite3.connect(self.home / 'state_5.sqlite')
		conn.execute('CREATE TABLE IF NOT EXISTS threads(id TEXT PRIMARY KEY,rollout_path TEXT,agent_path TEXT)')
		conn.execute('INSERT OR REPLACE INTO threads VALUES(?,?,?)', (ident, str(path), '/root/audit' if ident == self.child else None))
		conn.commit()
		conn.close()
	# @used-by :meth:`CodexContinuationTests.test_explicit_other_job_stays_foreign_despite_repeated_cwd_and_blocks_reviews()`
	# @used-by :meth:`CodexContinuationTests.test_new_native_root_chat_imports_exact_continuation_and_allows_both_review_kinds()`
	@contextmanager
	def selected(self):
		config = runtime.platform_settings('codex')
		config['homes'] = {'C2': str(self.home)}
		with patch.object(codex, 'platform_settings', return_value=config), runtime.using('codex', 'C2'):
			yield
	# 2026-10-18
	# "Enforce pre-registered experiment plans, claim-to-test alignment, native reviewer provenance, and executor metadata verification":
	# https://github.com/dmitry-ai/harness/issues/10
	# @used-by :meth:`CodexContinuationTests.test_explicit_other_job_stays_foreign_despite_repeated_cwd_and_blocks_reviews()`
	# @used-by :meth:`CodexContinuationTests.test_new_native_root_chat_imports_exact_continuation_and_allows_both_review_kinds()`
	def report(self):
		return self.review_report(self.package, self_review=True)
	# @used-by :mod:`unittest`
	def test_new_native_root_chat_imports_exact_continuation_and_allows_both_review_kinds(self):
		requests = codex.native_requests(self.project, self.parent, backend=self.home)
		self.assertEqual([item['text'] for item in requests], ['  Continue analysis.\nAfter outage.  '])
		self.assertEqual(requests[0]['project_binding']['kind'], 'codex-session-cwd')
		with self.selected():
			flow.adopt_requests(self.project, self.parent)
			self.package = self.review_package(self.parent)
			self.put_project('ꘖ/KB/Evidence/Reviews/self.json', json.dumps(self.report()))
			flow.record_review(self.project, 'ꘖ/KB/Evidence/Reviews/self.json', parent_id=self.parent, reviewer_id=self.parent)
			proof = codex.native_review_proof(self.project, self.parent, self.child, backend=self.home, write=False)
		self.assertEqual(proof['status'], 'completed')
		self.assertFalse(flow.load(self.project)['reviews'][0]['independent'])
	# @used-by :mod:`unittest`
	def test_same_words_in_another_native_root_do_not_establish_ownership(self):
		rows = [self.meta(self.parent, self.root), self.context(self.root), self.message('  Continue analysis.\nAfter outage.  ')]
		self.write(self.parent, rows)
		with self.assertRaises(ValueError):
			codex.native_requests(self.project, self.parent, backend=self.home)
		with self.assertRaises(ValueError):
			codex.require_current_binding(self.project, self.parent, backend=self.home)
	# @used-by :mod:`unittest`
	def test_changed_cwd_before_and_after_user_input_does_not_import_foreign_turn(self):
		rows = [self.meta(self.parent, self.project), self.context(self.project), self.message('Own first'), self.message('Foreign before its native context', turn='turn-b'), self.context(self.root, 'turn-b'), self.message('Foreign after context', turn='turn-b'), self.context(self.project, 'turn-c'), self.message('Own again', turn='turn-c')]
		self.write(self.parent, rows)
		requests = codex.native_requests(self.project, self.parent, backend=self.home)
		self.assertEqual([item['text'] for item in requests], ['Own first', 'Own again'])
	# @used-by :mod:`unittest`
	def test_explicit_other_job_stays_foreign_despite_repeated_cwd_and_blocks_reviews(self):
		rows = [*self.parent_rows[:-1], self.message('/upwork-init https://www.upwork.com/jobs/~0299999'), self.context(self.project), self.message('Continue analysis.'), self.parent_rows[-1]]
		self.write(self.parent, rows)
		self.assertEqual(len(codex.native_requests(self.project, self.parent, backend=self.home)), 1)
		with self.assertRaises(ValueError):
			codex.native_review_proof(self.project, self.parent, self.child, backend=self.home, write=False)
		self.put_project('ꘖ/KB/Evidence/Reviews/self.json', json.dumps(self.report()))
		with self.selected(), self.assertRaises(ValueError):
			flow.record_review(self.project, 'ꘖ/KB/Evidence/Reviews/self.json', parent_id=self.parent, reviewer_id=self.parent)
	# @used-by :mod:`unittest`
	def test_injected_rules_and_environment_are_excluded_but_user_text_is_unchanged(self):
		rules = '# AGENTS.md instructions for ' + str(self.project) + '\n<INSTRUCTIONS>text</INSTRUCTIONS>'
		literal_environment = '<environment_context>quoted by user</environment_context>'
		rows = [self.meta(self.parent, self.project), self.context(self.project), self.message(rules, ('agents_md.instructions',)), self.message('<environment_context>injected</environment_context>', ('environments.environment_context',)), self.message(rules), self.message(literal_environment), self.message(rules, kinds=None)]
		self.write(self.parent, rows)
		requests = codex.native_requests(self.project, self.parent, backend=self.home)
		self.assertEqual([item['text'] for item in requests], [rules, literal_environment])
	# @used-by :mod:`unittest`
	def test_missing_native_root_keeps_legacy_job_id_but_foreign_root_does_not(self):
		rows = [self.meta(self.parent, self.root), self.message('Reference ' + flow.load(self.project)['job_id'])]
		self.write(self.parent, rows)
		with self.assertRaises(ValueError):
			codex.native_requests(self.project, self.parent, backend=self.home)
		del rows[0]['payload']['cwd']
		self.write(self.parent, rows)
		self.assertEqual(len(codex.native_requests(self.project, self.parent, backend=self.home)), 1)
		rows += [self.message('/upwork-init https://www.upwork.com/jobs/~0299999'), self.message('Reference again ' + flow.load(self.project)['job_id']), self.message('Continue analysis.')]
		self.write(self.parent, rows)
		self.assertEqual(len(codex.native_requests(self.project, self.parent, backend=self.home)), 1)
		with self.assertRaises(ValueError):
			codex.require_current_binding(self.project, self.parent, backend=self.home)
# @used-by :func:`test_native_review_binding_m4._chip_payload()`
# @used-by :meth:`AntigravityContinuationTests.inputs()`
# @used-by :meth:`AntigravityContinuationTests.test_quoted_and_non_leading_upwork_init_never_override_or_poison_and_support_cross_platform_commands()`
# @used-by :meth:`AntigravityContinuationTests.test_status_five_compacted_step_recovers_nested_protobuf_and_transcript_fallback()`
# @used-by :meth:`test_blocked_report_hygiene_and_doc5_m2.BlockedReportHygieneAndDoc5M2Tests.setUp()`
# @used-by :meth:`test_blocked_report_m2.BlockedReportM2Tests.setUp()`
# @used-by :meth:`test_review_target_claim_and_wait_m5.ReviewTargetClaimAndWaitM5Tests._setup_antigravity_reviewer()`
def wire(field, payload):
	# @used-by :func:`wire()`
	def encode(value):
		encoded = bytearray()
		while value >= 128:
			encoded.append(value & 127 | 128)
			value >>= 7
		encoded.append(value)
		r = bytes(encoded)
		return r
	return encode(field << 3 | 2) + encode(len(payload)) + payload
# 2026-10-16
# "Unify Antigravity and OpenAI Codex adapters with build-native projections, parent-driven model selection, and cross-system continuation":
# https://github.com/dmitry-ai/harness/issues/6
# 2026-10-31
# "Reorganize AI into universal harness repository, translate rules and documentation to English, format per P.md, and enforce issue-driven Git workflow":
# https://github.com/dmitry-ai/harness/issues/26
class AntigravityContinuationTests(ProjectCase):
	# 2026-10-18
	# "Enforce pre-registered experiment plans, claim-to-test alignment, native reviewer provenance, and executor metadata verification":
	# https://github.com/dmitry-ai/harness/issues/10
	# 2026-11-26
	# "Apply cross-reference annotations across Harness Python and JavaScript":
	# https://github.com/dmitry-ai/harness/issues/305
	# @used-by :mod:`unittest`
	# @see :meth:`test_analysis_workflow.ProjectCase.setUp()`
	@override
	def setUp(self):
		super().setUp()
		self.home = self.root / 'ag-home'
		self.backend = self.home / '.gemini/antigravity'
		(self.backend / 'conversations').mkdir(parents=True)
		self.parent, self.child = (str(uuid.uuid4()), str(uuid.uuid4()))
		self.package = self.review_package(self.parent)
		conn = sqlite3.connect(self.backend / 'conversation_summaries.db')
		conn.execute('CREATE TABLE conversation_summaries(conversation_id TEXT,parent_conversation_id TEXT,agent_name TEXT,workspace_uris TEXT)')
		conn.execute('INSERT INTO conversation_summaries VALUES(?,?,?,?)', (self.parent, '', '', json.dumps([self.project.as_uri()])))
		conn.execute('INSERT INTO conversation_summaries VALUES(?,?,?,?)', (self.child, self.parent, 'self', json.dumps([self.project.as_uri()])))
		conn.commit()
		conn.close()
		self.inputs(['  Continue analysis.\nAfter outage.  '])
	# @used-by :func:`agent_tools.cli_registry._exec_rules_audit()`
	# @used-by :func:`agent_tools.cli_registry._exec_shadow_replay()`
	# @used-by :func:`agent_tools.issues.comment_grounding.check_comment_preflight()`
	# @used-by :func:`agent_tools.issues.comment_grounding.validate_close_comment()`
	# @used-by :func:`agent_tools.issues.repo_commands.run_fetch()`
	# @used-by :func:`agent_tools.issues.scope_completeness._flag_unclosed_parent()`
	# @used-by :func:`agent_tools.issues.scope_completeness.find_open_deferred_children()`
	# @used-by :meth:`AntigravityContinuationTests.test_explicit_upwork_init_binds_generic_workspace_without_rewriting_user_text()`
	# @used-by :meth:`AntigravityContinuationTests.test_foreign_or_multiple_native_workspaces_cannot_claim_identical_request()`
	# @used-by :meth:`AntigravityContinuationTests.test_historical_explicit_project_root_receipt_reconciles_without_rewriting_saved_state()`
	# @used-by :meth:`AntigravityContinuationTests.test_legacy_job_mention_after_foreign_init_cannot_reactivate_old_project()`
	# @used-by :meth:`AntigravityContinuationTests.test_native_workspace_supports_self_review_and_empty_metadata_keeps_legacy_job_id()`
	# @used-by :meth:`AntigravityContinuationTests.test_quoted_and_non_leading_upwork_init_never_override_or_poison_and_support_cross_platform_commands()`
	# @used-by :meth:`AntigravityContinuationTests.test_text_root_labels_neither_break_valid_workspace_nor_claim_foreign_workspace()`
	def workspace(self, paths):
		conn = sqlite3.connect(self.backend / 'conversation_summaries.db')
		conn.execute('UPDATE conversation_summaries SET workspace_uris=? WHERE conversation_id=?', (json.dumps([path.as_uri() for path in paths]), self.parent))
		conn.commit()
		conn.close()
	# @used-by :meth:`AntigravityContinuationTests.setUp()`
	# @used-by :meth:`AntigravityContinuationTests.test_explicit_upwork_init_binds_generic_workspace_without_rewriting_user_text()`
	# @used-by :meth:`AntigravityContinuationTests.test_foreign_job_does_not_claim_parent_or_self_review_while_text_root_preserves_workspace()`
	# @used-by :meth:`AntigravityContinuationTests.test_historical_explicit_project_root_receipt_reconciles_without_rewriting_saved_state()`
	# @used-by :meth:`AntigravityContinuationTests.test_legacy_job_mention_after_foreign_init_cannot_reactivate_old_project()`
	# @used-by :meth:`AntigravityContinuationTests.test_native_workspace_supports_self_review_and_empty_metadata_keeps_legacy_job_id()`
	# @used-by :meth:`AntigravityContinuationTests.test_quoted_and_non_leading_upwork_init_never_override_or_poison_and_support_cross_platform_commands()`
	# @used-by :meth:`AntigravityContinuationTests.test_text_root_labels_neither_break_valid_workspace_nor_claim_foreign_workspace()`
	def inputs(self, texts):
		conn = sqlite3.connect(self.backend / 'conversations' / (self.parent + '.db'))
		conn.execute('CREATE TABLE IF NOT EXISTS steps(idx INTEGER,step_type INTEGER,status INTEGER,step_format INTEGER,step_payload BLOB,metadata BLOB)')
		conn.execute('DELETE FROM steps')
		for i, text in enumerate(texts):
			conn.execute('INSERT INTO steps VALUES(?,14,3,0,?,NULL)', (i, wire(19, wire(2, text.encode()))))
		conn.commit()
		conn.close()
		prompt = 'Review ' + self.package['package']
		parent = [{'step_index': i, 'type': 'USER_INPUT', 'content': text} for i, text in enumerate(texts)]
		parent.append({'step_index': len(texts), 'type': 'PLANNER_RESPONSE', 'tool_calls': [{'name': 'invoke_subagent', 'args': {'Subagents': [{'TypeName': 'self', 'Model': 'inherit', 'Prompt': prompt}]}}]})
		child = [{'step_index': 0, 'type': 'SYSTEM_MESSAGE', 'content': prompt}, {'step_index': 1, 'type': 'PLANNER_RESPONSE', 'content': 'Reviewed'}]
		for cid, rows in [(self.parent, parent), (self.child, child)]:
			log = self.backend / 'brain' / cid / '.system_generated/logs/transcript_full.jsonl'
			log.parent.mkdir(parents=True, exist_ok=True)
			log.write_text('\n'.join((json.dumps(row, ensure_ascii=False) for row in rows)) + '\n', encoding='utf-8')
		conn = sqlite3.connect(self.backend / 'conversations' / (self.child + '.db'))
		conn.execute('CREATE TABLE IF NOT EXISTS steps(idx INTEGER,step_type INTEGER,status INTEGER)')
		conn.execute('DELETE FROM steps')
		conn.execute('INSERT INTO steps VALUES(1,15,3)')
		conn.commit()
		conn.close()
	# @used-by :mod:`unittest`
	def test_exact_native_workspace_allows_plain_continuation_and_independent_review(self):
		requests = antigravity.native_requests(self.project, self.parent, backend=self.backend)
		self.assertEqual(requests[0]['text'], '  Continue analysis.\nAfter outage.  ')
		self.assertEqual(requests[0]['project_binding']['kind'], 'antigravity-workspace-uris')
		proof = antigravity.native_review_proof(self.project, self.parent, self.child, backend=self.backend, write=False)
		self.assertEqual(proof['status'], 'completed')
	# @used-by :mod:`unittest`
	def test_foreign_or_multiple_native_workspaces_cannot_claim_identical_request(self):
		for paths in ([self.root], [self.project, self.root]):
			self.workspace(paths)
			with self.assertRaises(ValueError):
				antigravity.native_requests(self.project, self.parent, backend=self.backend)
	# 2026-11-21
	# "Remove text-based explicit-project-root override from request binding":
	# https://github.com/dmitry-ai/harness/issues/112
	# @used-by :mod:`unittest`
	def test_explicit_upwork_init_binds_generic_workspace_without_rewriting_user_text(self):
		self.workspace([self.root])
		job_id = flow.load(self.project)['job_id']
		init_request = f'/upwork-init https://www.upwork.com/jobs/{job_id}\nContinue analysis.'
		self.inputs([init_request])
		saved = antigravity.native_requests(self.project, self.parent, backend=self.backend)
		self.assertEqual(saved[0]['text'], init_request)
		self.assertEqual(saved[0]['project_binding']['kind'], 'explicit-upwork-init')
		self.assertEqual(antigravity.native_review_proof(self.project, self.parent, self.child, backend=self.backend, write=False)['status'], 'completed')
		for text_override in (f'Continue analysis.\nProject root: `{self.project}`', f'Продолжай.\nКорень проекта: `{self.project}`'):
			self.inputs([text_override])
			with self.assertRaises(ValueError):
				antigravity.native_requests(self.project, self.parent, backend=self.backend)
	# 2026-11-21
	# "Remove text-based explicit-project-root override from request binding":
	# https://github.com/dmitry-ai/harness/issues/112
	# @used-by :mod:`unittest`
	def test_foreign_job_does_not_claim_parent_or_self_review_while_text_root_preserves_workspace(self):
		self.inputs(['Own request', '/upwork-init https://www.upwork.com/jobs/~0299999', 'Continue analysis.'])
		self.assertEqual(len(antigravity.native_requests(self.project, self.parent, backend=self.backend)), 1)
		with self.assertRaises(ValueError):
			antigravity.native_review_proof(self.project, self.parent, self.child, backend=self.backend, write=False)
		with self.assertRaises(ValueError):
			antigravity.require_current_binding(self.project, self.parent, backend=self.backend)
		self.inputs(['Own request', f'Continue analysis.\nProject root: `{self.root}`', 'Continue analysis.'])
		self.assertEqual(len(antigravity.native_requests(self.project, self.parent, backend=self.backend)), 3)
	# 2026-11-21
	# "Remove text-based explicit-project-root override from request binding":
	# https://github.com/dmitry-ai/harness/issues/112
	# @used-by :mod:`unittest`
	def test_native_workspace_supports_self_review_and_empty_metadata_keeps_legacy_job_id(self):
		self.workspace([self.project])
		self.inputs(['Continue analysis.'])
		report = self.review_report(self.package, self_review=True)
		self.put_project('ꘖ/KB/Evidence/Reviews/self.json', json.dumps(report))
		with patch.object(Path, 'home', return_value=self.home), runtime.using('antigravity'):
			flow.record_review(self.project, 'ꘖ/KB/Evidence/Reviews/self.json', parent_id=self.parent, reviewer_id=self.parent)
		self.workspace([])
		self.inputs([f'Continue analysis.\nProject root: `{self.project}`'])
		with self.assertRaises(ValueError):
			antigravity.native_requests(self.project, self.parent, backend=self.backend)
		self.inputs(['Exact native job ' + flow.load(self.project)['job_id']])
		self.assertEqual(len(antigravity.native_requests(self.project, self.parent, backend=self.backend)), 1)
	# @used-by :mod:`unittest`
	def test_legacy_job_mention_after_foreign_init_cannot_reactivate_old_project(self):
		self.workspace([])
		job_id = flow.load(self.project)['job_id']
		texts = ['Exact native job ' + job_id, '/upwork-init https://www.upwork.com/jobs/~0299999', 'Reference to the former job ' + job_id, 'Continue analysis.']
		self.inputs(texts)
		self.assertEqual([item['text'] for item in antigravity.native_requests(self.project, self.parent, backend=self.backend)], [texts[0]])
		with self.assertRaises(ValueError):
			antigravity.require_current_binding(self.project, self.parent, backend=self.backend)
	# 2026-10-31
	# "Canonicalize relocated Codex, Antigravity, and Harness project roots and support v2Migrated gitFolder project resources":
	# https://github.com/dmitry-ai/harness/issues/29
	# @used-by :mod:`unittest`
	def test_git_folder_project_id_fallback_and_relocated_root_canonicalization(self):
		from agent_tools.platforms.request_binding import _same_root
		self.assertTrue(_same_root('C:/work/research/provision/code/Software/OpenAI/Codex', 'C:/work/research/provision/code/AI/products/OpenAI/ChatGPT/Desktop/Addons'))
		self.assertTrue(_same_root('C:/work/research/provision/code/Software/Google/AI/Antigravity', 'C:/work/research/provision/code/AI/products/Google/Antigravity/Addons'))
		self.assertTrue(_same_root('C:/work/upwork/code/AI', 'C:/work/research/provision/code/AI/harness'))
		self.assertTrue(_same_root('C:/work/research/provision/code/AI/primary', 'C:/work/research/provision/code/AI/harness'))
		pid = 'cd16380f-c085-4876-a083-62bf924eda55'
		projects_dir = self.backend.parent / 'config/projects'
		projects_dir.mkdir(parents=True, exist_ok=True)
		(projects_dir / f'{pid}.json').write_text(json.dumps({'id': pid, 'name': 'Test', 'projectResources': {'resources': [{'gitFolder': {'folderUri': self.project.as_uri()}}]}}), encoding='utf-8')
		conn = sqlite3.connect(self.backend / 'conversation_summaries.db')
		try:
			conn.execute('ALTER TABLE conversation_summaries ADD COLUMN project_id TEXT')
			conn.execute('UPDATE conversation_summaries SET workspace_uris=?, project_id=? WHERE conversation_id=?', ('[]', pid, self.parent))
			conn.commit()
		finally:
			conn.close()
		requests = antigravity.native_requests(self.project, self.parent, backend=self.backend)
		self.assertEqual(requests[0]['project_binding']['kind'], 'antigravity-project-id')
		self.assertEqual(Path(requests[0]['project_binding']['root']).resolve(), self.project.resolve())
	# 2026-11-14
	# "Consolidate token/stage summarize, native_review_proof, read-only SQLite, file:// helpers, and ProjectCleanupScanner across trace_common.py, antigravity.py, codex.py, metrics.py, and cleanup.py":
	# https://github.com/dmitry-ai/harness/issues/75
	# @used-by :mod:`unittest`
	def test_status_five_compacted_step_recovers_nested_protobuf_and_transcript_fallback(self):
		db_file = self.backend / 'conversations' / (self.parent + '.db')
		conn = sqlite3.connect(db_file)
		try:
			conn.execute('DELETE FROM steps')
			conn.execute('INSERT INTO steps VALUES(0,14,5,0,?,NULL)', (wire(19, wire(3, wire(1, b'First compacted request'))),))
			conn.execute('INSERT INTO steps VALUES(2,14,5,0,?,NULL)', (b'',))
			conn.commit()
		finally:
			conn.close()
		log = self.backend / 'brain' / self.parent / '.system_generated/logs/transcript_full.jsonl'
		log.write_text('\n'.join((json.dumps(row, ensure_ascii=False) for row in [{'step_index': 0, 'type': 'USER_INPUT', 'content': '<USER_REQUEST>\nFirst compacted request\n</USER_REQUEST>'}, {'step_index': 2, 'type': 'USER_INPUT', 'content': '<USER_REQUEST>\nSecond compacted request\n</USER_REQUEST>\n<ADDITIONAL_METADATA>\nmeta\n</ADDITIONAL_METADATA>'}])) + '\n', encoding='utf-8')
		requests = antigravity.native_requests(self.project, self.parent, backend=self.backend)
		self.assertEqual([item['text'] for item in requests], ['First compacted request', 'Second compacted request'])
		conn = sqlite3.connect(db_file)
		try:
			conn.execute('INSERT INTO steps VALUES(4,14,3,0,?,NULL)', (b'',))
			conn.commit()
		finally:
			conn.close()
		with self.assertRaises(ValueError):
			antigravity.native_requests(self.project, self.parent, backend=self.backend)
	# 2026-11-21
	# "Restrict explicit project root binding to full root labels":
	# https://github.com/dmitry-ai/harness/issues/111
	# 2026-11-21
	# "Remove text-based explicit-project-root override from request binding":
	# https://github.com/dmitry-ai/harness/issues/112
	# @used-by :mod:`unittest`
	def test_text_root_labels_neither_break_valid_workspace_nor_claim_foreign_workspace(self):
		self.workspace([self.project])
		for text_mention in (
			f'# 1\nПроект: `{self.root}`\nПредложи решения.',
			f'Продолжай.\nКорень проекта: `{self.root}`',
			f'Continue.\nProject root: `{self.root}`',
			f'> Project root: `{self.root}`\n```text\nКорень проекта: {self.root}\n```',
		):
			self.inputs([text_mention])
			requests = antigravity.native_requests(self.project, self.parent, backend=self.backend)
			self.assertEqual([item['text'] for item in requests], [text_mention])
			self.assertEqual(requests[0]['project_binding']['kind'], 'antigravity-workspace-uris')
		self.workspace([self.root])
		for explicit_text in (f'Продолжай.\nКорень проекта: `{self.project}`', f'Continue.\nProject root: `{self.project}`'):
			self.inputs([explicit_text])
			with self.assertRaises(ValueError):
				antigravity.native_requests(self.project, self.parent, backend=self.backend)
	# 2026-11-21
	# "Remove text-based explicit-project-root override from request binding":
	# https://github.com/dmitry-ai/harness/issues/112
	# @used-by :mod:`unittest`
	def test_historical_explicit_project_root_receipt_reconciles_without_rewriting_saved_state(self):
		from agent_tools import completion
		self.workspace([self.project])
		prompt = f'Continue.\nProject root: `{self.project}`'
		self.inputs([prompt])
		res = completion.begin(self.project, self.parent, platform='antigravity', backend=self.backend)
		state_path = self.project / res['state']
		saved = json.loads(state_path.read_text(encoding='utf-8'))
		saved['requests'][0]['project_binding'] = {'kind': 'explicit-project-root', 'native_step': 0, 'root': str(self.project)}
		saved['status'] = 'prepared'
		saved['prepared'] = {'journal_steps': [2], 'response_sha256': '0' * 64, 'response_file': str(self.project / 'res.md'), 'group_file': str(self.project / 'grp.json')}
		raw_bytes = (json.dumps(saved, ensure_ascii=False, indent=2) + '\n').encode('utf-8')
		state_path.write_bytes(raw_bytes)
		native = completion._native(self.project, self.parent, platform='antigravity', backend=self.backend)
		turn = completion._active(native)
		_, loaded = completion._state(self.project, native, turn, recovered=True, allow_extended=False)
		self.assertEqual(loaded['requests'][0]['project_binding']['kind'], 'explicit-project-root')
		self.assertNotIn('uncovered_requests', loaded)
		saved['status'] = 'delivered'
		turn_done = {**turn, 'completed': True}
		delivered_bytes = (json.dumps(saved, ensure_ascii=False, indent=2) + '\n').encode('utf-8')
		state_path.write_bytes(delivered_bytes)
		_, loaded_del = completion._state(self.project, native, turn_done, recovered=True, allow_extended=True)
		completion._persist(state_path, loaded_del)
		self.assertEqual(state_path.read_bytes(), delivered_bytes)
		for bad_binding, bad_text in (
			({'kind': 'explicit-project-root', 'native_step': 0, 'root': str(self.root)}, prompt),
			({'kind': 'codex-session-cwd', 'native_step': 0, 'root': str(self.project)}, prompt),
			({'kind': 'explicit-project-root', 'native_step': 0, 'root': str(self.project)}, 'Tampered prompt'),
		):
			tampered = json.loads(delivered_bytes.decode('utf-8'))
			tampered['requests'][0]['project_binding'] = bad_binding
			tampered['requests'][0]['text'] = bad_text
			state_path.write_bytes((json.dumps(tampered, ensure_ascii=False, indent=2) + '\n').encode('utf-8'))
			with self.assertRaisesRegex(ValueError, 'Native requests changed before the saved boundary'):
				completion._state(self.project, native, turn_done, recovered=True, allow_extended=True)
	# 2026-11-23
	# "Use native workspace priority and AST command parsing in request binding":
	# https://github.com/dmitry-ai/harness/issues/129
	# @used-by :mod:`unittest`
	def test_quoted_and_non_leading_upwork_init_never_override_or_poison_and_support_cross_platform_commands(self):
		from agent_tools import completion
		from agent_tools.platforms.request_binding import completion_project_id, scoped_inputs
		import check_pre_invocation
		job_id = flow.load(self.project)['job_id']
		other_url = 'https://www.upwork.com/jobs/~0299999999999999999'
		own_url = f'https://www.upwork.com/jobs/{job_id}'
		# @used-by :meth:`AntigravityContinuationTests.test_quoted_and_non_leading_upwork_init_never_override_or_poison_and_support_cross_platform_commands()`
		def _ag_chip_payload(prefix_text, cmd_name, suffix_text, flat_text):
			parts = [wire(2, flat_text.encode('utf-8'))]
			if prefix_text:
				parts.append(wire(3, wire(1, prefix_text.encode('utf-8'))))
			parts.append(wire(3, wire(2, wire(27, wire(1, wire(1, cmd_name.encode('utf-8')))))))
			if suffix_text:
				parts.append(wire(3, wire(1, suffix_text.encode('utf-8'))))
			return wire(19, b''.join(parts))
		# 1. Quoted / inline / blockquote / indented / mid-prose mentions never poison an Upwork project
		self.workspace([self.project])
		safe_quotes = [
			f'# 1\nReport:\n```\n/upwork-init  {other_url}\n```\nFix it.',
			f'```\n/upwork-init {other_url}\n```',
			f'```\n[upwork-init](slashCommand;upwork-init) {other_url}\n```',
			f'> /upwork-init {other_url}',
			f'    /upwork-init {other_url}',
			f'`/upwork-init {other_url}`',
			f'Mentioning /upwork-init {other_url} in prose.',
			f'```\n<command-name>/upwork-init</command-name>\n<command-args>{other_url}</command-args>\n```',
		]
		self.inputs([*safe_quotes, 'Follow-up turn stays owned.'])
		reqs = antigravity.native_requests(self.project, self.parent, backend=self.backend)
		self.assertEqual(len(reqs), len(safe_quotes) + 1)
		self.assertEqual(reqs[-1]['project_binding']['kind'], 'antigravity-workspace-uris')
		# 2. Antigravity protobuf slashCommand chip inside a fenced code block (973e033d case) does not poison Upwork or text-* project
		fenced_chip_text = f'# Report\n```\n/upwork-init  {other_url}\n```\nCheck this.'
		db_file = self.backend / 'conversations' / (self.parent + '.db')
		conn = sqlite3.connect(db_file)
		try:
			conn.execute('DELETE FROM steps')
			conn.execute('INSERT INTO steps VALUES(0,14,3,0,?,NULL)', (_ag_chip_payload('# Report\n```\n', 'upwork-init', f'  {other_url}\n```\nCheck this.', fenced_chip_text),))
			conn.execute('INSERT INTO steps VALUES(2,14,3,0,?,NULL)', (wire(19, wire(2, b'Second turn unaffected.')),))
			conn.commit()
		finally:
			conn.close()
		log = self.backend / 'brain' / self.parent / '.system_generated/logs/transcript_full.jsonl'
		log.write_text('\n'.join((json.dumps(r, ensure_ascii=False) for r in [{'step_index': 0, 'type': 'USER_INPUT', 'content': fenced_chip_text}, {'step_index': 2, 'type': 'USER_INPUT', 'content': 'Second turn unaffected.'}])) + '\n', encoding='utf-8')
		reqs_chip_fence = antigravity.native_requests(self.project, self.parent, backend=self.backend)
		self.assertEqual([r['text'] for r in reqs_chip_fence], [fenced_chip_text, 'Second turn unaffected.'])
		# 3. Non-Upwork text-* project (e.g. Harness / U / Init) keeps exact native workspace ownership even on real leading /upwork-init
		launcher = self.root / 'launcher_init'
		(launcher / '\ua66e/\u227b').mkdir(parents=True)
		(launcher / '\ua66e/\u227a').mkdir(parents=True)
		self.workspace([launcher])
		real_cmd = f'/upwork-init  {own_url}'
		conn = sqlite3.connect(db_file)
		try:
			conn.execute('DELETE FROM steps')
			conn.execute('INSERT INTO steps VALUES(0,14,3,0,?,NULL)', (_ag_chip_payload('', 'upwork-init', f'  {own_url}', real_cmd),))
			conn.commit()
		finally:
			conn.close()
		log.write_text(json.dumps({'step_index': 0, 'type': 'USER_INPUT', 'content': real_cmd}, ensure_ascii=False) + '\n', encoding='utf-8')
		launcher_native = antigravity.native_answers(launcher, self.parent, backend=self.backend)
		self.assertTrue(launcher_native['turns'][0]['owned'])
		self.assertEqual(launcher_native['turns'][0]['requests'][0]['project_binding']['kind'], 'antigravity-workspace-uris')
		# 4. Same leading Antigravity chip also binds the target Upwork project from the launcher workspace
		target_reqs = antigravity.native_requests(self.project, self.parent, backend=self.backend)
		self.assertEqual(len(target_reqs), 1)
		self.assertEqual(target_reqs[0]['text'], real_cmd)
		self.assertEqual(target_reqs[0]['project_binding']['kind'], 'explicit-upwork-init')
		# 5. Another leading native chip (/plan) does not bind as upwork-init
		plan_text = f'/plan\nCheck {own_url}'
		conn = sqlite3.connect(db_file)
		try:
			conn.execute('DELETE FROM steps')
			conn.execute('INSERT INTO steps VALUES(0,14,3,0,?,NULL)', (_ag_chip_payload('', 'plan', f'\nCheck {own_url}', plan_text),))
			conn.commit()
		finally:
			conn.close()
		with self.assertRaises(ValueError):
			antigravity.native_requests(self.project, self.parent, backend=self.backend)
		# 6. Cross-platform leading command formats: plain /upwork-init, Codex $upwork-init, Antigravity markdown link, Claude Code XML
		generic_ctx = [(-1, str(launcher), 'antigravity-workspace-uris')]
		for cmd_variant in (
			f'/upwork-init {own_url}',
			f'$upwork-init {own_url}',
			f'[upwork-init](slashCommand;upwork-init)  {own_url}',
			f'<command-message>upwork-init</command-message>\n<command-name>/upwork-init</command-name>\n<command-args>{own_url}</command-args>',
		):
			sel, act, bnd = scoped_inputs(self.project, job_id, [(0, cmd_variant)], generic_ctx)
			self.assertTrue(act, cmd_variant)
			self.assertEqual(len(sel), 1, cmd_variant)
			self.assertEqual(bnd['kind'], 'explicit-upwork-init', cmd_variant)
			sel_txt, act_txt, bnd_txt = scoped_inputs(launcher, completion_project_id(launcher), [(0, cmd_variant)], generic_ctx)
			self.assertTrue(act_txt, cmd_variant)
			self.assertEqual(bnd_txt['kind'], 'antigravity-workspace-uris', cmd_variant)
		# 7. Actionable diagnostic on real binding mismatch in completion._active and check_pre_invocation
		foreign = self.root / 'foreign_proj'
		(foreign / '\ua66e/\u227b').mkdir(parents=True)
		(foreign / '\ua66e/\u227a').mkdir(parents=True)
		self.workspace([launcher])
		self.inputs(['Normal request in launcher.'])
		with self.assertRaises(ValueError) as ctx_err:
			completion.begin(foreign, self.parent, platform='antigravity', backend=self.backend, dry_run=True)
		err_str = str(ctx_err.exception)
		self.assertIn('binding=antigravity-workspace-uris', err_str)
		self.assertIn('native_step=-1', err_str)
		self.assertIn(f'expected_root={foreign.resolve()}', err_str)
		self.assertIn(f'observed_root={launcher.resolve()}', err_str)
		conn_sum = sqlite3.connect(self.backend / 'conversation_summaries.db')
		try:
			conn_sum.execute('ALTER TABLE conversation_summaries ADD COLUMN status TEXT')
			conn_sum.execute('ALTER TABLE conversation_summaries ADD COLUMN not_fully_idle INTEGER')
			conn_sum.execute('ALTER TABLE conversation_summaries ADD COLUMN killed INTEGER')
			conn_sum.execute('ALTER TABLE conversation_summaries ADD COLUMN last_user_input_step_index INTEGER')
			conn_sum.execute("UPDATE conversation_summaries SET status='CASCADE_RUN_STATUS_RUNNING', not_fully_idle=1, killed=0, last_user_input_step_index=0")
			conn_sum.commit()
		finally:
			conn_sum.close()
		hook_out = check_pre_invocation.evaluate_pre_invocation_payload({'conversationId': self.parent, 'cwd': str(foreign), 'transcriptPath': str(log)}, backend_override=self.backend)
		self.assertEqual(hook_out.get('terminationBehavior'), 'terminate')
		hook_msg = hook_out['injectSteps'][0]['errorMessage']['userMessage']
		self.assertIn('binding=antigravity-workspace-uris', hook_msg)
		self.assertIn(f'observed_root={launcher.resolve()}', hook_msg)
