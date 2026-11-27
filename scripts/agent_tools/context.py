# 2026-10-11 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from datetime import datetime
from Df.Harness.Project.Context.ContextAssembler import ContextAssembler
from Df.Harness.Project.Context.ContextGenerator import ContextGenerator
from Df.Harness.Project.Context.LetterDiscoverer import LetterDiscoverer
from pathlib import Path
# 2026-11-26 "Move analysis workflow classes into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/380
# @used-by :mod:`agent_tools.context`
def _expand_entry(pp, raw: str | Path) -> str:
	return LetterDiscoverer.expand_entry(pp, raw)
# @used-by :mod:`agent_tools.context`
def _fence(text: str) -> str:
	return LetterDiscoverer.fence(text)
# @used-by :mod:`agent_tools.context`
def _inside_allowed(root: Path, path: str | Path, allowed_roots: tuple[Path, ...]=()) -> Path:
	return LetterDiscoverer.inside_allowed(root, path, allowed_roots)
# @used-by :mod:`agent_tools.context`
def _is_excluded(rel_path: Path, patterns: list[str]) -> bool:
	return LetterDiscoverer.is_excluded(rel_path, patterns)
# @used-by :meth:`test_agent_tools.ContextTests.test_default_context_config_includes_agent_kb_and_excludes_evidence_subfolder()`
# @used-by :meth:`test_agent_tools.ContextTests.test_sources_and_fences_preserved_in_configured_order()`
# @used-by :meth:`test_context_and_storage_determinism.ContextAndStorageDeterminismTests.test_generate_accepts_explicit_now_for_deterministic_timestamp()`
# @used-by :meth:`test_parallel_runner.ParallelRunnerTests.test_context_generate_accepts_fixed_now()`
# @used-by :meth:`test_readable_links.ReadableReferenceTests.test_exact_quotes_code_and_source_copies_are_not_rewritten_or_rejected()`
# @used-by :mod:`agent_tools.context`
def assemble(root: Path, manifest: dict | None=None, now: datetime | None=None) -> tuple[str, list[Path]]:
	return ContextAssembler(root, manifest, now=now).assemble()
# @used-by :mod:`agent_tools.context`
def default_context_config(root: Path | str | None=None) -> dict:
	return LetterDiscoverer.default_config(root)
# @used-by :meth:`test_agent_tools.ContextTests.test_final_without_draft_and_new_year_nested_letters()`
# @used-by :mod:`agent_tools.context`
def discover_letters(root: Path, languages=('EN', 'RU')) -> list[Path]:
	return LetterDiscoverer(root, languages).discover()
# @used-by :func:`agent_tools.cli.main()`
# @used-by :meth:`test_agent_tools.ContextTests.test_default_context_config_includes_agent_kb_and_excludes_evidence_subfolder()`
# @used-by :meth:`test_agent_tools.ContextTests.test_missing_input_fails_and_dry_run_writes_nothing()`
# @used-by :meth:`test_agent_tools.ContextTests.test_output_cannot_overwrite_input_or_escape_root()`
# @used-by :meth:`test_analysis_workflow.NativeReviewTests.test_full_workflow_requires_native_review_and_current_kb_then_exports_complete_context()`
# @used-by :meth:`test_context_and_storage_determinism.ContextAndStorageDeterminismTests.test_generate_accepts_explicit_now_for_deterministic_timestamp()`
# @used-by :meth:`test_onboarding.IsolationTests.test_incomplete_journal_does_not_replace_context()`
# @used-by :meth:`test_parallel_runner.ParallelRunnerTests.test_context_generate_accepts_fixed_now()`
# @used-by :meth:`test_path_registry.PathRegistryTests.test_custom_overlay_end_to_end_context_workflow_text_diagnostics_and_completion_canonicalization()`
# @used-by :meth:`test_path_registry.PathRegistryTests.test_v2_filesystem_auto_detection_journals_context_provenance_and_migration()`
# @used-by :meth:`test_portability.CodexEvidenceTests.test_codex_workflow_reviews_current_kb_and_exports_exact_native_request_and_reply()`
# @used-by :meth:`test_portability.CodexEvidenceTests.test_proposal_export_selects_each_language_final_or_existing_draft()`
# @used-by :meth:`test_resume_exports.ResumeExportTests.test_group_crash_reserves_all_numbers_and_preserves_previous_context()`
# @used-by :meth:`test_resume_exports.ResumeExportTests.test_multiple_exact_requests_share_one_answer_and_adoption_does_not_duplicate()`
# @used-by :mod:`agent_tools.context`
def generate(root: Path, config: Path | dict | None=None, output: Path | None=None, dry_run=False, now: datetime | None=None):
	return ContextGenerator(root, config, output, dry_run=dry_run, now=now).generate()
# @used-by :mod:`agent_tools.context`
def inside(root: Path, path: str | Path) -> Path:
	return LetterDiscoverer.inside(root, path)
# @used-by :meth:`test_agent_tools.ContextTests.test_empty_final_never_falls_back_to_draft()`
# @used-by :mod:`agent_tools.context`
def resolve_letter_file(path: Path, languages=('EN', 'RU')) -> Path | None:
	return LetterDiscoverer.resolve_letter_file(path, languages)
__all__ = ['_expand_entry', '_fence', '_inside_allowed', '_is_excluded', 'assemble', 'default_context_config', 'discover_letters', 'generate', 'inside', 'resolve_letter_file']
