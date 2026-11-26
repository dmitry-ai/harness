# 2026-11-25 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from pathlib import Path
# 2026-11-26 "Move analysis workflow classes into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/380
from Df.Harness.Project.LinkAudit import CHAT_REPLY_CALL_SITES, CHAT_REPLY_HELPER_SITE, KB_DOCUMENT_READABLE_CALL_SITES, LinkAudit
# @used-by :meth:`test_contract_invariants.ContractInvariantsM2Tests.test_readable_link_call_site_ast_policy_registry_and_negative_detection()`
# @used-by :mod:`agent_tools.contract_invariants`
def audit_readable_link_call_sites(scripts_dir: Path, *, require_expected_chat_sites: bool=True) -> list[str]:
	return LinkAudit(scripts_dir, require_expected_chat_sites=require_expected_chat_sites).audit()
__all__ = ['CHAT_REPLY_CALL_SITES', 'CHAT_REPLY_HELPER_SITE', 'KB_DOCUMENT_READABLE_CALL_SITES', 'audit_readable_link_call_sites']