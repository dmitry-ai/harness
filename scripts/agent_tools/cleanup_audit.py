# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo
# 2026-11-26 "Replace duplicated Harness logic with Df helpers": https://github.com/dmitry-ai/harness/issues/337
from Df.Core.lib.array.first import df_first
from Df.Core.lib.array.other.unique_fast import dfa_unique_fast
from Df.Core.lib.text.n.normalize import df_normalize
from .cli_common import read_input_bytes, verify_scratch_input_path
from .meta.builders import build_github_issue_metadata
from .meta.formatting import posix_path
from .meta.headers import render_metadata_header, strip_leading_metadata_header
from .path_registry import store_value, workspace_override
from .runtime import settings
from .storage import create_bytes
import hashlib
import json
# 2026-11-26
# "Persist cleanup audit manifests and metadata headers aligned with FILE-3":
# https://github.com/dmitry-ai/harness/issues/308
_ORDERED_META_KEYS = ('Time', 'Project', 'Journal', 'Agent', 'Trace')
# @used-by :func:`write_cleanup_manifest()`
def _build_manifest_payload(result: dict, now: datetime, timestamp: str, meta: dict[str, Any]) -> dict[str, Any]:
	projects = [e for e in result.get('projects') or () if isinstance(e, dict)]
	removed = [_extract_removed_record(e) for e in projects if 'removed' == e.get('status')]
	summary = [_project_summary_entry(e) for e in projects]
	base = {k: result.get(k) for k in ('mode', 'platform', 'cutoff', 'complete', 'active_instances', 'history_instances', 'skipped_disabled_instances', 'counts', 'discovery')}
	return {'schema_version': 1, 'timestamp': timestamp, 'recorded_at': now.isoformat(), **base, 'metadata': meta, 'removed_projects': removed, 'projects': summary, 'issues': result.get('issues') or []}
# @used-by :func:`_extract_removed_record()`
def _collect_instance_rollbacks(ag_val: dict) -> tuple[dict[str, dict], dict[str, dict]]:
	instances: dict[str, dict] = {}
	folder_snaps: dict[str, dict] = {}
	inst_map = ag_val.get('instances') if isinstance(ag_val.get('instances'), dict) else {'default': ag_val}
	for iid, rec in inst_map.items():
		if not isinstance(rec, dict):
			continue
		rb = rec.pop('rollback', None)
		rb_dict = rb if isinstance(rb, dict) else {}
		snaps = [{'id': p['id'], 'payload_base64': p['payload']} for p in rb_dict.get('projects') or () if isinstance(p, dict) and p.get('id') and p.get('payload')]
		instances[str(iid)] = {'project_ids': list(rec.get('removed_projects') or ()), 'snapshots': snaps}
		if rb_dict.get('folders') or rb_dict.get('assignments'):
			folder_snaps[str(iid)] = {'folders': list(rb_dict.get('folders') or ()), 'assignments': dict(rb_dict.get('assignments') or {})}
	return (instances, folder_snaps)
# @used-by :func:`record_cleanup_answer_log()`
# @used-by :func:`write_cleanup_manifest()`
def _create_unique_log_file(directory: Path, local: datetime, ext: str, payload: bytes, linked_fn) -> Path:
	if linked_fn(directory):
		raise ValueError('Cleanup log directory must not be linked')
	directory.mkdir(parents=True, exist_ok=True)
	number = 1
	while True:
		suffix = '' if 1 == number else f'--{number}'
		target = directory / f'{local:%d--%H-%M}{suffix}.{ext}'
		try:
			create_bytes(target, payload)
			break
		except FileExistsError:
			number += 1
	if target.read_bytes() != payload:
		raise OSError('Cleanup audit log read-back mismatch')
	return target
