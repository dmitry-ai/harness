# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from pathlib import Path
from typing import Any
from Df.Harness.Tdd.CommandInspector import CommandInspector
import re
# 2026-11-26 "Move verification gate subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/381
# @used-by :mod:`agent_tools.tdd.service_exempt`
class ServiceExempt:
	__SERVICE_HARNESS_CMD_RE = re.compile(r'(?i)^\s*(?:&\s*)?(?:python(?:3(?:\.\d+)?)?(?:\.exe)?\s+)?["\']?(?:[^"\']*[/\\])?(?:harness|upwork_project)\.py["\']?\s+(?:answer-check|answer-prepare|journal-sync|turn-begin|recover-checkpoint|recover-turn-violation|reconcile-unprepared-delivery|similar-project-exempt|tdd-check|issue-first-check|sync-conversation-title)(?:\s|$)')
	__SERVICE_ISSUE_CMD_RE = re.compile(r'(?i)^\s*(?:&\s*)?(?:python(?:3(?:\.\d+)?)?(?:\.exe)?\s+)?["\']?(?:[^"\']*[/\\])?df_github_issue\.py["\']?\s+(?:create|edit|comment|close|fetch|list|audit)(?:\s|$)')
	__SERVICE_WRITE_RE = re.compile(r'(?:^|/)\ua616/data/(?:scratch/[^/]+\.md|continuation\.md)$', re.IGNORECASE)
	# @used-by :func:`agent_tools.tdd.service_exempt.is_service_finalization_call()`
	# @used-by :meth:`Df.Harness.Gate.TddPreToolGate.TddPreToolGate.check()`
	# @used-by :meth:`Df.Harness.Tdd.Enforcement.Enforcement.evaluate_pre_tool_use()`
	# @used-by :meth:`test_df_harness_s11_wave2b_tdd.DfHarnessS11Wave2bTddTests.test_tdd_enforcement_evaluator_events_and_guards()`
	# @used-by :meth:`test_df_harness_s11_wave2b_tdd_cov2.DfHarnessS11Wave2bTddCov2Tests.test_outcome_service_substantive_and_worktree_scope()`
	def is_exempt(self, name: str, args: dict[str, Any], payload: dict[str, Any] | None=None) -> bool:
		if name in ('write_file', 'edit_file'):
			r = ServiceExempt.__is_service_write_path(str(args.get('Path') or ''))
		elif 'run_command' == name:
			cwd_raw = str((payload or {}).get('cwd') or '').strip()
			cwd = Path(cwd_raw).resolve() if cwd_raw else None
			r = ServiceExempt.__is_service_command(str(args.get('CommandLine') or ''), cwd)
		else:
			r = False
		return r
	# @used-by :meth:`ServiceExempt.is_exempt()`
	@staticmethod
	def __is_service_command(cmd: str, cwd: Path | None) -> bool:
		r = False
		if isinstance(cmd, str) and cmd.strip():
			from agent_tools.shell_audit import _split_shell_segments
			segs = [seg.strip() for seg in _split_shell_segments(cmd) if seg.strip()]
			if segs and all((bool(ServiceExempt.__SERVICE_HARNESS_CMD_RE.match(s) or ServiceExempt.__SERVICE_ISSUE_CMD_RE.match(s)) for s in segs)):
				r = (not CommandInspector.shell_code_write_targets(cmd, cwd=cwd)) and (not CommandInspector.shell_test_delete_targets(cmd, cwd=cwd))
		return r
	# @used-by :meth:`ServiceExempt.is_exempt()`
	@staticmethod
	def __is_service_write_path(raw_path: str) -> bool:
		norm = raw_path.strip().replace('\\', '/')
		return bool(norm) and ('..' not in Path(norm).parts) and bool(ServiceExempt.__SERVICE_WRITE_RE.search(norm))
