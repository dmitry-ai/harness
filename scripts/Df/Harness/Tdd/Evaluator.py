# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from pathlib import Path
from typing import Callable
from Df.Harness.Gate.FailfastGate import FailfastGate
from Df.Harness.Tdd.CodeClassifier import CodeClassifier
from Df.Harness.Tdd.CommandInspector import CommandInspector
from Df.Harness.Tdd.Exemption import Exemption
from Df.Harness.Tdd.WorktreeScope import WorktreeScope
from agent_tools.shell_audit import _split_shell_segments, normalize_host_path
# 2026-11-26 "Move verification gate subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/381
# @used-by :mod:`agent_tools.tdd.evaluator`
class Evaluator:
	# @used-by :func:`agent_tools.tdd.evaluator.evaluate_tdd_events()`
	# @used-by :meth:`Df.Harness.Tdd.Enforcement.Enforcement.__load_pre_tool_tdd_state()`
	# @used-by :meth:`test_code_fanout_gates.CodeFanoutGatesTests.test_antigravity_ps_deleted_worktree_commit_rebase_and_land_green()`
	# @used-by :meth:`test_df_harness_s11_wave2b_tail_cov.DfHarnessS11Wave2bTailCovTests.test_tdd_enforcement_evaluator_events_and_worktree()`
	# @used-by :meth:`test_df_harness_s11_wave2b_tdd.DfHarnessS11Wave2bTddTests.test_tdd_enforcement_evaluator_events_and_guards()`
	# @used-by :meth:`test_df_harness_s11_wave2b_tdd_cov2.DfHarnessS11Wave2bTddCov2Tests.test_evaluator_and_events_extractor_with_bg_tasks()`
	# @used-by :meth:`test_tdd_commit_reset_and_rebase.TddCommitResetAndRebaseTests.test_git_rebase_conflict_allows_resolution_and_enforces_full_green()`
	# @used-by :meth:`test_tdd_commit_reset_and_rebase.TddCommitResetAndRebaseTests.test_git_rebase_conflict_before_any_write_and_with_ps_var_in_pretool_enforcement()`
	# @used-by :meth:`test_tdd_commit_reset_and_rebase.TddCommitResetAndRebaseTests.test_variable_wt_commit_resets_scope_and_blocks_untested_second_commit()`
	# @used-by :meth:`test_tdd_worktree_cmd_scope.TddWorktreeCmdScopeTests.test_deleted_worktree_set_location_red_run_remains_verified()`
	# @used-by :meth:`test_tdd_worktree_land_green.TddWorktreeLandGreenTests.test_evaluator_worktree_land_green_and_compound_soundness()`
	def __init__(self, events: list[dict], *, require_final_full_green: bool=True, project_root: Path | None=None, is_exempt_fn: Callable | None=None) -> None:
		self.__events = events
		self.__require_final_full_green = require_final_full_green
		self.__project_root = project_root
		self.__is_exempt_fn = is_exempt_fn if None is not is_exempt_fn else Exemption.is_write_event_exempt
	# @used-by :func:`agent_tools.tdd.evaluator.evaluate_tdd_events()`
	# @used-by :meth:`Df.Harness.Tdd.Enforcement.Enforcement.__load_pre_tool_tdd_state()`
	# @used-by :meth:`test_code_fanout_gates.CodeFanoutGatesTests.test_antigravity_ps_deleted_worktree_commit_rebase_and_land_green()`
	# @used-by :meth:`test_df_harness_s11_wave2b_tail_cov.DfHarnessS11Wave2bTailCovTests.test_tdd_enforcement_evaluator_events_and_worktree()`
	# @used-by :meth:`test_df_harness_s11_wave2b_tdd.DfHarnessS11Wave2bTddTests.test_tdd_enforcement_evaluator_events_and_guards()`
	# @used-by :meth:`test_df_harness_s11_wave2b_tdd_cov2.DfHarnessS11Wave2bTddCov2Tests.test_evaluator_and_events_extractor_with_bg_tasks()`
	# @used-by :meth:`test_tdd_commit_reset_and_rebase.TddCommitResetAndRebaseTests.test_git_rebase_conflict_allows_resolution_and_enforces_full_green()`
	# @used-by :meth:`test_tdd_commit_reset_and_rebase.TddCommitResetAndRebaseTests.test_git_rebase_conflict_before_any_write_and_with_ps_var_in_pretool_enforcement()`
	# @used-by :meth:`test_tdd_commit_reset_and_rebase.TddCommitResetAndRebaseTests.test_variable_wt_commit_resets_scope_and_blocks_untested_second_commit()`
	# @used-by :meth:`test_tdd_worktree_cmd_scope.TddWorktreeCmdScopeTests.test_deleted_worktree_set_location_red_run_remains_verified()`
	# @used-by :meth:`test_tdd_worktree_land_green.TddWorktreeLandGreenTests.test_evaluator_worktree_land_green_and_compound_soundness()`
	def evaluate(self) -> dict:
		scopes: dict[str, dict] = {}
		orders: dict[str, dict] = {}
		violations: list[str] = []
		failfast_warnings: list[str] = []
		exempt_cache: dict[tuple[str, str], bool] = {}
		for order, _, ev in Evaluator.__order_tdd_events(self.__events):
			kind = ev.get('kind')
			step = order[0]
			if 'file_write' == kind:
				self.__apply_file_write_event(ev, step, order, scopes, orders, violations, exempt_cache)
			elif 'command' == kind:
				Evaluator.__apply_command_event(ev, step, order, scopes, orders, failfast_warnings)
		if self.__require_final_full_green:
			violations.extend(self.__collect_final_green_violations(scopes, orders, exempt_cache))
		r = {'scopes': scopes, 'verified': not violations, 'violations': violations}
		if failfast_warnings:
			r['failfast_warnings'] = failfast_warnings
		return r
	# @used-by :meth:`Evaluator.evaluate()`
	def __apply_file_write_event(self, ev: dict, step: int, order: tuple[int, int, int], scopes: dict[str, dict], orders: dict[str, dict], violations: list[str], exempt_cache: dict[tuple[str, str], bool]) -> None:
		cls = ev.get('classification')
		fpath = str(ev.get('path') or '')
		scope_str = WorktreeScope.resolve_key(fpath, str(ev.get('scope') or ''))
		if 'test' == cls and scope_str:
			self.__apply_test_file_event(fpath, scope_str, step, order, scopes, orders, exempt_cache)
		elif 'production' == cls and scope_str:
			self.__apply_prod_file_event(fpath, scope_str, step, order, scopes, orders, violations, exempt_cache)
	# 2026-11-28 "Reset TDD cycle on variable worktree commits and support rebase conflict state": https://github.com/dmitry-ai/harness/issues/441
	# @used-by :meth:`Evaluator.__apply_file_write_event()`
	def __apply_prod_file_event(self, fpath: str, scope_str: str, step: int, order: tuple[int, int, int], scopes: dict[str, dict], orders: dict[str, dict], violations: list[str], exempt_cache: dict[tuple[str, str], bool]) -> None:
		existing = scopes.get(scope_str)
		if None is not existing and existing['state'] in ('RED_VERIFIED', 'GREEN_IMPLEMENTING', 'REBASE_CONFLICT'):
			st, st_ord = (existing, orders[scope_str])
			st_ord['unverified_prod_writes'].append((fpath, order))
			Evaluator.__apply_prod_write(st, st_ord, fpath, step, order, violations)
		elif self.__is_exempt_cached(fpath, scope_str, exempt_cache):
			Evaluator.__record_exempt_edit(scopes, orders, scope_str, fpath, step, 'production')
		else:
			st, st_ord = Evaluator.__ensure_scope(scopes, orders, scope_str)
			st_ord['last_non_exempt_prod'] = order
			Evaluator.__apply_prod_write(st, st_ord, fpath, step, order, violations)
	# @used-by :meth:`Evaluator.__apply_file_write_event()`
	def __apply_test_file_event(self, fpath: str, scope_str: str, step: int, order: tuple[int, int, int], scopes: dict[str, dict], orders: dict[str, dict], exempt_cache: dict[tuple[str, str], bool]) -> None:
		if self.__require_final_full_green and self.__is_exempt_cached(fpath, scope_str, exempt_cache):
			Evaluator.__record_exempt_edit(scopes, orders, scope_str, fpath, step, 'test')
		else:
			st, st_ord = Evaluator.__ensure_scope(scopes, orders, scope_str)
			Evaluator.__apply_test_write(st, st_ord, fpath, step, order)
	# @used-by :meth:`Evaluator.evaluate()`
	def __collect_final_green_violations(self, scopes: dict[str, dict], orders: dict[str, dict], exempt_cache: dict[tuple[str, str], bool]) -> list[str]:
		r: list[str] = []
		for sk, st in sorted(scopes.items()):
			if self.__scope_needs_final_full_green(sk, st, orders[sk], exempt_cache):
				r.append(f"EXEC-2 TDD-FULL-GATE: Repository \"{sk}\" has production code edits (last edit at step {st['last_code_edit_step']}) without a subsequent passing (GREEN) full test suite run. Run the full test suite and verify all tests pass.")
		return r
	# @used-by :meth:`Evaluator.__scope_needs_final_full_green()`
	def __has_non_exempt_prod(self, sk: str, st_ord: dict, exempt_cache: dict[tuple[str, str], bool], *, min_order: tuple[int, int, int] | None=None) -> bool:
		known = st_ord['last_non_exempt_prod']
		if None is not known and (None is min_order or known >= min_order):
			r = True
		else:
			r = any((not self.__is_exempt_cached(fp, sk, exempt_cache) for fp, ord_ in st_ord['unverified_prod_writes'] if None is min_order or ord_ >= min_order))
		return r
	# @used-by :meth:`Evaluator.__apply_prod_file_event()`
	# @used-by :meth:`Evaluator.__apply_test_file_event()`
	# @used-by :meth:`Evaluator.__has_non_exempt_prod()`
	def __is_exempt_cached(self, fpath: str, scope_str: str, cache: dict[tuple[str, str], bool]) -> bool:
		key = (scope_str, fpath)
		if key not in cache:
			cache[key] = self.__is_exempt_fn(fpath, str(WorktreeScope.canonical_scope_path(scope_str)), project_root=self.__project_root)
		return cache[key]
	# @used-by :meth:`Evaluator.__collect_final_green_violations()`
	def __scope_needs_final_full_green(self, sk: str, st: dict, st_ord: dict, exempt_cache: dict[tuple[str, str], bool]) -> bool:
		last_edit_ord, full_green_ord = (st_ord['last_code_edit'], st_ord['last_full_green'])
		if (not st['any_prod_edit']) or (None is not full_green_ord and (None is last_edit_ord or full_green_ord > last_edit_ord)):
			r = False
		elif None is full_green_ord or (None is not st_ord['last_test_edit'] and st_ord['last_test_edit'] >= full_green_ord):
			r = self.__has_non_exempt_prod(sk, st_ord, exempt_cache)
		else:
			r = self.__has_non_exempt_prod(sk, st_ord, exempt_cache, min_order=full_green_ord)
		return r
	# 2026-11-28 "Reset TDD cycle on variable worktree commits and support rebase conflict state": https://github.com/dmitry-ai/harness/issues/441
	# @used-by :meth:`Evaluator.evaluate()`
	@staticmethod
	def __apply_command_event(ev: dict, step: int, order: tuple[int, int, int], scopes: dict[str, dict], orders: dict[str, dict], failfast_warnings: list[str]) -> None:
		outcome = ev.get('outcome') or {}
		if ev.get('is_git_commit') and outcome.get('exit_code') in (0, None):
			Evaluator.__apply_commit_reset(ev.get('commit_scope'), scopes, orders, ev=ev)
		if ev.get('git_rebase_action'):
			Evaluator.__apply_rebase_event(ev, outcome, scopes, orders)
		t_info = ev.get('test_info') or {}
		if t_info.get('is_test_cmd') and (not t_info.get('rigged_failure')):
			if t_info.get('is_full_suite'):
				Evaluator.__collect_failfast_warnings(str(ev.get('cmd') or ''), step, failfast_warnings)
			for sk, st in scopes.items():
				if Evaluator.command_matches_scope(ev, sk, set(st['written_tests'])):
					Evaluator.__update_scope_from_test_cmd(sk, st, orders[sk], ev, step, order, outcome, t_info)
	# @used-by :meth:`Evaluator.__apply_command_event()`
	@staticmethod
	def __apply_commit_reset(c_scope: str | None, scopes: dict[str, dict], orders: dict[str, dict], *, ev: dict | None=None) -> None:
		for sk, st in scopes.items():
			if WorktreeScope.scope_matches_commit(sk, c_scope, ev):
				st['state'] = 'IDLE'
				st['written_test_step'] = None
				st['red_step'] = None
				st['red_cmd'] = None
				st['cycle_had_prod_edit'] = False
				st['cycle_green_step'] = None
				orders[sk]['written_test'] = None
	# 2026-11-28 "Reset TDD cycle on variable worktree commits and support rebase conflict state": https://github.com/dmitry-ai/harness/issues/441
	# @used-by :meth:`Evaluator.__apply_prod_file_event()`
	@staticmethod
	def __apply_prod_write(st: dict, st_ord: dict, fpath: str, step: int, order: tuple[int, int, int], violations: list[str]) -> None:
		st['any_prod_edit'] = True
		if fpath not in st['touched_prod_files']:
			st['touched_prod_files'].append(fpath)
		if st['state'] in ('RED_VERIFIED', 'GREEN_IMPLEMENTING'):
			st['state'] = 'GREEN_IMPLEMENTING'
		elif 'REBASE_CONFLICT' != st['state']:
			msg = f'EXEC-2 TDD-RED-GATE: Production code "{fpath}" edited at step {step} after writing test(s), but no failing (RED) test run was observed after the test edit. Run the new test and observe it fail before writing production code.' if 'TEST_WRITTEN' == st['state'] else f'EXEC-2 TDD-RED-GATE: Production code "{fpath}" edited at step {step} without first writing a test and observing it fail (RED).'
			violations.append(msg)
		st['cycle_had_prod_edit'] = True
		st['last_prod_edit_step'] = step
		st['last_code_edit_step'] = step
		st_ord['last_code_edit'] = order
	# 2026-11-28 "Reset TDD cycle on variable worktree commits and support rebase conflict state": https://github.com/dmitry-ai/harness/issues/441
	# @used-by :meth:`Evaluator.__apply_command_event()`
	@staticmethod
	def __apply_rebase_event(ev: dict, outcome: dict, scopes: dict[str, dict], orders: dict[str, dict]) -> None:
		act, r_scope, has_conf = (ev.get('git_rebase_action'), ev.get('rebase_scope'), bool(outcome.get('has_rebase_conflict')))
		if has_conf and act in ('start', 'continue', 'skip'):
			Evaluator.__enter_rebase_conflict(ev, r_scope, scopes, orders)
		elif (not has_conf) and act in ('continue', 'abort', 'skip') and outcome.get('exit_code') in (0, None):
			Evaluator.__exit_rebase_conflict(ev, r_scope, scopes)
	# @used-by :meth:`Evaluator.__apply_test_file_event()`
	@staticmethod
	def __apply_test_write(st: dict, st_ord: dict, fpath: str, step: int, order: tuple[int, int, int]) -> None:
		if fpath not in st['written_tests']:
			st['written_tests'].append(fpath)
		if st['state'] in ('IDLE', 'TEST_WRITTEN'):
			st['state'] = 'TEST_WRITTEN'
			st['written_test_step'] = step
			st_ord['written_test'] = order
		st['last_code_edit_step'] = step
		st_ord['last_code_edit'] = order
		st_ord['last_test_edit'] = order
	# @used-by :meth:`Evaluator.__apply_command_event()`
	@staticmethod
	def __collect_failfast_warnings(cmd_text: str, step: int, failfast_warnings: list[str]) -> None:
		for seg in _split_shell_segments(cmd_text):
			miss = FailfastGate.missing_failfast_flag(seg.strip())
			if None is not miss:
				warn = f'EXEC-2 fail-fast advisory: Full-suite command at step {step} ({miss[0]}) omitted "{miss[1]}"; prefer fail-fast or harness.py run-tests.'
				if warn not in failfast_warnings:
					failfast_warnings.append(warn)
				break
	# @used-by :meth:`Evaluator.command_matches_scope()`
	@staticmethod
	def __cwd_matches_scope(cwd_p: Path | None, scope_p: Path, scope_key: str, scope_main_key: str, is_full_cmd: bool) -> bool:
		r = False
		if None is not cwd_p:
			cwd_scope = CodeClassifier.resolve_code_scope(cwd_p)
			direct = cwd_scope.as_posix().lower() == scope_key or cwd_p.is_relative_to(scope_p) or scope_p.is_relative_to(cwd_p)
			r = direct or (is_full_cmd and Evaluator.git_main_repo_root(cwd_scope).as_posix().lower() == scope_main_key)
		return r
	# @used-by :meth:`Evaluator.__apply_prod_file_event()`
	# @used-by :meth:`Evaluator.__apply_test_file_event()`
	# @used-by :meth:`Evaluator.__enter_rebase_conflict()`
	# @used-by :meth:`Evaluator.__record_exempt_edit()`
	@staticmethod
	def __ensure_scope(scopes: dict[str, dict], orders: dict[str, dict], scope_str: str) -> tuple[dict, dict]:
		st = scopes.setdefault(scope_str, {
			'any_prod_edit': False, 'cycle_green_step': None, 'cycle_had_prod_edit': False, 'exempt_edits': [],
			'last_code_edit_step': None, 'last_full_green_step': None, 'last_prod_edit_step': None, 'red_cmd': None,
			'red_step': None, 'state': 'IDLE', 'touched_prod_files': [], 'written_test_step': None, 'written_tests': [],
		})
		st_ord = orders.setdefault(scope_str, {'last_code_edit': None, 'last_full_green': None, 'last_non_exempt_prod': None, 'last_test_edit': None, 'unverified_prod_writes': [], 'written_test': None})
		return (st, st_ord)
	# 2026-11-28 "Reset TDD cycle on variable worktree commits and support rebase conflict state": https://github.com/dmitry-ai/harness/issues/441
	# @used-by :meth:`Evaluator.__apply_rebase_event()`
	@staticmethod
	def __enter_rebase_conflict(ev: dict, r_scope: str | None, scopes: dict[str, dict], orders: dict[str, dict]) -> None:
		matched = [st for sk, st in scopes.items() if WorktreeScope.scope_matches_commit(sk, r_scope, ev)]
		if not matched:
			sk = WorktreeScope.resolve_command_scope_key(r_scope, ev)
			if sk:
				matched = [Evaluator.__ensure_scope(scopes, orders, sk)[0]]
		for st in matched:
			st['state'] = 'REBASE_CONFLICT'
	# 2026-11-28 "Reset TDD cycle on variable worktree commits and support rebase conflict state": https://github.com/dmitry-ai/harness/issues/441
	# @used-by :meth:`Evaluator.__apply_rebase_event()`
	@staticmethod
	def __exit_rebase_conflict(ev: dict, r_scope: str | None, scopes: dict[str, dict]) -> None:
		for sk, st in scopes.items():
			if 'REBASE_CONFLICT' == st['state'] and WorktreeScope.scope_matches_commit(sk, r_scope, ev):
				st['state'] = 'IDLE'
	# @used-by :meth:`Evaluator.evaluate()`
	@staticmethod
	def __order_tdd_events(events: list[dict] | tuple[dict, ...] | None) -> list[tuple[tuple[int, int, int], int, dict]]:
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
	# @used-by :meth:`Evaluator.__apply_prod_file_event()`
	# @used-by :meth:`Evaluator.__apply_test_file_event()`
	@staticmethod
	def __record_exempt_edit(scopes: dict[str, dict], orders: dict[str, dict], scope_str: str, fpath: str, step: int, cls: str) -> None:
		st, _ = Evaluator.__ensure_scope(scopes, orders, scope_str)
		entry = {'classification': cls, 'path': fpath, 'step': step}
		if entry not in st['exempt_edits']:
			st['exempt_edits'].append(entry)
	# 2026-11-27 "Recognize passing worktree-land full test runs in TDD-FULL-GATE": https://github.com/dmitry-ai/harness/issues/398
	# @used-by :meth:`Evaluator.command_matches_scope()`
	@staticmethod
	def __resolve_event_target_scopes(targets: list[str], cwd_p: Path | None) -> list[Path]:
		r: list[Path] = []
		for tp in targets:
			try:
				cand = normalize_host_path(tp)
				full = cand.resolve() if cand.is_absolute() else ((cwd_p / cand).resolve() if cwd_p else cand.resolve())
				probe = full / '_wt_scope_probe' if (not full.exists()) and None is not WorktreeScope.extract_worktree_scope_id(full) else full
				r.append(CodeClassifier.resolve_code_scope(probe))
			except OSError:
				continue
		return r
	# 2026-11-27 "Recognize passing worktree-land full test runs in TDD-FULL-GATE": https://github.com/dmitry-ai/harness/issues/398
	# @used-by :meth:`Evaluator.__update_scope_from_test_cmd()`
	@staticmethod
	def __scope_is_ordinary_full(sk: str, ev: dict, t_info: dict) -> bool:
		has_land = bool(t_info.get('has_worktree_land'))
		has_ord = bool(t_info.get('has_ordinary_test', not t_info.get('worktree_land_only')))
		r = bool(t_info['ordinary_full_suite']) if 'ordinary_full_suite' in t_info else ((not has_land) and bool(t_info.get('is_full_suite')))
		if has_ord and (not r):
			r = bool(CommandInspector(str(ev.get('cmd') or ''), scope_root=WorktreeScope.canonical_scope_path(sk)).classify_test_command().get('ordinary_full_suite'))
		return r
	# @used-by :meth:`Evaluator.command_matches_scope()`
	@staticmethod
	def __scopes_overlap(resolved_scopes: list[Path], scope_p: Path, scope_key: str, scope_main_key: str, is_full_cmd: bool) -> bool:
		direct = any((rs.as_posix().lower() == scope_key or rs.is_relative_to(scope_p) or scope_p.is_relative_to(rs) for rs in resolved_scopes))
		return direct or (is_full_cmd and any((Evaluator.git_main_repo_root(rs).as_posix().lower() == scope_main_key for rs in resolved_scopes)))
	# 2026-11-27 "Recognize passing worktree-land full test runs in TDD-FULL-GATE": https://github.com/dmitry-ai/harness/issues/398
	# @used-by :meth:`Evaluator.__apply_command_event()`
	@staticmethod
	def __update_scope_from_test_cmd(sk: str, st: dict, st_ord: dict, ev: dict, step: int, order: tuple[int, int, int], outcome: dict, t_info: dict) -> None:
		has_land = bool(t_info.get('has_worktree_land'))
		wt_green = has_land and bool(outcome.get('worktree_land_full_green'))
		red_blocked = bool(t_info.get('worktree_land_only')) or bool(outcome.get('worktree_land_failed')) or (has_land and (not outcome.get('has_fail_log')))
		if (not red_blocked) and outcome.get('is_failure') and 'TEST_WRITTEN' == st['state'] and None is not st_ord['written_test'] and order > st_ord['written_test']:
			st['state'] = 'RED_VERIFIED'
			st['red_step'] = step
			st['red_cmd'] = ev.get('cmd')
		elif (wt_green or ((not t_info.get('worktree_land_only')) and outcome.get('is_pass'))) and None is not st_ord['last_code_edit'] and order > st_ord['last_code_edit']:
			st['cycle_green_step'] = step
			if wt_green or Evaluator.__scope_is_ordinary_full(sk, ev, t_info):
				st['last_full_green_step'] = step
				st_ord['last_full_green'] = order
	# 2026-11-27 "Recognize passing worktree-land full test runs in TDD-FULL-GATE": https://github.com/dmitry-ai/harness/issues/398
	# @used-by :func:`agent_tools.tdd.evaluator._command_matches_scope()`
	# @used-by :meth:`Evaluator.__apply_command_event()`
	@staticmethod
	def command_matches_scope(event: dict, scope_str: str, written_test_files: set[str]) -> bool:
		t_info = event.get('test_info') or {}
		outcome = event.get('outcome') or {}
		is_full_cmd = bool(t_info.get('is_full_suite'))
		if False is WorktreeScope.worktree_command_matches(event, scope_str, is_full_cmd):
			r = False
		else:
			scope_p = WorktreeScope.canonical_scope_path(scope_str)
			scope_key = scope_p.as_posix().lower()
			scope_main_key = Evaluator.git_main_repo_root(scope_p).as_posix().lower()
			cmd_norm = CodeClassifier.norm_posix(str(event.get('cmd') or '')).lower()
			cwd_raw = event.get('cwd')
			cwd_p = Path(cwd_raw).resolve() if cwd_raw else None
			extra_repo = outcome.get('worktree_land_main_repo') if outcome.get('worktree_land_full_green') else None
			targets = list(t_info.get('target_paths') or ()) + ([str(extra_repo)] if extra_repo else [])
			resolved_scopes = Evaluator.__resolve_event_target_scopes(targets, cwd_p)
			r = Evaluator.__scopes_overlap(resolved_scopes, scope_p, scope_key, scope_main_key, is_full_cmd) or any((Path(tf).name.lower() in cmd_norm or Path(tf).stem.lower() in cmd_norm for tf in written_test_files)) or scope_key in cmd_norm or ((not resolved_scopes) and Evaluator.__cwd_matches_scope(cwd_p, scope_p, scope_key, scope_main_key, is_full_cmd))
		return r
	# @used-by :func:`agent_tools.tdd.evaluator._git_main_repo_root()`
	# @used-by :meth:`Evaluator.__cwd_matches_scope()`
	# @used-by :meth:`Evaluator.__scopes_overlap()`
	# @used-by :meth:`Evaluator.command_matches_scope()`
	# @used-by :meth:`test_df_harness_s11_wave2b_tdd_cov2.DfHarnessS11Wave2bTddCov2Tests.test_evaluator_and_events_extractor_with_bg_tasks()`
	@staticmethod
	def git_main_repo_root(repo: Path) -> Path:
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
