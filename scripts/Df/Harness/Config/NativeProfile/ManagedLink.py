# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from pathlib import Path
from typing import Any
from Df.Harness.lib.config_blocks import dfh_has_linked_ancestor, dfh_is_linked_path
from Df.Harness.lib.native_links import dfh_absolute, dfh_directory_link, dfh_exists, dfh_file_link, dfh_json_bytes, dfh_link_matches_target, dfh_remove_link, dfh_restore_directory_link, dfh_retire_directory_link, dfh_same_path, dfh_verify_retired_directory_link
import os
# 2026-11-26 "Move turn lifecycle subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/383
class ManagedLink:
	# @used-by :func:`Df.Harness.lib.native_codex_plan._plan_codex_roles()`
	# @used-by :func:`Df.Harness.lib.native_codex_plan._plan_codex_skills()`
	# @used-by :func:`Df.Harness.lib.native_codex_roles._handle_existing_codex_link()`
	# @used-by :func:`Df.Harness.lib.native_codex_roles._retire_obsolete_skill_entry()`
	# @used-by :func:`Df.Harness.lib.native_codex_roles._retire_one_profile_role()`
	# @used-by :meth:`test_native_profiles.NativeProfileTests.test_unified_managed_link_and_manifest_helpers()`
	def __init__(self, path: str | Path, target: str | Path, kind: str, *, label: str='skill', legacy_dir: bool=False, ops: dict[str, Any] | None=None) -> None:
		self.path = dfh_absolute(path)
		self.target = target if isinstance(target, str) and kind in ('directory-junction', 'directory-symlink') else Path(target)
		self.kind = kind
		self.label = label
		self.legacy_dir = legacy_dir
		self.__ops = ops or {}
	# @used-by :meth:`Df.Harness.Config.NativeProfile.Applier.Applier.__apply()`
	def backup_payload(self) -> bytes:
		return dfh_json_bytes(self.identity_dict())
	# @used-by :meth:`test_native_profiles.NativeProfileTests.test_unified_managed_link_and_manifest_helpers()`
	def create(self, primary: str | Path) -> None:
		if dfh_has_linked_ancestor(self.path, include_self=False):
			raise ValueError(f'Linked {self.label} parent directory appeared before creation; preserved: {self.path}')
		if self.legacy_dir:
			self.path.rmdir()
		if 'file-symlink' == self.kind:
			self.__ops.get('file_link', dfh_file_link)(self.target, self.path, primary)
		else:
			self.__ops.get('directory_link', dfh_directory_link)(self.target, self.path, primary)
	# @used-by :meth:`Df.Harness.Config.NativeProfile.Applier.Applier.__handle_failure()`
	# @used-by :meth:`ManagedLink.backup_payload()`
	# @used-by :meth:`ManagedLink.restore_retired()`
	# @used-by :meth:`ManagedLink.retire()`
	# @used-by :meth:`ManagedLink.verify_retired()`
	# @used-by :meth:`test_native_profiles.NativeProfileTests.test_unified_managed_link_and_manifest_helpers()`
	def identity_dict(self) -> dict[str, str]:
		target = os.readlink(self.path) if 'file-symlink' == self.kind else str(self.target)
		return {'kind': self.kind, 'target': target}
	# @used-by :meth:`Df.Harness.Config.NativeProfile.Plan.Plan.readonly_issues()`
	# @used-by :meth:`test_native_profiles.NativeProfileTests.test_unified_managed_link_and_manifest_helpers()`
	def readonly_issue(self, *, retired: bool=False) -> dict[str, str]:
		if retired:
			message = 'Obsolete owned role file link needs retirement' if 'file-symlink' == self.kind else 'Obsolete owned skill directory link needs retirement'
		else:
			message = f'Shared role file link is missing: {self.target}' if 'file-symlink' == self.kind else f'Shared skill directory link is missing: {self.target}'
		return {'file': str(self.path), 'message': message}
	# @used-by :meth:`Df.Harness.Config.NativeProfile.Applier.Applier.__rollback()`
	# @used-by :meth:`test_native_profiles.NativeProfileTests.test_unified_managed_link_and_manifest_helpers()`
	def remove_created(self) -> None:
		self.__ops.get('remove_link', dfh_remove_link)(self.path, self.target)
	# @used-by :meth:`Df.Harness.Config.NativeProfile.Applier.Applier.__rollback()`
	def restore_retired(self, primary: str | Path) -> None:
		if 'file-symlink' == self.kind:
			if dfh_exists(self.path) or dfh_has_linked_ancestor(self.path, include_self=False):
				raise ValueError('Obsolete role destination changed before rollback; preserved')
			self.__ops.get('file_link', dfh_file_link)(self.target, self.path, primary)
		else:
			if dfh_exists(self.path) or dfh_is_linked_path(self.path) or dfh_has_linked_ancestor(self.path, include_self=False):
				raise ValueError('Obsolete skill destination changed before rollback; preserved')
			dfh_restore_directory_link(self.path, self.identity_dict(), primary, dir_link_fn=self.__ops.get('directory_link'))
			self.verify_retired()
	# @used-by :meth:`Df.Harness.Config.NativeProfile.Applier.Applier.__apply_links()`
	def retire(self) -> None:
		if 'file-symlink' == self.kind:
			self.__ops.get('remove_link', dfh_remove_link)(self.path, self.target)
		else:
			dfh_retire_directory_link(self.path, self.identity_dict())
	# @used-by :meth:`Df.Harness.Config.NativeProfile.Applier.Applier.__verify()`
	def verify_before_create(self, files: dict, retired_links: Any=()) -> None:
		if dfh_has_linked_ancestor(self.path, include_self=False):
			raise ValueError(f'Linked {self.label} parent directory appeared during migration; preserved: {self.path}')
		if self.path not in retired_links:
			if 'file-symlink' == self.kind:
				if dfh_exists(self.path) and (self.path not in files or None is not files[self.path][1]):
					raise ValueError(f'Role destination appeared during migration; preserved: {self.path}')
			elif self.legacy_dir:
				if not self.path.is_dir() or ['SKILL.md'] != sorted((p.name for p in self.path.iterdir())):
					raise ValueError(f'Legacy skill directory changed during migration; preserved: {self.path}')
			elif dfh_exists(self.path):
				raise ValueError(f'Skill destination appeared during migration; preserved: {self.path}')
	# @used-by :meth:`Df.Harness.Config.NativeProfile.Applier.Applier.__apply_links()`
	# @used-by :meth:`test_native_profiles.NativeProfileTests.test_unified_managed_link_and_manifest_helpers()`
	def verify_created(self) -> None:
		if 'file-symlink' == self.kind:
			target = Path(self.target)
			if not self.path.is_symlink() or not self.path.is_file() or (not dfh_same_path(self.path, target)) or (not self.path.samefile(target)) or (self.path.read_bytes() != target.read_bytes()):
				raise ValueError(f'New role link failed read-back verification: {self.path}')
		elif not self.path.is_dir() or (not dfh_same_path(self.path, self.target)):
			raise ValueError(f'New skill link failed read-back verification: {self.path}')
	# @used-by :meth:`Df.Harness.Config.NativeProfile.Applier.Applier.__verify()`
	# @used-by :meth:`ManagedLink.restore_retired()`
	def verify_retired(self) -> None:
		if 'file-symlink' != self.kind:
			dfh_verify_retired_directory_link(self.path, self.identity_dict())
		elif dfh_has_linked_ancestor(self.path, include_self=False) or not self.path.is_symlink() or (not dfh_link_matches_target(self.path, self.target)):
			raise ValueError(f'Obsolete role link changed during migration; preserved: {self.path}')
