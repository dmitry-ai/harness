# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Add blocking architecture audit gates with module-hash caching":
# https://github.com/dmitry-ai/harness/issues/363
from __future__ import annotations
from pathlib import Path
from typing import Any
import hashlib
import json
import tempfile
from ..shell_audit import normalize_host_path
from ..tdd.classifier import classify_code_path
from ..tdd.enforcement import _compute_edited_content, _git_head_text, _git_index_text
from .triggers import classify_code_change_trigger, extract_code_symbols
_AGG_PROD_FILES = 2
_AGG_SLOC_DELTA = 30
_SKIP_PARTS = frozenset({'.agents', '.git', '.venv', '__pycache__', 'build', 'dist', 'node_modules', 'out', 'target', 'venv', '\ua616', '\ua66e'})
# @used-by :func:`agent_tools.arch.evaluator._response_receipt_violations()`
# @used-by :func:`evaluate_pre_tool_use_arch_audit()`
# @used-by :func:`verify_staged_arch_audit()`
def _arch_index_paths(repo: Path | None, cwd: Path | None) -> list[Path]:
	roots: list[Path] = []
	for base in (repo, cwd):
		if None is base:
			continue
		res = Path(base).resolve()
		roots.append(res)
		if 3 <= len(res.parents) and 'worktrees' == res.parent.name and 'data' == res.parents[1].name:
			roots.append(res.parents[3])
		elif 4 <= len(res.parts) and ('\u2c0f', '\u227b', '\u2655', '\u26ef') == res.parts[-4:]:
			roots.append(res.parents[3])
	seen: set[str] = set()
	out: list[Path] = []
	for root in roots:
		idx = root / '\ua616/data/arch-reviews/index.json'
		key = str(idx).lower()
		if key not in seen:
			seen.add(key)
			out.append(idx)
	return out
# @used-by :func:`_evaluate_write_against_index()`
# @used-by :func:`agent_tools.arch.evaluator._response_receipt_violations()`
# @used-by :func:`verify_staged_arch_audit()`
def _blocking_findings(index: dict[str, Any], *, target: str | None=None) -> list[dict[str, Any]]:
	out: list[dict[str, Any]] = []
	for item in index.get('open_findings') or ():
		if not isinstance(item, dict) or 'open' != item.get('status') or item.get('severity') not in ('significant', 'critical'):
			continue
		if None is target or item.get('target') == target or (not item.get('target')):
			out.append(item)
	return out
# @used-by :func:`verify_staged_arch_audit()`
def _check_uncached_staged(uncached: list[dict[str, Any]], index: dict[str, Any], roots: list[Path], all_symbols: set[str]) -> list[str]:
	r: list[str] = []
	designs = [v for v in (index.get('approved_subjects') or {}).values() if isinstance(v, dict) and 'design' == v.get('kind')]
	if designs:
		missing = _missing_design_participants(designs[-1], roots, all_symbols)
		if missing:
			joined = ', '.join(missing[:8])
			r.append(f'ARCH-AUDIT-GATE: Pattern-washing detected at pre-commit — declared Participants missing from staged code: {joined}.')
	else:
		files_s = ', '.join((e['rel'] for e in uncached[:6]))
		r.append(f'ARCH-AUDIT-GATE: Staged architectural diff ({files_s}) lacks a matching approved arch-auditor receipt; run arch-prepare, invoke arch-auditor, and record with arch-record-review.')
	return r
# @used-by :func:`evaluate_pre_tool_use_arch_audit()`
def _evaluate_write_against_index(rel: str, new_text: str, trig: dict[str, Any], index: dict[str, Any]) -> str | None:
	open_f = _blocking_findings(index, target=rel) or (_blocking_findings(index) if trig['triggered'] else [])
	if open_f:
		fid, desc = (open_f[0].get('id'), open_f[0].get('description'))
		r: str | None = f'ARCH-AUDIT-GATE: Open arch-auditor finding {fid} blocks editing "{rel}": {desc}. Resolve and record an approved arch-auditor verdict.'
	elif not trig['triggered']:
		r = None
	else:
		new_sha = hashlib.sha256(new_text.encode('utf-8')).hexdigest()
		mod_entry = (index.get('approved_modules') or {}).get(rel) or {}
		approved_subjs = index.get('approved_subjects') or {}
		has_design = any((isinstance(v, dict) and v.get('kind') in ('design', 'code_diff') for v in approved_subjs.values()))
		if mod_entry.get('sha256') == new_sha or has_design:
			r = None
		else:
			reasons = ', '.join(trig['reasons'][:4])
			r = f'ARCH-AUDIT-GATE: Structural production change in "{rel}" ({reasons}) requires an approved arch-auditor receipt. Freeze specification with harness.py arch-prepare --kind design, invoke arch-auditor, and record with harness.py arch-record-review.'
	return r
