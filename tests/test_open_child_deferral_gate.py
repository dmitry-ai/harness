# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Block active-turn open deferred child issues in lifecycle auditor":
# https://github.com/dmitry-ai/harness/issues/367
from __future__ import annotations
from pathlib import Path
import json
import subprocess
import sys
import tempfile
import unittest
WT_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = WT_ROOT / 'scripts'
if str(SCRIPTS) not in sys.path:
	sys.path.insert(0, str(SCRIPTS))
from agent_tools import issue_lifecycle, repo_tags
from agent_tools.gates import run_answer_gates
SLUG = 'dmitry-ai/antigravity-addons'
# @used-by :meth:`OpenChildDeferralGateTests.test_open_deferred_child_blocks_lifecycle_and_answer_gates()`
def _gate_ctx(lifecycle_chk: dict, *, blocked_report: bool=False) -> dict:
	return {'role': 'primary', 'blocked_report': blocked_report, 'doc4_errs': [], 'link_errs': [], 'prob_errs': [], 'source_errs': [], 'lang_errs': [], 'exec5_chk': {'verified': True, 'violations': []}, 'http_chk': {'verified': True, 'violations': []}, 'comp_chk': {'verified': True}, 'evicted_cited': [], 'del_chk': {'verified': True}, 'issue_first_chk': {'verified': True, 'violations': []}, 'lifecycle_chk': lifecycle_chk, 'tdd_chk': {'verified': True, 'violations': []}, 'wf_errs': []}
# @used-by :func:`_init_repo()`
def _git(repo: Path, *args: str) -> None:
	subprocess.run(['git', *args], cwd=repo, check=True, capture_output=True, stdin=subprocess.DEVNULL, timeout=30)
# @used-by :meth:`OpenChildDeferralGateTests.test_open_deferred_child_blocks_lifecycle_and_answer_gates()`
# @used-by :meth:`OpenChildDeferralGateTests.test_unparented_open_bug_and_prior_turn_open_child_remain_allowed()`
def _init_repo(base: Path) -> tuple[Path, Path, Path, Path]:
	bare = base / 'remote.git'
	subprocess.run(['git', 'init', '--bare', str(bare)], check=True, capture_output=True, stdin=subprocess.DEVNULL, timeout=30)
	project = base / 'proj'
	(project / '_/\ua616').mkdir(parents=True, exist_ok=True)
	code_repo = project / 'code'
	code_repo.mkdir(parents=True, exist_ok=True)
	_git(code_repo, 'init')
	cfg = code_repo / '.git/config'
	cfg.write_text(cfg.read_text(encoding='utf-8') + f'[user]\n\temail = test@example.com\n\tname = Test\n[remote "origin"]\n\turl = https://github.com/{SLUG}.git\n\tpushurl = {bare.as_posix()}\n\tfetch = +refs/heads/*:refs/remotes/origin/*\n[url "{bare.as_posix()}"]\n\tinsteadOf = https://github.com/{SLUG}.git\n', encoding='utf-8')
	url_c1 = f'https://github.com/{SLUG}/issues/921'
	f_c1 = code_repo / 'phase1.py'
	f_c1.write_text(f'# {url_c1}\nx = 1\n', encoding='utf-8')
	_git(code_repo, 'add', 'phase1.py')
	_git(code_repo, 'commit', '-m', url_c1)
	repo_tags.ensure_commit_tag(code_repo, push=False)
	_git(code_repo, 'branch', '-M', 'main')
	_git(code_repo, 'push', '-u', 'origin', 'main', '--tags')
	safe_slug = SLUG.replace('/', '__')
	ev_dir = project / f'_/\ua616/KB/Evidence/GitHub/{safe_slug}'
	ev_dir.mkdir(parents=True, exist_ok=True)
	return (project, code_repo, f_c1, ev_dir)
