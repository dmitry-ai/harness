# 2026-11-27 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from pathlib import Path
from typing import Any
import hashlib
from Df.Harness.Arch.Enforcement import Enforcement
from Df.Harness.Arch.SpecValidator import SpecValidator
from Df.Harness.Arch.TriggerClassifier import TriggerClassifier
# 2026-11-27 "Reorganize Harness scripts into single-class Mage2Pro modules": https://github.com/dmitry-ai/harness/issues/338
class Evaluator:
	# @used-by :meth:`Evaluator.evaluate_response()`
	@staticmethod
	def __response_receipt_violations(root: Path | None, response: str, significant: bool) -> list[str]:
		r: list[str] = []
		if None is not root:
			root_p = Path(root).resolve()
			idx_paths = Enforcement.arch_index_paths(root_p, None)
			index, _ = Enforcement.load_merged_index(idx_paths)
			for item in Enforcement.blocking_findings(index):
				fid, sev, desc = (item.get('id'), item.get('severity'), item.get('description'))
				r.append(f'ARCH-2 (OPEN_ARCH_FINDING): Open arch-auditor finding {fid} ({sev}): {desc}')
			if significant and Enforcement.is_arch_governed(root_p, None, {}, idx_paths):
				resp_sha = hashlib.sha256(response.encode('utf-8')).hexdigest()
				matched = any((isinstance(v, dict) and 'response' == v.get('kind') and v.get('response_sha256') == resp_sha for v in (index.get('approved_subjects') or {}).values()))
				if not matched:
					r.append('ARCH-2 (MISSING_ARCH_AUDIT_RECEIPT): Significant architectural response requires an approved arch-auditor receipt matching response_sha256; run arch-prepare --kind response, invoke arch-auditor, and record with arch-record-review.')
		return r
	# @used-by :func:`agent_tools.arch.evaluator.check_runner_architecture()`
	# @used-by :meth:`test_df_harness_s11_wave2e_arch.DfHarnessArchWave2eTests.test_evaluator_checks_response_receipts_and_runner()`
	@staticmethod
	def check_runner(runner) -> None:
		chk = Evaluator().evaluate_response(runner.root, runner.turn, runner.response, blocked_report=bool(getattr(runner, 'blocked_report', False)))
		runner.value['arch_audit_check'] = chk
		if not chk['verified']:
			runner._fail_gate('architecture', '; '.join(chk['violations']))
	# @used-by :func:`agent_tools.arch.evaluator.evaluate_response_architecture()`
	# @used-by :meth:`Evaluator.check_runner()`
	# @used-by :meth:`test_df_harness_s11_wave2e_arch.DfHarnessArchWave2eTests.test_evaluator_checks_response_receipts_and_runner()`
	def evaluate_response(self, root: Path | None, turn: dict[str, Any] | None, response: str | None, *, blocked_report: bool=False) -> dict[str, Any]:
		text = response or ''
		trig = TriggerClassifier.classify_markdown(text, is_issue=False, is_parent_issue=False)
		if blocked_report:
			r: dict[str, Any] = {'verified': True, 'triggered': False, 'significant': False, 'reasons': [], 'patterns': [], 'violations': []}
		else:
			violations: list[str] = []
			patterns: list[str] = []
			if trig['triggered']:
				spec_res = SpecValidator().validate(text, require_full_fields=False)
				patterns = list(spec_res['patterns'])
				violations.extend((f"ARCH-1 ({it['code']}): {it['message']}" for it in spec_res['issues']))
			violations.extend(Evaluator.__response_receipt_violations(root, text, bool(trig['significant'])))
			r = {'verified': not violations, 'triggered': bool(trig['triggered']), 'significant': bool(trig['significant']), 'reasons': list(trig['reasons']), 'patterns': patterns, 'violations': violations}
		return r
