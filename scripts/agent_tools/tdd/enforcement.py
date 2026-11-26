# 2026-11-24 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from pathlib import Path
from ..shell_audit import _GITHUB_ISSUE_URL_RE, normalize_host_path
from .classifier import classify_code_path, resolve_code_scope
from .commands import shell_code_write_targets, shell_test_delete_targets
from .evaluator import evaluate_tdd_events
from .events import extract_antigravity_tdd_events
from .exemption import is_diff_exempt
from .ratchet import find_ratchet_approval, ratchet_diff_violations
from .service_exempt import is_service_finalization_call
from .substantive import is_substantive_test_content, source_text_assertion_issues
# 2026-11-26 "Support parent-issue inheritance and worktree-scoped TDD keys for coding fan-out": https://github.com/dmitry-ai/harness/issues/351
from .worktree_scope import resolve_tdd_scope_key
import difflib
import os
import subprocess
# 2026-11-25
# "Short-circuit non-code PreToolUse TDD checks and lazily memoize exemptions":
# https://github.com/dmitry-ai/harness/issues/250
_HEAD_TEXT_CACHE: dict[tuple[str, str, str], str | None] = {}
# @used-by :func:`_eval_test_ratchet_and_fitting()`
def _active_turn_issue_urls(new_text: str | None, old_text: str | None) -> list[str]:
	r: list[str] = []
	for blob in (new_text or '', old_text or ''):
		for u in _GITHUB_ISSUE_URL_RE.findall(blob):
			if u not in r:
				r.append(u)
	return r
# @used-by :func:`_eval_pre_code_write()`
# @used-by :func:`_eval_pre_test_write()`
# @used-by :func:`agent_tools.code_size_gate.evaluate_pre_tool_use_code_size()`
# @used-by :func:`agent_tools.code_style_gate.evaluate_pre_tool_use_code_style()`
# @used-by :func:`agent_tools.issue_comment_gate.evaluate_pre_tool_use_issue_comment()`
# @used-by :func:`agent_tools.subprocess_hygiene_gate.evaluate_pre_tool_use_subprocess_hygiene()`
# @used-by :func:`agent_tools.xref_gate.evaluate_pre_tool_use_xref()`
def _compute_edited_content(name: str, args: dict, target_path: Path) -> tuple[str | None, str | None, list[str], set[int]]:
	old_disk = target_path.read_text(encoding='utf-8', errors='replace') if target_path.is_file() else None
	new_text = _resolve_new_text(name, args, old_disk)
	if None is new_text:
		r = (old_disk, None, [], set())
	else:
		added_lines, added_nums = _diff_added_lines(old_disk, new_text)
		r = (old_disk, new_text, added_lines, added_nums)
	return r
# @used-by :func:`_compute_edited_content()`
# @used-by :func:`_verify_staged_test_file()`
def _diff_added_lines(old_text: str | None, new_text: str) -> tuple[list[str], set[int]]:
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
# 2026-11-25
# "Short-circuit non-code PreToolUse TDD checks and lazily memoize exemptions":
# https://github.com/dmitry-ai/harness/issues/250
# @used-by :func:`_eval_pre_write()`
def _eval_pre_code_write(name: str, args: dict, target_path: Path, cls: str, cwd: Path | None, payload: dict) -> str | None:
	scope = resolve_code_scope(target_path)
	# 2026-11-26 "Support parent-issue inheritance and worktree-scoped TDD keys for coding fan-out": https://github.com/dmitry-ai/harness/issues/351
	scope_key = resolve_tdd_scope_key(target_path, scope)
	if 'production' != cls:
		sc_state = _load_pre_tool_tdd_state(payload, cwd)['scopes'].get(scope_key) if target_path.is_file() else None
		r = _eval_pre_test_write(name, args, target_path, scope, cwd, sc_state)
	else:
		old_disk, new_text, _, _ = _compute_edited_content(name, args, target_path)
		# 2026-11-25
		# "Add comment-only diff lexer exemption for top 20 repository languages":
		# https://github.com/dmitry-ai/harness/issues/238
		if is_diff_exempt(target_path, old_disk, new_text, repo_root=scope, project_root=cwd or scope):
			r = None
		else:
			sc_state = _load_pre_tool_tdd_state(payload, cwd)['scopes'].get(scope_key)
			r = _eval_pre_prod_write(target_path, sc_state)
	return r
