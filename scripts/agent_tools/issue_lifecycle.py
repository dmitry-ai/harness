# 2026-11-18 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Fix post-audit edge cases in parent-child issue validation and turn-scoped lifecycle checks":
# https://github.com/dmitry-ai/harness/issues/87
# 2026-11-18 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Enforce parent problem issues and per-subtask child issue commits across issue and Git lifecycle gates":
# https://github.com/dmitry-ai/harness/issues/84
# 2026-11-13 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Extract issue_lifecycle.py from completion.py, fix open backlog-issue lifecycle gating, and consolidate Git/issue helpers in git_gate.py":
# https://github.com/dmitry-ai/harness/issues/53
import json
from pathlib import Path
import re
from .git_gate import extract_comment_issue_urls, extract_issue_urls, is_code_file, is_issue_tracked_code_repo, parse_issue_url, run_git_read, verify_repo_issue_ready_for_close
from .github_issue import extract_parent_issue_number, find_local_code_repo, find_tracked_child_issues, lint_issue_markdown
from .runtime import HARNESS_META
from .source_grounding import local_source_grounding_issues
_DEFERRED_HEADING_RE = re.compile('(?i)\\b(?:\\u043e\\u0442\\u043b\\u043e\\u0436\\u0435\\u043d\\w*|\\u043d\\u0435\\s+\\u0440\\u0435\\u0430\\u043b\\u0438\\u0437\\w*|\\u043d\\u0435\\s+\\u0437\\u0430\\u0442\\u0440\\u043e\\u043d\\u0443\\u0442\\w*|\\u043f\\u0440\\u043e\\u043f\\u0443\\u0449\\u0435\\u043d\\w*|deferred|skipped|excluded|out\\s+of\\s+scope|not\\s+implemented)\\b')
_DEFERRED_LINE_RE = re.compile('(?i)\\b(?:\\u043d\\u0435\\s+\\u0440\\u0435\\u0430\\u043b\\u0438\\u0437\\w*|\\u043e\\u0442\\u043b\\u043e\\u0436\\u0435\\u043d\\w*|deferred|skipped|excluded|not\\s+implemented)\\b')
_M_SUBTASK_ITEM_RE = re.compile('^(?:\\s*#{1,6}\\s+(?:\\d+(?:\\.\\d+)*\\.?\\s*)?|\\s*(?:[-*+]|\\d+[.)])\\s+)(?:\\*\\*|__|`|\\u00ab|"|\\\')*(?:(?i:implement|fix|add|enforce|update|resolve|subtask|method|\\u0440\\u0435\\u0430\\u043b\\u0438\\u0437\\u043e\\u0432\\u0430\\u0442\\u044c|\\u0438\\u0441\\u043f\\u0440\\u0430\\u0432\\u0438\\u0442\\u044c|\\u0434\\u043e\\u0431\\u0430\\u0432\\u0438\\u0442\\u044c|\\u043f\\u043e\\u0434\\u0437\\u0430\\u0434\\u0430\\u0447\\u0430|\\u043c\\u0435\\u0442\\u043e\\u0434)\\s+)?(?:\\*\\*|__|`|\\u00ab|"|\\\')*(?P<mid>M-(?:[A-Za-z]+-)*\\d+)[A-Za-z]?\\b')
def _extract_implemented_m_roots_from_response(response: str) -> list[str]:
	if not isinstance(response, str) or (not response.strip()):
		return []
	clean = re.sub('```[\\s\\S]*?```', '', response)
	r: list[str] = []
	skip_depth: int | None = None
	for line in clean.splitlines():
		m_hdr = re.match('^\\s*(#{1,6})\\s+', line)
		if m_hdr:
			hdr_depth = len(m_hdr.group(1))
			if _DEFERRED_HEADING_RE.search(line):
				if None is skip_depth or hdr_depth < skip_depth:
					skip_depth = hdr_depth
			elif None is not skip_depth and hdr_depth <= skip_depth:
				skip_depth = None
		if None is not skip_depth:
			continue
		m = _M_SUBTASK_ITEM_RE.match(line)
		if not m or _DEFERRED_LINE_RE.search(line):
			continue
		root_id = m.group('mid').upper()
		if root_id not in r:
			r.append(root_id)
	return r
