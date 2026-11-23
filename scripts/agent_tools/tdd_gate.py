# 2026-11-23 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Enforce PreToolUse fail-fast normalization and block redundant schedule timers over run_command":
# https://github.com/dmitry-ai/harness/issues/162
# 2026-11-23 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Add parallel fail-fast run-tests runner with module timeouts and TDD gate registration":
# https://github.com/dmitry-ai/harness/issues/160
# 2026-11-23 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Implement core Issue-First verification engine in agent_tools/issue_first_gate.py":
# https://github.com/dmitry-ai/harness/issues/143
# 2026-11-23 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Implement universal TDD verification engine in agent_tools/tdd_gate.py":
# https://github.com/dmitry-ai/harness/issues/135
from __future__ import annotations

import ast
from collections import Counter
import difflib
import json
import os
from pathlib import Path
import re
import subprocess
from urllib.parse import unquote, urlsplit
from .shell_audit import _GITHUB_ISSUE_URL_RE, _split_shell_segments, classify_git_argv, normalize_host_path, parse_issue_url

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
_EXTENSIONLESS_CODE_NAMES = frozenset({
	'makefile', 'dockerfile', 'justfile', 'rakefile', 'gemfile', 'vagrantfile', 'cmakelists.txt',
})
_GIT_HOOK_SCRIPT_NAMES = frozenset({
	'pre-commit', 'commit-msg', 'pre-push', 'prepare-commit-msg', 'post-commit', 'post-checkout', 'post-merge', 'pre-rebase',
})
_TEST_DIR_SEGMENTS = frozenset({
	'test', 'tests', '__tests__', 'spec', 'specs', 'e2e', 'unit_tests', 'integration_tests', 'functional_tests', 'e2e_tests',
})
_SCOPE_SUBDIR_SEGMENTS = frozenset({
	'test', 'tests', '__tests__', 'spec', 'specs', 'src', 'lib', 'scripts', 'bin', 'app', 'pkg', 'cmd',
})
_PROJECT_MARKER_FILES = (
	'package.json', 'pyproject.toml', 'setup.py', 'setup.cfg', 'composer.json',
	'Cargo.toml', 'go.mod', 'pom.xml', 'build.gradle', 'build.gradle.kts', 'runtime.json', 'paths.json',
)
_SKIP_SCAN_DIRS = frozenset({
	'.git', '__pycache__', 'node_modules', 'vendor', '.venv', 'venv', 'dist', 'build', 'target', '.tox', '.mypy_cache', '.pytest_cache', '\ua616', '\ua66e', '\U0001f56e',
})
_TEST_HELPER_FILENAMES = frozenset({
	'conftest.py', 'helpers.py', 'test_helpers.py', 'testutils.py', 'test_utils.py', 'fixtures.py',
	'testworkspace.cs', 'windowlifecyclehost.cs', 'runhidden.vbs',
})
_TEST_FILENAME_RE = re.compile(
	r'^(?:test[_.-].+|.+[_.-](?:tests?|specs?)|conftest)$',
	re.IGNORECASE,
)
_TEST_CAMEL_SUFFIX_RE = re.compile(r'.+(?:Test|Tests|Spec|Specs|Regression)$')
_RIGGED_FAILURE_RE = re.compile(
	r'(?:(?:;|&&|\|\|)\s*(?:exit\s+[1-9]\d*|false\b|return\s+[1-9]\d*|throw\b)|;\s*exit\s+\$?1\b)',
	re.IGNORECASE,
)
_INVOCATION_ERROR_RE = re.compile(
	r'(?i)(?:is not recognized as an internal or external command'
	r'|is not recognized as the name of a cmdlet'
	r'|:\s*command not found\b'
	r'|error:\s*unrecognized arguments:'
	r'|no such option:'
	r'|no module named\s+(?:pytest|unittest|nose|tox)\b'
	r'|cannot find module\b[^.\n]*(?:jest|vitest|mocha))'
)
_ZERO_TESTS_RE = re.compile(
	r'(?i)(?:\bRan\s+0\s+tests?\s+in\b'
	r'|\bcollected\s+0\s+items\b'
	r'|\bno\s+tests\s+ran\b'
	r'|\b0\s+tests?\s+passed,\s*0\s+failed\b'
	r'|[\u2139i]\s+tests\s+0\b)'
)
_EXIT_CODE_RE = re.compile(r'(?im)^(?:(?:Command|Process)\s+exited\s+with\s+code\s+(-?\d+)\.?|Exit\s+code:\s*(-?\d+))\s*$')
_OUTPUT_BODY_SPLIT_RE = re.compile(r'(?m)^(?:Command output|Output):\s*$')
_BG_TASK_ID_RE = re.compile(r'task\s+id:\s*([A-Za-z0-9_./:-]+)', re.IGNORECASE)
_BG_TASK_LOG_RE = re.compile(r'(?:Task\s+logs\s+are\s+available\s+at|Log):\s*(file:///[^\s\'"<>]+)', re.IGNORECASE)
_BG_TASK_FINISHED_RE = re.compile(r'Task\s+id\s+"([^"]+)"\s+finished\s+with\s+result:\s*([\s\S]*)', re.IGNORECASE)
_TEST_DEF_RE = re.compile(
	r'^\s*(?:(?:async\s+)?def\s+test_\w+\s*\('
	r'|(?:public|private|protected)?\s*(?:static\s+)?function\s+test\w*\s*\('
	r'|(?:it|test|describe)\s*\('
	r'|\[(?:Fact|Theory|Test|TestMethod)\b'
	r'|@Test\b'
	r'|func\s+Test\w*\s*\('
	r'|#\[test\]'
	r'|(?:Describe|Context|It)\s+[\'"]'
	r'|@test\s+[\'"])'
)
_ASSERTION_LINE_RE = re.compile(
	r'(?:\bassert\s+|\bassert\s*\('
	r'|\bself\.assert[A-Z]\w*\s*\('
	r'|\b\w+\.assert_(?:called|not_called|any_call|has_calls)\w*\s*\('
	r'|\bpytest\.raises\s*\('
	r'|\bassertRaises(?:Regex)?\s*\('
	r'|\bexpect\s*\('
	r'|\.(?:toEqual|toBe|toThrow|toContain|toMatch|toStrictEqual|toHaveBeenCalled|toHaveLength|rejects|resolves)\b'
	r'|\bassert\.(?:strictEqual|deepStrictEqual|deepEqual|equal|ok|throws|rejects|match|fail)\s*\('
	r'|\bAssert\.\w+\s*\('
	r'|\bAssert::\w+\s*\('
	r'|\$this->assert\w+\s*\('
	r'|\|\s*Should\s+-'
	r'|\bAssert-\w+\b'
	r'|\bt\.(?:Error|Errorf|Fatal|Fatalf|Fail|FailNow)\s*\('
	r'|\b(?:assert|require)\.\w+\s*\('
	r'|\b(?:debug_)?assert(?:_eq|_ne)?!\s*\('
	r'|\bfail\s*\()'
)
_SKIP_MARKER_RE = re.compile(
	r'(?:@unittest\.skip\w*\b'
	r'|@pytest\.mark\.skip\w*\b'
	r'|\bself\.skipTest\s*\('
	r'|\b(?:it|test|describe)\.skip\s*\('
	r'|\b(?:xit|xtest|xdescribe)\s*\('
	r'|\[(?:Ignore|Skip)\b'
	r'|\[(?:Fact|Theory)\s*\([^\)]*\bSkip\s*='
	r'|\bt\.Skip(?:f|Now)?\s*\('
	r'|#\[ignore\]'
	r'|\$this->markTestSkipped\s*\()'
)
_RATCHET_SLOP_RE = re.compile(
	r'(?i)^(?:updat(?:e|ed|ing)|fix(?:ed|ing)?|adjust(?:ed|ing)?|chang(?:e|ed|ing)|adapt(?:ed|ing)?|relax(?:ed|ing)?|align(?:ed|ing)?)'
	r'\s+(?:the\s+|failing\s+|broken\s+|existing\s+)?tests?(?:\s+expectations?)?'
	r'\s+(?:to\s+(?:pass|match|fit|align|reflect)|so\s+(?:it|ci|tests?)\s+(?:pass|turn)|for\s+(?:new|current)\s+(?:code|output|implementation))'
)
_RATCHET_OK_LINE_RE = re.compile(
	r'(?im)^\s*(?:[-*+]\s+)?(?:`|\*\*|__)?RATCHET-OK(?:\*\*|__|`)?\s*:\s*(.+?)\s*$'
)
_CODE_SUFFIX_ALT = '|'.join(sorted((re.escape(s.lstrip('.')) for s in SOFTWARE_CODE_SUFFIXES), key=len, reverse=True))
_CODE_LIT_EXT_RE = re.compile(rf'(?i)[A-Za-z0-9_./\\-]+\.(?:{_CODE_SUFFIX_ALT})(?=[\'"`\s,)\]]|$)')
_TEMP_PATH_HINT_RE = re.compile(
	r'(?i)(?:^|[/\\._-])(?:tmp|temp|tmpdir|tmp_path|sandbox|fixture|fixtures|sample|samples|mock|mocks|generated|out|output|dist|build|work|td|proj|project|repo|code_repo|scratch|harness_hook_runner)(?:$|[/\\._-])'
)
_SOURCE_TEXT_NONPY_READ_RE = re.compile(
	rf'(?i)(?:readFileSync|readFile|ReadAllText|ReadAllLines|file_get_contents|Get-Content|os\.ReadFile|read_to_string|readString|\.read_text|\.read_bytes|inspect\.getsource)\s*\([^)\n]*[\'"]([^\'"\n]+\.(?:{_CODE_SUFFIX_ALT}))[\'"]'
)
_SHELL_WRITE_CMD_PATTERNS = (
	re.compile(r'(?i)\b(?:Set-Content|Out-File|Add-Content)\b[^\r\n;|&]*?(?:-Path|-LiteralPath|-FilePath)\s+(?:"([^"]+)"|\'([^\']+)\'|([^\s;|&]+))'),
	re.compile(r'(?i)\b(?:Set-Content|Out-File|Add-Content)\s+(?!-)(?:"([^"]+)"|\'([^\']+)\'|([^\s;|&]+))'),
	re.compile(r'(?i)\[System\.IO\.File\]::WriteAll(?:Text|Bytes|Lines)\s*\(\s*(?:"([^"]+)"|\'([^\']+)\')'),
	re.compile(r'(?i)\bPath\s*\(\s*(?:"([^"]+)"|\'([^\']+)\')\s*\)\s*\.\s*write_(?:text|bytes)\s*\('),
	re.compile(r'(?i)\bopen\s*\(\s*(?:"([^"]+)"|\'([^\']+)\')\s*,\s*[\'"][wa][^\'"]*[\'"]'),
	re.compile(r'(?i)(?:^|[^0-9&])>>?\s*(?:"([^"]+)"|\'([^\']+)\'|([^\s;|&>]+))'),
	re.compile(r'(?i)\btee\b(?:\s+-[a-zA-Z]+)*\s+(?:"([^"]+)"|\'([^\']+)\'|([^\s;|&]+))'),
	re.compile(r'(?i)\bsed\b[^\r\n;|&]*\s-i[^\s]*[^\r\n;|&]*\s+(?:"([^"]+)"|\'([^\']+)\'|([^\s;|&]+))\s*$'),
	re.compile(r'(?i)\b(?:Copy-Item|Move-Item|cp|mv)\b[^\r\n;|&]*\s+(?:"([^"]+)"|\'([^\']+)\'|([^\s;|&]+))\s*$'),
)
_SHELL_DELETE_RE = re.compile(
	r'(?i)\b(?:git\s+rm|Remove-Item|rm|del|erase)\b[^\r\n;|&]*'
)
_SHELL_TEST_FILE_TOKEN_RE = re.compile(
	rf'(?:"([^"]+\.(?:{_CODE_SUFFIX_ALT}))"|\'([^\']+\.(?:{_CODE_SUFFIX_ALT}))\'|([^\s;|&"\']+\.(?:{_CODE_SUFFIX_ALT})))',
	re.IGNORECASE,
)


