# 2026-10-14 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from Df.Harness.Project.AttachmentInventory import AttachmentInventory
from Df.Harness.Project.AttachmentKbSyncer import AttachmentKbSyncer
from Df.Harness.Project.ExtraSourceBuilder import ExtraSourceBuilder
from Df.Harness.Project.FactualNoteValidator import FactualNoteValidator
from Df.Harness.Project.KbPopulator import KbPopulator
from Df.Harness.Project.OnceFileWriter import OnceFileWriter
from Df.Harness.Project.WebsiteCardSyncer import WebsiteCardSyncer
from pathlib import Path
from . import upwork_data
from .analysis import SECTIONS, TITLES, publish_owned, render_analysis, validate_analysis
# 2026-11-26 "Move analysis workflow classes into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/380
# @used-by :mod:`agent_tools.knowledge`
def _load_media_descriptions(project_root: Path, overrides: dict | None=None) -> dict[str, str]:
	return ExtraSourceBuilder.load_media_descriptions(project_root, overrides)
# @used-by :mod:`agent_tools.knowledge`
def _render_evidence_md(asset_evidence: list[dict], extra_sources: list[dict], project_root: Path | None=None) -> str | None:
	return KbPopulator.render_evidence_md(asset_evidence, extra_sources, project_root)
# @used-by :mod:`agent_tools.knowledge`
def _render_projects_md(data: dict, url: str, source_link: str, extra_sources: list[dict], project_root: Path | None=None) -> str:
	return KbPopulator.render_projects_md(data, url, source_link, extra_sources, project_root)
# @used-by :mod:`agent_tools.knowledge`
def _replace_section2_in_project_md(existing_md: str, data: dict, extra_sources: list[dict]) -> str:
	return AttachmentKbSyncer.replace_section2(existing_md, data, extra_sources)
# @used-by :func:`agent_tools.upwork_project.initialize_upwork_project()`
# @used-by :func:`populate_agent_kb()`
# @used-by :func:`sync_project_attachments_and_kb()`
# @used-by :mod:`agent_tools.knowledge`
def build_project_extra_sources(project_root: Path, data: dict, assets: list[dict] | None=None, *, fetch_videos: bool=True) -> list[dict]:
	return ExtraSourceBuilder(project_root, data, assets, fetch_videos=fetch_videos, loom_fn=upwork_data.extract_loom_video).build()
# @used-by :mod:`agent_tools.knowledge`
def create_once(path: Path, content: str):
	OnceFileWriter(path, content).write()
# @used-by :func:`agent_tools.platforms.antigravity.register_antigravity_project()`
# @used-by :mod:`agent_tools.knowledge`
def json_bytes(value):
	return OnceFileWriter.json_bytes(value)
# @used-by :mod:`agent_tools.knowledge`
def populate_agent_kb(project_root: Path, data: dict):
	return KbPopulator(project_root, data, extra_sources_fn=build_project_extra_sources).populate()
# @used-by :mod:`agent_tools.knowledge`
def sync_initial_website(root, snapshot, hypothesis=None):
	return WebsiteCardSyncer.sync_initial(root, snapshot, hypothesis)
# @used-by :func:`agent_tools.cli_domains._op_sync_attachments()`
# @used-by :meth:`test_onboarding.AttachmentTests.test_docx_and_text_attachments_saved_in_source_and_both_kbs()`
# @used-by :mod:`agent_tools.knowledge`
def sync_project_attachments_and_kb(project_root: Path, media_descriptions: dict | None=None, *, fetch_videos: bool=True) -> dict:
	return AttachmentKbSyncer(project_root, media_descriptions, fetch_videos=fetch_videos, extra_sources_fn=build_project_extra_sources).sync()
# @used-by :mod:`agent_tools.knowledge`
def sync_source_folder_attachments(project_root: Path, saved_attachments: list[dict] | None=None, asset_evidence: list[dict] | None=None) -> list[dict]:
	return AttachmentInventory(project_root).sync(saved_attachments, asset_evidence)
# @used-by :func:`test_atomic_prepare_and_narrowed_reconcile_m7._init_review_ready_project()`
# @used-by :func:`test_contract_invariants._init_tracked_project()`
# @used-by :func:`test_runtime_cache_and_evidence_fastpath_m9._write_minimal_v3_project()`
# @used-by :meth:`test_analysis_workflow.ProjectCase.review_package()`
# @used-by :meth:`test_analysis_workflow.ProjectCase.valid_review_analysis()`
# @used-by :meth:`test_df_harness_s11_wave2a_review.DfHarnessS11Wave2aReviewTests.test_z_review_lifecycle_and_validators_extra()`
# @used-by :meth:`test_publication_lifecycle.PublicationLifecycleTests.test_explicit_website_is_published_and_reused_without_overwriting_card_or_metadata()`
# @used-by :meth:`test_readable_links.ReadableProjectTests.test_website_card_uses_readable_iri_and_keeps_original_website_selection()`
# @used-by :mod:`agent_tools.knowledge`
def sync_website_card(root, value, *, selections=None, check=False):
	return WebsiteCardSyncer(root, value, selections=selections, check=check).sync()
# @used-by :func:`agent_tools.completion._factual_kb_note_issues()`
# @used-by :meth:`test_issue44.TestIssue44.test_validate_kb_factual_note_analytical_heading()`
# @used-by :meth:`test_issue44.TestIssue44.test_validate_kb_factual_note_clean()`
# @used-by :meth:`test_issue44.TestIssue44.test_validate_kb_factual_note_hypothesis_id()`
# @used-by :meth:`test_issue44.TestIssue44.test_validate_kb_factual_note_pro_con()`
# @used-by :meth:`test_issue44.TestIssue44.test_validate_kb_factual_note_root_cause()`
# @used-by :mod:`agent_tools.knowledge`
def validate_kb_factual_note(path: Path | str, text: str) -> list[str]:
	return FactualNoteValidator(path, text).issues()
# @used-by :mod:`agent_tools.knowledge`
def website_issues(value):
	return WebsiteCardSyncer.website_issues(value)
__all__ = ['AttachmentInventory', 'SECTIONS', 'TITLES', '_load_media_descriptions', '_render_evidence_md', '_render_projects_md', '_replace_section2_in_project_md', 'build_project_extra_sources', 'create_once', 'json_bytes', 'populate_agent_kb', 'publish_owned', 'render_analysis', 'sync_initial_website', 'sync_project_attachments_and_kb', 'sync_source_folder_attachments', 'sync_website_card', 'validate_analysis', 'validate_kb_factual_note', 'website_issues']
