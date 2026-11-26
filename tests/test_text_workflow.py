# 2026-10-20 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from copy import deepcopy
from typing import override
import json
import os
from test_agent_tools import TemporaryCase
from test_evidence_contract import claim_metadata, v3_analysis
from agent_tools import text_claims, text_workflow
from agent_tools.claims import claim_digest, claim_index
# @used-by :meth:`TextMapTests.test_limited_claim_rejects_lazy_conditional_qualification()`
# @used-by :meth:`TextMapTests.test_numeric_measurement_cannot_come_from_claim_wording_alone()`
# @used-by :meth:`TextMapTests.test_stale_block_bytes_or_missing_coverage_fail()`
# @used-by :meth:`TextMapTests.test_substantive_paragraph_cannot_be_unmapped_or_unsourced()`
# @used-by :meth:`TextMechanicalScopeTests.test_inspect_never_allows_even_one_word_change()`
# @used-by :meth:`TextMechanicalScopeTests.test_links_can_change_a_destination_but_cannot_change_link_label()`
# @used-by :meth:`TextMechanicalScopeTests.test_links_cannot_rewrite_exact_ascii_source_quote()`
# @used-by :meth:`TextMechanicalScopeTests.test_renumber_cannot_rewrite_a_quoted_section_example()`
# @used-by :meth:`TextMechanicalScopeTests.test_renumber_cannot_rewrite_a_section_symbol_inside_url()`
# @used-by :meth:`TextMechanicalScopeTests.test_renumber_cannot_rewrite_article_heading_text()`
# @used-by :meth:`TextMechanicalScopeTests.test_renumber_cannot_rewrite_plain_prose()`
# @used-by :meth:`TextMechanicalScopeTests.test_renumber_preserves_inline_and_fenced_code()`
# @used-by :meth:`TextTransactionTests.test_changed_protected_file_is_reported_without_restore()`
# @used-by :meth:`test_source_admission.SourceAdmissionTests.test_missing_source_checks_cannot_become_a_valid_mechanical_check()`
# @used-by :meth:`test_text_integration.TextBoundaryTests.test_links_only_allows_url_presentation_but_preserves_crlf_and_anchor_words()`
# @used-by :meth:`test_text_integration.TextBoundaryTests.test_missing_map_is_an_invalid_result_instead_of_a_crash()`
# @used-by :meth:`test_text_integration.TextBoundaryTests.test_renumber_scope_accepts_external_spacing_without_rebinding_its_number()`
# @used-by :meth:`test_text_integration.TextBoundaryTests.test_section_scope_covers_group_headers_and_protects_part_title()`
def codes(result):
	issues = result['issues'] if isinstance(result, dict) else result
	r = {issue['code'] for issue in issues}
	return r
