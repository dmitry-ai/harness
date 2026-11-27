# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from datetime import date
from pathlib import Path
from typing import Any
from Df.Harness.Runtime.SettingsLoader import SettingsLoader
from Df.Harness.lib.ag_daemon import dfh_project_item_matches_root, dfh_resolve_folders_json
from Df.Harness.lib.path_discovery import dfh_default_platform_paths
from Df.Harness.lib.path_resolve import dfh_project_paths
from Df.Harness.lib.runtime_context import dfh_request_day
from Df.Harness.lib.runtime_instances import dfh_platform_instances
from Df.Harness.lib.storage import dfh_create_bytes, dfh_locked, dfh_replace_bytes
from agent_tools.knowledge import json_bytes
import json
import uuid
# 2026-11-26 "Move turn lifecycle subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/383
class ProjectRegistrar:
	# @used-by :func:`agent_tools.platforms.antigravity.register()`
	# @used-by :func:`agent_tools.platforms.antigravity.register_antigravity_project()`
	# @used-by :meth:`test_df_harness_s11_wave2d_platform_cov.DfHarnessS11Wave2dPlatformCovTests.test_ag_and_codex_registrars_verifiers_and_title_sync()`
	def __init__(self, project_dir, domain_or_topic: str, date_str=None, *, projects_dir=None, folders_json_path=None, preferred_id: str | None=None, multi_instance: bool=False, _ops: dict[str, Any] | None=None) -> None:
		self.__project_dir = project_dir
		self.__domain_or_topic = domain_or_topic
		self.__date_str = date_str
		self.__projects_dir = projects_dir
		self.__folders_json_path = folders_json_path
		self.__preferred_id = preferred_id
		self.__multi_instance = multi_instance
		self.__ops = _ops or {}
	# @used-by :meth:`ProjectRegistrar.__register_single()`
	def __ensure_folder_branch(self, nodes: list, day: date) -> tuple[str, tuple[str, ...]]:
		branch = ('Upwork', 'Proposals', f'{day.year:04d}', f'{day.month:02d}', f'{day.day:02d}')
		parent = None
		for part in branch:
			node = next((x for x in nodes if x['name'].casefold() == part.casefold() and x.get('parentId') == parent), None)
			if None is node:
				node = {'id': f'folder-{uuid.uuid4().hex[:16]}', 'name': part, 'parentId': parent, 'color': '#10b981', 'isExpanded': True}
				nodes.append(node)
			parent = node['id']
		return (parent, branch)
	# @used-by :meth:`ProjectRegistrar.__register_multi()`
	def __find_preferred_id(self, ordered: list, root: Path) -> str | None:
		r: str | None = None
		for _, inst in ordered:
			p_dir = Path(inst['system_paths']['projects_dir'])
			if p_dir.is_dir():
				for path in sorted(p_dir.glob('*.json')):
					item = json.loads(path.read_text(encoding='utf-8-sig'))
					if dfh_project_item_matches_root(item, root)[0]:
						r = item.get('id') or path.stem
						break
			if r:
				break
		return r
	# @used-by :meth:`ProjectRegistrar.run()`
	def __register_multi(self) -> dict[str, Any]:
		load_cfg = self.__ops.get('settings') or (lambda: SettingsLoader().run())
		inst_fn = self.__ops.get('platform_instances') or (lambda p, **kw: dfh_platform_instances(p, config=load_cfg(), **kw))
		insts = inst_fn('antigravity', include_disabled=False)
		if not insts:
			raise ValueError('Antigravity has no enabled instances in runtime.json')
		ordered = sorted(insts.items(), key=lambda kv: (0 if kv[1].get('primary') else 1, kv[0]))
		preferred_id = self.__find_preferred_id(ordered, Path(self.__project_dir).resolve())
		per_instance, primary_receipt = ({}, None)
		for iid, inst in ordered:
			sp = inst['system_paths']
			folders_target = self.__resolve_folders(sp=sp)
			receipt = self.__register_single(Path(sp['projects_dir']), folders_target, preferred_id)
			preferred_id = preferred_id or receipt['project_id']
			per_instance[iid] = receipt
			if None is primary_receipt:
				primary_receipt = receipt
		return {**primary_receipt, 'instances': per_instance}
	# @used-by :meth:`ProjectRegistrar.__register_multi()`
	# @used-by :meth:`ProjectRegistrar.run()`
	def __register_single(self, projects_dir: Path, folders_json_path, preferred_id: str | None) -> dict[str, Any]:
		root = Path(self.__project_dir).resolve()
		day = self.__resolve_day(root)
		name = f'{self.__domain_or_topic} - U.P.{day:%Y.%m.%d}'
		with dfh_locked(projects_dir / '\ua616/data/registration.lock'):
			folders = self.__resolve_folders(folders_json_path)
			before = folders.read_bytes()
			listing = json.loads(before.decode('utf-8-sig'))
			nodes, assignments = (listing.get('folders'), listing.get('projectFolderMap'))
			if not isinstance(nodes, list) or (not isinstance(assignments, dict)):
				raise ValueError('Folders requires folders[] and projectFolderMap{}')
			parent, branch = self.__ensure_folder_branch(nodes, day)
			ident, payload, destination = self.__upsert_project_file(projects_dir, root, name, preferred_id)
			assignments[ident] = parent
			self.__write_folders(folders, before, listing, ident, parent)
			r = {'project_id': ident, 'project_name': payload['name'], 'project_file': str(destination), 'folder_id': parent, 'folder_path': ' / '.join(branch), 'folders_file': str(folders)}
		return r
	# @used-by :meth:`ProjectRegistrar.__register_single()`
	def __resolve_day(self, root: Path) -> date:
		load_cfg = self.__ops.get('settings') or (lambda: SettingsLoader().run())
		if self.__date_str:
			r = dfh_request_day(self.__date_str, settings_fn=load_cfg)
		elif 3 <= len(root.parents) and all((root.parents[i].name.isascii() and root.parents[i].name.isdigit() for i in (2, 1, 0))):
			r = date(int(root.parents[2].name), int(root.parents[1].name), int(root.parent.name))
		else:
			r = dfh_request_day(json.loads(dfh_project_paths(root, exact_root=True).project_json.read_text(encoding='utf-8'))['request_date'], settings_fn=load_cfg)
		return r
	# @used-by :meth:`ProjectRegistrar.__register_multi()`
	# @used-by :meth:`ProjectRegistrar.__register_single()`
	def __resolve_folders(self, folders_json_path=None, sp=None) -> Path:
		return dfh_resolve_folders_json(folders_json_path, sp, module_folders=self.__ops.get('module_folders'), initial_folders=self.__ops.get('initial_folders'), settings_fn=self.__ops.get('settings'), instances_fn=self.__ops.get('platform_instances'))
	# @used-by :meth:`ProjectRegistrar.__register_single()`
	def __upsert_project_file(self, projects: Path, root: Path, name: str, preferred_id: str | None) -> tuple[str, dict, Path]:
		ident, payload, destination, relocated = (None, None, None, None)
		for path in sorted(projects.glob('*.json')):
			item = json.loads(path.read_text(encoding='utf-8-sig'))
			matched, is_reloc = dfh_project_item_matches_root(item, root)
			if matched and (not is_reloc):
				ident, payload, destination = (item.get('id') or path.stem, item, path)
				break
			if matched and is_reloc and None is relocated:
				relocated = (item.get('id') or path.stem, item, path)
		if None is ident and None is not relocated:
			ident, payload, destination = relocated
			payload['projectResources'] = {**(payload.get('projectResources') or {}), 'resources': [{'folderUri': root.as_uri()}]}
			dfh_replace_bytes(destination, json_bytes(payload))
		elif None is ident:
			ident = preferred_id or str(uuid.uuid4())
			destination = projects / f'{ident}.json'
			payload = {'id': ident, 'name': name, 'projectResources': {'resources': [{'folderUri': root.as_uri()}]}, 'settings': {}, 'isWorkspaceOnly': False}
			dfh_create_bytes(destination, json_bytes(payload))
		return (ident, payload, destination)
	# @used-by :meth:`ProjectRegistrar.__register_single()`
	def __write_folders(self, folders: Path, before: bytes, listing: dict, ident: str, parent: str) -> None:
		if folders.read_bytes() != before:
			raise RuntimeError('Folders changed concurrently; retry registration')
		if json_bytes(listing) != before:
			dfh_replace_bytes(folders, json_bytes(listing))
		if json.loads(folders.read_text(encoding='utf-8-sig'))['projectFolderMap'].get(ident) != parent:
			raise RuntimeError('Project folder assignment did not persist; retry registration')
	# @used-by :func:`agent_tools.platforms.antigravity.register()`
	# @used-by :func:`agent_tools.platforms.antigravity.register_antigravity_project()`
	# @used-by :meth:`test_df_harness_s11_wave2d_platform_cov.DfHarnessS11Wave2dPlatformCovTests.test_ag_and_codex_registrars_verifiers_and_title_sync()`
	def run(self) -> dict[str, Any]:
		if self.__multi_instance and None is self.__projects_dir and None is self.__folders_json_path:
			r = self.__register_multi()
		else:
			default_dir = Path(self.__ops.get('default_projects_dir') or dfh_default_platform_paths('antigravity')['projects_dir'])
			r = self.__register_single(Path(self.__projects_dir or default_dir), self.__folders_json_path, self.__preferred_id)
		return r
