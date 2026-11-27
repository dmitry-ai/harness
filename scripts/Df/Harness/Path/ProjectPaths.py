# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from copy import deepcopy
from pathlib import Path
from typing import Any
from Df.Harness.Path.SlotResolver import SlotResolver
from Df.Harness.lib.path_discovery import dfh_refresh_known_overlay_links
from Df.Harness.lib.path_schema import dfh_canonicalize_root_dir, dfh_discover_overlay_file, dfh_infer_default_profile, dfh_inspect_journal_dir_on_disk, dfh_validate_overlay
from Df.Harness.lib.path_state import DISCOVERY_STATE, OVERLAY_REVERSE_MAP, SIMILAR_REVERSE_MAP
from Df.Harness.lib.path_template import URI_SCHEME_RE, dfh_escape_template_literal, dfh_expand_structure, dfh_expand_template, dfh_normalize_path_str, dfh_path_key
import glob
import json
# 2026-11-26 "Move turn lifecycle subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/383
class ProjectPaths:
	# @used-by :func:`Df.Harness.lib.path_discovery._scan_overlay_links()`
	# @used-by :func:`Df.Harness.lib.path_resolve._build_or_fetch_project_paths()`
	# @used-by :meth:`Df.Harness.Path.PathReporter.PathReporter.__discover_overlays()`
	# @used-by :meth:`test_df_harness_s11_wave2d.DfHarnessS11Wave2DTests.test_path_subsystem_classes()`
	def __init__(self, root: str | Path, *, registry: Any=None, env: dict[str, str] | None=None, _register_links: bool=True) -> None:
		from Df.Harness.lib.path_resolve import dfh_load_registry
		self.registry = registry or dfh_load_registry(env=env)
		self.root = dfh_canonicalize_root_dir(root, self.registry)
		prof_spec = self.__init_overlay_and_profile()
		raw_paths, merged_vars = self.__init_raw_paths_and_vars(prof_spec)
		self.__variables = merged_vars
		self.paths_str = SlotResolver(self.root, raw_paths, merged_vars, self.registry.env).run()
		self.__init_tools_and_repos(prof_spec, merged_vars, _register_links)
		self.__init_journal(prof_spec)
		self.deliverable_segments = tuple((self.overlay['deliverable_segments'] if self.overlay and self.overlay['deliverable_segments'] else ('/letters/', '/result/', '/defects/', '/articles/', '/\u2c3f/\u227b/\u2655/', '/artifacts/\u227b/deliverables/')))
		self.source_dirs = tuple((Path(self.__resolve_rel_to_root(item)) for item in (self.overlay['source_dirs'] if self.overlay else ())))
		if _register_links and (self.has_overlay or self.direct_similar_projects):
			self.register_reverse_links()
	# @used-by :meth:`ProjectPaths.__init_raw_paths_and_vars()`
	def __apply_v2_legacy_dir_names(self, merged_vars: dict[str, str]) -> None:
		ov_vars = self.overlay['variables'] if self.overlay else {}
		if 2 == self.fs_version and 'ARTIFACTS_DIR_NAME' not in ov_vars and 'ARTIFACTS_DIR' not in ov_vars:
			cur_art = self.registry.resolved_variables.get('ARTIFACTS_DIR_NAME', '\u2c0f')
			if not (self.root / cur_art).exists() and (self.root / 'Artifacts').is_dir():
				merged_vars['ARTIFACTS_DIR_NAME'] = 'Artifacts'
				art_out = self.registry.resolved_variables.get('ARTIFACTS_OUT_DIR_NAME', '\u227b')
				if 'DELIVERABLES_DIR_NAME' not in ov_vars and (self.root / 'Artifacts' / art_out / 'Deliverables').is_dir():
					merged_vars['DELIVERABLES_DIR_NAME'] = 'Deliverables'
				if 'INTERMEDIARY_DIR_NAME' not in ov_vars and (self.root / 'Artifacts' / art_out / 'Intermediary').is_dir():
					merged_vars['INTERMEDIARY_DIR_NAME'] = 'Intermediary'
	# @used-by unused
	def __getattr__(self, name: str) -> Any:
		if '_direct_similar_projects' == name:
			return self.direct_similar_projects
		raise AttributeError(f'{type(self).__name__!r} object has no attribute {name!r}')
	# @used-by :meth:`ProjectPaths.__init__()`
	def __init_journal(self, prof_spec: dict[str, Any]) -> None:
		ov_j_ver = self.overlay.get('journal_version') if self.overlay else None
		cfg_j_ver = ov_j_ver if None is not ov_j_ver else prof_spec['journal_version']
		j_eff = self.__resolve_effective_journal_dir()
		disk_j_ver, disk_j_pair = dfh_inspect_journal_dir_on_disk(j_eff, self.registry)
		self.journal_version = disk_j_ver if None is not disk_j_ver else cfg_j_ver
		eff_j_pair = disk_j_pair if None is not disk_j_pair else ((self.registry.resolved_variables.get('JOURNAL_OUT_DIR_NAME', '\u227b'), self.registry.resolved_variables.get('JOURNAL_IN_DIR_NAME', '\u227a')) if 2 <= self.journal_version else ('req', 'res'))
		if 'journal_req_dir' not in self.__explicit_overlay_paths:
			self.paths_str['journal_req_dir'] = dfh_normalize_path_str(f'{j_eff.as_posix()}/{eff_j_pair[0]}')
		if 'journal_res_dir' not in self.__explicit_overlay_paths:
			self.paths_str['journal_res_dir'] = dfh_normalize_path_str(f'{j_eff.as_posix()}/{eff_j_pair[1]}')
	# @used-by :meth:`ProjectPaths.__init__()`
	def __init_overlay_and_profile(self) -> dict[str, Any]:
		self.overlay_file = dfh_discover_overlay_file(self.root, self.registry)
		self.overlay = dfh_validate_overlay(json.loads(self.overlay_file.read_text(encoding='utf-8-sig')), self.overlay_file, self.registry) if None is not self.overlay_file else None
		self.has_overlay = None is not self.overlay
		self.tracked: bool | None = self.overlay.get('tracked') if self.overlay else None
		ov_fs_ver = self.overlay.get('fs_version') if self.overlay else None
		self.profile = (self.overlay.get('profile') if self.overlay else None) or dfh_infer_default_profile(self.root, self.overlay_file, self.registry, explicit_fs_version=ov_fs_ver)
		if self.profile not in self.registry.resolved_profiles:
			raise ValueError(f'Unknown project path profile: {self.profile!r}')
		prof_spec = self.registry.resolved_profiles[self.profile]
		self.fs_version = ov_fs_ver if None is not ov_fs_ver else prof_spec['fs_version']
		return prof_spec
	# @used-by :meth:`ProjectPaths.__init__()`
	def __init_raw_paths_and_vars(self, prof_spec: dict[str, Any]) -> tuple[dict[str, str], dict[str, str]]:
		ws_ovr = self.registry.workspace_overrides.get(dfh_path_key(self.root))
		raw_paths = dict(prof_spec['paths'])
		if ws_ovr:
			for k in ('data_dir', 'cleanup_log_dir', 'browser_locks_dir'):
				if k in ws_ovr and isinstance(ws_ovr[k], str):
					raw_paths[k] = ws_ovr[k]
		self.__explicit_overlay_paths: set[str] = set()
		if self.overlay:
			raw_paths.update(self.overlay['paths'])
			self.__explicit_overlay_paths = set(self.overlay['paths'])
		merged_vars = {**self.registry.raw_variables, **prof_spec['variables'], **(self.overlay['variables'] if self.overlay else {})}
		self.__apply_v2_legacy_dir_names(merged_vars)
		merged_vars['PROJECT_ROOT'] = dfh_escape_template_literal(self.root.as_posix())
		return (raw_paths, merged_vars)
	# @used-by :meth:`ProjectPaths.__init_tools_and_repos()`
	def __init_similar_projects(self, prof_spec: dict[str, Any], register_links: bool) -> None:
		raw_sim = self.overlay['similar_projects'] if self.overlay and self.overlay['similar_projects'] else prof_spec['similar_projects']
		direct_sim: list[Path] = []
		seen_sim: set[str] = {dfh_path_key(self.root)}
		for item in raw_sim:
			cand = dfh_canonicalize_root_dir(self.__resolve_rel_to_root(item), self.registry)
			if dfh_path_key(cand) not in seen_sim:
				seen_sim.add(dfh_path_key(cand))
				direct_sim.append(cand)
		self_key = dfh_path_key(self.root)
		for grp in self.registry.similar_project_groups:
			mem_roots = [dfh_canonicalize_root_dir(mem['project'], self.registry) for mem in grp['members']]
			if any((dfh_path_key(mr) == self_key for mr in mem_roots)):
				for mr in mem_roots:
					if dfh_path_key(mr) not in seen_sim:
						seen_sim.add(dfh_path_key(mr))
						direct_sim.append(mr)
		self.direct_similar_projects = tuple(direct_sim)
		self.__include_reverse_similar = register_links
	# @used-by :meth:`ProjectPaths.__init__()`
	def __init_tools_and_repos(self, prof_spec: dict[str, Any], merged_vars: dict[str, str], register_links: bool) -> None:
		merged_tools = deepcopy(self.registry.tools)
		merged_tools.update(dfh_expand_structure(prof_spec['tools'], merged_vars, env=self.registry.env))
		if self.overlay and self.overlay['tools']:
			merged_tools.update(dfh_expand_structure(self.overlay['tools'], merged_vars, env=self.registry.env))
		self.tools = merged_tools
		raw_code = self.overlay['code_repos'] if self.overlay and self.overlay['code_repos'] else prof_spec['code_repos']
		self.code_repos = tuple((Path(self.__resolve_rel_to_root(item)).resolve() for item in raw_code))
		raw_aux = {**prof_spec['auxiliary_repos'], **(self.overlay['auxiliary_repos'] if self.overlay else {})}
		self.auxiliary_repos = {k: Path(self.__resolve_rel_to_root(v)).resolve() for k, v in raw_aux.items()}
		raw_links = self.overlay['linked_roots'] if self.overlay and self.overlay['linked_roots'] else prof_spec['linked_roots']
		self.linked_roots = tuple((Path(self.__resolve_rel_to_root(item)).resolve() for item in raw_links))
		self.__init_similar_projects(prof_spec, register_links)
		self.journal_legacy_fallbacks = tuple((Path(self.__resolve_rel_to_root(item)) for item in prof_spec['journal_legacy_fallbacks']))
	# @used-by :meth:`ProjectPaths.to_dict()`
	@staticmethod
	def __path_exists(p_str: str) -> bool:
		return any((Path(m).exists() for m in glob.glob(p_str, recursive=True))) if '*' in p_str or '?' in p_str else Path(p_str).exists()
	# @used-by :meth:`ProjectPaths.__init_journal()`
	def __resolve_effective_journal_dir(self) -> Path:
		j_root, j_cur = (Path(self.paths_str['journal_root_dir']), self.journal_dir)
		if self.has_explicit_path('journal_dir') or self.journal_glob:
			if not j_cur.is_dir() and j_cur.parent == j_root and j_cur.name in ('1 - Analysis', '1 - \u0410\u043d\u0430\u043b\u0438\u0437') and (None is not dfh_inspect_journal_dir_on_disk(j_root, self.registry)[0]):
				self.paths_str['journal_dir'] = j_root.as_posix()
				r = j_root
			else:
				r = j_cur
		elif None is not dfh_inspect_journal_dir_on_disk(j_root, self.registry)[0]:
			r = j_root
		else:
			fb_hit = next((fb for fb in self.journal_legacy_fallbacks if fb != j_root and fb.is_dir()), None)
			if None is not fb_hit:
				self.paths_str['journal_dir'] = dfh_normalize_path_str(fb_hit.as_posix())
				r = fb_hit
			else:
				r = j_cur
		return r
	# @used-by :meth:`ProjectPaths.__init__()`
	# @used-by :meth:`ProjectPaths.__init_similar_projects()`
	# @used-by :meth:`ProjectPaths.__init_tools_and_repos()`
	# @used-by :meth:`ProjectPaths.expand()`
	def __resolve_rel_to_root(self, tpl: str) -> str:
		val = dfh_expand_template(tpl, self.__variables, env=self.registry.env, normalize=True)
		if not Path(val).is_absolute() and (not URI_SCHEME_RE.match(val)):
			val = dfh_normalize_path_str(f'{self.root.as_posix()}/{val}')
		return val
	# @used-by :func:`Df.Harness.lib.completion_checks.dfh_is_client_deliverable_path()`
	# @used-by :func:`Df.Harness.lib.path_state._fast_sig()`
	# @used-by :meth:`Df.Harness.Issue.EvidenceWorkspace.EvidenceWorkspace.issue_target_for_path()`
	# @used-by :meth:`Df.Harness.Issue.EvidenceWorkspace.EvidenceWorkspace.meta_dir_for_project_root()`
	# @used-by :meth:`Df.Harness.Review.MerkleCacheUpdater.MerkleCacheUpdater.update()`
	# @used-by :meth:`test_path_registry.PathRegistryTests.test_live_five_projects_integration_across_harness_subsystems_and_cli()`
	# @used-by :meth:`test_path_registry.PathRegistryTests.test_project_overlay_dag_cascades_and_remains_isolated_per_project()`
	# @used-by :meth:`test_path_registry_perf.PathRegistryPerformanceTests.test_project_paths_fast_cache_hits_and_invalidates_on_fs_mutations()`
	@property
	def agent_dir(self) -> Path:
		return Path(self.paths_str['agent_dir'])
	# @used-by :func:`Df.Harness.lib.completion_checks._collect_base_instruction_sources()`
	# @used-by :func:`Df.Harness.lib.config_codex.dfh_configure_codex_project()`
	# @used-by :func:`Df.Harness.lib.config_codex.dfh_project_rule_paths()`
	# @used-by :meth:`Df.Harness.Config.NativeBuilder.NativeBuilder.__prepare_codex_outputs()`
	# @used-by :meth:`Df.Harness.Upwork.ConfigurationChecker.ConfigurationChecker.check()`
	# @used-by :meth:`Df.Harness.Upwork.ProjectConfigurator.ProjectConfigurator.__prepare_agents_dirs()`
	# @used-by :meth:`Df.Harness.Upwork.ProjectConfigurator.ProjectConfigurator.__sync_context_config()`
	# @used-by :meth:`agent_tools.text_diagnostics.SourceDiagnosticsScanner._scan_ancestry_scope()`
	@property
	def agents_config_dir(self) -> Path:
		return Path(self.paths_str['agents_config_dir'])
	# @used-by :func:`Df.Harness.lib.config_codex._run_codex_project_publish()`
	# @used-by :func:`Df.Harness.lib.config_codex.dfh_configure_codex_project()`
	# @used-by :func:`Df.Harness.lib.config_codex.dfh_native_config()`
	# @used-by :meth:`Df.Harness.Config.NativeBuilder.NativeBuilder.__prepare_codex_outputs()`
	# @used-by :meth:`Df.Harness.Config.ProjectionPublisher.ProjectionPublisher.__finalize_codex_receipt()`
	# @used-by :meth:`agent_tools.text_diagnostics.SourceDiagnosticsScanner._scan_ancestry_scope()`
	@property
	def codex_config_toml(self) -> Path:
		return Path(self.paths_str['codex_config_toml'])
	# @used-by :meth:`Df.Harness.Upwork.ProjectConfigurator.ProjectConfigurator.__sync_context_config()`
	@property
	def context_config(self) -> Path:
		return Path(self.paths_str['context_config'])
	# @used-by :meth:`Df.Harness.Project.Context.ContextGenerator.ContextGenerator.generate()`
	# @used-by :meth:`Df.Harness.Project.Context.LetterDiscoverer.LetterDiscoverer.default_config()`
	# @used-by :meth:`Df.Harness.Upwork.ProjectConfigurator.ProjectConfigurator.default_context_config()`
	# @used-by :meth:`test_path_registry.PathRegistryTests.test_v2_filesystem_auto_detection_journals_context_provenance_and_migration()`
	@property
	def context_output(self) -> Path:
		return Path(self.paths_str['context_output'])
	# @used-by :func:`Df.Harness.lib.blocked_report_ops.dfh_blocked_report_issues()`
	# @used-by :meth:`Df.Harness.Completion.BudgetEvaluator.BudgetEvaluator.run()`
	# @used-by :meth:`test_df_harness_s11_wave2d_completion_cov.DfHarnessS11Wave2dCompletionCovTests.test_blocked_report_and_workflow_sync_ops()`
	@property
	def continuation_md(self) -> Path:
		return Path(self.paths_str['continuation_md'])
	# @used-by :func:`Df.Harness.lib.blocked_report_ops._check_text_workflow_gate()`
	# @used-by :func:`Df.Harness.lib.completion_core.dfh_turns_folder()`
	# @used-by :func:`Df.Harness.lib.journal.dfh_turns_dir()`
	# @used-by :func:`Df.Harness.lib.journal_upgrade.dfh_upgrade_journal()`
	# @used-by :func:`Df.Harness.lib.path_resolve.dfh_resolve_journal_data_dir()`
	# @used-by :func:`Df.Harness.lib.shadow_command.dfh_persist_shadow_replay_receipt()`
	# @used-by :func:`Df.Harness.lib.storage.dfh_data_dir_for()`
	# @used-by :func:`agent_tools.research.collect()`
	# @used-by :func:`agent_tools.research.observed_use()`
	# @used-by :func:`agent_tools.text_browser._endpoint_lock()`
	# @used-by :func:`agent_tools.text_claims.save_registry()`
	# @used-by :func:`agent_tools.text_workflow._folder()`
	# @used-by :func:`agent_tools.worktree_flow.worktree_land()`
	# @used-by :meth:`Df.Harness.Analysis.Merger.Merger.__load_base()`
	# @used-by :meth:`Df.Harness.Analysis.Merger.Merger.save()`
	# @used-by :meth:`Df.Harness.Analysis.OwnedPublisher.OwnedPublisher.publish()`
	# @used-by :meth:`Df.Harness.Analysis.RedFlagSyncer.RedFlagSyncer.sync()`
	# @used-by :meth:`Df.Harness.Analysis.Saver.Saver.__commit_locked()`
	# @used-by :meth:`Df.Harness.Arch.ReviewStore.ReviewStore.__arch_dir()`
	# @used-by :meth:`Df.Harness.Completion.BudgetEvaluator.BudgetEvaluator.run()`
	# @used-by :meth:`Df.Harness.Git.LandingLease.LandingLease.__init__()`
	# @used-by :meth:`Df.Harness.Git.PolyglotTestRunner.PolyglotTestRunner.__sandbox_root()`
	# @used-by :meth:`Df.Harness.Project.CardSyncer.CardSyncer.sync()`
	# @used-by :meth:`Df.Harness.Project.ExtraSourceBuilder.ExtraSourceBuilder.build()`
	# @used-by :meth:`Df.Harness.Project.ExtraSourceBuilder.ExtraSourceBuilder.load_media_descriptions()`
	# @used-by :meth:`Df.Harness.Project.Intake.CaptureCommitter.CaptureCommitter.__run_commit()`
	# @used-by :meth:`Df.Harness.Project.RegistrationAttemptStarter.RegistrationAttemptStarter.begin()`
	# @used-by :meth:`Df.Harness.Project.RegistrationStore.RegistrationStore.save()`
	# @used-by :meth:`Df.Harness.Project.Rename.StateRewriter.StateRewriter.migrate_journal_state()`
	# @used-by :meth:`Df.Harness.Project.Rename.StateRewriter.StateRewriter.refresh_workflow_file_hash()`
	# @used-by :meth:`Df.Harness.Project.Rename.StateRewriter.StateRewriter.rewrite()`
	# @used-by :meth:`Df.Harness.TestRunner.WorkerSemaphore.WorkerSemaphore.default_slots_dir()`
	# @used-by :meth:`Df.Harness.Upwork.ProjectConfigurator.ProjectConfigurator.__sync_context_config()`
	# @used-by :meth:`agent_tools.text_workflow.TextIntegrityVerifier.claim_snapshot()`
	# @used-by :meth:`test_df_harness_s11_wave2d.DfHarnessS11Wave2DTests.test_path_subsystem_classes()`
	# @used-by :meth:`test_path_registry.PathRegistryTests.test_project_overlay_dag_cascades_and_remains_isolated_per_project()`
	@property
	def data_dir(self) -> Path:
		return Path(self.paths_str['data_dir'])
	# @used-by :func:`Df.Harness.lib.cli_domain_ops.dfh_execute_collect()`
	# @used-by :func:`Df.Harness.lib.completion_checks.dfh_factual_kb_note_issues()`
	# @used-by :func:`Df.Harness.lib.completion_compaction.dfh_compaction_status()`
	# @used-by :func:`Df.Harness.lib.trace_review.dfh_persist_review_proof()`
	# @used-by :func:`agent_tools.research.collect()`
	# @used-by :func:`agent_tools.research.evidence_query()`
	# @used-by :func:`agent_tools.research.extract_file()`
	# @used-by :func:`agent_tools.text_browser.save_cdp_identity()`
	# @used-by :func:`test_df_harness_s11_wave2a_workflow._seed_project()`
	# @used-by :meth:`Df.Harness.Analysis.Claim.ManifestPrimaryVerifier.ManifestPrimaryVerifier.__load_state()`
	# @used-by :meth:`Df.Harness.Analysis.Claim.ManifestPrimaryVerifier.ManifestPrimaryVerifier.verify()`
	# @used-by :meth:`Df.Harness.Experiment.RunLoader.RunLoader.__load_raw()`
	# @used-by :meth:`Df.Harness.Experiment.RunRecorder.RunRecorder.__write_run()`
	# @used-by :meth:`Df.Harness.Grounding.EvidenceBundleIngestor.EvidenceBundleIngestor.__evidence_dirs()`
	# @used-by :meth:`Df.Harness.Issue.EvidenceWorkspace.EvidenceWorkspace.__target_for_project_root()`
	# @used-by :meth:`Df.Harness.Issue.EvidenceWorkspace.EvidenceWorkspace.evidence_issue_files()`
	# @used-by :meth:`Df.Harness.Issue.EvidenceWorkspace.EvidenceWorkspace.issue_target_for_path()`
	# @used-by :meth:`Df.Harness.Meta.MetricsSummarizer.MetricsSummarizer.__save_executor_metadata()`
	# @used-by :meth:`Df.Harness.Project.Context.LetterDiscoverer.LetterDiscoverer.default_config()`
	# @used-by :meth:`Df.Harness.Project.Intake.CaptureCommitter.CaptureCommitter.__run_locked()`
	# @used-by :meth:`Df.Harness.Project.Intake.IntakeIndexer.IntakeIndexer.rebuild()`
	# @used-by :meth:`Df.Harness.Project.Intake.ReceiptBuilder.ReceiptBuilder.build()`
	# @used-by :meth:`Df.Harness.Project.Intake.ReceiptValidator.ReceiptValidator.validate()`
	# @used-by :meth:`Df.Harness.Project.Intake.ReceiptValidator.ReceiptValidator.verify_snapshot()`
	# @used-by :meth:`Df.Harness.Project.KbPopulator.KbPopulator.populate()`
	# @used-by :meth:`Df.Harness.Review.DispositionRecorder.DispositionRecorder.record()`
	# @used-by :meth:`Df.Harness.Review.PackagePreparer.PackagePreparer.__write_candidate()`
	# @used-by :meth:`Df.Harness.Review.PackagePreparer.PackagePreparer.prepare()`
	# @used-by :meth:`Df.Harness.Review.VerdictPreparer.VerdictPreparer.__write_artifacts()`
	# @used-by :meth:`Df.Harness.Upwork.ProjectConfigurator.ProjectConfigurator.default_context_config()`
	# @used-by :meth:`Df.Harness.Workflow.HashCollector.HashCollector.evidence_paths()`
	# @used-by :meth:`Df.Harness.Workflow.HashCollector.HashCollector.kb_paths()`
	# @used-by :meth:`test_path_registry.PathRegistryTests.test_project_overlay_dag_cascades_and_remains_isolated_per_project()`
	@property
	def evidence_dir(self) -> Path:
		return Path(self.paths_str['evidence_dir'])
	# @used-by :meth:`Df.Harness.Meta.MetricsSummarizer.MetricsSummarizer.__save_executor_metadata()`
	# @used-by :meth:`Df.Harness.Meta.MetricsSummarizer.MetricsSummarizer.project_metrics()`
	# @used-by :meth:`test_df_harness_s11_wave2d_journal_path_cov.DfHarnessS11Wave2dJournalPathCovTests.test_paths_and_uri()`
	@property
	def executors_json(self) -> Path:
		return Path(self.paths_str['executors_json'])
	# @used-by :func:`Df.Harness.lib.journal_core.dfh_resolve_journal_dir()`
	# @used-by :func:`Df.Harness.lib.journal_upgrade.dfh_ensure_project_journal_upgraded()`
	# @used-by :meth:`Df.Harness.Path.PathReporter.PathReporter.__build_project_report()`
	# @used-by :meth:`test_df_harness_s11_wave2d_journal_path_cov.DfHarnessS11Wave2dJournalPathCovTests.test_paths_and_uri()`
	def expand(self, template: str) -> str:
		return self.__resolve_rel_to_root(template)
	# @used-by :func:`Df.Harness.lib.grounding.dfh_load_fact_ledger()`
	@property
	def facts_json(self) -> Path:
		return Path(self.paths_str['facts_json'])
	@property
	def grounding_cache_json(self) -> Path:
		return Path(self.paths_str['grounding_cache_json'])
	# @used-by :func:`Df.Harness.lib.completion_core.dfh_turns_folder()`
	# @used-by :func:`Df.Harness.lib.journal.dfh_turns_dir()`
	# @used-by :meth:`Df.Harness.Completion.BudgetEvaluator.BudgetEvaluator.run()`
	# @used-by :meth:`ProjectPaths.__resolve_effective_journal_dir()`
	# @used-by :meth:`ProjectPaths.journal_dir()`
	def has_explicit_path(self, name: str) -> bool:
		return name in self.__explicit_overlay_paths
	# @used-by :func:`agent_tools.research.collect()`
	# @used-by :meth:`Df.Harness.Analysis.ObservationResolver.ObservationResolver.__lookup_index()`
	@property
	def http_index_json(self) -> Path:
		return Path(self.paths_str['http_index_json'])
	# @used-by :func:`Df.Harness.lib.journal_core.dfh_canonicalize_journal_dir_identity()`
	# @used-by :func:`Df.Harness.lib.journal_core.dfh_journal_pair_names()`
	# @used-by :func:`Df.Harness.lib.journal_core.dfh_resolve_journal_dir()`
	# @used-by :func:`Df.Harness.lib.journal_integrity_ops.dfh_check_project_journal_problems()`
	# @used-by :func:`Df.Harness.lib.journal_upgrade.dfh_ensure_project_journal_upgraded()`
	# @used-by :func:`Df.Harness.lib.path_resolve._workspace_is_explicitly_tracked()`
	# @used-by :func:`Df.Harness.lib.path_state._fast_sig()`
	# @used-by :meth:`Df.Harness.Upwork.CliRunner.CliRunner.__cmd_journal_upgrade()`
	# @used-by :meth:`Df.Harness.Upwork.ProjectConfigurator.ProjectConfigurator.default_context_config()`
	# @used-by :meth:`Df.Harness.Upwork.ProjectInitializer.ProjectInitializer.__init_locked_state()`
	# @used-by :meth:`ProjectPaths.__resolve_effective_journal_dir()`
	# @used-by :meth:`ProjectPaths.to_dict()`
	# @used-by :meth:`test_path_registry.PathRegistryTests.test_project_overlay_dag_cascades_and_remains_isolated_per_project()`
	# @used-by :meth:`test_path_registry.PathRegistryTests.test_v1_journal_only_upgrade_preserves_v1_project_layout_and_historical_receipts()`
	@property
	def journal_dir(self) -> Path:
		matches = sorted((Path(m).resolve() for m in glob.glob(self.journal_glob, recursive=True) if Path(m).is_dir())) if (not self.has_explicit_path('journal_dir')) and self.journal_glob else []
		return matches[-1] if matches else Path(self.paths_str['journal_dir'])
	# @used-by :func:`Df.Harness.lib.journal_upgrade.dfh_ensure_project_journal_upgraded()`
	# @used-by :meth:`Df.Harness.Upwork.CliRunner.CliRunner.__cmd_journal_upgrade()`
	# @used-by :meth:`ProjectPaths.__resolve_effective_journal_dir()`
	# @used-by :meth:`ProjectPaths.journal_dir()`
	@property
	def journal_glob(self) -> str | None:
		return self.paths_str.get('journal_glob')
	# @used-by :func:`Df.Harness.lib.completion_checks.dfh_is_client_deliverable_path()`
	# @used-by :func:`Df.Harness.lib.journal_upgrade._sync_overlay_journal_slot()`
	# @used-by :func:`Df.Harness.lib.journal_upgrade.dfh_ensure_project_journal_upgraded()`
	# @used-by :func:`Df.Harness.lib.path_state._fast_sig()`
	# @used-by :meth:`Df.Harness.Upwork.CliRunner.CliRunner.__cmd_journal_upgrade()`
	@property
	def journal_root_dir(self) -> Path:
		return Path(self.paths_str['journal_root_dir'])
	# @used-by :func:`Df.Harness.lib.completion_checks.dfh_factual_kb_note_issues()`
	# @used-by :func:`agent_tools.evidence.source_reference()`
	# @used-by :func:`agent_tools.research.collect()`
	# @used-by :func:`agent_tools.research.compute_site_summary()`
	# @used-by :func:`agent_tools.research.evidence_query()`
	# @used-by :func:`agent_tools.research.extract_file()`
	# @used-by :func:`agent_tools.research.extract_observation()`
	# @used-by :func:`agent_tools.research.load_observation()`
	# @used-by :func:`agent_tools.text_browser.save_cdp_identity()`
	# @used-by :func:`agent_tools.text_claims.registry_path()`
	# @used-by :func:`agent_tools.text_sources._evaluate()`
	# @used-by :meth:`Df.Harness.Analysis.LocalSourceResolver.LocalSourceResolver.resolve()`
	# @used-by :meth:`Df.Harness.Analysis.Merger.Merger.__load_base()`
	# @used-by :meth:`Df.Harness.Analysis.Publisher.Publisher.__resolve_project_root()`
	# @used-by :meth:`Df.Harness.Analysis.RedFlagSyncer.RedFlagSyncer.sync()`
	# @used-by :meth:`Df.Harness.Analysis.Saver.Saver.__commit_locked()`
	# @used-by :meth:`Df.Harness.Completion.BudgetEvaluator.BudgetEvaluator.run()`
	# @used-by :meth:`Df.Harness.Experiment.ArtifactVerifier.ArtifactVerifier.verify()`
	# @used-by :meth:`Df.Harness.Experiment.ResultValidator.ResultValidator.__check_run()`
	# @used-by :meth:`Df.Harness.Experiment.RunLoader.RunLoader.__load_raw()`
	# @used-by :meth:`Df.Harness.Experiment.RunRecorder.RunRecorder.__write_run()`
	# @used-by :meth:`Df.Harness.Grounding.ResponseAuditor.ResponseAuditor.__check_kb_membership()`
	# @used-by :meth:`Df.Harness.Grounding.ResponseAuditor.ResponseAuditor.__collect_client_urls()`
	# @used-by :meth:`Df.Harness.Grounding.ResponseAuditor.ResponseAuditor.__collect_kb_urls()`
	# @used-by :meth:`Df.Harness.Project.AttachmentKbSyncer.AttachmentKbSyncer.sync()`
	# @used-by :meth:`Df.Harness.Project.Context.ContextAssembler.ContextAssembler.assemble()`
	# @used-by :meth:`Df.Harness.Project.Context.LetterDiscoverer.LetterDiscoverer.default_config()`
	# @used-by :meth:`Df.Harness.Project.ExtraSourceBuilder.ExtraSourceBuilder.__process_asset()`
	# @used-by :meth:`Df.Harness.Project.FinalizeDriftGuard.FinalizeDriftGuard.require()`
	# @used-by :meth:`Df.Harness.Project.Intake.CaptureCommitter.CaptureCommitter.__run_locked()`
	# @used-by :meth:`Df.Harness.Project.Intake.IntakeIndexer.IntakeIndexer.rebuild()`
	# @used-by :meth:`Df.Harness.Project.Intake.ReceiptValidator.ReceiptValidator.verify_snapshot()`
	# @used-by :meth:`Df.Harness.Project.KbPopulator.KbPopulator.__write_kb_pages()`
	# @used-by :meth:`Df.Harness.Project.KbPopulator.KbPopulator.populate()`
	# @used-by :meth:`Df.Harness.Project.WebsiteCardSyncer.WebsiteCardSyncer.__sync_selected()`
	# @used-by :meth:`Df.Harness.Review.MerkleCacheUpdater.MerkleCacheUpdater.__default_analysis()`
	# @used-by :meth:`Df.Harness.Review.PackageEnvelopeReader.PackageEnvelopeReader.load_analysis()`
	# @used-by :meth:`Df.Harness.Upwork.ProjectConfigurator.ProjectConfigurator.default_context_config()`
	# @used-by :meth:`Df.Harness.Upwork.ProjectInitializer.ProjectInitializer.__init_locked_state()`
	# @used-by :meth:`Df.Harness.Workflow.AnswerRecorder.AnswerRecorder.__check_red_flags()`
	# @used-by :meth:`Df.Harness.Workflow.HashCollector.HashCollector.kb_paths()`
	# @used-by :meth:`test_path_registry.PathRegistryTests.test_project_overlay_dag_cascades_and_remains_isolated_per_project()`
	@property
	def kb_dir(self) -> Path:
		return Path(self.paths_str['kb_dir'])
	# @used-by :meth:`Df.Harness.Grounding.ResponseAuditor.ResponseAuditor.__collect_client_urls()`
	# @used-by :meth:`Df.Harness.Grounding.ResponseAuditor.ResponseAuditor.__collect_kb_urls()`
	# @used-by :meth:`Df.Harness.Project.AttachmentKbSyncer.AttachmentKbSyncer.sync()`
	# @used-by :meth:`Df.Harness.Project.KbPopulator.KbPopulator.__write_kb_pages()`
	# @used-by :meth:`Df.Harness.Project.WebsiteCardSyncer.WebsiteCardSyncer.sync_initial()`
	# @used-by :meth:`Df.Harness.Upwork.ProjectConfigurator.ProjectConfigurator.default_context_config()`
	# @used-by :meth:`Df.Harness.Upwork.ProjectInitializer.ProjectInitializer.__init_locked_state()`
	# @used-by :meth:`Df.Harness.Workflow.HashCollector.HashCollector.evidence_paths()`
	# @used-by :meth:`test_path_registry.PathRegistryTests.test_v1_journal_only_upgrade_preserves_v1_project_layout_and_historical_receipts()`
	# @used-by :meth:`test_path_registry.PathRegistryTests.test_v2_filesystem_auto_detection_journals_context_provenance_and_migration()`
	@property
	def manual_kb_dir(self) -> Path:
		return Path(self.paths_str['manual_kb_dir'])
	# @used-by :func:`agent_tools.research.observed_use()`
	# @used-by :meth:`Df.Harness.Meta.MetricsSummarizer.MetricsSummarizer.project_metrics()`
	# @used-by :meth:`test_path_registry.PathRegistryTests.test_live_five_projects_integration_across_harness_subsystems_and_cli()`
	# @used-by :meth:`test_path_registry.PathRegistryTests.test_project_overlay_dag_cascades_and_remains_isolated_per_project()`
	@property
	def metrics_json(self) -> Path:
		return Path(self.paths_str['metrics_json'])
	# @used-by :func:`Df.Core.lib.fs.df_uri_file_decode()`
	# @used-by :func:`Df.Harness.lib.completion_checks.dfh_is_client_deliverable_path()`
	# @used-by :func:`Df.Harness.lib.completion_links._normalize_file_href_path()`
	# @used-by :func:`Df.Harness.lib.config_blocks.dfh_has_linked_ancestor()`
	# @used-by :func:`Df.Harness.lib.grounding_md.dfh_is_documentation_url()`
	# @used-by :func:`Df.Harness.lib.journal_upgrade._assert_not_linked_tree()`
	# @used-by :func:`Df.Harness.lib.native_links.dfh_absolute()`
	# @used-by :func:`Df.Harness.lib.native_links.dfh_direct_link_matches_target()`
	# @used-by :func:`Df.Harness.lib.native_links.dfh_exists()`
	# @used-by :func:`Df.Harness.lib.native_links.dfh_is_relocated_owned_link()`
	# @used-by :func:`Df.Harness.lib.native_links.dfh_link_matches_target()`
	# @used-by :func:`Df.Harness.lib.path_discovery.dfh_candidate_discovery_roots()`
	# @used-by :func:`Df.Harness.lib.path_resolve._stat_unlinked_registry()`
	# @used-by :func:`Df.Harness.lib.path_resolve.dfh_load_registry()`
	# @used-by :func:`Df.Harness.lib.path_resolve.dfh_relocated_harness_code_dirs()`
	# @used-by :func:`Df.Harness.lib.path_schema._build_similar_members()`
	# @used-by :func:`Df.Harness.lib.path_schema._collect_member_affiliates()`
	# @used-by :func:`Df.Harness.lib.path_schema._collect_overlay_files()`
	# @used-by :func:`Df.Harness.lib.path_state._fast_sig()`
	# @used-by :func:`Df.Harness.lib.path_template.dfh_is_linked()`
	# @used-by :func:`Df.Harness.lib.path_template.dfh_normalize_path_str()`
	# @used-by :func:`Df.Harness.lib.runtime_cache._file_stat_key()`
	# @used-by :func:`Df.Harness.lib.runtime_validate.dfh_expand_path()`
	# @used-by :func:`Df.Harness.lib.trace_common.dfh_local_uri_to_path()`
	# @used-by :func:`Df.Harness.lib.uri.dfh_local_uri_to_path()`
	# @used-by :func:`agent_tools.links.readable_reference()`
	# @used-by :func:`agent_tools.links.validate_file()`
	# @used-by :func:`agent_tools.markdown_links.decode_file_uri()`
	# @used-by :func:`agent_tools.markdown_links.display_address()`
	# @used-by :func:`agent_tools.text_browser._endpoint_with_meta()`
	# @used-by :func:`check_pre_invocation._ensure_scripts_on_path()`
	# @used-by :func:`check_stop_gate._ensure_scripts_on_path()`
	# @used-by :func:`conftest.configure_test_environment()`
	# @used-by :meth:`Df.Harness.Analysis.ObservationHtmlResolver.ObservationHtmlResolver.resolve()`
	# @used-by :meth:`Df.Harness.Analysis.RedFlagSyncer.RedFlagSyncer.sync()`
	# @used-by :meth:`Df.Harness.Completion.JournalReconciler.JournalReconciler.__prune_delivered_checkpoint_recovery()`
	# @used-by :meth:`Df.Harness.Config.NativeProfile.Applier.Applier.__handle_failure()`
	# @used-by :meth:`Df.Harness.Config.NativeProfile.Applier.Applier.__rollback()`
	# @used-by :meth:`Df.Harness.Gate.RepoLinkGate.RepoLinkGate.__validate_file_uri()`
	# @used-by :meth:`Df.Harness.Gate.RepoLinkGate.RepoLinkGate.__validate_relative_cross_repo()`
	# @used-by :meth:`Df.Harness.Gate.RepoLinkResolver.RepoLinkResolver.enclosing_github_repo()`
	# @used-by :meth:`Df.Harness.Git.VerificationSpecResolver.VerificationSpecResolver.__expand_token()`
	# @used-by :meth:`Df.Harness.Path.PathReporter.PathReporter.__check_similar_groups()`
	# @used-by :meth:`Df.Harness.Path.Registry.Registry.__init_core_maps()`
	# @used-by :meth:`Df.Harness.Perf.SuiteWorker.SuiteWorker.main()`
	# @used-by :meth:`Df.Harness.Project.Intake.IntakePathGuard.IntakePathGuard.plain()`
	# @used-by :meth:`Df.Harness.Project.WebsiteCardSyncer.WebsiteCardSyncer.sync()`
	# @used-by :meth:`Df.Harness.Project.WebsiteCardSyncer.WebsiteCardSyncer.sync_initial()`
	# @used-by :meth:`Df.Harness.Tdd.DiffCoverage.DiffCoverage.__find_uncovered()`
	# @used-by :meth:`Df.Harness.Tdd.DiffCoverageHook.DiffCoverageHook.prepare_env()`
	# @used-by :meth:`Df.Harness.Tdd.OutcomeParser.OutcomeParser.uri_to_local_path()`
	# @used-by :meth:`Df.Harness.Upwork.AttachmentDownloader.AttachmentDownloader.__build_headers()`
	# @used-by :meth:`Df.Harness.Upwork.CliRunner.CliRunner.__cmd_init()`
	# @used-by :meth:`Df.Harness.Upwork.JobUrlParser.JobUrlParser.extract_upwork_job_url_id()`
	# @used-by :meth:`Df.Harness.Upwork.ProjectConfigurator.ProjectConfigurator.default_context_config()`
	# @used-by :meth:`Df.Harness.Upwork.ProjectInitializer.ProjectInitializer.__init_locked_state()`
	# @used-by :meth:`Df.Harness.Workflow.ProgressPublisher.ProgressPublisher.__question_lines()`
	# @used-by :meth:`Df.Harness.Workflow.ProgressPublisher.ProgressPublisher.publish()`
	# @used-by :meth:`test_df_dotpy_bootstrap.DfDotPyBootstrapTests.test_df_bootstrap_loads_dotpy_packages_and_sibling_modules()`
	# @used-by :meth:`test_hook_trace_cache_and_watchdog.HookTraceCacheAndWatchdogTests.test_in_process_cache_shares_single_disk_read_across_pre_tool_gates()`
	# @used-by :meth:`test_path_registry.PathRegistryTests.test_live_five_projects_integration_across_harness_subsystems_and_cli()`
	# @used-by :meth:`test_path_registry.PathRegistryTests.test_project_overlay_dag_cascades_and_remains_isolated_per_project()`
	# @used-by :meth:`test_path_registry.PathRegistryTests.test_transitive_escapes_literal_dollar_in_env_and_relative_slot_anchoring()`
	# @used-by :meth:`test_path_registry.PathRegistryTests.test_v2_filesystem_auto_detection_journals_context_provenance_and_migration()`
	# @used-by :mod:`check_markdown_slop`
	# @used-by :mod:`check_rules_and_server_gate`
	# @used-by :mod:`df_article`
	# @used-by :mod:`df_github_issue`
	# @used-by :mod:`generate_context`
	# @used-by :mod:`git_fixture_cache`
	# @used-by :mod:`git_shim`
	# @used-by :mod:`harness`
	# @used-by :mod:`safe_commit`
	# @used-by :mod:`snapshot_draft`
	# @used-by :mod:`split_project_rules`
	# @used-by :mod:`test_addon_observability`
	# @used-by :mod:`test_agent_tools`
	# @used-by :mod:`test_arch_audit_gates`
	# @used-by :mod:`test_arch_review_cli`
	# @used-by :mod:`test_arch_rules_contract`
	# @used-by :mod:`test_arch_spec_and_triggers`
	# @used-by :mod:`test_ask_question_clarifications_m8`
	# @used-by :mod:`test_ask_question_pre_tool_gate`
	# @used-by :mod:`test_atomic_prepare_and_narrowed_reconcile_m7`
	# @used-by :mod:`test_background_wait_and_tdd_inheritance`
	# @used-by :mod:`test_blocked_report_hygiene_and_doc5_m2`
	# @used-by :mod:`test_blocked_report_m2`
	# @used-by :mod:`test_bounded_foreign_sync`
	# @used-by :mod:`test_budget_status_scoping`
	# @used-by :mod:`test_chat_reply_link_issues_m5`
	# @used-by :mod:`test_clarification_stop_consent`
	# @used-by :mod:`test_cleanup_audit`
	# @used-by :mod:`test_cleanup_integration`
	# @used-by :mod:`test_cleanup_lifecycle`
	# @used-by :mod:`test_cli_command_grounding`
	# @used-by :mod:`test_cli_common`
	# @used-by :mod:`test_cli_output_json`
	# @used-by :mod:`test_cli_registry`
	# @used-by :mod:`test_code_fanout_gates`
	# @used-by :mod:`test_code_formatting_rules`
	# @used-by :mod:`test_code_size_gate`
	# @used-by :mod:`test_code_style_gate`
	# @used-by :mod:`test_comment_exemption_and_denied_writes`
	# @used-by :mod:`test_context_and_storage_determinism`
	# @used-by :mod:`test_contract_invariants`
	# @used-by :mod:`test_cross_repo_issue_urls`
	# @used-by :mod:`test_df_analysis_companion_tracks`
	# @used-by :mod:`test_df_analysis_rules_contract`
	# @used-by :mod:`test_df_analysis`
	# @used-by :mod:`test_df_core_array`
	# @used-by :mod:`test_df_core_base`
	# @used-by :mod:`test_df_core_qa_s10`
	# @used-by :mod:`test_df_core_text_misc`
	# @used-by :mod:`test_df_dotpy_bootstrap`
	# @used-by :mod:`test_df_harness_dedup_s8`
	# @used-by :mod:`test_df_harness_lib_s10`
	# @used-by :mod:`test_df_harness_s11_wave2a_facade_exports`
	# @used-by :mod:`test_df_harness_s11_wave2a_project_ext`
	# @used-by :mod:`test_df_harness_s11_wave2a_review`
	# @used-by :mod:`test_df_harness_s11_wave2a_upwork`
	# @used-by :mod:`test_df_harness_s11_wave2a_workflow`
	# @used-by :mod:`test_df_harness_s11_wave2a`
	# @used-by :mod:`test_df_harness_s11_wave2b_gate_cov`
	# @used-by :mod:`test_df_harness_s11_wave2b_gate`
	# @used-by :mod:`test_df_harness_s11_wave2b_meta_cov`
	# @used-by :mod:`test_df_harness_s11_wave2b_meta`
	# @used-by :mod:`test_df_harness_s11_wave2b_perf_runner_cov`
	# @used-by :mod:`test_df_harness_s11_wave2b_tail_cov`
	# @used-by :mod:`test_df_harness_s11_wave2b_tdd_cov1`
	# @used-by :mod:`test_df_harness_s11_wave2b_tdd_cov2`
	# @used-by :mod:`test_df_harness_s11_wave2b_tdd`
	# @used-by :mod:`test_df_harness_s11_wave2b_xref_cov`
	# @used-by :mod:`test_df_harness_s11_wave2b_xref`
	# @used-by :mod:`test_df_harness_s11_wave2b`
	# @used-by :mod:`test_df_harness_s11_wave2c_cross_wave`
	# @used-by :mod:`test_df_harness_s11_wave2c_git`
	# @used-by :mod:`test_df_harness_s11_wave2c_grounding`
	# @used-by :mod:`test_df_harness_s11_wave2c_issues`
	# @used-by :mod:`test_df_harness_s11_wave2d_cli_cov`
	# @used-by :mod:`test_df_harness_s11_wave2d_completion_cov`
	# @used-by :mod:`test_df_harness_s11_wave2d_completion`
	# @used-by :mod:`test_df_harness_s11_wave2d_config_cov`
	# @used-by :mod:`test_df_harness_s11_wave2d_hook_cov`
	# @used-by :mod:`test_df_harness_s11_wave2d_journal_path_cov`
	# @used-by :mod:`test_df_harness_s11_wave2d_platform_cov`
	# @used-by :mod:`test_df_harness_s11_wave2d_shadow_runtime_cov`
	# @used-by :mod:`test_df_harness_s11_wave2d_tail_cov`
	# @used-by :mod:`test_df_harness_s11_wave2d`
	# @used-by :mod:`test_df_harness_s11_wave2e_arch`
	# @used-by :mod:`test_df_qa`
	# @used-by :mod:`test_df_upstream_fixes`
	# @used-by :mod:`test_diff_coverage_gate`
	# @used-by :mod:`test_diff_executability_contract`
	# @used-by :mod:`test_diff_executability_telemetry`
	# @used-by :mod:`test_diff_executability`
	# @used-by :mod:`test_dirty_diff_issue_scope`
	# @used-by :mod:`test_doc5_context_trigger`
	# @used-by :mod:`test_doc5_golden_feature_turn`
	# @used-by :mod:`test_doc5_replay_audit`
	# @used-by :mod:`test_env_isolation_and_worktree_gate_contracts`
	# @used-by :mod:`test_evidence_unification`
	# @used-by :mod:`test_executor_metadata`
	# @used-by :mod:`test_experiments`
	# @used-by :mod:`test_failfast_and_schedule_gate`
	# @used-by :mod:`test_falsifier_and_schedule_subagent_gate_m8`
	# @used-by :mod:`test_falsifier_default_send_message_and_schedule_m8`
	# @used-by :mod:`test_finalized_project_contract`
	# @used-by :mod:`test_gate_registry`
	# @used-by :mod:`test_git_fixture_cache`
	# @used-by :mod:`test_git_ignore`
	# @used-by :mod:`test_git_lifecycle_memoization`
	# @used-by :mod:`test_github_issue`
	# @used-by :mod:`test_grounding_corpus_cache_m9`
	# @used-by :mod:`test_harness_xref_compliance`
	# @used-by :mod:`test_hook_lazy_imports`
	# @used-by :mod:`test_hook_runner_e2e_budget`
	# @used-by :mod:`test_hook_runner_watchdog`
	# @used-by :mod:`test_hook_trace_cache_and_watchdog`
	# @used-by :mod:`test_hook_unification`
	# @used-by :mod:`test_incomplete_scope_regression_matrix`
	# @used-by :mod:`test_issue44`
	# @used-by :mod:`test_issue45_to_48`
	# @used-by :mod:`test_issue_close_acceptance`
	# @used-by :mod:`test_issue_comment_gate`
	# @used-by :mod:`test_issue_conversation_isolation`
	# @used-by :mod:`test_issue_decomposition`
	# @used-by :mod:`test_issue_first_completion`
	# @used-by :mod:`test_issue_first_gate`
	# @used-by :mod:`test_issue_first_github_cli`
	# @used-by :mod:`test_issue_first_pre_tool_use`
	# @used-by :mod:`test_issue_first_rules_contract`
	# @used-by :mod:`test_issue_preflight_and_batch`
	# @used-by :mod:`test_java_xref`
	# @used-by :mod:`test_journal_clarifications_and_disclosure`
	# @used-by :mod:`test_journal_idle_sync_and_liveness`
	# @used-by :mod:`test_journal_integrity`
	# @used-by :mod:`test_journal_metadata`
	# @used-by :mod:`test_js_xref`
	# @used-by :mod:`test_landing_lease`
	# @used-by :mod:`test_metadata_decomposition`
	# @used-by :mod:`test_metadata_rules_contract`
	# @used-by :mod:`test_metadata`
	# @used-by :mod:`test_mixed_commit_audit`
	# @used-by :mod:`test_multiturn_handoff_stop_guard_and_schedule_m1`
	# @used-by :mod:`test_native_review_binding_m4`
	# @used-by :mod:`test_observability_diagnostics`
	# @used-by :mod:`test_open_child_deferral_gate`
	# @used-by :mod:`test_optimistic_worktree_land`
	# @used-by :mod:`test_parallel_runner`
	# @used-by :mod:`test_parallel_test_runner`
	# @used-by :mod:`test_path_cache_and_diff_cov_perf`
	# @used-by :mod:`test_path_registry_perf`
	# @used-by :mod:`test_path_registry`
	# @used-by :mod:`test_perf_improvement_skill_contract`
	# @used-by :mod:`test_perf_profile_tests`
	# @used-by :mod:`test_perf_timesheet`
	# @used-by :mod:`test_polyglot_land`
	# @used-by :mod:`test_problem_metadata`
	# @used-by :mod:`test_project_domain_drift`
	# @used-by :mod:`test_project_labels`
	# @used-by :mod:`test_project_rename_verification`
	# @used-by :mod:`test_project_rename`
	# @used-by :mod:`test_pytest_xdist_runner`
	# @used-by :mod:`test_python_integrity_gate`
	# @used-by :mod:`test_python_xref`
	# @used-by :mod:`test_repo_link_gate`
	# @used-by :mod:`test_repo_locator_perf`
	# @used-by :mod:`test_repo_tag_close_gate`
	# @used-by :mod:`test_repo_tags_docs`
	# @used-by :mod:`test_repo_tags`
	# @used-by :mod:`test_repo_wait_and_retry`
	# @used-by :mod:`test_reused_reviewer_and_metadata_drift_m5`
	# @used-by :mod:`test_review_contract_package_and_paths_m6`
	# @used-by :mod:`test_review_target_claim_and_wait_m5`
	# @used-by :mod:`test_rules_architecture_m2`
	# @used-by :mod:`test_rules_audit`
	# @used-by :mod:`test_rules_progressive_disclosure`
	# @used-by :mod:`test_runtime_cache_and_evidence_fastpath_m9`
	# @used-by :mod:`test_runtime_snapshot`
	# @used-by :mod:`test_scatter_banner_gate`
	# @used-by :mod:`test_schema_help_and_analysis_merge_m10`
	# @used-by :mod:`test_scratch_slop_and_grounding_loc_m7`
	# @used-by :mod:`test_service_finalization_exempt_and_sync_all_open`
	# @used-by :mod:`test_shadow_replay_command`
	# @used-by :mod:`test_shadow_replay_m3`
	# @used-by :mod:`test_shell_herestring_write_targets_m4`
	# @used-by :mod:`test_snapshot_canary_and_hook_crash_audit`
	# @used-by :mod:`test_snapshot_latency_and_delegation_policy`
	# @used-by :mod:`test_source_diagnostics_scanner`
	# @used-by :mod:`test_source_grounding`
	# @used-by :mod:`test_stop_emergency_capture_and_foreign_sync`
	# @used-by :mod:`test_stop_gate_contract`
	# @used-by :mod:`test_stop_gate_subagents_m1`
	# @used-by :mod:`test_storage_fsync_guard`
	# @used-by :mod:`test_subprocess_hygiene_and_tree_kill`
	# @used-by :mod:`test_tdd_comment_exemption`
	# @used-by :mod:`test_tdd_completion`
	# @used-by :mod:`test_tdd_decomposition`
	# @used-by :mod:`test_tdd_fast_path`
	# @used-by :mod:`test_tdd_gate`
	# @used-by :mod:`test_tdd_git_gate`
	# @used-by :mod:`test_tdd_mechanical_exemption`
	# @used-by :mod:`test_tdd_pre_tool_use_perf`
	# @used-by :mod:`test_tdd_pre_tool_use`
	# @used-by :mod:`test_tdd_rules_contract`
	# @used-by :mod:`test_tdd_worktree_and_subagent_trace`
	# @used-by :mod:`test_text_browser`
	# @used-by :mod:`test_text_diagnostics`
	# @used-by :mod:`test_text_native_binding`
	# @used-by :mod:`test_turn_begin_status_and_auditors`
	# @used-by :mod:`test_turn_completion`
	# @used-by :mod:`test_turn_routing_and_handoff_m6`
	# @used-by :mod:`test_upwork_data`
	# @used-by :mod:`test_upwork_init_e2e`
	# @used-by :mod:`test_verification_observability`
	# @used-by :mod:`test_watchdog_and_timeout_gate`
	# @used-by :mod:`test_worker_semaphore_and_xdist`
	# @used-by :mod:`test_worktree_cleanup_guard`
	# @used-by :mod:`test_worktree_comment_exemption`
	# @used-by :mod:`test_worktree_flow`
	# @used-by :mod:`test_worktree_ignore`
	# @used-by :mod:`test_worktree_isolation_gate`
	# @used-by :mod:`test_worktree_lifecycle`
	# @used-by :mod:`test_xref_gate`
	# @used-by :mod:`upwork_project`
	# @used-by :mod:`validate_anchors`
	# @used-by :mod:`validate_links`
	# @used-by :mod:`validate_statements`
	# @used-by :mod:`validate_step`
	def path(self, name: str, default: str | Path | None=None) -> Path | None:
		return Path(self.paths_str[name]) if name in self.paths_str else (Path(default) if None is not default else None)
	# @used-by :func:`Df.Harness.lib.blocked_report_ops._needs_upwork_adoption()`
	# @used-by :func:`Df.Harness.lib.completion_checks.dfh_delegation_status()`
	# @used-by :func:`Df.Harness.lib.completion_commands._try_launcher_handoff()`
	# @used-by :func:`Df.Harness.lib.path_resolve._workspace_is_explicitly_tracked()`
	# @used-by :func:`Df.Harness.lib.path_state._fast_sig()`
	# @used-by :func:`Df.Harness.lib.request_binding.dfh_completion_project_id()`
	# @used-by :func:`Df.Harness.lib.request_binding.dfh_native_project_fields()`
	# @used-by :func:`Df.Harness.lib.request_binding.dfh_native_project_id()`
	# @used-by :func:`agent_tools.text_sources._evaluate()`
	# @used-by :func:`test_df_harness_s11_wave2a_workflow._seed_project()`
	# @used-by :meth:`Df.Harness.Analysis.Claim.ManifestPrimaryVerifier.ManifestPrimaryVerifier.__load_state()`
	# @used-by :meth:`Df.Harness.Completion.BudgetEvaluator.BudgetEvaluator.run()`
	# @used-by :meth:`Df.Harness.Gate.ExternalWriteGate.ExternalWriteGate.__match_upwork_root()`
	# @used-by :meth:`Df.Harness.Grounding.ResponseAuditor.ResponseAuditor.__check_kb_membership()`
	# @used-by :meth:`Df.Harness.Grounding.ResponseAuditor.ResponseAuditor.__collect_client_urls()`
	# @used-by :meth:`Df.Harness.Meta.ProjectIdentity.ProjectIdentity.__lookup_name_from_project_json()`
	# @used-by :meth:`Df.Harness.Platform.Antigravity.ProjectRegistrar.ProjectRegistrar.__resolve_day()`
	# @used-by :meth:`Df.Harness.Project.AttachmentKbSyncer.AttachmentKbSyncer.sync()`
	# @used-by :meth:`Df.Harness.Project.DriftAuditor.DriftAuditor.audit()`
	# @used-by :meth:`Df.Harness.Project.Intake.CaptureCommitter.CaptureCommitter.__run_locked()`
	# @used-by :meth:`Df.Harness.Project.Intake.CaptureCommitter.CaptureCommitter.resolve_project()`
	# @used-by :meth:`Df.Harness.Project.RegistrationExpectation.RegistrationExpectation.build()`
	# @used-by :meth:`Df.Harness.Project.Rename.ProjectRenamer.ProjectRenamer.__validate_inputs()`
	# @used-by :meth:`Df.Harness.Project.Rename.ProjectRenamer.ProjectRenamer.maybe_promote_domain()`
	# @used-by :meth:`Df.Harness.Project.Rename.StateRewriter.StateRewriter.__update_project_json()`
	# @used-by :meth:`Df.Harness.Upwork.ProjectInitializer.ProjectInitializer.__init_locked_state()`
	# @used-by :meth:`Df.Harness.Workflow.WorkflowResumer.WorkflowResumer.__apply()`
	@property
	def project_json(self) -> Path:
		return Path(self.paths_str['project_json'])
	# @used-by :func:`Df.Harness.lib.path_resolve._build_or_fetch_project_paths()`
	# @used-by :func:`Df.Harness.lib.path_resolve.dfh_project_paths()`
	# @used-by :meth:`ProjectPaths.__init__()`
	def register_reverse_links(self) -> None:
		rk = dfh_path_key(self.root)
		if self.has_overlay:
			for ext in (*self.linked_roots, *self.code_repos, *self.auxiliary_repos.values()):
				ek = dfh_path_key(ext)
				if ek != rk:
					OVERLAY_REVERSE_MAP[ek] = self.root
		reg_key = dfh_path_key(self.registry.source_path)
		for sp in self.direct_similar_projects:
			peers = SIMILAR_REVERSE_MAP.setdefault((reg_key, dfh_path_key(sp)), [])
			if all((dfh_path_key(p) != rk for p in peers)):
				peers.append(self.root)
	# @used-by :func:`Df.Harness.lib.shadow_command._stage_ag_from_receipt()`
	# @used-by :meth:`Df.Harness.Project.DriftAuditor.DriftAuditor.__title_mismatches()`
	# @used-by :meth:`Df.Harness.Project.RegistrationAttemptStarter.RegistrationAttemptStarter.begin()`
	# @used-by :meth:`Df.Harness.Project.RegistrationStore.RegistrationStore.save()`
	# @used-by :meth:`Df.Harness.Project.Rename.ProjectRenamer.ProjectRenamer.__extract_prior_ag_id()`
	# @used-by :meth:`Df.Harness.Project.Rename.ProjectRenamer.ProjectRenamer.__sync_registrations()`
	@property
	def registrations_json(self) -> Path:
		return Path(self.paths_str['registrations_json'])
	# @used-by :func:`Df.Harness.lib.journal_integrity_ops.dfh_check_project_journal_problems()`
	# @used-by :meth:`Df.Harness.Analysis.RedFlagSyncer.RedFlagSyncer.sync()`
	# @used-by :meth:`Df.Harness.Project.DriftAuditor.DriftAuditor.audit()`
	# @used-by :meth:`Df.Harness.Project.ExtraSourceBuilder.ExtraSourceBuilder.__process_asset()`
	# @used-by :meth:`Df.Harness.Project.Intake.CaptureCommitter.CaptureCommitter.__run_commit()`
	# @used-by :meth:`Df.Harness.Project.Intake.CaptureCommitter.CaptureCommitter.__run_locked()`
	# @used-by :meth:`Df.Harness.Project.Intake.CaptureCommitter.CaptureCommitter.resolve_project()`
	# @used-by :meth:`Df.Harness.Project.Intake.IntakeIndexer.IntakeIndexer.rebuild()`
	# @used-by :meth:`Df.Harness.Project.Intake.ReceiptBuilder.ReceiptBuilder.build()`
	# @used-by :meth:`Df.Harness.Project.Intake.ReceiptValidator.ReceiptValidator.validate()`
	# @used-by :meth:`Df.Harness.Project.Intake.ReceiptValidator.ReceiptValidator.verify_snapshot()`
	# @used-by :meth:`Df.Harness.Project.WebsiteCardSyncer.WebsiteCardSyncer.__sync_selected()`
	# @used-by :meth:`Df.Harness.Project.WebsiteCardSyncer.WebsiteCardSyncer.sync_initial()`
	# @used-by :meth:`Df.Harness.Upwork.ProjectConfigurator.ProjectConfigurator.default_context_config()`
	def rel_to_root(self, target: str | Path) -> str:
		p = Path(target).resolve()
		return p.relative_to(self.root).as_posix() if p.is_relative_to(self.root) else p.as_posix()
	# @used-by :func:`Df.Harness.lib.cli_domain_ops.dfh_execute_collect()`
	# @used-by :meth:`Df.Harness.Analysis.OwnedPublisher.OwnedPublisher.publish()`
	# @used-by :meth:`Df.Harness.Project.CardSyncer.CardSyncer.sync()`
	# @used-by :meth:`Df.Harness.Project.WebsiteCardSyncer.WebsiteCardSyncer.sync()`
	@property
	def rendered_json(self) -> Path:
		return Path(self.paths_str['rendered_json'])
	# @used-by :func:`Df.Harness.lib.cli_input.dfh_verify_scratch_input_path()`
	# @used-by :func:`Df.Harness.lib.completion_commands._collect_check_payload()`
	# @used-by :func:`Df.Harness.lib.completion_compaction._is_pre_checkpoint_authored()`
	# @used-by :func:`Df.Harness.lib.hook_pre_invocation_ops.dfh_scratch_answer_path()`
	# @used-by :meth:`Df.Harness.Project.FinalizeDriftGuard.FinalizeDriftGuard.require()`
	# @used-by :meth:`Df.Harness.Project.Rename.StateRewriter.StateRewriter.rewrite()`
	# @used-by :meth:`Df.Harness.Shadow.ReplayRunner.ReplayRunner.run()`
	@property
	def scratch_dir(self) -> Path:
		return Path(self.paths_str['scratch_dir'])
	# @used-by :func:`Df.Harness.lib.completion_checks.dfh_similar_projects_metadata()`
	# @used-by :func:`Df.Harness.lib.completion_recovery._allowed_similar_peers()`
	# @used-by :meth:`Df.Harness.Issue.PendingPeerFinder.PendingPeerFinder.find()`
	# @used-by :meth:`Df.Harness.Path.PathReporter.PathReporter.__build_project_report()`
	# @used-by :meth:`Df.Harness.Path.PathReporter.PathReporter.__discover_overlays()`
	# @used-by :meth:`Df.Harness.Path.SimilarProjectAuditor.SimilarProjectAuditor.__eval_overlay_peers()`
	# @used-by :meth:`ProjectPaths.to_dict()`
	# @used-by :meth:`test_path_registry.PathRegistryTests.test_similar_projects_groups_symmetric_overlays_affiliated_paths_and_validation()`
	@property
	def similar_projects(self) -> tuple[Path, ...]:
		out: list[Path] = list(self.direct_similar_projects)
		seen: set[str] = {dfh_path_key(self.root), *(dfh_path_key(p) for p in out)}
		if self.__include_reverse_similar:
			dfh_refresh_known_overlay_links(self.registry)
			rk, reg_key = (dfh_path_key(self.root), dfh_path_key(self.registry.source_path))
			for peer in [*DISCOVERY_STATE['similar_links'].get(rk, ()), *SIMILAR_REVERSE_MAP.get((reg_key, rk), ())]:
				pk = dfh_path_key(peer)
				if pk not in seen:
					seen.add(pk)
					out.append(peer)
		return tuple(out)
	# @used-by :meth:`Df.Harness.Analysis.LocalSourceResolver.LocalSourceResolver.resolve()`
	# @used-by :meth:`Df.Harness.Project.ExtraSourceBuilder.ExtraSourceBuilder.__process_asset()`
	# @used-by :meth:`Df.Harness.Workflow.HashCollector.HashCollector.evidence_paths()`
	@property
	def source_dir(self) -> Path:
		return Path(self.paths_str['source_dir'])
	# @used-by :func:`Df.Harness.lib.request_binding._validate_text_project_marker()`
	# @used-by :func:`Df.Harness.lib.request_binding.dfh_completion_project_id()`
	# @used-by :func:`Df.Harness.lib.request_binding.dfh_native_project_fields()`
	# @used-by :func:`test_arch_review_cli._init_text_workspace()`
	@property
	def text_project_json(self) -> Path:
		return Path(self.paths_str['text_project_json'])
	# @used-by :meth:`Df.Harness.Path.PathReporter.PathReporter.__build_project_report()`
	# @used-by :meth:`test_df_harness_s11_wave2d_journal_path_cov.DfHarnessS11Wave2dJournalPathCovTests.test_paths_and_uri()`
	# @used-by :meth:`test_path_registry.PathRegistryTests.test_similar_projects_groups_symmetric_overlays_affiliated_paths_and_validation()`
	def to_dict(self, *, check_exists: bool=True) -> dict[str, Any]:
		paths_view = {**self.paths_str, 'journal_dir': self.journal_dir.as_posix()}
		sim = self.similar_projects
		out: dict[str, Any] = {'auxiliary_repos': {k: p.as_posix() for k, p in self.auxiliary_repos.items()}, 'code_repos': [p.as_posix() for p in self.code_repos], 'fs_version': self.fs_version, 'has_overlay': self.has_overlay, 'journal_version': self.journal_version, 'linked_roots': [p.as_posix() for p in self.linked_roots], 'overlay_file': self.overlay_file.as_posix() if self.overlay_file else None, 'paths': paths_view, 'profile': self.profile, 'project_root': self.root.as_posix(), 'similar_projects': [p.as_posix() for p in sim], 'tools': deepcopy(self.tools)}
		if check_exists:
			out.update({'code_repos_exist': {p.as_posix(): p.is_dir() for p in self.code_repos}, 'linked_roots_exist': {p.as_posix(): p.exists() for p in self.linked_roots}, 'paths_exist': {k: self.__path_exists(v) for k, v in paths_view.items()}, 'similar_projects_exist': {p.as_posix(): p.is_dir() for p in sim}})
		return out
	# @used-by :func:`Df.Harness.lib.completion_core.dfh_turns_folder()`
	# @used-by :func:`Df.Harness.lib.hook_crash_ops.dfh_load_violation_receipt()`
	# @used-by :func:`Df.Harness.lib.hook_markdown_ops.dfh_check_turn_budget_gate()`
	# @used-by :func:`Df.Harness.lib.journal.dfh_turns_dir()`
	# @used-by :func:`Df.Harness.lib.path_resolve._workspace_is_explicitly_tracked()`
	# @used-by :func:`agent_tools.doc5_replay_audit.audit_local_saved_turns()`
	# @used-by :meth:`Df.Harness.Completion.BudgetEvaluator.BudgetEvaluator.run()`
	# @used-by :meth:`Df.Harness.Gate.ExternalWriteGate.ExternalWriteGate.__check_df_issue_turn_intent()`
	# @used-by :meth:`Df.Harness.Git.TransientWaitRunner.TransientWaitRunner.__active_turn_paths()`
	# @used-by :meth:`Df.Harness.Issue.CompetingTurnChecker.CompetingTurnChecker.__candidate_turns_dirs()`
	# @used-by :meth:`Df.Harness.Issue.EvidenceWorkspace.EvidenceWorkspace.__target_for_project_root()`
	# @used-by :meth:`Df.Harness.Issue.EvidenceWorkspace.EvidenceWorkspace.issue_target_for_path()`
	# @used-by :meth:`Df.Harness.Issue.ParityAuditor.ParityAuditor.__load_exemptions()`
	# @used-by :meth:`Df.Harness.Issue.PendingPeerFinder.PendingPeerFinder.find()`
	# @used-by :meth:`Df.Harness.Meta.Builders.Builders.__find_issue_state_pair()`
	# @used-by :meth:`Df.Harness.Meta.Builders.Builders.build_journal()`
	# @used-by :meth:`Df.Harness.Project.Rename.PostRenameVerifier.PostRenameVerifier.__launcher_stale_files()`
	# @used-by :meth:`Df.Harness.Project.Rename.StateRewriter.StateRewriter.rewrite()`
	# @used-by :meth:`Df.Harness.Project.Rename.StateRewriter.StateRewriter.rewrite_launcher_handoffs()`
	# @used-by :meth:`Df.Harness.Shadow.ReplayPipeline.ReplayPipeline.__find_reply_path()`
	# @used-by :meth:`Df.Harness.Shadow.ReplayPipeline.ReplayPipeline.__run_pre_invocation()`
	# @used-by :meth:`Df.Harness.Tdd.MechanicalExemption.MechanicalExemption.__candidate_recipe_dirs()`
	# @used-by :meth:`Df.Harness.Tdd.MechanicalExemption.MechanicalExemption.record_exemption()`
	# @used-by :meth:`Df.Harness.Tdd.RatchetGuard.RatchetGuard.turn_receipt_dirs()`
	# @used-by :meth:`test_blocked_report_hygiene_and_doc5_m2.BlockedReportHygieneAndDoc5M2Tests.test_blocked_report_records_journal_despite_hygiene_failures_and_allows_doc5()`
	# @used-by :meth:`test_path_registry.PathRegistryTests.test_live_five_projects_integration_across_harness_subsystems_and_cli()`
	# @used-by :meth:`test_path_registry.PathRegistryTests.test_project_overlay_dag_cascades_and_remains_isolated_per_project()`
	@property
	def turns_dir(self) -> Path:
		return Path(self.paths_str['turns_dir'])
	# @used-by :meth:`test_df_harness_s11_wave2d_journal_path_cov.DfHarnessS11Wave2dJournalPathCovTests.test_paths_and_uri()`
	# @used-by :meth:`test_path_registry.PathRegistryTests.test_transitive_escapes_literal_dollar_in_env_and_relative_slot_anchoring()`
	def var(self, name: str, default: str | None=None) -> str | None:
		return dfh_expand_template(f'${{{name}}}', self.__variables, env=self.registry.env, normalize=True) if name in self.__variables else default
	# @used-by :meth:`Df.Harness.Review.MerkleCacheUpdater.MerkleCacheUpdater.update()`
	# @used-by :meth:`Df.Harness.Review.MerkleDeltaCalculator.MerkleDeltaCalculator.load_cache()`
	@property
	def verified_claims_json(self) -> Path:
		return Path(self.paths_str['verified_claims_json'])
	# @used-by :func:`Df.Harness.lib.blocked_report_ops.dfh_evaluate_check_workflow_errors()`
	# @used-by :func:`Df.Harness.lib.completion_checks.dfh_workflow_gate_resolved()`
	# @used-by :meth:`Df.Harness.Project.Rename.PostRenameVerifier.PostRenameVerifier.__probe_workflow()`
	# @used-by :meth:`Df.Harness.Workflow.StateLoader.StateLoader.state_path()`
	@property
	def workflow_json(self) -> Path:
		return Path(self.paths_str['workflow_json'])
	# @used-by :func:`Df.Harness.lib.cli_registry_handlers.dfh_exec_worktree_begin()`
	# @used-by :func:`Df.Harness.lib.worktree.dfh_prepare_worktrees_base_dir()`
	# @used-by :meth:`test_df_harness_s11_wave2d_journal_path_cov.DfHarnessS11Wave2dJournalPathCovTests.test_paths_and_uri()`
	@property
	def worktrees_dir(self) -> Path:
		return Path(self.paths_str['worktrees_dir'])