def _norm_posix(path: str | Path) -> str:
	return str(path).replace('\\', '/')


def _has_shebang(path: Path, content: str | None = None) -> bool:
	if isinstance(content, str):
		return content.startswith('#!')
	try:
		if path.is_file():
			with path.open('rb') as fh:
				return fh.read(2) == b'#!'
	except OSError:
		pass
	return False


def is_software_code_file(path: str | Path, *, content: str | None = None) -> bool:
	p = Path(str(path))
	norm = _norm_posix(p)
	parts_low = [part.lower() for part in p.parts]
	if '.git' in parts_low or '__pycache__' in parts_low or 'node_modules' in parts_low:
		return False
	suffix = p.suffix.lower()
	if suffix in SOFTWARE_CODE_SUFFIXES:
		return True
	name_low = p.name.lower()
	if name_low in _EXTENSIONLESS_CODE_NAMES:
		return True
	if not suffix and name_low in _GIT_HOOK_SCRIPT_NAMES and any(seg in ('git_hooks', 'hooks') for seg in parts_low[:-1]):
		return True
	if not suffix and _has_shebang(p, content=content):
		return True
	return False


def is_test_file(path: str | Path, *, content: str | None = None) -> bool:
	if not is_software_code_file(path, content=content):
		return False
	p = Path(str(path))
	dir_parts_low = [part.lower() for part in p.parts[:-1]]
	if any(seg in _TEST_DIR_SEGMENTS for seg in dir_parts_low):
		return True
	stem = p.stem
	if _TEST_FILENAME_RE.match(stem):
		return True
	if _TEST_CAMEL_SUFFIX_RE.match(stem):
		return True
	if p.name.lower() in _TEST_HELPER_FILENAMES:
		return True
	return False


def classify_code_path(path: str | Path, *, content: str | None = None) -> str:
	if not is_software_code_file(path, content=content):
		return 'non_code'
	return 'test' if is_test_file(path, content=content) else 'production'


def resolve_code_scope(path: str | Path) -> Path:
	raw = normalize_host_path(path)
	try:
		p = raw.resolve()
	except OSError:
		p = raw
	start_dir = p if p.is_dir() else p.parent
	for anc in (start_dir, *start_dir.parents):
		if (anc / '.git').exists():
			return anc
	for anc in (start_dir, *start_dir.parents):
		if any((anc / m).exists() for m in _PROJECT_MARKER_FILES) or (anc / '\ua616').is_dir() or (anc / '.agents').is_dir():
			return anc
		try:
			if any(anc.glob('*.sln')) or any(anc.glob('*.csproj')):
				return anc
		except OSError:
			pass
	if start_dir.name.lower() in _SCOPE_SUBDIR_SEGMENTS and start_dir.parent != start_dir:
		return start_dir.parent
	return start_dir


def count_repo_test_files(scope_root: Path | None) -> int:
	if None is scope_root:
		return 0
	root = Path(scope_root)
	if not root.is_dir():
		return 0
	count = 0
	for dirpath, dirnames, filenames in os.walk(root):
		dirnames[:] = [d for d in dirnames if d not in _SKIP_SCAN_DIRS and d.lower() not in _SKIP_SCAN_DIRS]
		dp = Path(dirpath)
		for fn in filenames:
			cand = dp / fn
			if is_test_file(cand):
				count += 1
				if count >= 2:
					return count
	return count


def _extract_cmd_paths(seg: str) -> list[str]:
	out: list[str] = []
	for m in re.finditer(r'"([^"]+)"|\'([^\']+)\'|([^\s;|&]+)', seg):
		tok = m.group(1) or m.group(2) or m.group(3) or ''
		if not tok or tok.startswith('-'):
			continue
		if '/' in tok or '\\' in tok or re.search(rf'\.(?:{_CODE_SUFFIX_ALT})$', tok, re.I):
			out.append(tok)
	return out


def _single_test_file_in_args(seg: str) -> bool:
	for tok in _extract_cmd_paths(seg):
		if '*' in tok or '?' in tok:
			continue
		if is_test_file(tok):
			return True
	return False


