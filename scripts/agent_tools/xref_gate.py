# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from pathlib import Path
from .python_integrity import _git_read_text
from .shell_audit import normalize_host_path
from .tdd_gate import _compute_edited_content, _git_head_text, _git_index_text
from .xref import check_java_file_local, check_js_file_local, check_python_file_local, run_xref_check
import os
import re
import tempfile
# 2026-11-26
# "Enforce cross-reference compliance in PreToolUse and Git gates":
# https://github.com/dmitry-ai/harness/issues/306
_DEF_HINT_RE = {
	'java': re.compile(r'\)\s*(?:throws\b[^{;]*)?\{'),
	'js': re.compile(r'\bfunction\b|=>|\)\s*\{'),
	'python': re.compile(r'^\s*(?:async\s+)?def\s+\w+', re.M),
}
_EXT_TO_LANG = {
	'.cjs': 'js',
	'.java': 'java',
	'.js': 'js',
	'.jsx': 'js',
	'.mjs': 'js',
	'.py': 'python',
	'.ts': 'js',
	'.tsx': 'js',
}
_LANG_EXTS = {
	'java': ('.java',),
	'js': ('.cjs', '.js', '.jsx', '.mjs', '.ts', '.tsx'),
	'python': ('.py',),
}
_SKIP_PARTS = frozenset({'.git', '.venv', '__pycache__', 'build', 'dist', 'node_modules', 'out', 'target', 'venv', '\ua616', '\ua66e'})
# @used-by :func:`_resolve_xref_target()`
def _find_git_root(path: Path) -> Path | None:
	start = path if path.is_dir() else path.parent
	r = None
	for anc in (start, *start.parents):
		if (anc / '.git').exists():
			r = anc
			break
	return r
# @used-by :func:`check_file_xref_violations()`
# @used-by :func:`verify_staged_xref()`
# @used-by :func:`verify_worktree_xref_changes()`
def _format_xref_error(msg: str) -> str:
	return f'XREF-GATE: {msg[6:]}' if msg.startswith('XREF: ') else (msg if msg.startswith('XREF-GATE:') else f'XREF-GATE: {msg}')
# @used-by :func:`verify_worktree_xref_changes()`
def _git_changed_paths(wt_path: Path, target_branch: str) -> list[str]:
	raw = _git_read_text(wt_path, 'diff', '--name-only', '--diff-filter=ACMRD', f'{target_branch}..HEAD') or ''
	return sorted({ln.strip().replace('\\', '/') for ln in raw.splitlines() if ln.strip()})
# @used-by :func:`_has_xref_signal()`
# @used-by :func:`_is_repo_lang_synced()`
# @used-by :func:`check_file_xref_violations()`
# @used-by :func:`is_xref_governed_repo()`
def _has_xref_marker(text: str | None) -> bool:
	s = text or ''
	return '@used-by' in s or '@uses' in s
# @used-by :func:`_is_pre_tool_governed()`
def _has_xref_signal(text: str | None) -> bool:
	s = text or ''
	return _has_xref_marker(s) or '@override' in s or '@Override' in s
# @used-by :func:`_is_pre_tool_governed()`
# @used-by :func:`_is_repo_lang_synced()`
# @used-by :func:`is_xref_governed_repo()`
def _is_in_tempdir(path: Path) -> bool:
	try:
		r = Path(path).resolve().is_relative_to(Path(tempfile.gettempdir()).resolve())
	except (OSError, ValueError):
		r = False
	return r
# @used-by :func:`evaluate_pre_tool_use_xref()`
def _is_pre_tool_governed(repo_root: Path | None, target: Path, new_text: str) -> bool:
	if (not _is_in_tempdir(target)) or _has_xref_signal(new_text):
		r = True
	elif None is not repo_root:
		r = is_xref_governed_repo(repo_root)
	else:
		r = False
	return r
# @used-by :func:`verify_staged_xref()`
# @used-by :func:`verify_worktree_xref_changes()`
def _is_repo_lang_synced(repo: Path, lang: str, changed_rels: set[str]) -> bool:
	pat = _DEF_HINT_RE[lang]
	total, annotated = (0, 0)
	for rel, fp in _iter_repo_source_files(repo, _LANG_EXTS[lang]):
		if rel in changed_rels:
			continue
		txt = fp.read_text(encoding='utf-8', errors='replace')
		if pat.search(txt):
			total += 1
			if _has_xref_marker(txt):
				annotated += 1
	return 0 == total or annotated == total or ((not _is_in_tempdir(repo)) and annotated * 10 >= total * 9)
