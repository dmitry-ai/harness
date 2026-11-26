# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Enforce PreToolUse governance gate for ask_question calls":
# https://github.com/dmitry-ai/harness/issues/374
from __future__ import annotations
import re
NAME = 'SCOPE-2-ASK-QUESTION-GATE'
PRIORITY = 97
TOOLS = frozenset({'ask_question'})
_DEFERRAL_RE = re.compile(r'(?i)(?:continuation\.md|\b(?:defer|phased|next\s+turn|later\s+turn|subsequent\s+turn|split\s+across\s+turns)\b|\bphase\s*1\b.*\b(?:phase\s*2|later|next|defer|continuation)|\u043f\u043e\u044d\u0442\u0430\u043f\u043d|\u043e\u0442\u043b\u043e\u0436\u0438\u0442|\u043f\u0435\u0440\u0435\u043d\u0435\u0441\u0442\u0438\s+(?:\u0432|\u043d\u0430)\s+(?:\u0441\u043b\u0435\u0434\u0443\u044e\u0449|\u0434\u0440\u0443\u0433|\u043e\u0442\u0434\u0435\u043b\u044c\u043d)|\u0441\u043b\u0435\u0434\u0443\u044e\u0449\w*\s+(?:\u0445\u043e\u0434|\u043f\u0440\u043e\u0445\u043e\u0434)|\u0444\u0430\u0437\w*\s*1\b.*\u0444\u0430\u0437\w*\s*2)')
_EXPLICIT_STOP_RE = re.compile(r'(?i)(?:stop\s+(?:the|this)\s+turn|end\s+(?:the|this)\s+turn|return\s+control|pause\s+(?:the|this)\s+turn|\u043e\u0441\u0442\u0430\u043d\u043e\u0432\w*\s+\u0445\u043e\u0434|\u0437\u0430\u0432\u0435\u0440\u0448\w*\s+\u0445\u043e\u0434\s+\u0431\u0435\u0437|\u0432\u0435\u0440\u043d\w*\s+\u0443\u043f\u0440\u0430\u0432\u043b\u0435\u043d\u0438)')
_RECOMMENDED_RE = re.compile(r'(?i)(?:\(\s*(?:recommended|\u0440\u0435\u043a\u043e\u043c\u0435\u043d\u0434\u0443\u0435\u0442\u0441\u044f|\u0440\u0435\u043a\u043e\u043c\u0435\u043d\u0434\u0443\u0435\u043c\u044b\u0439)\s*\)|\brecommended\b)')
_STOP_GATE_BYPASS_RE = re.compile(r'(?i)(?:confirm\s+when\s+.*(?:fix(?:es)?|patch(?:es)?|blocker|harness|hook|bug)\s+.*(?:applied|resolved|fixed|done|ready)|wait\s+for\s+.*(?:harness|hook|blocker)\s+fix|stop\s+gate|\u043f\u043e\u0434\u0442\u0432\u0435\u0440\u0434\w*[,\s]+\u043a\u043e\u0433\u0434\u0430\s+.*(?:\u0438\u0441\u043f\u0440\u0430\u0432\u043b\u0435\u043d|\u0431\u043b\u043e\u043a\u0435\u0440|\u0445\u0443\u043a|harness).*(?:\u043f\u0440\u0438\u043c\u0435\u043d|\u0443\u0441\u0442\u0440\u0430\u043d|\u0433\u043e\u0442\u043e\u0432)|(?:\u043f\u0440\u043e\u0434\u043e\u043b\u0436\u0438\u0442\u044c|\u0432\u043e\u0437\u043e\u0431\u043d\u043e\u0432\u0438\u0442\u044c)\s+\u043f\u043e\u0441\u043b\u0435\s+(?:\u0438\u0441\u043f\u0440\u0430\u0432\u043b\u0435\u043d|\u043f\u043e\u0447\u0438\u043d\u043a|\u0443\u0441\u0442\u0440\u0430\u043d\u0435\u043d))')
# @used-by :func:`check()`
def _check_question_item(item: dict) -> str | None:
	q_text = str(item.get('question') or '')
	opts = [str(opt or '') for opt in (item.get('options') or ())]
	combined = '\n'.join((q_text, *opts))
	if _STOP_GATE_BYPASS_RE.search(combined):
		r: str | None = 'SCOPE-2-ASK-QUESTION-GATE: Do not use ask_question to park a blocked turn or bypass Stop Gate; document the blocker in \ua616/data/continuation.md and exit via harness.py answer-prepare --blocked-report.'
	elif any((_is_undisclosed_recommended_deferral(opt) for opt in opts)):
		r = 'SCOPE-2-ASK-QUESTION-GATE: Do not recommend undisclosed mid-turn scope deferral (continuation.md / phased cutoff) under (Recommended); execute the full explicit request or explicitly warn that the turn will stop and return control before completing remaining items.'
	else:
		r = None
	return r
# @used-by :func:`_check_question_item()`
def _is_undisclosed_recommended_deferral(option: str) -> bool:
	return bool(_RECOMMENDED_RE.search(option) and _DEFERRAL_RE.search(option) and (not _EXPLICIT_STOP_RE.search(option)))
# @used-by :func:`agent_tools.gates._load_builtin_entry()`
def check(name: str, args: dict, payload: dict | None=None) -> str | None:
	r: str | None = None
	if 'ask_question' == name:
		questions = (args or {}).get('questions')
		if isinstance(questions, list):
			for item in questions:
				if isinstance(item, dict):
					hit = _check_question_item(item)
					if None is not hit:
						r = hit
						break
	return r
