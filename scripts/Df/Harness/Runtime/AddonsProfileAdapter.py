# 2026-11-28 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from pathlib import Path
from typing import Any
from Df.Harness.lib.path_template import dfh_escape_template_literal, dfh_is_linked
import json
import re
# 2026-11-28 "Implement AddonsProfileAdapter with stat-keyed runtime cache invalidation": https://github.com/dmitry-ai/harness/issues/465
class AddonsProfileAdapter:
	__ID_RE = re.compile('^[A-Za-z0-9_-]+$')
	__SUPPORTED_SOURCE = 'addons_profiles_json'
	__USER_DATA_RE = re.compile('^[A-Za-z0-9-]+$')
	# @used-by :func:`Df.Harness.lib.runtime_cache._load_uncached_settings()`
	def __init__(self, registry: Any) -> None:
		self.__registry = registry
	# @used-by :meth:`AddonsProfileAdapter.__apply_platform()`
	@staticmethod
	def __apply_overrides(plat_id: str, instances: dict[str, dict[str, Any]], raw_overrides: Any) -> None:
		if None is not raw_overrides:
			if not isinstance(raw_overrides, dict):
				raise ValueError(f'runtime.json platforms.{plat_id}.instance_overrides must be an object')
			for inst_id, patch_cfg in raw_overrides.items():
				if inst_id not in instances:
					raise ValueError(f'runtime.json platforms.{plat_id}.instance_overrides references unknown profile {inst_id!r}')
				if not isinstance(patch_cfg, dict):
					raise ValueError(f'runtime.json platforms.{plat_id}.instance_overrides.{inst_id} must be an object')
				AddonsProfileAdapter.__merge_instance_override(plat_id, inst_id, instances[inst_id], patch_cfg)
	# @used-by :meth:`AddonsProfileAdapter.apply()`
	def __apply_platform(self, plat_id: str, plat_cfg: dict[str, Any]) -> Path | None:
		source_key = plat_cfg.get('instances_source')
		if None is source_key:
			r: Path | None = None
		else:
			src_path = self.__resolve_source_path(plat_id, plat_cfg, source_key)
			profiles = AddonsProfileAdapter.__read_profiles_file(plat_id, src_path)
			instances = AddonsProfileAdapter.__project_profiles(plat_id, profiles)
			AddonsProfileAdapter.__apply_overrides(plat_id, instances, plat_cfg.get('instance_overrides'))
			plat_cfg['instances'] = instances
			plat_cfg.pop('instances_source', None)
			plat_cfg.pop('instance_overrides', None)
			r = src_path
		return r
	# @used-by :meth:`AddonsProfileAdapter.__build_instance()`
	@staticmethod
	def __attach_optional_fields(plat_id: str, pid: str, entry: dict[str, Any], inst: dict[str, Any]) -> None:
		for src_key, dst_key in (('email', 'account_email'), ('chromeShortcut', 'chrome_shortcut')):
			raw_val = entry.get(src_key)
			if None is not raw_val:
				if not isinstance(raw_val, str):
					raise ValueError(f'{plat_id} profile {pid!r} {src_key} must be a string')
				trimmed = raw_val.strip()
				if trimmed:
					inst[dst_key] = dfh_escape_template_literal(trimmed)
	# @used-by :meth:`AddonsProfileAdapter.__project_profiles()`
	@staticmethod
	def __build_instance(plat_id: str, entry: dict[str, Any]) -> tuple[str, dict[str, Any]]:
		pid, ud = AddonsProfileAdapter.__validate_core_fields(plat_id, entry)
		enabled = entry.get('enabled', True)
		if not isinstance(enabled, bool) or ('A0' == pid and (not enabled)):
			raise ValueError(f'Invalid enabled flag in {plat_id} profile {pid!r}')
		raw_label = entry.get('label')
		if None is not raw_label and (not isinstance(raw_label, str) or not raw_label.strip()):
			raise ValueError(f'Invalid label in {plat_id} profile {pid!r}')
		esc_id = dfh_escape_template_literal(pid)
		esc_ud = dfh_escape_template_literal(ud)
		is_primary = 'A0' == pid
		label = dfh_escape_template_literal(raw_label.strip()) if None is not raw_label else ('Antigravity A0 (Default)' if is_primary else f'Antigravity {esc_id}')
		inst: dict[str, Any] = {'enabled': enabled, 'home': '${USER_HOME}' if is_primary else f'${{APPDATA}}/{esc_ud}/home', 'label': label, 'primary': is_primary, 'user_data_dir': f'${{APPDATA}}/{esc_ud}'}
		AddonsProfileAdapter.__attach_optional_fields(plat_id, pid, entry, inst)
		return (esc_id, inst)
	# @used-by :meth:`AddonsProfileAdapter.__apply_overrides()`
	@staticmethod
	def __merge_instance_override(plat_id: str, inst_id: str, target: dict[str, Any], patch_cfg: dict[str, Any]) -> None:
		for key, val in patch_cfg.items():
			if 'system_paths' == key:
				if not isinstance(val, dict):
					raise ValueError(f'runtime.json platforms.{plat_id}.instance_overrides.{inst_id}.system_paths must be an object')
				existing = target.get('system_paths')
				target['system_paths'] = {**(existing if isinstance(existing, dict) else {}), **val}
			else:
				target[key] = val
	# @used-by :meth:`AddonsProfileAdapter.__apply_platform()`
	@staticmethod
	def __project_profiles(plat_id: str, profiles: list[Any]) -> dict[str, dict[str, Any]]:
		seen: dict[str, set[str]] = {'chromeShortcut': set(), 'email': set(), 'id': set(), 'userData': set()}
		instances: dict[str, dict[str, Any]] = {}
		for entry in profiles:
			if not isinstance(entry, dict):
				raise ValueError(f'{plat_id} profiles.json entries must be objects')
			pid, inst = AddonsProfileAdapter.__build_instance(plat_id, entry)
			AddonsProfileAdapter.__record_unique_entry(plat_id, entry, seen)
			instances[pid] = inst
		if 'A0' not in instances:
			raise ValueError(f'{plat_id} profiles.json must register primary profile A0')
		return instances
	# @used-by :meth:`AddonsProfileAdapter.__apply_platform()`
	@staticmethod
	def __read_profiles_file(plat_id: str, src_path: Path) -> list[Any]:
		if dfh_is_linked(src_path):
			raise ValueError(f'Linked addons_profiles_json refused for {plat_id}: {src_path}')
		if not src_path.is_file():
			raise ValueError(f'Missing addons_profiles_json for {plat_id}: {src_path}')
		try:
			payload = json.loads(src_path.read_text(encoding='utf-8-sig'))
		except (OSError, ValueError) as exc:
			raise ValueError(f'Invalid profiles.json for {plat_id}: {exc}') from exc
		if not isinstance(payload, dict) or 1 != payload.get('schemaVersion') or (not isinstance(payload.get('profiles'), list)) or (not payload['profiles']):
			raise ValueError(f'Invalid profiles.json schema for {plat_id}: expected schemaVersion 1 and non-empty profiles list')
		return payload['profiles']
	# @used-by :meth:`AddonsProfileAdapter.__project_profiles()`
	@staticmethod
	def __record_unique_entry(plat_id: str, entry: dict[str, Any], seen: dict[str, set[str]]) -> None:
		checks = (
			('id', str(entry['id'])),
			('userData', str(entry['userData']).lower()),
			('email', str(entry.get('email') or '').strip().lower()),
			('chromeShortcut', str(entry.get('chromeShortcut') or '').strip().lower()),
		)
		for field, norm in checks:
			if norm:
				if norm in seen[field]:
					raise ValueError(f'Duplicate {field} in {plat_id} profiles.json: {norm!r}')
				seen[field].add(norm)
	# @used-by :meth:`AddonsProfileAdapter.__apply_platform()`
	def __resolve_source_path(self, plat_id: str, plat_cfg: dict[str, Any], source_key: Any) -> Path:
		if 'instances' in plat_cfg or 'homes' in plat_cfg:
			raise ValueError(f'runtime.json platforms.{plat_id} cannot define both instances_source and instances or homes')
		if AddonsProfileAdapter.__SUPPORTED_SOURCE != source_key:
			raise ValueError(f'Unsupported runtime.json platforms.{plat_id}.instances_source: {source_key!r}')
		raw_ref = plat_cfg.get(source_key)
		if not isinstance(raw_ref, str) or not raw_ref.strip():
			raise ValueError(f'runtime.json platforms.{plat_id}.{source_key} must be a non-empty path')
		return Path(self.__registry.expand(raw_ref))
	# @used-by :meth:`AddonsProfileAdapter.__build_instance()`
	@staticmethod
	def __validate_core_fields(plat_id: str, entry: dict[str, Any]) -> tuple[str, str]:
		pid = entry.get('id')
		ud = entry.get('userData')
		if not isinstance(pid, str) or not AddonsProfileAdapter.__ID_RE.match(pid):
			raise ValueError(f'Invalid profile id in {plat_id} profiles.json: {pid!r}')
		if not isinstance(ud, str) or not AddonsProfileAdapter.__USER_DATA_RE.match(ud):
			raise ValueError(f'Invalid userData segment in {plat_id} profile {pid!r}: {ud!r}')
		return (pid, ud)
	# @used-by :func:`Df.Harness.lib.runtime_cache._load_uncached_settings()`
	def apply(self, raw: dict[str, Any]) -> tuple[Path, ...]:
		tracked: list[Path] = []
		plats = raw.get('platforms') if isinstance(raw, dict) else None
		if isinstance(plats, dict):
			for plat_id, plat_cfg in plats.items():
				if isinstance(plat_cfg, dict):
					src = self.__apply_platform(str(plat_id), plat_cfg)
					if None is not src:
						tracked.append(src)
		return tuple(tracked)