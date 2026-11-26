# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from pathlib import Path
from .java_graph import build_java_call_graph, find_java_overridden_method
from .java_model import build_java_repo_index, index_java_file
from .java_tags import collect_file_java_uses, format_java_ref, is_valid_java_external, parse_javadoc_block, resolve_java_target
# 2026-11-26
# "Extend cross-reference engine for JS/TS and Java":
# https://github.com/dmitry-ai/harness/issues/301
# @used-by :func:`_sync_java_def_edit()`
def _build_java_def_replacement(dinfo: dict, hdr: dict, expected_used: list[str], ov_see: str | None) -> tuple[int, int, list[str]]:
	indent = dinfo['indent']
	body = [f'{indent} * {ln}' for ln in hdr['desc_lines']]
	body.extend((f'{indent} * - @used-by {ref}' for ref in expected_used))
	body.extend((f"{indent} * - @uses {e['raw_value']}" for e in hdr['uses']))
	see_vals = [e['raw_value'] for e in hdr['see']]
	if None is not ov_see and ov_see not in see_vals:
		see_vals.append(ov_see)
	body.extend((f'{indent} * @see {sv}' for sv in sorted(dict.fromkeys(see_vals))))
	repl = [f'{indent}/**', *body, f'{indent} */'] if body else []
	start = hdr['start_line'] - 1 if hdr['has_block'] else dinfo['doc_anchor_line'] - 1
	end = hdr['end_line'] if hdr['has_block'] else dinfo['doc_anchor_line'] - 1
	return (start, end, repl)
# @used-by :func:`_check_java_file()`
def _check_java_def(finfo: dict, dinfo: dict, repo_index: dict, used_by: dict[str, set[str]], errs: list[str]) -> None:
	rel = finfo['rel_path']
	skey = dinfo['symbol_key']
	hdr = parse_javadoc_block(finfo['lines'], dinfo['doc_anchor_line'], rel)
	errs.extend(hdr['syntax_errors'])
	_check_java_used_by(finfo, dinfo, hdr, used_by.get(skey, set()), repo_index, errs)
	_check_java_override(finfo, dinfo, hdr, repo_index, errs)
# @used-by :func:`check_java_repo()`
def _check_java_file(finfo: dict, repo_index: dict, used_by: dict[str, set[str]], errs: list[str]) -> None:
	_validate_java_file_uses(finfo, repo_index, errs)
	for dinfo in finfo['defs']:
		_check_java_def(finfo, dinfo, repo_index, used_by, errs)
# @used-by :func:`_check_java_def()`
def _check_java_override(finfo: dict, dinfo: dict, hdr: dict, repo_index: dict, errs: list[str]) -> None:
	ov_base = find_java_overridden_method(finfo, dinfo, repo_index)
	if None is not ov_base:
		rel, ln, sig = (finfo['rel_path'], dinfo['lineno'], dinfo['sig'])
		if not dinfo['has_override']:
			errs.append(f'XREF: {rel}:{ln} overriding method {sig} missing @Override annotation')
		expected_see = format_java_ref(ov_base, finfo, repo_index, wrap_link=False)
		if not any((expected_see == e['raw_value'] or ov_base == e['raw_value'] for e in hdr['see'])):
			errs.append(f'XREF: {rel}:{ln} overriding method {sig} missing @see {expected_see}')
	elif dinfo['has_override'] and (not hdr['see']):
		rel, ln, sig = (finfo['rel_path'], dinfo['lineno'], dinfo['sig'])
		errs.append(f'XREF: {rel}:{ln} @Override method {sig} missing @see reference')
# @used-by :func:`_check_java_def()`
def _check_java_used_by(finfo: dict, dinfo: dict, hdr: dict, computed: set[str], repo_index: dict, errs: list[str]) -> None:
	actual, manual_ext = _collect_actual_java_used_by(finfo, hdr, repo_index, errs)
	expected = _expected_java_used_by(computed, manual_ext, finfo, repo_index)
	rel, ln, sig = (finfo['rel_path'], dinfo['lineno'], dinfo['sig'])
	if not actual:
		errs.append(f'XREF: {rel}:{ln} Java method/constructor {sig} missing - @used-by')
	elif sorted(set(actual)) != expected or actual != sorted(actual):
		missing = sorted(set(expected) - set(actual))
		stale = sorted(set(actual) - set(expected))
		errs.append(f'XREF: {rel}:{ln} - @used-by drift on {sig} (missing={missing[:3]}, stale={stale[:3]})')
