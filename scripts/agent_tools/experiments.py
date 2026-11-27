# 2026-10-18 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
# 2026-11-26 "Move analysis workflow classes into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/380
from Df.Harness.Experiment.PlanStore import PlanStore as ExperimentPlanStore
from Df.Harness.Experiment.RequirementValidator import METHODS, OPERATORS, PROPERTY_METHODS, RequirementValidator, STATUSES
from Df.Harness.Experiment.ResultValidator import ResultValidator
from Df.Harness.Experiment.RunValidator import RunValidator as ExperimentRunValidator
from Df.Harness.Experiment.TraceInspector import TraceInspector as BrowserTraceInspector
# @used-by :meth:`test_experiments.ExperimentTests.test_actual_namespaced_cua_read_is_recognized_but_text_header_does_not_prove_identity()`
# @used-by :meth:`test_experiments.ExperimentTests.test_namespaced_documented_dom_snapshot_is_read_only_and_keeps_strict_grammar()`
# @used-by :mod:`agent_tools.experiments`
def _event_actions(event):
	return BrowserTraceInspector.event_actions(event)
# @used-by :meth:`test_experiments.ExperimentTests.test_actual_namespaced_cua_read_is_recognized_but_text_header_does_not_prove_identity()`
# @used-by :meth:`test_experiments.ExperimentTests.test_namespaced_documented_dom_snapshot_is_read_only_and_keeps_strict_grammar()`
# @used-by :mod:`agent_tools.experiments`
def _event_browser_identity(event):
	return BrowserTraceInspector.event_browser_identity(event)
# @used-by :mod:`agent_tools.experiments`
def digest(value):
	return RequirementValidator.digest(value)
# @used-by :mod:`agent_tools.experiments`
def evaluate_assertions(run, contents):
	return ExperimentRunValidator(None, run, contents).evaluate_assertions()
# @used-by :meth:`test_evidence_contract.EvidenceContractTests.test_experiment_primary_uses_recorder_artifact_and_actual_method()`
# @used-by :meth:`test_experiments.ExperimentTests.test_actual_exec_wrapper_with_nested_shell_plan_receipt_is_supported()`
# @used-by :meth:`test_experiments.ExperimentTests.test_actual_namespaced_cua_read_is_recognized_but_text_header_does_not_prove_identity()`
# @used-by :meth:`test_experiments.ExperimentTests.test_amended_expectation_requires_new_observation_and_retains_original()`
# @used-by :meth:`test_experiments.ExperimentTests.test_canonical_harness_cli_plan_commit_receipt_is_supported()`
# @used-by :meth:`test_experiments.ExperimentTests.test_disconfirming_false_cannot_be_forced_to_verified()`
# @used-by :meth:`test_experiments.ExperimentTests.test_explicit_native_primitives_with_same_context_remain_supported()`
# @used-by :meth:`test_experiments.ExperimentTests.test_german_url_and_turkish_ip_remain_distinct_actual_conditions()`
# @used-by :meth:`test_experiments.ExperimentTests.test_missing_and_unparsable_measurements_are_unverified_not_refuted()`
# @used-by :meth:`test_experiments.ExperimentTests.test_missing_native_identity_cannot_be_repaired_by_declared_session()`
# @used-by :meth:`test_experiments.ExperimentTests.test_modified_primary_bytes_or_plan_is_rejected()`
# @used-by :meth:`test_experiments.ExperimentTests.test_native_action_before_after_states_and_raw_predicate_can_verify_transition()`
# @used-by :meth:`test_experiments.ExperimentTests.test_positive_http_observation_is_verified_and_hashed()`
# @used-by :meth:`test_experiments.ExperimentTests.test_unavailable_run_preserves_gap_and_does_not_assert_property()`
# @used-by :meth:`test_experiments.ExperimentTests.test_unconditional_literal_action_with_locator_options_remains_supported()`
# @used-by :mod:`agent_tools.experiments`
def load_experiment(root, reference):
	return ExperimentRunValidator.load(root, reference)
# @used-by :meth:`test_experiments.ExperimentTests.test_modified_primary_bytes_or_plan_is_rejected()`
# @used-by :mod:`agent_tools.experiments`
def load_plan(root, reference):
	return ExperimentPlanStore(root).load(reference)
