# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from pathlib import Path
from .js_graph import build_js_call_graph, find_js_overridden_method
from .js_model import build_js_repo_index, index_js_file
from .js_tags import collect_file_js_uses, format_js_ref, is_valid_js_external, parse_jsdoc_block, resolve_js_link
# 2026-11-26
# "Extend cross-reference engine for JS/TS and Java":
# https://github.com/dmitry-ai/harness/issues/301
# @used-by :func:`_sync_js_def_edit()`
def _build_js_def_replacement(dinfo: dict, hdr: dict, expected_used: list[str], ov_see: str | None, need_jsdoc_ov: bool) -> tuple[int, int, list[str]]:
	indent = dinfo['indent']
	body = _format_js_body_lines(hdr, expected_used, ov_see, need_jsdoc_ov, dinfo['is_ts'], indent)
	repl = [f'{indent}/**', *body, f'{indent} */'] if body else []
	start = hdr['start_line'] - 1 if hdr['has_block'] else dinfo['lineno'] - 1
	end = hdr['end_line'] if hdr['has_block'] else dinfo['lineno'] - 1
	return (start, end, repl)
# @used-by :func:`_build_js_def_replacement()`
def _format_js_body_lines(hdr: dict, expected_used: list[str], ov_see: str | None, need_jsdoc_ov: bool, is_ts: bool, indent: str) -> list[str]:
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
# @used-by :func:`_check_js_file()`
def _check_js_def(finfo: dict, dinfo: dict, repo_index: dict, used_by: dict[str, set[str]], errs: list[str]) -> None:
	rel, qn = (finfo['rel_path'], dinfo['qualname'])
	skey = f'{rel}::{qn}'
	hdr = parse_jsdoc_block(finfo['lines'], dinfo['lineno'], rel)
	errs.extend(hdr['syntax_errors'])
	_check_js_used_by(rel, dinfo, hdr, used_by.get(skey, set()), repo_index, errs)
	_check_js_see_tags(rel, hdr, repo_index, errs)
	_check_js_override(finfo, dinfo, hdr, repo_index, errs)
# @used-by :func:`check_js_repo()`
def _check_js_file(finfo: dict, repo_index: dict, used_by: dict[str, set[str]], errs: list[str]) -> None:
	_validate_js_file_uses(finfo, repo_index, errs)
	for dinfo in finfo['defs']:
		_check_js_def(finfo, dinfo, repo_index, used_by, errs)
# @used-by :func:`_check_js_def()`
def _check_js_override(finfo: dict, dinfo: dict, hdr: dict, repo_index: dict, errs: list[str]) -> None:
	ov_base = find_js_overridden_method(finfo, dinfo, repo_index)
	if None is not ov_base:
		rel, ln, qn = (finfo['rel_path'], dinfo['lineno'], dinfo['qualname'])
		if dinfo['is_ts']:
			if not dinfo['has_ts_override']:
				errs.append(f'XREF: {rel}:{ln} TS overriding method {qn} missing override keyword')
			if hdr['has_jsdoc_override']:
				errs.append(f'XREF: {rel}:{ln} TS overriding method {qn} must not use JSDoc @override')
		elif not hdr['has_jsdoc_override']:
			errs.append(f'XREF: {rel}:{ln} JS overriding method {qn} missing JSDoc @override')
		expected_see = format_js_ref(ov_base, rel, repo_index)
		if not any((expected_see == e['raw_value'] for e in hdr['see'])):
			errs.append(f'XREF: {rel}:{ln} overriding method {qn} missing @see {expected_see}')
# @used-by :func:`_check_js_def()`
def _check_js_see_tags(rel: str, hdr: dict, repo_index: dict, errs: list[str]) -> None:
	for entry in hdr['see']:
		if entry['link_target']:
			ok, _ = resolve_js_link(entry['link_target'], entry['note'], rel, repo_index)
			if not ok:
				ln, rval = (entry['lineno'], entry['raw_value'])
				errs.append(f'XREF: {rel}:{ln} unresolved @see target {rval}')
