# 2026-11-24 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Enforce watchdog timeout and stdin isolation for unittest and pytest in failfast_gate":
# https://github.com/dmitry-ai/harness/issues/205
# 2026-11-23 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Enforce PreToolUse fail-fast normalization and block redundant schedule timers over run_command":
# https://github.com/dmitry-ai/harness/issues/162
from __future__ import annotations
from pathlib import Path
import json
import re
from .shell_audit import _split_shell_segments
from .tdd.commands import _HARNESS_WATCHDOG_PREFIX_RE, _mask_quoted, unwrap_watchdog_prefix
from .tdd_gate import _BG_TASK_FINISHED_RE, _BG_TASK_ID_RE, _normalize_args_dict, classify_test_command
_BG_TASK_ENDED_RE = re.compile(r'Task\s+id\s+"([^"]+)"\s+(?:finished|canceled|cancelled|terminated|killed)\b', re.IGNORECASE)
_DEFAULT_WATCHDOG_TIMEOUT = 300
_HARNESS_SCRIPT = (Path(__file__).resolve().parents[1] / 'harness.py').as_posix()
_MIN_SYNC_WAIT_MS = 5000
_PYTEST_TIMEOUT_RE = re.compile(r'(?:^|\s)--timeout(?:=|\s+)\d')
_QUOTED_RE = re.compile(r'"[^"]*"|\'[^\']*\'')
_RUNNER_SPECS = (
	('harness-run-tests', re.compile(r'(?i)(?:^|\s)["\']?(?:[^"\']*[/\\])?(?:harness|upwork_project)\.py["\']?\s+run-tests\b'), re.compile(r'(?i)\brun-tests\b'), None),
	('unittest', re.compile(r'(?i)\bpython(?:3(?:\.\d+)?)?(?:\.exe)?\b[^\r\n]*\s-m\s+unittest(?:\s+discover)?\b'), re.compile(r'(?:^|\s)(?:--failfast\b|-[A-Za-z]*f[A-Za-z]*\b)'), '-f'),
	('pytest', re.compile(r'(?i)(?:^|\s)(?:python(?:3(?:\.\d+)?)?(?:\.exe)?\s+-m\s+)?pytest(?:\.exe)?\b'), re.compile(r'(?:^|\s)(?:-x\b|--exitfirst\b|--maxfail(?:=|\s+))'), '-x'),
	('js-test', re.compile(r'(?i)(?:^|\s)(?:npx\s+)?(?:vitest(?:\s+run)?|jest|mocha|ava|tap|playwright\s+test|cypress\s+run)(?:\.cmd|\.exe)?\b'), re.compile(r'(?:^|\s)(?:--bail(?:=|\s|$)|-b\b|--max-failures(?:=|\s+))'), '--bail'),
	('go-test', re.compile(r'(?i)\bgo(?:\.exe)?\s+test\b'), re.compile(r'(?:^|\s)-failfast\b'), '-failfast'),
	('phpunit', re.compile(r'(?i)(?:^|\s|[/\\])(?:phpunit|pest)(?:\.bat|\.phar|\.exe)?\b'), re.compile(r'(?:^|\s)(?:--stop-on-failure\b|--bail\b)'), '--stop-on-failure'),
	('rspec', re.compile(r'(?i)\brspec\b'), re.compile(r'(?:^|\s)(?:--fail-fast\b|--only-failures\b)'), '--fail-fast'),
)
_TARGET_SYNC_WAIT_MS = 10000
_UNSAFE_WRAP_RE = re.compile(r'[$`><&|;(\r\n]')
def _active_turn_run_command_tasks(transcript_path: str) -> tuple[bool, set[str], set[str]]:
	explicit_schedule = False
	all_tids: set[str] = set()
	active_tids: set[str] = set()
	t_path = Path(transcript_path) if transcript_path else None
	if None is not t_path and 'transcript.jsonl' == t_path.name and (t_path.parent / 'transcript_full.jsonl').is_file():
		t_path = t_path.parent / 'transcript_full.jsonl'
	if None is not t_path and t_path.is_file():
		try:
			rows = [json.loads(line) for line in t_path.read_text(encoding='utf-8', errors='replace').splitlines() if line.strip()]
		except (OSError, ValueError):
			rows = []
		last_user = -1
		for idx, row in enumerate(rows):
			if isinstance(row, dict) and 'USER_INPUT' == row.get('type'):
				last_user = idx
		if 0 <= last_user:
			u_txt = str(rows[last_user].get('content') or '')
			explicit_schedule = bool(re.search(r'(?i)(?:^|\s)/schedule(?:\s|$)', u_txt))
		segment = rows[last_user + 1:] if 0 <= last_user else rows
		for pos, row in enumerate(segment):
			if not isinstance(row, dict):
				continue
			if row.get('type') in ('SYSTEM_MESSAGE', 'EPHEMERAL_MESSAGE', 'GENERIC') and row.get('content'):
				c_str = str(row.get('content'))
				for m_end in _BG_TASK_ENDED_RE.finditer(c_str):
					active_tids.discard(m_end.group(1).strip())
				m_fin = _BG_TASK_FINISHED_RE.search(c_str)
				if m_fin:
					active_tids.discard(m_fin.group(1).strip())
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
			for c_idx, call in enumerate(calls):
				if 'run_command' == str(call.get('name') or ''):
					matched = [outputs[c_idx]] if c_idx < len(outputs) else outputs
					for out_s in matched:
						for m_tid in _BG_TASK_ID_RE.finditer(out_s):
							tid = m_tid.group(1).strip().rstrip('.,')
							if tid:
								all_tids.add(tid)
								active_tids.add(tid)
	return (explicit_schedule, all_tids, active_tids)
