# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from typing import Any
from Df.Harness.Issue.Linter import Linter
from agent_tools.cli_common import dump_json
import argparse
# 2026-11-26 "Move repository and grounding subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/382
class RepoAuditor:
	# @used-by :func:`agent_tools.issues.repo_commands.run_audit_repo()`
	# @used-by :meth:`Df.Harness.Issue.Service.Service.cmd_audit_repo()`
	# @used-by :meth:`test_df_harness_s11_wave2c_issues.DfHarnessS11Wave2CIssuesTests.test_batch_runner_repo_auditor_and_transfer_runner()`
	def __init__(self, api_fn, linter: Linter, args: argparse.Namespace) -> None:
		self.__api = api_fn
		self.__linter = linter
		self.__args = args
	# @used-by :meth:`RepoAuditor.audit()`
	def __audit_comments(self, repo: str, target_locale: str, containers: dict[int, str]) -> tuple[list[dict[str, Any]], int]:
		raw_comments = self.__api(f'repos/{repo}/issues/comments?per_page=100', method='GET', paginate=True) or []
		corrupted: list[dict[str, Any]] = []
		for c in raw_comments:
			issue_num = int(c['issue_url'].rstrip('/').split('/')[-1])
			c_errs = self.__linter.lint(c.get('body') or '', is_title=False, target_locale=target_locale, container_text=containers.get(issue_num), check_structure_policy=False)
			if c_errs:
				corrupted.append({'comment_id': c['id'], 'issue_number': issue_num, 'html_url': c.get('html_url'), 'body_errors': c_errs})
		return (corrupted, len(raw_comments))
	# @used-by :meth:`RepoAuditor.audit()`
	def __audit_issues(self, issues: list[dict[str, Any]], target_locale: str, strict: bool) -> tuple[list[dict[str, Any]], dict[int, str]]:
		corrupted, containers = ([], {})
		for iss in issues:
			containers[iss['number']] = f"{iss.get('title') or ''}\n{iss.get('body') or ''}".strip()
			t_errs = self.__linter.lint(iss.get('title') or '', is_title=True, target_locale=target_locale, check_structure_policy=strict)
			b_errs = self.__linter.lint(iss.get('body') or '', is_title=False, target_locale=target_locale, check_structure_policy=strict)
			if t_errs or b_errs:
				corrupted.append({'number': iss['number'], 'title': iss.get('title'), 'html_url': iss.get('html_url'), 'title_errors': t_errs, 'body_errors': b_errs})
		return (corrupted, containers)
	# @used-by :func:`agent_tools.issues.repo_commands.run_audit_repo()`
	# @used-by :meth:`Df.Harness.Issue.Service.Service.cmd_audit_repo()`
	# @used-by :meth:`test_df_harness_s11_wave2c_issues.DfHarnessS11Wave2CIssuesTests.test_batch_runner_repo_auditor_and_transfer_runner()`
	def audit(self) -> int:
		repo = self.__linter.validate_repo(self.__args.repo)
		target_locale = getattr(self.__args, 'target_locale', 'en-US') or 'en-US'
		strict = bool(getattr(self.__args, 'strict_structure', False))
		raw_items = self.__api(f'repos/{repo}/issues?state={self.__args.state}&per_page=100', method='GET', paginate=True) or []
		issues = sorted((item for item in raw_items if 'pull_request' not in item), key=lambda x: x['number'])
		corrupted_issues, containers = self.__audit_issues(issues, target_locale, strict)
		corrupted_comments, c_count = self.__audit_comments(repo, target_locale, containers) if self.__args.include_comments else ([], 0)
		valid = not corrupted_issues and (not corrupted_comments)
		dump_json({'valid': valid, 'repo': repo, 'issue_count': len(issues), 'comment_count': c_count, 'corrupted_issue_count': len(corrupted_issues), 'corrupted_comment_count': len(corrupted_comments), 'corrupted_issues': corrupted_issues, 'corrupted_comments': corrupted_comments})
		return 0 if valid else 2
