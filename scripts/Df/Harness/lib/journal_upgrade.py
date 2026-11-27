# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from pathlib import Path
from Df.Harness.lib.journal_core import V1_PAIR, V2_PAIR, _BUCKET_DIR_RE, _LEGACY_ANALYSIS_NAMES, dfh_detect_journal_version, dfh_is_bucket_dir_name, dfh_is_step_md, dfh_iter_side_step_files, dfh_journal_bucket_name, dfh_raw_state_dir
from Df.Harness.lib.path_resolve import dfh_load_registry, dfh_project_paths
from Df.Harness.lib.path_schema import dfh_discover_overlay_file
from Df.Harness.lib.path_state import dfh_clear_registry_cache
from Df.Harness.lib.storage import dfh_data_dir_for, dfh_locked, dfh_replace_bytes
import json
import os
import re
# 2026-11-26 "Move turn lifecycle subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/383
_LEGACY_OVERLAY_VALS = ('${JOURNAL_ROOT_DIR}/1 - Analysis', '${JOURNAL_ROOT_DIR}/1 - \u0410\u043d\u0430\u043b\u0438\u0437', '\ua66e/1 - Analysis', '\ua66e/1 - \u0410\u043d\u0430\u043b\u0438\u0437')
# @used-by :func:`_execute_upgrade()`
def _apply_upgrade_moves(plans: list[tuple]) -> None:
	for _, _, _, _, src_f, dst_f, raw in plans:
		if src_f.resolve() != dst_f.resolve():
			dst_f.parent.mkdir(parents=True, exist_ok=True)
			if dst_f.exists():
				if dst_f.read_bytes() != raw:
					raise FileExistsError(f'Conflicting destination file during journal upgrade: {dst_f}')
				src_f.unlink()
			else:
				os.replace(src_f, dst_f)
			if dst_f.read_bytes() != raw:
				raise OSError(f'Journal upgrade SHA-256 read-back mismatch: {dst_f}')
# @used-by :func:`dfh_upgrade_journal()`
def _assert_not_linked_tree(path: Path) -> None:
	for cur in (path, *path.parents):
		try:
			if os.path.lexists(cur) and (cur.is_symlink() or cur.is_junction()):
				raise ValueError(f'Linked journal path refused: {cur}')
		except OSError:
			pass
		if cur.parent == cur:
			break
# @used-by :func:`_execute_upgrade()`
def _build_upgrade_plans(units: list[tuple[Path, Path]]) -> list[tuple[Path, Path, str, int, Path, Path, bytes]]:
	plans: list[tuple[Path, Path, str, int, Path, Path, bytes]] = []
	for src_u, dst_u in units:
		for side_label, src_names, dst_name in (('req', ('req', '\u227b'), '\u227b'), ('res', ('res', '\u227a'), '\u227a')):
			for st, src_f in _collect_side_sources(src_u, src_names):
				dst_f = dst_u / dst_name / dfh_journal_bucket_name(st) / f'{st}.md'
				raw = src_f.read_bytes()
				if dst_f.exists() and dst_f.resolve() != src_f.resolve() and dst_f.read_bytes() != raw:
					raise FileExistsError(f'Conflicting destination file during journal upgrade; preserved: {dst_f}')
				plans.append((src_u, dst_u, side_label, st, src_f, dst_f, raw))
	return plans
# @used-by :func:`_collect_side_sources()`
def _collect_one_side_dir(s_dir: Path, by_step: dict[int, Path], entries: list[tuple[int, Path]]) -> None:
	for child in sorted(s_dir.iterdir(), key=lambda p: p.name):
		cands = [child] if dfh_is_step_md(child) else ([bf for bf in sorted(child.iterdir(), key=lambda p: p.name) if dfh_is_step_md(bf)] if child.is_dir() and dfh_is_bucket_dir_name(child.name) else [])
		for fpath in cands:
			st = int(fpath.stem)
			if st in by_step and by_step[st].read_bytes() != fpath.read_bytes():
				raise FileExistsError(f'Conflicting duplicate step {st} during journal upgrade: {by_step[st]} vs {fpath}')
			by_step.setdefault(st, fpath)
			entries.append((st, fpath))
