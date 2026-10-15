"""Stable diagnostics shared by structural and evidence checks."""


def problem(code, field, message, *, claim_id=None, file=None, hint=None, severity='error'):
    return {k: v for k, v in dict(code=code, field=field, message=message,
        claim_id=claim_id, file=str(file) if file else None, hint=hint, severity=severity).items() if v is not None}


class ValidationError(ValueError):
    def __init__(self, issues):
        self.issues = issues
        super().__init__('\n'.join(f"{x['code']} {x.get('claim_id', '')} {x['field']}: {x['message']}" for x in issues))


def require_valid(issues):
    errors = [x for x in issues if x.get('severity', 'error') == 'error']
    if errors:
        raise ValidationError(errors)

