# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from datetime import datetime, timedelta, timezone
from pathlib import Path
import json
import subprocess
import sys
import tempfile
import unittest
WT_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = WT_ROOT / 'scripts'
if str(SCRIPTS) not in sys.path:
	sys.path.insert(0, str(SCRIPTS))
# @used-by :meth:`SnapshotLatencyAndDelegationPolicyTests.test_fallback_spike_blocks_promotion_only_when_strict_and_ignores_historical_lines()`
# @used-by :meth:`SnapshotLatencyAndDelegationPolicyTests.test_promote_rejects_large_transcript_slow_snapshot_and_accepts_fast_snapshot()`
def _commit_rg(repo: Path, source: str, message: str) -> None:
	(repo / 'scripts/check_rules_and_server_gate.py').write_text(source, encoding='utf-8')
	_git(repo, 'add', 'scripts/check_rules_and_server_gate.py')
	_git(repo, 'commit', '--no-verify', '-m', message)
# @used-by :func:`_commit_rg()`
# @used-by :func:`_seed_canary_repo()`
def _git(repo: Path, *args: str) -> str:
	proc = subprocess.run(['git', '--no-optional-locks', '-C', str(repo), *args], stdin=subprocess.DEVNULL, capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=30, check=True)
	return (proc.stdout or '').strip()
# @used-by :meth:`SnapshotLatencyAndDelegationPolicyTests.test_fallback_spike_blocks_promotion_only_when_strict_and_ignores_historical_lines()`
# @used-by :meth:`SnapshotLatencyAndDelegationPolicyTests.test_promote_rejects_large_transcript_slow_snapshot_and_accepts_fast_snapshot()`
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
	for rel in ('scripts/Df/__init__.py', 'scripts/Df/Core/lib/fs/.py', 'scripts/Df/Core/lib/git.py', 'scripts/agent_tools/path_cache.py', 'scripts/agent_tools/path_registry.py', 'scripts/agent_tools/runtime_snapshot.py'):
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
# @used-by :meth:`SnapshotLatencyAndDelegationPolicyTests.test_fallback_spike_blocks_promotion_only_when_strict_and_ignores_historical_lines()`
# @used-by :meth:`SnapshotLatencyAndDelegationPolicyTests.test_inspect_fallback_timeout_spike_filters_timestamps_and_check_before_promote()`
def _write_fallback_lines(store: Path, entries: list[tuple[datetime, str]]) -> None:
	store.mkdir(parents=True, exist_ok=True)
	lines = [f'{ts.isoformat()} fallback script=check_rules_and_server_gate.py current=aaa previous=bbb error={err}\n' for ts, err in entries]
	(store / 'fallback.log').write_text(''.join(lines), encoding='utf-8')
