# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from pathlib import Path
from Df.Harness.Tdd.CodeClassifier import CodeClassifier
from agent_tools.shell_audit import normalize_host_path
import re
# 2026-11-26 "Move verification gate subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/381
# @used-by :mod:`agent_tools.tdd.worktree_scope`
class WorktreeScope:
	# 2026-11-27 "Extract worktree scope IDs from shell command paths in WorktreeScope": https://github.com/dmitry-ai/harness/issues/397
	__CMD_TOKEN_RE = re.compile(r'"([^"]+)"|\'([^\']+)\'|([^\s;|&]+)')
	__GIT_C_WT_RE = re.compile(r'(?:-C|--work-tree)(?:=|\s+)(?:"([^"]+)"|\'([^\']+)\'|(\S+))')
	# 2026-11-28 "Reset TDD cycle on variable worktree commits and support rebase conflict state": https://github.com/dmitry-ai/harness/issues/441
	__PS_VAR_ASSIGN_RE = re.compile(r'(\$[A-Za-z_][A-Za-z0-9_]*)\s*=\s*(?:"([^"]+)"|\'([^\']+)\')')
	__RUNNER_SCRIPT_NAMES = frozenset({'df_github_issue.py', 'harness.py', 'safe_commit.py', 'upwork_project.py'})
	__WT_KEY_SEP = '::wt:'
	# 2026-11-28 "Reset TDD cycle on variable worktree commits and support rebase conflict state": https://github.com/dmitry-ai/harness/issues/441
	# @used-by :meth:`WorktreeScope.scope_matches_commit()`
	@staticmethod
	def __commit_worktree_id(commit_scope: str | None, event: dict | None) -> str | None:
		r = WorktreeScope.extract_worktree_scope_id(commit_scope)
		if None is r and isinstance(event, dict):
			r = WorktreeScope.extract_worktree_scope_id(event.get('cwd'))
			if None is r:
				raw_cmd = str(event.get('cmd') or '')
				r = WorktreeScope.__first_git_flag_wt(WorktreeScope.expand_ps_var_paths(raw_cmd))
				if None is r:
					wts = WorktreeScope.__extract_cmd_worktree_ids(raw_cmd)
					r = next(iter(wts)) if 1 == len(wts) else None
		return r
	# 2026-11-28 "Reset TDD cycle on variable worktree commits and support rebase conflict state": https://github.com/dmitry-ai/harness/issues/441
	# @used-by :meth:`WorktreeScope.resolve_command_scope_key()`
	@staticmethod
	def __first_git_flag_path(expanded_cmd: str) -> str | None:
		r: str | None = None
		for match in WorktreeScope.__GIT_C_WT_RE.finditer(expanded_cmd):
			raw = next((g for g in match.groups() if g), '')
			if raw:
				r = raw
				break
		return r
	# 2026-11-28 "Reset TDD cycle on variable worktree commits and support rebase conflict state": https://github.com/dmitry-ai/harness/issues/441
	# @used-by :meth:`WorktreeScope.__commit_worktree_id()`
	@staticmethod
	def __first_git_flag_wt(expanded_cmd: str) -> str | None:
		r: str | None = None
		for match in WorktreeScope.__GIT_C_WT_RE.finditer(expanded_cmd):
			raw = next((g for g in match.groups() if g), '')
			wt = WorktreeScope.extract_worktree_scope_id(raw)
			if None is not wt:
				r = wt
				break
		return r
	# 2026-11-27 "Extract worktree scope IDs from shell command paths in WorktreeScope": https://github.com/dmitry-ai/harness/issues/397
	# @used-by :meth:`WorktreeScope.__commit_worktree_id()`
	# @used-by :meth:`WorktreeScope.extract_command_worktree_ids()`
	@staticmethod
	def __extract_cmd_worktree_ids(cmd: str) -> set[str]:
		found: set[str] = set()
		for match in WorktreeScope.__CMD_TOKEN_RE.finditer(cmd):
			tok = next((g for g in match.groups() if g), '')
			if '=' in tok and (not tok.startswith('-')):
				rhs = tok.split('=', 1)[1]
				if '/' in rhs or '\\' in rhs:
					tok = rhs
			if tok and Path(tok).name.lower() not in WorktreeScope.__RUNNER_SCRIPT_NAMES:
				wt = WorktreeScope.extract_worktree_scope_id(tok)
				if None is not wt:
					found.add(wt.lower())
		return found
	# @used-by :meth:`WorktreeScope.scope_matches_commit()`
	@staticmethod
	def __norm_lower(path: Path) -> str:
		return path.resolve().as_posix().lower()
	# @used-by :func:`agent_tools.tdd.worktree_scope.canonical_scope_path()`
	# @used-by :meth:`Df.Harness.Tdd.Evaluator.Evaluator.__is_exempt_cached()`
	# @used-by :meth:`Df.Harness.Tdd.Evaluator.Evaluator.__scope_is_ordinary_full()`
	# @used-by :meth:`Df.Harness.Tdd.Evaluator.Evaluator.command_matches_scope()`
	# @used-by :meth:`test_df_harness_s11_wave2b_tdd_cov2.DfHarnessS11Wave2bTddCov2Tests.test_outcome_service_substantive_and_worktree_scope()`
	@staticmethod
	def canonical_scope_path(scope_key: str) -> Path:
		base, wt_id = WorktreeScope.split_key(scope_key)
		return CodeClassifier.resolve_code_scope(base / '_wt_scope_probe') if (not base.exists()) and None is not wt_id else base
	# 2026-11-28 "Reset TDD cycle on variable worktree commits and support rebase conflict state": https://github.com/dmitry-ai/harness/issues/441
	# @used-by :meth:`Df.Harness.Tdd.EventsExtractor.EventsExtractor.is_git_rebase_command()`
	# @used-by :meth:`WorktreeScope.__commit_worktree_id()`
	# @used-by :meth:`WorktreeScope.resolve_command_scope_key()`
	@staticmethod
	def expand_ps_var_paths(cmd: str) -> str:
		r = str(cmd or '')
		if '$' in r:
			pairs = {m.group(1).lower(): (m.group(2) or m.group(3) or '') for m in WorktreeScope.__PS_VAR_ASSIGN_RE.finditer(r)}
			for name, val in sorted(pairs.items(), key=lambda it: -len(it[0])):
				if val:
					r = re.sub(rf'(?<![A-Za-z0-9_]){re.escape(name)}(?![A-Za-z0-9_])(?!\s*=)', lambda _, v=val: f'"{v}"', r, flags=re.IGNORECASE)
		return r
	# 2026-11-27 "Extract worktree scope IDs from shell command paths in WorktreeScope": https://github.com/dmitry-ai/harness/issues/397
	# @used-by :func:`agent_tools.tdd.worktree_scope.extract_command_worktree_ids()`
	# @used-by :meth:`WorktreeScope.worktree_command_matches()`
	# @used-by :meth:`test_tdd_worktree_cmd_scope.TddWorktreeCmdScopeTests.test_deleted_worktree_set_location_red_run_remains_verified()`
	# @used-by :meth:`test_tdd_worktree_cmd_scope.TddWorktreeCmdScopeTests.test_runner_script_worktree_ignored_while_var_assignment_and_cd_extracted()`
	@staticmethod
	def extract_command_worktree_ids(event: dict) -> set[str]:
		found: set[str] = set()
		cwd_wt = WorktreeScope.extract_worktree_scope_id(event.get('cwd'))
		if None is not cwd_wt:
			found.add(cwd_wt.lower())
		for tp in (event.get('test_info') or {}).get('target_paths') or ():
			if Path(str(tp)).name.lower() in WorktreeScope.__RUNNER_SCRIPT_NAMES:
				continue
			tp_wt = WorktreeScope.extract_worktree_scope_id(tp)
			if None is not tp_wt:
				found.add(tp_wt.lower())
		found.update(WorktreeScope.__extract_cmd_worktree_ids(str(event.get('cmd') or '')))
		return found
	# @used-by :func:`agent_tools.tdd.worktree_scope.extract_worktree_scope_id()`
	# @used-by :meth:`Df.Harness.Tdd.Evaluator.Evaluator.__resolve_event_target_scopes()`
	# @used-by :meth:`WorktreeScope.__commit_worktree_id()`
	# @used-by :meth:`WorktreeScope.__extract_cmd_worktree_ids()`
	# @used-by :meth:`WorktreeScope.__first_git_flag_wt()`
	# @used-by :meth:`WorktreeScope.extract_command_worktree_ids()`
	# @used-by :meth:`WorktreeScope.resolve_command_scope_key()`
	# @used-by :meth:`WorktreeScope.resolve_key()`
	# @used-by :meth:`WorktreeScope.split_key()`
	@staticmethod
	def extract_worktree_scope_id(path: str | Path | None) -> str | None:
		r: str | None = None
		if path:
			parts = Path(str(path)).parts
			for idx in range(len(parts) - 3):
				if ('\ua616', 'data', 'worktrees') == (parts[idx], parts[idx + 1].lower(), parts[idx + 2].lower()) and parts[idx + 3].strip():
					r = parts[idx + 3].strip()
					break
		return r
	# 2026-11-28 "Reset TDD cycle on variable worktree commits and support rebase conflict state": https://github.com/dmitry-ai/harness/issues/441
	# @used-by :meth:`Df.Harness.Tdd.Evaluator.Evaluator.__enter_rebase_conflict()`
	@staticmethod
	def resolve_command_scope_key(raw_scope: str | Path | None, event: dict | None) -> str | None:
		expanded = WorktreeScope.expand_ps_var_paths(str((event or {}).get('cmd') or ''))
		raw_p = raw_scope or WorktreeScope.__first_git_flag_path(expanded) or (event or {}).get('cwd')
		r: str | None = None
		if raw_p:
			try:
				cwd_raw = (event or {}).get('cwd')
				cand = normalize_host_path(raw_p)
				full = cand.resolve() if cand.is_absolute() else ((Path(cwd_raw).resolve() / cand).resolve() if cwd_raw else cand.resolve())
				probe = full / '_wt_scope_probe' if (not full.exists()) and None is not WorktreeScope.extract_worktree_scope_id(full) else full
				r = WorktreeScope.resolve_key(full, CodeClassifier.resolve_code_scope(probe))
			except OSError:
				r = None
		return r
	# @used-by :func:`agent_tools.tdd.worktree_scope.resolve_tdd_scope_key()`
	# @used-by :meth:`Df.Harness.Tdd.Enforcement.Enforcement.__eval_pre_code_write()`
	# @used-by :meth:`Df.Harness.Tdd.Enforcement.Enforcement.__eval_shell_prod_writes()`
	# @used-by :meth:`Df.Harness.Tdd.Evaluator.Evaluator.__apply_file_write_event()`
	# @used-by :meth:`WorktreeScope.resolve_command_scope_key()`
	# @used-by :meth:`test_df_harness_s11_wave2b_tdd.DfHarnessS11Wave2bTddTests.test_tdd_enforcement_evaluator_events_and_guards()`
	@staticmethod
	def resolve_key(path: str | Path, scope: str | Path) -> str:
		scope_s = str(scope or '')
		if (not scope_s) or WorktreeScope.__WT_KEY_SEP in scope_s:
			r = scope_s
		else:
			wt_id = WorktreeScope.extract_worktree_scope_id(path)
			scope_wt = WorktreeScope.extract_worktree_scope_id(scope_s)
			r = f'{scope_s}{WorktreeScope.__WT_KEY_SEP}{wt_id}' if None is not wt_id and (None is scope_wt or scope_wt.lower() != wt_id.lower()) else scope_s
		return r
	# @used-by :func:`agent_tools.tdd.worktree_scope.scope_matches_commit()`
	# @used-by :meth:`Df.Harness.Tdd.Evaluator.Evaluator.__apply_commit_reset()`
	# @used-by :meth:`Df.Harness.Tdd.Evaluator.Evaluator.__enter_rebase_conflict()`
	# @used-by :meth:`Df.Harness.Tdd.Evaluator.Evaluator.__exit_rebase_conflict()`
	# @used-by :meth:`test_df_harness_s11_wave2b_tail_cov.DfHarnessS11Wave2bTailCovTests.test_tdd_enforcement_evaluator_events_and_worktree()`
	# @used-by :meth:`test_df_harness_s11_wave2b_tdd_cov2.DfHarnessS11Wave2bTddCov2Tests.test_outcome_service_substantive_and_worktree_scope()`
	# @used-by :meth:`test_tdd_commit_reset_and_rebase.TddCommitResetAndRebaseTests.test_variable_wt_commit_resets_scope_and_blocks_untested_second_commit()`
	@staticmethod
	def scope_matches_commit(scope_key: str, commit_scope: str | None, event: dict | None=None) -> bool:
		base, sk_wt = WorktreeScope.split_key(scope_key)
		c_wt = WorktreeScope.__commit_worktree_id(commit_scope, event)
		if None is not c_wt:
			r = None is not sk_wt and c_wt.lower() == sk_wt.lower()
		elif None is commit_scope:
			r = True
		elif WorktreeScope.__WT_KEY_SEP in scope_key:
			r = False
		else:
			r = WorktreeScope.__norm_lower(base) == WorktreeScope.__norm_lower(Path(commit_scope))
		return r
	# @used-by :func:`agent_tools.tdd.worktree_scope.split_tdd_scope_key()`
	# @used-by :meth:`WorktreeScope.canonical_scope_path()`
	# @used-by :meth:`WorktreeScope.scope_matches_commit()`
	# @used-by :meth:`WorktreeScope.worktree_command_matches()`
	# @used-by :meth:`test_df_harness_s11_wave2b_tdd_cov2.DfHarnessS11Wave2bTddCov2Tests.test_outcome_service_substantive_and_worktree_scope()`
	@staticmethod
	def split_key(scope_key: str) -> tuple[Path, str | None]:
		if WorktreeScope.__WT_KEY_SEP in scope_key:
			raw_base, raw_wt = scope_key.rsplit(WorktreeScope.__WT_KEY_SEP, 1)
			r: tuple[Path, str | None] = (Path(raw_base).resolve(), raw_wt or None)
		else:
			p = Path(scope_key).resolve()
			r = (p, WorktreeScope.extract_worktree_scope_id(p))
		return r
	# @used-by :func:`agent_tools.tdd.worktree_scope.worktree_command_matches()`
	# @used-by :meth:`Df.Harness.Tdd.Evaluator.Evaluator.command_matches_scope()`
	# @used-by :meth:`test_df_harness_s11_wave2b_tdd_cov2.DfHarnessS11Wave2bTddCov2Tests.test_outcome_service_substantive_and_worktree_scope()`
	@staticmethod
	def worktree_command_matches(event: dict, scope_key: str, is_full_cmd: bool) -> bool | None:
		_, sk_wt = WorktreeScope.split_key(scope_key)
		cmd_wts = WorktreeScope.extract_command_worktree_ids(event)
		if None is sk_wt:
			r: bool | None = False if cmd_wts else None
		elif cmd_wts:
			r = None if sk_wt.lower() in cmd_wts else False
		else:
			r = False if WorktreeScope.__WT_KEY_SEP in scope_key and (not is_full_cmd) else None
		return r
