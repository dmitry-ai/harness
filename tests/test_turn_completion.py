# 2026-10-23 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Implement turn-completion contract, journal watcher, primary source admission, and Codex root AGENTS.md loader":
# https://github.com/dmitry-ai/harness/issues/16
# 2026-10-31 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Reorganize AI into universal harness repository, translate rules and documentation to English, format per P.md, and enforce issue-driven Git workflow":
# https://github.com/dmitry-ai/harness/issues/26
# 2026-10-31 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Enforce browser CDP DOM collection for JS/anti-bot pages, block search-snippet citation substitution, and extract universal harness.py CLI":
# https://github.com/dmitry-ai/harness/issues/27
# 2026-10-31 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Prevent rogue ꘖ directory outside harness meta repo, remove mirror logic, and recognize GIT_OPTIONAL_LOCKS in git gate":
# https://github.com/dmitry-ai/harness/issues/28
# 2026-10-31 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Prevent intermediate subagent status replies from polluting the journal, enforce TEXT-1 language gate in completion, and codify background task timeouts":
# https://github.com/dmitry-ai/harness/issues/30
# 2026-10-31 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Enforce EXEC-5 code/issue lifecycle gate in answer-prepare, URL-only commit messages, git_shim/hook commit interception, and worktree isolation":
# https://github.com/dmitry-ai/harness/issues/31
# 2026-11-01 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Eliminate local/external quote, metric, and identifier fabrication via local source grounding, Stop hook, fresh-read provenance, and A.A audit gates":
# https://github.com/dmitry-ai/harness/issues/34
# 2026-11-02 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Prevent journal-watch duplicate pairs on orphan steps, block direct journal writes bypassing answer-prepare, add recover-turn-violation, and harden watcher lifecycle":
# https://github.com/dmitry-ai/harness/issues/36
# 2026-11-02 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Replace special-case grounding/locale regexes with universal locale, relational claim arity, standalone-number, capability, and review gates":
# https://github.com/dmitry-ai/harness/issues/37
# 2026-11-02 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Eliminate quadratic HTML extraction bloat, enforce output and Git blob size invariants, and protect Cygwin Git hooks and credential locks":
# https://github.com/dmitry-ai/harness/issues/38
# 2026-11-02 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Enforce GitHub Issue URL commit requirement across all repositories for agents while exempting human user commits by invocation context":
# https://github.com/dmitry-ai/harness/issues/39
# 2026-11-02 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Eliminate flashing Git console windows on Windows via CREATE_NO_WINDOW and journal-watch lifecycle skip":
# https://github.com/dmitry-ai/harness/issues/40
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
import json
from pathlib import Path
import sqlite3
import sys
import tempfile
import time
import unittest
from unittest.mock import patch
import uuid
SCRIPTS = Path(__file__).resolve().parents[1] / 'scripts'
sys.path.insert(0, str(SCRIPTS))
from agent_tools import completion, journal, journal_watch, workflow, text_workflow
from agent_tools.causal_checks import unsupported_probability_claims
from agent_tools.platforms import codex, antigravity
def wire(field, payload):
	def varint(value):
		out = bytearray()
		while value >= 128:
			out.append(value & 127 | 128)
			value >>= 7
		out.append(value)
		r = bytes(out)
		return r
	return varint(field << 3 | 2) + varint(len(payload)) + payload
@contextmanager
def running_watcher(directory):
	launched = []
	captured_kwargs = []
	original = journal_watch.subprocess.Popen
	def launch(*args, **kwargs):
		captured_kwargs.append(kwargs)
		process = original(*args, **kwargs)
		launched.append(process)
		r = process
		return r
	with patch.object(journal_watch.subprocess, 'Popen', side_effect=launch):
		first = journal_watch.start(state_dir=directory)
	if captured_kwargs and 'creationflags' in captured_kwargs[0]:
		flags = captured_kwargs[0]['creationflags']
		assert flags & getattr(journal_watch.subprocess, 'CREATE_NO_WINDOW', 0)
		assert 0 == (flags & getattr(journal_watch.subprocess, 'DETACHED_PROCESS', 8))
	try:
		yield first
	finally:
		journal_watch.stop(state_dir=directory)
		for process in launched:
			process.wait(timeout=8)
