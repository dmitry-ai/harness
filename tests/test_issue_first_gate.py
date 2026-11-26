# 2026-11-23 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

SCRIPT_DIR = Path(__file__).resolve().parents[1] / 'scripts'
if str(SCRIPT_DIR) not in sys.path:
	sys.path.insert(0, str(SCRIPT_DIR))

from agent_tools import issue_first_gate, shell_audit, tdd_gate


def _init_git_repo(repo: Path, *, remote_url: str | None = None) -> None:
	repo.mkdir(parents=True, exist_ok=True)
	subprocess.run(['git', 'init', str(repo)], check=True, capture_output=True)
	subprocess.run(['git', '-C', str(repo), 'config', 'user.email', 'test@example.com'], check=True, capture_output=True)
	subprocess.run(['git', '-C', str(repo), 'config', 'user.name', 'Test User'], check=True, capture_output=True)
	if remote_url:
		subprocess.run(['git', '-C', str(repo), 'remote', 'add', 'origin', remote_url], check=True, capture_output=True)


def _write_issue_evidence(proj_root: Path, slug: str, number: int, *, state: str = 'open', parent_number: int | None = None) -> Path:
	safe = slug.replace('/', '__')
	ev_dir = proj_root / 'ꘖ/KB/Evidence/GitHub' / safe
	ev_dir.mkdir(parents=True, exist_ok=True)
	body = f'Parent: #{parent_number}\n\n## Scope\nSubtask details.\n' if parent_number else '## Problem\nRoot cause details.\n'
	payload: dict = {
		'url': f'https://github.com/{slug}/issues/{number}',
		'html_url': f'https://github.com/{slug}/issues/{number}',
		'repo': slug,
		'kind': 'issue',
		'number': number,
		'issue_number': number,
		'state': state,
		'title': f'Issue {number}',
		'body': body,
	}
	if parent_number is not None:
		payload['parent_number'] = parent_number
		payload['parent_url'] = f'https://github.com/{slug}/issues/{parent_number}'
	out = ev_dir / f'issue-{number}.json'
	out.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding='utf-8')
	return out


