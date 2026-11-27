# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from contextlib import nullcontext
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any
from Df.Core.lib.array.first import df_first
from Df.Harness.Cleanup.StoreResolver import StoreResolver
from Df.Harness.Runtime.SettingsLoader import SettingsLoader
from Df.Harness.lib.cleanup_audit_ops import dfh_maybe_write_cleanup_manifest
from Df.Harness.lib.cleanup_mutation_ops import dfh_finish_pending, dfh_remove_antigravity, dfh_restore_antigravity
from Df.Harness.lib.cleanup_store_ops import STATUS_NAMES, dfh_antigravity_projects, dfh_candidates, dfh_catalog_projects, dfh_codex_glob_scope, dfh_conversations, dfh_count_indexed_conversations, dfh_linked, dfh_load_conversation_index, dfh_read_store_json
from Df.Harness.lib.path_resolve import dfh_store_path
from Df.Harness.lib.runtime_context import dfh_platform_name
from Df.Harness.lib.storage import dfh_locked
import sqlite3
# 2026-11-26 "Move turn lifecycle subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/383
class Scanner:
	# @used-by :func:`agent_tools.cleanup.cleanup_projects()`
	def __init__(self, *, apply=False, daily_root=None, now=None, config=None, ag_directory=None, ag_backend=None, folders=None, control=None, _ops=None) -> None:
		self.__ops = _ops or {}
		self.__apply = apply
		self.__config = config or self.__op('settings', lambda: SettingsLoader().run())()
		daily = Path(daily_root or Path(self.__config['workspace_root']) / self.__config['daily_root']).absolute()
		if dfh_linked(daily) or (not daily.is_dir()):
			raise ValueError('Daily archive must be an existing unlinked directory')
		self.__daily = daily.resolve()
		self.__now = now or datetime.now(timezone.utc)
		if None is self.__now.tzinfo:
			raise ValueError('Cleanup time must include a timezone')
		stores = StoreResolver(self.__config, self.__daily, ag_directory=ag_directory, ag_backend=ag_backend, folders=folders).run()
		self.__init_stores(stores, control)
		self.__catalog = None
		self.__history = None
		self.__result = self.__init_result()
	# @used-by :meth:`Scanner.__apply_removal()`
	# @used-by :meth:`Scanner.__evaluate_candidate_entry()`
	def __ag_flat(self, ag):
		return ag if self.__single_ag_mode else [p for plist in ag.values() for p in plist]
	# @used-by :meth:`Scanner.__apply_removal()`
	def __apply_ag_removal(self, root: Path, ag, live_check) -> dict:
		rem_fn = self.__op('remove_antigravity', dfh_remove_antigravity)
		if self.__single_ag_mode:
			r = rem_fn(root, self.__directory, self.__folder_file, ag, live_check)
		else:
			ag_results = {iid: rem_fn(root, self.__ag_stores[iid]['directory'], self.__folder_file, plist, live_check) for iid, plist in ag.items() if plist}
			r = {'complete': True, 'instances': ag_results, 'removed_projects': [pid for res in ag_results.values() for pid in res['removed_projects']], 'removed_folders': [fid for res in ag_results.values() for fid in res['removed_folders']]}
		return r
	# @used-by :meth:`Scanner.__handle_eligible()`
	def __apply_removal(self, entry: dict, root: Path, ag, cx: list, live_check) -> None:
		live_check()
		ag_flat = self.__ag_flat(ag)
		ag_meta = self.__build_ag_meta(ag_flat)
		proceed = True
		if cx:
			entry['codex'] = self.__control({'command': 'shared-cleanup-project', 'deferCommit': True, 'sharedId': cx[0]['id'], 'rootPaths': [str(root)], 'bindings': cx[0]['bindings'], 'antigravity': ag_meta})
			if True is not entry['codex'].get('complete'):
				entry['status'], self.__result['complete'], proceed = ('pending', False, False)
		if proceed and ag_flat:
			entry['antigravity'] = self.__apply_ag_removal(root, ag, live_check)
		if proceed and cx:
			entry['codex_commit'] = self.__control({'command': 'shared-cleanup-project', 'commit': True, 'sharedId': cx[0]['id'], 'rootPaths': [str(root)], 'bindings': cx[0]['bindings'], 'antigravity': ag_meta})
			if True is not entry['codex_commit'].get('complete'):
				entry['status'], self.__result['complete'], proceed = ('pending', False, False)
		if proceed:
			self.__finalize_removal(entry, root)
	# @used-by :meth:`Scanner.__apply_removal()`
	def __build_ag_meta(self, ag_flat: list) -> dict:
		raw_ag_dbs = [self.__backend / 'conversation_summaries.db'] if self.__single_ag_mode else [s['conversations_db'] for s in self.__ag_stores.values()]
		ag_dbs = [str(p) for p in sorted(raw_ag_dbs, key=lambda p: (0 if p.is_file() else 1))]
		return {'database': df_first(ag_dbs), 'databases': ag_dbs, 'projectIds': [p['id'] for p in ag_flat]}
	# @used-by :meth:`Scanner.__evaluate_candidate_entry()`
	# @used-by :meth:`Scanner.__try_preserve_unresolved()`
	def __collect_ag_projects(self, root: Path):
		ag_fn = self.__op('antigravity_projects', dfh_antigravity_projects)
		return ag_fn(self.__directory, root) if self.__single_ag_mode else {iid: ag_fn(store['directory'], root) if store['directory'].is_dir() else [] for iid, store in self.__ag_stores.items()}
	# @used-by :meth:`Scanner.__evaluate_candidate_entry()`
	# @used-by :meth:`Scanner.__try_preserve_unresolved()`
	def __discover_conversations(self, root: Path, ag, cx: list) -> dict:
		conv_fn = self.__op('conversations', dfh_conversations)
		default_conv = self.__op('default_conversations', dfh_conversations)
		if conv_fn is not default_conv:
			r = conv_fn(root, ag, self.__backend, self.__homes, cx)
		else:
			if None is self.__history:
				self.__history = self.__op('load_index', dfh_load_conversation_index)(self.__backend, self.__homes)
			r = self.__op('count_indexed', dfh_count_indexed_conversations)(root, ag, self.__homes, cx, self.__history)
		return r
	# @used-by :meth:`Scanner.__inspect_candidate()`
	def __evaluate_candidate_entry(self, entry: dict, root: Path) -> None:
		cx, ag = ([], [] if self.__single_ag_mode else {iid: [] for iid in self.__ag_stores})
		try:
			ag = self.__collect_ag_projects(root)
			cx = self.__op('catalog_projects', dfh_catalog_projects)(self.__catalog, root, self.__homes)
			counts = self.__discover_conversations(root, ag, cx)
			entry['conversations'] = counts
			ag_flat = self.__ag_flat(ag)
			if not ag_flat and (not cx) and (not any(counts.values())):
				entry['status'] = 'already-absent'
			elif any(counts.values()):
				entry.update(status='preserved', error='Project has conversations')
				self.__recover_preserved(entry, root, cx)
			else:
				self.__handle_eligible(entry, root, ag, cx, ag_flat)
		except (OSError, ValueError, RuntimeError, KeyError, TypeError, sqlite3.Error) as exc:
			self.__record_candidate_error(entry, root, ag, cx, exc)
	# @used-by :meth:`Scanner.__apply_removal()`
	def __finalize_removal(self, entry: dict, root: Path) -> None:
		finish_fn = self.__op('finish_pending', dfh_finish_pending)
		for store in self.__ag_stores.values():
			if store['directory'].is_dir():
				with dfh_locked(store['directory'] / '\ua616/data/registration.lock'):
					finish_fn(store['directory'], root)
		entry['status'] = 'removed'
		if self.__homes:
			self.__catalog = self.__control({'command': 'shared-catalog'})
	# @used-by :meth:`Scanner.__evaluate_candidate_entry()`
	def __handle_eligible(self, entry: dict, root: Path, ag, cx: list, ag_flat: list) -> None:
		entry['status'] = 'eligible'
		entry['native_projects'] = {'antigravity': [p['id'] for p in ag_flat], 'codex': [p['id'] for p in cx]}
		if not self.__single_ag_mode:
			entry['native_projects']['antigravity_instances'] = {iid: [p['id'] for p in plist] for iid, plist in ag.items() if plist}
		if self.__apply:
			conv_fn = self.__op('conversations', dfh_conversations)
			# @used-by :meth:`Scanner.__handle_eligible()`
			def live_check() -> None:
				live = conv_fn(root, ag, self.__backend, self.__homes, cx)
				entry['conversations'] = live
				if any(live.values()):
					raise ValueError('Project has conversations')
			self.__apply_removal(entry, root, ag, cx, live_check)
	# @used-by :meth:`Scanner.__init__()`
	def __init_result(self) -> dict[str, Any]:
		return {
			'complete': True,
			'mode': 'apply' if self.__apply else 'dry-run',
			'platform': dfh_platform_name(config=self.__config),
			'cutoff': (self.__now - timedelta(days=3)).isoformat(),
			'archive_preserved': str(self.__daily),
			'active_instances': {'antigravity': list(self.__ag_stores), 'codex': list(self.__homes)},
			'history_instances': self.__readonly_history['history_instances'],
			'skipped_disabled_instances': self.__readonly_history['skipped_disabled'],
			'projects': [],
			'issues': [],
		}
	# @used-by :meth:`Scanner.__init__()`
	def __init_stores(self, stores: dict[str, Any], control) -> None:
		self.__single_ag_mode = stores['single_ag_mode']
		self.__ag_stores = stores['ag_stores']
		self.__directory = stores['directory']
		self.__backend = stores['backend']
		self.__folder_file = stores['folder_file']
		self.__homes = stores['homes']
		self.__home_globs = stores['home_globs']
		self.__readonly_history = stores['readonly_history']
		if None is control:
			from Df.Harness.lib.codex_control import dfh_shared_control
			control = dfh_shared_control
		self.__control = control
	# @used-by :meth:`Scanner.run()`
	def __inspect_candidate(self, item: dict) -> None:
		entry = {**item, 'status': 'recent' if not item['old_enough'] else 'checking'}
		self.__result['projects'].append(entry)
		if item['old_enough']:
			self.__evaluate_candidate_entry(entry, Path(item['root']))
	# @used-by :meth:`Scanner.run()`
	def __inspect_unresolved(self, issues: list) -> None:
		for issue in issues:
			if not self.__try_preserve_unresolved(issue):
				self.__result['issues'].append(issue)
		self.__result['discovery']['unresolved_entries'] = len(self.__result['issues'])
	# @used-by :meth:`Scanner.__apply_ag_removal()`
	# @used-by :meth:`Scanner.__collect_ag_projects()`
	# @used-by :meth:`Scanner.__discover_conversations()`
	# @used-by :meth:`Scanner.__evaluate_candidate_entry()`
	# @used-by :meth:`Scanner.__finalize_removal()`
	# @used-by :meth:`Scanner.__handle_eligible()`
	# @used-by :meth:`Scanner.__init__()`
	# @used-by :meth:`Scanner.__record_candidate_error()`
	# @used-by :meth:`Scanner.__recover_ag()`
	# @used-by :meth:`Scanner.__recover_preserved()`
	# @used-by :meth:`Scanner.__try_preserve_unresolved()`
	# @used-by :meth:`Scanner.run()`
	def __op(self, name: str, default):
		return self.__ops.get(name, default)
	# @used-by :meth:`Scanner.run()`
	def __prepare_stores(self, issues: list) -> bool:
		r = True
		try:
			if self.__homes:
				self.__catalog = self.__control({'command': 'shared-catalog'})
				if not isinstance(self.__catalog, dict):
					raise RuntimeError('Shared-Projects is initializing; retry cleanup')
			if None is not self.__folder_file:
				dfh_read_store_json(self.__folder_file)
		except (OSError, ValueError, RuntimeError) as exc:
			self.__result.update(complete=False, issues=[*issues, {'error': str(exc)}])
			r = False
		return r
	# @used-by :meth:`Scanner.__evaluate_candidate_entry()`
	def __record_candidate_error(self, entry: dict, root: Path, ag, cx: list, exc: Exception) -> None:
		try:
			entry['conversations'] = self.__op('conversations', dfh_conversations)(root, ag, self.__backend, self.__homes, cx)
		except (OSError, ValueError, TypeError, sqlite3.Error):
			pass
		entry.update(status='preserved' if any(entry.get('conversations', {}).values()) else 'blocked', error=str(exc))
		if 'preserved' == entry['status']:
			self.__recover_preserved(entry, root, cx)
		elif 'blocked' == entry['status']:
			self.__result['complete'] = False
	# @used-by :meth:`Scanner.__recover_preserved()`
	def __recover_ag(self, entry: dict, root: Path) -> None:
		restore_fn = self.__op('restore_antigravity', dfh_restore_antigravity)
		if self.__single_ag_mode:
			entry['antigravity_recovery'] = restore_fn(root, self.__directory, self.__folder_file)
		elif self.__ag_stores:
			rec = {iid: restore_fn(root, store['directory'], self.__folder_file) for iid, store in self.__ag_stores.items() if store['directory'].is_dir()}
			entry['antigravity_recovery'] = {'complete': all((v.get('complete') for v in rec.values())), 'instances': rec}
	# @used-by :meth:`Scanner.__evaluate_candidate_entry()`
	# @used-by :meth:`Scanner.__record_candidate_error()`
	# @used-by :meth:`Scanner.__try_preserve_unresolved()`
	def __recover_preserved(self, entry: dict, root: Path, cx: list) -> None:
		if self.__apply:
			try:
				self.__recover_ag(entry, root)
				if cx:
					current_cx = self.__op('catalog_projects', dfh_catalog_projects)(self.__control({'command': 'shared-catalog'}), root, self.__homes)
					if any((p['cleanup_hold'] for p in current_cx)):
						entry['recovery'] = self.__control({'command': 'shared-cleanup-project', 'preserve': True, 'sharedId': cx[0]['id'], 'rootPaths': [str(root)], 'bindings': cx[0]['bindings']})
						if True is not entry['recovery'].get('complete'):
							self.__result['complete'] = False
			except (OSError, ValueError, RuntimeError) as recovery_error:
				entry['recovery_error'] = str(recovery_error)
				self.__result['complete'] = False
	# @used-by :meth:`Scanner.__inspect_unresolved()`
	def __try_preserve_unresolved(self, issue: dict) -> bool:
		root = Path(issue['root'])
		preserved = False
		try:
			if dfh_linked(root) or (not root.resolve().is_relative_to(self.__daily)):
				raise ValueError('Linked or escaped archive entry preserved')
			ag = self.__collect_ag_projects(root)
			cx = self.__op('catalog_projects', dfh_catalog_projects)(self.__catalog, root, self.__homes)
			counts = self.__discover_conversations(root, ag, cx)
			if any(counts.values()):
				entry = {'root': str(root), 'status': 'preserved', 'conversations': counts}
				self.__result['projects'].append(entry)
				self.__result['discovery']['excluded_with_conversations'] += 1
				self.__recover_preserved(entry, root, cx)
				preserved = True
		except (OSError, ValueError, RuntimeError, KeyError, TypeError, sqlite3.Error):
			pass
		return preserved
	# @used-by :func:`agent_tools.cleanup.cleanup_projects()`
	def run(self) -> dict[str, Any]:
		with dfh_locked(dfh_store_path('cleanup_lock')) if self.__apply else nullcontext(), dfh_codex_glob_scope(self.__home_globs, self.__readonly_history):
			found, issues = self.__op('candidates', dfh_candidates)(self.__daily, self.__config, self.__now)
			self.__result['discovery'] = {'verified_projects': len(found), 'modern_projects': sum(('project.json' == p['initialization_basis'] for p in found)), 'legacy_projects': sum(('project.json' != p['initialization_basis'] for p in found)), 'excluded_with_conversations': 0, 'unresolved_entries': len(issues)}
			if self.__prepare_stores(issues):
				self.__inspect_unresolved(issues)
				for item in found:
					self.__inspect_candidate(item)
				if self.__result['issues']:
					self.__result['complete'] = False
				self.__result['counts'] = {name: sum((p['status'] == name for p in self.__result['projects'])) for name in STATUS_NAMES}
				self.__op('maybe_manifest', dfh_maybe_write_cleanup_manifest)(self.__result, apply=self.__apply, now=self.__now, config=self.__config, linked_fn=dfh_linked)
		return self.__result