# @used-by :func:`_eval_pre_code_write()`
def _eval_pre_prod_write(target_path: Path, sc_state: dict | None) -> str | None:
	if None is not sc_state and sc_state.get('state') in ('RED_VERIFIED', 'GREEN_IMPLEMENTING'):
		r = None
	elif None is not sc_state and 'TEST_WRITTEN' == sc_state.get('state'):
		r = f'EXEC-2 TDD-RED-GATE: Cannot write/edit production code "{target_path.name}" yet \u2014 test file(s) were edited, but no failing (RED) test run has been observed after the test edit. Run the test first and observe it fail before writing production code.'
	else:
		r = f'EXEC-2 TDD-RED-GATE: Cannot write/edit production code "{target_path.name}" before writing a failing test. Strict TDD applies to all code: write a behavioral test first, run it to observe failure (RED), and only then implement production code.'
	return r
# 2026-11-25
# "Short-circuit non-code PreToolUse TDD checks and lazily memoize exemptions":
# https://github.com/dmitry-ai/harness/issues/250
# @used-by :func:`evaluate_pre_tool_use_tdd()`
def _eval_pre_run_command(cmd: str, cwd: Path | None, payload: dict) -> str | None:
	prod_targets = shell_code_write_targets(cmd, cwd=cwd)
	del_targets = shell_test_delete_targets(cmd, cwd=cwd)
	if (not prod_targets) and (not del_targets):
		r = None
	else:
		prod_err = _eval_shell_prod_writes(prod_targets, cwd, _load_pre_tool_tdd_state(payload, cwd)) if prod_targets else None
		r = prod_err or (_eval_shell_test_deletes(del_targets, cwd) if del_targets else None)
	return r
# @used-by :func:`_eval_pre_code_write()`
def _eval_pre_test_write(name: str, args: dict, target_path: Path, scope: Path, cwd: Path | None, sc_state: dict | None) -> str | None:
	old_disk, new_text, added_lines, added_nums = _compute_edited_content(name, args, target_path)
	# 2026-11-26 "Fix comment-only diff and denied-write gate false positives": https://github.com/dmitry-ai/harness/issues/276
	if None is new_text or is_diff_exempt(target_path, old_disk, new_text, repo_root=scope, project_root=cwd or scope):
		r = None
	else:
		ok_sub, sub_err = is_substantive_test_content(target_path, new_text)
		if not ok_sub:
			r = f'EXEC-2 TDD-SUBSTANTIVE-TEST-GATE: {sub_err}'
		else:
			behav_errs = source_text_assertion_issues(target_path, added_lines, full_content=new_text, added_line_numbers=added_nums)
			if behav_errs:
				r = 'EXEC-2 TDD-BEHAVIORAL-GATE: ' + '; '.join(behav_errs[:3])
			else:
				rel_posix = _rel_posix_for_scope(target_path, scope)
				r = _eval_test_ratchet_and_fitting(rel_posix, scope, cwd, old_disk, new_text, sc_state)
	return r
# @used-by :func:`evaluate_pre_tool_use_tdd()`
def _eval_pre_write(name: str, args: dict, cwd: Path | None, payload: dict) -> str | None:
	r = None
	raw_p = str(args.get('Path') or '').strip()
	if raw_p:
		cand = normalize_host_path(raw_p)
		target_path = cand.resolve() if cand.is_absolute() else ((cwd / cand).resolve() if cwd else cand.resolve())
		content_hint = args.get('Content') if 'write_file' == name and isinstance(args.get('Content'), str) else None
		cls = classify_code_path(target_path, content=content_hint)
		if 'non_code' != cls:
			r = _eval_pre_code_write(name, args, target_path, cls, cwd, payload)
	return r
# @used-by :func:`_eval_pre_run_command()`
def _eval_shell_prod_writes(prod_targets: list[Path], cwd: Path | None, tdd_state: dict) -> str | None:
	from .mechanical import find_matching_mechanical_recipes
	r = None
	for target_p in prod_targets:
		scope = resolve_code_scope(target_p)
		# 2026-11-26 "Support parent-issue inheritance and worktree-scoped TDD keys for coding fan-out": https://github.com/dmitry-ai/harness/issues/351
		sc_state = tdd_state['scopes'].get(resolve_tdd_scope_key(target_p, scope))
		# 2026-11-25
		# "Add auditable mechanical replacement recipe exemption for TDD and per-file issue gates":
		# https://github.com/dmitry-ai/harness/issues/239
		if (None is sc_state or sc_state.get('state') not in ('RED_VERIFIED', 'GREEN_IMPLEMENTING')) and (not find_matching_mechanical_recipes(scope, project_root=cwd or scope)):
			r = f'EXEC-2 TDD-RED-GATE: Shell command writes production code file "{target_p.name}" before a failing (RED) test was written and observed. Write a failing test first.'
			break
	return r
