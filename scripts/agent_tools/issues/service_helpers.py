# 2026-11-23 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
import argparse
import json
from pathlib import Path
import subprocess
from typing import Any
from ..git_gate import is_issue_tracked_code_repo, run_git_read
from ..storage import iter_embedded_json_objects
from .linter import IssueMarkdownLinter
from .workspace import IssueEvidenceWorkspace, _SKIP_TURN_SUFFIXES
# 2026-11-24
# "Decompose github_issue.py and issue_lifecycle.py into IssueMarkdownLinter, IssueEvidenceWorkspace, GitHubIssueService, and TurnIssueLifecycleAuditor with locked turn updates":
# https://github.com/dmitry-ai/harness/issues/77
def build_create_payload(args: argparse.Namespace, title: str, body: str) -> dict[str, Any]:
	payload: dict[str, Any] = {'title': title, 'body': body}
	if getattr(args, 'label', None):
		labels = [lbl.strip() for item in args.label for lbl in item.split(',') if lbl.strip()]
		if labels:
			payload['labels'] = labels
	if getattr(args, 'assignee', None):
		assignees = [a.strip() for item in args.assignee for a in item.split(',') if a.strip()]
		if assignees:
			payload['assignees'] = assignees
	if None is not getattr(args, 'milestone', None):
		payload['milestone'] = args.milestone
	return payload
def dirty_issue_first_files(workspace: IssueEvidenceWorkspace, repo: str, *, project_root: str | Path | None=None, source_files: list[tuple[Path, bytes]] | None=None, repo_root: str | Path | None=None) -> list[str]:
	code_repo = workspace.find_local_code_repo(repo, project_root=project_root, source_files=source_files, repo_root=repo_root)
	r: list[str] = []
	if None is not code_repo and (code_repo / '.git').exists() and (not _is_isolated_temp_root(code_repo, project_root)):
		proc = run_git_read(code_repo, ['status', '--porcelain', '-z', '--untracked-files=all'], check=False)
		if 0 == proc.returncode and proc.stdout:
			r = _parse_dirty_porcelain(code_repo, proc.stdout)
	return r
def _is_isolated_temp_root(code_repo: Path, project_root: str | Path | None) -> bool:
	r = False
	if None is not project_root and str(project_root).strip():
		pr = Path(project_root).resolve()
		pr_low = pr.as_posix().lower()
		if ('/temp/' in pr_low or '/tmp/' in pr_low) and (not code_repo.is_relative_to(pr)) and (not pr.is_relative_to(code_repo)):
			r = True
	return r
def _parse_dirty_porcelain(code_repo: Path, stdout: bytes) -> list[str]:
	# 2026-11-26 "Harden addon companion observability and conflict reservation hygiene": https://github.com/dmitry-ai/harness/issues/302
	from ..addon_observability import is_live_runtime_data_file
	from ..issue_first_gate import _is_excluded_meta_rel
	from ..tdd_gate import classify_code_path
	tracked = is_issue_tracked_code_repo(code_repo)
	entries = [e for e in stdout.decode('utf-8', errors='replace').split('\x00') if e]
	dirty: list[str] = []
	idx = 0
	while idx < len(entries):
		entry = entries[idx]
		rel_path = entry[3:].replace('\\', '/')
		idx += 2 if entry[:2].startswith(('R', 'C')) and idx + 1 < len(entries) else 1
		if rel_path and (not _is_excluded_meta_rel(rel_path)) and (not is_live_runtime_data_file(code_repo, rel_path)) and (tracked or 'non_code' != classify_code_path(code_repo / rel_path)):
			if rel_path not in dirty:
				dirty.append(rel_path)
	return sorted(dirty)
def _decode_gh_stdout(raw_out: str, paginate: bool) -> Any:
	if not raw_out.strip():
		r: Any = None
	elif not (paginate and raw_out.lstrip().startswith('[')):
		r = json.loads(raw_out)
	else:
		merged: list[Any] = []
		for obj in iter_embedded_json_objects(raw_out):
			merged.extend(obj) if isinstance(obj, list) else merged.append(obj)
		r = merged
	return r