# @used-by :func:`_lang_for_rel()`
# @used-by :func:`_resolve_xref_target()`
def _is_skipped_rel(rel: str) -> bool:
	return any((p in _SKIP_PARTS or p.lower() in _SKIP_PARTS for p in Path(rel).parts))
# 2026-11-26 "Add Df package dot-py bootstrap and dot-py support across Harness gates": https://github.com/dmitry-ai/harness/issues/320
# @used-by :func:`_iter_repo_source_files()`
# @used-by :func:`_lang_for_rel()`
# @used-by :func:`_resolve_xref_target()`
def _path_suffix(path: str | Path) -> str:
	p = Path(path)
	return p.suffix.lower() or (p.name.lower() if p.name.startswith('.') else '')
# @used-by :func:`_is_repo_lang_synced()`
# @used-by :func:`is_xref_governed_repo()`
def _iter_repo_source_files(repo: Path, exts: tuple[str, ...] | None=None) -> list[tuple[str, Path]]:
	valid = set(exts) if None is not exts else set(_EXT_TO_LANG)
	out: list[tuple[str, Path]] = []
	for dirpath, dirs, files in os.walk(repo):
		dirs[:] = [d for d in sorted(dirs) if d not in _SKIP_PARTS and d.lower() not in _SKIP_PARTS]
		base = Path(dirpath)
		for fname in sorted(files):
			fp = base / fname
			if _path_suffix(fp) in valid:
				out.append((fp.relative_to(repo).as_posix(), fp))
	return out
# @used-by :func:`_staged_overrides()`
# @used-by :func:`_verify_legacy_changed_files()`
# @used-by :func:`check_file_xref_violations()`
# @used-by :func:`verify_staged_xref()`
# @used-by :func:`verify_worktree_xref_changes()`
def _lang_for_rel(rel: str) -> str | None:
	return None if _is_skipped_rel(rel) else _EXT_TO_LANG.get(_path_suffix(rel))
# @used-by :func:`evaluate_pre_tool_use_xref()`
def _resolve_xref_target(args: dict, payload: dict) -> tuple[Path | None, Path, str] | None:
	raw_p = str(args.get('Path') or '').strip()
	r = None
	if raw_p:
		cwd_raw = str(payload.get('cwd') or '').strip()
		cand = normalize_host_path(raw_p)
		target = cand.resolve() if cand.is_absolute() else ((Path(cwd_raw).resolve() / cand).resolve() if cwd_raw else cand.resolve())
		if _path_suffix(target) in _EXT_TO_LANG:
			repo = _find_git_root(target)
			rel = target.relative_to(repo).as_posix() if None is not repo and target.is_relative_to(repo) else target.name
			if not _is_skipped_rel(rel):
				r = (repo, target, rel)
	return r
# @used-by :func:`verify_staged_xref()`
def _staged_overrides(repo: Path, staged_paths: list[str], use_index: bool) -> tuple[dict[str, str | None], list[str]]:
	overrides: dict[str, str | None] = {}
	langs: set[str] = set()
	for raw in staged_paths or ():
		rel = Path(raw).as_posix()
		lang = _lang_for_rel(rel)
		if None is lang:
			continue
		langs.add(lang)
		fpath = repo / rel
		overrides[rel] = _git_index_text(repo, rel) if use_index else (fpath.read_text(encoding='utf-8', errors='replace') if fpath.is_file() else None)
	return (overrides, sorted(langs))
# @used-by :func:`verify_staged_xref()`
# @used-by :func:`verify_worktree_xref_changes()`
def _verify_legacy_changed_files(repo: Path, lang: str, rels: list[str], cur_texts: dict[str, str | None], base_fn) -> list[str]:
	errs: list[str] = []
	for rel in sorted(rels):
		if lang == _lang_for_rel(rel):
			text = cur_texts.get(rel)
			if None is not text:
				errs.extend(check_file_xref_violations(rel, text, baseline_source=base_fn(repo, rel)))
	return errs
# @used-by :func:`_verify_legacy_changed_files()`
# @used-by :func:`evaluate_pre_tool_use_xref()`
# @used-by :meth:`test_df_dotpy_bootstrap.DfDotPyBootstrapTests.test_gates_and_classifiers_recognize_dotpy_files()`
# @used-by :meth:`test_xref_gate.XrefGateTests.test_pre_tool_use_blocks_unannotated_new_python_js_java_and_forbidden_syntax()`
# @used-by :mod:`agent_tools.xref_gate`
def check_file_xref_violations(path: str | Path, source: str, *, baseline_source: str | None=None) -> list[str]:
	rel = Path(path).as_posix()
	lang = _lang_for_rel(rel)
	if None is lang:
		r: list[str] = []
	else:
		checker = {'java': check_java_file_local, 'js': check_js_file_local, 'python': check_python_file_local}[lang]
		strict_existing = None is baseline_source or _has_xref_marker(baseline_source)
		r = [_format_xref_error(e) for e in checker(rel, source or '', baseline_source=baseline_source, strict_existing=strict_existing)]
	return r
