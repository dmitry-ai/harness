# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from typing import Any
from Df.Core.lib.array.first import df_last
from Df.Harness.lib.trace_common import dfh_parse_tool_args
import re
# 2026-11-26 "Move turn lifecycle subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/383
_ANSWER_HEADER_RE = re.compile(r'^(A\d+):\s*(.*)$')
_META_TS_RE = re.compile(r'^(Created|Completed)\s+At:\s*(.+?)\s*$')
# @used-by :func:`_record_ask_call()`
def _extract_question_texts(call: dict) -> list[str]:
	args = dfh_parse_tool_args(call.get('args', {}))
	qs = args.get('questions') if isinstance(args.get('questions'), list) else []
	return [str(q.get('question') or '').strip() for q in qs if isinstance(q, dict) and str(q.get('question') or '').strip()]
# @used-by :func:`_parse_output_envelope()`
def _parse_answers(body_lines: list[str]) -> list[dict[str, str]]:
	items: list[dict[str, str]] = []
	for line in body_lines:
		m = _ANSWER_HEADER_RE.match(line)
		if m:
			items.append({'id': m.group(1), 'text': m.group(2)})
		elif items:
			items[-1]['text'] = (items[-1]['text'] + '\n' + line) if items[-1]['text'] else line
	return [{'id': it['id'], 'text': it['text'].strip()} for it in items]
# @used-by :func:`_record_ask_call()`
def _parse_output_envelope(raw_content: str) -> tuple[str | None, str | None, list[dict[str, str]], str]:
	asked_at, answered_at = (None, None)
	lines = (raw_content or '').splitlines()
	idx = 0
	while idx < len(lines):
		m = _META_TS_RE.match(lines[idx].strip())
		if not m:
			break
		if 'Created' == m.group(1):
			asked_at = m.group(2).strip()
		else:
			answered_at = m.group(2).strip()
		idx += 1
	body_lines = lines[idx:]
	return (asked_at, answered_at, _parse_answers(body_lines), '\n'.join(body_lines).strip())
# @used-by :func:`dfh_extract_ask_question_clarifications()`
def _record_ask_call(row: dict, call: dict, out_row: dict | None) -> dict[str, Any]:
	raw = str(out_row.get('content') or '') if isinstance(out_row, dict) else ''
	env_asked, env_answered, answers, clean_body = _parse_output_envelope(raw)
	asked_at = row.get('created_at') if isinstance(row.get('created_at'), str) and row['created_at'].strip() else env_asked
	out_ts = out_row.get('created_at') if isinstance(out_row, dict) and isinstance(out_row.get('created_at'), str) else None
	return {'ask_step': row.get('step_index'), 'answer_step': out_row.get('step_index') if isinstance(out_row, dict) else None, 'asked_at': asked_at, 'answered_at': env_answered or out_ts, 'questions': _extract_question_texts(call), 'answers': answers, 'raw_output': clean_body}
# @used-by :func:`agent_tools.platforms.clarifications.build_segment_metadata()`
# @used-by :meth:`Df.Harness.Platform.Antigravity.TurnScanner.TurnScanner.__finalize_segment()`
def dfh_build_segment_metadata(segment: list[dict], seg_models: list[str] | tuple[str, ...], config_fn) -> dict[str, Any]:
	raw_model = df_last(seg_models)
	model_name, effort_val = (None, None)
	if raw_model:
		cfg = config_fn(raw_model)
		model_name = cfg.get('model') or raw_model
		effort_val = cfg.get('effort')
	r: dict[str, Any] = {'model': model_name, 'effort': effort_val}
	clarifications = dfh_extract_ask_question_clarifications(segment)
	if clarifications:
		r['clarifications'] = clarifications
	return r
# @used-by :func:`dfh_build_segment_metadata()`
# @used-by :meth:`Df.Harness.Platform.ClarificationExtractor.ClarificationExtractor.run()`
# @used-by :meth:`test_df_harness_s11_wave2d_platform_cov.DfHarnessS11Wave2dPlatformCovTests.test_trace_effects_review_and_clarifications()`
def dfh_extract_ask_question_clarifications(segment: list[dict], *, last_fn=df_last) -> list[dict[str, Any]]:
	r: list[dict[str, Any]] = []
	for pos, row in enumerate(segment or ()):
		if not isinstance(row, dict) or 'PLANNER_RESPONSE' != row.get('type'):
			continue
		calls = [c for c in row.get('tool_calls') or () if isinstance(c, dict)]
		for c_idx, call in enumerate(calls):
			if 'ask_question' == call.get('name'):
				out_row = dfh_find_generic_output(segment, pos, c_idx, last_fn=last_fn)
				r.append(_record_ask_call(row, call, out_row))
	return r
# @used-by :func:`agent_tools.platforms.clarifications._find_generic_output()`
# @used-by :func:`dfh_extract_ask_question_clarifications()`
def dfh_find_generic_output(segment: list[dict], pos: int, call_idx: int, *, last_fn=df_last) -> dict | None:
	generics: list[dict] = []
	for cand in segment[pos + 1:]:
		if not isinstance(cand, dict):
			continue
		if cand.get('type') in ('PLANNER_RESPONSE', 'USER_INPUT', 'CHECKPOINT'):
			break
		if 'GENERIC' == cand.get('type'):
			generics.append(cand)
	return generics[call_idx] if call_idx < len(generics) else last_fn(generics)
# @used-by :meth:`Df.Harness.Platform.Antigravity.TurnScanner.TurnScanner.__merge_pending()`
def dfh_merge_segment_metadata(merged: dict[str, Any], items: list[dict[str, Any]]) -> dict[str, Any]:
	req_ts = next((it.get('request_timestamp') for it in items if it.get('request_timestamp')), None)
	if None is not req_ts:
		merged['request_timestamp'] = req_ts
	for key in ('model', 'effort'):
		val = next((it.get(key) for it in reversed(items) if it.get(key)), None)
		if None is not val:
			merged[key] = val
	clars = [c for it in items for c in it.get('clarifications') or ()]
	if clars:
		merged['clarifications'] = clars
	return merged
