# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from pathlib import Path
import ast
import os
# 2026-11-26 "Move turn lifecycle subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/383
HOST_PROFILE_ENV_VARS = ('ANTIGRAVITY_ACCOUNT', 'ANTIGRAVITY_APP_DATA_DIR', 'CODEX_HOME')
WORKTREE_LAND_GATE_CONTRACTS: dict[str, dict[str, tuple[tuple[str, str], ...]]] = {
	'run_parallel_tests': {'timeout_tests': (('test_parallel_runner.py', 'ParallelRunnerTests.test_parallel_runner_module_timeout_terminates_stalled_worker'),)},
	'run_polyglot_land_tests': {'timeout_tests': (('test_polyglot_land.py', 'PolyglotLandTests.test_polyglot_land_and_health_handle_subprocess_timeout_cleanly'),)},
	'run_repo_health_check': {'timeout_tests': (('test_polyglot_land.py', 'PolyglotLandTests.test_polyglot_land_and_health_handle_subprocess_timeout_cleanly'),)},
	'verify_worktree_diff_coverage': {
		'scaling_tests': (
			('test_diff_coverage_gate.py', 'DiffCoverageGateTests.test_select_targeted_narrows_large_cross_cutting_test_diffs_to_prod_stems_and_packages'),
			('test_diff_coverage_gate.py', 'DiffCoverageGateTests.test_select_targeted_falls_back_to_direct_when_large_diff_has_no_token_match'),
			('test_diff_coverage_gate.py', 'DiffCoverageGateTests.test_worktree_land_handles_cross_cutting_commit_and_diff_coverage_timeout'),
		),
		'timeout_tests': (
			('test_diff_coverage_gate.py', 'DiffCoverageGateTests.test_run_trace_diff_coverage_handles_timeout_gracefully'),
			('test_diff_coverage_gate.py', 'DiffCoverageGateTests.test_worktree_land_handles_cross_cutting_commit_and_diff_coverage_timeout'),
		),
	},
	'verify_worktree_python_changes': {'scaling_tests': (('test_python_integrity_gate.py', 'PythonIntegrityGateTests.test_worktree_land_python_integrity_handles_cross_cutting_multi_file_commit'),)},
	'verify_worktree_xref_changes': {'scaling_tests': (('test_xref_gate.py', 'XrefGateTests.test_worktree_land_xref_handles_cross_cutting_multi_file_commit'),)},
}
_METADATA_CLI_COMMANDS = frozenset({'answer-prepare', 'cleanup-report', 'problem-metadata'})
_METADATA_SYMBOLS = frozenset({'build_answer_metadata', 'build_github_issue_metadata', 'build_problem_metadata', 'cleanup_report', 'format_answer_metadata_header', 'format_github_issue_metadata_header', 'format_problem_metadata_block', 'prepend_github_issue_metadata', 'record_cleanup_answer'})
_SUBPROCESS_RUNNERS = frozenset({'Popen', 'check_call', 'check_output', 'run'})
_WORKTREE_LAND_GATE_FUNCS = frozenset({'_post_merge_checks', '_rebase_and_test', '_run_land_checks', '_run_land_tests'})
# @used-by :func:`dfh_audit_metadata_test_env_isolation()`
def _audit_test_function(rel: str, fn: ast.FunctionDef, *, class_isolated: bool=False) -> list[str]:
	if class_isolated:
		errs: list[str] = []
	else:
		assigns = _collect_dict_assigns(fn)
		isolated, errs = _patch_dict_env_status(rel, fn, assigns)
		if fn.name.startswith('test_'):
			for node in ast.walk(fn):
				if isinstance(node, ast.Call):
					err = _check_one_metadata_call(rel, fn, node, isolated, assigns)
					if None is not err:
						errs.append(err)
	return errs
# @used-by :func:`_check_one_metadata_call()`
# @used-by :func:`_dict_literal_keys()`
# @used-by :func:`_extract_worktree_land_gates()`
# @used-by :func:`_has_substantive_assertion()`
# @used-by :func:`_is_metadata_cli_subprocess()`
def _call_name(node: ast.Call) -> str:
	if isinstance(node.func, ast.Name):
		r = node.func.id
	elif isinstance(node.func, ast.Attribute):
		r = node.func.attr
	else:
		r = ''
	return r