# @used-by :func:`_eval_pre_run_command()`
def _eval_shell_test_deletes(del_targets: list[Path], cwd: Path | None) -> str | None:
	r = None
	for del_test in del_targets:
		scope = resolve_code_scope(del_test)
		rel_posix = _rel_posix_for_scope(del_test, scope)
		if None is not _git_head_text(scope, rel_posix):
			approval = find_ratchet_approval(rel_posix, repo_root=scope, project_root=cwd or scope)
			if None is approval:
				r = f'EXEC-2 TDD-RATCHET-GATE: Deleting tracked test file "{rel_posix}" via shell command is prohibited without audited RATCHET-OK approval.'
				break
	return r
# @used-by :func:`_eval_pre_test_write()`
def _eval_test_ratchet_and_fitting(rel_posix: str, scope: Path, cwd: Path | None, old_disk: str | None, new_text: str, sc_state: dict | None) -> str | None:
	r = None
	issue_urls = _active_turn_issue_urls(new_text, old_disk)
	approval = find_ratchet_approval(rel_posix, repo_root=scope, project_root=cwd or scope, issue_urls=issue_urls)
	head_text = _git_head_text(scope, rel_posix)
	if None is not head_text:
		r_errs = ratchet_diff_violations(rel_posix, head_text, new_text, approval=approval)
		if r_errs:
			r = 'EXEC-2 TDD-RATCHET-GATE: ' + '; '.join(r_errs[:3])
	if None is r and None is not old_disk and None is not sc_state and 'GREEN_IMPLEMENTING' == sc_state.get('state'):
		fit_errs = ratchet_diff_violations(rel_posix, old_disk, new_text, approval=approval)
		if fit_errs:
			r = 'EXEC-2 TDD-ANTI-FITTING-GATE: Production code was already edited in this cycle; do not weaken or rewrite test assertions to fit the code! ' + '; '.join(fit_errs[:2])
	return r
# 2026-11-25
# "Short-circuit non-code PreToolUse TDD checks and lazily memoize exemptions":
# https://github.com/dmitry-ai/harness/issues/250
# @used-by :func:`_git_head_text()`
def _git_head_sha(repo_root: Path) -> str | None:
	gitdir, common = _resolve_git_dirs(repo_root)
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
# 2026-11-25
# "Short-circuit non-code PreToolUse TDD checks and lazily memoize exemptions":
# https://github.com/dmitry-ai/harness/issues/250
# @used-by :func:`_eval_shell_test_deletes()`
# @used-by :func:`_eval_test_ratchet_and_fitting()`
# @used-by :func:`_staged_entry_texts()`
# @used-by :func:`agent_tools.code_size_gate.evaluate_pre_tool_use_code_size()`
# @used-by :func:`agent_tools.code_size_gate.verify_staged_code_size_ratchet()`
# @used-by :func:`agent_tools.code_style_gate.evaluate_pre_tool_use_code_style()`
# @used-by :func:`agent_tools.code_style_gate.verify_staged_code_style_ratchet()`
# @used-by :func:`agent_tools.issue_comment_gate.evaluate_pre_tool_use_issue_comment()`
# @used-by :func:`agent_tools.issue_comment_gate.verify_staged_issue_comment_placement()`
# @used-by :func:`agent_tools.python_integrity.verify_touched_python_files()`
# @used-by :func:`agent_tools.subprocess_hygiene_gate.evaluate_pre_tool_use_subprocess_hygiene()`
# @used-by :func:`agent_tools.subprocess_hygiene_gate.verify_staged_subprocess_hygiene()`
# @used-by :func:`agent_tools.xref_gate.evaluate_pre_tool_use_xref()`
# @used-by :func:`agent_tools.xref_gate.verify_staged_xref()`
# @used-by :meth:`test_tdd_decomposition.TddDecompositionTests.test_enforcement_module_behavior_and_parity()`
def _git_head_text(repo_root: Path, rel_posix: str) -> str | None:
	sha = _git_head_sha(repo_root)
	if None is sha:
		r = _git_show_text(repo_root, f'HEAD:{rel_posix}')
	else:
		key = (str(repo_root).lower(), sha, rel_posix)
		if key not in _HEAD_TEXT_CACHE:
			if 256 <= len(_HEAD_TEXT_CACHE):
				_HEAD_TEXT_CACHE.clear()
			_HEAD_TEXT_CACHE[key] = _git_show_text(repo_root, f'HEAD:{rel_posix}')
		r = _HEAD_TEXT_CACHE[key]
	return r
