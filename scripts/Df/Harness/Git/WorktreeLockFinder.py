# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from pathlib import Path
from typing import Any
from Df.Core.lib.fs import df_path_posix
from Df.Core.lib.state import df_is_windows
import json
import os
import subprocess
_NO_WINDOW = getattr(subprocess, 'CREATE_NO_WINDOW', 0)
_PS_PROC_QUERY = 'Get-CimInstance Win32_Process | Select-Object ProcessId,Name,CommandLine | ConvertTo-Json -Compress'
# 2026-11-26 "Move repository and grounding subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/382
class WorktreeLockFinder:
	# @used-by :func:`agent_tools.worktree_guard.find_worktree_lock_holders()`
	# @used-by :meth:`Df.Harness.Git.WorktreeRemovalGuard.WorktreeRemovalGuard.__find_holders()`
	# @used-by :meth:`test_df_harness_s11_wave2c_git.DfHarnessS11Wave2CGitTests.test_worktree_flow_guard_and_land()`
	# @used-by :meth:`test_df_harness_s11_wave2c_git.DfHarnessS11Wave2CGitTests.test_worktree_helper_branches_lease_and_fifo()`
	def __init__(self, wt_path: Path, *, process_rows: list[dict[str, Any]] | None=None) -> None:
		self.__wt_path = Path(wt_path).resolve()
		self.__process_rows = process_rows
	# @used-by :meth:`WorktreeLockFinder.__parse_row()`
	# @used-by :meth:`WorktreeLockFinder.find()`
	@staticmethod
	def __norm_posix(value: str | Path) -> str:
		return df_path_posix(value or '').casefold().rstrip('/')
	# @used-by :meth:`WorktreeLockFinder.find()`
	def __parse_row(self, row: dict[str, Any], target_posix: str, target_win: str) -> dict[str, Any] | None:
		r: dict[str, Any] | None = None
		if isinstance(row, dict):
			raw_pid = row.get('ProcessId') if None is not row.get('ProcessId') else row.get('pid')
			cmd = str(row.get('CommandLine') or row.get('command_line') or '').strip()
			if None is not raw_pid and cmd:
				try:
					pid = int(raw_pid)
				except (TypeError, ValueError):
					pid = 0
				if 0 < pid and os.getpid() != pid and (target_posix in self.__norm_posix(cmd) or target_win in cmd.casefold()):
					name = str(row.get('Name') or row.get('name') or 'unknown').strip()
					r = {'pid': pid, 'name': name, 'command_line': cmd[:300]}
		return r
	# @used-by :meth:`WorktreeLockFinder.find()`
	@staticmethod
	def __query_win32() -> list[dict[str, Any]]:
		r: list[dict[str, Any]] = []
		if df_is_windows():
			try:
				proc = subprocess.run(['powershell', '-NoProfile', '-Command', _PS_PROC_QUERY], stdin=subprocess.DEVNULL, capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=15, check=False, creationflags=_NO_WINDOW)
			except (OSError, subprocess.SubprocessError):
				proc = None
			if None is not proc and 0 == proc.returncode and proc.stdout.strip():
				try:
					parsed = json.loads(proc.stdout)
				except ValueError:
					parsed = []
				r = [parsed] if isinstance(parsed, dict) else (parsed if isinstance(parsed, list) else [])
		return r
	# @used-by :func:`Df.Harness.lib.native_codex_roles._match_owned_role_block()`
	# @used-by :func:`Df.Harness.lib.storage._iter_str_json_objects()`
	# @used-by :func:`agent_tools.cli_output_json._truncated_top_level_failure()`
	# @used-by :func:`agent_tools.grounding_domains.extract_fact_tuples()`
	# @used-by :func:`agent_tools.worktree_guard.find_worktree_lock_holders()`
	# @used-by :meth:`Df.Harness.Git.IssueActionExtractor.IssueActionExtractor.__decode_text()`
	# @used-by :meth:`Df.Harness.Git.WorktreeRemovalGuard.WorktreeRemovalGuard.__find_holders()`
	# @used-by :meth:`Df.Harness.Project.CardSyncer.CardSyncer.__insert_offset()`
	# @used-by :meth:`Df.Harness.Tdd.CLikeCommentLexer.CLikeCommentLexer.__php_html_segment()`
	# @used-by :meth:`Df.Harness.Tdd.CLikeCommentLexer.CLikeCommentLexer.consume_shebang()`
	# @used-by :meth:`Df.Harness.Tdd.CommentScanners.CommentScanners.__find_heredoc_end()`
	# @used-by :meth:`Df.Harness.Tdd.CommentScanners.CommentScanners.scan_cpp_raw()`
	# @used-by :meth:`Df.Harness.Tdd.CommentScanners.CommentScanners.scan_heredoc()`
	# @used-by :meth:`Df.Harness.Tdd.CommentScanners.CommentScanners.scan_line_block()`
	# @used-by :meth:`Df.Harness.Tdd.CommentScanners.CommentScanners.scan_line_comment()`
	# @used-by :meth:`Df.Harness.Tdd.CommentScanners.CommentScanners.scan_ps_herestring()`
	# @used-by :meth:`Df.Harness.Tdd.DiffContract.DiffContract.__parse_batch_blobs()`
	# @used-by :meth:`Df.Harness.Tdd.ExtCommentLexer.ExtCommentLexer.__scan_long_bracket()`
	# @used-by :meth:`Df.Harness.Tdd.ExtCommentLexer.ExtCommentLexer.__scan_rust_raw_str()`
	# @used-by :meth:`Df.Harness.Tdd.MarkupCommentLexer.MarkupCommentLexer.__consume_astro_frontmatter()`
	# @used-by :meth:`Df.Harness.Tdd.MarkupCommentLexer.MarkupCommentLexer.__sfc_html_segment()`
	# @used-by :meth:`Df.Harness.Upwork.DocxExtractor.DocxExtractor.__load_numbering()`
	# @used-by :meth:`Df.Harness.Upwork.DocxExtractor.DocxExtractor.__num_props()`
	# @used-by :meth:`Df.Harness.Upwork.DocxExtractor.DocxExtractor.__parse_paragraph()`
	# @used-by :meth:`Df.Harness.Upwork.DocxExtractor.DocxExtractor.__read_abstract_nums()`
	# @used-by :meth:`Df.Harness.Upwork.PdfExtractor.PdfExtractor.__collect_visual_lines()`
	# @used-by :meth:`test_df_harness_s11_wave2c_git.DfHarnessS11Wave2CGitTests.test_worktree_flow_guard_and_land()`
	# @used-by :meth:`test_df_harness_s11_wave2c_git.DfHarnessS11Wave2CGitTests.test_worktree_helper_branches_lease_and_fifo()`
	def find(self) -> list[dict[str, Any]]:
		rows = self.__process_rows if None is not self.__process_rows else self.__query_win32()
		target_posix = self.__norm_posix(self.__wt_path)
		target_win = str(self.__wt_path).casefold().rstrip('\\')
		found: list[dict[str, Any]] = []
		seen: set[int] = set()
		for row in rows:
			item = self.__parse_row(row, target_posix, target_win)
			if None is not item and item['pid'] not in seen:
				seen.add(item['pid'])
				found.append(item)
		return found
