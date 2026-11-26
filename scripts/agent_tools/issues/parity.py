# 2026-11-23 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
import json
from pathlib import Path
import re
from ..git_gate import is_issue_tracked_code_repo, parse_issue_url
from .workspace import IssueEvidenceWorkspace
# 2026-11-24
# "Decompose github_issue.py and issue_lifecycle.py into IssueMarkdownLinter, IssueEvidenceWorkspace, GitHubIssueService, and TurnIssueLifecycleAuditor with locked turn updates":
# https://github.com/dmitry-ai/harness/issues/77
_DEFERRED_HEADING_RE = re.compile('(?i)\\b(?:\\u043e\\u0442\\u043b\\u043e\\u0436\\u0435\\u043d\\w*|\\u043d\\u0435\\s+\\u0440\\u0435\\u0430\\u043b\\u0438\\u0437\\w*|\\u043d\\u0435\\s+\\u0437\\u0430\\u0442\\u0440\\u043e\\u043d\\u0443\\u0442\\w*|\\u043f\\u0440\\u043e\\u043f\\u0443\\u0449\\u0435\\u043d\\w*|deferred|skipped|excluded|out\\s+of\\s+scope|not\\s+implemented)\\b')
_DEFERRED_LINE_RE = re.compile('(?i)\\b(?:\\u043d\\u0435\\s+\\u0440\\u0435\\u0430\\u043b\\u0438\\u0437\\w*|\\u043e\\u0442\\u043b\\u043e\\u0436\\u0435\\u043d\\w*|deferred|skipped|excluded|not\\s+implemented)\\b')
_M_SUBTASK_ITEM_RE = re.compile('^(?:\\s*#{1,6}\\s+(?:\\d+(?:\\.\\d+)*\\.?\\s*)?|\\s*(?:[-*+]|\\d+[.)])\\s+)(?:\\*\\*|__|`|\\u00ab|"|\\\')*(?:(?i:implement|fix|add|enforce|update|resolve|subtask|method|\\u0440\\u0435\\u0430\\u043b\\u0438\\u0437\\u043e\\u0432\\u0430\\u0442\\u044c|\\u0438\\u0441\\u043f\\u0440\\u0430\\u0432\\u0438\\u0442\\u044c|\\u0434\\u043e\\u0431\\u0430\\u0432\\u0438\\u0442\\u044c|\\u043f\\u043e\\u0434\\u0437\\u0430\\u0434\\u0430\\u0447\\u0430|\\u043c\\u0435\\u0442\\u043e\\u0434)\\s+)?(?:\\*\\*|__|`|\\u00ab|"|\\\')*(?P<mid>M-(?:[A-Za-z]+-)*\\d+)[A-Za-z]?\\b')
# @used-by :func:`_match_similar_exemption()`
def _exemption_matches_peer(ex: dict, peer_key: str, slug_keys: set[str]) -> bool:
	ex_root_raw = str(ex.get('peer_root') or '').strip()
	root_hit = False
	if ex_root_raw:
		try:
			root_hit = Path(ex_root_raw).resolve().as_posix().lower() == peer_key
		except OSError:
			root_hit = ex_root_raw.replace('\\', '/').rstrip('/').lower() == peer_key
	ex_repos = {str(s).strip().lower() for s in (ex.get('peer_repos') or ()) if str(s).strip()}
	ex_peer = str(ex.get('peer') or '').strip().lower()
	r = root_hit or bool(ex_repos & slug_keys) or bool(ex_peer and (ex_peer in slug_keys or ex_peer.replace('\\', '/').rstrip('/') == peer_key))
	return r
# @used-by :func:`_resolve_peer_parity()`
def _find_peer_issue_resolution(root: Path, slug_keys: set[str], turn_issues: dict[str, dict], candidate_repos: list[Path]) -> tuple[str | None, str | None]:
	res, ev = (None, None)
	for info in sorted(turn_issues.values(), key=lambda x: str(x.get('url') or '')):
		acts = {str(a) for a in (info.get('actions') or ()) if a}
		if info.get('last_action'):
			acts.add(str(info['last_action']))
		repo_s = str(info.get('repo') or '').strip()
		if repo_s.lower() in slug_keys and (acts & {'create', 'edit', 'comment'}) and IssueEvidenceWorkspace.evidence_issue_files(root, repo_s, f"issue-{int(info['number'])}.json", candidate_repos):
			res, ev = ('peer_issue_recorded', info.get('url'))
			break
	return (res, ev)
