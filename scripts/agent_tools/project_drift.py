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
# @used-by :mod:`agent_tools.project_drift`
def _load_json_dict(path: Path) -> dict | None:
	return df_json_dict_load(path)
# @used-by :mod:`agent_tools.project_drift`
def analysis_card_sync_issues(pp, value: dict) -> list[dict]:
	return CardSyncAuditor(pp, value, drift_fn=domain_drift_issues).audit()
# @used-by :func:`agent_tools.workflow.check_project()`
# @used-by :func:`agent_tools.workflow.complete_stage()`
# @used-by :func:`analysis_card_sync_issues()`
# @used-by :func:`require_no_domain_drift_for_finalize()`
# @used-by :mod:`agent_tools.project_drift`
def domain_drift_issues(root: Path | str, analysis_value: dict) -> list[dict]:
	return DriftAuditor(root, analysis_value).audit()
# @used-by :mod:`agent_tools.project_drift`
def require_no_domain_drift_for_finalize(root: Path | str) -> None:
	FinalizeDriftGuard(root, drift_fn=domain_drift_issues).require()
# @used-by :mod:`agent_tools.project_drift`
def require_stage_project_valid(root: Path | str, check_fn, base_msg: str) -> None:
	StageValidityGuard(root, check_fn, base_msg).require()
__all__ = ['_load_json_dict', 'analysis_card_sync_issues', 'domain_drift_issues', 'require_no_domain_drift_for_finalize', 'require_stage_project_valid']
