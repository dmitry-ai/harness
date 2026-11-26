# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from pathlib import Path
from Df.Core.lib.array.other.unique_fast import dfa_unique_fast
from Df.Harness.Tdd.CodeClassifier import CodeClassifier
from agent_tools.shell_audit import _split_shell_segments, normalize_host_path
import re
# 2026-11-26 "Move verification gate subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/381
# @used-by :mod:`agent_tools.tdd.commands`
class CommandInspector:
	HARNESS_WATCHDOG_PREFIX_RE = re.compile(r'(?i)^\s*(?:python(?:3(?:\.\d+)?)?(?:\.exe)?\s+)?["\']?(?:[^"\']*[/\\])?(?:harness|upwork_project)\.py["\']?\s+test-watchdog(?:\s+(?:(?:--timeout|--module-timeout|--format)(?:=|\s+)\S+|--cwd(?:=|\s+)(?:"[^"]+"|\'[^\']+\'|\S+)))*(?:\s+--)?\s+')
	RIGGED_FAILURE_RE = re.compile(r'(?:(?:;|&&|\|\|)\s*(?:exit\s+[1-9]\d*|false\b|return\s+[1-9]\d*|throw\b)|;\s*exit\s+\$?1\b)', re.IGNORECASE)
	SHELL_DELETE_RE = re.compile(r'(?i)\b(?:git\s+rm|Remove-Item|rm|del|erase)\b[^\r\n;|&]*')
	SHELL_TEST_FILE_TOKEN_RE = re.compile(rf'(?:"([^"]+\.(?:{CodeClassifier.CODE_SUFFIX_ALT}))"|\'([^\']+\.(?:{CodeClassifier.CODE_SUFFIX_ALT}))\'|([^\s;|&"\']+\.(?:{CodeClassifier.CODE_SUFFIX_ALT})))', re.IGNORECASE)
	__BASH_HEREDOC_RE = re.compile(r'(<<-?\s*(?:[\'"]?)([A-Za-z_][A-Za-z0-9_]*)(?:[\'"]?)[^\r\n]*)\r?\n[\s\S]*?\r?\n[ \t]*\2(?=\r?\n|$)')
	__CARGO_TEST_RE = re.compile(r'(?i)\bcargo(?:\.exe)?\s+test\b')
	__DIRECT_SCRIPT_RE = re.compile(r'(?i)(?:^|\s)(?:&\s*)?(?:python(?:3)?|node|pwsh|powershell|bash|sh|php|ruby|ts-node|tsx|bun|deno)(?:\.exe)?\s+|^\s*(?:&\s*)?["\']?(?:[A-Za-z]:[/\\]|\.{1,2}[/\\])?[^\s"\']*(?:test|spec|regression)')
	__EMBEDDED_WRITE_PATTERNS = tuple(
		re.compile(pat) for pat in (
			r'(?i)\b(?:Set-Content|Out-File|Add-Content)\b[^\r\n;|&]*?(?:-Path|-LiteralPath|-FilePath)\s+(?:"([^"]+)"|\'([^\']+)\'|([^\s;|&]+))',
			r'(?i)\b(?:Set-Content|Out-File|Add-Content)\s+(?!-)(?:"([^"]+)"|\'([^\']+)\'|([^\s;|&]+))',
			r'(?i)\[System\.IO\.File\]::WriteAll(?:Text|Bytes|Lines)\s*\(\s*(?:"([^"]+)"|\'([^\']+)\')',
			r'(?i)\bPath\s*\(\s*(?:"([^"]+)"|\'([^\']+)\')\s*\)\s*\.\s*write_(?:text|bytes)\s*\(',
			r'(?i)\bopen\s*\(\s*(?:"([^"]+)"|\'([^\']+)\')\s*,\s*[\'"][wa][^\'"]*[\'"]',
		)
	)
	__GO_TEST_RE = re.compile(r'(?i)\bgo(?:\.exe)?\s+test\b')
	__HARNESS_RUN_TESTS_RE = re.compile(r'(?i)(?:^|\s)["\']?(?:[^"\']*[/\\])?(?:harness|upwork_project)\.py["\']?\s+run-tests(?:\s|$)')
	__INLINE_SCRIPT_RE = re.compile(r'(\b(?:python(?:3)?|node)(?:\.exe)?\s+(?:-[A-Za-z]+\s+)*-[ce]\s+)(?:"(?:\\.|[^"\\])*"|\'(?:\'\'|[^\'])*\')', re.I)
	__MASK_QUOTED_RE = re.compile(r'"[^"]*"|\'[^\']*\'')
	__PATTERN_ARG_RE = re.compile(r'(?:-p|--pattern)(?:\s+|=)(?:"([^"]+)"|\'([^\']+)\'|(\S+))')
	__POST_CARGO_RUNNER_SPECS = (
		(r'(?i)\b(?:mvn|mvnw|gradle|gradlew)(?:\.cmd|\.bat)?\b[^\r\n]*\btest\b', r'(?:-Dtest=|--tests\b)', False),
		(r'(?i)\b(?:rspec|rake\s+test|rails\s+test)\b', r'\s-e\b', True),
		(r'(?i)\b(?:Invoke-Pester|bats|ctest|make\s+test|just\s+test)\b', None, True),
	)
	__PRE_GO_RUNNER_SPECS = (
		(r'(?i)(?:^|\s)(?:python(?:3(?:\.\d+)?)?(?:\.exe)?\s+-m\s+)?(?:pytest|nosetests|tox)(?:\.exe)?(?:\s|$)', r'(?:\s-k\b|::)', True),
		(r'(?i)\bnode(?:\.exe)?\b[^\r\n]*\s--test\b', r'--test-name-pattern\b', True),
		(r'(?i)\b(?:npm|pnpm|yarn|bun)(?:\.cmd|\.exe)?\s+(?:run\s+)?test(?::[\w-]+)?(?:\s|$)', r'(?:\s-t\b|\s--grep\b|\s--filter\b)', True),
		(r'(?i)(?:^|\s)(?:npx\s+)?(?:vitest|jest|mocha|ava|tap|playwright\s+test|cypress\s+run)(?:\.cmd|\.exe)?(?:\s|$)', r'(?:\s-t\b|\s--grep\b|\s-g\b)', True),
		(r'(?i)(?:^|\s|[/\\])(?:phpunit|pest|codecept)(?:\.bat|\.phar|\.exe)?(?:\s|$)', r'--filter\b', True),
		(r'(?i)\bdotnet(?:\.exe)?\s+test\b', r'--filter\b', False),
	)
	__PS_HERESTRING_RE = re.compile(r"@'[\s\S]*?'@|@\"[\s\S]*?\"@")
	__PYTHON_C_RE = re.compile(r'(?i)\bpython(?:3)?(?:\.exe)?\s+(?:-[A-Za-z]+\s+)*-c\b')
	__PYTHON_UNITTEST_RE = re.compile(r'(?i)\bpython(?:3(?:\.\d+)?)?(?:\.exe)?\b[^\r\n]*\s-m\s+unittest\b')
	__SHELL_REDIRECT_RE = re.compile(r'(?i)(?:"(?:\\.|[^"\\])*"|\'(?:\\.|[^\'\\])*\'|(?:^|\s)#[^\r\n]*)|(?<![0-9&\-=>])>>?(?![</])\s*(?:"([^"]+)"|\'([^\']+)\'|([^\s;|&>]+))')
	__OUTER_SHELL_WRITE_PATTERNS = (
		__SHELL_REDIRECT_RE,
		*(
			re.compile(pat) for pat in (
				r'(?i)\btee\b(?:\s+-[a-zA-Z]+)*\s+(?:"([^"]+)"|\'([^\']+)\'|([^\s;|&]+))',
				r'(?i)\bsed\b[^\r\n;|&]*\s-i[^\s]*[^\r\n;|&]*\s+(?:"([^"]+)"|\'([^\']+)\'|([^\s;|&]+))\s*$',
				r'(?i)\b(?:Copy-Item|Move-Item|cp|mv)\b[^\r\n;|&]*\s+(?:"([^"]+)"|\'([^\']+)\'|([^\s;|&]+))\s*$',
			)
		),
	)
	SHELL_WRITE_CMD_PATTERNS = __EMBEDDED_WRITE_PATTERNS + __OUTER_SHELL_WRITE_PATTERNS
	# @used-by :func:`agent_tools.tdd.commands.classify_test_command()`
	# @used-by :meth:`Df.Harness.Gate.FailfastGate.FailfastGate.evaluate()`
	# @used-by :meth:`Df.Harness.Tdd.Evaluator.Evaluator.__update_scope_from_test_cmd()`
	# @used-by :meth:`Df.Harness.Tdd.EventsExtractor.EventsExtractor.build_command_event()`
	# @used-by :meth:`test_df_harness_s11_wave2b_tdd.DfHarnessS11Wave2bTddTests.test_tdd_classifier_commands_and_lexers()`
	def __init__(self, cmd: str, *, scope_root: Path | None=None) -> None:
		self.__cmd = cmd
		self.__scope_root = scope_root
	# @used-by :func:`agent_tools.tdd.commands.classify_test_command()`
	# @used-by :meth:`Df.Harness.Gate.FailfastGate.FailfastGate.evaluate()`
	# @used-by :meth:`Df.Harness.Tdd.Evaluator.Evaluator.__update_scope_from_test_cmd()`
	# @used-by :meth:`Df.Harness.Tdd.EventsExtractor.EventsExtractor.build_command_event()`
	# @used-by :meth:`test_df_harness_s11_wave2b_tdd.DfHarnessS11Wave2bTddTests.test_tdd_classifier_commands_and_lexers()`
	def classify_test_command(self) -> dict:
		if not isinstance(self.__cmd, str) or not self.__cmd.strip():
			r = {'is_full_suite': False, 'is_test_cmd': False, 'rigged_failure': False, 'target_paths': []}
		else:
			is_test, is_full, targets = (False, False, [])
			for seg in _split_shell_segments(self.__cmd):
				s = CommandInspector.unwrap_watchdog_prefix(seg.strip())
				if s:
					seg_test, seg_full = CommandInspector.__classify_segment(s)
					if seg_test:
						is_test = True
						is_full = is_full or seg_full
						targets.extend(CommandInspector.extract_cmd_paths(s))
			if is_test and (not is_full) and None is not self.__scope_root and 1 >= CodeClassifier.count_repo_test_files(self.__scope_root):
				is_full = True
			r = {'is_full_suite': is_full, 'is_test_cmd': is_test, 'rigged_failure': bool(CommandInspector.RIGGED_FAILURE_RE.search(self.__cmd)), 'target_paths': dfa_unique_fast(targets)}
		return r
	# @used-by :meth:`CommandInspector.classify_test_command()`
	@staticmethod
	def __classify_segment(seg: str) -> tuple[bool, bool]:
		r = (False, False)
		for matcher in (CommandInspector.__match_harness_run_tests, CommandInspector.__match_python_unittest, CommandInspector.__match_pre_go_runner, CommandInspector.__match_go_or_cargo, CommandInspector.__match_post_cargo_runner, CommandInspector.__match_direct_test_script):
			hit = matcher(seg)
			if None is not hit:
				r = (True, hit)
				break
		return r
	# @used-by :meth:`CommandInspector.shell_write_targets()`
	@staticmethod
	def __collect_write_matches(cmd: str) -> list[str]:
		r: list[str] = []
		for seg in _split_shell_segments(cmd):
			r.extend(CommandInspector.__iter_write_matches(seg, CommandInspector.__EMBEDDED_WRITE_PATTERNS))
		for seg in _split_shell_segments(CommandInspector.__strip_shell_herestrings(cmd)):
			r.extend(CommandInspector.__iter_write_matches(seg, CommandInspector.__OUTER_SHELL_WRITE_PATTERNS))
		return r
	# @used-by :meth:`CommandInspector.__match_harness_run_tests()`
	# @used-by :meth:`CommandInspector.__match_python_unittest()`
	@staticmethod
	def __extract_pattern_arg(seg: str) -> str | None:
		m_pat = CommandInspector.__PATTERN_ARG_RE.search(seg)
		return (m_pat.group(1) or m_pat.group(2) or m_pat.group(3)) if m_pat else None
	# @used-by :meth:`CommandInspector.shell_test_delete_targets()`
	@staticmethod
	def __iter_delete_tokens(seg: str) -> list[str]:
		r: list[str] = []
		if CommandInspector.SHELL_DELETE_RE.search(seg):
			for m in CommandInspector.SHELL_TEST_FILE_TOKEN_RE.finditer(seg):
				raw_target = next((g for g in m.groups() if g), '')
				if raw_target:
					r.append(raw_target)
		return r
	# @used-by :meth:`CommandInspector.__collect_write_matches()`
	@staticmethod
	def __iter_write_matches(seg: str, patterns: tuple[re.Pattern[str], ...]) -> list[str]:
		r: list[str] = []
		for pat in patterns:
			for m in pat.finditer(seg):
				raw_target = next((g for g in m.groups() if g), '')
				if raw_target and (not raw_target.startswith(('$', '&', '/dev/null', 'nul', 'NUL'))):
					r.append(raw_target)
		return r
	# @used-by :meth:`CommandInspector.__classify_segment()`
	@staticmethod
	def __match_direct_test_script(seg: str) -> bool | None:
		hit = (not CommandInspector.__PYTHON_C_RE.search(CommandInspector.mask_quoted(seg))) and CommandInspector.single_test_file_in_args(seg) and bool(CommandInspector.__DIRECT_SCRIPT_RE.search(seg))
		return False if hit else None
	# @used-by :meth:`CommandInspector.__classify_segment()`
	@staticmethod
	def __match_go_or_cargo(seg: str) -> bool | None:
		masked = CommandInspector.mask_quoted(seg)
		r = None
		if CommandInspector.__GO_TEST_RE.search(masked):
			r = ('./...' in seg) and (not bool(re.search(r'\s-run\b', masked)))
		elif CommandInspector.__CARGO_TEST_RE.search(masked):
			after_ct = CommandInspector.__CARGO_TEST_RE.split(masked, maxsplit=1)[1]
			pos_ct = [t for t in re.findall(r'\S+', after_ct) if not t.startswith('-') and '--' != t]
			r = (not bool(re.search(r'--test\b', masked))) and (0 == len(pos_ct))
		return r
	# @used-by :meth:`CommandInspector.__classify_segment()`
	@staticmethod
	def __match_harness_run_tests(seg: str) -> bool | None:
		r = None
		if CommandInspector.__HARNESS_RUN_TESTS_RE.search(seg):
			has_mod = bool(re.search(r'(?:\s--module(?:=|\s+))', seg))
			pat_val = CommandInspector.__extract_pattern_arg(seg)
			narrow_pat = (None is not pat_val) and ('*' not in pat_val) and ('?' not in pat_val)
			r = (not has_mod) and (not narrow_pat)
		return r
	# @used-by :meth:`CommandInspector.__classify_segment()`
	@staticmethod
	def __match_post_cargo_runner(seg: str) -> bool | None:
		return CommandInspector.__match_runner_specs(seg, CommandInspector.__POST_CARGO_RUNNER_SPECS)
	# @used-by :meth:`CommandInspector.__classify_segment()`
	@staticmethod
	def __match_pre_go_runner(seg: str) -> bool | None:
		return CommandInspector.__match_runner_specs(seg, CommandInspector.__PRE_GO_RUNNER_SPECS)
	# @used-by :meth:`CommandInspector.__classify_segment()`
	@staticmethod
	def __match_python_unittest(seg: str) -> bool | None:
		masked = CommandInspector.mask_quoted(seg)
		r = None
		if CommandInspector.__PYTHON_UNITTEST_RE.search(masked):
			pat_val = CommandInspector.__extract_pattern_arg(seg)
			if re.search(r'\bdiscover\b', masked):
				r = (None is pat_val) or ('*' in pat_val) or ('?' in pat_val)
			else:
				after_u = re.split(r'\bunittest\b', seg, maxsplit=1)[1]
				pos_args = [tok for tok in re.findall(r'"[^"]+"|\'[^\']+\'|\S+', after_u) if not tok.startswith('-')]
				r = 0 == len(pos_args)
		return r
	# @used-by :meth:`CommandInspector.__match_post_cargo_runner()`
	# @used-by :meth:`CommandInspector.__match_pre_go_runner()`
	@staticmethod
	def __match_runner_specs(seg: str, specs: tuple[tuple[str, str | None, bool], ...]) -> bool | None:
		masked = CommandInspector.mask_quoted(seg)
		r = None
		for cmd_re, filt_re, check_file in specs:
			if re.search(cmd_re, masked):
				filtered = (None is not filt_re and bool(re.search(filt_re, seg))) or (check_file and CommandInspector.single_test_file_in_args(seg))
				r = not filtered
				break
		return r
	# @used-by :meth:`CommandInspector.shell_test_delete_targets()`
	# @used-by :meth:`CommandInspector.shell_write_targets()`
	@staticmethod
	def __resolve_shell_target(raw_target: str, base: Path) -> Path:
		cand = normalize_host_path(raw_target)
		return cand.resolve() if cand.is_absolute() else (base / cand).resolve()
	# @used-by :meth:`CommandInspector.__collect_write_matches()`
	@staticmethod
	def __strip_shell_herestrings(cmd: str) -> str:
		r = CommandInspector.__PS_HERESTRING_RE.sub('""', cmd)
		r = CommandInspector.__BASH_HEREDOC_RE.sub(r'\1', r)
		return CommandInspector.__INLINE_SCRIPT_RE.sub(r'\1""', r)
	# @used-by :func:`agent_tools.tdd.commands._extract_cmd_paths()`
	# @used-by :meth:`CommandInspector.classify_test_command()`
	# @used-by :meth:`CommandInspector.single_test_file_in_args()`
	@staticmethod
	def extract_cmd_paths(seg: str) -> list[str]:
		r: list[str] = []
		for m in re.finditer(r'"([^"]+)"|\'([^\']+)\'|([^\s;|&]+)', seg):
			tok = m.group(1) or m.group(2) or m.group(3) or ''
			if tok and (not tok.startswith('-')) and ('/' in tok or '\\' in tok or re.search(rf'\.(?:{CodeClassifier.CODE_SUFFIX_ALT})$', tok, re.I)):
				r.append(tok)
		return r
	# @used-by :func:`agent_tools.tdd.commands._mask_quoted()`
	# @used-by :meth:`CommandInspector.__match_direct_test_script()`
	# @used-by :meth:`CommandInspector.__match_go_or_cargo()`
	# @used-by :meth:`CommandInspector.__match_python_unittest()`
	# @used-by :meth:`CommandInspector.__match_runner_specs()`
	# @used-by :meth:`Df.Harness.Gate.FailfastGate.FailfastGate.missing_failfast_flag()`
	# @used-by :meth:`Df.Harness.Gate.FailfastGate.FailfastGate.missing_timeout_guard()`
	@staticmethod
	def mask_quoted(seg: str) -> str:
		return CommandInspector.__MASK_QUOTED_RE.sub(lambda m: ' ' * len(m.group(0)), seg)
	# @used-by :func:`agent_tools.tdd.commands.shell_code_write_targets()`
	# @used-by :meth:`Df.Harness.Tdd.Enforcement.Enforcement.__eval_pre_run_command()`
	# @used-by :meth:`Df.Harness.Tdd.ServiceExempt.ServiceExempt.__is_service_command()`
	@staticmethod
	def shell_code_write_targets(cmd: str, *, cwd: Path | None=None) -> list[Path]:
		return CommandInspector.shell_write_targets(cmd, cwd=cwd, classifications=('production',))
	# @used-by :func:`agent_tools.tdd.commands.shell_test_delete_targets()`
	# @used-by :meth:`Df.Harness.Tdd.Enforcement.Enforcement.__eval_pre_run_command()`
	# @used-by :meth:`Df.Harness.Tdd.ServiceExempt.ServiceExempt.__is_service_command()`
	@staticmethod
	def shell_test_delete_targets(cmd: str, *, cwd: Path | None=None) -> list[Path]:
		r: list[Path] = []
		if isinstance(cmd, str) and cmd.strip():
			base = Path(cwd).resolve() if None is not cwd else Path.cwd().resolve()
			seen: set[str] = set()
			for seg in _split_shell_segments(cmd):
				for raw_target in CommandInspector.__iter_delete_tokens(seg):
					full = CommandInspector.__resolve_shell_target(raw_target, base)
					key = full.as_posix().lower()
					if CodeClassifier.is_test_file(full) and key not in seen:
						seen.add(key)
						r.append(full)
		return r
	# @used-by :func:`agent_tools.tdd.commands.shell_write_targets()`
	# @used-by :meth:`CommandInspector.shell_code_write_targets()`
	@staticmethod
	def shell_write_targets(cmd: str, *, cwd: Path | None=None, classifications: tuple[str, ...] | None=None) -> list[Path]:
		r: list[Path] = []
		if isinstance(cmd, str) and cmd.strip():
			base = Path(cwd).resolve() if None is not cwd else Path.cwd().resolve()
			seen: set[str] = set()
			allowed = set(classifications) if None is not classifications else None
			for raw_target in CommandInspector.__collect_write_matches(cmd):
				full = CommandInspector.__resolve_shell_target(raw_target, base)
				key = full.as_posix().lower()
				if (None is allowed or CodeClassifier(full).classify() in allowed) and key not in seen:
					seen.add(key)
					r.append(full)
		return r
	# @used-by :func:`agent_tools.tdd.commands._single_test_file_in_args()`
	# @used-by :meth:`CommandInspector.__match_direct_test_script()`
	# @used-by :meth:`CommandInspector.__match_runner_specs()`
	@staticmethod
	def single_test_file_in_args(seg: str) -> bool:
		r = False
		for tok in CommandInspector.extract_cmd_paths(seg):
			if '*' not in tok and '?' not in tok and CodeClassifier.is_test_file(tok):
				r = True
				break
		return r
	# @used-by :func:`agent_tools.tdd.commands.unwrap_watchdog_prefix()`
	# @used-by :meth:`CommandInspector.classify_test_command()`
	# @used-by :meth:`Df.Harness.Gate.FailfastGate.FailfastGate.missing_failfast_flag()`
	@staticmethod
	def unwrap_watchdog_prefix(seg: str) -> str:
		m = CommandInspector.HARNESS_WATCHDOG_PREFIX_RE.match(seg or '')
		return seg[m.end():] if m else (seg or '')
