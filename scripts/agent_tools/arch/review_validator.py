# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Add arch-auditor subagent role and content-addressed review CLI":
# https://github.com/dmitry-ai/harness/issues/361
from __future__ import annotations
from typing import Any
_FINDING_CLASSES = frozenset({'missing_pattern', 'other', 'overengineering', 'participant_mismatch', 'pattern_washing'})
_FINDING_SEVERITIES = frozenset({'critical', 'minor', 'significant'})
_FINDING_STATUSES = frozenset({'open', 'resolved'})
_OUTCOMES = frozenset({'grounded', 'missing_pattern', 'overengineered', 'pattern_washing'})
_RESULTS = frozenset({'approved', 'needs_changes'})
_RISKS = frozenset({'high', 'low', 'medium'})
_VALID_CATS = frozenset({'Architectural', 'Behavioral', 'Concurrency', 'Creational', 'Structural', 'idiom_exception'})
class ArchitectureAuditValidator:
	# @used-by :meth:`ArchitectureAuditValidator._validate_pattern_check()`
	def _approval_conflict(self, idx: int, result: Any, item: dict[str, Any]) -> str | None:
		out_v, risk_v, pv = (item.get('outcome'), item.get('overengineering_risk'), item.get('participants_verified'))
		bad = 'approved' == result and ('grounded' != out_v or True is not pv or 'high' == risk_v)
		return f'approved verdict conflicts with pattern_checks[{idx}] (outcome={out_v}, participants_verified={pv}, overengineering_risk={risk_v})' if bad else None
	# @used-by :meth:`ArchitectureAuditValidator.validate()`
	def _validate_finding(self, idx: int, item: Any) -> list[str]:
		r: list[str] = []
		if not isinstance(item, dict):
			r.append(f'findings[{idx}] must be a JSON object')
		else:
			for fld in ('id', 'target', 'description'):
				if not isinstance(item.get(fld), str) or not item[fld].strip():
					r.append(f'findings[{idx}].{fld} must be a non-empty string')
			if item.get('violation_class') not in _FINDING_CLASSES:
				r.append(f'findings[{idx}].violation_class is invalid')
			if item.get('severity') not in _FINDING_SEVERITIES:
				r.append(f'findings[{idx}].severity is invalid')
			if item.get('status') not in _FINDING_STATUSES:
				r.append(f'findings[{idx}].status must be open or resolved')
		return r
	# @used-by :meth:`ArchitectureAuditValidator.validate()`
	def _validate_header(self, verdict: dict[str, Any], package_rel: str, package_sha256: str) -> list[str]:
		r: list[str] = []
		if 1 != verdict.get('schema_version'):
			r.append('schema_version must equal 1')
		if 'falsifier' != verdict.get('review_mode'):
			r.append('review_mode must equal falsifier')
		if package_rel and verdict.get('package') != package_rel:
			r.append('package path does not match frozen review package')
		if package_sha256 and verdict.get('package_sha256') != package_sha256:
			r.append('package_sha256 does not match frozen review package')
		if verdict.get('result') not in _RESULTS:
			r.append('result must be approved or needs_changes')
		if not isinstance(verdict.get('summary'), str) or not verdict['summary'].strip():
			r.append('summary must be a non-empty string')
		return r
	# @used-by :meth:`ArchitectureAuditValidator.validate()`
	def _validate_pattern_check(self, idx: int, item: Any, *, result: Any) -> list[str]:
		r: list[str] = []
		if not isinstance(item, dict):
			r.append(f'pattern_checks[{idx}] must be a JSON object')
		else:
			for fld in ('pattern', 'evidence'):
				if not isinstance(item.get(fld), str) or not item[fld].strip():
					r.append(f'pattern_checks[{idx}].{fld} must be a non-empty string')
			if item.get('category') not in _VALID_CATS:
				r.append(f'pattern_checks[{idx}].category is not a valid catalog category')
			if not isinstance(item.get('participants_verified'), bool):
				r.append(f'pattern_checks[{idx}].participants_verified must be boolean')
			if item.get('overengineering_risk') not in _RISKS or item.get('outcome') not in _OUTCOMES:
				r.append(f'pattern_checks[{idx}] has invalid overengineering_risk or outcome')
			conflict = self._approval_conflict(idx, result, item)
			if None is not conflict:
				r.append(conflict)
		return r
	# @used-by :meth:`ArchitectureAuditValidator.validate()`
	def _validate_result_semantics(self, result: Any, findings: Any) -> list[str]:
		r: list[str] = []
		if not isinstance(findings, list):
			r.append('findings must be a JSON list')
		else:
			open_items = [f for f in findings if isinstance(f, dict) and 'open' == f.get('status')]
			blocking = [f for f in open_items if f.get('severity') in ('significant', 'critical')]
			if 'approved' == result and blocking:
				r.append('approved verdict cannot contain open significant or critical findings')
			if 'needs_changes' == result and (not open_items):
				r.append('needs_changes verdict must include at least one open finding')
		return r
	# @used-by :func:`agent_tools.arch.review_store.record_arch_review()`
	# @used-by :meth:`test_arch_review_cli.ArchReviewCliTests.test_validator_rejects_pattern_washing_and_rubber_stamp_approvals()`
	def validate(self, verdict: Any, package: dict[str, Any] | None=None, *, package_rel: str='', package_sha256: str='') -> list[str]:
		if not isinstance(verdict, dict):
			r = ['verdict must be a JSON object']
		else:
			r = self._validate_header(verdict, package_rel, package_sha256)
			checks = verdict.get('pattern_checks')
			if not isinstance(checks, list) or not checks:
				r.append('pattern_checks must be a non-empty JSON list')
			else:
				for idx, item in enumerate(checks):
					r.extend(self._validate_pattern_check(idx, item, result=verdict.get('result')))
			findings = verdict.get('findings')
			r.extend(self._validate_result_semantics(verdict.get('result'), findings))
			if isinstance(findings, list):
				for idx, item in enumerate(findings):
					r.extend(self._validate_finding(idx, item))
		return r
__all__ = ['ArchitectureAuditValidator']