class CompletionCase(unittest.TestCase):
	def setUp(self):
		self.temp = tempfile.TemporaryDirectory()
		self.addCleanup(self.temp.cleanup)
		self.root = Path(self.temp.name)
		self.project = self.root / 'ordinary analysis'
		self.project.mkdir()
		self.home = self.root / 'codex'
		(self.home / 'sessions').mkdir(parents=True)
		self.cid, self.turn = (str(uuid.uuid4()), str(uuid.uuid4()))
		self.path = self.home / 'sessions' / (self.cid + '.jsonl')
		self.rows = [self.meta(), *self.turn_rows(self.turn, 'Check .agents.  \nExact.')]
		self.write()
	def meta(self, *, root=None, child=False):
		return {'type': 'session_meta', 'payload': {'id': self.cid, 'cwd': str(root or self.project), 'source': {'subagent': {'thread_spawn': {'parent_thread_id': str(uuid.uuid4())}}} if child else 'vscode'}}
	def turn_rows(self, turn, text):
		return [{'type': 'event_msg', 'payload': {'type': 'task_started', 'turn_id': turn}}, {'type': 'turn_context', 'payload': {'turn_id': turn, 'cwd': str(self.project)}}, {'type': 'response_item', 'payload': {'type': 'message', 'role': 'user', 'internal_chat_message_metadata_passthrough': {'content_item_kinds': ['user.text'], 'turn_id': turn}, 'content': [{'type': 'input_text', 'text': text}]}}]
	def write(self):
		self.path.write_text(''.join((json.dumps(row, ensure_ascii=False) + '\n' for row in self.rows)), encoding='utf-8')
		connection = sqlite3.connect(self.home / 'state_5.sqlite')
		connection.execute('CREATE TABLE IF NOT EXISTS threads(id TEXT PRIMARY KEY,rollout_path TEXT,agent_path TEXT)')
		connection.execute('INSERT OR REPLACE INTO threads VALUES(?,?,NULL)', (self.cid, str(self.path)))
		connection.commit()
		connection.close()
	def finish(self, text, *, turn=None, completed=True, event_text=None):
		self.rows.append({'type': 'response_item', 'payload': {'type': 'message', 'role': 'assistant', 'status': 'completed', 'phase': 'final_answer', 'content': [{'type': 'output_text', 'text': text}]}})
		if completed:
			self.rows.append({'type': 'event_msg', 'payload': {'type': 'task_complete', 'turn_id': turn or self.turn, 'last_agent_message': text if None is event_text else event_text}})
		self.write()
	def begin(self, **kw):
		return completion.begin(self.project, self.cid, platform='codex', backend=self.home, watch=False, **kw)
	def prepare(self, text, **kw):
		return completion.prepare(self.project, text, self.cid, platform='codex', backend=self.home, watch=False, **kw)
	def sync(self, **kw):
		return completion.sync(self.project, self.cid, platform='codex', backend=self.home, **kw)
	def saved(self, sub, step=1):
		return (self.project / 'ꙮ/1 - Analysis' / sub / f'{step}.md').read_bytes()
	def test_ordinary_analysis_needs_no_article_or_fabricated_intake(self):
		result = self.begin()
		state = json.loads((self.project / result['state']).read_text(encoding='utf-8'))
		self.assertTrue(result['journal_required'])
		self.assertEqual(set(state['applicable_rules']), {'FILE-3', 'EXEC-5', 'DOC-2'})
		self.assertIn('--no-optional-locks', state['applicable_rules']['EXEC-5']['requirement'])
		self.assertEqual(state['git_optional_locks_env'], '0')
		self.assertTrue(state['exec5_check']['verified'])
		self.assertFalse(state['rule_comprehension_verified'])
		self.assertFalse((self.project / 'ꘖ/project.json').exists())
		self.assertFalse((self.project / 'ꘖ/data/text-project.json').exists())
	def test_unflagged_git_read_in_active_turn_blocks_answer_prepare(self):
		self.rows.append({'type': 'response_item', 'payload': {'type': 'custom_tool_call', 'call_id': 'bad-git', 'name': 'exec', 'input': "await Promise.allSettled([exec_command({ cmd: 'git status --short' })]);"}})
		self.write()
		with self.assertRaisesRegex(ValueError, 'EXEC-5 violation'):
			self.prepare('Blocked response')
		state = json.loads(next((self.project / 'ꘖ/data/turns').glob('*.json')).read_text(encoding='utf-8'))
		self.assertFalse(state['exec5_check']['verified'])
		self.assertFalse(state['readiness_check']['verified'])
		self.rows[-1]['payload']['input'] = "await Promise.allSettled([exec_command({ cmd: 'git --no-optional-locks status --short' })]);"
		self.write()
		result = self.prepare('Allowed response')
		self.assertTrue(result['ready'])
		self.assertTrue(result['exec5_check']['verified'])
	def test_unflagged_git_read_allows_env_assignment(self):
		from agent_tools.git_gate import unflagged_git_read_commands
		self.assertEqual(unflagged_git_read_commands('$env:GIT_OPTIONAL_LOCKS="0"; git status --short'), [])
		self.assertEqual(unflagged_git_read_commands('GIT_OPTIONAL_LOCKS=0 git status --short'), [])
		self.assertEqual(unflagged_git_read_commands('git --no-optional-locks status --short'), [])
		self.assertEqual(unflagged_git_read_commands('git status --short'), ['git status --short'])
	def test_codex_compaction_and_adhoc_http_fetch_gates(self):
		self.rows.append({'type': 'response_item', 'payload': {'type': 'custom_tool_call', 'call_id': 'c-http', 'name': 'exec', 'input': "exec_command({ cmd: 'curl.exe https://df.tips/t/2722' })"}})
		self.write()
		with self.assertRaisesRegex(ValueError, 'KB-3 / EXEC-1 violation'):
			self.prepare('Blocked HTTP fetch')
		self.rows[-1]['payload']['input'] = "exec_command({ cmd: 'echo safe' })"
		self.rows.append({'type': 'response_item', 'payload': {'type': 'custom_tool_call_output', 'call_id': 'c-http', 'output': '2722: Real title'}})
		self.rows.append({'type': 'event_msg', 'payload': {'type': 'context_compacted', 'turn_id': self.turn}})
		self.write()
		with self.assertRaisesRegex(ValueError, 'COMPACT-1 / KB-3 violation'):
			self.prepare('Blocked after compaction')
		recovered = completion.recover_checkpoint(self.project, self.cid, platform='codex', backend=self.home)
		self.assertTrue(recovered['compaction_check']['verified'])
		self.assertIn('2722: Real title', recovered['pre_checkpoint_records'][0]['outputs'][0])
		self.assertTrue(self.prepare('Allowed after recover-checkpoint')['ready'])
	def test_instruction_snapshot_inventories_sources_without_claiming_model_delivery(self):
		local = self.project / '.agents/rules/local.md'
		local.parent.mkdir(parents=True)
		local.write_bytes(b'Local instruction before the turn')
		result = self.begin()
		state = json.loads((self.project / result['state']).read_text(encoding='utf-8'))
		snapshot = state['instruction_snapshot']
		sources = {item['path']: item for item in snapshot['sources']}
		canonical = completion.PRIMARY / 'rules/05-verification-audit.md'
		self.assertEqual(sources[str(canonical.resolve())]['sha256'], completion._hash(canonical.read_bytes()))
		self.assertEqual(sources[str(local.resolve())]['sha256'], completion._hash(local.read_bytes()))
		self.assertFalse(snapshot['selection_verified'])
		self.assertFalse(snapshot['delivery_to_model_verified'])
		self.assertEqual(snapshot['capture_stage'], 'turn-begin')
		local.write_bytes(b'Changed after the first snapshot')
		self.begin()
		reread = json.loads((self.project / result['state']).read_text(encoding='utf-8'))
		self.assertEqual(reread['instruction_snapshot'], snapshot)
	def test_malformed_local_rule_registration_is_retained_as_an_inventory_error(self):
		manifest = self.project / '.agents/rules.json'
		manifest.parent.mkdir(parents=True)
		manifest.write_bytes(b'{"entries":')
		result = self.prepare('Analysis can still be recorded while investigating broken rules')
		state = json.loads((self.project / result['state']).read_text(encoding='utf-8'))
		snapshot = state['instruction_snapshot']
		self.assertTrue(snapshot['errors'])
		self.assertEqual(manifest.read_bytes(), b'{"entries":')
		self.assertEqual(next((item['sha256'] for item in snapshot['sources'] if item['path'] == str(manifest.resolve()))), completion._hash(manifest.read_bytes()))
	def test_snapshot_upgrade_is_not_misreported_as_capture_at_the_turn_start(self):
		result = self.begin()
		path = self.project / result['state']
		state = json.loads(path.read_text(encoding='utf-8'))
		del state['instruction_snapshot']
		path.write_text(json.dumps(state), encoding='utf-8')
		self.begin()
		self.assertEqual(json.loads(path.read_text(encoding='utf-8'))['instruction_snapshot']['capture_stage'], 'existing-state-upgrade')
	def test_prepare_readback_is_exact_but_delivery_requires_native_completion(self):
		text = 'Answer with Unicode ꘖ.\r\n  Spaces preserved.  '
		result = self.prepare(text)
		self.assertTrue(result['ready'])
		self.assertFalse(result['delivery_verified'])
		self.assertEqual(self.saved('res'), text.encode())
		self.assertEqual(self.sync()['turns'], [])
		self.finish(text)
		delivered = self.sync()['turns'][0]
		self.assertTrue(delivered['delivery_verified'])
		self.assertFalse(delivered['recovered_after_delivery'])
		self.assertEqual(self.saved('req'), 'Check .agents.  \nExact.'.encode())
	def test_explicit_external_journal_binding_is_preserved_during_native_sync(self):
		selected = self.root / 'user selected journal'
		result = self.prepare('Selected journal response', journal_directory=selected)
		self.assertEqual(Path(result['response_file']), selected / 'res/1.md')
		with self.assertRaisesRegex(ValueError, 'different journal'):
			self.prepare('Selected journal response', journal_directory=self.root / 'another journal')
		self.finish('Selected journal response')
		self.assertTrue(self.sync()['turns'][0]['delivery_verified'])
		self.assertFalse((self.project / 'ꙮ').exists())
	def test_external_journal_cannot_bypass_the_current_client_document_gate(self):
		target = self.project / 'proposal.md'
		target.write_text('1. Current client text.', encoding='utf-8')
		request = codex.native_answers(self.project, self.cid, backend=self.home)['turns'][0]['requests'][0]['text']
		text_workflow.begin(self.project, {'kind': 'proposal', 'mode': 'edit', 'changes': 'prose', 'target': 'proposal.md', 'goal': 'Edit the requested document', 'requests': [request]})
		target.write_text('1. Changed directly without an apply receipt.', encoding='utf-8')
		selected = self.root / 'external journal'
		with self.assertRaisesRegex(ValueError, 'changed without a current apply receipt'):
			self.prepare('Claiming completion without the document check', journal_directory=selected)
		self.assertFalse((selected / 'res').exists())
	def test_watcher_respects_the_custom_journal_of_an_unprepared_turn(self):
		selected = self.root / 'selected journal'
		self.begin(journal_directory=selected)
		self.finish('Actual final without preparation')
		native = codex.native_answers(self.project, self.cid, backend=self.home)
		directory = self.root / 'watcher custom journal'
		journal_watch.register(self.project, native, 0, state_dir=directory, journal_directory=selected)
		self.assertTrue(journal_watch.once(state_dir=directory)['valid'])
		self.assertEqual((selected / 'res/1.md').read_bytes(), b'Actual final without preparation')
		self.assertFalse((self.project / 'ꙮ').exists())
	def test_native_sync_recovers_a_completely_skipped_prepare_once(self):
		self.finish('Already delivered answer.\n')
		first = self.sync()['turns'][0]
		self.assertTrue(first['recovered_after_delivery'])
		again = self.sync()['turns'][0]
		self.assertTrue(again['recovered_after_delivery'])
		self.assertEqual(again['journal_steps'], first['journal_steps'])
		self.assertEqual(len(list((self.project / 'ꙮ/1 - Analysis/res').glob('*.md'))), 1)
	def test_concurrent_native_reconciliation_creates_one_pair(self):
		self.finish('One delivered response')
		with ThreadPoolExecutor(max_workers=3) as pool:
			results = list(pool.map(lambda _: self.sync(), range(3)))
		self.assertEqual([r['turns'][0]['journal_steps'] for r in results], [[1], [1], [1]])
		self.assertEqual(len(list((self.project / 'ꙮ/1 - Analysis/res').glob('*.md'))), 1)
	def test_switching_active_native_turn_during_prepare_records_no_answer(self):
		second = str(uuid.uuid4())
		real = completion.begin
		def switch(*args, **kwargs):
			result = real(*args, **kwargs)
			self.rows += self.turn_rows(second, 'New human request')
			self.write()
			r = result
			return r
		with patch.object(completion, 'begin', side_effect=switch):
			with self.assertRaisesRegex(ValueError, 'changed during preparation'):
				self.prepare('Stale response')
		self.assertFalse((self.project / 'ꙮ').exists())
	def test_steering_during_begin_invalidates_the_prepared_request_snapshot(self):
		original = completion.begin
		def steer(*args, **kwargs):
			result = original(*args, **kwargs)
			self.rows.append(self.turn_rows(self.turn, 'New constraint during preparation')[2])
			self.write()
			r = result
			return r
		with patch.object(completion, 'begin', side_effect=steer):
			with self.assertRaisesRegex(ValueError, 'changed during preparation'):
				self.prepare('Response to the earlier request')
		self.assertFalse((self.project / 'ꙮ').exists())
	def test_waiting_for_writer_lock_does_not_allow_a_stale_ready_result(self):
		original = completion.locked
		calls = 0
		@contextmanager
		def switch_after_wait(*args, **kwargs):
			nonlocal calls
			calls += 1
			with original(*args, **kwargs):
				if 2 == calls:
					self.rows += self.turn_rows(str(uuid.uuid4()), 'A different active turn')
					self.write()
				yield
		with patch.object(completion, 'locked', side_effect=switch_after_wait):
			with self.assertRaisesRegex(ValueError, 'changed during preparation'):
				self.prepare('Stale response after waiting')
		self.assertFalse((self.project / 'ꙮ').exists())
	def test_steering_during_journal_write_preserves_history_without_granting_readiness(self):
		original = completion._record
		def steer(*args, **kwargs):
			result = original(*args, **kwargs)
			self.rows.append(self.turn_rows(self.turn, 'Late additional condition')[2])
			self.write()
			r = result
			return r
		with patch.object(completion, '_record', side_effect=steer):
			with self.assertRaisesRegex(ValueError, 'changed during preparation'):
				self.prepare('Already recorded original response')
		self.assertEqual(self.saved('res'), b'Already recorded original response')
		state = json.loads(next((self.project / 'ꘖ/data/turns').glob('*.json')).read_text(encoding='utf-8'))
		self.assertEqual(state['status'], 'preparation_unverified')
		self.assertFalse(state['readiness_check']['verified'])
		self.finish('Response accounting for the late condition')
		result = self.sync()
		self.assertFalse(result['valid'])
		self.assertEqual(self.saved('res'), b'Already recorded original response')
		self.assertEqual((self.project / result['turns'][0]['evidence']).read_bytes(), b'Response accounting for the late condition')
	def tracked(self):
		native = codex.native_answers(self.project, self.cid, backend=self.home)
		request = native['turns'][0]['requests'][0]
		marker = self.project / 'ꘖ/project.json'
		marker.parent.mkdir(parents=True, exist_ok=True)
		marker.write_text(json.dumps({'job_id': '~1234567890123456789'}), encoding='utf-8')
		state = workflow.load(self.project)
		state['requests'] = [request]
		path = workflow.state_path(self.project)
		path.parent.mkdir(parents=True, exist_ok=True)
		path.write_text(json.dumps(state), encoding='utf-8')
		r = path
		return r
	def test_tracked_initial_analysis_still_requires_answer_bound_approval(self):
		self.tracked()
		with patch('agent_tools.review.authorize', side_effect=ValueError('Need approved A.A review')):
			with self.assertRaisesRegex(ValueError, 'approved A.A'):
				self.prepare('Unapproved response')
		self.assertFalse((self.project / 'ꙮ').exists())
	def test_tracked_prepare_preserves_finalizer_receipt_without_duplicate_pair(self):
		path = self.tracked()
		def update(root, event, change):
			state = workflow.load(root)
			change(state)
			path.write_text(json.dumps(state), encoding='utf-8')
			r = {'workflow': str(path)}
			return r
		approval = {'package': 'test-review-package', 'response_sha256': completion._hash(b'Approved')}
		with patch('agent_tools.review.authorize', return_value=approval), patch.object(workflow, 'update', side_effect=update):
			result = self.prepare('Approved')
			self.assertEqual(self.prepare('Approved')['journal_steps'], [1])
		saved = workflow.load(self.project)['requests'][0]['response_prepared']
		self.assertEqual(saved['sha256'], result['response_sha256'])
		self.assertEqual(saved['review_approval'], approval)
		self.finish('Approved')
		self.assertEqual(self.sync()['turns'][0]['journal_steps'], [1])
	def test_begun_but_unprepared_turn_is_reported_as_late_recovery(self):
		self.begin()
		self.finish('Answer.')
		self.assertTrue(self.sync()['turns'][0]['recovered_after_delivery'])
	def test_changed_delivery_preserves_prepared_journal_and_native_conflict_bytes(self):
		self.prepare('Prepared answer.')
		self.finish('Different actually delivered answer.')
		result = self.sync()
		self.assertFalse(result['valid'])
		self.assertEqual(self.saved('res'), 'Prepared answer.'.encode())
		conflict = self.project / result['turns'][0]['evidence']
		self.assertEqual(conflict.read_bytes(), 'Different actually delivered answer.'.encode())
		self.assertEqual(self.sync()['turns'][0]['status'], 'conflict')
	def test_changed_prepared_bytes_and_new_uncovered_request_do_not_overwrite(self):
		self.prepare('Original')
		with self.assertRaisesRegex(ValueError, 'immutable'):
			self.prepare('Changed')
		self.rows.append(self.turn_rows(self.turn, 'One more condition.')[2])
		self.write()
		with self.assertRaisesRegex(ValueError, 'new native request'):
			self.prepare('Original')
		self.assertEqual(self.saved('res'), b'Original')
		self.finish('Response including the new condition')
		result = self.sync()
		self.assertFalse(result['valid'])
		state = json.loads(next((self.project / 'ꘖ/data/turns').glob('*.json')).read_text(encoding='utf-8'))
		self.assertEqual(state['uncovered_requests'][0]['text'], 'One more condition.')
		self.assertEqual((self.project / result['turns'][0]['evidence']).read_bytes(), b'Response including the new condition')
	def test_same_words_in_two_native_turns_are_two_exchanges(self):
		self.finish('Same')
		second = str(uuid.uuid4())
		self.rows += self.turn_rows(second, 'Check .agents.  \nExact.')
		self.finish('Same', turn=second)
		result = self.sync()
		self.assertEqual([x['journal_steps'] for x in result['turns']], [[1], [2]])
	def test_matching_native_request_ids_reuse_an_existing_record_answer_group(self):
		native = codex.native_answers(self.project, self.cid, backend=self.home)
		request = native['turns'][0]['requests'][0]
		journal.record_answer(self.project / 'ꙮ/1 - Analysis', [request['text']], 'Exact', 'older-record-api', [request['id']])
		self.finish('Exact')
		self.assertEqual(self.sync()['turns'][0]['journal_steps'], [1])
		self.assertEqual(len(list((self.project / 'ꙮ/1 - Analysis/res').glob('*.md'))), 1)
	def test_old_exact_native_turn_receipts_are_not_duplicated(self):
		journal.record_answer(self.project / 'ꙮ/1 - Analysis', ['Check .agents.  \nExact.'], 'Exact', self.turn)
		self.finish('Exact')
		result = self.sync()['turns'][0]
		self.assertEqual(result['journal_steps'], [1])
		self.assertFalse(result['recovered_after_delivery'])
		self.assertFalse(result['preparation_verified'])
		self.assertEqual(result['completion_provenance'], 'existing_journal')
	def test_partial_final_aborted_turn_and_commentary_are_not_delivery(self):
		self.rows.append({'type': 'response_item', 'payload': {'type': 'message', 'role': 'assistant', 'phase': 'commentary', 'content': [{'type': 'output_text', 'text': 'Working'}]}})
		self.finish('Incomplete', completed=False)
		self.assertEqual(self.sync()['turns'], [])
		self.rows.append({'type': 'event_msg', 'payload': {'type': 'turn_aborted', 'turn_id': self.turn}})
		self.write()
		self.assertEqual(self.sync()['turns'], [])
		self.assertFalse((self.project / 'ꙮ').exists())
	def test_partial_jsonl_and_disagreeing_native_final_are_not_verified(self):
		with self.path.open('ab') as stream:
			stream.write(b'{"partial":')
		with self.assertRaisesRegex(ValueError, 'partial record'):
			self.sync()
		self.finish('Actual', event_text='Different')
		with self.assertRaisesRegex(ValueError, 'disagree'):
			self.sync()
	def test_child_foreign_root_and_foreign_profile_never_create_user_pairs(self):
		self.rows[0] = self.meta(child=True)
		self.write()
		self.assertFalse(self.begin()['journal_required'])
		with self.assertRaisesRegex(ValueError, 'child'):
			self.prepare('No')
		self.assertFalse((self.project / 'ꙮ').exists())
		self.rows = [self.meta(root=self.root), *self.turn_rows(self.turn, 'Foreign')]
		self.rows[2]['payload']['cwd'] = str(self.root)
		self.write()
		with self.assertRaisesRegex(ValueError, 'belonging entirely'):
			self.begin()
		with self.assertRaisesRegex(ValueError, 'owned'):
			self.sync()
		other = self.root / 'other-profile'
		other.mkdir()
		with self.assertRaisesRegex(ValueError, 'missing or ambiguous'):
			completion.begin(self.project, self.cid, platform='codex', backend=other, watch=False)
	def test_injected_user_context_is_excluded_and_steered_requests_are_both_saved(self):
		injected = self.turn_rows(self.turn, '<environment_context>injected</environment_context>')[2]
		injected['payload']['internal_chat_message_metadata_passthrough']['content_item_kinds'] = ['environments.environment_context']
		self.rows += [injected, self.turn_rows(self.turn, 'Clarification.')[2]]
		self.finish('One answer to two requests.')
		result = self.sync()['turns'][0]
		self.assertEqual(result['journal_steps'], [1, 2])
		self.assertEqual(self.saved('req', 2), 'Clarification.'.encode())
	def test_watcher_independently_recovers_without_another_model_tool_call(self):
		native = codex.native_answers(self.project, self.cid, backend=self.home)
		directory = self.root / 'watch state'
		journal_watch.register(self.project, native, 0, state_dir=directory)
		journal_watch.once(state_dir=directory)
		self.finish('Native final')
		result = journal_watch.once(state_dir=directory)
		self.assertTrue(result['results'][0]['turns'][0]['delivery_verified'])
		self.assertEqual(self.saved('res'), b'Native final')
		self.assertEqual(journal_watch.once(state_dir=directory)['bindings_checked'], 0)
	def test_corrupt_binding_does_not_disable_other_conversations_or_rewrite_evidence(self):
		native = codex.native_answers(self.project, self.cid, backend=self.home)
		directory = self.root / 'watch state'
		journal_watch.register(self.project, native, 0, state_dir=directory)
		broken = directory / 'bindings/000-broken.json'
		broken.write_bytes(b'{"partial":')
		self.finish('Recovered despite another corrupt binding')
		result = journal_watch.once(state_dir=directory)
		self.assertFalse(result['valid'])
		self.assertTrue(any((r.get('turns') for r in result['results'])))
		self.assertEqual(broken.read_bytes(), b'{"partial":')
	def test_structurally_invalid_bindings_are_isolated_without_rewriting_them(self):
		native = codex.native_answers(self.project, self.cid, backend=self.home)
		directory = self.root / 'watch state'
		binding = Path(journal_watch.register(self.project, native, 0, state_dir=directory)['binding'])
		template = json.loads(binding.read_text(encoding='utf-8'))
		invalid = [{'platform': ['codex']}, {'platform': 'unknown'}, {'from_step': True}, {'conversation_id': 42}, {'conversation_id': 'not-a-uuid'}, {'project_root': 'relative-root'}, {'native_backend': {}}, {'journal_directory': []}, {'last_result': []}]
		evidence = {}
		for number, change in enumerate(invalid):
			path = directory / f'bindings/000-invalid-{number}.json'
			content = json.dumps({**template, **change}).encode()
			path.write_bytes(content)
			evidence[path] = content
		self.finish('Recovered despite structurally invalid bindings')
		result = journal_watch.once(state_dir=directory)
		self.assertFalse(result['valid'])
		self.assertEqual(sum((False is r.get('valid') for r in result['results'])), len(invalid))
		self.assertEqual(self.saved('res'), b'Recovered despite structurally invalid bindings')
		for path, content in evidence.items():
			self.assertEqual(path.read_bytes(), content)
	def registered_delivery(self):
		native = codex.native_answers(self.project, self.cid, backend=self.home)
		directory = self.root / 'watch state'
		binding = Path(journal_watch.register(self.project, native, 0, state_dir=directory)['binding'])
		self.finish('Original native final')
		self.assertTrue(journal_watch.once(state_dir=directory)['valid'])
		self.assertEqual(journal_watch.once(state_dir=directory)['bindings_checked'], 0)
		r = (directory, binding)
		return r
	def expire_binding(self, binding):
		value = json.loads(binding.read_text(encoding='utf-8'))
		value['last_checked_at'] = '2000-01-01T00:00:00+00:00'
		binding.write_text(json.dumps(value), encoding='utf-8')
	def test_periodic_integrity_check_detects_changed_journal_without_native_changes(self):
		directory, binding = self.registered_delivery()
		native_before = self.path.read_bytes()
		response = self.project / 'ꙮ/1 - Analysis/res/1.md'
		response.write_bytes(b'Externally changed response')
		self.expire_binding(binding)
		result = journal_watch.once(state_dir=directory)
		self.assertFalse(result['valid'])
		self.assertEqual(response.read_bytes(), b'Externally changed response')
		self.assertEqual(self.path.read_bytes(), native_before)
		evidence = self.project / result['results'][0]['turns'][0]['evidence']
		self.assertEqual(evidence.read_bytes(), b'Original native final')
		response.write_bytes(b'Original native final')
		self.expire_binding(binding)
		restored = journal_watch.once(state_dir=directory)
		self.assertTrue(restored['valid'])
		self.assertTrue(restored['results'][0]['turns'][0]['recovered_after_delivery'])
		self.assertEqual(restored['results'][0]['turns'][0]['completion_provenance'], 'recovered_native')
	def test_periodic_integrity_check_preserves_a_deleted_completed_journal_file(self):
		directory, binding = self.registered_delivery()
		request = self.project / 'ꙮ/1 - Analysis/req/1.md'
		request.unlink()
		self.expire_binding(binding)
		result = journal_watch.once(state_dir=directory)
		self.assertFalse(result['valid'])
		self.assertFalse(request.exists())
		self.assertEqual(self.saved('res'), b'Original native final')
		self.assertEqual(len(list((self.project / 'ꙮ/1 - Analysis/res').glob('*.md'))), 1)
	def test_missing_completed_group_receipt_cannot_create_a_duplicate_exchange(self):
		directory, binding = self.registered_delivery()
		groups = journal.state_dir(self.project / 'ꙮ/1 - Analysis') / 'answer-groups'
		next(groups.glob('*.json')).unlink()
		self.expire_binding(binding)
		result = journal_watch.once(state_dir=directory)
		self.assertFalse(result['valid'])
		self.assertEqual(self.saved('res'), b'Original native final')
		self.assertEqual(len(list((self.project / 'ꙮ/1 - Analysis/res').glob('*.md'))), 1)
	def test_transient_recheck_failure_is_reported_and_retried_without_native_changes(self):
		directory, binding = self.registered_delivery()
		self.expire_binding(binding)
		with patch.object(completion, 'sync', side_effect=OSError('Temporarily unavailable')):
			failed = journal_watch.once(state_dir=directory)
		self.assertFalse(failed['valid'])
		retried = journal_watch.once(state_dir=directory)
		self.assertTrue(retried['valid'])
		self.assertEqual(retried['bindings_checked'], 1)
	def test_temporary_permission_failure_reading_actual_journal_retries_next_pass(self):
		directory, binding = self.registered_delivery()
		self.expire_binding(binding)
		response = self.project / 'ꙮ/1 - Analysis/res/1.md'
		original = Path.read_bytes
		def unavailable(path):
			if path == response:
				raise PermissionError('Temporary denial of journal read')
			r = original(path)
			return r
		with patch.object(Path, 'read_bytes', unavailable):
			failed = journal_watch.once(state_dir=directory)
		self.assertFalse(failed['valid'])
		self.assertTrue(failed['results'][0]['retryable'])
		retried = journal_watch.once(state_dir=directory)
		self.assertTrue(retried['valid'])
		self.assertEqual(retried['bindings_checked'], 1)
		self.assertTrue(retried['results'][0]['turns'][0]['recovered_after_delivery'])
		self.assertEqual(response.read_bytes(), b'Original native final')
	def test_unchanged_native_cache_expires_at_the_configured_sixty_second_threshold(self):
		directory, binding = self.registered_delivery()
		value = json.loads(binding.read_text(encoding='utf-8'))
		value['last_checked_at'] = '2026-01-01T00:00:00+00:00'
		binding.write_text(json.dumps(value), encoding='utf-8')
		with patch.object(journal_watch, '_now', return_value='2026-01-01T00:00:59+00:00'):
			self.assertEqual(journal_watch.once(state_dir=directory)['bindings_checked'], 0)
		with patch.object(journal_watch, '_now', return_value='2026-01-01T00:01:00+00:00'):
			self.assertEqual(journal_watch.once(state_dir=directory)['bindings_checked'], 1)
	def test_binding_corrupted_during_sync_is_preserved_and_reported_without_crashing(self):
		native = codex.native_answers(self.project, self.cid, backend=self.home)
		directory = self.root / 'watch state'
		binding = Path(journal_watch.register(self.project, native, 0, state_dir=directory)['binding'])
		self.finish('Final before binding corruption')
		original = completion.sync
		def corrupt(*args, **kwargs):
			result = original(*args, **kwargs)
			binding.write_bytes(b'null')
			r = result
			return r
		with patch.object(completion, 'sync', side_effect=corrupt):
			result = journal_watch.once(state_dir=directory)
		self.assertFalse(result['valid'])
		self.assertEqual(binding.read_bytes(), b'null')
		self.assertEqual(self.saved('res'), b'Final before binding corruption')
	def test_earlier_registration_boundary_is_rechecked_without_native_file_change(self):
		self.finish('Earlier response')
		second = str(uuid.uuid4())
		self.rows += self.turn_rows(second, 'Later request')
		self.finish('Later response', turn=second)
		native = codex.native_answers(self.project, self.cid, backend=self.home)
		directory = self.root / 'watch state'
		journal_watch.register(self.project, native, native['turns'][1]['start_step'], state_dir=directory)
		journal_watch.once(state_dir=directory)
		self.assertEqual(self.saved('res'), b'Later response')
		journal_watch.register(self.project, native, 0, state_dir=directory)
		self.assertEqual(len(journal_watch.once(state_dir=directory)['results'][0]['turns']), 2)
		self.assertEqual(self.saved('res', 2), b'Earlier response')
	def test_user_exception_removes_only_its_own_registration(self):
		native = codex.native_answers(self.project, self.cid, backend=self.home)
		directory = self.root / 'watch state'
		own = journal_watch.register(self.project, native, 0, state_dir=directory)['binding']
		other = {**native, 'conversation_id': str(uuid.uuid4())}
		other_binding = journal_watch.register(self.project, other, 0, state_dir=directory)['binding']
		self.assertTrue(journal_watch.unregister(self.project, native, state_dir=directory)['binding_removed'])
		self.assertFalse(Path(own).exists())
		self.assertTrue(Path(other_binding).exists())
	def test_background_process_records_native_completion_after_the_caller_returns(self):
		native = codex.native_answers(self.project, self.cid, backend=self.home)
		directory = self.root / 'autonomous watcher'
		journal_watch.register(self.project, native, 0, state_dir=directory)
		with running_watcher(directory):
			self.finish('Autonomously reconciled native final')
			deadline = time.monotonic() + 8
			delivered = False
			while time.monotonic() < deadline:
				files = list((self.project / 'ꘖ/data/turns').glob('*.json'))
				delivered = any(('delivered' == json.loads(path.read_text(encoding='utf-8')).get('status') for path in files))
				if delivered:
					break
				time.sleep(0.05)
			self.assertTrue(delivered, journal_watch.status(state_dir=directory))
		self.assertEqual(self.saved('res'), b'Autonomously reconciled native final')
	def test_background_watcher_survives_a_binding_with_wrong_types(self):
		native = codex.native_answers(self.project, self.cid, backend=self.home)
		directory = self.root / 'typed corrupt watcher'
		binding = Path(journal_watch.register(self.project, native, 0, state_dir=directory)['binding'])
		broken = directory / 'bindings/000-wrong-types.json'
		invalid = {**json.loads(binding.read_text(encoding='utf-8')), 'platform': ['codex']}
		content = json.dumps(invalid).encode()
		broken.write_bytes(content)
		with running_watcher(directory):
			self.finish('Daemon survives wrong binding types')
			deadline = time.monotonic() + 8
			while time.monotonic() < deadline:
				files = list((self.project / 'ꘖ/data/turns').glob('*.json'))
				if any(('delivered' == json.loads(path.read_text(encoding='utf-8')).get('status') for path in files)):
					break
				time.sleep(0.05)
			self.assertEqual(journal_watch.status(state_dir=directory)['status'], 'running')
			self.assertEqual(self.saved('res'), b'Daemon survives wrong binding types')
		self.assertEqual(broken.read_bytes(), content)
	def test_background_watcher_survives_a_structurally_corrupt_group_and_records_another_project(self):
		directory, binding = self.registered_delivery()
		groups = journal.state_dir(self.project / 'ꙮ/1 - Analysis') / 'answer-groups'
		broken = next(groups.glob('*.json'))
		broken.write_bytes(b'null')
		self.expire_binding(binding)
		other = CompletionCase()
		other.setUp()
		self.addCleanup(other.doCleanups)
		other.finish('Healthy conversation remains observed')
		native = codex.native_answers(other.project, other.cid, backend=other.home)
		journal_watch.register(other.project, native, 0, state_dir=directory)
		with running_watcher(directory):
			deadline = time.monotonic() + 8
			response = other.project / 'ꙮ/1 - Analysis/res/1.md'
			while (not response.exists() or '2000-01-01T00:00:00+00:00' == json.loads(binding.read_text(encoding='utf-8')).get('last_checked_at')) and time.monotonic() < deadline:
				time.sleep(0.05)
			self.assertEqual(journal_watch.status(state_dir=directory)['status'], 'running')
			self.assertEqual(response.read_bytes(), b'Healthy conversation remains observed')
			value = json.loads(binding.read_text(encoding='utf-8'))
			self.assertFalse(value['last_result']['valid'])
		self.assertEqual(broken.read_bytes(), b'null')
