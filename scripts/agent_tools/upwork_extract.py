# 2026-10-14 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from Df.Harness.Upwork.AttachmentDownloader import AttachmentDownloader
from Df.Harness.Upwork.JobExtractor import JobExtractor
from Df.Harness.Upwork.PageDecoder import PageDecoder
from Df.Harness.Upwork.RpcClient import RpcClient as RPC
from Df.Harness.Upwork.SafeRedirect import SafeRedirect
from Df.Harness.Upwork.TabSelector import TabSelector
from pathlib import Path
from .text_browser import UPWORK_PAGE_STATE_EXPR
# 2026-11-26 "Move analysis workflow classes into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/380
MAX_ATTACHMENT = AttachmentDownloader.MAX_ATTACHMENT
_PAGE_STATE_EXPR = UPWORK_PAGE_STATE_EXPR
# @used-by :mod:`agent_tools.upwork_extract`
def _eval_session(mux, session_id, expression, *, await_promise=False, read_only=False, timeout_ms=25000):
	return JobExtractor.eval_session(mux, session_id, expression, await_promise=await_promise, read_only=read_only, timeout_ms=timeout_ms)
# @used-by :meth:`agent_tools.knowledge.AttachmentInventory._register_bytes()`
# @used-by :meth:`test_onboarding.AttachmentTests.test_paths_cannot_escape_or_use_windows_special_names()`
# @used-by :mod:`agent_tools.upwork_extract`
# @used-by :mod:`agent_tools.upwork_project`
def attachment_path(directory: Path, filename: str) -> Path:
	return AttachmentDownloader.attachment_path(directory, filename)
# @used-by :meth:`test_onboarding.AttachmentTests.test_access_denied_and_unloaded_pages_are_not_job_captures()`
# @used-by :meth:`test_text_browser.TextBrowserTests.test_read_only_cdp_expressions_live_headless_shell_contract()`
# @used-by :mod:`agent_tools.upwork_extract`
def decode_page(page, job_id):
	return PageDecoder(page, job_id).decode()
# @used-by :meth:`test_onboarding.AttachmentTests.test_cookie_domain_and_path_boundaries()`
# @used-by :meth:`test_onboarding.AttachmentTests.test_unrelated_initial_host_rejected_before_network()`
# @used-by :mod:`agent_tools.upwork_extract`
def download_attachment(attachment, directory: Path, cookies=(), user_agent='UpworkOnboarding/2'):
	return AttachmentDownloader(attachment, directory, cookies, user_agent).download()
# @used-by :func:`agent_tools.upwork_project.run()`
# @used-by :meth:`test_text_browser.TextBrowserTests.test_m2b_zero_extension_sentinel_skips_discarded_tabs_never_enumerates_cookies_and_guards_upwork_extract()`
# @used-by :mod:`agent_tools.upwork_extract`
# @used-by :mod:`agent_tools.upwork_project`
def extract_upwork_job(url_or_id, cdp_port=9222, fetch_related=True, attachments_dir=None, tab_id=None, *, session_id=None, config=None, http_get=None, cdp_call=None):
	return JobExtractor(url_or_id, cdp_port, fetch_related, attachments_dir, tab_id, session_id=session_id, config=config, http_get=http_get, cdp_call=cdp_call).extract()
# @used-by :meth:`test_onboarding.AttachmentTests.test_tab_selection_requires_exact_job_or_explicit_id()`
# @used-by :mod:`agent_tools.upwork_extract`
def select_tab(tabs, job_id, tab_id=None):
	return TabSelector(tabs, job_id, tab_id).select()
# @used-by :mod:`agent_tools.upwork_extract`
def upwork_host(url):
	return AttachmentDownloader.upwork_host(url)
__all__ = ['MAX_ATTACHMENT', 'RPC', 'SafeRedirect', '_PAGE_STATE_EXPR', '_eval_session', 'attachment_path', 'decode_page', 'download_attachment', 'extract_upwork_job', 'select_tab', 'upwork_host']
