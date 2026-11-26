# 2026-11-24 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
HARNESS_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = HARNESS_ROOT / 'scripts'
if str(SCRIPTS) not in sys.path:
	sys.path.insert(0, str(SCRIPTS))
def _run_probe(code: str) -> dict:
	proc = subprocess.run([sys.executable, '-I', '-c', code, str(SCRIPTS.resolve())], stdin=subprocess.DEVNULL, capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=30, check=True)
	return json.loads(proc.stdout)
# 2026-11-24
# "Convert PreToolUse hook entry points to lazy tool-scoped imports":
# https://github.com/dmitry-ai/harness/issues/187
class HookLazyImportsTests(unittest.TestCase):
	def test_cdp_bypass_py_edit_and_read_skip_git_gate_and_still_blocks_loopback(self) -> None:
		code = (
			'import json, sys\n'
			'sys.path.insert(0, sys.argv[1])\n'
			'from agent_tools.gates import cdp_bypass\n'
			'r1 = cdp_bypass.check("read_file", {"Path": "C:/tmp/mod.py"}, {})\n'
			'r2 = cdp_bypass.check("edit_file", {"Path": "C:/tmp/mod.py", "Target": "a", "Replacement": "b = 2"}, {})\n'
			'loaded = [m for m in ("agent_tools.git_gate", "agent_tools.path_registry", "agent_tools.runtime", "agent_tools.shell_audit") if m in sys.modules]\n'
			'print(json.dumps({"r1": r1, "r2": r2, "loaded": loaded}))\n'
		)
		out = _run_probe(code)
		self.assertIsNone(out['r1'])
		self.assertIsNone(out['r2'])
		self.assertEqual([], out['loaded'], f'Unexpected eager imports in cdp_bypass: {out["loaded"]}')
		from agent_tools.gates.cdp_bypass import check
		with tempfile.TemporaryDirectory() as td:
			other = Path(td).resolve() / 'ext.py'
			self.assertIsNotNone(check('read_file', {'Path': str(Path(td).resolve() / 'DevToolsActivePort')}, {}))
			self.assertIsNotNone(check('write_file', {'Path': str(other), 'Content': 'URL = "http://127.0.0.1:9222/devtools/page/1"\n'}, {}))
	def test_check_markdown_slop_non_md_edit_skips_domain_imports(self) -> None:
		code = (
			'import json, sys\n'
			'sys.path.insert(0, sys.argv[1])\n'
			'import check_markdown_slop as cms\n'
			'dec = cms._evaluate_payload({"toolCall": {"name": "edit_file", "args": {"Path": "scripts/demo.py", "Target": "x", "Replacement": "y"}}})\n'
			'loaded = [m for m in ("agent_tools.path_registry", "agent_tools.source_grounding", "agent_tools.git_gate") if m in sys.modules]\n'
			'print(json.dumps({"decision": dec, "loaded": loaded}))\n'
		)
		out = _run_probe(code)
		self.assertEqual('allow', out['decision']['decision'])
		self.assertEqual([], out['loaded'], f'check_markdown_slop eagerly imported: {out["loaded"]}')
	def test_discover_pre_tool_gates_tool_filtering_and_manifest_parity(self) -> None:
		from agent_tools.gates import _BUILTIN_TOOLS_MANIFEST, discover_pre_tool_gates
		read_names = [g['name'] for g in discover_pre_tool_gates(tool_name='read_file')]
		self.assertEqual(['REVIEW-1-BULK-SOURCE-GATE', 'CDP-BYPASS-GATE'], read_names)
		sched_names = [g['name'] for g in discover_pre_tool_gates(tool_name='schedule')]
		self.assertEqual(['EXEC-4-SCHEDULE-GATE'], sched_names)
		all_gates = discover_pre_tool_gates()
		self.assertGreaterEqual(len(all_gates), 14)
		for gate in all_gates:
			stem = gate['module'].rsplit('.', 1)[-1]
			self.assertIn(stem, _BUILTIN_TOOLS_MANIFEST, f'Missing manifest entry for {stem}')
			self.assertEqual(set(_BUILTIN_TOOLS_MANIFEST[stem]), set(gate['tools'] or ()), f'Manifest mismatch for {stem}')
	def test_rules_gate_import_and_read_file_and_schedule_skip_heavy_modules(self) -> None:
		code_imp = (
			'import json, sys\n'
			'sys.path.insert(0, sys.argv[1])\n'
			'import check_rules_and_server_gate as rg\n'
			'loaded = [m for m in ("agent_tools.path_registry", "agent_tools.git_gate", "agent_tools.failfast_gate", "agent_tools.gates") if m in sys.modules]\n'
			'has_lazy = callable(rg.check_rules_budget)\n'
			'print(json.dumps({"loaded": loaded, "has_lazy": has_lazy}))\n'
		)
		out_imp = _run_probe(code_imp)
		self.assertEqual([], out_imp['loaded'], f'check_rules_and_server_gate eagerly imported: {out_imp["loaded"]}')
		self.assertTrue(out_imp['has_lazy'])
		code_read = (
			'import json, sys\n'
			'sys.path.insert(0, sys.argv[1])\n'
			'import check_rules_and_server_gate as rg\n'
			'dec = rg._evaluate_payload({"toolCall": {"name": "read_file", "args": {"Path": "C:/tmp/demo.py"}}})\n'
			'loaded = [m for m in ("agent_tools.git_gate", "agent_tools.path_registry", "agent_tools.runtime", "agent_tools.tdd_gate", "agent_tools.issue_first_gate", "agent_tools.failfast_gate") if m in sys.modules]\n'
			'print(json.dumps({"decision": dec, "loaded": loaded}))\n'
		)
		out_read = _run_probe(code_read)
		self.assertEqual('allow', out_read['decision']['decision'])
		self.assertEqual([], out_read['loaded'], f'read_file loaded heavy modules: {out_read["loaded"]}')
		code_sched = (
			'import json, sys\n'
			'sys.path.insert(0, sys.argv[1])\n'
			'import check_rules_and_server_gate as rg\n'
			'dec = rg._evaluate_payload({"toolCall": {"name": "schedule", "args": {"CronExpression": "*/5 * * * *", "Prompt": "ping"}}})\n'
			'loaded = [m for m in ("agent_tools.git_gate", "agent_tools.path_registry", "agent_tools.gates.cdp_bypass") if m in sys.modules]\n'
			'print(json.dumps({"decision": dec, "loaded": loaded}))\n'
		)
		out_sched = _run_probe(code_sched)
		self.assertEqual('allow', out_sched['decision']['decision'])
		self.assertEqual([], out_sched['loaded'], f'schedule loaded heavy modules: {out_sched["loaded"]}')
if '__main__' == __name__:
	unittest.main()