# @used-by :func:`_build_upgrade_plans()`
def _collect_side_sources(src_jdir: Path, side_names: tuple[str, ...]) -> list[tuple[int, Path]]:
	entries: list[tuple[int, Path]] = []
	by_step: dict[int, Path] = {}
	for s_name in side_names:
		s_dir = src_jdir / s_name
		if s_dir.is_dir():
			_collect_one_side_dir(s_dir, by_step, entries)
	return entries
# @used-by :func:`_execute_upgrade()`
# @used-by :func:`dfh_upgrade_journal()`
def _discover_upgrade_units(j_root: Path) -> list[tuple[Path, Path]]:
	has_direct = any(((j_root / n).is_dir() for n in (*V1_PAIR, *V2_PAIR)))
	subjournals: list[Path] = []
	for child in sorted(j_root.iterdir(), key=lambda p: p.name):
		if child.is_dir() and child.name not in (*V1_PAIR, *V2_PAIR, 'source', '0', '0 - Context', '1 - Context') and (not dfh_is_bucket_dir_name(child.name)):
			if any(((child / n).is_dir() for n in (*V1_PAIR, *V2_PAIR))):
				subjournals.append(child)
	if 1 == len(subjournals) and (not has_direct) and subjournals[0].name in _LEGACY_ANALYSIS_NAMES:
		r = [(subjournals[0], j_root)]
	elif subjournals and (not has_direct):
		r = [(sub, sub) for sub in subjournals]
	else:
		r = [(j_root, j_root)]
	return r
# @used-by :func:`dfh_upgrade_journal()`
def _execute_upgrade(j_root: Path, proj_root: Path | None, data_root: Path, dry_run: bool) -> dict:
	units = _discover_upgrade_units(j_root)
	from_ver = min((dfh_detect_journal_version(src_u) for src_u, _ in units), default=1)
	plans = _build_upgrade_plans(units)
	moved = sum((1 for _, _, _, _, sf, df, _ in plans if sf.resolve() != df.resolve()))
	primary_dst = units[0][1]
	if dry_run:
		b_set = sorted({dfh_journal_bucket_name(st) for _, _, _, st, _, _, _ in plans}, key=lambda s: int(_BUCKET_DIR_RE.match(s).group(1)))
		r = {'buckets': b_set, 'dry_run': True, 'exists': True, 'from_version': from_ver, 'journal_dir': str(primary_dst), 'moved_files': moved, 'to_version': 3, 'upgraded': False, 'valid': True, 'verified_steps': len({(du, st) for _, du, _, st, _, _, _ in plans})}
	else:
		_apply_upgrade_moves(plans)
		readme_upd, state_mig = _finalize_upgraded_units(units, data_root)
		ov_upd = _sync_overlay_journal_slot(proj_root, primary_dst) if None is not proj_root else False
		dfh_clear_registry_cache()
		b_names, step_cnt = _summarize_v2_buckets(primary_dst)
		did_upg = 0 < moved or readme_upd or state_mig or ov_upd or 3 > from_ver
		r = {'buckets': b_names, 'exists': True, 'from_version': from_ver, 'journal_dir': str(primary_dst), 'moved_files': moved, 'overlay_updated': ov_upd, 'readme_updated': readme_upd, 'state_migrated': state_mig, 'to_version': dfh_detect_journal_version(primary_dst), 'upgraded': did_upg, 'valid': True, 'verified_steps': step_cnt}
	return r