# @used-by :meth:`OpenChildDeferralGateTests.test_open_deferred_child_blocks_lifecycle_and_answer_gates()`
# @used-by :meth:`OpenChildDeferralGateTests.test_unparented_open_bug_and_prior_turn_open_child_remain_allowed()`
def _write_issue(ev_dir: Path, num: int, state: str, title: str, *, parent: int | None=None) -> str:
	url = f'https://github.com/{SLUG}/issues/{num}'
	body = f'Parent: #{parent}\n\n## Scope\nDetails.\n' if None is not parent else '## Problem\nDetails.\n'
	rec = {'url': url, 'number': num, 'state': state, 'title': title, 'body': body}
	if None is not parent:
		rec['parent_number'] = parent
	(ev_dir / f'issue-{num}.json').write_text(json.dumps(rec), encoding='utf-8')
	return url
# 2026-11-26
# "Block active-turn open deferred child issues in lifecycle auditor":
# https://github.com/dmitry-ai/harness/issues/367
class OpenChildDeferralGateTests(unittest.TestCase):
	# @used-by :mod:`unittest`
	def test_open_deferred_child_blocks_lifecycle_and_answer_gates(self) -> None:
		with tempfile.TemporaryDirectory() as tmp:
			project, _, f_c1, ev_dir = _init_repo(Path(tmp))
			url_p = _write_issue(ev_dir, 920, 'open', 'Parent implementation task')
			url_c1 = _write_issue(ev_dir, 921, 'closed', 'Phase 1 subtask', parent=920)
			url_c2 = _write_issue(ev_dir, 922, 'open', 'Deferred phase 2 subtask', parent=920)
			turn = {
				'touched_files': [str(f_c1)],
				'issue_actions': [
					{'action': 'create', 'repo': SLUG, 'number': 920, 'url': url_p, 'state': 'open'},
					{'action': 'create', 'repo': SLUG, 'number': 921, 'url': url_c1, 'state': 'open', 'parent_number': 920},
					{'action': 'close', 'repo': SLUG, 'number': 921, 'url': url_c1, 'state': 'closed', 'parent_number': 920},
					{'action': 'create', 'repo': SLUG, 'number': 922, 'url': url_c2, 'state': 'open', 'parent_number': 920},
				],
			}
			res = issue_lifecycle.code_and_issue_lifecycle_status(project, turn, turn_state={})
			self.assertFalse(res['verified'], res)
			self.assertTrue(any(('issues/922' in v and 'deferred child' in v.lower() for v in res['violations'])), res['violations'])
			issues_norm, checks_norm = run_answer_gates(_gate_ctx(res, blocked_report=False))
			self.assertFalse(checks_norm['code_lifecycle'])
			self.assertTrue(any(('code_lifecycle' == it['gate_id'] for it in issues_norm)), issues_norm)
			issues_blk, _ = run_answer_gates(_gate_ctx(res, blocked_report=True))
			self.assertEqual([], issues_blk)
	# @used-by :mod:`unittest`
	def test_unparented_open_bug_and_prior_turn_open_child_remain_allowed(self) -> None:
		with tempfile.TemporaryDirectory() as tmp:
			project, _, f_c1, ev_dir = _init_repo(Path(tmp))
			_write_issue(ev_dir, 920, 'open', 'Parent implementation task')
			url_c1 = _write_issue(ev_dir, 921, 'closed', 'Phase 1 subtask', parent=920)
			_write_issue(ev_dir, 922, 'open', 'Pre-existing child from prior turn', parent=920)
			url_bug = _write_issue(ev_dir, 939, 'open', 'Unrelated discovered bug')
			turn = {
				'touched_files': [str(f_c1)],
				'issue_actions': [
					{'action': 'create', 'repo': SLUG, 'number': 921, 'url': url_c1, 'state': 'open', 'parent_number': 920},
					{'action': 'close', 'repo': SLUG, 'number': 921, 'url': url_c1, 'state': 'closed', 'parent_number': 920},
					{'action': 'create', 'repo': SLUG, 'number': 939, 'url': url_bug, 'state': 'open'},
				],
			}
			res = issue_lifecycle.code_and_issue_lifecycle_status(project, turn, turn_state={})
			self.assertTrue(res['verified'], res['violations'])
if '__main__' == __name__:
	unittest.main()
