# 2026-11-24 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from pathlib import Path
from ..shell_audit import _split_shell_segments, normalize_host_path
from .classifier import _norm_posix, resolve_code_scope
from .commands import classify_test_command
from .exemption import is_write_event_exempt
# 2026-11-26 "Support parent-issue inheritance and worktree-scoped TDD keys for coding fan-out": https://github.com/dmitry-ai/harness/issues/351
from .worktree_scope import canonical_scope_path, resolve_tdd_scope_key, scope_matches_commit, worktree_command_matches
# @used-by :func:`evaluate_tdd_events()`
def _apply_command_event(ev: dict, step: int, order: tuple[int, int, int], scopes: dict[str, dict], orders: dict[str, dict], failfast_warnings: list[str]) -> None:
	outcome = ev.get('outcome') or {}
	if ev.get('is_git_commit') and outcome.get('exit_code') in (0, None):
		_apply_commit_reset(ev.get('commit_scope'), scopes, orders, ev=ev)
	t_info = ev.get('test_info') or {}
	if t_info.get('is_test_cmd') and (not t_info.get('rigged_failure')):
		if t_info.get('is_full_suite'):
			_collect_failfast_warnings(str(ev.get('cmd') or ''), step, failfast_warnings)
		for sk, st in scopes.items():
			if _command_matches_scope(ev, sk, set(st['written_tests'])):
				_update_scope_from_test_cmd(sk, st, orders[sk], ev, step, order, outcome, t_info)
# 2026-11-26 "Support parent-issue inheritance and worktree-scoped TDD keys for coding fan-out": https://github.com/dmitry-ai/harness/issues/351
# @used-by :func:`_apply_command_event()`
def _apply_commit_reset(c_scope: str | None, scopes: dict[str, dict], orders: dict[str, dict], *, ev: dict | None=None) -> None:
	for sk, st in scopes.items():
		if scope_matches_commit(sk, c_scope, ev):
			st['state'] = 'IDLE'
			st['written_test_step'] = None
			st['red_step'] = None
			st['red_cmd'] = None
			st['cycle_had_prod_edit'] = False
			st['cycle_green_step'] = None
			orders[sk]['written_test'] = None
# 2026-11-26 "Support parent-issue inheritance and worktree-scoped TDD keys for coding fan-out": https://github.com/dmitry-ai/harness/issues/351
# 2026-11-26 "Implement diff executability classifier and automatic test skip": https://github.com/dmitry-ai/harness/issues/358
# @used-by :func:`evaluate_tdd_events()`
def _apply_file_write_event(ev: dict, step: int, order: tuple[int, int, int], scopes: dict[str, dict], orders: dict[str, dict], violations: list[str], *, project_root: Path | None=None, exempt_cache: dict[tuple[str, str], bool] | None=None) -> None:
	cls = ev.get('classification')
	fpath = str(ev.get('path') or '')
	scope_str = resolve_tdd_scope_key(fpath, str(ev.get('scope') or ''))
	cache = {} if None is exempt_cache else exempt_cache
	if 'test' == cls and scope_str:
		_apply_test_file_event(fpath, scope_str, step, order, scopes, orders, project_root, cache)
	elif 'production' == cls and scope_str:
		_apply_prod_file_event(fpath, scope_str, step, order, scopes, orders, violations, project_root, cache)
# 2026-11-26 "Implement diff executability classifier and automatic test skip": https://github.com/dmitry-ai/harness/issues/358
# 2026-11-26 "Add diff executability telemetry to worktree_land output and tdd_check scopes": https://github.com/dmitry-ai/harness/issues/359
# @used-by :func:`_apply_file_write_event()`
def _apply_test_file_event(fpath: str, scope_str: str, step: int, order: tuple[int, int, int], scopes: dict[str, dict], orders: dict[str, dict], project_root: Path | None, exempt_cache: dict[tuple[str, str], bool]) -> None:
	if _is_exempt_cached(fpath, scope_str, project_root, exempt_cache):
		_record_exempt_edit(scopes, orders, scope_str, fpath, step, 'test')
	else:
		st, st_ord = _ensure_scope(scopes, orders, scope_str)
		_apply_test_write(st, st_ord, fpath, step, order)
