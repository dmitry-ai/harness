# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from pathlib import Path
from typing import Any
from Df.Harness.lib.cleanup_lifecycle_ops import dfh_resolve_readonly_history
from Df.Harness.lib.cleanup_store_ops import dfh_linked
from Df.Harness.lib.path_discovery import dfh_default_platform_paths
from Df.Harness.lib.runtime_instances import dfh_platform_active, dfh_platform_adapter_name, dfh_platform_instances
# 2026-11-26 "Move turn lifecycle subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/383
class StoreResolver:
	# @used-by :meth:`Df.Harness.Cleanup.Scanner.Scanner.__init__()`
	def __init__(self, config: dict, daily: Path, *, ag_directory=None, ag_backend=None, folders=None) -> None:
		self.__config = config
		self.__daily = daily
		self.__ag_directory = ag_directory
		self.__ag_backend = ag_backend
		self.__folders = folders
	# @used-by :meth:`StoreResolver.__resolve_ag_instance()`
	def __abs_path(self, raw, fallback=None) -> Path | None:
		val = raw or fallback
		return Path(val).absolute() if val else None
	# @used-by :meth:`StoreResolver.run()`
	def __platform_ids(self, adapter: str) -> list[str]:
		platforms_cfg = self.__config.get('platforms') or {}
		return [pid for pid, pcfg in platforms_cfg.items() if isinstance(pcfg, dict) and adapter == dfh_platform_adapter_name(pid, pcfg) and dfh_platform_active(pid, config=self.__config)]
	# @used-by :meth:`StoreResolver.__resolve_ag_multi()`
	def __resolve_ag_instance(self, iid: str, inst: dict) -> dict:
		sp = inst['system_paths']
		home_dir = self.__abs_path(inst.get('home'))
		home_ag = dfh_default_platform_paths('antigravity', home=home_dir) if home_dir else {}
		p_dir = self.__abs_path(sp.get('projects_dir'), home_ag.get('projects_dir'))
		b_dir = self.__abs_path(sp.get('backend_dir'), home_ag.get('backend_dir'))
		conv_dir = self.__abs_path(sp.get('conversations_dir'), b_dir / 'conversations' if b_dir else None)
		brain_dir = self.__abs_path(sp.get('brain_dir'), b_dir / 'brain' if b_dir else None)
		conv_db = self.__abs_path(sp.get('conversations_db'), b_dir / 'conversation_summaries.db' if b_dir else None)
		self.__validate_ag_instance(iid, p_dir, home_dir, (b_dir, conv_dir, brain_dir, conv_db))
		has_history = bool((conv_db and conv_db.is_file()) or (conv_dir and conv_dir.is_dir() and any(conv_dir.iterdir())) or (brain_dir and brain_dir.is_dir() and any(brain_dir.iterdir())))
		return {'directory': p_dir, 'backend': b_dir or (conv_db.parent if conv_db else p_dir), 'conversations_dir': conv_dir, 'brain_dir': brain_dir, 'conversations_db': conv_db, 'allow_missing_db': not has_history, 'folders_json': sp.get('folders_json')}
	# @used-by :meth:`StoreResolver.run()`
	def __resolve_ag_multi(self, ag_plats: list[str]) -> tuple[dict, Path | None, Any]:
		ag_insts: dict = {}
		for pid in ag_plats:
			ag_insts.update(dfh_platform_instances(pid, config=self.__config, include_disabled=False))
		ag_stores = {iid: self.__resolve_ag_instance(iid, inst) for iid, inst in ag_insts.items()}
		first_store = next(iter(ag_stores.values()), None)
		directory = first_store['directory'] if first_store else None
		backend = {iid: (s['backend'], s['allow_missing_db'], s['conversations_db']) for iid, s in ag_stores.items()} if ag_stores else {}
		return (ag_stores, directory, backend)
	# @used-by :meth:`StoreResolver.run()`
	def __resolve_ag_single(self) -> tuple[dict, Path, Path]:
		def_ag = dfh_default_platform_paths('antigravity')
		p_dir = Path(self.__ag_directory or def_ag['projects_dir']).absolute()
		b_dir = Path(self.__ag_backend or def_ag['backend_dir']).absolute()
		if not p_dir.is_dir() or dfh_linked(p_dir):
			raise ValueError('Antigravity native stores unavailable or linked')
		if p_dir.is_relative_to(self.__daily):
			raise ValueError('Native stores must be outside the preserved daily archive')
		return ({'default': {'directory': p_dir, 'backend': b_dir, 'allow_missing_db': False}}, p_dir, b_dir)
	# @used-by :meth:`StoreResolver.run()`
	def __resolve_codex_homes(self, cx_plats: list[str]) -> tuple[dict, dict]:
		codex_insts: dict = {}
		for pid in cx_plats:
			codex_insts.update(dfh_platform_instances(pid, config=self.__config, include_disabled=False))
		homes = {iid: Path(inst['home']) if inst.get('home') else None for iid, inst in codex_insts.items() if inst.get('home') or inst['system_paths'].get('state_db_glob')}
		globs = {iid: inst['system_paths'].get('state_db_glob') for iid, inst in codex_insts.items() if (inst.get('home') or inst['system_paths'].get('state_db_glob')) and inst['system_paths'].get('state_db_glob')}
		return (homes, globs)
	# @used-by :meth:`StoreResolver.run()`
	def __resolve_folder_file(self, ag_plats: list[str], ag_stores: dict, single_ag_mode: bool) -> Path | None:
		platforms_cfg = self.__config.get('platforms') or {}
		ag_plat_folders = next(((platforms_cfg.get(pid) or {}).get('folders_json') for pid in ag_plats if (platforms_cfg.get(pid) or {}).get('folders_json')), None)
		folders_raw = self.__folders or next((s.get('folders_json') for s in ag_stores.values() if s.get('folders_json')), None) or ag_plat_folders
		if (ag_stores or None is not self.__folders) and (not folders_raw):
			raise ValueError('Antigravity folders_json is not configured in runtime.json')
		folder_file = Path(folders_raw).absolute() if (ag_stores or None is not self.__folders) else None
		if None is not folder_file:
			if dfh_linked(folder_file) or (single_ag_mode and (not folder_file.is_file())):
				raise ValueError('Antigravity native stores unavailable or linked')
			if folder_file.is_relative_to(self.__daily):
				raise ValueError('Native stores must be outside the preserved daily archive')
		return folder_file
	# @used-by :meth:`StoreResolver.__resolve_ag_instance()`
	def __validate_ag_instance(self, iid: str, p_dir: Path | None, home_dir: Path | None, extra: tuple[Path | None, ...]) -> None:
		b_dir, conv_dir, brain_dir, conv_db = extra
		all_paths = (p_dir, home_dir, *extra)
		if None is p_dir or any((None is not p and dfh_linked(p) for p in all_paths)):
			raise ValueError(f'Antigravity native stores unavailable or linked ({iid})')
		has_any = p_dir.is_dir() or (conv_dir and conv_dir.is_dir()) or (brain_dir and brain_dir.is_dir()) or (conv_db and conv_db.is_file()) or (home_dir and home_dir.is_dir())
		if not has_any:
			raise ValueError(f'Antigravity native stores unavailable or linked ({iid})')
		if any((None is not p and p.is_relative_to(self.__daily) for p in (p_dir, b_dir, conv_dir, brain_dir, conv_db))):
			raise ValueError('Native stores must be outside the preserved daily archive')
	# @used-by :meth:`Df.Harness.Cleanup.Scanner.Scanner.__init__()`
	def run(self) -> dict[str, Any]:
		single_ag_mode = None is not self.__ag_directory or None is not self.__ag_backend
		ag_plats = self.__platform_ids('antigravity')
		cx_plats = self.__platform_ids('codex')
		ag_stores, directory, backend = self.__resolve_ag_single() if single_ag_mode else self.__resolve_ag_multi(ag_plats)
		folder_file = self.__resolve_folder_file(ag_plats, ag_stores, single_ag_mode)
		homes, home_globs = self.__resolve_codex_homes(cx_plats)
		readonly_history = dfh_resolve_readonly_history(self.__config, self.__daily, ag_stores, homes, single_ag_mode=single_ag_mode)
		return {'single_ag_mode': single_ag_mode, 'ag_stores': ag_stores, 'directory': directory, 'backend': backend, 'folder_file': folder_file, 'homes': homes, 'home_globs': home_globs, 'readonly_history': readonly_history}
