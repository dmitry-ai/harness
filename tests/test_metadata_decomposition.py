# 2026-11-24 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# https://github.com/dmitry-ai/harness/issues/170
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
def _make_ag_fixture(base: Path) -> dict:
	proj = base / 'demo_proj'
	(proj / '\ua66e').mkdir(parents=True)
	(proj / '\ua616/data/turns').mkdir(parents=True)
	ag_cfg = base / 'ag_cfg/projects'
	ag_backend = base / 'ag_backend'
	ag_cfg.mkdir(parents=True)
	(ag_backend / 'conversations').mkdir(parents=True)
	cid = str(uuid.uuid4())
	pid = str(uuid.uuid4())
	(ag_cfg / f'{pid}.json').write_text(json.dumps({'id': pid, 'name': 'Meta Demo', 'projectResources': {'resources': [{'folderUri': proj.as_uri()}]}}), encoding='utf-8')
	t_log = ag_backend / 'brain' / cid / '.system_generated/logs/transcript_full.jsonl'
	t_log.parent.mkdir(parents=True)
	t_rows = [
		json.dumps({'step_index': 0, 'type': 'USER_INPUT', 'created_at': '2026-11-23T14:50:00Z', 'content': 'Hi'}),
		json.dumps({'step_index': 1, 'type': 'PLANNER_RESPONSE', 'created_at': '2026-11-23T14:53:46Z', 'model': 'gemini-4-neon-xhigh'}),
	]
	t_log.write_text('\n'.join(t_rows) + '\n', encoding='utf-8')
	with closing(sqlite3.connect(ag_backend / 'conversation_summaries.db')) as conn:
		conn.execute('CREATE TABLE conversation_summaries(conversation_id TEXT, title TEXT, project_id TEXT, parent_conversation_id TEXT, workspace_uris TEXT)')
		conn.execute('INSERT INTO conversation_summaries VALUES (?,?,?,?,?)', (cid, '1', pid, '', json.dumps([proj.as_uri()])))
		conn.commit()
	ag_paths = {'instance': 'A6', 'backend_dir': ag_backend, 'brain_dir': ag_backend / 'brain', 'conversations_db': ag_backend / 'conversation_summaries.db', 'conversations_dir': ag_backend / 'conversations', 'projects_dir': ag_cfg}
	return {'ag_backend': ag_backend, 'ag_paths': ag_paths, 'cid': cid, 'pid': pid, 'proj': proj, 't_log': t_log}
