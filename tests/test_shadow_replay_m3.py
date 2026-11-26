# 2026-11-25 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from pathlib import Path
import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
WT_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = WT_ROOT / 'scripts'
TESTS = WT_ROOT / 'tests'
for p in (SCRIPTS, TESTS):
	if str(p) not in sys.path:
		sys.path.insert(0, str(p))
HARNESS_PY = SCRIPTS / 'harness.py'
# @used-by :meth:`ShadowReplayM3Tests.test_shadow_replay_cli_executes_downstream_pipeline_and_cleans_scratch()`
# @used-by :meth:`ShadowReplayM3Tests.test_shadow_replay_detects_downstream_failure_and_cleans_scratch()`
def _snapshot_tree(root: Path) -> dict[str, str]:
	return {p.relative_to(root).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(root.rglob('*')) if p.is_file()}
# @used-by :meth:`ShadowReplayM3Tests.test_shadow_replay_cli_executes_downstream_pipeline_and_cleans_scratch()`
# @used-by :meth:`ShadowReplayM3Tests.test_shadow_replay_detects_downstream_failure_and_cleans_scratch()`
def _seed_pre_finalize_project(case: unittest.TestCase, base: Path) -> tuple[dict[str, str], Path, Path, Path, Path, str]:
	from test_upwork_init_e2e import PARENT_CID, _iso_env, _run_cli, _run_turn1_init_and_review
	home = base / 'home'
	backend = home / '.gemini/antigravity'
	launcher = base / 'proposals/init'
	ws = base / 'workspace'
	(launcher / '\ua616/data/turns').mkdir(parents=True)
	(launcher / '\ua66e').mkdir(parents=True)
	(ws / '\ua616/data/scratch').mkdir(parents=True)
	(ws / '\ua616/data/turns').mkdir(parents=True)
	(ws / '\ua616/paths.json').write_text(json.dumps({'version': 1}), encoding='utf-8')
	env = _iso_env(home)
	proj, _tx, cand_md, _ev_bin, _req1, _reply1, _rows = _run_turn1_init_and_review(case, base, launcher, backend, env)
	_run_cli(env, 'answer-prepare', str(proj), '--response-file', str(cand_md), '--conversation', PARENT_CID, '--platform', 'antigravity', '--consume-input', cwd=proj)
	return (env, backend, launcher, proj, ws, PARENT_CID)
# @used-by :meth:`ShadowReplayM3Tests.test_shadow_replay_cli_executes_downstream_pipeline_and_cleans_scratch()`
def _plant_shadowing_and_orphan_states(launcher: Path, proj: Path, cid: str) -> None:
	stale_daily = proj / '\ua616/data/turns/0000000000000000000000000000000000000001.json'
	stale_daily.write_text(json.dumps({'key': '0000000000000000000000000000000000000001', 'conversation_id': cid, 'native_turn_id': f'ag-{cid}-legacy', 'native_start_step': 0, 'status': 'open', 'project_root': str(proj), 'journal': str(proj / '\ua66e'), 'requests': [{'native_step': 0, 'text': 'stale'}, {'native_step': 2, 'text': 'stale2'}]}), encoding='utf-8')
	orphan_launcher = launcher / '\ua616/data/turns/ffffffffffffffffffffffffffffffffffffffff.json'
	orphan_launcher.write_text(json.dumps({'key': 'ffffffffffffffffffffffffffffffffffffffff', 'conversation_id': cid, 'native_turn_id': f'ag-{cid}-0', 'native_start_step': 0, 'status': 'open', 'project_root': str(launcher), 'journal': str(launcher / '\ua66e'), 'requests': [{'native_step': 0, 'text': 'orphan'}]}), encoding='utf-8')
