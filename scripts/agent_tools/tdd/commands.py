# 2026-11-24 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from pathlib import Path
# 2026-11-26 "Replace duplicated Harness logic with Df helpers": https://github.com/dmitry-ai/harness/issues/337
from Df.Core.lib.array.other.unique_fast import dfa_unique_fast
from ..shell_audit import _split_shell_segments, normalize_host_path
from .classifier import _CODE_SUFFIX_ALT, classify_code_path, count_repo_test_files, is_test_file
import re
_BASH_HEREDOC_RE = re.compile(r'(<<-?\s*(?:[\'"]?)([A-Za-z_][A-Za-z0-9_]*)(?:[\'"]?)[^\r\n]*)\r?\n[\s\S]*?\r?\n[ \t]*\2(?=\r?\n|$)')
_CARGO_TEST_RE = re.compile(r'(?i)\bcargo(?:\.exe)?\s+test\b')
_DIRECT_SCRIPT_RE = re.compile(r'(?i)(?:^|\s)(?:&\s*)?(?:python(?:3)?|node|pwsh|powershell|bash|sh|php|ruby|ts-node|tsx|bun|deno)(?:\.exe)?\s+|^\s*(?:&\s*)?["\']?(?:[A-Za-z]:[/\\]|\.{1,2}[/\\])?[^\s"\']*(?:test|spec|regression)')
_EMBEDDED_WRITE_PATTERNS = tuple(
	re.compile(pat) for pat in (
		r'(?i)\b(?:Set-Content|Out-File|Add-Content)\b[^\r\n;|&]*?(?:-Path|-LiteralPath|-FilePath)\s+(?:"([^"]+)"|\'([^\']+)\'|([^\s;|&]+))',
		r'(?i)\b(?:Set-Content|Out-File|Add-Content)\s+(?!-)(?:"([^"]+)"|\'([^\']+)\'|([^\s;|&]+))',
		r'(?i)\[System\.IO\.File\]::WriteAll(?:Text|Bytes|Lines)\s*\(\s*(?:"([^"]+)"|\'([^\']+)\')',
		r'(?i)\bPath\s*\(\s*(?:"([^"]+)"|\'([^\']+)\')\s*\)\s*\.\s*write_(?:text|bytes)\s*\(',
		r'(?i)\bopen\s*\(\s*(?:"([^"]+)"|\'([^\']+)\')\s*,\s*[\'"][wa][^\'"]*[\'"]',
	)
)
_GO_TEST_RE = re.compile(r'(?i)\bgo(?:\.exe)?\s+test\b')
_HARNESS_RUN_TESTS_RE = re.compile(r'(?i)(?:^|\s)["\']?(?:[^"\']*[/\\])?(?:harness|upwork_project)\.py["\']?\s+run-tests(?:\s|$)')
_HARNESS_WATCHDOG_PREFIX_RE = re.compile(r'(?i)^\s*(?:python(?:3(?:\.\d+)?)?(?:\.exe)?\s+)?["\']?(?:[^"\']*[/\\])?(?:harness|upwork_project)\.py["\']?\s+test-watchdog(?:\s+(?:(?:--timeout|--module-timeout|--format)(?:=|\s+)\S+|--cwd(?:=|\s+)(?:"[^"]+"|\'[^\']+\'|\S+)))*(?:\s+--)?\s+')
_INLINE_SCRIPT_RE = re.compile(r'(\b(?:python(?:3)?|node)(?:\.exe)?\s+(?:-[A-Za-z]+\s+)*-[ce]\s+)(?:"(?:\\.|[^"\\])*"|\'(?:\'\'|[^\'])*\')', re.I)
_MASK_QUOTED_RE = re.compile(r'"[^"]*"|\'[^\']*\'')
_PATTERN_ARG_RE = re.compile(r'(?:-p|--pattern)(?:\s+|=)(?:"([^"]+)"|\'([^\']+)\'|(\S+))')
_POST_CARGO_RUNNER_SPECS = (
	(r'(?i)\b(?:mvn|mvnw|gradle|gradlew)(?:\.cmd|\.bat)?\b[^\r\n]*\btest\b', r'(?:-Dtest=|--tests\b)', False),
	(r'(?i)\b(?:rspec|rake\s+test|rails\s+test)\b', r'\s-e\b', True),
	(r'(?i)\b(?:Invoke-Pester|bats|ctest|make\s+test|just\s+test)\b', None, True),
)
_PRE_GO_RUNNER_SPECS = (
	(r'(?i)(?:^|\s)(?:python(?:3(?:\.\d+)?)?(?:\.exe)?\s+-m\s+)?(?:pytest|nosetests|tox)(?:\.exe)?(?:\s|$)', r'(?:\s-k\b|::)', True),
	(r'(?i)\bnode(?:\.exe)?\b[^\r\n]*\s--test\b', r'--test-name-pattern\b', True),
	(r'(?i)\b(?:npm|pnpm|yarn|bun)(?:\.cmd|\.exe)?\s+(?:run\s+)?test(?::[\w-]+)?(?:\s|$)', r'(?:\s-t\b|\s--grep\b|\s--filter\b)', True),
	(r'(?i)(?:^|\s)(?:npx\s+)?(?:vitest|jest|mocha|ava|tap|playwright\s+test|cypress\s+run)(?:\.cmd|\.exe)?(?:\s|$)', r'(?:\s-t\b|\s--grep\b|\s-g\b)', True),
	(r'(?i)(?:^|\s|[/\\])(?:phpunit|pest|codecept)(?:\.bat|\.phar|\.exe)?(?:\s|$)', r'--filter\b', True),
	(r'(?i)\bdotnet(?:\.exe)?\s+test\b', r'--filter\b', False),
)
_PS_HERESTRING_RE = re.compile(r"@'[\s\S]*?'@|@\"[\s\S]*?\"@")
_PYTHON_C_RE = re.compile(r'(?i)\bpython(?:3)?(?:\.exe)?\s+(?:-[A-Za-z]+\s+)*-c\b')
_PYTHON_UNITTEST_RE = re.compile(r'(?i)\bpython(?:3(?:\.\d+)?)?(?:\.exe)?\b[^\r\n]*\s-m\s+unittest\b')
_RIGGED_FAILURE_RE = re.compile(r'(?:(?:;|&&|\|\|)\s*(?:exit\s+[1-9]\d*|false\b|return\s+[1-9]\d*|throw\b)|;\s*exit\s+\$?1\b)', re.IGNORECASE)
_SHELL_DELETE_RE = re.compile(r'(?i)\b(?:git\s+rm|Remove-Item|rm|del|erase)\b[^\r\n;|&]*')
_SHELL_REDIRECT_RE = re.compile(r'(?i)(?:"(?:\\.|[^"\\])*"|\'(?:\\.|[^\'\\])*\'|(?:^|\s)#[^\r\n]*)|(?<![0-9&\-=>])>>?(?![</])\s*(?:"([^"]+)"|\'([^\']+)\'|([^\s;|&>]+))')
_SHELL_TEST_FILE_TOKEN_RE = re.compile(rf'(?:"([^"]+\.(?:{_CODE_SUFFIX_ALT}))"|\'([^\']+\.(?:{_CODE_SUFFIX_ALT}))\'|([^\s;|&"\']+\.(?:{_CODE_SUFFIX_ALT})))', re.IGNORECASE)
_OUTER_SHELL_WRITE_PATTERNS = (
	_SHELL_REDIRECT_RE,
	*(
		re.compile(pat) for pat in (
			r'(?i)\btee\b(?:\s+-[a-zA-Z]+)*\s+(?:"([^"]+)"|\'([^\']+)\'|([^\s;|&]+))',
			r'(?i)\bsed\b[^\r\n;|&]*\s-i[^\s]*[^\r\n;|&]*\s+(?:"([^"]+)"|\'([^\']+)\'|([^\s;|&]+))\s*$',
			r'(?i)\b(?:Copy-Item|Move-Item|cp|mv)\b[^\r\n;|&]*\s+(?:"([^"]+)"|\'([^\']+)\'|([^\s;|&]+))\s*$',
		)
	),
)
_SHELL_WRITE_CMD_PATTERNS = _EMBEDDED_WRITE_PATTERNS + _OUTER_SHELL_WRITE_PATTERNS
# @used-by :func:`classify_test_command()`
def _classify_segment(seg: str) -> tuple[bool, bool]:
	r = (False, False)
	for matcher in (_match_harness_run_tests, _match_python_unittest, _match_pre_go_runner, _match_go_or_cargo, _match_post_cargo_runner, _match_direct_test_script):
		hit = matcher(seg)
		if None is not hit:
			r = (True, hit)
			break
	return r
