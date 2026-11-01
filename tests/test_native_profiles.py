# 2026-11-02 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Replace per-profile Harness projections with shared native connections":
# https://github.com/dmitry-ai/harness/issues/35
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import tomllib
from unittest.mock import patch
from test_agent_tools import TemporaryCase
from agent_tools import configuration, native_profiles as native, runtime
from agent_tools.storage import data_dir_for
class NativeProfileTests(TemporaryCase):
	def setUp(self):
		super().setUp()
		self.primary = self.root / 'harness/code'
		self.primary.mkdir(parents=True)
		(self.root / 'harness/_').mkdir()
		self.config = deepcopy(runtime.settings())
		self.config['workspace_root'] = str(self.root / 'workspace')
		self.gravity = {name: self.root / f'profiles/{name}/.gemini/config' for name in ('A0', 'A6')}
		self.homes = {name: self.root / f'profiles/{name}' for name in ('C1', 'C2')}
		self.config['platforms']['antigravity']['homes'] = {name: str(path.parent.parent) for name, path in self.gravity.items()}
		self.config['platforms']['codex']['homes'] = {name: str(path) for name, path in self.homes.items()}
		self.write(self.primary / 'runtime.json', json.dumps(self.config))
		self.write(self.primary / 'rules/00-scope.md', '---\ntrigger: always_on\n---\n# Scope\nUse canonical sources.  \n')
		self.write(self.primary / 'platforms/codex.md', '# Codex\nPreserve profile settings.  \n')
		self.write(self.primary / 'agents/worker.md', '# Worker\nRead current evidence.  \n')
		for name in ('upwork-init', 'df-article'):
			self.write(self.primary / f'skills/{name}/SKILL.md', f'---\nname: {name}\ndescription: {name} canonical instructions.\n---\nOriginal {name} workflow.\n')
	def write(self, path, text):
		path.parent.mkdir(parents=True, exist_ok=True)
		path.write_bytes(text.encode('utf-8'))
		return path
	def legacy_codex(self, name='C2'):
		home = self.homes[name]
		personal = '# Personal preferences\r\nKeep my exact prefix.\r\n\r\n'
		old = f'# Codex: Upwork\n\n<!-- Generated from {self.primary.as_posix()}; run upwork_project.py build-native to update. -->\n\n' + configuration._loader(self.primary).replace('/scripts/harness.py', '/scripts/upwork_project.py').replace('via harness.py git-read', 'via upwork_project.py git-read') + '\n'
		self.write(home / 'AGENTS.md', personal + old)
		self.write(home / 'config.toml', '# Keep this comment\nmodel = "mine"\n[features]\ncustom = true\n[agents.mine]\ndescription = "My agent"\nconfig_file = "mine.toml"\n')
		for skill in ('upwork-init', 'df-article'):
			self.write(home / f'skills/{skill}/SKILL.md', native._legacy_skill(skill, self.primary))
		for role, agent, purpose, _ in native._role_values(self.primary):
			self.write(home / f'agents/{agent}.toml', native._legacy_role(self.primary, role, agent, purpose).replace('/scripts/harness.py', '/scripts/upwork_project.py').replace('via harness.py git-read', 'via upwork_project.py git-read'))
		return personal.encode('utf-8')
	def install(self, names=('A6', 'C2'), **kwargs):
		return native.install_native_profiles(names, primary=self.primary, **kwargs)
	def snapshot(self):
		return {str(path.relative_to(self.root)): path.read_bytes() for path in self.root.rglob('*') if path.is_file()}
	def test_pilot_changes_only_selected_profiles_and_links_original_content(self):
		personal = self.legacy_codex()
		self.write(self.homes['C2'] / 'skills/personal/SKILL.md', 'My own workflow.\n')
		result = self.install()
		self.assertTrue(result['valid'], result)
		self.assertEqual(set(result['profiles']), {'A6', 'C2'})
		self.assertFalse(self.gravity['A0'].exists())
		self.assertFalse(self.homes['C1'].exists())
		self.assertTrue((self.homes['C2'] / 'AGENTS.md').read_bytes().startswith(personal))
		self.assertIn('platforms/codex/AGENTS.md', (self.homes['C2'] / 'AGENTS.md').read_text(encoding='utf-8'))
		config = tomllib.loads((self.homes['C2'] / 'config.toml').read_text(encoding='utf-8'))
		self.assertEqual(config['model'], 'mine')
		self.assertTrue(config['features']['custom'])
		self.assertEqual(config['agents']['mine']['description'], 'My agent')
		self.assertIn('# Keep this comment', (self.homes['C2'] / 'config.toml').read_text(encoding='utf-8'))
		self.assertNotIn('upwork-aa', config['agents'])
		role = self.homes['C2'] / 'agents/upwork-aa.toml'
		shared = self.primary / 'platforms/codex/agents/upwork-aa.toml'
		self.assertTrue(role.is_symlink())
		self.assertTrue(role.samefile(shared))
		self.assertEqual(role.read_bytes(), shared.read_bytes())
		self.write(shared, '# Updated shared role.\n')
		self.assertEqual(role.read_bytes(), shared.read_bytes())
		alias = self.homes['C2'] / 'skills/df-article'
		self.assertTrue(native._linked(alias))
		self.assertEqual(alias.resolve(), (self.primary / 'skills/df-article').resolve())
		self.assertEqual((alias / 'SKILL.md').read_bytes(), (self.primary / 'skills/df-article/SKILL.md').read_bytes())
		self.write(self.primary / 'skills/df-article/SKILL.md', 'Changed original workflow.\n')
		self.assertEqual((alias / 'SKILL.md').read_text(encoding='utf-8'), 'Changed original workflow.\n')
		self.assertEqual((self.homes['C2'] / 'skills/personal/SKILL.md').read_text(encoding='utf-8'), 'My own workflow.\n')
		self.assertTrue(result['profiles']['C2']['valid'])
		self.assertEqual(result['verification'], 'filesystem-only')
	def test_apply_and_check_are_idempotent_including_central_receipt(self):
		self.legacy_codex()
		self.assertTrue(self.install()['valid'])
		before = self.snapshot()
		again = self.install()
		self.assertTrue(again['valid'], again)
		self.assertEqual(again['written'], [])
		self.assertEqual(again['removed'], [])
		self.assertEqual(again['linked'], [])
		self.assertEqual(self.snapshot(), before)
		self.assertTrue(self.install(check=True)['valid'])
		self.assertEqual(self.snapshot(), before)
	def former_role_config(self):
		self.legacy_codex()
		self.assertTrue(self.install(('C2',))['valid'])
		path = self.homes['C2'] / 'config.toml'
		original = path.read_text(encoding='utf-8')
		definitions = {name: {'description': purpose, 'config_file': (self.primary / f'platforms/codex/agents/{name}.toml').as_posix()} for _, name, purpose, _ in native._role_values(self.primary)}
		former = native._legacy_role_config(original, definitions)
		state = native._load_state(self.primary)
		native._backup(self.primary, state, path, original.encode('utf-8'))
		state['profiles']['C2']['files'][str(path)] = hashlib.sha256(former.encode('utf-8')).hexdigest()
		self.write(native._state_path(self.primary), json.dumps(state))
		self.write(path, former)
		return path, original
	def test_owned_config_role_block_is_retired_preserving_other_edits(self):
		path, original = self.former_role_config()
		changed = path.read_text(encoding='utf-8').replace('model = "mine"', 'model = "new-choice"') + '\n# Later personal setting\n[agents.other]\ndescription = "Keep me"\n'
		self.write(path, changed)
		result = self.install(('C2',))
		self.assertTrue(result['valid'], result)
		actual = path.read_text(encoding='utf-8')
		self.assertEqual(actual, original.replace('model = "mine"', 'model = "new-choice"') + '\n\n# Later personal setting\n[agents.other]\ndescription = "Keep me"\n')
		self.assertTrue(self.install(('C2',), check=True)['valid'])
	def test_edited_owned_config_role_block_is_preserved(self):
		path, _ = self.former_role_config()
		self.write(path, path.read_text(encoding='utf-8').replace('Independent substantive review', 'My own review'))
		before = self.snapshot()
		result = self.install(('C2',))
		self.assertFalse(result['valid'])
		self.assertIn('differs from its exact owned generated block', str(result['issues']))
		self.assertEqual(self.snapshot(), before)
	def test_former_config_role_block_without_receipt_is_preserved(self):
		path, _ = self.former_role_config()
		state = native._load_state(self.primary)
		state['profiles']['C2']['files'].pop(str(path))
		self.write(native._state_path(self.primary), json.dumps(state))
		before = self.snapshot()
		result = self.install(('C2',))
		self.assertFalse(result['valid'])
		self.assertIn('no ownership proof', str(result['issues']))
		self.assertEqual(self.snapshot(), before)
	def test_wrong_role_file_link_is_preserved(self):
		self.assertTrue(self.install(('C2',))['valid'])
		path = self.homes['C2'] / 'agents/upwork-aa.toml'
		path.unlink()
		other = self.write(self.root / 'personal-role.toml', '# Personal role\n')
		path.symlink_to(other)
		result = self.install(('C2',))
		self.assertFalse(result['valid'])
		self.assertTrue(path.samefile(other))
		self.assertIn('different or missing file', str(result['issues']))
	def test_role_link_failure_restores_retired_roles_and_config(self):
		self.legacy_codex()
		before = {path: path.read_bytes() for path in self.homes['C2'].rglob('*') if path.is_file()}
		actual = native._file_link
		calls = 0
		def failing(target, path, primary):
			nonlocal calls
			calls += 1
			if calls == 2:
				raise OSError('Simulated second role link failure')
			actual(target, path, primary)
		with patch.object(native, '_file_link', side_effect=failing):
			result = self.install(('C2',))
		self.assertFalse(result['valid'])
		self.assertEqual({path: path.read_bytes() for path in self.homes['C2'].rglob('*') if path.is_file()}, before)
		self.assertFalse((self.homes['C2'] / 'agents/upwork-aa.toml').is_symlink())
		self.assertFalse(native._state_path(self.primary).exists())
	def test_check_creates_no_lock_receipt_or_profile_files(self):
		before = self.snapshot()
		result = self.install(check=True)
		self.assertFalse(result['valid'])
		self.assertFalse(result['profiles']['A6']['valid'])
		self.assertFalse(result['profiles']['C2']['valid'])
		self.assertEqual(self.snapshot(), before)
		self.assertFalse((data_dir_for(self.primary) / 'native-profiles').exists())
	def test_antigravity_inherits_and_preserves_unrelated_fields_and_hooks(self):
		path = self.gravity['A6'] / 'skills.json'
		original = {'entries': [{'path': (self.primary / 'skills').as_posix()}, {'path': 'mine', 'include_only': ['my-skill']}], 'inherits': [{'path': '/other/skills.json'}], 'exclude': ['hidden']}
		self.write(path, json.dumps(original))
		self.write(self.gravity['A6'] / 'hooks.json', json.dumps({'mine': {'Stop': [{'command': 'my-command'}]}}))
		result = self.install(('A6',))
		self.assertTrue(result['valid'], result)
		actual = json.loads(path.read_text(encoding='utf-8'))
		self.assertEqual(actual['entries'], [original['entries'][1]])
		self.assertEqual(actual['exclude'], ['hidden'])
		self.assertIn(original['inherits'][0], actual['inherits'])
		self.assertIn({'path': (self.primary / 'platforms/antigravity/skills.json').as_posix()}, actual['inherits'])
		self.assertEqual(json.loads((self.gravity['A6'] / 'hooks.json').read_text(encoding='utf-8'))['mine'], {'Stop': [{'command': 'my-command'}]})
	def test_conflicting_hook_blocks_the_whole_selected_plan(self):
		path = self.write(self.gravity['A6'] / 'hooks.json', json.dumps({'final-turn-gate': {'Stop': [{'command': 'my-custom-hook'}]}}))
		before = path.read_bytes()
		result = self.install()
		self.assertFalse(result['valid'])
		self.assertIn('Existing hook final-turn-gate', str(result['issues']))
		self.assertEqual(path.read_bytes(), before)
		self.assertFalse((self.homes['C2'] / 'AGENTS.md').exists())
		self.assertFalse((self.primary / 'platforms/codex/AGENTS.md').exists())
	def test_filtered_legacy_reference_is_preserved_without_duplicate_inheritance(self):
		path = self.write(self.gravity['A6'] / 'rules.json', json.dumps({'entries': [{'path': (self.primary / 'rules').as_posix(), 'include_only': ['00-scope']}]}))
		before = path.read_bytes()
		result = self.install(('A6',))
		self.assertFalse(result['valid'])
		self.assertIn('Filtered legacy', str(result['issues']))
		self.assertEqual(path.read_bytes(), before)
	def test_edited_wrapper_is_not_retired_or_replaced(self):
		self.legacy_codex()
		path = self.homes['C2'] / 'skills/df-article/SKILL.md'
		self.write(path, path.read_text(encoding='utf-8') + 'My additional rule.\n')
		before = self.snapshot()
		result = self.install()
		self.assertFalse(result['valid'])
		self.assertIn('not an exact generated wrapper', str(result['issues']))
		self.assertEqual(path.read_bytes(), before[str(path.relative_to(self.root))])
		self.assertFalse(native._linked(path.parent))
		self.assertFalse((self.gravity['A6'] / 'rules.json').exists())
	def test_wrong_skill_link_is_preserved(self):
		other = self.root / 'other-skill'
		other.mkdir()
		path = self.homes['C2'] / 'skills/df-article'
		native._directory_link(other, path, self.primary)
		result = self.install(('C2',))
		self.assertFalse(result['valid'])
		self.assertEqual(path.resolve(), other.resolve())
		self.assertIn('different or missing directory', str(result['issues']))
	def test_custom_same_name_role_and_personal_loader_edit_are_preserved(self):
		self.legacy_codex()
		path = self.homes['C2'] / 'config.toml'
		self.write(path, path.read_text(encoding='utf-8') + '[agents.upwork-aa]\ndescription = "My reviewer"\nconfig_file = "my-reviewer.toml"\n')
		before = path.read_bytes()
		result = self.install(('C2',))
		self.assertFalse(result['valid'])
		self.assertEqual(path.read_bytes(), before)
		self.assertTrue((self.homes['C2'] / 'agents/upwork-aa.toml').exists())
		self.assertFalse(native._linked(self.homes['C2'] / 'skills/df-article'))
	def test_existing_compact_loader_manual_edit_is_not_overwritten(self):
		self.assertTrue(self.install(('C2',))['valid'])
		path = self.homes['C2'] / 'AGENTS.md'
		self.write(path, path.read_text(encoding='utf-8').replace('before doing any work', 'only when I ask'))
		before = path.read_bytes()
		result = self.install(('C2',))
		self.assertFalse(result['valid'])
		self.assertEqual(path.read_bytes(), before)
	def test_new_link_failure_rolls_back_existing_profile_files(self):
		self.legacy_codex()
		before = {path: path.read_bytes() for path in self.homes['C2'].rglob('*') if path.is_file()}
		actual = native._directory_link
		calls = 0
		def failing(target, path, primary):
			nonlocal calls
			calls += 1
			if calls == 2:
				raise OSError('Simulated second link failure')
			actual(target, path, primary)
		with patch.object(native, '_directory_link', side_effect=failing):
			result = self.install(('C2',))
		self.assertFalse(result['valid'])
		self.assertEqual({path: path.read_bytes() for path in self.homes['C2'].rglob('*') if path.is_file()}, before)
		self.assertFalse(native._linked(self.homes['C2'] / 'skills/df-article'))
		self.assertFalse((self.primary / 'platforms/codex/AGENTS.md').exists())
		self.assertFalse(native._state_path(self.primary).exists())
	def test_concurrent_preimage_change_is_preserved_before_application(self):
		self.legacy_codex()
		path = self.homes['C2'] / 'AGENTS.md'
		backup = native._backup
		changed = False
		def changing(primary, state, target, payload):
			nonlocal changed
			result = backup(primary, state, target, payload)
			if not changed:
				self.write(path, 'Concurrent personal instructions.\n')
				changed = True
			return result
		with patch.object(native, '_backup', side_effect=changing):
			result = self.install(('C2',))
		self.assertFalse(result['valid'])
		self.assertEqual(path.read_text(encoding='utf-8'), 'Concurrent personal instructions.\n')
		self.assertFalse((self.primary / 'platforms/codex/AGENTS.md').exists())
	def test_shared_manual_edit_is_preserved(self):
		self.assertTrue(native.build_shared_native(self.primary)['valid'])
		path = self.primary / 'platforms/codex/AGENTS.md'
		self.write(path, path.read_text(encoding='utf-8') + '\nMy custom bootstrap rule.\n')
		before = path.read_bytes()
		result = self.install(('A6',))
		self.assertFalse(result['valid'])
		self.assertEqual(path.read_bytes(), before)
		self.assertFalse((self.gravity['A6'] / 'rules.json').exists())
	def test_project_retirement_requires_exact_ownership_and_keeps_unrelated_files(self):
		project = self.root / 'workspace'
		paths = native.legacy_project_projection_paths(project, self.primary)
		previous = {}
		originals = {}
		for index, path in enumerate(paths):
			self.write(path, f'Owned projection {index}.\n')
			previous[str(path.resolve())] = hashlib.sha256(path.read_bytes()).hexdigest()
			originals[str(path)] = path.read_bytes()
		unrelated = self.write(project / 'AGENTS.md', 'Keep my own project guidance.\n')
		previous[str(unrelated)] = hashlib.sha256(unrelated.read_bytes()).hexdigest()
		receipt = self.write(data_dir_for(project) / 'native-config.json', json.dumps(previous))
		self.assertFalse(native.retire_owned_project_projections(project, primary=self.primary, check=True)['valid'])
		result = native.retire_owned_project_projections(project, primary=self.primary)
		self.assertTrue(result['valid'], result)
		self.assertTrue(all(not path.exists() for path in paths))
		self.assertTrue(unrelated.exists())
		self.assertEqual(json.loads(receipt.read_text(encoding='utf-8')), {str(unrelated): previous[str(unrelated)]})
		self.assertFalse((project / '.agents').exists())
		state = native._load_state(self.primary)
		for path, content in originals.items():
			key = path + ':' + hashlib.sha256(content).hexdigest()
			self.assertEqual(Path(state['backups'][key]).read_bytes(), content)
		self.assertTrue(native.retire_owned_project_projections(project, primary=self.primary, check=True)['valid'])
	def test_edited_project_projection_blocks_all_retirements(self):
		project = self.root / 'workspace'
		paths = native.legacy_project_projection_paths(project, self.primary)
		previous = {}
		for index, path in enumerate(paths):
			self.write(path, f'Owned projection {index}.\n')
			previous[str(path.resolve())] = hashlib.sha256(path.read_bytes()).hexdigest()
		self.write(data_dir_for(project) / 'native-config.json', json.dumps(previous))
		self.write(paths[0], 'Manual edited projection.\n')
		result = native.retire_owned_project_projections(project, primary=self.primary)
		self.assertFalse(result['valid'])
		self.assertTrue(all(path.exists() for path in paths))
	def test_project_retirement_skips_a_linked_source_directory(self):
		project = self.root / 'workspace'
		alias = project / '.agents/skills/df-article'
		native._directory_link(self.primary / 'skills/df-article', alias, self.primary)
		original = (self.primary / 'skills/df-article/SKILL.md').read_bytes()
		result = native.retire_owned_project_projections(project, primary=self.primary)
		self.assertTrue(result['valid'], result)
		self.assertTrue(native._linked(alias))
		self.assertEqual((alias / 'SKILL.md').read_bytes(), original)
	def rename_af(self):
		self.config['platforms']['codex']['roles']['AF']['agent'] = 'evidence-worker'
		self.write(self.primary / 'runtime.json', json.dumps(self.config))
	def test_role_rename_retires_only_owned_links_and_shared_definition(self):
		self.assertTrue(self.install(('C2',))['valid'])
		old = self.homes['C2'] / 'agents/upwork-af.toml'
		shared = self.primary / 'platforms/codex/agents/upwork-af.toml'
		original = shared.read_bytes()
		personal = self.write(self.homes['C2'] / 'agents/personal.toml', '# My personal role\n')
		unowned = self.write(self.primary / 'platforms/codex/agents/unowned.toml', '# Unowned definition\n')
		self.rename_af()
		self.assertFalse(self.install(('C2',), check=True)['valid'])
		result = self.install(('C2',))
		self.assertTrue(result['valid'], result)
		self.assertFalse(old.is_symlink())
		self.assertFalse(shared.exists())
		self.assertTrue((self.homes['C2'] / 'agents/evidence-worker.toml').samefile(self.primary / 'platforms/codex/agents/evidence-worker.toml'))
		self.assertEqual(personal.read_text(encoding='utf-8'), '# My personal role\n')
		self.assertEqual(unowned.read_text(encoding='utf-8'), '# Unowned definition\n')
		state = native._load_state(self.primary)
		self.assertNotIn(str(shared), state['shared'])
		self.assertNotIn(str(old), state['profiles']['C2']['role_targets'])
		self.assertIn(str(old), state['profiles']['C2']['retired'])
		backup = state['backups'][str(shared) + ':' + hashlib.sha256(original).hexdigest()]
		self.assertEqual(Path(backup).read_bytes(), original)
		before = self.snapshot()
		self.assertTrue(self.install(('C2',), check=True)['valid'])
		again = self.install(('C2',))
		self.assertEqual((again['written'], again['removed'], again['linked']), ([], [], []))
		self.assertEqual(before, self.snapshot())
	def test_role_rename_keeps_unselected_profile_and_shared_target_owned(self):
		self.assertTrue(self.install(('C1', 'C2'))['valid'])
		shared = self.primary / 'platforms/codex/agents/upwork-af.toml'
		old_c1 = self.homes['C1'] / 'agents/upwork-af.toml'
		self.rename_af()
		self.assertTrue(self.install(('C2',))['valid'])
		self.assertTrue(old_c1.samefile(shared))
		state = native._load_state(self.primary)
		self.assertEqual(state['profiles']['C1']['role_targets'][str(old_c1)], str(shared))
		self.assertIn(str(shared), state['shared'])
		self.assertTrue(self.install(('C1',))['valid'])
		self.assertFalse(old_c1.is_symlink())
		self.assertFalse(shared.exists())
		self.assertTrue(self.install(('C1', 'C2'), check=True)['valid'])
	def test_removed_role_retires_its_owned_link_and_definition(self):
		self.assertTrue(self.install(('C2',))['valid'])
		self.config['platforms']['codex']['roles'].pop('AF')
		self.write(self.primary / 'runtime.json', json.dumps(self.config))
		result = self.install(('C2',))
		self.assertTrue(result['valid'], result)
		self.assertFalse((self.homes['C2'] / 'agents/upwork-af.toml').is_symlink())
		self.assertFalse((self.primary / 'platforms/codex/agents/upwork-af.toml').exists())
		self.assertTrue((self.homes['C2'] / 'agents/upwork-aa.toml').is_symlink())
		self.assertTrue(self.install(('C2',), check=True)['valid'])
	def test_edited_obsolete_role_link_blocks_rename_without_orphaning_ownership(self):
		self.assertTrue(self.install(('C2',))['valid'])
		old = self.homes['C2'] / 'agents/upwork-af.toml'
		old.unlink()
		personal = self.write(self.root / 'my-role.toml', '# My changed role\n')
		old.symlink_to(personal)
		self.rename_af()
		before = self.snapshot()
		result = self.install(('C2',))
		self.assertFalse(result['valid'])
		self.assertIn('Obsolete managed role link changed', str(result['issues']))
		self.assertEqual(self.snapshot(), before)
		self.assertIn(str(old), native._load_state(self.primary)['profiles']['C2']['role_targets'])
	def test_edited_obsolete_shared_role_is_preserved(self):
		self.assertTrue(self.install(('C2',))['valid'])
		shared = self.primary / 'platforms/codex/agents/upwork-af.toml'
		self.write(shared, shared.read_text(encoding='utf-8') + '# Personal modification\n')
		self.rename_af()
		before = self.snapshot()
		result = self.install(('C2',))
		self.assertFalse(result['valid'])
		self.assertIn('Obsolete shared role definition changed', str(result['issues']))
		self.assertEqual(self.snapshot(), before)
	def test_role_rename_failure_restores_retired_link_definition_and_receipt(self):
		self.assertTrue(self.install(('C2',))['valid'])
		old = self.homes['C2'] / 'agents/upwork-af.toml'
		shared = self.primary / 'platforms/codex/agents/upwork-af.toml'
		before = shared.read_bytes()
		receipt = native._state_path(self.primary).read_bytes()
		self.rename_af()
		actual = native._file_link
		def failing(target, path, primary):
			if path.name == 'evidence-worker.toml':
				raise OSError('New renamed role link failed')
			actual(target, path, primary)
		with patch.object(native, '_file_link', side_effect=failing):
			result = self.install(('C2',))
		self.assertFalse(result['valid'])
		self.assertEqual(result['rollback']['status'], 'complete')
		self.assertTrue(old.samefile(shared))
		self.assertEqual(shared.read_bytes(), before)
		self.assertEqual(native._state_path(self.primary).read_bytes(), receipt)
		self.assertFalse((self.primary / 'platforms/codex/agents/evidence-worker.toml').exists())
	def test_concurrent_personal_edit_does_not_stop_other_guarded_rollback(self):
		self.assertTrue(native.build_shared_native(self.primary)['valid'])
		bootstrap = self.primary / 'platforms/codex/AGENTS.md'
		before = bootstrap.read_bytes()
		receipt = native._state_path(self.primary).read_bytes()
		personal = self.write(self.homes['C2'] / 'AGENTS.md', '# My preferences\n')
		self.write(self.primary / 'rules/11-new.md', '---\ntrigger: always_on\n---\n# New\nNew instruction.\n')
		def failing(target, path, primary):
			self.write(personal, '# Concurrent personal edit\n')
			raise OSError('Role creation failed after concurrent edit')
		with patch.object(native, '_file_link', side_effect=failing):
			result = self.install(('C2',))
		self.assertFalse(result['valid'])
		self.assertEqual(result['rollback']['status'], 'partial')
		self.assertEqual(personal.read_text(encoding='utf-8'), '# Concurrent personal edit\n')
		self.assertEqual(bootstrap.read_bytes(), before)
		self.assertEqual(native._state_path(self.primary).read_bytes(), receipt)
		self.assertFalse(native._linked(self.homes['C2'] / 'skills/df-article'))
		self.assertTrue(Path(result['recovery_receipt']).is_file())
		recovery = json.loads(Path(result['recovery_receipt']).read_text(encoding='utf-8'))
		self.assertEqual(recovery['rollback']['status'], 'partial')
		self.assertTrue(recovery['backups'])
	def test_changed_created_link_does_not_stop_other_guarded_rollback(self):
		personal = self.write(self.homes['C2'] / 'AGENTS.md', '# Original preferences\n')
		external = self.write(self.root / 'personal-role.toml', '# Personal role\n')
		actual = native._file_link
		changed = self.homes['C2'] / 'agents/upwork-aa.toml'
		def failing(target, path, primary):
			if path.name == 'upwork-af.toml':
				changed.unlink()
				changed.symlink_to(external)
				raise OSError('Later role creation failed')
			actual(target, path, primary)
		with patch.object(native, '_file_link', side_effect=failing):
			result = self.install(('C2',))
		self.assertFalse(result['valid'])
		self.assertEqual(result['rollback']['status'], 'partial')
		self.assertTrue(changed.samefile(external))
		self.assertEqual(personal.read_text(encoding='utf-8'), '# Original preferences\n')
		self.assertFalse((self.primary / 'platforms/codex/AGENTS.md').exists())
		self.assertFalse(native._linked(self.homes['C2'] / 'skills/upwork-init'))
	def test_skill_parent_link_injected_during_backup_is_preserved_without_escape(self):
		personal = self.write(self.homes['C2'] / 'AGENTS.md', '# Original preferences\n')
		external = self.root / 'external-user-skills'
		external.mkdir()
		sentinel = self.write(external / 'personal.txt', 'Preserve me\n')
		parent = self.homes['C2'] / 'skills'
		actual = native._backup
		def changing(primary, state, target, payload):
			value = actual(primary, state, target, payload)
			if not native._linked(parent):
				native._directory_link(external, parent, self.primary)
			return value
		with patch.object(native, '_backup', side_effect=changing):
			result = self.install(('C2',))
		self.assertFalse(result['valid'])
		self.assertIn('Linked skill parent directory', str(result['issues']))
		self.assertTrue(parent.samefile(external))
		self.assertEqual(list(external.iterdir()), [sentinel])
		self.assertEqual(personal.read_text(encoding='utf-8'), '# Original preferences\n')
		self.assertFalse((self.primary / 'platforms/codex/AGENTS.md').exists())
	def test_skill_parent_link_injected_immediately_before_creation_cannot_escape(self):
		personal = self.write(self.homes['C2'] / 'AGENTS.md', '# Original preferences\n')
		external = self.root / 'external-user-skills'
		external.mkdir()
		parent = self.homes['C2'] / 'skills'
		actual = native._directory_link
		def changing(target, path, primary):
			if not native._linked(parent):
				actual(external, parent, primary)
			actual(target, path, primary)
		with patch.object(native, '_directory_link', side_effect=changing):
			result = self.install(('C2',))
		self.assertFalse(result['valid'])
		self.assertTrue(parent.samefile(external))
		self.assertEqual(list(external.iterdir()), [])
		self.assertEqual(personal.read_text(encoding='utf-8'), '# Original preferences\n')
		self.assertFalse((self.primary / 'platforms/codex/AGENTS.md').exists())
	def test_role_parent_link_injected_immediately_before_creation_cannot_escape(self):
		personal = self.write(self.homes['C2'] / 'AGENTS.md', '# Original preferences\n')
		external = self.root / 'external-user-roles'
		external.mkdir()
		parent = self.homes['C2'] / 'agents'
		actual = native._file_link
		def changing(target, path, primary):
			if not native._linked(parent):
				native._directory_link(external, parent, primary)
			actual(target, path, primary)
		with patch.object(native, '_file_link', side_effect=changing):
			result = self.install(('C2',))
		self.assertFalse(result['valid'])
		self.assertTrue(parent.samefile(external))
		self.assertEqual(list(external.iterdir()), [])
		self.assertEqual(personal.read_text(encoding='utf-8'), '# Original preferences\n')
		self.assertFalse((self.primary / 'platforms/codex/AGENTS.md').exists())
	def renamed_article(self):
		source = self.primary / 'skills/df-article'
		renamed = self.primary / 'skills/article-renamed'
		source.rename(renamed)
		return source, renamed
	def test_skill_rename_retires_owned_dangling_link_with_identity_backup(self):
		self.assertTrue(self.install(('C2',))['valid'])
		old = self.homes['C2'] / 'skills/df-article'
		identity = native._directory_link_identity(old)
		source, renamed = self.renamed_article()
		original = (renamed / 'SKILL.md').read_bytes()
		personal = self.root / 'personal-skill'
		personal.mkdir()
		unknown = self.homes['C2'] / 'skills/personal'
		native._directory_link(personal, unknown, self.primary)
		self.assertFalse(old.exists())
		self.assertTrue(native._linked(old))
		self.assertFalse(self.install(('C2',), check=True)['valid'])
		result = self.install(('C2',))
		self.assertTrue(result['valid'], result)
		self.assertFalse(native._exists(old))
		self.assertFalse(native._linked(old))
		self.assertTrue((self.homes['C2'] / 'skills/article-renamed').samefile(renamed))
		self.assertEqual((renamed / 'SKILL.md').read_bytes(), original)
		self.assertTrue(unknown.samefile(personal))
		state = native._load_state(self.primary)
		self.assertNotIn(str(old), state['profiles']['C2']['links'])
		self.assertIn(str(old), state['profiles']['C2']['retired'])
		payload = native._json(identity)
		backup = state['backups'][str(old) + ':' + hashlib.sha256(payload).hexdigest()]
		self.assertEqual(Path(backup).read_bytes(), payload)
		before = self.snapshot()
		self.assertTrue(self.install(('C2',), check=True)['valid'])
		again = self.install(('C2',))
		self.assertEqual((again['written'], again['removed'], again['linked']), ([], [], []))
		self.assertEqual(self.snapshot(), before)
	def test_removed_skill_retires_alias_without_deleting_canonical_directory(self):
		self.assertTrue(self.install(('C2',))['valid'])
		source = self.primary / 'skills/df-article'
		original = (source / 'SKILL.md').read_bytes()
		(source / 'SKILL.md').rename(source / 'ARCHIVED.md')
		result = self.install(('C2',))
		self.assertTrue(result['valid'], result)
		self.assertFalse(native._exists(self.homes['C2'] / 'skills/df-article'))
		self.assertTrue(source.is_dir())
		self.assertEqual((source / 'ARCHIVED.md').read_bytes(), original)
		self.assertTrue(self.install(('C2',), check=True)['valid'])
	def test_dangling_directory_symlink_skill_is_retired(self):
		self.assertTrue(self.install(('C2',))['valid'])
		old = self.homes['C2'] / 'skills/df-article'
		source = self.primary / 'skills/df-article'
		native._remove_link(old, source)
		old.symlink_to(source, target_is_directory=True)
		self.renamed_article()
		self.assertTrue(old.is_symlink())
		self.assertFalse(old.exists())
		result = self.install(('C2',))
		self.assertTrue(result['valid'], result)
		self.assertFalse(old.is_symlink())
	def test_skill_rename_does_not_touch_unselected_profile_or_forget_ownership(self):
		self.assertTrue(self.install(('C1', 'C2'))['valid'])
		source, renamed = self.renamed_article()
		old_c1 = self.homes['C1'] / 'skills/df-article'
		self.assertTrue(self.install(('C2',))['valid'])
		self.assertTrue(native._linked(old_c1))
		self.assertEqual(native._load_state(self.primary)['profiles']['C1']['links'][str(old_c1)], str(source))
		self.assertTrue(self.install(('C1',))['valid'])
		self.assertFalse(native._exists(old_c1))
		self.assertTrue((self.homes['C1'] / 'skills/article-renamed').samefile(renamed))
		self.assertTrue(self.install(('C1', 'C2'), check=True)['valid'])
	def test_manually_replaced_obsolete_skill_directory_is_preserved(self):
		self.assertTrue(self.install(('C2',))['valid'])
		source, renamed = self.renamed_article()
		old = self.homes['C2'] / 'skills/df-article'
		native._remove_link(old, source)
		sentinel = self.write(old / 'personal.txt', 'My content\n')
		before = self.snapshot()
		result = self.install(('C2',))
		self.assertFalse(result['valid'])
		self.assertIn('Obsolete managed skill link changed', str(result['issues']))
		self.assertEqual(self.snapshot(), before)
		self.assertEqual(sentinel.read_text(encoding='utf-8'), 'My content\n')
		self.assertTrue((renamed / 'SKILL.md').is_file())
	def test_wrong_target_obsolete_skill_link_is_preserved(self):
		self.assertTrue(self.install(('C2',))['valid'])
		source, _ = self.renamed_article()
		old = self.homes['C2'] / 'skills/df-article'
		native._remove_link(old, source)
		personal = self.root / 'personal-skill'
		personal.mkdir()
		native._directory_link(personal, old, self.primary)
		before = self.snapshot()
		result = self.install(('C2',))
		self.assertFalse(result['valid'])
		self.assertTrue(old.samefile(personal))
		self.assertEqual(self.snapshot(), before)
	def test_obsolete_skill_under_linked_parent_is_preserved(self):
		self.assertTrue(self.install(('C2',))['valid'])
		self.renamed_article()
		parent = self.homes['C2'] / 'skills'
		external = self.root / 'external-user-skills'
		parent.rename(external)
		native._directory_link(external, parent, self.primary)
		before = {p.name: native._directory_link_identity(p) for p in external.iterdir()}
		result = self.install(('C2',))
		self.assertFalse(result['valid'])
		self.assertIn('Linked obsolete skill parent directory', str(result['issues']))
		self.assertTrue(parent.samefile(external))
		self.assertEqual({p.name: native._directory_link_identity(p) for p in external.iterdir()}, before)
	def check_skill_rename_rollback(self, directory_symlink=False):
		self.assertTrue(self.install(('C2',))['valid'])
		old = self.homes['C2'] / 'skills/df-article'
		source = self.primary / 'skills/df-article'
		if directory_symlink:
			native._remove_link(old, source)
			old.symlink_to(source, target_is_directory=True)
		identity = native._directory_link_identity(old)
		_, renamed = self.renamed_article()
		original = (renamed / 'SKILL.md').read_bytes()
		receipt = native._state_path(self.primary).read_bytes()
		actual = native._directory_link
		def failing(target, path, primary):
			if path.name == 'article-renamed':
				raise OSError('Renamed skill creation failed')
			actual(target, path, primary)
		with patch.object(native, '_directory_link', side_effect=failing):
			result = self.install(('C2',))
		self.assertFalse(result['valid'])
		self.assertEqual(result['rollback']['status'], 'complete', result)
		self.assertEqual(native._directory_link_identity(old), identity)
		self.assertFalse(old.exists())
		self.assertEqual((renamed / 'SKILL.md').read_bytes(), original)
		self.assertEqual(native._state_path(self.primary).read_bytes(), receipt)
		self.assertFalse(native._exists(self.homes['C2'] / 'skills/article-renamed'))
	def test_failed_skill_rename_restores_dangling_directory_junction_identity(self):
		self.check_skill_rename_rollback()
	def test_failed_skill_rename_restores_dangling_directory_symlink_identity(self):
		self.check_skill_rename_rollback(directory_symlink=True)
	def test_obsolete_skill_changed_during_backup_is_preserved(self):
		self.assertTrue(self.install(('C2',))['valid'])
		source, _ = self.renamed_article()
		old = self.homes['C2'] / 'skills/df-article'
		personal = self.root / 'personal-skill'
		personal.mkdir()
		receipt = native._state_path(self.primary).read_bytes()
		actual = native._backup
		def changing(primary, state, path, payload):
			value = actual(primary, state, path, payload)
			if path == old:
				native._remove_link(old, source)
				native._directory_link(personal, old, self.primary)
			return value
		with patch.object(native, '_backup', side_effect=changing):
			result = self.install(('C2',))
		self.assertFalse(result['valid'])
		self.assertIn('Obsolete skill link changed during migration', str(result['issues']))
		self.assertTrue(old.samefile(personal))
		self.assertEqual(native._state_path(self.primary).read_bytes(), receipt)
	def test_concurrent_replacement_during_skill_rollback_is_preserved(self):
		self.assertTrue(self.install(('C2',))['valid'])
		self.renamed_article()
		old = self.homes['C2'] / 'skills/df-article'
		receipt = native._state_path(self.primary).read_bytes()
		def failing(target, path, primary):
			self.write(old / 'personal.txt', 'Concurrent replacement\n')
			raise OSError('Renamed skill creation failed')
		with patch.object(native, '_directory_link', side_effect=failing):
			result = self.install(('C2',))
		self.assertFalse(result['valid'])
		self.assertEqual(result['rollback']['status'], 'partial')
		self.assertFalse(native._linked(old))
		self.assertEqual((old / 'personal.txt').read_text(encoding='utf-8'), 'Concurrent replacement\n')
		self.assertEqual(native._state_path(self.primary).read_bytes(), receipt)
		self.assertTrue(Path(result['recovery_receipt']).is_file())
	def test_unknown_prior_link_record_is_preserved_during_skill_rename(self):
		self.assertTrue(self.install(('C2',))['valid'])
		unknown = self.homes['C2'] / 'custom/personal-skill'
		personal = self.root / 'personal-skill'
		personal.mkdir()
		native._directory_link(personal, unknown, self.primary)
		state = native._load_state(self.primary)
		state['profiles']['C2']['links'][str(unknown)] = str(personal)
		self.write(native._state_path(self.primary), json.dumps(state))
		self.renamed_article()
		self.assertTrue(self.install(('C2',))['valid'])
		self.assertTrue(unknown.samefile(personal))
		self.assertEqual(native._load_state(self.primary)['profiles']['C2']['links'][str(unknown)], str(personal))
