# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from datetime import datetime, timezone
from pathlib import Path
from .journal import iter_side_step_files, journal_pair_dirs
from .meta.formatting import parse_timestamp
from .meta.headers import extract_leading_metadata_header
from .path_registry import default_platform_paths
from .platforms.trace_common import open_readonly_sqlite
from .runtime import platform_adapter_name, platform_instances
import glob
import json
import sqlite3
# 2026-11-26
# "Compute upwork-cleanup age from lifecycle activity and scan disabled history stores":
# https://github.com/dmitry-ai/harness/issues/307
_DELIVERABLE_DIRS = ('result', 'Letters', '\u2c0f/\u227b/\u2655/\U0001f582', '\u2c0f/\u227a/\U0001f582')
_LEGACY_JOURNAL_SUBS = ('1 - Analysis', '1 - \u0410\u043d\u0430\u043b\u0438\u0437')
# @used-by :func:`effective_project_activity()`
def _best_activity(candidates_list: list[tuple[datetime | None, str]], base_dt: datetime, base_basis: str) -> tuple[datetime, str]:
	best_dt, best_basis = (base_dt, base_basis)
	for cand_dt, cand_basis in candidates_list:
		if None is not cand_dt and cand_dt > best_dt:
			best_dt, best_basis = (cand_dt, cand_basis)
	return (best_dt, best_basis)
# @used-by :func:`effective_project_activity()`
def _collect_handoff_activity(root: Path, state: dict, config: dict, path_key_fn) -> datetime | None:
	keys = set(project_canonical_keys(root, path_key_fn))
	job_id = str(state.get('job_id') or '').strip()
	best: datetime | None = None
	for t_dir in _launcher_turn_dirs(root, config):
		for tf in sorted(t_dir.glob('*.json')):
			if '-' in tf.stem:
				continue
			data = _safe_json_dict(tf)
			if None is not data and _turn_matches_project(data, keys, job_id, path_key_fn):
				cand = _parse_iso_dt(data.get('updated_at')) or _parse_iso_dt(data.get('created_at'))
				if None is not cand and (None is best or cand > best):
					best = cand
	return best
# @used-by :func:`effective_project_activity()`
def _collect_rename_activity(state: dict) -> datetime | None:
	best: datetime | None = None
	for item in state.get('renamed_from') or ():
		if isinstance(item, dict):
			cand = _parse_iso_dt(item.get('at'))
			if None is not cand and (None is best or cand > best):
				best = cand
	return best
# @used-by :func:`effective_project_activity()`
def _collect_workflow_finalize(root: Path) -> datetime | None:
	data = _safe_json_dict(root / '\ua616/data/workflow.json')
	stages = data.get('stages') if isinstance(data, dict) else None
	fin = stages.get('finalize') if isinstance(stages, dict) else None
	return _parse_iso_dt(fin.get('time')) if isinstance(fin, dict) else None
# @used-by :func:`count_project_conversations()`
def _count_ag_conversations(ag_projects, ag_rows, rec_ag_ids: dict[str, set[str]], keys: list[str], belongs_fn, key_cache: dict) -> dict[str, int]:
	r: dict[str, int] = {}
	if isinstance(ag_projects, dict):
		total = 0
		rows_map = ag_rows if isinstance(ag_rows, dict) else {}
		for iid in list(dict.fromkeys([*ag_projects, *rows_map])):
			ag_ids = {p['id'] for p in ag_projects.get(iid, ())} | rec_ag_ids.get(iid, set())
			cnt = sum((proj_id in ag_ids or any((_matches_any_key(uri, keys, belongs_fn, key_cache) for uri in uris)) for proj_id, uris in rows_map.get(iid, ())))
			r['antigravity:' + iid] = cnt
			total += cnt
		if ag_projects or rows_map:
			r['antigravity'] = total
	else:
		ag_ids = {p['id'] for p in ag_projects} | rec_ag_ids.get('*', set())
		r['antigravity'] = sum((proj_id in ag_ids or any((_matches_any_key(uri, keys, belongs_fn, key_cache) for uri in uris)) for proj_id, uris in ag_rows))
	return r
# @used-by :func:`count_project_conversations()`
def _count_codex_conversations(homes: dict, catalog: list, codex_rows: dict, rec_cx_ids: dict[str, set[str]], keys: list[str], belongs_fn, key_cache: dict) -> dict[str, int]:
	r: dict[str, int] = {}
	for profile in list(dict.fromkeys([*homes, *codex_rows])):
		cx_ids = ({p['bindings'][profile] for p in catalog} if profile in homes else set()) | rec_cx_ids.get(profile, set())
		r['codex:' + profile] = len({tid for tid, proj_id, cwd in codex_rows.get(profile, ()) if proj_id in cx_ids or _matches_any_key(cwd, keys, belongs_fn, key_cache)})
	return r