def classify_test_command(cmd: str, *, scope_root: Path | None = None) -> dict:
	if not isinstance(cmd, str) or not cmd.strip():
		return {'is_test_cmd': False, 'is_full_suite': False, 'rigged_failure': False, 'target_paths': []}
	rigged = bool(_RIGGED_FAILURE_RE.search(cmd))
	is_test = False
	is_full = False
	targets: list[str] = []
	for seg in _split_shell_segments(cmd):
		s = seg.strip()
		if not s:
			continue
		seg_is_test = False
		seg_is_full = False
		# Harness parallel test runner (harness.py run-tests)
		if re.search(r'(?i)(?:^|\s)["\']?(?:[^"\']*[/\\])?(?:harness|upwork_project)\.py["\']?\s+run-tests(?:\s|$)', s):
			seg_is_test = True
			has_mod = bool(re.search(r'(?:\s--module(?:=|\s+))', s))
			m_pat = re.search(r'(?:-p|--pattern)(?:\s+|=)(?:"([^"]+)"|\'([^\']+)\'|(\S+))', s)
			pat_val = (m_pat.group(1) or m_pat.group(2) or m_pat.group(3)) if m_pat else None
			narrow_pat = (None is not pat_val) and ('*' not in pat_val) and ('?' not in pat_val)
			seg_is_full = (not has_mod) and (not narrow_pat)
		# Python unittest
		elif re.search(r'(?i)\bpython(?:3(?:\.\d+)?)?(?:\.exe)?\b[^\r\n]*\s-m\s+unittest\b', s):
			seg_is_test = True
			has_discover = bool(re.search(r'\bdiscover\b', s))
			m_pat = re.search(r'(?:-p|--pattern)(?:\s+|=)(?:"([^"]+)"|\'([^\']+)\'|(\S+))', s)
			pat_val = (m_pat.group(1) or m_pat.group(2) or m_pat.group(3)) if m_pat else None
			if has_discover:
				seg_is_full = (None is pat_val) or ('*' in pat_val) or ('?' in pat_val)
			else:
				after_u = re.split(r'\bunittest\b', s, maxsplit=1)[1]
				pos_args = [tok for tok in re.findall(r'"[^"]+"|\'[^\']+\'|\S+', after_u) if not tok.startswith('-')]
				seg_is_full = len(pos_args) == 0
		# Python pytest / nosetests / tox
		elif re.search(r'(?i)(?:^|\s)(?:python(?:3(?:\.\d+)?)?(?:\.exe)?\s+-m\s+)?(?:pytest|nosetests|tox)(?:\.exe)?(?:\s|$)', s):
			seg_is_test = True
			filtered = bool(re.search(r'(?:\s-k\b|::)', s)) or _single_test_file_in_args(s)
			seg_is_full = not filtered
		# Node --test
		elif re.search(r'(?i)\bnode(?:\.exe)?\b[^\r\n]*\s--test\b', s):
			seg_is_test = True
			filtered = bool(re.search(r'--test-name-pattern\b', s)) or _single_test_file_in_args(s)
			seg_is_full = not filtered
		# npm / pnpm / yarn / bun test
		elif re.search(r'(?i)\b(?:npm|pnpm|yarn|bun)(?:\.cmd|\.exe)?\s+(?:run\s+)?test(?::[\w-]+)?(?:\s|$)', s):
			seg_is_test = True
			filtered = bool(re.search(r'(?:\s-t\b|\s--grep\b|\s--filter\b)', s)) or _single_test_file_in_args(s)
			seg_is_full = not filtered
		# vitest / jest / mocha / ava / tap / playwright / cypress
		elif re.search(r'(?i)(?:^|\s)(?:npx\s+)?(?:vitest|jest|mocha|ava|tap|playwright\s+test|cypress\s+run)(?:\.cmd|\.exe)?(?:\s|$)', s):
			seg_is_test = True
			filtered = bool(re.search(r'(?:\s-t\b|\s--grep\b|\s-g\b)', s)) or _single_test_file_in_args(s)
			seg_is_full = not filtered
		# PHPUnit / Pest / Codeception
		elif re.search(r'(?i)(?:^|\s|[/\\])(?:phpunit|pest|codecept)(?:\.bat|\.phar|\.exe)?(?:\s|$)', s):
			seg_is_test = True
			filtered = bool(re.search(r'--filter\b', s)) or _single_test_file_in_args(s)
			seg_is_full = not filtered
		# dotnet test
		elif re.search(r'(?i)\bdotnet(?:\.exe)?\s+test\b', s):
			seg_is_test = True
			seg_is_full = not bool(re.search(r'--filter\b', s))
		# go test
		elif re.search(r'(?i)\bgo(?:\.exe)?\s+test\b', s):
			seg_is_test = True
			seg_is_full = ('./...' in s) and (not bool(re.search(r'\s-run\b', s)))
		# cargo test
		elif re.search(r'(?i)\bcargo(?:\.exe)?\s+test\b', s):
			seg_is_test = True
			after_ct = re.split(r'(?i)\bcargo(?:\.exe)?\s+test\b', s, maxsplit=1)[1]
			pos_ct = [t for t in re.findall(r'"[^"]+"|\'[^\']+\'|\S+', after_ct) if not t.startswith('-') and '--' != t]
			seg_is_full = (not bool(re.search(r'--test\b', s))) and (len(pos_ct) == 0)
		# Maven / Gradle
		elif re.search(r'(?i)\b(?:mvn|mvnw|gradle|gradlew)(?:\.cmd|\.bat)?\b[^\r\n]*\btest\b', s):
			seg_is_test = True
			seg_is_full = not bool(re.search(r'(?:-Dtest=|--tests\b)', s))
		# Ruby rspec / rails test / rake test
		elif re.search(r'(?i)\b(?:rspec|rake\s+test|rails\s+test)\b', s):
			seg_is_test = True
			seg_is_full = (not bool(re.search(r'\s-e\b', s))) and (not _single_test_file_in_args(s))
		# Pester / bats / ctest / make test / just test
		elif re.search(r'(?i)\b(?:Invoke-Pester|bats|ctest|make\s+test|just\s+test)\b', s):
			seg_is_test = True
			seg_is_full = not _single_test_file_in_args(s)
		# Direct execution of a test script file (python test_foo.py, node foo.test.mjs, ./test-native.ps1, bash test_a.sh)
		elif not re.search(r'(?i)\bpython(?:3)?(?:\.exe)?\s+(?:-[A-Za-z]+\s+)*-c\b', s) and _single_test_file_in_args(s):
			if re.search(r'(?i)(?:^|\s)(?:&\s*)?(?:python(?:3)?|node|pwsh|powershell|bash|sh|php|ruby|ts-node|tsx|bun|deno)(?:\.exe)?\s+|^\s*(?:&\s*)?["\']?(?:[A-Za-z]:[/\\]|\.{1,2}[/\\])?[^\s"\']*(?:test|spec|regression)', s):
				seg_is_test = True
				seg_is_full = False
		if seg_is_test:
			is_test = True
			if seg_is_full:
				is_full = True
			targets.extend(_extract_cmd_paths(s))
	if is_test and (not is_full) and None is not scope_root:
		if count_repo_test_files(scope_root) <= 1:
			is_full = True
	return {'is_test_cmd': is_test, 'is_full_suite': is_full, 'rigged_failure': rigged, 'target_paths': list(dict.fromkeys(targets))}


def _uri_to_local_path(uri: str) -> Path | None:
	raw = (uri or '').strip()
	if not raw:
		return None
	if raw.lower().startswith('file:'):
		parsed = urlsplit(raw)
		p_str = unquote(parsed.path)
		if parsed.netloc and re.fullmatch(r'[A-Za-z]:', parsed.netloc):
			p_str = parsed.netloc + p_str
		elif re.match(r'^/[A-Za-z]:/', p_str):
			p_str = p_str[1:]
		return Path(p_str)
	return Path(raw)


def _infer_exit_code_from_log_text(text: str) -> int | None:
	if not text:
		return None
	m_ec = _EXIT_CODE_RE.search(text)
	if m_ec:
		return int(m_ec.group(1) or m_ec.group(2))
	if re.search(r'(?m)^FAILED\s*\(', text) or re.search(r'(?m)^FAIL\b', text) or re.search(r'(?i)\btest result:\s*FAILED\b|\bFAILURES!\b|\bERRORS!\b|\bFailed!\s*-\s*Failed:\s*[1-9]', text):
		return 1
	if re.search(r'(?m)^Ran\s+\d+\s+tests?\s+in\s+\d', text) and re.search(r'(?m)^OK(?:\s|\(|$)', text):
		return 0
	if re.search(r'(?i)\btest result:\s*ok\.\s*[1-9]\d*\s+passed;\s*0\s+failed\b|\bPassed!\s*-\s*Failed:\s*0,\s*Passed:\s*[1-9]|\bOK\s*\(\d+\s+tests?', text):
		return 0
	if re.search(r'(?m)^\d+\s+passed\b', text) and (not re.search(r'(?i)\b[1-9]\d*\s+(?:failed|errors?)\b', text)):
		return 0
	if re.search(r'[\u2139i]\s+fail\s+0\b', text) and re.search(r'[\u2139i]\s+tests\s+[1-9]\d*\b', text):
		return 0
	if re.search(r'[\u2139i]\s+fail\s+[1-9]\d*\b', text):
		return 1
	return None


