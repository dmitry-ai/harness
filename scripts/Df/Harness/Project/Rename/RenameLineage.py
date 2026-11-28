# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
import hashlib
import json
from pathlib import Path
# 2026-11-26 "Move analysis workflow classes into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/380
class RenameLineage:
	# @used-by :meth:`RenameLineage.same_journal_identity_with_rename()`
	# @used-by :meth:`RenameLineage.same_project_root_check()`
	@classmethod
	def __has_rename_lineage(cls, existing_root: Path, missing_root: Path) -> bool:
		target_key = missing_root.as_posix().casefold()
		return any((cand.as_posix().casefold() == target_key for cand in cls.__rename_lineage_roots(existing_root)))
	# @used-by :meth:`RenameLineage.same_journal_identity_with_rename()`
	@staticmethod
	def __is_under_journal_root(path: Path) -> Path | None:
		r = None
		if '\ua66e' == path.name:
			r = path.parent
		elif '\ua66e' == path.parent.name and path.name in ('1 - Analysis', '1 - \u0410\u043d\u0430\u043b\u0438\u0437'):
			r = path.parent.parent
		return r
	# @used-by :meth:`RenameLineage.__has_rename_lineage()`
	# @used-by :meth:`RenameLineage.find_sibling_project_path()`
	@staticmethod
	def __rename_lineage_roots(existing_root: Path) -> tuple[Path, ...]:
		pj_path = existing_root / '\ua616/project.json'
		r: list[Path] = []
		if pj_path.is_file():
			try:
				history = json.loads(pj_path.read_text(encoding='utf-8-sig')).get('renamed_from') or []
			except (OSError, ValueError):
				history = []
			for item in history:
				if isinstance(item, dict) and item.get('from'):
					cand = Path(str(item['from'])).resolve()
					if not cand.is_dir():
						r.append(cand)
		return tuple(r)
	# @used-by :func:`agent_tools.project_rename_state.capture_file_sha()`
	# @used-by :meth:`Df.Harness.Project.Rename.ProjectRenamer.ProjectRenamer.__sync_registrations()`
	# @used-by :meth:`Df.Harness.Project.Rename.StateRewriter.StateRewriter.refresh_workflow_file_hash()`
	# @used-by :meth:`test_df_harness_s11_wave2a_project_ext.DfHarnessS11Wave2aProjectExtTests.test_project_rename_classes()`
	@staticmethod
	def capture_file_sha(path: Path) -> str | None:
		return hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else None
	# 2026-11-28 "Recognize cross-repo approved arch-auditor receipts in Enforcement.verify_staged": https://github.com/dmitry-ai/harness/issues/467
	# @used-by :func:`agent_tools.project_rename_state.find_sibling_project_path()`
	# @used-by :meth:`test_df_harness_s11_wave2a_project_ext.DfHarnessS11Wave2aProjectExtTests.test_z_project_rename_full_coverage()`
	@classmethod
	def find_sibling_project_path(cls, raw_val: str, project_root: Path, daily_root: Path, *, extra_allowed_roots: tuple[Path, ...]=()) -> Path | None:
		r: Path | None = None
		try:
			candidate = Path(raw_val).resolve()
		except OSError:
			candidate = None
		if None is not candidate and candidate.is_relative_to(daily_root):
			allowed = (project_root, *cls.__rename_lineage_roots(project_root))
			in_project = any((candidate.is_relative_to(root_p) or root_p.is_relative_to(candidate) for root_p in allowed))
			in_extra = any((candidate.is_relative_to(extra_p) for extra_p in extra_allowed_roots))
			if (not in_project) and (not in_extra):
				r = candidate
		return r
	# @used-by :func:`agent_tools.project_rename_state._path_pairs()`
	# @used-by :meth:`Df.Harness.Project.Rename.PostRenameVerifier.PostRenameVerifier.__launcher_stale_files()`
	# @used-by :meth:`Df.Harness.Project.Rename.PostRenameVerifier.PostRenameVerifier.__verify_journal_regression()`
	# @used-by :meth:`Df.Harness.Project.Rename.StateRewriter.StateRewriter.migrate_journal_state()`
	# @used-by :meth:`Df.Harness.Project.Rename.StateRewriter.StateRewriter.rewrite()`
	# @used-by :meth:`Df.Harness.Project.Rename.StateRewriter.StateRewriter.rewrite_launcher_handoffs()`
	# @used-by :meth:`test_df_harness_s11_wave2a_project_ext.DfHarnessS11Wave2aProjectExtTests.test_project_rename_classes()`
	@staticmethod
	def path_pairs(old_root: Path, new_root: Path, old_state: Path | None, new_state: Path | None) -> list[tuple[str, str]]:
		raw: list[tuple[Path, Path]] = []
		if None is not old_state and None is not new_state:
			raw.append((old_state, new_state))
		raw.append((old_root, new_root))
		r: list[tuple[str, str]] = []
		for src, dst in raw:
			r.extend([(src.as_uri(), dst.as_uri()), (str(src), str(dst))])
			if src.as_posix() != str(src):
				r.append((src.as_posix(), dst.as_posix()))
		return r
	# @used-by :func:`agent_tools.project_rename_state.same_journal_identity_with_rename()`
	# @used-by :meth:`test_df_harness_s11_wave2a_project_ext.DfHarnessS11Wave2aProjectExtTests.test_z_project_rename_full_coverage()`
	@classmethod
	def same_journal_identity_with_rename(cls, first: str | Path | None, second: str | Path | None, canon_fn) -> bool:
		r = False
		if isinstance(first, (str, Path)) and isinstance(second, (str, Path)) and str(first).strip() and str(second).strip():
			c1, c2 = (canon_fn(first), canon_fn(second))
			if c1 == c2:
				r = True
			else:
				r1, r2 = (cls.__is_under_journal_root(c1), cls.__is_under_journal_root(c2))
				if None is not r1 and None is not r2:
					r = (r1.is_dir() and (not r2.is_dir()) and cls.__has_rename_lineage(r1, r2)) or (r2.is_dir() and (not r1.is_dir()) and cls.__has_rename_lineage(r2, r1))
		return r
	# @used-by :func:`agent_tools.project_rename_state.same_project_root_check()`
	# @used-by :meth:`test_df_harness_s11_wave2a_project_ext.DfHarnessS11Wave2aProjectExtTests.test_project_rename_classes()`
	@classmethod
	def same_project_root_check(cls, first: str | Path | None, second: str | Path | None, canon_fn, key_fn) -> bool:
		r = False
		if None is not first and None is not second:
			s1, s2 = (str(first).strip(), str(second).strip())
			if s1 and s2 and (not (isinstance(first, str) and (not Path(s1).is_absolute()))) and (not (isinstance(second, str) and (not Path(s2).is_absolute()))):
				try:
					c1, c2 = (canon_fn(s1), canon_fn(s2))
					r = True if key_fn(c1) == key_fn(c2) else ((c1.is_dir() and (not c2.is_dir()) and cls.__has_rename_lineage(c1, c2)) or (c2.is_dir() and (not c1.is_dir()) and cls.__has_rename_lineage(c2, c1)))
				except (OSError, ValueError):
					r = False
		return r
