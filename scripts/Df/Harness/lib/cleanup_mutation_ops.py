# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from pathlib import Path
from Df.Harness.lib.cleanup_store_ops import dfh_antigravity_projects, dfh_linked, dfh_path_key, dfh_read_store_json
from Df.Harness.lib.storage import dfh_create_bytes, dfh_locked, dfh_replace_bytes
from agent_tools.research import json_data
import base64
import json
# 2026-11-26 "Move turn lifecycle subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/383
# @used-by :func:`dfh_remove_antigravity()`
def _commit_pruned_folders(folders: Path, before: bytes, value: dict, check, *, replace_bytes_fn) -> None:
	check()
	if folders.read_bytes() != before:
		raise ValueError('Folders changed after native deletion; retry cleanup')
	payload = json_data(value)
	replace_bytes_fn(folders, payload)
	if folders.read_bytes() != payload:
		raise ValueError('Folders did not confirm cleanup; retry')
# @used-by :func:`dfh_prune_folders()`
def _drop_empty_folders(by_id: dict, assignments: dict, affected: set[str]) -> list[str]:
	r: list[str] = []
	while True:
		empty = {ident for ident in affected if ident in by_id and ident not in assignments.values() and (not any((n.get('parentId') == ident for n in by_id.values())))}
		if not empty:
			break
		for ident in empty:
			r.append(ident)
			del by_id[ident]
	return r
# @used-by :func:`dfh_restore_antigravity()`
def _restore_pending_files(directory: Path, root, *, create_bytes_fn) -> list[str]:
	restored: list[str] = []
	for project in dfh_antigravity_projects(directory, root):
		if None is project['sha']:
			target = Path(project['file'])
			if dfh_linked(target) or target.parent.resolve() != directory.resolve():
				raise ValueError('Unsafe Antigravity restoration path')
			create_bytes_fn(target, project['restore'])
			restored.append(project['id'])
	return restored
# @used-by :func:`dfh_restore_antigravity()`
def _restore_pending_folders(folders: Path, pending: dict, *, replace_bytes_fn) -> None:
	before = folders.read_bytes()
	value = dfh_read_store_json(folders)
	ids = {n['id'] for n in value['folders']}
	for node in pending['folders']:
		if node['id'] not in ids:
			value['folders'].append(node)
			ids.add(node['id'])
	for ident, folder in pending['assignments'].items():
		value['projectFolderMap'].setdefault(ident, folder)
	if any((folder not in ids for folder in value['projectFolderMap'].values())) or any((None is not n.get('parentId') and n['parentId'] not in ids for n in value['folders'])):
		raise ValueError('Restored Folders ancestry is incomplete')
	if folders.read_bytes() != before:
		raise ValueError('Folders changed during restoration')
	replace_bytes_fn(folders, json_data(value))
# @used-by :func:`dfh_remove_antigravity()`
def _save_pending_snapshot(directory: Path, root, original: dict, current: list[dict], *, replace_bytes_fn) -> dict:
	pending_file = directory / '\ua616/data/cleanup-pending.json'
	pending = dfh_read_store_json(pending_file) if pending_file.exists() else {}
	ancestry = dfh_collect_folder_ancestors({node['id']: node for node in original['folders']}, original['projectFolderMap'], (p['id'] for p in current), 'Invalid pending Folders ancestry')
	snapshot = pending.setdefault(dfh_path_key(root), {'projects': [{'id': p['id'], 'payload': base64.b64encode(p['sha'] if None is not p['sha'] else p['restore']).decode('ascii')} for p in current], 'folders': [node for node in original['folders'] if node['id'] in ancestry], 'assignments': {p['id']: original['projectFolderMap'][p['id']] for p in current if p['id'] in original['projectFolderMap']}})
	replace_bytes_fn(pending_file, json_data(pending))
	return snapshot
# @used-by :func:`dfh_remove_antigravity()`
def _unlink_ag_projects(directory: Path, current: list[dict], check) -> list[str]:
	removed: list[str] = []
	for project in current:
		path = Path(project['file'])
		actual = path.read_bytes() if path.exists() else None
		if path.parent.resolve() != directory.resolve() or dfh_linked(path) or actual != project['sha']:
			raise ValueError('Native project changed before removal')
		check()
		if dfh_linked(path) or (path.read_bytes() if path.exists() else None) != project['sha']:
			raise ValueError('Native project changed during the final conversation check')
		if None is not actual:
			path.unlink()
		removed.append(project['id'])
	return removed