# @used-by :func:`check_similar_project_parity()`
def _load_similar_project_exemptions(root: Path, turn_state: dict | None) -> list[dict]:
	from ..path_registry import project_paths
	items = [raw for raw in ((turn_state or {}).get('similar_project_exemptions') or []) if isinstance(raw, dict)]
	turn_key = str((turn_state or {}).get('key') or '').strip()
	if turn_key:
		ex_file = project_paths(root, exact_root=True).turns_dir / f'{turn_key}-similar-exemptions.json'
		if ex_file.is_file():
			try:
				loaded = json.loads(ex_file.read_text(encoding='utf-8'))
				raw_list = loaded.get('exemptions') if isinstance(loaded, dict) else loaded
				if isinstance(raw_list, list):
					items.extend((raw for raw in raw_list if isinstance(raw, dict)))
			except (OSError, ValueError):
				pass
	return items
# @used-by :func:`_resolve_peer_parity()`
def _match_similar_exemption(exemptions: list[dict], peer_root: Path, peer_slugs: list[str]) -> dict | None:
	peer_key, slug_keys = (peer_root.as_posix().lower(), {s.lower() for s in peer_slugs})
	return next((ex for ex in exemptions if 30 <= len(str(ex.get('reason') or '').strip()) and _exemption_matches_peer(ex, peer_key, slug_keys)), None)
# @used-by :func:`extract_implemented_m_roots()`
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
# @used-by :func:`_evaluate_similar_peer_item()`
# @used-by :func:`similar_project_repo_slugs()`
def _peer_code_repo_candidates(peer_root: Path, *, registry=None) -> list[Path]:
	from ..path_registry import project_paths
	pp_peer = project_paths(peer_root, registry=registry)
	out, seen = ([], set())
	for cand in (*pp_peer.code_repos, pp_peer.root, pp_peer.root / 'code', pp_peer.root / '\u2c0f/\u227b/\u2655/\u26ef', pp_peer.root / 'Artifacts/\u227b/Deliverables/\u26ef'):
		try:
			resolved = cand.resolve()
		except OSError:
			continue
		key = resolved.as_posix().lower()
		if key not in seen and is_issue_tracked_code_repo(resolved):
			seen.add(key)
			out.append(resolved)
	return out
# @used-by :func:`_evaluate_similar_peer_item()`
def _resolve_peer_parity(root: Path, item: dict, peer_root: Path, peer_slugs: list[str], exemptions: list[dict], turn_issues: dict[str, dict], candidate_repos: list[Path]) -> tuple[str | None, str | None]:
	if item.get('peer_touched'):
		resolution, matched_ev = ('peer_code_updated', peer_root.as_posix())
	else:
		resolution, matched_ev = _find_peer_issue_resolution(root, {s.lower() for s in peer_slugs}, turn_issues, candidate_repos)
		if None is resolution:
			ex = _match_similar_exemption(exemptions, peer_root, peer_slugs)
			if None is not ex:
				resolution, matched_ev = ('exempted', str(ex.get('reason') or '').strip())
	return (resolution, matched_ev)
# @used-by :func:`check_similar_project_parity()`
def _evaluate_similar_peer_item(root: Path, item: dict, exemptions: list[dict], turn_issues: dict[str, dict], candidate_repos: list[Path], cand_keys: set[str], violations: list[str], canonicalize_root_dir) -> tuple[dict, bool]:
	peer_root = canonicalize_root_dir(Path(item['peer_root']))
	for pcr in _peer_code_repo_candidates(peer_root):
		if pcr.as_posix().lower() not in cand_keys:
			cand_keys.add(pcr.as_posix().lower())
			candidate_repos.append(pcr)
	peer_slugs = similar_project_repo_slugs(peer_root)
	resolution, matched_ev = _resolve_peer_parity(root, item, peer_root, peer_slugs, exemptions, turn_issues, candidate_repos)
	satisfied = None is not resolution
	if not satisfied:
		target_repo = peer_slugs[0] if peer_slugs else peer_root.as_posix()
		hint = f" (repos: {', '.join(peer_slugs)})" if peer_slugs else ''
		violations.append(f"EXEC-5 / SCOPE-4 parity violation: changes in similar source [{item['source_label']}] require parity with peer {peer_root.as_posix()}{hint}; update peer code, file a porting GitHub issue via df_github_issue.py create --repo {target_repo}, or record an audited exemption via harness.py similar-project-exempt \"{root.as_posix()}\" --peer \"{target_repo}\" --reason \"<technical justification >= 30 chars>\"")
	rec = {'group_id': item.get('group_id'), 'source_projects': [Path(sp).as_posix() for sp in item.get('source_projects') or ()], 'peer_root': peer_root.as_posix(), 'peer_repos': peer_slugs, 'satisfied': satisfied, 'resolution': resolution, 'evidence': matched_ev}
	return (rec, satisfied)