# @used-by :func:`count_post_init_work()`
def _deliverable_file_count(root: Path) -> int:
	total = 0
	for rel in _DELIVERABLE_DIRS:
		d_path = root / rel
		if d_path.is_dir():
			total += sum((1 for f in d_path.rglob('*') if f.is_file() and 0 < f.stat().st_size))
	return total
# @used-by :func:`resolve_readonly_history()`
def _disabled_ag_history(config: dict, daily: Path, active_ag: dict) -> dict[str, tuple[Path, bool, Path]]:
	r: dict[str, tuple[Path, bool, Path]] = {}
	for pid, pcfg in (config.get('platforms') or {}).items():
		if not isinstance(pcfg, dict) or 'antigravity' != platform_adapter_name(pid, pcfg):
			continue
		for iid, inst in platform_instances(pid, config=config, include_disabled=True).items():
			if iid in active_ag or inst.get('enabled'):
				continue
			entry = _probe_disabled_ag_db(inst, daily)
			if None is not entry:
				r[iid] = entry
	return r
# @used-by :func:`resolve_readonly_history()`
def _disabled_codex_history(config: dict, daily: Path, active_homes: dict) -> tuple[dict[str, Path | None], dict[str, str]]:
	homes: dict[str, Path | None] = {}
	globs: dict[str, str] = {}
	for pid, pcfg in (config.get('platforms') or {}).items():
		if not isinstance(pcfg, dict) or 'codex' != platform_adapter_name(pid, pcfg):
			continue
		for iid, inst in platform_instances(pid, config=config, include_disabled=True).items():
			if iid in active_homes or inst.get('enabled'):
				continue
			home = Path(inst['home']) if inst.get('home') else None
			glob_raw = (inst.get('system_paths') or {}).get('state_db_glob')
			dbs = resolve_codex_state_dbs(home, glob_raw)
			if dbs and (not any(((not p.is_symlink()) and p.resolve().is_relative_to(daily) for p in dbs))):
				homes[iid] = home
				if glob_raw:
					globs[iid] = glob_raw
	return (homes, globs)
# @used-by :func:`_recorded_native_ids()`
def _extract_nested_project_ids(section, map_key: str) -> dict[str, set[str]]:
	r: dict[str, set[str]] = {}
	mapping = section.get(map_key) if isinstance(section, dict) else None
	if isinstance(mapping, dict):
		for key, rec in mapping.items():
			if isinstance(rec, dict) and rec.get('project_id'):
				r.setdefault(str(key), set()).add(str(rec['project_id']))
	return r
# @used-by :func:`_journal_pair_activity()`
def _journal_dirs_for_project(root: Path) -> list[Path]:
	j_root = root / '\ua66e'
	r: list[Path] = []
	if j_root.is_dir():
		r.append(j_root)
		for sub in _LEGACY_JOURNAL_SUBS:
			cand = j_root / sub
			if cand.is_dir():
				r.append(cand)
	return r
# @used-by :func:`count_post_init_work()`
# @used-by :func:`effective_project_activity()`
def _journal_pair_activity(root: Path) -> tuple[datetime | None, int]:
	best: datetime | None = None
	steps: set[int] = set()
	for jdir in _journal_dirs_for_project(root):
		try:
			req_dir, res_dir = journal_pair_dirs(jdir)
			req_map = dict(iter_side_step_files(req_dir))
			res_map = dict(iter_side_step_files(res_dir))
		except (OSError, ValueError):
			continue
		for st in sorted(set(req_map) & set(res_map)):
			steps.add(st)
			cand = _step_response_time(res_map[st])
			if None is not cand and (None is best or cand > best):
				best = cand
	return (best, len(steps))
# @used-by :func:`_collect_handoff_activity()`
def _launcher_turn_dirs(root: Path, config: dict) -> list[Path]:
	cands: list[Path] = [root / '\ua616/data/turns']
	ws_raw = config.get('workspace_root') if isinstance(config, dict) else None
	if ws_raw:
		cands.append(Path(ws_raw) / 'proposals/init/\ua616/data/turns')
	if 4 <= len(root.parents):
		cands.append(root.parents[3].parent / 'init/\ua616/data/turns')
	seen: set[str] = set()
	r: list[Path] = []
	for d in cands:
		if d.is_dir():
			key = str(d.resolve()).casefold()
			if key not in seen:
				seen.add(key)
				r.append(d)
	return r
