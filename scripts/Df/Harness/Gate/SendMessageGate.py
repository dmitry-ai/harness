# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
import re
# 2026-11-26 "Move verification gate subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/381
class SendMessageGate:
	NAME = 'REVIEW-4-SEND-MESSAGE-GATE'
	PRIORITY = 96
	TOOLS = frozenset({'send_message'})
	__FENCE_JSON_RE = re.compile(r'^\s*```(?:json)?\s*\{', re.I)
	__MAX_JSON_MSG_BYTES = 4096
	__VERDICT_KEY_RE = re.compile(r'"(?:claim_reviews|disproved_claims|pattern_checks)"\s*:')
	__VERDICT_META_RE = re.compile(r'"(?:schema_version|package_sha256|findings|result)"\s*:')
	# @used-by :meth:`SendMessageGate.check()`
	@staticmethod
	def __is_duplicate_verdict_payload(msg: str) -> bool:
		stripped = msg.lstrip()
		looks_json = stripped.startswith('{') or bool(SendMessageGate.__FENCE_JSON_RE.match(msg))
		has_verdict = bool(SendMessageGate.__VERDICT_KEY_RE.search(msg)) and bool(SendMessageGate.__VERDICT_META_RE.search(msg))
		is_large_json = looks_json and SendMessageGate.__MAX_JSON_MSG_BYTES < len(msg.encode('utf-8')) and bool(SendMessageGate.__VERDICT_META_RE.search(msg))
		return has_verdict or is_large_json
	# @used-by :func:`agent_tools.gates.send_message_gate.check()`
	# @used-by :meth:`test_df_harness_s11_wave2b_gate.DfHarnessS11Wave2bGateTests.test_gate_pretool_classes_cover_all_guards()`
	def check(self, name: str, args: dict, payload: dict | None=None) -> str | None:
		r: str | None = None
		if 'send_message' == name:
			msg = str((args or {}).get('Message') or '')
			if msg and SendMessageGate.__is_duplicate_verdict_payload(msg):
				r = 'REVIEW-4-SEND-MESSAGE-GATE: Do not duplicate the JSON review verdict via send_message; return the single JSON verdict once directly in your final PLANNER_RESPONSE (end your turn without calling send_message).'
		return r