# @used-by :func:`_resolve_pre_tool_target()`
def _find_git_root(path: Path) -> Path | None:
	start = path if path.is_dir() else path.parent
	r = None
	for anc in (start, *start.parents):
		if (anc / '.git').exists():
			r = anc
			break
	return r
# @used-by :func:`agent_tools.arch.evaluator._response_receipt_violations()`
# @used-by :func:`evaluate_pre_tool_use_arch_audit()`
# @used-by :func:`verify_staged_arch_audit()`
def _is_arch_governed(repo: Path | None, cwd: Path | None, payload: dict[str, Any], idx_paths: list[Path], *, strict: bool=False) -> bool:
	base = repo or cwd
	has_idx = any((p.is_file() for p in idx_paths))
	has_rule = False
	for cand in (repo, cwd):
		if None is not cand and ((cand / 'rules/12-architecture.md').is_file() or (cand / '\u2c0f/\u227b/\u2655/\u26ef/rules/12-architecture.md').is_file()):
			has_rule = True
			break
	return bool(strict or payload.get('enforce_arch_audit') or has_idx or has_rule or (None is not base and (not _is_in_tempdir(base))))
# @used-by :func:`_is_arch_governed()`
def _is_in_tempdir(path: Path) -> bool:
	try:
		r = Path(path).resolve().is_relative_to(Path(tempfile.gettempdir()).resolve())
	except (OSError, ValueError):
		r = False
	return r
# @used-by :func:`agent_tools.arch.evaluator._response_receipt_violations()`
# @used-by :func:`evaluate_pre_tool_use_arch_audit()`
# @used-by :func:`verify_staged_arch_audit()`
def _load_merged_index(idx_paths: list[Path]) -> tuple[dict[str, Any], list[Path]]:
	merged: dict[str, Any] = {'approved_modules': {}, 'approved_subjects': {}, 'open_findings': []}
	roots: list[Path] = []
	for idx_p in idx_paths:
		if not idx_p.is_file():
			continue
		try:
			data = json.loads(idx_p.read_text(encoding='utf-8'))
		except (OSError, ValueError):
			continue
		if not isinstance(data, dict):
			continue
		roots.append(idx_p.parents[3])
		merged['approved_modules'].update(data.get('approved_modules') or {})
		merged['approved_subjects'].update(data.get('approved_subjects') or {})
		merged['open_findings'].extend(data.get('open_findings') or ())
	return (merged, roots)
# @used-by :func:`_check_uncached_staged()`
def _missing_design_participants(design_entry: dict[str, Any], roots: list[Path], staged_symbols: set[str]) -> list[str]:
	pkg_rel = str(design_entry.get('package') or '').strip()
	declared: list[str] = []
	for root in roots:
		cand = (root / pkg_rel).resolve() if pkg_rel else None
		if None is not cand and cand.is_file():
			try:
				pkg = json.loads(cand.read_text(encoding='utf-8'))
				declared = [str(p) for p in pkg.get('declared_participants') or () if str(p).strip()]
			except (OSError, ValueError):
				declared = []
			break
	return [name for name in declared if name not in staged_symbols]
