# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from pathlib import Path
from Df.Harness.Runtime.SettingsLoader import SettingsLoader
from Df.Harness.lib.ag_inputs import dfh_antigravity_paths, dfh_conversation_db_path, dfh_find_subagent_invocations, dfh_transcript_path
from Df.Harness.lib.ag_wire import dfh_configuration, dfh_generation_matches_executor, dfh_wire_fields, dfh_wire_path
from Df.Harness.lib.path_discovery import dfh_default_platform_paths
from Df.Harness.lib.runtime_context import dfh_platform_settings
from Df.Harness.lib.runtime_instances import dfh_platform_instances
from Df.Harness.lib.trace_common import dfh_open_readonly_sqlite, dfh_read_jsonl_objects
import hashlib
# 2026-11-26 "Move turn lifecycle subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/383
# @used-by :func:`_match_log_path_to_instance()`
def _load_ag_instances(cfg: dict, instances_fn) -> dict:
	if 'antigravity' not in cfg['platforms']:
		r: dict = {}
	elif None is not instances_fn:
		r = instances_fn('antigravity', include_disabled=True)
	else:
		r = dfh_platform_instances('antigravity', config=cfg, include_disabled=True)
	return r
# @used-by :func:`dfh_proof_paths()`
def _match_log_path_to_instance(log_path: Path, cid, *, settings_fn, instances_fn, default_paths_fn=dfh_default_platform_paths) -> dict:
	ag_insts = _load_ag_instances(settings_fn(), instances_fn)
	r: dict | None = None
	for inst in ag_insts.values():
		sp = inst['system_paths']
		for key in ('brain_dir', 'backend_dir'):
			path_str = sp.get(key)
			if path_str and log_path.is_relative_to(Path(path_str).resolve()):
				r = dfh_antigravity_paths(backend=sp.get('backend_dir'), instance=inst['id'], conversation_id=cid, settings_fn=settings_fn)
				break
		if None is not r:
			break
	if None is r:
		home_backend = Path(default_paths_fn('antigravity')['backend_dir']).resolve()
		if not log_path.is_relative_to(home_backend):
			raise ValueError('Saved Antigravity proof names an unconfigured or external log path')
		r = dfh_antigravity_paths(backend=home_backend, conversation_id=cid, settings_fn=settings_fn)
	return r
# @used-by :func:`dfh_model_metadata()`
def _read_model_table_rows(connection, path: Path, tables: set[str], history: dict, sources: list) -> None:
	for table, field_path, key in (('gen_metadata', (1, 19), 'generations'), ('executor_metadata', (10, 1, 28), 'configurations')):
		if table in tables and {'idx', 'data'}.issubset({row[1] for row in connection.execute('PRAGMA table_info(' + table + ')')}):
			for index, blob in connection.execute('SELECT idx,data FROM ' + table + ' ORDER BY idx'):
				values = dfh_wire_path(blob, field_path)
				history[key].extend(({'index': index, 'value': v} for v in values))
				if values:
					sources.append({'native_file': str(path), 'table': table, 'row': index, 'protobuf_path': list(field_path), 'sha256': hashlib.sha256(blob or b'').hexdigest()})
# @used-by :func:`dfh_model_metadata()`
def _read_step_model_history(connection, history: dict) -> None:
	if 'metadata' in {row[1] for row in connection.execute('PRAGMA table_info(steps)')}:
		for index, blob in connection.execute('SELECT idx,metadata FROM steps WHERE step_type=15 AND status IN (3,5) ORDER BY idx'):
			try:
				history['model_ids'].extend(({'step': index, 'value': value} for field, kind, value in dfh_wire_fields(blob or b'') if 11 == field and 0 == kind and value))
			except (ValueError, IndexError):
				pass
# @used-by :meth:`Df.Harness.Platform.Antigravity.ExecutorMetadataReader.ExecutorMetadataReader.__resolve_child_requested()`
# @used-by :meth:`Df.Harness.Platform.Antigravity.ExecutorMetadataReader.ExecutorMetadataReader.run()`
def dfh_apply_requested_config(requested: dict, observed: dict, raw_config, selection_kind: str, source) -> None:
	cfg = dfh_configuration(raw_config)
	gen_match = dfh_generation_matches_executor(observed['generation_model'], cfg['model'])
	requested.update(cfg, executor_model=cfg['model'], generation_model=observed['generation_model'] if gen_match else None, selection=selection_kind, source=source)
	if gen_match and observed['generation_model']:
		requested['model'] = observed['generation_model']
