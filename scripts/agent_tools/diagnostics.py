# 2026-10-15 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Eliminate redundant subagent searches with HTTP evidence caching, structured Analysis.json workflow, and in-chat resume":
# https://github.com/dmitry-ai/harness/issues/4
# 2026-10-31 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Reorganize AI into universal harness repository, translate rules and documentation to English, format per P.md, and enforce issue-driven Git workflow":
# https://github.com/dmitry-ai/harness/issues/26
def problem(code, field, message, *, claim_id=None, file=None, hint=None, severity='error'):
	return {k: v for k, v in dict(code=code, field=field, message=message, claim_id=claim_id, file=str(file) if file else None, hint=hint, severity=severity).items() if None is not v}
class ValidationError(ValueError):
	def __init__(self, issues):
		self.issues = issues
		super().__init__('\n'.join((f"{x['code']} {x.get('claim_id', '')} {x['field']}: {x['message']}" for x in issues)))
def require_valid(issues):
	errors = [x for x in issues if 'error' == x.get('severity', 'error')]
	if errors:
		raise ValidationError(errors)
