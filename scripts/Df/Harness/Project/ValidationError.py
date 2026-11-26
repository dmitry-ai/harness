# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from typing import override
# 2026-11-26 "Move analysis workflow classes into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/380
class ValidationError(ValueError):
	# @used-by :meth:`Df.Harness.Project.IssueValidator.IssueValidator.require_valid()`
	# @used-by :meth:`test_schema_help_and_analysis_merge_m10.SchemaHelpAndAnalysisMergeM10Tests.test_validators_emit_actionable_hints()`
	# @see :meth:`ValueError.__init__()`
	@override
	def __init__(self, issues) -> None:
		self.issues = issues
		super().__init__('\n'.join((f"{x['code']} {x.get('claim_id', '')} {x['field']}: {x['message']}" + (f" [hint: {x['hint']}]" if x.get('hint') else '') for x in issues)))