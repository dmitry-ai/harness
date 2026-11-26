# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from pathlib import Path
from agent_tools.shell_audit import _split_shell_segments
from agent_tools.tdd.commands import _HARNESS_WATCHDOG_PREFIX_RE, _mask_quoted, unwrap_watchdog_prefix
from agent_tools.tdd_gate import classify_test_command
import re
# 2026-11-26 "Move verification gate subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/381
class FailfastGate:
	__DEFAULT_WATCHDOG_TIMEOUT = 300
	__HARNESS_SCRIPT = (Path(__file__).resolve().parents[3] / 'harness.py').as_posix()
	__MIN_SYNC_WAIT_MS = 5000
	__PYTEST_TIMEOUT_RE = re.compile(r'(?:^|\s)--timeout(?:=|\s+)\d')
	__QUOTED_RE = re.compile(r'"[^"]*"|\'[^\']*\'')
	__RUNNER_SPECS = (
		('harness-run-tests', re.compile(r'(?i)(?:^|\s)["\']?(?:[^"\']*[/\\])?(?:harness|upwork_project)\.py["\']?\s+run-tests\b'), re.compile(r'(?i)\brun-tests\b'), None),
		('unittest', re.compile(r'(?i)\bpython(?:3(?:\.\d+)?)?(?:\.exe)?\b[^\r\n]*\s-m\s+unittest(?:\s+discover)?\b'), re.compile(r'(?:^|\s)(?:--failfast\b|-[A-Za-z]*f[A-Za-z]*\b)'), '-f'),
		('pytest', re.compile(r'(?i)(?:^|\s)(?:python(?:3(?:\.\d+)?)?(?:\.exe)?\s+-m\s+)?pytest(?:\.exe)?\b'), re.compile(r'(?:^|\s)(?:-x\b|--exitfirst\b|--maxfail(?:=|\s+))'), '-x'),
		('js-test', re.compile(r'(?i)(?:^|\s)(?:npx\s+)?(?:vitest(?:\s+run)?|jest|mocha|ava|tap|playwright\s+test|cypress\s+run)(?:\.cmd|\.exe)?\b'), re.compile(r'(?:^|\s)(?:--bail(?:=|\s|$)|-b\b|--max-failures(?:=|\s+))'), '--bail'),
		('go-test', re.compile(r'(?i)\bgo(?:\.exe)?\s+test\b'), re.compile(r'(?:^|\s)-failfast\b'), '-failfast'),
		('phpunit', re.compile(r'(?i)(?:^|\s|[/\\])(?:phpunit|pest)(?:\.bat|\.phar|\.exe)?\b'), re.compile(r'(?:^|\s)(?:--stop-on-failure\b|--bail\b)'), '--stop-on-failure'),
		('rspec', re.compile(r'(?i)\brspec\b'), re.compile(r'(?:^|\s)(?:--fail-fast\b|--only-failures\b)'), '--fail-fast'),
	)
	__TARGET_SYNC_WAIT_MS = 10000
	__UNSAFE_WRAP_RE = re.compile(r'[$`><&|;(\r\n]')
	# @used-by :meth:`FailfastGate.__normalize_test_cmd()`
	@staticmethod
	def __apply_sync_wait(args: dict, overwrite: dict) -> None:
		if True is not args.get('IsDaemon'):
			wait_ms = FailfastGate.__parse_wait_ms(args.get('WaitMsBeforeAsync'))
			if None is wait_ms or FailfastGate.__MIN_SYNC_WAIT_MS > wait_ms:
				overwrite['WaitMsBeforeAsync'] = FailfastGate.__TARGET_SYNC_WAIT_MS
	# @used-by :meth:`FailfastGate.__normalize_test_cmd()`
	@staticmethod
	def __apply_timeout_guard(cur: str, segs: list[str], is_single: bool) -> tuple[str | None, str]:
		deny, out_cmd = (None, cur)
		miss_t = [mt for seg in segs if None is not (mt := FailfastGate.missing_timeout_guard(seg))]
		if miss_t:
			label, hint = miss_t[0]
			if is_single and FailfastGate.__is_safe_watchdog_wrap(cur):
				out_cmd = FailfastGate.__wrap_watchdog_cmd(cur)
			else:
				deny = f'Unbounded test command ({label}) omits a watchdog timeout and stdin detachment; use {hint}.'
		return (deny, out_cmd)
	# @used-by :meth:`FailfastGate.__normalize_test_cmd()`
	@staticmethod
	def __inject_missing_failfast(cmd: str, segs: list[str], is_single: bool) -> tuple[str | None, str]:
		deny, cur = (None, cmd)
		missing = [(seg, miss) for seg in segs if None is not (miss := FailfastGate.missing_failfast_flag(seg))]
		if missing:
			_, (label, flag, _) = missing[0]
			if not is_single:
				deny = f'Multi-segment test command ({label}) omits fail-fast flag "{flag}"; add "{flag}" or use harness.py run-tests.'
			else:
				m_cmd = FailfastGate.missing_failfast_flag(cur)
				if None is not m_cmd:
					pos = m_cmd[2].end()
					cur = f'{cur[:pos]} {flag}{cur[pos:]}'
		return (deny, cur)
	# @used-by :meth:`FailfastGate.__apply_timeout_guard()`
	@staticmethod
	def __is_safe_watchdog_wrap(cmd: str) -> bool:
		return not bool(FailfastGate.__UNSAFE_WRAP_RE.search(FailfastGate.__QUOTED_RE.sub('', cmd or '')))
	# @used-by :meth:`FailfastGate.evaluate()`
	@staticmethod
	def __normalize_test_cmd(cmd: str, args: dict) -> tuple[str | None, dict | None]:
		segs = [seg.strip() for seg in _split_shell_segments(cmd) if seg.strip()]
		unquoted = FailfastGate.__QUOTED_RE.sub('', cmd)
		is_single = (1 == len(segs)) and ('|' not in unquoted) and ('\n' not in unquoted)
		deny, cur = FailfastGate.__inject_missing_failfast(cmd, segs, is_single)
		overwrite: dict = {}
		if None is deny:
			deny, cur = FailfastGate.__apply_timeout_guard(cur, [cur.strip()] if is_single else segs, is_single)
		if None is deny:
			if cur != cmd:
				overwrite['CommandLine'] = cur
			FailfastGate.__apply_sync_wait(args, overwrite)
		return (deny, overwrite if overwrite else None)
	# @used-by :meth:`FailfastGate.__apply_sync_wait()`
	@staticmethod
	def __parse_wait_ms(raw) -> int | None:
		r = None
		if isinstance(raw, int) and (not isinstance(raw, bool)):
			r = raw
		elif isinstance(raw, str) and raw.strip().lstrip('-').isdigit():
			r = int(raw.strip())
		return r
	# @used-by :meth:`FailfastGate.__apply_timeout_guard()`
	@staticmethod
	def __wrap_watchdog_cmd(cmd: str) -> str:
		return f'python "{FailfastGate.__HARNESS_SCRIPT}" test-watchdog --timeout {FailfastGate.__DEFAULT_WATCHDOG_TIMEOUT} {cmd.strip()}'
	# @used-by :func:`agent_tools.failfast_gate.missing_failfast_flag()`
	# @used-by :meth:`FailfastGate.__inject_missing_failfast()`
	@staticmethod
	def missing_failfast_flag(seg: str) -> tuple[str, str, re.Match] | None:
		r = None
		if isinstance(seg, str) and seg.strip():
			inner = unwrap_watchdog_prefix(seg)
			prefix_len = len(seg) - len(inner)
			start = max(0, prefix_len - 1)
			masked_seg = _mask_quoted(seg)
			for label, anchor_re, has_re, flag in FailfastGate.__RUNNER_SPECS:
				hay = seg if 'harness-run-tests' == label else masked_seg
				m_anc = anchor_re.search(hay, start)
				if m_anc:
					if None is not flag and (not has_re.search(hay[prefix_len:])):
						r = (label, flag, m_anc)
					break
		return r
	# @used-by :func:`agent_tools.failfast_gate.missing_timeout_guard()`
	# @used-by :meth:`FailfastGate.__apply_timeout_guard()`
	@staticmethod
	def missing_timeout_guard(seg: str) -> tuple[str, str] | None:
		r = None
		if isinstance(seg, str) and seg.strip():
			s = seg.strip()
			if (not FailfastGate.__RUNNER_SPECS[0][1].search(s)) and (not _HARNESS_WATCHDOG_PREFIX_RE.match(s)):
				masked = _mask_quoted(s)
				if FailfastGate.__RUNNER_SPECS[1][1].search(masked):
					r = ('unittest', 'harness.py run-tests --module-timeout 300 or harness.py test-watchdog --timeout 300')
				elif FailfastGate.__RUNNER_SPECS[2][1].search(masked) and (not FailfastGate.__PYTEST_TIMEOUT_RE.search(masked)):
					r = ('pytest', '--timeout=<S> or harness.py test-watchdog --timeout 300')
		return r
	# @used-by :func:`agent_tools.failfast_gate.evaluate_pre_tool_use_test_failfast()`
	def evaluate(self, name: str, args: dict) -> tuple[str | None, dict | None]:
		r: tuple[str | None, dict | None] = (None, None)
		if 'run_command' == name:
			cmd = str(args.get('CommandLine') or '')
			if classify_test_command(cmd).get('is_test_cmd'):
				r = FailfastGate.__normalize_test_cmd(cmd, args)
		return r
