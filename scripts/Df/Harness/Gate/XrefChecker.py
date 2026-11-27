# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from pathlib import Path
from Df.Core.lib.fs import df_path_suffix
from Df.Core.lib.git import df_git_root
from Df.Harness.Xref.Java.Syncer import Syncer as JavaSyncer
from Df.Harness.Xref.Js.Syncer import Syncer as JsSyncer
from Df.Harness.Xref.Python.Syncer import Syncer as PythonSyncer
from agent_tools.shell_audit import normalize_host_path
import os
import re
import tempfile
# 2026-11-26 "Move verification gate subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/381
class XrefChecker:
	DEF_HINT_RE = {
		'java': re.compile(r'\)\s*(?:throws\b[^{;]*)?\{'),
		'js': re.compile(r'\bfunction\b|=>|\)\s*\{'),
		'python': re.compile(r'^\s*(?:async\s+)?def\s+\w+', re.M),
	}
	EXT_TO_LANG = {
		'.cjs': 'js',
		'.java': 'java',
		'.js': 'js',
		'.jsx': 'js',
		'.mjs': 'js',
		'.py': 'python',
		'.ts': 'js',
		'.tsx': 'js',
	}
	LANG_EXTS = {
		'java': ('.java',),
		'js': ('.cjs', '.js', '.jsx', '.mjs', '.ts', '.tsx'),
		'python': ('.py',),
	}
	SKIP_PARTS = frozenset({'.git', '.venv', '__pycache__', 'build', 'dist', 'node_modules', 'out', 'target', 'venv', '\ua616', '\ua66e'})
	# @used-by :func:`agent_tools.xref_gate.check_file_xref_violations()`
	# @used-by :meth:`Df.Harness.Gate.XrefPreToolGate.XrefPreToolGate.check()`
	# @used-by :meth:`XrefChecker.verify_legacy_changed_files()`
	# @used-by :meth:`test_df_harness_s11_wave2b_gate.DfHarnessS11Wave2bGateTests.test_gate_thin_pretool_shims_and_checkers()`
	def __init__(self, path: str | Path, source: str, *, baseline_source: str | None=None) -> None:
		self.__path = path
		self.__source = source or ''
		self.__baseline_source = baseline_source
	# @used-by :meth:`XrefChecker.is_governed_repo()`
	# @used-by :meth:`XrefChecker.is_pre_tool_governed()`
	# @used-by :meth:`XrefChecker.is_repo_lang_synced()`
	@staticmethod
	def __is_in_tempdir(path: Path) -> bool:
		try:
			r = Path(path).resolve().is_relative_to(Path(tempfile.gettempdir()).resolve())
		except (OSError, ValueError):
			r = False
		return r
	# @used-by :meth:`XrefChecker.lang_for_rel()`
	# @used-by :meth:`XrefChecker.resolve_target()`
	@staticmethod
	def __is_skipped_rel(rel: str) -> bool:
		return any((p in XrefChecker.SKIP_PARTS or p.lower() in XrefChecker.SKIP_PARTS for p in Path(rel).parts))
	# @used-by :meth:`XrefChecker.is_governed_repo()`
	# @used-by :meth:`XrefChecker.is_repo_lang_synced()`
	@staticmethod
	def __iter_repo_source_files(repo: Path, exts: tuple[str, ...] | None=None) -> list[tuple[str, Path]]:
		valid = set(exts) if None is not exts else set(XrefChecker.EXT_TO_LANG)
		out: list[tuple[str, Path]] = []
		for dirpath, dirs, files in os.walk(repo):
			dirs[:] = [d for d in sorted(dirs) if d not in XrefChecker.SKIP_PARTS and d.lower() not in XrefChecker.SKIP_PARTS]
			base = Path(dirpath)
			for fname in sorted(files):
				fp = base / fname
				if df_path_suffix(fp) in valid:
					out.append((fp.relative_to(repo).as_posix(), fp))
		return out
	# @used-by :meth:`Df.Harness.Gate.XrefStagedGate.XrefStagedGate.verify()`
	# @used-by :meth:`Df.Harness.Gate.XrefWorktreeGate.XrefWorktreeGate.verify()`
	# @used-by :meth:`XrefChecker.check()`
	@staticmethod
	def format_error(msg: str) -> str:
		return f'XREF-GATE: {msg[6:]}' if msg.startswith('XREF: ') else (msg if msg.startswith('XREF-GATE:') else f'XREF-GATE: {msg}')
	# @used-by :meth:`XrefChecker.check()`
	# @used-by :meth:`XrefChecker.is_governed_repo()`
	# @used-by :meth:`XrefChecker.is_pre_tool_governed()`
	# @used-by :meth:`XrefChecker.is_repo_lang_synced()`
	@staticmethod
	def has_xref_marker(text: str | None) -> bool:
		s = text or ''
		return '@used-by' in s or '@uses' in s
	# @used-by :func:`agent_tools.xref_gate.is_xref_governed_repo()`
	# @used-by :meth:`Df.Harness.Gate.XrefStagedGate.XrefStagedGate.verify()`
	# @used-by :meth:`Df.Harness.Gate.XrefWorktreeGate.XrefWorktreeGate.verify()`
	# @used-by :meth:`XrefChecker.is_pre_tool_governed()`
	@staticmethod
	def is_governed_repo(repo_root: Path, staged_paths: list[str] | tuple[str, ...]=(), *, overrides_map: dict[str, str | None] | None=None) -> bool:
		repo = Path(repo_root).resolve()
		if not XrefChecker.__is_in_tempdir(repo):
			r = True
		elif any((XrefChecker.has_xref_marker(v) for v in (overrides_map or {}).values())):
			r = True
		else:
			r = any((XrefChecker.has_xref_marker(fp.read_text(encoding='utf-8', errors='replace')) for _, fp in XrefChecker.__iter_repo_source_files(repo)))
		return r
	# @used-by :meth:`Df.Harness.Gate.XrefPreToolGate.XrefPreToolGate.check()`
	# @used-by :meth:`test_df_harness_s11_wave2b_gate_cov.DfHarnessS11Wave2bGateCovTests.test_rules_auditor_subprocess_and_xref_checker()`
	@staticmethod
	def is_pre_tool_governed(repo_root: Path | None, target: Path, new_text: str) -> bool:
		has_sig = XrefChecker.has_xref_marker(new_text) or '@override' in new_text or '@Override' in new_text
		if (not XrefChecker.__is_in_tempdir(target)) or has_sig:
			r = True
		elif None is not repo_root:
			r = XrefChecker.is_governed_repo(repo_root)
		else:
			r = False
		return r
	# @used-by :meth:`Df.Harness.Gate.XrefStagedGate.XrefStagedGate.verify()`
	# @used-by :meth:`Df.Harness.Gate.XrefWorktreeGate.XrefWorktreeGate.verify()`
	# @used-by :meth:`test_df_harness_s11_wave2b_gate_cov.DfHarnessS11Wave2bGateCovTests.test_rules_auditor_subprocess_and_xref_checker()`
	@staticmethod
	def is_repo_lang_synced(repo: Path, lang: str, changed_rels: set[str]) -> bool:
		pat = XrefChecker.DEF_HINT_RE[lang]
		total, annotated = (0, 0)
		for rel, fp in XrefChecker.__iter_repo_source_files(repo, XrefChecker.LANG_EXTS[lang]):
			if rel in changed_rels:
				continue
			txt = fp.read_text(encoding='utf-8', errors='replace')
			if pat.search(txt):
				total += 1
				if XrefChecker.has_xref_marker(txt):
					annotated += 1
		return 0 == total or annotated == total or ((not XrefChecker.__is_in_tempdir(repo)) and annotated * 10 >= total * 9)
	# @used-by :meth:`Df.Harness.Gate.XrefStagedGate.XrefStagedGate.__staged_overrides()`
	# @used-by :meth:`Df.Harness.Gate.XrefStagedGate.XrefStagedGate.verify()`
	# @used-by :meth:`Df.Harness.Gate.XrefWorktreeGate.XrefWorktreeGate.verify()`
	# @used-by :meth:`XrefChecker.check()`
	# @used-by :meth:`XrefChecker.verify_legacy_changed_files()`
	@staticmethod
	def lang_for_rel(rel: str) -> str | None:
		return None if XrefChecker.__is_skipped_rel(rel) else XrefChecker.EXT_TO_LANG.get(df_path_suffix(rel))
	# @used-by :meth:`Df.Harness.Gate.XrefPreToolGate.XrefPreToolGate.check()`
	# @used-by :meth:`test_df_harness_s11_wave2b_gate_cov.DfHarnessS11Wave2bGateCovTests.test_rules_auditor_subprocess_and_xref_checker()`
	@staticmethod
	def resolve_target(args: dict, payload: dict) -> tuple[Path | None, Path, str] | None:
		raw_p = str(args.get('Path') or '').strip()
		r = None
		if raw_p:
			cwd_raw = str(payload.get('cwd') or '').strip()
			cand = normalize_host_path(raw_p)
			target = cand.resolve() if cand.is_absolute() else ((Path(cwd_raw).resolve() / cand).resolve() if cwd_raw else cand.resolve())
			if df_path_suffix(target) in XrefChecker.EXT_TO_LANG:
				repo = df_git_root(target)
				rel = target.relative_to(repo).as_posix() if None is not repo and target.is_relative_to(repo) else target.name
				if not XrefChecker.__is_skipped_rel(rel):
					r = (repo, target, rel)
		return r
	# @used-by :meth:`Df.Harness.Gate.XrefStagedGate.XrefStagedGate.verify()`
	# @used-by :meth:`Df.Harness.Gate.XrefWorktreeGate.XrefWorktreeGate.verify()`
	# @used-by :meth:`test_df_harness_s11_wave2b_gate_cov.DfHarnessS11Wave2bGateCovTests.test_rules_auditor_subprocess_and_xref_checker()`
	@staticmethod
	def verify_legacy_changed_files(repo: Path, lang: str, rels: list[str], cur_texts: dict[str, str | None], base_fn) -> list[str]:
		errs: list[str] = []
		for rel in sorted(rels):
			if lang == XrefChecker.lang_for_rel(rel):
				text = cur_texts.get(rel)
				if None is not text:
					errs.extend(XrefChecker(rel, text, baseline_source=base_fn(repo, rel)).check())
		return errs
	# @used-by :func:`agent_tools.xref_gate.check_file_xref_violations()`
	# @used-by :meth:`Df.Harness.Gate.XrefPreToolGate.XrefPreToolGate.check()`
	# @used-by :meth:`XrefChecker.verify_legacy_changed_files()`
	# @used-by :meth:`test_df_harness_s11_wave2b_gate.DfHarnessS11Wave2bGateTests.test_gate_thin_pretool_shims_and_checkers()`
	def check(self) -> list[str]:
		rel = Path(self.__path).as_posix()
		lang = XrefChecker.lang_for_rel(rel)
		if None is lang:
			r: list[str] = []
		else:
			checker = {'java': JavaSyncer.check_file_local, 'js': JsSyncer.check_file_local, 'python': PythonSyncer.check_file_local}[lang]
			strict_existing = None is self.__baseline_source or XrefChecker.has_xref_marker(self.__baseline_source)
			r = [XrefChecker.format_error(e) for e in checker(rel, self.__source, baseline_source=self.__baseline_source, strict_existing=strict_existing)]
		return r