def parse_command_outcome(outputs: list[str] | tuple[str, ...] | str, *, task_log_paths: list[Path] | None = None) -> dict:
	parts = [outputs] if isinstance(outputs, str) else [str(o) for o in (outputs or ()) if o]
	combined = '\n'.join(parts)
	bg_task_id = None
	m_tid = _BG_TASK_ID_RE.search(combined)
	if m_tid:
		bg_task_id = m_tid.group(1).strip().rstrip('.,')
	bg_log_path = None
	m_log = _BG_TASK_LOG_RE.search(combined)
	if m_log:
		lp = _uri_to_local_path(m_log.group(1))
		if None is not lp:
			bg_log_path = str(lp)
	exit_code = None
	for part in parts:
		header = _OUTPUT_BODY_SPLIT_RE.split(part, maxsplit=1)[0]
		m_hdr = _EXIT_CODE_RE.search(header)
		if m_hdr:
			exit_code = int(m_hdr.group(1) or m_hdr.group(2))
	extra_log_text = ''
	log_candidates: list[Path] = []
	if bg_log_path:
		log_candidates.append(Path(bg_log_path))
	for lp in (task_log_paths or ()):
		p_obj = Path(lp)
		if p_obj not in log_candidates:
			log_candidates.append(p_obj)
	if None is exit_code:
		for lp in log_candidates:
			try:
				if lp.is_file():
					txt = lp.read_text(encoding='utf-8', errors='replace')
					extra_log_text += '\n' + txt[-16000:]
					inferred = _infer_exit_code_from_log_text(txt[-16000:])
					if None is not inferred:
						exit_code = inferred
						break
			except OSError:
				continue
	if None is exit_code:
		exit_code = _infer_exit_code_from_log_text(combined)
	full_text = combined + extra_log_text
	is_inv_err = bool(_INVOCATION_ERROR_RE.search(full_text))
	ran_zero = bool(_ZERO_TESTS_RE.search(full_text))
	is_failure = (None is not exit_code) and (0 != exit_code) and (not is_inv_err)
	is_pass = (0 == exit_code) and (not ran_zero) and (not is_inv_err)
	return {
		'exit_code': exit_code,
		'is_failure': is_failure,
		'is_pass': is_pass,
		'is_invocation_error': is_inv_err,
		'ran_zero_tests': ran_zero,
		'background_task_id': bg_task_id,
		'background_log_path': bg_log_path,
	}


def is_substantive_test_content(path: str | Path, content: str) -> tuple[bool, str | None]:
	p = Path(str(path))
	if not isinstance(content, str) or not content.strip():
		return (False, f'Test file {p.name} is empty; write concrete behavioral assertions.')
	if p.name.lower() in _TEST_HELPER_FILENAMES:
		return (True, None)
	non_comment_lines = [
		ln.strip() for ln in content.splitlines()
		if ln.strip() and (not ln.strip().startswith(('#', '//', '/*', '*', '--', 'REM ', 'rem ')))
	]
	if not non_comment_lines:
		return (False, f'Test file {p.name} contains only comments and no executable tests.')
	has_assert = bool(_ASSERTION_LINE_RE.search(content))
	if '.py' == p.suffix.lower():
		try:
			tree = ast.parse(content)
			has_ast_assert = any(
				isinstance(node, ast.Assert)
				or (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and (node.func.attr.startswith('assert') or node.func.attr in ('raises', 'fail')))
				for node in ast.walk(tree)
			)
			has_assert = has_assert or has_ast_assert
		except SyntaxError:
			pass
	if not has_assert:
		return (False, f'Test file {p.name} contains no verifiable assertions or expectations (assertionless test stubs are prohibited).')
	return (True, None)


def _ast_expr_contains_code_literal(node: ast.AST) -> str | None:
	for sub in ast.walk(node):
		if isinstance(sub, ast.Constant) and isinstance(sub.value, str):
			m = _CODE_LIT_EXT_RE.search(sub.value)
			if m:
				lit = m.group(0)
				if (not is_test_file(lit)) and (not _TEMP_PATH_HINT_RE.search(lit)):
					return lit
	return None


def _ast_expr_uses_temp_base(node: ast.AST) -> bool:
	for sub in ast.walk(node):
		if isinstance(sub, ast.Name) and _TEMP_PATH_HINT_RE.search(sub.id):
			return True
		if isinstance(sub, ast.Attribute) and _TEMP_PATH_HINT_RE.search(sub.attr):
			return True
	return False


def _ast_expr_uses_repo_anchor(node: ast.AST) -> bool:
	for sub in ast.walk(node):
		if isinstance(sub, ast.Name) and sub.id in ('__file__', 'SCRIPT_DIR', 'SCRIPTS', 'PRIMARY', 'PRIMARY_AGENTS_DIR', 'REPO_ROOT', 'HARNESS_CODE'):
			return True
		if isinstance(sub, ast.Attribute) and sub.attr in ('PRIMARY', 'PRIMARY_AGENTS_DIR', 'HARNESS_CODE'):
			return True
	return False


def source_text_assertion_issues(
	path: str | Path,
	added_lines: list[str] | tuple[str, ...],
	*,
	full_content: str | None = None,
	added_line_numbers: set[int] | None = None,
) -> list[str]:
	p = Path(str(path))
	issues: list[str] = []
	if '.py' == p.suffix.lower() and isinstance(full_content, str) and full_content.strip():
		try:
			tree = ast.parse(full_content)
			# Track local variables bound to repo/production code paths and thin read-wrapper functions
			repo_anchor_vars: set[str] = set()
			for node in ast.walk(tree):
				if isinstance(node, ast.Assign) and _ast_expr_uses_repo_anchor(node.value):
					for tgt in node.targets:
						if isinstance(tgt, ast.Name):
							repo_anchor_vars.add(tgt.id)
				elif isinstance(node, ast.AnnAssign) and None is not node.value and isinstance(node.target, ast.Name) and _ast_expr_uses_repo_anchor(node.value):
					repo_anchor_vars.add(node.target.id)

			def _has_repo_anchor(expr: ast.AST) -> bool:
				if _ast_expr_uses_repo_anchor(expr):
					return True
				return any(isinstance(sub, ast.Name) and sub.id in repo_anchor_vars for sub in ast.walk(expr))

			var_code_lits: dict[str, str] = {}
			read_wrappers: dict[str, set[int]] = {}
			for node in ast.walk(tree):
				if isinstance(node, ast.Assign):
					lit_v = _ast_expr_contains_code_literal(node.value)
					if None is not lit_v and ((not _ast_expr_uses_temp_base(node.value)) or _has_repo_anchor(node.value)):
						for tgt in node.targets:
							if isinstance(tgt, ast.Name):
								var_code_lits[tgt.id] = lit_v
				elif isinstance(node, ast.AnnAssign) and None is not node.value and isinstance(node.target, ast.Name):
					lit_v = _ast_expr_contains_code_literal(node.value)
					if None is not lit_v and ((not _ast_expr_uses_temp_base(node.value)) or _has_repo_anchor(node.value)):
						var_code_lits[node.target.id] = lit_v
				elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
					param_names = [a.arg for a in node.args.args]
					matched_idxs: set[int] = set()
					for sub in ast.walk(node):
						if not isinstance(sub, ast.Call):
							continue
						sfn = sub.func
						s_read = isinstance(sfn, ast.Attribute) and sfn.attr in ('read_text', 'read_bytes')
						s_open = (isinstance(sfn, ast.Name) and 'open' == sfn.id) or (isinstance(sfn, ast.Attribute) and 'open' == sfn.attr)
						if not (s_read or s_open):
							continue
						s_tgt = sfn.value if s_read else (sub.args[0] if sub.args else None)
						if None is s_tgt or (_ast_expr_uses_temp_base(s_tgt) and (not _has_repo_anchor(s_tgt))):
							continue
						used_names = {n.id for n in ast.walk(s_tgt) if isinstance(n, ast.Name)}
						for p_idx, p_name in enumerate(param_names):
							if p_name in used_names:
								matched_idxs.add(p_idx)
					if matched_idxs:
						read_wrappers[node.name] = matched_idxs

			for node in ast.walk(tree):
				if not isinstance(node, ast.Call):
					continue
				lineno = getattr(node, 'lineno', None)
				if None is not added_line_numbers and None is not lineno and lineno not in added_line_numbers:
					continue
				fn = node.func
				if isinstance(fn, ast.Attribute) and fn.attr in ('getsource', 'getsourcelines'):
					issues.append(f'Behavioral test violation in {p.name}:{lineno}: inspect.{fn.attr}() reads source text instead of testing runtime behavior.')
					continue
				# Check calls to detected local read-wrapper helpers
				fn_name = fn.id if isinstance(fn, ast.Name) else (fn.attr if isinstance(fn, ast.Attribute) else None)
				if fn_name and fn_name in read_wrappers:
					for p_idx in read_wrappers[fn_name]:
						if p_idx < len(node.args):
							arg_expr = node.args[p_idx]
							w_lit = _ast_expr_contains_code_literal(arg_expr)
							if None is not w_lit and ((not _ast_expr_uses_temp_base(arg_expr)) or _has_repo_anchor(arg_expr)):
								issues.append(f'Behavioral test violation in {p.name}:{lineno}: helper "{fn_name}" reads production source file "{w_lit}" as text instead of executing its behavior.')
								break
				is_read_method = isinstance(fn, ast.Attribute) and fn.attr in ('read_text', 'read_bytes')
				is_open_call = (isinstance(fn, ast.Name) and 'open' == fn.id) or (isinstance(fn, ast.Attribute) and 'open' == fn.attr)
				if not (is_read_method or is_open_call):
					continue
				target_expr = fn.value if is_read_method else (node.args[0] if node.args else None)
				if None is target_expr:
					continue
				lit = _ast_expr_contains_code_literal(target_expr)
				if None is lit and isinstance(target_expr, ast.Name) and target_expr.id in var_code_lits:
					lit = var_code_lits[target_expr.id]
				if None is lit:
					continue
				if _ast_expr_uses_temp_base(target_expr) and (not _has_repo_anchor(target_expr)):
					continue
				issues.append(f'Behavioral test violation in {p.name}:{lineno}: test reads production source file "{lit}" as text instead of executing its behavior.')
			return issues
		except SyntaxError:
			pass
	for idx, raw_line in enumerate(added_lines or (), 1):
		line = str(raw_line)
		if re.search(r'\binspect\.getsource(?:lines)?\s*\(', line):
			issues.append(f'Behavioral test violation in {p.name} (added line {idx}): inspect.getsource reads source text instead of testing behavior.')
			continue
		for m in _SOURCE_TEXT_NONPY_READ_RE.finditer(line):
			lit = m.group(1)
			if is_test_file(lit) or _TEMP_PATH_HINT_RE.search(lit):
				continue
			if re.search(r'(?i)\b(?:tmp|temp|tmpdir|tmp_path|os\.tmpdir|mkdtemp|self\.root|TemporaryDirectory)\b', line):
				continue
			issues.append(f'Behavioral test violation in {p.name} (added line {idx}): test reads production source file "{lit}" as text instead of executing its behavior.')
	return issues


