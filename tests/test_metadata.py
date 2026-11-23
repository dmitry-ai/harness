# 2026-11-23 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Implement shared execution metadata collector and tab-indented JSON header formatter":
# https://github.com/dmitry-ai/harness/issues/149
from __future__ import annotations

from contextlib import closing
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import sqlite3
import sys
import tempfile
import unittest
from unittest.mock import patch
import uuid

SCRIPT_DIR = Path(__file__).resolve().parents[1] / 'scripts'
if str(SCRIPT_DIR) not in sys.path:
	sys.path.insert(0, str(SCRIPT_DIR))

from agent_tools import metadata


class MetadataFormattingAndCollectionTests(unittest.TestCase):
	def test_format_local_timestamp_and_duration_timecode(self) -> None:
		tz_plus3 = timezone(timedelta(hours=3))
		tz_minus5 = timezone(timedelta(hours=-5))
		tz_half = timezone(timedelta(hours=5, minutes=30))
		tz_utc = timezone.utc

		self.assertEqual(
			metadata.format_local_timestamp('2026-11-23T14:53:46Z', tz=tz_plus3),
			'2026-11-23 17:53:46 UTC+3',
		)
		self.assertEqual(
			metadata.format_local_timestamp('2026-11-23 14:53:46.820400+00:00', tz=tz_minus5),
			'2026-11-23 09:53:46 UTC-5',
		)
		self.assertEqual(
			metadata.format_local_timestamp('2026-11-23T14:53:46Z', tz=tz_half),
			'2026-11-23 20:23:46 UTC+5:30',
		)
		self.assertEqual(
			metadata.format_local_timestamp('2026-11-23T14:53:46Z', tz=tz_utc),
			'2026-11-23 14:53:46 UTC+0',
		)
		local_now = metadata.format_local_timestamp(datetime(2026, 11, 23, 14, 53, 46, tzinfo=timezone.utc))
		self.assertRegex(local_now, r'^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2} UTC[+-]\d+(?::\d{2})?$')

		self.assertEqual(
			metadata.format_duration_timecode('2026-11-23T14:53:46Z', '2026-11-23T14:53:46Z'),
			'00:00:00',
		)
		self.assertEqual(
			metadata.format_duration_timecode('2026-11-23T14:53:46Z', '2026-11-23T14:58:58Z'),
			'00:05:12',
		)
		self.assertEqual(
			metadata.format_duration_timecode('2026-11-23T14:00:00Z', '2026-11-23T15:02:05Z'),
			'01:02:05',
		)
		self.assertEqual(
			metadata.format_duration_timecode('2026-11-23T15:00:00Z', '2026-11-23T14:55:00Z'),
			'00:00:00',
		)

	def test_render_prepend_extract_and_strip_tab_indented_json_header(self) -> None:
		sample = {
			'Time': {
				'Request': '2026-11-23 17:53:46 UTC+3',
				'Response': '2026-11-23 17:58:58 UTC+3',
				'Duration': '00:05:12',
			},
			'Project': {
				'Name': 'Harness',
				'Path': 'C:/work/research/provision/code/AI/harness',
			},
			'Journal': {
				'Step': 223,
				'Conversation': '223',
			},
			'Agent': {
				'System': 'Antigravity',
				'Instance': 'A6',
				'Model': 'gemini-4-neon',
				'Effort': 'xhigh',
			},
			'Trace': {
				'Conversation ID': '9049ad03-aade-46fa-940f-a28b095d5e94',
				'Journal': {
					'Response': 'C:/work/research/provision/code/AI/harness/ꙮ/≺/221–240/223.md',
				},
			},
		}
		header = metadata.render_metadata_header(sample)
		self.assertTrue(header.startswith('```json\n{\n\t"Time": {\n\t\t"Request": "2026-11-23 17:53:46 UTC+3",'))
		self.assertIn('ꙮ/≺/221–240/223.md', header)
		self.assertTrue(header.endswith('\n}\n```\n\n'))

		body = 'Answer with Unicode ꘖ.\r\n  Spaces preserved.  '
		combined = metadata.prepend_metadata_header(body, sample)
		self.assertTrue(combined.endswith(body))
		parsed, extracted_body = metadata.extract_leading_metadata_header(combined)
		self.assertEqual(parsed, sample)
		self.assertEqual(extracted_body, body)
		self.assertEqual(metadata.strip_leading_metadata_header(combined), body)

		# Calling prepend_metadata_header on text that already has a Harness metadata block replaces it without doubling
		updated = {**sample, 'Journal': {'Step': 224, 'Conversation': '224'}}
		replaced = metadata.prepend_metadata_header(combined, updated)
		self.assertEqual(replaced.count('```json'), 1)
		parsed2, extracted_body2 = metadata.extract_leading_metadata_header(replaced)
		self.assertEqual(parsed2, updated)
		self.assertEqual(extracted_body2, body)

		# Non-Harness leading JSON code block must NOT be stripped
		ordinary_json_md = '```json\n{\n\t"foo": "bar"\n}\n```\n\nBody text.\n'
		parsed_none, untouched = metadata.extract_leading_metadata_header(ordinary_json_md)
		self.assertIsNone(parsed_none)
		self.assertEqual(untouched, ordinary_json_md)
		self.assertEqual(metadata.strip_leading_metadata_header(ordinary_json_md), ordinary_json_md)

	def test_build_journal_metadata_for_antigravity_and_codex(self) -> None:
		tz_plus3 = timezone(timedelta(hours=3))
		with tempfile.TemporaryDirectory() as tmp:
			base = Path(tmp).resolve()
			proj = base / 'harness'
			(proj / 'ꙮ').mkdir(parents=True)
			(proj / 'ꘖ/data/turns').mkdir(parents=True)

			# --- Antigravity fixture ---
			ag_cfg = base / 'ag_home/.gemini/config'
			ag_backend = base / 'ag_home/.gemini/antigravity'
			(ag_cfg / 'projects').mkdir(parents=True)
			(ag_backend / 'conversations').mkdir(parents=True)
			cid = str(uuid.uuid4())
			pid = str(uuid.uuid4())
			(ag_cfg / 'projects' / f'{pid}.json').write_text(
				json.dumps({
					'id': pid,
					'name': 'Harness',
					'projectResources': {'resources': [{'gitFolder': {'folderUri': proj.as_uri()}}]},
				}),
				encoding='utf-8',
			)
			t_log = ag_backend / 'brain' / cid / '.system_generated/logs/transcript_full.jsonl'
			t_log.parent.mkdir(parents=True)
			t_log.write_text(
				'\n'.join([
					json.dumps({'step_index': 0, 'type': 'USER_INPUT', 'created_at': '2026-11-23T14:50:00Z', 'content': 'Hi'}),
					json.dumps({'step_index': 1, 'type': 'PLANNER_RESPONSE', 'created_at': '2026-11-23T14:53:46Z', 'model': 'gemini-4-neon-xhigh', 'content': 'Done'}),
				]) + '\n',
				encoding='utf-8',
			)
			with closing(sqlite3.connect(ag_backend / 'conversation_summaries.db')) as conn:
				conn.execute(
					'CREATE TABLE conversation_summaries('
					'conversation_id TEXT, title TEXT, project_id TEXT, parent_conversation_id TEXT, '
					'workspace_uris TEXT, last_user_input_time TEXT)'
				)
				conn.execute(
					'INSERT INTO conversation_summaries VALUES (?,?,?,?,?,?)',
					(cid, '1', pid, '', json.dumps([proj.as_uri()]), '2026-11-23 14:50:00+00:00'),
				)
				conn.commit()
			with closing(sqlite3.connect(ag_backend / 'conversations' / f'{cid}.db')) as conn:
				conn.execute('CREATE TABLE steps(idx INTEGER, step_type INTEGER, status INTEGER, metadata BLOB)')
				conn.execute('INSERT INTO steps VALUES (0, 14, 3, ?)', (b'',))
				conn.execute('INSERT INTO steps VALUES (1, 15, 3, ?)', (b'',))
				conn.commit()

			fake_ag_paths = {
				'instance': 'A6',
				'backend_dir': ag_backend,
				'brain_dir': ag_backend / 'brain',
				'conversations_db': ag_backend / 'conversation_summaries.db',
				'conversations_dir': ag_backend / 'conversations',
				'projects_dir': ag_cfg / 'projects',
			}
			turn = {
				'turn_id': f'ag-{cid}-0',
				'start_step': 0,
				'final_step': 1,
				'turn_index': 1,
				'request_timestamp': '2026-11-23T14:50:00Z',
				'response_timestamp': '2026-11-23T14:53:46Z',
				'model': 'gemini-4-neon',
				'effort': 'xhigh',
				'requests': [{'id': f'{cid}-0', 'text': 'Hi', 'native_step': 0}],
			}
			native = {
				'platform': 'antigravity',
				'instance': 'A6',
				'conversation_id': cid,
				'native_backend': str(ag_backend),
				'source_file': str(t_log),
				'turns': [turn],
			}
			with patch('agent_tools.metadata._resolve_ag_paths_safe', return_value=fake_ag_paths):
				ag_meta = metadata.build_journal_metadata(
					proj,
					native,
					turn,
					journal_dir=proj / 'ꙮ',
					steps=[1],
					turn_key='abc123key',
					group_file=proj / 'ꘖ/data/.journal/deadbeef/answer-groups/native-abc123key.json',
					response_at=datetime(2026, 11, 23, 14, 53, 46, tzinfo=timezone.utc),
					tz=tz_plus3,
				)

			self.assertEqual(ag_meta['Time'], {
				'Request': '2026-11-23 17:50:00 UTC+3',
				'Response': '2026-11-23 17:53:46 UTC+3',
				'Duration': '00:03:46',
			})
			self.assertEqual(ag_meta['Project'], {
				'Name': 'Harness',
				'Path': proj.as_posix(),
			})
			self.assertEqual(ag_meta['Journal'], {
				'Step': 1,
				'Conversation': '1',
			})
			self.assertEqual(ag_meta['Agent'], {
				'System': 'Antigravity',
				'Instance': 'A6',
				'Model': 'gemini-4-neon',
				'Effort': 'xhigh',
			})
			self.assertEqual(ag_meta['Trace']['Conversation ID'], cid)
			self.assertEqual(ag_meta['Trace']['Turn']['Number'], 1)
			self.assertEqual(ag_meta['Trace']['Turn']['ID'], f'ag-{cid}-0')
			self.assertEqual(ag_meta['Trace']['Turn']['Key'], 'abc123key')
			self.assertEqual(ag_meta['Trace']['Turn']['Start Step'], 0)
			self.assertEqual(ag_meta['Trace']['Turn']['Final Step'], 1)
			self.assertNotIn('\\', ag_meta['Trace']['Turn']['State'])
			self.assertTrue(ag_meta['Trace']['Turn']['State'].endswith('/ꘖ/data/turns/abc123key.json'))
			self.assertTrue(ag_meta['Trace']['Journal']['Request'].endswith('/ꙮ/≻/1–20/1.md'))
			self.assertTrue(ag_meta['Trace']['Journal']['Response'].endswith('/ꙮ/≺/1–20/1.md'))
			self.assertTrue(ag_meta['Trace']['Journal']['Group'].endswith('/answer-groups/native-abc123key.json'))
			self.assertEqual(ag_meta['Trace']['Transcript'], t_log.as_posix())

			# --- Codex multi-step fixture ---
			cx_home = base / 'codex_home'
			cx_rollout = cx_home / 'sessions/2026/11/23/rollout.jsonl'
			cx_rollout.parent.mkdir(parents=True)
			cx_cid = str(uuid.uuid4())
			cx_rollout.write_text(
				'\n'.join([
					json.dumps({'type': 'session_meta', 'timestamp': '2026-11-23T15:00:00Z', 'payload': {'id': cx_cid, 'cwd': str(proj)}}),
					json.dumps({'type': 'event_msg', 'timestamp': '2026-11-23T15:00:01Z', 'payload': {'type': 'task_started', 'turn_id': 't-cx-2'}}),
					json.dumps({'type': 'turn_context', 'timestamp': '2026-11-23T15:00:02Z', 'payload': {'turn_id': 't-cx-2', 'cwd': str(proj), 'model': 'gpt-6.1-sol', 'effort': 'max'}}),
				]) + '\n',
				encoding='utf-8',
			)
			cx_turn = {
				'turn_id': 't-cx-2',
				'start_step': 1,
				'final_step': 12,
				'turn_index': 2,
				'request_timestamp': '2026-11-23T15:00:01Z',
				'response_timestamp': '2026-11-23T15:10:06Z',
				'model': 'gpt-6.1-sol',
				'effort': 'max',
				'requests': [
					{'id': f'codex:{cx_cid}:2', 'text': 'Req A', 'native_step': 2},
					{'id': f'codex:{cx_cid}:4', 'text': 'Req B', 'native_step': 4},
				],
			}
			cx_native = {
				'platform': 'codex',
				'instance': 'C2',
				'conversation_id': cx_cid,
				'native_backend': str(cx_home),
				'source_file': str(cx_rollout),
				'turns': [{'turn_id': 't-cx-1'}, cx_turn],
			}
			with patch('agent_tools.metadata._resolve_ag_paths_safe', return_value=fake_ag_paths):
				cx_meta = metadata.build_journal_metadata(
					proj,
					cx_native,
					cx_turn,
					journal_dir=proj / 'ꙮ',
					steps=[3, 4],
					turn_key='cx999key',
					conversation_steps=[1, 3, 4],
					response_at=datetime(2026, 11, 23, 15, 10, 6, tzinfo=timezone.utc),
					tz=tz_plus3,
				)
			self.assertEqual(cx_meta['Time'], {
				'Request': '2026-11-23 18:00:01 UTC+3',
				'Response': '2026-11-23 18:10:06 UTC+3',
				'Duration': '00:10:05',
			})
			self.assertEqual(cx_meta['Journal'], {
				'Step': [3, 4],
				'Conversation': '1, 3, 4',
			})
			self.assertEqual(cx_meta['Agent'], {
				'System': 'Codex',
				'Instance': 'C2',
				'Model': 'gpt-6.1-sol',
				'Effort': 'max',
			})
			self.assertEqual(cx_meta['Trace']['Turn']['Number'], 2)
			self.assertEqual(len(cx_meta['Trace']['Journal']['Request']), 2)
			self.assertEqual(len(cx_meta['Trace']['Journal']['Response']), 2)

	def test_build_github_issue_metadata_live_env_child_subagent_and_standalone(self) -> None:
		tz_plus3 = timezone(timedelta(hours=3))
		with tempfile.TemporaryDirectory() as tmp:
			base = Path(tmp).resolve()
			proj = base / 'harness'
			(proj / 'ꙮ').mkdir(parents=True)
			tdir = proj / 'ꘖ/data/turns'
			tdir.mkdir(parents=True)

			ag_cfg = base / 'ag_home/.gemini/config'
			ag_backend = base / 'ag_home/.gemini/antigravity'
			(ag_cfg / 'projects').mkdir(parents=True)
			(ag_backend / 'conversations').mkdir(parents=True)
			parent_cid = str(uuid.uuid4())
			child_cid = str(uuid.uuid4())
			pid = str(uuid.uuid4())
			(ag_cfg / 'projects' / f'{pid}.json').write_text(
				json.dumps({
					'id': pid,
					'name': 'Harness',
					'projectResources': {'resources': [{'folderUri': proj.as_uri()}]},
				}),
				encoding='utf-8',
			)
			parent_log = ag_backend / 'brain' / parent_cid / '.system_generated/logs/transcript_full.jsonl'
			parent_log.parent.mkdir(parents=True)
			parent_log.write_text(
				'\n'.join([
					json.dumps({'step_index': 0, 'type': 'USER_INPUT', 'created_at': '2026-11-23T18:10:30Z', 'content': 'Task'}),
					json.dumps({'step_index': 2, 'type': 'PLANNER_RESPONSE', 'created_at': '2026-11-23T18:10:33Z', 'model': 'gemini-4-neon-xhigh'}),
				]) + '\n',
				encoding='utf-8',
			)
			child_log = ag_backend / 'brain' / child_cid / '.system_generated/logs/transcript_full.jsonl'
			child_log.parent.mkdir(parents=True)
			child_log.write_text(
				json.dumps({'step_index': 1, 'type': 'PLANNER_RESPONSE', 'created_at': '2026-11-23T18:12:00Z', 'model': 'gemini-4-hydrogen-low'}) + '\n',
				encoding='utf-8',
			)
			with closing(sqlite3.connect(ag_backend / 'conversation_summaries.db')) as conn:
				conn.execute(
					'CREATE TABLE conversation_summaries('
					'conversation_id TEXT, title TEXT, project_id TEXT, parent_conversation_id TEXT, workspace_uris TEXT)'
				)
				conn.execute(
					'INSERT INTO conversation_summaries VALUES (?,?,?,?,?)',
					(parent_cid, '223', pid, '', json.dumps([proj.as_uri()])),
				)
				conn.execute(
					'INSERT INTO conversation_summaries VALUES (?,?,?,?,?)',
					(child_cid, '', pid, parent_cid, json.dumps([proj.as_uri()])),
				)
				conn.commit()
			turn_key = '91355b8fe91e6b668342eb9403711b16accbb450'
			turn_file = tdir / f'{turn_key}.json'
			turn_file.write_text(
				json.dumps({
					'key': turn_key,
					'project_root': str(proj),
					'platform': 'antigravity',
					'native_backend': str(ag_backend),
					'conversation_id': parent_cid,
					'native_turn_id': f'ag-{parent_cid}-0',
					'native_start_step': 0,
					'journal': str(proj / 'ꙮ'),
					'status': 'open',
					'reserved_journal_steps': [223],
					'requests': [{'id': f'{parent_cid}-0', 'text': 'Task', 'native_step': 0}],
				}),
				encoding='utf-8',
			)
			fake_ag_paths = {
				'instance': 'A6',
				'backend_dir': ag_backend,
				'brain_dir': ag_backend / 'brain',
				'conversations_db': ag_backend / 'conversation_summaries.db',
				'conversations_dir': ag_backend / 'conversations',
				'projects_dir': ag_cfg / 'projects',
			}
			env_primary = {
				'ANTIGRAVITY_AGENT': '1',
				'ANTIGRAVITY_ACCOUNT': 'A6',
				'ANTIGRAVITY_CONVERSATION_ID': parent_cid,
				'ANTIGRAVITY_PROJECT_ID': pid,
				'ANTIGRAVITY_APP_DATA_DIR': str(ag_backend),
				'ANTIGRAVITY_SOURCE_METADATA': json.dumps({'tool': {'conversationId': parent_cid, 'stepIndex': 76}}),
			}
			now_dt = datetime(2026, 11, 23, 18, 20, 5, tzinfo=timezone.utc)
			with patch('agent_tools.metadata._resolve_ag_paths_safe', return_value=fake_ag_paths):
				iss_meta = metadata.build_github_issue_metadata(
					issue_url='https://github.com/dmitry-ai/harness/issues/149',
					project_root=proj,
					env=env_primary,
					now=now_dt,
					tz=tz_plus3,
				)
			self.assertEqual(iss_meta['Time'], '2026-11-23 21:20:05 UTC+3')
			self.assertEqual(iss_meta['Issue'], 'https://github.com/dmitry-ai/harness/issues/149')
			self.assertEqual(iss_meta['Project'], {'Name': 'Harness', 'Path': proj.as_posix()})
			self.assertEqual(iss_meta['Journal'], {'Step': 223, 'Conversation': '223'})
			self.assertEqual(iss_meta['Agent'], {
				'System': 'Antigravity',
				'Instance': 'A6',
				'Model': 'gemini-4-neon',
				'Effort': 'xhigh',
			})
			self.assertEqual(iss_meta['Trace']['Conversation ID'], parent_cid)
			self.assertEqual(iss_meta['Trace']['Turn']['Number'], 1)
			self.assertEqual(iss_meta['Trace']['Turn']['Key'], turn_key)
			self.assertEqual(iss_meta['Trace']['Turn']['Start Step'], 0)
			self.assertEqual(iss_meta['Trace']['Turn']['Tool Step'], 76)
			self.assertEqual(iss_meta['Trace']['Turn']['State'], turn_file.as_posix())
			self.assertTrue(iss_meta['Trace']['Journal']['Request'].endswith('/ꙮ/≻/221–240/223.md'))
			self.assertTrue(iss_meta['Trace']['Journal']['Response'].endswith('/ꙮ/≺/221–240/223.md'))
			self.assertEqual(iss_meta['Trace']['Transcript'], parent_log.as_posix())

			# Child subagent inherits primary Journal/Turn while keeping its own model/effort and Subagent ID
			env_child = {
				**env_primary,
				'ANTIGRAVITY_CONVERSATION_ID': child_cid,
				'ANTIGRAVITY_SOURCE_METADATA': json.dumps({'tool': {'conversationId': child_cid, 'stepIndex': 5}}),
			}
			with patch('agent_tools.metadata._resolve_ag_paths_safe', return_value=fake_ag_paths):
				child_meta = metadata.build_github_issue_metadata(
					issue_url='https://github.com/dmitry-ai/harness/issues/149',
					project_root=proj,
					env=env_child,
					now=now_dt,
					tz=tz_plus3,
				)
			self.assertEqual(child_meta['Journal'], {'Step': 223, 'Conversation': '223'})
			self.assertEqual(child_meta['Agent']['Model'], 'gemini-4-hydrogen')
			self.assertEqual(child_meta['Agent']['Effort'], 'low')
			self.assertEqual(child_meta['Trace']['Conversation ID'], parent_cid)
			self.assertEqual(child_meta['Trace']['Subagent ID'], child_cid)
			self.assertEqual(child_meta['Trace']['Transcript'], child_log.as_posix())

			# Standalone run without agent environment produces minimal accurate metadata
			standalone_dir = base / 'standalone_repo'
			standalone_dir.mkdir()
			with patch('agent_tools.metadata._resolve_ag_paths_safe', return_value=None):
				minimal = metadata.build_github_issue_metadata(
					issue_url='https://github.com/acme/demo/issues/7',
					project_root=standalone_dir,
					env={},
					now=now_dt,
					tz=tz_plus3,
				)
			self.assertEqual(minimal, {
				'Time': '2026-11-23 21:20:05 UTC+3',
				'Issue': 'https://github.com/acme/demo/issues/7',
				'Project': {
					'Name': 'standalone_repo',
					'Path': standalone_dir.as_posix(),
				},
			})


if '__main__' == __name__:
	unittest.main()
