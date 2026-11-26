# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Ban file:/// links for GitHub repositories and ground tagged GitHub URLs":
# https://github.com/dmitry-ai/harness/issues/264
from __future__ import annotations
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
WT_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = WT_ROOT / 'scripts'
if str(SCRIPTS) not in sys.path:
	sys.path.insert(0, str(SCRIPTS))
from agent_tools import completion, links, staged_gates
from agent_tools.issues.linter import IssueMarkdownLinter
from agent_tools.repo_tags import ensure_commit_tag
from agent_tools.response_grounding import ResponseEvidenceAuditor
import check_markdown_slop
# @used-by :func:`_init_tagged_repo()`
def _git(repo: Path, *args: str) -> None:
	subprocess.run(['git', '-C', str(repo), *args], check=True, capture_output=True, stdin=subprocess.DEVNULL, timeout=30)
# @used-by :func:`_sample_workspace()`
def _init_tagged_repo(root: Path, slug: str, files: dict[str, str], *, tag_date: str='2026-11-26') -> Path:
	root.mkdir(parents=True, exist_ok=True)
	_git(root, 'init', '-b', 'main')
	cfg = root / '.git/config'
	cfg.write_text(cfg.read_text(encoding='utf-8') + f'[user]\n\temail = test@example.com\n\tname = Test\n[remote "origin"]\n\turl = https://github.com/{slug}.git\n', encoding='utf-8')
	for rel, content in files.items():
		fp = root / rel
		fp.parent.mkdir(parents=True, exist_ok=True)
		fp.write_text(content, encoding='utf-8')
	_git(root, 'add', '.')
	_git(root, 'commit', '-m', f'https://github.com/{slug}/issues/1')
	ensure_commit_tag(root, date_override=tag_date, push=False)
	return root
# @used-by :meth:`RepoLinkGateTests.test_cross_repo_relative_link_rejected_while_intra_repo_relative_link_allowed()`
# @used-by :meth:`RepoLinkGateTests.test_grounding_accepts_verified_local_repo_tagged_url_and_blocks_fabrications()`
# @used-by :meth:`RepoLinkGateTests.test_issue_linter_staged_gate_and_markdown_hook_enforce_repo_link_ban()`
# @used-by :meth:`RepoLinkGateTests.test_rejects_file_uri_to_github_repo_and_allows_non_repo_and_gitignored_files()`
# @used-by :meth:`RepoLinkGateTests.test_validates_github_blob_and_tree_tags_paths_lines_and_anchors()`
def _sample_workspace(base: Path) -> tuple[Path, Path, Path]:
	proj = base / 'proj'
	meta = _init_tagged_repo(proj, 'acme/demo--meta', {'docs/b.md': '# Target\nBody.\n'})
	code = _init_tagged_repo(
		proj / 'code',
		'acme/demo',
		{
			'.gitignore': 'scratch/\n',
			'data/cfg.json': '{"nested": {"k": 42}}\n',
			'docs/guide.md': '# Guide\n\n## Alpha Section\nDetails here.\n',
			'src/app.py': 'LIMIT_BYTES = 4096\nMSG = "verified payload marker for grounding"\ndef run():\n\treturn LIMIT_BYTES\n',
		},
	)
	plain = base / 'plain/notes.md'
	plain.parent.mkdir(parents=True, exist_ok=True)
	plain.write_text('Plain local note.\n', encoding='utf-8')
	return (meta, code, plain)
