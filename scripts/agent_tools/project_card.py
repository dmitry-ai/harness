# 2026-10-17 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
# 2026-11-26 "Extract general duplicated helpers into Df/Core and Df/Qa": https://github.com/dmitry-ai/harness/issues/378
from Df.Core.lib.sha256 import df_sha256
# 2026-11-26 "Move analysis workflow classes into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/380
from Df.Harness.Project.CardSyncer import CardSyncer
# @used-by :meth:`test_df_core_qa_s10.DfCoreQaS10Tests.test_harness_callers_delegate_to_new_core_and_qa_helpers()`
def _digest(data):
	return df_sha256(data)
# @used-by :meth:`test_readable_links.ReadableProjectTests.test_website_card_uses_readable_iri_and_keeps_original_website_selection()`
def sync_block(root, target, key, content, position='after-title', *, check=False, source=None, attributes=None):
	return CardSyncer(root, target, key, content, position, check=check, source=source, attributes=attributes).sync()