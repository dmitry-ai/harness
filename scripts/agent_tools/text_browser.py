# 2026-10-20 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
# 2026-11-27 "Move repository and grounding subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/382
from Df.Harness.Text.Browser.AnchorStatusChecker import AnchorStatusChecker
from Df.Harness.Text.Browser.CdpDomCollector import CdpDomCollector
from Df.Harness.Text.Browser.CdpSession import CdpSession as CDPSession
from Df.Harness.Text.Browser.DomPoller import DomPoller
from Df.Harness.Text.Browser.GuardedCdp import GuardedCdp as GuardedCDP
from Df.Harness.Text.Browser.HeadlessDomCollector import HeadlessDomCollector
from Df.Harness.Text.Browser.HeadlessShell import HeadlessShell as ManagedHeadlessShell
from Df.Harness.Text.Browser.PreflightChecker import PreflightChecker
from Df.Harness.lib.browser import DOM_CAPTURE_EXPR, MINIMAL_DOM_CAPTURE_EXPR, READ_ONLY_CDP_EXPRESSIONS, UPWORK_PAGE_STATE_EXPR, USER_AGENT_EXPR, dfh_argument_values as _argument_values, dfh_checked_ws as _checked_ws, dfh_discover_cdp_browser as discover_cdp_browser, dfh_endpoint as _endpoint, dfh_endpoint_lock as _endpoint_lock, dfh_endpoint_with_meta as _endpoint_with_meta, dfh_headless_mcp_args as headless_mcp_args, dfh_http_json as _http_json, dfh_node_binary as _node_binary, dfh_normal_path as _normal_path, dfh_operation as operation, dfh_probe_cdp_arguments as probe_cdp_arguments, dfh_profile as _profile, dfh_query_target_infos as _query_target_infos, dfh_read_active_port_file as _read_active_port_file, dfh_resolve_cdp_port as resolve_cdp_port, dfh_resolve_headless_shell as resolve_headless_shell, dfh_save_cdp_identity as save_cdp_identity, dfh_session as _session, dfh_transport as _transport
_DOM_CAPTURE_EXPR = DOM_CAPTURE_EXPR
# @used-by unused
def _poll_dom_on_session(cdp_sess, session_id, timeout, *, single_pass=False):
	return DomPoller(cdp_sess, session_id, timeout, single_pass=single_pass).poll()
# @used-by :meth:`Df.Harness.Upwork.CliRunner.CliRunner.__run_browser_anchor()`
def browser_anchor_status(*, session_id=None, init_sentinel_tab=None, config=None, http_get=None, cdp_call=None):
	return AnchorStatusChecker(session_id=session_id, init_sentinel_tab=init_sentinel_tab, config=config, http_get=http_get, cdp_call=cdp_call).check()
# @used-by :mod:`agent_tools.text_browser`
def collect_cdp_dom(root, url, *, cdp_port=None, session_id=None, timeout=15, config=None, http_get=None, cdp_call=None, headless_shell=None):
	return CdpDomCollector(root, url, cdp_port=cdp_port, session_id=session_id, timeout=timeout, config=config, http_get=http_get, cdp_call=cdp_call, headless_shell=headless_shell).collect()
collect_cdp_dom._df_default_browser_facade = True
# @used-by unused
def collect_headless_dom(root, url, *, timeout=15, config=None, headless_shell=None):
	return HeadlessDomCollector(root, url, timeout=timeout, config=config, headless_shell=headless_shell).collect()
# @used-by :meth:`Df.Harness.Upwork.JobExtractor.JobExtractor.extract()`
# @used-by :meth:`test_text_browser.TextBrowserTests.check()`
# @used-by :meth:`test_text_browser.TextBrowserTests.test_live_account_marker_is_separate_from_profile_and_caller_assertion()`
def preflight(spec, *, config=None, http_get=None, cdp_call=None, require_target=True, cdp_session=None):
	return PreflightChecker(spec, config=config, http_get=http_get, cdp_call=cdp_call, require_target=require_target, cdp_session=cdp_session).check()