# 2026-10-20
# "Implement /df-article and /df-proposal client-text skills, AI-slop linter, scoped baseline diffs, and semantic § rendering":
# https://github.com/dmitry-ai/harness/issues/13
# 2026-10-31
# "Reorganize AI into universal harness repository, translate rules and documentation to English, format per P.md, and enforce issue-driven Git workflow":
# https://github.com/dmitry-ai/harness/issues/26
class TextWorkspaceCase(TemporaryCase):
	# 2026-11-26
	# "Apply cross-reference annotations across Harness Python and JavaScript":
	# https://github.com/dmitry-ai/harness/issues/305
	# @used-by :meth:`test_source_admission.SourceAdmissionTests.setUp()`
	# @used-by :meth:`test_text_integration.TextReviewTests.setUp()`
	# @used-by :mod:`unittest`
	# @see :meth:`test_agent_tools.TemporaryCase.setUp()`
	@override
	def setUp(self):
		super().setUp()
		self.project = self.root / 'plain-text-workspace'
		self.project.mkdir()
	# @used-by :meth:`TextClaimRevisionTests.test_a_self_authored_note_is_not_a_native_reassessment_of_changed_evidence()`
	# @used-by :meth:`TextTransactionTests.test_begin_never_overwrites_a_protected_previous_draft()`
	# @used-by :meth:`TextTransactionTests.test_changed_protected_file_is_reported_without_restore()`
	# @used-by :meth:`TextTransactionTests.test_formatter_cannot_overwrite_a_document_protected_by_the_operation()`
	# @used-by :meth:`TextTransactionTests.test_target_indirection_created_after_capture_cannot_redirect_apply()`
	# @used-by :meth:`TextTransactionTests.test_unregistered_candidate_output_requires_cas_and_keeps_history()`
	# @used-by :meth:`TextWorkspaceCase.start()`
	# @used-by :meth:`test_historical_admission.HistoricalAdmissionTests.check_and_review()`
	# @used-by :meth:`test_source_admission.SourceAdmissionTests.test_full_native_review_fixture_requires_and_preserves_source_assessments()`
	# @used-by :meth:`test_source_admission.SourceAdmissionTests.test_real_http_failure_and_redirect_are_saved_once_per_base_url()`
	# @used-by :meth:`test_source_admission.SourceAdmissionTests.test_source_check_cli_preserves_success_and_failed_receipts_with_exit_codes()`
	# @used-by :meth:`test_text_integration.TextBoundaryTests.test_cli_proposal_profile_and_fields_have_real_exit_status()`
	# @used-by :meth:`test_text_integration.TextReviewTests.record_fixture()`
	def project_file(self, relative, text):
		path = self.project / relative
		path.parent.mkdir(parents=True, exist_ok=True)
		path.write_bytes(text.encode('utf-8'))
		r = path
		return r
	# @used-by :func:`agent_tools.text_cli.main()`
	# @used-by :meth:`TextClaimRevisionTests.test_a_self_authored_note_is_not_a_native_reassessment_of_changed_evidence()`
	# @used-by :meth:`TextClaimRevisionTests.test_changed_primary_bytes_invalidate_an_existing_semantic_check()`
	# @used-by :meth:`TextClaimRevisionTests.test_primary_revision_marks_all_transitive_dependents_stale_and_archives_old_bytes()`
	# @used-by :meth:`TextClaimRevisionTests.test_registry_compare_and_swap_never_overwrites_manual_revision()`
	# @used-by :meth:`TextMapTests.test_limited_claim_rejects_lazy_conditional_qualification()`
	# @used-by :meth:`TextMapTests.test_numeric_measurement_cannot_come_from_claim_wording_alone()`
	# @used-by :meth:`TextMapTests.test_stale_block_bytes_or_missing_coverage_fail()`
	# @used-by :meth:`TextMapTests.test_standalone_proposal_map_needs_no_five_analysis_stages()`
	# @used-by :meth:`TextTransactionTests.test_propose_creates_reviewable_candidate_without_writing_target()`
	# @used-by :meth:`test_text_integration.TextReviewTests.setUp()`
	def registry(self, value=None):
		if None is value:
			captured = v3_analysis(self.project)
			value = {'schema_version': 3, 'facts': captured['facts']}
		r = (text_claims.save_registry(self.project, value), value)
		return r
	# @used-by :func:`agent_tools.article.check_link_style()`
	# @used-by :func:`agent_tools.article.check_structure()`
	# @used-by :func:`agent_tools.claims._quantity_matches()`
	# @used-by :func:`agent_tools.code_size_gate._code_lines_and_semicolons()`
	# @used-by :func:`agent_tools.code_style_gate._scan_tokens()`
	# @used-by :func:`agent_tools.grounding_domains.extract_fact_tuples()`
	# @used-by :func:`agent_tools.grounding_domains.ticket_message_issues()`
	# @used-by :func:`agent_tools.issue_comment_gate._trailing_comment_urls()`
	# @used-by :func:`agent_tools.knowledge._replace_section2_in_project_md()`
	# @used-by :func:`agent_tools.links.parse_markdown_headings()`
	# @used-by :func:`agent_tools.native_profiles._profile_agents()`
	# @used-by :func:`agent_tools.research._grep_section_windows()`
	# @used-by :func:`agent_tools.research.extract_markdown()`
	# @used-by :func:`agent_tools.scatter_banner._has_unnegated_match()`
	# @used-by :func:`agent_tools.scatter_banner._proposal_slice()`
	# @used-by :func:`agent_tools.tdd.comment_lexers_c.lex_php()`
	# @used-by :func:`agent_tools.tdd.comment_lexers_c.lex_python()`
	# @used-by :func:`agent_tools.tdd.comment_lexers_markup._consume_astro_frontmatter()`
	# @used-by :func:`agent_tools.tdd.comment_lexers_markup.lex_sfc()`
	# @used-by :func:`agent_tools.tdd.mechanical._consume_partial_match()`
	# @used-by :func:`agent_tools.text_core._excerpt()`
	# @used-by :func:`agent_tools.text_core.bold_spans()`
	# @used-by :func:`agent_tools.text_core.check_response()`
	# @used-by :func:`agent_tools.text_core.prose_spans()`
	# @used-by :func:`agent_tools.text_core.reference_document()`
	# @used-by :func:`agent_tools.text_core.sentences()`
	# @used-by :func:`agent_tools.text_sections.content_blocks()`
	# @used-by :func:`agent_tools.upwork_data.discover_pdf_ligature_repairs()`
	# @used-by :meth:`TextClaimRevisionTests.test_changed_primary_bytes_invalidate_an_existing_semantic_check()`
	# @used-by :meth:`TextMapTests.test_limited_claim_rejects_lazy_conditional_qualification()`
	# @used-by :meth:`TextMapTests.test_standalone_proposal_map_needs_no_five_analysis_stages()`
	# @used-by :meth:`TextTransactionTests.test_begin_never_overwrites_a_protected_previous_draft()`
	# @used-by :meth:`TextTransactionTests.test_changed_protected_file_is_reported_without_restore()`
	# @used-by :meth:`TextTransactionTests.test_direct_write_bypass_never_acquires_a_valid_receipt()`
	# @used-by :meth:`TextTransactionTests.test_formatter_cannot_overwrite_a_document_protected_by_the_operation()`
	# @used-by :meth:`TextTransactionTests.test_manual_change_after_check_preserves_the_users_new_bytes()`
	# @used-by :meth:`TextTransactionTests.test_propose_creates_reviewable_candidate_without_writing_target()`
	# @used-by :meth:`TextTransactionTests.test_registered_target_cannot_be_overwritten_via_formatter()`
	# @used-by :meth:`TextTransactionTests.test_successful_mechanical_apply_has_a_receipt_and_preserves_original()`
	# @used-by :meth:`TextTransactionTests.test_target_indirection_created_after_capture_cannot_redirect_apply()`
	# @used-by :meth:`TextTransactionTests.test_workspace_and_integrity_verifier_single_pass_invariants()`
	# @used-by :meth:`agent_tools.issues.linter.IssueMarkdownLinter.has_enumerated_slop_title()`
	# @used-by :meth:`agent_tools.shell_audit.ShellCommandInspector.extract_issue_actions()`
	# @used-by :meth:`test_agent_tools.LinkTests.test_real_http_redirect_anchor_and_404()`
	# @used-by :meth:`test_analysis_workflow.MetricsTests.test_collect_http_positional_batch_extract_profile_and_14_url_evidence_query()`
	# @used-by :meth:`test_analysis_workflow.ResearchTests.test_real_get_and_cross_origin_redirect_strip_authentication()`
	# @used-by :meth:`test_context_and_storage_determinism.ContextAndStorageDeterminismTests.test_locked_create_on_held_zero_byte_lock_waits_without_permission_error()`
	# @used-by :meth:`test_historical_admission.HistoricalAdmissionTests.test_unrelated_registry_revision_and_target_do_not_invalidate_selected_history()`
	# @used-by :meth:`test_landing_lease.LandingLeaseTests.test_fifo_ordering_prevents_starvation()`
	# @used-by :meth:`test_optimistic_worktree_land.OptimisticWorktreeLandTests.test_targeted_wait_blocks_when_turn_touches_leased_repo_or_worktree()`
	# @used-by :meth:`test_path_cache_and_diff_cov_perf.PathCacheAndDiffCovPerfTests.test_path_cache_rlock_handles_concurrent_eviction_and_clear()`
	# @used-by :meth:`test_repo_wait_and_retry.RepoWaitAndRetryTests.test_wait_repo_reacts_to_lease_release_dead_pid_and_clean_tree()`
	# @used-by :meth:`test_review_target_claim_and_wait_m5.ReviewTargetClaimAndWaitM5Tests.test_native_review_proof_retryable_flag_and_bounded_wait_for_final_response()`
	# @used-by :meth:`test_source_admission.SourceAdmissionTests.setUp()`
	# @used-by :meth:`test_source_admission.SourceAdmissionTests.test_real_http_failure_and_redirect_are_saved_once_per_base_url()`
	# @used-by :meth:`test_text_browser.TextBrowserTests.test_m1_live_headless_shell_public_isolation_and_h_chs_6_static_skip()`
	# @used-by :meth:`test_text_browser.TextBrowserTests.test_read_only_cdp_expressions_live_headless_shell_contract()`
	# @used-by :meth:`test_text_browser.TextBrowserTests.test_session_lock_serializes_preflight_with_its_action()`
	# @used-by :meth:`test_text_integration.TextBoundaryTests.test_links_only_allows_url_presentation_but_preserves_crlf_and_anchor_words()`
	# @used-by :meth:`test_text_integration.TextBoundaryTests.test_matching_request_blocks_direct_write_but_unrelated_journal_is_allowed()`
	# @used-by :meth:`test_text_integration.TextBoundaryTests.test_missing_map_is_an_invalid_result_instead_of_a_crash()`
	# @used-by :meth:`test_text_integration.TextReviewTests.setUp()`
	# @used-by :meth:`test_turn_completion.AntigravityAddonsIntegrationTests.test_antigravity_journal_conversation_auto_titling_and_comma_append()`
	def start(self, base='1. The captured page contains the concern.\n', **overrides):
		relative = overrides.get('target', 'result/EN/proposal.md')
		target = self.project_file(relative, base)
		spec = {'kind': 'proposal', 'mode': 'edit', 'changes': 'prose', 'target': relative, 'goal': 'Explain the observed page content.', 'requests': ['Revise the specified proposal only.']}
		spec.update(overrides)
		r = (target, text_workflow.begin(self.project, spec))
		return r
	# @used-by :meth:`TextClaimRevisionTests.test_changed_primary_bytes_invalidate_an_existing_semantic_check()`
	# @used-by :meth:`TextMapTests.test_explicit_offer_can_be_nonfactual_without_a_registry()`
	# @used-by :meth:`TextMapTests.test_limited_claim_rejects_lazy_conditional_qualification()`
	# @used-by :meth:`TextMapTests.test_numeric_measurement_cannot_come_from_claim_wording_alone()`
	# @used-by :meth:`TextMapTests.test_stale_block_bytes_or_missing_coverage_fail()`
	# @used-by :meth:`TextMapTests.test_standalone_proposal_map_needs_no_five_analysis_stages()`
	# @used-by :meth:`TextMapTests.test_substantive_paragraph_cannot_be_unmapped_or_unsourced()`
	# @used-by :meth:`TextTransactionTests.test_propose_creates_reviewable_candidate_without_writing_target()`
	# @used-by :meth:`test_source_admission.SourceAdmissionTests.test_full_native_review_fixture_requires_and_preserves_source_assessments()`
	# @used-by :meth:`test_text_integration.TextReviewTests.setUp()`
	# @used-by :meth:`test_text_integration.TextReviewTests.test_map_change_does_not_inherit_an_old_check_approval()`
	# @used-by :meth:`test_text_integration.TextReviewTests.test_same_rejected_subject_cannot_be_reset_by_a_new_operation_path()`
	def manifest(self, text, *, kind='proposal', ids=('F-PRIMARY-1',), role='observation'):
		return {'schema_version': 1, 'registry': 'ꘖ/KB/TextClaims.json', 'blocks': [{'key': 'text-' + str(index), 'section': block['section'], 'text_sha256': text_claims.digest(block['text'].encode()), 'role': role, 'goal_basis': 'The requested answer concerns this observed content.', 'new_content': 'This point adds the captured page content.', 'claim_ids': list(ids), **({'nonfactual_basis': 'Exact commercial offer, not a claim about an observed system.'} if 'nonfactual' == role else {})} for index, block in enumerate(text_claims.blocks(text, kind), 1)]}
