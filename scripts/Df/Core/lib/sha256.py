# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from pathlib import Path
import hashlib
# 2026-11-26 "Extract general duplicated helpers into Df/Core and Df/Qa": https://github.com/dmitry-ai/harness/issues/378
# Return lowercase hex SHA-256 digest of raw bytes.
# @used-by :func:`agent_tools.admission._digest()`
# @used-by :func:`agent_tools.analysis.digest()`
# @used-by :func:`agent_tools.intake._hash()`
# @used-by :func:`agent_tools.project_card._digest()`
# @used-by :func:`agent_tools.snapshot.snapshot_draft()`
# @used-by :func:`agent_tools.text_claims.digest()`
# @used-by :func:`df_sha256_file()`
# @used-by :func:`df_sha256_text()`
# @used-by :meth:`test_df_core_qa_s10.DfCoreQaS10Tests.test_sha256_json_io_and_time_helpers()`
def df_sha256(data: bytes) -> str:
	return hashlib.sha256(data).hexdigest()
# Return lowercase hex SHA-256 digest of a file's raw bytes.
# @used-by :func:`agent_tools.snapshot.snapshot_draft()`
# @used-by :func:`agent_tools.stop_emergency_capture._record_emergency_files()`
# @used-by :meth:`test_df_core_qa_s10.DfCoreQaS10Tests.test_sha256_json_io_and_time_helpers()`
def df_sha256_file(path: str | Path) -> str:
	return df_sha256(Path(path).read_bytes())
# Return lowercase hex SHA-256 digest of UTF-8 encoded text.
# @used-by :func:`agent_tools.snapshot.snapshot_draft()`
# @used-by :func:`agent_tools.stop_emergency_capture._record_emergency_files()`
# @used-by :meth:`test_df_core_qa_s10.DfCoreQaS10Tests.test_sha256_json_io_and_time_helpers()`
def df_sha256_text(text: str) -> str:
	return df_sha256(text.encode('utf-8'))