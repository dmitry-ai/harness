# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from pathlib import Path
from Df.Harness.lib.shell import dfh_parse_issue_url
import re
# 2026-11-26 "Move repository and grounding subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/382
_DEFERRED_HEADING_RE = re.compile('(?i)\\b(?:\\u043e\\u0442\\u043b\\u043e\\u0436\\u0435\\u043d\\w*|\\u043d\\u0435\\s+\\u0440\\u0435\\u0430\\u043b\\u0438\\u0437\\w*|\\u043d\\u0435\\s+\\u0437\\u0430\\u0442\\u0440\\u043e\\u043d\\u0443\\u0442\\w*|\\u043f\\u0440\\u043e\\u043f\\u0443\\u0449\\u0435\\u043d\\w*|deferred|skipped|excluded|out\\s+of\\s+scope|not\\s+implemented)\\b')
_DEFERRED_LINE_RE = re.compile('(?i)\\b(?:\\u043d\\u0435\\s+\\u0440\\u0435\\u0430\\u043b\\u0438\\u0437\\w*|\\u043e\\u0442\\u043b\\u043e\\u0436\\u0435\\u043d\\w*|deferred|skipped|excluded|not\\s+implemented)\\b')
_M_SUBTASK_ITEM_RE = re.compile('^(?:\\s*#{1,6}\\s+(?:\\d+(?:\\.\\d+)*\\.?\\s*)?|\\s*(?:[-*+]|\\d+[.)])\\s+)(?:\\*\\*|__|`|\\u00ab|"|\\\')*(?:(?i:implement|fix|add|enforce|update|resolve|subtask|method|\\u0440\\u0435\\u0430\\u043b\\u0438\\u0437\\u043e\\u0432\\u0430\\u0442\\u044c|\\u0438\\u0441\\u043f\\u0440\\u0430\\u0432\\u0438\\u0442\\u044c|\\u0434\\u043e\\u0431\\u0430\\u0432\\u0438\\u0442\\u044c|\\u043f\\u043e\\u0434\\u0437\\u0430\\u0434\\u0430\\u0447\\u0430|\\u043c\\u0435\\u0442\\u043e\\u0434)\\s+)?(?:\\*\\*|__|`|\\u00ab|"|\\\')*(?P<mid>M-(?:[A-Za-z]+-)*\\d+)[A-Za-z]?\\b')
# @used-by :func:`dfh_filter_turn_state_items()`
def _item_belongs_to_turn(item: dict, ts_cid_low: str, ts_plat: str, native_urls: set[str], has_competing_open_turns: bool) -> bool:
	rec_cid = str(item.get('recorded_conversation_id') or '').strip().lower()
	rec_plat = str(item.get('recorded_platform') or '').strip().lower()
	u_item = (item.get('url') or '').strip()
	plat_skip = ('codex' == rec_plat and ts_plat and 'codex' != ts_plat) or ('non_codex' == rec_plat and 'codex' == ts_plat)
	if plat_skip:
		r = False
	elif rec_cid:
		r = (not ts_cid_low) or (rec_cid == ts_cid_low)
	elif u_item in native_urls:
		r = True
	elif ts_plat in ('antigravity', 'codex') and ('non_codex' == rec_plat or bool(native_urls) or has_competing_open_turns):
		r = False
	else:
		r = (not native_urls) or (u_item in native_urls)
	return r
# @used-by :func:`dfh_extract_implemented_m_roots()`
def _next_skip_depth(line: str, skip_depth: int | None) -> int | None:
	r = skip_depth
	m_hdr = re.match('^\\s*(#{1,6})\\s+', line)
	if m_hdr:
		d = len(m_hdr.group(1))
		if _DEFERRED_HEADING_RE.search(line):
			r = d if None is skip_depth or d < skip_depth else skip_depth
		elif None is not skip_depth and d <= skip_depth:
			r = None
	return r
# @used-by :func:`agent_tools.issues.parity.extract_implemented_m_roots()`
# @used-by :meth:`Df.Harness.Issue.TurnAuditor.TurnAuditor.check_multi_subtask_decomposition()`
# @used-by :meth:`test_df_harness_s11_wave2c_issues.DfHarnessS11Wave2CIssuesTests.test_issue_turn_lib_session_scope_and_pending_peers()`
# @used-by :mod:`agent_tools.issue_lifecycle`
def dfh_extract_implemented_m_roots(response: str) -> list[str]:
	r: list[str] = []
	if isinstance(response, str) and response.strip():
		skip_depth: int | None = None
		for line in re.sub('```[\\s\\S]*?```', '', response).splitlines():
			skip_depth = _next_skip_depth(line, skip_depth)
			m = _M_SUBTASK_ITEM_RE.match(line) if None is skip_depth else None
			if m and (not _DEFERRED_LINE_RE.search(line)):
				root_id = m.group('mid').upper()
				if root_id not in r:
					r.append(root_id)
	return r
