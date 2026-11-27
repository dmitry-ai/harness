# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from pathlib import Path
from Df.Harness.Grounding.LocalSourceAuditor import LocalSourceAuditor
from Df.Harness.lib.grounding import dfh_read_only_grounding
from Df.Harness.lib.issue import dfh_emit_grounding_failure
from agent_tools.cli_common import dump_json
import argparse
# 2026-11-26 "Move repository and grounding subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/382
class CommentGrounder:
	# @used-by :func:`agent_tools.issues.comment_grounding.check_comment_grounding()`
	# @used-by :func:`agent_tools.issues.comment_grounding.check_comment_preflight()`
	# @used-by :meth:`Df.Harness.Issue.CloseCommentValidator.CloseCommentValidator.validate()`
	# @used-by :meth:`Df.Harness.Issue.Service.Service.cmd_comment()`
	# @used-by :meth:`test_df_harness_s11_wave2c_issues.DfHarnessS11Wave2CIssuesTests.test_service_metadata_prepender_and_comment_validators()`
	def __init__(self, workspace, repo: str, consumable: list[tuple[Path, bytes]], *, project_root: str | Path | None=None, repo_root: str | Path | None=None) -> None:
		self.__workspace = workspace
		self.__repo = repo
		self.__consumable = consumable
		self.__project_root = project_root
		self.__repo_root = repo_root
	# @used-by :meth:`CommentGrounder.check_grounding()`
	def __resolve_root(self) -> Path | None:
		if None is not self.__project_root and str(self.__project_root).strip():
			r: Path | None = Path(self.__project_root).resolve()
		else:
			code_repo = self.__workspace.find_local_code_repo(self.__repo, project_root=self.__project_root, source_files=self.__consumable, repo_root=self.__repo_root)
			if None is not code_repo:
				try:
					from agent_tools.path_registry import project_paths
					r = project_paths(code_repo).root
				except (OSError, ValueError):
					r = code_repo
			else:
				try:
					from agent_tools.path_registry import resolve_project_root
					r = resolve_project_root(Path.cwd().resolve())
				except (OSError, ValueError):
					r = Path.cwd().resolve()
		return r
	# @used-by :func:`agent_tools.issues.comment_grounding.check_comment_grounding()`
	# @used-by :meth:`CommentGrounder.check_preflight()`
	# @used-by :meth:`Df.Harness.Issue.CloseCommentValidator.CloseCommentValidator.validate()`
	# @used-by :meth:`test_df_harness_s11_wave2c_issues.DfHarnessS11Wave2CIssuesTests.test_service_metadata_prepender_and_comment_validators()`
	def check_grounding(self, text: str | None) -> list[str]:
		r: list[str] = []
		if isinstance(text, str) and text.strip():
			ground_root = self.__resolve_root()
			if None is not ground_root:
				with dfh_read_only_grounding():
					r = LocalSourceAuditor(ground_root, text).run()
		return r
	# @used-by :func:`agent_tools.issues.comment_grounding.check_comment_preflight()`
	# @used-by :meth:`Df.Harness.Issue.Service.Service.cmd_comment()`
	def check_preflight(self, args: argparse.Namespace, body: str) -> int | None:
		existing_cids = self.__workspace.find_existing_issue_comments(self.__consumable, self.__repo, args.issue, project_root=self.__project_root) if None is args.comment_id and None is not args.issue and (not getattr(args, 'allow_additional_comment', False)) else []
		if existing_cids:
			dump_json({'ok': False, 'action': 'comment', 'stage': 'idempotent_comment_gate', 'repo': self.__repo, 'issue': args.issue, 'existing_comment_ids': existing_cids, 'error': f'EXEC-5 / SCOPE-2: Issue #{args.issue} already has tracked comment(s) {existing_cids} in KB/Evidence/GitHub; use --comment-id {existing_cids[-1]} to update the existing comment in place instead of posting a duplicate comment (or pass --allow-additional-comment if explicitly instructed)'})
			r: int | None = 2
		else:
			g_errors = self.check_grounding(body)
			r = dfh_emit_grounding_failure('comment', self.__repo, g_errors, number=getattr(args, 'issue', None), comment_id=getattr(args, 'comment_id', None)) if g_errors else None
		return r
