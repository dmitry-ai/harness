# 2026-11-25 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from pathlib import Path
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
import unittest
WT_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = WT_ROOT / 'scripts'
TESTS_DIR = Path(__file__).resolve().parent
for p in (SCRIPTS, TESTS_DIR):
	if str(p) not in sys.path:
		sys.path.insert(0, str(p))
from agent_tools.runtime_launchers import harness_hook_runner_source
from test_tdd_pre_tool_use_perf import _seed_multicommit_transcript
# @used-by :meth:`HookRunnerE2EBudgetTests.test_cold_start_runner_stays_within_25_percent_of_hooks_json_timeout()`
def _configured_rules_gate_timeout() -> float:
	data = json.loads((WT_ROOT / 'platforms/antigravity/hooks.json').read_text(encoding='utf-8'))
	r: float | None = None
	for group in data.get('rules-and-server-gate', {}).get('PreToolUse') or ():
		for hk in group.get('hooks') or ():
			if 'check_rules_and_server_gate.py' in str(hk.get('command') or ''):
				r = float(hk['timeout'])
				break
	if None is r:
		raise AssertionError('check_rules_and_server_gate.py timeout not found in platforms/antigravity/hooks.json')
	return r
# @used-by :meth:`HookRunnerE2EBudgetTests.test_cold_start_runner_stays_within_25_percent_of_hooks_json_timeout()`
def _stage_snapshot_runner(base: Path) -> tuple[Path, Path]:
	store = base / 'snap_store'
	rel = store / 'releases/e2e_snap'
	shutil.copytree(WT_ROOT / 'scripts', rel / 'scripts', ignore=shutil.ignore_patterns('__pycache__', '*.pyc'))
	for fn in ('paths.json', 'runtime.json'):
		shutil.copy2(WT_ROOT / fn, rel / fn)
	(rel / 'snapshot.json').write_text(json.dumps({'canonical_primary': WT_ROOT.as_posix(), 'commit_sha': 'e2e_snap', 'schema_version': 1}), encoding='utf-8')
	(store / 'current.json').write_text(json.dumps({'canonical_primary': WT_ROOT.as_posix(), 'current': 'e2e_snap', 'previous': None, 'version': 1}), encoding='utf-8')
	runner = base / 'harness_hook_runner.py'
	runner.write_text(harness_hook_runner_source(WT_ROOT, store_dir=store), encoding='utf-8')
	return (runner, store)
# 2026-11-25
# "Add cold-start harness_hook_runner budget test against hooks.json timeout":
# https://github.com/dmitry-ai/harness/issues/254
class HookRunnerE2EBudgetTests(unittest.TestCase):
	# @used-by :mod:`unittest`
	def test_cold_start_runner_stays_within_25_percent_of_hooks_json_timeout(self) -> None:
		timeout_s = _configured_rules_gate_timeout()
		budget_s = 0.25 * timeout_s
		self.assertGreater(timeout_s, 0.0)
		with tempfile.TemporaryDirectory() as td:
			base = Path(td).resolve()
			runner, store = _stage_snapshot_runner(base)
			repo, tx = _seed_multicommit_transcript(base, 25)
			env = {**os.environ, 'HARNESS_RUNTIME_STORE': str(store)}
			env.pop('HARNESS_DEV_LIVE_HOOKS', None)
			cases = (
				('non_code_write', {'cwd': str(repo), 'transcriptPath': str(tx), 'toolCall': {'name': 'write_file', 'args': {'Path': str(repo / '\ua616/data/scratch/answer.md'), 'Content': 'Answer.\n'}}}),
				('non_writing_cmd', {'cwd': str(repo), 'transcriptPath': str(tx), 'toolCall': {'name': 'run_command', 'args': {'CommandLine': 'python scripts/harness.py answer-prepare . --response-file x.md'}}}),
				('prod_write_red', {'cwd': str(repo), 'transcriptPath': str(tx), 'toolCall': {'name': 'write_file', 'args': {'Path': str(repo / 'src/prod_next.py'), 'Content': 'X = 1\n'}}}),
			)
			for label, payload in cases:
				t0 = time.perf_counter()
				proc = subprocess.run([sys.executable, str(runner), 'check_rules_and_server_gate.py'], input=json.dumps(payload, ensure_ascii=False), text=True, encoding='utf-8', capture_output=True, env=env, timeout=timeout_s, check=False)
				elapsed = time.perf_counter() - t0
				self.assertEqual(0, proc.returncode, f'{label}: stderr={proc.stderr}')
				self.assertEqual('allow', json.loads(proc.stdout)['decision'], f'{label}: {proc.stdout}')
				self.assertLessEqual(elapsed, budget_s, f'{label}: cold start {elapsed:.3f}s exceeded 25% budget ({budget_s:.2f}s of {timeout_s:.1f}s)')
if '__main__' == __name__:
	unittest.main()