def _apply_sync_wait(args: dict, overwrite: dict) -> None:
	if True is not args.get('IsDaemon'):
		wait_ms = _parse_wait_ms(args.get('WaitMsBeforeAsync'))
		if None is wait_ms or _MIN_SYNC_WAIT_MS > wait_ms:
			overwrite['WaitMsBeforeAsync'] = _TARGET_SYNC_WAIT_MS
def _apply_timeout_guard(cur: str, segs: list[str], is_single: bool) -> tuple[str | None, str]:
	deny, out_cmd = (None, cur)
	miss_t = [mt for seg in segs if None is not (mt := missing_timeout_guard(seg))]
	if miss_t:
		label, hint = miss_t[0]
		if is_single and _is_safe_watchdog_wrap(cur):
			out_cmd = _wrap_watchdog_cmd(cur)
		else:
			deny = f'Unbounded test command ({label}) omits a watchdog timeout and stdin detachment; use {hint}.'
	return (deny, out_cmd)
def _inject_missing_failfast(cmd: str, segs: list[str], is_single: bool) -> tuple[str | None, str]:
	deny, cur = (None, cmd)
	missing = [(seg, miss) for seg in segs if None is not (miss := missing_failfast_flag(seg))]
	if missing:
		_, (label, flag, _) = missing[0]
		if not is_single:
			deny = f'Multi-segment test command ({label}) omits fail-fast flag "{flag}"; add "{flag}" or use harness.py run-tests.'
		else:
			m_cmd = missing_failfast_flag(cur)
			if None is not m_cmd:
				pos = m_cmd[2].end()
				cur = f'{cur[:pos]} {flag}{cur[pos:]}'
	return (deny, cur)
def _is_safe_watchdog_wrap(cmd: str) -> bool:
	return not bool(_UNSAFE_WRAP_RE.search(_QUOTED_RE.sub('', cmd or '')))
def _parse_wait_ms(raw) -> int | None:
	r = None
	if isinstance(raw, int) and (not isinstance(raw, bool)):
		r = raw
	elif isinstance(raw, str) and raw.strip().lstrip('-').isdigit():
		r = int(raw.strip())
	return r
