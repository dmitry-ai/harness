# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# 2026-11-26 "Codify single-source diff executability contract across Harness gates and runtime snapshot": https://github.com/dmitry-ai/harness/issues/360
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
_APP_PY = '# header\nVAL = 1\n# @used-by unused\ndef run() -> int:\n\treturn 1\n'
_NO_WINDOW = getattr(subprocess, 'CREATE_NO_WINDOW', 0)
_SNAP_PY = '# snap header\nVAL = 1\n'
_TEST_OK_PY = '# test header\nimport unittest\nclass OkT(unittest.TestCase):\n\t# @used-by :mod:`unittest`\n\tdef test_ok(self) -> None:\n\t\tself.assertEqual(1, 1)\n'
# @used-by :meth:`DiffExecutabilityContractTests.test_all_six_gates_delegate_through_diff_executability()`
# @used-by :meth:`DiffExecutabilityContractTests.test_runtime_snapshot_canary_skips_non_executable_and_runs_for_code_or_config()`
# @used-by :meth:`DiffExecutabilityContractTests.test_worktree_land_passes_prev_head_base_ref_and_skips_canary_for_non_exec()`
def _commit_file(repo: Path, rel: str, text: str, msg: str) -> str:
	target = repo / rel
	target.parent.mkdir(parents=True, exist_ok=True)
	target.write_text(text, encoding='utf-8')
	_git(repo, 'add', rel)
	_git(repo, 'commit', '--no-verify', '-m', msg)
	return _git(repo, 'rev-parse', 'HEAD')
# @used-by :func:`_commit_file()`
# @used-by :func:`_init_harness_repo()`
# @used-by :func:`_init_node_repo()`
# @used-by :func:`_init_py_repo()`
# @used-by :func:`_verify_tdd_gate_delegation()`
# @used-by :meth:`DiffExecutabilityContractTests.test_all_six_gates_delegate_through_diff_executability()`
def _git(repo: Path, *args: str) -> str:
	proc = subprocess.run(['git', '--no-optional-locks', '-C', str(repo), *args], stdin=subprocess.DEVNULL, capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=30, check=True, creationflags=_NO_WINDOW)
	return (proc.stdout or '').strip()
# @used-by :meth:`DiffExecutabilityContractTests.test_all_six_gates_delegate_through_diff_executability()`
# @used-by :meth:`DiffExecutabilityContractTests.test_runtime_snapshot_canary_skips_non_executable_and_runs_for_code_or_config()`
# @used-by :meth:`DiffExecutabilityContractTests.test_worktree_land_passes_prev_head_base_ref_and_skips_canary_for_non_exec()`
def _init_harness_repo(root: Path) -> Path:
	repo = root / 'harness_repo'
	(repo / 'scripts').mkdir(parents=True)
	(repo / 'tests').mkdir(parents=True)
	_git(repo, 'init', '-b', 'main')
	_git(repo, 'config', 'user.email', 'test@example.com')
	_git(repo, 'config', 'user.name', 'Test')
	(repo / '.git/info/exclude').write_text('\ua616/\n', encoding='utf-8')
	(repo / 'paths.json').write_text('{"version": 1}\n', encoding='utf-8')
	(repo / 'runtime.json').write_text('{"version": 1}\n', encoding='utf-8')
	(repo / 'README.md').write_text('# Harness Demo\n', encoding='utf-8')
	for ep in ('check_markdown_slop.py', 'check_rules_and_server_gate.py', 'check_pre_invocation.py', 'check_stop_gate.py', 'git_shim.py'):
		(repo / 'scripts' / ep).write_text(_SNAP_PY, encoding='utf-8')
	(repo / 'tests/test_ok.py').write_text(_TEST_OK_PY, encoding='utf-8')
	_git(repo, 'add', '.')
	_git(repo, 'commit', '--no-verify', '-m', 'init')
	return repo
# @used-by :meth:`DiffExecutabilityContractTests.test_all_six_gates_delegate_through_diff_executability()`
def _init_node_repo(root: Path) -> Path:
	repo = root / 'node_repo'
	repo.mkdir(parents=True)
	_git(repo, 'init', '-b', 'main')
	_git(repo, 'config', 'user.email', 'test@example.com')
	_git(repo, 'config', 'user.name', 'Test')
	(repo / 'package.json').write_text(json.dumps({'name': 'demo', 'scripts': {'test': 'node --test demo.test.js'}}), encoding='utf-8')
	(repo / 'app.js').write_text('// old\nconst x = 1;\n', encoding='utf-8')
	_git(repo, 'add', '.')
	_git(repo, 'commit', '--no-verify', '-m', 'init')
	return repo