# @used-by :func:`_build_manifest_payload()`
def _extract_removed_record(entry: dict) -> dict[str, Any]:
	ag_val = entry.get('antigravity') if isinstance(entry.get('antigravity'), dict) else {}
	instances, folder_snaps = _collect_instance_rollbacks(ag_val) if ag_val else ({}, {})
	raw_ids = ag_val.get('removed_projects') or (entry.get('native_projects') or {}).get('antigravity') or ()
	# 2026-11-26 "Replace duplicated Harness logic with Df helpers": https://github.com/dmitry-ai/harness/issues/337
	project_ids = dfa_unique_fast([str(pid) for pid in raw_ids if pid])
	removed_folders = dfa_unique_fast([str(fid) for fid in (ag_val.get('removed_folders') or ()) if fid])
	return {
		'root': entry.get('root'),
		'job_id': entry.get('job_id'),
		'project_id': df_first(project_ids),
		'project_ids': project_ids,
		'instances': instances,
		'removed_folders': removed_folders,
		'folder_snapshots': folder_snaps,
		'created_at': entry.get('created_at'),
		'effective_activity_at': entry.get('effective_activity_at'),
		'age_basis': entry.get('age_basis'),
		'conversations': entry.get('conversations') or {},
	}
# @used-by :func:`record_cleanup_answer_log()`
def _find_recent_manifest(directory: Path, moment: datetime) -> Path | None:
	r: Path | None = None
	if directory.is_dir():
		cutoff = (moment - timedelta(minutes=15)).timestamp()
		cands = [p for p in directory.glob('*.json') if p.is_file() and p.stat().st_mtime >= cutoff]
		if cands:
			r = max(cands, key=lambda p: (p.stat().st_mtime_ns, p.name))
	return r
# @used-by :func:`record_cleanup_answer_log()`
# @used-by :func:`write_cleanup_manifest()`
def _istanbul_stamp(now: datetime | None) -> tuple[datetime, str]:
	moment = now or datetime.now(timezone.utc)
	if None is moment.tzinfo or None is moment.utcoffset():
		raise ValueError('Cleanup report time must include a timezone')
	local = moment.astimezone(ZoneInfo('Europe/Istanbul'))
	offset = int(local.utcoffset().total_seconds() / 60)
	hours, minutes = divmod(abs(offset), 60)
	zone = f"UTC{('+' if 0 <= offset else '-')}{hours}" + (f':{minutes:02d}' if minutes else '')
	return (local, f'{local:%Y-%m-%d %H:%M} {zone}')
# @used-by :func:`_build_manifest_payload()`
def _project_summary_entry(entry: dict) -> dict[str, Any]:
	r = {'root': entry.get('root'), 'job_id': entry.get('job_id'), 'status': entry.get('status'), 'created_at': entry.get('created_at'), 'effective_activity_at': entry.get('effective_activity_at'), 'age_basis': entry.get('age_basis'), 'conversations': entry.get('conversations') or {}}
	if entry.get('error'):
		r['error'] = entry['error']
	return r
# @used-by :func:`build_cleanup_metadata()`
def _resolve_meta_root(project_root: str | Path | None, config: dict | None) -> Path:
	if None is not project_root and str(project_root).strip():
		r = Path(project_root).resolve()
	elif isinstance(config, dict) and config.get('workspace_root'):
		r = Path(config['workspace_root']).resolve()
	else:
		r = Path.cwd().resolve()
	return r
# @used-by :func:`record_cleanup_answer_log()`
# @used-by :func:`write_cleanup_manifest()`
def build_cleanup_metadata(*, timestamp: str, project_root: str | Path | None=None, config: dict | None=None, manifest_path: str | Path | None=None, env: dict[str, str] | None=None) -> dict[str, Any]:
	eff_root = _resolve_meta_root(project_root, config)
	try:
		raw = build_github_issue_metadata(issue_url='', project_root=eff_root, env=env)
	except Exception:
		raw = {}
	raw.pop('Issue', None)
	raw['Time'] = timestamp
	if not isinstance(raw.get('Project'), dict) or (not str(raw['Project'].get('Path') or '').strip()):
		raw['Project'] = {'Name': eff_root.name or 'Workspace', 'Path': posix_path(eff_root)}
	if None is not manifest_path and str(manifest_path).strip():
		trace = dict(raw.get('Trace') or {}) if isinstance(raw.get('Trace'), dict) else {}
		trace['Cleanup Manifest'] = posix_path(Path(manifest_path).resolve())
		raw['Trace'] = trace
	return {k: raw[k] for k in _ORDERED_META_KEYS if k in raw and raw[k]}
# @used-by :meth:`agent_tools.cleanup.ProjectCleanupScanner.run()`
def maybe_write_cleanup_manifest(result: dict, *, apply: bool, now: datetime, config: dict, linked_fn, log_root=None, project_root=None, env=None) -> None:
	if apply:
		m_path = write_cleanup_manifest(result, now=now, config=config, linked_fn=linked_fn, log_root=log_root, project_root=project_root, env=env)
		result['audit_manifest'] = str(m_path)
