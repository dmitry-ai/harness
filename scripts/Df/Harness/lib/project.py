# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from pathlib import Path
from typing import Any
import json
from Df.Core.lib.text.source import df_text_rewrite_pairs
# 2026-11-26 "Create Df/Harness library for shared Harness helpers": https://github.com/dmitry-ai/harness/issues/379
# Return True when a project-relative path should be skipped during Harness tree cloning.
# @used-by :func:`agent_tools.shadow_replay_clone._is_skipped_rel()`
# @used-by :meth:`Df.Harness.Shadow.WorkspaceCloner.WorkspaceCloner.run()`
# @used-by :meth:`test_df_harness_lib_s10.DfHarnessLibS10Tests.test_cli_journal_and_project_helpers()`
def dfh_is_skipped_rel(rel: Path) -> bool:
	parts = rel.parts
	if any((p.endswith('.lock') for p in parts)):
		r = True
	elif 3 <= len(parts) and '\ua616' == parts[0] and 'data' == parts[1] and parts[2] in ('scratch', '.journal'):
		r = True
	else:
		r = False
	return r
# 2026-11-28 "Use .md root card via v2_upwork profile": https://github.com/dmitry-ai/harness/issues/415
# Resolve the project root overview card, falling back to legacy readme.md only when .md is absent.
# @used-by :meth:`Df.Harness.Analysis.RedFlagSyncer.RedFlagSyncer.sync()`
# @used-by :meth:`Df.Harness.Project.CardSyncAuditor.CardSyncAuditor.audit()`
# @used-by :meth:`Df.Harness.Project.WebsiteCardSyncer.WebsiteCardSyncer.sync()`
# @used-by :meth:`Df.Harness.Project.WebsiteCardSyncer.WebsiteCardSyncer.sync_initial()`
# @used-by :meth:`Df.Harness.Upwork.ProjectConfigurator.ProjectConfigurator.default_context_config()`
# @used-by :meth:`Df.Harness.Workflow.HealthAuditor.HealthAuditor.__check_deliverable_links()`
# @used-by :meth:`Df.Harness.Workflow.ReceiptVerifier.ReceiptVerifier.__resolve_artifact()`
# @used-by :meth:`test_upwork_v2_root_card.UpworkV2RootCardTests.test_legacy_v2_readme_fallback_works_across_card_consumers()`
def dfh_resolve_overview_md(pp: Any) -> Path:
	primary = pp.path('overview_md', pp.root / '.md')
	legacy = pp.root / 'readme.md'
	return legacy if '.md' == primary.name and (not primary.exists()) and legacy.is_file() else primary
# Rewrite path strings inside a JSON file in place using case-insensitive replacement pairs.
# @used-by :func:`Df.Harness.lib.shadow_clone._remap_journal_data()`
# @used-by :func:`Df.Harness.lib.shadow_clone.dfh_remap_shadow_state()`
# @used-by :func:`Df.Harness.lib.shadow_command._copy_native_profile()`
# @used-by :func:`agent_tools.shadow_replay_clone._rewrite_json_file()`
# @used-by :meth:`test_df_harness_lib_s10.DfHarnessLibS10Tests.test_cli_journal_and_project_helpers()`
def dfh_rewrite_json_file(path: Path, pairs: list[tuple[str, str]], *, preserve_keys: tuple[str, ...]=()) -> bool:
	r = False
	if path.is_file():
		data = json.loads(path.read_text(encoding='utf-8-sig'))
		updated = dfh_rewrite_value(data, pairs, preserve_keys=preserve_keys)
		path.write_text(json.dumps(updated, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
		r = True
	return r
# Recursively rewrite string keys and values inside JSON-like structures with replacement pairs.
# @used-by :func:`agent_tools.project_rename_state._rewrite_value()`
# @used-by :func:`agent_tools.shadow_replay_clone._rewrite_value()`
# @used-by :func:`dfh_rewrite_json_file()`
# @used-by :meth:`Df.Harness.Project.Rename.StateRewriter.StateRewriter.__rewrite_json_file()`
# @used-by :meth:`Df.Harness.Project.Rename.StateRewriter.StateRewriter.rewrite_launcher_handoffs()`
# @used-by :meth:`test_df_harness_lib_s10.DfHarnessLibS10Tests.test_cli_journal_and_project_helpers()`
def dfh_rewrite_value(value: Any, pairs: list[tuple[str, str]], *, preserve_keys: tuple[str, ...]=()) -> Any:
	if isinstance(value, str):
		r: Any = df_text_rewrite_pairs(value, pairs)
	elif isinstance(value, list):
		r = [dfh_rewrite_value(v, pairs, preserve_keys=preserve_keys) for v in value]
	elif isinstance(value, dict):
		r = {(df_text_rewrite_pairs(k, pairs) if isinstance(k, str) else k): (v if k in preserve_keys else dfh_rewrite_value(v, pairs, preserve_keys=preserve_keys)) for k, v in value.items()}
	else:
		r = value
	return r