class TextMapTests(TextWorkspaceCase):
	# @used-by :mod:`unittest`
	def test_standalone_proposal_map_needs_no_five_analysis_stages(self):
		self.registry()
		candidate = '1. The captured page contains the concern.\n'
		target, op = self.start()
		result = text_workflow.check(self.project, op['id'], candidate, self.manifest(candidate))
		self.assertTrue(result['valid'], result['issues'])
		self.assertTrue((self.project / 'ꘖ/data/text-project.json').is_file())
		self.assertFalse((self.project / 'ꘖ/project.json').exists())
		self.assertFalse((self.project / 'ꘖ/KB/Analysis.json').exists())
		self.assertEqual(result['claim_versions'].keys(), {'F-PRIMARY-1'})
		self.assertEqual(target.read_text(encoding='utf-8'), candidate)
	# 2026-10-22
	# "Ban conditional conjunctions in limited claim qualifications and isolate closed admin access from proven public storefront facts":
	# https://github.com/dmitry-ai/harness/issues/15
	# @used-by :mod:`unittest`
	def test_limited_claim_rejects_lazy_conditional_qualification(self):
		captured = v3_analysis(self.project)
		captured['facts'][0]['verification_status'] = 'limited'
		captured['facts'][0]['missing_checks'] = ['Verify on mobile viewport.']
		self.registry({'schema_version': 3, 'facts': captured['facts']})
		candidate = '1. The captured page contains the concern if valid.\n'
		target, op = self.start()
		manifest = self.manifest(candidate)
		manifest['blocks'][0]['qualification'] = 'if'
		result = text_workflow.check(self.project, op['id'], candidate, manifest)
		self.assertFalse(result['valid'])
		self.assertIn('text.qualification_lazy', codes(result))
		candidate_ok = '1. The captured page contains the concern for desktop-only.\n'
		manifest_ok = self.manifest(candidate_ok)
		manifest_ok['blocks'][0]['qualification'] = 'desktop-only'
		result_ok = text_workflow.check(self.project, op['id'], candidate_ok, manifest_ok)
		self.assertTrue(result_ok['valid'], result_ok['issues'])
	# @used-by :mod:`unittest`
	def test_map_includes_proposal_continuations_and_literal_evidence(self):
		candidate = '1. The captured page contains the concern.\nThe captured page also contains Alternative.\n```text\nThe concern\n```\n\n2. The next point follows.\n'
		blocks = text_claims.blocks(candidate, 'proposal')
		self.assertEqual([block['section'] for block in blocks], ['1', '2'])
		self.assertIn('The captured page also contains Alternative.', blocks[0]['text'])
		self.assertIn('```text\nThe concern\n```', blocks[0]['text'])
		self.assertIn('The captured page also contains Alternative.', blocks[0]['prose'])
	# @used-by :mod:`unittest`
	def test_article_grouping_node_does_not_duplicate_its_child_claim(self):
		candidate = '# I. Analysis\n## 1\n<a name="I.1"></a>\n### 1.1\n<a name="I.1.1"></a>\nThe concern is present.\n# II. Recommendations\n## 1\n<a name="II.1"></a>\n**[§I.1.1](#I.1.1)** → inspect the captured page.\n'
		mapped = text_claims.blocks(candidate, 'article')
		self.assertEqual([block['section'] for block in mapped], ['I.1.1', 'II.1'])
	# @used-by :mod:`unittest`
	def test_stale_block_bytes_or_missing_coverage_fail(self):
		self.registry()
		original = '1. The captured page contains the concern.\n'
		manifest = self.manifest(original)
		changed = '1. The captured page contains Alternative.\n'
		self.assertIn('text.block_version', codes(text_claims.validate_map(self.project, changed, 'proposal', manifest)))
		manifest['blocks'] = []
		self.assertIn('text.coverage', codes(text_claims.validate_map(self.project, original, 'proposal', manifest)))
	# @used-by :mod:`unittest`
	def test_substantive_paragraph_cannot_be_unmapped_or_unsourced(self):
		candidate = '1. The page contains a claim.\n'
		result = text_claims.validate_map(self.project, candidate, 'proposal', self.manifest(candidate, ids=()))
		self.assertIn('text.unsourced', codes(result))
	# @used-by :mod:`unittest`
	def test_explicit_offer_can_be_nonfactual_without_a_registry(self):
		candidate = '1. Fix the listener for $50.\n'
		result = text_claims.validate_map(self.project, candidate, 'proposal', self.manifest(candidate, ids=(), role='nonfactual'))
		self.assertTrue(result['valid'], result['issues'])
		self.assertFalse((self.project / 'ꘖ/KB/TextClaims.json').exists())
	# @used-by :mod:`unittest`
	def test_numeric_measurement_cannot_come_from_claim_wording_alone(self):
		self.registry()
		candidate = '1. The captured page contains 47 records.\n'
		result = text_claims.validate_map(self.project, candidate, 'proposal', self.manifest(candidate))
		self.assertIn('text.number', codes(result))