# @used-by :meth:`DiffExecutabilityContractTests.test_all_six_gates_delegate_through_diff_executability()`
def _init_py_repo(root: Path) -> Path:
	repo = root / 'py_repo'
	(repo / 'pkg').mkdir(parents=True)
	(repo / 'tests').mkdir(parents=True)
	_git(repo, 'init', '-b', 'main')
	_git(repo, 'config', 'user.email', 'test@example.com')
	_git(repo, 'config', 'user.name', 'Test')
	(repo / '.git/info/exclude').write_text('\ua616/\n', encoding='utf-8')
	(repo / 'pkg/app.py').write_text(_APP_PY, encoding='utf-8')
	(repo / 'tests/test_ok.py').write_text(_TEST_OK_PY, encoding='utf-8')
	_git(repo, 'add', '.')
	_git(repo, 'commit', '--no-verify', '-m', 'init')
	return repo
# @used-by :meth:`DiffExecutabilityContractTests.test_all_six_gates_delegate_through_diff_executability()`
def _verify_tdd_gate_delegation(case: unittest.TestCase, py_repo: Path) -> None:
	from agent_tools.tdd import diff_executability as de, enforcement, evaluator, events
	app_f = py_repo / 'pkg/app.py'
	cmt_py = _APP_PY.replace('# header', '# updated header')
	with patch.object(de, 'is_non_executable_diff', wraps=de.is_non_executable_diff) as spy_pre:
		err = enforcement.evaluate_pre_tool_use_tdd('edit_file', {'Path': str(app_f), 'Target': '# header', 'Replacement': '# updated header'}, {'cwd': str(py_repo)})
		case.assertIsNone(err)
		case.assertGreaterEqual(spy_pre.call_count, 1)
	app_f.write_text(cmt_py, encoding='utf-8')
	_git(py_repo, 'add', 'pkg/app.py')
	with patch.object(de, 'is_non_executable_diff', wraps=de.is_non_executable_diff) as spy_commit:
		case.assertEqual([], enforcement.verify_staged_tdd_diff(py_repo, ['pkg/app.py'], use_index=True))
		case.assertGreaterEqual(spy_commit.call_count, 1)
	with patch.object(de, 'is_git_path_non_executable', wraps=de.is_git_path_non_executable) as spy_eval:
		ev_res = evaluator.evaluate_tdd_events([events.build_file_write_tdd_event(1, app_f, cwd=py_repo)], require_final_full_green=True, project_root=py_repo)
		case.assertTrue(ev_res['verified'], ev_res)
		case.assertGreaterEqual(spy_eval.call_count, 1)
	_git(py_repo, 'commit', '--no-verify', '-m', 'comment only')
