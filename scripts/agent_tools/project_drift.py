# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from pathlib import Path
# 2026-11-26 "Extract general duplicated helpers into Df/Core and Df/Qa": https://github.com/dmitry-ai/harness/issues/378
from Df.Core.lib.json_io import df_json_dict_load
# 2026-11-26 "Move analysis workflow classes into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/380
from Df.Harness.Project.CardSyncAuditor import CardSyncAuditor
from Df.Harness.Project.DriftAuditor import DriftAuditor
from Df.Harness.Project.FinalizeDriftGuard import FinalizeDriftGuard
from Df.Harness.Project.StageValidityGuard import StageValidityGuard
# @used-by :meth:`test_df_core_qa_s10.DfCoreQaS10Tests.test_harness_callers_delegate_to_new_core_and_qa_helpers()`
def _load_json_dict(path: Path) -> dict | None:
	return df_json_dict_load(path)
# @used-by :meth:`agent_tools.workflow.ProjectHealthAuditor._analysis_card_issues()`
def analysis_card_sync_issues(pp, value: dict) -> list[dict]:
	return CardSyncAuditor(pp, value, drift_fn=domain_drift_issues).audit()
# @used-by :func:`analysis_card_sync_issues()`
# @used-by :func:`require_no_domain_drift_for_finalize()`
def domain_drift_issues(root: Path | str, analysis_value: dict) -> list[dict]:
	return DriftAuditor(root, analysis_value).audit()
# @used-by :meth:`agent_tools.workflow.WorkflowStateEngine._finalize_stage()`
def require_no_domain_drift_for_finalize(root: Path | str) -> None:
	FinalizeDriftGuard(root, drift_fn=domain_drift_issues).require()
# @used-by :meth:`agent_tools.workflow.WorkflowStateEngine._apply_complete_stage()`
def require_stage_project_valid(root: Path | str, check_fn, base_msg: str) -> None:
	StageValidityGuard(root, check_fn, base_msg).require()