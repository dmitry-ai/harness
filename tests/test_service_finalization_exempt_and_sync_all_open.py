# 2026-11-25 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Exempt service finalization calls from EXEC-2-TDD-GATE and add journal-sync --all-open":
# https://github.com/dmitry-ai/harness/issues/256
from __future__ import annotations
from pathlib import Path
from unittest.mock import patch
import argparse
import subprocess
import sys
import tempfile
import time
import unittest
WT_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = WT_ROOT / 'scripts'
TESTS = WT_ROOT / 'tests'
for _p in (str(SCRIPTS), str(TESTS)):
	if _p not in sys.path:
		sys.path.insert(0, _p)
from agent_tools import completion, journal, tdd_gate
from test_stop_emergency_capture_and_foreign_sync import _reserve_foreign, _seed_ag_conversation
import check_rules_and_server_gate as rg
def _git(repo: Path, *args: str) -> None:
	subprocess.run(['git', *args], cwd=repo, check=True, capture_output=True, stdin=subprocess.DEVNULL, timeout=30)
def _init_repo(repo: Path) -> None:
	repo.mkdir(parents=True, exist_ok=True)
	_git(repo, 'init')
	_git(repo, 'config', 'user.email', 'test@example.com')
	_git(repo, 'config', 'user.name', 'Test')
	(repo / 'app.py').write_text('x = 1\n', encoding='utf-8')
	_git(repo, 'add', 'app.py')
	_git(repo, 'commit', '-m', 'init')
def _tool_payload(cwd: Path, name: str, args: dict) -> dict:
	return {'cwd': str(cwd), 'toolCall': {'name': name, 'args': args}}
class ServiceFinalizationAndSyncAllOpenTests(unittest.TestCase):
	def test_journal_sync_all_open_reconciles_idle_turns_and_honors_adopt_conflict(self) -> None:
		with tempfile.TemporaryDirectory() as td:
			base = Path(td).resolve()
			proj, backend = (base / 'proj', base / 'ag_backend')
			(proj / '\ua66e').mkdir(parents=True)
			(proj / '\ua616/data/turns').mkdir(parents=True)
			cid_a, cid_b, cid_c, cid_d = ('11111111-1111-1111-1111-111111111111', '22222222-2222-2222-2222-222222222222', '33333333-3333-3333-3333-333333333333', '44444444-4444-4444-4444-444444444444')
			beg_a = _reserve_foreign(backend, proj, cid_a, 'Idle turn A', None)
			beg_b = _reserve_foreign(backend, proj, cid_b, 'Idle turn B', None)
			beg_c = _reserve_foreign(backend, proj, cid_c, 'Conflict turn C', None, patch_state={'status': 'conflict'})
			beg_d = _reserve_foreign(backend, proj, cid_d, 'Running turn D', None)
			_seed_ag_conversation(backend, proj, cid_a, 'Idle turn A', 'Reply A.')
			_seed_ag_conversation(backend, proj, cid_b, 'Idle turn B', 'Reply B.')
			_seed_ag_conversation(backend, proj, cid_c, 'Conflict turn C', 'Reply C.')
			parser = argparse.ArgumentParser()
			completion.add_parser_arguments(parser, 'journal-sync')
			parsed = parser.parse_args([str(proj), '--all-open'])
			self.assertTrue(parsed.all_open)
			parsed.command = 'journal-sync'
			res1 = completion.execute(parsed)
			self.assertTrue(res1['valid'], res1)
			self.assertTrue(res1['all_open'])
			self.assertEqual((2, 2), (res1['synced_count'], res1['skipped_count']))
			self.assertEqual(['1.md', '2.md'], sorted((p.name for p in (proj / '\ua66e/\u227a/1\u201320').glob('*.md'))))
			res_map1 = journal.iter_turn_reservations(proj / '\ua66e')
			self.assertNotIn(beg_a['turn_key'], res_map1)
			self.assertNotIn(beg_b['turn_key'], res_map1)
			self.assertIn(beg_c['turn_key'], res_map1)
			self.assertIn(beg_d['turn_key'], res_map1)
			res2 = completion.sync(proj, None, adopt_conflict=True, all_open=True)
			self.assertTrue(res2['valid'], res2)
			self.assertEqual((1, 1), (res2['synced_count'], res2['skipped_count']))
			self.assertEqual('conversation_not_idle', res2['skipped'][0]['reason'])
			self.assertEqual(['1.md', '2.md', '3.md'], sorted((p.name for p in (proj / '\ua66e/\u227a/1\u201320').glob('*.md'))))
			res_map2 = journal.iter_turn_reservations(proj / '\ua66e')
			self.assertNotIn(beg_c['turn_key'], res_map2)
			self.assertIn(beg_d['turn_key'], res_map2)
	def test_service_finalization_passes_under_blocked_tdd_and_shell_bypass_is_denied(self) -> None:
		with tempfile.TemporaryDirectory() as td:
			repo = Path(td).resolve() / 'repo'
			_init_repo(repo)
			cases = [
				('write_file', {'Path': str(repo / '\ua616/data/scratch/answer-abc123.md'), 'Content': 'Blocked report.\n'}),
				('write_file', {'Path': str(repo / '\ua616/data/continuation.md'), 'Content': 'Next step.\n'}),
				('run_command', {'CommandLine': 'python "scripts/harness.py" answer-prepare "." --response-file "\ua616/data/scratch/answer-abc123.md" --blocked-report'}),
				('run_command', {'CommandLine': 'python "scripts/harness.py" answer-check "." --response-file "\ua616/data/scratch/answer-abc123.md"'}),
				('run_command', {'CommandLine': 'python "scripts/harness.py" journal-sync "." --all-open'}),
				('run_command', {'CommandLine': 'python "scripts/df_github_issue.py" create --repo dmitry-ai/harness --title "Bug" --body-file "\ua616/data/scratch/body.md"'}),
			]
			with patch.object(tdd_gate, 'evaluate_pre_tool_use_tdd', side_effect=AssertionError('TDD artificially blocked')):
				for name, args in cases:
					t0 = time.perf_counter()
					dec = rg._evaluate_payload(_tool_payload(repo, name, args))
					dt = time.perf_counter() - t0
					self.assertEqual('allow', dec['decision'], (name, args, dec))
					self.assertLess(dt, 0.2, (name, dt))
			bypass_cmd = 'python "scripts/harness.py" answer-check "." --response-file "a.md"; Set-Content -Path "app.py" -Value "x=2"'
			dec_bypass = rg._evaluate_payload(_tool_payload(repo, 'run_command', {'CommandLine': bypass_cmd}))
			self.assertEqual('deny', dec_bypass['decision'], dec_bypass)
			self.assertIn('TDD-RED-GATE', dec_bypass['reason'])
			dec_trav = rg._evaluate_payload(_tool_payload(repo, 'write_file', {'Path': str(repo / '\ua616/data/scratch/../../../app.py'), 'Content': 'x = 2\n'}))
			self.assertEqual('deny', dec_trav['decision'], dec_trav)
			self.assertIn('TDD-RED-GATE', dec_trav['reason'])
if '__main__' == __name__:
	unittest.main()