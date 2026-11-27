# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from pathlib import Path
from types import SimpleNamespace
import json
import subprocess
import sys
import tempfile
import unittest
WT_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = WT_ROOT / 'scripts'
if str(SCRIPTS) not in sys.path:
	sys.path.insert(0, str(SCRIPTS))
_NO_WIN = getattr(subprocess, 'CREATE_NO_WINDOW', 0)
# @used-by :func:`_init_repo()`
# @used-by :meth:`DfHarnessS11Wave2bGateCovTests.test_repo_links_tags_and_worktree_isolation()`
def _git(repo: Path, *args: str) -> subprocess.CompletedProcess:
	return subprocess.run(['git', '-C', str(repo), *args], stdin=subprocess.DEVNULL, capture_output=True, text=True, encoding='utf-8', check=False, timeout=30, creationflags=_NO_WIN)
# @used-by :meth:`DfHarnessS11Wave2bGateCovTests.test_repo_links_tags_and_worktree_isolation()`
# @used-by :meth:`DfHarnessS11Wave2bGateCovTests.test_rules_auditor_subprocess_and_xref_checker()`
def _init_repo(repo: Path, remote_url: str | None=None) -> None:
	repo.mkdir(parents=True, exist_ok=True)
	_git(repo, 'init')
	_git(repo, 'config', 'user.email', 't@example.com')
	_git(repo, 'config', 'user.name', 'T')
	if remote_url:
		_git(repo, 'remote', 'add', 'origin', remote_url)