# @used-by :func:`_check_js_def()`
def _check_js_used_by(rel: str, dinfo: dict, hdr: dict, computed: set[str], repo_index: dict, errs: list[str]) -> None:
	actual, manual_ext = _collect_actual_js_used_by(rel, hdr, repo_index, errs)
	expected = _expected_js_used_by(computed, manual_ext, rel, repo_index)
	ln, qn = (dinfo['lineno'], dinfo['qualname'])
	if not actual:
		errs.append(f'XREF: {rel}:{ln} function/method {qn} missing @used-by')
	elif sorted(set(actual)) != expected or actual != sorted(actual):
		missing = sorted(set(expected) - set(actual))
		stale = sorted(set(actual) - set(expected))
		errs.append(f'XREF: {rel}:{ln} @used-by drift on {qn} (missing={missing[:3]}, stale={stale[:3]})')
# @used-by :func:`_check_js_used_by()`
def _collect_actual_js_used_by(rel: str, hdr: dict, repo_index: dict, errs: list[str]) -> tuple[list[str], list[str]]:
	actual, manual_ext = ([], [])
	for entry in hdr['used_by']:
		rval, eln = (entry['raw_value'], entry['lineno'])
		actual.append(rval)
		if entry['link_target']:
			ok, _ = resolve_js_link(entry['link_target'], entry['note'], rel, repo_index)
			if not ok:
				errs.append(f'XREF: {rel}:{eln} unresolved @used-by target {rval}')
		elif is_valid_js_external(rval, repo_index['repo_root']):
			manual_ext.append(rval)
		else:
			errs.append(f'XREF: {rel}:{eln} invalid external @used-by target {rval}')
	return (actual, manual_ext)
# 2026-11-26
# "Apply cross-reference annotations across Harness Python and JavaScript":
# https://github.com/dmitry-ai/harness/issues/305
# @used-by :func:`_check_js_used_by()`
# @used-by :func:`_sync_js_def_edit()`
def _expected_js_used_by(computed: set[str], manual_ext: list[str], current_rel: str, repo_index: dict) -> list[str]:
	refs = {format_js_ref(ck, current_rel, repo_index) for ck in computed}
	refs.update((m for m in manual_ext if 'unused' != m.split()[0]))
	if not refs:
		refs.update(manual_ext)
	return sorted(refs)
# @used-by :func:`_sync_js_file_source()`
def _sync_js_def_edit(finfo: dict, dinfo: dict, lines: list[str], repo_index: dict, used_by: dict[str, set[str]]) -> tuple[int, int, list[str]]:
	rel, qn = (finfo['rel_path'], dinfo['qualname'])
	skey = f'{rel}::{qn}'
	hdr = parse_jsdoc_block(lines, dinfo['lineno'], rel)
	manual_ext = [e['raw_value'] for e in hdr['used_by'] if None is e['link_target'] and is_valid_js_external(e['raw_value'], repo_index['repo_root'])]
	expected_used = _expected_js_used_by(used_by.get(skey, set()), manual_ext, rel, repo_index)
	ov_base = find_js_overridden_method(finfo, dinfo, repo_index)
	ov_see = format_js_ref(ov_base, rel, repo_index) if None is not ov_base else None
	need_jsdoc_ov = None is not ov_base and (not dinfo['is_ts'])
	return _build_js_def_replacement(dinfo, hdr, expected_used, ov_see, need_jsdoc_ov)
# @used-by :func:`sync_js_repo()`
def _sync_js_file_source(finfo: dict, repo_index: dict, used_by: dict[str, set[str]]) -> str:
	lines = list(finfo['lines'])
	edits = [_sync_js_def_edit(finfo, dinfo, lines, repo_index, used_by) for dinfo in finfo['defs']]
	for start, end, repl in sorted(edits, key=lambda x: x[0], reverse=True):
		lines[start:end] = repl
	trailing = '\n' if finfo['source'].endswith('\n') else ''
	return '\n'.join(lines) + trailing
# @used-by :func:`_check_js_file()`
def _validate_js_file_uses(finfo: dict, repo_index: dict, errs: list[str]) -> None:
	rel = finfo['rel_path']
	for item in collect_file_js_uses(finfo):
		if item['link_target']:
			ok, _ = resolve_js_link(item['link_target'], item['note'], rel, repo_index)
			if not ok:
				ln, rval = (item['lineno'], item['raw_value'])
				errs.append(f'XREF: {rel}:{ln} unresolved @uses target {rval}')
