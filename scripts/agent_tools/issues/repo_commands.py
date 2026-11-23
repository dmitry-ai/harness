# 2026-11-24 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Isolate per-conversation github_issues recording and turn-state filtering":
# https://github.com/dmitry-ai/harness/issues/195
# 2026-11-23 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# https://github.com/dmitry-ai/harness/issues/77
from __future__ import annotations
import argparse
import time
from typing import Any
from ..cli_common import dump_json
from .linter import IssueMarkdownLinter
from .service_helpers import resolve_title
from .workspace import IssueEvidenceWorkspace
def _audit_repo_comments(api_fn, linter: IssueMarkdownLinter, repo: str, target_locale: str, containers: dict[int, str]) -> tuple[list[dict[str, Any]], int]:
	raw_comments = api_fn(f'repos/{repo}/issues/comments?per_page=100', method='GET', paginate=True) or []
	corrupted: list[dict[str, Any]] = []
	for c in raw_comments:
		issue_num = int(c['issue_url'].rstrip('/').split('/')[-1])
		c_errs = linter.lint(c.get('body') or '', is_title=False, target_locale=target_locale, container_text=containers.get(issue_num), check_structure_policy=False)
		if c_errs:
			corrupted.append({'comment_id': c['id'], 'issue_number': issue_num, 'html_url': c.get('html_url'), 'body_errors': c_errs})
	return (corrupted, len(raw_comments))
def _audit_repo_issues(linter: IssueMarkdownLinter, issues: list[dict[str, Any]], target_locale: str, strict: bool) -> tuple[list[dict[str, Any]], dict[int, str]]:
	corrupted, containers = ([], {})
	for iss in issues:
		containers[iss['number']] = f"{iss.get('title') or ''}\n{iss.get('body') or ''}".strip()
		t_errs = linter.lint(iss.get('title') or '', is_title=True, target_locale=target_locale, check_structure_policy=strict)
		b_errs = linter.lint(iss.get('body') or '', is_title=False, target_locale=target_locale, check_structure_policy=strict)
		if t_errs or b_errs:
			corrupted.append({'number': iss['number'], 'title': iss.get('title'), 'html_url': iss.get('html_url'), 'title_errors': t_errs, 'body_errors': b_errs})
	return (corrupted, containers)
def _poll_transferred_repo(api_fn, target_repo: str, max_attempts: int, delay_s: float) -> dict[str, Any] | None:
	r = None
	for attempt in range(max_attempts):
		try:
			cand = api_fn(f'repos/{target_repo}', method='GET')
			if isinstance(cand, dict) and target_repo.lower() == str(cand.get('full_name') or '').lower():
				r = cand
				break
		except RuntimeError:
			pass
		if attempt + 1 < max_attempts and 0 < delay_s:
			time.sleep(delay_s)
	return r
def run_audit_repo(api_fn, linter: IssueMarkdownLinter, args: argparse.Namespace) -> int:
	repo = linter.validate_repo(args.repo)
	target_locale = getattr(args, 'target_locale', 'en-US') or 'en-US'
	strict = bool(getattr(args, 'strict_structure', False))
	raw_items = api_fn(f'repos/{repo}/issues?state={args.state}&per_page=100', method='GET', paginate=True) or []
	issues = sorted((item for item in raw_items if 'pull_request' not in item), key=lambda x: x['number'])
	corrupted_issues, containers = _audit_repo_issues(linter, issues, target_locale, strict)
	corrupted_comments, c_count = _audit_repo_comments(api_fn, linter, repo, target_locale, containers) if args.include_comments else ([], 0)
	valid = not corrupted_issues and (not corrupted_comments)
	dump_json({'valid': valid, 'repo': repo, 'issue_count': len(issues), 'comment_count': c_count, 'corrupted_issue_count': len(corrupted_issues), 'corrupted_comment_count': len(corrupted_comments), 'corrupted_issues': corrupted_issues, 'corrupted_comments': corrupted_comments})
	return 0 if valid else 2