class TextTransactionTests(TextWorkspaceCase):
	# @used-by :mod:`unittest`
	def test_propose_creates_reviewable_candidate_without_writing_target(self):
		self.registry()
		original = '1. The captured page contains the concern.\n'
		target, op = self.start(original, mode='propose')
		candidate = '1. The captured page contains Alternative.\n'
		checked = text_workflow.check(self.project, op['id'], candidate, self.manifest(candidate))
		self.assertTrue(checked['valid'], checked['issues'])
		self.assertEqual(target.read_bytes(), original.encode())
		self.assertTrue((self.project / checked['candidate']).is_file())
		with self.assertRaisesRegex(ValueError, 'proposes/inspects'):
			text_workflow.apply(self.project, checked['check'])
		self.assertEqual(target.read_bytes(), original.encode())
	# @used-by :mod:`unittest`
	def test_manual_change_after_check_preserves_the_users_new_bytes(self):
		target, op = self.start('1. The queue refers to §3.\n\n3. The handler runs.\n', changes='renumber')
		candidate = '1. The queue refers to §2.\n\n2. The handler runs.\n'
		checked = text_workflow.check(self.project, op['id'], candidate)
		self.assertTrue(checked['valid'], checked['issues'])
		manual = b'1. User rewrote this while the agent reviewed its candidate.\n'
		target.write_bytes(manual)
		with self.assertRaisesRegex(ValueError, 'stale|conflict|failed'):
			text_workflow.apply(self.project, checked['check'])
		self.assertEqual(target.read_bytes(), manual)
	# @used-by :mod:`unittest`
	def test_changed_protected_file_is_reported_without_restore(self):
		protected = self.project_file('result/EN/draft.working.md', 'User original\n')
		target, op = self.start(changes='renumber', protected=['result/EN/draft.working.md'])
		protected.write_bytes(b'User is now editing this protected document.\n')
		checked = text_workflow.check(self.project, op['id'], target.read_text(encoding='utf-8'))
		self.assertIn('text.protected', codes(checked))
		self.assertEqual(protected.read_bytes(), b'User is now editing this protected document.\n')
		with self.assertRaises(ValueError):
			text_workflow.apply(self.project, checked['check'])
		self.assertEqual(protected.read_bytes(), b'User is now editing this protected document.\n')
	# @used-by :mod:`unittest`
	def test_begin_never_overwrites_a_protected_previous_draft(self):
		protected = self.project_file('result/EN/draft.prev.md', 'User preserved a different baseline.\n')
		before = protected.read_bytes()
		try:
			self.start(target='result/EN/draft.md', protected=['result/EN/draft.prev.md'])
		except ValueError:
			pass
		self.assertEqual(protected.read_bytes(), before)
	# @used-by :mod:`unittest`
	def test_successful_mechanical_apply_has_a_receipt_and_preserves_original(self):
		original = '1. The queue refers to §3.\n\n3. The handler runs.\n'
		target, op = self.start(original, changes='renumber')
		candidate = '1. The queue refers to §2.\n\n2. The handler runs.\n'
		checked = text_workflow.check(self.project, op['id'], candidate)
		applied = text_workflow.apply(self.project, checked['check'])
		self.assertEqual(target.read_text(encoding='utf-8'), candidate)
		self.assertTrue((self.project / applied['receipt']).is_file())
		self.assertEqual(text_workflow.operation(self.project, op['id'])[1], original.encode())
		self.assertTrue(text_workflow.gate(self.project)['valid'])
		with self.assertRaisesRegex(ValueError, 'semantic publication'):
			text_workflow.gate(self.project, publication=True)
	# @used-by :mod:`unittest`
	def test_registered_target_cannot_be_overwritten_via_formatter(self):
		target, _ = self.start()
		before = target.read_bytes()
		with self.assertRaisesRegex(ValueError, 'Registered text target'):
			text_workflow.write_candidate_output(target, b'Replacement', expected_sha256=text_claims.digest(before))
		self.assertEqual(target.read_bytes(), before)
	# @used-by :mod:`unittest`
	def test_formatter_cannot_overwrite_a_document_protected_by_the_operation(self):
		protected = self.project_file('result/EN/draft.working.md', 'User original\n')
		self.start(protected=['result/EN/draft.working.md'])
		before = protected.read_bytes()
		with self.assertRaisesRegex(ValueError, 'protected|Protected|Registered'):
			text_workflow.write_candidate_output(protected, b'Agent overwrote it.\n', expected_sha256=text_claims.digest(before))
		self.assertEqual(protected.read_bytes(), before)
	# @used-by :mod:`unittest`
	def test_target_indirection_created_after_capture_cannot_redirect_apply(self):
		original = '1. See https://example.org/original\n'
		protected = self.project_file('result/EN/draft.working.md', original)
		target, op = self.start(original, changes='links', protected=['result/EN/draft.working.md'])
		target.unlink()
		try:
			os.symlink(protected, target)
		except OSError as exc:
			self.skipTest('Host does not permit test symlink creation: ' + str(exc))
		candidate = '1. See https://example.org/replacement\n'
		try:
			checked = text_workflow.check(self.project, op['id'], candidate)
			text_workflow.apply(self.project, checked['check'])
		except ValueError:
			self.assertEqual(protected.read_bytes(), original.encode())
			return
		self.fail('The changed target indirection let apply overwrite the protected file')
	# @used-by :mod:`unittest`
	def test_unregistered_candidate_output_requires_cas_and_keeps_history(self):
		output = self.project_file('scratch/candidate.md', 'Initial candidate\n')
		before = output.read_bytes()
		with self.assertRaisesRegex(ValueError, 'expected-sha256'):
			text_workflow.write_candidate_output(output, b'Changed candidate\n')
		self.assertEqual(output.read_bytes(), before)
		receipt = text_workflow.write_candidate_output(output, b'Changed candidate\n', expected_sha256=text_claims.digest(before))
		self.assertEqual(receipt['kind'], 'candidate')
		self.assertFalse(receipt['publication_approved'])
		self.assertEqual(output.read_bytes(), b'Changed candidate\n')
	# @used-by :mod:`unittest`
	def test_direct_write_bypass_never_acquires_a_valid_receipt(self):
		target, _ = self.start()
		target.write_bytes(b'1. Direct shell overwrite.\n')
		with self.assertRaisesRegex(ValueError, 'without a current apply receipt'):
			text_workflow.gate(self.project)
	# 2026-11-14
	# "Decompose text_workflow.py into ClientTextWorkspace and TextIntegrityVerifier classes":
	# https://github.com/dmitry-ai/harness/issues/78
	# @used-by :mod:`unittest`
	def test_workspace_and_integrity_verifier_single_pass_invariants(self):
		from unittest.mock import patch
		original = '1. The queue refers to §3.\n\n3. The handler runs.\n'
		_, op = self.start(original, changes='renumber', requests=['req-78-a'])
		ws = text_workflow.ClientTextWorkspace(self.project)
		self.assertEqual(op['id'], ws.operation_meta(op['id'])['id'])
		candidate = '1. The queue refers to §2.\n\n2. The handler runs.\n'
		scope_calls = []
		orig_scope = text_workflow.ClientTextWorkspace.scope_issues
		# @used-by :meth:`TextTransactionTests.test_workspace_and_integrity_verifier_single_pass_invariants()`
		def spy_scope(o, b, c):
			scope_calls.append(o['id'])
			return orig_scope(o, b, c)
		with patch.object(text_workflow.ClientTextWorkspace, 'scope_issues', staticmethod(spy_scope)):
			checked = ws.check(op['id'], candidate)
		self.assertEqual([op['id']], scope_calls)
		ws.apply(checked['check'])
		base_bin = ws.folder / 'operations' / op['id'] / 'base.bin'
		orig_read_bytes = type(base_bin).read_bytes
		# @used-by :meth:`TextTransactionTests.test_workspace_and_integrity_verifier_single_pass_invariants()`
		def forbid_base_read(p):
			if p.resolve() == base_bin.resolve():
				raise AssertionError('gate_requests must not read base.bin')
			return orig_read_bytes(p)
		with patch.object(type(base_bin), 'read_bytes', forbid_base_read):
			gated = text_workflow.gate_requests([self.project], ['req-78-a'], 'Done.', capture=False)
		self.assertEqual(1, len(gated))
		self.assertTrue(gated[0]['valid'])
		verifier = text_workflow.TextIntegrityVerifier(ws)
		snap = verifier.snapshot(ws.index()['targets'])
		self.assertEqual('original_admitted_artifacts', verifier.verify(snap)['scope'])