# @used-by :func:`_execute_upgrade()`
def _finalize_upgraded_units(units: list[tuple[Path, Path]], data_root: Path) -> tuple[bool, bool]:
	readme_upd = state_mig = False
	for src_u, dst_u in units:
		(dst_u / '\u227b').mkdir(parents=True, exist_ok=True)
		(dst_u / '\u227a').mkdir(parents=True, exist_ok=True)
		_prune_legacy_side_dirs(src_u, dst_u)
		if src_u.resolve() != dst_u.resolve() and src_u.is_dir() and (not any(src_u.iterdir())):
			src_u.rmdir()
		if _migrate_journal_state_dir(src_u, dst_u, data_root):
			state_mig = True
		if _rewrite_journal_readme(dst_u / 'README.md'):
			readme_upd = True
	return (readme_upd, state_mig)
# @used-by :func:`_merge_state_subdirs()`
def _merge_one_state_dir(src_sub: Path, dst_sub: Path, *, prune_empty: bool) -> bool:
	moved = False
	if src_sub.is_dir():
		dst_sub.mkdir(parents=True, exist_ok=True)
		for f in sorted(src_sub.glob('*.json')):
			dst_f, raw = (dst_sub / f.name, f.read_bytes())
			if dst_f.exists():
				if dst_f.read_bytes() != raw:
					raise FileExistsError(f'Conflicting journal state file during upgrade: {dst_f}')
				f.unlink()
			else:
				os.replace(f, dst_f)
			moved = True
		if prune_empty and (not any(src_sub.iterdir())):
			src_sub.rmdir()
	return moved
# @used-by :func:`_migrate_journal_state_dir()`
# @used-by :meth:`test_df_harness_s11_wave2d_journal_path_cov.DfHarnessS11Wave2dJournalPathCovTests.test_journal_sync_and_upgrade()`
def _merge_state_subdirs(old_sdir: Path, new_sdir: Path) -> bool:
	m1 = _merge_one_state_dir(old_sdir / 'answer-groups', new_sdir / 'answer-groups', prune_empty=True)
	m2 = _merge_one_state_dir(old_sdir, new_sdir, prune_empty=False)
	if not any(old_sdir.iterdir()):
		old_sdir.rmdir()
	return m1 or m2
# @used-by :func:`_finalize_upgraded_units()`
def _migrate_journal_state_dir(src_jdir: Path, dst_jdir: Path, data_root: Path) -> bool:
	r = False
	if src_jdir.resolve() != dst_jdir.resolve():
		old_sdir, new_sdir = (dfh_raw_state_dir(src_jdir, data_root=data_root), dfh_raw_state_dir(dst_jdir, data_root=data_root))
		if old_sdir.is_dir() and old_sdir.resolve() != new_sdir.resolve():
			(old_sdir / 'writer.lock').unlink(missing_ok=True)
			if not new_sdir.exists():
				new_sdir.parent.mkdir(parents=True, exist_ok=True)
				os.replace(old_sdir, new_sdir)
				r = True
			else:
				r = _merge_state_subdirs(old_sdir, new_sdir)
	return r
# @used-by :func:`dfh_upgrade_journal()`
def _overlay_needs_sync(proj_root: Path | None) -> bool:
	r = False
	ov_f = dfh_discover_overlay_file(proj_root, dfh_load_registry()) if None is not proj_root else None
	if None is not ov_f and ov_f.is_file():
		try:
			ov_obj = json.loads(ov_f.read_text(encoding='utf-8-sig'))
			r = isinstance(ov_obj, dict) and isinstance(ov_obj.get('paths'), dict) and ov_obj['paths'].get('journal_dir') in _LEGACY_OVERLAY_VALS
		except (OSError, ValueError):
			r = False
	return r
