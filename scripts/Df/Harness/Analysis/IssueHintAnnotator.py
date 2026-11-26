# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
_HINTS = {
	'experiment': ('schema-help experiment', 'Hint: run "harness.py schema-help experiment" for required fields, valid property/method pairs, and assertion locators.'),
	'review': ('schema-help review', 'Hint: run "harness.py schema-help review" for review_mode (falsifier vs standard), claim_targets, and schema_version 2 fields.'),
}
# 2026-11-26 "Move analysis workflow classes into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/380
class IssueHintAnnotator:
	# @used-by :func:`agent_tools.schema_help.annotate_experiment_issues()`
	# @used-by :func:`agent_tools.schema_help.annotate_review_issues()`
	# @used-by :meth:`Df.Harness.Experiment.RequirementValidator.RequirementValidator.issues()`
	# @used-by :meth:`Df.Harness.Review.ReportValidator.ReportValidator.validate()`
	# @used-by :meth:`test_df_harness_s11_wave2a.DfHarnessS11Wave2aTests.test_schema_help_classes()`
	def __init__(self, kind: str, issues: list[str]) -> None:
		self.__kind = kind
		self.__issues = issues
	# @used-by :func:`agent_tools.schema_help.annotate_experiment_issues()`
	# @used-by :func:`agent_tools.schema_help.annotate_review_issues()`
	# @used-by :meth:`Df.Harness.Experiment.RequirementValidator.RequirementValidator.issues()`
	# @used-by :meth:`Df.Harness.Review.ReportValidator.ReportValidator.validate()`
	# @used-by :meth:`test_df_harness_s11_wave2a.DfHarnessS11Wave2aTests.test_schema_help_classes()`
	def annotate(self) -> list[str]:
		marker, hint = _HINTS[self.__kind]
		return [msg if marker in msg else f'{msg} ({hint})' for msg in self.__issues]