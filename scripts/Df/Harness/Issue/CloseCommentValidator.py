# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from pathlib import Path
from Df.Harness.Issue.CommentGrounder import CommentGrounder
from Df.Harness.lib.issue import dfh_emit_grounding_failure
from agent_tools.cli_common import dump_json
import argparse
# 2026-11-26 "Move repository and grounding subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/382
class CloseCommentValidator:
	# @used-by :func:`agent_tools.issues.comment_grounding.validate_close_comment()`
	# @used-by :meth:`Df.Harness.Issue.Service.Service.__verify_close_prereqs()`
	# @used-by :meth:`test_df_harness_s11_wave2c_issues.DfHarnessS11Wave2CIssuesTests.test_service_metadata_prepender_and_comment_validators()`
	def __init__(self, service, args: argparse.Namespace, repo: str, number: int, consumable: list[tuple[Path, bytes]], target_locale: str, container_text: str | None, project_root: str | Path | None) -> None:
		self.__service = service
		self.__args = args
		self.__repo = repo
		self.__number = number
		self.__consumable = consumable
		self.__target_locale = target_locale
		self.__container_text = container_text
		self.__project_root = project_root
	# @used-by :func:`agent_tools.issues.comment_grounding.validate_close_comment()`
	# @used-by :meth:`Df.Harness.Issue.Service.Service.__verify_close_prereqs()`
	# @used-by :meth:`test_df_harness_s11_wave2c_issues.DfHarnessS11Wave2CIssuesTests.test_service_metadata_prepender_and_comment_validators()`
	def validate(self) -> tuple[str | None, int | None]:
		comment_body: str | None = None
		err_rc: int | None = None
		if self.__args.comment_file:
			c_path, c_raw, comment_body = self.__service.linter.read_utf8_no_bom_file(self.__args.comment_file)
			self.__consumable.append((c_path, c_raw))
			c_errors = self.__service.linter.lint(comment_body, is_title=False, target_locale=self.__target_locale, container_text=self.__container_text, check_structure_policy=False)
			if c_errors:
				dump_json({'ok': False, 'action': 'close', 'stage': 'pre_flight_comment_lint', 'repo': self.__repo, 'number': self.__number, 'comment_errors': c_errors})
				err_rc = 2
			else:
				g_errors = CommentGrounder(self.__service.workspace, self.__repo, self.__consumable, project_root=self.__project_root, repo_root=getattr(self.__args, 'repo_root', None)).check_grounding(comment_body)
				if g_errors:
					err_rc = dfh_emit_grounding_failure('close', self.__repo, g_errors, number=self.__number)
		return (comment_body, err_rc)
