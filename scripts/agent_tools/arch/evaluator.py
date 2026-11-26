# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Add software design pattern specification validator and trigger checks":
# https://github.com/dmitry-ai/harness/issues/349
from __future__ import annotations
from pathlib import Path
from typing import Any
import hashlib
# 2026-11-26
# "Add blocking architecture audit gates with module-hash caching":
# https://github.com/dmitry-ai/harness/issues/363
from .enforcement import _arch_index_paths, _blocking_findings, _is_arch_governed, _load_merged_index
from .spec import validate_arch_spec_markdown
from .triggers import classify_markdown_arch_trigger
# 2026-11-26
# "Add blocking architecture audit gates with module-hash caching":
# https://github.com/dmitry-ai/harness/issues/363
# @used-by :func:`evaluate_response_architecture()`
def _response_receipt_violations(root: Path | None, response: str, significant: bool) -> list[str]:
	r: list[str] = []
	if None is not root:
		root_p = Path(root).resolve()
		idx_paths = _arch_index_paths(root_p, None)
		index, _ = _load_merged_index(idx_paths)
		for item in _blocking_findings(index):
			fid, sev, desc = (item.get('id'), item.get('severity'), item.get('description'))
			r.append(f'ARCH-2 (OPEN_ARCH_FINDING): Open arch-auditor finding {fid} ({sev}): {desc}')
		if significant and _is_arch_governed(root_p, None, {}, idx_paths):
			resp_sha = hashlib.sha256(response.encode('utf-8')).hexdigest()
			matched = any((isinstance(v, dict) and 'response' == v.get('kind') and v.get('response_sha256') == resp_sha for v in (index.get('approved_subjects') or {}).values()))
			if not matched:
				r.append('ARCH-2 (MISSING_ARCH_AUDIT_RECEIPT): Significant architectural response requires an approved arch-auditor receipt matching response_sha256; run arch-prepare --kind response, invoke arch-auditor, and record with arch-record-review.')
	return r
# @used-by :func:`agent_tools.blocked_report._run_runner_audits()`
# @used-by :meth:`test_arch_spec_and_triggers.ArchSpecAndTriggersTests.test_runner_architecture_check_records_state_and_fails_gate_on_missing_patterns()`
# @used-by :mod:`agent_tools.arch.evaluator`
# @used-by :mod:`agent_tools.arch`
def check_runner_architecture(runner) -> None:
	chk = evaluate_response_architecture(runner.root, runner.turn, runner.response, blocked_report=bool(getattr(runner, 'blocked_report', False)))
	runner.value['arch_audit_check'] = chk
	if not chk['verified']:
		runner._fail_gate('architecture', '; '.join(chk['violations']))
# @used-by :func:`agent_tools.gates.answer_checks._architecture_messages()`
# @used-by :func:`check_runner_architecture()`
# @used-by :meth:`test_arch_audit_gates.ArchAuditGatesTests.test_answer_and_stop_gates_enforce_significant_response_receipt_and_open_findings()`
# @used-by :mod:`agent_tools.arch.evaluator`
# @used-by :mod:`agent_tools.arch`
def evaluate_response_architecture(root: Path | None, turn: dict[str, Any] | None, response: str | None, *, blocked_report: bool=False) -> dict[str, Any]:
	text = response or ''
	trig = classify_markdown_arch_trigger(text, is_issue=False, is_parent_issue=False)
	if blocked_report:
		r: dict[str, Any] = {'verified': True, 'triggered': False, 'significant': False, 'reasons': [], 'patterns': [], 'violations': []}
	else:
		violations: list[str] = []
		patterns: list[str] = []
		if trig['triggered']:
			spec_res = validate_arch_spec_markdown(text, require_full_fields=False)
			patterns = list(spec_res['patterns'])
			violations.extend((f"ARCH-1 ({it['code']}): {it['message']}" for it in spec_res['issues']))
		violations.extend(_response_receipt_violations(root, text, bool(trig['significant'])))
		r = {'verified': not violations, 'triggered': bool(trig['triggered']), 'significant': bool(trig['significant']), 'reasons': list(trig['reasons']), 'patterns': patterns, 'violations': violations}
	return r
__all__ = ['check_runner_architecture', 'evaluate_response_architecture']