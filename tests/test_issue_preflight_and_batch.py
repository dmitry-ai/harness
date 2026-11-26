# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch
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
from agent_tools import github_issue, issue_first_gate, shell_audit, source_grounding
from agent_tools.repo_tags import ensure_commit_tag
# @used-by :meth:`IssuePreflightAndBatchTests.test_batch_close_enforces_grounding_consumes_inputs_and_extracts_actions()`
# @used-by :meth:`IssuePreflightAndBatchTests.test_close_and_comment_reject_ungrounded_blob_claim_before_api_call()`
# @used-by :meth:`IssuePreflightAndBatchTests.test_test_summary_counts_allowed_alongside_blob_link_while_ungrounded_numbers_fail()`
def _commit_and_tag(repo: Path, rel: str, text: str, msg: str) -> str:
	fp = repo / rel
	fp.parent.mkdir(parents=True, exist_ok=True)
	fp.write_text(text, encoding='utf-8')
	_git(repo, 'add', rel)
	_git(repo, 'commit', '--no-verify', '-m', msg)
	return ensure_commit_tag(repo, push=False)['tag']
# @used-by :func:`_commit_and_tag()`
# @used-by :func:`_init_tagged_project()`
def _git(repo: Path, *args: str) -> None:
	subprocess.run(['git', *args], cwd=str(repo), stdin=subprocess.DEVNULL, capture_output=True, timeout=30, check=True)
# @used-by :meth:`IssuePreflightAndBatchTests.test_batch_close_enforces_grounding_consumes_inputs_and_extracts_actions()`
# @used-by :meth:`IssuePreflightAndBatchTests.test_batch_create_verifies_readback_and_action_extraction()`
# @used-by :meth:`IssuePreflightAndBatchTests.test_close_and_comment_reject_ungrounded_blob_claim_before_api_call()`
# @used-by :meth:`IssuePreflightAndBatchTests.test_test_summary_counts_allowed_alongside_blob_link_while_ungrounded_numbers_fail()`
def _init_tagged_project(root: Path, slug: str='acme/demo') -> tuple[Path, Path]:
	proj = root / 'proj'
	(proj / '\ua616/data/scratch').mkdir(parents=True, exist_ok=True)
	code = proj / 'code'
	code.mkdir(parents=True, exist_ok=True)
	_git(code, 'init', '-b', 'main')
	_git(code, 'config', 'user.email', 'test@example.com')
	_git(code, 'config', 'user.name', 'Test')
	_git(code, 'remote', 'add', 'origin', f'https://github.com/{slug}.git')
	return (proj, code)
# @used-by :meth:`IssuePreflightAndBatchTests.test_batch_close_enforces_grounding_consumes_inputs_and_extracts_actions()`
# @used-by :meth:`IssuePreflightAndBatchTests.test_batch_create_verifies_readback_and_action_extraction()`
def _make_fake_gh(slug: str, issues_db: dict[int, dict], comments_db: dict[int, dict], calls: list[tuple[str, str]]):
	next_num = [max(issues_db)]
	next_cid = [700]
	# @used-by :func:`_make_fake_gh()`
	def _fake_gh(endpoint: str, *, method: str='GET', payload: dict | None=None, paginate: bool=False):
		calls.append((method, endpoint))
		if 'POST' == method and endpoint.endswith('/issues'):
			next_num[0] += 1
			num = next_num[0]
			issues_db[num] = {'body': payload['body'], 'html_url': f'https://github.com/{slug}/issues/{num}', 'id': 4000 + num, 'number': num, 'state': 'open', 'state_reason': None, 'title': payload['title']}
			r = issues_db[num]
		elif 'POST' == method and endpoint.endswith('/sub_issues'):
			r = {'linked': True}
		elif 'POST' == method and endpoint.endswith('/comments'):
			next_cid[0] += 1
			cid = next_cid[0]
			inum = int(endpoint.split('/issues/')[1].split('/')[0])
			comments_db[cid] = {'body': payload['body'], 'html_url': f'https://github.com/{slug}/issues/{inum}#issuecomment-{cid}', 'id': cid, 'issue_number': inum}
			r = comments_db[cid]
		elif 'GET' == method and '/issues/comments/' in endpoint:
			r = comments_db[int(endpoint.rsplit('/', 1)[-1])]
		elif 'PATCH' == method and '/issues/' in endpoint:
			num = int(endpoint.rsplit('/', 1)[-1])
			issues_db[num].update(payload or {})
			r = issues_db[num]
		else:
			r = issues_db[int(endpoint.rsplit('/', 1)[-1])]
		return r
	return _fake_gh