# @used-by :func:`agent_tools.meta.transcripts._resolve_ag_model_and_effort()`
# @used-by :meth:`Df.Harness.Platform.Antigravity.ExecutorMetadataReader.ExecutorMetadataReader.__resolve_child_requested()`
# @used-by :meth:`Df.Harness.Platform.Antigravity.ExecutorMetadataReader.ExecutorMetadataReader.run()`
def dfh_model_metadata(backend, conversation_id: str, *, paths=None) -> tuple[dict, dict, list]:
	path = dfh_conversation_db_path(backend, conversation_id, paths=paths)
	history: dict = {'generations': [], 'configurations': [], 'model_ids': []}
	sources: list = []
	with dfh_open_readonly_sqlite(path) as connection:
		tables = {row[0] for row in connection.execute("SELECT name FROM sqlite_master WHERE type='table'")}
		_read_model_table_rows(connection, path, tables, history, sources)
		_read_step_model_history(connection, history)
	generation = history['generations'][-1]['value'] if history['generations'] else None
	config = history['configurations'][-1]['value'] if history['configurations'] else None
	configured = dfh_configuration(config)
	return ({'model': generation, 'generation_model': generation, 'executor_model': configured['model'], 'effort': configured['effort'], 'configuration': config, 'model_ids': sorted({item['value'] for item in history['model_ids']})}, history, sources)
# @used-by :func:`agent_tools.platforms.antigravity._native_invocation()`
# @used-by :meth:`Df.Harness.Platform.Antigravity.ExecutorMetadataReader.ExecutorMetadataReader.__resolve_child_requested()`
def dfh_native_invocation(backend, parent_id: str, conversation_id: str, role: str, *, paths=None, platform_settings_fn=None, settings_fn=None) -> tuple[dict, dict]:
	load_cfg = settings_fn if None is not settings_fn else (lambda: SettingsLoader().run())
	ps_fn = platform_settings_fn if None is not platform_settings_fn else (lambda name: dfh_platform_settings(name, settings_fn=load_cfg))
	resolved = paths or dfh_antigravity_paths(backend=backend, conversation_id=conversation_id, settings_fn=load_cfg)
	brain_dir = Path(resolved['brain_dir'])
	child_log = dfh_transcript_path(brain_dir, conversation_id)
	parent_log = dfh_transcript_path(brain_dir, parent_id)
	initial = next((item.get('content', '') for item in dfh_read_jsonl_objects(child_log)), '')
	with dfh_open_readonly_sqlite(Path(resolved['conversations_db'])) as connection:
		row = connection.execute('SELECT parent_conversation_id,agent_name FROM conversation_summaries WHERE conversation_id=?', (conversation_id,)).fetchone()
	if None is row or row[0] != parent_id or row[1] != ps_fn('antigravity')['roles'][role]['agent']:
		raise ValueError('Native child relationship/role is not established')
	matches, _ = dfh_find_subagent_invocations(dfh_read_jsonl_objects(parent_log), conversation_id, row[1], initial)
	if not matches:
		raise ValueError('Matching native child invocation not established')
	exact_matches = [m for m in matches if m[2]]
	index, invocation = exact_matches[-1][:2] if exact_matches else matches[-1][:2]
	return (invocation, {'native_file': str(parent_log), 'step': index, 'kind': 'invoke_subagent'})
# @used-by :func:`agent_tools.platforms.antigravity._proof_paths()`
# @used-by :meth:`Df.Harness.Platform.Antigravity.ProofVerifier.ProofVerifier.run()`
def dfh_proof_paths(native, *, settings_fn=None, instances_fn=None, default_paths_fn=None) -> dict:
	if not isinstance(native, dict):
		raise ValueError('Native review proof must be a JSON object')
	load_cfg = settings_fn if None is not settings_fn else (lambda: SettingsLoader().run())
	cid = native.get('reviewer_id') or native.get('parent_id')
	if native.get('instance'):
		r = dfh_antigravity_paths(instance=native['instance'], conversation_id=cid, settings_fn=load_cfg)
	elif native.get('native_log'):
		dp_fn = default_paths_fn if None is not default_paths_fn else dfh_default_platform_paths
		r = _match_log_path_to_instance(Path(native['native_log']).resolve(), cid, settings_fn=load_cfg, instances_fn=instances_fn, default_paths_fn=dp_fn)
	else:
		r = dfh_antigravity_paths(conversation_id=cid, settings_fn=load_cfg)
	return r
# @used-by :meth:`Df.Harness.Platform.Antigravity.ReviewProver.ReviewProver.__build_extra_fields()`
def dfh_query_step_model_ids(backend, cid: str, *, step=None, paths=None) -> set:
	r: set = set()
	with dfh_open_readonly_sqlite(dfh_conversation_db_path(backend, cid, paths=paths)) as connection:
		if 'metadata' in {row[1] for row in connection.execute('PRAGMA table_info(steps)')}:
			sql = 'SELECT metadata FROM steps WHERE step_type=15 AND status IN (3,5)' + (' AND idx=?' if None is not step else '')
			for blob, in connection.execute(sql, (step,) if None is not step else ()).fetchall():
				try:
					r.update((value for field, kind, value in dfh_wire_fields(blob or b'') if 11 == field and 0 == kind and value))
				except (ValueError, IndexError):
					r = set()
					break
	return r