# 2026-11-25
# "Short-circuit non-code PreToolUse TDD checks and lazily memoize exemptions":
# https://github.com/dmitry-ai/harness/issues/250
# 2026-11-26 "Add diff executability telemetry to worktree_land output and tdd_check scopes": https://github.com/dmitry-ai/harness/issues/359
# @used-by :func:`_apply_file_write_event()`
def _apply_prod_file_event(fpath: str, scope_str: str, step: int, order: tuple[int, int, int], scopes: dict[str, dict], orders: dict[str, dict], violations: list[str], project_root: Path | None, exempt_cache: dict[tuple[str, str], bool]) -> None:
	existing = scopes.get(scope_str)
	if None is not existing and existing['state'] in ('RED_VERIFIED', 'GREEN_IMPLEMENTING'):
		st, st_ord = (existing, orders[scope_str])
		st_ord['unverified_prod_writes'].append((fpath, order))
		_apply_prod_write(st, st_ord, fpath, step, order, violations)
	elif _is_exempt_cached(fpath, scope_str, project_root, exempt_cache):
		_record_exempt_edit(scopes, orders, scope_str, fpath, step, 'production')
	else:
		st, st_ord = _ensure_scope(scopes, orders, scope_str)
		st_ord['last_non_exempt_prod'] = order
		_apply_prod_write(st, st_ord, fpath, step, order, violations)
# @used-by :func:`_apply_prod_file_event()`
def _apply_prod_write(st: dict, st_ord: dict, fpath: str, step: int, order: tuple[int, int, int], violations: list[str]) -> None:
	st['any_prod_edit'] = True
	if fpath not in st['touched_prod_files']:
		st['touched_prod_files'].append(fpath)
	if st['state'] in ('RED_VERIFIED', 'GREEN_IMPLEMENTING'):
		st['state'] = 'GREEN_IMPLEMENTING'
	elif 'TEST_WRITTEN' == st['state']:
		violations.append(f'EXEC-2 TDD-RED-GATE: Production code "{fpath}" edited at step {step} after writing test(s), but no failing (RED) test run was observed after the test edit. Run the new test and observe it fail before writing production code.')
	else:
		violations.append(f'EXEC-2 TDD-RED-GATE: Production code "{fpath}" edited at step {step} without first writing a test and observing it fail (RED).')
	st['cycle_had_prod_edit'] = True
	st['last_prod_edit_step'] = step
	st['last_code_edit_step'] = step
	st_ord['last_code_edit'] = order
# @used-by :func:`_apply_test_file_event()`
def _apply_test_write(st: dict, st_ord: dict, fpath: str, step: int, order: tuple[int, int, int]) -> None:
	if fpath not in st['written_tests']:
		st['written_tests'].append(fpath)
	if st['state'] in ('IDLE', 'TEST_WRITTEN'):
		st['state'] = 'TEST_WRITTEN'
		st['written_test_step'] = step
		st_ord['written_test'] = order
	st['last_code_edit_step'] = step
	st_ord['last_code_edit'] = order
	st_ord['last_test_edit'] = order
# @used-by :func:`_apply_command_event()`
def _collect_failfast_warnings(cmd_text: str, step: int, failfast_warnings: list[str]) -> None:
	from ..failfast_gate import missing_failfast_flag
	for seg in _split_shell_segments(cmd_text):
		miss = missing_failfast_flag(seg.strip())
		if None is not miss:
			warn = f'EXEC-2 fail-fast advisory: Full-suite command at step {step} ({miss[0]}) omitted "{miss[1]}"; prefer fail-fast or harness.py run-tests.'
			if warn not in failfast_warnings:
				failfast_warnings.append(warn)
			break
