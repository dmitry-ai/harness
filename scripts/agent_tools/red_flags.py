# 2026-10-15 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
# 2026-11-26 "Move analysis workflow classes into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/380
from Df.Harness.Analysis.RedFlagRenderer import RedFlagRenderer, STATUSES
from Df.Harness.Analysis.RedFlagSyncer import END, RedFlagSyncer, START
from Df.Harness.Analysis.RedFlagValidator import FLAGS, RedFlagValidator
# @used-by :mod:`agent_tools.red_flags`
def red_flag_issues(value, claims):
	return RedFlagValidator(value, claims).issues()
# @used-by :meth:`test_red_flags.RedFlagTests.test_legacy_top_block_moves_to_final_first_level_section_without_losing_text()`
# @used-by :mod:`agent_tools.red_flags`
def render_red_flags(value, *, project_card=False, analysis_rel='\ua616/KB/Analysis.json'):
	return RedFlagRenderer(value, project_card=project_card, analysis_rel=analysis_rel).render()
# @used-by :meth:`test_red_flags.RedFlagTests.test_append_and_remove_preserve_newlines_bom_and_empty_cards()`
# @used-by :meth:`test_red_flags.RedFlagTests.test_legacy_analysis_does_not_silently_clear_existing_risks()`
# @used-by :meth:`test_red_flags.RedFlagTests.test_legacy_top_block_moves_to_final_first_level_section_without_losing_text()`
# @used-by :meth:`test_red_flags.RedFlagTests.test_manual_section_heading_edits_are_preserved_as_conflicts()`
# @used-by :meth:`test_red_flags.RedFlagTests.test_manual_warning_edits_and_malformed_markers_are_preserved_as_conflicts()`
# @used-by :meth:`test_red_flags.RedFlagTests.test_no_flags_does_not_create_warning_or_change_original_card()`
# @used-by :meth:`test_red_flags.RedFlagTests.test_unknown_duplicate_and_unsupported_basis_cannot_be_published()`
# @used-by :meth:`test_upwork_card_and_red_flags.UpworkCardAndRedFlagsTests.test_markerless_red_flags_dual_surface_and_legacy_migration()`
# @used-by :meth:`test_upwork_v2_root_card.UpworkV2RootCardTests.test_legacy_v2_readme_fallback_works_across_card_consumers()`
# @used-by :mod:`agent_tools.red_flags`
def sync_project_red_flags(root, value):
	return RedFlagSyncer(root, value).sync()
__all__ = ['END', 'FLAGS', 'START', 'STATUSES', 'red_flag_issues', 'render_red_flags', 'sync_project_red_flags']