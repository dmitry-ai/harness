# 2026-11-24 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from pathlib import Path
from ..shell_audit import normalize_host_path
import os
import re
# 2026-11-24
# "Decompose tdd_gate.py into modular TDD verification package":
# https://github.com/dmitry-ai/harness/issues/169
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
_CODE_SUFFIX_ALT = '|'.join(sorted((re.escape(s.lstrip('.')) for s in SOFTWARE_CODE_SUFFIXES), key=len, reverse=True))
_EXTENSIONLESS_CODE_NAMES = frozenset({
	'makefile', 'dockerfile', 'justfile', 'rakefile', 'gemfile', 'vagrantfile', 'cmakelists.txt',
})
_GIT_HOOK_SCRIPT_NAMES = frozenset({
	'pre-commit', 'commit-msg', 'pre-push', 'prepare-commit-msg', 'post-commit', 'post-checkout', 'post-merge', 'pre-rebase',
})
_PROJECT_MARKER_FILES = (
	'package.json', 'pyproject.toml', 'setup.py', 'setup.cfg', 'composer.json',
	'Cargo.toml', 'go.mod', 'pom.xml', 'build.gradle', 'build.gradle.kts', 'runtime.json', 'paths.json',
)
_SCOPE_SUBDIR_SEGMENTS = frozenset({
	'test', 'tests', '__tests__', 'spec', 'specs', 'src', 'lib', 'scripts', 'bin', 'app', 'pkg', 'cmd',
})
_SKIP_SCAN_DIRS = frozenset({
	'.git', '__pycache__', 'node_modules', 'vendor', '.venv', 'venv', 'dist', 'build', 'target', '.tox', '.mypy_cache', '.pytest_cache', '\ua616', '\ua66e', '\U0001f56e',
})
_TEST_CAMEL_SUFFIX_RE = re.compile(r'.+(?:Test|Tests|Spec|Specs|Regression)$')
_TEST_DIR_SEGMENTS = frozenset({
	'test', 'tests', '__tests__', 'spec', 'specs', 'e2e', 'unit_tests', 'integration_tests', 'functional_tests', 'e2e_tests',
})
_TEST_FILENAME_RE = re.compile(r'^(?:test[_.-].+|.+[_.-](?:tests?|specs?)|conftest)$', re.IGNORECASE)
_TEST_HELPER_FILENAMES = frozenset({
	'conftest.py', 'helpers.py', 'test_helpers.py', 'testutils.py', 'test_utils.py', 'fixtures.py',
	'testworkspace.cs', 'windowlifecyclehost.cs', 'runhidden.vbs',
	# 2026-11-26 "Fix comment-only diff and denied-write gate false positives": https://github.com/dmitry-ai/harness/issues/276
	'assertions.java', 'assertions.hpp',
})
def _count_dir_tests(dp: Path, filenames: list[str], cap: int) -> int:
	r = 0
	for fn in filenames:
		if is_test_file(dp / fn):
			r += 1
			if cap <= r:
				break
	return r
def _find_git_ancestor(start_dir: Path) -> Path | None:
	r = None
	for anc in (start_dir, *start_dir.parents):
		if (anc / '.git').exists():
			r = anc
			break
	return r
def _find_marker_ancestor(start_dir: Path) -> Path | None:
	r = None
	for anc in (start_dir, *start_dir.parents):
		if _is_project_marker_dir(anc):
			r = anc
			break
	return r
def _has_shebang(path: Path, content: str | None=None) -> bool:
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
def _is_project_marker_dir(anc: Path) -> bool:
	r = any((anc / m).exists() for m in _PROJECT_MARKER_FILES) or (anc / '\ua616').is_dir() or (anc / '.agents').is_dir()
	if not r:
		try:
			r = any(anc.glob('*.sln')) or any(anc.glob('*.csproj'))
		except OSError:
			pass
	return r
def _norm_posix(path: str | Path) -> str:
	return str(path).replace('\\', '/')
def classify_code_path(path: str | Path, *, content: str | None=None) -> str:
	if not is_software_code_file(path, content=content):
		r = 'non_code'
	else:
		r = 'test' if is_test_file(path, content=content) else 'production'
	return r
