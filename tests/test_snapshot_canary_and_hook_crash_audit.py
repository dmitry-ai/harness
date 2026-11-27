# 2026-11-25 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from pathlib import Path
from unittest.mock import patch
import json
import subprocess
import sys
import tempfile
import unittest
WT_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = WT_ROOT / 'scripts'
if str(SCRIPTS) not in sys.path:
	sys.path.insert(0, str(SCRIPTS))
# @used-by :meth:`SnapshotCanaryAndHookCrashAuditTests.test_promote_rejects_chatty_pre_tool_use_snapshot_and_keeps_current()`
# @used-by :meth:`SnapshotCanaryAndHookCrashAuditTests.test_promote_rejects_slow_pre_tool_use_snapshot_and_keeps_current()`
def _commit_rg(repo: Path, source: str, message: str) -> None:
	(repo / 'scripts/check_rules_and_server_gate.py').write_text(source, encoding='utf-8')
	_git(repo, 'add', 'scripts/check_rules_and_server_gate.py')
	_git(repo, 'commit', '--no-verify', '-m', message)
# @used-by :func:`_commit_rg()`
# @used-by :func:`_seed_canary_repo()`
def _git(repo: Path, *args: str) -> str:
	proc = subprocess.run(['git', '--no-optional-locks', '-C', str(repo), *args], stdin=subprocess.DEVNULL, capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=30, check=True)
	return (proc.stdout or '').strip()
# @used-by :meth:`SnapshotCanaryAndHookCrashAuditTests.test_promote_rejects_chatty_pre_tool_use_snapshot_and_keeps_current()`
# @used-by :meth:`SnapshotCanaryAndHookCrashAuditTests.test_promote_rejects_slow_pre_tool_use_snapshot_and_keeps_current()`
def _seed_canary_repo(base: Path) -> Path:
	repo = base / 'proj/\u2c0f/\u227b/\u2655/\u26ef'
	(repo / 'scripts/agent_tools/gates').mkdir(parents=True, exist_ok=True)
	_git(repo, 'init', '-b', 'main')
	_git(repo, 'config', 'user.email', 'test@example.com')
	_git(repo, 'config', 'user.name', 'Test')
	(repo / 'paths.json').write_text((WT_ROOT / 'paths.json').read_text(encoding='utf-8'), encoding='utf-8')
	(repo / 'runtime.json').write_text((WT_ROOT / 'runtime.json').read_text(encoding='utf-8'), encoding='utf-8')
	(repo / 'scripts/agent_tools/__init__.py').write_text('', encoding='utf-8')
	(repo / 'scripts/agent_tools/gates/__init__.py').write_text('def discover_pre_tool_gates():\n\treturn []\n', encoding='utf-8')
	# 2026-11-26 "Extract general duplicated helpers into Df/Core and Df/Qa": https://github.com/dmitry-ai/harness/issues/378
	# 2026-11-26 "Move turn lifecycle subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/383
	for rel in ('scripts/Df/__init__.py', 'scripts/Df/Core/lib/fs/.py', 'scripts/Df/Core/lib/git.py', 'scripts/Df/Harness/Path/CacheStore.py', 'scripts/Df/Harness/Path/PathReporter.py', 'scripts/Df/Harness/Path/ProjectPaths.py', 'scripts/Df/Harness/Path/Registry.py', 'scripts/Df/Harness/Path/SimilarProjectAuditor.py', 'scripts/Df/Harness/Path/SlotResolver.py', 'scripts/Df/Harness/lib/path_discovery.py', 'scripts/Df/Harness/lib/path_resolve.py', 'scripts/Df/Harness/lib/path_schema.py', 'scripts/Df/Harness/lib/path_state.py', 'scripts/Df/Harness/lib/path_template.py', 'scripts/Df/Harness/lib/uri.py', 'scripts/agent_tools/path_cache.py', 'scripts/agent_tools/path_registry.py', 'scripts/agent_tools/runtime_snapshot.py'):
		src = WT_ROOT / rel
		if src.is_file():
			dst = repo / rel
			dst.parent.mkdir(parents=True, exist_ok=True)
			dst.write_text(src.read_text(encoding='utf-8'), encoding='utf-8')
	good_rg = 'import json\nimport sys\ndef _evaluate_payload(payload):\n\treturn {"decision": "allow"}\nif "__main__" == __name__:\n\tsys.stdout.write(json.dumps(_evaluate_payload({})))\n'
	allow_src = 'import json\nimport sys\nif "__main__" == __name__:\n\tsys.stdout.write(json.dumps({"decision": "allow"}))\n'
	shim_src = 'import sys\nif "__main__" == __name__:\n\traise SystemExit(0)\n'
	(repo / 'scripts/check_rules_and_server_gate.py').write_text(good_rg, encoding='utf-8')
	(repo / 'scripts/check_markdown_slop.py').write_text(allow_src, encoding='utf-8')
	(repo / 'scripts/check_pre_invocation.py').write_text(allow_src, encoding='utf-8')
	(repo / 'scripts/check_stop_gate.py').write_text(allow_src, encoding='utf-8')
	(repo / 'scripts/git_shim.py').write_text(shim_src, encoding='utf-8')
	_git(repo, 'add', '.')
	_git(repo, 'commit', '--no-verify', '-m', 'init')
	return repo