# @used-by :func:`_count_ag_conversations()`
# @used-by :func:`_count_codex_conversations()`
def _matches_any_key(raw_path, keys: list[str], belongs_fn, key_cache: dict) -> bool:
	return any((belongs_fn(raw_path, wanted, wanted + '/', key_cache) for wanted in keys))
# @used-by :func:`_collect_handoff_activity()`
# @used-by :func:`_collect_rename_activity()`
# @used-by :func:`_collect_workflow_finalize()`
def _parse_iso_dt(raw) -> datetime | None:
	r: datetime | None = None
	if isinstance(raw, str) and raw.strip():
		try:
			dt = datetime.fromisoformat(raw.strip().replace('Z', '+00:00'))
			r = dt if None is not dt.tzinfo else None
		except ValueError:
			r = None
	return r
# @used-by :func:`_disabled_ag_history()`
def _probe_disabled_ag_db(inst: dict, daily: Path) -> tuple[Path, bool, Path] | None:
	sp = inst.get('system_paths') or {}
	home_dir = Path(inst['home']).absolute() if inst.get('home') else None
	home_ag = default_platform_paths('antigravity', home=home_dir) if None is not home_dir else {}
	b_raw = sp.get('backend_dir') or home_ag.get('backend_dir')
	b_dir = Path(b_raw).absolute() if b_raw else None
	db_raw = sp.get('conversations_db')
	conv_db = Path(db_raw).absolute() if db_raw else (b_dir / 'conversation_summaries.db' if None is not b_dir else None)
	r: tuple[Path, bool, Path] | None = None
	if None is not conv_db and (conv_db.is_file() or conv_db.is_symlink()):
		if conv_db.is_symlink() or (not conv_db.resolve().is_relative_to(daily)):
			r = (b_dir or conv_db.parent, False, conv_db)
	return r
# @used-by :func:`count_project_conversations()`
def _recorded_native_ids(root: Path) -> tuple[dict[str, set[str]], dict[str, set[str]]]:
	data = _safe_json_dict(root / '\ua616/data/registrations.json') or {}
	ag_sec = data.get('antigravity')
	ag_ids = _extract_nested_project_ids(ag_sec, 'instances')
	if isinstance(ag_sec, dict) and ag_sec.get('project_id'):
		ag_ids.setdefault('*', set()).add(str(ag_sec['project_id']))
	cx_ids = _extract_nested_project_ids(data.get('codex'), 'profiles')
	return (ag_ids, cx_ids)
# @used-by :func:`_collect_handoff_activity()`
# @used-by :func:`_collect_workflow_finalize()`
# @used-by :func:`_recorded_native_ids()`
# @used-by :func:`project_canonical_keys()`
def _safe_json_dict(path: Path) -> dict | None:
	r: dict | None = None
	if path.is_file() and (not path.is_symlink()):
		try:
			parsed = json.loads(path.read_text(encoding='utf-8-sig'))
			r = parsed if isinstance(parsed, dict) else None
		except (OSError, ValueError):
			r = None
	return r
# @used-by :func:`_journal_pair_activity()`
def _step_response_time(res_path: Path) -> datetime | None:
	r: datetime | None = None
	try:
		meta, _ = extract_leading_metadata_header(res_path.read_text(encoding='utf-8', errors='replace'))
		t_obj = meta.get('Time') if isinstance(meta, dict) else None
		raw_ts = t_obj.get('Response') if isinstance(t_obj, dict) else (t_obj if isinstance(t_obj, str) else None)
		r = parse_timestamp(raw_ts) if raw_ts else None
		if None is r:
			r = datetime.fromtimestamp(res_path.stat().st_mtime, timezone.utc)
	except OSError:
		r = None
	return r
# @used-by :func:`_collect_handoff_activity()`
def _turn_matches_project(data: dict, keys: set[str], job_id: str, path_key_fn) -> bool:
	ho = data.get('handed_off_to') if isinstance(data.get('handed_off_to'), dict) else {}
	ho_root = str(ho.get('project_root') or '').strip()
	p_root = str(data.get('project_root') or '').strip()
	matched = bool(job_id and ho.get('job_id') == job_id)
	for raw in (ho_root, p_root):
		if raw and (not matched):
			try:
				matched = path_key_fn(raw) in keys
			except ValueError:
				matched = False
	return matched
# @used-by :func:`count_project_conversations()`
def count_post_init_work(root: Path) -> int:
	r = 0
	if isinstance(root, Path) and root.is_dir():
		deliverables = _deliverable_file_count(root)
		_, pair_count = _journal_pair_activity(root)
		r = deliverables + max(0, pair_count - 1)
	return r