# @used-by :func:`_check_java_used_by()`
def _collect_actual_java_used_by(finfo: dict, hdr: dict, repo_index: dict, errs: list[str]) -> tuple[list[str], list[str]]:
	rel = finfo['rel_path']
	actual, manual_ext = ([], [])
	for entry in hdr['used_by']:
		rval, eln = (entry['raw_value'], entry['lineno'])
		actual.append(rval)
		if entry['link_target']:
			ok, _ = resolve_java_target(entry['link_target'], finfo, repo_index)
			if not ok:
				errs.append(f'XREF: {rel}:{eln} unresolved - @used-by target {rval}')
		elif is_valid_java_external(rval, repo_index['repo_root']):
			manual_ext.append(rval)
		else:
			errs.append(f'XREF: {rel}:{eln} invalid external - @used-by target {rval}')
	return (actual, manual_ext)
# 2026-11-26
# "Apply cross-reference annotations across Harness Python and JavaScript":
# https://github.com/dmitry-ai/harness/issues/305
# @used-by :func:`_check_java_used_by()`
# @used-by :func:`_sync_java_def_edit()`
def _expected_java_used_by(computed: set[str], manual_ext: list[str], current_finfo: dict, repo_index: dict) -> list[str]:
	refs = {format_java_ref(ck, current_finfo, repo_index, wrap_link=True) for ck in computed}
	refs.update((m for m in manual_ext if 'unused' != m.split()[0]))
	if not refs:
		refs.update(manual_ext)
	return sorted(refs)
# @used-by :func:`_sync_java_file_source()`
def _sync_java_def_edit(finfo: dict, dinfo: dict, lines: list[str], repo_index: dict, used_by: dict[str, set[str]]) -> tuple[int, int, list[str]]:
	skey = dinfo['symbol_key']
	hdr = parse_javadoc_block(lines, dinfo['doc_anchor_line'], finfo['rel_path'])
	manual_ext = [e['raw_value'] for e in hdr['used_by'] if None is e['link_target'] and is_valid_java_external(e['raw_value'], repo_index['repo_root'])]
	expected_used = _expected_java_used_by(used_by.get(skey, set()), manual_ext, finfo, repo_index)
	ov_base = find_java_overridden_method(finfo, dinfo, repo_index)
	ov_see = format_java_ref(ov_base, finfo, repo_index, wrap_link=False) if None is not ov_base else None
	return _build_java_def_replacement(dinfo, hdr, expected_used, ov_see)
# @used-by :func:`sync_java_repo()`
def _sync_java_file_source(finfo: dict, repo_index: dict, used_by: dict[str, set[str]]) -> str:
	lines = list(finfo['lines'])
	edits = [_sync_java_def_edit(finfo, dinfo, lines, repo_index, used_by) for dinfo in finfo['defs']]
	for start, end, repl in sorted(edits, key=lambda x: x[0], reverse=True):
		lines[start:end] = repl
	trailing = '\n' if finfo['source'].endswith('\n') else ''
	return '\n'.join(lines) + trailing
# @used-by :func:`_check_java_file()`
def _validate_java_file_uses(finfo: dict, repo_index: dict, errs: list[str]) -> None:
	rel = finfo['rel_path']
	for item in collect_file_java_uses(finfo):
		if item['link_target']:
			ok, _ = resolve_java_target(item['link_target'], finfo, repo_index)
			if not ok:
				ln, rval = (item['lineno'], item['raw_value'])
				errs.append(f'XREF: {rel}:{ln} unresolved - @uses target {rval}')