# @used-by :meth:`SnapshotCanaryAndHookCrashAuditTests.test_answer_check_enforces_hook_crash_gate()`
# @used-by :meth:`SnapshotCanaryAndHookCrashAuditTests.test_hook_crash_audit_blocks_silent_omission_and_accepts_disclosed_issue_or_recovery()`
def _write_transcript(path: Path, rows: list[dict]) -> Path:
	path.parent.mkdir(parents=True, exist_ok=True)
	path.write_text(''.join((json.dumps(r, ensure_ascii=False) + '\n' for r in rows)), encoding='utf-8')
	return path
# 2026-11-25
# "Add PreToolUse canary probe to runtime snapshot validation and turn hook-crash audit":
# https://github.com/dmitry-ai/harness/issues/251
class SnapshotCanaryAndHookCrashAuditTests(unittest.TestCase):
	# @used-by :mod:`unittest`
	def test_answer_check_enforces_hook_crash_gate(self) -> None:
		from agent_tools import completion
		with tempfile.TemporaryDirectory() as td:
			root = Path(td).resolve() / 'proj'
			(root / '\ua616/data/turns').mkdir(parents=True)
			(root / '\ua66e').mkdir(parents=True)
			tx = _write_transcript(root / 'tx.jsonl', [
				{'step_index': 0, 'type': 'USER_INPUT', 'content': 'Check status'},
				{'step_index': 2, 'type': 'GENERIC', 'status': 'ERROR', 'error': 'JSON hook "jsonhook__rules-and-server-gate_PreToolUse_0_0" failed: command failed: exit status 1, stderr: ', 'content': 'Encountered error in step execution: JSON hook "jsonhook__rules-and-server-gate_PreToolUse_0_0" failed: command failed: exit status 1, stderr: '},
			])
			cid = '11111111-1111-1111-1111-111111111111'
			turn = {'turn_id': f'ag-{cid}-0', 'start_step': 0, 'requests': [{'id': f'{cid}-0', 'text': 'Check status'}], 'owned': True, 'completed': False, 'aborted': False, 'touched_files': [], 'issue_actions': [], 'exec5_violations': [], 'http_fetch_violations': [], 'issue_first_events': [], 'tdd_events': [], 'compaction': {}, 'delegation': {}}
			native = {'platform': 'antigravity', 'conversation_id': cid, 'native_backend': str(root), 'source_file': str(tx), 'primary': True, 'turns': [turn], 'active_turn_id': turn['turn_id']}
			with patch.object(completion, '_native', return_value=native):
				silent = completion.check_answer(root, 'Status is clean.\n', conversation=cid, platform='antigravity')
				self.assertFalse(silent['valid'], silent)
				self.assertFalse(silent['checks']['hook_crash'])
				disclosed = completion.check_answer(root, 'PreToolUse hook rules-and-server-gate failed with exit status 1 on step 2.\n', conversation=cid, platform='antigravity')
				self.assertTrue(disclosed['checks']['hook_crash'], disclosed)
	# @used-by :mod:`unittest`
	def test_hook_crash_audit_blocks_silent_omission_and_accepts_disclosed_issue_or_recovery(self) -> None:
		from agent_tools.hook_crash_audit import detect_hook_crashes, evaluate_hook_crash_check
		with tempfile.TemporaryDirectory() as td:
			root = Path(td).resolve() / 'proj'
			(root / '\ua616/data/turns').mkdir(parents=True)
			(root / '\ua616/KB/Evidence/GitHub/dmitry-ai__harness').mkdir(parents=True)
			tx_clean = _write_transcript(root / 'tx_clean.jsonl', [
				{'step_index': 0, 'type': 'USER_INPUT', 'content': 'Inspect report'},
				{'step_index': 1, 'type': 'GENERIC', 'status': 'DONE', 'content': 'Read quote: JSON hook "jsonhook__rules-and-server-gate_PreToolUse_0_0" failed: exit status 1'},
			])
			native_clean = {'source_file': str(tx_clean)}
			turn_clean = {'start_step': 0, 'requests': [{'id': 'c-0', 'text': 'Inspect report'}], 'issue_actions': []}
			self.assertEqual([], detect_hook_crashes(native_clean, turn_clean))
			self.assertTrue(evaluate_hook_crash_check(root, native_clean, turn_clean, {}, 'Done cleanly.')['verified'])
			tx_err = _write_transcript(root / 'tx_err.jsonl', [
				{'step_index': 0, 'type': 'USER_INPUT', 'content': 'Implement feature'},
				{'step_index': 5, 'type': 'GENERIC', 'status': 'ERROR', 'error': 'JSON hook "jsonhook__rules-and-server-gate_PreToolUse_0_0" failed: command failed: exit status 1, stderr: ', 'content': 'Encountered error in step execution: JSON hook "jsonhook__rules-and-server-gate_PreToolUse_0_0" failed: command failed: exit status 1, stderr: '},
			])
			native_err = {'source_file': str(tx_err)}
			turn_err = {'start_step': 0, 'requests': [{'id': 'c-0', 'text': 'Implement feature'}], 'issue_actions': []}
			self.assertEqual(5, detect_hook_crashes(native_err, turn_err)[0]['step'])
			self.assertFalse(evaluate_hook_crash_check(root, native_err, turn_err, {'key': 'tk1'}, 'Implemented feature cleanly.')['verified'])
			self.assertTrue(evaluate_hook_crash_check(root, native_err, turn_err, {'key': 'tk1'}, 'PreToolUse hook rules-and-server-gate failed with exit status 1 on step 5.')['verified'])
			ev_file = root / '\ua616/KB/Evidence/GitHub/dmitry-ai__harness/issue-245.json'
			ev_file.write_text(json.dumps({'repo': 'dmitry-ai/harness', 'number': 245, 'title': 'PreToolUse JSON hook rules-and-server-gate failed on timeout', 'body': 'JSON hook failure details', 'state': 'open'}), encoding='utf-8')
			self.assertTrue(evaluate_hook_crash_check(root, native_err, {**turn_err, 'issue_actions': [{'repo': 'dmitry-ai/harness', 'number': 245, 'action': 'create', 'url': 'https://github.com/dmitry-ai/harness/issues/245'}]}, {'key': 'tk1'}, 'Completed task.')['verified'])
			(root / '\ua616/data/turns/tk1-violation-recovery.json').write_text(json.dumps({'turn_key': 'tk1', 'covered_hook_crash_steps': [5], 'reason': 'Transient host error investigated'}), encoding='utf-8')
			self.assertTrue(evaluate_hook_crash_check(root, native_err, turn_err, {'key': 'tk1'}, 'Completed task.')['verified'])
	# @used-by :mod:`unittest`
	def test_live_worktree_passes_pre_tool_use_canary(self) -> None:
		from agent_tools.snapshot_canary import run_pre_tool_use_canary
		ok, detail = run_pre_tool_use_canary(WT_ROOT)
		self.assertTrue(ok, detail)
	# @used-by :mod:`unittest`
	def test_promote_rejects_chatty_pre_tool_use_snapshot_and_keeps_current(self) -> None:
		from agent_tools.runtime_snapshot import promote_runtime_snapshot
		with tempfile.TemporaryDirectory() as td:
			root = Path(td).resolve()
			repo = _seed_canary_repo(root)
			store = root / 'store'
			sha1 = promote_runtime_snapshot(repo, store_dir=store)['commit_sha']
			chatty_rg = 'import json\nimport subprocess\nimport sys\ndef _evaluate_payload(payload):\n\tfor _ in range(3):\n\t\tsubprocess.run(["git", "--version"], stdin=subprocess.DEVNULL, capture_output=True, check=False)\n\treturn {"decision": "allow"}\nif "__main__" == __name__:\n\tsys.stdout.write(json.dumps(_evaluate_payload({})))\n'
			_commit_rg(repo, chatty_rg, 'chatty regression')
			bad = promote_runtime_snapshot(repo, store_dir=store)
			self.assertFalse(bad['valid'], bad)
			self.assertFalse(bad['promoted'], bad)
			self.assertIn('subprocess', bad.get('error', '').lower())
			self.assertEqual(sha1, json.loads((store / 'current.json').read_text(encoding='utf-8'))['current'])
	# @used-by :mod:`unittest`
	def test_promote_rejects_slow_pre_tool_use_snapshot_and_keeps_current(self) -> None:
		from agent_tools.runtime_snapshot import promote_runtime_snapshot
		with tempfile.TemporaryDirectory() as td:
			root = Path(td).resolve()
			repo = _seed_canary_repo(root)
			store = root / 'store'
			sha1 = promote_runtime_snapshot(repo, store_dir=store)['commit_sha']
			slow_rg = 'import json\nimport sys\nimport time\ndef _evaluate_payload(payload):\n\ttime.sleep(0.6)\n\treturn {"decision": "allow"}\nif "__main__" == __name__:\n\tsys.stdout.write(json.dumps(_evaluate_payload({})))\n'
			_commit_rg(repo, slow_rg, 'slow regression')
			bad = promote_runtime_snapshot(repo, store_dir=store)
			self.assertFalse(bad['valid'], bad)
			self.assertFalse(bad['promoted'], bad)
			self.assertIn('latency', bad.get('error', '').lower())
			self.assertEqual(sha1, json.loads((store / 'current.json').read_text(encoding='utf-8'))['current'])
if '__main__' == __name__:
	unittest.main()