def _check_diagnostic_audit_filing(root: Path, response, workspace_code_repos: set[Path], repo_touched: dict, turn_issues: dict, candidate_repos: list[Path], violations: list[str]) -> None:
	if isinstance(response, str) and response.strip() and workspace_code_repos and (not repo_touched):
		has_diag_causes = bool(re.search('(?m)(?:^|\\s|`|\\*\\*)(?:C|H)-[1-9]\\d*\\b', response))
		has_diag_methods = bool(re.search('(?m)(?:^|\\s|`|\\*\\*)M-[1-9]\\d*\\b', response))
		has_py_targets = bool(re.search('\\b[A-Za-z0-9_/-]+\\.py\\b', response))
		if has_diag_causes and has_diag_methods and has_py_targets:
			for ws_repo in sorted(workspace_code_repos, key=str):
				ws_slug = origin_repo_slug(ws_repo)
				if ws_slug:
					has_ws_issue = any((info['repo'].lower() == ws_slug.lower() and (None is _resolve_issue_parent_number(root, info['repo'], int(info['number']), turn_issues, candidate_repos, require_parent_evidence=False)) for info in turn_issues.values()))
					if not has_ws_issue:
						for resp_url in extract_issue_urls(response):
							parsed = parse_issue_url(resp_url)
							if None is not parsed and parsed[0].lower() == ws_slug.lower() and evidence_issue_files(root, parsed[0], f'issue-{parsed[1]}.json', candidate_repos) and (None is _resolve_issue_parent_number(root, parsed[0], parsed[1], turn_issues, candidate_repos, require_parent_evidence=False)):
								has_ws_issue = True
								break
					if not has_ws_issue:
						violations.append(f'EXEC-5 / SCOPE-2: Diagnostic audit of {ws_slug} identifies repository defects (C-/H-) and remediation methods (M-) without recording a corresponding parent problem GitHub Issue via df_github_issue.py')
def _resolve_issue_parent_number(root: Path, slug: str, num: int, turn_issues: dict, candidate_repos: list[Path], *, require_parent_evidence: bool=True) -> int | None:
	issue_url = f'https://github.com/{slug}/issues/{int(num)}'
	pnum = turn_issues.get(issue_url, {}).get('parent_number')
	if not isinstance(pnum, int) or isinstance(pnum, bool):
		pnum = None
		for p in evidence_issue_files(root, slug, f'issue-{int(num)}.json', candidate_repos)[:1]:
			try:
				data = json.loads(p.read_text(encoding='utf-8'))
			except (OSError, ValueError):
				continue
			iss_obj = data.get('issue') if isinstance(data, dict) and isinstance(data.get('issue'), dict) else data
			if isinstance(iss_obj, dict):
				raw_p = iss_obj.get('parent_number')
				if isinstance(raw_p, int) and (not isinstance(raw_p, bool)):
					pnum = raw_p
				else:
					pnum = extract_parent_issue_number(str(iss_obj.get('body') or ''), slug)
				break
	if isinstance(pnum, int) and pnum != int(num) and (not require_parent_evidence or evidence_issue_files(root, slug, f'issue-{pnum}.json', candidate_repos)):
		return pnum
	return None
