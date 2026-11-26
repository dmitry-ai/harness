# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from pathlib import Path
import re
# 2026-11-26 "Move turn lifecycle subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/383
class SlotResolver:
	# @used-by :meth:`Df.Harness.Path.ProjectPaths.ProjectPaths.__init__()`
	def __init__(self, root: Path, raw_paths: dict[str, str], merged_vars: dict[str, str], env: dict[str, str] | None) -> None:
		self.__root = root
		self.__raw_paths = raw_paths
		self.__vars = merged_vars
		self.__env = env
		self.__paths_str: dict[str, str] = {}
	# @used-by :meth:`SlotResolver.run()`
	def __prepare_maps(self) -> tuple[dict[str, str], dict[str, str], dict[str, str]]:
		from agent_tools import path_registry as pr
		eff_tpls, slot_vars, var_to_slot = ({}, {}, {})
		for slot_key, slot_tpl in self.__raw_paths.items():
			slot_var = re.sub('[^A-Za-z0-9_]', '_', slot_key).upper()
			eff_tpl = slot_tpl
			if pr._VAR_NAME_RE.match(slot_var):
				self_tok = f'${{{slot_var}}}'
				if self_tok in eff_tpl and slot_var in self.__vars:
					eff_tpl = eff_tpl.replace(self_tok, self.__vars[slot_var])
				slot_vars[slot_key] = slot_var
				var_to_slot[slot_var] = slot_key
			eff_tpls[slot_key] = eff_tpl
		return (eff_tpls, slot_vars, var_to_slot)
	# @used-by :meth:`SlotResolver.__resolve_one()`
	def __resolve_deps(self, eff_tpl: str, next_chain: tuple[str, ...], eff_tpls: dict[str, str], slot_vars: dict[str, str], var_to_slot: dict[str, str]) -> None:
		from agent_tools import path_registry as pr
		for m in pr._TOKEN_RE.finditer(eff_tpl):
			ref = (m.group(1) or '').strip()
			if ref and (not ref.upper().startswith('ENV:')):
				if ref in next_chain:
					raise ValueError(f"Cyclic path template variable reference: {' -> '.join((*next_chain, ref))}")
				if ref in var_to_slot:
					self.__resolve_one(var_to_slot[ref], eff_tpls, slot_vars, var_to_slot, next_chain)
	# @used-by :meth:`SlotResolver.__resolve_deps()`
	# @used-by :meth:`SlotResolver.run()`
	def __resolve_one(self, slot_key: str, eff_tpls: dict[str, str], slot_vars: dict[str, str], var_to_slot: dict[str, str], chain: tuple[str, ...]=()) -> str:
		if slot_key in self.__paths_str:
			r = self.__paths_str[slot_key]
		else:
			from agent_tools import path_registry as pr
			slot_var, eff_tpl = (slot_vars.get(slot_key), eff_tpls[slot_key])
			self.__resolve_deps(eff_tpl, (*chain, slot_var) if slot_var else chain, eff_tpls, slot_vars, var_to_slot)
			val = pr.expand_template(eff_tpl, self.__vars, env=self.__env, normalize=True)
			if not Path(val).is_absolute() and (not pr._URI_SCHEME_RE.match(val)):
				val = pr.normalize_path_str(f'{self.__root.as_posix()}/{val}')
			self.__paths_str[slot_key] = val
			if slot_var:
				var_val = val + ('/' if eff_tpl.endswith(('/', '\\')) and (not val.endswith('/')) else '')
				self.__vars[slot_var] = pr.escape_template_literal(var_val)
			r = val
		return r
	# @used-by :meth:`Df.Harness.Path.ProjectPaths.ProjectPaths.__init__()`
	def run(self) -> dict[str, str]:
		eff_tpls, slot_vars, var_to_slot = self.__prepare_maps()
		for slot_key in self.__raw_paths:
			self.__resolve_one(slot_key, eff_tpls, slot_vars, var_to_slot)
		return self.__paths_str
