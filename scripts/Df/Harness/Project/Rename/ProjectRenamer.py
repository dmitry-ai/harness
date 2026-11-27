# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from agent_tools.path_cache import clear_path_cache
from agent_tools.path_registry import clear_registry_cache, project_paths, store_path
from agent_tools.runtime import platform_instances, request_day, settings
from agent_tools.storage import locked, replace_bytes
from Df.Harness.Project.DomainNormalizer import DomainNormalizer
from Df.Harness.Project.InitLabelResolver import InitLabelResolver
from Df.Harness.Project.LabelError import LabelError
from Df.Harness.Project.Registry import Registry
from Df.Harness.Project.Rename.PostRenameVerifier import PostRenameVerifier
from Df.Harness.Project.Rename.RenameLineage import RenameLineage
from Df.Harness.Project.Rename.StateRewriter import StateRewriter
import json
import os
from pathlib import Path
import re
import uuid
_SEQ_PREFIX_RE = re.compile(r'^(\d+) - (.+)$')
# 2026-11-26 "Move analysis workflow classes into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/380
class ProjectRenamer:
	# @used-by :func:`agent_tools.project_rename.rename_project()`
	# @used-by :meth:`ProjectRenamer.maybe_promote_domain()`
	# @used-by :meth:`test_df_harness_s11_wave2a_project_ext.DfHarnessS11Wave2aProjectExtTests.test_project_rename_classes()`
	# @used-by :meth:`test_df_harness_s11_wave2a_project_ext.DfHarnessS11Wave2aProjectExtTests.test_z_project_rename_full_coverage()`
	def __init__(self, project_root: str | Path, *, domain: str | None=None, topic: str | None=None, daily_root: Path | None=None, register_native: bool | None=None, antigravity_projects_dirs: dict[str, Path] | None=None, antigravity_folders_json: Path | None=None, targets: list[str] | None=None, registrars: dict | None=None, launcher_root: Path | None=None, update_index_fn=None, pre_snap_fn=None, verify_fn=None) -> None:
		self.__project_root, self.__domain, self.__topic = (project_root, domain, topic)
		self.__daily_root, self.__register_native = (daily_root, register_native)
		self.__ag_dirs, self.__folders_json = (antigravity_projects_dirs, antigravity_folders_json)
		self.__targets, self.__registrars, self.__launcher_root = (targets, registrars, launcher_root)
		self.__update_index_fn, self.__pre_snap_fn, self.__verify_fn = (update_index_fn, pre_snap_fn, verify_fn)
	# @used-by :meth:`ProjectRenamer.__build_ag_registrar()`
	# @used-by :meth:`ProjectRenamer.__sync_registrations()`
	@staticmethod
	def __antigravity_dirs_map(override: dict[str, Path] | None) -> dict[str, Path]:
		if None is not override:
			r = {k: Path(v) for k, v in override.items()}
		else:
			insts = platform_instances('antigravity', include_disabled=False)
			ordered = sorted(insts.items(), key=lambda kv: (0 if kv[1].get('primary') else 1, kv[0]))
			r = {iid: Path(inst['system_paths']['projects_dir']) for iid, inst in ordered if inst.get('system_paths', {}).get('projects_dir')}
		return r
	# @used-by :meth:`ProjectRenamer.rename()`
	def __apply_mutations(self, old_root: Path, new_root: Path, new_label: str, new_kind: str, pj_old: dict, eff_launcher: Path | None, pre_snap: dict, backups: list, state_moves: list) -> tuple[str | None, dict | None, dict]:
		clear_path_cache()
		clear_registry_cache()
		idx_fn = self.update_projects_index if None is self.__update_index_fn else self.__update_index_fn
		idx_file = idx_fn(old_root, new_root, pj_old['job_id'], self.__daily_root, backups)
		StateRewriter(old_root, new_root, new_label, new_kind, backups=backups, state_moves=state_moves).rewrite()
		if None is not eff_launcher:
			StateRewriter.rewrite_launcher_handoffs(eff_launcher, old_root, new_root, backups=backups)
		reg_info = self.__sync_registrations(old_root, new_root, new_label, pj_old.get('request_date'), backups)
		post_ver = PostRenameVerifier(old_root, new_root, pre_snap, launcher_root=eff_launcher).verify() if None is self.__verify_fn else self.__verify_fn(old_root, new_root, pre_snap, launcher_root=eff_launcher)
		return (idx_file, reg_info, post_ver)
	# @used-by :meth:`ProjectRenamer.__sync_registrations()`
	@classmethod
	def __build_ag_registrar(cls, ag_dirs: dict[str, Path] | None, folders_json: Path | None, preferred_id: str | None):
		from agent_tools.platforms.antigravity import register as ag_default, register_antigravity_project
		if None is ag_dirs and None is folders_json:
			r = None
		else:
			dirs = cls.__antigravity_dirs_map(ag_dirs)
			# @used-by :meth:`ProjectRenamer.__build_ag_registrar()`
			def _reg(project, label, day):
				per_inst, first, pid = ({}, None, preferred_id)
				for iid, pdir in dirs.items():
					rec = register_antigravity_project(project, label, day, projects_dir=pdir, folders_json_path=folders_json, preferred_id=pid)
					pid = pid or rec['project_id']
					per_inst[iid] = rec
					first = rec if None is first else first
				return {**first, 'instances': per_inst} if None is not first else ag_default(project, label, day)
			r = _reg
		return r
	# @used-by :meth:`ProjectRenamer.__rename_dir_safe()`
	@staticmethod
	def __do_dir_rename(old_root: Path, new_root: Path) -> None:
		if old_root.name.casefold() == new_root.name.casefold() and old_root.name != new_root.name:
			tmp_root = old_root.parent / f'.rename-tmp-{uuid.uuid4().hex[:10]}'
			os.rename(old_root, tmp_root)
			os.rename(tmp_root, new_root)
		else:
			os.rename(old_root, new_root)
	# @used-by :meth:`ProjectRenamer.__sync_antigravity_native_files()`
	@classmethod
	def __extract_prior_ag_id(cls, new_root: Path, ag_dirs: dict[str, Path], old_root: Path) -> str | None:
		regs_f = project_paths(new_root, exact_root=True).registrations_json
		r: str | None = None
		if regs_f.is_file():
			try:
				ag = json.loads(regs_f.read_text(encoding='utf-8-sig')).get('antigravity') or {}
				r = ag.get('project_id') or (ag.get('last_success') or {}).get('project_id')
			except (OSError, ValueError):
				r = None
		if None is r:
			r = cls.__scan_ag_dirs_for_uri(ag_dirs, old_root.as_uri().casefold())
		return r
	# @used-by :meth:`ProjectRenamer.rename()`
	@classmethod
	def __rename_dir_safe(cls, old_root: Path, new_root: Path) -> Path | None:
		prev_cwd = Path.cwd().resolve()
		moved_cwd = prev_cwd if prev_cwd == old_root or prev_cwd.is_relative_to(old_root) else None
		if None is not moved_cwd:
			os.chdir(old_root.parent)
		try:
			cls.__do_dir_rename(old_root, new_root)
		except PermissionError as exc:
			if None is not moved_cwd:
				os.chdir(moved_cwd)
			raise PermissionError(f'Cannot rename locked project directory "{old_root}" -> "{new_root}": close open handles referencing this folder and retry ({exc})') from exc
		except OSError:
			if None is not moved_cwd:
				os.chdir(moved_cwd)
			raise
		return moved_cwd
	# @used-by :meth:`ProjectRenamer.rename()`
	@staticmethod
	def __rollback(old_root: Path, new_root: Path, same_dir: bool, moved_cwd: Path | None, backups: list, state_moves: list) -> None:
		for path, raw in reversed(backups):
			try:
				path.unlink(missing_ok=True) if None is raw else replace_bytes(path, raw)
			except OSError:
				pass
		for old_st, new_st in reversed(state_moves):
			if new_st.is_dir() and (not old_st.exists()):
				os.replace(new_st, old_st)
		if (not same_dir) and new_root.is_dir() and (not old_root.exists()):
			os.rename(new_root, old_root)
		if None is not moved_cwd and old_root.is_dir():
			os.chdir(moved_cwd)
		clear_path_cache()
		clear_registry_cache()
	# @used-by :meth:`ProjectRenamer.__extract_prior_ag_id()`
	@staticmethod
	def __scan_ag_dirs_for_uri(ag_dirs: dict[str, Path], old_uri: str) -> str | None:
		r: str | None = None
		for pdir in ag_dirs.values():
			for cand in sorted(pdir.glob('*.json')) if pdir.is_dir() else ():
				try:
					item = json.loads(cand.read_text(encoding='utf-8-sig'))
					res = (item.get('projectResources') or {}).get('resources') or []
					if any((isinstance(x, dict) and str(x.get('folderUri') or '').casefold() == old_uri for x in res)):
						r = item.get('id') or cand.stem
						break
				except (OSError, ValueError):
					continue
			if None is not r:
				break
		return r
	# @used-by :meth:`ProjectRenamer.__sync_registrations()`
	@classmethod
	def __sync_antigravity_native_files(cls, old_root: Path, new_root: Path, new_label: str, day_str: str, ag_dirs: dict[str, Path], backups: list) -> str | None:
		new_name = f'{new_label} - U.P.{request_day(day_str):%Y.%m.%d}'
		pid = cls.__extract_prior_ag_id(new_root, ag_dirs, old_root)
		if None is not pid:
			for pdir in ag_dirs.values():
				target = pdir / f'{pid}.json'
				if target.is_file():
					with locked(pdir / '\ua616' / 'data' / 'registration.lock'):
						raw = target.read_bytes()
						backups.append((target, raw))
						payload = json.loads(raw.decode('utf-8-sig'))
						payload['name'] = new_name
						payload['projectResources'] = {**(payload.get('projectResources') or {}), 'resources': [{'folderUri': new_root.as_uri()}]}
						replace_bytes(target, (json.dumps(payload, ensure_ascii=False, indent=2) + '\n').encode('utf-8'))
		return pid
	# @used-by :meth:`ProjectRenamer.__apply_mutations()`
	def __sync_registrations(self, old_root: Path, new_root: Path, new_label: str, day_str: str, backups: list) -> dict | None:
		daily_default = (Path(settings()['workspace_root']).resolve() / settings()['daily_root']).resolve()
		regs_f = project_paths(new_root, exact_root=True).registrations_json
		should = self.__register_native if None is not self.__register_native else (regs_f.is_file() or new_root.is_relative_to(daily_default))
		r = None
		if should:
			pid = self.__sync_antigravity_native_files(old_root, new_root, new_label, day_str, self.__antigravity_dirs_map(self.__ag_dirs), backups)
			eff_regs = dict(self.__registrars or {})
			if 'antigravity' not in eff_regs:
				custom_ag = self.__build_ag_registrar(self.__ag_dirs, self.__folders_json, pid)
				if None is not custom_ag:
					eff_regs['antigravity'] = custom_ag
			backups.append((regs_f, regs_f.read_bytes() if regs_f.is_file() else None))
			old_sha = RenameLineage.capture_file_sha(regs_f)
			r = Registry(new_root, new_label, day_str).register(targets=self.__targets, registrars=eff_regs or None, single=False)
			StateRewriter.refresh_workflow_file_hash(new_root, regs_f, old_sha)
		return r
	# @used-by :meth:`ProjectRenamer.rename()`
	def __validate_inputs(self) -> tuple[Path, Path, str, str, dict]:
		old_root = Path(self.__project_root).resolve()
		pj_path = project_paths(old_root, exact_root=True).project_json
		if not old_root.is_dir() or (not pj_path.is_file()):
			raise ValueError(f'Existing Upwork project with \ua616/project.json required: {old_root}')
		if not self.__domain and (not self.__topic):
			raise LabelError('Specify --domain <host> or --topic "<Title>" for rename-project')
		new_label, new_kind, _ = InitLabelResolver(domain=self.__domain, topic=self.__topic, strict_domain=bool(self.__domain)).resolve()
		pj_old = json.loads(pj_path.read_text(encoding='utf-8-sig'))
		match = _SEQ_PREFIX_RE.match(old_root.name)
		new_root = old_root.parent / (f'{match.group(1)} - {new_label}' if match else new_label)
		if new_root != old_root and new_root.exists() and old_root.name.casefold() != new_root.name.casefold():
			raise FileExistsError(f'Target project directory already exists: {new_root}')
		return (old_root, new_root, new_label, new_kind, pj_old)
	# @used-by :func:`agent_tools.project_rename.apply_domain_promotion()`
	# @used-by :meth:`test_df_harness_s11_wave2a_project_ext.DfHarnessS11Wave2aProjectExtTests.test_z_project_rename_full_coverage()`
	@classmethod
	def apply_domain_promotion(cls, project_root: Path, analysis_value: dict, result: dict, *, register_native: bool | None=None, launcher_root: Path | None=None, maybe_promote_fn=None) -> dict:
		promo = cls.maybe_promote_domain(project_root, analysis_value, register_native=register_native, launcher_root=launcher_root) if None is maybe_promote_fn else maybe_promote_fn(project_root, analysis_value, register_native=register_native, launcher_root=launcher_root)
		result['domain_promotion'] = promo
		if False is promo.get('valid'):
			result['valid'] = False
		elif promo.get('renamed'):
			new_root, old_str = (Path(promo['project_dir']), str(Path(project_root).resolve()))
			result['project_dir'] = str(new_root)
			for key in ('target', 'output'):
				if isinstance(result.get(key), str) and old_str in result[key]:
					result[key] = result[key].replace(old_str, str(new_root), 1)
		return result
	# @used-by :func:`agent_tools.project_rename._infer_daily_root()`
	# @used-by :meth:`ProjectRenamer.rename()`
	# @used-by :meth:`ProjectRenamer.update_projects_index()`
	# @used-by :meth:`test_df_harness_s11_wave2a_project_ext.DfHarnessS11Wave2aProjectExtTests.test_project_rename_classes()`
	@staticmethod
	def infer_daily_root(root: Path, daily_root: Path | None) -> Path | None:
		if None is not daily_root:
			r: Path | None = Path(daily_root).resolve()
		elif 4 <= len(root.parents) and all((root.parents[i].name.isascii() and root.parents[i].name.isdigit() for i in (2, 1, 0))):
			r = root.parents[3].resolve()
		else:
			r = None
		return r
	# @used-by :func:`agent_tools.project_rename.maybe_promote_project_domain()`
	# @used-by :meth:`ProjectRenamer.apply_domain_promotion()`
	@classmethod
	def maybe_promote_domain(cls, project_root: str | Path, analysis_value: dict, *, daily_root: Path | None=None, register_native: bool | None=None, launcher_root: Path | None=None, rename_fn=None) -> dict:
		root = Path(project_root).resolve()
		pj_path = project_paths(root, exact_root=True).project_json
		if not pj_path.is_file():
			r = {'renamed': False, 'reason': 'not_upwork_project', 'project_dir': str(root)}
		else:
			pj = json.loads(pj_path.read_text(encoding='utf-8-sig'))
			domain, basis_id = cls.resolve_promotable_target_domain(analysis_value)
			cur_label = root.name.split(' - ', 1)[-1]
			if pj.get('domain_drift_exempt'):
				r = {'renamed': False, 'reason': 'domain_drift_exempt', 'project_dir': str(root)}
			elif None is domain:
				r = {'renamed': False, 'reason': 'no_high_confidence_target_domain', 'project_dir': str(root)}
			elif cur_label.casefold() == domain.casefold():
				r = {'renamed': False, 'reason': 'already_matches_domain', 'domain': domain, 'basis_id': basis_id, 'project_dir': str(root)}
			else:
				res = cls(root, domain=domain, daily_root=daily_root, register_native=register_native, launcher_root=launcher_root).rename() if None is rename_fn else rename_fn(root, domain=domain, daily_root=daily_root, register_native=register_native, launcher_root=launcher_root)
				r = {**res, 'basis_id': basis_id}
		return r
	# @used-by :func:`agent_tools.intake._restore()`
	# @used-by :func:`agent_tools.intake.commit_capture()`
	# @used-by :func:`agent_tools.project_rename.rename_project()`
	# @used-by :func:`agent_tools.storage.create_bytes()`
	# @used-by :meth:`Df.Harness.Project.Intake.CaptureCommitter.CaptureCommitter.__init__()`
	# @used-by :meth:`Df.Harness.Project.Intake.CaptureCommitter.CaptureCommitter.restore()`
	# @used-by :meth:`ProjectRenamer.__do_dir_rename()`
	# @used-by :meth:`ProjectRenamer.__rollback()`
	# @used-by :meth:`test_df_harness_s11_wave2a_project_ext.DfHarnessS11Wave2aProjectExtTests.test_project_rename_classes()`
	# @used-by :meth:`test_df_harness_s11_wave2a_project_ext.DfHarnessS11Wave2aProjectExtTests.test_z_project_rename_full_coverage()`
	# @used-by :meth:`test_intake.IntakeTests.test_concurrent_replacement_during_retirement_keeps_both_versions()`
	# @used-by :meth:`test_native_profiles.NativeProfileTests.renamed_article()`
	# @used-by :meth:`test_native_profiles.NativeProfileTests.test_obsolete_skill_under_linked_parent_is_preserved()`
	# @used-by :meth:`test_native_profiles.NativeProfileTests.test_removed_skill_retires_alias_without_deleting_canonical_directory()`
	def rename(self) -> dict:
		old_root, new_root, new_label, new_kind, pj_old = self.__validate_inputs()
		eff_launcher = PostRenameVerifier.infer_launcher_root(old_root, self.infer_daily_root(old_root, self.__daily_root), self.__launcher_root)
		pre_snap = PostRenameVerifier.capture_pre_snapshot(old_root) if None is self.__pre_snap_fn else self.__pre_snap_fn(old_root)
		same_dir, backups, state_moves = (new_root == old_root, [], [])
		moved_cwd = None if same_dir else self.__rename_dir_safe(old_root, new_root)
		try:
			idx_file, reg_info, post_ver = self.__apply_mutations(old_root, new_root, new_label, new_kind, pj_old, eff_launcher, pre_snap, backups, state_moves)
		except Exception:
			self.__rollback(old_root, new_root, same_dir, moved_cwd, backups, state_moves)
			raise
		if not post_ver['valid']:
			self.__rollback(old_root, new_root, same_dir, moved_cwd, backups, state_moves)
			r = {'valid': False, 'renamed': False, 'rolled_back': True, 'old_project_dir': str(old_root), 'project_dir': str(old_root), 'job_id': pj_old['job_id'], 'label': pj_old.get('label'), 'launcher_root': str(eff_launcher) if None is not eff_launcher else None, 'post_verification': post_ver, 'errors': post_ver['errors']}
		else:
			if None is not moved_cwd and new_root.is_dir():
				os.chdir(new_root)
			r = {'valid': True, 'renamed': not same_dir, 'old_project_dir': str(old_root), 'project_dir': str(new_root), 'job_id': pj_old['job_id'], 'label': new_label, 'label_kind': new_kind, 'launcher_root': str(eff_launcher) if None is not eff_launcher else None, 'projects_index': idx_file, 'registration': reg_info, 'post_verification': post_ver}
		return r
	# @used-by :func:`agent_tools.project_rename.resolve_promotable_target_domain()`
	# @used-by :meth:`Df.Harness.Project.DriftAuditor.DriftAuditor.audit()`
	# @used-by :meth:`ProjectRenamer.maybe_promote_domain()`
	# @used-by :meth:`test_df_harness_s11_wave2a_project_ext.DfHarnessS11Wave2aProjectExtTests.test_project_rename_classes()`
	@staticmethod
	def resolve_promotable_target_domain(analysis_value: dict, *, min_probability: int=75) -> tuple[str | None, str | None]:
		r: tuple[str | None, str | None] = (None, None)
		if isinstance(analysis_value, dict):
			identities = {c['id']: c for c in (analysis_value.get('identity') or ()) if isinstance(c, dict) and isinstance(c.get('id'), str)}
			hits: dict[str, str] = {}
			for site in analysis_value.get('websites') or ():
				if isinstance(site, dict) and 'target' == site.get('role'):
					host, bid = (DomainNormalizer(site.get('url')).normalize(), site.get('basis_id'))
					if host and isinstance(bid, str) and bid in identities:
						hits.setdefault(host, bid)
			if 1 == len(hits):
				host, bid = next(iter(hits.items()))
				claim = identities[bid]
				score = claim.get('probability_percent')
				if 'verified' == claim.get('verification_status') or (isinstance(score, int) and (not isinstance(score, bool)) and min_probability <= score):
					r = (host, bid)
		return r
	# @used-by :func:`agent_tools.project_rename._update_projects_index()`
	# @used-by :meth:`ProjectRenamer.__apply_mutations()`
	@classmethod
	def update_projects_index(cls, old_root: Path, new_root: Path, job_id: str, daily_root: Path | None, backups: list) -> str | None:
		daily_default = (Path(settings()['workspace_root']).resolve() / settings()['daily_root']).resolve()
		daily = cls.infer_daily_root(new_root, daily_root)
		r = None
		if None is not daily and new_root.is_relative_to(daily):
			use_central = daily == daily_default and (not (daily / '\ua616/data/projects.json').exists())
			state_dir = store_path('upwork_projects_dir') if use_central else daily / '\ua616/data'
			with locked(state_dir / 'projects.lock'):
				index_file = state_dir / 'projects.json'
				raw = index_file.read_bytes() if index_file.is_file() else None
				backups.append((index_file, raw))
				index = json.loads(raw.decode('utf-8')) if None is not raw else {}
				index[job_id] = new_root.relative_to(daily).as_posix()
				replace_bytes(index_file, (json.dumps(index, ensure_ascii=False, indent=2) + '\n').encode('utf-8'))
				r = str(index_file)
		return r
