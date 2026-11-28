# 2026-11-28 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from pathlib import Path
from typing import Any
import json
import re
import tempfile
from Df.Harness.Issue.RepoLocator import RepoLocator
from Df.Harness.lib.path_resolve import dfh_var_value
from Df.Harness.lib.worktree import dfh_git_config_file
# 2026-11-28 "Recognize cross-repo approved arch-auditor receipts in Enforcement.verify_staged": https://github.com/dmitry-ai/harness/issues/467
class RepoReceiptSpecification:
	__GITHUB_URL_RE = re.compile(r'github\.com[:/]([A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+?)(?:\.git)?(?:[\s/#]|$)', re.I)
	__ISSUE_SLUG_RE = re.compile(r'^https://github\.com/([A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+)/issues/\d+(?:#.*)?$', re.I)
	__ORIGIN_BLOCK_RE = re.compile(r'(?ms)^\[remote\s+"origin"\][^\[]*')
	# @used-by :meth:`RepoReceiptSpecification.__merge_harness_index()`
	@staticmethod
	def __is_in_tempdir(path: Path) -> bool:
		try:
			r = Path(path).resolve().is_relative_to(Path(tempfile.gettempdir()).resolve())
		except (OSError, ValueError):
			r = False
		return r
	# @used-by :meth:`RepoReceiptSpecification.__merge_entries()`
	# @used-by :meth:`RepoReceiptSpecification.__merge_modules()`
	@staticmethod
	def __matches_entry(issue_url: Any, slug: str | None, *, cross_repo: bool) -> bool:
		entry_slug = RepoReceiptSpecification.issue_slug(issue_url)
		if cross_repo:
			r = None is not slug and entry_slug == slug
		elif None is slug:
			r = True
		else:
			r = None is entry_slug or entry_slug == slug
		return r
	# @used-by :meth:`RepoReceiptSpecification.__merge_harness_index()`
	# @used-by :meth:`RepoReceiptSpecification.load_scoped_index()`
	@staticmethod
	def __merge_entries(merged: dict[str, Any], data: dict[str, Any], slug: str | None, *, cross_repo: bool) -> None:
		for key, item in (data.get('approved_subjects') or {}).items():
			if isinstance(item, dict) and RepoReceiptSpecification.__matches_entry(item.get('issue_url'), slug, cross_repo=cross_repo):
				merged['approved_subjects'][key] = item
		for item in data.get('open_findings') or ():
			if isinstance(item, dict) and RepoReceiptSpecification.__matches_entry(item.get('issue_url'), slug, cross_repo=cross_repo):
				merged['open_findings'].append(item)
		RepoReceiptSpecification.__merge_modules(merged['approved_modules'], data.get('approved_modules') or {}, slug, cross_repo=cross_repo)
	# @used-by :meth:`RepoReceiptSpecification.load_scoped_index()`
	@staticmethod
	def __merge_harness_index(repo: Path | None, slug: str | None, loaded: set[str], merged: dict[str, Any], roots: list[Path]) -> None:
		h_root = RepoReceiptSpecification.harness_arch_root()
		if None is not slug and None is not h_root and None is not repo:
			h_res = h_root.resolve()
			temp_ok = (not RepoReceiptSpecification.__is_in_tempdir(repo)) or RepoReceiptSpecification.__is_in_tempdir(h_res)
			if temp_ok and str(h_res).lower() not in loaded:
				h_data = RepoReceiptSpecification.__read_index(h_res / '\ua616/data/arch-reviews/index.json')
				if None is not h_data:
					roots.append(h_res)
					RepoReceiptSpecification.__merge_entries(merged, h_data, slug, cross_repo=True)
	# @used-by :meth:`RepoReceiptSpecification.__merge_entries()`
	@staticmethod
	def __merge_modules(dest: dict[str, Any], raw_mods: dict[str, Any], slug: str | None, *, cross_repo: bool) -> None:
		for raw_key, item in raw_mods.items():
			if not isinstance(item, dict):
				continue
			if '::' in raw_key:
				scope_part, bare_rel = raw_key.split('::', 1)
				if None is not slug and scope_part.lower() == slug:
					dest[bare_rel] = item
			elif (not cross_repo) and RepoReceiptSpecification.__matches_entry(item.get('issue_url'), slug, cross_repo=False):
				dest[raw_key] = item
	# @used-by :meth:`RepoReceiptSpecification.__merge_harness_index()`
	# @used-by :meth:`RepoReceiptSpecification.load_scoped_index()`
	@staticmethod
	def __read_index(idx_p: Path) -> dict[str, Any] | None:
		r: dict[str, Any] | None = None
		if idx_p.is_file():
			try:
				parsed = json.loads(idx_p.read_text(encoding='utf-8'))
				if isinstance(parsed, dict):
					r = parsed
			except (OSError, ValueError):
				r = None
		return r
	# @used-by :meth:`RepoReceiptSpecification.__merge_harness_index()`
	@staticmethod
	def harness_arch_root() -> Path | None:
		try:
			raw = dfh_var_value('HARNESS_ROOT')
			r: Path | None = Path(raw).resolve() if raw else None
		except (KeyError, OSError, ValueError):
			r = None
		return r
	# @used-by :meth:`Df.Harness.Arch.ReviewStore.ReviewStore.__module_scope()`
	# @used-by :meth:`Df.Harness.Arch.ReviewStore.ReviewStore.__same_finding_scope()`
	# @used-by :meth:`RepoReceiptSpecification.__matches_entry()`
	@staticmethod
	def issue_slug(issue_url: Any) -> str | None:
		m = RepoReceiptSpecification.__ISSUE_SLUG_RE.match(str(issue_url or '').strip())
		return m.group(1).lower() if None is not m else None
	# @used-by :meth:`RepoReceiptSpecification.load_scoped_index()`
	@staticmethod
	def repo_slug(repo: Path | None) -> str | None:
		r: str | None = None
		if None is not repo:
			cfg_file = dfh_git_config_file(Path(repo))
			if cfg_file.is_file():
				try:
					text = cfg_file.read_text(encoding='utf-8', errors='replace')
				except OSError:
					text = ''
				m_blk = RepoReceiptSpecification.__ORIGIN_BLOCK_RE.search(text)
				m_url = RepoReceiptSpecification.__GITHUB_URL_RE.search(m_blk.group(0)) if None is not m_blk else None
				r = m_url.group(1).lower() if None is not m_url else None
			if None is r:
				slugs = RepoLocator.extract_config_slugs(Path(repo))
				r = slugs[0].lower() if slugs else None
		return r
	# @used-by :meth:`Df.Harness.Arch.Enforcement.Enforcement.evaluate_pre_tool_use()`
	# @used-by :meth:`Df.Harness.Arch.Enforcement.Enforcement.verify_staged()`
	def load_scoped_index(self, repo: Path | None, local_idx_paths: list[Path]) -> tuple[dict[str, Any], list[Path]]:
		slug = RepoReceiptSpecification.repo_slug(repo)
		merged: dict[str, Any] = {'approved_modules': {}, 'approved_subjects': {}, 'open_findings': []}
		roots: list[Path] = []
		loaded: set[str] = set()
		for idx_p in local_idx_paths:
			data = RepoReceiptSpecification.__read_index(idx_p)
			if None is not data:
				root_p = idx_p.parents[3].resolve()
				roots.append(root_p)
				loaded.add(str(root_p).lower())
				RepoReceiptSpecification.__merge_entries(merged, data, slug, cross_repo=False)
		RepoReceiptSpecification.__merge_harness_index(repo, slug, loaded, merged, roots)
		return (merged, roots)