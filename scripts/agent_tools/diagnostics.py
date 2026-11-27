# 2026-10-15 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
# 2026-11-26 "Replace duplicated Harness logic with Df helpers": https://github.com/dmitry-ai/harness/issues/337
from Df.Core.lib.array.clean.main import df_clean_null
# 2026-11-26 "Move analysis workflow classes into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/380
from Df.Harness.Project.Diagnostics import Diagnostics
from Df.Harness.Project.IssueValidator import IssueValidator
from Df.Harness.Project.ValidationError import ValidationError
# @used-by :func:`agent_tools.journal_integrity.check_project_journal_problems()`
# @used-by :meth:`test_df_harness_dedup_s8.DfHarnessDedupS8Tests.test_clean_null_and_unique_fast_delegation_to_df()`
# @used-by :mod:`agent_tools.diagnostics`
def problem(code, field, message, *, claim_id=None, file=None, hint=None, severity='error'):
	return Diagnostics(clean_null=df_clean_null).problem(code, field, message, claim_id=claim_id, file=file, hint=hint, severity=severity)
# @used-by :func:`agent_tools.analysis.validate_analysis()`
# @used-by :mod:`agent_tools.diagnostics`
def require_valid(issues):
	IssueValidator(issues).require_valid()
__all__ = ['ValidationError', 'df_clean_null', 'problem', 'require_valid']