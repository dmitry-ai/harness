# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from agent_tools import journal
from agent_tools.journal_integrity import journal_validation_errors
from agent_tools.path_registry import project_paths
from Df.Harness.Project.Rename.RenameLineage import RenameLineage
import json
from pathlib import Path
# 2026-11-26 "Move analysis workflow classes into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/380
class PostRenameVerifier:
	# @used-by :func:`agent_tools.project_rename_verify.verify_post_rename()`
	# @used-by :meth:`Df.Harness.Project.Rename.ProjectRenamer.ProjectRenamer.__apply_mutations()`
	def __init__(self, old_root: Path, new_root: Path, pre: dict, *, launcher_root: Path | None=None, review_auth_fn=None, stage_statuses_fn=None) -> None:
		self.__old_root, self.__new_root, self.__pre = (old_root, new_root, pre)
		self.__launcher_root, self.__review_auth_fn, self.__stage_statuses_fn = (launcher_root, review_auth_fn, stage_statuses_fn)
	# @used-by :meth:`PostRenameVerifier.capture_pre_snapshot()`
	# @used-by :meth:`PostRenameVerifier.verify()`
	@staticmethod
	def __check_config_status(root: Path) -> tuple[bool, list]:
		from Df.Harness.Upwork.ConfigurationChecker import ConfigurationChecker
		try:
			res = ConfigurationChecker(root).check()
			r = (bool(res.get('valid')), list(res.get('issues') or ()))
		except (OSError, ValueError) as exc:
			r = (False, [{'message': str(exc)}])
		return r
	# @used-by :meth:`PostRenameVerifier.__verify_journal_regression()`
	# @used-by :meth:`PostRenameVerifier.capture_pre_snapshot()`
	@staticmethod
	def __collect_journal_errors(root: Path) -> list[str]:
		jdir = journal.resolve_journal_dir(root)
		r: list[str] = []
		if jdir.is_dir():
			steps = sorted(journal.get_existing_step_ids(jdir))
			for step in steps:
				r.extend(journal.step_errors(jdir, step))
			if steps:
				r.extend(journal_validation_errors(jdir, project_root=root, strict_sequence=True))
		return r
	# @used-by :meth:`PostRenameVerifier.verify()`
	@staticmethod
	def __launcher_stale_files(launcher_root: Path | None, old_root: Path, new_root: Path) -> list[str]:
		r: list[str] = []
		if None is not launcher_root and old_root != new_root:
			turns_dir = project_paths(Path(launcher_root).resolve(), exact_root=True).turns_dir
			needles = [old_s.casefold() for old_s, _ in RenameLineage.path_pairs(old_root, new_root, None, None)]
			if turns_dir.is_dir():
				for sf in sorted(turns_dir.glob('*.json')):
					try:
						blob = json.dumps(json.loads(sf.read_text(encoding='utf-8-sig')), ensure_ascii=False).casefold()
					except (OSError, ValueError):
						continue
					if any((n in blob for n in needles)):
						r.append(sf.name)
		return r
	# @used-by :meth:`PostRenameVerifier.capture_pre_snapshot()`
	# @used-by :meth:`PostRenameVerifier.verify()`
	@staticmethod
	def __probe_review_auth(root: Path, wf_state: dict, review_auth_fn=None) -> tuple[bool, str | None]:
		if not wf_state.get('reviews'):
			r: tuple[bool, str | None] = (True, None)
		else:
			from Df.Harness.Review.ReviewAuthorizer import ReviewAuthorizer
			try:
				if None is review_auth_fn:
					ReviewAuthorizer(root, wf_state).authorize()
				else:
					review_auth_fn(root, wf_state)
				r = (True, None)
			except (OSError, ValueError) as exc:
				r = (False, str(exc))
		return r
	# @used-by :meth:`PostRenameVerifier.capture_pre_snapshot()`
	# @used-by :meth:`PostRenameVerifier.verify()`
	@staticmethod
	def __probe_workflow(root: Path, stage_statuses_fn=None) -> tuple[dict | None, dict[str, str]]:
		wf_path = project_paths(root, exact_root=True).workflow_json
		if not wf_path.is_file():
			r: tuple[dict | None, dict[str, str]] = (None, {})
		else:
			from Df.Harness.Workflow.StageEngine import StageEngine
			eng = StageEngine(root)
			wf_state = eng.load()
			stages = eng.stage_statuses(wf_state) if None is stage_statuses_fn else stage_statuses_fn(root, wf_state)
			r = (wf_state, stages)
		return r
	# @used-by :meth:`PostRenameVerifier.verify()`
	@classmethod
	def __verify_journal_regression(cls, old_root: Path, new_root: Path, pre_errors: list[str], errors: list[str]) -> list[str]:
		post_j = cls.__collect_journal_errors(new_root)
		pairs = RenameLineage.path_pairs(old_root, new_root, None, None)
		norm_pre = set(pre_errors)
		for err in pre_errors:
			mapped = err
			for old_s, new_s in pairs:
				mapped = mapped.replace(old_s, new_s)
			norm_pre.add(mapped)
		for err in post_j:
			if err not in norm_pre:
				errors.append(f'validate_step regression after rename: {err}')
		return post_j
	# @used-by :func:`agent_tools.project_rename_verify.capture_pre_rename_snapshot()`
	# @used-by :meth:`Df.Harness.Project.Rename.ProjectRenamer.ProjectRenamer.rename()`
	@classmethod
	def capture_pre_snapshot(cls, old_root: Path, *, review_auth_fn=None, stage_statuses_fn=None) -> dict:
		wf_state, stages = cls.__probe_workflow(old_root, stage_statuses_fn)
		has_reviews = bool(wf_state and wf_state.get('reviews'))
		rev_ok, _ = cls.__probe_review_auth(old_root, wf_state, review_auth_fn) if has_reviews else (True, None)
		cfg_ok, _ = cls.__check_config_status(old_root)
		return {'workflow_stages': stages, 'has_reviews': has_reviews, 'review_auth_ok': rev_ok, 'configure_valid': cfg_ok, 'journal_errors': cls.__collect_journal_errors(old_root)}
	# @used-by :func:`agent_tools.project_rename_verify.infer_launcher_root()`
	# @used-by :meth:`Df.Harness.Project.Rename.ProjectRenamer.ProjectRenamer.rename()`
	# @used-by :meth:`test_df_harness_s11_wave2a_project_ext.DfHarnessS11Wave2aProjectExtTests.test_project_rename_classes()`
	@staticmethod
	def infer_launcher_root(old_root: Path, daily_root: Path | None, launcher_root: Path | None) -> Path | None:
		if None is not launcher_root:
			r: Path | None = Path(launcher_root).resolve()
		elif None is not daily_root:
			cand = (Path(daily_root).resolve().parent / 'init').resolve()
			r = cand if (cand / '\ua616/data/turns').is_dir() else None
		else:
			r = None
		return r
	# @used-by :func:`agent_tools.project_rename_verify.verify_post_rename()`
	# @used-by :meth:`Df.Harness.Project.Rename.ProjectRenamer.ProjectRenamer.__apply_mutations()`
	def verify(self) -> dict:
		errors: list[str] = []
		post_wf, post_stages = self.__probe_workflow(self.__new_root, self.__stage_statuses_fn)
		for stage, prev in (self.__pre.get('workflow_stages') or {}).items():
			if 'complete' == prev and 'complete' != post_stages.get(stage):
				errors.append(f'workflow stage regression: {stage} degraded from complete to {post_stages.get(stage)}')
		rev_ok = True
		if self.__pre.get('has_reviews') and self.__pre.get('review_auth_ok') and None is not post_wf:
			rev_ok, rev_err = self.__probe_review_auth(self.__new_root, post_wf, self.__review_auth_fn)
			if not rev_ok:
				errors.append(f'review.authorize failed after rename: {rev_err}')
		cfg_ok, cfg_issues = self.__check_config_status(self.__new_root)
		if self.__pre.get('configure_valid') and (not cfg_ok):
			errors.append(f'configure --check regressed after rename: {cfg_issues[:3]}')
		post_j = self.__verify_journal_regression(self.__old_root, self.__new_root, list(self.__pre.get('journal_errors') or ()), errors)
		stale_l = self.__launcher_stale_files(self.__launcher_root, self.__old_root, self.__new_root)
		if stale_l:
			errors.append(f"launcher handoffs retain stale project path: {', '.join(stale_l[:5])}")
		return {'valid': not errors, 'errors': errors, 'workflow_stages': post_stages, 'review_authorized': rev_ok, 'configure_valid': cfg_ok, 'journal_errors': post_j, 'stale_launcher_files': stale_l}
