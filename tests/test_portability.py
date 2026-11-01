# 2026-10-16 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Unify Antigravity and OpenAI Codex adapters with build-native projections, parent-driven model selection, and cross-system continuation":
# https://github.com/dmitry-ai/harness/issues/6
# 2026-10-31 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Reorganize AI into universal harness repository, translate rules and documentation to English, format per P.md, and enforce issue-driven Git workflow":
# https://github.com/dmitry-ai/harness/issues/26
# 2026-11-02 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Replace per-profile Harness projections with shared native connections":
# https://github.com/dmitry-ai/harness/issues/35
from contextlib import contextmanager
from copy import deepcopy
import json
from pathlib import Path
import shutil
import sqlite3
import tomllib
import unittest
from unittest.mock import patch
import uuid
from test_analysis_workflow import ProjectCase
from test_agent_tools import TemporaryCase
from test_onboarding import source
from agent_tools import configuration, runtime, metrics, workflow as flow, upwork_project as up
from agent_tools.platforms import codex
from agent_tools.analysis import publish_owned, render_analysis, SECTIONS
from agent_tools.context import generate
from agent_tools.snapshot import snapshot_draft
class ProjectionTests(TemporaryCase):
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
	def test_verified_legacy_migrates_but_manual_configuration_and_fallback_survive(self):
		configuration.build_native(self.output, primary=self.primary)
		legacy = self.output / 'CODEX.md'
		legacy.write_bytes(b'old owned projection')
		receipt = self.output / 'ꘖ/data/native-config.json'
		ownership = json.loads(receipt.read_text(encoding='utf-8'))
		ownership[str(legacy)] = configuration._digest(legacy.read_bytes())
		receipt.write_text(json.dumps(ownership), encoding='utf-8')
		native = self.output / '.codex/config.toml'
		native.write_text('model = "mine"\nproject_doc_fallback_filenames = ["TEAM.md", "CODEX.md"]\nproject_doc_max_bytes = 65536\ndeveloper_instructions = "Keep my instructions"\n[features]\ncustom = true\n')
		result = configuration.build_native(self.output, primary=self.primary)
		self.assertTrue(result['valid'], result)
		self.assertFalse(legacy.exists())
		backups = list((self.output / 'ꘖ/data/native-retired').rglob('*.bin'))
		self.assertEqual([path.read_bytes() for path in backups], [b'old owned projection'])
		value = tomllib.loads(native.read_text())
		self.assertEqual(value['project_doc_fallback_filenames'], ['TEAM.md'])
		self.assertNotIn('project_doc_max_bytes', value)
		self.assertEqual(value['model'], 'mine')
		self.assertTrue(value['features']['custom'])
		self.assertTrue(value['developer_instructions'].startswith('Keep my instructions'))
		native.write_text(native.read_text().replace('Read the listed canonical', 'Manual modification'))
		previous = native.read_bytes()
		self.assertFalse(configuration.build_native(self.output, primary=self.primary)['valid'])
		self.assertEqual(native.read_bytes(), previous)
	def test_unowned_legacy_prevents_partial_migration(self):
		self.output.mkdir()
		legacy = self.output / 'CODEX.md'
		legacy.write_text('MY ORIGINAL')
		result = configuration.build_native(self.output, primary=self.primary)
		self.assertFalse(result['valid'])
		self.assertEqual(legacy.read_text(), 'MY ORIGINAL')
		self.assertFalse((self.output / '.codex/config.toml').exists())
	def test_global_instructions_are_read_safely_and_local_override_keeps_its_priority(self):
		config = deepcopy(runtime.settings())
		homes = {name: str(self.root / name) for name in ('C1', 'C2')}
		config['platforms']['codex']['homes'] = homes
		for home in homes.values():
			path = Path(home) / 'config.toml'
			path.parent.mkdir()
			path.write_text('developer_instructions = "GLOBAL"\nsecret = "DO NOT RETURN"\n')
		with patch.object(configuration, 'settings', return_value=config), patch.object(configuration, 'profile_name', side_effect=ValueError('unknown')):
			value = configuration.global_codex_instructions()
			self.assertEqual(value['developer_instructions'], 'GLOBAL')
			self.assertNotIn('DO NOT RETURN', str(value))
			(Path(homes['C2']) / 'config.toml').write_text('developer_instructions = "DIFFERENT"\n')
			with self.assertRaisesRegex(ValueError, 'differ'):
				configuration.global_codex_instructions()
		project = self.output / 'job'
		native = project / '.codex/config.toml'
		native.parent.mkdir(parents=True)
		native.write_text('developer_instructions = "LOCAL OVERRIDE"\n')
		up.configure_project(project, self.primary)
		value = tomllib.loads(native.read_text())['developer_instructions']
		self.assertTrue(value.startswith('LOCAL OVERRIDE'))
		self.assertNotIn('policy-instructions', value)
		self.assertIn('00-scope.md', value)
	def test_generation_is_idempotent_detects_source_changes_and_preserves_manual_edits(self):
		first = configuration.build_native(self.output, primary=self.primary)
		self.assertTrue(first['valid'])
		self.assertEqual(configuration.build_native(self.output, primary=self.primary)['written'], [])
		self.assertTrue(configuration.build_native(self.output, primary=self.primary, check=True)['valid'])
		rule = self.primary / 'rules/00-scope.md'
		rule.write_text(rule.read_text(encoding='utf-8') + '\nSpecific changed policy.\n', encoding='utf-8')
		self.assertTrue(configuration.build_native(self.output, primary=self.primary, check=True)['valid'])
		self.assertEqual(configuration.build_native(self.output, primary=self.primary)['written'], [])
		generated = self.primary / 'platforms/codex/agents/upwork-aa.toml'
		generated.write_text('USER CHANGE', encoding='utf-8')
		result = configuration.build_native(self.output, primary=self.primary)
		self.assertFalse(result['valid'])
		self.assertEqual(generated.read_text(), 'USER CHANGE')
	def test_check_does_not_create_an_uninstalled_workspace(self):
		self.assertFalse(configuration.build_native(self.output, primary=self.primary, check=True)['valid'])
		self.assertFalse(self.output.exists())
	def test_dangling_personal_guidance_links_are_preserved_before_shared_publication(self):
		for relative in ('AGENTS.md', '.codex/config.toml', 'CODEX.md'):
			with self.subTest(relative=relative):
				project = self.root / ('dangling-' + Path(relative).stem)
				path = project / relative
				path.parent.mkdir(parents=True)
				target = self.root / 'missing-personal' / Path(relative).name
				path.symlink_to(target)
				identity = path.readlink()
				result = configuration.build_native(project, primary=self.primary)
				self.assertFalse(result['valid'], result)
				self.assertTrue(path.is_symlink())
				self.assertEqual(path.readlink(), identity)
				self.assertFalse(target.exists())
				self.assertFalse((self.primary / 'agents/af-worker.md').exists())
	def test_shared_generation_uses_one_owner_across_projects_and_profile_install(self):
		from agent_tools import native_profiles
		from agent_tools.storage import data_dir_for
		home = self.root / 'profile-C2'
		def install(check=False):
			return native_profiles.install_native_profiles(['C2'], primary=self.primary, check=check, config_dirs={}, codex_homes={'C2': home})
		self.assertTrue(install()['valid'])
		self.assertTrue(configuration.build_native(self.output, primary=self.primary)['valid'])
		receipt_path = data_dir_for(self.output) / 'native-config.json'
		legacy_receipt = json.loads(receipt_path.read_text(encoding='utf-8'))
		for path in native_profiles.shared_native_outputs(self.primary):
			legacy_receipt[str(path)] = configuration._digest(path.read_bytes())
		receipt_path.write_text(json.dumps(legacy_receipt), encoding='utf-8')
		self.assertFalse(configuration.build_native(self.output, primary=self.primary, check=True)['valid'])
		first_rule = self.primary / 'rules/91-first-added.md'
		first_rule.write_text('---\ntrigger: always_on\n---\n# Added rule\nFirst addition.  \n', encoding='utf-8')
		self.assertTrue(configuration.build_native(self.output, primary=self.primary)['valid'])
		second = self.root / 'another-workspace'
		second_rule = self.primary / 'rules/92-second-added.md'
		second_rule.write_text('---\ntrigger: always_on\n---\n# Added rule\nSecond addition.  \n', encoding='utf-8')
		self.assertTrue(configuration.build_native(second, primary=self.primary)['valid'])
		third_rule = self.primary / 'rules/93-third-added.md'
		third_rule.write_text('---\ntrigger: always_on\n---\n# Added rule\nThird addition.  \n', encoding='utf-8')
		result = install()
		self.assertTrue(result['valid'], result)
		self.assertTrue(install(check=True)['valid'])
		bootstrap = self.primary / 'platforms/codex/AGENTS.md'
		self.assertIn('93-third-added.md', bootstrap.read_text(encoding='utf-8'))
		state = native_profiles._load_state(self.primary)
		self.assertEqual(state['shared'][str(bootstrap)], configuration._digest(bootstrap.read_bytes()))
		for project in (self.output, second):
			receipt = json.loads((data_dir_for(project) / 'native-config.json').read_text(encoding='utf-8'))
			self.assertFalse(any(Path(path).is_relative_to(self.primary) for path in receipt))
	def test_first_install_preserves_an_unowned_antigravity_worker(self):
		worker = self.primary / 'agents/af-worker.md'
		worker.write_text('CUSTOM WORKER', encoding='utf-8')
		result = configuration.build_native(self.output, primary=self.primary)
		self.assertFalse(result['valid'])
		self.assertEqual(worker.read_text(), 'CUSTOM WORKER')
	def test_native_toml_preserves_settings_and_resolves_models_from_one_config(self):
		config = deepcopy(runtime.settings())
		config['platforms']['codex']['roles']['AA'].update(model='test-next-model', effort='high')
		with patch.object(runtime, 'settings', return_value=config), patch.object(configuration, 'settings', return_value=config):
			result = configuration.build_native(self.output, primary=self.primary)
		self.assertTrue(result['valid'])
		native_config = tomllib.loads((self.output / '.codex/config.toml').read_text())
		self.assertNotIn('model', native_config)
		self.assertNotIn('model_reasoning_effort', native_config)
		for name in ('upwork-aa', 'upwork-af'):
			self.assertFalse((self.output / f'.codex/agents/{name}.toml').exists())
			value = tomllib.loads((self.primary / f'platforms/codex/agents/{name}.toml').read_text(encoding='utf-8'))
			self.assertNotIn('model', value)
			self.assertNotIn('model_reasoning_effort', value)
		with patch.object(runtime, 'settings', return_value=config):
			self.assertEqual(runtime.role_settings('codex', 'AF')['selection'], 'parent')
			self.assertNotIn('model', runtime.role_settings('codex', 'AF'))
		original = 'model = "user-selected"\n[projects."C:/elsewhere"]\ntrust_level = "trusted"\n'
		result = tomllib.loads(configuration._root_options(original, 'Load source policy.'))
		self.assertEqual(result['model'], 'user-selected')
		self.assertEqual(result['projects']['C:/elsewhere']['trust_level'], 'trusted')
		self.assertNotIn('project_doc_fallback_filenames', result)
		self.assertNotIn('project_doc_max_bytes', result)
		self.assertIn('Load source policy.', result['developer_instructions'])
	def test_project_rules_feed_both_systems_and_detect_stale_codex_projection(self):
		project = self.output / 'job'
		local = project / '.agents/rules/91-proposal.md'
		local.parent.mkdir(parents=True)
		local.write_text('---\ntrigger: always_on\n---\n# Proposal\nPreserve the agreed scope.\n', encoding='utf-8')
		manual = project / 'KB/Project.md'
		manual.parent.mkdir()
		manual.write_bytes(b'MANUAL KB\r\n')
		native = project / '.codex/config.toml'
		native.parent.mkdir()
		native.write_text('model = "user-selected"\n[features]\ncustom = true\n')
		up.configure_project(project, self.primary, job_url='https://www.upwork.com/jobs/~021234', domain_or_topic='Topic')
		self.assertFalse((project / 'CODEX.md').exists())
		self.assertNotIn('developer_instructions', tomllib.loads(native.read_text()))
		self.assertEqual(manual.read_bytes(), b'MANUAL KB\r\n')
		config = tomllib.loads(native.read_text())
		self.assertEqual(config['model'], 'user-selected')
		self.assertTrue(config['features']['custom'])
		self.assertTrue(configuration.configure_codex_project(project, self.primary, check=True)['valid'])
		self.assertTrue(up.check_configuration(project, self.primary)['valid'])
		self.assertFalse(list((project / '.agents').rglob('*.py')))
		local.write_text(local.read_text(encoding='utf-8') + 'New user instruction.\n', encoding='utf-8')
		self.assertTrue(configuration.configure_codex_project(project, self.primary, check=True)['valid'])
		up.configure_project(project, self.primary)
		self.assertNotIn('New user instruction.', native.read_text())
		self.assertNotIn('developer_instructions', tomllib.loads(native.read_text()))
		self.assertTrue(configuration.configure_codex_project(project, self.primary, check=True)['valid'])
		(project / '.agents/skills.json').unlink()
		self.assertFalse(up.check_configuration(project, self.primary)['valid'])
	def test_multiline_toml_values_do_not_damage_unrelated_settings(self):
		original = '# Preserve root and table settings.\n"project_doc_fallback_filenames" = [\n    "TEAM.md", # ], # and quotes are not structure\n    \'AGENTS.local.md\',\n]\nmodel = "keep-me"\ndeveloper_instructions = ' + "'''" + 'A multiline instruction.\n[This is plain text, not a TOML table]\nproject_doc_max_bytes = 1\n' + "'''" + '\n[features]\ncustom = true\n'
		expected = tomllib.loads(original)
		updated = configuration._root_options(original, 'Load source policy.')
		actual = tomllib.loads(updated)
		self.assertEqual(actual['model'], expected['model'])
		self.assertTrue(actual['developer_instructions'].startswith(expected['developer_instructions']))
		self.assertEqual(actual['features'], expected['features'])
		self.assertEqual(actual['project_doc_fallback_filenames'], ['TEAM.md', 'AGENTS.local.md'])
		self.assertEqual(configuration._root_options(updated, 'Load source policy.'), updated)
		for quote in ('"', "'"):
			for ending in (4, 5):
				with self.subTest(quote=quote, ending=ending):
					source = 'banner = ' + quote * 3 + 'text' + quote * ending + '\nproject_doc_fallback_filenames = [\n "TEAM.md",\n]\n'
					actual = tomllib.loads(configuration._root_options(source, 'Load source policy.'))
					self.assertEqual(actual['banner'], tomllib.loads(source)['banner'])
					self.assertEqual(actual['project_doc_fallback_filenames'], ['TEAM.md'])
	def test_extra_rule_sources_are_projected_and_unsupported_selectors_reported(self):
		project = self.output / 'job'
		up.configure_project(project, self.primary)
		agents = project / '.agents'
		extra = agents / 'extra-rules/nested/91-manual.md'
		extra.parent.mkdir(parents=True)
		extra.write_text('---\ntrigger: always_on\n---\n# Local\nAdditional actual project rule.\n', encoding='utf-8')
		manifest = agents / 'rules.json'
		data = json.loads(manifest.read_text(encoding='utf-8'))
		data['entries'].extend([{'path': 'extra-rules'}, {'path': extra.as_posix()}])
		manifest.write_text(json.dumps(data), encoding='utf-8')
		self.assertTrue(up.check_configuration(project, self.primary)['valid'])
		up.configure_project(project, self.primary)
		self.assertEqual(configuration._project_rule_paths(project, self.primary).count(extra.resolve()), 1)
		self.assertFalse((project / '.codex/config.toml').exists())
		self.assertTrue(up.check_configuration(project, self.primary)['valid'])
		previous = (project / '.agents/rules/90-project.md').read_bytes()
		data['entries'][-1]['include_only'] = ['some.md']
		manifest.write_text(json.dumps(data), encoding='utf-8')
		with self.assertRaisesRegex(ValueError, 'filtered'):
			up.configure_project(project, self.primary)
		check = up.check_configuration(project, self.primary)
		self.assertFalse(check['valid'])
		self.assertIn('filtered', check['issues'][0]['message'])
		self.assertEqual((project / '.agents/rules/90-project.md').read_bytes(), previous)
	def test_project_setup_merges_native_entries_and_preserves_custom_context(self):
		project = self.output / 'job'
		agents = project / '.agents'
		agents.mkdir(parents=True)
		manifest = agents / 'rules.json'
		manifest.write_text(json.dumps({'entries': [{'path': str(self.primary / 'rules')}], 'custom': 'keep'}))
		context = agents / 'context.json'
		original = b'{"version":1,"output":"custom.md","sections":[{"title":"Custom","files":[".md"]}]}\n'
		context.write_bytes(original)
		up.configure_project(project, self.primary)
		saved = json.loads(manifest.read_text())
		self.assertEqual(saved['custom'], 'keep')
		self.assertIn({'path': 'rules'}, saved['entries'])
		self.assertEqual(context.read_bytes(), original)
