# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# 2026-11-26 "Enforce mixed executable and bulk comment-only commit audit and decomposition rules": https://github.com/dmitry-ai/harness/issues/362
from __future__ import annotations
from pathlib import Path
from unittest.mock import patch
import contextlib
import io
import json
import subprocess
import sys
import tempfile
import unittest
WT_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = WT_ROOT / 'scripts'
if str(SCRIPTS) not in sys.path:
	sys.path.insert(0, str(SCRIPTS))
_BULK_COUNT = 20
_ISSUE_URL = 'https://github.com/owner/demo/issues/7'
_NO_WINDOW = getattr(subprocess, 'CREATE_NO_WINDOW', 0)
# @used-by :func:`_init_bulk_repo()`
# @used-by :func:`_seed_mixed_changes()`
# @used-by :meth:`MixedCommitAuditTests.test_pre_commit_emits_non_blocking_mixed_warning_to_stderr()`
# @used-by :meth:`MixedCommitAuditTests.test_worktree_land_emits_mixed_commit_warning_and_clean_commit_has_none()`
def _git(repo: Path, *args: str) -> str:
	proc = subprocess.run(['git', '--no-optional-locks', '-C', str(repo), *args], stdin=subprocess.DEVNULL, capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=30, check=True, creationflags=_NO_WINDOW)
	return (proc.stdout or '').strip()
# @used-by :meth:`MixedCommitAuditTests.test_pre_commit_emits_non_blocking_mixed_warning_to_stderr()`
# @used-by :meth:`MixedCommitAuditTests.test_turn_issue_lifecycle_auditor_emits_soft_mixed_commit_warning()`
# @used-by :meth:`MixedCommitAuditTests.test_worktree_land_emits_mixed_commit_warning_and_clean_commit_has_none()`
def _init_bulk_repo(repo: Path) -> list[str]:
	(repo / 'pkg').mkdir(parents=True, exist_ok=True)
	(repo / 'tests').mkdir(parents=True, exist_ok=True)
	_git(repo, 'init', '-b', 'main')
	_git(repo, 'config', 'user.email', 'test@example.com')
	_git(repo, 'config', 'user.name', 'Test')
	_git(repo, 'remote', 'add', 'origin', 'https://github.com/owner/demo.git')
	(repo / '.git/info/exclude').write_text('\ua616/\n', encoding='utf-8')
	(repo / 'pkg/__init__.py').write_text('# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk\n', encoding='utf-8')
	(repo / 'pkg/app.py').write_text('# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk\n# header\nVAL = 1\n', encoding='utf-8')
	(repo / 'tests/test_app.py').write_text('# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk\nimport unittest\nclass AppT(unittest.TestCase):\n\t# @used-by :mod:`unittest`\n\tdef test_ok(self) -> None:\n\t\tself.assertEqual(1, 1)\n', encoding='utf-8')
	comment_rels: list[str] = []
	for idx in range(_BULK_COUNT):
		rel = f'pkg/c_{idx:02d}.py'
		(repo / rel).write_text(f'# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk\n# old {idx}\nN = {idx}\n', encoding='utf-8')
		comment_rels.append(rel)
	_git(repo, 'add', '.')
	_git(repo, 'commit', '--no-verify', '-m', 'init')
	return comment_rels
# @used-by :meth:`MixedCommitAuditTests.test_pre_commit_emits_non_blocking_mixed_warning_to_stderr()`
# @used-by :meth:`MixedCommitAuditTests.test_turn_issue_lifecycle_auditor_emits_soft_mixed_commit_warning()`
# @used-by :meth:`MixedCommitAuditTests.test_worktree_land_emits_mixed_commit_warning_and_clean_commit_has_none()`
def _seed_mixed_changes(repo: Path, comment_rels: list[str], *, include_test: bool=False, commit_msg: str | None=None) -> list[str]:
	touched: list[str] = []
	for idx, rel in enumerate(comment_rels):
		(repo / rel).write_text(f'# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk\n# new {idx}\nN = {idx}\n', encoding='utf-8')
		touched.append(rel)
	(repo / 'pkg/app.py').write_text(f'# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk\n# header\n# 2026-11-26 "Update val": {_ISSUE_URL}\nVAL = 2\n', encoding='utf-8')
	touched.append('pkg/app.py')
	if include_test:
		(repo / 'tests/test_app.py').write_text(f'# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk\nimport unittest\nclass AppT(unittest.TestCase):\n\t# 2026-11-26 "Update val": {_ISSUE_URL}\n\t# @used-by :mod:`unittest`\n\tdef test_ok(self) -> None:\n\t\tself.assertEqual(1, 1)\n\t\tself.assertEqual(2, 2)\n', encoding='utf-8')
		touched.append('tests/test_app.py')
	_git(repo, 'add', *touched)
	if None is not commit_msg:
		_git(repo, 'commit', '--no-verify', '-m', commit_msg)
	return touched
