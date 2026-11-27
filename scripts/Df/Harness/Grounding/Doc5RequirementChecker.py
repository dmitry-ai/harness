# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from pathlib import Path
from typing import Any
from Df.Harness.Issue.RepoLocator import RepoLocator, V2_CODE_RELS
from Df.Harness.lib.trace import dfh_cmd_from_call, dfh_row_outputs
import re
# 2026-11-26 "Move repository and grounding subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/382
_EXCLUDED_CLI_RE = re.compile(r'\b(?:pytest|unittest|run-tests|test-watchdog|perf-profile-tests|answer-check|answer-prepare|tdd-check|issue-first-check|analysis-check|rules-audit|collect|collect-http|collect-browser|xref-check|git-read)\b', re.IGNORECASE)
_HARNESS_CLI_RE = re.compile(r'(?:harness|upwork_project|df_github_issue|validate_step)\.py', re.IGNORECASE)
class Doc5RequirementChecker:
	# @used-by :func:`agent_tools.doc5_context.turn_requires_doc5_problem_analysis()`
	# @used-by :meth:`Df.Harness.Grounding.Doc5ContextDetector.Doc5ContextDetector.__requires_doc5()`
	# @used-by :meth:`test_df_harness_s11_wave2c_grounding.DfHarnessS11Wave2CGroundingTests.test_cli_command_and_doc5_requirement_auditors()`
	def __init__(self, turn_context: dict | None) -> None:
		self.__turn_context = turn_context
	# @used-by :meth:`Doc5RequirementChecker.is_required()`
	@classmethod
	def __earliest_cli_failure_step(cls, turn: dict[str, Any], native: dict[str, Any] | None) -> int | None:
		from agent_tools.hook_crash_audit import _load_turn_rows
		rows = _load_turn_rows(native, turn)
		bg_steps: dict[str, int] = {}
		hits: list[int] = []
		for pos, row in enumerate(rows):
			calls = [c for c in (row.get('tool_calls') or ()) if isinstance(c, dict)]
			if calls:
				step_idx = row['step_index'] if isinstance(row.get('step_index'), int) else pos
				outs = dfh_row_outputs(rows, pos)
				joined = '\n'.join(outs)
				for idx, call in enumerate(calls):
					cls.__inspect_call_failure(call, outs[idx] if idx < len(outs) else joined, step_idx, bg_steps, hits)
		cls.__record_bg_cli_failures(rows, bg_steps, hits)
		return min(hits) if hits else None
	# @used-by :meth:`Doc5RequirementChecker.is_required()`
	@staticmethod
	def __has_post_failure_parent_issue(turn: dict[str, Any], fail_step: int, local_repos: set[str] | None=None) -> bool:
		r = False
		for act in turn.get('issue_actions') or ():
			if isinstance(act, dict) and 'create' == str(act.get('action') or '').lower() and None is act.get('parent_number'):
				repo = str(act.get('repo') or '').strip().lower()
				act_step = act.get('step')
				if ((not local_repos) or (repo in local_repos)) and (None is act_step or (isinstance(act_step, int) and act_step >= fail_step)):
					r = True
					break
		return r
	# @used-by :meth:`Doc5RequirementChecker.__earliest_cli_failure_step()`
	@classmethod
	def __inspect_call_failure(cls, call: dict[str, Any], matched: str, step_idx: int, bg_steps: dict[str, int], hits: list[int]) -> None:
		from agent_tools.tdd_gate import parse_command_outcome
		cmd = dfh_cmd_from_call(call)
		if cmd and _HARNESS_CLI_RE.search(cmd) and (not _EXCLUDED_CLI_RE.search(cmd)):
			out_info = parse_command_outcome(matched)
			if out_info.get('background_task_id'):
				bg_steps[str(out_info['background_task_id'])] = step_idx
			elif cls.is_failed_cli_output(matched):
				hits.append(step_idx)
	# @used-by :meth:`Doc5RequirementChecker.__earliest_cli_failure_step()`
	@classmethod
	def __record_bg_cli_failures(cls, rows: list[dict[str, Any]], bg_steps: dict[str, int], hits: list[int]) -> None:
		from agent_tools.tdd_gate import _BG_TASK_FINISHED_RE
		for row in rows:
			if row.get('type') in ('EPHEMERAL_MESSAGE', 'SYSTEM_MESSAGE', 'GENERIC') and row.get('content'):
				m_fin = _BG_TASK_FINISHED_RE.search(str(row.get('content')))
				if None is not m_fin and m_fin.group(1).strip() in bg_steps and cls.is_failed_cli_output(m_fin.group(2)):
					hits.append(bg_steps[m_fin.group(1).strip()])
	# @used-by :meth:`Doc5RequirementChecker.is_required()`
	@staticmethod
	def __workspace_repo_slugs(root: Any) -> set[str]:
		slugs: set[str] = set()
		if None is not root and str(root).strip():
			from agent_tools.path_registry import project_paths
			root_p = Path(root).resolve()
			cands: list[Path] = [root_p, root_p / 'code', *(root_p / rel for rel in V2_CODE_RELS)]
			try:
				cands = [*project_paths(root_p).code_repos, *cands]
			except (OSError, ValueError):
				pass
			locator = RepoLocator()
			for cand in cands:
				if (cand / '.git').exists():
					slug = locator.origin_repo_slug(cand)
					if slug:
						slugs.add(slug.lower())
		return slugs
	# @used-by :func:`agent_tools.doc5_context._is_failed_cli_output()`
	# @used-by :meth:`Doc5RequirementChecker.__inspect_call_failure()`
	# @used-by :meth:`Doc5RequirementChecker.__record_bg_cli_failures()`
	# @used-by :meth:`test_df_harness_s11_wave2c_grounding.DfHarnessS11Wave2CGroundingTests.test_cli_command_and_doc5_requirement_auditors()`
	@staticmethod
	def is_failed_cli_output(text: str) -> bool:
		from agent_tools.cli_output_json import top_level_json_has_failure
		from agent_tools.tdd_gate import parse_command_outcome
		out = parse_command_outcome(text)
		rc = out.get('exit_code')
		if None is not rc:
			r = (0 != rc) or top_level_json_has_failure(text)
		else:
			low = (text or '').lower()
			r = ('fail' == out.get('status')) or top_level_json_has_failure(text) or ('valueerror:' in low) or ('traceback (most recent call last)' in low)
		return r
	# @used-by :func:`agent_tools.doc5_context.turn_requires_doc5_problem_analysis()`
	# @used-by :meth:`Df.Harness.Grounding.Doc5ContextDetector.Doc5ContextDetector.__requires_doc5()`
	# @used-by :meth:`test_df_harness_s11_wave2c_grounding.DfHarnessS11Wave2CGroundingTests.test_cli_command_and_doc5_requirement_auditors()`
	def is_required(self) -> bool:
		r = False
		if isinstance(self.__turn_context, dict):
			if self.__turn_context.get('bug_report_signal'):
				r = True
			else:
				turn = self.__turn_context.get('turn')
				if isinstance(turn, dict) and 'standalone' != turn.get('turn_id'):
					fail_step = self.__earliest_cli_failure_step(turn, self.__turn_context.get('native'))
					if None is not fail_step:
						r = self.__has_post_failure_parent_issue(turn, fail_step, self.__workspace_repo_slugs(self.__turn_context.get('root')))
		return r