# @used-by :func:`_audit_test_function()`
def _check_one_metadata_call(rel: str, fn: ast.FunctionDef, call: ast.Call, isolated: bool, assigns: dict[str, set[str]]) -> str | None:
	name = _call_name(call)
	r: str | None = None
	if _is_metadata_cli_subprocess(call) and (not _subprocess_env_isolated(call, isolated, assigns)):
		r = f'{rel}:{fn.name}: unisolated metadata CLI subprocess call'
	elif name in _METADATA_SYMBOLS and None is _kw_value(call, 'env') and (not isolated):
		r = f'{rel}:{fn.name}: metadata call {name} lacks host profile env isolation'
	return r
# @used-by :func:`_patch_dict_env_status()`
def _check_one_patch_dict(rel: str, fn: ast.FunctionDef, call: ast.Call, assigns: dict[str, set[str]]) -> tuple[bool, list[str]]:
	clear_kw = _kw_value(call, 'clear')
	if isinstance(clear_kw, ast.Constant) and True is clear_kw.value:
		r: tuple[bool, list[str]] = (True, [])
	else:
		keys = _dict_literal_keys(call.args[1], assigns)
		if None is keys:
			r = (False, [])
		else:
			missing = [k for k in HOST_PROFILE_ENV_VARS if k not in keys]
			if not missing:
				r = (True, [])
			elif keys & set(HOST_PROFILE_ENV_VARS):
				joined = ', '.join(missing)
				r = (False, [f'{rel}:{fn.name}: partial os.environ patch missing {joined}'])
			else:
				r = (False, [])
	return r
# @used-by :func:`dfh_audit_metadata_test_env_isolation()`
def _class_setup_isolates_env(cls_node: ast.ClassDef) -> bool:
	r = False
	for item in cls_node.body:
		if isinstance(item, ast.FunctionDef) and 'setUp' == item.name:
			iso, errs = _patch_dict_env_status(cls_node.name, item, _collect_dict_assigns(item))
			r = iso and (not errs)
			break
	return r
# @used-by :func:`_audit_test_function()`
# @used-by :func:`_class_setup_isolates_env()`
def _collect_dict_assigns(fn: ast.FunctionDef) -> dict[str, set[str]]:
	assigns: dict[str, set[str]] = {}
	for node in ast.walk(fn):
		if isinstance(node, ast.Assign) and 1 == len(node.targets) and isinstance(node.targets[0], ast.Name):
			keys = _dict_literal_keys(node.value, assigns)
			if None is not keys:
				assigns[node.targets[0].id] = keys
	return assigns
# @used-by :func:`_check_one_patch_dict()`
# @used-by :func:`_collect_dict_assigns()`
# @used-by :func:`_subprocess_env_isolated()`
def _dict_literal_keys(expr: ast.expr, assigns: dict[str, set[str]]) -> set[str] | None:
	if isinstance(expr, ast.Dict):
		r: set[str] | None = {k.value for k in expr.keys if isinstance(k, ast.Constant) and isinstance(k.value, str)}
	elif isinstance(expr, ast.Name) and expr.id in assigns:
		r = assigns[expr.id]
	elif isinstance(expr, ast.Call) and _call_name(expr) in {'isolated_host_env', 'isolated_subprocess_env'}:
		r = set(HOST_PROFILE_ENV_VARS)
	else:
		r = None
	return r
# @used-by :func:`dfh_audit_worktree_land_gate_contracts()`
def _extract_worktree_land_gates(worktree_flow_py: Path) -> set[str]:
	tree = ast.parse(worktree_flow_py.read_text(encoding='utf-8'))
	gates: set[str] = set()
	for node in tree.body:
		if isinstance(node, ast.FunctionDef) and node.name in _WORKTREE_LAND_GATE_FUNCS:
			for sub in ast.walk(node):
				if isinstance(sub, ast.Call):
					name = _call_name(sub)
					if name.startswith(('run_', 'verify_')):
						gates.add(name)
	return gates
# @used-by :func:`_verify_contract_test_ref()`
def _find_test_method(tree: ast.Module, qualname: str) -> ast.FunctionDef | None:
	r: ast.FunctionDef | None = None
	if '.' not in qualname:
		r = next((n for n in tree.body if isinstance(n, ast.FunctionDef) and qualname == n.name), None)
	else:
		cls_name, meth_name = qualname.split('.', 1)
		cls_node = next((n for n in tree.body if isinstance(n, ast.ClassDef) and cls_name == n.name), None)
		if None is not cls_node:
			r = next((item for item in cls_node.body if isinstance(item, ast.FunctionDef) and meth_name == item.name), None)
	return r