def gh_api_call(endpoint: str, *, method: str='GET', payload: dict[str, Any] | None=None, paginate: bool=False, runner=None) -> Any:
	cmd = ['gh', 'api', endpoint]
	if 'GET' != method:
		cmd.extend(['-X', method])
	if paginate:
		cmd.append('--paginate')
	input_bytes = None
	if None is not payload:
		cmd.extend(['--input', '-'])
		input_bytes = json.dumps(payload, ensure_ascii=False).encode('utf-8')
	run_fn = runner if None is not runner else subprocess.run
	proc = run_fn(cmd, input=input_bytes, capture_output=True, check=False, creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
	if 0 != proc.returncode:
		err_msg = proc.stderr.decode('utf-8', errors='replace').strip() or proc.stdout.decode('utf-8', errors='replace').strip()
		raise RuntimeError(f'gh api {method} {endpoint} failed (exit {proc.returncode}): {err_msg}')
	return _decode_gh_stdout(proc.stdout.decode('utf-8'), paginate)
def _recorded_open_turn_repos(turn_dirs: list[Path]) -> set[str]:
	recorded: set[str] = set()
	for tdir in turn_dirs:
		if not tdir.is_dir():
			continue
		for tfile in tdir.glob('*.json'):
			if tfile.name.endswith(_SKIP_TURN_SUFFIXES):
				continue
			try:
				tdata = json.loads(tfile.read_text(encoding='utf-8'))
			except (OSError, ValueError):
				continue
			if isinstance(tdata, dict) and 'open' == tdata.get('status'):
				_collect_recorded_repos_from_turn(tdata, recorded)
	return recorded
def _collect_recorded_repos_from_turn(tdata: dict[str, Any], recorded: set[str]) -> None:
	gh_raw = tdata.get('github_issues') or {}
	items = gh_raw.values() if isinstance(gh_raw, dict) else gh_raw if isinstance(gh_raw, list) else ()
	for item in items:
		if isinstance(item, dict):
			acts = {str(a) for a in (item.get('actions') or ()) if a}
			if item.get('last_action'):
				acts.add(str(item['last_action']))
			r_slug = str(item.get('repo') or '').strip().lower()
			if r_slug and (acts & {'create', 'edit', 'comment'}):
				recorded.add(r_slug)
def pending_similar_peer_slugs(workspace: IssueEvidenceWorkspace, code_repo: Path | None, *, repo: str, project_root: str | Path | None=None, source_files: list[tuple[Path, bytes]]=()) -> list[str]:
	r: list[str] = []
	if None is not code_repo:
		try:
			from ..issue_lifecycle import similar_project_repo_slugs
			from ..path_registry import project_paths
			pp_repo = project_paths(code_repo)
		except (OSError, ValueError):
			pp_repo = None
		if None is not pp_repo:
			peer_slugs = list(dict.fromkeys((slug for peer in pp_repo.similar_projects for slug in similar_project_repo_slugs(peer))))
			if peer_slugs:
				turn_dirs = list(dict.fromkeys([*(tdir for _, tdir in workspace.resolve_issue_targets(source_files, repo, project_root=project_root)), pp_repo.turns_dir]))
				recorded = _recorded_open_turn_repos(turn_dirs)
				r = [s for s in peer_slugs if s.lower() not in recorded]
	return r
def resolve_metadata_project_root(workspace: IssueEvidenceWorkspace, repo: str, project_root: str | Path | None, consumable: list[tuple[Path, bytes]]) -> Path | None:
	if None is not project_root and str(project_root).strip():
		r: Path | None = Path(project_root).resolve()
	else:
		code_repo = workspace.find_local_code_repo(repo, project_root=project_root, source_files=consumable)
		if None is not code_repo:
			try:
				from ..path_registry import project_paths
				r = project_paths(code_repo).root
			except (OSError, ValueError):
				r = code_repo
		else:
			try:
				from ..path_registry import resolve_project_root
				r = resolve_project_root(Path.cwd().resolve())
			except (OSError, ValueError):
				r = Path.cwd().resolve()
	return r
def resolve_title(args: argparse.Namespace, consumable: list[tuple[Path, bytes]]) -> str | None:
	if getattr(args, 'title_file', None):
		t_path, t_raw, t_text = IssueMarkdownLinter.read_utf8_no_bom_file(args.title_file)
		consumable.append((t_path, t_raw))
		r = t_text.strip()
	elif None is not getattr(args, 'title', None):
		r = args.title.strip()
	else:
		r = None
	return r