class DiffExecutabilityContractTests(unittest.TestCase):
	# @used-by :mod:`unittest`
	def test_all_six_gates_delegate_through_diff_executability(self) -> None:
		from agent_tools import polyglot_land, runtime_snapshot, snapshot_canary
		from agent_tools.tdd import diff_executability as de
		from agent_tools.worktree_flow import worktree_begin, worktree_land
		with tempfile.TemporaryDirectory() as td:
			root = Path(td).resolve()
			py_repo = _init_py_repo(root)
			_verify_tdd_gate_delegation(self, py_repo)
			wt = Path(worktree_begin(py_repo, 'gate-wt', worktrees_dir=root / 'wts')['worktree'])
			_commit_file(wt, 'pkg/app.py', _APP_PY.replace('# header', '# wt comment'), 'wt cmt')
			with patch.object(de, 'classify_git_range', wraps=de.classify_git_range) as spy_wt:
				land = worktree_land(wt, run_tests=True, remove=True, owner='wt', leases_dir=root / 'leases', promote_snapshot=False)
				self.assertTrue(land['valid'] and land['landed'], land)
				self.assertGreaterEqual(spy_wt.call_count, 1)
			node_repo = _init_node_repo(root)
			node_wt = Path(worktree_begin(node_repo, 'node-wt', worktrees_dir=root / 'nwts')['worktree'])
			_commit_file(node_wt, 'app.js', '// updated\nconst x = 1;\n', 'js cmt')
			with patch.object(de, 'classify_git_range', wraps=de.classify_git_range) as spy_poly:
				ok_p, res_p = polyglot_land.run_polyglot_land_tests(node_repo, node_wt, base_ref='main')
				self.assertTrue(ok_p)
				self.assertIsNone(res_p)
				self.assertGreaterEqual(spy_poly.call_count, 1)
			h_repo = _init_harness_repo(root)
			prev_sha = _git(h_repo, 'rev-parse', 'HEAD')
			_commit_file(h_repo, 'README.md', '# Harness v2\n', 'doc edit')
			with patch.object(de, 'should_run_snapshot_canary', wraps=de.should_run_snapshot_canary) as spy_can, patch.object(de, 'classify_git_range', wraps=de.classify_git_range) as spy_rng, patch.object(snapshot_canary, 'run_pre_tool_use_canary', side_effect=AssertionError('must skip canary')):
				snap = runtime_snapshot.promote_runtime_snapshot(h_repo, store_dir=root / 'store', base_ref=prev_sha)
				self.assertTrue(snap['valid'] and snap['promoted'], snap)
				self.assertGreaterEqual(spy_can.call_count, 1)
				self.assertGreaterEqual(spy_rng.call_count, 1)
	# @used-by :mod:`unittest`
	def test_contract_constants_declare_all_six_gates_and_land_stage_policies(self) -> None:
		from agent_tools import tdd, tdd_gate
		from agent_tools.tdd.diff_executability import DIFF_EXECUTABILITY_GATES, should_run_snapshot_canary
		from agent_tools.worktree_flow import LAND_STAGE_POLICIES
		expected_gates = {'PreToolUse', 'pre-commit', 'tdd/evaluator.py', 'worktree_land', 'polyglot_land', 'runtime_snapshot'}
		self.assertEqual(expected_gates, set(DIFF_EXECUTABILITY_GATES))
		self.assertEqual(6, len(DIFF_EXECUTABILITY_GATES))
		self.assertIs(DIFF_EXECUTABILITY_GATES, tdd.DIFF_EXECUTABILITY_GATES)
		self.assertIs(DIFF_EXECUTABILITY_GATES, tdd_gate.DIFF_EXECUTABILITY_GATES)
		self.assertIs(should_run_snapshot_canary, tdd.should_run_snapshot_canary)
		self.assertIs(should_run_snapshot_canary, tdd_gate.should_run_snapshot_canary)
		exec_only = {'diff_coverage', 'polyglot_tests', 'post_land_health', 'snapshot_canary', 'tests'}
		always = {'ff_merge', 'push', 'python_integrity', 'rebase', 'snapshot_promote', 'tag', 'worktree_cleanup', 'xref_integrity'}
		self.assertTrue(set(LAND_STAGE_POLICIES.values()).issubset({'always', 'executable_only'}))
		for stage in exec_only:
			self.assertEqual('executable_only', LAND_STAGE_POLICIES.get(stage), stage)
		for stage in always:
			self.assertEqual('always', LAND_STAGE_POLICIES.get(stage), stage)
	# @used-by :mod:`unittest`
	def test_docs_and_rules_codify_contract_within_rules_audit_budgets(self) -> None:
		from agent_tools import links
		from agent_tools.rules_audit import audit_rules
		import check_markdown_slop
		audit = audit_rules(WT_ROOT)
		self.assertTrue(audit['valid'], audit['issues'])
		self.assertEqual([], audit['issues'])
		rule_p = WT_ROOT / 'rules/08-execution-and-tools.md'
		doc_p = WT_ROOT / 'scripts/docs/worktrees-and-testing.md'
		for doc in (rule_p, doc_p):
			self.assertEqual([], links.validate_file(doc, local_anchors=True, readable_links=True), str(doc))
			self.assertEqual([], check_markdown_slop.markdown_slop_issues(doc.read_text(encoding='utf-8')), str(doc))
		rule_txt = rule_p.read_text(encoding='utf-8')
		for tok in ('diff_executability', '--no-tests-reason'):
			self.assertIn(tok, rule_txt, f'Missing {tok!r} in rules/08-execution-and-tools.md')
		doc_txt = doc_p.read_text(encoding='utf-8')
		for tok in ('diff_executability', '--no-tests-reason', 'LAND_STAGE_POLICIES', 'runtime_snapshot'):
			self.assertIn(tok, doc_txt, f'Missing {tok!r} in scripts/docs/worktrees-and-testing.md')
	# @used-by :mod:`unittest`
	def test_runtime_snapshot_canary_skips_non_executable_and_runs_for_code_or_config(self) -> None:
		from agent_tools import runtime_snapshot, snapshot_canary
		with tempfile.TemporaryDirectory() as td:
			root = Path(td).resolve()
			repo, store = (_init_harness_repo(root), root / 'store')
			with patch.object(snapshot_canary, 'run_pre_tool_use_canary', return_value=(True, 'ok')) as spy_def:
				res_def = runtime_snapshot.promote_runtime_snapshot(repo, store_dir=store)
				self.assertTrue(res_def['valid'] and res_def['promoted'], res_def)
				self.assertFalse(res_def['canary_skipped'])
				self.assertEqual(1, spy_def.call_count)
			sha_doc = _commit_file(repo, 'README.md', '# Harness Updated\n', 'doc update')
			with patch.object(snapshot_canary, 'run_pre_tool_use_canary', side_effect=AssertionError('must skip canary')):
				res_doc = runtime_snapshot.promote_runtime_snapshot(repo, store_dir=store, base_ref=res_def['commit_sha'])
				self.assertTrue(res_doc['valid'] and res_doc['promoted'] and res_doc['canary_skipped'], res_doc)
				self.assertEqual(sha_doc, json.loads((store / 'current.json').read_text(encoding='utf-8'))['current'])
			sha_cmt = _commit_file(repo, 'scripts/check_stop_gate.py', _SNAP_PY.replace('# snap header', '# new comment'), 'cmt update')
			with patch.object(snapshot_canary, 'run_pre_tool_use_canary', side_effect=AssertionError('must skip canary')):
				res_cmt = runtime_snapshot.promote_runtime_snapshot(repo, store_dir=store, base_ref=sha_doc)
				self.assertTrue(res_cmt['valid'] and res_cmt['promoted'] and res_cmt['canary_skipped'], res_cmt)
				self.assertEqual(sha_cmt, json.loads((store / 'current.json').read_text(encoding='utf-8'))['current'])
			sha_py = _commit_file(repo, 'scripts/check_stop_gate.py', _SNAP_PY.replace('VAL = 1', 'VAL = 2'), 'exec py')
			with patch.object(snapshot_canary, 'run_pre_tool_use_canary', return_value=(True, 'ok')) as spy_py:
				res_py = runtime_snapshot.promote_runtime_snapshot(repo, store_dir=store, base_ref=sha_cmt)
				self.assertTrue(res_py['valid'] and res_py['promoted'] and (not res_py['canary_skipped']), res_py)
				self.assertEqual(1, spy_py.call_count)
			_commit_file(repo, 'runtime.json', '{"version": 2}\n', 'config change')
			with patch.object(snapshot_canary, 'run_pre_tool_use_canary', return_value=(True, 'ok')) as spy_cfg:
				res_cfg = runtime_snapshot.promote_runtime_snapshot(repo, store_dir=store, base_ref=sha_py)
				self.assertTrue(res_cfg['valid'] and res_cfg['promoted'] and (not res_cfg['canary_skipped']), res_cfg)
				self.assertEqual('runtime_config_changed', res_cfg['canary_reason'])
				self.assertEqual(1, spy_cfg.call_count)
	# @used-by :mod:`unittest`
	def test_worktree_land_passes_prev_head_base_ref_and_skips_canary_for_non_exec(self) -> None:
		from agent_tools import snapshot_canary
		from agent_tools.worktree_flow import worktree_begin, worktree_land
		with tempfile.TemporaryDirectory() as td:
			root = Path(td).resolve()
			repo = _init_harness_repo(root)
			store, leases = (root / 'store', root / 'leases')
			wt = Path(worktree_begin(repo, 'doc-snap', worktrees_dir=root / 'wts')['worktree'])
			_commit_file(wt, 'README.md', '# Landed Doc\n', 'doc land')
			with patch.object(snapshot_canary, 'run_pre_tool_use_canary', side_effect=AssertionError('must skip canary')):
				land = worktree_land(wt, run_tests=True, remove=True, owner='doc', leases_dir=leases, promote_snapshot=True, snapshot_store=store)
			self.assertTrue(land['valid'] and land['landed'], land)
			self.assertEqual(0, land['test_runs'])
			self.assertTrue(land['runtime_snapshot']['promoted'], land['runtime_snapshot'])
			self.assertTrue(land['runtime_snapshot']['canary_skipped'], land['runtime_snapshot'])
			ptr = json.loads((store / 'current.json').read_text(encoding='utf-8'))
			self.assertEqual(land['head'], ptr['current'])
if '__main__' == __name__:
	unittest.main()
