# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Block active-turn open deferred child issues in lifecycle auditor":
# https://github.com/dmitry-ai/harness/issues/367
from __future__ import annotations
from pathlib import Path
# @used-by :func:`find_open_deferred_children()`
def _issue_created_in_turn(info: dict) -> bool:
	return 'create' == info.get('last_action') or 'create' in set(info.get('actions') or ())
# @used-by :func:`flag_parent_and_deferred_children()`
def _flag_unclosed_parent(auditor, code_repo: Path, slug: str, pnum: int) -> None:
	children = auditor.workspace.find_tracked_child_issues(slug, pnum, project_root=auditor.root, code_repo=code_repo)
	if children and all(('closed' == c.get('state') for c in children)):
		p_url = f'https://github.com/{slug}/issues/{pnum}'
		p_state = auditor.workspace.evidence_issue_state(auditor.root, slug, pnum, auditor.candidate_repos) or (auditor.turn_issues.get(p_url) or {}).get('state') or 'open'
		if 'closed' != p_state:
			auditor.violations.append(f'EXEC-5 violation: parent issue {p_url} in {slug} remains {p_state} after all tracked child subtask issues are closed; close it via df_github_issue.py close')
# @used-by :func:`flag_parent_and_deferred_children()`
def find_open_deferred_children(auditor, slug: str) -> dict[int, list[str]]:
	grouped: dict[int, list[str]] = {}
	slug_low = slug.lower()
	for issue_url, info in sorted(auditor.turn_issues.items()):
		if info.get('repo', '').lower() != slug_low or (not _issue_created_in_turn(info)):
			continue
		num = int(info['number'])
		pnum = auditor._resolve_parent_number(info['repo'], num, require_parent_evidence=False)
		if None is pnum:
			continue
		eff_state = auditor.workspace.evidence_issue_state(auditor.root, slug, num, auditor.candidate_repos) or info.get('state') or 'open'
		if 'closed' != eff_state:
			grouped.setdefault(pnum, []).append(issue_url)
	return grouped
# @used-by :meth:`agent_tools.issues.auditor.TurnIssueLifecycleAuditor._flag_unclosed_completed_parents()`
def flag_parent_and_deferred_children(auditor, code_repo: Path, slug: str, parent_nums: set[int]) -> None:
	for pnum in sorted(parent_nums):
		_flag_unclosed_parent(auditor, code_repo, slug, pnum)
	for pnum, child_urls in sorted(find_open_deferred_children(auditor, slug).items()):
		joined = ', '.join(child_urls)
		p_url = f'https://github.com/{slug}/issues/{pnum}'
		auditor.violations.append(f'SCOPE-2 / EXEC-5 violation: active turn created open deferred child issue(s) under parent {p_url} in {slug} ({joined}) without completing them; finish all requested subtasks, pass --blocked-report for a documented blocker, or obtain explicit user authorization to stop the turn early')