class TextMechanicalScopeTests(TextWorkspaceCase):
	# @used-by :func:`agent_tools.cli_domains._op_collect_browser()`
	# @used-by :func:`agent_tools.cli_domains._op_collect_http()`
	# @used-by :meth:`TextMechanicalScopeTests.test_links_can_change_a_destination_but_cannot_change_link_label()`
	# @used-by :meth:`TextMechanicalScopeTests.test_links_cannot_rewrite_exact_ascii_source_quote()`
	# @used-by :meth:`TextMechanicalScopeTests.test_renumber_cannot_rewrite_a_quoted_section_example()`
	# @used-by :meth:`TextMechanicalScopeTests.test_renumber_cannot_rewrite_a_section_symbol_inside_url()`
	# @used-by :meth:`TextMechanicalScopeTests.test_renumber_cannot_rewrite_article_heading_text()`
	# @used-by :meth:`TextMechanicalScopeTests.test_renumber_cannot_rewrite_plain_prose()`
	# @used-by :meth:`TextMechanicalScopeTests.test_renumber_preserves_inline_and_fenced_code()`
	def scope(self, base, candidate, *, kind='proposal', changes='renumber'):
		operation = {'kind': kind, 'mode': 'edit', 'changes': changes, 'allow_sections': []}
		r = text_workflow.scope_issues(operation, base.encode(), candidate)
		return r
	# @used-by :mod:`unittest`
	def test_renumber_cannot_rewrite_plain_prose(self):
		base = '1. The form exists.\n3. It sends an event.\n'
		candidate = '1. The form was deleted.\n2. It sends an event.\n'
		self.assertIn('text.scope', codes(self.scope(base, candidate)))
	# @used-by :mod:`unittest`
	def test_renumber_cannot_rewrite_article_heading_text(self):
		base = '# I. Analysis\n## 1. The page loads\n<a name="I.1"></a>\nThe concern is present.\n'
		candidate = '# I. Analysis\n## 1. The payment system leaks data\n<a name="I.1"></a>\nThe concern is present.\n'
		self.assertIn('text.scope', codes(self.scope(base, candidate, kind='article')))
	# @used-by :mod:`unittest`
	def test_renumber_cannot_rewrite_a_quoted_section_example(self):
		base = '1. The source says "§1 is the original example".\n'
		candidate = '2. The source says "§2 is the original example".\n'
		self.assertIn('text.scope', codes(self.scope(base, candidate)))
	# @used-by :mod:`unittest`
	def test_renumber_cannot_rewrite_a_section_symbol_inside_url(self):
		base = '1. The endpoint is https://example.org/§1\n'
		candidate = '2. The endpoint is https://example.org/§2\n'
		self.assertIn('text.scope', codes(self.scope(base, candidate)))
	# @used-by :mod:`unittest`
	def test_renumber_preserves_inline_and_fenced_code(self):
		base = '1. The literal is `§1`.\n```js\nconst ref = "§1";\n```\n'
		for candidate in (base.replace('`§1`', '`§2`'), base.replace('"§1"', '"§2"')):
			self.assertIn('text.scope', codes(self.scope(base, candidate)))
	# @used-by :mod:`unittest`
	def test_links_can_change_a_destination_but_cannot_change_link_label(self):
		base = '1. Read [the documentation](https://example.org/old).\n'
		good = '1. Read [the documentation](https://example.org/new).\n'
		bad = '1. Read [the website leaks payment data](https://example.org/new).\n'
		self.assertEqual(self.scope(base, good, kind='article', changes='links'), [])
		self.assertIn('text.scope', codes(self.scope(base, bad, kind='article', changes='links')))
	# @used-by :mod:`unittest`
	def test_links_cannot_rewrite_exact_ascii_source_quote(self):
		base = '1. The source says "Use https://example.org/original".\n'
		candidate = '1. The source says "Use https://example.org/replacement".\n'
		self.assertIn('text.scope', codes(self.scope(base, candidate, changes='links')))
	# @used-by :mod:`unittest`
	def test_inspect_never_allows_even_one_word_change(self):
		op = {'kind': 'proposal', 'mode': 'inspect', 'changes': 'prose', 'allow_sections': []}
		issues = text_workflow.scope_issues(op, b'1. The form exists.\n', '1. The form changed.\n')
		self.assertIn('text.inspect_write', codes(issues))
