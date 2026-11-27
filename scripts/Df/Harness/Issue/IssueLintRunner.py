# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from Df.Harness.Issue.Linter import Linter
from Df.Harness.lib.issue import dfh_resolve_title
from agent_tools.cli_common import dump_json
import argparse
# 2026-11-26 "Move repository and grounding subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/382
class IssueLintRunner:
	# @used-by :func:`agent_tools.issues.repo_commands.run_lint()`
	# @used-by :meth:`Df.Harness.Issue.Service.Service.cmd_lint()`
	def __init__(self, linter: Linter, args: argparse.Namespace) -> None:
		self.__linter = linter
		self.__args = args
	# @used-by :func:`agent_tools.issues.repo_commands.run_lint()`
	# @used-by :meth:`Df.Harness.Issue.Service.Service.cmd_lint()`
	def run(self) -> int:
		consumable: list = []
		target_locale = getattr(self.__args, 'target_locale', 'en-US') or 'en-US'
		repo = self.__linter.validate_repo(self.__args.repo) if getattr(self.__args, 'repo', None) else None
		parent_num = self.__linter.parse_parent_arg(getattr(self.__args, 'parent', None), repo)
		title = dfh_resolve_title(self.__args, consumable)
		title_errors = self.__linter.lint(title, is_title=True, target_locale=target_locale) if None is not title else []
		body_errors = self.__linter.lint(self.__linter.read_utf8_no_bom_file(self.__args.body_file)[2], is_title=False, target_locale=target_locale, parent_number=parent_num, repo=repo) if self.__args.body_file else []
		valid = not title_errors and (not body_errors)
		dump_json({'valid': valid, 'title_errors': title_errors, 'body_errors': body_errors})
		return 0 if valid else 2
