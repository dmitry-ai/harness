# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from pathlib import Path
from typing import Any
import json
# 2026-11-26 "Extract general duplicated helpers into Df/Core and Df/Qa": https://github.com/dmitry-ai/harness/issues/378
# Serialize value to deterministic UTF-8 JSON bytes ending with a newline.
# @used-by :func:`agent_tools.admission._bytes()`
# @used-by :meth:`test_df_core_qa_s10.DfCoreQaS10Tests.test_sha256_json_io_and_time_helpers()`
def df_json_bytes(value: Any, *, indent: int | str | None=None) -> bytes:
	if None is indent:
		txt = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'))
	else:
		txt = json.dumps(value, ensure_ascii=False, indent=indent)
	return (txt + '\n').encode('utf-8')
# Read a UTF-8 JSON file and return its top-level dict, or None on missing/invalid/non-dict data.
# @used-by :func:`agent_tools.journal_integrity._load_json_dict()`
# @used-by :func:`agent_tools.project_drift._load_json_dict()`
# @used-by :meth:`Df.Harness.Project.DriftAuditor.DriftAuditor.__title_mismatches()`
# @used-by :meth:`Df.Harness.Project.DriftAuditor.DriftAuditor.audit()`
# @used-by :meth:`Df.Harness.Project.FinalizeDriftGuard.FinalizeDriftGuard.require()`
# @used-by :meth:`test_df_core_qa_s10.DfCoreQaS10Tests.test_sha256_json_io_and_time_helpers()`
def df_json_dict_load(path: str | Path) -> dict[str, Any] | None:
	p = Path(path)
	r: dict[str, Any] | None = None
	if p.is_file():
		try:
			parsed = json.loads(p.read_text(encoding='utf-8-sig'))
			if isinstance(parsed, dict):
				r = parsed
		except (OSError, ValueError):
			r = None
	return r