# @used-by :func:`shell_write_targets()`
def _collect_write_matches(cmd: str) -> list[str]:
	r: list[str] = []
	for seg in _split_shell_segments(cmd):
		r.extend(_iter_write_matches(seg, _EMBEDDED_WRITE_PATTERNS))
	for seg in _split_shell_segments(_strip_shell_herestrings(cmd)):
		r.extend(_iter_write_matches(seg, _OUTER_SHELL_WRITE_PATTERNS))
	return r
# @used-by :func:`_single_test_file_in_args()`
# @used-by :func:`classify_test_command()`
def _extract_cmd_paths(seg: str) -> list[str]:
	r: list[str] = []
	for m in re.finditer(r'"([^"]+)"|\'([^\']+)\'|([^\s;|&]+)', seg):
		tok = m.group(1) or m.group(2) or m.group(3) or ''
		if tok and (not tok.startswith('-')) and ('/' in tok or '\\' in tok or re.search(rf'\.(?:{_CODE_SUFFIX_ALT})$', tok, re.I)):
			r.append(tok)
	return r
# @used-by :func:`_match_harness_run_tests()`
# @used-by :func:`_match_python_unittest()`
def _extract_pattern_arg(seg: str) -> str | None:
	m_pat = _PATTERN_ARG_RE.search(seg)
	return (m_pat.group(1) or m_pat.group(2) or m_pat.group(3)) if m_pat else None