def _wrap_watchdog_cmd(cmd: str) -> str:
	return f'python "{_HARNESS_SCRIPT}" test-watchdog --timeout {_DEFAULT_WATCHDOG_TIMEOUT} {cmd.strip()}'
def evaluate_pre_tool_use_schedule(name: str, args: dict, payload: dict) -> str | None:
	r = None
	if 'schedule' == name and (not args.get('CronExpression')) and (True is not args.get('IsDaemon')) and (None is not args.get('DurationSeconds')):
		t_raw = str(payload.get('transcriptPath') or '').strip()
		explicit_schedule, all_tids, active_tids = _active_turn_run_command_tasks(t_raw)
		if not explicit_schedule:
			cond = str(args.get('TimerCondition') or '').strip()
			if cond and cond in all_tids:
				r = f'EXEC-4-SCHEDULE-GATE: Do not attach a schedule timer to run_command task "{cond}"; run_command already delivers reactive completion notifications. Use in-process timeouts such as harness.py run-tests --module-timeout instead.'
			elif active_tids:
				joined = ', '.join(sorted(active_tids))
				r = f'EXEC-4-SCHEDULE-GATE: Active background run_command task(s) ({joined}) already deliver reactive completion notifications; do not attach a one-shot schedule timer over active run_command tasks.'
	return r
def evaluate_pre_tool_use_test_failfast(name: str, args: dict) -> tuple[str | None, dict | None]:
	deny_reason, overwrite = (None, {})
	if 'run_command' == name:
		cmd = str(args.get('CommandLine') or '')
		if classify_test_command(cmd).get('is_test_cmd'):
			segs = [seg.strip() for seg in _split_shell_segments(cmd) if seg.strip()]
			unquoted = _QUOTED_RE.sub('', cmd)
			is_single = (1 == len(segs)) and ('|' not in unquoted) and ('\n' not in unquoted)
			deny_reason, cur_cmd = _inject_missing_failfast(cmd, segs, is_single)
			if None is deny_reason:
				deny_reason, cur_cmd = _apply_timeout_guard(cur_cmd, [cur_cmd.strip()] if is_single else segs, is_single)
			if None is deny_reason and cur_cmd != cmd:
				overwrite['CommandLine'] = cur_cmd
			if None is deny_reason:
				_apply_sync_wait(args, overwrite)
	return (deny_reason, overwrite if overwrite else None)
def missing_failfast_flag(seg: str) -> tuple[str, str, re.Match] | None:
	r = None
	if isinstance(seg, str) and seg.strip():
		inner = unwrap_watchdog_prefix(seg)
		prefix_len = len(seg) - len(inner)
		start = max(0, prefix_len - 1)
		masked_seg = _mask_quoted(seg)
		for label, anchor_re, has_re, flag in _RUNNER_SPECS:
			hay = seg if 'harness-run-tests' == label else masked_seg
			m_anc = anchor_re.search(hay, start)
			if m_anc:
				if None is not flag and (not has_re.search(hay[prefix_len:])):
					r = (label, flag, m_anc)
				break
	return r
def missing_timeout_guard(seg: str) -> tuple[str, str] | None:
	r = None
	if isinstance(seg, str) and seg.strip():
		s = seg.strip()
		if (not _RUNNER_SPECS[0][1].search(s)) and (not _HARNESS_WATCHDOG_PREFIX_RE.match(s)):
			masked = _mask_quoted(s)
			if _RUNNER_SPECS[1][1].search(masked):
				r = ('unittest', 'harness.py run-tests --module-timeout 300 or harness.py test-watchdog --timeout 300')
			elif _RUNNER_SPECS[2][1].search(masked) and (not _PYTEST_TIMEOUT_RE.search(masked)):
				r = ('pytest', '--timeout=<S> or harness.py test-watchdog --timeout 300')
	return r
