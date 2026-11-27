# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
import re
# 2026-11-26 "Move turn lifecycle subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/383
# @used-by :func:`_decode_message_payload()`
def _decode_media_lines(msg_fields: list) -> str | None:
	medias: list[str] = []
	for field, kind, val in msg_fields:
		if 9 == field and 2 == kind:
			m_fields = {mf: mv.decode('utf-8', 'replace') for mf, mk, mv in dfh_wire_fields(val) if 2 == mk and mf in (1, 4, 5)}
			uri = m_fields.get(5) or m_fields.get(4) or m_fields.get(1)
			if uri:
				medias.append(f'[Image: {uri}]')
	return '\n'.join(medias) if medias else None
# @used-by :func:`dfh_decode_user_step_entry()`
def _decode_message_payload(payload: bytes | None, status: int) -> tuple[str | None, dict]:
	r, meta = (None, {})
	messages = [val for field, kind, val in dfh_wire_fields(payload or b'') if 19 == field and 2 == kind]
	if messages:
		msg_fields = list(dfh_wire_fields(messages[0]))
		meta = dfh_extract_user_step_meta(msg_fields)
		texts = [val.decode('utf-8') for field, kind, val in msg_fields if 2 == field and 2 == kind and val.decode('utf-8').strip()]
		if not texts and 5 == status:
			texts = dfh_wire_path(messages[0], (3, 1))
		r = texts[0] if texts else _decode_media_lines(msg_fields)
	return (r, meta)
# @used-by :func:`_decode_wire_value()`
# @used-by :func:`dfh_wire_fields()`
def _decode_varint(data: bytes, offset: int) -> tuple[int, int]:
	value, shift = (0, 0)
	while True:
		byte = data[offset]
		offset += 1
		value |= (byte & 127) << shift
		if 128 > byte:
			break
		shift += 7
		if 70 < shift:
			raise ValueError('Unsupported native protobuf varint')
	return (value, offset)
# @used-by :func:`dfh_wire_fields()`
def _decode_wire_value(data: bytes, offset: int, kind: int):
	if 0 == kind:
		r = _decode_varint(data, offset)
	elif 2 == kind:
		size, offset = _decode_varint(data, offset)
		value = data[offset:offset + size]
		if len(value) != size:
			raise ValueError('Native protobuf field is truncated')
		r = (value, offset + size)
	elif kind in (1, 5):
		size = 8 if 1 == kind else 4
		r = (data[offset:offset + size], offset + size)
	else:
		raise ValueError('Unsupported native protobuf encoding')
	return r
# @used-by :func:`_extract_item_slash_cmds()`
def _extract_cmd_names(blob: bytes) -> list[str]:
	r: list[str] = []
	for a, b, c in dfh_wire_fields(blob):
		if 1 == a and 2 == b:
			for x, y, z in dfh_wire_fields(c):
				if 1 == x and 2 == y:
					name = z.decode('utf-8', 'replace').strip()
					if name:
						r.append(name)
	return r
# @used-by :func:`_parse_structured_item()`
def _extract_item_slash_cmds(sv: bytes, seen_non_ws: bool) -> list[dict]:
	r: list[dict] = []
	try:
		for ssf, ssk, ssv in dfh_wire_fields(sv):
			if 27 == ssf and 2 == ssk:
				for name in _extract_cmd_names(ssv):
					r.append({'name': name, 'leading': not seen_non_ws})
	except (ValueError, IndexError, TypeError):
		pass
	return r
# @used-by :func:`dfh_extract_user_step_meta()`
def _parse_structured_item(val: bytes, seen_non_ws: bool, slash_commands: list[dict]) -> bool:
	try:
		sub_fields = list(dfh_wire_fields(val))
	except (ValueError, IndexError, TypeError):
		sub_fields = []
	for sf, sk, sv in sub_fields:
		if 1 == sf and 2 == sk and sv.decode('utf-8', 'replace').strip():
			seen_non_ws = True
		elif 2 == sf and 2 == sk:
			found = _extract_item_slash_cmds(sv, seen_non_ws)
			slash_commands.extend(found)
			seen_non_ws = True
			if found:
				break
	return seen_non_ws
# @used-by :func:`dfh_wire_path()`
def _wire_step_values(values: list, field: int) -> list:
	found: list = []
	for value in values:
		try:
			found.extend((part for number, kind, part in dfh_wire_fields(value or b'') if number == field and 2 == kind))
		except (ValueError, IndexError, TypeError):
			continue
	return found
# @used-by :func:`Df.Harness.lib.ag_metadata.dfh_apply_requested_config()`
# @used-by :func:`Df.Harness.lib.ag_metadata.dfh_model_metadata()`
# @used-by :func:`agent_tools.meta.formatting._split_model_and_effort()`
# @used-by :meth:`Df.Harness.Platform.Antigravity.ExecutorMetadataReader.ExecutorMetadataReader.run()`
# @used-by :meth:`Df.Harness.Platform.Antigravity.TurnScanner.TurnScanner.__finalize_segment()`
def dfh_configuration(value) -> dict:
	if not isinstance(value, str) or (not value.strip()):
		r = {'model': None, 'effort': None}
	else:
		match = re.fullmatch('(.+)-(minimal|low|medium|high|xhigh|max|ultra)', value)
		r = {'model': match[1], 'effort': match[2]} if match else {'model': value, 'effort': None}
	return r