class TextClaimRevisionTests(TextWorkspaceCase):
	# @used-by :meth:`TextClaimRevisionTests.test_a_self_authored_note_is_not_a_native_reassessment_of_changed_evidence()`
	# @used-by :meth:`TextClaimRevisionTests.test_primary_revision_marks_all_transitive_dependents_stale_and_archives_old_bytes()`
	def dependent_registry(self):
		captured = v3_analysis(self.project)
		fact = captured['facts'][0]
		second = claim_metadata('F-DEPENDENT-1')
		second.update(essence='The first dependent text refers to the captured content.', evidence=[], derived_from=[{'claim_id': fact['id'], 'sha256': claim_digest(fact)}])
		third = claim_metadata('F-DEPENDENT-2')
		third.update(essence='The second dependent text refers to the first conclusion.', evidence=[], derived_from=[{'claim_id': second['id'], 'sha256': claim_digest(second)}])
		r = {'schema_version': 3, 'facts': [fact, second, third]}
		return r
	# @used-by :mod:`unittest`
	def test_primary_revision_marks_all_transitive_dependents_stale_and_archives_old_bytes(self):
		value = self.dependent_registry()
		saved, _ = self.registry(value)
		original = (self.project / saved['registry']).read_bytes()
		changed = deepcopy(value)
		changed['facts'][0]['essence'] = 'The captured page includes Alternative.'
		updated = text_claims.save_registry(self.project, changed, expected_sha256=saved['sha256'])
		self.assertEqual(updated['invalidated_claims'], ['F-DEPENDENT-1', 'F-DEPENDENT-2'])
		current = json.loads((self.project / updated['registry']).read_text(encoding='utf-8'))
		index = claim_index(current)
		for ident in updated['invalidated_claims']:
			self.assertEqual(index[ident]['verification_status'], 'stale')
			self.assertTrue(index[ident]['missing_checks'])
			self.assertTrue(index[ident]['superseded_dependencies'])
		archive = self.project / 'ꘖ/data/text-claim-history' / (text_claims.digest(original) + '.json')
		self.assertEqual(archive.read_bytes(), original)
	# @used-by :mod:`unittest`
	def test_registry_compare_and_swap_never_overwrites_manual_revision(self):
		saved, value = self.registry()
		path = self.project / saved['registry']
		manual = path.read_bytes() + b'\n'
		path.write_bytes(manual)
		value['facts'][0]['essence'] = 'A revised claim.'
		with self.assertRaisesRegex(ValueError, 'registry changed'):
			text_claims.save_registry(self.project, value, expected_sha256=saved['sha256'])
		self.assertEqual(path.read_bytes(), manual)
	# @used-by :mod:`unittest`
	def test_changed_primary_bytes_invalidate_an_existing_semantic_check(self):
		self.registry()
		candidate = '1. The captured page contains the concern.\n'
		_, op = self.start(candidate, mode='propose')
		checked = text_workflow.check(self.project, op['id'], candidate, self.manifest(candidate))
		self.assertTrue(checked['valid'], checked['issues'])
		body = next((path for path in checked['inputs'] if path.endswith('response.bin')))
		(self.project / body).write_bytes(b'The original concern was removed.')
		with self.assertRaisesRegex(ValueError, 'stale|failed'):
			text_workflow.refresh_check(self.project, checked['check'])
	# @used-by :mod:`unittest`
	def test_a_self_authored_note_is_not_a_native_reassessment_of_changed_evidence(self):
		value = self.dependent_registry()
		saved, _ = self.registry(value)
		changed = deepcopy(value)
		changed['facts'][0]['essence'] = 'The captured page includes Alternative.'
		changed['facts'][1]['derived_from'][0]['sha256'] = claim_digest(changed['facts'][0])
		changed['facts'][2]['derived_from'][0]['sha256'] = claim_digest(changed['facts'][1])
		self.project_file('ꘖ/data/my-opinion.txt', 'Everything is still true because I say so.\n')
		reassessments = {claim['id']: {'basis': 'I consider it unchanged.', 'previous_sha256': claim_digest(claim), 'evidence': ['ꘖ/data/my-opinion.txt']} for claim in value['facts'][1:]}
		try:
			updated = text_claims.save_registry(self.project, changed, expected_sha256=saved['sha256'], reassessments=reassessments)
		except ValueError:
			return
		self.assertEqual(updated['invalidated_claims'], ['F-DEPENDENT-1', 'F-DEPENDENT-2'])