# @used-by :func:`_staged_entry_texts()`
# @used-by :func:`agent_tools.code_size_gate.verify_staged_code_size_ratchet()`
# @used-by :func:`agent_tools.code_style_gate.verify_staged_code_style_ratchet()`
# @used-by :func:`agent_tools.issue_comment_gate.verify_staged_issue_comment_placement()`
# @used-by :func:`agent_tools.rules_audit._read_staged_overrides()`
# @used-by :func:`agent_tools.subprocess_hygiene_gate.verify_staged_subprocess_hygiene()`
# @used-by :func:`agent_tools.xref_gate._staged_overrides()`
def _git_index_text(repo_root: Path, rel_posix: str) -> str | None:
	return _git_show_text(repo_root, f':{rel_posix}')
# @used-by :func:`_git_head_text()`
# @used-by :func:`_git_index_text()`
def _git_show_text(repo_root: Path, spec: str) -> str | None:
	r = None
	if (repo_root / '.git').exists():
		proc = subprocess.run(
			['git', '--no-optional-locks', '-C', str(repo_root), 'show', spec],
			capture_output=True,
			env={**os.environ, 'GIT_OPTIONAL_LOCKS': '0'},
			check=False,
			creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0),
		)
		if 0 == proc.returncode:
			r = proc.stdout.decode('utf-8', errors='replace')
	return r
# 2026-11-25
# "Short-circuit non-code PreToolUse TDD checks and lazily memoize exemptions":
# https://github.com/dmitry-ai/harness/issues/250
# @used-by :func:`_eval_pre_code_write()`
# @used-by :func:`_eval_pre_run_command()`
def _load_pre_tool_tdd_state(payload: dict, cwd: Path | None) -> dict:
	t_raw = str(payload.get('transcriptPath') or '').strip()
	events = extract_antigravity_tdd_events(Path(t_raw), cwd=cwd) if t_raw else []
	return evaluate_tdd_events(events, require_final_full_green=False, project_root=cwd)
# @used-by :func:`_eval_pre_test_write()`
# @used-by :func:`_eval_shell_test_deletes()`
def _rel_posix_for_scope(target_path: Path, scope: Path) -> str:
	try:
		r = target_path.relative_to(scope).as_posix()
	except ValueError:
		r = target_path.name
	return r
# @used-by :func:`_git_head_sha()`
def _resolve_git_dirs(repo_root: Path) -> tuple[Path | None, Path | None]:
	dot = repo_root / '.git'
	if dot.is_dir():
		r: tuple[Path | None, Path | None] = (dot, dot)
	elif dot.is_file():
		r = _resolve_worktree_git_dirs(repo_root, dot)
	else:
		r = (None, None)
	return r
# @used-by :func:`_compute_edited_content()`
def _resolve_new_text(name: str, args: dict, old_disk: str | None) -> str | None:
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
# @used-by :func:`_resolve_git_dirs()`
def _resolve_worktree_git_dirs(repo_root: Path, dot: Path) -> tuple[Path | None, Path | None]:
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
# @used-by :func:`verify_staged_tdd_diff()`
def _staged_entry_texts(repo: Path, rel: str, use_index: bool, issue_urls: list[str]) -> tuple[Path, str | None, str | None, str]:
	fpath = repo / rel
	head_text = _git_head_text(repo, rel)
	disk_text = _git_index_text(repo, rel) if use_index else (fpath.read_text(encoding='utf-8', errors='replace') if fpath.is_file() else None)
	if None is disk_text:
		cls = classify_code_path(fpath, content=head_text)
	else:
		cls = classify_code_path(fpath, content=disk_text)
		for u in _GITHUB_ISSUE_URL_RE.findall(disk_text):
			if u not in issue_urls:
				issue_urls.append(u)
	return (fpath, head_text, disk_text, cls)
# @used-by :func:`verify_staged_tdd_diff()`
def _verify_staged_test_file(repo: Path, rel: str, fpath: Path, head_text: str | None, disk_text: str | None, project_root: Path | None, issue_urls: list[str]) -> list[str]:
	r: list[str] = []
	# 2026-11-26 "Fix comment-only diff and denied-write gate false positives": https://github.com/dmitry-ai/harness/issues/276
	exempt = None is not head_text and None is not disk_text and is_diff_exempt(fpath, head_text, disk_text, repo_root=repo, project_root=project_root or repo)
	if (not exempt) and None is not disk_text:
		ok_sub, sub_err = is_substantive_test_content(fpath, disk_text)
		if not ok_sub:
			r.append(f'EXEC-2 TDD-SUBSTANTIVE-TEST-GATE: {sub_err}')
		added_lines, added_nums = _diff_added_lines(head_text, disk_text)
		for b_err in source_text_assertion_issues(fpath, added_lines, full_content=disk_text, added_line_numbers=added_nums):
			r.append(f'EXEC-2 TDD-BEHAVIORAL-GATE: {b_err}')
	if (not exempt) and None is not head_text:
		approval = find_ratchet_approval(rel, repo_root=repo, project_root=project_root or repo, issue_urls=issue_urls)
		for r_err in ratchet_diff_violations(rel, head_text, disk_text, approval=approval):
			r.append(f'EXEC-2 {r_err}')
	return r
