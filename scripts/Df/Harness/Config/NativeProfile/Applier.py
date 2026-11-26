# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from copy import deepcopy
from pathlib import Path
from Df.Harness.Config.NativeProfile.ApplyFailure import ApplyFailure
import json
import subprocess
import uuid
# 2026-11-26 "Move turn lifecycle subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/383
class Applier:
	# @used-by :func:`agent_tools.native_profiles._execute()`
	def __init__(self, plan, primary, state, *, check: bool=False) -> None:
		self.__plan = plan
		self.__primary = primary
		self.__state = state
		self.__check = check
	# @used-by :meth:`Applier.run()`
	def __apply(self) -> dict:
		from agent_tools import native_profiles as np
		receipt = np._state_path(self.__primary)
		receipt_before = receipt.read_bytes() if receipt.exists() else None
		if None is not receipt_before and json.loads(receipt_before) != self.__state:
			raise ValueError('Native ownership changed before migration; preserved')
		self.__verify()
		updated = deepcopy(self.__state)
		backups = [np._backup(self.__primary, updated, path, before) for path, (before, _) in self.__plan.files.items() if None is not before]
		backups.extend((np._backup(self.__primary, updated, path, link.backup_payload()) for path, link in self.__plan.retired_links.items()))
		self.__verify()
		applied, created_links, retired_links = ([], [], [])
		try:
			self.__apply_files(applied)
			self.__apply_links(created_links, retired_links)
			self.__commit_receipt(receipt, receipt_before, updated)
		except (ValueError, OSError, subprocess.SubprocessError) as exc:
			self.__handle_failure(exc, updated, applied, created_links, retired_links, backups)
		self.__prune_empty_parents(applied)
		return {'backups': backups, 'linked': [str(p) for p in self.__plan.managed_links], 'removed': [str(p) for p, (_, v) in self.__plan.files.items() if None is v] + [str(p) for p in self.__plan.retired_links], 'written': [str(p) for p, (_, v) in self.__plan.files.items() if None is not v]}
	# @used-by :meth:`Applier.__apply()`
	def __apply_files(self, applied: list) -> None:
		from agent_tools import native_profiles as np
		for path, (before, after) in self.__plan.files.items():
			if np._linked_ancestor(path) or (path.read_bytes() if path.is_file() else None) != before:
				raise ValueError(f'Configuration changed before write; preserved: {path}')
			path.unlink() if None is after else np.replace_bytes(path, after)
			applied.append(path)
	# @used-by :meth:`Applier.__apply()`
	def __apply_links(self, created_links: list, retired_links: list) -> None:
		for link in self.__plan.retired_links.values():
			link.retire()
			retired_links.append(link)
		for link in self.__plan.managed_links.values():
			link.create(self.__primary)
			created_links.append(link)
			link.verify_created()
		for path, (_, after) in self.__plan.files.items():
			if None is not after and path.read_bytes() != after:
				raise ValueError(f'Native configuration read-back differs: {path}')
	# @used-by :meth:`Applier.run()`
	def __attach_profile_views(self, result: dict) -> None:
		from agent_tools import native_profiles as np
		for name, profile in result['profiles'].items():
			base = Path(profile['path'])
			local = [issue for issue in result['issues'] if np._absolute(issue['file']).is_relative_to(base)]
			global_issues = [issue for issue in result['issues'] if not any((np._absolute(issue['file']).is_relative_to(Path(item['path'])) for item in result['profiles'].values()))]
			profile.update(config=str(base), valid=not local and (not global_issues), issues=[*global_issues, *local], written=[p for p in result['written'] if np._absolute(p).is_relative_to(base)], removed=[p for p in result['removed'] if np._absolute(p).is_relative_to(base)], link_targets=profile.pop('links', {}), links=[p for p in result['linked'] if np._absolute(p).is_relative_to(base)], **self.__plan.details.get(name, {}))
	# @used-by :meth:`Applier.__apply()`
	def __commit_receipt(self, receipt: Path, receipt_before: bytes | None, updated: dict) -> None:
		from agent_tools import native_profiles as np
		updated.setdefault('shared', {}).update(self.__plan.shared)
		for path in self.__plan.removed_shared:
			updated['shared'].pop(path, None)
		updated.setdefault('profiles', {}).update(self.__plan.profiles)
		payload = np._json(updated)
		if (receipt.read_bytes() if receipt.exists() else None) != receipt_before:
			raise ValueError('Native ownership changed during migration; preserved')
		if not receipt.exists() or receipt.read_bytes() != payload:
			np.replace_bytes(receipt, payload)
	# @used-by :meth:`Applier.__apply()`
	def __handle_failure(self, exc: Exception, updated: dict, applied: list, created_links: list, retired_links: list, backups: list) -> None:
		from agent_tools import native_profiles as np
		rollback = self.__rollback(applied, created_links, retired_links)
		recovery = None
		if 'partial' == rollback['status']:
			recovery = np.data_dir_for(self.__primary) / 'native-profiles/recovery' / f'{uuid.uuid4().hex}.json'
			try:
				recovery.parent.mkdir(parents=True, exist_ok=True)
				np.create_bytes(recovery, np._json({'backups': updated.get('backups', {}), 'created_links': {str(l.path): str(l.target) for l in created_links}, 'error': str(exc), 'files': {str(p): {'after_sha256': np._hash(a) if None is not a else None, 'before_sha256': np._hash(b) if None is not b else None} for p, (b, a) in self.__plan.files.items()}, 'retired_directory_links': {str(l.path): l.identity_dict() for l in retired_links if 'file-symlink' != l.kind}, 'retired_links': {str(l.path): str(l.target) for l in retired_links if 'file-symlink' == l.kind}, 'rollback': rollback, 'schema_version': 1}))
			except OSError as rec_err:
				rollback['issues'].append({'file': str(recovery), 'message': f'Recovery receipt could not be saved: {rec_err}'})
				recovery = None
		raise ApplyFailure(exc, rollback, backups, str(recovery) if recovery else None) from exc
	# @used-by :meth:`Applier.__apply()`
	def __prune_empty_parents(self, applied: list) -> None:
		from agent_tools import native_profiles as np
		for path in applied:
			if None is self.__plan.files[path][1]:
				parent = path.parent
				if 'SKILL.md' == path.name and 'skills' == parent.parent.name and '.agents' == parent.parent.parent.name:
					if np._linked(parent) or (not self.__try_rmdir(parent)):
						continue
					parent = parent.parent
				while parent.name in ('agents', '.codex', 'skills', '.agents') and parent.is_dir() and (not np._linked(parent)) and self.__try_rmdir(parent):
					parent = parent.parent
	# @used-by :meth:`Applier.__handle_failure()`
	def __rollback(self, applied: list, created_links: list, retired_links: list) -> dict:
		issues, restored = ([], [])
		for link in reversed(created_links):
			try:
				link.remove_created()
				restored.append(str(link.path))
			except (ValueError, OSError, subprocess.SubprocessError) as exc:
				issues.append({'file': str(link.path), 'message': str(exc)})
		self.__rollback_files(applied, restored, issues)
		for link in reversed(retired_links):
			try:
				link.restore_retired(self.__primary)
				restored.append(str(link.path))
			except (ValueError, OSError, subprocess.SubprocessError) as exc:
				issues.append({'file': str(link.path), 'message': str(exc)})
		return {'issues': issues, 'restored': restored, 'status': 'partial' if issues else 'complete'}
	# @used-by :meth:`Applier.__rollback()`
	def __rollback_files(self, applied: list, restored: list, issues: list) -> None:
		from agent_tools import native_profiles as np
		for path in reversed(applied):
			try:
				before, after = self.__plan.files[path]
				if np._linked_ancestor(path):
					raise ValueError('Linked path prevents rollback; backup retained')
				if (path.read_bytes() if path.is_file() else None) != after:
					raise ValueError('Concurrent edit prevents rollback; backup retained')
				path.unlink(missing_ok=True) if None is before else np.replace_bytes(path, before)
				restored.append(str(path))
			except (ValueError, OSError, subprocess.SubprocessError) as exc:
				issues.append({'file': str(path), 'message': str(exc)})
	# @used-by :meth:`Applier.__prune_empty_parents()`
	@staticmethod
	def __try_rmdir(parent: Path) -> bool:
		try:
			parent.rmdir()
			r = True
		except OSError:
			r = False
		return r
	# @used-by :meth:`Applier.__apply()`
	def __verify(self) -> None:
		from agent_tools import native_profiles as np
		for path, (before, _) in self.__plan.files.items():
			if np._linked_ancestor(path) or (path.read_bytes() if path.is_file() else None) != before:
				raise ValueError(f'Configuration changed during migration; external edit preserved: {path}')
		for link in self.__plan.managed_links.values():
			link.verify_before_create(self.__plan.files, self.__plan.retired_links)
		for link in self.__plan.retired_links.values():
			link.verify_retired()
	# @used-by :func:`agent_tools.native_profiles._execute()`
	def run(self) -> dict:
		issues = self.__plan.readonly_issues() if self.__check else self.__plan.issues
		result = {'backups': [], 'issues': issues, 'linked': [], 'profiles': deepcopy(self.__plan.profiles), 'removed': [], 'valid': not issues, 'verification': 'filesystem-only', 'written': []}
		if not issues and (not self.__check):
			try:
				result.update(self.__apply())
			except (ValueError, OSError, subprocess.SubprocessError) as exc:
				result['valid'] = False
				result['issues'].append({'file': str(self.__primary), 'message': str(exc)})
				if isinstance(exc, ApplyFailure):
					result.update(rollback=exc.rollback, backups=exc.backups, recovery_receipt=exc.recovery)
					result['issues'].extend(exc.rollback['issues'])
		self.__attach_profile_views(result)
		return result