# @used-by :func:`agent_tools.cli_domains._op_prepare_experiment()`
# @used-by :meth:`test_analysis_workflow.ProjectCase.experiment_gap()`
# @used-by :meth:`test_evidence_contract.EvidenceContractTests.test_experiment_primary_uses_recorder_artifact_and_actual_method()`
# @used-by :meth:`test_experiments.ExperimentTests.plan()`
# @used-by :mod:`agent_tools.experiments`
def prepare_experiment(root, requirement, *, amendment_of=None, amendment_reason=None):
	return ExperimentPlanStore(root).prepare(requirement, amendment_of=amendment_of, amendment_reason=amendment_reason)
# @used-by :func:`agent_tools.cli_domains._op_record_experiment()`
# @used-by :meth:`test_analysis_workflow.ProjectCase.experiment_gap()`
# @used-by :meth:`test_evidence_contract.EvidenceContractTests.test_experiment_primary_uses_recorder_artifact_and_actual_method()`
# @used-by :meth:`test_experiments.ExperimentTests.run_record()`
# @used-by :meth:`test_experiments.ExperimentTests.test_actual_exec_wrapper_with_nested_shell_plan_receipt_is_supported()`
# @used-by :meth:`test_experiments.ExperimentTests.test_actual_namespaced_cua_read_is_recognized_but_text_header_does_not_prove_identity()`
# @used-by :meth:`test_experiments.ExperimentTests.test_before_snapshot_cannot_be_taken_from_action_after_output()`
# @used-by :meth:`test_experiments.ExperimentTests.test_browser_label_http_and_action_in_comment_are_not_interaction_proof()`
# @used-by :meth:`test_experiments.ExperimentTests.test_canonical_harness_cli_plan_commit_receipt_is_supported()`
# @used-by :meth:`test_experiments.ExperimentTests.test_conflicting_native_action_parameter_and_output_identity_is_unknown()`
# @used-by :meth:`test_experiments.ExperimentTests.test_context_or_session_difference_is_rejected_even_for_same_tab_ids()`
# @used-by :meth:`test_experiments.ExperimentTests.test_egress_must_be_measured_in_the_actual_action_browser_context()`
# @used-by :meth:`test_experiments.ExperimentTests.test_explicit_native_primitives_with_same_context_remain_supported()`
# @used-by :meth:`test_experiments.ExperimentTests.test_false_branch_loops_definitions_and_dynamic_scripts_never_prove_executed_click()`
# @used-by :meth:`test_experiments.ExperimentTests.test_german_url_and_turkish_ip_remain_distinct_actual_conditions()`
# @used-by :meth:`test_experiments.ExperimentTests.test_missing_native_identity_cannot_be_repaired_by_declared_session()`
# @used-by :meth:`test_experiments.ExperimentTests.test_native_action_before_after_states_and_raw_predicate_can_verify_transition()`
# @used-by :meth:`test_experiments.ExperimentTests.test_native_actions_without_prior_plan_commit_receipt_cannot_be_verified()`
# @used-by :meth:`test_experiments.ExperimentTests.test_native_before_and_action_in_different_browser_tabs_are_rejected()`
# @used-by :meth:`test_experiments.ExperimentTests.test_native_private_mode_requires_explicit_browser_context_inspection()`
# @used-by :meth:`test_experiments.ExperimentTests.test_no_cookies_does_not_prove_incognito()`
# @used-by :meth:`test_experiments.ExperimentTests.test_unconditional_literal_action_with_locator_options_remains_supported()`
# @used-by :mod:`agent_tools.experiments`
def record_experiment(root, specification, *, tool_trace=None):
	return ExperimentRunValidator.record(root, specification, tool_trace=tool_trace)
# @used-by :meth:`test_schema_help_and_analysis_merge_m10.SchemaHelpAndAnalysisMergeM10Tests.test_validators_emit_actionable_hints()`
# @used-by :mod:`agent_tools.experiments`
def requirement_issues(requirements):
	return RequirementValidator(requirements).issues()
# @used-by :meth:`test_experiments.ExperimentTests.test_positive_http_observation_is_verified_and_hashed()`
# @used-by :meth:`test_experiments.ExperimentTests.test_unavailable_run_preserves_gap_and_does_not_assert_property()`
# @used-by :mod:`agent_tools.experiments`
def result_issues(root, requirement, result):
	return ResultValidator(root, requirement, result).issues()
__all__ = ['BrowserTraceInspector', 'ExperimentPlanStore', 'ExperimentRunValidator', 'METHODS', 'OPERATORS', 'PROPERTY_METHODS', 'STATUSES', '_event_actions', '_event_browser_identity', 'digest', 'evaluate_assertions', 'load_experiment', 'load_plan', 'prepare_experiment', 'record_experiment', 'requirement_issues', 'result_issues']
