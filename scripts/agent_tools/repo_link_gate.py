# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from pathlib import Path
# 2026-11-26 "Move verification gate subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/381
from Df.Harness.Gate.RepoLinkGate import RepoLinkGate
from Df.Harness.Gate.RepoLinkResolver import RepoLinkResolver
GITHUB_BLOB_TREE_RE = RepoLinkResolver.GITHUB_BLOB_TREE_RE
# @used-by :meth:`Df.Harness.Issue.Linter.Linter.__check_body_blocks()`
# @used-by :meth:`Df.Harness.Research.LinkAuditor.LinkAuditor.chat_reply_link_issues()`
# @used-by :mod:`agent_tools.repo_link_gate`
def chat_repo_link_issues(content: str, *, root: Path | None=None) -> list[str]:
	return RepoLinkGate.check_chat(content, root=root)
# @used-by :func:`Df.Harness.lib.hook_markdown_ops.dfh_check_doc_grounding_and_links()`
# @used-by :meth:`Df.Harness.Research.LinkAuditor.LinkAuditor.validate_file()`
# @used-by :mod:`agent_tools.repo_link_gate`
def file_repo_link_issues(doc_path: Path, content: str, *, repo_root: Path | None=None) -> list[str]:
	return RepoLinkGate.check_file(doc_path, content, repo_root=repo_root)
# @used-by :meth:`Df.Harness.Grounding.ResponseAuditor.ResponseAuditor.validate()`
# @used-by :mod:`agent_tools.repo_link_gate`
def hydrate_local_repo_urls(auditor) -> set[str]:
	return RepoLinkResolver.hydrate_local_urls(auditor)
# @used-by :func:`Df.Harness.lib.hook_markdown_ops.dfh_check_doc_grounding_and_links()`
# @used-by :mod:`agent_tools.repo_link_gate`
def is_skipped_repo_link_doc(path: Path | str) -> bool:
	return RepoLinkResolver.is_skipped_doc(path)
# @used-by :meth:`Df.Harness.Grounding.ActiveCorpusBuilder.ActiveCorpusBuilder.collect_local_repo_entries()`
# @used-by :mod:`agent_tools.repo_link_gate`
def resolve_local_github_blob(root: Path | None, url: str) -> tuple[str, str] | None:
	return RepoLinkResolver(root).resolve_blob(url)
# @used-by :mod:`agent_tools.repo_link_gate`
def verify_staged_repo_links(repo_root: Path, staged_paths: list[str], *, use_index: bool=True) -> list[str]:
	return RepoLinkGate().verify_staged(repo_root, staged_paths, use_index=use_index)
__all__ = ['GITHUB_BLOB_TREE_RE', 'chat_repo_link_issues', 'file_repo_link_issues', 'hydrate_local_repo_urls', 'is_skipped_repo_link_doc', 'resolve_local_github_blob', 'verify_staged_repo_links']
