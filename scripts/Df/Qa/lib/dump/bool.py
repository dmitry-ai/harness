# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
# 2026-11-26 "Port Df/Qa classes and validation libraries": https://github.com/dmitry-ai/harness/issues/325
# Convert a boolean into `'true'` or `'false'`.
# https://github.com/mage2pro/core/blob/11.6.1/Qa/lib/dump/bool.php#L9
# @used-by :meth:`Df.Qa.Dumper.Dumper.dump()`
# @used-by :meth:`test_df_qa.TestDfQa.test_dump_and_dumper()`
def df_bts(v: bool) -> str:
	return 'true' if v else 'false'
# 2017-11-08 Convert a boolean into `'yes'` or `'no'`.
# https://github.com/mage2pro/core/blob/11.6.1/Qa/lib/dump/bool.php#L17
# @used-by :meth:`test_df_qa.TestDfQa.test_dump_and_dumper()`
def df_bts_yn(v: bool) -> str:
	return 'yes' if v else 'no'