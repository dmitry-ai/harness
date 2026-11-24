# 2026-11-24 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Use canonical native inputs and strip USER_REQUEST in native_review_proof":
# https://github.com/dmitry-ai/harness/issues/210
from __future__ import annotations
import sqlite3
def resolve_parent_binding_inputs(backend, parent_id, parent_inputs, *, paths, native_inputs_fn, extract_transcript_fn):
	try:
		loaded = native_inputs_fn(backend, parent_id, paths=paths, include_meta=True)
	except (OSError, sqlite3.Error, ValueError):
		loaded = None
	if loaded:
		r = loaded
	else:
		r = [(item.get('step_index', idx), extract_transcript_fn(item)) for idx, item in enumerate(parent_inputs) if 'USER_INPUT' == item.get('type') and isinstance(item.get('content'), str)]
	return r
