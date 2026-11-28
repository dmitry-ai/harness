# 2026-11-28 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from copy import deepcopy
from pathlib import Path
from unittest.mock import patch
import json
import os
import time
import unittest
from test_agent_tools import TemporaryCase
from Df.Harness.lib import runtime_cache
from agent_tools import path_registry as pr, runtime
# 2026-11-28 "Implement AddonsProfileAdapter with stat-keyed runtime cache invalidation": https://github.com/dmitry-ai/harness/issues/465
class AddonsProfileAdapterTests(TemporaryCase):
	# @used-by :meth:`AddonsProfileAdapterTests.test_cache_invalidates_for_profiles_and_paths_registry_coherently()`
	# @used-by :meth:`AddonsProfileAdapterTests.test_copied_materialized_config_stays_isolated_from_live_profiles()`
	# @used-by :meth:`AddonsProfileAdapterTests.test_escapes_template_literals_and_rejects_traversal_and_symlinks()`
	# @used-by :meth:`AddonsProfileAdapterTests.test_projects_addons_profiles_with_overrides_and_env_expansion()`
	# @used-by :meth:`AddonsProfileAdapterTests.test_rejects_conflicts_malformed_schema_and_unknown_overrides()`
	def _write_fixture(self, profiles_payload: dict | None, *, overrides: dict | None=None, extra_platform: dict | None=None, raw_profiles_text: str | None=None) -> tuple[Path, Path, Path, Path]:
		roaming = (self.root / 'Users/alice/AppData/Roaming').resolve()
		user_home = (self.root / 'Users/alice').resolve()
		profiles_file = (self.root / 'addons/Multi-Account/profiles.json').resolve()
		if None is not raw_profiles_text:
			profiles_file.parent.mkdir(parents=True, exist_ok=True)
			profiles_file.write_text(raw_profiles_text, encoding='utf-8')
		elif None is not profiles_payload:
			profiles_file.parent.mkdir(parents=True, exist_ok=True)
			profiles_file.write_text(json.dumps(profiles_payload), encoding='utf-8')
		reg_file = self.root / 'paths.json'
		reg_file.write_text(json.dumps({
			'version': 1,
			'variables': {
				'OS_USER_HOME': user_home.as_posix(),
				'USER_HOME': '${OS_USER_HOME}',
				'APPDATA': roaming.as_posix(),
				'ANTIGRAVITY_ADDONS_CODE': (self.root / 'addons').resolve().as_posix(),
			},
			'tools': {},
			'harness_stores': {},
			'project_profiles': {'default': {'paths': {}}},
			'platform_layouts': {
				'antigravity': {
					'default_home': '${USER_HOME}',
					'default_user_data_dir': '${APPDATA}/Antigravity',
					'defaults': {'gemini_dir': '${INSTANCE_HOME}/.gemini', 'config_dir': '${INSTANCE_GEMINI_DIR}/config', 'backend_dir': '${INSTANCE_GEMINI_DIR}/antigravity'},
					'system_paths': {'home': '${INSTANCE_HOME}', 'user_data_dir': '${INSTANCE_USER_DATA}', 'config_dir': '${INSTANCE_CONFIG_DIR}', 'backend_dir': '${INSTANCE_BACKEND_DIR}', 'logs_dir': '${INSTANCE_USER_DATA}/logs'},
				}
			},
		}), encoding='utf-8')
		ag_cfg = {
			'enabled': True,
			'label': 'Antigravity (A)',
			'adapter': 'antigravity',
			'addons_profiles_json': '${ANTIGRAVITY_ADDONS_CODE}/Multi-Account/profiles.json',
			'instances_source': 'addons_profiles_json',
		}
		if None is not overrides:
			ag_cfg['instance_overrides'] = overrides
		if None is not extra_platform:
			ag_cfg.update(extra_platform)
		rt_file = self.root / 'runtime.json'
		rt_file.write_text(json.dumps({'version': 2, 'paths_registry': 'paths.json', 'workspace_root': self.root.as_posix(), 'platforms': {'antigravity': ag_cfg}}), encoding='utf-8')
		return (rt_file, profiles_file, reg_file, roaming)
	# @used-by :mod:`unittest`
	def test_cache_invalidates_for_profiles_and_paths_registry_coherently(self):
		payload = {'schemaVersion': 1, 'skillsRoot': '${ANTIGRAVITY_ADDONS_CODE}', 'profiles': [{'id': 'A0', 'userData': 'Antigravity'}, {'id': 'A6', 'userData': 'Antigravity-A6', 'email': 'admin6@mage2.pro', 'chromeShortcut': '6'}]}
		rt_file, profiles_file, reg_file, _ = self._write_fixture(payload)
		key1, first = runtime_cache.dfh_load_cached_settings_readonly(rt_file, runtime._validate_runtime)
		self.assertEqual(['A0', 'A6'], list(first['platforms']['antigravity']['instances']))
		time.sleep(0.02)
		payload['profiles'].insert(1, {'id': 'A5', 'userData': 'Antigravity-A5', 'email': 'admin5@mage2.pro', 'chromeShortcut': '5'})
		profiles_file.write_text(json.dumps(payload), encoding='utf-8')
		key2, second = runtime_cache.dfh_load_cached_settings_readonly(rt_file, runtime._validate_runtime)
		self.assertEqual(['A0', 'A5', 'A6'], list(second['platforms']['antigravity']['instances']))
		self.assertNotEqual(key1, key2)
		time.sleep(0.02)
		reg_data = json.loads(reg_file.read_text(encoding='utf-8'))
		new_roaming = (self.root / 'Users/bob/AppData/Roaming').resolve()
		reg_data['variables']['APPDATA'] = new_roaming.as_posix()
		reg_file.write_text(json.dumps(reg_data, indent=2), encoding='utf-8')
		key3, third = runtime_cache.dfh_load_cached_settings_readonly(rt_file, runtime._validate_runtime)
		self.assertEqual((new_roaming / 'Antigravity-A5/home').as_posix(), third['platforms']['antigravity']['instances']['A5']['home'])
		self.assertNotEqual(key2, key3)
	# @used-by :mod:`unittest`
	def test_copied_materialized_config_stays_isolated_from_live_profiles(self):
		payload = {'schemaVersion': 1, 'skillsRoot': '${ANTIGRAVITY_ADDONS_CODE}', 'profiles': [{'id': 'A0', 'userData': 'Antigravity'}, {'id': 'A5', 'userData': 'Antigravity-A5', 'email': 'admin5@mage2.pro', 'chromeShortcut': '5'}]}
		rt_file, _, _, _ = self._write_fixture(payload)
		loaded = deepcopy(runtime.settings(rt_file))
		self.assertNotIn('instances_source', loaded['platforms']['antigravity'])
		self.assertNotIn('instance_overrides', loaded['platforms']['antigravity'])
		loaded['platforms']['antigravity']['instances'] = {'A0': {'enabled': True, 'primary': True, 'home': (self.root / 'custom_a0').as_posix()}}
		synth_rt = self.root / 'synth-runtime.json'
		synth_rt.write_text(json.dumps(loaded), encoding='utf-8')
		reloaded = runtime.settings(synth_rt)
		self.assertEqual(['A0'], list(reloaded['platforms']['antigravity']['instances']))
	# @used-by :mod:`unittest`
	def test_escapes_template_literals_and_rejects_traversal_and_symlinks(self):
		payload = {'schemaVersion': 1, 'skillsRoot': '${ANTIGRAVITY_ADDONS_CODE}', 'profiles': [{'id': 'A0', 'userData': 'Antigravity'}, {'id': 'A5', 'userData': 'Antigravity-A5', 'label': 'Literal ${APPDATA} %USERPROFILE%', 'email': 'a+${USER_HOME}@mage2.pro', 'chromeShortcut': '5'}]}
		rt_file, _, _, _ = self._write_fixture(payload)
		inst5 = runtime.settings(rt_file)['platforms']['antigravity']['instances']['A5']
		self.assertEqual('Literal ${APPDATA} %USERPROFILE%', inst5['label'])
		self.assertEqual('a+${USER_HOME}@mage2.pro', inst5['account_email'])
		for bad_ud in ('../escape', 'nested/dir', 'C:/Windows', 'dir\\sub'):
			rt_bad, _, _, _ = self._write_fixture({'schemaVersion': 1, 'skillsRoot': 'x', 'profiles': [{'id': 'A0', 'userData': 'Antigravity'}, {'id': 'A5', 'userData': bad_ud, 'email': 'a5@mage2.pro', 'chromeShortcut': '5'}]})
			with self.assertRaisesRegex(ValueError, 'userData'):
				runtime.settings(rt_bad)
		rt_link, _, _, _ = self._write_fixture({'schemaVersion': 1, 'skillsRoot': 'x', 'profiles': [{'id': 'A0', 'userData': 'Antigravity'}]})
		with patch('Df.Harness.Runtime.AddonsProfileAdapter.dfh_is_linked', return_value=True):
			pr.clear_registry_cache()
			with self.assertRaisesRegex(ValueError, 'Linked'):
				runtime.settings(rt_link)
	# @used-by :mod:`unittest`
	def test_projects_addons_profiles_with_overrides_and_env_expansion(self):
		payload = {
			'schemaVersion': 1,
			'skillsRoot': '${ANTIGRAVITY_ADDONS_CODE}',
			'profiles': [
				{'id': 'A0', 'userData': 'Antigravity'},
				{'id': 'A5', 'userData': 'Antigravity-A5', 'email': 'admin5@mage2.pro', 'chromeShortcut': '5'},
				{'id': 'A6', 'userData': 'Antigravity-A6', 'email': 'admin6@mage2.pro', 'chromeShortcut': '6', 'enabled': False, 'label': 'Custom A6'},
			],
		}
		overrides = {'A0': {'label': 'Antigravity A0 (Default)', 'system_paths': {'logs_dir': '${APPDATA}/CustomLogs'}}, 'A5': {'disabled_reason': 'none'}}
		rt_file, _, _, roaming = self._write_fixture(payload, overrides=overrides)
		cfg = runtime.settings(rt_file)
		insts = cfg['platforms']['antigravity']['instances']
		self.assertEqual(['A0', 'A5', 'A6'], list(insts))
		self.assertTrue(insts['A0']['primary'])
		self.assertNotIn('account_email', insts['A0'])
		self.assertNotIn('chrome_shortcut', insts['A0'])
		self.assertEqual('Antigravity A0 (Default)', insts['A0']['label'])
		self.assertEqual((self.root / 'Users/alice').resolve().as_posix(), insts['A0']['home'])
		self.assertEqual((roaming / 'CustomLogs').as_posix(), insts['A0']['system_paths']['logs_dir'])
		self.assertFalse(insts['A5']['primary'])
		self.assertEqual('Antigravity A5', insts['A5']['label'])
		self.assertEqual('admin5@mage2.pro', insts['A5']['account_email'])
		self.assertEqual('5', insts['A5']['chrome_shortcut'])
		self.assertEqual((roaming / 'Antigravity-A5/home').as_posix(), insts['A5']['home'])
		self.assertEqual((roaming / 'Antigravity-A5').as_posix(), insts['A5']['user_data_dir'])
		self.assertFalse(insts['A6']['enabled'])
		self.assertEqual('Custom A6', insts['A6']['label'])
		with patch.dict(os.environ, {'APPDATA': (self.root / 'alt_roaming').resolve().as_posix()}, clear=False):
			pr.clear_registry_cache()
			self.assertEqual((self.root / 'Users/alice/AppData/Roaming/Antigravity-A5/home').resolve().as_posix(), runtime.settings(rt_file)['platforms']['antigravity']['instances']['A5']['home'])
	# @used-by :mod:`unittest`
	def test_rejects_conflicts_malformed_schema_and_unknown_overrides(self):
		valid_payload = {'schemaVersion': 1, 'skillsRoot': 'x', 'profiles': [{'id': 'A0', 'userData': 'Antigravity'}, {'id': 'A5', 'userData': 'Antigravity-A5', 'email': 'admin5@mage2.pro', 'chromeShortcut': '5'}]}
		rt_missing, _, _, _ = self._write_fixture(None)
		with self.assertRaisesRegex(ValueError, 'addons_profiles_json'):
			runtime.settings(rt_missing)
		rt_malformed, _, _, _ = self._write_fixture(None, raw_profiles_text='{bad json')
		with self.assertRaisesRegex(ValueError, 'profiles'):
			runtime.settings(rt_malformed)
		rt_dual, _, _, _ = self._write_fixture(valid_payload, extra_platform={'instances': {'A0': {'home': self.root.as_posix()}}})
		with self.assertRaisesRegex(ValueError, 'both'):
			runtime.settings(rt_dual)
		rt_src, _, _, _ = self._write_fixture(valid_payload, extra_platform={'instances_source': 'unknown_source'})
		with self.assertRaisesRegex(ValueError, 'instances_source'):
			runtime.settings(rt_src)
		rt_unknown_ov, _, _, _ = self._write_fixture(valid_payload, overrides={'A99': {'enabled': False}})
		with self.assertRaisesRegex(ValueError, 'A99'):
			runtime.settings(rt_unknown_ov)
		for bad_payload in (
			{'schemaVersion': 99, 'profiles': []},
			{'schemaVersion': 1, 'profiles': [{'id': 'A5', 'userData': 'Antigravity-A5', 'email': 'a5@mage2.pro', 'chromeShortcut': '5'}]},
			{'schemaVersion': 1, 'profiles': [{'id': 'A0', 'userData': 'Antigravity', 'enabled': False}]},
			{'schemaVersion': 1, 'profiles': [{'id': 'A0', 'userData': 'Antigravity'}, {'id': 'A5', 'userData': 'Antigravity-A5', 'email': 'a@m.pro', 'chromeShortcut': '5'}, {'id': 'A6', 'userData': 'Antigravity-A6', 'email': 'A@M.PRO', 'chromeShortcut': '6'}]},
			{'schemaVersion': 1, 'profiles': [{'id': 'A0', 'userData': 'Antigravity'}, {'id': 'A5', 'userData': 'Antigravity-A5', 'email': 'a5@m.pro', 'chromeShortcut': '5'}, {'id': 'A6', 'userData': 'Antigravity-A6', 'email': 'a6@m.pro', 'chromeShortcut': '5'}]},
		):
			rt_bad, _, _, _ = self._write_fixture(bad_payload)
			with self.assertRaises(ValueError):
				runtime.settings(rt_bad)
if '__main__' == __name__:
	unittest.main()