# 2026-11-26 "Move verification gate subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/381
# @used-by :mod:`unittest`
class DfHarnessS11Wave2bGateCovTests(unittest.TestCase):
	# @used-by :mod:`unittest`
	def test_browser_bulk_read_external_write_and_registry_gates(self) -> None:
		from Df.Harness.Gate.BrowserMcpGate import BrowserMcpGate
		from Df.Harness.Gate.BulkSourceReadGate import BulkSourceReadGate
		from Df.Harness.Gate.CodeSizeAnalyzer import CodeSizeAnalyzer
		from Df.Harness.Gate.CodeStyleAnalyzer import CodeStyleAnalyzer
		from Df.Harness.Gate.ExternalWriteGate import ExternalWriteGate
		from Df.Harness.Gate.PreToolRegistry import PreToolRegistry
		with tempfile.TemporaryDirectory() as td:
			root = Path(td).resolve()
			tx = root / 'tx.jsonl'
			rows = [{'step_index': 0, 'type': 'USER_INPUT', 'content': 'Inspect files'}, {'step_index': 1, 'type': 'PLANNER_RESPONSE', 'tool_calls': [{'name': 'mcp_chrome_new_page', 'args': {'background': True}}, {'name': 'read_file', 'args': {'Path': str(root / 'a.py')}}]}, {'step_index': 2, 'type': 'PLANNER_RESPONSE', 'tool_calls': [{'name': 'read_file', 'args': {'Path': str(root / 'b.py')}}, {'name': 'read_file', 'args': {'Path': str(root / 'c.py')}}]}]
			tx.write_text('\n'.join((json.dumps(r) for r in rows)) + '\n', encoding='utf-8')
			has_bg = BrowserMcpGate.turn_has_background_mcp_new_page({'transcriptPath': str(tx)})
			self.assertTrue(has_bg)
			self.assertEqual(2, len(BulkSourceReadGate.recent_segment_rows(tx)))
			self.assertIsNone(BulkSourceReadGate().check('read_file', {'Path': str(root / 'd.py')}, {'transcriptPath': str(tx)}))
			self.assertEqual(2, CodeSizeAnalyzer('def f():\n\t"doc"\n\treturn 1\n').analyze()['file_sloc'])
			dq_lines = CodeStyleAnalyzer('x = "plain"\n').analyze()['double_quotes']
			self.assertTrue(dq_lines)
			plug_dir = root / 'plugs'
			plug_dir.mkdir()
			(plug_dir / 'custom_gate.py').write_text('NAME = "CUSTOM"\nPRIORITY = 50\nTOOLS = frozenset({"demo_tool"})\ndef check(n, a, p):\n\treturn None\n', encoding='utf-8')
			self.assertEqual('allow', PreToolRegistry().run('demo_tool', {}, {}, extra_dirs=[plug_dir])['decision'])
			upw = root / 'upwork_proj'
			turns = upw / '\ua616/data/turns'
			turns.mkdir(parents=True)
			(turns / 't1.json').write_text(json.dumps({'status': 'open', 'request_text': 'Analyze only'}), encoding='utf-8')
			cmd = f'python df_github_issue.py create --repo o/r --body-file "{upw}/b.md"'
			self.assertIsNone(ExternalWriteGate.upwork_project_root_for_command(cmd))
			self.assertIsNone(ExternalWriteGate().check('run_command', {'CommandLine': cmd}, {'cwd': str(upw)}))
	# @used-by :mod:`unittest`
	def test_issue_comment_checker_and_scanner_cover_py_js_and_xml(self) -> None:
		from Df.Harness.Gate.IssueCommentChecker import IssueCommentChecker
		from Df.Harness.Gate.IssueCommentScanner import IssueCommentScanner
		py_base = '# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk\nclass A:\n\tdef f(self):\n\t\treturn 1\n'
		py_new = '# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk\n# 2026-11-26 "Demo": https://github.com/o/r/issues/1\nclass A:\n\t# 2026-11-26 "Demo": https://github.com/o/r/issues/1\n\tdef f(self):\n\t\t# 2026-11-26 "Demo": https://github.com/o/r/issues/1\n\t\treturn 2\n'
		self.assertIsInstance(IssueCommentChecker('scripts/a.py', py_new, baseline_source=py_base).check(), list)
		js_lines = ['function f() {', '\treturn 1;', '}']
		js_span = IssueCommentScanner.construct_span(js_lines, 1, '.js', {})
		self.assertEqual((1, 3, 'block'), js_span)
		xml_lines = ['<root>', '\t<item/>', '</root>']
		xml_span = IssueCommentScanner.construct_span(xml_lines, 1, '.xml', {})
		self.assertEqual((1, 3, 'block'), xml_span)
		self.assertEqual(2, IssueCommentScanner.next_code_line(1, {2, 3}, 3))
		self.assertIsNotNone(IssueCommentScanner.resolve_target({'Path': 'a.py'}, {'cwd': str(WT_ROOT)}))
	# @used-by :mod:`unittest`
	def test_repo_links_tags_and_worktree_isolation(self) -> None:
		from Df.Harness.Gate.RepoLinkGate import RepoLinkGate
		from Df.Harness.Gate.RepoLinkResolver import RepoLinkResolver
		from Df.Harness.Gate.RepoTagGate import RepoTagGate
		from Df.Harness.Gate.WorktreeIsolationGate import WorktreeIsolationGate
		with tempfile.TemporaryDirectory() as td:
			base = Path(td).resolve()
			bare = base / 'origin.git'
			_git(base, 'init', '--bare', str(bare))
			repo = base / 'repo'
			_init_repo(repo, 'https://github.com/acme/demo.git')
			(repo / '.gitignore').write_text('ignored.txt\n', encoding='utf-8')
			(repo / 'ignored.txt').write_text('x\n', encoding='utf-8')
			(repo / 'README.md').write_text('# Intro\nText\n', encoding='utf-8')
			(repo / 'cfg.json').write_text('{"k": 1}\n', encoding='utf-8')
			_git(repo, 'add', '.gitignore', 'README.md', 'cfg.json')
			_git(repo, 'commit', '-m', 'init')
			_git(repo, 'tag', '2026-11-26')
			sha = _git(repo, 'rev-parse', 'HEAD').stdout.strip()
			blob_url = 'https://github.com/acme/demo/blob/2026-11-26/README.md#intro'
			self.assertTrue(RepoLinkResolver.is_gitignored(repo, 'ignored.txt'))
			self.assertEqual([], RepoLinkResolver.validate_github_url(blob_url, repo))
			self.assertEqual([], RepoLinkResolver.validate_github_url('https://github.com/acme/demo/blob/2026-11-26/cfg.json#L1', repo))
			aud = SimpleNamespace(root=repo, authored_urls=[blob_url], observed_urls=set(), observed_texts={})
			self.assertTrue(RepoLinkResolver.hydrate_local_urls(aud))
			self.assertTrue(RepoLinkGate.check_chat(f'[a](file:///{repo.as_posix()}/README.md)', root=repo))
			self.assertIsInstance(RepoLinkGate.check_file(repo / 'README.md', '[x](../other/a.md)', repo_root=repo), list)
			_git(repo, 'remote', 'set-url', 'origin', str(bare))
			_git(repo, 'push', '-u', 'origin', 'HEAD', '--tags')
			tag_out = RepoTagGate(repo, sha, 'https://github.com/acme/demo/issues/1').verify()
			self.assertEqual('2026-11-26', tag_out)
			fin = RepoTagGate.finalize_close_check(repo, sha, 'https://github.com/acme/demo/issues/1', SimpleNamespace(verify_commit_pushed=lambda *_a: True, upstream_unpushed=lambda _r: (True, [])))
			self.assertTrue(fin['verified'])
			turns = repo / '\ua616/data/turns'
			turns.mkdir(parents=True)
			(turns / 'a.json').write_text(json.dumps({'status': 'open', 'conversation_id': 'c1', 'updated_at': '2099-01-01T00:00:00Z'}), encoding='utf-8')
			(turns / 'b.json').write_text(json.dumps({'status': 'open', 'conversation_id': 'c2', 'updated_at': '2099-01-01T00:00:00Z'}), encoding='utf-8')
			self.assertIsNotNone(WorktreeIsolationGate().check('write_file', {'Path': str(repo / 'README.md')}, {'cwd': str(repo)}))
	# @used-by :mod:`unittest`
	def test_rules_auditor_subprocess_and_xref_checker(self) -> None:
		from Df.Harness.Gate.RulesAuditChecker import RulesAuditChecker
		from Df.Harness.Gate.RulesAuditor import RulesAuditor
		from Df.Harness.Gate.RulesManifest import RulesManifest
		from Df.Harness.Gate.SubprocessHygieneChecker import SubprocessHygieneChecker
		from Df.Harness.Gate.SubprocessHygieneStagedGate import SubprocessHygieneStagedGate
		from Df.Harness.Gate.XrefChecker import XrefChecker
		with tempfile.TemporaryDirectory() as td:
			root = Path(td).resolve()
			prim = root / 'prim'
			rules = prim / 'rules'
			rules.mkdir(parents=True)
			rf = rules / '00-demo.md'
			rf.write_text('---\ntrigger: always_on\n---\n# Demo\nRead `foo.md` without link.\n', encoding='utf-8')
			self.assertEqual(prim.resolve(), RulesManifest.resolve_primary(prim, root))
			rep = RulesAuditor(prim).audit()
			self.assertIn('valid', rep)
			fmt_txt = RulesAuditor.format_text(rep)
			self.assertIn('rules-audit', fmt_txt)
			self.assertIn('files', RulesAuditor.build_semantic_brief(prim))
			html_issues = RulesAuditChecker.check_html_comments([{'name': '00-demo.md', 'text': '<!-- leak -->'}])
			self.assertTrue(html_issues)
			self.assertIsNone(RulesAuditor.check_shared_rule_edit('write_file', {'Path': str(root / 'other.md'), 'Content': 'hi'}))
			self.assertEqual([], SubprocessHygieneChecker('scripts/a.py', 'import subprocess\nsubprocess.run(["x"], **{"stdin": subprocess.DEVNULL})\n').check())
			sub_errs = SubprocessHygieneStagedGate.run_staged_gate('subprocess_hygiene_gate', 'verify_staged_subprocess_hygiene', root, [])
			self.assertIsNone(sub_errs)
			repo = root / 'xrepo'
			_init_repo(repo)
			(repo / 'scripts').mkdir()
			(repo / 'scripts/a.py').write_text('# @used-by unused\ndef f():\n\treturn 1\n', encoding='utf-8')
			self.assertTrue(XrefChecker.is_pre_tool_governed(repo, repo / 'scripts/a.py', '# @used-by unused\ndef f():\n\treturn 1\n'))
			self.assertIsInstance(XrefChecker.is_repo_lang_synced(repo, 'python', set()), bool)
			self.assertIsNotNone(XrefChecker.resolve_target({'Path': str(repo / 'scripts/a.py')}, {}))
			leg_errs = XrefChecker.verify_legacy_changed_files(repo, 'python', ['scripts/a.py'], {'scripts/a.py': 'def f():\n\treturn 1\n'}, lambda _repo, _r: None)
			self.assertIsInstance(leg_errs, list)
if '__main__' == __name__:
	unittest.main()