# @used-by :func:`agent_tools.issues.parity.filter_turn_state_items()`
# @used-by :meth:`Df.Harness.Issue.TurnAuditor.TurnAuditor.collect_turn_issues()`
# @used-by :meth:`test_df_harness_s11_wave2c_issues.DfHarnessS11Wave2CIssuesTests.test_issue_turn_lib_session_scope_and_pending_peers()`
def dfh_filter_turn_state_items(gh_items: list, ts_cid: str, ts_plat: str, native_urls: set[str], *, has_competing_open_turns: bool=False) -> list[dict]:
	ts_cid_low = str(ts_cid or '').strip().lower()
	ts_plat_low = str(ts_plat or '').strip().lower()
	return [item for item in gh_items if isinstance(item, dict) and _item_belongs_to_turn(item, ts_cid_low, ts_plat_low, native_urls, has_competing_open_turns)]
# @used-by :func:`agent_tools.issues.parity.merge_turn_issue_item()`
# @used-by :meth:`Df.Harness.Issue.TurnAuditor.TurnAuditor.collect_turn_issues()`
# @used-by :meth:`test_df_harness_s11_wave2c_issues.DfHarnessS11Wave2CIssuesTests.test_issue_turn_lib_session_scope_and_pending_peers()`
def dfh_merge_turn_issue_item(turn_issues: dict[str, dict], item: dict) -> None:
	url = (item.get('url') or '').strip()
	parsed = dfh_parse_issue_url(url)
	if None is not parsed:
		slug, num = parsed
		act = item.get('action') or item.get('last_action')
		st = 'closed' if 'close' == act else str(item.get('state') or '').strip().lower()
		prev = turn_issues.get(url, {})
		cids = list(dict.fromkeys([*(prev.get('comment_ids') or ()), *(item.get('comment_ids') or ())]))
		acts = list(dict.fromkeys([a for a in (*(prev.get('actions') or ()), *(item.get('actions') or ()), act) if a]))
		raw_p = item.get('parent_number')
		pnum = raw_p if isinstance(raw_p, int) and (not isinstance(raw_p, bool)) else prev.get('parent_number')
		entry = {'url': url, 'repo': slug, 'number': num, 'state': st or prev.get('state') or 'open', 'last_action': act or prev.get('last_action') or 'issue', 'actions': acts, 'comment_ids': cids}
		if isinstance(pnum, int) and pnum != num:
			entry['parent_number'] = pnum
		turn_issues[url] = entry
# @used-by :func:`agent_tools.issues.parity.verify_multi_subtask_counts()`
# @used-by :meth:`Df.Harness.Issue.TurnAuditor.TurnAuditor.check_multi_subtask_decomposition()`
def dfh_verify_multi_subtask_counts(impl_m_roots: list[str], per_repo: list[tuple[Path, str, list[str]]], total_child_urls: int, violations: list[str]) -> None:
	if 2 <= len(impl_m_roots) and per_repo:
		joined_m = ', '.join(impl_m_roots)
		if 1 == len(per_repo):
			_, slug, c_urls = per_repo[0]
			if len(c_urls) < len(impl_m_roots):
				violations.append(f'EXEC-5 violation: response implements {len(impl_m_roots)} autonomous M-* subtasks ({joined_m}) in {slug}, which requires a parent problem issue and at least {len(impl_m_roots)} separate child subtask issues (--parent <N>) with separate commits, found {len(c_urls)} parent-linked committed child issue(s)')
		else:
			for _, slug, c_urls in per_repo:
				if not c_urls:
					violations.append(f'EXEC-5 violation: touched repository {slug} in multi-repository M-* implementation lacks a parent-linked committed child subtask issue (--parent <N>)')
			if total_child_urls < len(impl_m_roots):
				violations.append(f'EXEC-5 violation: response implements {len(impl_m_roots)} autonomous M-* subtasks ({joined_m}) across {len(per_repo)} repositories, which requires at least {len(impl_m_roots)} parent-linked committed child subtask issues in total, found {total_child_urls}')