def _check_multi_subtask_decomposition(root: Path, response, repo_touched: dict, committed_by_repo: dict[Path, set[str]], turn_issues: dict, required_issues_by_repo: dict[Path, set[str]], candidate_repos: list[Path], violations: list[str]) -> None:
	active_repos = [cr for cr, rels in sorted(repo_touched.items(), key=lambda x: str(x[0])) if rels or committed_by_repo.get(cr)]
	if not active_repos:
		return
	impl_m_roots = _extract_implemented_m_roots_from_response(response or '')
	for code_repo in active_repos:
		slug = origin_repo_slug(code_repo)
		if not slug:
			continue
		committed_urls = committed_by_repo.get(code_repo) or set()
		parent_nums: set[int] = set()
		for c_url in sorted(committed_urls):
			parsed_c = parse_issue_url(c_url)
			if None is not parsed_c and parsed_c[0].lower() == slug.lower():
				pnum = _resolve_issue_parent_number(root, parsed_c[0], parsed_c[1], turn_issues, candidate_repos)
				if None is not pnum:
					parent_nums.add(pnum)
		if 2 <= len(impl_m_roots):
			req_urls = sorted(required_issues_by_repo.get(code_repo) or ())
			committed_child_urls: list[str] = []
			for c_url in req_urls:
				if c_url not in committed_urls:
					continue
				parsed = parse_issue_url(c_url)
				if None is not parsed and parsed[0].lower() == slug.lower():
					if None is not _resolve_issue_parent_number(root, parsed[0], parsed[1], turn_issues, candidate_repos):
						committed_child_urls.append(c_url)
			if len(committed_child_urls) < len(impl_m_roots):
				violations.append(f'EXEC-5 violation: response implements {len(impl_m_roots)} autonomous M-* subtasks ({", ".join(impl_m_roots)}) in {slug}, which requires a parent problem issue and at least {len(impl_m_roots)} separate child subtask issues (--parent <N>) with separate commits, found {len(committed_child_urls)} parent-linked committed child issue(s)')
		elif 2 <= len(committed_urls):
			for c_url in sorted(committed_urls):
				c_info = turn_issues.get(c_url) or {}
				c_acts = set(c_info.get('actions') or ())
				if 'create' in c_acts and c_info.get('repo', '').lower() == slug.lower():
					if None is _resolve_issue_parent_number(root, c_info['repo'], int(c_info['number']), turn_issues, candidate_repos):
						violations.append(f'EXEC-5 violation: multi-commit subtask issue {c_url} created in {slug} lacks a --parent link to a parent problem issue')
		for pnum in sorted(parent_nums):
			children = find_tracked_child_issues(slug, pnum, project_root=root, code_repo=code_repo)
			if children and all(('closed' == c.get('state') for c in children)):
				p_url = f'https://github.com/{slug}/issues/{pnum}'
				p_state = evidence_issue_state(root, slug, pnum, candidate_repos) or (turn_issues.get(p_url) or {}).get('state') or 'open'
				if 'closed' != p_state:
					violations.append(f'EXEC-5 violation: parent issue {p_url} in {slug} remains {p_state} after all tracked child subtask issues are closed; close it via df_github_issue.py close')
def _check_repo_commits_and_files(code_repo: Path, rel_paths: list[str], turn_issues: dict, required_issues: set[str], violations: list[str]) -> set[str]:
	committed_urls: set[str] = set()
	if rel_paths:
		st_proc = run_git_read(code_repo, ['status', '--porcelain', '-z', '--', *rel_paths], check=False)
		if 0 == st_proc.returncode and st_proc.stdout.strip(b'\x00'):
			violations.append(f'Modified files in {code_repo} are not committed: {", ".join(rel_paths)}')
		for rel in rel_paths:
			fpath = code_repo / rel
			if fpath.is_file() and is_code_file(rel):
				try:
					file_text = fpath.read_text(encoding='utf-8', errors='replace')
					urls_in_file = extract_issue_urls(file_text)
					comment_urls = extract_comment_issue_urls(file_text)
				except OSError:
					urls_in_file = []
					comment_urls = set()
				if not urls_in_file:
					violations.append(f'Modified code file {fpath} does not reference a GitHub Issue URL')
				for cu in comment_urls:
					if cu in turn_issues:
						required_issues.add(cu)
						committed_urls.add(cu)
		existing_rels = [rel for rel in rel_paths if (code_repo / rel).exists()]
		if existing_rels:
			commit_urls: list[str] = []
			for rel in existing_rels:
				log_proc = run_git_read(code_repo, ['log', '-n', '1', '--format=%B', '--', f':(literal){rel}'], check=False)
				if 0 == log_proc.returncode:
					for cu in extract_issue_urls(log_proc.stdout.decode('utf-8', errors='replace')):
						if cu not in commit_urls:
							commit_urls.append(cu)
			if not commit_urls:
				violations.append(f'Latest commit for {", ".join(existing_rels)} in {code_repo} does not reference a GitHub Issue URL')
			for cu in commit_urls:
				required_issues.add(cu)
				committed_urls.add(cu)
	return committed_urls
