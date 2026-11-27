# 2026-10-11 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from pathlib import Path
from Df.Harness.Text.DraftSnapshotter import DraftSnapshotter
# 2026-10-11
# "Extract self-contained .agents toolkit, deterministic validation CLI, and rule architecture from wayse.pt":
# https://github.com/dmitry-ai/harness/issues/2
# 2026-10-31
# "Reorganize AI into universal harness repository, translate rules and documentation to English, format per P.md, and enforce issue-driven Git workflow":
# https://github.com/dmitry-ai/harness/issues/26
# 2026-11-27 "Reorganize Harness scripts into single-class Mage2Pro modules": https://github.com/dmitry-ai/harness/issues/338
# @used-by :meth:`Df.Harness.Cli.Dispatcher.Dispatcher.__dispatch()`
# @used-by :meth:`Df.Harness.Text.Workspace.Workspace.__snapshot_draft_if_needed()`
# @used-by :meth:`test_agent_tools.SnapshotTests.test_changed_previous_copy_is_not_silently_replaced()`
# @used-by :meth:`test_agent_tools.SnapshotTests.test_current_bytes_preserved_once_per_turn()`
# @used-by :meth:`test_agent_tools.UpworkProjectTests.test_agent_data_dir_prefers_vai_directory()`
# @used-by :meth:`test_df_harness_s11_final_338.DfHarnessS11Final338Tests.test_draft_snapshotter_and_facade_cover_capture_verify_and_errors()`
# @used-by :meth:`test_onboarding.IsolationTests.test_two_drafts_in_one_turn_have_distinct_archives()`
# @used-by :meth:`test_portability.CodexEvidenceTests.test_codex_workflow_reviews_current_kb_and_exports_exact_native_request_and_reply()`
def snapshot_draft(source: Path, turn: str) -> Path:
	return DraftSnapshotter(source, turn).snapshot()
