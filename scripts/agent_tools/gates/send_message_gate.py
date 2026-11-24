# 2026-11-24 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Enforce single falsifier review default and block duplicate send_message reports":
# https://github.com/dmitry-ai/harness/issues/226
from __future__ import annotations
import re
NAME = 'REVIEW-4-SEND-MESSAGE-GATE'
PRIORITY = 96
TOOLS = frozenset({'send_message'})
_FENCE_JSON_RE = re.compile(r'^\s*```(?:json)?\s*\{', re.I)
_MAX_JSON_MSG_BYTES = 4096
_VERDICT_KEY_RE = re.compile(r'"(?:claim_reviews|disproved_claims)"\s*:')
_VERDICT_META_RE = re.compile(r'"(?:schema_version|package_sha256|findings|result)"\s*:')
def _is_duplicate_verdict_payload(msg: str) -> bool:
	stripped = msg.lstrip()
	looks_json = stripped.startswith('{') or bool(_FENCE_JSON_RE.match(msg))
	has_verdict = bool(_VERDICT_KEY_RE.search(msg)) and bool(_VERDICT_META_RE.search(msg))
	is_large_json = looks_json and _MAX_JSON_MSG_BYTES < len(msg.encode('utf-8')) and bool(_VERDICT_META_RE.search(msg))
	return has_verdict or is_large_json
def check(name: str, args: dict, payload: dict | None=None) -> str | None:
	r: str | None = None
	if 'send_message' == name:
		msg = str((args or {}).get('Message') or '')
		if msg and _is_duplicate_verdict_payload(msg):
			r = 'REVIEW-4-SEND-MESSAGE-GATE: Do not duplicate the JSON review verdict via send_message; return the single JSON verdict once directly in your final PLANNER_RESPONSE (end your turn without calling send_message).'
	return r
