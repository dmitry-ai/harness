# 2026-11-24 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from pathlib import Path
from typing import Any
from Df.Harness.Meta.ProjectIdentity import ProjectIdentity
# 2026-11-26 "Move verification gate subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/381
_PROJECTS_DIR_CACHE = ProjectIdentity.PROJECTS_DIR_CACHE
# @used-by :mod:`agent_tools.meta`
# @used-by :mod:`agent_tools.metadata`
def _antigravity_project_dirs(ag_paths: dict[str, Any] | None=None, *, canon_root: Path | None=None) -> list[Path]:
	return ProjectIdentity.antigravity_project_dirs(ag_paths, canon_root=canon_root)
# @used-by :mod:`agent_tools.meta`
# @used-by :mod:`agent_tools.metadata`
def _is_temp_path(path: Path) -> bool:
	return ProjectIdentity.is_temp_path(path)
# @used-by :mod:`agent_tools.meta`
# @used-by :mod:`agent_tools.metadata`
def _load_projects_dir_items(pdir: Path) -> list[dict[str, Any]]:
	return ProjectIdentity.load_projects_dir_items(pdir)
# @used-by :mod:`agent_tools.meta`
# @used-by :mod:`agent_tools.metadata`
def _resolve_ag_paths_safe(backend=None, *, instance=None, conversation_id=None) -> dict[str, Any] | None:
	return ProjectIdentity.resolve_ag_paths_safe(backend=backend, instance=instance, conversation_id=conversation_id)
# @used-by :mod:`agent_tools.meta`
# @used-by :mod:`agent_tools.metadata`
def _resolve_codex_paths_safe(backend=None, *, instance=None, conversation_id=None) -> dict[str, Any] | None:
	return ProjectIdentity.resolve_codex_paths_safe(backend=backend, instance=instance, conversation_id=conversation_id)
# 2026-11-24
# "Decompose metadata.py into modular metadata collection package":
# https://github.com/dmitry-ai/harness/issues/170
# @used-by :meth:`test_journal_metadata.JournalMetadataIntegrationTests.test_resolve_project_identity_skips_user_registry_for_isolated_temp_dir()`
# @used-by :meth:`test_metadata_decomposition.MetadataDecompositionTests.test_identity_submodule_resolves_registry_project_json_and_fallback()`
# @used-by :mod:`agent_tools.meta`
# @used-by :mod:`agent_tools.metadata`
def resolve_project_identity(root: str | Path, *, ag_paths: dict[str, Any] | None=None, project_id: str | None=None) -> dict[str, str]:
	return ProjectIdentity(root, ag_paths=ag_paths, project_id=project_id).resolve()