# @used-by :meth:`IssuePreflightAndBatchTests.test_batch_close_enforces_grounding_consumes_inputs_and_extracts_actions()`
# @used-by :meth:`IssuePreflightAndBatchTests.test_batch_create_verifies_readback_and_action_extraction()`
# @used-by :meth:`IssuePreflightAndBatchTests.test_close_and_comment_reject_ungrounded_blob_claim_before_api_call()`
def _run_cli_json(argv: list[str]) -> tuple[int, str, dict]:
	buf = io.StringIO()
	with redirect_stdout(buf):
		rc = github_issue.main(argv)
	raw = buf.getvalue()
	return (rc, raw, json.loads(raw))
# 2026-11-26 "Enforce pre-flight comment grounding and add batch GitHub issue commands": https://github.com/dmitry-ai/harness/issues/353
class IssuePreflightAndBatchTests(unittest.TestCase):
	# @used-by :mod:`unittest`
	def test_batch_close_enforces_grounding_consumes_inputs_and_extracts_actions(self) -> None:
		slug = 'acme/demo'
		with tempfile.TemporaryDirectory() as td:
			proj, code = _init_tagged_project(Path(td).resolve(), slug)
			issues_db = {n: {'body': '## Scope\nChild.\n', 'html_url': f'https://github.com/{slug}/issues/{n}', 'id': 4000 + n, 'number': n, 'state': 'open', 'state_reason': None, 'title': f'Child {n}'} for n in (51, 52)}
			comments_db: dict[int, dict] = {}
			calls: list[tuple[str, str]] = []
			fake_gh = _make_fake_gh(slug, issues_db, comments_db, calls)
			tag51 = _commit_and_tag(code, 'scripts/m1.py', f'# https://github.com/{slug}/issues/51\nLIMIT = 42\n', f'https://github.com/{slug}/issues/51')
			tag52 = _commit_and_tag(code, 'scripts/m2.py', f'# https://github.com/{slug}/issues/52\nRATE = 77\n', f'https://github.com/{slug}/issues/52')
			bad_c = proj / '\ua616/data/scratch/bad_c.md'
			bad_c.write_text(f'Updated [m1.py](https://github.com/{slug}/blob/{tag51}/scripts/m1.py) with 19918 rows.\n', encoding='utf-8')
			bad_spec = proj / '\ua616/data/scratch/bad_close.json'
			bad_spec.write_text(json.dumps([{'comment_file': str(bad_c), 'issue': 51}]), encoding='utf-8')
			with patch('agent_tools.github_issue._gh_api', side_effect=fake_gh):
				rc_bad, _, data_bad = _run_cli_json(['batch-close', '--repo', slug, '--spec-file', str(bad_spec), '--project-root', str(proj)])
			self.assertEqual(2, rc_bad, data_bad)
			self.assertEqual('pre_flight_grounding', data_bad['results'][0]['stage'])
			self.assertEqual([], calls)
			c1, c2 = (proj / '\ua616/data/scratch/c1.md', proj / '\ua616/data/scratch/c2.md')
			c1.write_text(f'Updated [m1.py](https://github.com/{slug}/blob/{tag51}/scripts/m1.py): Ran 1334 tests in 44.2s, 1334 tests passed.\n', encoding='utf-8')
			c2.write_text(f'Updated [m2.py](https://github.com/{slug}/blob/{tag52}/scripts/m2.py): 159/159 modules passed.\n', encoding='utf-8')
			close_spec = proj / '\ua616/data/scratch/close.json'
			close_spec.write_text(json.dumps([{'comment_file': str(c1), 'issue': 51}, {'comment_file': str(c2), 'issue': 52}]), encoding='utf-8')
			with patch('agent_tools.github_issue._gh_api', side_effect=fake_gh):
				rc_cl, _, data_cl = _run_cli_json(['batch-close', '--repo', slug, '--spec-file', str(close_spec), '--project-root', str(proj), '--consume-input'])
			self.assertEqual(0, rc_cl, data_cl)
			self.assertEqual(2, data_cl['succeeded'])
			self.assertFalse(close_spec.exists())
			self.assertFalse(c1.exists())
			self.assertFalse(c2.exists())
			clean_cl = json.dumps({**data_cl, 'consumed_files': [], 'results': [{**it, 'consumed_files': []} for it in data_cl['results']]})
			cl_actions = shell_audit.extract_issue_actions_from_outputs([clean_cl])
			self.assertEqual([(51, 'close'), (52, 'close')], [(a['number'], a['action']) for a in cl_actions])
	# @used-by :mod:`unittest`
	def test_batch_create_verifies_readback_and_action_extraction(self) -> None:
		slug = 'acme/demo'
		with tempfile.TemporaryDirectory() as td:
			proj, _ = _init_tagged_project(Path(td).resolve(), slug)
			url50 = f'https://github.com/{slug}/issues/50'
			issues_db = {50: {'body': '## Problem\nParent details.\n', 'html_url': url50, 'id': 4050, 'number': 50, 'state': 'open', 'state_reason': None, 'title': 'Parent problem'}}
			comments_db: dict[int, dict] = {}
			calls: list[tuple[str, str]] = []
			b1, b2 = (proj / '\ua616/data/scratch/b1.md', proj / '\ua616/data/scratch/b2.md')
			b1.write_text('Parent: #50\n\n## Scope\nFirst child task.\n', encoding='utf-8')
			b2.write_text('Parent: #50\n\n## Scope\nSecond child task.\n', encoding='utf-8')
			create_spec = proj / '\ua616/data/scratch/create.json'
			create_spec.write_text(json.dumps([{'body_file': str(b1), 'parent': 50, 'title': 'Add first module'}, {'body_file': str(b2), 'parent': 50, 'title': 'Add second module'}]), encoding='utf-8')
			fake_gh = _make_fake_gh(slug, issues_db, comments_db, calls)
			with patch('agent_tools.github_issue._gh_api', side_effect=fake_gh):
				rc_cr, raw_cr, data_cr = _run_cli_json(['batch-create', '--repo', slug, '--spec-file', str(create_spec), '--project-root', str(proj), '--no-metadata'])
			self.assertEqual(0, rc_cr, data_cr)
			self.assertTrue(data_cr['ok'])
			self.assertEqual('batch-create', data_cr['action'])
			self.assertEqual(2, data_cr['succeeded'])
			self.assertTrue((proj / '\ua616/KB/Evidence/GitHub/acme__demo/issue-51.json').is_file())
			self.assertTrue((proj / '\ua616/KB/Evidence/GitHub/acme__demo/issue-52.json').is_file())
			cr_actions = shell_audit.extract_issue_actions_from_outputs([raw_cr])
			self.assertEqual([(51, 'create', 50), (52, 'create', 50)], [(a['number'], a['action'], a.get('parent_number')) for a in cr_actions])
			self.assertTrue(issue_first_gate.is_df_github_issue_command('python scripts/df_github_issue.py batch-create --repo acme/demo --spec-file s.json'))
			self.assertTrue(issue_first_gate.is_df_github_issue_command('python scripts/df_github_issue.py batch-close --repo acme/demo --spec-file s.json'))
			self.assertTrue(issue_first_gate.is_df_github_issue_command('$gi = "scripts/df_github_issue.py"; python $gi batch-create --spec-file s.json'))
	# @used-by :mod:`unittest`
	def test_close_and_comment_reject_ungrounded_blob_claim_before_api_call(self) -> None:
		slug = 'acme/demo'
		with tempfile.TemporaryDirectory() as td:
			proj, code = _init_tagged_project(Path(td).resolve(), slug)
			tag = _commit_and_tag(code, 'scripts/calc.py', f'# https://github.com/{slug}/issues/10\nLIMIT = 42\n', f'https://github.com/{slug}/issues/10')
			bad_file = proj / '\ua616/data/scratch/comment.md'
			bad_file.write_text(f'Verified [calc.py](https://github.com/{slug}/blob/{tag}/scripts/calc.py) handled 19918 records.\n', encoding='utf-8')
			calls: list[tuple[str, str]] = []
			# @used-by :meth:`IssuePreflightAndBatchTests.test_close_and_comment_reject_ungrounded_blob_claim_before_api_call()`
			def _spy_api(endpoint: str, *, method: str='GET', payload: dict | None=None, paginate: bool=False):
				calls.append((method, endpoint))
				return {}
			with patch('agent_tools.github_issue._gh_api', side_effect=_spy_api):
				rc_cm, _, data_cm = _run_cli_json(['comment', '--repo', slug, '--issue', '10', '--body-file', str(bad_file), '--project-root', str(proj)])
				rc_cl, _, data_cl = _run_cli_json(['close', '--repo', slug, '--issue', '10', '--comment-file', str(bad_file), '--project-root', str(proj)])
			self.assertEqual(2, rc_cm, data_cm)
			self.assertEqual('pre_flight_grounding', data_cm['stage'])
			self.assertTrue(any(('19918' in e for e in data_cm['grounding_errors'])), data_cm)
			self.assertEqual(2, rc_cl, data_cl)
			self.assertEqual('pre_flight_grounding', data_cl['stage'])
			self.assertTrue(any(('19918' in e for e in data_cl['grounding_errors'])), data_cl)
			self.assertEqual([], calls)
	# @used-by :mod:`unittest`
	def test_test_summary_counts_allowed_alongside_blob_link_while_ungrounded_numbers_fail(self) -> None:
		slug = 'acme/demo'
		with tempfile.TemporaryDirectory() as td:
			proj, code = _init_tagged_project(Path(td).resolve(), slug)
			tag = _commit_and_tag(code, 'scripts/calc.py', f'# https://github.com/{slug}/issues/10\nLIMIT = 42\n', f'https://github.com/{slug}/issues/10')
			blob = f'https://github.com/{slug}/blob/{tag}/scripts/calc.py'
			ok_text = f'Updated [calc.py]({blob}) (LIMIT 42): Ran 1334 tests in 44.2s, 1334 tests passed (1334 passed, 1 skipped in 44.2s, 159/159 modules, workers=6, passed=1334, skipped=1).\n'
			self.assertEqual([], source_grounding.local_source_grounding_issues(proj, ok_text))
			bad_text = f'Updated [calc.py]({blob}): processed 19918 items and 20000 bytes.\n'
			bad_errs = source_grounding.local_source_grounding_issues(proj, bad_text)
			self.assertTrue(any(('19918' in e for e in bad_errs)), bad_errs)
			self.assertTrue(any(('20000' in e for e in bad_errs)), bad_errs)
			t_src = proj / 'tickets/7654321/source.md'
			t_src.parent.mkdir(parents=True, exist_ok=True)
			t_src.write_text('# Ticket 7654321\n### Message #1\nLimit is 42.\n', encoding='utf-8')
			ticket_text = f'Per [Ticket](<{t_src.as_posix()}>): 1334 tests passed.\n'
			ticket_errs = source_grounding.local_source_grounding_issues(proj, ticket_text)
			self.assertTrue(any(('1334' in e for e in ticket_errs)), ticket_errs)
if '__main__' == __name__:
	unittest.main()
