# 2026-11-13 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Extract issue_lifecycle.py from completion.py, fix open backlog-issue lifecycle gating, and consolidate Git/issue helpers in git_gate.py":
# https://github.com/dmitry-ai/harness/issues/53
import json
from pathlib import Path
import re
from .git_gate import extract_comment_issue_urls, extract_issue_urls, is_code_file, is_issue_tracked_code_repo, parse_issue_url, run_git_read, verify_repo_issue_ready_for_close
from .github_issue import find_local_code_repo, lint_issue_markdown
from .runtime import HARNESS_META
from .source_grounding import local_source_grounding_issues
def _check_diagnostic_audit_filing(root: Path, response, workspace_code_repos: set[Path], repo_touched: dict, turn_issues: dict, candidate_repos: list[Path], violations: list[str]) -> None:
	if isinstance(response, str) and response.strip() and workspace_code_repos and (not repo_touched):
		has_diag_causes = bool(re.search('(?m)(?:^|\\s|`|\\*\\*)(?:C|H)-[1-9]\\d*\\b', response))
		has_diag_methods = bool(re.search('(?m)(?:^|\\s|`|\\*\\*)M-[1-9]\\d*\\b', response))
		has_py_targets = bool(re.search('\\b[A-Za-z0-9_/-]+\\.py\\b', response))
		if has_diag_causes and has_diag_methods and has_py_targets:
			for ws_repo in sorted(workspace_code_repos, key=str):
				ws_slug = origin_repo_slug(ws_repo)
				if ws_slug:
					has_ws_issue = any((info['repo'].lower() == ws_slug.lower() for info in turn_issues.values()))
					if not has_ws_issue:
						for resp_url in extract_issue_urls(response):
							parsed = parse_issue_url(resp_url)
							if None is not parsed and parsed[0].lower() == ws_slug.lower() and evidence_issue_files(root, parsed[0], f'issue-{parsed[1]}.json', candidate_repos):
								has_ws_issue = True
								break
					if not has_ws_issue:
						violations.append(f'EXEC-5 / SCOPE-2: Diagnostic audit of {ws_slug} identifies repository defects (C-/H-) and remediation methods (M-) without recording corresponding GitHub Issues via df_github_issue.py')
def _check_repo_commits_and_files(code_repo: Path, rel_paths: list[str], turn_issues: dict, required_issues: set[str], violations: list[str]) -> None:
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
def _check_turn_issue_evidence(root: Path, turn_issues: dict, repo_by_issue_url: dict, candidate_repos: list[Path], checked_urls: set[str], checked_issues: list[dict], violations: list[str]) -> None:
	for issue_url, info in sorted(turn_issues.items()):
		slug, num = (info['repo'], int(info['number']))
		ev_state = evidence_issue_state(root, slug, num, candidate_repos)
		eff_state = ev_state or info.get('state') or 'open'
		if issue_url not in checked_urls:
			mapped_repo = repo_by_issue_url.get(issue_url)
			checked_issues.append({'url': issue_url, 'repo': slug, 'number': num, 'state': eff_state, 'code_repo': str(mapped_repo) if mapped_repo else None, 'commit_and_push_verified': False})
			checked_urls.add(issue_url)
		iss_files = evidence_issue_files(root, slug, f'issue-{num}.json', candidate_repos)
		if not iss_files and info.get('last_action') in ('create', 'edit'):
			violations.append(f'GitHub issue {issue_url} is missing saved API read-back Evidence JSON (issue-{num}.json)')
		container_text = None
		for p in iss_files[:1]:
			try:
				data = json.loads(p.read_text(encoding='utf-8'))
				iss_obj = data.get('issue') if isinstance(data.get('issue'), dict) else data
				t_txt = str(iss_obj.get('title') or '')
				b_txt = str(iss_obj.get('body') or '')
				container_text = f'{t_txt}\n{b_txt}'.strip()
				if t_txt and info.get('last_action') in ('create', 'edit'):
					for err in lint_issue_markdown(t_txt, is_title=True):
						violations.append(f'GitHub issue {issue_url} title lint error ({err.get("code")}): {err.get("message")}')
				if b_txt and info.get('last_action') in ('create', 'edit'):
					for err in lint_issue_markdown(b_txt, is_title=False):
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
						for err in lint_issue_markdown(c_body, is_title=False, container_text=container_text):
							violations.append(f'GitHub comment {issue_url}#issuecomment-{cid} lint error ({err.get("code")}): {err.get("message")}')
						for g_err in local_source_grounding_issues(root, c_body, doc_path=cp):
							violations.append(f'GitHub comment {issue_url}#issuecomment-{cid} grounding error: {g_err}')
				except (OSError, ValueError):
					continue
def _collect_turn_issues(turn: dict, turn_state: dict | None) -> dict[str, dict]:
	turn_issues: dict[str, dict] = {}
	gh_raw = (turn_state or {}).get('github_issues') or []
	gh_items = list(gh_raw.values()) if isinstance(gh_raw, dict) else list(gh_raw)
	for item in gh_items + list(turn.get('issue_actions') or []):
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
				turn_issues[url] = {'url': url, 'repo': slug, 'number': num, 'state': st or prev_entry.get('state') or 'open', 'last_action': act or prev_entry.get('last_action') or 'issue', 'comment_ids': cids}
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
	_check_diagnostic_audit_filing(root, response, workspace_code_repos, repo_touched, turn_issues, candidate_repos, violations)
	for code_repo, rel_set in sorted(repo_touched.items(), key=lambda x: str(x[0])):
		req_set = required_issues_by_repo.setdefault(code_repo, set())
		_check_repo_commits_and_files(code_repo, sorted(rel_set), turn_issues, req_set, violations)
		for issue_url in sorted(req_set):
			parsed = parse_issue_url(issue_url)
			if None is not parsed:
				slug, num = parsed
				try:
					ready = verify_repo_issue_ready_for_close(code_repo, slug, num)
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
