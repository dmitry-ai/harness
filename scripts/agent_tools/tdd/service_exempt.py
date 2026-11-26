# 2026-11-25 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from pathlib import Path
from typing import Any
import re
_SERVICE_HARNESS_CMD_RE = re.compile(r'(?i)^\s*(?:&\s*)?(?:python(?:3(?:\.\d+)?)?(?:\.exe)?\s+)?["\']?(?:[^"\']*[/\\])?(?:harness|upwork_project)\.py["\']?\s+(?:answer-check|answer-prepare|journal-sync|turn-begin|recover-checkpoint|recover-turn-violation|reconcile-unprepared-delivery|similar-project-exempt|tdd-check|issue-first-check|sync-conversation-title)(?:\s|$)')
_SERVICE_ISSUE_CMD_RE = re.compile(r'(?i)^\s*(?:&\s*)?(?:python(?:3(?:\.\d+)?)?(?:\.exe)?\s+)?["\']?(?:[^"\']*[/\\])?df_github_issue\.py["\']?\s+(?:create|edit|comment|close|fetch|list|audit)(?:\s|$)')
_SERVICE_WRITE_RE = re.compile(r'(?:^|/)\ua616/data/(?:scratch/[^/]+\.md|continuation\.md)$', re.IGNORECASE)
def _is_service_command(cmd: str, cwd: Path | None) -> bool:
	r = False
	if isinstance(cmd, str) and cmd.strip():
		from ..shell_audit import _split_shell_segments
		segs = [seg.strip() for seg in _split_shell_segments(cmd) if seg.strip()]
		if segs and all((bool(_SERVICE_HARNESS_CMD_RE.match(s) or _SERVICE_ISSUE_CMD_RE.match(s)) for s in segs)):
			from .commands import shell_code_write_targets, shell_test_delete_targets
			r = (not shell_code_write_targets(cmd, cwd=cwd)) and (not shell_test_delete_targets(cmd, cwd=cwd))
	return r
def _is_service_write_path(raw_path: str) -> bool:
	norm = raw_path.strip().replace('\\', '/')
	return bool(norm) and ('..' not in Path(norm).parts) and bool(_SERVICE_WRITE_RE.search(norm))
# 2026-11-26
# "Exempt service finalization calls from PreToolUse TDD gate and add journal-sync --all-open":
# https://github.com/dmitry-ai/harness/issues/256
def is_service_finalization_call(name: str, args: dict[str, Any], payload: dict[str, Any] | None=None) -> bool:
	if name in ('write_file', 'edit_file'):
		r = _is_service_write_path(str(args.get('Path') or ''))
	elif 'run_command' == name:
		cwd_raw = str((payload or {}).get('cwd') or '').strip()
		cwd = Path(cwd_raw).resolve() if cwd_raw else None
		r = _is_service_command(str(args.get('CommandLine') or ''), cwd)
	else:
		r = False
	return r
__all__ = ['is_service_finalization_call']