# @used-by :func:`agent_tools.cleanup._count_indexed_conversations()`
def count_project_conversations(root, ag_projects, homes, catalog, index, path_key_fn, belongs_fn) -> dict[str, int]:
	ag_rows, codex_rows, key_cache = index
	keys = project_canonical_keys(root, path_key_fn)
	rec_ag, rec_cx = _recorded_native_ids(Path(root)) if isinstance(root, (str, Path)) else ({}, {})
	r = _count_ag_conversations(ag_projects, ag_rows, rec_ag, keys, belongs_fn, key_cache)
	r.update(_count_codex_conversations(homes, catalog, codex_rows, rec_cx, keys, belongs_fn, key_cache))
	post_work = count_post_init_work(Path(root)) if isinstance(root, (str, Path)) else 0
	if 0 < post_work:
		r['post_init_work'] = post_work
	return r
# @used-by :func:`agent_tools.cleanup._age()`
def effective_project_activity(root, state: dict, config: dict, base_dt: datetime, base_basis: str, path_key_fn) -> tuple[datetime, str]:
	if not isinstance(root, Path) or (not root.exists()):
		r = (base_dt, base_basis)
	else:
		jrn_dt, _ = _journal_pair_activity(root)
		cands = [
			(_collect_workflow_finalize(root), 'workflow.finalize'),
			(_collect_rename_activity(state), 'project.renamed_from'),
			(_collect_handoff_activity(root, state, config, path_key_fn), 'handed_off_conversation'),
			(jrn_dt, 'journal.latest_pair'),
		]
		r = _best_activity(cands, base_dt, base_basis)
	return r
# @used-by :func:`agent_tools.cleanup._load_conversation_index()`
def load_codex_history_rows(homes: dict, globs: dict, guard_fn) -> dict[str, list]:
	r: dict[str, list] = {}
	for profile, home in homes.items():
		databases = resolve_codex_state_dbs(home, globs.get(profile))
		if not databases:
			raise ValueError(f'Native Codex history unavailable: {profile}')
		p_rows = []
		for database in databases:
			with open_readonly_sqlite(database, guard=guard_fn, query_only=True, row_factory=sqlite3.Row, timeout=5) as conn:
				p_rows.extend(((row['id'], row['project_id'], row['cwd']) for row in conn.execute('SELECT id, project_id, cwd FROM threads')))
		r[profile] = p_rows
	return r
# @used-by :func:`_collect_handoff_activity()`
# @used-by :func:`count_project_conversations()`
def project_canonical_keys(root, path_key_fn) -> list[str]:
	keys = [path_key_fn(root)]
	if isinstance(root, (str, Path)):
		data = _safe_json_dict(Path(root) / '\ua616/project.json')
		for item in (data.get('renamed_from') or ()) if isinstance(data, dict) else ():
			if isinstance(item, dict) and item.get('from'):
				try:
					key = path_key_fn(str(item['from']))
					if key not in keys:
						keys.append(key)
				except ValueError:
					continue
	return keys
# @used-by :func:`_disabled_codex_history()`
# @used-by :func:`load_codex_history_rows()`
def resolve_codex_state_dbs(home: Path | None, glob_raw: str | None) -> list[Path]:
	if glob_raw:
		pattern = glob_raw if Path(glob_raw).is_absolute() else ((Path(home) / glob_raw).as_posix() if None is not home else '')
		r = sorted((Path(p) for p in glob.glob(pattern, recursive=True) if Path(p).is_file() or Path(p).is_symlink())) if pattern else []
	elif None is not home and Path(home).exists():
		r = sorted((p for p in Path(home).glob('state_*.sqlite') if p.is_file() or p.is_symlink()))
	else:
		r = []
	return r
# @used-by :meth:`agent_tools.cleanup.ProjectCleanupScanner.__init__()`
def resolve_readonly_history(config: dict, daily: Path, active_ag: dict, active_homes: dict, *, single_ag_mode: bool=False) -> dict:
	platforms_cfg = config.get('platforms') or {}
	skipped: dict[str, list[str]] = {}
	for plat_id in platforms_cfg:
		disabled_ids = [iid for iid, v in platform_instances(plat_id, config=config, include_disabled=True).items() if not v['enabled']]
		if disabled_ids:
			skipped[plat_id] = disabled_ids
	ro_ag = {} if single_ag_mode else _disabled_ag_history(config, daily, active_ag)
	ro_cx, ro_globs = _disabled_codex_history(config, daily, active_homes)
	return {
		'ag_backend': ro_ag,
		'codex_globs': ro_globs,
		'codex_homes': ro_cx,
		'history_instances': {'antigravity': [*active_ag, *ro_ag], 'codex': [*active_homes, *ro_cx]},
		'skipped_disabled': skipped,
	}