# @used-by :func:`shell_test_delete_targets()`
def _iter_delete_tokens(seg: str) -> list[str]:
	r: list[str] = []
	if _SHELL_DELETE_RE.search(seg):
		for m in _SHELL_TEST_FILE_TOKEN_RE.finditer(seg):
			raw_target = next((g for g in m.groups() if g), '')
			if raw_target:
				r.append(raw_target)
	return r
# @used-by :func:`_collect_write_matches()`
def _iter_write_matches(seg: str, patterns: tuple[re.Pattern[str], ...]=_SHELL_WRITE_CMD_PATTERNS) -> list[str]:
	r: list[str] = []
	for pat in patterns:
		for m in pat.finditer(seg):
			raw_target = next((g for g in m.groups() if g), '')
			if raw_target and (not raw_target.startswith(('$', '&', '/dev/null', 'nul', 'NUL'))):
				r.append(raw_target)
	return r
# @used-by :func:`_match_direct_test_script()`
# @used-by :func:`_match_go_or_cargo()`
# @used-by :func:`_match_python_unittest()`
# @used-by :func:`_match_runner_specs()`
# @used-by :func:`agent_tools.failfast_gate.missing_failfast_flag()`
# @used-by :func:`agent_tools.failfast_gate.missing_timeout_guard()`
def _mask_quoted(seg: str) -> str:
	return _MASK_QUOTED_RE.sub(lambda m: ' ' * len(m.group(0)), seg)