class CodexEvidenceTests(ProjectCase):
	def setUp(self):
		super().setUp()
		self.home = self.root / 'codex-profile'
		self.home.mkdir()
		self.parent, self.child = (str(uuid.uuid4()), str(uuid.uuid4()))
		self.model = 'observed-parent-model'
		self.assignment = 'gAAAAA-native-encrypted-assignment'
		flow.resume(self.project, 'native fixture', '  $upwork-init https://www.upwork.com/jobs/' + source()['job_id'] + '\nExact text.  ')
		self.package = self.review_package(self.parent)
		self.parent_rows = [self.meta(self.parent), self.context(), self.message('user', '  $upwork-init https://www.upwork.com/jobs/' + source()['job_id'] + '\nExact text.  '), {'type': 'response_item', 'payload': {'type': 'function_call', 'name': 'collaboration.spawn_agent', 'call_id': 'spawn-reviewer', 'arguments': json.dumps({'task_name': 'reviewer', 'message': self.assignment})}}]
		self.child_rows = [self.meta(self.child, self.parent), self.context(), {'type': 'response_item', 'payload': {'type': 'agent_message', 'author': '/root', 'recipient': '/root/reviewer', 'content': [{'type': 'input_text', 'text': 'Message Type: NEW_TASK\nPayload:\n'}, {'type': 'encrypted_content', 'encrypted_content': self.assignment}]}}, self.message('assistant', 'Reviewed.'), {'type': 'event_msg', 'payload': {'type': 'task_complete', 'last_agent_message': 'Reviewed.'}}]
		self.set_review_input(self.package)
		self.write_trace(self.parent, self.parent_rows)
		self.write_trace(self.child, self.child_rows)
	def meta(self, ident, parent=None):
		return {'type': 'session_meta', 'payload': {'id': ident, 'source': {'subagent': {'thread_spawn': {'parent_thread_id': parent, 'agent_path': '/root/reviewer'}}} if parent else 'vscode'}}
	def context(self):
		return {'type': 'turn_context', 'payload': {'model': self.model, 'effort': 'max'}}
	def message(self, role, text):
		return {'type': 'response_item', 'payload': {'type': 'message', 'role': role, 'content': [{'type': 'input_text' if 'user' == role else 'output_text', 'text': text}]}}
	def set_review_input(self, package):
		with patch.dict('os.environ', {'CODEX_THREAD_ID': self.child}):
			receipt = flow.review_input(self.project, package['package'])
		self.child_rows = [item for item in self.child_rows if 'review-input-call' != item.get('payload', {}).get('call_id')]
		self.child_rows[3:3] = [{'type': 'response_item', 'payload': {'type': 'custom_tool_call', 'call_id': 'review-input-call', 'name': 'exec', 'input': f'''python upwork_project.py review-input "{self.project}" --package "{package['package']}" --platform codex'''}}, {'type': 'response_item', 'payload': {'type': 'custom_tool_call_output', 'call_id': 'review-input-call', 'output': [{'type': 'input_text', 'text': json.dumps(receipt)}]}}]
	def write_trace(self, ident, rows):
		path = self.home / 'sessions/2026/10/15' / (ident + '.jsonl')
		path.parent.mkdir(parents=True, exist_ok=True)
		path.write_text('\n'.join((json.dumps(row, ensure_ascii=False) for row in rows)) + '\n', encoding='utf-8')
		connection = sqlite3.connect(self.home / 'state_5.sqlite')
		connection.execute('CREATE TABLE IF NOT EXISTS threads(id TEXT PRIMARY KEY, rollout_path TEXT, agent_path TEXT)')
		connection.execute('INSERT OR REPLACE INTO threads VALUES(?,?,?)', (ident, str(path), '/root/reviewer' if ident == self.child else None))
		connection.commit()
		connection.close()
		r = path
		return r
	@contextmanager
	def selected(self):
		config = runtime.platform_settings('codex')
		config['homes'] = {'C2': str(self.home)}
		with patch.object(codex, 'platform_settings', return_value=config), runtime.using('codex', 'C2'):
			yield
	def test_exact_user_text_job_scope_and_cross_platform_request_merge(self):
		other = str(uuid.uuid4())
		rows = [*self.parent_rows, self.message('user', 'Continue analysis.\n\nAfter outage.'), self.message('user', '/upwork-init https://www.upwork.com/jobs/~0299999'), self.message('user', 'Text of another project.')]
		self.write_trace(self.parent, rows)
		requests = codex.native_requests(self.project, self.parent, backend=self.home)
		self.assertEqual(len(requests), 2)
		self.assertTrue(requests[0]['text'].startswith('  $upwork-init'))
		self.assertTrue(requests[0]['text'].endswith('  '))
		flow.resume(self.project, 'cross-system')
		flow.update(self.project, {'action': 'fixture'}, lambda state: state['requests'].append({'id': 'antigravity-existing', 'text': 'Previous exact request', 'native_conversation_id': other, 'response_prepared': {'turn': 'old', 'steps': [1], 'sha256': 'kept'}}))
		with self.selected():
			flow.adopt_requests(self.project, self.parent)
			flow.adopt_requests(self.project, self.parent)
		saved = flow.load(self.project)['requests']
		self.assertEqual(len(saved), 3)
		self.assertEqual(saved[0]['response_prepared']['sha256'], 'kept')
	def test_review_provenance_checks_parent_completion_model_and_assignment(self):
		with self.selected():
			proof = metrics.native_review_proof(self.project, self.parent, self.child)
			self.assertEqual(proof['assignment_source'], 'matching-native-spawn-and-child-ciphertext')
			metrics.verify_native_proof(self.project, proof, package=Path(self.package['package']).name)
			with self.assertRaises(ValueError):
				metrics.verify_native_proof(self.project, proof, package='unassigned-package.json')
			proof['final_response_sha256'] = 'authored-assertion'
			with self.assertRaises(ValueError):
				metrics.verify_native_proof(self.project, proof)
		self.child_rows[-1]['payload']['type'] = 'turn_aborted'
		self.write_trace(self.child, self.child_rows)
		with self.assertRaises(ValueError):
			codex.native_review_proof(self.project, self.parent, self.child, backend=self.home)
		self.child_rows[-1]['payload']['type'] = 'task_complete'
		self.child_rows[1]['payload']['model'] = 'different-model'
		self.write_trace(self.child, self.child_rows)
		with self.assertRaises(ValueError):
			codex.native_review_proof(self.project, self.parent, self.child, backend=self.home)
	def test_native_windows_extended_path_keeps_the_profile_boundary(self):
		path = self.write_trace(self.child, self.child_rows)
		connection = sqlite3.connect(self.home / 'state_5.sqlite')
		connection.execute('UPDATE threads SET rollout_path=? WHERE id=?', ('\\\\?\\' + str(path), self.child))
		connection.commit()
		connection.close()
		with self.selected():
			proof = metrics.native_review_proof(self.project, self.parent, self.child)
			self.assertEqual(Path(proof['native_log']), path)
		outside = self.root / 'outside.jsonl'
		outside.write_bytes(path.read_bytes())
		connection = sqlite3.connect(self.home / 'state_5.sqlite')
		connection.execute('UPDATE threads SET rollout_path=? WHERE id=?', ('\\\\?\\' + str(outside), self.child))
		connection.commit()
		connection.close()
		with self.assertRaisesRegex(ValueError, 'outside the selected profile'):
			codex.native_review_proof(self.project, self.parent, self.child, backend=self.home)
	def test_parent_can_select_another_model_and_effort_with_native_proof(self):
		self.parent_rows[-1]['payload']['arguments'] = json.dumps({'task_name': 'reviewer', 'message': self.assignment, 'model': 'context-selected-model', 'reasoning_effort': 'high', 'fork_turns': 'none'})
		self.write_trace(self.parent, self.parent_rows)
		self.child_rows[1]['payload'].update(model='context-selected-model', effort='high')
		self.write_trace(self.child, self.child_rows)
		with self.selected():
			proof = metrics.native_review_proof(self.project, self.parent, self.child)
			self.assertEqual(proof['model_selection']['selection'], 'explicit-parent-spawn')
			metrics.verify_native_proof(self.project, proof)
	def test_codex_token_metrics_use_response_usage_and_do_not_count_summaries(self):
		row = {'type': 'token_usage_record', 'payload': {'thread_id': self.child, 'turn_id': 'turn', 'response_id': 'response', 'usage': {'input_tokens': 100, 'cached_input_tokens': 60, 'output_tokens': 7}}}
		path = self.write_trace(self.parent, [*self.parent_rows, self.meta(str(uuid.uuid4())), row, row, {'type': 'event_msg', 'payload': {'type': 'token_count', 'info': {'total_token_usage': {'input_tokens': 999}}}}])
		result = metrics.summarize([path], {self.child: [{'stage': 'review', 'first_step': 0, 'last_step': 1000}]})
		self.assertEqual(result['generations'], 1)
		self.assertEqual(result['duplicate_records_ignored'], 1)
		self.assertEqual(result['tokens']['input_tokens']['complete_total'], 100)
		self.assertEqual(result['tokens']['cache_read_tokens']['complete_total'], 60)
		self.assertEqual(result['phases']['review']['generations'], 1)
	def test_encrypted_assignment_or_missing_native_package_execution_cannot_prove_a_review(self):
		self.child_rows[2]['payload']['content'][1]['encrypted_content'] = 'different-assignment'
		self.write_trace(self.child, self.child_rows)
		with self.assertRaisesRegex(ValueError, 'Encrypted native spawn'):
			codex.native_review_proof(self.project, self.parent, self.child, backend=self.home)
		self.child_rows[2]['payload']['content'][1]['encrypted_content'] = self.assignment
		self.child_rows = [item for item in self.child_rows if 'custom_tool_call_output' != item.get('payload', {}).get('type')]
		self.write_trace(self.child, self.child_rows)
		with self.assertRaisesRegex(ValueError, 'review-input execution'):
			codex.native_review_proof(self.project, self.parent, self.child, backend=self.home)
	def test_self_review_uses_codex_parent_evidence_without_requiring_antigravity(self):
		report = self.review_report(self.package, self_review=True)
		self.put_project('ꘖ/KB/Evidence/Reviews/self.json', json.dumps(report))
		with self.selected():
			flow.record_review(self.project, 'ꘖ/KB/Evidence/Reviews/self.json', parent_id=self.parent, reviewer_id=self.parent)
		self.assertFalse(flow.load(self.project)['reviews'][0]['independent'])
	def test_codex_workflow_reviews_current_kb_and_exports_exact_native_request_and_reply(self):
		value = self.valid_review_analysis()
		publish_owned(self.project / 'ꘖ/KB/Analysis.md', render_analysis(value))
		self.put_project('ꘖ/KB/Evidence/init.json', '{}')
		self.put_project('ꘖ/KB/Evidence/research.json', '{}')
		with self.selected():
			flow.resume(self.project, 'continue in Codex')
			flow.adopt_requests(self.project, self.parent)
			flow.complete_stage(self.project, 'identity_init', ['ꘖ/project.json'], ['ꘖ/KB/Evidence/init.json'])
			flow.complete_stage(self.project, 'research', ['ꘖ/project.json'], ['ꘖ/KB/Evidence/research.json'])
			flow.complete_stage(self.project, 'analysis', ['ꘖ/project.json'], ['ꘖ/KB/Analysis.json', 'ꘖ/KB/Analysis.md'])
			answer = 'Exact final answer.\n\nWithout reconstruction.\n\nClient task'
			package = self.review_package(self.parent, response=answer)
			self.set_review_input(package)
			report = self.review_report(package)
			self.child_rows[-1]['payload']['last_agent_message'] = json.dumps(report, ensure_ascii=False)
			self.write_trace(self.child, self.child_rows)
			native = metrics.native_review_proof(self.project, self.parent, self.child)
			self.put_project('ꘖ/KB/Evidence/Reviews/report.json', json.dumps(report))
			flow.record_review(self.project, 'ꘖ/KB/Evidence/Reviews/report.json', parent_id=self.parent, reviewer_id=self.child, native_evidence=native['proof'])
			flow.complete_stage(self.project, 'review', ['ꘖ/KB/Analysis.json'], ['ꘖ/KB/Evidence/Reviews/report.json'])
			flow.complete_stage(self.project, 'kb_review', flow.kb_paths(self.project), ['ꘖ/KB/Analysis.md'], note='Checked current KB')
			flow.record_current_answer(self.project, answer)
			flow.complete_stage(self.project, 'finalize', flow.kb_paths(self.project), ['ꙮ/1 - Analysis/res/1.md'])
			self.assertTrue(all(('complete' == value for value in flow.status(self.project)['stages'].values())))
			draft = self.put_project('result/EN/draft.md', 'User draft\r\n')
			self.put_project('ꘖ/data/continuation.md', 'Current goal: revise the existing proposal.\n')
			snapshot_draft(draft, 'cross_system_proposal')
			draft.write_text('Revised proposal', encoding='utf-8')
			status = flow.status(self.project)
			self.assertEqual(status['scope'], 'initial_analysis')
			self.assertTrue(all(('complete' == value for value in status['stages'].values())))
			self.assertIn('result/EN/draft.md', [item['path'] for item in status['proposal_artifacts']])
			self.assertEqual((draft.parent / 'draft.prev.md').read_bytes(), b'User draft\r\n')
			flow.resume(self.project, 'another request', 'New exact request')
			self.assertEqual(flow.status(self.project)['next_stage'], 'review')
			self.put_project('ꘖ/data/registrations.json', json.dumps({'codex': {'complete': False, 'profiles': {'C2': {'ready': False}}, 'status': 'pending'}}))
			self.assertEqual(flow.status(self.project)['next_stage'], 'identity_init')
			with self.assertRaisesRegex(ValueError, 'registration'):
				flow.complete_stage(self.project, 'identity_init', ['ꘖ/project.json'], ['ꘖ/KB/Evidence/init.json'])
		expected = self.parent_rows[2]['payload']['content'][0]['text']
		self.assertEqual((self.project / 'ꙮ/1 - Analysis/req/1.md').read_bytes().decode(), expected)
		context = (self.project / 'ꙮ/0/Context.md').read_text(encoding='utf-8')
		self.assertIn(expected, context)
		self.assertIn(answer, context)
	def test_second_platform_keeps_original_date_root_manual_kb_and_saved_snapshot(self):
		manual = self.project / 'KB/Project.md'
		manual.write_bytes(manual.read_bytes() + b'\nUSER TEXT\n')
		before = manual.read_bytes()
		state_before = json.loads((self.project / 'ꘖ/project.json').read_text(encoding='utf-8'))
		result = up.initialize_upwork_project(source()['job_id'], 'Different label', '2026-10-16', daily_root=self.root / 'daily', extracted_data=source(), register_native=False, platform='codex')
		self.assertEqual(Path(result['project_dir']), self.project)
		self.assertEqual(manual.read_bytes(), before)
		state = json.loads((self.project / 'ꘖ/project.json').read_text(encoding='utf-8'))
		self.assertEqual(state['request_date'], state_before['request_date'])
		self.assertEqual(state['snapshot'], state_before['snapshot'])
		self.assertFalse((self.project / '.codex/config.toml').exists())
		self.assertIn('`Topic`', (self.project / '.agents/rules/90-project.md').read_text(encoding='utf-8'))
	def test_proposal_export_selects_each_language_final_or_existing_draft(self):
		en = self.put_project('result/EN/draft.md', 'English draft')
		self.put_project('result/RU/draft.md', 'Russian draft')
		self.put_project('result/EN/draft.prev.md', 'Earlier version')
		target, _, _ = generate(self.project, self.project / '.agents/context.json')
		first = target.read_text(encoding='utf-8')
		self.assertIn('English draft', first)
		self.assertIn('Russian draft', first)
		self.assertNotIn('Earlier version', first)
		final = self.put_project('result/EN/final.md', 'Approved English version')
		generate(self.project, self.project / '.agents/context.json')
		saved = target.read_bytes()
		self.assertIn(b'Approved English version', saved)
		self.assertNotIn(b'English draft', saved)
		final.write_bytes(b'')
		with self.assertRaises(ValueError):
			generate(self.project, self.project / '.agents/context.json')
		self.assertEqual(target.read_bytes(), saved)
		self.assertEqual(en.read_text(), 'English draft')
	def test_known_old_context_is_upgraded_with_a_preserved_original(self):
		context = self.project / '.agents/context.json'
		legacy = up.default_context_config()
		next((section for section in legacy['sections'] if 'Proposals' == section['title'])).pop('drafts')
		original = json.dumps(legacy, ensure_ascii=False).encode('utf-8')
		context.write_bytes(original)
		up.configure_project(self.project)
		saved = json.loads(context.read_text(encoding='utf-8'))
		self.assertEqual(next((section for section in saved['sections'] if 'Proposals' == section['title']))['drafts'], ['result'])
		self.assertIn(original, [file.read_bytes() for file in (self.project / 'ꘖ/data/config-history').glob('*.json')])