class MetadataDecompositionTests(unittest.TestCase):
	def test_blocks_builders_produce_step_paths_labels_and_blocks(self) -> None:
		from agent_tools.meta import blocks
		tz_plus3 = timezone(timedelta(hours=3))
		with tempfile.TemporaryDirectory() as tmp:
			jdir = Path(tmp).resolve() / '\ua66e'
			jdir.mkdir(parents=True)
			req_one, res_one = blocks._journal_step_paths(jdir, [5])
			self.assertTrue(str(req_one).endswith('/\ua66e/\u227b/1\u201320/5.md'))
			self.assertTrue(str(res_one).endswith('/\ua66e/\u227a/1\u201320/5.md'))
			req_many, res_many = blocks._journal_step_paths(jdir, [2, 1, 2])
			self.assertEqual(len(req_many), 2)
			self.assertEqual(len(res_many), 2)
		self.assertEqual(blocks._conversation_label(summary_title='Custom Title', conversation_steps=[1], current_steps=[2]), 'Custom Title')
		self.assertEqual(blocks._conversation_label(summary_title='1', conversation_steps=[1], current_steps=[2]), '1, 2')
		self.assertEqual(blocks._conversation_label(summary_title='New Conversation', conversation_steps=[3], current_steps=[4]), '3, 4')
		self.assertEqual(blocks._build_agent_block('antigravity', 'A6', 'gemini-4-neon', None), {'System': 'Antigravity', 'Instance': 'A6', 'Model': 'gemini-4-neon', 'Effort': None})
		self.assertEqual(blocks._build_agent_block('codex', None, None, 'high'), {'System': 'Codex', 'Effort': 'high'})
		t_blk = blocks._build_time_block(datetime(2026, 11, 23, 14, 0, 0, tzinfo=timezone.utc), datetime(2026, 11, 23, 14, 5, 30, tzinfo=timezone.utc), tz_plus3)
		self.assertEqual(t_blk, {'Request': '2026-11-23 17:00:00 UTC+3', 'Response': '2026-11-23 17:05:30 UTC+3', 'Duration': '00:05:30'})
	def test_builders_honor_facade_monkeypatch_seam_and_match_metadata_parity(self) -> None:
		from agent_tools import metadata
		from agent_tools.meta import builders
		tz_plus3 = timezone(timedelta(hours=3))
		now_dt = datetime(2026, 11, 23, 14, 53, 46, tzinfo=timezone.utc)
		with tempfile.TemporaryDirectory() as tmp:
			fx = _make_ag_fixture(Path(tmp).resolve())
			turn = {'turn_id': f"ag-{fx['cid']}-0", 'start_step': 0, 'final_step': 1, 'turn_index': 1, 'request_timestamp': '2026-11-23T14:50:00Z', 'response_timestamp': '2026-11-23T14:53:46Z', 'model': 'gemini-4-neon', 'effort': 'xhigh'}
			native = {'platform': 'antigravity', 'instance': 'A6', 'conversation_id': fx['cid'], 'native_backend': str(fx['ag_backend']), 'source_file': str(fx['t_log']), 'turns': [turn]}
			with patch('agent_tools.metadata._resolve_ag_paths_safe', return_value=fx['ag_paths']):
				m_j = metadata.build_journal_metadata(fx['proj'], native, turn, journal_dir=fx['proj'] / '\ua66e', steps=[1], turn_key='k1', response_at=now_dt, tz=tz_plus3)
				b_j = builders.build_journal_metadata(fx['proj'], native, turn, journal_dir=fx['proj'] / '\ua66e', steps=[1], turn_key='k1', response_at=now_dt, tz=tz_plus3)
			self.assertEqual(m_j, b_j)
			self.assertEqual(b_j['Project']['Name'], 'Meta Demo')
			env_ag = {'ANTIGRAVITY_CONVERSATION_ID': fx['cid'], 'ANTIGRAVITY_ACCOUNT': 'A6', 'ANTIGRAVITY_PROJECT_ID': fx['pid'], 'ANTIGRAVITY_APP_DATA_DIR': str(fx['ag_backend']), 'ANTIGRAVITY_SOURCE_METADATA': json.dumps({'tool': {'conversationId': fx['cid'], 'stepIndex': 9}})}
			with patch('agent_tools.metadata._resolve_ag_paths_safe', return_value=fx['ag_paths']):
				m_i = metadata.build_github_issue_metadata(issue_url='https://github.com/dmitry-ai/harness/issues/170', project_root=fx['proj'], env=env_ag, now=now_dt, tz=tz_plus3)
				b_i = builders.build_github_issue_metadata(issue_url='https://github.com/dmitry-ai/harness/issues/170', project_root=fx['proj'], env=env_ag, now=now_dt, tz=tz_plus3)
			self.assertEqual(m_i, b_i)
			self.assertEqual(b_i['Agent']['Model'], 'gemini-4-neon')
			self.assertEqual(b_i['Trace']['Turn']['Tool Step'], 9)
	def test_formatting_submodule_handles_paths_timestamps_steps_and_models(self) -> None:
		from agent_tools.meta import formatting
		tz_plus3 = timezone(timedelta(hours=3))
		self.assertEqual(formatting.posix_path('C:\\work\\demo\\file.py'), 'C:/work/demo/file.py')
		self.assertIsNone(formatting.parse_timestamp(None))
		self.assertIsNone(formatting.parse_timestamp('   '))
		self.assertIsNone(formatting.parse_timestamp('not-a-date'))
		parsed = formatting.parse_timestamp('2026-11-23T14:53:46.123456789Z')
		self.assertIsNotNone(parsed)
		self.assertEqual(formatting.format_local_timestamp(parsed, tz=tz_plus3), '2026-11-23 17:53:46 UTC+3')
		self.assertEqual(formatting.format_duration_timecode('2026-11-23T14:50:00Z', '2026-11-23T14:55:07Z'), '00:05:07')
		self.assertEqual(formatting.format_duration_timecode('2026-11-23T15:00:00Z', '2026-11-23T14:00:00Z'), '00:00:00')
		self.assertIsNone(formatting.format_duration_timecode(None, '2026-11-23T14:00:00Z'))
		self.assertIsNone(formatting._format_step_value([]))
		self.assertEqual(formatting._format_step_value([7]), 7)
		self.assertEqual(formatting._format_step_value([9, 3, 9, 0]), [3, 9])
		self.assertEqual(formatting._system_display_name('antigravity'), 'Antigravity')
		self.assertEqual(formatting._system_display_name('codex'), 'Codex')
		self.assertIsNone(formatting._system_display_name(''))
		self.assertEqual(formatting._split_model_and_effort('gemini-4-neon-xhigh'), ('gemini-4-neon', 'xhigh'))
		self.assertEqual(formatting._split_model_and_effort('gpt-6.1-sol', 'max'), ('gpt-6.1-sol', 'max'))
	def test_headers_submodule_roundtrips_and_ignores_non_harness_json(self) -> None:
		from agent_tools.meta import headers
		sample = {'Time': '2026-11-23 20:00:00 UTC+3', 'Issue': 'https://github.com/dmitry-ai/harness/issues/170', 'Project': {'Name': 'Harness', 'Path': 'C:/work/harness'}}
		self.assertTrue(headers._is_harness_metadata_obj(sample))
		self.assertFalse(headers._is_harness_metadata_obj({'Unknown': 1, 'Project': {'Path': 'C:/x'}}))
		self.assertFalse(headers._is_harness_metadata_obj({'Project': {'Path': '   '}, 'Time': 'x'}))
		rendered = headers.render_metadata_header(sample)
		self.assertTrue(rendered.startswith('```json\n{\n\t"Time":'))
		body = 'Body line.\n'
		prefixed = headers.prepend_metadata_header(body, sample)
		extracted, clean = headers.extract_leading_metadata_header(prefixed)
		self.assertEqual(extracted, sample)
		self.assertEqual(clean, body)
		self.assertEqual(headers.strip_leading_metadata_header(prefixed), body)
		replaced = headers.prepend_metadata_header(prefixed, {**sample, 'Time': '2026-11-24 00:00:00 UTC+3'})
		self.assertEqual(replaced.count('```json'), 1)
		ordinary = '```json\n{"foo": "bar"}\n```\n\nText.\n'
		self.assertEqual(headers.extract_leading_metadata_header(ordinary), (None, ordinary))
	def test_identity_submodule_resolves_registry_project_json_and_fallback(self) -> None:
		from agent_tools.meta import identity
		with tempfile.TemporaryDirectory() as tmp:
			base = Path(tmp).resolve()
			pdir = base / 'projects'
			pdir.mkdir()
			proj_reg = base / 'reg_proj'
			proj_reg.mkdir()
			pid = str(uuid.uuid4())
			(pdir / f'{pid}.json').write_text(json.dumps({'id': pid, 'name': 'Registry Name', 'projectResources': {'resources': [{'folderUri': proj_reg.as_uri()}]}}), encoding='utf-8')
			ag_paths = {'projects_dir': pdir}
			self.assertEqual(identity.resolve_project_identity(proj_reg, ag_paths=ag_paths, project_id=pid), {'Name': 'Registry Name', 'Path': proj_reg.as_posix()})
			self.assertEqual(identity.resolve_project_identity(proj_reg, ag_paths=ag_paths), {'Name': 'Registry Name', 'Path': proj_reg.as_posix()})
			proj_json_dir = base / 'json_proj'
			(proj_json_dir / '\ua616').mkdir(parents=True)
			(proj_json_dir / '\ua616/project.json').write_text(json.dumps({'project_name': 'From Project JSON'}), encoding='utf-8')
			self.assertEqual(identity.resolve_project_identity(proj_json_dir), {'Name': 'From Project JSON', 'Path': proj_json_dir.as_posix()})
			proj_bare = base / 'bare_proj'
			proj_bare.mkdir()
			self.assertEqual(identity.resolve_project_identity(proj_bare), {'Name': 'bare_proj', 'Path': proj_bare.as_posix()})
	def test_metadata_facade_exports_match_meta_package_symbols(self) -> None:
		from agent_tools import meta, metadata
		expected = (
			'_FRAC_SECONDS_RE', '_HARNESS_TOP_KEYS', '_LEADING_JSON_FENCE_RE', '_PROJECTS_DIR_CACHE', '_SYSTEM_DISPLAY', '_UUID_RE',
			'_ag_transcript_file', '_antigravity_project_dirs', '_conversation_label', '_extract_ag_transcript_info',
			'_extract_codex_transcript_info', '_extract_turn_steps_from_state', '_find_turn_state_for_conversation',
			'_format_step_value', '_is_harness_metadata_obj', '_is_temp_path', '_journal_step_paths',
			'_load_projects_dir_items', '_parse_antigravity_source_metadata', '_read_ag_summary_row',
			'_resolve_ag_model_and_effort', '_resolve_ag_paths_safe', '_resolve_codex_paths_safe',
			'_split_model_and_effort', '_system_display_name', 'build_github_issue_metadata',
			'build_journal_metadata', 'extract_leading_metadata_header', 'format_duration_timecode',
			'format_local_timestamp', 'parse_timestamp', 'posix_path', 'prepend_metadata_header',
			'render_metadata_header', 'resolve_project_identity', 'strip_leading_metadata_header',
		)
		for sym in expected:
			self.assertTrue(hasattr(metadata, sym), f'Missing facade export: {sym}')
			self.assertTrue(hasattr(meta, sym), f'Missing package export: {sym}')
			self.assertIs(getattr(metadata, sym), getattr(meta, sym), f'Symbol mismatch for {sym}')
	def test_transcripts_submodule_parses_antigravity_codex_and_turn_state(self) -> None:
		from agent_tools.meta import transcripts
		with tempfile.TemporaryDirectory() as tmp:
			base = Path(tmp).resolve()
			ag_log = base / 'ag.jsonl'
			ag_rows = [
				{'step_index': 0, 'type': 'USER_INPUT', 'created_at': '2026-11-23T10:00:00Z'},
				{'step_index': 1, 'type': 'PLANNER_RESPONSE', 'created_at': '2026-11-23T10:01:00Z', 'model': 'gemini-4-hydrogen-low'},
				{'step_index': 2, 'type': 'USER_INPUT', 'created_at': '2026-11-23T10:05:00Z'},
				{'step_index': 3, 'type': 'PLANNER_RESPONSE', 'created_at': '2026-11-23T10:06:00Z', 'model': 'gemini-4-neon-xhigh'},
			]
			ag_log.write_text('\n'.join((json.dumps(r) for r in ag_rows)) + '\n', encoding='utf-8')
			ag_info = transcripts._extract_ag_transcript_info(ag_log, start_step=2, final_step=3)
			self.assertEqual(ag_info, {'request_timestamp': '2026-11-23T10:05:00Z', 'response_timestamp': '2026-11-23T10:06:00Z', 'model': 'gemini-4-neon', 'effort': 'xhigh', 'turn_index': 2})
			cx_log = base / 'cx.jsonl'
			cx_rows = [
				{'timestamp': '2026-11-23T11:00:00Z', 'type': 'event_msg', 'payload': {'type': 'task_started', 'turn_id': 't1'}},
				{'timestamp': '2026-11-23T11:01:00Z', 'type': 'event_msg', 'payload': {'type': 'task_started', 'turn_id': 't2'}},
				{'timestamp': '2026-11-23T11:01:02Z', 'type': 'turn_context', 'payload': {'turn_id': 't2', 'model': 'gpt-6.1-sol', 'effort': 'max'}},
				{'timestamp': '2026-11-23T11:02:00Z', 'type': 'event_msg', 'payload': {'type': 'task_complete', 'turn_id': 't2'}},
			]
			cx_log.write_text('\n'.join((json.dumps(r) for r in cx_rows)) + '\n', encoding='utf-8')
			cx_info = transcripts._extract_codex_transcript_info(cx_log, turn_id='t2')
			self.assertEqual(cx_info, {'request_timestamp': '2026-11-23T11:01:00Z', 'response_timestamp': '2026-11-23T11:02:00Z', 'model': 'gpt-6.1-sol', 'effort': 'max', 'turn_index': 2})
			self.assertEqual(transcripts._parse_antigravity_source_metadata({'ANTIGRAVITY_SOURCE_METADATA': json.dumps({'tool': {'conversationId': 'ABC', 'stepIndex': 4}})}), ('abc', 4))
			self.assertEqual(transcripts._parse_antigravity_source_metadata({'ANTIGRAVITY_SOURCE_METADATA': '{bad'}), (None, None))
			tdir = base / 'turns'
			tdir.mkdir()
			cid = str(uuid.uuid4())
			(tdir / 'closed.json').write_text(json.dumps({'conversation_id': cid, 'status': 'delivered'}), encoding='utf-8')
			(tdir / 'open.json').write_text(json.dumps({'conversation_id': cid, 'status': 'open', 'reserved_journal_steps': [8]}), encoding='utf-8')
			(tdir / 'skip-ratchet-ok.json').write_text(json.dumps({'conversation_id': cid, 'status': 'open'}), encoding='utf-8')
			hit = transcripts._find_turn_state_for_conversation(tdir, cid)
			self.assertIsNotNone(hit)
			self.assertEqual(hit[0].name, 'open.json')
			self.assertEqual(transcripts._extract_turn_steps_from_state({'prepared': {'journal_steps': [4, 2]}, 'reserved_journal_steps': [9]}), [2, 4])
			self.assertEqual(transcripts._extract_turn_steps_from_state({'reserved_journal_steps': [9]}), [9])
if '__main__' == __name__:
	unittest.main()
