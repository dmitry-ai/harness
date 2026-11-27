# 2026-11-27 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from copy import deepcopy
from pathlib import Path
from unittest.mock import patch
import io
import json
import os
import sys
import tempfile
import unittest
WT_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = WT_ROOT / 'scripts'
if str(SCRIPTS) not in sys.path:
	sys.path.insert(0, str(SCRIPTS))
# 2026-11-27 "Move turn lifecycle subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/383
# @used-by :mod:`unittest`
class DfHarnessS11Wave2dConfigCovTests(unittest.TestCase):
	# @used-by :meth:`DfHarnessS11Wave2dConfigCovTests.test_native_builder_and_projection_publisher()`
	# @used-by :meth:`DfHarnessS11Wave2dConfigCovTests.test_native_profiles_install_rename_retire_and_rollback()`
	def _build_fixture(self, root: Path) -> tuple[Path, dict, dict[str, Path], dict[str, Path]]:
		from agent_tools import runtime
		primary = root / 'harness/code'
		(root / 'harness/_').mkdir(parents=True, exist_ok=True)
		cfg = deepcopy(runtime.settings())
		cfg['workspace_root'] = str(root / 'workspace')
		grav = {n: root / f'profiles/{n}/.gemini/config' for n in ('A0', 'A6')}
		homes = {n: root / f'profiles/{n}' for n in ('C1', 'C2')}
		cfg['platforms']['antigravity']['instances'] = {n: {'enabled': True, 'home': str(p.parent.parent)} for n, p in grav.items()}
		cfg['platforms']['codex']['instances'] = {n: {'enabled': True, 'home': str(p)} for n, p in homes.items()}
		self._write(primary / 'runtime.json', json.dumps(cfg))
		self._write(primary / 'rules/00-scope.md', '---\ntrigger: always_on\n---\n# Scope\nUse canonical sources.  \n')
		self._write(primary / 'platforms/codex.md', '# Codex\nPreserve profile settings.  \n')
		self._write(primary / 'agents/worker.md', '# Worker\nRead current evidence.  \n')
		for name in ('upwork-init', 'df-article'):
			self._write(primary / f'skills/{name}/SKILL.md', f'---\nname: {name}\ndescription: {name} docs.\n---\nBody {name}.\n')
		return (primary, cfg, grav, homes)
	# @used-by :meth:`DfHarnessS11Wave2dConfigCovTests.test_native_profiles_install_rename_retire_and_rollback()`
	def _seed_legacy_profiles(self, primary: Path, grav: dict[str, Path], homes: dict[str, Path]) -> None:
		from Df.Harness.lib.config_codex import dfh_loader
		from Df.Harness.lib.native_ag_plan import dfh_role_values
		from Df.Harness.lib.native_codex_roles import dfh_legacy_role, dfh_legacy_role_config, dfh_legacy_skill
		home = homes['C2']
		old = f'# Codex: Upwork\n\n<!-- Generated from {primary.as_posix()}; run upwork_project.py build-native to update. -->\n\n' + dfh_loader(primary) + '\n'
		self._write(home / 'AGENTS.md', '# Personal\n\n' + old)
		defs = {ag: {'config_file': (primary / f'platforms/codex/agents/{ag}.toml').as_posix(), 'description': purp} for _, ag, purp, _ in dfh_role_values(primary)}
		toml_base = '# Keep comment\nmodel = "mine"\n[plugins."chrome-devtools@openai-bundled"]\nenabled = true\n'
		dfh_legacy_role_config(toml_base, defs)
		self._write(home / 'config.toml', toml_base)
		for skill in ('upwork-init', 'df-article'):
			self._write(home / f'skills/{skill}/SKILL.md', dfh_legacy_skill(skill, primary))
		for role, ag, purp, _ in dfh_role_values(primary):
			self._write(home / f'agents/{ag}.toml', dfh_legacy_role(primary, role, ag, purp))
		ag_cfg = grav['A6']
		self._write(ag_cfg / 'config.json', json.dumps({'cdp_grant': True, 'custom': 1}))
		self._write(ag_cfg / 'mcp_config.json', json.dumps({'mcpServers': {'chrome-devtools': {'command': 'npx', 'args': ['chrome-devtools-mcp@latest']}}}))
		self._write(ag_cfg / 'hooks.json', json.dumps({'hooks': {'Stop': [{'hooks': [{'type': 'command', 'command': 'echo keep'}]}]}}))
		self._write(ag_cfg / 'rules/manifest.json', json.dumps({'inherits': [], 'entries': [{'path': str(primary / 'rules/00-scope.md')}]}))
	# @used-by :meth:`DfHarnessS11Wave2dConfigCovTests._build_fixture()`
	# @used-by :meth:`DfHarnessS11Wave2dConfigCovTests._seed_legacy_profiles()`
	# @used-by :meth:`DfHarnessS11Wave2dConfigCovTests.test_native_builder_and_projection_publisher()`
	# @used-by :meth:`DfHarnessS11Wave2dConfigCovTests.test_native_profiles_install_rename_retire_and_rollback()`
	# @used-by :meth:`DfHarnessS11Wave2dConfigCovTests.test_rule_splitter_and_config_blocks_helpers()`
	def _write(self, path: Path, text: str) -> Path:
		path.parent.mkdir(parents=True, exist_ok=True)
		path.write_bytes(text.encode('utf-8'))
		return path
	# @used-by :mod:`unittest`
	def test_managed_link_and_native_links_edge_helpers(self) -> None:
		from Df.Harness.Config.NativeProfile.ManagedLink import ManagedLink
		from Df.Harness.lib import native_links as nl
		with tempfile.TemporaryDirectory() as td:
			root = Path(td).resolve()
			primary = root / 'harness/code'
			(root / 'harness/_').mkdir(parents=True)
			target = root / 'target_dir'
			target.mkdir()
			(target / 'SKILL.md').write_text('x', encoding='utf-8')
			link_p = root / 'profile/skills/demo'
			ml = ManagedLink(link_p, target, 'directory-junction', label='skill')
			self.assertIsNone(ml.verify_before_create({}))
			self.assertTrue(ml.readonly_issue()['message'])
			ml.create(primary)
			self.assertIsNone(ml.verify_created())
			self.assertTrue(nl.dfh_link_matches_target(link_p, target))
			self.assertEqual(nl.dfh_link_target_path(link_p).resolve(), target.resolve())
			self.assertTrue(nl.dfh_is_relocated_owned_link(link_p, str(target), root / 'other', {nl.dfh_absolute(target)}))
			self.assertIsInstance(ml.identity_dict(), dict)
			self.assertIsInstance(ml.backup_payload(), bytes)
			ml_r = ManagedLink(link_p, Path(os.readlink(link_p)), nl.dfh_directory_link_identity(link_p)['kind'], label='skill')
			self.assertIsNone(ml_r.verify_retired())
			ml_r.retire()
			self.assertIn('retirement', ml.readonly_issue(retired=True)['message'])
			ml_r.restore_retired(primary)
			self.assertIsNone(ml.verify_created())
			ml.remove_created()
			self.assertFalse(nl.dfh_exists(link_p))
			self.assertIsInstance(nl.dfh_relocated_primaries(primary), tuple)
			self.assertEqual(nl.dfh_hash(b'abc'), nl.dfh_hash(b'abc'))
	# @used-by :mod:`unittest`
	def test_native_builder_and_projection_publisher(self) -> None:
		from Df.Harness.Config.NativeBuilder import NativeBuilder
		from Df.Harness.Config.ProjectionPublisher import ProjectionPublisher
		from Df.Harness.lib.config_codex import dfh_global_codex_instructions
		from Df.Harness.lib.native_codex_plan import dfh_retire_owned_project_projections
		with tempfile.TemporaryDirectory() as td:
			root = Path(td).resolve()
			primary, cfg, _, homes = self._build_fixture(root)
			ws = root / 'workspace'
			(ws / '\ua616/data').mkdir(parents=True)
			self._write(ws / '.agents/rules/90-project.md', '---\ntrigger: always_on\n---\n# Project\nLocal rule.  \n')
			self._write(homes['C1'] / 'config.toml', 'developer_instructions = "Global C1 rules"\n')
			built = NativeBuilder(ws, primary).run()
			self.assertTrue(built['valid'], built)
			checked = NativeBuilder(ws, primary, check=True).run()
			self.assertTrue(checked['valid'], checked)
			ret_res = dfh_retire_owned_project_projections(ws, primary=primary)
			self.assertTrue(ret_res['valid'], ret_res)
			leg = ws / 'legacy_proj.md'
			pub1 = ProjectionPublisher(ws, {leg: 'hello\n'}).run()
			self.assertTrue(pub1['valid'])
			pub2 = ProjectionPublisher(ws, {}, retire=[leg]).run()
			self.assertTrue(pub2['valid'])
			self.assertFalse(leg.exists())
			pub_empty = ProjectionPublisher(ws, {ws / '.codex/config.toml': ''}).run()
			self.assertTrue(pub_empty['valid'])
			cfg2 = deepcopy(cfg)
			cfg2['platforms'].pop('codex', None)
			self._write(primary / 'runtime.json', json.dumps(cfg2))
			disabled = NativeBuilder(ws, primary).run()
			self.assertTrue(disabled['valid'], disabled)
			inst = dfh_global_codex_instructions(settings_fn=lambda: cfg, profile_name_fn=lambda: 'C1')
			self.assertEqual(inst['developer_instructions'], 'Global C1 rules')
	# @used-by :mod:`unittest`
	def test_native_profiles_install_rename_retire_and_rollback(self) -> None:
		from Df.Harness.Config.NativeProfile.Applier import Applier
		from Df.Harness.Config.NativeProfile.ManagedLink import ManagedLink
		from Df.Harness.Config.NativeProfile.Plan import Plan
		from Df.Harness.lib.native_links import dfh_load_state
		from agent_tools import native_profiles as native
		with tempfile.TemporaryDirectory() as td:
			root = Path(td).resolve()
			primary, cfg, grav, homes = self._build_fixture(root)
			self._seed_legacy_profiles(primary, grav, homes)
			chk = native.install_native_profiles(('A6', 'C2'), check=True, primary=primary)
			self.assertFalse(chk['valid'])
			res = native.install_native_profiles(('A6', 'C2'), primary=primary)
			self.assertTrue(res['valid'], res)
			self.assertTrue(native.install_native_profiles(('A6', 'C2'), check=True, primary=primary)['valid'])
			self.assertTrue(native.build_shared_native(primary, check=True)['valid'])
			first_role = next(iter(cfg['platforms']['codex']['roles']))
			cfg['platforms']['codex']['roles'][first_role]['agent'] = 'af_renamed'
			self._write(primary / 'runtime.json', json.dumps(cfg))
			(primary / 'skills/df-article/SKILL.md').unlink()
			(primary / 'skills/df-article').rmdir()
			res2 = native.install_native_profiles(('A6', 'C2'), primary=primary)
			self.assertTrue(res2['valid'], res2)
			p_fail = Plan()
			p_fail.file(homes['C2'] / 'rollback_tmp/f.txt', b'temp')
			p_fail.managed_links[homes['C2'] / 'skills/boom'] = ManagedLink(homes['C2'] / 'skills/boom', primary / 'skills/upwork-init', 'directory', ops={'directory_link': lambda *_a, **_k: (_ for _ in ()).throw(OSError('boom'))})
			rb = Applier(p_fail, primary, dfh_load_state(primary)).run()
			self.assertFalse(rb['valid'])
			self.assertFalse((homes['C2'] / 'rollback_tmp/f.txt').exists())
	# @used-by :mod:`unittest`
	def test_rule_splitter_and_config_blocks_helpers(self) -> None:
		from Df.Harness.lib.config_blocks import _advance_quoted, _step_toml_char, dfh_digest, dfh_store_content_backup
		from Df.Harness.lib.rule_splitter import dfh_split_rules, dfh_split_rules_main
		with tempfile.TemporaryDirectory() as td:
			root = Path(td).resolve()
			rules = root / '.agents/rules'
			self._write(rules / '91-existing.md', '# Existing\n')
			big = '---\ntrigger: always_on\n---\n# Project Passport\nKeep me.\n# Deploy Notes\n' + ('Details line.\n' * 80)
			self._write(rules / '90-project.md', big)
			buf = io.StringIO()
			with patch('sys.stdout', buf):
				self.assertTrue(dfh_split_rules(rules, max_bytes=100))
				self.assertFalse(dfh_split_rules(rules, max_bytes=999999, force=False))
				dfh_split_rules_main(['split_project_rules.py', str(root)])
			self.assertTrue((rules / '92-deploy-notes.md').is_file())
			self.assertEqual(_advance_quoted('"a\\"b"', 0, '"'), (1, None))
			st = _step_toml_char('a = [1] # c\n', 4, 0, None, False)
			self.assertEqual(st[0], 5)
			self.assertEqual(len(dfh_digest(b'x')), 64)
			bk, _ = dfh_store_content_backup(root / 'bk', root / 'a.txt', b'payload')
			self.assertTrue(bk.is_file())
if '__main__' == __name__:
	unittest.main()