# @used-by :func:`_verify_contract_test_ref()`
def _has_substantive_assertion(fn: ast.FunctionDef) -> bool:
	return any((isinstance(n, ast.Assert) or (isinstance(n, ast.Call) and _call_name(n).startswith('assert')) for n in ast.walk(fn)))
# @used-by :func:`_is_patch_dict_environ()`
def _is_environ_target(arg: ast.expr) -> bool:
	return (isinstance(arg, ast.Constant) and 'os.environ' == arg.value) or (isinstance(arg, ast.Attribute) and 'environ' == arg.attr)
# @used-by :func:`_check_one_metadata_call()`
def _is_metadata_cli_subprocess(call: ast.Call) -> bool:
	if not call.args or _call_name(call) not in _SUBPROCESS_RUNNERS:
		r = False
	else:
		strs = {n.value for n in ast.walk(call.args[0]) if isinstance(n, ast.Constant) and isinstance(n.value, str)}
		r = bool(strs & _METADATA_CLI_COMMANDS) and (not (strs & {'-h', '--help'}))
	return r
# @used-by :func:`_patch_dict_env_status()`
def _is_patch_dict_environ(call: ast.Call) -> bool:
	return isinstance(call.func, ast.Attribute) and 'dict' == call.func.attr and 2 <= len(call.args) and _is_environ_target(call.args[0])
# @used-by :func:`_check_one_metadata_call()`
# @used-by :func:`_check_one_patch_dict()`
# @used-by :func:`_subprocess_env_isolated()`
def _kw_value(call: ast.Call, name: str) -> ast.expr | None:
	return next((kw.value for kw in call.keywords if name == kw.arg), None)
# @used-by :func:`_audit_test_function()`
# @used-by :func:`_class_setup_isolates_env()`
def _patch_dict_env_status(rel: str, fn: ast.FunctionDef, assigns: dict[str, set[str]]) -> tuple[bool, list[str]]:
	isolated = False
	errs: list[str] = []
	for node in ast.walk(fn):
		if isinstance(node, ast.Call) and _is_patch_dict_environ(node):
			iso, node_errs = _check_one_patch_dict(rel, fn, node, assigns)
			isolated = isolated or iso
			errs.extend(node_errs)
	return (isolated, errs)
# @used-by :func:`_check_one_metadata_call()`
def _subprocess_env_isolated(call: ast.Call, isolated: bool, assigns: dict[str, set[str]]) -> bool:
	env_kw = _kw_value(call, 'env')
	if None is env_kw:
		r = isolated
	else:
		keys = _dict_literal_keys(env_kw, assigns)
		r = True if None is keys else set(HOST_PROFILE_ENV_VARS).issubset(keys)
	return r
# @used-by :func:`_verify_gate_entry()`
def _verify_contract_test_ref(tests_dir: Path, gate: str, filename: str, qualname: str) -> str | None:
	path = tests_dir / filename
	if not path.is_file():
		r: str | None = f'{gate}: missing contract test file {filename} ({qualname})'
	else:
		fn = _find_test_method(ast.parse(path.read_text(encoding='utf-8')), qualname)
		if None is fn:
			r = f'{gate}: missing contract test method {filename}::{qualname}'
		elif not _has_substantive_assertion(fn):
			r = f'{gate}: contract test {filename}::{qualname} has no substantive assertion'
		else:
			r = None
	return r
# @used-by :func:`dfh_audit_worktree_land_gate_contracts()`
def _verify_gate_entry(tests_dir: Path, gate: str, entry: dict[str, tuple[tuple[str, str], ...]]) -> list[str]:
	refs = [*entry.get('scaling_tests', ()), *entry.get('timeout_tests', ())]
	errs: list[str] = [] if refs else [f'{gate}: contract entry declares no scaling_tests or timeout_tests']
	for filename, qualname in refs:
		err = _verify_contract_test_ref(tests_dir, gate, filename, qualname)
		if None is not err:
			errs.append(err)
	return errs