# 2026-11-24
# "Decompose tdd_gate.py into modular TDD verification package":
# https://github.com/dmitry-ai/harness/issues/169
# @used-by :func:`agent_tools.gates.tdd.check()`
# @used-by :meth:`test_comment_exemption_and_denied_writes.CommentExemptionAndDeniedWritesTests.test_tdd_exempts_comment_only_test_edits_and_recognizes_java_assertions()`
# @used-by :meth:`test_tdd_comment_exemption.CommentOnlyExemptionTests.test_pre_tool_use_allows_comment_only_edit_and_denies_code_edit()`
# @used-by :meth:`test_tdd_decomposition.TddDecompositionTests.test_enforcement_module_behavior_and_parity()`
# @used-by :meth:`test_tdd_fast_path.TddFastPathTests.test_pre_tool_use_short_circuits_non_code_and_non_writing_commands()`
# @used-by :meth:`test_tdd_mechanical_exemption.MechanicalExemptionTests.test_pre_tool_use_allows_matching_mechanical_edit_and_denies_extraneous_edit()`
# @used-by :mod:`agent_tools.tdd_gate`
# @used-by :mod:`agent_tools.tdd`
def evaluate_pre_tool_use_tdd(name: str, args: dict, payload: dict) -> str | None:
	r = None
	# 2026-11-26
	# "Exempt service finalization calls from PreToolUse TDD gate and add journal-sync --all-open":
	# https://github.com/dmitry-ai/harness/issues/256
	if not is_service_finalization_call(name, args, payload):
		cwd_raw = str(payload.get('cwd') or '').strip()
		cwd = Path(cwd_raw).resolve() if cwd_raw else None
		if name in ('write_file', 'edit_file'):
			r = _eval_pre_write(name, args, cwd, payload)
		elif 'run_command' == name:
			r = _eval_pre_run_command(str(args.get('CommandLine') or ''), cwd, payload)
	return r
# 2026-11-24
# "Decompose tdd_gate.py into modular TDD verification package":
# https://github.com/dmitry-ai/harness/issues/169
# @used-by :meth:`agent_tools.git_gate.GitRepoGate.verify_tdd_commit()`
# @used-by :meth:`test_comment_exemption_and_denied_writes.CommentExemptionAndDeniedWritesTests.test_tdd_exempts_comment_only_test_edits_and_recognizes_java_assertions()`
# @used-by :meth:`test_tdd_decomposition.TddDecompositionTests.test_enforcement_module_behavior_and_parity()`
# @used-by :meth:`test_tdd_gate.TddGateCoreTests.test_hardening_header_exit_code_indirect_source_read_and_index_blob()`
# @used-by :mod:`agent_tools.tdd_gate`
# @used-by :mod:`agent_tools.tdd`
def verify_staged_tdd_diff(repo_root: Path, staged_paths: list[str], *, message: str | None=None, project_root: Path | None=None, use_index: bool=False) -> list[str]:
	repo = Path(repo_root).resolve()
	r: list[str] = []
	staged_prod: list[str] = []
	staged_tests: list[str] = []
	issue_urls = list(_GITHUB_ISSUE_URL_RE.findall(message)) if message else []
	for rel in staged_paths or ():
		fpath, head_text, disk_text, cls = _staged_entry_texts(repo, rel, use_index, issue_urls)
		if 'production' == cls and None is not disk_text:
			# 2026-11-25
			# "Add comment-only diff lexer exemption for top 20 repository languages":
			# https://github.com/dmitry-ai/harness/issues/238
			if not is_diff_exempt(fpath, head_text, disk_text, repo_root=repo, message=message, project_root=project_root):
				staged_prod.append(rel)
		elif 'test' == cls:
			if None is not disk_text:
				staged_tests.append(rel)
			r.extend(_verify_staged_test_file(repo, rel, fpath, head_text, disk_text, project_root, issue_urls))
	if staged_prod and (not staged_tests):
		r.append(f'EXEC-2 TDD-COMMIT-GATE: Staged commit modifies production code ({", ".join(staged_prod[:5])}) without staging any test file. Strict TDD requires writing failing behavioral tests alongside all code changes.')
	return r
