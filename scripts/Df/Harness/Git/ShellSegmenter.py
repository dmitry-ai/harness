# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
import re
_SEPARATORS = frozenset({';', '\r', '\n', '&&', '||', '|'})
_TOKEN_RE = re.compile(r'("(?:\\.|[^"\\])*"|\'(?:\\.|[^\'\\])*\'|&&|\|\||[;\|\r\n]|[^"\'\s;\|\&]+|\s+)')
# 2026-11-26 "Move repository and grounding subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/382
class ShellSegmenter:
	# @used-by :func:`Df.Harness.lib.issue.dfh_is_df_issue_command_text()`
	# @used-by :func:`agent_tools.shell_audit._split_shell_segments()`
	# @used-by :meth:`Df.Harness.Git.CdpBypassAudit.CdpBypassAudit.detect()`
	# @used-by :meth:`Df.Harness.Git.GitSegmentExtractor.GitSegmentExtractor.extract()`
	# @used-by :meth:`test_df_harness_s11_wave2c_git.DfHarnessS11Wave2CGitTests.test_shell_audit_single_class_modules_and_facade()`
	def __init__(self, cmd: str) -> None:
		self.__cmd = cmd
	# @used-by :func:`Df.Core.lib.reflection.text.explode.df_explode_method()`
	# @used-by :func:`Df.Core.lib.text.camel.df_explode_camel()`
	# @used-by :func:`Df.Core.lib.text.csv.df_csv_parse()`
	# @used-by :func:`Df.Core.lib.text.explode.df_explode_multiple()`
	# @used-by :func:`Df.Core.lib.text.explode.df_explode_space()`
	# @used-by :func:`Df.Core.lib.text.explode.df_explode_url()`
	# @used-by :func:`Df.Core.lib.text.parse.df_parse_colon()`
	# @used-by :func:`Df.Harness.lib.ag_inputs._extract_event_direct_uuids()`
	# @used-by :func:`Df.Harness.lib.env_isolation_ops._find_test_method()`
	# @used-by :func:`Df.Harness.lib.grounding.dfh_norm_quote_text()`
	# @used-by :func:`Df.Harness.lib.grounding.dfh_quote_segments_present()`
	# @used-by :func:`Df.Harness.lib.grounding.dfh_resolve_local_href()`
	# @used-by :func:`Df.Harness.lib.hook_runtime_ops.dfh_scan_doc4_sentence_issues()`
	# @used-by :func:`Df.Harness.lib.hook_subagent_ops._process_row_message()`
	# @used-by :func:`Df.Harness.lib.hook_verif_ops.dfh_is_shadow_replay_cmd()`
	# @used-by :func:`Df.Harness.lib.issue.dfh_build_create_payload()`
	# @used-by :func:`Df.Harness.lib.issue.dfh_is_df_issue_command_text()`
	# @used-by :func:`Df.Harness.lib.issue.dfh_is_excluded_meta_rel()`
	# @used-by :func:`Df.Harness.lib.path_template.dfh_glob_parent_stat()`
	# @used-by :func:`Df.Harness.lib.path_template.dfh_normalize_path_str()`
	# @used-by :func:`Df.Harness.lib.rule_splitter._partition_rule_sections()`
	# @used-by :func:`Df.Harness.lib.shadow_command._build_command_argv()`
	# @used-by :func:`Df.Harness.lib.snapshot_canary_ops.dfh_inspect_fallback_timeout_spike()`
	# @used-by :func:`Df.Harness.lib.text_claims.dfh_primary_numbers()`
	# @used-by :func:`Df.Qa.lib.bt.main.df_bt_has()`
	# @used-by :func:`Df.Qa.lib.diagnostics.df_webserver()`
	# @used-by :func:`agent_tools.cli_output_json._body_without_header()`
	# @used-by :func:`agent_tools.evidence.contains_quote()`
	# @used-by :func:`agent_tools.shell_audit._split_shell_segments()`
	# @used-by :func:`test_issue_preflight_and_batch._make_fake_gh()`
	# @used-by :meth:`Df.DotPyFinder.__resolve_target()`
	# @used-by :meth:`Df.Harness.Analysis.Claim.InlineCalcVerifier.InlineCalcVerifier.__decimal_matches()`
	# @used-by :meth:`Df.Harness.Analysis.Claim.InlineCalcVerifier.InlineCalcVerifier.__record_rhs()`
	# @used-by :meth:`Df.Harness.Analysis.Claim.QuantityMatcher.QuantityMatcher.__sign_before()`
	# @used-by :meth:`Df.Harness.Analysis.Claim.SourceNumericTokenizer.SourceNumericTokenizer.tokenize()`
	# @used-by :meth:`Df.Harness.Analysis.HtmlQuoteVerifier.HtmlQuoteVerifier.__contains()`
	# @used-by :meth:`Df.Harness.Analysis.JsonPointer.JsonPointer.resolve()`
	# @used-by :meth:`Df.Harness.Analysis.ObservationBundleLoader.ObservationBundleLoader.__inspect_resp_bin()`
	# @used-by :meth:`Df.Harness.Analysis.ObservationContentLoader.ObservationContentLoader.load()`
	# @used-by :meth:`Df.Harness.Analysis.ObservationProber.ObservationProber.probe()`
	# @used-by :meth:`Df.Harness.Analysis.RedFlagSyncer.RedFlagSyncer.__build_block()`
	# @used-by :meth:`Df.Harness.Analysis.SavedQuoteVerifier.SavedQuoteVerifier.__contains()`
	# @used-by :meth:`Df.Harness.Analysis.Validator.Validator.__check_legacy_argument()`
	# @used-by :meth:`Df.Harness.Arch.Catalog.Catalog.__candidate_pattern_keys()`
	# @used-by :meth:`Df.Harness.Cli.GitShim.GitShim.__normalize_arg_token()`
	# @used-by :meth:`Df.Harness.Experiment.RunAuditor.RunAuditor.__check_serp()`
	# @used-by :meth:`Df.Harness.Gate.PythonIntegrity.PythonIntegrity.__collect_defined_globals()`
	# @used-by :meth:`Df.Harness.Gate.RepoLinkGate.RepoLinkGate.__validate_relative_cross_repo()`
	# @used-by :meth:`Df.Harness.Gate.RepoTagGate.RepoTagGate.__read_local_tag_map()`
	# @used-by :meth:`Df.Harness.Gate.RulesAuditor.RulesAuditor.__load_rule_entries()`
	# @used-by :meth:`Df.Harness.Gate.RulesManifest.RulesManifest.inspect_rule()`
	# @used-by :meth:`Df.Harness.Git.CdpBypassAudit.CdpBypassAudit.detect()`
	# @used-by :meth:`Df.Harness.Git.CommitArgsParser.CommitArgsParser.__consume_msg_or_file()`
	# @used-by :meth:`Df.Harness.Git.CommitTagger.CommitTagger.__commit_sha_and_day()`
	# @used-by :meth:`Df.Harness.Git.CommitTagger.CommitTagger.__read_tag_refs()`
	# @used-by :meth:`Df.Harness.Git.DirtyMainChecker.DirtyMainChecker.__porcelain_paths()`
	# @used-by :meth:`Df.Harness.Git.GitSegmentExtractor.GitSegmentExtractor.extract()`
	# @used-by :meth:`Df.Harness.Git.RepoGate.RepoGate.main_repo()`
	# @used-by :meth:`Df.Harness.Git.RetroTagger.RetroTagger.__plan()`
	# @used-by :meth:`Df.Harness.Git.RetroTagger.RetroTagger.__read_tag_refs()`
	# @used-by :meth:`Df.Harness.Git.VerificationSpecResolver.VerificationSpecResolver.__auto_node_spec()`
	# @used-by :meth:`Df.Harness.Git.WorktreeCommandGuard.WorktreeCommandGuard.__has_managed_delete()`
	# @used-by :meth:`Df.Harness.Git.WorktreeCommandGuard.WorktreeCommandGuard.check()`
	# @used-by :meth:`Df.Harness.Git.WorktreeExcludeManager.WorktreeExcludeManager.__tracked_entries()`
	# @used-by :meth:`Df.Harness.Grounding.BlockLineAuditor.BlockLineAuditor.__check_backtick_and_guillemet_quotes()`
	# @used-by :meth:`Df.Harness.Grounding.BlockLineAuditor.BlockLineAuditor.__check_blockquote()`
	# @used-by :meth:`Df.Harness.Grounding.BlockLineAuditor.BlockLineAuditor.__check_guillemet_quote()`
	# @used-by :meth:`Df.Harness.Grounding.BlockLineAuditor.BlockLineAuditor.audit_lines()`
	# @used-by :meth:`Df.Harness.Grounding.DomainFactExtractor.DomainFactExtractor.extract_domain_entities()`
	# @used-by :meth:`Df.Harness.Grounding.EvidenceBundleIngestor.EvidenceBundleIngestor.__record_direct_payload()`
	# @used-by :meth:`Df.Harness.Grounding.EvidenceBundleIngestor.EvidenceBundleIngestor.__record_topic_entry()`
	# @used-by :meth:`Df.Harness.Grounding.LocaleVerifier.LocaleVerifier.__char_script()`
	# @used-by :meth:`Df.Harness.Grounding.LocaleVerifier.LocaleVerifier.__extract_body_prose()`
	# @used-by :meth:`Df.Harness.Grounding.LocaleVerifier.LocaleVerifier.__locale_to_target()`
	# @used-by :meth:`Df.Harness.Grounding.ResponseAuditor.ResponseAuditor.__check_external_refs()`
	# @used-by :meth:`Df.Harness.Grounding.ResponseAuditor.ResponseAuditor.__extract_inline_block_refs()`
	# @used-by :meth:`Df.Harness.Grounding.ResponseAuditor.ResponseAuditor.is_descriptive_title_label()`
	# @used-by :meth:`Df.Harness.Grounding.Tier0Index.Tier0Index.__match_entry_entities()`
	# @used-by :meth:`Df.Harness.Issue.Linter.Linter.has_enumerated_slop_title()`
	# @used-by :meth:`Df.Harness.Issue.ReadCache.ReadCache.__extract_diff_header_path()`
	# @used-by :meth:`Df.Harness.Issue.ReadCache.ReadCache.__parse_log_index()`
	# @used-by :meth:`Df.Harness.Issue.ReadCache.ReadCache.__read_head_oid()`
	# @used-by :meth:`Df.Harness.Issue.ReadCache.ReadCache.__read_packed_ref()`
	# @used-by :meth:`Df.Harness.Issue.ReadCache.ReadCache.__resolve_git_dir()`
	# @used-by :meth:`Df.Harness.Issue.ReadCache.ReadCache.find_commit_for_issue()`
	# @used-by :meth:`Df.Harness.Issue.ReadCache.ReadCache.parse_porcelain_z_entries()`
	# @used-by :meth:`Df.Harness.Issue.RepoTransferRunner.RepoTransferRunner.transfer()`
	# @used-by :meth:`Df.Harness.Path.CacheStore.CacheStore.__linked_worktree_main_repo()`
	# @used-by :meth:`Df.Harness.Project.DriftAuditor.DriftAuditor.audit()`
	# @used-by :meth:`Df.Harness.Project.LabelStateUpdater.LabelStateUpdater.update()`
	# @used-by :meth:`Df.Harness.Project.LabelValidator.LabelValidator.is_valid_domain()`
	# @used-by :meth:`Df.Harness.Project.RegistrationExpectation.RegistrationExpectation.build()`
	# @used-by :meth:`Df.Harness.Project.Rename.ProjectRenamer.ProjectRenamer.maybe_promote_domain()`
	# @used-by :meth:`Df.Harness.Research.Extractor.Extractor.extract()`
	# @used-by :meth:`Df.Harness.Research.HtmlData.HtmlData.handle_endtag()`
	# @used-by :meth:`Df.Harness.Research.ObservationBundleScanner.ObservationBundleScanner.__scan_raw_json_title()`
	# @used-by :meth:`Df.Harness.Research.ObservationBundleScanner.ObservationBundleScanner.__scan_raw_response()`
	# @used-by :meth:`Df.Harness.Tdd.CommandInspector.CommandInspector.__match_go_or_cargo()`
	# @used-by :meth:`Df.Harness.Tdd.CommandInspector.CommandInspector.__match_python_unittest()`
	# @used-by :meth:`Df.Harness.Tdd.DiffExecutability.DiffExecutability.__git_diff_entries()`
	# @used-by :meth:`Df.Harness.Tdd.DiffExecutability.DiffExecutability.__resolve_range_recipes()`
	# @used-by :meth:`Df.Harness.Tdd.Enforcement.Enforcement.__resolve_worktree_git_dirs()`
	# @used-by :meth:`Df.Harness.Tdd.Evaluator.Evaluator.git_main_repo_root()`
	# @used-by :meth:`Df.Harness.Tdd.OutcomeParser.OutcomeParser.__header_exit_code()`
	# @used-by :meth:`Df.Harness.Tdd.OutcomeParser.OutcomeParser.extract_bg_task_ids()`
	# @used-by :meth:`Df.Harness.Text.Article.GraphAuditor.GraphAuditor.__check_conditional_line()`
	# @used-by :meth:`Df.Harness.Text.MechanicalProjector.MechanicalProjector.__project_prose()`
	# @used-by :meth:`Df.Harness.Text.Proposal.Linter.Linter.check_references()`
	# @used-by :meth:`Df.Harness.Text.Proposal.Parser.Parser.__build_block()`
	# @used-by :meth:`Df.Harness.Text.Proposal.Parser.Parser.parent_name()`
	# @used-by :meth:`Df.Harness.Text.Proposal.Renderer.Renderer.__assign_numbers()`
	# @used-by :meth:`Df.Harness.Text.ResponseChecker.ResponseChecker.__check_against()`
	# @used-by :meth:`Df.Harness.Text.ResponseChecker.ResponseChecker.__similarity()`
	# @used-by :meth:`Df.Harness.Text.WorkspaceScopeChecker.WorkspaceScopeChecker.__permitted_sections()`
	# @used-by :meth:`Df.Harness.Upwork.JobUrlParser.JobUrlParser.extract_upwork_job_url_id()`
	# @used-by :meth:`Df.Harness.Upwork.LoomVideoExtractor.LoomVideoExtractor.parse_webvtt_phrases()`
	# @used-by :meth:`Df.Harness.Upwork.MarkdownTableSanitizer.MarkdownTableSanitizer.__is_heading()`
	# @used-by :meth:`Df.Harness.Upwork.MarkdownTableSanitizer.MarkdownTableSanitizer.split_sentences_one_per_line()`
	# @used-by :meth:`Df.Harness.Upwork.MarkdownTableSanitizer.MarkdownTableSanitizer.structure_job_description()`
	# @used-by :meth:`Df.Harness.Upwork.PdfExtractor.PdfExtractor.__detect_bold_fonts()`
	# @used-by :meth:`Df.Harness.Upwork.ProjectInitializer.ProjectInitializer.__maybe_register()`
	# @used-by :meth:`Df.Harness.Upwork.ProjectInitializer.ProjectInitializer.__run_configure()`
	# @used-by :meth:`Df.Harness.Xref.Java.Graph.Graph.__type_name_candidates()`
	# @used-by :meth:`Df.Harness.Xref.Java.Syncer.Syncer.__expected_java_used_by()`
	# @used-by :meth:`Df.Harness.Xref.Java.Tags.Tags.__resolve_external_java_ref()`
	# @used-by :meth:`Df.Harness.Xref.Java.Tags.Tags.__resolve_repo_java_member()`
	# @used-by :meth:`Df.Harness.Xref.Java.Tags.Tags.__resolve_type_fqn()`
	# @used-by :meth:`Df.Harness.Xref.Java.Tags.Tags.__shorten_java_type()`
	# @used-by :meth:`Df.Harness.Xref.Java.Tags.Tags.format_ref()`
	# @used-by :meth:`Df.Harness.Xref.Java.Tags.Tags.is_valid_external()`
	# @used-by :meth:`Df.Harness.Xref.Java.Tags.Tags.resolve_target()`
	# @used-by :meth:`Df.Harness.Xref.Js.Syncer.Syncer.__expected_js_used_by()`
	# @used-by :meth:`Df.Harness.Xref.Js.Tags.Tags.__format_cross_file_symbol()`
	# @used-by :meth:`Df.Harness.Xref.Js.Tags.Tags.format_ref()`
	# @used-by :meth:`Df.Harness.Xref.Js.Tags.Tags.is_valid_external()`
	# @used-by :meth:`Df.Harness.Xref.Python.Graph.Graph.__follow_reexport()`
	# @used-by :meth:`Df.Harness.Xref.Python.Graph.Graph.__resolve_class_key()`
	# @used-by :meth:`Df.Harness.Xref.Python.Graph.Graph.__resolve_dotted_symbol()`
	# @used-by :meth:`Df.Harness.Xref.Python.Model.Model.__resolve_relative_module()`
	# @used-by :meth:`Df.Harness.Xref.Python.Model.Model.add_import_node()`
	# @used-by :meth:`Df.Harness.Xref.Python.Overrides.Overrides.__expand_local_alias()`
	# @used-by :meth:`Df.Harness.Xref.Python.Overrides.Overrides.__load_stdlib_class()`
	# @used-by :meth:`Df.Harness.Xref.Python.Syncer.Syncer.__expected_used_by_lines()`
	# @used-by :meth:`Df.Harness.Xref.Python.Tags.Tags.__probe_stdlib_parts()`
	# @used-by :meth:`Df.Harness.Xref.Python.Tags.Tags.__resolve_module_attr_in_repo()`
	# @used-by :meth:`Df.Harness.Xref.Python.Tags.Tags.is_valid_external_target()`
	# @used-by :meth:`Df.Harness.Xref.Python.Tags.Tags.resolve_stdlib_symbol()`
	# @used-by :meth:`test_agents_loader.AgentsLoaderTests.test_guidance_uses_current_canonical_loader_without_copying_rule_bodies()`
	# @used-by :meth:`test_cleanup_integration.CleanupIntegrationTests._init_and_register()`
	# @used-by :meth:`test_df_article.SlopDetectionTests.test_orphan_analysis_paragraph_is_reported()`
	# @used-by :meth:`test_df_harness_s11_wave2c_git.DfHarnessS11Wave2CGitTests.test_shell_audit_single_class_modules_and_facade()`
	# @used-by :meth:`test_df_proposal.ProposalTransformTests.test_reordering_moves_child_references_and_keeps_prose()`
	# @used-by :meth:`test_onboarding.InitializationTests.test_concurrent_numbers_and_same_job_are_exclusive()`
	# @used-by :meth:`test_tdd_rules_contract.TddRulesAndDocumentationContractTests.test_failfast_defaults_and_schedule_prohibition_contract()`
	# @used-by :meth:`test_text_browser.TextBrowserTests.test_m2a_extension_manifest_key_and_multi_profile_tab_broker_isolation()`
	# @used-by :meth:`test_text_core.ArticleIntegrityTests.test_used_leaf_does_not_make_unused_sibling_a_premise()`
	def split(self) -> list[str]:
		r: list[str] = []
		curr: list[str] = []
		for m in _TOKEN_RE.finditer(self.__cmd):
			tok = m.group(0)
			if tok not in _SEPARATORS:
				curr.append(tok)
			else:
				seg = ''.join(curr).strip()
				if seg:
					r.append(seg)
				curr = []
		tail = ''.join(curr).strip()
		if tail:
			r.append(tail)
		return r
