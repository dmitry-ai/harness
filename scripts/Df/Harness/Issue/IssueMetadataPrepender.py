# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from pathlib import Path
from typing import Any
from Df.Harness.Issue.EvidenceWorkspace import EvidenceWorkspace
# 2026-11-26 "Move repository and grounding subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/382
class IssueMetadataPrepender:
	# @used-by :meth:`Df.Harness.Issue.Service.Service.__write_created_issue()`
	# @used-by :meth:`test_df_harness_s11_wave2c_issues.DfHarnessS11Wave2CIssuesTests.test_service_metadata_prepender_and_comment_validators()`
	def __init__(self, workspace: EvidenceWorkspace, api_fn) -> None:
		self.__workspace = workspace
		self.__api = api_fn
	# @used-by :meth:`Df.Harness.Issue.Service.Service.__write_created_issue()`
	# @used-by :meth:`test_df_harness_s11_wave2c_issues.DfHarnessS11Wave2CIssuesTests.test_service_metadata_prepender_and_comment_validators()`
	def prepend(self, repo: str, num: int, created: dict[str, Any], body: str, project_root: str | Path | None, consumable: list[tuple[Path, bytes]], state: dict[str, Any]) -> None:
		from agent_tools.metadata import build_github_issue_metadata, extract_leading_metadata_header, prepend_metadata_header
		existing_meta, _ = extract_leading_metadata_header(body)
		if None is existing_meta:
			issue_url = str(created.get('html_url') or f'https://github.com/{repo}/issues/{num}')
			meta_obj = build_github_issue_metadata(issue_url=issue_url, project_root=self.resolve_project_root(self.__workspace, repo, project_root, consumable))
			prefixed = prepend_metadata_header(body, meta_obj)
			self.__api(f'repos/{repo}/issues/{num}', method='PATCH', payload={'body': prefixed})
			state['body'], state['prepended'] = (prefixed, True)
	# @used-by :func:`agent_tools.issues.service_helpers.resolve_metadata_project_root()`
	# @used-by :meth:`IssueMetadataPrepender.prepend()`
	@staticmethod
	def resolve_project_root(workspace: EvidenceWorkspace, repo: str, project_root: str | Path | None, consumable: list[tuple[Path, bytes]]) -> Path | None:
		if None is not project_root and str(project_root).strip():
			r: Path | None = Path(project_root).resolve()
		else:
			code_repo = workspace.find_local_code_repo(repo, project_root=project_root, source_files=consumable)
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