# @used-by :func:`_classify_segment()`
def _match_direct_test_script(seg: str) -> bool | None:
	hit = (not _PYTHON_C_RE.search(_mask_quoted(seg))) and _single_test_file_in_args(seg) and bool(_DIRECT_SCRIPT_RE.search(seg))
	return False if hit else None
# @used-by :func:`_classify_segment()`
def _match_go_or_cargo(seg: str) -> bool | None:
	masked = _mask_quoted(seg)
	r = None
	if _GO_TEST_RE.search(masked):
		r = ('./...' in seg) and (not bool(re.search(r'\s-run\b', masked)))
	elif _CARGO_TEST_RE.search(masked):
		after_ct = _CARGO_TEST_RE.split(masked, maxsplit=1)[1]
		pos_ct = [t for t in re.findall(r'\S+', after_ct) if not t.startswith('-') and '--' != t]
		r = (not bool(re.search(r'--test\b', masked))) and (0 == len(pos_ct))
	return r
# @used-by :func:`_classify_segment()`
def _match_harness_run_tests(seg: str) -> bool | None:
	r = None
	if _HARNESS_RUN_TESTS_RE.search(seg):
		has_mod = bool(re.search(r'(?:\s--module(?:=|\s+))', seg))
		pat_val = _extract_pattern_arg(seg)
		narrow_pat = (None is not pat_val) and ('*' not in pat_val) and ('?' not in pat_val)
		r = (not has_mod) and (not narrow_pat)
	return r
# @used-by :func:`_classify_segment()`
def _match_post_cargo_runner(seg: str) -> bool | None:
	return _match_runner_specs(seg, _POST_CARGO_RUNNER_SPECS)
# @used-by :func:`_classify_segment()`
def _match_pre_go_runner(seg: str) -> bool | None:
	return _match_runner_specs(seg, _PRE_GO_RUNNER_SPECS)
# @used-by :func:`_classify_segment()`
def _match_python_unittest(seg: str) -> bool | None:
	masked = _mask_quoted(seg)
	r = None
	if _PYTHON_UNITTEST_RE.search(masked):
		pat_val = _extract_pattern_arg(seg)
		if re.search(r'\bdiscover\b', masked):
			r = (None is pat_val) or ('*' in pat_val) or ('?' in pat_val)
		else:
			after_u = re.split(r'\bunittest\b', seg, maxsplit=1)[1]
			pos_args = [tok for tok in re.findall(r'"[^"]+"|\'[^\']+\'|\S+', after_u) if not tok.startswith('-')]
			r = 0 == len(pos_args)
	return r
# @used-by :func:`_match_post_cargo_runner()`
# @used-by :func:`_match_pre_go_runner()`
def _match_runner_specs(seg: str, specs: tuple[tuple[str, str | None, bool], ...]) -> bool | None:
	masked = _mask_quoted(seg)
	r = None
	for cmd_re, filt_re, check_file in specs:
		if re.search(cmd_re, masked):
			filtered = (None is not filt_re and bool(re.search(filt_re, seg))) or (check_file and _single_test_file_in_args(seg))
			r = not filtered
			break
	return r
# @used-by :func:`shell_test_delete_targets()`
# @used-by :func:`shell_write_targets()`
def _resolve_shell_target(raw_target: str, base: Path) -> Path:
	cand = normalize_host_path(raw_target)
	return cand.resolve() if cand.is_absolute() else (base / cand).resolve()
# @used-by :func:`_match_direct_test_script()`
# @used-by :func:`_match_runner_specs()`
def _single_test_file_in_args(seg: str) -> bool:
	r = False
	for tok in _extract_cmd_paths(seg):
		if '*' not in tok and '?' not in tok and is_test_file(tok):
			r = True
			break
	return r
# 2026-11-24
# "Strip PowerShell here-strings before shell redirect write-target scanning":
# https://github.com/dmitry-ai/harness/issues/221
# @used-by :func:`_collect_write_matches()`
def _strip_shell_herestrings(cmd: str) -> str:
	r = _PS_HERESTRING_RE.sub('""', cmd)
	r = _BASH_HEREDOC_RE.sub(r'\1', r)
	return _INLINE_SCRIPT_RE.sub(r'\1""', r)