# @used-by :func:`_save_pending_snapshot()`
# @used-by :func:`dfh_prune_folders()`
def dfh_collect_folder_ancestors(by_id, assignments, project_ids, error_msg) -> set[str]:
	r: set[str] = set()
	for ident in project_ids:
		folder = assignments.get(ident)
		seen: set[str] = set()
		while None is not folder:
			if folder in seen or folder not in by_id:
				raise ValueError(error_msg)
			seen.add(folder)
			r.add(folder)
			folder = by_id[folder].get('parentId')
	return r
# @used-by :func:`agent_tools.cleanup._finish_pending()`
# @used-by :func:`dfh_restore_antigravity()`
# @used-by :meth:`Df.Harness.Cleanup.Scanner.Scanner.__finalize_removal()`
def dfh_finish_pending(directory: Path, root, *, replace_bytes_fn=dfh_replace_bytes) -> None:
	path = directory / '\ua616/data/cleanup-pending.json'
	if path.exists():
		pending = dfh_read_store_json(path)
		pending.pop(dfh_path_key(root), None)
		if not pending:
			path.unlink()
		else:
			replace_bytes_fn(path, json_data(pending))
# @used-by :func:`agent_tools.cleanup.prune_folders()`
# @used-by :func:`dfh_remove_antigravity()`
def dfh_prune_folders(value: dict, removed_ids) -> list[str]:
	nodes, assignments = (value['folders'], value['projectFolderMap'])
	if not isinstance(nodes, list) or (not isinstance(assignments, dict)):
		raise ValueError('Invalid Folders store')
	by_id = {node['id']: node for node in nodes}
	if len(by_id) != len(nodes):
		raise ValueError('Duplicate Folders identities')
	affected = dfh_collect_folder_ancestors(by_id, assignments, removed_ids, 'Broken Folders ancestry')
	for ident in removed_ids:
		assignments.pop(ident, None)
	r = _drop_empty_folders(by_id, assignments, affected)
	value['folders'] = [n for n in nodes if n['id'] in by_id]
	for key in ('collapsedFolders', 'collapsedFolderIds'):
		if key in value:
			value[key] = [ident for ident in value[key] if ident not in r]
	return r
# @used-by :func:`agent_tools.cleanup.remove_antigravity()`
# @used-by :meth:`Df.Harness.Cleanup.Scanner.Scanner.__apply_ag_removal()`
def dfh_remove_antigravity(root, directory: Path, folders: Path, expected: list[dict], check, *, replace_bytes_fn=dfh_replace_bytes) -> dict:
	with dfh_locked(directory / '\ua616/data/registration.lock'):
		check()
		current = dfh_antigravity_projects(directory, root)
		if [(p['id'], p['sha']) for p in current] != [(p['id'], p['sha']) for p in expected]:
			raise ValueError('Antigravity registration changed; retry cleanup')
		before = folders.read_bytes()
		value = dfh_read_store_json(folders)
		original = json.loads(before.decode('utf-8-sig'))
		pruned = dfh_prune_folders(value, [p['id'] for p in current])
		if folders.read_bytes() != before:
			raise ValueError('Folders changed; retry cleanup')
		snapshot = _save_pending_snapshot(directory, root, original, current, replace_bytes_fn=replace_bytes_fn)
		removed = _unlink_ag_projects(directory, current, check)
		_commit_pruned_folders(folders, before, value, check, replace_bytes_fn=replace_bytes_fn)
		r = {'complete': True, 'removed_projects': removed, 'removed_folders': pruned, 'awaiting_commit': True, 'rollback': snapshot}
	return r
# @used-by :func:`agent_tools.cleanup.restore_antigravity()`
# @used-by :meth:`Df.Harness.Cleanup.Scanner.Scanner.__recover_ag()`
def dfh_restore_antigravity(root, directory: Path, folders: Path, *, create_bytes_fn=dfh_create_bytes, replace_bytes_fn=dfh_replace_bytes) -> dict:
	with dfh_locked(directory / '\ua616/data/registration.lock'):
		path = directory / '\ua616/data/cleanup-pending.json'
		pending = dfh_read_store_json(path).get(dfh_path_key(root)) if path.exists() else None
		if not pending:
			r = {'complete': True, 'restored_projects': []}
		else:
			restored = _restore_pending_files(directory, root, create_bytes_fn=create_bytes_fn)
			_restore_pending_folders(folders, pending, replace_bytes_fn=replace_bytes_fn)
			dfh_finish_pending(directory, root, replace_bytes_fn=replace_bytes_fn)
			r = {'complete': True, 'restored_projects': restored}
	return r