class MixedCommitAuditTests(unittest.TestCase):
	# @used-by :mod:`unittest`
	def test_detect_mixed_commit_warning_threshold_and_exports(self) -> None:
		from agent_tools import tdd, tdd_gate
		from agent_tools.tdd.diff_executability import MIXED_COMMIT_COMMENT_THRESHOLD, check_staged_mixed_commit_warning, check_touched_mixed_commit_warning, detect_mixed_commit_warning
		self.assertEqual(20, MIXED_COMMIT_COMMENT_THRESHOLD)
		self.assertIs(MIXED_COMMIT_COMMENT_THRESHOLD, tdd.MIXED_COMMIT_COMMENT_THRESHOLD)
		self.assertIs(MIXED_COMMIT_COMMENT_THRESHOLD, tdd_gate.MIXED_COMMIT_COMMENT_THRESHOLD)
		self.assertIs(detect_mixed_commit_warning, tdd.detect_mixed_commit_warning)
		self.assertIs(detect_mixed_commit_warning, tdd_gate.detect_mixed_commit_warning)
		self.assertIs(check_staged_mixed_commit_warning, tdd.check_staged_mixed_commit_warning)
		self.assertIs(check_touched_mixed_commit_warning, tdd.check_touched_mixed_commit_warning)
		hit = detect_mixed_commit_warning({'category_counts': {'comment_only': 20, 'executable': 1}, 'executable_files': ['pkg/app.py'], 'non_executable_files': [f'pkg/c_{i:02d}.py' for i in range(20)]})
		self.assertIsNotNone(hit)
		self.assertEqual('MIXED_BULK_COMMENT_AND_EXECUTABLE_COMMIT', hit['code'])
		self.assertEqual(20, hit['comment_only_file_count'])
		self.assertEqual(1, hit['executable_file_count'])
		self.assertEqual(20, hit['threshold'])
		self.assertTrue(bool(str(hit.get('message') or '').strip()))
		self.assertIsNone(detect_mixed_commit_warning({'category_counts': {'comment_only': 25}, 'executable_files': []}))
		self.assertIsNone(detect_mixed_commit_warning({'category_counts': {'executable': 25}, 'executable_files': [f'pkg/e_{i}.py' for i in range(25)]}))
		self.assertIsNone(detect_mixed_commit_warning({'category_counts': {'comment_only': 19, 'executable': 1}, 'executable_files': ['pkg/app.py']}))
	# @used-by :mod:`unittest`
	def test_df_github_issue_skill_documents_decomposition_and_passes_lint(self) -> None:
		from agent_tools import links
		import check_markdown_slop
		skill_p = WT_ROOT / 'skills/df-github-issue/SKILL.md'
		text = skill_p.read_text(encoding='utf-8')
		self.assertEqual([], links.validate_file(skill_p, local_anchors=True, readable_links=True))
		self.assertEqual([], check_markdown_slop.markdown_slop_issues(text))
		for tok in ('@override', '@used-by', 'JSDoc', 'Javadoc', '20', 'worktree_land', 'pre-commit', 'TurnIssueLifecycleAuditor'):
			self.assertIn(tok, text, f'Missing {tok!r} in skills/df-github-issue/SKILL.md')
	# @used-by :mod:`unittest`
	def test_pre_commit_emits_non_blocking_mixed_warning_to_stderr(self) -> None:
		from agent_tools import git_gate
		from agent_tools.staged_gates import verify_staged_extra_gates
		with tempfile.TemporaryDirectory() as td:
			repo = Path(td).resolve() / 'repo'
			comment_rels = _init_bulk_repo(repo)
			staged = _seed_mixed_changes(repo, comment_rels, include_test=True, commit_msg=None)
			buf_extra = io.StringIO()
			with contextlib.redirect_stderr(buf_extra):
				errs = verify_staged_extra_gates(repo, staged, use_index=True)
			self.assertEqual([], errs)
			self.assertIn('WARNING:', buf_extra.getvalue())
			self.assertIn('comment-only', buf_extra.getvalue().lower())
			buf_hook = io.StringIO()
			with contextlib.redirect_stderr(buf_hook):
				rc = git_gate.run_git_hook('pre-commit', cwd=repo, agent_context=True)
			self.assertEqual(0, rc, buf_hook.getvalue())
			self.assertIn('WARNING:', buf_hook.getvalue())
			self.assertIn('comment-only', buf_hook.getvalue().lower())
			_git(repo, 'reset', 'HEAD', '--', *comment_rels)
			buf_small = io.StringIO()
			with contextlib.redirect_stderr(buf_small):
				self.assertEqual([], verify_staged_extra_gates(repo, ['pkg/app.py', 'tests/test_app.py'], use_index=True))
			self.assertEqual('', buf_small.getvalue())
	# @used-by :mod:`unittest`
	def test_turn_issue_lifecycle_auditor_emits_soft_mixed_commit_warning(self) -> None:
		from agent_tools.issues import auditor as aud_mod
		with tempfile.TemporaryDirectory() as td:
			root = Path(td).resolve() / 'proj'
			repo = root / '\u2c0f/\u227b/\u2655/\u26ef'
			ev_dir = root / '\ua616/KB/Evidence/GitHub/owner__demo'
			ev_dir.mkdir(parents=True)
			(ev_dir / 'issue-7.json').write_text(json.dumps({'number': 7, 'state': 'closed', 'title': 'Update val', 'body': 'Body.'}), encoding='utf-8')
			comment_rels = _init_bulk_repo(repo)
			touched = _seed_mixed_changes(repo, comment_rels, include_test=False, commit_msg=_ISSUE_URL)
			turn_mixed = {'touched_files': [str(repo / rel) for rel in touched], 'issue_actions': []}
			with patch.object(aud_mod, 'verify_repo_issue_ready_for_close', return_value={'verified': True, 'violations': []}):
				res_mixed = aud_mod.TurnIssueLifecycleAuditor(root, turn_mixed, None).audit()
			self.assertTrue(res_mixed['verified'], res_mixed)
			self.assertEqual([], res_mixed['violations'])
			self.assertEqual(1, len(res_mixed['warnings']), res_mixed)
			self.assertIn('comment-only', res_mixed['warnings'][0].lower())
			turn_clean = {'touched_files': [str(repo / 'pkg/app.py')], 'issue_actions': []}
			with patch.object(aud_mod, 'verify_repo_issue_ready_for_close', return_value={'verified': True, 'violations': []}):
				res_clean = aud_mod.TurnIssueLifecycleAuditor(root, turn_clean, None).audit()
			self.assertTrue(res_clean['verified'], res_clean)
			self.assertEqual([], res_clean['warnings'])
	# @used-by :mod:`unittest`
	def test_worktree_land_emits_mixed_commit_warning_and_clean_commit_has_none(self) -> None:
		from agent_tools.worktree_flow import worktree_begin, worktree_land
		with tempfile.TemporaryDirectory() as td:
			root = Path(td).resolve()
			repo = root / 'repo'
			comment_rels = _init_bulk_repo(repo)
			wt_base, leases = (root / 'wts', root / 'leases')
			wt_mix = Path(worktree_begin(repo, 'mixed-land', worktrees_dir=wt_base)['worktree'])
			_seed_mixed_changes(wt_mix, comment_rels, include_test=False, commit_msg=_ISSUE_URL)
			res_mix = worktree_land(wt_mix, run_tests=True, remove=True, owner='mix', leases_dir=leases, promote_snapshot=False)
			self.assertTrue(res_mix['valid'] and res_mix['landed'], res_mix)
			self.assertEqual(1, res_mix['test_runs'])
			warn = res_mix['mixed_commit_warning']
			self.assertIsNotNone(warn)
			self.assertEqual('MIXED_BULK_COMMENT_AND_EXECUTABLE_COMMIT', warn['code'])
			self.assertEqual(20, warn['comment_only_file_count'])
			self.assertEqual(1, warn['executable_file_count'])
			self.assertEqual([warn['message']], res_mix['warnings'])
			self.assertEqual(['pkg/app.py'], res_mix['executable_files'])
			self.assertEqual(1, res_mix['executable_file_count'])
			self.assertEqual(20, res_mix['non_executable_file_count'])
			self.assertEqual(20, len(res_mix['non_executable_files']))
			wt_cmt = Path(worktree_begin(repo, 'pure-cmt', worktrees_dir=wt_base)['worktree'])
			(wt_cmt / 'pkg/c_00.py').write_text('# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk\n# pure cmt\nN = 0\n', encoding='utf-8')
			_git(wt_cmt, 'add', 'pkg/c_00.py')
			_git(wt_cmt, 'commit', '--no-verify', '-m', 'pure comment')
			res_cmt = worktree_land(wt_cmt, run_tests=True, remove=True, owner='cmt', leases_dir=leases, promote_snapshot=False)
			self.assertTrue(res_cmt['valid'] and res_cmt['landed'], res_cmt)
			self.assertIsNone(res_cmt['mixed_commit_warning'])
			self.assertEqual([], res_cmt['warnings'])
if '__main__' == __name__:
	unittest.main()
