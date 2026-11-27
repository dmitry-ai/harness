# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from pathlib import Path
from Df.Harness.Xref.Js.Graph import Graph
from Df.Harness.Xref.Js.Model import Model
from Df.Harness.Xref.Js.Tags import Tags
# 2026-11-26 "Move verification gate subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/381
class Syncer:
	# @used-by :func:`agent_tools.xref.js_sync.sync_js_repo()`
	# @used-by :meth:`test_df_harness_s11_wave2b_xref.DfHarnessS11Wave2bXrefTests.test_js_xref_classes_tokenize_imports_graph_and_sync()`
	def __init__(self, repo_root: Path) -> None:
		self.__repo_root = Path(repo_root).resolve()
	# @used-by :func:`agent_tools.xref.js_sync.sync_js_repo()`
	# @used-by :meth:`test_df_harness_s11_wave2b_xref.DfHarnessS11Wave2bXrefTests.test_js_xref_classes_tokenize_imports_graph_and_sync()`
	def sync(self, *, apply: bool=True, files: list[str] | None=None) -> dict:
		repo_index = Model(self.__repo_root).build_repo_index()
		used_by = Graph(repo_index).build()
		target_rels = sorted(repo_index['files']) if None is files else [Path(f).as_posix() for f in files if Path(f).as_posix() in repo_index['files']]
		changed: list[str] = []
		for rel in target_rels:
			finfo = repo_index['files'][rel]
			updated = Syncer.__sync_js_file_source(finfo, repo_index, used_by)
			if updated != finfo['source']:
				changed.append(rel)
				if apply:
					(self.__repo_root / rel).write_text(updated, encoding='utf-8', newline='\n')
		return {'applied': apply, 'changed_count': len(changed), 'changed_files': changed, 'file_count': len(target_rels), 'lang': 'js', 'repo': self.__repo_root.as_posix(), 'valid': True}
	# @used-by :meth:`Syncer.__sync_js_def_edit()`
	@staticmethod
	def __build_js_def_replacement(dinfo: dict, hdr: dict, expected_used: list[str], ov_see: str | None, need_jsdoc_ov: bool) -> tuple[int, int, list[str]]:
		indent = dinfo['indent']
		body = Syncer.__format_js_body_lines(hdr, expected_used, ov_see, need_jsdoc_ov, dinfo['is_ts'], indent)
		repl = [f'{indent}/**', *body, f'{indent} */'] if body else []
		start = hdr['start_line'] - 1 if hdr['has_block'] else dinfo['lineno'] - 1
		end = hdr['end_line'] if hdr['has_block'] else dinfo['lineno'] - 1
		return (start, end, repl)
	# @used-by :meth:`Syncer.__check_js_file()`
	@staticmethod
	def __check_js_def(finfo: dict, dinfo: dict, repo_index: dict, used_by: dict[str, set[str]], errs: list[str]) -> None:
		rel, qn = (finfo['rel_path'], dinfo['qualname'])
		hdr = Tags(finfo['lines'], dinfo['lineno'], rel).parse_jsdoc_block()
		errs.extend(hdr['syntax_errors'])
		Syncer.__check_js_used_by(rel, dinfo, hdr, used_by.get(f'{rel}::{qn}', set()), repo_index, errs)
		Syncer.__check_js_see_tags(rel, hdr, repo_index, errs)
		Syncer.__check_js_override(finfo, dinfo, hdr, repo_index, errs)
	# @used-by :meth:`Syncer.check_repo()`
	@staticmethod
	def __check_js_file(finfo: dict, repo_index: dict, used_by: dict[str, set[str]], errs: list[str]) -> None:
		Syncer.__validate_js_file_uses(finfo, repo_index, errs)
		for dinfo in finfo['defs']:
			Syncer.__check_js_def(finfo, dinfo, repo_index, used_by, errs)
	# @used-by :meth:`Syncer.__check_js_def()`
	@staticmethod
	def __check_js_override(finfo: dict, dinfo: dict, hdr: dict, repo_index: dict, errs: list[str]) -> None:
		ov_base = Graph.find_overridden_method(finfo, dinfo, repo_index)
		if None is not ov_base:
			rel, ln, qn = (finfo['rel_path'], dinfo['lineno'], dinfo['qualname'])
			if dinfo['is_ts']:
				if not dinfo['has_ts_override']:
					errs.append(f'XREF: {rel}:{ln} TS overriding method {qn} missing override keyword')
				if hdr['has_jsdoc_override']:
					errs.append(f'XREF: {rel}:{ln} TS overriding method {qn} must not use JSDoc @override')
			elif not hdr['has_jsdoc_override']:
				errs.append(f'XREF: {rel}:{ln} JS overriding method {qn} missing JSDoc @override')
			expected_see = Tags.format_ref(ov_base, rel, repo_index)
			if not any((expected_see == e['raw_value'] for e in hdr['see'])):
				errs.append(f'XREF: {rel}:{ln} overriding method {qn} missing @see {expected_see}')
	# @used-by :meth:`Syncer.__check_js_def()`
	@staticmethod
	def __check_js_see_tags(rel: str, hdr: dict, repo_index: dict, errs: list[str]) -> None:
		for entry in hdr['see']:
			if entry['link_target']:
				ok, _ = Tags.resolve_link(entry['link_target'], entry['note'], rel, repo_index)
				if not ok:
					ln, rval = (entry['lineno'], entry['raw_value'])
					errs.append(f'XREF: {rel}:{ln} unresolved @see target {rval}')
	# @used-by :meth:`Syncer.__check_js_def()`
	@staticmethod
	def __check_js_used_by(rel: str, dinfo: dict, hdr: dict, computed: set[str], repo_index: dict, errs: list[str]) -> None:
		actual, manual_ext = Syncer.__collect_actual_js_used_by(rel, hdr, repo_index, errs)
		expected = Syncer.__expected_js_used_by(computed, manual_ext, rel, repo_index)
		ln, qn = (dinfo['lineno'], dinfo['qualname'])
		if not actual:
			errs.append(f'XREF: {rel}:{ln} function/method {qn} missing @used-by')
		elif sorted(set(actual)) != expected or actual != sorted(actual):
			missing = sorted(set(expected) - set(actual))
			stale = sorted(set(actual) - set(expected))
			errs.append(f'XREF: {rel}:{ln} @used-by drift on {qn} (missing={missing[:3]}, stale={stale[:3]})')
	# @used-by :meth:`Syncer.__check_js_used_by()`
	@staticmethod
	def __collect_actual_js_used_by(rel: str, hdr: dict, repo_index: dict, errs: list[str]) -> tuple[list[str], list[str]]:
		actual, manual_ext = ([], [])
		for entry in hdr['used_by']:
			rval, eln = (entry['raw_value'], entry['lineno'])
			actual.append(rval)
			if entry['link_target']:
				ok, _ = Tags.resolve_link(entry['link_target'], entry['note'], rel, repo_index)
				if not ok:
					errs.append(f'XREF: {rel}:{eln} unresolved @used-by target {rval}')
			elif Tags.is_valid_external(rval, repo_index['repo_root']):
				manual_ext.append(rval)
			else:
				errs.append(f'XREF: {rel}:{eln} invalid external @used-by target {rval}')
		return (actual, manual_ext)
	# @used-by :meth:`Syncer.__check_js_used_by()`
	# @used-by :meth:`Syncer.__sync_js_def_edit()`
	@staticmethod
	def __expected_js_used_by(computed: set[str], manual_ext: list[str], current_rel: str, repo_index: dict) -> list[str]:
		refs = {Tags.format_ref(ck, current_rel, repo_index) for ck in computed}
		refs.update((m for m in manual_ext if 'unused' != m.split()[0]))
		if not refs:
			refs.update(manual_ext)
		return sorted(refs)
	# @used-by :meth:`Syncer.__build_js_def_replacement()`
	@staticmethod
	def __format_js_body_lines(hdr: dict, expected_used: list[str], ov_see: str | None, need_jsdoc_ov: bool, is_ts: bool, indent: str) -> list[str]:
		body = [f'{indent} * {ln}' for ln in hdr['desc_lines']]
		body.extend((f'{indent} * @used-by {ref}' for ref in expected_used))
		body.extend((f"{indent} * @uses {e['raw_value']}" for e in hdr['uses']))
		if need_jsdoc_ov or (hdr['has_jsdoc_override'] and (not is_ts)):
			body.append(f'{indent} * @override')
		see_vals = [e['raw_value'] for e in hdr['see']]
		if None is not ov_see and ov_see not in see_vals:
			see_vals.append(ov_see)
		body.extend((f'{indent} * @see {sv}' for sv in sorted(dict.fromkeys(see_vals))))
		return body
	# @used-by :meth:`Syncer.__sync_js_file_source()`
	@staticmethod
	def __sync_js_def_edit(finfo: dict, dinfo: dict, lines: list[str], repo_index: dict, used_by: dict[str, set[str]]) -> tuple[int, int, list[str]]:
		rel, qn = (finfo['rel_path'], dinfo['qualname'])
		hdr = Tags(lines, dinfo['lineno'], rel).parse_jsdoc_block()
		manual_ext = [e['raw_value'] for e in hdr['used_by'] if None is e['link_target'] and Tags.is_valid_external(e['raw_value'], repo_index['repo_root'])]
		expected_used = Syncer.__expected_js_used_by(used_by.get(f'{rel}::{qn}', set()), manual_ext, rel, repo_index)
		ov_base = Graph.find_overridden_method(finfo, dinfo, repo_index)
		ov_see = Tags.format_ref(ov_base, rel, repo_index) if None is not ov_base else None
		need_jsdoc_ov = None is not ov_base and (not dinfo['is_ts'])
		return Syncer.__build_js_def_replacement(dinfo, hdr, expected_used, ov_see, need_jsdoc_ov)
	# @used-by :meth:`Syncer.sync()`
	@staticmethod
	def __sync_js_file_source(finfo: dict, repo_index: dict, used_by: dict[str, set[str]]) -> str:
		lines = list(finfo['lines'])
		edits = [Syncer.__sync_js_def_edit(finfo, dinfo, lines, repo_index, used_by) for dinfo in finfo['defs']]
		for start, end, repl in sorted(edits, key=lambda x: x[0], reverse=True):
			lines[start:end] = repl
		trailing = '\n' if finfo['source'].endswith('\n') else ''
		return '\n'.join(lines) + trailing
	# @used-by :meth:`Syncer.__check_js_file()`
	@staticmethod
	def __validate_js_file_uses(finfo: dict, repo_index: dict, errs: list[str]) -> None:
		rel = finfo['rel_path']
		for item in Tags.collect_file_uses(finfo):
			if item['link_target']:
				ok, _ = Tags.resolve_link(item['link_target'], item['note'], rel, repo_index)
				if not ok:
					ln, rval = (item['lineno'], item['raw_value'])
					errs.append(f'XREF: {rel}:{ln} unresolved @uses target {rval}')
	# @used-by :func:`agent_tools.xref.js_sync.check_js_file_local()`
	# @used-by :meth:`Df.Harness.Gate.XrefChecker.XrefChecker.check()`
	# @used-by :meth:`test_df_harness_s11_wave2b_xref.DfHarnessS11Wave2bXrefTests.test_js_xref_classes_tokenize_imports_graph_and_sync()`
	@staticmethod
	def check_file_local(rel_posix: str, source: str, *, baseline_source: str | None=None, strict_existing: bool=False) -> list[str]:
		finfo = Model.index_file(rel_posix, source)
		errs: list[str] = []
		base_missing: set[str] = set()
		if None is not baseline_source and (not strict_existing):
			binfo = Model.index_file(rel_posix, baseline_source)
			base_missing = {d['qualname'] for d in binfo['defs'] if not Tags(binfo['lines'], d['lineno'], rel_posix).parse_jsdoc_block()['used_by']}
		for dinfo in finfo['defs']:
			hdr = Tags(finfo['lines'], dinfo['lineno'], rel_posix).parse_jsdoc_block()
			errs.extend(hdr['syntax_errors'])
			ln, qn = (dinfo['lineno'], dinfo['qualname'])
			if not hdr['used_by'] and (strict_existing or qn not in base_missing):
				errs.append(f'XREF: {rel_posix}:{ln} function/method {qn} missing @used-by')
			if (hdr['has_jsdoc_override'] or dinfo['has_ts_override']) and (not hdr['see']):
				errs.append(f'XREF: {rel_posix}:{ln} overriding method {qn} missing @see reference')
		return errs
	# @used-by :func:`agent_tools.xref.js_sync.check_js_repo()`
	# @used-by :meth:`Df.Harness.Xref.Engine.Engine.check()`
	@staticmethod
	def check_repo(repo_root: Path, *, files: list[str] | None=None, overrides_map: dict[str, str] | None=None) -> dict:
		repo_index = Model(repo_root, overrides_map=overrides_map).build_repo_index()
		used_by = Graph(repo_index).build()
		target_rels = sorted(repo_index['files']) if None is files else [Path(f).as_posix() for f in files if Path(f).as_posix() in repo_index['files']]
		errs: list[str] = []
		for rel in target_rels:
			Syncer.__check_js_file(repo_index['files'][rel], repo_index, used_by, errs)
		return {'file_count': len(target_rels), 'issue_count': len(errs), 'issues': errs, 'lang': 'js', 'repo': Path(repo_root).resolve().as_posix(), 'valid': not errs}