def _check_turn_issue_evidence(root: Path, turn_issues: dict, repo_by_issue_url: dict, candidate_repos: list[Path], checked_urls: set[str], checked_issues: list[dict], violations: list[str]) -> None:
	for issue_url, info in sorted(turn_issues.items()):
		slug, num = (info['repo'], int(info['number']))
		actions = set(info.get('actions') or ())
		mutated_in_turn = info.get('last_action') in ('create', 'edit') or bool(actions & {'create', 'edit'})
		ev_state = evidence_issue_state(root, slug, num, candidate_repos)
		eff_state = ev_state or info.get('state') or 'open'
		if issue_url not in checked_urls:
			mapped_repo = repo_by_issue_url.get(issue_url)
			checked_issues.append({'url': issue_url, 'repo': slug, 'number': num, 'state': eff_state, 'code_repo': str(mapped_repo) if mapped_repo else None, 'commit_and_push_verified': False})
			checked_urls.add(issue_url)
		iss_files = evidence_issue_files(root, slug, f'issue-{num}.json', candidate_repos)
		if not iss_files and mutated_in_turn:
			violations.append(f'GitHub issue {issue_url} is missing saved API read-back Evidence JSON (issue-{num}.json)')
		container_text = None
		for p in iss_files[:1]:
			try:
				data = json.loads(p.read_text(encoding='utf-8'))
				iss_obj = data.get('issue') if isinstance(data.get('issue'), dict) else data
				t_txt = str(iss_obj.get('title') or '')
				b_txt = str(iss_obj.get('body') or '')
				container_text = f'{t_txt}\n{b_txt}'.strip()
				pnum = info.get('parent_number')
				if not isinstance(pnum, int) or isinstance(pnum, bool):
					raw_p = iss_obj.get('parent_number')
					pnum = raw_p if isinstance(raw_p, int) and (not isinstance(raw_p, bool)) else extract_parent_issue_number(b_txt, slug)
				if isinstance(pnum, int) and pnum != num:
					if not evidence_issue_files(root, slug, f'issue-{pnum}.json', candidate_repos):
						violations.append(f'GitHub child issue {issue_url} references parent #{pnum}, which is missing saved API read-back Evidence JSON (issue-{pnum}.json)')
				if t_txt and mutated_in_turn:
					for err in lint_issue_markdown(t_txt, is_title=True):
						violations.append(f'GitHub issue {issue_url} title lint error ({err.get("code")}): {err.get("message")}')
				if b_txt and mutated_in_turn:
					eff_p = pnum if isinstance(pnum, int) and pnum != num else None
					for err in lint_issue_markdown(b_txt, is_title=False, parent_number=eff_p, repo=slug, self_number=num):
						violations.append(f'GitHub issue {issue_url} body lint error ({err.get("code")}): {err.get("message")}')
					for g_err in local_source_grounding_issues(root, b_txt, doc_path=p):
						violations.append(f'GitHub issue {issue_url} body grounding error: {g_err}')
			except (OSError, ValueError):
				continue
		for cid in info.get('comment_ids') or []:
			for cp in evidence_issue_files(root, slug, f'comment-{cid}.json', candidate_repos)[:1]:
				try:
					cdata = json.loads(cp.read_text(encoding='utf-8'))
					c_body = str(cdata.get('body') or '')
					if c_body:
						for err in lint_issue_markdown(c_body, is_title=False, container_text=container_text, check_structure_policy=False):
							violations.append(f'GitHub comment {issue_url}#issuecomment-{cid} lint error ({err.get("code")}): {err.get("message")}')
						for g_err in local_source_grounding_issues(root, c_body, doc_path=cp):
							violations.append(f'GitHub comment {issue_url}#issuecomment-{cid} grounding error: {g_err}')
				except (OSError, ValueError):
					continue
