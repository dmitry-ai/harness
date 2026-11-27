# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from pathlib import Path
from Df.Harness.Tdd.DiffExecutability import DiffExecutability
from agent_tools.shell_audit import _GITHUB_ISSUE_URL_RE, is_code_file, parse_issue_url
# 2026-11-26 "Move verification gate subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/381
# @used-by :mod:`agent_tools.tdd.exemption`
class Exemption:
	# @used-by :meth:`Exemption.__verify_single_file_issue_urls()`
	@staticmethod
	def __check_file_issue_urls(name: str, content: str, stripped_msg: str | None, repo_slug: str | None) -> None:
		raw_urls = set(_GITHUB_ISSUE_URL_RE.findall(content))
		if not raw_urls:
			raise ValueError(f'Issue-tracked code file lacks a GitHub Issue URL reference: {name}')
		file_urls = Exemption.__same_repo_urls(raw_urls, repo_slug)
		if not file_urls:
			raise ValueError(f'EXEC-5 ISSUE-FIRST-GATE: Referenced issue {sorted(raw_urls)[0]} does not match repository {repo_slug}')
		if None is not stripped_msg and stripped_msg not in file_urls:
			raise ValueError(f'Issue-tracked code file {name} does not reference the commit GitHub Issue URL {stripped_msg}')
	# @used-by :meth:`Exemption.__same_repo_urls()`
	# @used-by :meth:`Exemption.filter_repo_turn_issue_urls()`
	@staticmethod
	def __is_same_repo_url(url: str, repo_slug: str | None) -> bool:
		parsed = parse_issue_url(url)
		return (not repo_slug) or (None is not parsed and parsed[0].lower() == repo_slug.lower())
	# @used-by :meth:`Exemption.is_write_event_exempt()`
	@staticmethod
	def __resolve_scope_rel_path(fpath: Path, scope: Path) -> str:
		parts = fpath.parts
		r = ''
		for idx in range(len(parts) - 3):
			if ('\ua616', 'data', 'worktrees') == parts[idx:idx + 3] and idx + 4 < len(parts):
				r = Path(*parts[idx + 4:]).as_posix()
				break
		if not r:
			try:
				r = fpath.resolve().relative_to(scope.resolve()).as_posix()
			except (OSError, ValueError):
				r = ''
		return r
	# @used-by :meth:`Exemption.__check_file_issue_urls()`
	# @used-by :meth:`Exemption.__verify_single_file_issue_urls()`
	@staticmethod
	def __same_repo_urls(urls: set[str], repo_slug: str | None) -> set[str]:
		return {u for u in urls if Exemption.__is_same_repo_url(u, repo_slug)}
	# @used-by :meth:`Exemption.verify_staged_issue_urls()`
	@staticmethod
	def __verify_single_file_issue_urls(gate, name: str, content: str, stripped_msg: str | None, all_new: set[str], repo_slug: str | None=None) -> None:
		Exemption.__check_file_issue_urls(name, content, stripped_msg, repo_slug)
		added_urls, head_urls = gate._extract_added_diff_urls(name)
		new_diff_urls = Exemption.__same_repo_urls(added_urls - head_urls, repo_slug)
		if 1 < len(new_diff_urls):
			raise ValueError(f'Staged diff in {name} introduces multiple distinct GitHub Issue URLs: {sorted(new_diff_urls)}')
		if None is not stripped_msg and new_diff_urls and (new_diff_urls != {stripped_msg}):
			raise ValueError(f'Staged diff in {name} introduces GitHub Issue URL(s) {sorted(new_diff_urls)} not matching commit message {stripped_msg}')
		all_new.update(new_diff_urls)
	# @used-by :func:`agent_tools.tdd.exemption.filter_repo_turn_issue_urls()`
	# @used-by :meth:`test_df_harness_s11_wave2b_tdd_cov2.DfHarnessS11Wave2bTddCov2Tests.test_exemption_mechanical_and_ratchet_guard()`
	@staticmethod
	def filter_repo_turn_issue_urls(comment_urls: set[str], turn_issues: dict, repo_slug: str | None) -> list[str]:
		return sorted((u for u in comment_urls if u in turn_issues and Exemption.__is_same_repo_url(u, repo_slug)))
	# @used-by :meth:`Df.Harness.Tdd.Enforcement.Enforcement.__eval_pre_code_write()`
	# @used-by :meth:`Df.Harness.Tdd.Enforcement.Enforcement.__eval_pre_test_write()`
	# @used-by :meth:`Df.Harness.Tdd.Enforcement.Enforcement.__verify_staged_test_file()`
	# @used-by :meth:`Df.Harness.Tdd.Enforcement.Enforcement.verify_staged_diff()`
	# @used-by :meth:`test_df_harness_s11_wave2b_tdd.DfHarnessS11Wave2bTddTests.test_tdd_diff_executability_and_coverage()`
	@staticmethod
	def is_diff_exempt(path: str | Path, old_text: str | None, new_text: str | None, *, repo_root: Path | None=None, message: str | None=None, project_root: Path | None=None, non_exec_fn=None) -> bool:
		fn = non_exec_fn if None is not non_exec_fn else DiffExecutability.is_non_executable_diff
		return fn(path, old_text, new_text, repo_root=repo_root, message=message, project_root=project_root)
	# @used-by :meth:`Exemption.is_write_event_exempt()`
	# @used-by :meth:`Exemption.verify_staged_issue_urls()`
	# @used-by :meth:`test_df_harness_s11_wave2b_tdd_cov2.DfHarnessS11Wave2bTddCov2Tests.test_exemption_mechanical_and_ratchet_guard()`
	@staticmethod
	def is_git_path_exempt(repo_root: Path, rel_posix: str, *, disk_text: str | None=None, use_index: bool=False, message: str | None=None, project_root: Path | None=None, non_exec_fn=None) -> bool:
		fn = non_exec_fn if None is not non_exec_fn else DiffExecutability.is_git_path_non_executable
		return fn(repo_root, rel_posix, disk_text=disk_text, use_index=use_index, message=message, project_root=project_root)
	# @used-by :func:`agent_tools.tdd.exemption.is_write_event_exempt()`
	# @used-by :meth:`Df.Harness.Tdd.Evaluator.Evaluator.__init__()`
	# @used-by :meth:`test_df_harness_s11_wave2b_tdd_cov2.DfHarnessS11Wave2bTddCov2Tests.test_exemption_mechanical_and_ratchet_guard()`
	@staticmethod
	def is_write_event_exempt(raw_path: str | Path, scope_str: str, *, project_root: Path | None=None, git_non_exec_fn=None) -> bool:
		r = False
		if raw_path and scope_str:
			fpath, scope = (Path(str(raw_path)), Path(scope_str))
			rel = Exemption.__resolve_scope_rel_path(fpath, scope)
			if rel and (scope / '.git').exists():
				r = Exemption.is_git_path_exempt(scope, rel, project_root=project_root, non_exec_fn=git_non_exec_fn)
		return r
	# @used-by :func:`agent_tools.tdd.exemption.verify_staged_issue_urls()`
	# @used-by :meth:`test_df_harness_s11_wave2b_tail_cov.DfHarnessS11Wave2bTailCovTests.test_tdd_exemption_mechanical_ratchet_and_substantive()`
	# @used-by :meth:`test_df_harness_s11_wave2b_tdd_cov2.DfHarnessS11Wave2bTddCov2Tests.test_exemption_mechanical_and_ratchet_guard()`
	@staticmethod
	def verify_staged_issue_urls(gate, relative: list[str], stripped_msg: str | None, *, project_root: Path | None=None) -> set[str]:
		from agent_tools.issue_lifecycle import origin_repo_slug
		repo_slug = origin_repo_slug(gate.root)
		all_new: set[str] = set()
		for name in relative:
			path = gate.root / name
			if path.is_file() and is_code_file(name):
				content = path.read_text(encoding='utf-8', errors='replace')
				if content.strip() and (not Exemption.is_git_path_exempt(gate.root, name, disk_text=content, message=stripped_msg, project_root=project_root)):
					Exemption.__verify_single_file_issue_urls(gate, name, content, stripped_msg, all_new, repo_slug)
		if 1 < len(all_new):
			raise ValueError(f'Staged files mix changes from multiple GitHub Issues: {sorted(all_new)}')
		return all_new