# @used-by :mod:`agent_tools.xref`
def check_java_file_local(rel_posix: str, source: str, *, baseline_source: str | None=None, strict_existing: bool=False) -> list[str]:
	finfo = index_java_file(rel_posix, source)
	errs: list[str] = []
	base_missing: set[str] = set()
	if None is not baseline_source and (not strict_existing):
		binfo = index_java_file(rel_posix, baseline_source)
		base_missing = {d['symbol_key'] for d in binfo['defs'] if not parse_javadoc_block(binfo['lines'], d['doc_anchor_line'], rel_posix)['used_by']}
	for dinfo in finfo['defs']:
		hdr = parse_javadoc_block(finfo['lines'], dinfo['doc_anchor_line'], rel_posix)
		errs.extend(hdr['syntax_errors'])
		ln, sig = (dinfo['lineno'], dinfo['sig'])
		if not hdr['used_by'] and (strict_existing or dinfo['symbol_key'] not in base_missing):
			errs.append(f'XREF: {rel_posix}:{ln} Java method/constructor {sig} missing - @used-by')
		if dinfo['has_override'] and (not hdr['see']):
			errs.append(f'XREF: {rel_posix}:{ln} @Override method {sig} missing @see reference')
	return errs
# @used-by :func:`agent_tools.xref.run_xref_check()`
# @used-by :meth:`test_java_xref.JavaXrefTests.test_java_anonymous_class_overloads_and_plugin_xml()`
# @used-by :meth:`test_java_xref.JavaXrefTests.test_java_rejects_bare_used_by_and_uses_block_tags()`
# @used-by :meth:`test_java_xref.JavaXrefTests.test_java_see_override_edges_unused_and_lf_sync()`
# @used-by :meth:`test_java_xref.JavaXrefTests.test_java_sync_and_check_overrides_records_and_uses()`
# @used-by :mod:`agent_tools.xref`
def check_java_repo(repo_root: Path, *, files: list[str] | None=None, overrides_map: dict[str, str] | None=None) -> dict:
	repo_index = build_java_repo_index(repo_root, overrides_map=overrides_map)
	used_by = build_java_call_graph(repo_index)
	target_rels = sorted(repo_index['files']) if None is files else [Path(f).as_posix() for f in files if Path(f).as_posix() in repo_index['files']]
	errs: list[str] = []
	for rel in target_rels:
		_check_java_file(repo_index['files'][rel], repo_index, used_by, errs)
	return {'file_count': len(target_rels), 'issue_count': len(errs), 'issues': errs, 'lang': 'java', 'repo': Path(repo_root).resolve().as_posix(), 'valid': not errs}
# @used-by :func:`agent_tools.xref.run_xref_sync()`
# @used-by :meth:`test_java_xref.JavaXrefTests.test_java_anonymous_class_overloads_and_plugin_xml()`
# @used-by :meth:`test_java_xref.JavaXrefTests.test_java_see_override_edges_unused_and_lf_sync()`
# @used-by :meth:`test_java_xref.JavaXrefTests.test_java_sync_and_check_overrides_records_and_uses()`
# @used-by :mod:`agent_tools.xref`
def sync_java_repo(repo_root: Path, *, apply: bool=True, files: list[str] | None=None) -> dict:
	root = Path(repo_root).resolve()
	repo_index = build_java_repo_index(root)
	used_by = build_java_call_graph(repo_index)
	target_rels = sorted(repo_index['files']) if None is files else [Path(f).as_posix() for f in files if Path(f).as_posix() in repo_index['files']]
	changed: list[str] = []
	for rel in target_rels:
		finfo = repo_index['files'][rel]
		updated = _sync_java_file_source(finfo, repo_index, used_by)
		if updated != finfo['source']:
			changed.append(rel)
			if apply:
				# 2026-11-26
				# "Apply cross-reference annotations across Harness Python and JavaScript":
				# https://github.com/dmitry-ai/harness/issues/305
				(root / rel).write_text(updated, encoding='utf-8', newline='\n')
	return {'applied': apply, 'changed_count': len(changed), 'changed_files': changed, 'file_count': len(target_rels), 'lang': 'java', 'repo': root.as_posix(), 'valid': True}
