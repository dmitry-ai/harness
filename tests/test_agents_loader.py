# 2026-10-23 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from typing import override
import json
import shutil
import tomllib
from git_fixture_cache import clone_template_git_repo
from test_agent_tools import TemporaryCase
from agent_tools import configuration, runtime
# 2026-10-23
# "Implement turn-completion contract, journal watcher, primary source admission, and Codex root AGENTS.md loader":
# https://github.com/dmitry-ai/harness/issues/16
# 2026-10-31
# "Reorganize AI into universal harness repository, translate rules and documentation to English, format per P.md, and enforce issue-driven Git workflow":
# https://github.com/dmitry-ai/harness/issues/26
class AgentsLoaderTests(TemporaryCase):
	# 2026-11-26
	# "Apply cross-reference annotations across Harness Python and JavaScript":
	# https://github.com/dmitry-ai/harness/issues/305
	# @used-by :mod:`unittest`
	# @see :meth:`test_agent_tools.TemporaryCase.setUp()`
	@override
	def setUp(self):
		super().setUp()
		self.primary = self.root / 'canonical'
		for relative in ('rules', 'platforms', 'skills/upwork-init', 'agents'):
			(self.primary / relative).mkdir(parents=True, exist_ok=True)
		for path in runtime.PRIMARY.joinpath('rules').glob('*.md'):
			shutil.copyfile(path, self.primary / 'rules' / path.name)
		for relative in ('runtime.json', 'platforms/codex.md', 'skills/upwork-init/SKILL.md', 'agents/worker.md'):
			shutil.copyfile(runtime.PRIMARY / relative, self.primary / relative)
		self.output = self.root / 'workspace'
	# @used-by :meth:`AgentsLoaderTests.test_check_detects_missing_guidance_without_writing_and_build_repairs_it()`
	# @used-by :meth:`AgentsLoaderTests.test_edit_to_generated_guidance_blocks_other_pending_configuration_updates()`
	# @used-by :meth:`AgentsLoaderTests.test_existing_unowned_guidance_is_preserved_without_partial_installation()`
	# @used-by :meth:`AgentsLoaderTests.test_guidance_uses_current_canonical_loader_without_copying_rule_bodies()`
	# @used-by :meth:`AgentsLoaderTests.test_new_source_path_updates_guidance_and_existing_toml_together()`
	def build(self, *, check=False):
		return configuration.build_native(self.output, primary=self.primary, check=check)
	# @used-by :meth:`AgentsLoaderTests.test_check_detects_missing_guidance_without_writing_and_build_repairs_it()`
	# @used-by :meth:`AgentsLoaderTests.test_edit_to_generated_guidance_blocks_other_pending_configuration_updates()`
	# @used-by :meth:`AgentsLoaderTests.test_existing_unowned_guidance_is_preserved_without_partial_installation()`
	# @used-by :meth:`AgentsLoaderTests.test_new_source_path_updates_guidance_and_existing_toml_together()`
	def snapshot(self):
		return {p.relative_to(self.output).as_posix(): p.read_bytes() for p in self.output.rglob('*') if p.is_file() and 'ꘖ/data/native-config.lock' != p.relative_to(self.output).as_posix()}
	# @used-by :mod:`unittest`
	def test_guidance_uses_current_canonical_loader_without_copying_rule_bodies(self):
		rule = self.primary / 'rules/90-loader-test.md'
		rule.write_text('CANONICAL BODY MUST STAY IN ITS SOURCE\n', encoding='utf-8')
		result = self.build()
		self.assertTrue(result['valid'], result)
		guidance = self.output / 'AGENTS.md'
		text = guidance.read_text(encoding='utf-8')
		for source in [*self.primary.joinpath('rules').glob('*.md'), self.primary / 'platforms/codex.md']:
			self.assertIn(source.as_posix(), text)
		self.assertIn('.agents/rules/*.md', text)
		self.assertIn('.agents/rules.json', text)
		self.assertIn('turn-begin', text)
		self.assertIn('answer-prepare', text)
		# 2026-10-24
		# "Enforce Git --no-optional-locks read gate, add git_shim.py wrapper, and add PreToolUse rules budget and server hygiene gates":
		# https://github.com/dmitry-ai/harness/issues/17
		self.assertIn('--no-optional-locks', text)
		self.assertIn('git-read', text)
		self.assertNotIn('CANONICAL BODY MUST STAY IN ITS SOURCE', text)
		native = tomllib.loads((self.output / '.codex/config.toml').read_text(encoding='utf-8'))
		loader = native['developer_instructions'].split(configuration.START, 1)[1]
		loader = loader.split(configuration.END, 1)[0].strip()
		self.assertIn(loader, text)
		# 2026-10-24
		# "Enforce Git --no-optional-locks read gate, add git_shim.py wrapper, and add PreToolUse rules budget and server hygiene gates":
		# https://github.com/dmitry-ai/harness/issues/17
		self.assertIn('--no-optional-locks', loader)
		receipt = json.loads((self.output / 'ꘖ/data/native-config.json').read_text(encoding='utf-8'))
		self.assertEqual(receipt[str(guidance.resolve())], configuration._digest(guidance.read_bytes()))
	# @used-by :mod:`unittest`
	def test_check_detects_missing_guidance_without_writing_and_build_repairs_it(self):
		self.assertTrue(self.build()['valid'])
		guidance = self.output / 'AGENTS.md'
		wanted = guidance.read_bytes()
		guidance.unlink()
		before = self.snapshot()
		result = self.build(check=True)
		self.assertFalse(result['valid'])
		self.assertTrue(any((item['file'] == str(guidance.resolve()) for item in result['issues'])))
		self.assertEqual(self.snapshot(), before)
		self.assertTrue(self.build()['valid'])
		self.assertEqual(guidance.read_bytes(), wanted)
		self.assertTrue(self.build(check=True)['valid'])
		self.assertEqual(self.build()['written'], [])
	# @used-by :mod:`unittest`
	def test_existing_unowned_guidance_is_preserved_without_partial_installation(self):
		self.output.mkdir()
		guidance = self.output / 'AGENTS.md'
		guidance.write_bytes(b'User rules\r\nKeep exact bytes.\r\n')
		before = self.snapshot()
		result = self.build()
		self.assertFalse(result['valid'])
		self.assertEqual(self.snapshot(), before)
		self.assertFalse((self.primary / 'agents/af-worker.md').exists())
	# @used-by :mod:`unittest`
	def test_edit_to_generated_guidance_blocks_other_pending_configuration_updates(self):
		self.assertTrue(self.build()['valid'])
		guidance = self.output / 'AGENTS.md'
		guidance.write_bytes(guidance.read_bytes() + b'\nManual user addition.\n')
		(self.primary / 'rules/91-new.md').write_text('New rule.\n', encoding='utf-8')
		before = self.snapshot()
		result = self.build()
		self.assertFalse(result['valid'])
		self.assertEqual(self.snapshot(), before)
		self.assertTrue(any((item['file'] == str(guidance.resolve()) for item in result['issues'])))
	# @used-by :mod:`unittest`
	def test_new_source_path_updates_guidance_and_existing_toml_together(self):
		self.assertTrue(self.build()['valid'])
		rule = self.primary / 'rules/91-new.md'
		rule.write_text('Read this policy by reference.\n', encoding='utf-8')
		before = self.snapshot()
		self.assertFalse(self.build(check=True)['valid'])
		self.assertEqual(self.snapshot(), before)
		self.assertTrue(self.build()['valid'])
		self.assertIn(rule.as_posix(), (self.output / 'AGENTS.md').read_text(encoding='utf-8'))
		native = tomllib.loads((self.output / '.codex/config.toml').read_text(encoding='utf-8'))
		self.assertIn(rule.as_posix(), native['developer_instructions'])
		self.assertTrue(self.build(check=True)['valid'])
	# 2026-10-24
	# "Enforce Git --no-optional-locks read gate, add git_shim.py wrapper, and add PreToolUse rules budget and server hygiene gates":
	# https://github.com/dmitry-ai/harness/issues/17
	# @used-by :mod:`unittest`
	def test_read_git_and_git_shim_and_unflagged_detector(self):
		from agent_tools import git_gate
		import git_shim
		repo = self.root / 'repo'
		# 2026-11-26 "Cache template Git repositories and in-process CLI helpers in slow test fixtures": https://github.com/dmitry-ai/harness/issues/355
		clone_template_git_repo(repo)
		(repo / 'README.md').write_text('hello\n', encoding='utf-8')
		res = git_gate.read_git(repo, 'status', ['--short'])
		self.assertTrue(res['valid'], res)
		self.assertEqual(res['command'][:3], ['git', '--no-optional-locks', '-C'])
		self.assertEqual(res['git_optional_locks'], '0')
		with self.assertRaises(ValueError):
			git_gate.read_git(repo, 'commit', ['-m', 'x'])
		self.assertEqual(git_shim.prepare_git_invocation(['status', '--short'], mode='inject')[0], ['--no-optional-locks', 'status', '--short'])
		with self.assertRaises(ValueError):
			git_shim.prepare_git_invocation(['status', '--short'], mode='reject')
		violations = git_gate.unflagged_git_read_commands('git status --short && git --no-optional-locks diff --stat && git -C "C:/repo" log -1')
		self.assertEqual(len(violations), 2)
		self.assertIn('git status --short', violations[0])
		self.assertIn('git -C "C:/repo" log -1', violations[1])
	# 2026-10-31
	# "Reorganize AI into universal harness repository, translate rules and documentation to English, format per P.md, and enforce issue-driven Git workflow":
	# https://github.com/dmitry-ai/harness/issues/26
	# @used-by :mod:`unittest`
	def test_issue_tracked_code_repo_requires_github_issue_url_in_code_and_commit_message(self):
		from agent_tools import git_gate
		import git_shim
		import subprocess
		project = self.root / 'tracked_project'
		code_repo = project / 'code'
		(project / '_').mkdir(parents=True)
		(project / '.agents').mkdir(parents=True)
		# 2026-11-26 "Cache template Git repositories and in-process CLI helpers in slow test fixtures": https://github.com/dmitry-ai/harness/issues/355
		clone_template_git_repo(code_repo)
		self.assertTrue(git_gate.is_issue_tracked_code_repo(code_repo))
		script = code_repo / 'mod.py'
		script.write_text('x = 1\n', encoding='utf-8')
		subprocess.run(['git', 'add', 'mod.py'], cwd=code_repo, check=True, capture_output=True)
		with self.assertRaisesRegex(ValueError, 'Issue-tracked code file lacks a GitHub Issue URL'):
			git_gate.check_commit(code_repo, ['mod.py'])
		script.write_text('# https://github.com/dmitry-ai/harness/issues/26\nx = 1\n', encoding='utf-8')
		subprocess.run(['git', 'add', 'mod.py'], cwd=code_repo, check=True, capture_output=True)
		# 2026-11-23
		# "Enforce TDD test coverage and ratchet in Git pre-commit gate":
		# https://github.com/dmitry-ai/harness/issues/137
		with self.assertRaisesRegex(ValueError, 'TDD-COMMIT-GATE'):
			git_gate.check_commit(code_repo, ['mod.py'])
		test_mod = code_repo / 'tests/test_mod.py'
		test_mod.parent.mkdir(parents=True, exist_ok=True)
		test_mod.write_text('# https://github.com/dmitry-ai/harness/issues/26\nimport unittest\nclass T(unittest.TestCase):\n\tdef test_x(self):\n\t\tself.assertEqual(1, 1)\n', encoding='utf-8')
		subprocess.run(['git', 'add', 'tests/test_mod.py'], cwd=code_repo, check=True, capture_output=True)
		self.assertEqual(git_gate.check_commit(code_repo, ['mod.py', 'tests/test_mod.py']), ['mod.py', 'tests/test_mod.py'])
		# 2026-10-31
		# "Enforce EXEC-5 code/issue lifecycle gate in answer-prepare, URL-only commit messages, git_shim/hook commit interception, and worktree isolation":
		# https://github.com/dmitry-ai/harness/issues/31
		# 2026-11-02
		# "Enforce GitHub Issue URL commit requirement across all repositories for agents while exempting human user commits by invocation context":
		# https://github.com/dmitry-ai/harness/issues/39
		with self.assertRaisesRegex(ValueError, 'Commit message for an agent commit must contain only the GitHub Issue URL'):
			git_gate.commit(code_repo, ['mod.py', 'tests/test_mod.py'], 'Missing issue URL', execute=False)
		with self.assertRaisesRegex(ValueError, 'Commit message for an agent commit must contain only the GitHub Issue URL'):
			git_gate.commit(code_repo, ['mod.py', 'tests/test_mod.py'], 'Fix\n\nhttps://github.com/dmitry-ai/harness/issues/26', execute=False)
		with self.assertRaisesRegex(ValueError, 'Issue-tracked code file mod.py does not reference the commit GitHub Issue URL'):
			git_gate.commit(code_repo, ['mod.py', 'tests/test_mod.py'], 'https://github.com/dmitry-ai/harness/issues/31', execute=False)
		self.assertEqual(git_gate.commit(code_repo, ['mod.py', 'tests/test_mod.py'], 'https://github.com/dmitry-ai/harness/issues/26', execute=True), ['mod.py', 'tests/test_mod.py'])
		with self.assertRaisesRegex(ValueError, 'git commit --no-verify/-n is prohibited'):
			git_shim.prepare_git_invocation(['commit', '--no-verify', '-m', 'https://github.com/dmitry-ai/harness/issues/26'], cwd=code_repo)
		self.assertEqual(len(git_gate.prohibited_git_write_commands('git commit --no-verify -m "x" && git filter-branch -f')), 3)
		script.write_text('# https://github.com/dmitry-ai/harness/issues/26\nx = 2\n', encoding='utf-8')
		test_mod.write_text('# https://github.com/dmitry-ai/harness/issues/26\nimport unittest\nclass T(unittest.TestCase):\n\tdef test_x(self):\n\t\tself.assertEqual(1, 1)\n\tdef test_x2(self):\n\t\tself.assertEqual(2, 2)\n', encoding='utf-8')
		subprocess.run(['git', 'add', 'mod.py', 'tests/test_mod.py'], cwd=code_repo, check=True, capture_output=True)
		dirty_other = code_repo / 'dirty.py'
		dirty_other.write_text('# https://github.com/dmitry-ai/harness/issues/99\ny = 2\n', encoding='utf-8')
		subprocess.run(['git', 'add', 'dirty.py'], cwd=code_repo, check=True, capture_output=True)
		with self.assertRaisesRegex(ValueError, 'Staged paths differ from explicit paths'):
			git_gate.commit(code_repo, ['mod.py', 'tests/test_mod.py'], 'https://github.com/dmitry-ai/harness/issues/26', execute=False, worktree=False)
		committed = git_gate.commit(code_repo, ['mod.py', 'tests/test_mod.py'], 'https://github.com/dmitry-ai/harness/issues/26', execute=True, worktree=True)
		self.assertEqual(committed, ['mod.py', 'tests/test_mod.py'])
		log_msg = subprocess.run(['git', '--no-optional-locks', 'log', '-1', '--format=%B'], cwd=code_repo, check=True, capture_output=True, text=True).stdout.strip()
		self.assertEqual(log_msg, 'https://github.com/dmitry-ai/harness/issues/26')
		self.assertTrue(dirty_other.exists())
	# 2026-11-14
	# "Decompose git_gate.py into shell_audit.py, GitRepoGate, and single-pass pre-commit validation":
	# https://github.com/dmitry-ai/harness/issues/67
	# @used-by :mod:`unittest`
	def test_shell_audit_inspector_and_single_pass_repo_gate_commit(self):
		import subprocess
		from unittest.mock import patch
		from agent_tools import git_gate, shell_audit
		self.assertNotIn('subprocess', shell_audit.__dict__)
		inspector = shell_audit.ShellCommandInspector()
		self.assertEqual(inspector.unpersisted_http_fetch_commands('curl https://example.com/a'), ['curl https://example.com/a'])
		self.assertEqual(inspector.unpersisted_http_fetch_commands('python harness.py collect-http p https://example.com/a'), [])
		self.assertEqual(shell_audit.normalize_commit_message('# comment\nhttps://github.com/dmitry-ai/harness/issues/67\n# trailing'), 'https://github.com/dmitry-ai/harness/issues/67')
		actions = inspector.extract_issue_actions(['{"ok": true, "action": "edit", "repo": "dmitry-ai/harness", "number": 67, "state": "open"}'])
		self.assertEqual(1, len(actions))
		self.assertEqual(67, actions[0]['number'])
		# 2026-11-18
		# "Ignore source-code search and file-viewer lines in ShellCommandInspector.extract_issue_actions":
		# https://github.com/dmitry-ai/harness/issues/88
		grep_out = 'code\\tests\\test_agents_loader.py:177:\t\tactions = inspector.extract_issue_actions([\'{"ok": true, "action": "edit", "repo": "dmitry-ai/harness", "number": 67, "state": "open"}\'])'
		self.assertEqual([], inspector.extract_issue_actions([grep_out]))
		viewer_out = 'Showing lines 165-190 of 201\n177: \t\tactions = inspector.extract_issue_actions([\'{"ok": true, "action": "edit", "repo": "dmitry-ai/harness", "number": 67, "state": "open"}\'])'
		self.assertEqual([], inspector.extract_issue_actions([viewer_out]))
		multi_out = '{\n  "ok": true,\n  "action": "create",\n  "repo": "dmitry-ai/harness",\n  "number": 88,\n  "parent_number": 82\n}\n{\n  "ok": true,\n  "action": "close",\n  "repo": "dmitry-ai/harness",\n  "number": 88,\n  "state": "closed"\n}\n'
		multi_actions = inspector.extract_issue_actions([multi_out])
		self.assertEqual(2, len(multi_actions))
		self.assertEqual(82, multi_actions[0].get('parent_number'))
		self.assertEqual('closed', multi_actions[1].get('state'))
		code_repo = self.root / 'sp_proj/code'
		(self.root / 'sp_proj/_').mkdir(parents=True)
		# 2026-11-26 "Cache template Git repositories and in-process CLI helpers in slow test fixtures": https://github.com/dmitry-ai/harness/issues/355
		clone_template_git_repo(code_repo)
		mod = code_repo / 'mod.py'
		mod.write_text('# https://github.com/dmitry-ai/harness/issues/67\nx = 1\n', encoding='utf-8')
		# 2026-11-23
		# "Enforce TDD test coverage and ratchet in Git pre-commit gate":
		# https://github.com/dmitry-ai/harness/issues/137
		sp_test = code_repo / 'tests/test_mod.py'
		sp_test.parent.mkdir(parents=True, exist_ok=True)
		sp_test.write_text('# https://github.com/dmitry-ai/harness/issues/67\nimport unittest\nclass T(unittest.TestCase):\n\tdef test_ok(self):\n\t\tself.assertEqual(1, 1)\n', encoding='utf-8')
		subprocess.run(['git', 'add', 'mod.py', 'tests/test_mod.py'], cwd=code_repo, check=True, capture_output=True)
		gate = git_gate.GitRepoGate(code_repo, strict=True)
		gate.verify_issue_workflow(['mod.py', 'tests/test_mod.py'], message='https://github.com/dmitry-ai/harness/issues/67\n# git comment')
		with self.assertRaisesRegex(ValueError, 'Commit message for an agent commit must contain only the GitHub Issue URL'):
			gate.verify_issue_workflow(['mod.py', 'tests/test_mod.py'], message='# https://github.com/dmitry-ai/harness/issues/67')
		calls = []
		orig_check = git_gate.GitRepoGate.check_commit
		# @used-by :meth:`AgentsLoaderTests.test_shell_audit_inspector_and_single_pass_repo_gate_commit()`
		def spy_check(inst, paths, *, message=None):
			calls.append((inst.root, list(paths), message))
			return orig_check(inst, paths, message=message)
		with patch.object(git_gate.GitRepoGate, 'check_commit', spy_check):
			gate.commit(['mod.py', 'tests/test_mod.py'], 'https://github.com/dmitry-ai/harness/issues/67', execute=True)
		self.assertEqual(1, len(calls))
		self.assertEqual('https://github.com/dmitry-ai/harness/issues/67', calls[0][2])
