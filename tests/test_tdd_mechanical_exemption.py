# 2026-11-25 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# https://github.com/dmitry-ai/harness/issues/239
from __future__ import annotations
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
SCRIPT_DIR = Path(__file__).resolve().parents[1] / 'scripts'
if str(SCRIPT_DIR) not in sys.path:
	sys.path.insert(0, str(SCRIPT_DIR))
from agent_tools import git_gate
from agent_tools.cli_registry import add_registered_parsers, execute_registered, registered_commands
from agent_tools.issues.auditor import TurnIssueLifecycleAuditor
import argparse
from agent_tools.tdd.enforcement import evaluate_pre_tool_use_tdd
from agent_tools.tdd.evaluator import evaluate_tdd_events
from agent_tools.tdd.events import build_file_write_tdd_event
from agent_tools.tdd.mechanical import matches_mechanical_recipe, record_mechanical_exemption, validate_mechanical_reason
ISSUE_URL = 'https://github.com/example-org/legacy-app/issues/42'
OTHER_ISSUE_URL = 'https://github.com/example-org/legacy-app/issues/99'
OLD_URL = 'https://upwork.com/fl/mage2pro'
NEW_URL = 'https://github.com/dmitrii-fediuk'
VALID_REASON = 'Bulk mechanical author profile URL replacement requested in user instruction 252 and tracked in issue #42.'
def _git(*args: str) -> None:
	subprocess.run(['git', *args], check=True, stdin=subprocess.DEVNULL, capture_output=True, timeout=30)
def _init_repo(repo: Path, remote_url: str='https://github.com/example-org/legacy-app.git') -> None:
	repo.mkdir(parents=True, exist_ok=True)
	_git('init', '-b', 'main', str(repo))
	cfg = repo / '.git/config'
	extra = (
		'[user]\n\temail = test@example.com\n\tname = Test User\n'
		f'[remote "origin"]\n\turl = {remote_url}\n\tfetch = +refs/heads/*:refs/remotes/origin/*\n'
	)
	cfg.write_text(cfg.read_text(encoding='utf-8') + extra, encoding='utf-8')
def _seed_commit(repo: Path, rel: str, content: str) -> None:
	target = repo / rel
	target.parent.mkdir(parents=True, exist_ok=True)
	target.write_text(content, encoding='utf-8')
	_git('-C', str(repo), 'add', rel)
	_git('-C', str(repo), 'commit', '--no-verify', '-m', 'seed')