def validate_ratchet_reason(reason: str) -> tuple[bool, str | None]:
	cleaned = ' '.join((reason or '').strip().split())
	if 30 > len(cleaned):
		return (False, 'RATCHET-OK reason must be at least 30 characters explaining why the old expectation changed and by whose decision.')
	if _RATCHET_SLOP_RE.search(cleaned):
		return (False, 'RATCHET-OK reason cannot be a test-fitting excuse ("updating test to pass/match implementation"); cite the requirement/user decision or physical contract change.')
	return (True, None)


def _match_ratchet_target(target_spec: str, file_path: str | Path) -> bool:
	spec = _norm_posix((target_spec or '').strip().strip('`"\'')).lstrip('./').lower()
	if not spec:
		return False
	if '*' == spec or 'all' == spec:
		return True
	fp = _norm_posix(file_path).lstrip('./').lower()
	fp_name = Path(fp).name.lower()
	return fp == spec or fp.endswith('/' + spec) or fp_name == spec


def _parse_ratchet_ok_lines(body: str) -> list[tuple[str, str]]:
	out: list[tuple[str, str]] = []
	for m in _RATCHET_OK_LINE_RE.finditer(body or ''):
		rest = m.group(1).strip()
		m_split = re.match(r'^([^\s—–:-]+(?:/[^\s—–:-]+)*)\s*(?:—|–|--|:|-)\s*(.+)$', rest)
		if m_split and ('.' in m_split.group(1) or '/' in m_split.group(1) or '*' == m_split.group(1)):
			out.append((m_split.group(1).strip(), m_split.group(2).strip()))
		else:
			out.append(('*', rest))
	return out


def _load_turn_ratchet_receipts(project_root: Path | None) -> list[dict]:
	if None is project_root:
		return []
	from .path_registry import project_paths
	items: list[dict] = []
	turns_dirs = [Path(project_root) / '\ua616/data/turns', Path(project_root) / '_/\ua616/data/turns']
	try:
		td = project_paths(project_root).turns_dir
		if td not in turns_dirs:
			turns_dirs.insert(0, td)
	except (OSError, ValueError):
		pass
	for td in turns_dirs:
		if not td.is_dir():
			continue
		for rf in td.glob('*-ratchet-ok.json'):
			try:
				data = json.loads(rf.read_text(encoding='utf-8'))
			except (OSError, ValueError):
				continue
			raw_list = data.get('approvals') if isinstance(data, dict) else data
			if isinstance(raw_list, list):
				for entry in raw_list:
					if isinstance(entry, dict):
						items.append(entry)
	return items


def find_ratchet_approval(
	file_path: str | Path,
	*,
	repo_root: Path | None = None,
	project_root: Path | None = None,
	turn_receipts: list[dict] | None = None,
	issue_urls: list[str] | tuple[str, ...] = (),
) -> dict | None:
	receipts = list(turn_receipts or ())
	if None is not project_root:
		receipts.extend(_load_turn_ratchet_receipts(project_root))
	elif None is not repo_root:
		receipts.extend(_load_turn_ratchet_receipts(repo_root))
	for item in receipts:
		reason = str(item.get('reason') or '').strip()
		target = str(item.get('file') or item.get('target') or '').strip()
		ok, _ = validate_ratchet_reason(reason)
		if ok and _match_ratchet_target(target, file_path):
			return {'source': 'turn_receipt', 'file': target, 'reason': reason}
	from .issue_lifecycle import evidence_issue_files
	roots: list[Path] = []
	for cand in (project_root, repo_root):
		if None is not cand:
			rc = Path(cand).resolve()
			if rc not in roots:
				roots.append(rc)
	if not roots:
		roots.append(Path.cwd().resolve())
	base_root = roots[0]
	for raw_url in issue_urls or ():
		parsed = parse_issue_url(str(raw_url).strip())
		if None is parsed:
			continue
		slug, num = parsed
		for ev_path in evidence_issue_files(base_root, slug, f'issue-{num}.json', candidate_repos=roots):
			try:
				data = json.loads(ev_path.read_text(encoding='utf-8'))
				iss = data.get('issue') if isinstance(data, dict) and isinstance(data.get('issue'), dict) else data
				body = str((iss or {}).get('body') or '')
			except (OSError, ValueError):
				continue
			for target_spec, reason in _parse_ratchet_ok_lines(body):
				ok, _ = validate_ratchet_reason(reason)
				if ok and _match_ratchet_target(target_spec, file_path):
					return {'source': str(ev_path), 'issue_url': raw_url, 'file': target_spec, 'reason': reason}
	return None


def ratchet_diff_violations(
	rel_path: str,
	old_text: str,
	new_text: str | None,
	*,
	approval: dict | None = None,
) -> list[str]:
	if None is not approval:
		ok, _ = validate_ratchet_reason(str(approval.get('reason') or ''))
		if ok:
			return []
	if None is new_text:
		return [f'TDD-RATCHET: Deleting existing test file {rel_path} is prohibited without audited RATCHET-OK approval.']
	old_lines = old_text.splitlines()
	new_lines = new_text.splitlines()
	removed: list[str] = []
	added: list[str] = []
	for line in difflib.unified_diff(old_lines, new_lines, lineterm='', n=0):
		if line.startswith(('---', '+++', '@@')):
			continue
		if line.startswith('-'):
			removed.append(line[1:])
		elif line.startswith('+'):
			added.append(line[1:])
	added_counts = Counter(ln.strip() for ln in added if ln.strip())
	violations: list[str] = []
	for rem in removed:
		stripped = rem.strip()
		if not stripped or stripped.startswith(('#', '//', '/*', '*')):
			continue
		if added_counts[stripped] > 0:
			added_counts[stripped] -= 1
			continue
		if _TEST_DEF_RE.match(rem):
			violations.append(f'TDD-RATCHET: Existing test definition deleted or modified in {rel_path} ("{stripped[:100]}") without audited RATCHET-OK approval.')
		elif _ASSERTION_LINE_RE.search(rem):
			violations.append(f'TDD-RATCHET: Existing assertion deleted or altered in {rel_path} ("{stripped[:100]}") without audited RATCHET-OK approval.')
	old_skip_count = sum(1 for ln in old_lines if _SKIP_MARKER_RE.search(ln))
	new_skip_count = sum(1 for ln in new_lines if _SKIP_MARKER_RE.search(ln))
	if new_skip_count > old_skip_count:
		violations.append(f'TDD-RATCHET: Existing test file {rel_path} adds skip/ignore marker(s) ({old_skip_count} -> {new_skip_count}) without audited RATCHET-OK approval.')
	return violations


