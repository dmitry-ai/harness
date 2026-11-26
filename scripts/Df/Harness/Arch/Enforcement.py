# 2026-11-27 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from pathlib import Path
from typing import Any
import hashlib
import json
import tempfile
from Df.Harness.Arch.TriggerClassifier import TriggerClassifier
from agent_tools.shell_audit import normalize_host_path
from agent_tools.tdd.classifier import classify_code_path
from agent_tools.tdd.enforcement import _compute_edited_content, _git_head_text, _git_index_text
# 2026-11-27 "Reorganize Harness scripts into single-class Mage2Pro modules": https://github.com/dmitry-ai/harness/issues/338
class Enforcement:
	__AGG_PROD_FILES = 2
	__AGG_SLOC_DELTA = 30
	__SKIP_PARTS = frozenset({'.agents', '.git', '.venv', '__pycache__', 'build', 'dist', 'node_modules', 'out', 'target', 'venv', '\ua616', '\ua66e'})
	# @used-by :meth:`Enforcement.verify_staged()`
	@staticmethod
	def __check_uncached_staged(uncached: list[dict[str, Any]], index: dict[str, Any], roots: list[Path], all_symbols: set[str]) -> list[str]:
		r: list[str] = []
		designs = [v for v in (index.get('approved_subjects') or {}).values() if isinstance(v, dict) and 'design' == v.get('kind')]
		if designs:
			missing = Enforcement.__missing_design_participants(designs[-1], roots, all_symbols, [e['rel'] for e in uncached])
			if missing:
				joined = ', '.join(missing[:8])
				r.append(f'ARCH-AUDIT-GATE: Pattern-washing detected at pre-commit — declared Participants missing from staged code: {joined}.')
		else:
			files_s = ', '.join((e['rel'] for e in uncached[:6]))
			r.append(f'ARCH-AUDIT-GATE: Staged architectural diff ({files_s}) lacks a matching approved arch-auditor receipt; run arch-prepare, invoke arch-auditor, and record with arch-record-review.')
		return r
	# @used-by :meth:`Enforcement.evaluate_pre_tool_use()`
	@staticmethod
	def __evaluate_write_against_index(rel: str, new_text: str, trig: dict[str, Any], index: dict[str, Any]) -> str | None:
		open_f = Enforcement.blocking_findings(index, target=rel) or (Enforcement.blocking_findings(index) if trig['triggered'] else [])
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
	# @used-by :meth:`Enforcement.__resolve_pre_tool_target()`
	@staticmethod
	def __find_git_root(path: Path) -> Path | None:
		start = path if path.is_dir() else path.parent
		r = None
		for anc in (start, *start.parents):
			if (anc / '.git').exists():
				r = anc
				break
		return r
	# @used-by :meth:`Enforcement.is_arch_governed()`
	@staticmethod
	def __is_in_tempdir(path: Path) -> bool:
		try:
			r = Path(path).resolve().is_relative_to(Path(tempfile.gettempdir()).resolve())
		except (OSError, ValueError):
			r = False
		return r
	# @used-by :meth:`Enforcement.__missing_design_participants()`
	@staticmethod
	def __is_path_participant(token: str) -> bool:
		return '/' in token or token.endswith(('.py', '.js', '.ts', '.java', '.php', '.go', '.rs', '.json'))
	# @used-by :meth:`Enforcement.__missing_design_participants()`
	@staticmethod
	def __load_declared_participants(design_entry: dict[str, Any], roots: list[Path]) -> list[str]:
		pkg_rel = str(design_entry.get('package') or '').strip()
		r: list[str] = []
		for root in roots if pkg_rel else ():
			cand = (root / pkg_rel).resolve()
			if cand.is_file():
				try:
					raw_p = json.loads(cand.read_text(encoding='utf-8')).get('declared_participants') or ()
					r = [str(p) for p in raw_p if str(p).strip()]
				except (OSError, ValueError):
					r = []
				break
		return r
	# @used-by :meth:`Enforcement.__check_uncached_staged()`
	@staticmethod
	def __missing_design_participants(design_entry: dict[str, Any], roots: list[Path], staged_symbols: set[str], staged_rels: list[str] | tuple[str, ...]=()) -> list[str]:
		declared = Enforcement.__load_declared_participants(design_entry, roots)
		sym_tokens = [tok for tok in declared if not Enforcement.__is_path_participant(tok)]
		path_tokens = [tok for tok in declared if Enforcement.__is_path_participant(tok)]
		if sym_tokens:
			r = [] if any((Enforcement.__symbol_matches(tok, staged_symbols) for tok in sym_tokens)) else sym_tokens
		elif path_tokens:
			rel_set = set(staged_rels)
			r = [] if any((Enforcement.__path_matches(tok, rel_set) for tok in path_tokens)) else path_tokens
		else:
			r = []
		return r
	# @used-by :meth:`Enforcement.__missing_design_participants()`
	@staticmethod
	def __path_matches(token: str, rels: set[str]) -> bool:
		return any((rel == token or rel.endswith('/' + token) for rel in rels))
	# @used-by :meth:`Enforcement.evaluate_pre_tool_use()`
	@staticmethod
	def __resolve_pre_tool_target(args: dict, payload: dict) -> tuple[Path | None, Path, str, Path | None] | None:
		raw_p = str(args.get('Path') or '').strip()
		r = None
		if raw_p:
			cwd_raw = str(payload.get('cwd') or '').strip()
			cwd = Path(cwd_raw).resolve() if cwd_raw else None
			cand = normalize_host_path(raw_p)
			target = cand.resolve() if cand.is_absolute() else ((cwd / cand).resolve() if None is not cwd else cand.resolve())
			repo = Enforcement.__find_git_root(target)
			rel = target.relative_to(repo).as_posix() if None is not repo and target.is_relative_to(repo) else target.name
			skipped = any((part in Enforcement.__SKIP_PARTS or part.lower() in Enforcement.__SKIP_PARTS for part in Path(rel).parts))
			if (not skipped) and 'production' == classify_code_path(Path(rel)):
				r = (repo, target, rel, cwd)
		return r
	# @used-by :meth:`Enforcement.verify_staged()`
	@staticmethod
	def __staged_code_entries(repo: Path, staged_paths: list[str], use_index: bool) -> tuple[list[dict[str, Any]], set[str], int]:
		entries: list[dict[str, Any]] = []
		all_symbols: set[str] = set()
		total_sloc = 0
		clf = TriggerClassifier()
		for raw in staged_paths or ():
			rel = Path(raw).as_posix()
			if any((part in Enforcement.__SKIP_PARTS or part.lower() in Enforcement.__SKIP_PARTS for part in Path(rel).parts)) or 'production' != classify_code_path(Path(rel)):
				continue
			head_txt = _git_head_text(repo, rel)
			new_txt = _git_index_text(repo, rel) if use_index else ((repo / rel).read_text(encoding='utf-8', errors='replace') if (repo / rel).is_file() else None)
			if None is new_txt:
				continue
			sym = TriggerClassifier.extract_symbols(new_txt, rel_path=rel)
			all_symbols.update(sym['classes'] | sym['functions'])
			trig = clf.classify_code_change(rel, head_txt, new_txt)
			total_sloc += int(trig['added_sloc'])
			entries.append({'rel': rel, 'sha256': hashlib.sha256(new_txt.encode('utf-8')).hexdigest(), 'trig': trig})
		return (entries, all_symbols, total_sloc)
	# @used-by :meth:`Enforcement.__missing_design_participants()`
	@staticmethod
	def __symbol_matches(token: str, symbols: set[str]) -> bool:
		return token in symbols or ('.' in token and token.rsplit('.', 1)[-1] in symbols)
	# @used-by :meth:`Df.Harness.Arch.Evaluator.Evaluator.__response_receipt_violations()`
	# @used-by :meth:`Enforcement.evaluate_pre_tool_use()`
	# @used-by :meth:`Enforcement.verify_staged()`
	@staticmethod
	def arch_index_paths(repo: Path | None, cwd: Path | None) -> list[Path]:
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
	# @used-by :meth:`Df.Harness.Arch.Evaluator.Evaluator.__response_receipt_violations()`
	# @used-by :meth:`Enforcement.__evaluate_write_against_index()`
	# @used-by :meth:`Enforcement.verify_staged()`
	@staticmethod
	def blocking_findings(index: dict[str, Any], *, target: str | None=None) -> list[dict[str, Any]]:
		out: list[dict[str, Any]] = []
		for item in index.get('open_findings') or ():
			if not isinstance(item, dict) or 'open' != item.get('status') or item.get('severity') not in ('significant', 'critical'):
				continue
			if None is target or item.get('target') == target or (not item.get('target')):
				out.append(item)
		return out
	# @used-by :func:`agent_tools.arch.enforcement.evaluate_pre_tool_use_arch_audit()`
	# @used-by :meth:`test_df_harness_s11_wave2e_arch.DfHarnessArchWave2eTests.test_enforcement_preserves_gates_and_395_participants()`
	@staticmethod
	def evaluate_pre_tool_use(name: str, args: dict, payload: dict) -> str | None:
		r: str | None = None
		resolved = Enforcement.__resolve_pre_tool_target(args, payload) if name in ('write_file', 'edit_file') else None
		if None is not resolved:
			repo, target, rel, cwd = resolved
			idx_paths = Enforcement.arch_index_paths(repo, cwd)
			if Enforcement.is_arch_governed(repo, cwd, payload, idx_paths):
				old_text, new_text, _, _ = _compute_edited_content(name, args, target)
				if None is not new_text:
					trig = TriggerClassifier().classify_code_change(rel, old_text, new_text)
					index, _ = Enforcement.load_merged_index(idx_paths)
					r = Enforcement.__evaluate_write_against_index(rel, new_text, trig, index)
		return r
	# @used-by :meth:`Df.Harness.Arch.Evaluator.Evaluator.__response_receipt_violations()`
	# @used-by :meth:`Enforcement.evaluate_pre_tool_use()`
	# @used-by :meth:`Enforcement.verify_staged()`
	# @used-by :meth:`test_df_harness_s11_wave2e_arch.DfHarnessArchWave2eTests.test_enforcement_preserves_gates_and_395_participants()`
	@staticmethod
	def is_arch_governed(repo: Path | None, cwd: Path | None, payload: dict[str, Any], idx_paths: list[Path], *, strict: bool=False) -> bool:
		base = repo or cwd
		has_idx = any((p.is_file() for p in idx_paths))
		has_rule = False
		for cand in (repo, cwd):
			if None is not cand and ((cand / 'rules/12-architecture.md').is_file() or (cand / '\u2c0f/\u227b/\u2655/\u26ef/rules/12-architecture.md').is_file()):
				has_rule = True
				break
		return bool(strict or payload.get('enforce_arch_audit') or has_idx or has_rule or (None is not base and (not Enforcement.__is_in_tempdir(base))))
	# @used-by :meth:`Df.Harness.Arch.Evaluator.Evaluator.__response_receipt_violations()`
	# @used-by :meth:`Enforcement.evaluate_pre_tool_use()`
	# @used-by :meth:`Enforcement.verify_staged()`
	@staticmethod
	def load_merged_index(idx_paths: list[Path]) -> tuple[dict[str, Any], list[Path]]:
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
	# @used-by :func:`agent_tools.arch.enforcement.verify_staged_arch_audit()`
	# @used-by :meth:`test_df_harness_s11_wave2e_arch.DfHarnessArchWave2eTests.test_enforcement_preserves_gates_and_395_participants()`
	def verify_staged(self, repo_root: Path, staged_paths: list[str], *, use_index: bool=True, strict: bool=False) -> list[str]:
		repo = Path(repo_root).resolve()
		idx_paths = Enforcement.arch_index_paths(repo, None)
		r: list[str] = []
		if Enforcement.is_arch_governed(repo, None, {}, idx_paths, strict=strict):
			index, roots = Enforcement.load_merged_index(idx_paths)
			for f in Enforcement.blocking_findings(index):
				fid, sev, desc = (f.get('id'), f.get('severity'), f.get('description'))
				r.append(f'ARCH-AUDIT-GATE: Open arch-auditor finding {fid} ({sev}) blocks commit: {desc}')
			entries, all_symbols, total_sloc = Enforcement.__staged_code_entries(repo, staged_paths, use_index)
			agg_triggered = Enforcement.__AGG_PROD_FILES <= len(entries) or Enforcement.__AGG_SLOC_DELTA <= total_sloc
			triggered = [e for e in entries if e['trig']['triggered'] or agg_triggered]
			if triggered and (not r):
				approved_mods = index.get('approved_modules') or {}
				uncached = [e for e in triggered if (approved_mods.get(e['rel']) or {}).get('sha256') != e['sha256']]
				if uncached:
					r.extend(Enforcement.__check_uncached_staged(uncached, index, roots, all_symbols))
		return r