class AntigravityCompletionTests(unittest.TestCase):
	def setUp(self):
		self.temp = tempfile.TemporaryDirectory()
		self.addCleanup(self.temp.cleanup)
		self.root = Path(self.temp.name)
		self.project = self.root / 'project'
		self.project.mkdir()
		self.backend = self.root / 'ag'
		(self.backend / 'conversations').mkdir(parents=True)
		self.cid = str(uuid.uuid4())
		self.path = self.backend / 'brain' / self.cid / '.system_generated/logs/transcript_full.jsonl'
		self.path.parent.mkdir(parents=True)
		self.rows = [{'step_index': 0, 'type': 'USER_INPUT', 'content': 'Native user'}]
		c = sqlite3.connect(self.backend / 'conversation_summaries.db')
		c.execute('CREATE TABLE conversation_summaries(conversation_id TEXT,parent_conversation_id TEXT,workspace_uris TEXT,status TEXT,not_fully_idle INTEGER,killed INTEGER,last_user_input_step_index INTEGER)')
		c.execute('INSERT INTO conversation_summaries VALUES(?,?,?,?,?,?,?)', (self.cid, '', json.dumps([self.project.as_uri()]), 'CASCADE_RUN_STATUS_RUNNING', 1, 0, 0))
		c.commit()
		c.close()
		c = sqlite3.connect(self.backend / 'conversations' / (self.cid + '.db'))
		c.execute('CREATE TABLE steps(idx INTEGER,step_type INTEGER,status INTEGER,step_format INTEGER,step_payload BLOB)')
		c.execute('INSERT INTO steps VALUES(0,14,3,0,?)', (wire(19, wire(2, 'Native user'.encode())),))
		c.commit()
		c.close()
		self.write()
	def write(self):
		self.path.write_text(''.join((json.dumps(row) + '\n' for row in self.rows)), encoding='utf-8')
	def finish(self, content='Final ꘖ', *, idle=True, partial=False):
		self.rows += [{'step_index': 1, 'type': 'PLANNER_RESPONSE', 'content': content}]
		c = sqlite3.connect(self.backend / 'conversations' / (self.cid + '.db'))
		c.execute('INSERT INTO steps VALUES(1,15,?,0,NULL)', (1 if partial else 3,))
		c.commit()
		c.close()
		c = sqlite3.connect(self.backend / 'conversation_summaries.db')
		c.execute('UPDATE conversation_summaries SET status=?,not_fully_idle=?', ('CASCADE_RUN_STATUS_IDLE' if idle else 'CASCADE_RUN_STATUS_RUNNING', 0 if idle else 1))
		c.commit()
		c.close()
		self.write()
	def sync(self):
		return completion.sync(self.project, self.cid, platform='antigravity', backend=self.backend)
	def test_idle_and_native_terminal_status_are_both_required(self):
		self.finish(idle=False)
		self.assertEqual(self.sync()['turns'], [])
		c = sqlite3.connect(self.backend / 'conversation_summaries.db')
		c.execute("UPDATE conversation_summaries SET status='CASCADE_RUN_STATUS_IDLE',not_fully_idle=0")
		c.commit()
		c.close()
		result = self.sync()['turns'][0]
		self.assertTrue(result['delivery_verified'])
		self.assertEqual((self.project / 'ꙮ/1 - Analysis/res/1.md').read_text(encoding='utf-8'), 'Final ꘖ')
	def test_partial_step_and_child_are_not_completed_public_answers(self):
		self.finish(partial=True)
		self.assertEqual(self.sync()['turns'], [])
		c = sqlite3.connect(self.backend / 'conversation_summaries.db')
		c.execute('UPDATE conversation_summaries SET parent_conversation_id=?', (str(uuid.uuid4()),))
		c.commit()
		c.close()
		with self.assertRaisesRegex(ValueError, 'child'):
			self.sync()
	def test_watcher_rechecks_native_step_status_without_a_transcript_or_summary_change(self):
		self.finish(partial=True)
		native = antigravity.native_answers(self.project, self.cid, backend=self.backend)
		directory = self.root / 'AG watcher'
		journal_watch.register(self.project, native, 0, state_dir=directory)
		self.assertEqual(journal_watch.once(state_dir=directory)['results'][0]['turns'], [])
		c = sqlite3.connect(self.backend / 'conversations' / (self.cid + '.db'))
		c.execute('UPDATE steps SET status=3 WHERE idx=1')
		c.commit()
		c.close()
		self.assertTrue(journal_watch.once(state_dir=directory)['results'][0]['turns'][0]['delivery_verified'])
	def test_mid_turn_checkpoint_blocks_until_recover_checkpoint(self):
		self.rows += [{'step_index': 1, 'type': 'PLANNER_RESPONSE', 'content': '', 'tool_calls': [{'id': 'c1', 'name': 'run_command', 'args': {'CommandLine': 'echo ok'}}]}, {'step_index': 2, 'type': 'GENERIC', 'content': '2722: Resolving Next.js interference'}, {'step_index': 3, 'type': 'CHECKPOINT', 'content': 'Compacted summary omitting 2722'}]
		self.write()
		with self.assertRaisesRegex(ValueError, 'COMPACT-1 / KB-3 violation'):
			completion.prepare(self.project, 'Response after compaction.', self.cid, platform='antigravity', backend=self.backend, watch=False)
		recovered = completion.recover_checkpoint(self.project, self.cid, platform='antigravity', backend=self.backend)
		self.assertTrue(recovered['compaction_check']['verified'])
		self.assertIn('2722: Resolving Next.js interference', recovered['pre_checkpoint_records'][0]['outputs'][0])
		prepared = completion.prepare(self.project, 'Response after compaction.', self.cid, platform='antigravity', backend=self.backend, watch=False)
		self.assertTrue(prepared['ready'])
	def test_adhoc_http_fetch_in_shell_blocks_and_collect_http_persists(self):
		from agent_tools import research
		self.rows += [{'step_index': 1, 'type': 'PLANNER_RESPONSE', 'content': '', 'tool_calls': [{'id': 'c1', 'name': 'run_command', 'args': {'CommandLine': 'python -c "import urllib.request; urllib.request.urlopen(\'https://df.tips/tag/google-analytics.json\')"'}}]}]
		self.write()
		with self.assertRaisesRegex(ValueError, 'KB-3 / EXEC-1 violation'):
			completion.prepare(self.project, 'Blocked ad-hoc HTTP.', self.cid, platform='antigravity', backend=self.backend, watch=False)
		fake_html = b'<html><head><title>Resolving Next.js interference</title></head><body><h1>Resolving Next.js interference</h1></body></html>'
		obs = research.collect_http(self.project, 'https://df.tips/t/2722', fetcher=lambda u, h, t: research.Response(u, 200, 'text/html', fake_html))
		self.assertEqual(obs['status'], 200)
		self.assertTrue((self.project / 'ꘖ/data/http-index.json').is_file())
	def test_external_article_link_requires_kb_grounding_and_matching_observed_title(self):
		marker = self.project / 'ꘖ/project.json'
		marker.parent.mkdir(parents=True, exist_ok=True)
		marker.write_text(json.dumps({'job_id': '~123456'}), encoding='utf-8')
		kb_dir = self.project / 'ꘖ/KB'
		kb_dir.mkdir(parents=True, exist_ok=True)
		bad_resp = 'See [How to set up client-side events for Google Analytics in Google Tag Manager for Magento?](https://df.tips/t/2722).'
		with self.assertRaisesRegex(ValueError, 'KB-1 / KB-3: External URL in response is missing from ꘖ/KB'):
			completion.prepare(self.project, bad_resp, self.cid, platform='antigravity', backend=self.backend, watch=False)
		(kb_dir / 'GA4-Audit.md').write_text('Source: https://df.tips/t/2722\n', encoding='utf-8')
		with self.assertRaisesRegex(ValueError, 'VERIFY-1 / KB-3: External article link .* has no saved observation'):
			completion.prepare(self.project, bad_resp, self.cid, platform='antigravity', backend=self.backend, watch=False)
		ev_dir = kb_dir / 'Evidence'
		ev_dir.mkdir(parents=True, exist_ok=True)
		(ev_dir / 'df-tips.json').write_text(json.dumps({'url': 'https://df.tips/tag/google-analytics.json', 'topic_list': {'topics': [{'id': 2722, 'title': "Resolving Next.js interference with the Google tag's cross-domain measurement linker", 'slug': 'resolving-next-js-interference'}]}}), encoding='utf-8')
		with self.assertRaisesRegex(ValueError, 'VERIFY-1 / LINK-1: Link title .* contradicts saved observation title'):
			completion.prepare(self.project, bad_resp, self.cid, platform='antigravity', backend=self.backend, watch=False)
		good_resp = "See [Resolving Next.js interference with the Google tag's cross-domain measurement linker](https://df.tips/t/2722)."
		prepared = completion.prepare(self.project, good_resp, self.cid, platform='antigravity', backend=self.backend, watch=False)
		self.assertTrue(prepared['ready'])
	def test_universal_source_kb_check_blocks_reddit_js_shell_unverified_short_links_missing_anchors_and_fake_quotes(self):
		from agent_tools import research
		self.assertFalse((self.project / 'ꘖ/project.json').exists())
		reddit_url = 'https://www.reddit.com/r/GoogleGeminiAI/comments/1abc/post/'
		short_link_resp = f'Author [u/Kooky-Split-8432]({reddit_url}#t1_nvz0p8c) wrote: «I hit a brick wall with Google Antigravity».'
		with self.assertRaisesRegex(ValueError, 'VERIFY-1 / KB-3: External article link .* has no saved observation'):
			completion.prepare(self.project, short_link_resp, self.cid, platform='antigravity', backend=self.backend, watch=False)
		js_shell = ('<!DOCTYPE html><html><head><title>Reddit</title><style>' + ('body{}' * 1400) + '</style></head><body><form><input type="hidden" name="js_challenge" value="1"/></form></body></html>').encode('utf-8')
		research.collect_http(self.project, reddit_url, fetcher=lambda u, h, t: research.Response(u, 200, 'text/html', js_shell), browser='never')
		with self.assertRaisesRegex(ValueError, 'VERIFY-1 / KB-3: External article link .* has no valid saved observation in ꘖ/KB/Evidence \\(browser_check_required=True'):
			completion.prepare(self.project, short_link_resp, self.cid, platform='antigravity', backend=self.backend, watch=False)
		html_no_anchor = b'<html><head><title>Google Antigravity Thread</title></head><body><h1>Google Antigravity Thread</h1><p>I hit a brick wall with Google Antigravity in production.</p></body></html>'
		research.collect_http(self.project, reddit_url, fetcher=lambda u, h, t: research.Response(u, 200, 'text/html', html_no_anchor), browser='never', refresh_reason='replace shell with body lacking anchor')
		with self.assertRaisesRegex(ValueError, 'VERIFY-1 / LINK-2: External link .* references anchor "#t1_nvz0p8c" which is absent from the saved observation'):
			completion.prepare(self.project, short_link_resp, self.cid, platform='antigravity', backend=self.backend, watch=False)
		html_with_anchor = b'<html><head><title>Google Antigravity Thread</title></head><body><h1>Google Antigravity Thread</h1><div id="t1_nvz0p8c"><p>I hit a brick wall with Google Antigravity in production.</p></div></body></html>'
		research.collect_http(self.project, reddit_url, fetcher=lambda u, h, t: research.Response(u, 200, 'text/html', html_with_anchor), browser='never', refresh_reason='add verified anchor')
		fake_quote_resp = f'Author [u/Kooky-Split-8432]({reddit_url}#t1_nvz0p8c) wrote: «Completely fabricated quote from search snippet».'
		with self.assertRaisesRegex(ValueError, 'VERIFY-1 / LINK-1: Verbatim quote .* attributed to .* is absent from the saved observation'):
			completion.prepare(self.project, fake_quote_resp, self.cid, platform='antigravity', backend=self.backend, watch=False)
		prepared = completion.prepare(self.project, short_link_resp, self.cid, platform='antigravity', backend=self.backend, watch=False)
		self.assertTrue(prepared['ready'])
	def test_unadopted_substantive_followup_in_tracked_project_cannot_bypass_review(self):
		marker = self.project / 'ꘖ/project.json'
		marker.parent.mkdir(parents=True, exist_ok=True)
		marker.write_text(json.dumps({'job_id': '~123456'}), encoding='utf-8')
		state = workflow.load(self.project)
		state['requests'] = [{'id': 'old-turn-0', 'text': 'Old request'}]
		state.setdefault('stages', {}).setdefault('finalize', {})['status'] = 'complete'
		wpath = workflow.state_path(self.project)
		wpath.parent.mkdir(parents=True, exist_ok=True)
		wpath.write_text(json.dumps(state), encoding='utf-8')
		with self.assertRaisesRegex(ValueError, 'REVIEW-3 / REVIEW-4: Adopt current requests'):
			completion.prepare(self.project, 'Hypothesis H-1: score 85%.', self.cid, platform='antigravity', backend=self.backend, watch=False)
		prepared_ordinary = completion.prepare(self.project, 'Ordinary reply after analysis completion (90.77%) mentioning ꘖ/KB.', self.cid, platform='antigravity', backend=self.backend, watch=False)
		self.assertTrue(prepared_ordinary['ready'])
	def test_kb_persistence_checks_target_path_not_scratch_content(self):
		self.rows.append({'step_index': 1, 'type': 'PLANNER_RESPONSE', 'content': '', 'tool_calls': [{'id': 'c1', 'name': 'write_file', 'args': {'Path': 'ꘖ/data/scratch/answer.md', 'Content': 'Mentions ꘖ/KB and ꘖ\\KB.'}}]})
		self.write()
		res1 = completion.begin(self.project, self.cid, platform='antigravity', backend=self.backend, watch=False)
		self.assertEqual(res1['delegation_check']['kb_persistence_step_count'], 0)
		self.rows.append({'step_index': 2, 'type': 'PLANNER_RESPONSE', 'content': '', 'tool_calls': [{'id': 'c2', 'name': 'write_file', 'args': {'Path': 'ꘖ/KB/Module.md', 'Content': 'New KB content'}}]})
		self.write()
		res2 = completion.begin(self.project, self.cid, platform='antigravity', backend=self.backend, watch=False)
		self.assertEqual(res2['delegation_check']['kb_persistence_step_count'], 1)
	def test_adopt_requests_isolates_foreign_answer_group_mismatch(self):
		jdir = self.project / 'ꙮ/1 - Analysis'
		(jdir / 'req').mkdir(parents=True, exist_ok=True)
		(jdir / 'res').mkdir(parents=True, exist_ok=True)
		(jdir / 'req/99.md').write_text('Edited foreign req', encoding='utf-8')
		(jdir / 'res/99.md').write_text('Foreign res', encoding='utf-8')
		gdir = journal.state_dir(jdir) / 'answer-groups'
		gdir.mkdir(parents=True, exist_ok=True)
		(gdir / 'native-foreign.json').write_text(json.dumps({'turn': 'native-foreign', 'journal': str(jdir.resolve()), 'status': 'complete', 'steps': [99], 'requests': ['Original foreign req'], 'request_ids': ['foreign-cid-0'], 'response_sha256': '00' * 32}), encoding='utf-8')
		self.assertEqual(journal.answer_groups(jdir, request_ids={f'{self.cid}-0'}), [])
	def test_unencoded_file_uri_accepted_in_prepare_and_reconciled_in_sync(self):
		with self.assertRaisesRegex(ValueError, 'LINK-5'):
			completion.prepare(self.project, 'See [File](file:///C:/work/with%20space.md).', self.cid, platform='antigravity', backend=self.backend, watch=False)
		prepared = completion.prepare(self.project, 'See [File](C:/work/test.md).', self.cid, platform='antigravity', backend=self.backend, watch=False)
		self.assertTrue(prepared['ready'])
		self.finish('See [File](file:///C:/work/test.md).')
		synced = self.sync()['turns'][0]
		self.assertEqual(synced['status'], 'delivered')
		self.assertTrue(synced['delivery_verified'])
	def test_single_turn_conversation_with_minus_one_last_user_index_syncs(self):
		c = sqlite3.connect(self.backend / 'conversation_summaries.db')
		c.execute('UPDATE conversation_summaries SET last_user_input_step_index=-1')
		c.commit()
		c.close()
		self.finish('Single turn reply.')
		synced = self.sync()['turns'][0]
		self.assertEqual(synced['status'], 'delivered')
		self.assertTrue(synced['delivery_verified'])
	def test_excessive_unpersisted_tool_steps_without_subagent_or_kb_write_blocks(self):
		marker = self.project / 'ꘖ/project.json'
		marker.parent.mkdir(parents=True, exist_ok=True)
		marker.write_text(json.dumps({'job_id': '~123456'}), encoding='utf-8')
		for idx in range(1, 43):
			self.rows.append({'step_index': idx, 'type': 'PLANNER_RESPONSE', 'content': '', 'tool_calls': [{'id': f'c{idx}', 'name': 'read_file', 'args': {'Path': 'README.md'}}]})
		self.write()
		with self.assertRaisesRegex(ValueError, 'REVIEW-1 / KB-3 violation in active turn: bulk primary-agent research'):
			completion.prepare(self.project, 'Simple reply.', self.cid, platform='antigravity', backend=self.backend, watch=False)
		self.rows.append({'step_index': 43, 'type': 'PLANNER_RESPONSE', 'content': '', 'tool_calls': [{'id': 'c43', 'name': 'invoke_subagent', 'args': {'TypeName': 'af-worker'}}]})
		self.write()
		prepared = completion.prepare(self.project, 'Simple reply.', self.cid, platform='antigravity', backend=self.backend, watch=False)
		self.assertTrue(prepared['ready'])
	def test_unfinished_parallel_subagent_turn_merges_with_next_request_and_blocks_english_stub_on_russian_request(self):
		req1 = '\u041f\u0440\u043e\u0432\u0435\u0440\u044c \u0434\u0432\u0435 \u0437\u0430\u0434\u0430\u0447\u0438 \u0432 \u0440\u0435\u043f\u043e\u0437\u0438\u0442\u043e\u0440\u0438\u0438.'
		req2 = '\u041a\u0430\u043a\u043e\u0439 \u0441\u0442\u0430\u0442\u0443\u0441 \u043f\u043e \u0437\u0430\u0434\u0430\u0447\u0430\u043c?'
		self.rows = [
			{'step_index': 0, 'type': 'USER_INPUT', 'content': req1},
			{'step_index': 1, 'type': 'PLANNER_RESPONSE', 'content': '', 'tool_calls': [{'id': 's1', 'name': 'invoke_subagent', 'args': {'TypeName': 'self'}}, {'id': 's2', 'name': 'invoke_subagent', 'args': {'TypeName': 'self'}}]},
			{'step_index': 2, 'type': 'EPHEMERAL_MESSAGE', 'content': '<SYSTEM_MESSAGE>\nSubagent 111 completed.\n</SYSTEM_MESSAGE>'},
			{'step_index': 3, 'type': 'PLANNER_RESPONSE', 'content': 'Subagent 1 finished. Waiting for the remaining 1 subagent to complete.'},
			{'step_index': 4, 'type': 'USER_INPUT', 'content': req2}
		]
		self.write()
		c = sqlite3.connect(self.backend / 'conversations' / (self.cid + '.db'))
		c.execute('DELETE FROM steps')
		c.execute('INSERT INTO steps VALUES(0,14,3,0,?)', (wire(19, wire(2, req1.encode('utf-8'))),))
		c.execute('INSERT INTO steps VALUES(3,15,3,0,NULL)')
		c.execute('INSERT INTO steps VALUES(4,14,3,0,?)', (wire(19, wire(2, req2.encode('utf-8'))),))
		c.commit()
		c.close()
		c = sqlite3.connect(self.backend / 'conversation_summaries.db')
		c.execute('UPDATE conversation_summaries SET last_user_input_step_index=4')
		c.commit()
		c.close()
		native = antigravity.native_answers(self.project, self.cid, backend=self.backend)
		self.assertEqual(1, len(native['turns']))
		self.assertEqual([f'{self.cid}-0', f'{self.cid}-4'], [r['id'] for r in native['turns'][0]['requests']])
		with self.assertRaisesRegex(ValueError, 'FILE-3 / REVIEW-1'):
			completion.prepare(self.project, 'Waiting for the remaining 1 subagent to complete.', self.cid, platform='antigravity', backend=self.backend, watch=False)
		with self.assertRaisesRegex(ValueError, 'TEXT-1'):
			completion.prepare(self.project, 'All subagent tasks were verified and completed without errors.', self.cid, platform='antigravity', backend=self.backend, watch=False)
		final_ru = '\u041e\u0431\u0435 \u0437\u0430\u0434\u0430\u0447\u0438 \u0432\u044b\u043f\u043e\u043b\u043d\u0435\u043d\u044b \u0438 \u043f\u0440\u043e\u0432\u0435\u0440\u0435\u043d\u044b.'
		prepared = completion.prepare(self.project, final_ru, self.cid, platform='antigravity', backend=self.backend, watch=False)
		self.assertTrue(prepared['ready'])
		self.assertEqual([1, 2], prepared['journal_steps'])
	def test_code_and_issue_lifecycle_gate_blocks_uncommitted_unpushed_and_open_issue_in_prepare(self):
		import subprocess
		bare = self.root / 'remote.git'
		subprocess.run(['git', 'init', '--bare', str(bare)], check=True, capture_output=True)
		code_repo = self.project / 'code'
		(self.project / '_/ꘖ').mkdir(parents=True, exist_ok=True)
		code_repo.mkdir(parents=True, exist_ok=True)
		subprocess.run(['git', 'init'], cwd=code_repo, check=True, capture_output=True)
		subprocess.run(['git', 'config', 'user.email', 'test@example.com'], cwd=code_repo, check=True, capture_output=True)
		subprocess.run(['git', 'config', 'user.name', 'Test'], cwd=code_repo, check=True, capture_output=True)
		subprocess.run(['git', 'remote', 'add', 'origin', str(bare)], cwd=code_repo, check=True, capture_output=True)
		mod = code_repo / 'mod.py'
		mod.write_text('x = 1\n', encoding='utf-8')
		self.rows.append({'step_index': 1, 'type': 'PLANNER_RESPONSE', 'content': '', 'tool_calls': [{'id': 'w1', 'name': 'write_file', 'args': {'Path': str(mod)}}]})
		self.write()
		with self.assertRaisesRegex(ValueError, 'EXEC-5 violation in active turn \\(code/issue lifecycle incomplete\\)'):
			completion.prepare(self.project, 'Done.', self.cid, platform='antigravity', backend=self.backend, watch=False)
		mod.write_text('# https://github.com/dmitry-ai/antigravity-addons/issues/999\nx = 1\n', encoding='utf-8')
		subprocess.run(['git', 'add', 'mod.py'], cwd=code_repo, check=True, capture_output=True)
		subprocess.run(['git', 'commit', '-m', 'https://github.com/dmitry-ai/antigravity-addons/issues/999'], cwd=code_repo, check=True, capture_output=True)
		subprocess.run(['git', 'branch', '-M', 'main'], cwd=code_repo, check=True, capture_output=True)
		subprocess.run(['git', 'push', '-u', 'origin', 'main'], cwd=code_repo, check=True, capture_output=True)
		mod.write_text('# https://github.com/dmitry-ai/antigravity-addons/issues/999\nx = 2\n', encoding='utf-8')
		subprocess.run(['git', 'add', 'mod.py'], cwd=code_repo, check=True, capture_output=True)
		subprocess.run(['git', 'commit', '-m', 'https://github.com/dmitry-ai/antigravity-addons/issues/999'], cwd=code_repo, check=True, capture_output=True)
		with self.assertRaisesRegex(ValueError, 'has not been pushed to upstream'):
			completion.prepare(self.project, 'Done.', self.cid, platform='antigravity', backend=self.backend, watch=False)
		subprocess.run(['git', 'push'], cwd=code_repo, check=True, capture_output=True)
		ev_file = self.project / '_/ꘖ/KB/Evidence/GitHub/dmitry-ai__antigravity-addons/issue-999.json'
		ev_file.parent.mkdir(parents=True, exist_ok=True)
		ev_file.write_text(json.dumps({'url': 'https://github.com/dmitry-ai/antigravity-addons/issues/999', 'issue': {'number': 999, 'state': 'OPEN'}}), encoding='utf-8')
		with self.assertRaisesRegex(ValueError, 'remains open; close it via df_github_issue.py close'):
			completion.prepare(self.project, 'Done.', self.cid, platform='antigravity', backend=self.backend, watch=False)
		ev_file.write_text(json.dumps({'url': 'https://github.com/dmitry-ai/antigravity-addons/issues/999', 'issue': {'number': 999, 'state': 'CLOSED'}}), encoding='utf-8')
		prepared = completion.prepare(self.project, 'Done.', self.cid, platform='antigravity', backend=self.backend, watch=False)
		self.assertTrue(prepared['ready'])
		self.assertTrue(prepared['code_lifecycle_check']['verified'])
	def test_local_source_grounding_blocks_fabricated_quotes_identifiers_and_currencies(self):
		src_dir = self.project / 'source/Nexcess/support/48401406/KB'
		src_dir.mkdir(parents=True, exist_ok=True)
		src_file = src_dir / 'source.md'
		src_file.write_text('# Case 48401406\nAuthor: Brent\nInvoice #4901796 on 2026-06-22 charged $425.00 for XS Plan.\nMessage: "Please review our XS Plan renewal invoice."\n', encoding='utf-8')
		bad_quote_resp = 'In [source.md](source/Nexcess/support/48401406/KB/source.md) the invoice states `"5697111 2026-10-22 $475.27 PAID"`.'
		with self.assertRaisesRegex(ValueError, 'VERIFY-1 / LINK-1'):
			completion.prepare(self.project, bad_quote_resp, self.cid, platform='antigravity', backend=self.backend, watch=False)
		bad_id_resp = 'In [source.md](source/Nexcess/support/48401406/KB/source.md) invoice `#5697111` charged `$425.00`.'
		with self.assertRaisesRegex(ValueError, 'VERIFY-1 / DOC-1: Unverified numeric figure or identifier'):
			completion.prepare(self.project, bad_id_resp, self.cid, platform='antigravity', backend=self.backend, watch=False)
		bad_amt_resp = 'In [source.md](source/Nexcess/support/48401406/KB/source.md) invoice `#4901796` charged `$475.27`.'
		with self.assertRaisesRegex(ValueError, 'VERIFY-1 / DOC-1: Unverified numeric figure or identifier'):
			completion.prepare(self.project, bad_amt_resp, self.cid, platform='antigravity', backend=self.backend, watch=False)
		bad_count_resp = 'In [source.md](source/Nexcess/support/48401406/KB/source.md) invoice `#4901796` had `65` occurrences and cost `EUR 300`.'
		with self.assertRaisesRegex(ValueError, 'VERIFY-1 / DOC-1: Unverified numeric figure or identifier'):
			completion.prepare(self.project, bad_count_resp, self.cid, platform='antigravity', backend=self.backend, watch=False)
		bad_rel_mod = 'In [source.md](source/Nexcess/support/48401406/KB/source.md) the file was modified directly inside `vendor/mirasvit/`.'
		with self.assertRaisesRegex(ValueError, 'VERIFY-1 / LINK-1: Relational modification claim requires at least two distinct primary source operands'):
			completion.prepare(self.project, bad_rel_mod, self.cid, platform='antigravity', backend=self.backend, watch=False)
		good_resp = 'In [source.md](source/Nexcess/support/48401406/KB/source.md) invoice `#4901796` charged `$425.00`: «Please review our XS Plan renewal invoice.»'
		prepared = completion.prepare(self.project, good_resp, self.cid, platform='antigravity', backend=self.backend, watch=False)
		self.assertTrue(prepared['ready'])
	def test_post_checkpoint_unreread_source_blocks_analysis_and_response(self):
		src_dir = self.project / 'source/Nexcess/support/48401406/KB'
		src_dir.mkdir(parents=True, exist_ok=True)
		src_file = src_dir / 'source.md'
		src_file.write_text('# Case 48401406\nInvoice #4901796 charged $425.00.\n', encoding='utf-8')
		an_file = src_dir / 'analysis.md'
		an_file.write_text('In [source.md](source.md) invoice `#4901796` charged `$425.00`.\n', encoding='utf-8')
		self.rows += [
			{'step_index': 1, 'type': 'PLANNER_RESPONSE', 'content': '', 'tool_calls': [{'id': 'r1', 'name': 'read_file', 'args': {'Path': str(src_file)}}]},
			{'step_index': 2, 'type': 'GENERIC', 'content': '# Case 48401406'},
			{'step_index': 3, 'type': 'CHECKPOINT', 'content': 'Compacted summary'},
			{'step_index': 4, 'type': 'PLANNER_RESPONSE', 'content': '', 'tool_calls': [{'id': 'w1', 'name': 'write_file', 'args': {'Path': str(an_file)}}]}
		]
		self.write()
		completion.recover_checkpoint(self.project, self.cid, platform='antigravity', backend=self.backend)
		with self.assertRaisesRegex(ValueError, 'COMPACT-1 / KB-3 violation in active turn: analysis.md written after CHECKPOINT without re-reading evicted sibling source.md'):
			completion.prepare(self.project, 'Summary.', self.cid, platform='antigravity', backend=self.backend, watch=False)
		self.rows.append({'step_index': 5, 'type': 'PLANNER_RESPONSE', 'content': '', 'tool_calls': [{'id': 'r2', 'name': 'read_file', 'args': {'Path': str(src_file)}}]})
		self.write()
		prepared = completion.prepare(self.project, 'In [source.md](source/Nexcess/support/48401406/KB/source.md) invoice `#4901796` charged `$425.00`.', self.cid, platform='antigravity', backend=self.backend, watch=False)
		self.assertTrue(prepared['ready'])
	def test_unpersisted_source_reads_and_af_worker_cannot_bypass_substantive_review(self):
		marker = self.project / '\ua616/project.json'
		marker.parent.mkdir(parents=True, exist_ok=True)
		marker.write_text(json.dumps({'job_id': '~123456'}), encoding='utf-8')
		for idx in range(1, 11):
			self.rows.append({'step_index': idx, 'type': 'PLANNER_RESPONSE', 'content': '', 'tool_calls': [{'id': f'sr{idx}', 'name': 'read_file', 'args': {'Path': f'source/Nexcess/support/{idx}/KB/source.md'}}]})
		self.write()
		with self.assertRaisesRegex(ValueError, 'REVIEW-1 / KB-3 violation in active turn: bulk primary-agent research'):
			completion.prepare(self.project, 'Simple reply.', self.cid, platform='antigravity', backend=self.backend, watch=False)
		self.rows.append({'step_index': 11, 'type': 'PLANNER_RESPONSE', 'content': '', 'tool_calls': [{'id': 'af1', 'name': 'invoke_subagent', 'args': {'TypeName': 'af-worker'}}]})
		self.write()
		state = workflow.load(self.project)
		state['requests'] = [{'id': 'old-turn-0', 'text': 'Old request'}]
		state.setdefault('stages', {}).setdefault('finalize', {})['status'] = 'complete'
		wpath = workflow.state_path(self.project)
		wpath.parent.mkdir(parents=True, exist_ok=True)
		wpath.write_text(json.dumps(state), encoding='utf-8')
		with self.assertRaisesRegex(ValueError, 'REVIEW-3 / REVIEW-4: Adopt current requests'):
			completion.prepare(self.project, 'Method M-SRV-1: score 90%.', self.cid, platform='antigravity', backend=self.backend, watch=False)
	def test_orphan_pair_adopted_without_duplicate_and_overwritten_claimed_pair_flags_conflict(self):
		jdir = self.project / 'ꙮ/1 - Analysis'
		(jdir / 'req').mkdir(parents=True, exist_ok=True)
		(jdir / 'res').mkdir(parents=True, exist_ok=True)
		(jdir / 'req/75.md').write_bytes(b'Native user\r\n')
		(jdir / 'res/75.md').write_bytes('Final ꘖ\r\n'.encode('utf-8'))
		self.finish('Final ꘖ')
		synced = self.sync()['turns'][0]
		self.assertEqual(synced['status'], 'delivered')
		self.assertEqual(synced['journal_steps'], [75])
		self.assertEqual(synced['completion_provenance'], 'existing_journal')
		self.assertFalse(synced['recovered_after_delivery'])
		self.assertFalse((jdir / 'req/76.md').exists())
		again = self.sync()['turns'][0]
		self.assertEqual(again['status'], 'delivered')
		self.assertEqual(again['journal_steps'], [75])
		other = AntigravityCompletionTests()
		other.setUp()
		self.addCleanup(other.doCleanups)
		ojdir = other.project / 'ꙮ/1 - Analysis'
		(ojdir / 'req').mkdir(parents=True, exist_ok=True)
		(ojdir / 'res').mkdir(parents=True, exist_ok=True)
		gdir = journal.state_dir(ojdir) / 'answer-groups'
		gdir.mkdir(parents=True, exist_ok=True)
		(gdir / 'native-owner36.json').write_text(json.dumps({'version': 1, 'journal': str(ojdir.resolve()), 'turn': 'native-owner36', 'status': 'complete', 'steps': [36], 'requests': ['Original step 36 request'], 'response_sha256': '11' * 32, 'tokens': ['tok36'], 'request_ids': ['other-conv-112']}), encoding='utf-8')
		(ojdir / 'req/36.md').write_text('Native user', encoding='utf-8')
		(ojdir / 'res/36.md').write_text('Overwritten 36 response', encoding='utf-8')
		other.finish('Overwritten 36 response')
		conflict_res = other.sync()
		self.assertFalse(conflict_res['valid'])
		self.assertEqual(conflict_res['turns'][0]['status'], 'conflict')
		self.assertIn('claimed by another answer group', conflict_res['turns'][0]['detail'])
		self.assertFalse((ojdir / 'req/37.md').exists())
	def test_recover_turn_violation_unblocks_prepare_and_gate_blocks_direct_journal_writes(self):
		import check_rules_and_server_gate as gate
		self.assertIsNotNone(gate.check_journal_write_gate('write_file', {'Path': 'C:/work/project/ꙮ/1 - \u0410\u043d\u0430\u043b\u0438\u0437/req/36.md'}))
		self.assertIsNotNone(gate.check_journal_write_gate('edit_file', {'Path': 'C:/work/project/ꙮ/res/120.md'}))
		self.assertIsNotNone(gate.check_journal_write_gate('run_command', {'CommandLine': 'python scripts/record_step.py --dir ꙮ'}))
		self.assertIsNone(gate.check_journal_write_gate('write_file', {'Path': 'C:/work/project/ꘖ/data/scratch/answer.md'}))
		self.rows += [
			{'step_index': 1, 'type': 'PLANNER_RESPONSE', 'content': '', 'tool_calls': [{'id': 'g1', 'name': 'run_command', 'args': {'CommandLine': 'git status --short'}}, {'id': 'h1', 'name': 'run_command', 'args': {'CommandLine': 'curl.exe https://example.com/'}}]}
		]
		self.write()
		with self.assertRaisesRegex(ValueError, 'EXEC-5 violation'):
			completion.prepare(self.project, 'Final after recovery.', self.cid, platform='antigravity', backend=self.backend, watch=False)
		rec = completion.recover_turn_violation(self.project, self.cid, reason='Verified retrospective violation recovery', platform='antigravity', backend=self.backend)
		self.assertTrue(rec['exec5_check']['verified'])
		self.assertTrue(rec['exec5_check'].get('recovered_via_receipt'))
		self.assertTrue(rec['http_fetch_check']['verified'])
		self.assertTrue(rec['http_fetch_check'].get('recovered_via_receipt'))
		prepared = completion.prepare(self.project, 'Final after recovery.', self.cid, platform='antigravity', backend=self.backend, watch=False)
		self.assertTrue(prepared['ready'])
	def test_crlf_prepared_journal_and_system_message_subagent_completion_do_not_conflict(self):
		prepared = completion.prepare(self.project, 'Line 1\r\nLine 2\r\n', self.cid, platform='antigravity', backend=self.backend, watch=False)
		self.assertTrue(prepared['ready'])
		self.finish('Line 1\nLine 2')
		synced = self.sync()['turns'][0]
		self.assertEqual(synced['status'], 'delivered')
		self.assertTrue(synced['delivery_verified'])
	def test_universal_gates_m1_to_m6_for_external_writes_dict_issues_and_kb_mutations(self):
		import check_rules_and_server_gate as gate
		self.assertIsNotNone(gate.check_external_write_gate('run_command', {'CommandLine': 'gh issue create --repo smokeday-com/m --title T --body B'}))
		self.assertIsNotNone(gate.check_external_write_gate('run_command', {'CommandLine': 'gh api repos/smokeday-com/m/issues/37/comments -X POST'}))
		marker = self.project / 'ꘖ/project.json'
		marker.parent.mkdir(parents=True, exist_ok=True)
		marker.write_text(json.dumps({'job_id': '~123456'}), encoding='utf-8')
		res_begin = completion.begin(self.project, self.cid, platform='antigravity', backend=self.backend, watch=False)
		body_p = self.project / 'ꘖ/data/scratch/issue.md'
		body_p.parent.mkdir(parents=True, exist_ok=True)
		body_p.write_text('## Root Cause\nBody.\n', encoding='utf-8')
		self.assertIsNotNone(gate.check_external_write_gate('run_command', {'CommandLine': f'python df_github_issue.py create --repo smokeday-com/m --title T --body-file "{body_p}"'}))
		tpath = self.project / res_begin['state']
		tdata = json.loads(tpath.read_text(encoding='utf-8'))
		tdata['github_issues'] = {
			'https://github.com/smokeday-com/m/issues/48': {
				'repo': 'smokeday-com/m',
				'number': 48,
				'url': 'https://github.com/smokeday-com/m/issues/48',
				'state': 'open',
				'last_action': 'create',
			}
		}
		tpath.write_text(json.dumps(tdata), encoding='utf-8')
		ev_p = self.project / 'ꘖ/KB/Evidence/GitHub/smokeday-com__m/issue-48.json'
		ev_p.parent.mkdir(parents=True, exist_ok=True)
		ev_p.write_text(json.dumps({'url': 'https://github.com/smokeday-com/m/issues/48', 'number': 48, 'state': 'open', 'title': '\u0420\u0443\u0441\u0441\u043a\u0438\u0439 \u0437\u0430\u0433\u043e\u043b\u043e\u0432\u043e\u043a', 'body': '\u0420\u0443\u0441\u0441\u043a\u0438\u0439 \u0442\u0435\u043a\u0441\u0442 \u043e\u043f\u0438\u0441\u0430\u043d\u0438\u044f \u0437\u0430\u0434\u0430\u0447\u0438 \u0441 \u043a\u043e\u0434\u043e\u043c `test`.'}), encoding='utf-8')
		with self.assertRaisesRegex(ValueError, 'EXEC-5 violation in active turn \\(code/issue lifecycle incomplete\\).*LOCALE_MISMATCH'):
			completion.prepare(self.project, 'Summary.', self.cid, platform='antigravity', backend=self.backend, watch=False)
	def test_git_blob_size_gates_cygwin_paths_and_stale_credential_locks(self):
		import os
		import subprocess
		import git_shim
		from agent_tools import git_gate
		self.assertEqual(git_gate.normalize_host_path('/cygdrive/c/work/research'), Path('C:/work/research'))
		eff_read, _ = git_shim.prepare_git_invocation(['-C', '/cygdrive/c/work/research', 'status', '--short'])
		self.assertEqual(eff_read[:3], ['--no-optional-locks', '-C', 'C:/work/research'])
		lock_old = self.root / 'old.git-credentials.lock'
		lock_fresh = self.root / 'fresh.git-credentials.lock'
		lock_old.write_text('', encoding='utf-8')
		lock_fresh.write_text('', encoding='utf-8')
		old_ts = time.time() - 60.0
		os.utime(lock_old, (old_ts, old_ts))
		removed = git_gate.cleanup_stale_credential_locks(10.0, candidates=[lock_old, lock_fresh], check_running=False)
		self.assertEqual(removed, [str(lock_old)])
		self.assertFalse(lock_old.exists())
		self.assertTrue(lock_fresh.exists())
		bare = self.root / 'remote-blobs.git'
		subprocess.run(['git', 'init', '--bare', str(bare)], check=True, capture_output=True)
		repo = self.root / 'blob-repo'
		repo.mkdir(parents=True, exist_ok=True)
		subprocess.run(['git', 'init'], cwd=repo, check=True, capture_output=True)
		subprocess.run(['git', 'config', 'user.email', 'test@example.com'], cwd=repo, check=True, capture_output=True)
		subprocess.run(['git', 'config', 'user.name', 'Test'], cwd=repo, check=True, capture_output=True)
		subprocess.run(['git', 'remote', 'add', 'origin', str(bare)], cwd=repo, check=True, capture_output=True)
		har_file = repo / 'source/session.har'
		har_file.parent.mkdir(parents=True, exist_ok=True)
		har_file.write_bytes(b'H' * 1024)
		ext_file = repo / 'Evidence/HTTP/obs1/cap1/extracted-html.json'
		ext_file.parent.mkdir(parents=True, exist_ok=True)
		ext_file.write_bytes(b'E' * 2048)
		subprocess.run(['git', 'add', 'source/session.har', 'Evidence/HTTP/obs1/cap1/extracted-html.json'], cwd=repo, check=True, capture_output=True)
		git_gate.verify_staged_blob_sizes(repo)
		with patch.object(git_gate, 'EXTRACTED_MAX_BYTES', 1500):
			with self.assertRaisesRegex(ValueError, 'Staged derived extraction file .* exceeding MAX_BYTES'):
				git_gate.verify_staged_blob_sizes(repo)
		with patch.object(git_gate, 'GITHUB_MAX_BLOB_BYTES', 512):
			with self.assertRaisesRegex(ValueError, 'Staged Git blob .* exceeding GitHub GH001 hard limit'):
				git_gate.verify_staged_blob_sizes(repo)
		subprocess.run(['git', 'commit', '-m', 'Initial files kept in git'], cwd=repo, check=True, capture_output=True)
		git_gate.verify_push_blob_sizes(repo)
		with patch.object(git_gate, 'EXTRACTED_MAX_BYTES', 1500):
			with self.assertRaisesRegex(ValueError, 'Unpushed derived extraction blob .* exceeding MAX_BYTES'):
				git_gate.verify_push_blob_sizes(repo)
		with patch.object(git_gate, 'GITHUB_MAX_BLOB_BYTES', 512):
			with self.assertRaisesRegex(ValueError, 'Unpushed Git blob .* exceeding GitHub GH001 hard limit'):
				git_gate.verify_push_blob_sizes(repo)
		eff_push, _ = git_shim.prepare_git_invocation(['-C', str(repo), 'push', 'origin', 'HEAD'])
		self.assertEqual(eff_push[:2], ['-c', 'credentialstore.locktimeoutms=5000'])
		self.assertFalse(git_gate.is_agent_git_context(env={}, ancestor_names=('python.exe', 'sh.exe', 'git.exe', 'bash.exe', 'windowsterminal.exe', 'explorer.exe')))
		self.assertTrue(git_gate.is_agent_git_context(env={'ANTIGRAVITY_AGENT': '1'}, ancestor_names=('python.exe', 'bash.exe')))
		self.assertTrue(git_gate.is_agent_git_context(env={}, ancestor_names=('python.exe', 'sh.exe', 'git.exe', 'powershell.exe', 'language_server.exe', 'antigravity.exe')))
		self.assertTrue(git_gate.is_agent_git_context(env={}, ancestor_names=('python.exe', 'sh.exe', 'git.exe', 'codex-command-runner.exe', 'codex.exe')))
		msg_file = repo / '.git/COMMIT_EDITMSG'
		msg_file.write_text('2026-11-02\n', encoding='utf-8')
		(repo / 'note.md').write_text('human note\n', encoding='utf-8')
		subprocess.run(['git', 'add', 'note.md'], cwd=repo, check=True, capture_output=True)
		self.assertEqual(git_gate.run_git_hook('pre-commit', cwd=repo, agent_context=False), 0)
		self.assertEqual(git_gate.run_git_hook('commit-msg', [str(msg_file)], cwd=repo, agent_context=False), 0)
		self.assertEqual(git_gate.run_git_hook('commit-msg', [str(msg_file)], cwd=repo, agent_context=True), 2)
		with self.assertRaisesRegex(ValueError, 'commit message for an agent commit must contain only the GitHub Issue URL'):
			git_gate.verify_git_write_invocation(['-C', str(repo), 'commit', '-m', '2026-11-02'], agent_context=True)
		git_gate.verify_git_write_invocation(['-C', str(repo), 'commit', '-am', '2026-11-02'], agent_context=False)
		msg_file.write_text('https://github.com/dmitry-ai/harness/issues/39\n', encoding='utf-8')
		self.assertEqual(git_gate.run_git_hook('commit-msg', [str(msg_file)], cwd=repo, agent_context=True), 0)
		self.assertEqual(git_gate._NO_WINDOW, getattr(subprocess, 'CREATE_NO_WINDOW', 0))
		with patch.object(completion, '_code_and_issue_lifecycle_status', side_effect=AssertionError('sync must not run git lifecycle checks')):
			self.finish('Delivered without git storm in sync.')
			synced = self.sync()['turns'][0]
			self.assertTrue(synced['delivery_verified'])
