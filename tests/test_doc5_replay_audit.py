# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Enforce historical feature-turn regression audit before worktree landing":
# https://github.com/dmitry-ai/harness/issues/373
from __future__ import annotations
from pathlib import Path
from unittest.mock import patch
import json
import subprocess
import sys
import tempfile
import unittest
WT_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = WT_ROOT / 'scripts'
TESTS = WT_ROOT / 'tests'
CORPUS_DIR = WT_ROOT / 'tests/fixtures/feature_turns'
for p in (SCRIPTS, TESTS):
	if str(p) not in sys.path:
		sys.path.insert(0, str(p))
# @used-by :func:`_init_gate_demo_repo()`
# @used-by :meth:`Doc5ReplayAuditTests.test_worktree_land_enforces_answer_gate_corpus_before_merge()`
def _git(repo: Path, *args: str) -> str:
	proc = subprocess.run(['git', '--no-optional-locks', '-C', str(repo), *args], stdin=subprocess.DEVNULL, capture_output=True, text=True, encoding='utf-8', check=True, timeout=30)
	return (proc.stdout or '').strip()
# @used-by :meth:`Doc5ReplayAuditTests.test_worktree_land_enforces_answer_gate_corpus_before_merge()`
def _init_gate_demo_repo(root: Path) -> Path:
	repo = root / 'repo'
	(repo / 'scripts/agent_tools').mkdir(parents=True)
	(repo / 'tests/fixtures/feature_turns').mkdir(parents=True)
	_git(repo, 'init', '-b', 'main')
	_git(repo, 'config', 'user.email', 'test@example.com')
	_git(repo, 'config', 'user.name', 'Test')
	_git(repo, 'remote', 'add', 'origin', 'https://github.com/owner/demo.git')
	(repo / '.gitignore').write_text('__pycache__/\n*.pyc\n', encoding='utf-8')
	(repo / 'scripts/agent_tools/doc5_context.py').write_text('def marker() -> int:\n\treturn 1\n', encoding='utf-8')
	(repo / 'tests/test_ok.py').write_text('import sys, unittest\nfrom pathlib import Path\nsys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))\nfrom agent_tools import doc5_context\nclass T(unittest.TestCase):\n\tdef test_ok(self) -> None:\n\t\tself.assertEqual(1, doc5_context.marker())\n', encoding='utf-8')
	(repo / 'tests/fixtures/feature_turns/01_demo.json').write_text('{}\n', encoding='utf-8')
	_git(repo, 'add', '.')
	_git(repo, 'commit', '--no-verify', '-m', 'init')
	return repo