# @used-by :func:`agent_tools.gates.xref.check()`
# @used-by :mod:`agent_tools.xref_gate`
def evaluate_pre_tool_use_xref(name: str, args: dict, payload: dict) -> str | None:
	r: str | None = None
	if name in ('write_file', 'edit_file'):
		resolved = _resolve_xref_target(args, payload)
		if None is not resolved:
			repo_root, target, rel = resolved
			old_disk, new_text, _, _ = _compute_edited_content(name, args, target)
			if None is not new_text and _is_pre_tool_governed(repo_root, target, new_text):
				base = _git_head_text(repo_root, rel) if None is not repo_root else old_disk
				errs = check_file_xref_violations(rel, new_text, baseline_source=base)
				r = '; '.join(errs[:3]) if errs else None
	return r
# @used-by :func:`_is_pre_tool_governed()`
# @used-by :func:`verify_staged_xref()`
# @used-by :func:`verify_worktree_xref_changes()`
# @used-by :meth:`test_xref_gate.XrefGateTests.test_pre_tool_use_blocks_unannotated_new_python_js_java_and_forbidden_syntax()`
# @used-by :mod:`agent_tools.xref_gate`
def is_xref_governed_repo(repo_root: Path, staged_paths: list[str] | tuple[str, ...]=(), *, overrides_map: dict[str, str | None] | None=None) -> bool:
	repo = Path(repo_root).resolve()
	if not _is_in_tempdir(repo):
		r = True
	elif any((_has_xref_marker(v) for v in (overrides_map or {}).values())):
		r = True
	else:
		r = any((_has_xref_marker(fp.read_text(encoding='utf-8', errors='replace')) for _, fp in _iter_repo_source_files(repo)))
	return r
# @used-by :func:`agent_tools.staged_gates.verify_staged_extra_gates()`
# @used-by :meth:`test_xref_gate.XrefGateTests._assert_staged_js_java_and_legacy()`
# @used-by :mod:`agent_tools.xref_gate`
def verify_staged_xref(repo_root: Path, staged_paths: list[str], *, use_index: bool=True, strict: bool=False) -> list[str]:
	repo = Path(repo_root).resolve()
	overrides, langs = _staged_overrides(repo, staged_paths, use_index)
	errs: list[str] = []
	if langs and (strict or is_xref_governed_repo(repo, staged_paths, overrides_map=overrides)):
		changed_rels = set(overrides)
		for lang in langs:
			lang_ov = {k: v for k, v in overrides.items() if lang == _lang_for_rel(k)}
			if strict or _is_repo_lang_synced(repo, lang, changed_rels):
				errs.extend((_format_xref_error(e) for e in run_xref_check(repo, lang=lang, overrides_map=lang_ov)['issues']))
			else:
				errs.extend(_verify_legacy_changed_files(repo, lang, list(lang_ov), lang_ov, _git_head_text))
	return errs
# @used-by :func:`agent_tools.worktree_flow._rebase_and_test()`
# @used-by :meth:`test_xref_gate.XrefGateTests.test_worktree_land_blocks_stale_xref_and_passes_when_synced()`
# @used-by :mod:`agent_tools.xref_gate`
def verify_worktree_xref_changes(wt_path: Path, target_branch: str, *, strict: bool=False) -> list[str]:
	wt = Path(wt_path).resolve()
	changed = _git_changed_paths(wt, target_branch)
	langs = sorted({lg for rel in changed for lg in (_lang_for_rel(rel),) if None is not lg})
	errs: list[str] = []
	if langs and (strict or is_xref_governed_repo(wt, changed)):
		changed_set = set(changed)
		for lang in langs:
			if strict or _is_repo_lang_synced(wt, lang, changed_set):
				errs.extend((_format_xref_error(e) for e in run_xref_check(wt, lang=lang)['issues']))
			else:
				cur_texts = {rel: (wt / rel).read_text(encoding='utf-8', errors='replace') for rel in changed if lang == _lang_for_rel(rel) and (wt / rel).is_file()}
				errs.extend(_verify_legacy_changed_files(wt, lang, list(cur_texts), cur_texts, lambda r, p: _git_read_text(r, 'show', f'{target_branch}:{p}')))
	return errs
__all__ = ['check_file_xref_violations', 'evaluate_pre_tool_use_xref', 'is_xref_governed_repo', 'verify_staged_xref', 'verify_worktree_xref_changes']
