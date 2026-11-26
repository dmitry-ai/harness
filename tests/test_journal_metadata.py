# 2026-11-23 Dmitrii Fediuk https://github.com/dmitrii-fediuk
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

import check_stop_gate
from agent_tools import completion, journal, metadata, review, storage, text_core


# @used-by :meth:`JournalMetadataIntegrationTests.test_antigravity_prepare_prepends_metadata_and_stop_gate_and_sync_accept_clean_chat_reply()`
def _wire(field: int, payload: bytes) -> bytes:
	# @used-by :func:`_wire()`
	def _varint(val: int) -> bytes:
		out = bytearray()
		while 128 <= val:
			out.append((val & 127) | 128)
			val >>= 7
		out.append(val)
		return bytes(out)
	return _varint((field << 3) | 2) + _varint(len(payload)) + payload


# 2026-11-23
# "Prepend JSON metadata headers to new journal responses":
# https://github.com/dmitry-ai/harness/issues/151
class JournalMetadataIntegrationTests(unittest.TestCase):
	# @used-by :mod:`unittest`
	def test_antigravity_prepare_prepends_metadata_and_stop_gate_and_sync_accept_clean_chat_reply(self):
		with tempfile.TemporaryDirectory() as tmp:
			root = Path(tmp)
			proj = root / 'my-proj'
			proj.mkdir()
			backend = root / 'ag'
			(backend / 'conversations').mkdir(parents=True)
			projects_dir = root / 'config/projects'
			projects_dir.mkdir(parents=True)
			pid = str(uuid.uuid4())
			(projects_dir / f'{pid}.json').write_text(
				json.dumps({
					'id': pid,
					'name': 'Harness Demo',
					'projectResources': {'resources': [{'folderUri': proj.resolve().as_uri()}]},
				}),
				encoding='utf-8',
			)
			cid = str(uuid.uuid4())
			log_path = backend / 'brain' / cid / '.system_generated/logs/transcript_full.jsonl'
			log_path.parent.mkdir(parents=True)
			rows = [
				{'step_index': 0, 'type': 'USER_INPUT', 'created_at': '2026-11-23T14:00:00Z', 'content': 'Explain status.'},
				{'step_index': 1, 'type': 'PLANNER_RESPONSE', 'created_at': '2026-11-23T14:01:00Z', 'model': 'gemini-4-neon-xhigh', 'content': '', 'tool_calls': [{'id': 'c1', 'name': 'run_command', 'args': {'CommandLine': 'echo ok'}}]},
				{'step_index': 2, 'type': 'GENERIC', 'content': 'ok'},
			]
			log_path.write_text('\n'.join((json.dumps(r) for r in rows)) + '\n', encoding='utf-8')
			c = sqlite3.connect(backend / 'conversation_summaries.db')
			try:
				c.execute('CREATE TABLE conversation_summaries(conversation_id TEXT,parent_conversation_id TEXT,workspace_uris TEXT,status TEXT,not_fully_idle INTEGER,killed INTEGER,last_user_input_step_index INTEGER,project_id TEXT,title TEXT)')
				c.execute('INSERT INTO conversation_summaries VALUES(?,?,?,?,?,?,?,?,?)', (cid, '', json.dumps([proj.resolve().as_uri()]), 'CASCADE_RUN_STATUS_RUNNING', 1, 0, 0, pid, 'New Conversation'))
				c.commit()
			finally:
				c.close()
			cdb = sqlite3.connect(backend / 'conversations' / f'{cid}.db')
			try:
				cdb.execute('CREATE TABLE steps(idx INTEGER,step_type INTEGER,status INTEGER,step_format INTEGER,step_payload BLOB)')
				cdb.execute('INSERT INTO steps VALUES(0,14,3,0,?)', (_wire(19, _wire(2, b'Explain status.')),))
				cdb.execute('INSERT INTO steps VALUES(1,15,3,0,?)', (b'',))
				cdb.commit()
			finally:
				cdb.close()

			clean_body = 'Exact clean chat answer.\nSecond line preserved.  '
			prepared = completion.prepare(proj, clean_body, cid, platform='antigravity', backend=backend, watch=False)
			self.assertTrue(prepared['ready'])
			self.assertEqual(prepared['body_sha256'], hashlib.sha256(clean_body.encode('utf-8')).hexdigest())
			res_path = Path(prepared['response_file'])
			raw_saved = res_path.read_text(encoding='utf-8')
			self.assertEqual(prepared['response_sha256'], hashlib.sha256(raw_saved.encode('utf-8')).hexdigest())
			self.assertTrue(raw_saved.startswith('```json\n{\n\t"Time":'))
			parsed_meta, extracted_body = metadata.extract_leading_metadata_header(raw_saved)
			self.assertIsNotNone(parsed_meta)
			self.assertEqual(extracted_body, clean_body)
			self.assertIn('Request', parsed_meta['Time'])
			self.assertIn('Response', parsed_meta['Time'])
			self.assertIn('Duration', parsed_meta['Time'])
			self.assertEqual(parsed_meta['Project']['Name'], 'Harness Demo')
			self.assertEqual(parsed_meta['Project']['Path'], proj.resolve().as_posix())
			self.assertEqual(parsed_meta['Journal']['Step'], 1)
			self.assertEqual(parsed_meta['Journal']['Conversation'], '1')
			self.assertEqual(parsed_meta['Agent']['System'], 'Antigravity')
			self.assertEqual(parsed_meta['Agent']['Model'], 'gemini-4-neon')
			self.assertEqual(parsed_meta['Agent']['Effort'], 'xhigh')
			self.assertEqual(parsed_meta['Trace']['Conversation ID'], cid)
			self.assertEqual(parsed_meta['Trace']['Turn']['Number'], 1)
			self.assertEqual(parsed_meta['Trace']['Journal']['Response'], res_path.resolve().as_posix())
			self.assertEqual(parsed_meta['Trace']['Transcript'], log_path.resolve().as_posix())

			# Stop gate allows the clean chat reply (without JSON header) and blocks post-prepare edits.
			rows_clean = [*rows, {'step_index': 3, 'type': 'PLANNER_RESPONSE', 'created_at': '2026-11-23T14:02:15Z', 'model': 'gemini-4-neon-xhigh', 'content': clean_body}]
			log_path.write_text('\n'.join((json.dumps(r) for r in rows_clean)) + '\n', encoding='utf-8')
			stop_ok = check_stop_gate.evaluate_stop_payload({'terminationReason': 'NO_TOOL_CALL', 'fullyIdle': True, 'cwd': str(proj), 'sessionId': cid, 'transcriptPath': str(log_path)}, backend_override=backend)
			self.assertEqual(stop_ok['decision'], 'allow', stop_ok)

			rows_edited = [*rows, {'step_index': 3, 'type': 'PLANNER_RESPONSE', 'created_at': '2026-11-23T14:02:15Z', 'model': 'gemini-4-neon-xhigh', 'content': 'Edited after prepare!'}]
			log_path.write_text('\n'.join((json.dumps(r) for r in rows_edited)) + '\n', encoding='utf-8')
			stop_bad = check_stop_gate.evaluate_stop_payload({'terminationReason': 'NO_TOOL_CALL', 'fullyIdle': True, 'cwd': str(proj), 'sessionId': cid, 'transcriptPath': str(log_path)}, backend_override=backend)
			self.assertEqual(stop_bad['decision'], 'continue', stop_bad)

			# Restore clean chat reply, finalize native DB, and reconcile cleanly without conflict.
			log_path.write_text('\n'.join((json.dumps(r) for r in rows_clean)) + '\n', encoding='utf-8')
			c = sqlite3.connect(backend / 'conversation_summaries.db')
			try:
				c.execute("UPDATE conversation_summaries SET status='CASCADE_RUN_STATUS_IDLE',not_fully_idle=0")
				c.commit()
			finally:
				c.close()
			cdb = sqlite3.connect(backend / 'conversations' / f'{cid}.db')
			try:
				cdb.execute('INSERT INTO steps VALUES(3,15,3,0,?)', (b'',))
				cdb.commit()
			finally:
				cdb.close()

			synced = completion.sync(proj, cid, platform='antigravity', backend=backend)
			self.assertTrue(synced['valid'], synced)
			self.assertEqual(synced['turns'][0]['status'], 'delivered')
			self.assertTrue(synced['turns'][0]['delivery_verified'])
			self.assertTrue(synced['turns'][0]['preparation_verified'])
			self.assertEqual(synced['turns'][0]['completion_provenance'], 'prepared')
			self.assertEqual(res_path.read_text(encoding='utf-8'), raw_saved)

	# @used-by :mod:`unittest`
	def test_codex_prepare_reprepare_and_unprepared_recovery_prepend_metadata(self):
		with tempfile.TemporaryDirectory() as tmp:
			root = Path(tmp)
			proj = root / 'codex-proj'
			proj.mkdir()
			home = root / 'codex-home'
			cid = str(uuid.uuid4())
			t1 = str(uuid.uuid4())
			t2 = str(uuid.uuid4())
			rollout = home / 'sessions/2026/11/23' / f'rollout-2026-11-23T14-00-00-{cid}.jsonl'
			rollout.parent.mkdir(parents=True)
			rows = [
				{'timestamp': '2026-11-23T14:00:00Z', 'type': 'session_meta', 'payload': {'id': cid, 'cwd': str(proj), 'source': 'desktop'}},
				{'timestamp': '2026-11-23T14:00:01Z', 'type': 'turn_context', 'payload': {'turn_id': t1, 'cwd': str(proj), 'model': 'gpt-6.1-sol', 'effort': 'max'}},
				{'timestamp': '2026-11-23T14:00:02Z', 'type': 'event_msg', 'payload': {'type': 'task_started', 'turn_id': t1}},
				{'timestamp': '2026-11-23T14:00:02Z', 'type': 'response_item', 'payload': {'type': 'message', 'role': 'user', 'content': [{'type': 'input_text', 'text': 'First request.'}]}},
			]
			rollout.write_text('\n'.join((json.dumps(r) for r in rows)) + '\n', encoding='utf-8')
			db = sqlite3.connect(home / 'state_5.sqlite')
			try:
				db.execute('CREATE TABLE threads(id TEXT PRIMARY KEY,rollout_path TEXT,cwd TEXT,source TEXT)')
				db.execute('INSERT INTO threads VALUES(?,?,?,?)', (cid, str(rollout), str(proj), 'desktop'))
				db.commit()
			finally:
				db.close()

			p1 = completion.prepare(proj, 'Draft v1.', cid, platform='codex', backend=home, watch=False)
			p1_rep = completion.prepare(proj, 'Draft v2.', cid, platform='codex', backend=home, watch=False)
			self.assertTrue(p1_rep.get('reprepared_before_delivery'))
			self.assertEqual(p1_rep['journal_steps'], [1])
			res1 = Path(p1_rep['response_file']).read_text(encoding='utf-8')
			meta1, body1 = metadata.extract_leading_metadata_header(res1)
			self.assertIsNotNone(meta1)
			self.assertEqual(body1, 'Draft v2.')
			self.assertEqual(meta1['Agent']['System'], 'Codex')
			self.assertEqual(meta1['Agent']['Model'], 'gpt-6.1-sol')
			self.assertEqual(meta1['Agent']['Effort'], 'max')
			self.assertEqual(meta1['Trace']['Turn']['Number'], 1)

			# Repeated prepare with unchanged body is read-only.
			before_rep = (Path(p1_rep['response_file']).read_bytes(), Path(p1_rep['response_file']).stat().st_mtime_ns)
			with patch.object(storage.os, 'replace', side_effect=AssertionError('Unchanged prepare must not rewrite')):
				p1_again = completion.prepare(proj, 'Draft v2.', cid, platform='codex', backend=home, watch=False)
			self.assertEqual(p1_again['recorded_at'], p1_rep['recorded_at'])
			self.assertEqual((Path(p1_rep['response_file']).read_bytes(), Path(p1_rep['response_file']).stat().st_mtime_ns), before_rep)

			# Complete turn 1 with clean chat text, then add unprepared completed turn 2.
			rows += [
				{'timestamp': '2026-11-23T14:01:02Z', 'type': 'response_item', 'payload': {'type': 'message', 'role': 'assistant', 'phase': 'final_answer', 'status': 'completed', 'content': [{'type': 'output_text', 'text': 'Draft v2.'}]}},
				{'timestamp': '2026-11-23T14:01:03Z', 'type': 'event_msg', 'payload': {'type': 'task_complete', 'turn_id': t1, 'last_agent_message': 'Draft v2.'}},
				{'timestamp': '2026-11-23T14:05:00Z', 'type': 'turn_context', 'payload': {'turn_id': t2, 'cwd': str(proj), 'model': 'gpt-6.1-sol', 'effort': 'high'}},
				{'timestamp': '2026-11-23T14:05:00Z', 'type': 'event_msg', 'payload': {'type': 'task_started', 'turn_id': t2}},
				{'timestamp': '2026-11-23T14:05:00Z', 'type': 'response_item', 'payload': {'type': 'message', 'role': 'user', 'content': [{'type': 'input_text', 'text': 'Second request.'}]}},
				{'timestamp': '2026-11-23T14:06:30Z', 'type': 'response_item', 'payload': {'type': 'message', 'role': 'assistant', 'phase': 'final_answer', 'status': 'completed', 'content': [{'type': 'output_text', 'text': 'Unprepared turn 2 answer.'}]}},
				{'timestamp': '2026-11-23T14:06:31Z', 'type': 'event_msg', 'payload': {'type': 'task_complete', 'turn_id': t2, 'last_agent_message': 'Unprepared turn 2 answer.'}},
			]
			rollout.write_text('\n'.join((json.dumps(r) for r in rows)) + '\n', encoding='utf-8')
			synced = completion.sync(proj, cid, platform='codex', backend=home)
			self.assertTrue(synced['valid'], synced)
			self.assertEqual([t['journal_steps'] for t in synced['turns']], [[1], [2]])
			self.assertTrue(synced['turns'][0]['preparation_verified'])
			self.assertTrue(synced['turns'][1]['recovered_after_delivery'])
			res2_path = journal.step_file(proj / 'ꙮ/≺', 2, directory=proj / 'ꙮ')
			meta2, body2 = metadata.extract_leading_metadata_header(res2_path.read_text(encoding='utf-8'))
			self.assertIsNotNone(meta2)
			self.assertEqual(body2, 'Unprepared turn 2 answer.')
			self.assertEqual(meta2['Time']['Duration'], '00:01:30')
			self.assertEqual(meta2['Journal']['Step'], 2)
			self.assertEqual(meta2['Journal']['Conversation'], '1, 2')
			self.assertEqual(meta2['Agent']['Effort'], 'high')
			self.assertEqual(meta2['Trace']['Turn']['Number'], 2)

	# @used-by :mod:`unittest`
	def test_text_core_and_review_authorize_handle_metadata_prefixed_response(self):
		with tempfile.TemporaryDirectory() as tmp:
			root = Path(tmp)
			jdir = root / 'j'
			(jdir / 'res').mkdir(parents=True)
			hdr = metadata.render_metadata_header({
				'Time': {'Response': '2026-11-23 22:00:00 UTC+3'},
				'Project': {'Name': 'Demo', 'Path': root.resolve().as_posix()},
				'Journal': {'Step': 1, 'Conversation': '1'},
				'Agent': {'System': 'Antigravity', 'Instance': 'A6', 'Model': 'gemini-4-neon', 'Effort': 'xhigh'},
			})
			ru_body = 'Задача выполнена полностью.\nВсе тесты прошли успешно.\n'
			prefixed = hdr + ru_body
			target = jdir / 'res/1.md'
			target.write_text(prefixed, encoding='utf-8')
			findings = text_core.check_response(target, text=prefixed, lexicon=[])
			self.assertEqual([f for f in findings if 'error' == f.severity], [])
			# Review authorize matches clean body approval when given metadata-prefixed journal text.
			body_sha = hashlib.sha256(ru_body.encode('utf-8')).hexdigest()
			fake_pkg = {'risk': 'routine', 'subject_sha256': 'sub1', 'response': {'sha256': body_sha}, 'claims': [], 'evidence_inputs': {}}
			fake_state = {
				'stages': {'finalize': {'status': 'complete'}},
				'questions': {},
				'reviews': [{'schema_version': review.REVIEW_SCHEMA, 'id': 'r1', 'reviewer_id': 'rev-1', 'subject_sha256': 'sub1', 'package': 'pkg.json', 'response_sha256': body_sha, 'result': 'approved', 'independent': False}],
			}
			with patch.object(review, '_analysis', return_value={}), \
				patch.object(review, 'read_package', return_value=fake_pkg), \
				patch.object(review.ReviewQuorumEvaluator, 'entry_proof_current', return_value=True), \
				patch.object(review.ReviewQuorumEvaluator, 'findings_closed', return_value=True), \
				patch.object(review.ReviewQuorumEvaluator, 'quorum_satisfied', return_value=True), \
				patch.object(review, 'update_verified_claims_cache', return_value={}), \
				patch.object(review, 'inside', return_value=target):
				auth = review.authorize(root, fake_state, response=prefixed)
			self.assertEqual(auth['response_sha256'], body_sha)

	# @used-by :mod:`unittest`
	def test_resolve_project_identity_skips_user_registry_for_isolated_temp_dir(self):
		with tempfile.TemporaryDirectory() as tmp:
			proj = Path(tmp) / 'isolated-temp-proj'
			proj.mkdir()
			calls = []
			# @used-by :meth:`JournalMetadataIntegrationTests.test_resolve_project_identity_skips_user_registry_for_isolated_temp_dir()`
			def _spy(*args, **kwargs):
				calls.append((args, kwargs))
				return {}
			with patch('agent_tools.runtime.platform_instances', side_effect=_spy):
				ident = metadata.resolve_project_identity(proj)
			self.assertEqual(calls, [])
			self.assertEqual(ident['Name'], 'isolated-temp-proj')
			self.assertEqual(ident['Path'], proj.resolve().as_posix())


if '__main__' == __name__:
	unittest.main()