def _collect_turn_issues(turn: dict, turn_state: dict | None) -> dict[str, dict]:
	turn_issues: dict[str, dict] = {}
	ts_cid = str((turn_state or {}).get('conversation_id') or '').strip()
	ts_plat = str((turn_state or {}).get('platform') or '').strip().lower()
	gh_raw = (turn_state or {}).get('github_issues') or []
	gh_items = list(gh_raw.values()) if isinstance(gh_raw, dict) else list(gh_raw)
	native_items = [it for it in (turn.get('issue_actions') or []) if isinstance(it, dict)]
	native_urls = {(it.get('url') or '').strip() for it in native_items if (it.get('url') or '').strip()}
	filtered_gh: list[dict] = []
	for item in gh_items:
		if not isinstance(item, dict):
			continue
		rec_cid = str(item.get('recorded_conversation_id') or '').strip()
		if rec_cid and ts_cid and rec_cid != ts_cid:
			continue
		rec_plat = str(item.get('recorded_platform') or '').strip().lower()
		if 'codex' == rec_plat and ts_plat and ('codex' != ts_plat):
			continue
		if 'non_codex' == rec_plat and 'codex' == ts_plat:
			continue
		u_item = (item.get('url') or '').strip()
		if native_urls and u_item not in native_urls:
			continue
		filtered_gh.append(item)
	for item in filtered_gh + native_items:
		if isinstance(item, dict):
			url = (item.get('url') or '').strip()
			parsed = parse_issue_url(url)
			if None is not parsed:
				slug, num = parsed
				st = str(item.get('state') or '').strip().lower()
				act = item.get('action') or item.get('last_action')
				if 'close' == act:
					st = 'closed'
				prev_entry = turn_issues.get(url, {})
				cids = list(prev_entry.get('comment_ids') or [])
				for cid in item.get('comment_ids') or []:
					if cid not in cids:
						cids.append(cid)
				acts = list(prev_entry.get('actions') or [])
				for a in item.get('actions') or []:
					if a and a not in acts:
						acts.append(a)
				if act and act not in acts:
					acts.append(act)
				pnum = item.get('parent_number') if isinstance(item.get('parent_number'), int) and (not isinstance(item.get('parent_number'), bool)) else prev_entry.get('parent_number')
				entry = {'url': url, 'repo': slug, 'number': num, 'state': st or prev_entry.get('state') or 'open', 'last_action': act or prev_entry.get('last_action') or 'issue', 'actions': acts, 'comment_ids': cids}
				if isinstance(pnum, int) and pnum != num:
					entry['parent_number'] = pnum
				turn_issues[url] = entry
	return turn_issues
def code_and_issue_lifecycle_status(root, turn, turn_state=None, response=None) -> dict:
	root = Path(root).resolve()
	repo_touched: dict[Path, set[str]] = {}
	for raw_p in turn.get('touched_files') or []:
		if isinstance(raw_p, str) and raw_p.strip():
			try:
				p = Path(raw_p.strip())
				p = p.resolve() if p.is_absolute() else (root / p).resolve()
			except OSError:
				continue
			for anc in (p, *p.parents):
				if is_issue_tracked_code_repo(anc):
					try:
						rel = p.relative_to(anc).as_posix()
					except ValueError:
						break
					if rel and '.' != rel and (not rel.startswith(('.git/', '\ua616/', '\ua66e/', '_/'))):
						repo_touched.setdefault(anc, set()).add(rel)
					break
	turn_issues = _collect_turn_issues(turn, turn_state)
	candidate_repos = list(repo_touched.keys())
	for cand in (root, root / 'code', root.parent / 'code'):
		cand_res = cand.resolve()
		if is_issue_tracked_code_repo(cand_res) and cand_res not in candidate_repos:
			candidate_repos.append(cand_res)
	for info in turn_issues.values():
		found_repo = find_local_code_repo(info['repo'], project_root=root)
		if None is not found_repo:
			found_res = found_repo.resolve()
			if is_issue_tracked_code_repo(found_res) and found_res not in candidate_repos:
				candidate_repos.append(found_res)
	workspace_code_repos = {c.resolve() for c in (root, root / 'code', root.parent / 'code') if is_issue_tracked_code_repo(c.resolve())}
	required_issues_by_repo: dict[Path, set[str]] = {rep: set() for rep in candidate_repos}
	repo_by_issue_url: dict[str, Path] = {}
	for url, info in turn_issues.items():
		for cand in candidate_repos:
			slug = origin_repo_slug(cand)
			if slug and slug.lower() == info['repo'].lower():
				repo_by_issue_url[url] = cand
				if 'close' == info.get('last_action'):
					required_issues_by_repo.setdefault(cand, set()).add(url)
					repo_touched.setdefault(cand, set())
	violations: list[str] = []
	checked_issues: list[dict] = []
	checked_urls: set[str] = set()
	committed_by_repo: dict[Path, set[str]] = {}
	_check_diagnostic_audit_filing(root, response, workspace_code_repos, repo_touched, turn_issues, candidate_repos, violations)
	for code_repo, rel_set in sorted(repo_touched.items(), key=lambda x: str(x[0])):
		req_set = required_issues_by_repo.setdefault(code_repo, set())
		committed_by_repo[code_repo] = _check_repo_commits_and_files(code_repo, sorted(rel_set), turn_issues, req_set, violations)
		for issue_url in sorted(req_set):
			parsed = parse_issue_url(issue_url)
			if None is not parsed:
				slug, num = parsed
				try:
					ready = verify_repo_issue_ready_for_close(code_repo, slug, num, project_root=root)
				except (ValueError, RuntimeError) as exc:
					ready = {'verified': False, 'violations': [str(exc)]}
				for v in ready.get('violations') or []:
					if v not in violations:
						violations.append(v)
				ev_state = evidence_issue_state(root, slug, num, candidate_repos)
				eff_state = ev_state or turn_issues.get(issue_url, {}).get('state') or 'open'
				checked_issues.append({'url': issue_url, 'repo': slug, 'number': num, 'state': eff_state, 'code_repo': str(code_repo), 'commit_and_push_verified': bool(ready.get('verified'))})
				checked_urls.add(issue_url)
				if 'closed' != eff_state:
					violations.append(f'GitHub issue {issue_url} remains {eff_state}; close it via df_github_issue.py close after git push before answer-prepare')
	_check_turn_issue_evidence(root, turn_issues, repo_by_issue_url, candidate_repos, checked_urls, checked_issues, violations)
	_check_multi_subtask_decomposition(root, response, repo_touched, committed_by_repo, turn_issues, required_issues_by_repo, candidate_repos, violations)
	return {'verified': not violations, 'touched_repos': {str(k): sorted(v) for k, v in repo_touched.items()}, 'issues': checked_issues, 'violations': violations}
