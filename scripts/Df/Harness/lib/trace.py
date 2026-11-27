# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from pathlib import Path
from typing import Any
import json
# 2026-11-26 "Create Df/Harness library for shared Harness helpers": https://github.com/dmitry-ai/harness/issues/379
# @used-by :func:`dfh_cmd_from_call()`
def _parse_call_args(raw_args: Any) -> dict[str, Any]:
	parsed = raw_args
	if isinstance(raw_args, str):
		try:
			parsed = json.loads(raw_args)
		except ValueError:
			parsed = {}
	return parsed if isinstance(parsed, dict) else {}
# @used-by :func:`agent_tools.cli_command_grounding._cmd_from_tool_call()`
# @used-by :func:`agent_tools.doc5_context._cmd_from_call()`
# @used-by :func:`agent_tools.verification_observability._cmd_from_call()`
# @used-by :meth:`test_df_harness_lib_s10.DfHarnessLibS10Tests.test_trace_and_timesheet_helpers()`
def dfh_cmd_from_call(call: dict[str, Any]) -> str:
	name = str(call.get('name') or '')
	r = ''
	if 'exec' == name or name.endswith(('run_command', 'exec_command')):
		args = _parse_call_args(call.get('args', call.get('arguments', {})))
		r = str(args.get('CommandLine') or args.get('cmd') or args.get('command') or '')
	return r
# @used-by :func:`agent_tools.meta.transcripts._extract_ag_transcript_info()`
# @used-by :func:`agent_tools.meta.transcripts._read_ag_rows()`
# @used-by :meth:`Df.Harness.Meta.TranscriptReader.TranscriptReader.read_ag_rows()`
# @used-by :meth:`test_df_harness_lib_s10.DfHarnessLibS10Tests.test_hook_and_transcript_callers_delegate_to_df_harness()`
# @used-by :meth:`test_df_harness_lib_s10.DfHarnessLibS10Tests.test_trace_and_timesheet_helpers()`
def dfh_read_ag_rows(path: Path) -> list[dict[str, Any]]:
	r: list[dict[str, Any]] = []
	try:
		lines = Path(path).read_text(encoding='utf-8', errors='replace').splitlines()
	except OSError:
		lines = []
	for ln in lines:
		if ln.strip():
			try:
				obj = json.loads(ln)
			except ValueError:
				obj = None
			if isinstance(obj, dict):
				r.append(obj)
	return r
# @used-by :func:`agent_tools.cli_command_grounding._collect_row_outputs()`
# @used-by :func:`agent_tools.doc5_context._row_outputs()`
# @used-by :func:`agent_tools.verification_observability._row_outputs()`
# @used-by :meth:`test_df_harness_lib_s10.DfHarnessLibS10Tests.test_trace_and_timesheet_helpers()`
def dfh_row_outputs(rows: list[dict[str, Any]], pos: int) -> list[str]:
	r: list[str] = []
	for cand in rows[pos + 1:]:
		if cand.get('type') in ('PLANNER_RESPONSE', 'USER_INPUT', 'CHECKPOINT'):
			break
		if 'GENERIC' == cand.get('type') and cand.get('content'):
			r.append(str(cand.get('content')))
	return r
