# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from pathlib import Path
import os
# 2026-11-26 "Move turn lifecycle subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/383
class ManagedLink:
	# @used-by :func:`agent_tools.native_profiles._codex_plan()`
	# @used-by :func:`agent_tools.native_profiles._plan_codex_link()`
	# @used-by :func:`agent_tools.native_profiles._retire_profile_roles()`
	# @used-by :func:`agent_tools.native_profiles._retire_profile_skills()`
	# @used-by :meth:`test_native_profiles.NativeProfileTests.test_unified_managed_link_and_manifest_helpers()`
	def __init__(self, path, target, kind, *, label='skill', legacy_dir=False) -> None:
		from agent_tools import native_profiles as np
		self.path = np._absolute(path)
		self.target = target if isinstance(target, str) and kind in ('directory-junction', 'directory-symlink') else Path(target)
		self.kind = kind
		self.label = label
		self.legacy_dir = legacy_dir
	# @used-by :meth:`Df.Harness.Config.NativeProfile.Applier.Applier.__apply()`
	def backup_payload(self) -> bytes:
		from agent_tools import native_profiles as np
		return np._json(self.identity_dict())
	# @used-by :meth:`test_native_profiles.NativeProfileTests.test_unified_managed_link_and_manifest_helpers()`
	def create(self, primary) -> None:
		from agent_tools import native_profiles as np
		if np._linked_ancestor(self.path, include_self=False):
			raise ValueError(f'Linked {self.label} parent directory appeared before creation; preserved: {self.path}')
		if self.legacy_dir:
			self.path.rmdir()
		if 'file-symlink' == self.kind:
			np._file_link(self.target, self.path, primary)
		else:
			np._directory_link(self.target, self.path, primary)
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
		from agent_tools import native_profiles as np
		np._remove_link(self.path, self.target)
	# @used-by :meth:`Df.Harness.Config.NativeProfile.Applier.Applier.__rollback()`
	def restore_retired(self, primary) -> None:
		from agent_tools import native_profiles as np
		if 'file-symlink' == self.kind:
			if np._exists(self.path) or np._linked_ancestor(self.path, include_self=False):
				raise ValueError('Obsolete role destination changed before rollback; preserved')
			np._file_link(self.target, self.path, primary)
		else:
			if np._exists(self.path) or np._linked(self.path) or np._linked_ancestor(self.path, include_self=False):
				raise ValueError('Obsolete skill destination changed before rollback; preserved')
			np._restore_directory_link(self.path, self.identity_dict(), primary)
			self.verify_retired()
	# @used-by :meth:`Df.Harness.Config.NativeProfile.Applier.Applier.__apply_links()`
	def retire(self) -> None:
		from agent_tools import native_profiles as np
		if 'file-symlink' == self.kind:
			np._remove_link(self.path, self.target)
		else:
			np._retire_directory_link(self.path, self.identity_dict())
	# @used-by :meth:`Df.Harness.Config.NativeProfile.Applier.Applier.__verify()`
	def verify_before_create(self, files, retired_links=()) -> None:
		from agent_tools import native_profiles as np
		if np._linked_ancestor(self.path, include_self=False):
			raise ValueError(f'Linked {self.label} parent directory appeared during migration; preserved: {self.path}')
		if self.path not in retired_links:
			if 'file-symlink' == self.kind:
				if np._exists(self.path) and (self.path not in files or None is not files[self.path][1]):
					raise ValueError(f'Role destination appeared during migration; preserved: {self.path}')
			elif self.legacy_dir:
				if not self.path.is_dir() or ['SKILL.md'] != sorted((p.name for p in self.path.iterdir())):
					raise ValueError(f'Legacy skill directory changed during migration; preserved: {self.path}')
			elif np._exists(self.path):
				raise ValueError(f'Skill destination appeared during migration; preserved: {self.path}')
	# @used-by :meth:`Df.Harness.Config.NativeProfile.Applier.Applier.__apply_links()`
	# @used-by :meth:`test_native_profiles.NativeProfileTests.test_unified_managed_link_and_manifest_helpers()`
	def verify_created(self) -> None:
		from agent_tools import native_profiles as np
		if 'file-symlink' == self.kind:
			target = Path(self.target)
			if not self.path.is_symlink() or not self.path.is_file() or (not np._same_path(self.path, target)) or (not self.path.samefile(target)) or (self.path.read_bytes() != target.read_bytes()):
				raise ValueError(f'New role link failed read-back verification: {self.path}')
		elif not self.path.is_dir() or (not np._same_path(self.path, self.target)):
			raise ValueError(f'New skill link failed read-back verification: {self.path}')
	# @used-by :meth:`Df.Harness.Config.NativeProfile.Applier.Applier.__verify()`
	# @used-by :meth:`ManagedLink.restore_retired()`
	def verify_retired(self) -> None:
		from agent_tools import native_profiles as np
		if 'file-symlink' != self.kind:
			np._verify_retired_directory_link(self.path, self.identity_dict())
		elif np._linked_ancestor(self.path, include_self=False) or not self.path.is_symlink() or (not np._link_matches_target(self.path, self.target)):
			raise ValueError(f'Obsolete role link changed during migration; preserved: {self.path}')