def run_fetch(service, args: argparse.Namespace) -> int:
	repo, number, project_root = (service.linter.validate_repo(args.repo), int(args.issue), getattr(args, 'project_root', None))
	fetched = service._api(f'repos/{repo}/issues/{number}', method='GET')
	if not isinstance(fetched, dict) or 'pull_request' in fetched:
		raise ValueError(f'Target #{number} in {repo} is not a valid GitHub issue')
	eff_parent = service.linter.extract_parent_number(str(fetched.get('body') or ''), repo)
	if None is not eff_parent and eff_parent != number:
		service.verify_and_persist_parent_issue([], repo, eff_parent, self_number=number, project_root=project_root)
	service.workspace.persist_issue_evidence([], repo, fetched, kind='issue', action='fetch', project_root=project_root, parent_number=eff_parent, conversation_id=getattr(args, 'conversation', None))
	out: dict[str, Any] = {'ok': True, 'action': 'fetch', 'repo': repo, 'number': number, 'state': fetched.get('state'), 'state_reason': fetched.get('state_reason'), 'title': fetched.get('title'), 'html_url': fetched.get('html_url'), 'verified': True, 'body_chars': len(fetched.get('body') or '')}
	if None is not eff_parent and eff_parent != number:
		out.update(parent_number=int(eff_parent), parent_url=f'https://github.com/{repo}/issues/{int(eff_parent)}')
	dump_json(out)
	return 0
def run_lint(linter: IssueMarkdownLinter, args: argparse.Namespace) -> int:
	consumable: list = []
	target_locale = getattr(args, 'target_locale', 'en-US') or 'en-US'
	repo = linter.validate_repo(args.repo) if getattr(args, 'repo', None) else None
	parent_num = linter.parse_parent_arg(getattr(args, 'parent', None), repo)
	title = resolve_title(args, consumable)
	title_errors = linter.lint(title, is_title=True, target_locale=target_locale) if None is not title else []
	body_errors = linter.lint(linter.read_utf8_no_bom_file(args.body_file)[2], is_title=False, target_locale=target_locale, parent_number=parent_num, repo=repo) if args.body_file else []
	valid = not title_errors and (not body_errors)
	dump_json({'valid': valid, 'title_errors': title_errors, 'body_errors': body_errors})
	return 0 if valid else 2
def run_transfer_repo(api_fn, linter: IssueMarkdownLinter, workspace: IssueEvidenceWorkspace, args: argparse.Namespace) -> int:
	repo = linter.validate_repo(args.repo)
	new_owner = linter.validate_slug_part(args.new_owner, 'new_owner')
	new_name = linter.validate_slug_part(args.new_name, 'new_name') if getattr(args, 'new_name', None) else repo.split('/', 1)[1]
	target_repo = f'{new_owner}/{new_name}'
	if repo.lower() == target_repo.lower():
		raise ValueError(f'Source and target repositories are identical: {repo}')
	payload = {'new_owner': new_owner, **({'new_name': new_name} if getattr(args, 'new_name', None) else {})}
	transfer_resp = api_fn(f'repos/{repo}/transfer', method='POST', payload=payload)
	fetched = _poll_transferred_repo(api_fn, target_repo, max(1, int(getattr(args, 'poll_attempts', 8) or 8)), float(getattr(args, 'poll_interval', 1.5)))
	ev_path = workspace.persist_repo_transfer_evidence(repo, target_repo, transfer_resp if isinstance(transfer_resp, dict) else None, fetched, project_root=getattr(args, 'project_root', None))
	if None is fetched:
		dump_json({'ok': False, 'action': 'transfer-repo', 'stage': 'post_flight_readback', 'source_repo': repo, 'target_repo': target_repo, 'verified': False, 'evidence': str(ev_path)})
		r = 2
	else:
		dump_json({'ok': True, 'action': 'transfer-repo', 'source_repo': repo, 'target_repo': fetched.get('full_name'), 'html_url': fetched.get('html_url'), 'private': bool(fetched.get('private')), 'default_branch': fetched.get('default_branch'), 'verified': True, 'evidence': str(ev_path)})
		r = 0
	return r
