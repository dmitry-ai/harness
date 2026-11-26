# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from pathlib import Path
from agent_tools.hook_runtime import read_last_user_segment
import json
# 2026-11-26 "Move verification gate subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/381
class BulkSourceReadGate:
	MAX_UNPERSISTED_SOURCE_READS = 10
	NAME = 'REVIEW-1-BULK-SOURCE-GATE'
	PRIORITY = 70
	TOOLS = frozenset({'read_file'})
	# @used-by :meth:`BulkSourceReadGate.check()`
	@staticmethod
	def __update_streak(streak: set[str], cname: str, cargs: dict) -> None:
		if 'invoke_subagent' == cname:
			streak.clear()
		elif cname in ('write_file', 'edit_file'):
			wpath = (cargs.get('Path') or '').replace('\\', '/').lower()
			if wpath.endswith('/kb/analysis.md') or '/\ua616/kb/' in wpath:
				streak.clear()
		elif 'read_file' == cname:
			rpath = (cargs.get('Path') or '').replace('\\', '/').lower()
			if rpath.endswith('/kb/source.md'):
				streak.add(rpath)
	# @used-by :func:`agent_tools.gates.bulk_source_read._parse_call_args()`
	# @used-by :meth:`BulkSourceReadGate.check()`
	# @used-by :meth:`Df.Harness.Gate.BrowserMcpGate.BrowserMcpGate.turn_has_background_mcp_new_page()`
	# @used-by :meth:`test_df_harness_s11_wave2b_gate.DfHarnessS11Wave2bGateTests.test_gate_pretool_classes_cover_all_guards()`
	@staticmethod
	def parse_call_args(raw) -> dict:
		r = raw if isinstance(raw, dict) else {}
		if isinstance(raw, str):
			try:
				parsed = json.loads(raw)
				r = parsed if isinstance(parsed, dict) else {}
			except ValueError:
				r = {}
		return r
	# @used-by :func:`agent_tools.gates.bulk_source_read._recent_segment_rows()`
	# @used-by :meth:`BulkSourceReadGate.check()`
	# @used-by :meth:`Df.Harness.Gate.BrowserMcpGate.BrowserMcpGate.turn_has_background_mcp_new_page()`
	@staticmethod
	def recent_segment_rows(t_path: Path) -> list[dict]:
		return read_last_user_segment(t_path)[2]
	# @used-by :func:`agent_tools.gates.bulk_source_read.check()`
	def check(self, name: str, args: dict, payload: dict | None=None) -> str | None:
		r = None
		target = (args.get('Path') or '').replace('\\', '/').lower() if 'read_file' == name else ''
		t_raw = (payload or {}).get('transcriptPath') or ''
		if target.endswith('/kb/source.md') and t_raw:
			streak: set[str] = set()
			for row in BulkSourceReadGate.recent_segment_rows(Path(t_raw)):
				for call in row.get('tool_calls') or []:
					if isinstance(call, dict):
						BulkSourceReadGate.__update_streak(streak, call.get('name', ''), BulkSourceReadGate.parse_call_args(call.get('args')))
			if target not in streak and BulkSourceReadGate.MAX_UNPERSISTED_SOURCE_READS <= len(streak):
				r = f'REVIEW-1 / KB-3: Already read {len(streak)} source.md files in a row without persisting analysis.md or delegating to af-worker (limit: {BulkSourceReadGate.MAX_UNPERSISTED_SOURCE_READS}). Persist analysis.md for already-read cases or delegate via invoke_subagent before reading more source.md files.'
		return r
