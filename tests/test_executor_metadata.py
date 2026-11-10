# 2026-11-10 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Fix Antigravity executor/generation model mismatch in native-review-proof, decouple post-finalize deliverable reviews from initial Analysis.json, cache source grounding, and preserve journal recording on gate failure":
# https://github.com/dmitry-ai/harness/issues/51
# 2026-10-18 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Enforce pre-registered experiment plans, claim-to-test alignment, native reviewer provenance, and executor metadata verification":
# https://github.com/dmitry-ai/harness/issues/10
# 2026-10-31 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Reorganize AI into universal harness repository, translate rules and documentation to English, format per P.md, and enforce issue-driven Git workflow":
# https://github.com/dmitry-ai/harness/issues/26
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import sqlite3
import sys
import tempfile
import unittest
from unittest.mock import patch
import uuid
SCRIPTS = Path(__file__).resolve().parents[1] / 'scripts'
sys.path.insert(0, str(SCRIPTS))
from agent_tools import metrics, runtime
from agent_tools.platforms import antigravity as ag, codex
def varint(value):
	out = bytearray()
	while value > 127:
		out.append(value & 127 | 128)
		value >>= 7
	out.append(value)
	r = bytes(out)
	return r
def wire(path, value):
	value = value.encode('utf-8')
	for field in reversed(path):
		value = varint(field << 3 | 2) + varint(len(value)) + value
	r = value
	return r