# @used-by :func:`evaluate_pre_tool_use_arch_audit()`
def _resolve_pre_tool_target(args: dict, payload: dict) -> tuple[Path | None, Path, str, Path | None] | None:
	raw_p = str(args.get('Path') or '').strip()
	r = None
	if raw_p:
		cwd_raw = str(payload.get('cwd') or '').strip()
		cwd = Path(cwd_raw).resolve() if cwd_raw else None
		cand = normalize_host_path(raw_p)
		target = cand.resolve() if cand.is_absolute() else ((cwd / cand).resolve() if None is not cwd else cand.resolve())
		repo = _find_git_root(target)
		rel = target.relative_to(repo).as_posix() if None is not repo and target.is_relative_to(repo) else target.name
		skipped = any((part in _SKIP_PARTS or part.lower() in _SKIP_PARTS for part in Path(rel).parts))
		if (not skipped) and 'production' == classify_code_path(Path(rel)):
			r = (repo, target, rel, cwd)
	return r
# @used-by :func:`verify_staged_arch_audit()`
def _staged_code_entries(repo: Path, staged_paths: list[str], use_index: bool) -> tuple[list[dict[str, Any]], set[str], int]:
	entries: list[dict[str, Any]] = []
	all_symbols: set[str] = set()
	total_sloc = 0
	for raw in staged_paths or ():
		rel = Path(raw).as_posix()
		if any((part in _SKIP_PARTS or part.lower() in _SKIP_PARTS for part in Path(rel).parts)) or 'production' != classify_code_path(Path(rel)):
			continue
		head_txt = _git_head_text(repo, rel)
		new_txt = _git_index_text(repo, rel) if use_index else ((repo / rel).read_text(encoding='utf-8', errors='replace') if (repo / rel).is_file() else None)
		if None is new_txt:
			continue
		sym = extract_code_symbols(new_txt, rel_path=rel)
		all_symbols.update(sym['classes'] | sym['functions'])
		trig = classify_code_change_trigger(rel, head_txt, new_txt)
		total_sloc += int(trig['added_sloc'])
		entries.append({'rel': rel, 'sha256': hashlib.sha256(new_txt.encode('utf-8')).hexdigest(), 'trig': trig})
	return (entries, all_symbols, total_sloc)
# @used-by :func:`agent_tools.gates.arch_audit.check()`
# @used-by :mod:`agent_tools.arch.enforcement`
def evaluate_pre_tool_use_arch_audit(name: str, args: dict, payload: dict) -> str | None:
	r: str | None = None
	resolved = _resolve_pre_tool_target(args, payload) if name in ('write_file', 'edit_file') else None
	if None is not resolved:
		repo, target, rel, cwd = resolved
		idx_paths = _arch_index_paths(repo, cwd)
		if _is_arch_governed(repo, cwd, payload, idx_paths):
			old_text, new_text, _, _ = _compute_edited_content(name, args, target)
			if None is not new_text:
				trig = classify_code_change_trigger(rel, old_text, new_text)
				index, _ = _load_merged_index(idx_paths)
				r = _evaluate_write_against_index(rel, new_text, trig, index)
	return r
# @used-by :func:`agent_tools.staged_gates.verify_staged_extra_gates()`
# @used-by :mod:`agent_tools.arch.enforcement`
def verify_staged_arch_audit(repo_root: Path, staged_paths: list[str], *, use_index: bool=True, strict: bool=False) -> list[str]:
	repo = Path(repo_root).resolve()
	idx_paths = _arch_index_paths(repo, None)
	r: list[str] = []
	if _is_arch_governed(repo, None, {}, idx_paths, strict=strict):
		index, roots = _load_merged_index(idx_paths)
		for f in _blocking_findings(index):
			fid, sev, desc = (f.get('id'), f.get('severity'), f.get('description'))
			r.append(f'ARCH-AUDIT-GATE: Open arch-auditor finding {fid} ({sev}) blocks commit: {desc}')
		entries, all_symbols, total_sloc = _staged_code_entries(repo, staged_paths, use_index)
		agg_triggered = _AGG_PROD_FILES <= len(entries) or _AGG_SLOC_DELTA <= total_sloc
		triggered = [e for e in entries if e['trig']['triggered'] or agg_triggered]
		if triggered and (not r):
			approved_mods = index.get('approved_modules') or {}
			uncached = [e for e in triggered if (approved_mods.get(e['rel']) or {}).get('sha256') != e['sha256']]
			if uncached:
				r.extend(_check_uncached_staged(uncached, index, roots, all_symbols))
	return r
__all__ = ['evaluate_pre_tool_use_arch_audit', 'verify_staged_arch_audit']
