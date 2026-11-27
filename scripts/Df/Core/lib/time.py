# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from datetime import datetime, timezone
# 2026-11-26 "Extract general duplicated helpers into Df/Core and Df/Qa": https://github.com/dmitry-ai/harness/issues/378
# Return current UTC timestamp formatted as an ISO 8601 string.
# @used-by :func:`Df.Harness.lib.shadow_command.dfh_persist_shadow_replay_receipt()`
# @used-by :meth:`test_df_core_qa_s10.DfCoreQaS10Tests.test_sha256_json_io_and_time_helpers()`
def df_utc_iso(*, timespec: str='seconds') -> str:
	return datetime.now(timezone.utc).isoformat(timespec=timespec)