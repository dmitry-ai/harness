# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from pathlib import Path
from unittest.mock import MagicMock, patch
import json
import sys
import tempfile
import unittest
WT_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = WT_ROOT / 'scripts'
if str(SCRIPTS) not in sys.path:
	sys.path.insert(0, str(SCRIPTS))
# 2026-11-26 "Move verification gate subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/381
# @used-by :mod:`unittest`
class DfHarnessS11Wave2bMetaCovTests(unittest.TestCase):
	# @used-by :mod:`unittest`
	def test_blocks_clarifications_builders_problem_codex_and_turn_state(self) -> None:
		from Df.Harness.Meta.Blocks import Blocks
		from Df.Harness.Meta.Builders import Builders
		from Df.Harness.Meta.TranscriptReader import TranscriptReader
		with tempfile.TemporaryDirectory() as td:
			base = Path(td).resolve()
			root = base / 'proj'
			src_root = base / 'src_proj'
			turns_dir = root / '\ua616/data/turns'
			turns_dir.mkdir(parents=True)
			src_root.mkdir(parents=True)
			cid = '11111111-2222-4333-8444-555555555555'
			state_file = turns_dir / 'turn-1.json'
			state_obj = {'conversation_id': cid, 'status': 'open', 'key': 'turn-1', 'native_turn_id': 't1', 'native_start_step': 1, 'prepared': {'journal_steps': [2], 'group_file': str(root / 'grp.json')}}
			state_file.write_text(json.dumps(state_obj), encoding='utf-8')
			clar_turn = {'clarifications': [{'ask_step': 1, 'answer_step': 2, 'asked_at': '2026-11-26T10:00:00Z', 'answered_at': '2026-11-26T10:01:00Z', 'questions': ['Which mode?'], 'answers': [{'id': 'A1', 'text': 'Fast'}]}]}
			clars = Blocks.build_clarifications(clar_turn, state_file, None)
			self.assertEqual(1, len(clars))
			self.assertEqual('Fast', clars[0]['Answers'][0]['Text'])
			self.assertIsNotNone(Blocks.resolve_hook('resolve_project_identity', Builders, Builders.build_problem))
			found = TranscriptReader.find_turn_state_for_conversation(turns_dir, cid)
			self.assertIsNotNone(found)
			self.assertEqual([2], TranscriptReader.extract_turn_steps_from_state(found[1]))
			rollout = base / 'rollout.jsonl'
			rollout.write_text(json.dumps({'timestamp': '2026-11-26T10:00:00Z', 'type': 'turn_context', 'payload': {'turn_id': 't1', 'model': 'gpt-5', 'effort': 'high'}}) + '\n', encoding='utf-8')
			# 2026-11-28 "Reject invalid or foreign GitHub issues in problem-metadata builder and CLI": https://github.com/dmitry-ai/harness/issues/429
			ev_dir = root / '\ua616/KB/Evidence/GitHub/dmitry-ai__harness'
			ev_dir.mkdir(parents=True, exist_ok=True)
			(ev_dir / 'issue-381.json').write_text(json.dumps({'url': 'https://github.com/dmitry-ai/harness/issues/381', 'repo': 'dmitry-ai/harness', 'number': 381, 'state': 'open', 'title': 'Wave2b issue', 'body': 'Details.'}), encoding='utf-8')
			with patch('agent_tools.runtime._codex_home_conversation_trace', return_value=str(rollout)):
				prob = Builders.build_problem(issue_url='https://github.com/dmitry-ai/harness/issues/381', project_root=root, source_project_root=src_root, env={'CODEX_THREAD_ID': cid})
			self.assertEqual('https://github.com/dmitry-ai/harness/issues/381', prob['Issue'])
			self.assertIn('Source Project', prob)
			with self.assertRaises(ValueError):
				Builders.build_problem(issue_url=None, allow_no_issue=False)
	# @used-by :mod:`unittest`
	def test_metrics_summarizer_covers_adapters_executors_reviews_and_instances(self) -> None:
		from Df.Harness.Meta.MetricsSummarizer import MetricsSummarizer
		with tempfile.TemporaryDirectory() as td:
			root = Path(td).resolve()
			ev_dir = root / '\ua616/KB/Evidence'
			ev_dir.mkdir(parents=True)
			rev_file = ev_dir / 'rev1.json'
			rev_file.write_text(json.dumps({'result': 'approved', 'findings': [{'status': 'confirmed'}]}), encoding='utf-8')
			tr = root / 'trace.jsonl'
			tr.write_text(json.dumps({'step_index': 1, 'type': 'PLANNER_RESPONSE', 'model': 'm1'}) + '\n', encoding='utf-8')
			fake_adapter = MagicMock()
			fake_adapter.native_requests.return_value = {'ok': True}
			fake_adapter.native_review_proof.return_value = {'surface': 'antigravity'}
			fake_adapter.verify_native_proof.return_value = {'verified': True}
			fake_adapter.native_tool_trace.return_value = {'events': []}
			fake_adapter.native_executor_metadata.return_value = {'conversation_id': 'c1', 'parent_id': None, 'role': 'primary', 'surface': 'antigravity', 'requested': {}, 'observed': {}, 'verification': 'ok'}
			with patch('agent_tools.platforms.adapter', return_value=fake_adapter):
				self.assertEqual({'ok': True}, MetricsSummarizer.native_requests(root, 'c1', platform='antigravity', backend='b1', instance='i1'))
				self.assertEqual({'surface': 'antigravity'}, MetricsSummarizer.native_review_proof(root, 'p1', 'r1', platform='antigravity', backend='b1', instance='i1', wait_timeout=1.0, role='ARCH'))
				self.assertEqual({'verified': True}, MetricsSummarizer.verify_native_proof(root, {'surface': 'antigravity'}))
				self.assertEqual({'events': []}, MetricsSummarizer.native_tool_trace(root, {'surface': 'antigravity', 'conversation_id': 'c1'}))
				rec = MetricsSummarizer.record_executor_metadata(root, 'c1', platform='antigravity', backend='b1', instance='i1')
				self.assertIn('sha256', rec)
			state = {'questions': {'Q1': {'id': 'Q1', 'status': 'done', 'searches': [{'useful': True}]}}, 'reviews': [{'reviewer_id': 'r1', 'risk': 'low', 'report': '\ua616/KB/Evidence/rev1.json'}]}
			with patch('agent_tools.workflow.load', return_value=state), patch('agent_tools.workflow.stage_statuses', return_value={}):
				pm = MetricsSummarizer.project_metrics(root)
			self.assertEqual(1, len(pm['executors']))
			self.assertEqual(1, len(pm['reviews']))
			self.assertEqual(('antigravity', 'b1'), MetricsSummarizer.resolve_platform_and_backend('antigravity', 'b1', None))
			self.assertEqual([], MetricsSummarizer.wire_fields(b''))
			fake_inst = {'id': 'ag1', 'platform': 'antigravity', 'enabled': True, 'backend_dir': str(root), 'trace_file': str(tr), 'system_paths': {}}
			with patch('agent_tools.runtime.find_conversation_instance', return_value=[fake_inst]):
				inst_sum = MetricsSummarizer.summarize_instance('c1')
			self.assertEqual('ag1', inst_sum['instance']['id'])
if '__main__' == __name__:
	unittest.main()