# 2026-11-24
# "Decompose tdd_gate.py into modular TDD verification package":
# https://github.com/dmitry-ai/harness/issues/169
# @used-by :func:`agent_tools.failfast_gate.evaluate_pre_tool_use_test_failfast()`
# @used-by :func:`agent_tools.tdd.evaluator._update_scope_from_test_cmd()`
# @used-by :func:`agent_tools.tdd.events.build_command_tdd_event()`
# @used-by :meth:`test_df_harness_dedup_s8.DfHarnessDedupS8Tests.test_clean_null_and_unique_fast_delegation_to_df()`
# @used-by :meth:`test_parallel_runner.ParallelRunnerTests.test_classify_run_tests_full_and_filtered()`
# @used-by :meth:`test_parallel_test_runner.ParallelTestRunnerTests.test_classify_test_command_recognizes_harness_run_tests_full_and_filtered()`
# @used-by :meth:`test_pytest_xdist_runner.PytestXdistRunnerTests.test_classify_pytest_xdist_full_suite_and_filtered()`
# @used-by :meth:`test_tdd_decomposition.TddDecompositionTests.test_commands_module_behavior_and_parity()`
# @used-by :meth:`test_tdd_gate.TddGateCoreTests.test_chronological_tdd_state_machine_and_commit_reset()`
# @used-by :meth:`test_tdd_gate.TddGateCoreTests.test_test_command_detection_full_suite_vs_single_and_rigged_rejection()`
# @used-by :meth:`test_watchdog_and_timeout_gate.WatchdogAndTimeoutGateTests.test_non_test_command_mentioning_pytest_in_quoted_arg_is_ignored()`
# @used-by :meth:`test_watchdog_and_timeout_gate.WatchdogAndTimeoutGateTests.test_tdd_classify_unwraps_test_watchdog_prefix_for_scope_and_full_suite()`
# @used-by :mod:`agent_tools.tdd_gate`
# @used-by :mod:`agent_tools.tdd`
def classify_test_command(cmd: str, *, scope_root: Path | None=None) -> dict:
	if not isinstance(cmd, str) or not cmd.strip():
		r = {'is_full_suite': False, 'is_test_cmd': False, 'rigged_failure': False, 'target_paths': []}
	else:
		is_test, is_full, targets = (False, False, [])
		for seg in _split_shell_segments(cmd):
			s = unwrap_watchdog_prefix(seg.strip())
			if s:
				seg_test, seg_full = _classify_segment(s)
				if seg_test:
					is_test = True
					is_full = is_full or seg_full
					targets.extend(_extract_cmd_paths(s))
		if is_test and (not is_full) and None is not scope_root and 1 >= count_repo_test_files(scope_root):
			is_full = True
		# 2026-11-26 "Replace duplicated Harness logic with Df helpers": https://github.com/dmitry-ai/harness/issues/337
		r = {'is_full_suite': is_full, 'is_test_cmd': is_test, 'rigged_failure': bool(_RIGGED_FAILURE_RE.search(cmd)), 'target_paths': dfa_unique_fast(targets)}
	return r
