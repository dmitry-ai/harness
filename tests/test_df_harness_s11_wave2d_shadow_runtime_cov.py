# 2026-11-27 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from argparse import Namespace
from pathlib import Path
from unittest.mock import patch
import json
import sys
import tempfile
import unittest
WT_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = WT_ROOT / 'scripts'
if str(SCRIPTS) not in sys.path:
	sys.path.insert(0, str(SCRIPTS))
_CID = '33333333-4444-5555-6666-777777777777'
# 2026-11-27 "Move turn lifecycle subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/383
# @used-by :mod:`unittest`
class DfHarnessS11Wave2dShadowRuntimeCovTests(unittest.TestCase):
	# @used-by :mod:`unittest`
	def test_runtime_cache_context_and_resolve(self) -> None:
		from Df.Harness.lib import runtime_cache as rc, runtime_context as rctx, runtime_conversations as rconv, runtime_instances as ri, runtime_resolve as rres, runtime_snapshot_ops as rso, runtime_validate as rv
		from agent_tools import runtime as rt_mod
		with tempfile.TemporaryDirectory() as td:
			root = Path(td).resolve()
			cfg = {'platforms': {'antigravity': {'adapter': 'antigravity', 'enabled': True, 'addons': {'code_dir': str(root / 'addon')}, 'browser': {'cdp_port': 9222}, 'instances': {'A0': {'enabled': True, 'home': str(root / 'ag0')}}}, 'codex': {'adapter': 'codex', 'enabled': True, 'roles': {'A.A': {'model': 'm', 'effort': 'high'}}, 'instances': {'C1': {'enabled': True, 'home': str(root / 'cx1')}}}}, 'text': {'browser': {'sessions': {'s1': {'endpoint': 'http://127.0.0.1:9333', 'devtools_active_port': str(root / 'p'), 'profile': {'path': str(root / 'prof')}}}}}}
			self.assertIn(9222, rc.dfh_cached_browser_perimeter(cfg, rt_mod)['ports'])
			self.assertTrue(rc.dfh_cached_addon_roots(cfg, rt_mod, lambda s: s))
			self.assertIsInstance(rc.dfh_cached_browser_perimeter(None, rt_mod), dict)
			self.assertIsInstance(rc.dfh_cached_addon_roots(None, rt_mod, lambda s: s), list)
			called: list[int] = []
			rc.dfh_run_shell_violation_scan(lambda x: called.append(x), 1)
			with rc.dfh_skip_shell_violations():
				rc.dfh_run_shell_violation_scan(lambda x: called.append(x), 2)
			self.assertEqual(called, [1])
			self.assertIn('C1', rctx.dfh_profile_name('C1', config=cfg))
			self.assertEqual(rctx.dfh_registration_profile_name('C1', config=cfg), 'C1')
			self.assertIn('model', rctx.dfh_role_settings('codex', 'A.A', settings_fn=lambda: cfg))
			self.assertIsInstance(ri.dfh_all_instances(config=cfg, check_exists=True), dict)
			self.assertTrue(ri.dfh_enabled_platforms(config=cfg))
			self.assertEqual(ri.dfh_instance_entry('C1', platform='codex', config=cfg)['id'], 'C1')
			self.assertIsInstance(ri.dfh_instance_paths('C1', platform='codex', config=cfg), dict)
			self.assertIsInstance(rres.dfh_resolve_antigravity_backend(instance='A0', config=cfg), Path)
			self.assertIsInstance(rres.dfh_resolve_codex_home(instance='C1', config=cfg), Path)
			self.assertIsNone(rconv.dfh_codex_home_conversation_trace(root / 'cx1', _CID))
			self.assertIsInstance(rso.dfh_check_runtime_snapshot(WT_ROOT, store_dir=root / 'store'), dict)
			self.assertIsInstance(rso.dfh_finalize_native_install({'valid': True}, WT_ROOT, check=True), dict)
			self.assertIsInstance(rso.dfh_is_harness_code_repo(WT_ROOT), bool)
			self.assertFalse(rv.dfh_exists_flag(str(root / 'missing')))
			self.assertEqual(rv.dfh_resolve_glob_paths(str(root / '*.missing')), [])
	# @used-by :mod:`unittest`
	def test_shadow_clone_and_command_ops(self) -> None:
		from Df.Harness.Shadow.WorkspaceCloner import WorkspaceCloner
		from Df.Harness.lib import shadow_clone as scl, shadow_command as scmd
		from agent_tools import shadow_replay_clone as src_mod
		with tempfile.TemporaryDirectory() as td:
			root = Path(td).resolve()
			src, dst, launch = (root / 'src', root / 'dst', root / 'launcher')
			for d in (src, launch):
				(d / '\ua616/data/turns').mkdir(parents=True)
				(d / '\ua616/KB/Evidence').mkdir(parents=True)
			(src / '\ua616/project.json').write_text(json.dumps({'job_id': '~1111111111'}), encoding='utf-8')
			(src / '\ua616/KB/Evidence/a.txt').write_text('ev', encoding='utf-8')
			(src / '\ua616/data/rendered.json').write_text(json.dumps({'p': str(src)}), encoding='utf-8')
			WorkspaceCloner(src, dst, hardlink_evidence=True).run()
			self.assertTrue((dst / '\ua616/KB/Evidence/a.txt').is_file())
			scl.dfh_remap_shadow_state(src, dst)
			tx = root / 'tx.jsonl'
			tx.write_text(json.dumps({'step_index': 0, 'type': 'USER_INPUT', 'content': 'hi'}) + '\n', encoding='utf-8')
			stop_tx = scl.dfh_build_stop_transcript(tx, 'answer', root / 'stop_out')
			self.assertTrue(stop_tx.is_file())
			with scl.dfh_shadow_isolation_context({src: dst}, legacy_ctx=src_mod._legacy_shadow_patch_ctx):
				self.assertTrue(dst.is_dir())
			self.assertTrue(scl.dfh_cleanup_shadow_root(root / 'stop_out'))
			scmd.dfh_stage_command_shadow_copies(src, launch, root / 'sh1')
			self.assertIsInstance(scmd._build_command_argv('python harness.py status {project}', dst, launch), list)
			self.assertEqual(scmd._parse_json_stdout('{"ok": true}'), {'ok': True})
			self.assertIn('HOME', scmd._iso_cmd_env(root / 'sh1'))
			self.assertIsNotNone(scmd.dfh_persist_shadow_replay_receipt(root / 'ws', src, {'valid': True, 'stages_verified': [], 'errors': []}, exec_rename_domain=None, command='status'))
	# @used-by :mod:`unittest`
	def test_shadow_pipeline_and_runner(self) -> None:
		from Df.Harness.Shadow.CommandExecutor import CommandExecutor
		from Df.Harness.Shadow.ReplayPipeline import ReplayPipeline
		from Df.Harness.Shadow.ReplayRunner import ReplayRunner
		with tempfile.TemporaryDirectory() as td:
			root = Path(td).resolve()
			src, dst = (root / 'src', root / 'dst')
			for d in (src, dst):
				(d / '\ua616/data/turns').mkdir(parents=True)
			tx = root / 'tx.jsonl'
			tx.write_text(json.dumps({'step_index': 0, 'type': 'USER_INPUT', 'content': 'hi'}) + '\n', encoding='utf-8')
			resp = root / 'cand.md'
			resp.write_text('Hello.\n', encoding='utf-8')
			(root / 'rp').mkdir()
			checks, ver, errs = ({}, [], [])
			with patch('Df.Harness.Shadow.ReplayPipeline.dfh_begin', return_value={'status': 'open', 'turn_key': 'k1', 'reconciled': []}), patch('Df.Harness.Shadow.ReplayPipeline.dfh_check_answer', return_value={'valid': True, 'issues': []}), patch('Df.Harness.Shadow.ReplayPipeline.dfh_prepare', return_value={'ready': True, 'body_sha256': 'x', 'response_file': str(resp)}), patch('Df.Harness.Hook.PreInvocationGate.PreInvocationGate.run', return_value={}), patch('Df.Harness.Hook.StopGate.StopGate.run', return_value={'decision': 'allow'}):
				ReplayPipeline(dst, None, root / 'rp', _CID, 'antigravity', root / 'ag', tx, resp, checks, ver, errs).run()
			self.assertIn('answer_prepare', ver)
			with patch('Df.Harness.lib.shadow_command.subprocess.run', return_value=Namespace(returncode=0, stdout='{"valid": true}', stderr='')), patch('agent_tools.project_rename_verify.capture_pre_rename_snapshot', return_value={}), patch('agent_tools.project_rename_verify.verify_post_rename', return_value={'valid': True, 'errors': []}):
				CommandExecutor(src, dst, None, None, root / 'ce', exec_rename_domain=None, command='status {project}', checks={}, verified=[], errors=[]).run()
			with patch('agent_tools.project_rename.rename_project', return_value={'valid': True, 'renamed': True, 'project_dir': str(dst), 'post_verification': {'valid': True, 'errors': []}}):
				CommandExecutor(src, dst, None, None, root / 'ce2', exec_rename_domain='example.com', command=None, checks={}, verified=[], errors=[]).run()
			with patch.object(ReplayRunner, '_ReplayRunner__run_shadow_mode', lambda *_a: None):
				rep = ReplayRunner(src, _CID, workspace=root / 'ws2', backend=root / 'ag', response_file=resp, keep=False).run()
			self.assertIn('valid', rep)
if '__main__' == __name__:
	unittest.main()