class CausalBasisTests(unittest.TestCase):
	def test_observed_ignorance_to_equal_probability_error_is_rejected(self):
		text = 'Scores are conditional: equal percentages mean there is no evidentiary basis to prefer one over the other.'
		self.assertTrue(unsupported_probability_claims(text))
	def test_quotes_code_negation_and_explicit_symmetric_prior_are_allowed(self):
		bad = 'equal percentages mean there is no evidentiary basis'
		for text in ['> ' + bad, '```text\n' + bad + '\n```', 'The source writes: «' + bad + '».', 'Absence of data does not mean equal probabilities.', 'Equal prior probabilities are given by the symmetric experiment condition.']:
			self.assertFalse(unsupported_probability_claims(text), text)
class WatcherLifecycleTests(unittest.TestCase):
	def test_single_daemon_cooperatively_stops_without_touching_apps(self):
		with tempfile.TemporaryDirectory() as temp:
			directory = Path(temp) / 'watcher with spaces'
			with running_watcher(directory) as first:
				second = journal_watch.start(state_dir=directory)
				self.assertEqual(first['pid'], second['pid'])
				self.assertEqual(first['token'], second['token'])
			self.assertEqual(journal_watch.status(state_dir=directory)['status'], 'stopped')
			log_lines = [json.loads(line) for line in (directory / 'daemon.log').read_text(encoding='utf-8').splitlines() if line.strip() and line.lstrip().startswith('{')]
			events = {item.get('event') for item in log_lines}
			self.assertIn('start_spawn', events)
			self.assertIn('daemon_started', events)
			self.assertIn('stop_requested', events)
			self.assertIn('daemon_stopped', events)
			dry = journal_watch.once(state_dir=directory, dry_run=True)
			self.assertTrue(dry['dry_run'])
if '__main__' == __name__:
	unittest.main()
