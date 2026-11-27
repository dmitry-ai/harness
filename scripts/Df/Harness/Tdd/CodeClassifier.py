# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from pathlib import Path
from Df.Core.lib.fs import df_path_posix
from Df.Core.lib.git import df_git_root
from agent_tools.shell_audit import normalize_host_path
import os
import re
# 2026-11-26 "Move verification gate subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/381
# @used-by :mod:`agent_tools.tdd.classifier`
class CodeClassifier:
	EXTENSIONLESS_CODE_NAMES = frozenset({
		'makefile', 'dockerfile', 'justfile', 'rakefile', 'gemfile', 'vagrantfile', 'cmakelists.txt',
	})
	GIT_HOOK_SCRIPT_NAMES = frozenset({
		'pre-commit', 'commit-msg', 'pre-push', 'prepare-commit-msg', 'post-commit', 'post-checkout', 'post-merge', 'pre-rebase',
	})
	PROJECT_MARKER_FILES = (
		'package.json', 'pyproject.toml', 'setup.py', 'setup.cfg', 'composer.json',
		'Cargo.toml', 'go.mod', 'pom.xml', 'build.gradle', 'build.gradle.kts', 'runtime.json', 'paths.json',
	)
	SCOPE_SUBDIR_SEGMENTS = frozenset({
		'test', 'tests', '__tests__', 'spec', 'specs', 'src', 'lib', 'scripts', 'bin', 'app', 'pkg', 'cmd',
	})
	SKIP_SCAN_DIRS = frozenset({
		'.git', '__pycache__', 'node_modules', 'vendor', '.venv', 'venv', 'dist', 'build', 'target', '.tox', '.mypy_cache', '.pytest_cache', '\ua616', '\ua66e', '\U0001f56e',
	})
	SOFTWARE_CODE_SUFFIXES = frozenset({
		'.py', '.pyi', '.pyx',
		'.js', '.mjs', '.cjs', '.ts', '.tsx', '.jsx', '.vue', '.svelte', '.astro',
		'.css', '.scss', '.sass', '.less',
		'.php', '.phtml',
		'.cs', '.fs', '.vb',
		'.java', '.kt', '.kts', '.scala', '.groovy',
		'.c', '.h', '.cc', '.cpp', '.cxx', '.hpp', '.hxx',
		'.rs', '.go', '.zig', '.swift', '.m', '.mm',
		'.ps1', '.psm1', '.psd1',
		'.sh', '.bash', '.zsh', '.fish', '.cmd', '.bat', '.vbs',
		'.awk', '.sed', '.pl', '.pm', '.rb', '.lua', '.tcl',
		'.sql', '.graphql', '.gql', '.proto',
		'.tf', '.tfvars', '.hcl', '.dockerfile',
	})
	CODE_SUFFIX_ALT = '|'.join(sorted((re.escape(s.lstrip('.')) for s in SOFTWARE_CODE_SUFFIXES), key=len, reverse=True))
	TEST_CAMEL_SUFFIX_RE = re.compile(r'.+(?:Test|Tests|Spec|Specs|Regression)$')
	TEST_DIR_SEGMENTS = frozenset({
		'test', 'tests', '__tests__', 'spec', 'specs', 'e2e', 'unit_tests', 'integration_tests', 'functional_tests', 'e2e_tests',
	})
	TEST_FILENAME_RE = re.compile(r'^(?:test[_.-].+|.+[_.-](?:tests?|specs?)|conftest)$', re.IGNORECASE)
	TEST_HELPER_FILENAMES = frozenset({
		'conftest.py', 'helpers.py', 'test_helpers.py', 'testutils.py', 'test_utils.py', 'fixtures.py',
		'testworkspace.cs', 'windowlifecyclehost.cs', 'runhidden.vbs', 'assertions.java', 'assertions.hpp',
	})
	# @used-by :func:`agent_tools.tdd.classifier.classify_code_path()`
	# @used-by :meth:`Df.Harness.Tdd.CommandInspector.CommandInspector.shell_write_targets()`
	# @used-by :meth:`Df.Harness.Tdd.Enforcement.Enforcement.__eval_pre_write()`
	# @used-by :meth:`Df.Harness.Tdd.Enforcement.Enforcement.__staged_entry_texts()`
	# @used-by :meth:`Df.Harness.Tdd.EventsExtractor.EventsExtractor.build_file_write_event()`
	# @used-by :meth:`test_df_harness_s11_wave2b_tdd.DfHarnessS11Wave2bTddTests.test_tdd_classifier_commands_and_lexers()`
	def __init__(self, path: str | Path, *, content: str | None=None) -> None:
		self.__path = path
		self.__content = content
	# @used-by :func:`agent_tools.tdd.classifier.classify_code_path()`
	# @used-by :meth:`Df.Harness.Tdd.CommandInspector.CommandInspector.shell_write_targets()`
	# @used-by :meth:`Df.Harness.Tdd.Enforcement.Enforcement.__eval_pre_write()`
	# @used-by :meth:`Df.Harness.Tdd.Enforcement.Enforcement.__staged_entry_texts()`
	# @used-by :meth:`Df.Harness.Tdd.EventsExtractor.EventsExtractor.build_file_write_event()`
	# @used-by :meth:`test_df_harness_s11_wave2b_tdd.DfHarnessS11Wave2bTddTests.test_tdd_classifier_commands_and_lexers()`
	def classify(self) -> str:
		if not CodeClassifier.is_software_code_file(self.__path, content=self.__content):
			r = 'non_code'
		else:
			r = 'test' if CodeClassifier.is_test_file(self.__path, content=self.__content) else 'production'
		return r
	# @used-by :meth:`CodeClassifier.count_repo_test_files()`
	@staticmethod
	def __count_dir_tests(dp: Path, filenames: list[str], cap: int) -> int:
		r = 0
		for fn in filenames:
			if CodeClassifier.is_test_file(dp / fn):
				r += 1
				if cap <= r:
					break
		return r
	# @used-by :meth:`CodeClassifier.resolve_code_scope()`
	@staticmethod
	def __find_marker_ancestor(start_dir: Path) -> Path | None:
		r = None
		for anc in (start_dir, *start_dir.parents):
			if CodeClassifier.__is_project_marker_dir(anc):
				r = anc
				break
		return r
	# @used-by :meth:`CodeClassifier.__find_marker_ancestor()`
	@staticmethod
	def __is_project_marker_dir(anc: Path) -> bool:
		r = any(((anc / m).exists() for m in CodeClassifier.PROJECT_MARKER_FILES)) or (anc / '\ua616').is_dir() or (anc / '.agents').is_dir()
		if not r:
			try:
				r = any(anc.glob('*.sln')) or any(anc.glob('*.csproj'))
			except OSError:
				pass
		return r
	# @used-by :meth:`CodeClassifier.resolve_code_scope()`
	@staticmethod
	def __resolve_deleted_worktree_scope(p: Path) -> Path | None:
		from agent_tools.path_registry import project_paths
		parts, r = (p.parts, None)
		for idx in range(len(parts) - 3):
			if ('\ua616', 'data', 'worktrees') == parts[idx:idx + 3] and idx + 4 < len(parts):
				proj_root = Path(*parts[:idx]).resolve()
				rel = Path(*parts[idx + 4:]).as_posix()
				cands = [cr.resolve() for cr in (*project_paths(proj_root).code_repos, proj_root / '\u2c0f/\u227b/\u2655/\u26ef', proj_root / 'code') if (cr / '.git').exists()]
				uniq = list(dict.fromkeys(cands))
				if not uniq and (proj_root / '.git').exists():
					uniq = [proj_root]
				r = next((cr for cr in uniq if (cr / rel).exists()), uniq[0] if 1 == len(uniq) else None)
				break
		return r
	# @used-by :func:`agent_tools.tdd.classifier.count_repo_test_files()`
	# @used-by :meth:`Df.Harness.Tdd.CommandInspector.CommandInspector.classify_test_command()`
	# @used-by :meth:`test_df_harness_s11_wave2b_tdd_cov1.DfHarnessS11Wave2bTddCov1Tests.test_diff_contract_executability_and_coverage_end_to_end()`
	@staticmethod
	def count_repo_test_files(scope_root: Path | None) -> int:
		r = 0
		if None is not scope_root:
			root = Path(scope_root)
			if root.is_dir():
				for dirpath, dirnames, filenames in os.walk(root):
					dirnames[:] = [d for d in dirnames if d not in CodeClassifier.SKIP_SCAN_DIRS and d.lower() not in CodeClassifier.SKIP_SCAN_DIRS]
					r += CodeClassifier.__count_dir_tests(Path(dirpath), filenames, 2 - r)
					if 2 <= r:
						break
		return r
	# @used-by :func:`agent_tools.tdd.classifier._has_shebang()`
	# @used-by :meth:`CodeClassifier.is_software_code_file()`
	# @used-by :meth:`Df.Harness.Tdd.CommentDiff.CommentDiff.detect_language()`
	# @used-by :meth:`test_df_harness_s11_wave2b_tdd_cov1.DfHarnessS11Wave2bTddCov1Tests.test_classifier_command_inspector_and_lexers()`
	@staticmethod
	def has_shebang(path: Path, content: str | None=None) -> bool:
		r = False
		if isinstance(content, str):
			r = content.startswith('#!')
		else:
			try:
				if path.is_file():
					with path.open('rb') as fh:
						r = b'#!' == fh.read(2)
			except OSError:
				pass
		return r
	# @used-by :func:`agent_tools.tdd.classifier.is_software_code_file()`
	# @used-by :meth:`CodeClassifier.classify()`
	# @used-by :meth:`CodeClassifier.is_test_file()`
	# @used-by :meth:`Df.Harness.Tdd.DiffExecutability.DiffExecutability.__classify_existing_git_path()`
	# @used-by :meth:`Df.Harness.Tdd.DiffExecutability.DiffExecutability.__classify_last_commit_path()`
	# @used-by :meth:`Df.Harness.Tdd.DiffExecutability.DiffExecutability.__classify_modified_entry()`
	# @used-by :meth:`Df.Harness.Tdd.DiffExecutability.DiffExecutability.__classify_non_modified_entry()`
	# @used-by :meth:`Df.Harness.Tdd.DiffExecutability.DiffExecutability.__classify_single_blob()`
	# @used-by :meth:`Df.Harness.Tdd.DiffExecutability.DiffExecutability.classify_git_path()`
	# @used-by :meth:`Df.Harness.Tdd.DiffExecutability.DiffExecutability.classify_text_diff()`
	@staticmethod
	def is_software_code_file(path: str | Path, *, content: str | None=None) -> bool:
		p = Path(str(path))
		parts_low = [part.lower() for part in p.parts]
		if '.git' in parts_low or '__pycache__' in parts_low or 'node_modules' in parts_low:
			r = False
		else:
			name_low = p.name.lower()
			suffix = p.suffix.lower() or (name_low if name_low.startswith('.') else '')
			is_hook = (not suffix) and name_low in CodeClassifier.GIT_HOOK_SCRIPT_NAMES and any((seg in ('git_hooks', 'hooks') for seg in parts_low[:-1]))
			r = suffix in CodeClassifier.SOFTWARE_CODE_SUFFIXES or name_low in CodeClassifier.EXTENSIONLESS_CODE_NAMES or is_hook or ((not suffix) and CodeClassifier.has_shebang(p, content=content))
		return r
	# @used-by :func:`agent_tools.tdd.classifier.is_test_file()`
	# @used-by :meth:`CodeClassifier.__count_dir_tests()`
	# @used-by :meth:`CodeClassifier.classify()`
	# @used-by :meth:`Df.Harness.Gate.CodeSizeChecker.CodeSizeChecker.__limits_for_path()`
	# @used-by :meth:`Df.Harness.Gate.SubprocessHygieneChecker.SubprocessHygieneChecker.is_target()`
	# @used-by :meth:`Df.Harness.Tdd.CommandInspector.CommandInspector.shell_test_delete_targets()`
	# @used-by :meth:`Df.Harness.Tdd.CommandInspector.CommandInspector.single_test_file_in_args()`
	# @used-by :meth:`Df.Harness.Tdd.SubstantiveTestChecker.SubstantiveTestChecker.__nonpy_source_text_issues()`
	# @used-by :meth:`Df.Harness.Tdd.SubstantiveTestChecker.SubstantiveTestChecker.ast_expr_contains_code_literal()`
	@staticmethod
	def is_test_file(path: str | Path, *, content: str | None=None) -> bool:
		if not CodeClassifier.is_software_code_file(path, content=content):
			r = False
		else:
			p = Path(str(path))
			dir_parts_low = [part.lower() for part in p.parts[:-1]]
			stem = p.stem
			r = any((seg in CodeClassifier.TEST_DIR_SEGMENTS for seg in dir_parts_low)) or bool(CodeClassifier.TEST_FILENAME_RE.match(stem)) or bool(CodeClassifier.TEST_CAMEL_SUFFIX_RE.match(stem)) or p.name.lower() in CodeClassifier.TEST_HELPER_FILENAMES
		return r
	# @used-by :func:`agent_tools.tdd.classifier._norm_posix()`
	# @used-by :meth:`CodeClassifier.resolve_code_scope()`
	# @used-by :meth:`Df.Harness.Tdd.Evaluator.Evaluator.command_matches_scope()`
	# @used-by :meth:`Df.Harness.Tdd.RatchetGuard.RatchetGuard.match_target()`
	# @used-by :meth:`test_df_harness_s11_wave2b_tdd_cov1.DfHarnessS11Wave2bTddCov1Tests.test_classifier_command_inspector_and_lexers()`
	@staticmethod
	def norm_posix(path: str | Path) -> str:
		return df_path_posix(path)
	# @used-by :func:`agent_tools.tdd.classifier.resolve_code_scope()`
	# @used-by :meth:`Df.Harness.Tdd.Enforcement.Enforcement.__eval_pre_code_write()`
	# @used-by :meth:`Df.Harness.Tdd.Enforcement.Enforcement.__eval_shell_prod_writes()`
	# @used-by :meth:`Df.Harness.Tdd.Enforcement.Enforcement.__eval_shell_test_deletes()`
	# @used-by :meth:`Df.Harness.Tdd.Evaluator.Evaluator.__cwd_matches_scope()`
	# @used-by :meth:`Df.Harness.Tdd.Evaluator.Evaluator.__resolve_event_target_scopes()`
	# @used-by :meth:`Df.Harness.Tdd.EventsExtractor.EventsExtractor.build_file_write_event()`
	# @used-by :meth:`Df.Harness.Tdd.WorktreeScope.WorktreeScope.canonical_scope_path()`
	# @used-by :meth:`test_df_harness_s11_wave2b_tdd_cov1.DfHarnessS11Wave2bTddCov1Tests.test_diff_contract_executability_and_coverage_end_to_end()`
	@staticmethod
	def resolve_code_scope(path: str | Path) -> Path:
		raw = normalize_host_path(path)
		try:
			p = raw.resolve()
		except OSError:
			p = raw
		start_dir = p if p.is_dir() else p.parent
		git_anc = df_git_root(start_dir)
		deleted_wt = '/data/worktrees/' in CodeClassifier.norm_posix(p).lower() and (not p.exists()) and (None is git_anc or '/data/worktrees/' not in CodeClassifier.norm_posix(git_anc).lower())
		r = CodeClassifier.__resolve_deleted_worktree_scope(p) if deleted_wt else git_anc
		if None is r:
			r = CodeClassifier.__find_marker_ancestor(start_dir)
		if None is r:
			r = start_dir.parent if start_dir.name.lower() in CodeClassifier.SCOPE_SUBDIR_SEGMENTS and start_dir.parent != start_dir else start_dir
		return r