class RepoLinkGateTests(unittest.TestCase):
	# @used-by :mod:`unittest`
	def test_cross_repo_relative_link_rejected_while_intra_repo_relative_link_allowed(self) -> None:
		with tempfile.TemporaryDirectory() as tmp:
			meta, code, _ = _sample_workspace(Path(tmp).resolve())
			app_posix = (code / 'src/app.py').as_posix()
			doc = meta / 'docs/a.md'
			doc.write_text('Intra-repo [b.md](b.md) works.  \n', encoding='utf-8')
			self.assertEqual([], links.validate_file(doc, local_anchors=True, readable_links=True))
			doc.write_text('Cross-repo [app.py](../code/src/app.py#L1-L2).  \n', encoding='utf-8')
			cross_errs = links.validate_file(doc, local_anchors=True, readable_links=True)
			self.assertTrue(any('LINK-6' in e for e in cross_errs), cross_errs)
			doc.write_text(f'File URI [app.py](file:///{app_posix}#L1-L2).  \n', encoding='utf-8')
			uri_errs = links.validate_file(doc, local_anchors=True, readable_links=True)
			self.assertTrue(any('LINK-6' in e for e in uri_errs), uri_errs)
			doc.write_text('Tagged [app.py](https://github.com/acme/demo/blob/2026-11-26/src/app.py#L1-L2).  \n', encoding='utf-8')
			self.assertEqual([], links.validate_file(doc, local_anchors=True, readable_links=True))
	# @used-by :mod:`unittest`
	def test_grounding_accepts_verified_local_repo_tagged_url_and_blocks_fabrications(self) -> None:
		with tempfile.TemporaryDirectory() as tmp:
			meta, _, _ = _sample_workspace(Path(tmp).resolve())
			url = 'https://github.com/acme/demo/blob/2026-11-26/src/app.py#L1-L2'
			good = f'Constant `4096` in [app.py]({url}) prints \u00abverified payload marker for grounding\u00bb.  \n'
			self.assertEqual([], ResponseEvidenceAuditor(meta, good, []).validate())
			chk = completion.check_answer(meta, good)
			self.assertTrue(chk['valid'], chk)
			bad_quote = f'In [app.py]({url}) it says \u00abcompletely invented payload string here\u00bb.  \n'
			q_errs = ResponseEvidenceAuditor(meta, bad_quote, []).validate()
			self.assertTrue(any('VERIFY-1' in e for e in q_errs), q_errs)
			bad_num = f'In [app.py]({url}) the buffer limit is `99999` bytes.  \n'
			n_errs = ResponseEvidenceAuditor(meta, bad_num, []).validate()
			self.assertTrue(any('99999' in e for e in n_errs), n_errs)
	# @used-by :mod:`unittest`
	def test_issue_linter_staged_gate_and_markdown_hook_enforce_repo_link_ban(self) -> None:
		with tempfile.TemporaryDirectory() as tmp:
			meta, code, _ = _sample_workspace(Path(tmp).resolve())
			app_uri = 'file:///' + (code / 'src/app.py').as_posix() + '#L1-L2'
			lint_errs = IssueMarkdownLinter().lint(f'## Root Cause\nSee [app.py]({app_uri}).\n', is_title=False)
			self.assertIn('REPO_LINK_FORBIDDEN', {e['code'] for e in lint_errs}, lint_errs)
			note = meta / 'docs/note.md'
			bad_md = f'Reference [app.py]({app_uri}) here.  \n'
			note.write_text(bad_md, encoding='utf-8')
			staged_bad = staged_gates.verify_staged_extra_gates(meta, ['docs/note.md'], use_index=False)
			self.assertTrue(any('LINK-6' in e for e in staged_bad), staged_bad)
			hook_bad = check_markdown_slop.check_markdown_content(bad_md, str(note))
			self.assertIn('LINK-6', hook_bad or '')
			good_md = 'Reference [app.py](https://github.com/acme/demo/blob/2026-11-26/src/app.py#L1-L2) here.  \n'
			note.write_text(good_md, encoding='utf-8')
			self.assertEqual([], staged_gates.verify_staged_extra_gates(meta, ['docs/note.md'], use_index=False))
			self.assertIsNone(check_markdown_slop.check_markdown_content(good_md, str(note)))
	# @used-by :mod:`unittest`
	def test_rejects_file_uri_to_github_repo_and_allows_non_repo_and_gitignored_files(self) -> None:
		with tempfile.TemporaryDirectory() as tmp:
			meta, code, plain = _sample_workspace(Path(tmp).resolve())
			ignored = code / 'scratch/temp.txt'
			ignored.parent.mkdir(parents=True, exist_ok=True)
			ignored.write_text('scratch\n', encoding='utf-8')
			app_uri = 'file:///' + (code / 'src/app.py').as_posix() + '#L1-L2'
			errs = links.chat_reply_link_issues(f'Inspect [app.py]({app_uri}).  \n', root=meta)
			self.assertTrue(any('LINK-6' in e and 'acme/demo' in e for e in errs), errs)
			self.assertEqual([], links.chat_reply_link_issues(f'Scratch [temp.txt](file:///{ignored.as_posix()}).  \n', root=meta))
			self.assertEqual([], links.chat_reply_link_issues(f'Plain [notes.md](file:///{plain.as_posix()}).  \n', root=meta))
			quoted = f'> [app.py]({app_uri})\n\n```markdown\n[app.py]({app_uri})\n```\n'
			self.assertEqual([], links.chat_reply_link_issues(quoted, root=meta))
	# @used-by :mod:`unittest`
	def test_validates_github_blob_and_tree_tags_paths_lines_and_anchors(self) -> None:
		with tempfile.TemporaryDirectory() as tmp:
			meta, _, _ = _sample_workspace(Path(tmp).resolve())
			good_urls = (
				'https://github.com/acme/demo/blob/2026-11-26/src/app.py#L1-L3',
				'https://github.com/acme/demo/blob/2026-11-26/docs/guide.md#alpha-section',
				'https://github.com/acme/demo/blob/2026-11-26/data/cfg.json#/nested/k',
				'https://github.com/acme/demo/tree/2026-11-26/src',
				'https://github.com/mage2pro/core/blob/11.6.1/Qa/lib/validation/assert/.php#L6-L16',
			)
			for u in good_urls:
				self.assertEqual([], links.chat_reply_link_issues(f'See [ref]({u}).  \n', root=meta), u)
			bad_urls = (
				'https://github.com/acme/demo/blob/main/src/app.py#L1-L3',
				'https://github.com/acme/demo/blob/2026-11-26--9/src/app.py',
				'https://github.com/acme/demo/blob/2026-11-26/src/missing.py',
				'https://github.com/acme/demo/blob/2026-11-26/src/app.py#L1-L99',
				'https://github.com/acme/demo/blob/2026-11-26/docs/guide.md#no-such-heading',
				'https://github.com/acme/demo/blob/2026-11-26/data/cfg.json#/nested/missing',
				'https://github.com/acme/demo/blob/2026-11-26/src',
				'https://github.com/acme/demo/tree/2026-11-26/src/app.py',
			)
			for u in bad_urls:
				errs = links.chat_reply_link_issues(f'See [ref]({u}).  \n', root=meta)
				self.assertTrue(any('LINK-6' in e for e in errs), f'Expected LINK-6 for {u}, got {errs}')
if '__main__' == __name__:
	unittest.main()