# @used-by :func:`_finalize_upgraded_units()`
def _prune_legacy_side_dirs(src_u: Path, dst_u: Path) -> None:
	for dir_cand in (src_u, dst_u):
		for s_name in (*V1_PAIR, *V2_PAIR):
			s_dir = dir_cand / s_name
			if s_dir.is_dir():
				for child in list(s_dir.iterdir()):
					if child.is_dir() and dfh_is_bucket_dir_name(child.name) and (not any(child.iterdir())):
						child.rmdir()
				if s_name in V1_PAIR and (not any(s_dir.iterdir())):
					s_dir.rmdir()
# @used-by :func:`_finalize_upgraded_units()`
def _rewrite_journal_readme(readme_path: Path) -> bool:
	r = False
	if readme_path.is_file():
		orig = readme_path.read_text(encoding='utf-8')
		updated = orig.replace('{req,res}', '{\u227b,\u227a}')
		updated = re.sub('\\((?:req|\\u227b)/(\\d+)\\.md\\)', lambda m: f'(\u227b/{dfh_journal_bucket_name(int(m.group(1)))}/{int(m.group(1))}.md)', updated)
		updated = re.sub('\\((?:res|\\u227a)/(\\d+)\\.md\\)', lambda m: f'(\u227a/{dfh_journal_bucket_name(int(m.group(1)))}/{int(m.group(1))}.md)', updated)
		if updated != orig:
			dfh_replace_bytes(readme_path, updated.encode('utf-8'))
			r = True
	return r
# @used-by :func:`_execute_upgrade()`
# @used-by :func:`dfh_upgrade_journal()`
def _summarize_v2_buckets(primary_dst: Path) -> tuple[list[str], int]:
	b_names = sorted({child.name for s_name in V2_PAIR if (primary_dst / s_name).is_dir() for child in (primary_dst / s_name).iterdir() if child.is_dir() and dfh_is_bucket_dir_name(child.name)}, key=lambda s: int(_BUCKET_DIR_RE.match(s).group(1)))
	step_cnt = len({st for s_name in V2_PAIR for st, _ in dfh_iter_side_step_files(primary_dst / s_name)})
	return (b_names, step_cnt)
# @used-by :func:`_execute_upgrade()`
def _sync_overlay_journal_slot(project_root: Path, dst_jdir: Path) -> bool:
	ov_file = dfh_discover_overlay_file(project_root, dfh_load_registry())
	r = False
	if None is not ov_file and ov_file.is_file():
		raw_text = ov_file.read_text(encoding='utf-8-sig')
		raw_obj = json.loads(raw_text)
		if isinstance(raw_obj, dict) and isinstance(raw_obj.get('paths'), dict) and raw_obj['paths'].get('journal_dir') in _LEGACY_OVERLAY_VALS:
			if dst_jdir.resolve() == dfh_project_paths(project_root, exact_root=True).journal_root_dir.resolve():
				indent = '\t' if '\n\t"' in raw_text else 2
				raw_obj['paths']['journal_dir'] = '${JOURNAL_ROOT_DIR}'
				trailing = '\n' if raw_text.endswith('\n') else ''
				dfh_replace_bytes(ov_file, (json.dumps(raw_obj, ensure_ascii=False, indent=indent) + trailing).encode('utf-8'))
				dfh_clear_registry_cache()
				r = True
	return r
# @used-by :func:`dfh_upgrade_journal()`
def _unit_needs_upgrade(src_jdir: Path, dst_jdir: Path) -> bool:
	readme = dst_jdir / 'README.md'
	readme_old = readme.is_file() and ('{req,res}' in (txt := readme.read_text(encoding='utf-8', errors='replace')) or bool(re.search('\\((?:req|res|\\u227b|\\u227a)/\\d+\\.md\\)', txt)))
	return src_jdir.resolve() != dst_jdir.resolve() or (dst_jdir / 'req').is_dir() or (dst_jdir / 'res').is_dir() or 3 > dfh_detect_journal_version(dst_jdir) or readme_old
