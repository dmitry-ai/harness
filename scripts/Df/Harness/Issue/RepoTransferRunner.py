# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from typing import Any
from Df.Harness.Issue.EvidenceWorkspace import EvidenceWorkspace
from Df.Harness.Issue.Linter import Linter
from agent_tools.cli_common import dump_json
import argparse
import time
# 2026-11-26 "Move repository and grounding subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/382
class RepoTransferRunner:
	# @used-by :func:`agent_tools.issues.repo_commands.run_transfer_repo()`
	# @used-by :meth:`Df.Harness.Issue.Service.Service.cmd_transfer_repo()`
	# @used-by :meth:`test_df_harness_s11_wave2c_issues.DfHarnessS11Wave2CIssuesTests.test_batch_runner_repo_auditor_and_transfer_runner()`
	def __init__(self, api_fn, linter: Linter, workspace: EvidenceWorkspace, args: argparse.Namespace) -> None:
		self.__api = api_fn
		self.__linter = linter
		self.__workspace = workspace
		self.__args = args
	# @used-by :meth:`RepoTransferRunner.transfer()`
	def __poll_transferred(self, target_repo: str, max_attempts: int, delay_s: float) -> dict[str, Any] | None:
		r = None
		for attempt in range(max_attempts):
			try:
				cand = self.__api(f'repos/{target_repo}', method='GET')
				if isinstance(cand, dict) and target_repo.lower() == str(cand.get('full_name') or '').lower():
					r = cand
					break
			except RuntimeError:
				pass
			if attempt + 1 < max_attempts and 0 < delay_s:
				time.sleep(delay_s)
		return r
	# @used-by :func:`agent_tools.issues.repo_commands.run_transfer_repo()`
	# @used-by :meth:`Df.Harness.Issue.Service.Service.cmd_transfer_repo()`
	# @used-by :meth:`test_df_harness_s11_wave2c_issues.DfHarnessS11Wave2CIssuesTests.test_batch_runner_repo_auditor_and_transfer_runner()`
	# @uses :meth:`Df.Harness.Issue.EvidenceWorkspace.EvidenceWorkspace.persist_repo_transfer_evidence()`
	# @uses :meth:`Df.Harness.Issue.Linter.Linter.validate_slug_part()`
	def transfer(self) -> int:
		repo = self.__linter.validate_repo(self.__args.repo)
		new_owner = self.__linter.validate_slug_part(self.__args.new_owner, 'new_owner')
		new_name = self.__linter.validate_slug_part(self.__args.new_name, 'new_name') if getattr(self.__args, 'new_name', None) else repo.split('/', 1)[1]
		target_repo = f'{new_owner}/{new_name}'
		if repo.lower() == target_repo.lower():
			raise ValueError(f'Source and target repositories are identical: {repo}')
		payload = {'new_owner': new_owner, **({'new_name': new_name} if getattr(self.__args, 'new_name', None) else {})}
		transfer_resp = self.__api(f'repos/{repo}/transfer', method='POST', payload=payload)
		fetched = self.__poll_transferred(target_repo, max(1, int(getattr(self.__args, 'poll_attempts', 8) or 8)), float(getattr(self.__args, 'poll_interval', 1.5)))
		ev_path = self.__workspace.persist_repo_transfer_evidence(repo, target_repo, transfer_resp if isinstance(transfer_resp, dict) else None, fetched, project_root=getattr(self.__args, 'project_root', None))
		if None is fetched:
			dump_json({'ok': False, 'action': 'transfer-repo', 'stage': 'post_flight_readback', 'source_repo': repo, 'target_repo': target_repo, 'verified': False, 'evidence': str(ev_path)})
			r = 2
		else:
			dump_json({'ok': True, 'action': 'transfer-repo', 'source_repo': repo, 'target_repo': fetched.get('full_name'), 'html_url': fetched.get('html_url'), 'private': bool(fetched.get('private')), 'default_branch': fetched.get('default_branch'), 'verified': True, 'evidence': str(ev_path)})
			r = 0
		return r
