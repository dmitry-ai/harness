# 2026-10-30 Dmitrii Fediuk https://github.com/dmitrii-fediuk
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from agent_tools.github_issue import has_enumerated_slop_title, lint_issue_markdown, main
# 2026-11-26 "Enforce pushed Git tags on issue-closing commits in lifecycle gates": https://github.com/dmitry-ai/harness/issues/263
from agent_tools.repo_tags import ensure_commit_tag
# 2026-10-30
# "Implement /df-github-issue skill and df_github_issue.py CLI with UTF-8 file input and mandatory API read-back verification":
# https://github.com/dmitry-ai/harness/issues/20
# 2026-10-31
# "Reorganize AI into universal harness repository, translate rules and documentation to English, format per P.md, and enforce issue-driven Git workflow":
# https://github.com/dmitry-ai/harness/issues/26
class TestGitHubIssueTool(unittest.TestCase):
	def test_clean_markdown_passes(self):
		clean = '## 1. Root Cause\nIn `Magento\\PageCache\\Model\\Cache\\Warmer` (`vendor/magento/module-page-cache/Model/Cache/Warmer.php`, lines 122–125 — see §6.1):\n```php\n$identifier = $this->cookieManager->getCookie(\'affiliate_identifier\') ?: null;\nif ($identifier && $this->customerSession->getId()) {\n    $this->accountService->ensureCustomerRelation((string)$identifier, `0`);\n}\n```\n```xml\n    <type name="Magento\\Framework\\Data\\Form\\FormKey">\n        <arguments>\n            <argument name="session" xsi:type="object">Magento\\Framework\\Session\\Generic\\Proxy</argument>\n        </arguments>\n    </type>\n```\nPaginated URLs like `/water-pipes.html?p=2` work across «Customers» in `0.131–0.325` seconds.\n'
		self.assertEqual(lint_issue_markdown(clean), [])
	def test_detects_all_seven_powershell_corruption_classes(self):
		errs_a = lint_issue_markdown('### Problem\nOut of Stock (\\')
		codes_a = {e['code'] for e in errs_a}
		self.assertIn('TRUNCATED_END', codes_a)
		errs_nul = lint_issue_markdown('### Problem\nversion \x000.0.1')
		self.assertIn('CONTROL_CHAR', {e['code'] for e in errs_nul})
		errs_b = lint_issue_markdown('### Problem\nIn (\x0bendor/magento) and (\true) and (\\x08in/magento)')
		codes_b = {e['code'] for e in errs_b}
		self.assertIn('CONTROL_CHAR', codes_b)
		self.assertIn('INLINE_TAB_ESCAPE', codes_b)
		errs_c1 = lint_issue_markdown('### Problem\nRun \\bin/magento page-cache:warm\\ to warm `cache`.')
		self.assertIn('BACKSLASH_WRAPPED_CODE', {e['code'] for e in errs_c1})
		errs_c2 = lint_issue_markdown('### Problem\n`Mirasvit` calls:\n``php\n$x = 1;\n``\n')
		self.assertIn('BROKEN_CODE_FENCE', {e['code'] for e in errs_c2})
		errs_c3 = lint_issue_markdown('### Problem\n' + 'In vendor/magento/module-page-cache/Model/Cache/Warmer.php::execute() ' * 4)
		self.assertIn('STRIPPED_ALL_BACKTICKS', {e['code'] for e in errs_c3})
		errs_d = lint_issue_markdown('### Problem\nWhen `!->shouldRedirectToCart()`, call `->updateCache(, )` and `empty()` or `(?callable  = null)`.')
		codes_d = {e['code'] for e in errs_d}
		self.assertIn('EATEN_VARIABLE_ARROW', codes_d)
		self.assertIn('EATEN_VARIABLE_ARG', codes_d)
		errs_e = lint_issue_markdown('### Problem\nTakes `43?45` seconds on every request?even when rows ? causing `?Customers?` in ?6.1.')
		codes_e = {e['code'] for e in errs_e}
		self.assertIn('QUESTION_MARK_RANGE', codes_e)
		self.assertIn('QUESTION_MARK_WORD_JOIN', codes_e)
		self.assertIn('QUESTION_MARK_SPACED', codes_e)
		self.assertIn('QUESTION_MARK_QUOTES', codes_e)
		self.assertIn('QUESTION_MARK_SECTION', codes_e)
		errs_f = lint_issue_markdown('\ufeff### Problem\nValid `code` here.')
		self.assertIn('UTF8_BOM', {e['code'] for e in errs_f})
		errs_g = lint_issue_markdown('### Problem\n```xml\n<type name=Magento\\Framework\\Data\\Form\\FormKey>\n<argument name=session xsi:type=object>Proxy</argument>\n</type>\n```')
		self.assertIn('UNQUOTED_XML_ATTR', {e['code'] for e in errs_g})
	def test_create_and_consume_input_with_readback_verification(self):
		with tempfile.TemporaryDirectory() as tmp:
			body_path = Path(tmp) / 'body.md'
			body_text = '## Summary\nFix `Magento\\Framework\\Data\\Form\\FormKey` in lines 10–20.\n'
			body_path.write_text(body_text, encoding='utf-8', newline='\n')
			# 2026-11-23
			# "Prepend structured JSON metadata header to new GitHub issues in df_github_issue.py":
			# https://github.com/dmitry-ai/harness/issues/150
			stored = {'number': 46, 'title': 'Test issue title', 'body': body_text, 'html_url': 'https://github.com/smokeday-com/m/issues/46'}
			# 2026-11-03
			# "Replace persistent journal daemon with foreground-only idempotent reconciliation":
			# https://github.com/dmitry-ai/harness/issues/41
			def fake_run(cmd, *, input=None, capture_output=True, check=False, creationflags=None):
				self.assertEqual(creationflags, getattr(subprocess, 'CREATE_NO_WINDOW', 0))
				class DummyProc:
					returncode = 0
					stderr = b''
					stdout = b''
				proc = DummyProc()
				if '-X' in cmd and 'POST' in cmd:
					payload = json.loads(input.decode('utf-8'))
					stored['title'] = payload['title']
					stored['body'] = payload['body']
					proc.stdout = json.dumps(stored).encode('utf-8')
				elif '-X' in cmd and 'PATCH' in cmd:
					payload = json.loads(input.decode('utf-8'))
					stored.update(payload)
					proc.stdout = json.dumps(stored).encode('utf-8')
				else:
					proc.stdout = json.dumps(stored).encode('utf-8')
				r = proc
				return r
			with patch('agent_tools.github_issue.subprocess.run', side_effect=fake_run):
				# 2026-11-02
				# "Replace special-case grounding/locale regexes with universal locale, relational claim arity, standalone-number, capability, and review gates":
				# https://github.com/dmitry-ai/harness/issues/37
				rc = main(['create', '--repo', 'smokeday-com/m', '--title', 'Test issue title', '--body-file', str(body_path), '--project-root', str(tmp), '--consume-input'])
				self.assertEqual(rc, 0)
				self.assertFalse(body_path.exists())
				# 2026-11-23
				# "Prepend structured JSON metadata header to new GitHub issues in df_github_issue.py":
				# https://github.com/dmitry-ai/harness/issues/150
				self.assertTrue(stored['body'].startswith('```json\n{\n\t"Time": '))
				self.assertTrue(stored['body'].endswith(body_text))
	# 2026-10-31
	# "Enforce EXEC-5 code/issue lifecycle gate in answer-prepare, URL-only commit messages, git_shim/hook commit interception, and worktree isolation":
	# https://github.com/dmitry-ai/harness/issues/31
	def test_close_requires_committed_issue_url_in_local_code_repo(self):
		with tempfile.TemporaryDirectory() as tmp:
			proj = Path(tmp) / 'proj'
			code_repo = proj / 'code'
			(proj / '_/ꘖ').mkdir(parents=True)
			code_repo.mkdir(parents=True)
			subprocess.run(['git', 'init'], cwd=code_repo, check=True, capture_output=True)
			subprocess.run(['git', 'config', 'user.email', 'test@example.com'], cwd=code_repo, check=True, capture_output=True)
			subprocess.run(['git', 'config', 'user.name', 'Test'], cwd=code_repo, check=True, capture_output=True)
			subprocess.run(['git', 'remote', 'add', 'origin', 'https://github.com/smokeday-com/m.git'], cwd=code_repo, check=True, capture_output=True)
			def fake_gh(endpoint, *, method='GET', payload=None, paginate=False):
				return {'number': 46, 'title': 'T', 'body': 'B', 'state': 'closed', 'state_reason': 'completed', 'html_url': 'https://github.com/smokeday-com/m/issues/46'}
			old_cwd = Path.cwd()
			os.chdir(proj)
			try:
				with patch('agent_tools.github_issue._gh_api', side_effect=fake_gh):
					rc_fail = main(['close', '--repo', 'smokeday-com/m', '--issue', '46', '--reason', 'completed'])
					self.assertEqual(rc_fail, 2)
					mod = code_repo / 'mod.py'
					mod.write_text('# https://github.com/smokeday-com/m/issues/46\nx = 1\n', encoding='utf-8')
					subprocess.run(['git', 'add', 'mod.py'], cwd=code_repo, check=True, capture_output=True)
					# 2026-11-26 "Enforce pushed Git tags on issue-closing commits in lifecycle gates": https://github.com/dmitry-ai/harness/issues/263
					subprocess.run(['git', 'commit', '-m', 'https://github.com/smokeday-com/m/issues/46'], cwd=code_repo, check=True, capture_output=True, stdin=subprocess.DEVNULL, timeout=30)
					ensure_commit_tag(code_repo, push=False)
					rc = main(['close', '--repo', 'smokeday-com/m', '--issue', '46', '--reason', 'completed'])
					self.assertEqual(rc, 0)
					self.assertTrue((proj / '_/ꘖ/KB/Evidence/GitHub/smokeday-com__m/issue-46.json').is_file())
			finally:
				os.chdir(old_cwd)
	# 2026-11-02
	# "Replace special-case grounding/locale regexes with universal locale, relational claim arity, standalone-number, capability, and review gates":
	# https://github.com/dmitry-ai/harness/issues/37
	def test_universal_locale_gate_blocks_cyrillic_and_greek_prose_while_allowing_fenced_logs(self):
		ru_title = lint_issue_markdown('Аудит кейсов Upwork — обнаружена проблема в Warmer.php', is_title=True)
		self.assertIn('LOCALE_MISMATCH', {e['code'] for e in ru_title})
		gr_body = lint_issue_markdown('## 1. Root Cause\nΑυτή είναι μια ανάλυση του προβλήματος στο `Warmer.php`.\n', is_title=False)
		self.assertIn('LOCALE_MISMATCH', {e['code'] for e in gr_body})
		en_with_foreign_fence = (
			'## 1. Root Cause\n'
			'In `vendor/magento/module-page-cache/Model/Cache/Warmer.php` the log records:\n'
			'```text\n'
			'Ошибка подключения к базе данных: Σφάλμα σύνδεσης\n'
			'```\n'
			'> «Клиент сообщил о проблеме с кэшем»\n'
			'This is caused by an uninitialized session state in `Warmer.php`.\n'
		)
		self.assertEqual(lint_issue_markdown(en_with_foreign_fence, is_title=False), [])
	# 2026-11-02
	# "Replace special-case grounding/locale regexes with universal locale, relational claim arity, standalone-number, capability, and review gates":
	# https://github.com/dmitry-ai/harness/issues/37
	def test_idempotent_comment_gate_blocks_duplicate_comment_without_comment_id(self):
		with tempfile.TemporaryDirectory() as tmp:
			proj = Path(tmp) / 'proj'
			ev_dir = proj / '_/ꘖ/KB/Evidence/GitHub/smokeday-com__m'
			ev_dir.mkdir(parents=True)
			(ev_dir / 'comment-4345628095.json').write_text(
				json.dumps({
					'id': 4345628095,
					'issue_number': 37,
					'html_url': 'https://github.com/smokeday-com/m/issues/37#issuecomment-4345628095',
					'body': '## Historical Context\nInitial comment in English with `code`.\n',
				}),
				encoding='utf-8',
			)
			body_path = proj / '_/ꘖ/data/scratch/comment.md'
			body_path.parent.mkdir(parents=True)
			body_path.write_text('## Historical Context\nUpdated comment in English with `code`.\n', encoding='utf-8')
			def fake_gh(endpoint, *, method='GET', payload=None, paginate=False):
				return {'id': 4345628095, 'body': body_path.read_text(encoding='utf-8'), 'html_url': 'https://github.com/smokeday-com/m/issues/37#issuecomment-4345628095'}
			with patch('agent_tools.github_issue._gh_api', side_effect=fake_gh):
				rc_dup = main(['comment', '--repo', 'smokeday-com/m', '--issue', '37', '--body-file', str(body_path), '--project-root', str(proj)])
				self.assertEqual(rc_dup, 2)
				rc_edit = main(['comment', '--repo', 'smokeday-com/m', '--comment-id', '4345628095', '--body-file', str(body_path), '--project-root', str(proj)])
				self.assertEqual(rc_edit, 0)
	# 2026-11-18
	# "Reject enumerated multi-item issue titles in df_github_issue.py and active turn lifecycle checks":
	# https://github.com/dmitry-ai/harness/issues/83
	# 2026-11-18
	# "Fix post-audit edge cases in parent-child issue validation and turn-scoped lifecycle checks":
	# https://github.com/dmitry-ai/harness/issues/87
	def test_enumerated_slop_titles_rejected_and_clean_titles_accepted(self):
		slop_titles = (
			'Isolate public DOM captures in chrome-headless-shell, enforce fail-closed primary Chrome profile verification, and block loopback CDP bypasses',
			'Resolve HTML heading-wrapper/Markdown fragment scopes, structural anti-bot challenge classification, and unified DOM/intake source-check provenance',
			'Fix X, Y and Z in parser',
			'Fix A, B, C, and D across modules',
			'Support X, Y, or Z',
			'Unify X, Y, & Z',
			'Refactor X; Y; Z',
			'Validate X, Y, Z',
			'Add A + B + C support',
			'Route A / B / C requests',
			'Исправить X, Y и Z в модуле',
			'Unify `a.py`, `b.py`, and `c.py`',
			'Fix `X, Y, and Z`',
			'Fix feature A + feature B + feature C',
			'Route path A / path B / path C',
			'Fix gates (X, Y, and Z)',
			'When closing parent issues, verify X, Y and Z',
		)
		for title in slop_titles:
			self.assertTrue(has_enumerated_slop_title(title), title)
			errs = lint_issue_markdown(title, is_title=True, target_locale='und')
			self.assertIn('ENUMERATED_SLOP_TITLE', {e['code'] for e in errs}, title)
		clean_titles = (
			'Install and verify Harness global customizations in every configured Antigravity profile (A0, A6)',
			'In text_browser.py, validate A and reject B',
			'In text_browser.py, validate A, and reject B',
			'When closing parent issues, verify X, and check Y',
			'For parent issues with children, verify A and reject B',
			'Fix A, B: handle C and D',
			'Fix `f(a, b)` and `g(c, d)`',
			'Fix `foo(a, b, c)` crash',
			'Process 1,000 events in `research.py`',
			'Reject enumerated multi-item issue titles in df_github_issue.py and active turn lifecycle checks',
			'Enforce parent problem issues and per-subtask child issue commits across issue and Git lifecycle gates',
			'Document parent-child issue decomposition and enumerated title ban in EXEC-5 and df-github-issue',
		)
		for title in clean_titles:
			self.assertFalse(has_enumerated_slop_title(title), title)
			self.assertEqual(lint_issue_markdown(title, is_title=True), [], title)
		with tempfile.TemporaryDirectory() as tmp:
			body_path = Path(tmp) / 'body.md'
			body_path.write_text('## Problem\nSingle problem description.\n', encoding='utf-8')
			rc = main(['create', '--repo', 'smokeday-com/m', '--title', slop_titles[0], '--body-file', str(body_path), '--project-root', str(tmp)])
			self.assertEqual(rc, 2)
	# 2026-11-18
	# "Enforce parent problem issues and per-subtask child issue commits across issue and Git lifecycle gates":
	# https://github.com/dmitry-ai/harness/issues/84
	# 2026-11-18
	# "Fix post-audit edge cases in parent-child issue validation and turn-scoped lifecycle checks":
	# https://github.com/dmitry-ai/harness/issues/87
	def test_parent_child_issue_linking_bundled_subtasks_and_parent_closure(self):
		import check_rules_and_server_gate as gate_hook
		from agent_tools.git_gate import verify_repo_issue_ready_for_close
		bundled_body = '## Solution\n1. M-1 Isolate public captures.\n1. M-2 Enforce primary profile check.\n'
		self.assertIn('BUNDLED_SUBTASKS_IN_SINGLE_ISSUE', {e['code'] for e in lint_issue_markdown(bundled_body)})
		verb_bundled_body = '## Solution\n- Implement M-1 in `github_issue.py`.\n- Implement M-2 in `git_gate.py`.\n'
		self.assertIn('BUNDLED_SUBTASKS_IN_SINGLE_ISSUE', {e['code'] for e in lint_issue_markdown(verb_bundled_body)})
		dup_link_body = '## Solution\n1. M-1 (see #41)\n1. M-2 (see #41)\n'
		self.assertIn('BUNDLED_SUBTASKS_IN_SINGLE_ISSUE', {e['code'] for e in lint_issue_markdown(dup_link_body)})
		indented_distinct_body = 'Parent: #40\n\n## Plan\n1. M-1 First\n   - See #41\n1. M-2 Second\n   - See #42\n'
		self.assertEqual(lint_issue_markdown(indented_distinct_body, parent_number=40, repo='smokeday-com/m', self_number=40), [])
		parent_diag_body = '## Problem\n1. `H-1` — missing check.\n1. `H-2` — fallback bypass.\n1. `H-3` — stale cache.\n'
		self.assertEqual(lint_issue_markdown(parent_diag_body), [])
		child_family_body = '**Parent:** #40\n\n## Subtask Scope\n1. `M-2A` — extension offscreen anchor.\n1. `M-2B` — sentinel fallback.\n'
		self.assertEqual(lint_issue_markdown(child_family_body, parent_number=40, repo='smokeday-com/m'), [])
		unlinked_child_body = '## Subtask Scope\nImplement `M-1` only.\n'
		self.assertIn('MISSING_PARENT_ISSUE_LINK', {e['code'] for e in lint_issue_markdown(unlinked_child_body, parent_number=40, repo='smokeday-com/m')})
		self.assertIsNotNone(gate_hook.check_external_write_gate('run_command', {'CommandLine': 'gh api repos/x/y/issues -f title=foo'}))
		self.assertIsNotNone(gate_hook.check_external_write_gate('run_command', {'CommandLine': 'gh.exe api repos/x/y/issues -f title=foo'}))
		self.assertIsNotNone(gate_hook.check_external_write_gate('run_command', {'CommandLine': 'gh api repos/x/y/issues --method=DELETE'}))
		self.assertIsNone(gate_hook.check_external_write_gate('run_command', {'CommandLine': 'gh api repos/x/y/issues -X GET -f state=open'}))
		self.assertIsNone(gate_hook.check_external_write_gate('run_command', {'CommandLine': 'gh api repos/x/y/issues --method=GET -f state=open'}))
		with tempfile.TemporaryDirectory() as tmp:
			proj = Path(tmp) / 'proj'
			code_repo = proj / 'code'
			(proj / '_/\ua616').mkdir(parents=True)
			code_repo.mkdir(parents=True)
			# 2026-11-26 "Enforce pushed Git tags on issue-closing commits in lifecycle gates": https://github.com/dmitry-ai/harness/issues/263
			subprocess.run(['git', 'init'], cwd=code_repo, check=True, capture_output=True, stdin=subprocess.DEVNULL, timeout=30)
			(code_repo / '.git/config').write_text((code_repo / '.git/config').read_text(encoding='utf-8') + '[user]\n\temail = test@example.com\n\tname = Test\n[remote "origin"]\n\turl = https://github.com/smokeday-com/m.git\n', encoding='utf-8')
			url40, url41, url42, url46 = ('https://github.com/smokeday-com/m/' + f'issues/{n}' for n in (40, 41, 42, 46))
			f46 = code_repo / 'mod46.py'
			f46.write_text('# ' + url46 + '\nx = 46\n', encoding='utf-8')
			subprocess.run(['git', 'add', 'mod46.py'], cwd=code_repo, check=True, capture_output=True)
			subprocess.run(['git', 'commit', '-m', url46], cwd=code_repo, check=True, capture_output=True)
			with self.assertRaisesRegex(ValueError, 'no commit in'):
				verify_repo_issue_ready_for_close(code_repo, 'smokeday-com/m', 4, project_root=proj)
			next_num = [40]
			issues_db = {40: {'number': 40, 'id': 4000, 'title': 'Root problem in parser', 'body': parent_diag_body, 'state': 'open', 'state_reason': None, 'html_url': url40}}
			def fake_gh(endpoint, *, method='GET', payload=None, paginate=False):
				if 'POST' == method and endpoint.endswith('/issues'):
					next_num[0] += 1
					num = next_num[0]
					issues_db[num] = {'number': num, 'id': 4000 + num, 'title': payload['title'], 'body': payload['body'], 'state': 'open', 'state_reason': None, 'html_url': 'https://github.com/smokeday-com/m/' + f'issues/{num}'}
					return issues_db[num]
				if 'POST' == method and endpoint.endswith('/sub_issues'):
					return {'linked': True}
				if 'PATCH' == method and '/issues/' in endpoint:
					num = int(endpoint.rsplit('/', 1)[-1])
					self.assertTrue(bool(payload), 'Must not send an empty PATCH')
					issues_db[num].update(payload)
					return issues_db[num]
				if 'GET' == method and '/issues/' in endpoint:
					num = int(endpoint.rsplit('/', 1)[-1])
					if num not in issues_db:
						raise RuntimeError('404 Not Found')
					return issues_db[num]
				raise AssertionError(f'Unexpected {method} {endpoint}')
			b41 = proj / '_/\ua616/data/scratch/b41.md'
			b41.parent.mkdir(parents=True)
			b41.write_text(f'Parent: [Issue #40]({url40})\n\n## Scope\nFix H-1.\n', encoding='utf-8')
			b42 = proj / '_/\ua616/data/scratch/b42.md'
			b42.write_text('Parent: #40\n\n## Scope\nFix H-2.\n', encoding='utf-8')
			b43_bad = proj / '_/\ua616/data/scratch/b43_bad.md'
			b43_bad.write_text('Parent: #999999\n\n## Scope\nOrphan parent ref.\n', encoding='utf-8')
			issues_db[43] = {'number': 43, 'id': 4043, 'title': 'Fix H-3 child check', 'body': '**Parent:** #40\n\n## Scope\nLinked via edit --parent.\n', 'state': 'open', 'state_reason': None, 'html_url': 'https://github.com/smokeday-com/m/' + 'issues/43'}
			with patch('agent_tools.github_issue._gh_api', side_effect=fake_gh):
				self.assertEqual(main(['create', '--repo', 'smokeday-com/m', '--title', 'Bad parent body ref', '--body-file', str(b43_bad), '--project-root', str(proj)]), 1)
				self.assertEqual(main(['edit', '--repo', 'smokeday-com/m', '--issue', '43', '--parent', '40', '--project-root', str(proj)]), 0)
				ev_dir = proj / '_/\ua616/KB/Evidence/GitHub/smokeday-com__m'
				ev43 = json.loads((ev_dir / 'issue-43.json').read_text(encoding='utf-8'))
				self.assertEqual(ev43['parent_number'], 40)
				self.assertEqual(main(['create', '--repo', 'smokeday-com/m', '--parent', '40', '--title', 'Fix H-1 check', '--body-file', str(b41), '--project-root', str(proj), '--consume-input']), 0)
				self.assertEqual(main(['create', '--repo', 'smokeday-com/m', '--parent', url40, '--title', 'Fix H-2 fallback', '--body-file', str(b42), '--project-root', str(proj), '--consume-input']), 0)
				ev41 = json.loads((ev_dir / 'issue-41.json').read_text(encoding='utf-8'))
				self.assertEqual(ev41['parent_number'], 40)
				self.assertEqual(ev41['parent_url'], url40)
				f41 = code_repo / 'mod41.py'
				f41.write_text('# ' + url41 + '\nx = 1\n', encoding='utf-8')
				subprocess.run(['git', 'add', 'mod41.py'], cwd=code_repo, check=True, capture_output=True)
				# 2026-11-26 "Enforce pushed Git tags on issue-closing commits in lifecycle gates": https://github.com/dmitry-ai/harness/issues/263
				subprocess.run(['git', 'commit', '-m', url41], cwd=code_repo, check=True, capture_output=True, stdin=subprocess.DEVNULL, timeout=30)
				ensure_commit_tag(code_repo, push=False)
				self.assertEqual(main(['close', '--repo', 'smokeday-com/m', '--issue', '41', '--project-root', str(proj)]), 0)
				self.assertEqual(json.loads((ev_dir / 'issue-41.json').read_text(encoding='utf-8'))['parent_number'], 40)
				self.assertEqual(main(['close', '--repo', 'smokeday-com/m', '--issue', '40', '--project-root', str(proj)]), 2)
				f42 = code_repo / 'mod42.py'
				f42.write_text('# ' + url42 + '\nx = 2\n', encoding='utf-8')
				# 2026-11-26 "Enforce pushed Git tags on issue-closing commits in lifecycle gates": https://github.com/dmitry-ai/harness/issues/263
				subprocess.run(['git', 'add', 'mod42.py'], cwd=code_repo, check=True, capture_output=True, stdin=subprocess.DEVNULL, timeout=30)
				subprocess.run(['git', 'commit', '-m', url42], cwd=code_repo, check=True, capture_output=True, stdin=subprocess.DEVNULL, timeout=30)
				ensure_commit_tag(code_repo, push=False)
				self.assertEqual(main(['close', '--repo', 'smokeday-com/m', '--issue', '42', '--project-root', str(proj)]), 0)
				url43 = 'https://github.com/smokeday-com/m/' + 'issues/43'
				f43 = code_repo / 'mod43.py'
				f43.write_text('# ' + url43 + '\nx = 43\n', encoding='utf-8')
				# 2026-11-26 "Enforce pushed Git tags on issue-closing commits in lifecycle gates": https://github.com/dmitry-ai/harness/issues/263
				subprocess.run(['git', 'add', 'mod43.py'], cwd=code_repo, check=True, capture_output=True, stdin=subprocess.DEVNULL, timeout=30)
				subprocess.run(['git', 'commit', '-m', url43], cwd=code_repo, check=True, capture_output=True, stdin=subprocess.DEVNULL, timeout=30)
				ensure_commit_tag(code_repo, push=False)
				self.assertEqual(main(['close', '--repo', 'smokeday-com/m', '--issue', '43', '--project-root', str(proj)]), 0)
				f40_mono = code_repo / 'mod40.py'
				f40_mono.write_text('# ' + url40 + '\nx = 40\n', encoding='utf-8')
				subprocess.run(['git', 'add', 'mod40.py'], cwd=code_repo, check=True, capture_output=True)
				subprocess.run(['git', 'commit', '-m', url40], cwd=code_repo, check=True, capture_output=True)
				self.assertEqual(main(['close', '--repo', 'smokeday-com/m', '--issue', '40', '--project-root', str(proj)]), 2)
				subprocess.run(['git', 'reset', '--hard', 'HEAD~1'], cwd=code_repo, check=True, capture_output=True)
				self.assertEqual(main(['close', '--repo', 'smokeday-com/m', '--issue', '40', '--project-root', str(proj)]), 0)
	# 2026-11-22
	# "Add audited transfer-repo subcommand to df_github_issue.py":
	# https://github.com/dmitry-ai/harness/issues/126
	# 2026-11-22
	# "Isolate transfer-repo unit test from live df-servers repository evidence":
	# https://github.com/dmitry-ai/harness/issues/127
	def test_transfer_repo_verifies_readback_and_persists_evidence(self):
		with tempfile.TemporaryDirectory() as tmp:
			proj = Path(tmp) / 'proj'
			(proj / '\ua616').mkdir(parents=True)
			calls = []
			def fake_gh(endpoint, *, method='GET', payload=None, paginate=False):
				calls.append((method, endpoint, payload))
				if 'POST' == method and 'repos/example-owner/demo-srv/transfer' == endpoint:
					self.assertEqual(payload, {'new_owner': 'example-org'})
					return {'full_name': 'example-owner/demo-srv', 'html_url': 'https://github.com/example-owner/demo-srv'}
				if 'GET' == method and 'repos/example-org/demo-srv' == endpoint:
					if 2 == len(calls):
						raise RuntimeError('404 Not Found')
					return {'full_name': 'example-org/demo-srv', 'html_url': 'https://github.com/example-org/demo-srv', 'private': False, 'default_branch': 'main'}
				raise AssertionError(f'Unexpected {method} {endpoint}')
			with patch('agent_tools.github_issue._gh_api', side_effect=fake_gh):
				rc = main(['transfer-repo', '--repo', 'example-owner/demo-srv', '--new-owner', 'example-org', '--project-root', str(proj), '--poll-attempts', '3', '--poll-interval', '0'])
				self.assertEqual(rc, 0)
			ev_file = proj / '\ua616/KB/Evidence/GitHub/example-org__demo-srv/transfer-example-owner__demo-srv-to-example-org__demo-srv.json'
			self.assertTrue(ev_file.is_file())
			ev_data = json.loads(ev_file.read_text(encoding='utf-8'))
			self.assertEqual(ev_data['verified_repo']['full_name'], 'example-org/demo-srv')
			self.assertEqual(main(['transfer-repo', '--repo', 'example-org/demo-srv', '--new-owner', 'example-org', '--project-root', str(proj)]), 1)
	# 2026-11-23
	# "Prepend structured JSON metadata header to new GitHub issues in df_github_issue.py":
	# https://github.com/dmitry-ai/harness/issues/150
	def test_create_prepends_tab_indented_json_metadata_header_and_supports_opt_out(self):
		import io
		from agent_tools import metadata
		with tempfile.TemporaryDirectory() as tmp:
			proj = Path(tmp).resolve() / 'demo-proj'
			(proj / '\ua616/data/scratch').mkdir(parents=True)
			body_file = proj / '\ua616/data/scratch/issue.md'
			raw_body = '## Problem\nMissing metadata header in new issues.\n'
			body_file.write_text(raw_body, encoding='utf-8', newline='\n')
			issues_db = {}
			next_num = [10]
			calls = []
			def fake_gh(endpoint, *, method='GET', payload=None, paginate=False):
				calls.append((method, endpoint))
				if 'POST' == method and endpoint.endswith('/issues'):
					num = next_num[0]
					next_num[0] += 1
					issues_db[num] = {
						'number': num,
						'id': 9000 + num,
						'title': payload['title'],
						'body': payload['body'],
						'state': 'open',
						'html_url': f'https://github.com/acme/demo/issues/{num}',
					}
					return dict(issues_db[num])
				if 'PATCH' == method and '/issues/' in endpoint:
					num = int(endpoint.rsplit('/', 1)[-1])
					issues_db[num].update(payload)
					return dict(issues_db[num])
				if 'GET' == method and '/issues/' in endpoint:
					num = int(endpoint.rsplit('/', 1)[-1])
					return dict(issues_db[num])
				raise AssertionError(f'Unexpected {method} {endpoint}')
			with patch('agent_tools.github_issue._gh_api', side_effect=fake_gh):
				buf = io.StringIO()
				with patch('sys.stdout', buf):
					rc = main(['create', '--repo', 'acme/demo', '--title', 'Add metadata header', '--body-file', str(body_file), '--project-root', str(proj)])
				self.assertEqual(rc, 0, buf.getvalue())
				out = json.loads(buf.getvalue())
				self.assertTrue(out['verified'])
				self.assertTrue(out.get('metadata_prepended'))
				stored_body = issues_db[10]['body']
				self.assertTrue(stored_body.startswith('```json\n{\n\t"Time": '))
				parsed_meta, extracted_body = metadata.extract_leading_metadata_header(stored_body)
				self.assertIsNotNone(parsed_meta)
				self.assertEqual(parsed_meta['Issue'], 'https://github.com/acme/demo/issues/10')
				self.assertEqual(parsed_meta['Project']['Path'], proj.as_posix())
				self.assertRegex(parsed_meta['Time'], r'^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2} UTC[+-]\d+(?::\d{2})?$')
				self.assertEqual(extracted_body, raw_body)
				ev_file = proj / '\ua616/KB/Evidence/GitHub/acme__demo/issue-10.json'
				self.assertEqual(json.loads(ev_file.read_text(encoding='utf-8'))['body'], stored_body)

				# Opt-out via --no-metadata skips PATCH and leaves body verbatim
				calls.clear()
				buf2 = io.StringIO()
				with patch('sys.stdout', buf2):
					rc2 = main(['create', '--repo', 'acme/demo', '--title', 'Plain issue body', '--body-file', str(body_file), '--project-root', str(proj), '--no-metadata'])
				self.assertEqual(rc2, 0, buf2.getvalue())
				self.assertEqual(issues_db[11]['body'], raw_body)
				self.assertFalse(any(('PATCH' == m for m, _ in calls)))

				# Existing Harness metadata header in body is not duplicated
				prefixed_file = proj / '\ua616/data/scratch/prefixed.md'
				prefixed_file.write_text(stored_body, encoding='utf-8', newline='\n')
				calls.clear()
				buf3 = io.StringIO()
				with patch('sys.stdout', buf3):
					rc3 = main(['create', '--repo', 'acme/demo', '--title', 'Already prefixed issue', '--body-file', str(prefixed_file), '--project-root', str(proj)])
				self.assertEqual(rc3, 0, buf3.getvalue())
				self.assertEqual(issues_db[12]['body'].count('```json'), 1)
				self.assertFalse(any(('PATCH' == m for m, _ in calls)))
if '__main__' == __name__:
	unittest.main()