# @used-by :mod:`unittest`
class Doc5ReplayAuditTests(unittest.TestCase):
	# @used-by :mod:`unittest`
	def test_tracked_feature_turn_corpus_has_zero_false_positives_and_catches_regression(self) -> None:
		from agent_tools import doc5_context, doc5_replay_audit
		self.assertTrue(CORPUS_DIR.is_dir(), f'Missing corpus dir: {CORPUS_DIR}')
		res = doc5_replay_audit.audit_feature_turn_corpus(CORPUS_DIR)
		self.assertTrue(res['valid'], res)
		self.assertEqual(3, res['checked'])
		self.assertEqual([], res['false_positives'])
		self.assertEqual([], res['false_negatives'])
		with patch.object(doc5_context, 'turn_requires_doc5_problem_analysis', return_value=True):
			bad = doc5_replay_audit.audit_feature_turn_corpus(CORPUS_DIR)
		self.assertFalse(bad['valid'], bad)
		self.assertEqual(2, len(bad['false_positives']), bad)
		sub_res = doc5_replay_audit._run_worktree_corpus_subprocess(WT_ROOT, CORPUS_DIR)
		self.assertTrue(sub_res['valid'], sub_res)
		self.assertEqual(3, sub_res['checked'])
	# @used-by :mod:`unittest`
	def test_audit_local_saved_turns_flags_false_positives_and_passes_clean_history(self) -> None:
		from agent_tools import doc5_context, doc5_replay_audit
		from test_stop_emergency_capture_and_foreign_sync import _seed_ag_conversation
		with tempfile.TemporaryDirectory() as td:
			base = Path(td).resolve()
			proj, backend = (base / 'proj', base / 'ag_backend')
			res_dir = proj / '\ua66e/\u227a/1\u201320'
			res_dir.mkdir(parents=True)
			(proj / '\ua616/data/turns').mkdir(parents=True)
			cid = '99999999-1111-2222-3333-444444444444'
			tx = _seed_ag_conversation(backend, proj, cid, 'Implement feature', 'Completed feature cleanly.  \n')
			rows = [
				{'step_index': 0, 'type': 'USER_INPUT', 'content': 'Implement feature'},
				{'step_index': 2, 'type': 'PLANNER_RESPONSE', 'tool_calls': [{'name': 'run_command', 'args': {'CommandLine': 'python harness.py turn-begin "C:/work/proj" --platform antigravity'}}]},
				{'step_index': 3, 'type': 'GENERIC', 'content': 'Command exited with code 0.\n\nCommand output:\n{"ok": true, "foreign_reconciliation": [{"result": {"valid": false}}]}'},
				{'step_index': 5, 'type': 'PLANNER_RESPONSE', 'content': 'Completed feature cleanly.  \n', 'tool_calls': []},
			]
			tx.write_text(''.join((json.dumps(r, ensure_ascii=False) + '\n' for r in rows)), encoding='utf-8')
			rf = res_dir / '1.md'
			rf.write_text('Completed feature cleanly.  \n', encoding='utf-8')
			turn_key = 'savedfeatkey01'
			state = {'key': turn_key, 'status': 'delivered', 'platform': 'antigravity', 'conversation_id': cid, 'native_backend': str(backend), 'native_turn_id': f'ag-{cid}-0', 'prepared': {'response_file': str(rf), 'journal_steps': [1]}}
			(proj / '\ua616/data/turns' / f'{turn_key}.json').write_text(json.dumps(state), encoding='utf-8')
			clean = doc5_replay_audit.audit_local_saved_turns(proj, limit=10)
			self.assertTrue(clean['valid'], clean)
			self.assertEqual(1, clean['checked'])
			with patch.object(doc5_context, 'turn_requires_doc5_problem_analysis', return_value=True):
				flagged = doc5_replay_audit.audit_local_saved_turns(proj, limit=10)
			self.assertFalse(flagged['valid'], flagged)
			self.assertEqual([turn_key], flagged['false_positives'])
	# @used-by :mod:`unittest`
	def test_worktree_land_enforces_answer_gate_corpus_before_merge(self) -> None:
		from agent_tools import doc5_replay_audit
		from agent_tools.worktree_flow import worktree_begin, worktree_cleanup, worktree_land
		with tempfile.TemporaryDirectory() as td:
			root = Path(td).resolve()
			repo = _init_gate_demo_repo(root)
			wt = Path(worktree_begin(repo, 'gate-audit', worktrees_dir=root / 'wts')['worktree'])
			(wt / 'notes.txt').write_text('non-gate\n', encoding='utf-8')
			_git(wt, 'add', 'notes.txt')
			_git(wt, 'commit', '--no-verify', '-m', 'touch non-gate')
			skip_res = doc5_replay_audit.verify_worktree_answer_gate_corpus(wt, 'main')
			self.assertTrue(skip_res['valid'], skip_res)
			self.assertTrue(skip_res['skipped'], skip_res)
			(wt / 'scripts/agent_tools/doc5_context.py').write_text('def marker() -> int:\n\treturn 1 + 0\n', encoding='utf-8')
			_git(wt, 'add', 'scripts/agent_tools/doc5_context.py')
			_git(wt, 'commit', '--no-verify', '-m', 'touch doc5 gate')
			fail_payload = {'valid': False, 'skipped': False, 'checked': 2, 'false_positives': ['01_demo.json'], 'false_negatives': []}
			with patch.object(doc5_replay_audit, '_run_worktree_corpus_subprocess', return_value=fail_payload):
				blocked = worktree_land(wt, run_tests=True, remove=False, leases_dir=root / 'leases', promote_snapshot=False)
			self.assertFalse(blocked['valid'], blocked)
			self.assertEqual('answer_gate_corpus', blocked['stage'])
			self.assertIn('01_demo.json', blocked['error'])
			ok_payload = {'valid': True, 'skipped': False, 'checked': 2, 'false_positives': [], 'false_negatives': []}
			with patch.object(doc5_replay_audit, '_run_worktree_corpus_subprocess', return_value=ok_payload):
				passed = worktree_land(wt, run_tests=True, remove=True, leases_dir=root / 'leases', promote_snapshot=False)
			self.assertTrue(passed['valid'], passed)
			self.assertTrue(passed['landed'])
			if wt.exists():
				worktree_cleanup(repo, wt, force=True)
if '__main__' == __name__:
	unittest.main()