# @used-by :func:`evaluate_tdd_events()`
def _collect_final_green_violations(scopes: dict[str, dict], orders: dict[str, dict], project_root: Path | None, exempt_cache: dict[tuple[str, str], bool]) -> list[str]:
	r: list[str] = []
	for sk, st in sorted(scopes.items()):
		if _scope_needs_final_full_green(sk, st, orders[sk], project_root, exempt_cache):
			r.append(f"EXEC-2 TDD-FULL-GATE: Repository \"{sk}\" has production code edits (last edit at step {st['last_code_edit_step']}) without a subsequent passing (GREEN) full test suite run. Run the full test suite and verify all tests pass.")
	return r
# 2026-11-26 "Support parent-issue inheritance and worktree-scoped TDD keys for coding fan-out": https://github.com/dmitry-ai/harness/issues/351
# @used-by :func:`_apply_command_event()`
def _command_matches_scope(event: dict, scope_str: str, written_test_files: set[str]) -> bool:
	t_info = event.get('test_info') or {}
	is_full_cmd = bool(t_info.get('is_full_suite'))
	if False is worktree_command_matches(event, scope_str, is_full_cmd):
		r = False
	else:
		scope_p = canonical_scope_path(scope_str)
		scope_key = scope_p.as_posix().lower()
		scope_main_key = _git_main_repo_root(scope_p).as_posix().lower()
		cmd_norm = _norm_posix(str(event.get('cmd') or '')).lower()
		cwd_raw = event.get('cwd')
		cwd_p = Path(cwd_raw).resolve() if cwd_raw else None
		resolved_scopes = _resolve_event_target_scopes(t_info.get('target_paths') or [], cwd_p)
		r = _scopes_overlap(resolved_scopes, scope_p, scope_key, scope_main_key, is_full_cmd) or any(Path(tf).name.lower() in cmd_norm or Path(tf).stem.lower() in cmd_norm for tf in written_test_files) or scope_key in cmd_norm or ((not resolved_scopes) and _cwd_matches_scope(cwd_p, scope_p, scope_key, scope_main_key, is_full_cmd))
	return r
# @used-by :func:`_command_matches_scope()`
def _cwd_matches_scope(cwd_p: Path | None, scope_p: Path, scope_key: str, scope_main_key: str, is_full_cmd: bool) -> bool:
	r = False
	if None is not cwd_p:
		cwd_scope = resolve_code_scope(cwd_p)
		direct = cwd_scope.as_posix().lower() == scope_key or cwd_p.is_relative_to(scope_p) or scope_p.is_relative_to(cwd_p)
		r = direct or (is_full_cmd and _git_main_repo_root(cwd_scope).as_posix().lower() == scope_main_key)
	return r
# 2026-11-26 "Add diff executability telemetry to worktree_land output and tdd_check scopes": https://github.com/dmitry-ai/harness/issues/359
# @used-by :func:`_apply_prod_file_event()`
# @used-by :func:`_apply_test_file_event()`
# @used-by :func:`_record_exempt_edit()`
def _ensure_scope(scopes: dict[str, dict], orders: dict[str, dict], scope_str: str) -> tuple[dict, dict]:
	st = scopes.setdefault(scope_str, {
		'any_prod_edit': False,
		'cycle_green_step': None,
		'cycle_had_prod_edit': False,
		'exempt_edits': [],
		'last_code_edit_step': None,
		'last_full_green_step': None,
		'last_prod_edit_step': None,
		'red_cmd': None,
		'red_step': None,
		'state': 'IDLE',
		'touched_prod_files': [],
		'written_test_step': None,
		'written_tests': [],
	})
	# 2026-11-24
	# "Fix EXEC-2 TDD trace scoping for deleted worktrees and subagent steps":
	# https://github.com/dmitry-ai/harness/issues/173
	st_ord = orders.setdefault(scope_str, {'last_code_edit': None, 'last_full_green': None, 'last_non_exempt_prod': None, 'last_test_edit': None, 'unverified_prod_writes': [], 'written_test': None})
	return (st, st_ord)