# @used-by :func:`agent_tools.cleanup.record_cleanup_answer()`
def record_cleanup_answer_log(body, *, now=None, log_root=None, config=None, manifest_path=None, project_root=None, env=None, settings_fn=None, linked_fn=None) -> dict[str, Any]:
	if not isinstance(body, str) or (not body.strip()):
		raise ValueError('Cleanup answer must not be empty')
	local, timestamp = _istanbul_stamp(now)
	cfg = config if None is not config else (settings_fn() if None is not settings_fn else settings())
	directory = resolve_cleanup_log_root(config=cfg, log_root=log_root) / f'{local:%Y/%m}'
	eff_manifest = Path(manifest_path).resolve() if None is not manifest_path and str(manifest_path).strip() else _find_recent_manifest(directory, now or datetime.now(timezone.utc))
	# 2026-11-26 "Replace duplicated Harness logic with Df helpers": https://github.com/dmitry-ai/harness/issues/337
	clean_body = strip_leading_metadata_header(df_normalize(body))
	meta = build_cleanup_metadata(timestamp=timestamp, project_root=project_root, config=cfg, manifest_path=eff_manifest, env=env)
	payload = (render_metadata_header(meta) + clean_body).encode('utf-8')
	target = _create_unique_log_file(directory, local, 'md', payload, linked_fn or (lambda _p: False))
	m_str = posix_path(eff_manifest) if None is not eff_manifest else None
	return {'path': str(target), 'timestamp': timestamp, 'metadata': meta, 'manifest': m_str, 'answer': clean_body, 'log_sha256': hashlib.sha256(payload).hexdigest(), 'body_sha256': hashlib.sha256(clean_body.encode('utf-8')).hexdigest()}
# @used-by :func:`record_cleanup_answer_log()`
# @used-by :func:`write_cleanup_manifest()`
def resolve_cleanup_log_root(*, config: dict | None=None, log_root: str | Path | None=None) -> Path:
	if None is not log_root and str(log_root).strip():
		r = Path(log_root).absolute()
	else:
		cfg = config if None is not config else settings()
		ws = Path(cfg['workspace_root']).resolve()
		ovr_log = workspace_override(ws, 'cleanup_log_dir')
		default_log = Path(ovr_log) if ovr_log else ws / str(store_value('workspace_cleanup_log_rel'))
		r = default_log.absolute()
	return r
# @used-by :func:`agent_tools.upwork_project.run()`
def run_cleanup_report_cli(args) -> dict[str, Any]:
	from . import cleanup
	source_path = getattr(args, 'answer_file', None) or getattr(args, 'answer', '-')
	proj_raw = getattr(args, 'project', None)
	proj_root = Path(proj_raw).resolve() if None is not proj_raw and str(proj_raw).strip() else Path.cwd().resolve()
	consume = bool(getattr(args, 'consume_input', False)) and '-' != str(source_path)
	target_scratch = verify_scratch_input_path(proj_root, source_path) if consume else None
	raw_bytes = read_input_bytes(source_path)
	res = cleanup.record_cleanup_answer(raw_bytes.decode('utf-8'), manifest_path=getattr(args, 'manifest', None), project_root=proj_root)
	if None is not target_scratch and target_scratch.exists() and target_scratch.read_bytes() == raw_bytes:
		target_scratch.unlink()
		res['consumed_input'] = str(target_scratch)
	return res
# @used-by :func:`maybe_write_cleanup_manifest()`
def write_cleanup_manifest(result: dict, *, now: datetime, config: dict, linked_fn, log_root=None, project_root=None, env=None) -> Path:
	local, timestamp = _istanbul_stamp(now)
	meta = build_cleanup_metadata(timestamp=timestamp, project_root=project_root, config=config, env=env)
	manifest = _build_manifest_payload(result, now, timestamp, meta)
	payload = (json.dumps(manifest, ensure_ascii=False, indent='\t') + '\n').encode('utf-8')
	root = resolve_cleanup_log_root(config=config, log_root=log_root)
	return _create_unique_log_file(root / f'{local:%Y/%m}', local, 'json', payload, linked_fn)