def shell_write_targets(cmd: str, *, cwd: Path | None = None, classifications: tuple[str, ...] | None = None) -> list[Path]:
	if not isinstance(cmd, str) or not cmd.strip():
		return []
	base = Path(cwd).resolve() if None is not cwd else Path.cwd().resolve()
	found: list[Path] = []
	seen: set[str] = set()
	allowed = set(classifications) if None is not classifications else None
	for seg in _split_shell_segments(cmd):
		for pat in _SHELL_WRITE_CMD_PATTERNS:
			for m in pat.finditer(seg):
				raw_target = next((g for g in m.groups() if g), '')
				if not raw_target or raw_target.startswith(('$', '&', '/dev/null', 'nul', 'NUL')):
					continue
				cand = normalize_host_path(raw_target)
				full = cand.resolve() if cand.is_absolute() else (base / cand).resolve()
				if None is allowed or classify_code_path(full) in allowed:
					key = full.as_posix().lower()
					if key not in seen:
						seen.add(key)
						found.append(full)
	return found


def shell_code_write_targets(cmd: str, *, cwd: Path | None = None) -> list[Path]:
	return shell_write_targets(cmd, cwd=cwd, classifications=('production',))


def shell_test_delete_targets(cmd: str, *, cwd: Path | None = None) -> list[Path]:
	if not isinstance(cmd, str) or not cmd.strip():
		return []
	base = Path(cwd).resolve() if None is not cwd else Path.cwd().resolve()
	found: list[Path] = []
	seen: set[str] = set()
	for seg in _split_shell_segments(cmd):
		if not _SHELL_DELETE_RE.search(seg):
			continue
		for m in _SHELL_TEST_FILE_TOKEN_RE.finditer(seg):
			raw_target = next((g for g in m.groups() if g), '')
			if not raw_target:
				continue
			cand = normalize_host_path(raw_target)
			full = cand.resolve() if cand.is_absolute() else (base / cand).resolve()
			if is_test_file(full):
				key = full.as_posix().lower()
				if key not in seen:
					seen.add(key)
					found.append(full)
	return found


def _unwrap_arg_value(val):
	if isinstance(val, str) and len(val) >= 2 and val[0] == '"' and val[-1] == '"':
		try:
			parsed = json.loads(val)
			if isinstance(parsed, str):
				return parsed
		except ValueError:
			pass
	return val


def _normalize_args_dict(raw_args) -> dict:
	parsed = raw_args
	if isinstance(parsed, str):
		try:
			parsed = json.loads(parsed)
		except ValueError:
			return {}
	if not isinstance(parsed, dict):
		return {}
	return {k: _unwrap_arg_value(v) for k, v in parsed.items()}


def _is_git_commit_command(cmd: str, *, cwd: Path | None = None) -> tuple[bool, Path | None]:
	if not isinstance(cmd, str) or 'git' not in cmd.lower():
		return (False, None)
	from .git_gate import resolve_git_repo_from_argv
	from .shell_audit import _iter_shell_git_segments
	for _, tokens in _iter_shell_git_segments(cmd):
		sub, _ = classify_git_argv(tokens)
		if 'commit' == sub:
			repo = resolve_git_repo_from_argv(tokens, cwd=cwd)
			return (True, repo)
	if re.search(r'\bsafe_commit\.py\b[^\r\n]*--execute\b', cmd):
		m_repo = re.search(r'--repo\s+(?:"([^"]+)"|\'([^\']+)\'|(\S+))', cmd)
		raw_r = (m_repo.group(1) or m_repo.group(2) or m_repo.group(3)) if m_repo else None
		repo = normalize_host_path(raw_r).resolve() if raw_r else (Path(cwd).resolve() if cwd else None)
		return (True, repo)
	return (False, None)


def _command_matches_scope(event: dict, scope_str: str, written_test_files: set[str]) -> bool:
	scope_p = Path(scope_str).resolve()
	scope_key = scope_p.as_posix().lower()
	cmd = str(event.get('cmd') or '')
	cmd_norm = _norm_posix(cmd).lower()
	targets = event.get('test_info', {}).get('target_paths') or []
	cwd_raw = event.get('cwd')
	cwd_p = Path(cwd_raw).resolve() if cwd_raw else None
	resolved_scopes: list[Path] = []
	for tp in targets:
		try:
			cand = normalize_host_path(tp)
			full = cand.resolve() if cand.is_absolute() else ((cwd_p / cand).resolve() if cwd_p else cand.resolve())
			resolved_scopes.append(resolve_code_scope(full))
		except OSError:
			continue
	if resolved_scopes:
		if any(rs.as_posix().lower() == scope_key or rs.is_relative_to(scope_p) or scope_p.is_relative_to(rs) for rs in resolved_scopes):
			return True
	for tf in written_test_files:
		tf_name = Path(tf).name.lower()
		tf_stem = Path(tf).stem.lower()
		if tf_name in cmd_norm or tf_stem in cmd_norm:
			return True
	if scope_key in cmd_norm:
		return True
	if None is not cwd_p:
		cwd_scope = resolve_code_scope(cwd_p)
		if cwd_scope.as_posix().lower() == scope_key or cwd_p.is_relative_to(scope_p) or scope_p.is_relative_to(cwd_p):
			if not resolved_scopes:
				return True
	return False


def build_command_tdd_event(step: int, cmd: str, outputs: list[str] | tuple[str, ...] | str, *, cwd: Path | None = None, scope_hint: Path | None = None) -> dict:
	eff_cwd = Path(cwd).resolve() if None is not cwd else None
	is_commit, commit_repo = _is_git_commit_command(cmd, cwd=eff_cwd)
	test_info = classify_test_command(cmd, scope_root=scope_hint)
	outcome = parse_command_outcome(outputs)
	return {
		'kind': 'command',
		'step': int(step),
		'cmd': str(cmd or ''),
		'cwd': str(eff_cwd) if None is not eff_cwd else '',
		'outcome': outcome,
		'test_info': test_info,
		'is_git_commit': is_commit,
		'commit_scope': str(commit_repo) if None is not commit_repo else None,
	}


def build_file_write_tdd_event(step: int, raw_path: str | Path, *, cwd: Path | None = None, content: str | None = None) -> dict:
	cand = normalize_host_path(raw_path)
	full = cand.resolve() if cand.is_absolute() else ((Path(cwd).resolve() / cand).resolve() if None is not cwd else cand.resolve())
	cls = classify_code_path(full, content=content)
	scope = resolve_code_scope(full) if 'non_code' != cls else full.parent
	return {
		'kind': 'file_write',
		'step': int(step),
		'path': str(full),
		'classification': cls,
		'scope': str(scope),
	}