class ExecutorMetadataTests(unittest.TestCase):
	def setUp(self):
		self.temp = tempfile.TemporaryDirectory()
		self.addCleanup(self.temp.cleanup)
		self.root = Path(self.temp.name)
		self.backend = self.root / 'antigravity'
		self.backend.mkdir()
		(self.backend / 'conversations').mkdir()
		self.home = self.root / 'codex'
		self.home.mkdir()
		self.parent, self.aa, self.af = (str(uuid.uuid4()) for _ in range(3))
	def ag_database(self, ident, model=None, configuration=None, legacy_id=None):
		database = self.backend / 'conversations' / (ident + '.db')
		connection = sqlite3.connect(database)
		connection.execute('CREATE TABLE steps(idx INTEGER,step_type INTEGER,status INTEGER,metadata BLOB)')
		connection.execute('INSERT INTO steps VALUES(1,15,3,?)', (varint(11 << 3) + varint(legacy_id) if legacy_id else b'',))
		if None is not model:
			connection.execute('CREATE TABLE gen_metadata(idx INTEGER,data BLOB,size INTEGER)')
			blob = wire((1, 19), model)
			connection.execute('INSERT INTO gen_metadata VALUES(0,?,?)', (blob, len(blob)))
		if None is not configuration:
			connection.execute('CREATE TABLE executor_metadata(idx INTEGER,data BLOB)')
			connection.execute('INSERT INTO executor_metadata VALUES(0,?)', (wire((10, 1, 28), configuration),))
		connection.commit()
		connection.close()
	def ag_child(self, ident, agent, selection):
		connection = sqlite3.connect(self.backend / 'conversation_summaries.db')
		connection.execute('CREATE TABLE IF NOT EXISTS conversation_summaries(conversation_id TEXT,parent_conversation_id TEXT,agent_name TEXT)')
		connection.execute('INSERT INTO conversation_summaries VALUES(?,?,?)', (ident, self.parent, agent))
		connection.commit()
		connection.close()
		prompt = 'Unique assigned task ' + ident
		child_log = self.backend / 'brain' / ident / '.system_generated/logs/transcript_full.jsonl'
		child_log.parent.mkdir(parents=True)
		child_log.write_text(json.dumps({'type': 'SYSTEM_MESSAGE', 'content': prompt}) + '\n')
		parent_log = self.backend / 'brain' / self.parent / '.system_generated/logs/transcript_full.jsonl'
		parent_log.parent.mkdir(parents=True, exist_ok=True)
		with parent_log.open('a') as stream:
			stream.write(json.dumps({'step_index': 1, 'type': 'PLANNER_RESPONSE', 'tool_calls': [{'name': 'invoke_subagent', 'args': {'Subagents': [{'TypeName': agent, 'Model': selection, 'Prompt': prompt}]}}]}) + '\n')
	def ag_read(self, ident, **kwargs):
		return ag.native_executor_metadata(self.root, ident, backend=self.backend, **kwargs)
	def test_primary_reads_actual_generation_and_executor_configuration_paths(self):
		self.ag_database(self.parent, 'reported-model', 'reported-model-high', 17)
		result = self.ag_read(self.parent)
		self.assertEqual(result['requested']['model'], 'reported-model')
		self.assertEqual(result['observed']['model'], 'reported-model')
		self.assertEqual(result['observed']['effort'], 'high')
		self.assertEqual(result['verification']['status'], 'verified')
		self.assertEqual({tuple(item['protobuf_path']) for item in result['metadata_sources']}, {(1, 19), (10, 1, 28)})
		self.assertFalse((self.root / 'ꘖ').exists(), 'Read-only metadata API must not create output files')
	def test_missing_tables_and_numeric_id_do_not_invent_model_or_high_mode(self):
		self.ag_database(self.parent, legacy_id=17)
		result = self.ag_read(self.parent)
		self.assertIsNone(result['observed']['model'])
		self.assertIsNone(result['observed']['effort'])
		self.assertEqual(result['observed']['model_ids'], [17])
		self.assertEqual(result['verification']['status'], 'unverified')
	def test_generation_and_config_model_mismatch_is_explicit(self):
		self.ag_database(self.parent, 'actually-reported', 'selected-different-high')
		result = self.ag_read(self.parent)
		self.assertEqual(result['verification']['status'], 'mismatch')
		self.assertEqual(result['observed']['configuration'], 'selected-different-high')
	def test_all_roles_use_native_invocations_without_runtime_model_fallback(self):
		self.ag_database(self.parent, 'native-parent', 'native-parent-high')
		self.ag_database(self.aa, 'native-parent', 'native-parent-high')
		self.ag_database(self.af, 'native-extractor', 'native-extractor-low')
		self.ag_child(self.aa, 'self', 'inherit')
		self.ag_child(self.af, 'af-worker', 'native-extractor-low')
		primary = self.ag_read(self.parent)
		aa = self.ag_read(self.aa, role='AA', parent_id=self.parent)
		af = self.ag_read(self.af, role='AF', parent_id=self.parent)
		self.assertEqual([item['role'] for item in (primary, aa, af)], ['primary', 'AA', 'AF'])
		self.assertEqual(aa['requested']['selection'], 'inherit')
		self.assertEqual(aa['requested']['model'], 'native-parent')
		self.assertEqual(af['requested']['model'], 'native-extractor')
		self.assertEqual(af['requested']['effort'], 'low')
		self.assertTrue(all(('verified' == item['verification']['status'] for item in (primary, aa, af))))
	def test_inherited_effort_mismatch_is_not_silently_inferred_high(self):
		self.ag_database(self.parent, 'native-parent', 'native-parent-high')
		self.ag_database(self.aa, 'native-parent', 'native-parent-low')
		self.ag_child(self.aa, 'self', 'inherit')
		result = self.ag_read(self.aa, role='AA', parent_id=self.parent)
		self.assertEqual(result['verification']['effort'], 'mismatch')
	def test_af_role_cannot_be_assigned_to_native_aa_session(self):
		self.ag_database(self.parent)
		self.ag_database(self.aa)
		self.ag_child(self.aa, 'self', 'inherit')
		with self.assertRaisesRegex(ValueError, 'role'):
			self.ag_read(self.aa, role='AF', parent_id=self.parent)
	def test_unsupported_protobuf_keeps_missing_fields_unverified(self):
		self.ag_database(self.parent, 'model', 'model-high')
		connection = sqlite3.connect(self.backend / 'conversations' / (self.parent + '.db'))
		connection.execute('UPDATE executor_metadata SET data=?', (b'\xff',))
		connection.commit()
		connection.close()
		result = self.ag_read(self.parent)
		self.assertEqual(result['observed']['model'], 'model')
		self.assertIsNone(result['observed']['effort'])
		self.assertEqual(result['verification']['status'], 'unverified')
	def codex_trace(self, ident, *, model='native-codex', effort='high', parent=None, call=None, meta_model=None):
		meta = {'id': ident, 'source': {'subagent': {'thread_spawn': {'parent_thread_id': parent, 'agent_path': '/root/worker'}}} if parent else 'vscode'}
		if None is not meta_model:
			meta['model'] = meta_model
		rows = [{'type': 'session_meta', 'payload': meta}]
		context = {'model': model, 'effort': effort}
		if None is not model or None is not effort:
			rows.append({'type': 'turn_context', 'payload': context})
		if call:
			rows.append({'type': 'response_item', 'payload': {'type': 'function_call', 'name': 'collaboration.spawn_agent', 'call_id': 'spawn', 'arguments': json.dumps({'task_name': 'worker', 'message': 'assigned task', **call})}})
		path = self.home / 'sessions' / (ident + '.jsonl')
		path.parent.mkdir(exist_ok=True)
		path.write_text('\n'.join((json.dumps(row) for row in rows)) + '\n')
		connection = sqlite3.connect(self.home / 'state_5.sqlite')
		connection.execute('CREATE TABLE IF NOT EXISTS threads(id TEXT PRIMARY KEY,rollout_path TEXT,agent_path TEXT)')
		connection.execute('INSERT OR REPLACE INTO threads VALUES (?,?,?)', (ident, str(path), '/root/worker' if parent else None))
		connection.commit()
		connection.close()
		r = (path, rows)
		return r
	def test_codex_primary_distinguishes_requested_unknown_from_observed(self):
		self.codex_trace(self.parent)
		result = codex.native_executor_metadata(self.root, self.parent, backend=self.home)
		self.assertIsNone(result['requested']['model'])
		self.assertEqual(result['observed'], {'model': 'native-codex', 'effort': 'high'})
		self.assertEqual(result['verification']['status'], 'unverified')
	def test_codex_aa_and_af_use_actual_spawn_selection(self):
		self.codex_trace(self.parent, call={})
		path, rows = self.codex_trace(self.parent, call={'fork_turns': 'all'})
		self.codex_trace(self.aa, parent=self.parent)
		result = codex.native_executor_metadata(self.root, self.aa, role='AA', parent_id=self.parent, backend=self.home)
		self.assertEqual(result['requested']['model'], 'native-codex')
		self.assertEqual(result['verification']['status'], 'verified')
		self.codex_trace(self.parent, call={'model': 'extractor-choice', 'reasoning_effort': 'low'})
		self.codex_trace(self.af, model='extractor-choice', effort='low', parent=self.parent)
		af = codex.native_executor_metadata(self.root, self.af, role='AF', parent_id=self.parent, backend=self.home)
		self.assertEqual(af['requested']['selection'], 'explicit-parent-spawn')
		self.assertEqual(af['verification']['status'], 'verified')
	def test_codex_explicit_requested_actual_model_mismatch_is_reported(self):
		self.codex_trace(self.parent, call={'model': 'requested', 'reasoning_effort': 'high'})
		self.codex_trace(self.aa, model='actual-other', effort='low', parent=self.parent)
		result = codex.native_executor_metadata(self.root, self.aa, role='AA', parent_id=self.parent, backend=self.home)
		self.assertEqual(result['verification']['status'], 'mismatch')
		self.assertEqual(result['verification']['model'], 'mismatch')
		self.assertEqual(result['verification']['effort'], 'mismatch')
	def test_codex_missing_native_context_is_explicitly_unverified(self):
		self.codex_trace(self.parent, model=None, effort=None)
		result = codex.native_executor_metadata(self.root, self.parent, backend=self.home)
		self.assertIsNone(result['observed']['model'])
		self.assertIsNone(result['observed']['effort'])
		self.assertEqual(result['verification']['status'], 'unverified')
	def test_immutable_executor_snapshots_cover_all_roles_and_can_be_reused(self):
		self.ag_database(self.parent, 'native-parent', 'native-parent-high')
		self.ag_database(self.aa, 'native-parent', 'native-parent-high')
		self.ag_database(self.af, 'extractor', 'extractor-low')
		self.ag_child(self.aa, 'self', 'inherit')
		self.ag_child(self.af, 'af-worker', 'extractor-low')
		receipts = []
		for ident, role in ((self.parent, 'primary'), (self.aa, 'AA'), (self.af, 'AF')):
			receipts.append(metrics.record_executor_metadata(self.root, ident, role=role, parent_id=self.parent if 'primary' != role else None, platform='antigravity', backend=self.backend))
		repeated = metrics.record_executor_metadata(self.root, self.parent, platform='antigravity', backend=self.backend)
		self.assertEqual(repeated['proof'], receipts[0]['proof'])
		index = json.loads((self.root / 'ꘖ/data/executors.json').read_bytes())
		self.assertEqual(len(index['snapshots']), 3)
		for receipt in receipts:
			self.assertEqual(hashlib.sha256((self.root / receipt['proof']).read_bytes()).hexdigest(), receipt['sha256'])
	def test_existing_codex_review_model_gate_still_rejects_missing_actual_context(self):
		self.codex_trace(self.parent, call={'fork_turns': 'all'})
		self.codex_trace(self.aa, model=None, effort=None, parent=self.parent)
		with self.assertRaisesRegex(ValueError, 'model/effort'):
			codex._model(codex._trace(self.home, self.aa)[3])
	def test_variant_suffixed_generation_model_matches_executor_configuration_and_inherit(self):
		self.ag_database(self.parent, 'gemini-4-argon-b', 'gemini-4-argon-high')
		self.ag_database(self.aa, 'gemini-4-argon-b', 'gemini-4-argon-high')
		self.ag_child(self.aa, 'self', 'inherit')
		primary = self.ag_read(self.parent)
		aa = self.ag_read(self.aa, role='AA', parent_id=self.parent)
		self.assertEqual(primary['observed']['generation_model'], 'gemini-4-argon-b')
		self.assertEqual(primary['observed']['executor_model'], 'gemini-4-argon')
		self.assertEqual(primary['verification']['status'], 'verified')
		self.assertEqual(aa['requested']['generation_model'], 'gemini-4-argon-b')
		self.assertEqual(aa['requested']['executor_model'], 'gemini-4-argon')
		self.assertEqual(aa['verification']['status'], 'verified')
if '__main__' == __name__:
	unittest.main()
