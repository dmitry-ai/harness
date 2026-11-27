# 2026-11-24 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from pathlib import Path
# 2026-11-26 "Move analysis workflow classes into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/380
from Df.Harness.Analysis.CandidateMerger import CandidateMerger
from Df.Harness.Analysis.Merger import Merger
# @used-by unused
def merge_analysis_candidate(base: dict, patch: dict) -> dict:
	return CandidateMerger(base, patch).merge()
# @used-by :func:`Df.Harness.lib.cli_domain_ops._op_save_analysis()`
# @used-by :meth:`test_schema_help_and_analysis_merge_m10.SchemaHelpAndAnalysisMergeM10Tests.test_save_analysis_merge_supports_partial_draft_final_commit_and_patch()`
def save_merged_analysis(root: Path | str, patch: dict, expected_sha256: str | None=None, *, partial: bool=False) -> dict:
	return Merger(root, patch, expected_sha256=expected_sha256, partial=partial).save()