def count_repo_test_files(scope_root: Path | None) -> int:
	r = 0
	if None is not scope_root:
		root = Path(scope_root)
		if root.is_dir():
			for dirpath, dirnames, filenames in os.walk(root):
				dirnames[:] = [d for d in dirnames if d not in _SKIP_SCAN_DIRS and d.lower() not in _SKIP_SCAN_DIRS]
				r += _count_dir_tests(Path(dirpath), filenames, 2 - r)
				if 2 <= r:
					break
	return r
def is_software_code_file(path: str | Path, *, content: str | None=None) -> bool:
	p = Path(str(path))
	parts_low = [part.lower() for part in p.parts]
	if '.git' in parts_low or '__pycache__' in parts_low or 'node_modules' in parts_low:
		r = False
	else:
		suffix = p.suffix.lower()
		name_low = p.name.lower()
		is_hook = (not suffix) and name_low in _GIT_HOOK_SCRIPT_NAMES and any(seg in ('git_hooks', 'hooks') for seg in parts_low[:-1])
		r = suffix in SOFTWARE_CODE_SUFFIXES or name_low in _EXTENSIONLESS_CODE_NAMES or is_hook or ((not suffix) and _has_shebang(p, content=content))
	return r
def is_test_file(path: str | Path, *, content: str | None=None) -> bool:
	if not is_software_code_file(path, content=content):
		r = False
	else:
		p = Path(str(path))
		dir_parts_low = [part.lower() for part in p.parts[:-1]]
		stem = p.stem
		r = any(seg in _TEST_DIR_SEGMENTS for seg in dir_parts_low) or bool(_TEST_FILENAME_RE.match(stem)) or bool(_TEST_CAMEL_SUFFIX_RE.match(stem)) or p.name.lower() in _TEST_HELPER_FILENAMES
	return r
# 2026-11-24
# "Fix EXEC-2 TDD trace scoping for deleted worktrees and subagent steps":
# https://github.com/dmitry-ai/harness/issues/173
def _resolve_deleted_worktree_scope(p: Path) -> Path | None:
	from ..path_registry import project_paths
	parts, r = (p.parts, None)
	for idx in range(len(parts) - 3):
		if ('\ua616', 'data', 'worktrees') == parts[idx:idx + 3] and idx + 4 < len(parts):
			proj_root = Path(*parts[:idx]).resolve()
			rel = Path(*parts[idx + 4:]).as_posix()
			cands = [cr.resolve() for cr in (*project_paths(proj_root).code_repos, proj_root / '\u2c0f/\u227b/\u2655/\u26ef', proj_root / 'code') if (cr / '.git').exists()]
			uniq = list(dict.fromkeys(cands))
			r = next((cr for cr in uniq if (cr / rel).exists()), uniq[0] if 1 == len(uniq) else None)
			break
	return r
def resolve_code_scope(path: str | Path) -> Path:
	raw = normalize_host_path(path)
	try:
		p = raw.resolve()
	except OSError:
		p = raw
	start_dir = p if p.is_dir() else p.parent
	# 2026-11-24
	# "Fix EXEC-2 TDD trace scoping for deleted worktrees and subagent steps":
	# https://github.com/dmitry-ai/harness/issues/173
	# 2026-11-24
	# "Fix worktree scope resolution for new files in TDD classifier":
	# https://github.com/dmitry-ai/harness/issues/188
	git_anc = _find_git_ancestor(start_dir)
	deleted_wt = '/data/worktrees/' in _norm_posix(p).lower() and (not p.exists()) and (None is git_anc or '/data/worktrees/' not in _norm_posix(git_anc).lower())
	r = _resolve_deleted_worktree_scope(p) if deleted_wt else git_anc
	if None is r:
		r = _find_marker_ancestor(start_dir)
	if None is r:
		r = start_dir.parent if start_dir.name.lower() in _SCOPE_SUBDIR_SEGMENTS and start_dir.parent != start_dir else start_dir
	return r
