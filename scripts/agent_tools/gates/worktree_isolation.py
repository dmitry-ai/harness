# 2026-11-24 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import time
# 2026-11-24
# "Add PreToolUse worktree isolation gate for live main checkouts":
# https://github.com/dmitry-ai/harness/issues/185
NAME = 'EXEC-5-WORKTREE-GATE'
PRIORITY = 97
# 2026-11-26 "Block raw worktree removal and fail closed on locked cleanup": https://github.com/dmitry-ai/harness/issues/303
TOOLS = frozenset({'write_file', 'edit_file', 'run_command'})
_ACTIVE_TURN_MAX_AGE_SECONDS = 86400
_META_PARTS = frozenset({'.git', '__pycache__', 'node_modules', '\ua616', '\ua66e', '\U0001f56e'})
def _active_turn_id(path: Path, cutoff: float) -> str | None:
	r = None
	try:
		data = json.loads(path.read_text(encoding='utf-8-sig'))
	except (OSError, ValueError):
		data = None
	if isinstance(data, dict) and 'open' == data.get('status'):
		if cutoff <= _turn_timestamp(data, path):
			r = str(data.get('conversation_id') or data.get('turn_key') or path.stem).strip() or path.stem
	return r
def _count_active_open_turns(turns_dir: Path, *, max_age_seconds: int=_ACTIVE_TURN_MAX_AGE_SECONDS) -> int:
	active: set[str] = set()
	cutoff = time.time() - max(60, int(max_age_seconds))
	try:
		entries = list(turns_dir.glob('*.json'))
	except OSError:
		entries = []
	for path in entries:
		if not path.name.endswith('-checkpoint-recovery.json'):
			tid = _active_turn_id(path, cutoff)
			if None is not tid:
				active.add(tid)
	return len(active)
def _evaluate_main_checkout(name: str, repo_root: Path, cwd: str | None) -> str | None:
	from ..runtime_snapshot import is_harness_code_repo
	r = None
	if is_harness_code_repo(repo_root):
		r = f'EXEC-5: Direct {name} inside Harness main checkout ({repo_root.as_posix()}) is prohibited; create an isolated linked worktree via harness.py worktree-begin "{repo_root.as_posix()}" --task <task-id> and land via worktree-land.'
	else:
		turns_dir = _find_turns_dir(repo_root, cwd)
		if None is not turns_dir:
			active = _count_active_open_turns(turns_dir)
			if 2 <= active:
				r = f'EXEC-5: Direct {name} inside main checkout ({repo_root.as_posix()}) is blocked while {active} concurrent open turns are active in {turns_dir.as_posix()}; create an isolated linked worktree via harness.py worktree-begin "{repo_root.as_posix()}" --task <task-id>.'
	return r
def _find_git_repo_root(path: Path) -> Path | None:
	r = None
	start = path if path.is_dir() else path.parent
	for anc in (start, *start.parents):
		if (anc / '.git').exists():
			r = anc
			break
	return r
def _find_turns_dir(repo_root: Path, cwd: str | None) -> Path | None:
	r = None
	roots = [repo_root]
	if cwd and str(cwd).strip():
		roots.append(Path(str(cwd)).resolve())
	for base in roots:
		for depth, anc in enumerate((base, *base.parents)):
			if 6 < depth:
				break
			cand = anc / '\ua616/data/turns'
			if cand.is_dir():
				r = cand
				break
		if None is not r:
			break
	return r
def _governed_repo_for_path(raw: str, cwd: str | None) -> Path | None:
	r = None
	full = _resolve_target_path(raw, cwd)
	repo_root = _find_git_repo_root(full)
	if None is not repo_root:
		try:
			rel = full.relative_to(repo_root).as_posix()
		except ValueError:
			rel = ''
		if rel and (not _is_meta_rel(rel)):
			r = repo_root
	return r
def _is_meta_rel(rel_posix: str) -> bool:
	parts = [p.casefold() for p in rel_posix.replace('\\', '/').split('/') if p and '.' != p]
	return (not parts) or any(part in _META_PARTS for part in parts)
def _resolve_target_path(raw: str, cwd: str | None) -> Path:
	text = raw.strip()
	if 'nt' == os.name and 3 <= len(text) and '/' == text[0] and text[1].isalpha() and '/' == text[2]:
		text = f'{text[1]}:{text[2:]}'
	cand = Path(text)
	if not cand.is_absolute() and cwd and str(cwd).strip():
		cand = Path(str(cwd)) / cand
	try:
		r = cand.resolve()
	except OSError:
		r = cand
	return r
def _turn_timestamp(data: dict, path: Path) -> float:
	r = 0.0
	for key in ('updated_at', 'created_at'):
		val = data.get(key)
		if isinstance(val, str) and val.strip():
			try:
				dt = datetime.fromisoformat(val.strip().replace('Z', '+00:00'))
				r = (dt if None is not dt.tzinfo else dt.replace(tzinfo=timezone.utc)).timestamp()
				break
			except ValueError:
				pass
	if 0.0 == r:
		try:
			r = path.stat().st_mtime
		except OSError:
			r = 0.0
	return r
def check(name: str, args: dict, payload: dict | None=None) -> str | None:
	r = None
	# 2026-11-26 "Block raw worktree removal and fail closed on locked cleanup": https://github.com/dmitry-ai/harness/issues/303
	if 'run_command' == name:
		from ..worktree_guard import prohibited_worktree_shell_deletions
		viols = prohibited_worktree_shell_deletions(str(args.get('CommandLine') or ''))
		r = '; '.join(viols) if viols else None
	elif name in TOOLS:
		raw = args.get('Path') or args.get('path') or args.get('TargetFile') or ''
		if isinstance(raw, str) and raw.strip():
			cwd_val = (payload or {}).get('cwd')
			cwd = cwd_val if isinstance(cwd_val, str) else None
			repo_root = _governed_repo_for_path(raw, cwd)
			if None is not repo_root:
				from ..worktree_flow import is_linked_worktree
				if not is_linked_worktree(repo_root):
					r = _evaluate_main_checkout(name, repo_root, cwd)
	return r