# 2026-11-23
# "Implement core Issue-First verification engine in agent_tools/issue_first_gate.py":
# https://github.com/dmitry-ai/harness/issues/143
class IssueFirstGateCoreTests(unittest.TestCase):
	def test_resolve_issue_first_target_distinguishes_github_backed_local_and_metadata_paths(self) -> None:
		with tempfile.TemporaryDirectory() as tmp:
			base = Path(tmp).resolve()
			# 1. Dual-repo issue-tracked code repo with GitHub remote
			proj = base / 'proj'
			(proj / '_/ꘖ').mkdir(parents=True)
			code_repo = proj / 'code'
			_init_git_repo(code_repo, remote_url='https://github.com/acme/demo.git')

			t_test = issue_first_gate.resolve_issue_first_target(code_repo / 'tests/test_app.py')
			self.assertIsNotNone(t_test)
			self.assertEqual(t_test['repo_slug'], 'acme/demo')
			self.assertEqual(t_test['classification'], 'test')
			self.assertEqual(t_test['rel_path'], 'tests/test_app.py')

			t_prod = issue_first_gate.resolve_issue_first_target(code_repo / 'src/app.py')
			self.assertIsNotNone(t_prod)
			self.assertEqual(t_prod['classification'], 'production')

			t_doc = issue_first_gate.resolve_issue_first_target(code_repo / 'rules/08-execution-and-tools.md')
			self.assertIsNotNone(t_doc)
			self.assertEqual(t_doc['classification'], 'non_code')

			# Metadata paths inside or outside code_repo are never governed
			for meta_rel in (
				'.git/config',
				'ꘖ/data/scratch/issue-body.md',
				'ꙮ/≻/1–20/1.md',
				'🕮/Project.md',
				'Ⰿ/≺/Logs/log.md',
			):
				self.assertIsNone(
					issue_first_gate.resolve_issue_first_target(code_repo / meta_rel),
					f'Metadata path must not be governed: {meta_rel}',
				)

			# 2. Standalone GitHub-backed repo (not dual_repo/v2_software layout)
			standalone = base / 'standalone'
			_init_git_repo(standalone, remote_url='git@github.com:acme/tool.git')
			self.assertEqual(issue_first_gate.resolve_issue_first_target(standalone / 'tests/test_tool.py')['repo_slug'], 'acme/tool')
			self.assertEqual(issue_first_gate.resolve_issue_first_target(standalone / 'tool.py')['classification'], 'production')
			self.assertIsNone(issue_first_gate.resolve_issue_first_target(standalone / 'README.md'))

			# 3. Local-only git repo without GitHub remote -> not governed
			bare = base / 'bare.git'
			subprocess.run(['git', 'init', '--bare', str(bare)], check=True, capture_output=True)
			local_repo = base / 'local_only'
			_init_git_repo(local_repo, remote_url=str(bare))
			self.assertIsNone(issue_first_gate.resolve_issue_first_target(local_repo / 'tests/test_local.py'))
			self.assertIsNone(issue_first_gate.resolve_issue_first_target(local_repo / 'app.py'))

			# 4. Plain non-git directory -> not governed
			plain = base / 'plain_dir'
			plain.mkdir()
			self.assertIsNone(issue_first_gate.resolve_issue_first_target(plain / 'script.py'))

	def test_shell_write_targets_detects_test_production_and_doc_writes(self) -> None:
		with tempfile.TemporaryDirectory() as tmp:
			repo = Path(tmp).resolve() / 'repo'
			repo.mkdir()
			cmd_test = f'Set-Content -Path "{repo / "tests/test_calc.py"}" -Value "assert True"'
			cmd_prod = f'Out-File -FilePath "{repo / "src/calc.py"}"'
			cmd_doc = f'python -c "from pathlib import Path; Path(\'{(repo / "rules/08.md").as_posix()}\').write_text(\'hi\')"'
			cmd_redir = f'echo ok > "{repo / "tests/test_other.js"}"'

			self.assertEqual(tdd_gate.shell_code_write_targets(cmd_test, cwd=repo), [])
			self.assertEqual(tdd_gate.shell_code_write_targets(cmd_prod, cwd=repo), [(repo / 'src/calc.py').resolve()])

			self.assertEqual(tdd_gate.shell_write_targets(cmd_test, cwd=repo), [(repo / 'tests/test_calc.py').resolve()])
			self.assertEqual(tdd_gate.shell_write_targets(cmd_prod, cwd=repo), [(repo / 'src/calc.py').resolve()])
			self.assertEqual(tdd_gate.shell_write_targets(cmd_doc, cwd=repo), [(repo / 'rules/08.md').resolve()])
			self.assertEqual(tdd_gate.shell_write_targets(cmd_redir, cwd=repo), [(repo / 'tests/test_other.js').resolve()])

	def test_extract_issue_actions_recognizes_fetch_and_anti_spoofing_command_check(self) -> None:
		fetch_out = json.dumps({
			'ok': True,
			'action': 'fetch',
			'repo': 'acme/demo',
			'number': 12,
			'state': 'open',
			'html_url': 'https://github.com/acme/demo/issues/12',
			'verified': True,
		})
		parsed = shell_audit.extract_issue_actions_from_outputs([fetch_out])
		self.assertEqual(len(parsed), 1)
		self.assertEqual(parsed[0]['action'], 'fetch')
		self.assertEqual(parsed[0]['repo'], 'acme/demo')
		self.assertEqual(parsed[0]['number'], 12)
		self.assertEqual(parsed[0]['state'], 'open')

		# Real df_github_issue.py mutating/fetch invocations
		for good_cmd in (
			'python "C:/work/scripts/df_github_issue.py" create --repo acme/demo --title "Bug" --body-file b.md',
			'python df_github_issue.py fetch --repo acme/demo --issue 12',
			'python3 scripts/df_github_issue.py edit --repo acme/demo --issue 12 --body-file b.md',
			'python scripts/df_github_issue.py comment --repo acme/demo --issue 12 --body-file c.md',
			'python scripts/df_github_issue.py close --repo acme/demo --issue 12',
		):
			self.assertTrue(issue_first_gate.is_df_github_issue_command(good_cmd), good_cmd)

		# Spoofing and non-binding commands must be rejected
		for bad_cmd in (
			'echo \'{"ok":true,"action":"create","repo":"acme/demo","number":99}\'',
			'Write-Output \'{"ok":true,"action":"create","repo":"acme/demo","number":99}\'',
			'python -c "print(\'df_github_issue.py create\')"',
			'python df_github_issue.py lint --title "T" --body-file b.md',
			'python df_github_issue.py audit-repo --repo acme/demo',
		):
			self.assertFalse(issue_first_gate.is_df_github_issue_command(bad_cmd), bad_cmd)

	def test_chronological_state_machine_enforces_parent_issue_before_tests_and_code(self) -> None:
		with tempfile.TemporaryDirectory() as tmp:
			base = Path(tmp).resolve()
			proj = base / 'proj'
			(proj / 'ꘖ/KB/Evidence/GitHub').mkdir(parents=True)
			code = proj / 'code'
			_init_git_repo(code, remote_url='https://github.com/acme/demo.git')
			_write_issue_evidence(proj, 'acme/demo', 8, state='open')
			_write_issue_evidence(proj, 'acme/demo', 9, state='closed')
			_write_issue_evidence(proj, 'acme/demo', 10, state='open')
			_write_issue_evidence(proj, 'acme/demo', 11, state='open', parent_number=10)

			def _cw(step: int, rel: str, cls: str = 'test') -> dict:
				return {
					'kind': 'code_write',
					'step': step,
					'path': str(code / rel),
					'rel_path': rel,
					'repo_root': str(code),
					'repo_slug': 'acme/demo',
					'classification': cls,
				}

			def _ia(step: int, action: str, number: int, *, state: str | None = None, parent_number: int | None = None) -> dict:
				ev = {
					'kind': 'issue_action',
					'step': step,
					'action': action,
					'repo': 'acme/demo',
					'number': number,
					'url': f'https://github.com/acme/demo/issues/{number}',
					'state': state,
				}
				if parent_number is not None:
					ev['parent_number'] = parent_number
				return ev

			# 1. Test written before any parent issue -> FAIL
			r1 = issue_first_gate.evaluate_issue_first_events([_cw(1, 'tests/test_a.py', 'test')], project_root=proj)
			self.assertFalse(r1['verified'])
			self.assertTrue(any('ISSUE-FIRST-GATE' in v and 'test_a.py' in v for v in r1['violations']), r1['violations'])

			# 2. Test written at step 1, parent issue retroactively created at step 3 -> FAIL
			r2 = issue_first_gate.evaluate_issue_first_events(
				[_cw(1, 'tests/test_a.py', 'test'), _ia(3, 'create', 10, state='open')],
				project_root=proj,
			)
			self.assertFalse(r2['verified'])
			self.assertGreaterEqual(len(r2['violations']), 2, r2['violations'])
			self.assertTrue(any('AFTER code/test edits' in v for v in r2['violations']), r2['violations'])

			# 3. Same-step parallel create + write -> FAIL (must complete in strictly earlier step)
			r3 = issue_first_gate.evaluate_issue_first_events(
				[_ia(1, 'create', 10, state='open'), _cw(1, 'tests/test_a.py', 'test')],
				project_root=proj,
			)
			self.assertFalse(r3['verified'])

			# 4. Parent created -> test -> prod -> child created -> child closed -> next test under same open parent -> PASS
			r4 = issue_first_gate.evaluate_issue_first_events(
				[
					_ia(1, 'create', 10, state='open'),
					_cw(3, 'tests/test_a.py', 'test'),
					_cw(5, 'src/a.py', 'production'),
					_ia(6, 'create', 11, state='open', parent_number=10),
					_ia(8, 'close', 11, state='closed', parent_number=10),
					_cw(9, 'tests/test_b.py', 'test'),
				],
				project_root=proj,
			)
			self.assertTrue(r4['verified'], r4)

			# 5. Closing parent resets active state -> subsequent test edit without new parent FAILS
			r5 = issue_first_gate.evaluate_issue_first_events(
				[
					_ia(1, 'create', 10, state='open'),
					_cw(3, 'tests/test_a.py', 'test'),
					_ia(6, 'close', 10, state='closed'),
					_cw(8, 'tests/test_reg.py', 'test'),
				],
				project_root=proj,
			)
			self.assertFalse(r5['verified'])
			self.assertTrue(any('test_reg.py' in v for v in r5['violations']), r5['violations'])

			# 6. Closing parent -> opening NEW parent #15 -> regression test -> PASS
			r6 = issue_first_gate.evaluate_issue_first_events(
				[
					_ia(1, 'create', 10, state='open'),
					_cw(3, 'tests/test_a.py', 'test'),
					_ia(6, 'close', 10, state='closed'),
					_ia(7, 'create', 15, state='open'),
					_cw(9, 'tests/test_reg.py', 'test'),
				],
				project_root=proj,
			)
			self.assertTrue(r6['verified'], r6)

			# 7. Child created under CLOSED parent #9 -> FAIL
			r7 = issue_first_gate.evaluate_issue_first_events(
				[
					_ia(1, 'create', 12, state='open', parent_number=9),
					_cw(3, 'tests/test_c.py', 'test'),
				],
				project_root=proj,
			)
			self.assertFalse(r7['verified'])

			# 8. Child created under already-OPEN pre-existing parent #8 -> PASS
			r8 = issue_first_gate.evaluate_issue_first_events(
				[
					_ia(1, 'create', 13, state='open', parent_number=8),
					_cw(3, 'tests/test_d.py', 'test'),
				],
				project_root=proj,
			)
			self.assertTrue(r8['verified'], r8)

			# 9. Fetching CLOSED issue #9 does NOT unlock; fetching OPEN parent #8 DOES unlock
			r9_closed = issue_first_gate.evaluate_issue_first_events(
				[_ia(1, 'fetch', 9, state='closed'), _cw(3, 'tests/test_e.py', 'test')],
				project_root=proj,
			)
			self.assertFalse(r9_closed['verified'])

			r9_open = issue_first_gate.evaluate_issue_first_events(
				[_ia(1, 'fetch', 8, state='open'), _cw(3, 'tests/test_e.py', 'test')],
				project_root=proj,
			)
			self.assertTrue(r9_open['verified'], r9_open)

	def test_user_input_seeding_accepts_referenced_open_evidence_and_rejects_closed_or_unreferenced(self) -> None:
		with tempfile.TemporaryDirectory() as tmp:
			base = Path(tmp).resolve()
			proj = base / 'proj'
			code = proj / 'code'
			_init_git_repo(code, remote_url='https://github.com/acme/demo.git')
			_write_issue_evidence(proj, 'acme/demo', 20, state='open')
			_write_issue_evidence(proj, 'acme/demo', 21, state='closed')
			_write_issue_evidence(proj, 'acme/demo', 22, state='open')

			write_ev = [{
				'kind': 'code_write',
				'step': 1,
				'path': str(code / 'tests/test_app.py'),
				'rel_path': 'tests/test_app.py',
				'repo_root': str(code),
				'repo_slug': 'acme/demo',
				'classification': 'test',
			}]

			# Unreferenced open backlog issue #20 must NOT silently unlock
			res_unref = issue_first_gate.evaluate_issue_first_events(
				write_ev,
				requests=[{'text': 'Implement new feature X'}],
				project_root=proj,
			)
			self.assertFalse(res_unref['verified'])

			# Referenced CLOSED historical issue #21 must NOT unlock
			res_closed = issue_first_gate.evaluate_issue_first_events(
				write_ev,
				requests=[{'text': 'Follow pattern from https://github.com/acme/demo/issues/21 for new feature'}],
				project_root=proj,
			)
			self.assertFalse(res_closed['verified'])

			# Referenced OPEN parent issue #22 by URL unlocks
			res_url = issue_first_gate.evaluate_issue_first_events(
				write_ev,
				requests=[{'text': 'Fix https://github.com/acme/demo/issues/22'}],
				project_root=proj,
			)
			self.assertTrue(res_url['verified'], res_url)

			# Referenced OPEN parent issue #22 by #22 unlocks
			res_num = issue_first_gate.evaluate_issue_first_events(
				write_ev,
				requests=[{'text': 'Work on issue #22'}],
				project_root=proj,
			)
			self.assertTrue(res_num['verified'], res_num)

	def test_evaluate_pre_tool_use_issue_first_blocks_spoofing_and_enforces_live_order(self) -> None:
		with tempfile.TemporaryDirectory() as tmp:
			base = Path(tmp).resolve()
			proj = base / 'proj'
			(proj / '_/ꘖ/KB/Evidence/GitHub').mkdir(parents=True)
			code = proj / 'code'
			_init_git_repo(code, remote_url='https://github.com/acme/demo.git')
			test_f = code / 'tests/test_app.py'
			scratch_f = proj / '_/ꘖ/data/scratch/issue-body.md'
			tx = base / 'transcript.jsonl'

			# 1. Missing transcriptPath -> fail-closed DENY on test file
			err_no_tx = issue_first_gate.evaluate_pre_tool_use_issue_first(
				'write_file',
				{'Path': str(test_f), 'Content': 'def test_x(): assert True\n'},
				{'cwd': str(proj)},
			)
			self.assertIsNotNone(err_no_tx)
			self.assertIn('ISSUE-FIRST-GATE', err_no_tx)

			# 2. Scratch markdown file allowed before any issue
			self.assertIsNone(
				issue_first_gate.evaluate_pre_tool_use_issue_first(
					'write_file',
					{'Path': str(scratch_f), 'Content': '## Problem\nDetails.\n'},
					{'cwd': str(proj)},
				)
			)

			# 3. Spoofed echo JSON in transcript must NOT unlock Issue-First
			spoof_rows = [
				{'step_index': 0, 'type': 'USER_INPUT', 'content': 'Add feature'},
				{'step_index': 1, 'type': 'PLANNER_RESPONSE', 'tool_calls': [{'name': 'run_command', 'args': {'CommandLine': 'echo \'{"ok":true,"action":"create","repo":"acme/demo","number":99}\''}}]},
				{'step_index': 2, 'type': 'GENERIC', 'content': 'Command exited with code 0.\n\nCommand output:\n{"ok": true, "action": "create", "repo": "acme/demo", "number": 99}\n'},
			]
			tx.write_text(''.join(json.dumps(r) + '\n' for r in spoof_rows), encoding='utf-8')
			err_spoof = issue_first_gate.evaluate_pre_tool_use_issue_first(
				'write_file',
				{'Path': str(test_f), 'Content': 'def test_x(): assert True\n'},
				{'cwd': str(proj), 'transcriptPath': str(tx)},
			)
			self.assertIsNotNone(err_spoof)
			self.assertIn('ISSUE-FIRST-GATE', err_spoof)

			# 4. Shell write to test file before parent issue -> DENY
			err_shell = issue_first_gate.evaluate_pre_tool_use_issue_first(
				'run_command',
				{'CommandLine': f'Set-Content -Path "{test_f}" -Value "assert True"'},
				{'cwd': str(proj), 'transcriptPath': str(tx)},
			)
			self.assertIsNotNone(err_shell)
			self.assertIn('ISSUE-FIRST-GATE', err_shell)

			# 5. Real df_github_issue.py create output unlocks BOTH write_file and shell write to test file
			good_rows = [
				{'step_index': 0, 'type': 'USER_INPUT', 'content': 'Add feature'},
				{'step_index': 1, 'type': 'PLANNER_RESPONSE', 'tool_calls': [{'name': 'run_command', 'args': {'CommandLine': 'python scripts/df_github_issue.py create --repo acme/demo --title "Feature problem" --body-file b.md'}}]},
				{'step_index': 2, 'type': 'GENERIC', 'content': 'Command exited with code 0.\n\nCommand output:\n' + json.dumps({'ok': True, 'action': 'create', 'repo': 'acme/demo', 'number': 30, 'state': 'open', 'html_url': 'https://github.com/acme/demo/issues/30', 'verified': True}) + '\n'},
			]
			tx.write_text(''.join(json.dumps(r) + '\n' for r in good_rows), encoding='utf-8')
			self.assertIsNone(
				issue_first_gate.evaluate_pre_tool_use_issue_first(
					'write_file',
					{'Path': str(test_f), 'Content': 'def test_x(): assert True\n'},
					{'cwd': str(proj), 'transcriptPath': str(tx)},
				)
			)
			self.assertIsNone(
				issue_first_gate.evaluate_pre_tool_use_issue_first(
					'run_command',
					{'CommandLine': f'Set-Content -Path "{test_f}" -Value "assert True"'},
					{'cwd': str(proj), 'transcriptPath': str(tx)},
				)
			)


if '__main__' == __name__:
	unittest.main()