class MechanicalExemptionTests(unittest.TestCase):
	def test_auditor_and_evaluator_accept_committed_mechanical_diff_and_reject_drift(self) -> None:
		with tempfile.TemporaryDirectory() as tmp:
			proj = Path(tmp).resolve() / 'proj'
			repo = proj / 'code'
			(proj / '_').mkdir(parents=True)
			(proj / 'ꘖ/data/turns').mkdir(parents=True)
			_init_repo(repo)
			_seed_commit(repo, 'src/cfg.js', f"export const HOME = '{OLD_URL}';\n")
			record_mechanical_exemption(proj, repo=repo, issue_url=ISSUE_URL, pattern=OLD_URL, replacement=NEW_URL, reason=VALID_REASON, turn_key='turn-aud')
			(repo / 'src/cfg.js').write_text(f"export const HOME = '{NEW_URL}';\n", encoding='utf-8')
			_git('-C', str(repo), 'add', 'src/cfg.js')
			_git('-C', str(repo), 'commit', '--no-verify', '-m', ISSUE_URL)
			aud = TurnIssueLifecycleAuditor(proj, {'touched_files': [str(repo / 'src/cfg.js')]}, None)
			aud._inspect_touched_code_file(repo, 'src/cfg.js', set(), set())
			self.assertEqual([], aud.violations)
			ev = build_file_write_tdd_event(1, repo / 'src/cfg.js', cwd=repo)
			res_ok = evaluate_tdd_events([ev], require_final_full_green=True, project_root=proj)
			self.assertTrue(res_ok['verified'], res_ok)
			(repo / 'src/cfg.js').write_text(f"export const HOME = '{NEW_URL}';\nexport const X = 1;\n", encoding='utf-8')
			res_bad = evaluate_tdd_events([ev], require_final_full_green=True, project_root=proj)
			self.assertFalse(res_bad['verified'], res_bad)
	def test_cli_parser_dispatches_tdd_exempt_mechanical_with_turn_key(self) -> None:
		with tempfile.TemporaryDirectory() as tmp:
			proj = Path(tmp).resolve() / 'proj'
			repo = proj / 'repo'
			(proj / 'ꘖ/data/turns').mkdir(parents=True)
			_init_repo(repo)
			parser = argparse.ArgumentParser()
			sub = parser.add_subparsers(dest='command', required=True)
			add_registered_parsers(sub)
			args = parser.parse_args([
				'tdd-exempt-mechanical', str(proj), '--repo', str(repo),
				'--issue', ISSUE_URL, '--pattern', OLD_URL, '--replacement', NEW_URL,
				'--reason', VALID_REASON, '--turn-key', 'cli-turn-1',
			])
			handled, res, _ = execute_registered(args)
			self.assertTrue(handled)
			self.assertTrue(res['valid'])
			self.assertEqual('cli-turn-1', res['turn_key'])
	def test_cli_registration_and_validation_errors(self) -> None:
		self.assertIn('tdd-exempt-mechanical', registered_commands())
		self.assertFalse(validate_mechanical_reason('too short')[0])
		self.assertFalse(validate_mechanical_reason('bypass tdd gate because I want to skip writing tests quickly')[0])
		self.assertTrue(validate_mechanical_reason(VALID_REASON)[0])
		with tempfile.TemporaryDirectory() as tmp:
			proj = Path(tmp).resolve() / 'proj'
			repo = proj / 'repo'
			(proj / 'ꘖ/data/turns').mkdir(parents=True)
			_init_repo(repo)
			with self.assertRaises(ValueError):
				record_mechanical_exemption(proj, repo=repo, issue_url='not-a-url', pattern=OLD_URL, replacement=NEW_URL, reason=VALID_REASON, turn_key='t1')
			with self.assertRaises(ValueError):
				record_mechanical_exemption(proj, repo=repo, issue_url=ISSUE_URL, pattern='', replacement=NEW_URL, reason=VALID_REASON, turn_key='t1')
			with self.assertRaises(ValueError):
				record_mechanical_exemption(proj, repo=repo, issue_url=ISSUE_URL, pattern=OLD_URL, replacement=OLD_URL, reason=VALID_REASON, turn_key='t1')
			with self.assertRaises(ValueError):
				record_mechanical_exemption(proj, repo=repo, issue_url='https://github.com/other/repo/issues/1', pattern=OLD_URL, replacement=NEW_URL, reason=VALID_REASON, turn_key='t1')
	def test_git_gate_enforces_exact_recipe_issue_binding_and_mixed_m2_commit(self) -> None:
		with tempfile.TemporaryDirectory() as tmp:
			proj = Path(tmp).resolve() / 'proj'
			repo = proj / 'repo'
			(proj / 'ꘖ/data/turns').mkdir(parents=True)
			_init_repo(repo)
			_seed_commit(repo, 'src/cfg.php', f"<?php\nreturn '{OLD_URL}';\n")
			_seed_commit(repo, 'src/lib.rs', f'// {OLD_URL}\nfn url() -> &str {{ "{OLD_URL}" }}\n')
			_seed_commit(repo, 'src/hdr.js', f'// header {OLD_URL}\nconst a = 1;\n')
			record_mechanical_exemption(proj, repo=repo, issue_url=ISSUE_URL, pattern=r'https?://(?:www\.)?upwork\.com/fl/mage2pro', replacement=NEW_URL, reason=VALID_REASON, is_regex=True, ignore_case=True, turn_key='t-git')
			(repo / 'src/cfg.php').write_text(f"<?php\nreturn '{NEW_URL}';\n", encoding='utf-8')
			(repo / 'src/lib.rs').write_text(f'// {NEW_URL}\nfn url() -> &str {{ "{NEW_URL}" }}\n', encoding='utf-8')
			(repo / 'src/hdr.js').write_text(f'// header {NEW_URL}\nconst a = 1;\n', encoding='utf-8')
			_git('-C', str(repo), 'add', 'src/cfg.php', 'src/lib.rs', 'src/hdr.js')
			self.assertEqual(0, git_gate.run_git_hook('pre-commit', cwd=repo, agent_context=True))
			git_gate.verify_git_write_invocation(['-C', str(repo), 'commit', '-m', ISSUE_URL], agent_context=True)
			with self.assertRaisesRegex(ValueError, 'TDD-COMMIT-GATE'):
				git_gate.verify_git_write_invocation(['-C', str(repo), 'commit', '-m', OTHER_ISSUE_URL], agent_context=True)
			(repo / 'src/cfg.php').write_text(f"<?php\nreturn '{NEW_URL}';\n$extra = 1;\n", encoding='utf-8')
			_git('-C', str(repo), 'add', 'src/cfg.php')
			self.assertEqual(2, git_gate.run_git_hook('pre-commit', cwd=repo, agent_context=True))
	def test_matches_mechanical_recipe_strict_line_identity(self) -> None:
		lit = {'ignore_case': False, 'is_regex': False, 'pattern': OLD_URL, 'replacement': NEW_URL}
		rx = {'ignore_case': True, 'is_regex': True, 'pattern': r'https?://(?:www\.)?upwork\.com/fl/mage2pro', 'replacement': NEW_URL}
		self.assertTrue(matches_mechanical_recipe(f"a = '{OLD_URL}'\nb = '{OLD_URL}'\n", f"a = '{NEW_URL}'\nb = '{NEW_URL}'\n", lit))
		self.assertTrue(matches_mechanical_recipe(f"a = 'http://www.UPWORK.com/fl/mage2pro'\n", f"a = '{NEW_URL}'\n", rx))
		self.assertFalse(matches_mechanical_recipe(f"a = '{OLD_URL}'; x = 1\n", f"a = '{NEW_URL}'; x = 2\n", lit))
		self.assertFalse(matches_mechanical_recipe(f"a = '{OLD_URL}'\n", f"a = '{NEW_URL}'\nextra = 1\n", lit))
		self.assertFalse(matches_mechanical_recipe(None, f"a = '{NEW_URL}'\n", lit))
		self.assertFalse(matches_mechanical_recipe(f"a = '{OLD_URL}'\n", None, lit))
	def test_pre_tool_use_allows_matching_mechanical_edit_and_denies_extraneous_edit(self) -> None:
		with tempfile.TemporaryDirectory() as tmp:
			proj = Path(tmp).resolve() / 'proj'
			repo = proj / 'repo'
			(proj / 'ꘖ/data/turns').mkdir(parents=True)
			_init_repo(repo)
			_seed_commit(repo, 'src/lib.rs', f'fn u() -> &str {{ "{OLD_URL}" }}\n')
			record_mechanical_exemption(proj, repo=repo, issue_url=ISSUE_URL, pattern=OLD_URL, replacement=NEW_URL, reason=VALID_REASON, turn_key='t-pre')
			ok_err = evaluate_pre_tool_use_tdd(
				'edit_file',
				{'Path': str(repo / 'src/lib.rs'), 'Target': OLD_URL, 'Replacement': NEW_URL},
				{'cwd': str(proj)},
			)
			self.assertIsNone(ok_err)
			bad_err = evaluate_pre_tool_use_tdd(
				'edit_file',
				{'Path': str(repo / 'src/lib.rs'), 'Target': f'fn u() -> &str {{ "{OLD_URL}" }}', 'Replacement': f'fn v() -> &str {{ "{NEW_URL}" }}'},
				{'cwd': str(proj)},
			)
			self.assertIsNotNone(bad_err)
			self.assertIn('TDD-RED-GATE', str(bad_err))
if '__main__' == __name__:
	unittest.main()