# @used-by :func:`_command_matches_scope()`
# @used-by :func:`_cwd_matches_scope()`
# @used-by :func:`_scopes_overlap()`
def _git_main_repo_root(repo: Path) -> Path:
	r = repo.resolve()
	dot_git = r / '.git'
	if dot_git.is_file():
		try:
			txt = dot_git.read_text(encoding='utf-8', errors='replace').strip()
			if txt.lower().startswith('gitdir:'):
				gitdir = normalize_host_path(txt.split(':', 1)[1].strip())
				if not gitdir.is_absolute():
					gitdir = (r / gitdir).resolve()
				if 'worktrees' == gitdir.parent.name and '.git' == gitdir.parent.parent.name:
					r = gitdir.parent.parent.parent.resolve()
		except OSError:
			pass
	return r
# 2026-11-25
# "Short-circuit non-code PreToolUse TDD checks and lazily memoize exemptions":
# https://github.com/dmitry-ai/harness/issues/250
# @used-by :func:`_scope_needs_final_full_green()`
def _has_non_exempt_prod(sk: str, st_ord: dict, project_root: Path | None, exempt_cache: dict[tuple[str, str], bool], *, min_order: tuple[int, int, int] | None=None) -> bool:
	known = st_ord['last_non_exempt_prod']
	if None is not known and (None is min_order or known >= min_order):
		r = True
	else:
		r = any((not _is_exempt_cached(fp, sk, project_root, exempt_cache) for fp, ord_ in st_ord['unverified_prod_writes'] if None is min_order or ord_ >= min_order))
	return r
# 2026-11-25
# "Add comment-only diff lexer exemption for top 20 repository languages":
# https://github.com/dmitry-ai/harness/issues/238
# 2026-11-25
# "Short-circuit non-code PreToolUse TDD checks and lazily memoize exemptions":
# https://github.com/dmitry-ai/harness/issues/250
# @used-by :func:`_apply_prod_file_event()`
# @used-by :func:`_apply_test_file_event()`
# @used-by :func:`_has_non_exempt_prod()`
def _is_exempt_cached(fpath: str, scope_str: str, project_root: Path | None, cache: dict[tuple[str, str], bool]) -> bool:
	key = (scope_str, fpath)
	if key not in cache:
		# 2026-11-26 "Support parent-issue inheritance and worktree-scoped TDD keys for coding fan-out": https://github.com/dmitry-ai/harness/issues/351
		cache[key] = is_write_event_exempt(fpath, str(canonical_scope_path(scope_str)), project_root=project_root)
	return cache[key]
# 2026-11-24
# "Fix EXEC-2 TDD trace scoping for deleted worktrees and subagent steps":
# https://github.com/dmitry-ai/harness/issues/173
# @used-by :func:`evaluate_tdd_events()`
def _order_tdd_events(events: list[dict] | tuple[dict, ...] | None) -> list[tuple[tuple[int, int, int], int, dict]]:
	sub_ids: dict[str, int] = {}
	tagged: list[tuple[tuple[int, int, int], int, dict]] = []
	for idx, ev in enumerate(events or ()):
		step = int(ev.get('step', 0))
		raw_sub = ev.get('sub_step')
		sub_step = int(raw_sub) if isinstance(raw_sub, int) and (not isinstance(raw_sub, bool)) else -1
		cid = str(ev.get('subagent_id') or '').strip()
		if cid:
			sub_seq = sub_ids.setdefault(cid, len(sub_ids) + 1)
		else:
			sub_seq = 0 if 0 > sub_step else 1
		tagged.append(((step, sub_seq, sub_step), idx, ev))
	tagged.sort(key=lambda item: (item[0], item[1]))
	return tagged
# 2026-11-26 "Add diff executability telemetry to worktree_land output and tdd_check scopes": https://github.com/dmitry-ai/harness/issues/359
# @used-by :func:`_apply_prod_file_event()`
# @used-by :func:`_apply_test_file_event()`
def _record_exempt_edit(scopes: dict[str, dict], orders: dict[str, dict], scope_str: str, fpath: str, step: int, cls: str) -> None:
	st, _ = _ensure_scope(scopes, orders, scope_str)
	entry = {'classification': cls, 'path': fpath, 'step': step}
	if entry not in st['exempt_edits']:
		st['exempt_edits'].append(entry)
