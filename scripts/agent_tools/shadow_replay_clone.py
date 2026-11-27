# 2026-11-25 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from contextlib import contextmanager
from pathlib import Path
# 2026-11-26 "Move turn lifecycle subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/383
from Df.Core.lib.text.source import df_text_rewrite_pairs
from Df.Harness.Shadow.WorkspaceCloner import WorkspaceCloner
from Df.Harness.lib.path_template import dfh_path_key
from Df.Harness.lib.project import dfh_is_skipped_rel, dfh_rewrite_json_file, dfh_rewrite_value
from Df.Harness.lib.shadow_clone import dfh_build_stop_transcript as build_stop_transcript, dfh_cleanup_shadow_root as cleanup_shadow_root, dfh_path_pairs as _path_pairs, dfh_remap_shadow_state as remap_shadow_state, dfh_shadow_isolation_context
# @used-by :func:`agent_tools.shadow_replay.run_shadow_replay()`
# @used-by :func:`shadow_isolation_context()`
# @used-by :meth:`test_df_harness_s11_wave2d_shadow_runtime_cov.DfHarnessS11Wave2dShadowRuntimeCovTests.test_shadow_clone_and_command_ops()`
@contextmanager
def _legacy_shadow_patch_ctx(relocations: dict[Path, Path]):
	from . import journal as journal_mod
	from .platforms import antigravity as ag_mod
	orig_title, orig_same_j = (ag_mod.update_conversation_title, journal_mod.same_journal_identity)
	mapped = {(dfh_path_key(Path(src).resolve() / '\ua66e'), dfh_path_key(Path(dst).resolve() / '\ua66e')) for src, dst in relocations.items()}
	# @used-by :func:`_legacy_shadow_patch_ctx()`
	def _match(first, second) -> bool:
		r = orig_same_j(first, second)
		if not r and first and second:
			k1, k2 = (dfh_path_key(Path(first).resolve()), dfh_path_key(Path(second).resolve()))
			r = (k1, k2) in mapped or (k2, k1) in mapped
		return r
	ag_mod.update_conversation_title = lambda cid, title, **_kw: {'changed': False, 'conversation_id': cid, 'reason': 'shadow_replay_disabled', 'synced': False, 'title': title}
	journal_mod.same_journal_identity = _match
	try:
		yield
	finally:
		ag_mod.update_conversation_title = orig_title
		journal_mod.same_journal_identity = orig_same_j
# @used-by :meth:`test_df_harness_lib_s10.DfHarnessLibS10Tests.test_harness_callers_delegate_to_df_harness_helpers()`
def _is_skipped_rel(rel: Path) -> bool:
	return dfh_is_skipped_rel(rel)
# @used-by unused
def _rewrite_json_file(path: Path, pairs: list[tuple[str, str]], *, preserve_keys: tuple[str, ...]=()) -> None:
	dfh_rewrite_json_file(path, pairs, preserve_keys=preserve_keys)
# @used-by :meth:`test_df_core_qa_s10.DfCoreQaS10Tests.test_harness_callers_delegate_to_new_core_and_qa_helpers()`
def _rewrite_path_text(text: str, pairs: list[tuple[str, str]]) -> str:
	return df_text_rewrite_pairs(text, pairs)
# @used-by :meth:`test_df_harness_lib_s10.DfHarnessLibS10Tests.test_harness_callers_delegate_to_df_harness_helpers()`
def _rewrite_value(value, pairs: list[tuple[str, str]], *, preserve_keys: tuple[str, ...]=()):
	return dfh_rewrite_value(value, pairs, preserve_keys=preserve_keys)
# @used-by unused
def clone_project_tree(src_root: Path, dst_root: Path, *, hardlink_evidence: bool=True) -> None:
	WorkspaceCloner(src_root, dst_root, hardlink_evidence=hardlink_evidence).run()
# @used-by unused
@contextmanager
def shadow_isolation_context(relocations: dict[Path, Path]):
	with dfh_shadow_isolation_context(relocations, legacy_ctx=_legacy_shadow_patch_ctx):
		yield