def evidence_issue_files(root: Path, repo_slug: str, fname: str, candidate_repos=()) -> list[Path]:
	safe_repo = repo_slug.replace('/', '__')
	roots = [Path(root).resolve()] + [Path(rep).resolve().parent for rep in candidate_repos]
	ev_files: list[Path] = []
	for rt in roots:
		for rel in ('_/\ua616/KB/Evidence/GitHub', '\ua616/KB/Evidence/GitHub'):
			p = rt / rel / safe_repo / fname
			if p.is_file() and p not in ev_files:
				ev_files.append(p)
	hm = (HARNESS_META / '\ua616/KB/Evidence/GitHub' / safe_repo / fname).resolve()
	if hm.is_file() and hm not in ev_files:
		ev_files.append(hm)
	return ev_files
def evidence_issue_state(root: Path, repo_slug: str, number: int, candidate_repos=()) -> str | None:
	r = None
	for p in evidence_issue_files(root, repo_slug, f'issue-{int(number)}.json', candidate_repos):
		try:
			data = json.loads(p.read_text(encoding='utf-8'))
			issue_obj = data.get('issue') if isinstance(data.get('issue'), dict) else data
			st = str(issue_obj.get('state') or '').strip().lower()
			if st:
				r = st
				break
		except (OSError, ValueError):
			continue
	return r
def origin_repo_slug(code_repo: Path) -> str | None:
	r = None
	cfg_file = Path(code_repo) / '.git/config'
	if cfg_file.is_file():
		try:
			cfg_text = cfg_file.read_text(encoding='utf-8', errors='replace')
			cm = re.search('github\\.com[:/]([A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+?)(?:\\.git)?/?(?:\\s|$)', cfg_text)
			if cm:
				r = cm.group(1)
		except OSError:
			pass
	if None is r:
		proc = run_git_read(code_repo, ['remote', 'get-url', 'origin'], check=False)
		if 0 == proc.returncode:
			remote = proc.stdout.decode('utf-8', errors='replace').strip()
			m = re.search('github\\.com[:/]([A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+?)(?:\\.git)?$', remote)
			if m:
				r = m.group(1)
	return r