def extract_antigravity_tdd_events(transcript_path: Path, *, cwd: Path | None = None) -> list[dict]:
	t_path = Path(transcript_path)
	if 'transcript.jsonl' == t_path.name:
		full_sib = t_path.parent / 'transcript_full.jsonl'
		if full_sib.is_file():
			t_path = full_sib
	if not t_path.is_file():
		return []
	try:
		rows = [json.loads(line) for line in t_path.read_text(encoding='utf-8', errors='replace').splitlines() if line.strip()]
	except (OSError, ValueError):
		return []
	last_user = -1
	for idx, row in enumerate(rows):
		if isinstance(row, dict) and 'USER_INPUT' == row.get('type'):
			last_user = idx
	segment = rows[last_user + 1:]
	events: list[dict] = []
	bg_task_index: dict[str, int] = {}
	for pos, row in enumerate(segment):
		if not isinstance(row, dict):
			continue
		step_idx = row.get('step_index') if isinstance(row.get('step_index'), int) else pos
		rtype = row.get('type')
		if rtype in ('SYSTEM_MESSAGE', 'EPHEMERAL_MESSAGE', 'GENERIC') and row.get('content'):
			c_str = str(row.get('content'))
			m_fin = _BG_TASK_FINISHED_RE.search(c_str)
			if m_fin:
				fin_tid = m_fin.group(1).strip()
				if fin_tid in bg_task_index:
					ev_idx = bg_task_index[fin_tid]
					events[ev_idx]['outcome'] = parse_command_outcome(m_fin.group(2))
		calls = [c for c in (row.get('tool_calls') or ()) if isinstance(c, dict)]
		if not calls:
			continue
		outputs: list[str] = []
		for nxt in segment[pos + 1:]:
			if not isinstance(nxt, dict):
				continue
			if nxt.get('type') in ('PLANNER_RESPONSE', 'USER_INPUT', 'CHECKPOINT'):
				break
			if 'GENERIC' == nxt.get('type') and nxt.get('content'):
				outputs.append(str(nxt.get('content')))
		for c_pos, call in enumerate(calls):
			cname = str(call.get('name') or '')
			cargs = _normalize_args_dict(call.get('args', {}))
			if cname in ('write_file', 'edit_file', 'write_to_file', 'replace_file_content', 'multi_replace_file_content'):
				raw_p = str(cargs.get('Path') or cargs.get('TargetFile') or cargs.get('AbsolutePath') or cargs.get('path') or '').strip()
				if raw_p:
					content_hint = cargs.get('Content') if 'write_file' == cname else None
					ev = build_file_write_tdd_event(step_idx, raw_p, cwd=cwd, content=content_hint if isinstance(content_hint, str) else None)
					if 'non_code' != ev['classification']:
						events.append(ev)
			elif 'run_command' == cname:
				cmd = str(cargs.get('CommandLine') or '').strip()
				if cmd:
					matched_outs = [outputs[c_pos]] if c_pos < len(outputs) else outputs
					ev = build_command_tdd_event(step_idx, cmd, matched_outs, cwd=cwd)
					ev_idx = len(events)
					events.append(ev)
					tid = ev['outcome'].get('background_task_id')
					if tid:
						bg_task_index[tid] = ev_idx
	return events


def evaluate_tdd_events(events: list[dict], *, require_final_full_green: bool = True) -> dict:
	from .failfast_gate import missing_failfast_flag
	scopes: dict[str, dict] = {}
	violations: list[str] = []
	failfast_warnings: list[str] = []

	def _ensure_scope(scope_str: str) -> dict:
		return scopes.setdefault(scope_str, {
			'state': 'IDLE',
			'written_tests': [],
			'written_test_step': None,
			'red_step': None,
			'red_cmd': None,
			'last_code_edit_step': None,
			'last_prod_edit_step': None,
			'touched_prod_files': [],
			'cycle_had_prod_edit': False,
			'any_prod_edit': False,
			'cycle_green_step': None,
			'last_full_green_step': None,
		})

	for ev in events or ():
		kind = ev.get('kind')
		step = int(ev.get('step', 0))
		if 'file_write' == kind:
			cls = ev.get('classification')
			scope_str = str(ev.get('scope') or '')
			fpath = str(ev.get('path') or '')
			if 'non_code' == cls or not scope_str:
				continue
			st = _ensure_scope(scope_str)
			if 'test' == cls:
				if fpath not in st['written_tests']:
					st['written_tests'].append(fpath)
				if st['state'] in ('IDLE', 'TEST_WRITTEN'):
					st['state'] = 'TEST_WRITTEN'
					st['written_test_step'] = step
				st['last_code_edit_step'] = step
			elif 'production' == cls:
				st['any_prod_edit'] = True
				if fpath not in st['touched_prod_files']:
					st['touched_prod_files'].append(fpath)
				if st['state'] not in ('RED_VERIFIED', 'GREEN_IMPLEMENTING'):
					if 'TEST_WRITTEN' == st['state']:
						violations.append(
							f'EXEC-2 TDD-RED-GATE: Production code "{fpath}" edited at step {step} after writing test(s), '
							'but no failing (RED) test run was observed after the test edit. Run the new test and observe it fail before writing production code.'
						)
					else:
						violations.append(
							f'EXEC-2 TDD-RED-GATE: Production code "{fpath}" edited at step {step} without first writing a test and observing it fail (RED).'
						)
				else:
					st['state'] = 'GREEN_IMPLEMENTING'
				st['cycle_had_prod_edit'] = True
				st['last_prod_edit_step'] = step
				st['last_code_edit_step'] = step
		elif 'command' == kind:
			outcome = ev.get('outcome') or {}
			if ev.get('is_git_commit') and (outcome.get('exit_code') in (0, None)):
				c_scope = ev.get('commit_scope')
				target_scopes = [s for s in scopes if (None is c_scope) or Path(s).resolve().as_posix().lower() == Path(c_scope).resolve().as_posix().lower()]
				for sk in target_scopes:
					st = scopes[sk]
					st['state'] = 'IDLE'
					st['written_test_step'] = None
					st['red_step'] = None
					st['red_cmd'] = None
					st['cycle_had_prod_edit'] = False
					st['cycle_green_step'] = None
				continue
			t_info = ev.get('test_info') or {}
			if not t_info.get('is_test_cmd') or t_info.get('rigged_failure'):
				continue
			if t_info.get('is_full_suite'):
				cmd_text = str(ev.get('cmd') or '')
				for seg in _split_shell_segments(cmd_text):
					miss = missing_failfast_flag(seg.strip())
					if None is not miss:
						warn = f'EXEC-2 fail-fast advisory: Full-suite command at step {step} ({miss[0]}) omitted "{miss[1]}"; prefer fail-fast or harness.py run-tests.'
						if warn not in failfast_warnings:
							failfast_warnings.append(warn)
						break
			for sk, st in scopes.items():
				if not _command_matches_scope(ev, sk, set(st['written_tests'])):
					continue
				# Re-check full suite awareness against actual scope root
				scope_full = bool(t_info.get('is_full_suite'))
				if not scope_full:
					scope_full = classify_test_command(str(ev.get('cmd') or ''), scope_root=Path(sk))['is_full_suite']
				if outcome.get('is_failure') and 'TEST_WRITTEN' == st['state'] and None is not st['written_test_step'] and step > st['written_test_step']:
					st['state'] = 'RED_VERIFIED'
					st['red_step'] = step
					st['red_cmd'] = ev.get('cmd')
				elif outcome.get('is_pass'):
					if None is not st['last_code_edit_step'] and step > st['last_code_edit_step']:
						st['cycle_green_step'] = step
						if scope_full:
							st['last_full_green_step'] = step
	if require_final_full_green:
		for sk, st in sorted(scopes.items()):
			if not st['any_prod_edit']:
				continue
			last_edit = st['last_code_edit_step']
			full_green = st['last_full_green_step']
			if None is full_green or (None is not last_edit and full_green <= last_edit):
				violations.append(
					f'EXEC-2 TDD-FULL-GATE: Repository "{sk}" has production code edits (last edit at step {last_edit}) '
					'without a subsequent passing (GREEN) full test suite run. Run the full test suite and verify all tests pass.'
				)
	r = {'verified': not violations, 'scopes': scopes, 'violations': violations}
	if failfast_warnings:
		r['failfast_warnings'] = failfast_warnings
	return r


def _git_head_text(repo_root: Path, rel_posix: str) -> str | None:
	if not (repo_root / '.git').exists():
		return None
	proc = subprocess.run(
		['git', '--no-optional-locks', '-C', str(repo_root), 'show', f'HEAD:{rel_posix}'],
		capture_output=True,
		env={**os.environ, 'GIT_OPTIONAL_LOCKS': '0'},
		check=False,
		creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0),
	)
	if 0 != proc.returncode:
		return None
	return proc.stdout.decode('utf-8', errors='replace')


def _git_index_text(repo_root: Path, rel_posix: str) -> str | None:
	if not (repo_root / '.git').exists():
		return None
	proc = subprocess.run(
		['git', '--no-optional-locks', '-C', str(repo_root), 'show', f':{rel_posix}'],
		capture_output=True,
		env={**os.environ, 'GIT_OPTIONAL_LOCKS': '0'},
		check=False,
		creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0),
	)
	if 0 != proc.returncode:
		return None
	return proc.stdout.decode('utf-8', errors='replace')


def _compute_edited_content(name: str, args: dict, target_path: Path) -> tuple[str | None, str | None, list[str], set[int]]:
	old_disk = target_path.read_text(encoding='utf-8', errors='replace') if target_path.is_file() else None
	if 'write_file' == name:
		new_text = args.get('Content')
		if not isinstance(new_text, str):
			return (old_disk, None, [], set())
	elif 'edit_file' == name:
		target_str = args.get('Target')
		repl_str = args.get('Replacement')
		if None is old_disk or (not isinstance(target_str, str)) or (not isinstance(repl_str, str)):
			return (old_disk, None, [], set())
		if target_str not in old_disk:
			return (old_disk, None, [], set())
		new_text = old_disk.replace(target_str, repl_str)
	else:
		return (old_disk, None, [], set())
	old_lines = (old_disk or '').splitlines()
	new_lines = new_text.splitlines()
	added_lines: list[str] = []
	added_line_nums: set[int] = set()
	sm = difflib.SequenceMatcher(None, old_lines, new_lines)
	for tag, _, _, j1, j2 in sm.get_opcodes():
		if tag in ('insert', 'replace'):
			for idx in range(j1, j2):
				added_lines.append(new_lines[idx])
				added_line_nums.add(idx + 1)
	return (old_disk, new_text, added_lines, added_line_nums)


