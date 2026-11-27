# 2026-11-23 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from pathlib import Path
from typing import Any
from Df.Harness.Issue.DirtyIssueFirstScanner import DirtyIssueFirstScanner
from Df.Harness.Issue.EvidenceWorkspace import EvidenceWorkspace
from Df.Harness.Issue.IssueMetadataPrepender import IssueMetadataPrepender
from Df.Harness.Issue.PendingPeerFinder import PendingPeerFinder
from Df.Harness.lib.issue import dfh_build_create_payload, dfh_gh_api_call, dfh_resolve_title
import argparse
# 2026-11-26 "Move repository and grounding subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/382
# @used-by unused
def build_create_payload(args: argparse.Namespace, title: str, body: str) -> dict[str, Any]:
	return dfh_build_create_payload(args, title, body)
# @used-by :meth:`test_addon_observability.AddonObservabilityTests.test_dirty_issue_first_excludes_live_runtime_data_only()`
def dirty_issue_first_files(workspace: EvidenceWorkspace, repo: str, *, project_root: str | Path | None=None, source_files: list[tuple[Path, bytes]] | None=None, repo_root: str | Path | None=None) -> list[str]:
	return DirtyIssueFirstScanner(workspace, repo, project_root=project_root, source_files=source_files, repo_root=repo_root).scan()
# @used-by unused
def gh_api_call(endpoint: str, *, method: str='GET', payload: dict[str, Any] | None=None, paginate: bool=False, runner=None) -> Any:
	return dfh_gh_api_call(endpoint, method=method, payload=payload, paginate=paginate, runner=runner)
# @used-by unused
def pending_similar_peer_slugs(workspace: EvidenceWorkspace, code_repo: Path | None, *, repo: str, project_root: str | Path | None=None, source_files: list[tuple[Path, bytes]]=()) -> list[str]:
	return PendingPeerFinder(workspace, code_repo, repo=repo, project_root=project_root, source_files=source_files).find()
# @used-by unused
def resolve_metadata_project_root(workspace: EvidenceWorkspace, repo: str, project_root: str | Path | None, consumable: list[tuple[Path, bytes]]) -> Path | None:
	return IssueMetadataPrepender.resolve_project_root(workspace, repo, project_root, consumable)
# @used-by unused
def resolve_title(args: argparse.Namespace, consumable: list[tuple[Path, bytes]]) -> str | None:
	return dfh_resolve_title(args, consumable)