# @used-by :func:`_command_matches_scope()`
def _resolve_event_target_scopes(targets: list[str], cwd_p: Path | None) -> list[Path]:
	r: list[Path] = []
	for tp in targets:
		try:
			cand = normalize_host_path(tp)
			full = cand.resolve() if cand.is_absolute() else ((cwd_p / cand).resolve() if cwd_p else cand.resolve())
			r.append(resolve_code_scope(full))
		except OSError:
			continue
	return r
# 2026-11-25
# "Short-circuit non-code PreToolUse TDD checks and lazily memoize exemptions":
# https://github.com/dmitry-ai/harness/issues/250
# @used-by :func:`_collect_final_green_violations()`
def _scope_needs_final_full_green(sk: str, st: dict, st_ord: dict, project_root: Path | None, exempt_cache: dict[tuple[str, str], bool]) -> bool:
	last_edit_ord, full_green_ord = (st_ord['last_code_edit'], st_ord['last_full_green'])
	if (not st['any_prod_edit']) or (None is not full_green_ord and (None is last_edit_ord or full_green_ord > last_edit_ord)):
		r = False
	elif None is full_green_ord or (None is not st_ord['last_test_edit'] and st_ord['last_test_edit'] >= full_green_ord):
		r = _has_non_exempt_prod(sk, st_ord, project_root, exempt_cache)
	else:
		r = _has_non_exempt_prod(sk, st_ord, project_root, exempt_cache, min_order=full_green_ord)
	return r
# @used-by :func:`_command_matches_scope()`
def _scopes_overlap(resolved_scopes: list[Path], scope_p: Path, scope_key: str, scope_main_key: str, is_full_cmd: bool) -> bool:
	direct = any(rs.as_posix().lower() == scope_key or rs.is_relative_to(scope_p) or scope_p.is_relative_to(rs) for rs in resolved_scopes)
	return direct or (is_full_cmd and any(_git_main_repo_root(rs).as_posix().lower() == scope_main_key for rs in resolved_scopes))
# @used-by :func:`_apply_command_event()`
def _update_scope_from_test_cmd(sk: str, st: dict, st_ord: dict, ev: dict, step: int, order: tuple[int, int, int], outcome: dict, t_info: dict) -> None:
	# 2026-11-26 "Support parent-issue inheritance and worktree-scoped TDD keys for coding fan-out": https://github.com/dmitry-ai/harness/issues/351
	scope_full = bool(t_info.get('is_full_suite')) or classify_test_command(str(ev.get('cmd') or ''), scope_root=canonical_scope_path(sk))['is_full_suite']
	if outcome.get('is_failure') and 'TEST_WRITTEN' == st['state'] and None is not st_ord['written_test'] and order > st_ord['written_test']:
		st['state'] = 'RED_VERIFIED'
		st['red_step'] = step
		st['red_cmd'] = ev.get('cmd')
	elif outcome.get('is_pass') and None is not st_ord['last_code_edit'] and order > st_ord['last_code_edit']:
		st['cycle_green_step'] = step
		if scope_full:
			st['last_full_green_step'] = step
			st_ord['last_full_green'] = order