def _active_turn_issue_urls(new_text: str | None, old_text: str | None) -> list[str]:
	urls: list[str] = []
	for blob in (new_text or '', old_text or ''):
		for u in _GITHUB_ISSUE_URL_RE.findall(blob):
			if u not in urls:
				urls.append(u)
	return urls


def evaluate_pre_tool_use_tdd(name: str, args: dict, payload: dict) -> str | None:
	cwd_raw = str(payload.get('cwd') or '').strip()
	cwd = Path(cwd_raw).resolve() if cwd_raw else None
	t_raw = str(payload.get('transcriptPath') or '').strip()
	events = extract_antigravity_tdd_events(Path(t_raw), cwd=cwd) if t_raw else []
	tdd_state = evaluate_tdd_events(events, require_final_full_green=False)
	if name in ('write_file', 'edit_file'):
		raw_p = str(args.get('Path') or '').strip()
		if not raw_p:
			return None
		cand = normalize_host_path(raw_p)
		target_path = cand.resolve() if cand.is_absolute() else ((cwd / cand).resolve() if cwd else cand.resolve())
		content_hint = args.get('Content') if 'write_file' == name and isinstance(args.get('Content'), str) else None
		cls = classify_code_path(target_path, content=content_hint)
		if 'non_code' == cls:
			return None
		scope = resolve_code_scope(target_path)
		scope_key = str(scope)
		sc_state = tdd_state['scopes'].get(scope_key)
		if 'production' == cls:
			if None is sc_state or sc_state.get('state') not in ('RED_VERIFIED', 'GREEN_IMPLEMENTING'):
				if None is not sc_state and 'TEST_WRITTEN' == sc_state.get('state'):
					return (
						f'EXEC-2 TDD-RED-GATE: Cannot write/edit production code "{target_path.name}" yet — '
						'test file(s) were edited, but no failing (RED) test run has been observed after the test edit. '
						'Run the test first and observe it fail before writing production code.'
					)
				return (
					f'EXEC-2 TDD-RED-GATE: Cannot write/edit production code "{target_path.name}" before writing a failing test. '
					'Strict TDD applies to all code: write a behavioral test first, run it to observe failure (RED), and only then implement production code.'
				)
			return None
		# Target is a test file ('test')
		old_disk, new_text, added_lines, added_line_nums = _compute_edited_content(name, args, target_path)
		if None is new_text:
			return None
		ok_sub, sub_err = is_substantive_test_content(target_path, new_text)
		if not ok_sub:
			return f'EXEC-2 TDD-SUBSTANTIVE-TEST-GATE: {sub_err}'
		behav_errs = source_text_assertion_issues(target_path, added_lines, full_content=new_text, added_line_numbers=added_line_nums)
		if behav_errs:
			return 'EXEC-2 TDD-BEHAVIORAL-GATE: ' + '; '.join(behav_errs[:3])
		try:
			rel_posix = target_path.relative_to(scope).as_posix()
		except ValueError:
			rel_posix = target_path.name
		issue_urls = _active_turn_issue_urls(new_text, old_disk)
		approval = find_ratchet_approval(rel_posix, repo_root=scope, project_root=cwd or scope, issue_urls=issue_urls)
		head_text = _git_head_text(scope, rel_posix)
		if None is not head_text:
			r_errs = ratchet_diff_violations(rel_posix, head_text, new_text, approval=approval)
			if r_errs:
				return 'EXEC-2 TDD-RATCHET-GATE: ' + '; '.join(r_errs[:3])
		# Anti-test-fitting guard: if production code was already edited in this cycle, block weakening even new test assertions
		if None is not old_disk and None is not sc_state and 'GREEN_IMPLEMENTING' == sc_state.get('state'):
			fit_errs = ratchet_diff_violations(rel_posix, old_disk, new_text, approval=approval)
			if fit_errs:
				return (
					'EXEC-2 TDD-ANTI-FITTING-GATE: Production code was already edited in this cycle; '
					'do not weaken or rewrite test assertions to fit the code! ' + '; '.join(fit_errs[:2])
				)
		return None
	if 'run_command' == name:
		cmd = str(args.get('CommandLine') or '')
		for target_p in shell_code_write_targets(cmd, cwd=cwd):
			scope = resolve_code_scope(target_p)
			sc_state = tdd_state['scopes'].get(str(scope))
			if None is sc_state or sc_state.get('state') not in ('RED_VERIFIED', 'GREEN_IMPLEMENTING'):
				return (
					f'EXEC-2 TDD-RED-GATE: Shell command writes production code file "{target_p.name}" '
					'before a failing (RED) test was written and observed. Write a failing test first.'
				)
		for del_test in shell_test_delete_targets(cmd, cwd=cwd):
			scope = resolve_code_scope(del_test)
			try:
				rel_posix = del_test.relative_to(scope).as_posix()
			except ValueError:
				rel_posix = del_test.name
			if None is not _git_head_text(scope, rel_posix):
				approval = find_ratchet_approval(rel_posix, repo_root=scope, project_root=cwd or scope)
				if None is approval:
					return f'EXEC-2 TDD-RATCHET-GATE: Deleting tracked test file "{rel_posix}" via shell command is prohibited without audited RATCHET-OK approval.'
		return None
	return None


def verify_staged_tdd_diff(
	repo_root: Path,
	staged_paths: list[str],
	*,
	message: str | None = None,
	project_root: Path | None = None,
	use_index: bool = False,
) -> list[str]:
	repo = Path(repo_root).resolve()
	violations: list[str] = []
	staged_prod: list[str] = []
	staged_tests: list[str] = []
	issue_urls: list[str] = []
	if message:
		issue_urls.extend(_GITHUB_ISSUE_URL_RE.findall(message))
	for rel in staged_paths or ():
		fpath = repo / rel
		head_text = _git_head_text(repo, rel)
		if use_index:
			disk_text = _git_index_text(repo, rel)
		else:
			disk_text = fpath.read_text(encoding='utf-8', errors='replace') if fpath.is_file() else None
		if None is not disk_text:
			cls = classify_code_path(fpath, content=disk_text)
			for u in _GITHUB_ISSUE_URL_RE.findall(disk_text):
				if u not in issue_urls:
					issue_urls.append(u)
		else:
			cls = classify_code_path(fpath, content=head_text)
		if 'production' == cls and None is not disk_text:
			staged_prod.append(rel)
		elif 'test' == cls:
			if None is not disk_text:
				staged_tests.append(rel)
				ok_sub, sub_err = is_substantive_test_content(fpath, disk_text)
				if not ok_sub:
					violations.append(f'EXEC-2 TDD-SUBSTANTIVE-TEST-GATE: {sub_err}')
				# Check newly added lines for behavioral test guard
				old_lines = (head_text or '').splitlines()
				new_lines = disk_text.splitlines()
				added_lines: list[str] = []
				added_nums: set[int] = set()
				for tag, _, _, j1, j2 in difflib.SequenceMatcher(None, old_lines, new_lines).get_opcodes():
					if tag in ('insert', 'replace'):
						for idx in range(j1, j2):
							added_lines.append(new_lines[idx])
							added_nums.add(idx + 1)
				for b_err in source_text_assertion_issues(fpath, added_lines, full_content=disk_text, added_line_numbers=added_nums):
					violations.append(f'EXEC-2 TDD-BEHAVIORAL-GATE: {b_err}')
			if None is not head_text:
				approval = find_ratchet_approval(rel, repo_root=repo, project_root=project_root or repo, issue_urls=issue_urls)
				for r_err in ratchet_diff_violations(rel, head_text, disk_text, approval=approval):
					violations.append(f'EXEC-2 {r_err}')
	if staged_prod and (not staged_tests):
		violations.append(
			f'EXEC-2 TDD-COMMIT-GATE: Staged commit modifies production code ({", ".join(staged_prod[:5])}) '
			'without staging any test file. Strict TDD requires writing failing behavioral tests alongside all code changes.'
		)
	return violations
