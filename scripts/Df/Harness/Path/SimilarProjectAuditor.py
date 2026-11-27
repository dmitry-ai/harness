# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from pathlib import Path
from typing import Any
from Df.Harness.lib.path_resolve import dfh_load_registry, dfh_project_paths
from Df.Harness.lib.path_schema import dfh_canonicalize_root_dir
from Df.Harness.lib.path_template import dfh_path_key
# 2026-11-26 "Move turn lifecycle subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/383
class SimilarProjectAuditor:
	# @used-by :func:`agent_tools.path_registry.evaluate_similar_project_touches()`
	# @used-by :meth:`test_df_harness_s11_wave2d_journal_path_cov.DfHarnessS11Wave2dJournalPathCovTests.test_paths_and_uri()`
	# @used-by :meth:`test_df_harness_s11_wave2d_tail_cov.DfHarnessS11Wave2dTailCovTests.test_hook_emergency_and_path_tail()`
	def __init__(self, touched_repo_files: list[Path] | tuple[Path, ...] | set[Path], *, registry: Any=None) -> None:
		self.__raw_files = touched_repo_files or ()
		self.__reg = registry or dfh_load_registry()
		self.__emitted: dict[str, dict[str, Any]] = {}
	# @used-by :meth:`SimilarProjectAuditor.run()`
	def __eval_groups(self, resolved_files: list[Path]) -> None:
		for grp in self.__reg.similar_project_groups:
			members_state: list[dict[str, Any]] = []
			for mem in grp['members']:
				m_root = dfh_canonicalize_root_dir(mem['project'], self.__reg)
				m_roots = self.__match_roots(m_root)
				m_affs = [Path(a).resolve() for a in mem['affiliated_paths']]
				hits = [fp for fp in resolved_files if any((fp == r or fp.is_relative_to(r) for r in m_roots)) or any((fp == a or fp.is_relative_to(a) for a in m_affs))]
				members_state.append({'hits': hits, 'root': m_root})
			touched = [ms for ms in members_state if ms['hits']]
			if touched:
				self.__record_group_peers(grp['id'], members_state, touched)
	# @used-by :meth:`SimilarProjectAuditor.run()`
	def __eval_overlay_peers(self, resolved_files: list[Path], file_roots: dict[str, Path]) -> None:
		touched_keys = {dfh_path_key(r) for r in file_roots.values()}
		for fp in resolved_files:
			src_root = file_roots[dfh_path_key(fp)]
			try:
				pp_f = dfh_project_paths(src_root, registry=self.__reg, exact_root=True)
			except (OSError, ValueError):
				continue
			for peer in pp_f.similar_projects:
				pk = dfh_path_key(peer)
				if pk != dfh_path_key(src_root):
					p_roots = self.__match_roots(peer)
					hit = pk in touched_keys or any((f2 == pr or f2.is_relative_to(pr) for f2 in resolved_files for pr in p_roots))
					self.__record_peer(peer, group_id=None, source_projects=[src_root], source_label=f'{src_root.as_posix()} ({fp.name})', peer_touched=hit)
	# @used-by :meth:`SimilarProjectAuditor.__eval_groups()`
	# @used-by :meth:`SimilarProjectAuditor.__eval_overlay_peers()`
	def __match_roots(self, proj_root: Path) -> list[Path]:
		roots = [proj_root]
		try:
			pp_m = dfh_project_paths(proj_root, registry=self.__reg, exact_root=True)
			for cr in (*pp_m.code_repos, *pp_m.auxiliary_repos.values()):
				if all((dfh_path_key(cr) != dfh_path_key(x) for x in roots)):
					roots.append(cr)
		except (OSError, ValueError):
			pass
		return roots
	# @used-by :meth:`SimilarProjectAuditor.__eval_groups()`
	def __record_group_peers(self, gid: str, members_state: list[dict[str, Any]], touched: list[dict[str, Any]]) -> None:
		for ms in members_state:
			srcs = [tm for tm in touched if dfh_path_key(tm['root']) != dfh_path_key(ms['root'])]
			if srcs:
				parts = [f"{tm['root'].as_posix()} ({', '.join(sorted({h.name for h in tm['hits']})[:3])})" for tm in srcs]
				self.__record_peer(ms['root'], group_id=gid, source_projects=[tm['root'] for tm in srcs], source_label='; '.join(parts), peer_touched=bool(ms['hits']))
	# @used-by :meth:`SimilarProjectAuditor.__eval_overlay_peers()`
	# @used-by :meth:`SimilarProjectAuditor.__record_group_peers()`
	def __record_peer(self, peer_root: Path, *, group_id: str | None, source_projects: list[Path], source_label: str, peer_touched: bool) -> None:
		pk = dfh_path_key(peer_root)
		prev = self.__emitted.get(pk)
		if None is prev:
			self.__emitted[pk] = {'group_id': group_id, 'peer_root': peer_root, 'peer_touched': bool(peer_touched), 'source_label': source_label, 'source_projects': list(source_projects)}
		else:
			if None is prev['group_id'] and None is not group_id:
				prev['group_id'] = group_id
			prev['peer_touched'] = prev['peer_touched'] or bool(peer_touched)
			for sp in source_projects:
				if all((dfh_path_key(sp) != dfh_path_key(x) for x in prev['source_projects'])):
					prev['source_projects'].append(sp)
	# @used-by :meth:`SimilarProjectAuditor.run()`
	def __resolve_input_files(self) -> list[Path]:
		out: list[Path] = []
		seen: set[str] = set()
		for raw_f in self.__raw_files:
			if not raw_f:
				continue
			try:
				fp = Path(raw_f).resolve()
			except OSError:
				continue
			fk = dfh_path_key(fp)
			if fk not in seen:
				seen.add(fk)
				out.append(fp)
		return out
	# @used-by :func:`agent_tools.path_registry.evaluate_similar_project_touches()`
	# @used-by :meth:`test_df_harness_s11_wave2d_journal_path_cov.DfHarnessS11Wave2dJournalPathCovTests.test_paths_and_uri()`
	# @used-by :meth:`test_df_harness_s11_wave2d_tail_cov.DfHarnessS11Wave2dTailCovTests.test_hook_emergency_and_path_tail()`
	def run(self) -> list[dict[str, Any]]:
		resolved = self.__resolve_input_files()
		if not resolved:
			r: list[dict[str, Any]] = []
		else:
			file_roots: dict[str, Path] = {}
			for fp in resolved:
				try:
					file_roots[dfh_path_key(fp)] = dfh_project_paths(fp, registry=self.__reg).root
				except (OSError, ValueError):
					file_roots[dfh_path_key(fp)] = dfh_canonicalize_root_dir(fp.parent, self.__reg)
			self.__eval_groups(resolved)
			self.__eval_overlay_peers(resolved, file_roots)
			r = [self.__emitted[k] for k in sorted(self.__emitted, key=lambda key: str(self.__emitted[key]['peer_root']))]
		return r