# 2026-11-24
# "Decompose tdd_gate.py into modular TDD verification package":
# https://github.com/dmitry-ai/harness/issues/169
# @used-by :func:`agent_tools.completion._tdd_status()`
# @used-by :func:`agent_tools.tdd.enforcement._load_pre_tool_tdd_state()`
# @used-by :meth:`test_background_wait_and_tdd_inheritance.BackgroundWaitAndTddInheritanceTests.test_completed_prior_turn_does_not_bleed_tdd_events_into_unrelated_followup()`
# @used-by :meth:`test_background_wait_and_tdd_inheritance.BackgroundWaitAndTddInheritanceTests.test_unfinished_background_run_command_and_russian_stub_merge_and_preserve_tdd_full_gate()`
# @used-by :meth:`test_code_fanout_gates.CodeFanoutGatesTests.test_missing_transcript_inheritance_and_plain_repo_commit_scope_reset()`
# @used-by :meth:`test_code_fanout_gates.CodeFanoutGatesTests.test_parallel_deleted_worktrees_isolate_tdd_scopes_and_accept_main_full_green()`
# @used-by :meth:`test_diff_executability.DiffExecutabilityTests.test_evaluator_exempts_comment_only_test_edits_in_idle_and_post_green()`
# @used-by :meth:`test_diff_executability_telemetry.DiffExecutabilityTelemetryTests.test_evaluate_tdd_events_records_exempt_edits_without_state_transition()`
# @used-by :meth:`test_failfast_and_schedule_gate.FailFastAndScheduleGateTests.test_tdd_gate_records_non_failfast_full_suite_warning_without_breaking_verified()`
# @used-by :meth:`test_parallel_test_runner.ParallelTestRunnerTests.test_classify_test_command_recognizes_harness_run_tests_full_and_filtered()`
# @used-by :meth:`test_parallel_test_runner.ParallelTestRunnerTests.test_linked_worktree_scope_accepts_full_suite_green_on_main_repo()`
# @used-by :meth:`test_pytest_xdist_runner.PytestXdistRunnerTests.test_tdd_state_machine_rejects_exit_5_red_and_accepts_xdist_full_green()`
# @used-by :meth:`test_tdd_comment_exemption.CommentOnlyExemptionTests.test_evaluator_skips_tdd_red_and_full_gates_for_comment_only_write()`
# @used-by :meth:`test_tdd_decomposition.TddDecompositionTests.test_evaluator_module_behavior_and_parity()`
# @used-by :meth:`test_tdd_fast_path.TddFastPathTests.test_evaluator_lazy_exemption_and_full_green_edge_cases()`
# @used-by :meth:`test_tdd_fast_path.TddFastPathTests.test_evaluator_memoizes_exemption_and_allows_exempt_only_edits()`
# @used-by :meth:`test_tdd_gate.TddGateCoreTests.test_chronological_tdd_state_machine_and_commit_reset()`
# @used-by :meth:`test_tdd_gate.TddGateCoreTests.test_extract_antigravity_tdd_events_handles_compact_and_full_transcripts()`
# @used-by :meth:`test_tdd_mechanical_exemption.MechanicalExemptionTests.test_auditor_and_evaluator_accept_committed_mechanical_diff_and_reject_drift()`
# @used-by :meth:`test_tdd_worktree_and_subagent_trace.TddWorktreeAndSubagentTraceTests.test_combined_git_commit_and_full_test_command_updates_full_green()`
# @used-by :meth:`test_tdd_worktree_and_subagent_trace.TddWorktreeAndSubagentTraceTests.test_subagent_events_sharing_parent_step_preserve_sub_step_order()`
# @used-by :meth:`test_worktree_comment_exemption.WorktreeCommentExemptionTests.test_deleted_sibling_and_nested_worktree_comment_only_commits_are_exempt()`
# @used-by :meth:`test_worktree_comment_exemption.WorktreeCommentExemptionTests.test_deleted_worktree_non_comment_code_commit_remains_blocked()`
# @used-by :mod:`agent_tools.tdd_gate`
# @used-by :mod:`agent_tools.tdd`
def evaluate_tdd_events(events: list[dict], *, require_final_full_green: bool=True, project_root: Path | None=None) -> dict:
	scopes: dict[str, dict] = {}
	orders: dict[str, dict] = {}
	violations: list[str] = []
	failfast_warnings: list[str] = []
	exempt_cache: dict[tuple[str, str], bool] = {}
	for order, _, ev in _order_tdd_events(events):
		kind = ev.get('kind')
		step = order[0]
		if 'file_write' == kind:
			_apply_file_write_event(ev, step, order, scopes, orders, violations, project_root=project_root, exempt_cache=exempt_cache)
		elif 'command' == kind:
			_apply_command_event(ev, step, order, scopes, orders, failfast_warnings)
	if require_final_full_green:
		violations.extend(_collect_final_green_violations(scopes, orders, project_root, exempt_cache))
	r = {'scopes': scopes, 'verified': not violations, 'violations': violations}
	if failfast_warnings:
		r['failfast_warnings'] = failfast_warnings
	return r