# @used-by :func:`agent_tools.platforms.trace_common.record_normalized_tool_effects()`
# @used-by :func:`agent_tools.tdd.enforcement._eval_pre_run_command()`
# @used-by :func:`agent_tools.tdd.service_exempt._is_service_command()`
# @used-by :meth:`test_issue_first_gate.IssueFirstGateCoreTests.test_shell_write_targets_detects_test_production_and_doc_writes()`
# @used-by :meth:`test_shell_herestring_write_targets_m4.ShellHerestringWriteTargetsM4Tests.test_ignores_arrows_and_html_inside_powershell_herestring()`
# @used-by :meth:`test_shell_herestring_write_targets_m4.ShellHerestringWriteTargetsM4Tests.test_ignores_double_quoted_herestring_and_bash_heredoc_bodies()`
# @used-by :meth:`test_shell_herestring_write_targets_m4.ShellHerestringWriteTargetsM4Tests.test_preserves_real_shell_redirects_and_embedded_code_writes()`
# @used-by :meth:`test_tdd_decomposition.TddDecompositionTests.test_commands_module_behavior_and_parity()`
# @used-by :meth:`test_tdd_gate.TddGateCoreTests.test_shell_code_write_targets_and_ratchet_issue_evidence()`
# @used-by :mod:`agent_tools.tdd_gate`
# @used-by :mod:`agent_tools.tdd`
def shell_code_write_targets(cmd: str, *, cwd: Path | None=None) -> list[Path]:
	return shell_write_targets(cmd, cwd=cwd, classifications=('production',))
# @used-by :func:`agent_tools.tdd.enforcement._eval_pre_run_command()`
# @used-by :func:`agent_tools.tdd.service_exempt._is_service_command()`
# @used-by :meth:`test_tdd_decomposition.TddDecompositionTests.test_commands_module_behavior_and_parity()`
# @used-by :mod:`agent_tools.tdd_gate`
# @used-by :mod:`agent_tools.tdd`
def shell_test_delete_targets(cmd: str, *, cwd: Path | None=None) -> list[Path]:
	r: list[Path] = []
	if isinstance(cmd, str) and cmd.strip():
		base = Path(cwd).resolve() if None is not cwd else Path.cwd().resolve()
		seen: set[str] = set()
		for seg in _split_shell_segments(cmd):
			for raw_target in _iter_delete_tokens(seg):
				full = _resolve_shell_target(raw_target, base)
				key = full.as_posix().lower()
				if is_test_file(full) and key not in seen:
					seen.add(key)
					r.append(full)
	return r
# @used-by :func:`agent_tools.issue_first_bg._handle_run_command_call()`
# @used-by :func:`agent_tools.issue_first_gate.evaluate_pre_tool_use_issue_first()`
# @used-by :func:`agent_tools.platforms.trace_common.record_normalized_tool_effects()`
# @used-by :func:`shell_code_write_targets()`
# @used-by :meth:`test_issue_first_gate.IssueFirstGateCoreTests.test_shell_write_targets_detects_test_production_and_doc_writes()`
# @used-by :meth:`test_shell_herestring_write_targets_m4.ShellHerestringWriteTargetsM4Tests.test_ignores_arrows_and_html_inside_powershell_herestring()`
# @used-by :meth:`test_tdd_decomposition.TddDecompositionTests.test_commands_module_behavior_and_parity()`
# @used-by :mod:`agent_tools.tdd_gate`
# @used-by :mod:`agent_tools.tdd`
def shell_write_targets(cmd: str, *, cwd: Path | None=None, classifications: tuple[str, ...] | None=None) -> list[Path]:
	r: list[Path] = []
	if isinstance(cmd, str) and cmd.strip():
		base = Path(cwd).resolve() if None is not cwd else Path.cwd().resolve()
		seen: set[str] = set()
		allowed = set(classifications) if None is not classifications else None
		for raw_target in _collect_write_matches(cmd):
			full = _resolve_shell_target(raw_target, base)
			key = full.as_posix().lower()
			if (None is allowed or classify_code_path(full) in allowed) and key not in seen:
				seen.add(key)
				r.append(full)
	return r
# 2026-11-24
# "Enforce watchdog timeout and stdin isolation for unittest and pytest in failfast_gate":
# https://github.com/dmitry-ai/harness/issues/205
# @used-by :func:`agent_tools.failfast_gate.missing_failfast_flag()`
# @used-by :func:`classify_test_command()`
def unwrap_watchdog_prefix(seg: str) -> str:
	m = _HARNESS_WATCHDOG_PREFIX_RE.match(seg or '')
	return seg[m.end():] if m else (seg or '')
