# 2026-11-24 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Enable parallel pytest-xdist full-suite execution and outcome parsing":
# https://github.com/dmitry-ai/harness/issues/178
# 2026-11-24 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# https://github.com/dmitry-ai/harness/issues/169
from __future__ import annotations
from pathlib import Path
from urllib.parse import unquote, urlsplit
import re
_BG_TASK_FINISHED_RE = re.compile(r'Task\s+id\s+"([^"]+)"\s+finished\s+with\s+result:\s*([\s\S]*)', re.IGNORECASE)
_BG_TASK_ID_RE = re.compile(r'task\s+id:\s*([A-Za-z0-9_./:-]+)', re.IGNORECASE)
_BG_TASK_LOG_RE = re.compile(r'(?:Task\s+logs\s+are\s+available\s+at|Log):\s*(file:///[^\s\'"<>]+)', re.IGNORECASE)
_EXIT_CODE_RE = re.compile(r'(?im)^(?:(?:Command|Process)\s+exited\s+with\s+code\s+(-?\d+)\.?|Exit\s+code:\s*(-?\d+))\s*$')
_FAIL_LOG_RE = re.compile(r'(?m:^FAILED(?:\s*\(|\s+\S)|^FAIL\b)|(?i:\btest result:\s*FAILED\b|\bFAILURES!\b|\bERRORS!\b|\bFailed!\s*-\s*Failed:\s*[1-9]|=+\s+[^=\n]*\b[1-9]\d*\s+(?:failed|errors?)\b[^=\n]*=+)')
_INVOCATION_ERROR_RE = re.compile(
	r'(?i)(?:is not recognized as an internal or external command'
	r'|is not recognized as the name of a cmdlet'
	r'|:\s*command not found\b'
	r'|error:\s*unrecognized arguments:'
	r'|no such option:'
	r'|no module named\s+(?:pytest|unittest|nose|tox)\b'
	r'|cannot find module\b[^.\n]*(?:jest|vitest|mocha))'
)
_NODE_FAIL_LOG_RE = re.compile(r'[\u2139i]\s+fail\s+[1-9]\d*\b')
_OUTPUT_BODY_SPLIT_RE = re.compile(r'(?m)^(?:Command output|Output):\s*$')
_ZERO_TESTS_RE = re.compile(
	r'(?i)(?:\bRan\s+0\s+tests?\s+in\b'
	r'|\bcollected\s+0\s+items\b'
	r'|\bno\s+tests\s+ran\b'
	r'|\b0\s+tests?\s+passed,\s*0\s+failed\b'
	r'|[\u2139i]\s+tests\s+0\b)'
)
def _collect_log_candidates(bg_log_path: str | None, task_log_paths: list[Path] | None) -> list[Path]:
	r: list[Path] = [Path(bg_log_path)] if bg_log_path else []
	for lp in task_log_paths or ():
		p_obj = Path(lp)
		if p_obj not in r:
			r.append(p_obj)
	return r
def _extract_bg_meta(combined: str) -> tuple[str | None, str | None]:
	m_tid = _BG_TASK_ID_RE.search(combined)
	bg_tid = m_tid.group(1).strip().rstrip('.,') if m_tid else None
	m_log = _BG_TASK_LOG_RE.search(combined)
	lp = _uri_to_local_path(m_log.group(1)) if m_log else None
	return (bg_tid, str(lp) if None is not lp else None)
def _header_exit_code(parts: list[str]) -> int | None:
	r = None
	for part in parts:
		header = _OUTPUT_BODY_SPLIT_RE.split(part, maxsplit=1)[0]
		m_hdr = _EXIT_CODE_RE.search(header)
		if m_hdr:
			r = int(m_hdr.group(1) or m_hdr.group(2))
	return r
def _infer_exit_code_from_log_text(text: str) -> int | None:
	r = None
	if text:
		m_ec = _EXIT_CODE_RE.search(text)
		if m_ec:
			r = int(m_ec.group(1) or m_ec.group(2))
		elif _FAIL_LOG_RE.search(text):
			r = 1
		elif _is_pass_log_text(text):
			r = 0
		elif _NODE_FAIL_LOG_RE.search(text):
			r = 1
	return r
def _infer_from_log_files(log_candidates: list[Path]) -> tuple[int | None, str]:
	exit_code = None
	extra = ''
	for lp in log_candidates:
		try:
			if lp.is_file():
				tail = lp.read_text(encoding='utf-8', errors='replace')[-16000:]
				extra += '\n' + tail
				inferred = _infer_exit_code_from_log_text(tail)
				if None is not inferred:
					exit_code = inferred
					break
		except OSError:
			continue
	return (exit_code, extra)
def _is_pass_log_text(text: str) -> bool:
	return bool(
		(re.search(r'(?m)^Ran\s+\d+\s+tests?\s+in\s+\d', text) and re.search(r'(?m)^OK(?:\s|\(|$)', text))
		or re.search(r'(?i)\btest result:\s*ok\.\s*[1-9]\d*\s+passed;\s*0\s+failed\b|\bPassed!\s*-\s*Failed:\s*0,\s*Passed:\s*[1-9]|\bOK\s*\(\d+\s+tests?', text)
		or (re.search(r'(?m)^(?:=+\s+[^=\n]*\b)?[1-9]\d*\s+passed\b', text) and (not re.search(r'(?i)\b[1-9]\d*\s+(?:failed|errors?)\b', text)))
		or (re.search(r'[\u2139i]\s+fail\s+0\b', text) and re.search(r'[\u2139i]\s+tests\s+[1-9]\d*\b', text))
	)
def _uri_to_local_path(uri: str) -> Path | None:
	raw = (uri or '').strip()
	if not raw:
		r = None
	elif not raw.lower().startswith('file:'):
		r = Path(raw)
	else:
		parsed = urlsplit(raw)
		p_str = unquote(parsed.path)
		if parsed.netloc and re.fullmatch(r'[A-Za-z]:', parsed.netloc):
			p_str = parsed.netloc + p_str
		elif re.match(r'^/[A-Za-z]:/', p_str):
			p_str = p_str[1:]
		r = Path(p_str)
	return r
def parse_command_outcome(outputs: list[str] | tuple[str, ...] | str, *, task_log_paths: list[Path] | None=None) -> dict:
	parts = [outputs] if isinstance(outputs, str) else [str(o) for o in (outputs or ()) if o]
	combined = '\n'.join(parts)
	bg_task_id, bg_log_path = _extract_bg_meta(combined)
	exit_code = _header_exit_code(parts)
	extra_log_text = ''
	if None is exit_code:
		exit_code, extra_log_text = _infer_from_log_files(_collect_log_candidates(bg_log_path, task_log_paths))
	if None is exit_code:
		exit_code = _infer_exit_code_from_log_text(combined)
	full_text = combined + extra_log_text
	is_inv_err = bool(_INVOCATION_ERROR_RE.search(full_text))
	has_fail_log = bool(_FAIL_LOG_RE.search(full_text) or _NODE_FAIL_LOG_RE.search(full_text))
	ran_zero = bool(_ZERO_TESTS_RE.search(full_text)) and (not has_fail_log)
	is_fail = (None is not exit_code) and (0 != exit_code) and (not is_inv_err) and (not ran_zero)
	is_pass = (0 == exit_code) and (not ran_zero) and (not is_inv_err)
	return {'background_log_path': bg_log_path, 'background_task_id': bg_task_id, 'exit_code': exit_code, 'is_failure': is_fail, 'is_invocation_error': is_inv_err, 'is_pass': is_pass, 'ran_zero_tests': ran_zero}