# @used-by :func:`Df.Harness.lib.ag_inputs.dfh_native_inputs()`
# @used-by :func:`agent_tools.platforms.antigravity._decode_user_step()`
# @used-by :func:`dfh_extract_step_text()`
def dfh_decode_user_step_entry(payload, status: int, index: int, load_transcript) -> tuple[str, dict]:
	r, meta = (None, {})
	try:
		r, meta = _decode_message_payload(payload, status)
	except (IndexError, UnicodeError):
		if 5 != status:
			raise ValueError('Exact native user text is unavailable; do not reconstruct it from summaries')
	if None is r and 5 == status:
		r = dfh_extract_transcript_user_input(load_transcript().get(index))
	if None is r:
		raise ValueError('Exact native user text is unavailable; do not reconstruct it from summaries')
	return (r, meta)
# @used-by :func:`Df.Harness.lib.turn_routing_ops._extract_step_text_from_db()`
def dfh_extract_step_text(payload) -> str | None:
	r: str | None = None
	try:
		r, _ = dfh_decode_user_step_entry(payload, 3, 0, lambda: {})
	except ValueError:
		r = None
	return r
# @used-by :func:`dfh_decode_user_step_entry()`
# @used-by :meth:`Df.Harness.Platform.Antigravity.ReviewProver.ReviewProver.__build_extra_fields()`
def dfh_extract_transcript_user_input(t_row) -> str | None:
	r: str | None = None
	if isinstance(t_row, dict):
		raw = t_row.get('content')
		if isinstance(raw, str):
			m = re.search('<USER_REQUEST>\\r?\\n([\\s\\S]*?)\\r?\\n</USER_REQUEST>', raw)
			if m and m.group(1).strip():
				r = m.group(1)
			elif raw.strip() and '<USER_REQUEST>' not in raw:
				r = raw
		if None is r and isinstance(t_row.get('media'), list):
			uris = [f"[Image: {item['uri']}]" for item in t_row['media'] if isinstance(item, dict) and item.get('uri')]
			if uris:
				r = '\n'.join(uris)
	return r
# @used-by :func:`_decode_message_payload()`
def dfh_extract_user_step_meta(msg_fields: list) -> dict:
	has_items, seen_non_ws, slash_commands = (False, False, [])
	for field, kind, val in msg_fields:
		if 3 == field and 2 == kind:
			has_items = True
			seen_non_ws = _parse_structured_item(val, seen_non_ws, slash_commands)
	return {'has_structured_items': True, 'slash_commands': slash_commands} if has_items else {}
# @used-by :func:`Df.Harness.lib.ag_metadata.dfh_apply_requested_config()`
# @used-by :meth:`Df.Harness.Platform.Antigravity.ExecutorMetadataReader.ExecutorMetadataReader.run()`
def dfh_generation_matches_executor(generation_model, executor_model) -> bool:
	r = False
	if isinstance(generation_model, str) and generation_model.strip() and isinstance(executor_model, str) and executor_model.strip():
		g_val, e_val = (generation_model.strip(), executor_model.strip())
		r = g_val == e_val or g_val.startswith(e_val + '-')
	return r
# @used-by :func:`Df.Harness.lib.ag_metadata._read_step_model_history()`
# @used-by :func:`Df.Harness.lib.ag_metadata.dfh_query_step_model_ids()`
# @used-by :func:`_decode_media_lines()`
# @used-by :func:`_decode_message_payload()`
# @used-by :func:`_extract_cmd_names()`
# @used-by :func:`_extract_item_slash_cmds()`
# @used-by :func:`_parse_structured_item()`
# @used-by :func:`_wire_step_values()`
# @used-by :func:`agent_tools.metrics.wire_fields()`
def dfh_wire_fields(data: bytes) -> list[tuple]:
	offset, r = (0, [])
	while offset < len(data):
		tag, offset = _decode_varint(data, offset)
		field, kind = (tag >> 3, tag & 7)
		if not field:
			raise ValueError('Unsupported native protobuf field')
		value, offset = _decode_wire_value(data, offset, kind)
		r.append((field, kind, value))
	return r
# @used-by :func:`Df.Harness.lib.ag_metadata._read_model_table_rows()`
# @used-by :func:`_decode_message_payload()`
def dfh_wire_path(blob, path) -> list[str]:
	values = [blob]
	for field in path:
		values = _wire_step_values(values, field)
	r: list[str] = []
	for value in values:
		try:
			text = value.decode('utf-8')
			if text.strip():
				r.append(text)
		except UnicodeError:
			pass
	return r
