# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from pathlib import Path
from Df.Harness.Xref.Python.Graph import Graph
from Df.Harness.Xref.Python.Model import Model
from Df.Harness.Xref.Python.Overrides import Overrides
from Df.Harness.Xref.Python.Tags import Tags
# 2026-11-26 "Move verification gate subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/381
class Syncer:
	# @used-by :func:`agent_tools.xref.python_sync.sync_python_repo()`
	# @used-by :meth:`test_df_harness_s11_wave2b_xref.DfHarnessS11Wave2bXrefTests.test_python_xref_classes_and_engine_roundtrip()`
	def __init__(self, repo_root: Path) -> None:
		self.__repo_root = Path(repo_root).resolve()
	# @used-by :func:`agent_tools.xref.python_sync.sync_python_repo()`
	# @used-by :meth:`test_df_harness_s11_wave2b_xref.DfHarnessS11Wave2bXrefTests.test_python_xref_classes_and_engine_roundtrip()`
	def sync(self, *, apply: bool=True, files: list[str] | None=None) -> dict:
		repo_index = Model(self.__repo_root).build_repo_index()
		used_by = Graph(repo_index).build()
		target_rels = sorted(repo_index['files']) if None is files else [Path(f).as_posix() for f in files if Path(f).as_posix() in repo_index['files']]
		changed: list[str] = []
		for rel in target_rels:
			finfo = repo_index['files'][rel]
			if finfo['syntax_error']:
				continue
			updated = Syncer.__sync_file_source(finfo, repo_index, used_by)
			if updated != finfo['source']:
				changed.append(rel)
				if apply:
					(self.__repo_root / rel).write_text(updated, encoding='utf-8', newline='\n')
		return {'applied': apply, 'changed_count': len(changed), 'changed_files': changed, 'file_count': len(target_rels), 'lang': 'python', 'repo': self.__repo_root.as_posix(), 'valid': True}
	# @used-by :meth:`Syncer.__sync_def_edit()`
	@staticmethod
	def __build_def_replacement(dinfo: dict, header: dict, expected_used: list[str], override_see: str | None, need_ov: bool, lines: list[str]) -> tuple[int, int, list[str]]:
		indent = dinfo['indent']
		new_lines = list(header['prefix'])
		new_lines.extend((f'{indent}# @used-by {ref}' for ref in expected_used))
		new_lines.extend((entry['raw'] for entry in header['uses']))
		see_vals = [e['raw_value'] for e in header['see']]
		if None is not override_see and override_see not in see_vals:
			see_vals.append(override_see)
		new_lines.extend((f'{indent}# @see {sv}' for sv in sorted(dict.fromkeys(see_vals))))
		dec_slice = lines[dinfo['dec_lineno'] - 1:dinfo['lineno'] - 1]
		if need_ov and (not dinfo['has_override']):
			dec_slice = [*dec_slice, f'{indent}@override']
		new_lines.extend(dec_slice)
		return (header['start_line'] - 1, dinfo['lineno'] - 1, new_lines)
	# @used-by :meth:`Syncer.__check_file_xref()`
	@staticmethod
	def __check_def_xref(finfo: dict, dinfo: dict, repo_index: dict, used_by: dict[str, set[tuple[str, str]]], errs: list[str]) -> None:
		rel, mod, qn = (finfo['rel_path'], finfo['module'], dinfo['qualname'])
		hdr = Tags(finfo['lines'], dinfo['dec_lineno'], rel).parse_header_block()
		errs.extend(hdr['syntax_errors'])
		Syncer.__check_used_by_tags(rel, mod, dinfo, hdr, used_by.get(f'{mod}.{qn}', set()), repo_index, errs)
		Syncer.__check_see_tags(rel, mod, hdr, repo_index, errs)
		Syncer.__check_override_contract(finfo, dinfo, hdr, repo_index, errs)
	# @used-by :meth:`Syncer.check_repo()`
	@staticmethod
	def __check_file_xref(finfo: dict, repo_index: dict, used_by: dict[str, set[tuple[str, str]]], errs: list[str]) -> None:
		if finfo['syntax_error']:
			rel, syn_err = (finfo['rel_path'], finfo['syntax_error'])
			errs.append(f'XREF: {rel} syntax error: {syn_err}')
		else:
			Syncer.__validate_file_uses_tags(finfo, repo_index, errs)
			for dinfo in finfo['defs']:
				Syncer.__check_def_xref(finfo, dinfo, repo_index, used_by, errs)
	# @used-by :meth:`Syncer.__check_def_xref()`
	@staticmethod
	def __check_override_contract(finfo: dict, dinfo: dict, hdr: dict, repo_index: dict, errs: list[str]) -> None:
		ov_base = Syncer.__override_base_for_def(finfo, dinfo, repo_index)
		if None is not ov_base:
			rel, ln, qn = (finfo['rel_path'], dinfo['lineno'], dinfo['qualname'])
			if not dinfo['has_override']:
				errs.append(f'XREF: {rel}:{ln} overriding method {qn} missing @override decorator')
			elif not dinfo['override_valid_pos']:
				errs.append(f'XREF: {rel}:{ln} @override on {qn} must be the lowest decorator closest to def')
			expected_see = Syncer.__format_override_see(ov_base, finfo['module'])
			if not any((expected_see == e['raw_value'] or ov_base == (e['sphinx_target'] or '').rstrip('()') for e in hdr['see'])):
				errs.append(f'XREF: {rel}:{ln} overriding method {qn} missing # @see {expected_see}')
	# @used-by :meth:`Syncer.__check_def_xref()`
	@staticmethod
	def __check_see_tags(rel: str, mod: str, hdr: dict, repo_index: dict, errs: list[str]) -> None:
		for entry in hdr['see']:
			if entry['sphinx_target']:
				ok, _ = Tags.resolve_sphinx_target(entry['sphinx_target'], mod, repo_index)
				if not ok:
					eln, rval = (entry['lineno'], entry['raw_value'])
					errs.append(f'XREF: {rel}:{eln} unresolved @see target {rval}')
	# @used-by :meth:`Syncer.__check_def_xref()`
	@staticmethod
	def __check_used_by_tags(rel: str, mod: str, dinfo: dict, hdr: dict, computed: set[tuple[str, str]], repo_index: dict, errs: list[str]) -> None:
		actual_refs, manual_ext = Syncer.__collect_actual_used_by(rel, mod, hdr, repo_index, errs)
		expected = Syncer.__expected_used_by_lines(computed, manual_ext, mod)
		ln, qn = (dinfo['lineno'], dinfo['qualname'])
		if not actual_refs:
			errs.append(f'XREF: {rel}:{ln} function/method {qn} missing @used-by')
		elif sorted(set(actual_refs)) != expected or actual_refs != sorted(actual_refs):
			missing = sorted(set(expected) - set(actual_refs))
			stale = sorted(set(actual_refs) - set(expected))
			errs.append(f'XREF: {rel}:{ln} @used-by drift on {qn} (missing={missing[:3]}, stale={stale[:3]})')
	# @used-by :meth:`Syncer.__check_used_by_tags()`
	@staticmethod
	def __collect_actual_used_by(rel: str, mod: str, hdr: dict, repo_index: dict, errs: list[str]) -> tuple[list[str], list[str]]:
		actual_refs, manual_ext = ([], [])
		for entry in hdr['used_by']:
			rval, eln = (entry['raw_value'], entry['lineno'])
			actual_refs.append(rval)
			if entry['sphinx_target']:
				ok, _ = Tags.resolve_sphinx_target(entry['sphinx_target'], mod, repo_index)
				if not ok:
					errs.append(f'XREF: {rel}:{eln} unresolved @used-by target {rval}')
			elif Tags.is_valid_external_target(rval, repo_index['repo_root']):
				manual_ext.append(rval)
			else:
				errs.append(f'XREF: {rel}:{eln} invalid external @used-by target {rval}')
		return (actual_refs, manual_ext)
	# @used-by :meth:`Syncer.__check_used_by_tags()`
	# @used-by :meth:`Syncer.__sync_def_edit()`
	@staticmethod
	def __expected_used_by_lines(computed: set[tuple[str, str]], manual_ext: list[str], current_module: str) -> list[str]:
		refs = {Tags.format_ref(ckey, ckind, current_module) for ckey, ckind in computed}
		refs.update((m for m in manual_ext if 'unused' != m.split()[0]))
		if not refs:
			refs.update(manual_ext)
		return sorted(refs)
	# @used-by :meth:`Syncer.__check_override_contract()`
	# @used-by :meth:`Syncer.__sync_def_edit()`
	@staticmethod
	def __format_override_see(ov_base: str, current_module: str) -> str:
		return Tags.format_ref(ov_base, 'meth', current_module)
	# @used-by :meth:`Syncer.__sync_file_source()`
	@staticmethod
	def __insert_typing_override_import(lines: list[str]) -> list[str]:
		if any(('from typing import ' in ln and 'override' in ln for ln in lines)):
			r = lines
		else:
			pos = Syncer.__override_import_pos(lines)
			r = [*lines[:pos], 'from typing import override', *lines[pos:]]
		return r
	# @used-by :meth:`Syncer.__check_override_contract()`
	# @used-by :meth:`Syncer.__sync_def_edit()`
	@staticmethod
	def __override_base_for_def(finfo: dict, dinfo: dict, repo_index: dict) -> str | None:
		r: str | None = None
		if dinfo['is_method'] and dinfo['class_qualname']:
			cinfo = finfo['classes'].get(dinfo['class_qualname'])
			if None is not cinfo:
				r = Overrides(finfo, cinfo, repo_index).find_overridden_method(dinfo['name'])
		return r
	# @used-by :meth:`Syncer.__insert_typing_override_import()`
	@staticmethod
	def __override_import_pos(lines: list[str]) -> int:
		pos = 0
		for idx, ln in enumerate(lines):
			s = ln.strip()
			if s.startswith(('# @used-by', '# @uses', '# @see')):
				break
			if s.startswith('#') or s.startswith('from __future__ import'):
				pos = idx + 1
			elif s.startswith('from '):
				if 'from typing import override' < s:
					pos = idx
					break
				pos = idx + 1
			elif s:
				break
		return pos
	# @used-by :meth:`Syncer.__sync_file_source()`
	@staticmethod
	def __sync_def_edit(finfo: dict, dinfo: dict, lines: list[str], repo_index: dict, used_by: dict[str, set[tuple[str, str]]]) -> tuple[tuple[int, int, list[str]], bool]:
		mod, qn = (finfo['module'], dinfo['qualname'])
		hdr = Tags(lines, dinfo['dec_lineno'], finfo['rel_path']).parse_header_block()
		manual_ext = [e['raw_value'] for e in hdr['used_by'] if None is e['sphinx_target'] and Tags.is_valid_external_target(e['raw_value'], repo_index['repo_root'])]
		expected_used = Syncer.__expected_used_by_lines(used_by.get(f'{mod}.{qn}', set()), manual_ext, mod)
		ov_base = Syncer.__override_base_for_def(finfo, dinfo, repo_index)
		ov_see = Syncer.__format_override_see(ov_base, mod) if None is not ov_base else None
		need_ov = None is not ov_base
		edit = Syncer.__build_def_replacement(dinfo, hdr, expected_used, ov_see, need_ov, lines)
		return (edit, need_ov and (not dinfo['has_override']))
	# @used-by :meth:`Syncer.sync()`
	@staticmethod
	def __sync_file_source(finfo: dict, repo_index: dict, used_by: dict[str, set[tuple[str, str]]]) -> str:
		lines = list(finfo['lines'])
		edits: list[tuple[int, int, list[str]]] = []
		added_override = False
		for dinfo in finfo['defs']:
			edit, did_ov = Syncer.__sync_def_edit(finfo, dinfo, lines, repo_index, used_by)
			edits.append(edit)
			added_override = added_override or did_ov
		for start, end, repl in sorted(edits, key=lambda x: x[0], reverse=True):
			lines[start:end] = repl
		if added_override:
			lines = Syncer.__insert_typing_override_import(lines)
		trailing = '\n' if finfo['source'].endswith('\n') else ''
		return '\n'.join(lines) + trailing
	# @used-by :meth:`Syncer.__check_file_xref()`
	@staticmethod
	def __validate_file_uses_tags(finfo: dict, repo_index: dict, errs: list[str]) -> None:
		rel, mod = (finfo['rel_path'], finfo['module'])
		for item in Tags.collect_file_uses(finfo):
			if item['sphinx_target']:
				ok, _ = Tags.resolve_sphinx_target(item['sphinx_target'], mod, repo_index)
				if not ok:
					iln, rval = (item['lineno'], item['raw_value'])
					errs.append(f'XREF: {rel}:{iln} unresolved @uses target {rval}')
	# @used-by :func:`agent_tools.xref.python_sync.check_python_file_local()`
	# @used-by :meth:`Df.Harness.Gate.XrefChecker.XrefChecker.check()`
	@staticmethod
	def check_file_local(rel_posix: str, source: str, *, baseline_source: str | None=None, strict_existing: bool=False) -> list[str]:
		finfo = Model.index_file(rel_posix, '', source)
		errs: list[str] = []
		if not finfo['syntax_error']:
			base_missing: set[str] = set()
			if None is not baseline_source and (not strict_existing):
				binfo = Model.index_file(rel_posix, '', baseline_source)
				base_missing = {d['qualname'] for d in binfo['defs'] if not Tags(binfo['lines'], d['dec_lineno'], rel_posix).parse_header_block()['used_by']}
			for dinfo in finfo['defs']:
				hdr = Tags(finfo['lines'], dinfo['dec_lineno'], rel_posix).parse_header_block()
				errs.extend(hdr['syntax_errors'])
				ln, qn = (dinfo['lineno'], dinfo['qualname'])
				if not hdr['used_by'] and (strict_existing or qn not in base_missing):
					errs.append(f'XREF: {rel_posix}:{ln} function/method {qn} missing @used-by')
				if dinfo['has_override'] and (not dinfo['override_valid_pos']):
					errs.append(f'XREF: {rel_posix}:{ln} @override on {qn} must be closest decorator to def')
				if dinfo['has_override'] and (not hdr['see']):
					errs.append(f'XREF: {rel_posix}:{ln} @override method {qn} missing # @see reference')
		return errs
	# @used-by :func:`agent_tools.xref.python_sync.check_python_repo()`
	# @used-by :meth:`Df.Harness.Xref.Engine.Engine.check()`
	# @used-by :meth:`test_df_harness_s11_wave2b_xref_cov.DfHarnessS11Wave2bXrefCovTests.test_python_xref_covers_all_exports_with_overrides_and_stdlib_tags()`
	@staticmethod
	def check_repo(repo_root: Path, *, files: list[str] | None=None, overrides_map: dict[str, str] | None=None) -> dict:
		repo_index = Model(repo_root, overrides_map=overrides_map).build_repo_index()
		used_by = Graph(repo_index).build()
		target_rels = sorted(repo_index['files']) if None is files else [Path(f).as_posix() for f in files if Path(f).as_posix() in repo_index['files']]
		errs: list[str] = []
		for rel in target_rels:
			Syncer.__check_file_xref(repo_index['files'][rel], repo_index, used_by, errs)
		return {'file_count': len(target_rels), 'issue_count': len(errs), 'issues': errs, 'lang': 'python', 'repo': Path(repo_root).resolve().as_posix(), 'valid': not errs}
