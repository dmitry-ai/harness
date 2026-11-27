# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from typing import Any
from agent_tools.cli_common import dump_json
import argparse
# 2026-11-26 "Move repository and grounding subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/382
class IssueFetcher:
	# @used-by :func:`agent_tools.issues.repo_commands.run_fetch()`
	# @used-by :meth:`Df.Harness.Issue.Service.Service.cmd_fetch()`
	def __init__(self, service, args: argparse.Namespace) -> None:
		self.__service = service
		self.__args = args
	# @used-by :func:`agent_tools.issues.repo_commands.run_fetch()`
	# @used-by :meth:`Df.Harness.Issue.Service.Service.cmd_fetch()`
	# @uses :meth:`Df.Harness.Issue.Service.Service.call_api()`
	def fetch(self) -> int:
		repo, number, project_root = (self.__service.linter.validate_repo(self.__args.repo), int(self.__args.issue), getattr(self.__args, 'project_root', None))
		fetched = self.__service.call_api(f'repos/{repo}/issues/{number}', method='GET')
		if not isinstance(fetched, dict) or 'pull_request' in fetched:
			raise ValueError(f'Target #{number} in {repo} is not a valid GitHub issue')
		eff_parent = self.__service.linter.extract_parent_number(str(fetched.get('body') or ''), repo)
		if None is not eff_parent and eff_parent != number:
			self.__service.verify_and_persist_parent_issue([], repo, eff_parent, self_number=number, project_root=project_root)
		self.__service.workspace.persist_issue_evidence([], repo, fetched, kind='issue', action='fetch', project_root=project_root, parent_number=eff_parent, conversation_id=getattr(self.__args, 'conversation', None))
		out: dict[str, Any] = {'ok': True, 'action': 'fetch', 'repo': repo, 'number': number, 'state': fetched.get('state'), 'state_reason': fetched.get('state_reason'), 'title': fetched.get('title'), 'html_url': fetched.get('html_url'), 'verified': True, 'body_chars': len(fetched.get('body') or '')}
		if None is not eff_parent and eff_parent != number:
			out.update(parent_number=int(eff_parent), parent_url=f'https://github.com/{repo}/issues/{int(eff_parent)}')
		dump_json(out)
		return 0