# 2026-11-25
# "Add workspace-local shadow-replay CLI command and EXEC-2 acceptance gate":
# https://github.com/dmitry-ai/harness/issues/237
class ShadowReplayM3Tests(unittest.TestCase):
	# @used-by :mod:`unittest`
	def test_exec2_rules_and_readme_document_shadow_replay_gate(self) -> None:
		from agent_tools import links
		from agent_tools.cli_registry import registered_commands
		import check_markdown_slop
		self.assertIn('shadow-replay', registered_commands())
		# 2026-11-25
		# "Refactor shared rules into compact three-layer M-2 architecture":
		# https://github.com/dmitry-ai/harness/issues/242
		skill_doc = WT_ROOT / 'skills/upwork-init/SKILL.md'
		readme_doc = WT_ROOT / 'scripts/README-agent-tools.md'
		for doc in (skill_doc, readme_doc):
			self.assertEqual(links.validate_file(doc, local_anchors=True, readable_links=True), [])
			self.assertEqual(check_markdown_slop.markdown_slop_issues(doc.read_text(encoding='utf-8')), [])
		skill_text = skill_doc.read_text(encoding='utf-8')
		for tok in ('shadow-replay', '\ua616/data/scratch/shadow-replay', 'FILE-6', 'stages_verified'):
			self.assertIn(tok, skill_text)
		self.assertIn('shadow-replay', readme_doc.read_text(encoding='utf-8'))
	# @used-by :mod:`unittest`
	def test_shadow_replay_cli_executes_downstream_pipeline_and_cleans_scratch(self) -> None:
		with tempfile.TemporaryDirectory() as tmp:
			base = Path(tmp)
			env, backend, launcher, proj, ws, cid = _seed_pre_finalize_project(self, base)
			_plant_shadowing_and_orphan_states(launcher, proj, cid)
			proj_before = _snapshot_tree(proj)
			launcher_before = _snapshot_tree(launcher)
			proc = subprocess.run([sys.executable, str(HARNESS_PY), 'shadow-replay', str(proj), '--launcher', str(launcher), '--conversation', cid, '--workspace', str(ws), '--backend', str(backend), '--platform', 'antigravity'], cwd=str(ws), env=env, stdin=subprocess.DEVNULL, capture_output=True, text=True, encoding='utf-8', timeout=90, check=False)
			self.assertEqual(proc.returncode, 0, f'STDOUT:\n{proc.stdout}\nSTDERR:\n{proc.stderr}')
			res = json.loads(proc.stdout)
			self.assertTrue(res['valid'], res)
			self.assertTrue(res['cleaned_up'])
			shadow_dir = Path(res['shadow_dir'])
			self.assertTrue(shadow_dir.resolve().is_relative_to((ws / '\ua616/data/scratch/shadow-replay').resolve()))
			self.assertFalse(shadow_dir.exists())
			for stage in ('pre_invocation', 'turn_begin', 'review_authorization', 'answer_check', 'answer_prepare', 'stage_finalize', 'stop_gate_project', 'stop_gate_launcher'):
				self.assertIn(stage, res['stages_verified'])
			self.assertIn('live_llm_generation', res['stages_not_run'])
			self.assertEqual(res['checks']['stage_finalize']['status'], 'complete')
			self.assertEqual(res['checks']['stop_gate_project']['decision'], 'allow')
			self.assertEqual(res['checks']['stop_gate_launcher']['decision'], 'allow')
			self.assertEqual(res['checks']['pre_invocation']['launcher_orphans_created'], 0)
			self.assertEqual(list((ws / '\ua616/data/turns').glob('*')), [])
			self.assertEqual(_snapshot_tree(proj), proj_before)
			self.assertEqual(_snapshot_tree(launcher), launcher_before)
	# @used-by :mod:`unittest`
	def test_shadow_replay_detects_downstream_failure_and_cleans_scratch(self) -> None:
		with tempfile.TemporaryDirectory() as tmp:
			base = Path(tmp)
			env, backend, launcher, proj, ws, cid = _seed_pre_finalize_project(self, base)
			bad_cand = base / 'bad-reply.md'
			bad_cand.write_text('Плохая ссылка [документ](<file:///C:/dir%20with%20space/doc.md>).  \n', encoding='utf-8')
			proj_before = _snapshot_tree(proj)
			proc = subprocess.run([sys.executable, str(HARNESS_PY), 'shadow-replay', str(proj), '--launcher', str(launcher), '--conversation', cid, '--workspace', str(ws), '--backend', str(backend), '--platform', 'antigravity', '--response-file', str(bad_cand)], cwd=str(ws), env=env, stdin=subprocess.DEVNULL, capture_output=True, text=True, encoding='utf-8', timeout=90, check=False)
			self.assertEqual(proc.returncode, 2, f'STDOUT:\n{proc.stdout}\nSTDERR:\n{proc.stderr}')
			res = json.loads(proc.stdout)
			self.assertFalse(res['valid'])
			self.assertTrue(res['cleaned_up'])
			self.assertFalse(Path(res['shadow_dir']).exists())
			self.assertTrue(res['errors'])
			self.assertEqual(_snapshot_tree(proj), proj_before)
if '__main__' == __name__:
	unittest.main()