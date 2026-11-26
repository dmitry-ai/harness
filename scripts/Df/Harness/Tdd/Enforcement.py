# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from pathlib import Path
from typing import Callable
from Df.Core.lib.git import df_git_read_text
from Df.Harness.Tdd.CodeClassifier import CodeClassifier
from Df.Harness.Tdd.CommandInspector import CommandInspector
from Df.Harness.Tdd.Evaluator import Evaluator
from Df.Harness.Tdd.EventsExtractor import EventsExtractor
from Df.Harness.Tdd.Exemption import Exemption
from Df.Harness.Tdd.MechanicalExemption import MechanicalExemption
from Df.Harness.Tdd.RatchetGuard import RatchetGuard
from Df.Harness.Tdd.ServiceExempt import ServiceExempt
from Df.Harness.Tdd.SubstantiveTestChecker import SubstantiveTestChecker
from Df.Harness.Tdd.WorktreeScope import WorktreeScope
from agent_tools.shell_audit import _GITHUB_ISSUE_URL_RE, normalize_host_path
import difflib
# 2026-11-26 "Move verification gate subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/381
# @used-by :mod:`agent_tools.tdd.enforcement`
class Enforcement:
	__HEAD_TEXT_CACHE: dict[tuple[str, str, str], str | None] = {}
	# @used-by :func:`agent_tools.tdd.enforcement.evaluate_pre_tool_use_tdd()`
	# @used-by :meth:`Df.Harness.Gate.TddPreToolGate.TddPreToolGate.check()`
	# @used-by :meth:`test_df_harness_s11_wave2b_tdd.DfHarnessS11Wave2bTddTests.test_tdd_enforcement_evaluator_events_and_guards()`
	def __init__(self, *, event_extractor: Callable | None=None, diff_non_exec_fn: Callable | None=None) -> None:
		self.__event_extractor = event_extractor
		self.__diff_non_exec_fn = diff_non_exec_fn
	# @used-by :func:`agent_tools.tdd.enforcement.evaluate_pre_tool_use_tdd()`
	# @used-by :meth:`Df.Harness.Gate.TddPreToolGate.TddPreToolGate.check()`
	# @used-by :meth:`test_df_harness_s11_wave2b_tdd.DfHarnessS11Wave2bTddTests.test_tdd_enforcement_evaluator_events_and_guards()`
	def evaluate_pre_tool_use(self, name: str, args: dict, payload: dict) -> str | None:
		r = None
		if not ServiceExempt().is_exempt(name, args, payload):
			cwd_raw = str(payload.get('cwd') or '').strip()
			cwd = Path(cwd_raw).resolve() if cwd_raw else None
			if name in ('write_file', 'edit_file'):
				r = self.__eval_pre_write(name, args, cwd, payload)
			elif 'run_command' == name:
				r = self.__eval_pre_run_command(str(args.get('CommandLine') or ''), cwd, payload)
		return r
	# @used-by :meth:`Enforcement.__eval_pre_write()`
	def __eval_pre_code_write(self, name: str, args: dict, target_path: Path, cls: str, cwd: Path | None, payload: dict) -> str | None:
		scope = CodeClassifier.resolve_code_scope(target_path)
		scope_key = WorktreeScope.resolve_key(target_path, scope)
		if 'production' != cls:
			sc_state = self.__load_pre_tool_tdd_state(payload, cwd)['scopes'].get(scope_key) if target_path.is_file() else None
			r = Enforcement.__eval_pre_test_write(name, args, target_path, scope, cwd, sc_state, self.__diff_non_exec_fn)
		else:
			old_disk, new_text, _, _ = Enforcement.compute_edited_content(name, args, target_path)
			if Exemption.is_diff_exempt(target_path, old_disk, new_text, repo_root=scope, project_root=cwd or scope, non_exec_fn=self.__diff_non_exec_fn):
				r = None
			else:
				sc_state = self.__load_pre_tool_tdd_state(payload, cwd)['scopes'].get(scope_key)
				r = Enforcement.__eval_pre_prod_write(target_path, sc_state)
		return r
	# @used-by :meth:`Enforcement.evaluate_pre_tool_use()`
	def __eval_pre_run_command(self, cmd: str, cwd: Path | None, payload: dict) -> str | None:
		prod_targets = CommandInspector.shell_code_write_targets(cmd, cwd=cwd)
		del_targets = CommandInspector.shell_test_delete_targets(cmd, cwd=cwd)
		if (not prod_targets) and (not del_targets):
			r = None
		else:
			prod_err = Enforcement.__eval_shell_prod_writes(prod_targets, cwd, self.__load_pre_tool_tdd_state(payload, cwd)) if prod_targets else None
			r = prod_err or (Enforcement.__eval_shell_test_deletes(del_targets, cwd) if del_targets else None)
		return r
	# @used-by :meth:`Enforcement.evaluate_pre_tool_use()`
	def __eval_pre_write(self, name: str, args: dict, cwd: Path | None, payload: dict) -> str | None:
		r = None
		raw_p = str(args.get('Path') or '').strip()
		if raw_p:
			cand = normalize_host_path(raw_p)
			target_path = cand.resolve() if cand.is_absolute() else ((cwd / cand).resolve() if cwd else cand.resolve())
			content_hint = args.get('Content') if 'write_file' == name and isinstance(args.get('Content'), str) else None
			cls = CodeClassifier(target_path, content=content_hint).classify()
			if 'non_code' != cls:
				r = self.__eval_pre_code_write(name, args, target_path, cls, cwd, payload)
		return r
	# @used-by :meth:`Enforcement.__eval_pre_code_write()`
	# @used-by :meth:`Enforcement.__eval_pre_run_command()`
	def __load_pre_tool_tdd_state(self, payload: dict, cwd: Path | None) -> dict:
		t_raw = str(payload.get('transcriptPath') or '').strip()
		if t_raw:
			events = self.__event_extractor(Path(t_raw), cwd=cwd) if None is not self.__event_extractor else EventsExtractor(Path(t_raw), cwd=cwd).extract()
		else:
			events = []
		return Evaluator(events, require_final_full_green=False, project_root=cwd).evaluate()
	# @used-by :meth:`Enforcement.__verify_staged_test_file()`
	# @used-by :meth:`Enforcement.compute_edited_content()`
	@staticmethod
	def __diff_added_lines(old_text: str | None, new_text: str) -> tuple[list[str], set[int]]:
		old_lines = (old_text or '').splitlines()
		new_lines = new_text.splitlines()
		added_lines: list[str] = []
		added_nums: set[int] = set()
		for tag, _, _, j1, j2 in difflib.SequenceMatcher(None, old_lines, new_lines).get_opcodes():
			if tag in ('insert', 'replace'):
				for idx in range(j1, j2):
					added_lines.append(new_lines[idx])
					added_nums.add(idx + 1)
		return (added_lines, added_nums)
	# @used-by :meth:`Enforcement.__eval_pre_code_write()`
	@staticmethod
	def __eval_pre_prod_write(target_path: Path, sc_state: dict | None) -> str | None:
		if None is not sc_state and sc_state.get('state') in ('RED_VERIFIED', 'GREEN_IMPLEMENTING'):
			r = None
		elif None is not sc_state and 'TEST_WRITTEN' == sc_state.get('state'):
			r = f'EXEC-2 TDD-RED-GATE: Cannot write/edit production code "{target_path.name}" yet \u2014 test file(s) were edited, but no failing (RED) test run has been observed after the test edit. Run the test first and observe it fail before writing production code.'
		else:
			r = f'EXEC-2 TDD-RED-GATE: Cannot write/edit production code "{target_path.name}" before writing a failing test. Strict TDD applies to all code: write a behavioral test first, run it to observe failure (RED), and only then implement production code.'
		return r
	# @used-by :meth:`Enforcement.__eval_pre_code_write()`
	@staticmethod
	def __eval_pre_test_write(name: str, args: dict, target_path: Path, scope: Path, cwd: Path | None, sc_state: dict | None, diff_non_exec_fn: Callable | None=None) -> str | None:
		old_disk, new_text, added_lines, added_nums = Enforcement.compute_edited_content(name, args, target_path)
		if None is new_text or Exemption.is_diff_exempt(target_path, old_disk, new_text, repo_root=scope, project_root=cwd or scope, non_exec_fn=diff_non_exec_fn):
			r = None
		else:
			ok_sub, sub_err = SubstantiveTestChecker(target_path, new_text).check_content()
			if not ok_sub:
				r = f'EXEC-2 TDD-SUBSTANTIVE-TEST-GATE: {sub_err}'
			else:
				behav_errs = SubstantiveTestChecker.source_text_assertion_issues(target_path, added_lines, full_content=new_text, added_line_numbers=added_nums)
				if behav_errs:
					r = 'EXEC-2 TDD-BEHAVIORAL-GATE: ' + '; '.join(behav_errs[:3])
				else:
					rel_posix = Enforcement.__rel_posix_for_scope(target_path, scope)
					r = Enforcement.__eval_test_ratchet_and_fitting(rel_posix, scope, cwd, old_disk, new_text, sc_state)
		return r
	# @used-by :meth:`Enforcement.__eval_pre_run_command()`
	@staticmethod
	def __eval_shell_prod_writes(prod_targets: list[Path], cwd: Path | None, tdd_state: dict) -> str | None:
		r = None
		for target_p in prod_targets:
			scope = CodeClassifier.resolve_code_scope(target_p)
			sc_state = tdd_state['scopes'].get(WorktreeScope.resolve_key(target_p, scope))
			if (None is sc_state or sc_state.get('state') not in ('RED_VERIFIED', 'GREEN_IMPLEMENTING')) and (not MechanicalExemption.find_matching_recipes(scope, project_root=cwd or scope)):
				r = f'EXEC-2 TDD-RED-GATE: Shell command writes production code file "{target_p.name}" before a failing (RED) test was written and observed. Write a failing test first.'
				break
		return r
	# @used-by :meth:`Enforcement.__eval_pre_run_command()`
	@staticmethod
	def __eval_shell_test_deletes(del_targets: list[Path], cwd: Path | None) -> str | None:
		r = None
		for del_test in del_targets:
			scope = CodeClassifier.resolve_code_scope(del_test)
			rel_posix = Enforcement.__rel_posix_for_scope(del_test, scope)
			if None is not Enforcement.git_head_text(scope, rel_posix):
				approval = RatchetGuard.find_approval(rel_posix, repo_root=scope, project_root=cwd or scope)
				if None is approval:
					r = f'EXEC-2 TDD-RATCHET-GATE: Deleting tracked test file "{rel_posix}" via shell command is prohibited without audited RATCHET-OK approval.'
					break
		return r
	# @used-by :meth:`Enforcement.__eval_pre_test_write()`
	@staticmethod
	def __eval_test_ratchet_and_fitting(rel_posix: str, scope: Path, cwd: Path | None, old_disk: str | None, new_text: str, sc_state: dict | None) -> str | None:
		r = None
		issue_urls = Enforcement.active_turn_issue_urls(new_text, old_disk)
		approval = RatchetGuard.find_approval(rel_posix, repo_root=scope, project_root=cwd or scope, issue_urls=issue_urls)
		head_text = Enforcement.git_head_text(scope, rel_posix)
		if None is not head_text:
			r_errs = RatchetGuard(rel_posix, head_text, new_text, approval=approval).check()
			if r_errs:
				r = 'EXEC-2 TDD-RATCHET-GATE: ' + '; '.join(r_errs[:3])
		if None is r and None is not old_disk and None is not sc_state and 'GREEN_IMPLEMENTING' == sc_state.get('state'):
			fit_errs = RatchetGuard(rel_posix, old_disk, new_text, approval=approval).check()
			if fit_errs:
				r = 'EXEC-2 TDD-ANTI-FITTING-GATE: Production code was already edited in this cycle; do not weaken or rewrite test assertions to fit the code! ' + '; '.join(fit_errs[:2])
		return r
	# @used-by :meth:`Enforcement.git_head_text()`
	@staticmethod
	def __git_head_sha(repo_root: Path) -> str | None:
		gitdir, common = Enforcement.__resolve_git_dirs(repo_root)
		r = None
		if None is not gitdir and (gitdir / 'HEAD').is_file():
			try:
				raw = (gitdir / 'HEAD').read_text(encoding='utf-8', errors='replace').strip()
				if raw.startswith('ref:'):
					ref_p = common / raw[4:].strip()
					cand = ref_p.read_text(encoding='utf-8', errors='replace').strip() if ref_p.is_file() else ''
				else:
					cand = raw
				if 40 == len(cand) and all((ch in '0123456789abcdefABCDEF' for ch in cand)):
					r = cand.lower()
			except OSError:
				r = None
		return r
	# @used-by :meth:`Enforcement.git_head_text()`
	# @used-by :meth:`Enforcement.git_index_text()`
	@staticmethod
	def __git_show_text(repo_root: Path, spec: str) -> str | None:
		return df_git_read_text(repo_root, 'show', spec) if (repo_root / '.git').exists() else None
	# @used-by :meth:`Enforcement.__eval_pre_test_write()`
	# @used-by :meth:`Enforcement.__eval_shell_test_deletes()`
	@staticmethod
	def __rel_posix_for_scope(target_path: Path, scope: Path) -> str:
		try:
			r = target_path.relative_to(scope).as_posix()
		except ValueError:
			r = target_path.name
		return r
	# @used-by :meth:`Enforcement.__git_head_sha()`
	@staticmethod
	def __resolve_git_dirs(repo_root: Path) -> tuple[Path | None, Path | None]:
		dot = repo_root / '.git'
		if dot.is_dir():
			r: tuple[Path | None, Path | None] = (dot, dot)
		elif dot.is_file():
			r = Enforcement.__resolve_worktree_git_dirs(repo_root, dot)
		else:
			r = (None, None)
		return r
	# @used-by :meth:`Enforcement.compute_edited_content()`
	@staticmethod
	def __resolve_new_text(name: str, args: dict, old_disk: str | None) -> str | None:
		r = None
		if 'write_file' == name:
			cand = args.get('Content')
			r = cand if isinstance(cand, str) else None
		elif 'edit_file' == name:
			target_str = args.get('Target')
			repl_str = args.get('Replacement')
			if None is not old_disk and isinstance(target_str, str) and isinstance(repl_str, str) and target_str in old_disk:
				r = old_disk.replace(target_str, repl_str)
		return r
	# @used-by :meth:`Enforcement.__resolve_git_dirs()`
	@staticmethod
	def __resolve_worktree_git_dirs(repo_root: Path, dot: Path) -> tuple[Path | None, Path | None]:
		r: tuple[Path | None, Path | None] = (None, None)
		try:
			txt = dot.read_text(encoding='utf-8', errors='replace').strip()
			if txt.lower().startswith('gitdir:'):
				gd = normalize_host_path(txt.split(':', 1)[1].strip())
				gd = gd.resolve() if gd.is_absolute() else (repo_root / gd).resolve()
				cd_file = gd / 'commondir'
				common = (gd / cd_file.read_text(encoding='utf-8', errors='replace').strip()).resolve() if cd_file.is_file() else gd
				r = (gd, common)
		except OSError:
			r = (None, None)
		return r
	# @used-by :meth:`Enforcement.verify_staged_diff()`
	@staticmethod
	def __staged_entry_texts(repo: Path, rel: str, use_index: bool, issue_urls: list[str]) -> tuple[Path, str | None, str | None, str]:
		fpath = repo / rel
		head_text = Enforcement.git_head_text(repo, rel)
		disk_text = Enforcement.git_index_text(repo, rel) if use_index else (fpath.read_text(encoding='utf-8', errors='replace') if fpath.is_file() else None)
		if None is disk_text:
			cls = CodeClassifier(fpath, content=head_text).classify()
		else:
			cls = CodeClassifier(fpath, content=disk_text).classify()
			for u in _GITHUB_ISSUE_URL_RE.findall(disk_text):
				if u not in issue_urls:
					issue_urls.append(u)
		return (fpath, head_text, disk_text, cls)
	# @used-by :meth:`Enforcement.verify_staged_diff()`
	@staticmethod
	def __verify_staged_test_file(repo: Path, rel: str, fpath: Path, head_text: str | None, disk_text: str | None, project_root: Path | None, issue_urls: list[str], diff_non_exec_fn: Callable | None=None) -> list[str]:
		r: list[str] = []
		exempt = None is not head_text and None is not disk_text and Exemption.is_diff_exempt(fpath, head_text, disk_text, repo_root=repo, project_root=project_root or repo, non_exec_fn=diff_non_exec_fn)
		if (not exempt) and None is not disk_text:
			ok_sub, sub_err = SubstantiveTestChecker(fpath, disk_text).check_content()
			if not ok_sub:
				r.append(f'EXEC-2 TDD-SUBSTANTIVE-TEST-GATE: {sub_err}')
			added_lines, added_nums = Enforcement.__diff_added_lines(head_text, disk_text)
			for b_err in SubstantiveTestChecker.source_text_assertion_issues(fpath, added_lines, full_content=disk_text, added_line_numbers=added_nums):
				r.append(f'EXEC-2 TDD-BEHAVIORAL-GATE: {b_err}')
		if (not exempt) and None is not head_text:
			approval = RatchetGuard.find_approval(rel, repo_root=repo, project_root=project_root or repo, issue_urls=issue_urls)
			for r_err in RatchetGuard(rel, head_text, disk_text, approval=approval).check():
				r.append(f'EXEC-2 {r_err}')
		return r
	# @used-by :func:`agent_tools.tdd.enforcement._active_turn_issue_urls()`
	# @used-by :meth:`Enforcement.__eval_test_ratchet_and_fitting()`
	@staticmethod
	def active_turn_issue_urls(new_text: str | None, old_text: str | None) -> list[str]:
		r: list[str] = []
		for blob in (new_text or '', old_text or ''):
			for u in _GITHUB_ISSUE_URL_RE.findall(blob):
				if u not in r:
					r.append(u)
		return r
	# @used-by :func:`agent_tools.tdd.enforcement._compute_edited_content()`
	# @used-by :meth:`Df.Harness.Gate.CodeSizePreToolGate.CodeSizePreToolGate.check()`
	# @used-by :meth:`Df.Harness.Gate.CodeStylePreToolGate.CodeStylePreToolGate.check()`
	# @used-by :meth:`Df.Harness.Gate.IssueCommentPreToolGate.IssueCommentPreToolGate.check()`
	# @used-by :meth:`Df.Harness.Gate.SubprocessHygienePreToolGate.SubprocessHygienePreToolGate.check()`
	# @used-by :meth:`Df.Harness.Gate.XrefPreToolGate.XrefPreToolGate.check()`
	# @used-by :meth:`Enforcement.__eval_pre_code_write()`
	# @used-by :meth:`Enforcement.__eval_pre_test_write()`
	@staticmethod
	def compute_edited_content(name: str, args: dict, target_path: Path) -> tuple[str | None, str | None, list[str], set[int]]:
		old_disk = target_path.read_text(encoding='utf-8', errors='replace') if target_path.is_file() else None
		new_text = Enforcement.__resolve_new_text(name, args, old_disk)
		if None is new_text:
			r = (old_disk, None, [], set())
		else:
			added_lines, added_nums = Enforcement.__diff_added_lines(old_disk, new_text)
			r = (old_disk, new_text, added_lines, added_nums)
		return r
	# @used-by :func:`agent_tools.tdd.enforcement._git_head_text()`
	# @used-by :meth:`Df.Harness.Gate.CodeSizePreToolGate.CodeSizePreToolGate.check()`
	# @used-by :meth:`Df.Harness.Gate.CodeSizeStagedGate.CodeSizeStagedGate.verify()`
	# @used-by :meth:`Df.Harness.Gate.CodeStylePreToolGate.CodeStylePreToolGate.check()`
	# @used-by :meth:`Df.Harness.Gate.CodeStyleStagedGate.CodeStyleStagedGate.verify()`
	# @used-by :meth:`Df.Harness.Gate.IssueCommentPreToolGate.IssueCommentPreToolGate.check()`
	# @used-by :meth:`Df.Harness.Gate.IssueCommentStagedGate.IssueCommentStagedGate.verify()`
	# @used-by :meth:`Df.Harness.Gate.PythonIntegrity.PythonIntegrity.verify_touched()`
	# @used-by :meth:`Df.Harness.Gate.SubprocessHygienePreToolGate.SubprocessHygienePreToolGate.check()`
	# @used-by :meth:`Df.Harness.Gate.SubprocessHygieneStagedGate.SubprocessHygieneStagedGate.verify()`
	# @used-by :meth:`Df.Harness.Gate.XrefPreToolGate.XrefPreToolGate.check()`
	# @used-by :meth:`Df.Harness.Gate.XrefStagedGate.XrefStagedGate.verify()`
	# @used-by :meth:`Enforcement.__eval_shell_test_deletes()`
	# @used-by :meth:`Enforcement.__eval_test_ratchet_and_fitting()`
	# @used-by :meth:`Enforcement.__staged_entry_texts()`
	@staticmethod
	def git_head_text(repo_root: Path, rel_posix: str) -> str | None:
		sha = Enforcement.__git_head_sha(repo_root)
		if None is sha:
			r = Enforcement.__git_show_text(repo_root, f'HEAD:{rel_posix}')
		else:
			key = (str(repo_root).lower(), sha, rel_posix)
			if key not in Enforcement.__HEAD_TEXT_CACHE:
				if 256 <= len(Enforcement.__HEAD_TEXT_CACHE):
					Enforcement.__HEAD_TEXT_CACHE.clear()
				Enforcement.__HEAD_TEXT_CACHE[key] = Enforcement.__git_show_text(repo_root, f'HEAD:{rel_posix}')
			r = Enforcement.__HEAD_TEXT_CACHE[key]
		return r
	# @used-by :func:`agent_tools.tdd.enforcement._git_index_text()`
	# @used-by :meth:`Df.Harness.Gate.CodeSizeStagedGate.CodeSizeStagedGate.verify()`
	# @used-by :meth:`Df.Harness.Gate.CodeStyleStagedGate.CodeStyleStagedGate.verify()`
	# @used-by :meth:`Df.Harness.Gate.IssueCommentStagedGate.IssueCommentStagedGate.verify()`
	# @used-by :meth:`Df.Harness.Gate.RulesAuditor.RulesAuditor.__read_staged_overrides()`
	# @used-by :meth:`Df.Harness.Gate.SubprocessHygieneStagedGate.SubprocessHygieneStagedGate.verify()`
	# @used-by :meth:`Df.Harness.Gate.XrefStagedGate.XrefStagedGate.__staged_overrides()`
	# @used-by :meth:`Enforcement.__staged_entry_texts()`
	@staticmethod
	def git_index_text(repo_root: Path, rel_posix: str) -> str | None:
		return Enforcement.__git_show_text(repo_root, f':{rel_posix}')
	# @used-by :func:`agent_tools.tdd.enforcement.verify_staged_tdd_diff()`
	@staticmethod
	def verify_staged_diff(repo_root: Path, staged_paths: list[str], *, message: str | None=None, project_root: Path | None=None, use_index: bool=False, diff_non_exec_fn: Callable | None=None) -> list[str]:
		repo = Path(repo_root).resolve()
		r: list[str] = []
		staged_prod: list[str] = []
		staged_tests: list[str] = []
		issue_urls = list(_GITHUB_ISSUE_URL_RE.findall(message)) if message else []
		for rel in staged_paths or ():
			fpath, head_text, disk_text, cls = Enforcement.__staged_entry_texts(repo, rel, use_index, issue_urls)
			if 'production' == cls and None is not disk_text:
				if not Exemption.is_diff_exempt(fpath, head_text, disk_text, repo_root=repo, message=message, project_root=project_root, non_exec_fn=diff_non_exec_fn):
					staged_prod.append(rel)
			elif 'test' == cls:
				if None is not disk_text:
					staged_tests.append(rel)
				r.extend(Enforcement.__verify_staged_test_file(repo, rel, fpath, head_text, disk_text, project_root, issue_urls, diff_non_exec_fn))
		if staged_prod and (not staged_tests):
			joined = ', '.join(staged_prod[:5])
			r.append(f'EXEC-2 TDD-COMMIT-GATE: Staged commit modifies production code ({joined}) without staging any test file. Strict TDD requires writing failing behavioral tests alongside all code changes.')
		return r