# 2026-11-26 "Add multi-MB hook latency canary and codify multi-track delegation policy": https://github.com/dmitry-ai/harness/issues/357
class SnapshotLatencyAndDelegationPolicyTests(unittest.TestCase):
	# @used-by :mod:`unittest`
	def test_delegation_rule_and_worktree_doc_codify_multi_track_policy_and_pass_audits(self) -> None:
		from agent_tools import links, rules_audit
		import check_markdown_slop
		rule_path = WT_ROOT / 'rules/07-review-and-delegation.md'
		doc_path = WT_ROOT / 'scripts/docs/worktrees-and-testing.md'
		rule_bytes = rule_path.read_bytes()
		rule_text = rule_bytes.decode('utf-8')
		doc_text = doc_path.read_text(encoding='utf-8')
		self.assertLessEqual(len(rule_bytes), 6000)
		for token in ('>= 3', 'self', 'worktree', 'main'):
			self.assertIn(token, rule_text)
		for token in ('worktree', 'parallel', 'fallback.log', 'TimeoutError', '1.5s'):
			self.assertIn(token, doc_text)
		audit = rules_audit.audit_rules(WT_ROOT)
		self.assertTrue(audit['valid'], audit)
		self.assertEqual([], audit['issues'])
		self.assertLessEqual(audit['total_always_on_bytes'], 24000)
		self.assertEqual([], links.validate_file(rule_path, local_anchors=True, readable_links=True))
		self.assertEqual([], links.validate_file(doc_path, local_anchors=True, readable_links=True))
		self.assertEqual([], check_markdown_slop.markdown_slop_issues(rule_text))
		self.assertEqual([], check_markdown_slop.markdown_slop_issues(doc_text))
	# @used-by :mod:`unittest`
	def test_fallback_spike_blocks_promotion_only_when_strict_and_ignores_historical_lines(self) -> None:
		from agent_tools.runtime_snapshot import promote_runtime_snapshot
		with tempfile.TemporaryDirectory() as td:
			root = Path(td).resolve()
			repo = _seed_canary_repo(root)
			store = root / 'store'
			r1 = promote_runtime_snapshot(repo, store_dir=store)
			self.assertTrue(r1['promoted'], r1)
			self.assertEqual(0, r1['fallback_audit']['new_timeout_count'])
			self.assertFalse(r1['fallback_audit']['spike_detected'])
			t_ptr1 = datetime.fromisoformat(json.loads((store / 'current.json').read_text(encoding='utf-8'))['updated_at'])
			old_entries = [(t_ptr1 - timedelta(seconds=20 - i), 'TimeoutError: Hook watchdog timeout after 6s') for i in range(6)]
			old_entries.append((t_ptr1, 'TimeoutError: Hook watchdog timeout after 6s'))
			_write_fallback_lines(store, old_entries)
			_commit_rg(repo, 'import json\nimport sys\ndef _evaluate_payload(payload):\n\treturn {"decision": "allow", "v": 2}\nif "__main__" == __name__:\n\tsys.stdout.write(json.dumps(_evaluate_payload({})))\n', 'v2')
			r2 = promote_runtime_snapshot(repo, store_dir=store, fail_on_fallback_spike=True)
			self.assertTrue(r2['promoted'], r2)
			sha2 = r2['commit_sha']
			t_ptr2 = datetime.fromisoformat(json.loads((store / 'current.json').read_text(encoding='utf-8'))['updated_at'])
			new_entries = old_entries + [(t_ptr2 + timedelta(seconds=1 + i), 'RuntimeError: boom') for i in range(2)] + [(t_ptr2 + timedelta(seconds=10 + i), 'TimeoutError: Hook watchdog timeout after 6s') for i in range(5)]
			_write_fallback_lines(store, new_entries)
			_commit_rg(repo, 'import json\nimport sys\ndef _evaluate_payload(payload):\n\treturn {"decision": "allow", "v": 3}\nif "__main__" == __name__:\n\tsys.stdout.write(json.dumps(_evaluate_payload({})))\n', 'v3')
			blocked = promote_runtime_snapshot(repo, store_dir=store, fail_on_fallback_spike=True)
			self.assertFalse(blocked['valid'], blocked)
			self.assertFalse(blocked['promoted'], blocked)
			self.assertEqual(5, blocked['fallback_audit']['new_timeout_count'])
			self.assertEqual(sha2, json.loads((store / 'current.json').read_text(encoding='utf-8'))['current'])
			hotfix = promote_runtime_snapshot(repo, store_dir=store, fail_on_fallback_spike=False)
			self.assertTrue(hotfix['promoted'], hotfix)
			self.assertTrue(hotfix['fallback_audit']['spike_detected'])
			self.assertEqual(5, hotfix['fallback_audit']['new_timeout_count'])
	# @used-by :mod:`unittest`
	def test_inspect_fallback_timeout_spike_filters_timestamps_and_check_before_promote(self) -> None:
		from agent_tools.snapshot_latency_canary import check_fallback_before_promote, inspect_fallback_timeout_spike
		with tempfile.TemporaryDirectory() as td:
			store = Path(td).resolve() / 'store'
			empty = inspect_fallback_timeout_spike(store)
			self.assertEqual(0, empty['new_timeout_count'])
			self.assertFalse(empty['spike_detected'])
			self.assertIsNone(empty['since'])
			base = datetime(2026, 11, 26, 10, 0, 0, tzinfo=timezone.utc)
			entries = [(base - timedelta(seconds=10 - i), 'TimeoutError: old timeout') for i in range(6)]
			entries.append((base, 'TimeoutError: exact boundary timeout'))
			entries.append((base + timedelta(seconds=2), 'RuntimeError: unrelated'))
			entries.extend([(base + timedelta(seconds=5 + i), 'TimeoutError: fresh timeout') for i in range(5)])
			_write_fallback_lines(store, entries)
			all_cnt = inspect_fallback_timeout_spike(store, since_iso=None, threshold=5)
			self.assertEqual(12, all_cnt['new_timeout_count'])
			self.assertTrue(all_cnt['spike_detected'])
			since_res = inspect_fallback_timeout_spike(store, since_iso=base.isoformat(), threshold=5)
			self.assertEqual(5, since_res['new_timeout_count'])
			self.assertTrue(since_res['spike_detected'])
			self.assertEqual(base.isoformat(), since_res['since'])
			self.assertFalse(inspect_fallback_timeout_spike(store, since_iso=base.isoformat(), threshold=6)['spike_detected'])
			audit_ok, err_ok = check_fallback_before_promote(store, {'updated_at': base.isoformat()}, fail_on_fallback_spike=False)
			self.assertTrue(audit_ok['spike_detected'])
			self.assertIsNone(err_ok)
			audit_fail, err_fail = check_fallback_before_promote(store, {'updated_at': base.isoformat()}, fail_on_fallback_spike=True)
			self.assertEqual(5, audit_fail['new_timeout_count'])
			self.assertIsNotNone(err_fail)
	# @used-by :mod:`unittest`
	def test_live_worktree_passes_large_transcript_latency_canary(self) -> None:
		from agent_tools.snapshot_latency_canary import LARGE_CANARY_MAX_MEDIAN_SECONDS, LARGE_CANARY_RUNS, LARGE_TRANSCRIPT_BYTES, run_large_transcript_latency_canary
		ok, detail = run_large_transcript_latency_canary(WT_ROOT)
		self.assertTrue(ok, detail)
		meta = json.loads(detail)
		self.assertGreaterEqual(meta['transcript_bytes'], LARGE_TRANSCRIPT_BYTES)
		self.assertEqual(LARGE_CANARY_RUNS, meta['runs'])
		self.assertLessEqual(meta['median_seconds'], LARGE_CANARY_MAX_MEDIAN_SECONDS)
	# @used-by :mod:`unittest`
	def test_promote_rejects_large_transcript_slow_snapshot_and_accepts_fast_snapshot(self) -> None:
		from agent_tools.runtime_snapshot import promote_runtime_snapshot
		with tempfile.TemporaryDirectory() as td:
			root = Path(td).resolve()
			repo = _seed_canary_repo(root)
			store = root / 'store'
			fast1 = promote_runtime_snapshot(repo, store_dir=store)
			self.assertTrue(fast1['promoted'], fast1)
			sha1 = fast1['commit_sha']
			slow_large_rg = (
				'import json\nimport pathlib\nimport sys\nimport time\n'
				'def _evaluate_payload(payload):\n'
				'\ttp = payload.get("transcriptPath", "")\n'
				'\tif tp and pathlib.Path(tp).is_file() and 1_000_000 <= pathlib.Path(tp).stat().st_size:\n'
				'\t\targs = (payload.get("toolCall") or {}).get("args") or {}\n'
				'\t\tif str(args.get("Path", "")).endswith(".py"):\n'
				'\t\t\ttime.sleep(1.6)\n'
				'\treturn {"decision": "allow"}\n'
				'if "__main__" == __name__:\n\tsys.stdout.write(json.dumps(_evaluate_payload({})))\n'
			)
			_commit_rg(repo, slow_large_rg, 'large transcript latency regression')
			bad = promote_runtime_snapshot(repo, store_dir=store)
			self.assertFalse(bad['valid'], bad)
			self.assertFalse(bad['promoted'], bad)
			self.assertIn('latency', bad.get('error', '').lower())
			self.assertEqual(sha1, json.loads((store / 'current.json').read_text(encoding='utf-8'))['current'])
			fast_rg = 'import json\nimport sys\ndef _evaluate_payload(payload):\n\treturn {"decision": "allow", "fast": True}\nif "__main__" == __name__:\n\tsys.stdout.write(json.dumps(_evaluate_payload({})))\n'
			_commit_rg(repo, fast_rg, 'fast fix')
			good = promote_runtime_snapshot(repo, store_dir=store)
			self.assertTrue(good['valid'], good)
			self.assertTrue(good['promoted'], good)
			self.assertEqual(good['commit_sha'], json.loads((store / 'current.json').read_text(encoding='utf-8'))['current'])
if '__main__' == __name__:
	unittest.main()