# @used-by :func:`Df.Harness.lib.completion_commands._begin_live()`
# @used-by :func:`Df.Harness.lib.hook_stop_ops.dfh_record_emergency_locked()`
# @used-by :meth:`Df.Harness.Completion.JournalReconciler.JournalReconciler.run()`
# @used-by :meth:`Df.Harness.Upwork.CliRunner.CliRunner.__cmd_journal_upgrade()`
# @used-by :meth:`Df.Harness.Upwork.ProjectConfigurator.ProjectConfigurator.configure()`
# @used-by :meth:`Df.Harness.Workflow.AnswerRecorder.AnswerRecorder.record()`
# @used-by :meth:`Df.Harness.Workflow.RequestAdopter.RequestAdopter.adopt()`
# @used-by :meth:`Df.Harness.Workflow.WorkflowResumer.WorkflowResumer.resume()`
# @used-by :meth:`test_path_registry.PathRegistryTests.test_v1_journal_only_upgrade_preserves_v1_project_layout_and_historical_receipts()`
def dfh_ensure_project_journal_upgraded(root: str | Path, *, selected: str | Path | None=None) -> dict:
	pp = dfh_project_paths(Path(root).resolve(), exact_root=True)
	if None is not selected:
		sel_str = pp.expand(str(selected)) if '${' in str(selected) else str(selected)
		sel_p = (pp.root / sel_str).resolve()
		if '\ua66e' == sel_p.name and sel_p.exists():
			r = dfh_upgrade_journal(sel_p, project_root=pp.root)
		elif '\ua66e' == sel_p.parent.name and sel_p.name in _LEGACY_ANALYSIS_NAMES and sel_p.parent.exists():
			r = dfh_upgrade_journal(sel_p.parent, project_root=pp.root)
		else:
			ver = dfh_detect_journal_version(sel_p)
			r = {'exists': sel_p.exists(), 'from_version': ver, 'journal_dir': str(sel_p), 'moved_files': 0, 'to_version': ver, 'upgraded': False, 'valid': True}
	else:
		r = dfh_upgrade_journal(pp.journal_dir if pp.journal_glob else pp.journal_root_dir, project_root=pp.root)
	return r
# @used-by :func:`dfh_ensure_project_journal_upgraded()`
# @used-by :meth:`Df.Harness.Upwork.CliRunner.CliRunner.__cmd_journal_upgrade()`
# @used-by :meth:`test_agent_tools.JournalTests.test_o_journal_20_entry_bucketing_and_partial_range_normalization()`
def dfh_upgrade_journal(journal_root: str | Path, *, project_root: str | Path | None=None, dry_run: bool=False) -> dict:
	j_root = Path(journal_root).resolve()
	proj_root = Path(project_root).resolve() if None is not project_root else None
	if not j_root.exists():
		r = {'buckets': [], 'exists': False, 'from_version': 3, 'journal_dir': str(j_root), 'moved_files': 0, 'to_version': 3, 'upgraded': False, 'valid': True, 'verified_steps': 0}
	else:
		_assert_not_linked_tree(j_root)
		units_preview = _discover_upgrade_units(j_root)
		if not _overlay_needs_sync(proj_root) and (not any((_unit_needs_upgrade(s, d) for s, d in units_preview))):
			primary_dst = units_preview[0][1]
			b_names, step_cnt = _summarize_v2_buckets(primary_dst)
			r = {'buckets': b_names, 'exists': True, 'from_version': 3, 'journal_dir': str(primary_dst), 'moved_files': 0, 'to_version': 3, 'upgraded': False, 'valid': True, 'verified_steps': step_cnt}
		else:
			data_root = dfh_project_paths(proj_root, exact_root=True).data_dir if None is not proj_root else dfh_data_dir_for(j_root)
			if dry_run:
				r = _execute_upgrade(j_root, proj_root, data_root, True)
			else:
				with dfh_locked(data_root / 'journal-upgrade.lock'):
					r = _execute_upgrade(j_root, proj_root, data_root, False)
	return r
