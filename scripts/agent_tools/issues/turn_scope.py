# 2026-11-24 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from pathlib import Path
from typing import Any
import json
import os
# 2026-11-25
# "Add auditable mechanical replacement recipe exemption for TDD and per-file issue gates":
# https://github.com/dmitry-ai/harness/issues/239
_SKIP_TURN_SUFFIXES = ('-checkpoint-recovery.json', '-violation-recovery.json', '-similar-exemptions.json', '-ratchet-ok.json', '-mechanical-exempt.json')
# @used-by :func:`has_competing_open_turns()`
def _candidate_turns_dirs(root: Path) -> list[Path]:
	from ..path_registry import project_paths
	resolved = Path(root).resolve()
	cands: list[Path] = []
	try:
		cands.append(project_paths(resolved, exact_root=True).turns_dir.resolve())
	except (OSError, ValueError):
		pass
	for sub in ('_/\ua616/data/turns', '\ua616/data/turns'):
		p = (resolved / sub).resolve()
		if p not in cands:
			cands.append(p)
	return [d for d in cands if d.is_dir()]
# @used-by :func:`detect_active_session()`
def _fallback_env_session(environ: dict[str, str]) -> tuple[str, str]:
	from ..meta.transcripts import _parse_antigravity_source_metadata
	meta_cid, _ = _parse_antigravity_source_metadata(environ)
	ag_raw = str(environ.get('ANTIGRAVITY_CONVERSATION_ID') or '').strip() or str(meta_cid or '').strip()
	cx_raw = str(environ.get('CODEX_THREAD_ID') or '').strip()
	if ag_raw:
		r = ('antigravity', ag_raw.lower())
	elif cx_raw:
		r = ('codex', cx_raw.lower())
	else:
		r = ('', '')
	return r
# @used-by :func:`select_target_open_turns()`
def _match_open_by_cid(open_files: list[tuple[Path, str, str]], cid_low: str) -> list[Path]:
	return [tfile for tfile, _, t_cid in open_files if t_cid and cid_low == t_cid.lower()]
# @used-by :func:`select_target_open_turns()`
def _resolve_antigravity_parent_cid(active_cid: str, environ: dict[str, str]) -> str:
	r = ''
	try:
		from ..meta.builders import _collect_ag_issue_ctx
		ctx = _collect_ag_issue_ctx(environ, active_cid)
		parent = str(ctx.get('primary_cid') or '').strip().lower()
		r = parent if parent and parent != active_cid.lower() else ''
	except Exception:
		r = ''
	return r
# @used-by :func:`select_target_open_turns()`
def _sole_untagged_open_turn(open_files: list[tuple[Path, str, str]], active_plat: str) -> list[Path]:
	r: list[Path] = []
	if 1 == len(open_files):
		tfile, t_plat, t_cid = open_files[0]
		if (not t_cid) and ((not active_plat) or (not t_plat) or active_plat == t_plat):
			r = [tfile]
	return r
# 2026-11-24
# "Isolate per-conversation github_issues recording and turn-state filtering":
# https://github.com/dmitry-ai/harness/issues/195
# @used-by :meth:`agent_tools.issues.workspace.IssueEvidenceWorkspace.record_issue_in_open_turns()`
def detect_active_session(conversation_id: str | None=None, env: dict[str, str] | None=None) -> tuple[str, str]:
	from ..meta.builders import _detect_env_platform
	environ = dict(os.environ) if None is env else dict(env)
	plat, env_cid, _ = _detect_env_platform(environ)
	if not env_cid:
		fb_plat, fb_cid = _fallback_env_session(environ)
		plat, env_cid = (plat or fb_plat, fb_cid)
	explicit = str(conversation_id or '').strip().lower()
	eff_cid = explicit if explicit else str(env_cid or '').strip().lower()
	eff_plat = str(plat or '').strip().lower()
	return (eff_plat, eff_cid)
# @used-by :meth:`agent_tools.issues.auditor.TurnIssueLifecycleAuditor._collect_repos_and_issues()`
# @used-by :meth:`agent_tools.issues.auditor.TurnIssueLifecycleAuditor.collect_turn_issues()`
def has_competing_open_turns(root: Path, current_cid: str) -> bool:
	cur_low = str(current_cid or '').strip().lower()
	open_cids: set[str] = set()
	open_total = 0
	for tdir in _candidate_turns_dirs(root):
		for tfile in tdir.glob('*.json'):
			if tfile.name.endswith(_SKIP_TURN_SUFFIXES):
				continue
			try:
				data: Any = json.loads(tfile.read_text(encoding='utf-8'))
			except (OSError, ValueError):
				continue
			if isinstance(data, dict) and 'open' == data.get('status'):
				open_total += 1
				cid = str(data.get('conversation_id') or '').strip().lower()
				if cid:
					open_cids.add(cid)
	has_other_cid = bool(cur_low and any((cid != cur_low for cid in open_cids)))
	return has_other_cid or 2 <= open_total
# @used-by :meth:`agent_tools.issues.workspace.IssueEvidenceWorkspace.record_issue_in_open_turns()`
def select_target_open_turns(open_files: list[tuple[Path, str, str]], active_plat: str, active_cid: str, *, env: dict[str, str] | None=None) -> tuple[list[Path], str, str]:
	environ = dict(os.environ) if None is env else dict(env)
	if not active_cid:
		r = ([open_files[0][0]], '', active_plat or open_files[0][1]) if 1 == len(open_files) else ([], '', active_plat)
	else:
		targets = _match_open_by_cid(open_files, active_cid)
		rec_cid = active_cid
		if (not targets) and 'antigravity' == active_plat:
			parent_cid = _resolve_antigravity_parent_cid(active_cid, environ)
			if parent_cid:
				targets = _match_open_by_cid(open_files, parent_cid)
				if targets:
					rec_cid = parent_cid
		if not targets:
			targets = _sole_untagged_open_turn(open_files, active_plat)
		r = (targets, rec_cid, active_plat)
	return r