# @used-by :meth:`agent_tools.issues.auditor.TurnIssueLifecycleAuditor.audit()`
# @used-by :mod:`agent_tools.issue_lifecycle`
def check_similar_project_parity(root: Path, repo_touched: dict[Path, set[str]], turn_issues: dict[str, dict], turn_state: dict | None, candidate_repos: list[Path], violations: list[str]) -> dict:
	from ..path_registry import canonicalize_root_dir, evaluate_similar_project_touches
	touched_files = [code_repo / rel for code_repo, rels in sorted(repo_touched.items(), key=lambda x: str(x[0])) for rel in sorted(rels)]
	touches = evaluate_similar_project_touches(touched_files) if touched_files else []
	if not touches:
		r = {'verified': True, 'peers': []}
	else:
		exemptions = _load_similar_project_exemptions(root, turn_state)
		cand_keys = {c.resolve().as_posix().lower() for c in candidate_repos}
		peer_records, all_ok = ([], True)
		for item in touches:
			rec, ok = _evaluate_similar_peer_item(root, item, exemptions, turn_issues, candidate_repos, cand_keys, violations, canonicalize_root_dir)
			peer_records.append(rec)
			all_ok = all_ok and ok
		r = {'verified': all_ok, 'peers': peer_records}
	return r
# @used-by :meth:`agent_tools.issues.auditor.TurnIssueLifecycleAuditor._check_multi_subtask_decomposition()`
# @used-by :mod:`agent_tools.issue_lifecycle`
def extract_implemented_m_roots(response: str) -> list[str]:
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
# 2026-11-24
# "Isolate per-conversation github_issues recording and turn-state filtering":
# https://github.com/dmitry-ai/harness/issues/195
# @used-by :func:`filter_turn_state_items()`
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
# 2026-11-24
# "Isolate per-conversation github_issues recording and turn-state filtering":
# https://github.com/dmitry-ai/harness/issues/195
# @used-by :meth:`agent_tools.issues.auditor.TurnIssueLifecycleAuditor.collect_turn_issues()`
# @used-by :meth:`test_issue_conversation_isolation.IssueConversationIsolationTests.test_filter_rejects_legacy_non_codex_broadcast_and_competing_untagged_entries()`
def filter_turn_state_items(gh_items: list, ts_cid: str, ts_plat: str, native_urls: set[str], *, has_competing_open_turns: bool=False) -> list[dict]:
	ts_cid_low = str(ts_cid or '').strip().lower()
	ts_plat_low = str(ts_plat or '').strip().lower()
	return [item for item in gh_items if isinstance(item, dict) and _item_belongs_to_turn(item, ts_cid_low, ts_plat_low, native_urls, has_competing_open_turns)]
# @used-by :meth:`agent_tools.issues.auditor.TurnIssueLifecycleAuditor.collect_turn_issues()`
def merge_turn_issue_item(turn_issues: dict[str, dict], item: dict) -> None:
	url = (item.get('url') or '').strip()
	parsed = parse_issue_url(url)
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
# @used-by :func:`_evaluate_similar_peer_item()`
# @used-by :func:`agent_tools.completion._similar_projects_metadata()`
# @used-by :func:`agent_tools.completion.similar_project_exempt()`
# @used-by :func:`agent_tools.issues.service_helpers.pending_similar_peer_slugs()`
def similar_project_repo_slugs(peer_root: Path, *, registry=None) -> list[str]:
	slugs, seen = ([], set())
	for cand in _peer_code_repo_candidates(peer_root, registry=registry):
		slug = IssueEvidenceWorkspace.origin_repo_slug(cand)
		if slug and slug.lower() not in seen:
			seen.add(slug.lower())
			slugs.append(slug)
	return slugs
# @used-by :meth:`agent_tools.issues.auditor.TurnIssueLifecycleAuditor._check_multi_subtask_decomposition()`
def verify_multi_subtask_counts(impl_m_roots: list[str], per_repo: list[tuple[Path, str, list[str]]], total_child_urls: int, violations: list[str]) -> None:
	if 2 <= len(impl_m_roots) and per_repo:
		if 1 == len(per_repo):
			_, slug, c_urls = per_repo[0]
			if len(c_urls) < len(impl_m_roots):
				violations.append(f'EXEC-5 violation: response implements {len(impl_m_roots)} autonomous M-* subtasks ({", ".join(impl_m_roots)}) in {slug}, which requires a parent problem issue and at least {len(impl_m_roots)} separate child subtask issues (--parent <N>) with separate commits, found {len(c_urls)} parent-linked committed child issue(s)')
		else:
			for _, slug, c_urls in per_repo:
				if not c_urls:
					violations.append(f'EXEC-5 violation: touched repository {slug} in multi-repository M-* implementation lacks a parent-linked committed child subtask issue (--parent <N>)')
			if total_child_urls < len(impl_m_roots):
				violations.append(f'EXEC-5 violation: response implements {len(impl_m_roots)} autonomous M-* subtasks ({", ".join(impl_m_roots)}) across {len(per_repo)} repositories, which requires at least {len(impl_m_roots)} parent-linked committed child subtask issues in total, found {total_child_urls}')