# @used-by :meth:`Df.Harness.Gate.XrefChecker.XrefChecker.check()`
# @used-by :mod:`agent_tools.xref`
def check_js_file_local(rel_posix: str, source: str, *, baseline_source: str | None=None, strict_existing: bool=False) -> list[str]:
	finfo = index_js_file(rel_posix, source)
	errs: list[str] = []
	base_missing: set[str] = set()
	if None is not baseline_source and (not strict_existing):
		binfo = index_js_file(rel_posix, baseline_source)
		base_missing = {d['qualname'] for d in binfo['defs'] if not parse_jsdoc_block(binfo['lines'], d['lineno'], rel_posix)['used_by']}
	for dinfo in finfo['defs']:
		hdr = parse_jsdoc_block(finfo['lines'], dinfo['lineno'], rel_posix)
		errs.extend(hdr['syntax_errors'])
		ln, qn = (dinfo['lineno'], dinfo['qualname'])
		if not hdr['used_by'] and (strict_existing or qn not in base_missing):
			errs.append(f'XREF: {rel_posix}:{ln} function/method {qn} missing @used-by')
		if (hdr['has_jsdoc_override'] or dinfo['has_ts_override']) and (not hdr['see']):
			errs.append(f'XREF: {rel_posix}:{ln} overriding method {qn} missing @see reference')
	return errs
# @used-by :func:`agent_tools.xref.run_xref_check()`
# @used-by :meth:`test_js_xref.JsXrefTests.test_js_global_assignment_and_top_level_listener_edges()`
# @used-by :meth:`test_js_xref.JsXrefTests.test_js_override_and_ts_override_require_see_and_modifier()`
# @used-by :meth:`test_js_xref.JsXrefTests.test_js_sync_and_check_commonjs_esm_classes_and_uses()`
# @used-by :meth:`test_js_xref.JsXrefTests.test_js_validator_rejects_broken_and_missing_used_by()`
# @used-by :mod:`agent_tools.xref`
def check_js_repo(repo_root: Path, *, files: list[str] | None=None, overrides_map: dict[str, str] | None=None) -> dict:
	repo_index = build_js_repo_index(repo_root, overrides_map=overrides_map)
	used_by = build_js_call_graph(repo_index)
	target_rels = sorted(repo_index['files']) if None is files else [Path(f).as_posix() for f in files if Path(f).as_posix() in repo_index['files']]
	errs: list[str] = []
	for rel in target_rels:
		_check_js_file(repo_index['files'][rel], repo_index, used_by, errs)
	return {'file_count': len(target_rels), 'issue_count': len(errs), 'issues': errs, 'lang': 'js', 'repo': Path(repo_root).resolve().as_posix(), 'valid': not errs}
# @used-by :func:`agent_tools.xref.run_xref_sync()`
# @used-by :meth:`test_js_xref.JsXrefTests.test_js_global_assignment_and_top_level_listener_edges()`
# @used-by :meth:`test_js_xref.JsXrefTests.test_js_override_and_ts_override_require_see_and_modifier()`
# @used-by :meth:`test_js_xref.JsXrefTests.test_js_sync_and_check_commonjs_esm_classes_and_uses()`
# @used-by :mod:`agent_tools.xref`
def sync_js_repo(repo_root: Path, *, apply: bool=True, files: list[str] | None=None) -> dict:
	root = Path(repo_root).resolve()
	repo_index = build_js_repo_index(root)
	used_by = build_js_call_graph(repo_index)
	target_rels = sorted(repo_index['files']) if None is files else [Path(f).as_posix() for f in files if Path(f).as_posix() in repo_index['files']]
	changed: list[str] = []
	for rel in target_rels:
		finfo = repo_index['files'][rel]
		updated = _sync_js_file_source(finfo, repo_index, used_by)
		if updated != finfo['source']:
			changed.append(rel)
			if apply:
				# 2026-11-26
				# "Apply cross-reference annotations across Harness Python and JavaScript":
				# https://github.com/dmitry-ai/harness/issues/305
				(root / rel).write_text(updated, encoding='utf-8', newline='\n')
	return {'applied': apply, 'changed_count': len(changed), 'changed_files': changed, 'file_count': len(target_rels), 'lang': 'js', 'repo': root.as_posix(), 'valid': True}
