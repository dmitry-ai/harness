# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from datetime import datetime, timezone
from pathlib import Path
from Df.Core.lib.git import df_git_root
from Df.Core.lib.state import df_is_windows
import json
import time
# 2026-11-26 "Move verification gate subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/381
class WorktreeIsolationGate:
	NAME = 'EXEC-5-WORKTREE-GATE'
	PRIORITY = 97
	TOOLS = frozenset({'write_file', 'edit_file', 'run_command'})
	__ACTIVE_TURN_MAX_AGE_SECONDS = 86400
	__META_PARTS = frozenset({'.git', '__pycache__', 'node_modules', '\ua616', '\ua66e', '\U0001f56e'})
	# @used-by :meth:`WorktreeIsolationGate.__count_active_open_turns()`
	@staticmethod
	def __active_turn_id(path: Path, cutoff: float) -> str | None:
		r = None
		try:
			data = json.loads(path.read_text(encoding='utf-8-sig'))
		except (OSError, ValueError):
			data = None
		if isinstance(data, dict) and 'open' == data.get('status') and cutoff <= WorktreeIsolationGate.__turn_timestamp(data, path):
			r = str(data.get('conversation_id') or data.get('turn_key') or path.stem).strip() or path.stem
		return r
	# @used-by :meth:`WorktreeIsolationGate.__evaluate_main_checkout()`
	@staticmethod
	def __count_active_open_turns(turns_dir: Path, *, max_age_seconds: int=__ACTIVE_TURN_MAX_AGE_SECONDS) -> int:
		active: set[str] = set()
		cutoff = time.time() - max(60, int(max_age_seconds))
		try:
			entries = list(turns_dir.glob('*.json'))
		except OSError:
			entries = []
		for path in entries:
			if not path.name.endswith('-checkpoint-recovery.json'):
				tid = WorktreeIsolationGate.__active_turn_id(path, cutoff)
				if None is not tid:
					active.add(tid)
		return len(active)
	# @used-by :meth:`WorktreeIsolationGate.check()`
	@staticmethod
	def __evaluate_main_checkout(name: str, repo_root: Path, cwd: str | None) -> str | None:
		from agent_tools.runtime_snapshot import is_harness_code_repo
		r = None
		if is_harness_code_repo(repo_root):
			r = f'EXEC-5: Direct {name} inside Harness main checkout ({repo_root.as_posix()}) is prohibited; create an isolated linked worktree via harness.py worktree-begin "{repo_root.as_posix()}" --task <task-id> and land via worktree-land.'
		else:
			turns_dir = WorktreeIsolationGate.__find_turns_dir(repo_root, cwd)
			if None is not turns_dir:
				active = WorktreeIsolationGate.__count_active_open_turns(turns_dir)
				if 2 <= active:
					r = f'EXEC-5: Direct {name} inside main checkout ({repo_root.as_posix()}) is blocked while {active} concurrent open turns are active in {turns_dir.as_posix()}; create an isolated linked worktree via harness.py worktree-begin "{repo_root.as_posix()}" --task <task-id>.'
		return r
	# @used-by :meth:`WorktreeIsolationGate.__evaluate_main_checkout()`
	@staticmethod
	def __find_turns_dir(repo_root: Path, cwd: str | None) -> Path | None:
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
	# @used-by :meth:`WorktreeIsolationGate.check()`
	@staticmethod
	def __governed_repo_for_path(raw: str, cwd: str | None) -> Path | None:
		r = None
		full = WorktreeIsolationGate.__resolve_target_path(raw, cwd)
		repo_root = df_git_root(full)
		if None is not repo_root:
			try:
				rel = full.relative_to(repo_root).as_posix()
			except ValueError:
				rel = ''
			if rel and (not WorktreeIsolationGate.__is_meta_rel(rel)):
				r = repo_root
		return r
	# @used-by :meth:`WorktreeIsolationGate.__governed_repo_for_path()`
	@staticmethod
	def __is_meta_rel(rel_posix: str) -> bool:
		parts = [p.casefold() for p in rel_posix.replace('\\', '/').split('/') if p and '.' != p]
		return (not parts) or any((part in WorktreeIsolationGate.__META_PARTS for part in parts))
	# @used-by :meth:`WorktreeIsolationGate.__governed_repo_for_path()`
	@staticmethod
	def __resolve_target_path(raw: str, cwd: str | None) -> Path:
		text = raw.strip()
		if df_is_windows() and 3 <= len(text) and '/' == text[0] and text[1].isalpha() and '/' == text[2]:
			text = f'{text[1]}:{text[2:]}'
		cand = Path(text)
		if not cand.is_absolute() and cwd and str(cwd).strip():
			cand = Path(str(cwd)) / cand
		try:
			r = cand.resolve()
		except OSError:
			r = cand
		return r
	# @used-by :meth:`WorktreeIsolationGate.__active_turn_id()`
	@staticmethod
	def __turn_timestamp(data: dict, path: Path) -> float:
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
	# @used-by :func:`agent_tools.gates.worktree_isolation.check()`
	def check(self, name: str, args: dict, payload: dict | None=None) -> str | None:
		r = None
		if 'run_command' == name:
			from agent_tools.worktree_guard import prohibited_worktree_shell_deletions
			viols = prohibited_worktree_shell_deletions(str(args.get('CommandLine') or ''))
			r = '; '.join(viols) if viols else None
		elif name in WorktreeIsolationGate.TOOLS:
			raw = args.get('Path') or args.get('path') or args.get('TargetFile') or ''
			if isinstance(raw, str) and raw.strip():
				cwd_val = (payload or {}).get('cwd')
				cwd = cwd_val if isinstance(cwd_val, str) else None
				repo_root = WorktreeIsolationGate.__governed_repo_for_path(raw, cwd)
				if None is not repo_root:
					from agent_tools.worktree_flow import is_linked_worktree
					if not is_linked_worktree(repo_root):
						r = WorktreeIsolationGate.__evaluate_main_checkout(name, repo_root, cwd)
		return r