# @used-by :meth:`Df.Harness.Completion.EnvIsolationAuditor.EnvIsolationAuditor.run()`
# @used-by :meth:`test_df_harness_s11_wave2d_completion_cov.DfHarnessS11Wave2dCompletionCovTests.test_env_isolation_auditor_and_recovery_ops()`
def dfh_audit_metadata_test_env_isolation(tests_dir: Path) -> list[str]:
	errs: list[str] = []
	for path in sorted(Path(tests_dir).glob('test_*.py')):
		tree = ast.parse(path.read_text(encoding='utf-8'))
		for node in tree.body:
			if isinstance(node, ast.FunctionDef):
				errs.extend(_audit_test_function(path.name, node))
			elif isinstance(node, ast.ClassDef):
				cls_iso = _class_setup_isolates_env(node)
				for item in node.body:
					if isinstance(item, ast.FunctionDef):
						errs.extend(_audit_test_function(path.name, item, class_isolated=cls_iso))
	return errs
# @used-by :meth:`Df.Harness.Completion.EnvIsolationAuditor.EnvIsolationAuditor.run()`
# @used-by :meth:`test_env_isolation_and_worktree_gate_contracts.EnvIsolationAndWorktreeGateContractsTests.test_harness_worktree_land_gates_pass_scaling_and_timeout_contract_and_negative_detection()`
def dfh_audit_worktree_land_gate_contracts(scripts_dir: Path, tests_dir: Path, *, registry: dict[str, dict[str, tuple[tuple[str, str], ...]]] | None=None) -> list[str]:
	reg = WORKTREE_LAND_GATE_CONTRACTS if None is registry else registry
	wf_path = Path(scripts_dir) / 'agent_tools/worktree_flow.py'
	if not wf_path.is_file():
		errs = [f'Missing worktree_flow.py at {wf_path.as_posix()}']
	else:
		gates = _extract_worktree_land_gates(wf_path)
		errs = [f'Unregistered worktree-land gate: {g}' for g in sorted(gates) if g not in reg]
		for gate in sorted(gates & set(reg)):
			errs.extend(_verify_gate_entry(Path(tests_dir), gate, reg[gate]))
	return errs
# @used-by :func:`dfh_isolated_subprocess_env()`
# @used-by :meth:`test_cleanup.CleanupReportTests.test_cli_logs_actual_stdin_answer_from_either_platform_without_running_cleanup()`
# @used-by :meth:`test_cleanup.CleanupReportTests.test_empty_answer_or_naive_timestamp_does_not_create_a_log()`
# @used-by :meth:`test_cleanup.CleanupReportTests.test_exact_answer_and_filename_use_the_same_istanbul_time_across_utc_midnight()`
# @used-by :meth:`test_cleanup.CleanupReportTests.test_repeated_and_concurrent_answers_never_overwrite_logs_in_the_same_minute()`
# @used-by :meth:`test_cleanup_audit.CleanupAuditTests.test_cleanup_report_isolates_conflicting_host_a0_and_codex_env()`
# @used-by :meth:`test_cleanup_audit.CleanupAuditTests.test_cleanup_report_writes_metadata_header_links_manifest_and_consumes_scratch_file()`
# @used-by :meth:`test_cleanup_integration.CleanupIntegrationTests.test_apply_and_cleanup_report_manifest_and_metadata_roundtrip()`
# @used-by :meth:`test_env_isolation_and_worktree_gate_contracts.EnvIsolationAndWorktreeGateContractsTests.test_harness_metadata_tests_pass_host_env_isolation_contract_and_negative_detection()`
# @used-by :meth:`test_github_issue.TestGitHubIssueTool.test_create_and_consume_input_with_readback_verification()`
# @used-by :meth:`test_github_issue.TestGitHubIssueTool.test_create_prepends_tab_indented_json_metadata_header_and_supports_opt_out()`
def dfh_isolated_host_env(**overrides: str) -> dict[str, str]:
	r = {k: '' for k in HOST_PROFILE_ENV_VARS}
	r.update(overrides)
	return r
# @used-by :meth:`test_df_harness_s11_wave2d_completion_cov.DfHarnessS11Wave2dCompletionCovTests.test_env_isolation_auditor_and_recovery_ops()`
# @used-by :meth:`test_env_isolation_and_worktree_gate_contracts.EnvIsolationAndWorktreeGateContractsTests.test_harness_metadata_tests_pass_host_env_isolation_contract_and_negative_detection()`
# @used-by :meth:`test_problem_metadata.ProblemMetadataTests.test_cli_problem_metadata_outputs_json_and_markdown_and_enforces_issue_key()`
def dfh_isolated_subprocess_env(base: dict[str, str] | None=None, **overrides: str) -> dict[str, str]:
	r = dict(os.environ if None is base else base)
	r.update(dfh_isolated_host_env(**overrides))
	return r
