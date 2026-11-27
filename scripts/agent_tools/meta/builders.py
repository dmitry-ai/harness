# 2026-11-24 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from datetime import datetime
from pathlib import Path
from typing import Any
from Df.Harness.Meta.Builders import Builders
# 2026-11-24
# "Decompose metadata.py into modular metadata collection package":
# https://github.com/dmitry-ai/harness/issues/170
# 2026-11-26 "Move verification gate subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/381
# @used-by :func:`agent_tools.issues.turn_scope._resolve_antigravity_parent_cid()`
def _collect_ag_issue_ctx(environ: dict[str, str], active_cid: str) -> dict[str, Any]:
	return Builders.collect_ag_issue_ctx(environ, active_cid)
# @used-by :func:`agent_tools.issues.turn_scope.detect_active_session()`
def _detect_env_platform(environ: dict[str, str]) -> tuple[str | None, str | None, int | None]:
	return Builders.detect_env_platform(environ)
# @used-by :meth:`Df.Harness.Cleanup.AuditLogger.AuditLogger.run()`
# @used-by :meth:`agent_tools.issues.service.GitHubIssueService._prepend_issue_metadata()`
# @used-by :meth:`test_metadata.MetadataFormattingAndCollectionTests.test_build_github_issue_metadata_live_env_child_subagent_and_standalone()`
# @used-by :meth:`test_metadata_decomposition.MetadataDecompositionTests.test_builders_honor_facade_monkeypatch_seam_and_match_metadata_parity()`
# @used-by :mod:`agent_tools.meta`
# @used-by :mod:`agent_tools.metadata`
def build_github_issue_metadata(*, issue_url: str, project_root: str | Path | None=None, env: dict[str, str] | None=None, now: datetime | str | None=None, tz=None) -> dict[str, Any]:
	return Builders(project_root, env=env, now=now, tz=tz).build_github_issue(issue_url=issue_url)
# @used-by :func:`Df.Harness.lib.completion_record._maybe_prepend_journal_metadata()`
# @used-by :func:`Df.Harness.lib.hook_stop_ops._build_emergency_response()`
# @used-by :meth:`test_journal_clarifications_and_disclosure.JournalClarificationsAndDisclosureTests.test_build_journal_metadata_includes_clarifications_and_preserves_user_input_hash()`
# @used-by :meth:`test_metadata.MetadataFormattingAndCollectionTests.test_build_journal_metadata_for_antigravity_and_codex()`
# @used-by :meth:`test_metadata_decomposition.MetadataDecompositionTests.test_builders_honor_facade_monkeypatch_seam_and_match_metadata_parity()`
# @used-by :mod:`agent_tools.meta`
# @used-by :mod:`agent_tools.metadata`
def build_journal_metadata(root: str | Path, native: dict[str, Any], turn: dict[str, Any], *, journal_dir: str | Path, steps: list[int], turn_key: str, turn_state_path: str | Path | None=None, group_file: str | Path | None=None, conversation_steps: list[int] | None=None, request_at: datetime | str | None=None, response_at: datetime | str | None=None, tz=None) -> dict[str, Any]:
	return Builders.build_journal(root, native, turn, journal_dir=journal_dir, steps=steps, turn_key=turn_key, turn_state_path=turn_state_path, group_file=group_file, conversation_steps=conversation_steps, request_at=request_at, response_at=response_at, tz=tz)
# 2026-11-24
# "Add structured problem metadata builder and CLI command":
# https://github.com/dmitry-ai/harness/issues/180
# @used-by :func:`Df.Harness.lib.cli_registry_handlers.dfh_exec_problem_metadata()`
# @used-by :meth:`test_problem_metadata.ProblemMetadataTests.test_build_problem_metadata_allow_no_issue_keeps_mandatory_issue_key()`
# @used-by :meth:`test_problem_metadata.ProblemMetadataTests.test_build_problem_metadata_rejects_missing_or_invalid_issue_url()`
# @used-by :meth:`test_problem_metadata.ProblemMetadataTests.test_build_problem_metadata_with_issue_url_and_distinct_source_project()`
# @used-by :mod:`agent_tools.meta`
# @used-by :mod:`agent_tools.metadata`
def build_problem_metadata(*, issue_url: str | None=None, project_root: str | Path | None=None, source_project_root: str | Path | None=None, allow_no_issue: bool=False, env: dict[str, str] | None=None, now: datetime | str | None=None, tz=None) -> dict[str, Any]:
	return Builders.build_problem(issue_url=issue_url, project_root=project_root, source_project_root=source_project_root, allow_no_issue=allow_no_issue, env=env, now=now, tz=tz)
