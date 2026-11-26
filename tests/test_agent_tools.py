# 2026-10-11 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import override
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import threading
import unittest
from unittest.mock import patch
SCRIPTS = Path(__file__).resolve().parents[1] / 'scripts'
sys.path.insert(0, str(SCRIPTS))
from agent_tools import journal
from agent_tools.context import assemble, generate, resolve_letter_file, discover_letters
from agent_tools.git_gate import check_commit, commit
from agent_tools.links import Page, check_network, references, validate_content
from agent_tools.snapshot import snapshot_draft
from agent_tools.statements import validate_statements
# 2026-10-11
# "Extract self-contained .agents toolkit, deterministic validation CLI, and rule architecture from wayse.pt":
# https://github.com/dmitry-ai/harness/issues/2
# 2026-10-31
# "Reorganize AI into universal harness repository, translate rules and documentation to English, format per P.md, and enforce issue-driven Git workflow":
# https://github.com/dmitry-ai/harness/issues/26
class TemporaryCase(unittest.TestCase):
	# 2026-11-26
	# "Apply cross-reference annotations across Harness Python and JavaScript":
	# https://github.com/dmitry-ai/harness/issues/305
	# @used-by :meth:`GitTests.setUp()`
	# @used-by :meth:`test_agents_loader.AgentsLoaderTests.setUp()`
	# @used-by :meth:`test_analysis_workflow.ProjectCase.setUp()`
	# @used-by :meth:`test_cleanup.CleanupTests.setUp()`
	# @used-by :meth:`test_cleanup_audit.CleanupAuditTests.setUp()`
	# @used-by :meth:`test_cleanup_integration.CleanupIntegrationTests.setUp()`
	# @used-by :meth:`test_cleanup_lifecycle.CleanupLifecycleTests.setUp()`
	# @used-by :meth:`test_evidence_contract.ClaimGraphValidatorTests.setUp()`
	# @used-by :meth:`test_evidence_contract.EvidenceContractTests.setUp()`
	# @used-by :meth:`test_instances_config.RuntimeInstancesTests.setUp()`
	# @used-by :meth:`test_intake.IntakeTests.setUp()`
	# @used-by :meth:`test_native_profiles.NativeProfileTests.setUp()`
	# @used-by :meth:`test_portability.ProjectionTests.setUp()`
	# @used-by :meth:`test_readable_links.ReadableReferenceTests.setUp()`
	# @used-by :meth:`test_red_flags.RedFlagTests.setUp()`
	# @used-by :meth:`test_registration_portability.RegistrationProfileTests.setUp()`
	# @used-by :meth:`test_registration_portability.RegistrationTests.setUp()`
	# @used-by :meth:`test_text_workflow.TextWorkspaceCase.setUp()`
	# @used-by :meth:`unittest.TestCase.setUp()`
	# @used-by :mod:`unittest`
	# @see :meth:`unittest.TestCase.setUp()`
	@override
	def setUp(self):
		self.temp = tempfile.TemporaryDirectory()
		self.addCleanup(self.temp.cleanup)
		self.root = Path(self.temp.name)
	# @used-by :meth:`ContextTests.test_default_context_config_includes_agent_kb_and_excludes_evidence_subfolder()`
	# @used-by :meth:`ContextTests.test_empty_final_never_falls_back_to_draft()`
	# @used-by :meth:`ContextTests.test_final_without_draft_and_new_year_nested_letters()`
	# @used-by :meth:`ContextTests.test_generate_context_cli_supports_positional_root_and_default_config()`
	# @used-by :meth:`ContextTests.test_missing_input_fails_and_dry_run_writes_nothing()`
	# @used-by :meth:`ContextTests.test_output_cannot_overwrite_input_or_escape_root()`
	# @used-by :meth:`ContextTests.test_sources_and_fences_preserved_in_configured_order()`
	# @used-by :meth:`GitTests.setUp()`
	# @used-by :meth:`GitTests.test_unrelated_staged_change_is_rejected()`
	# @used-by :meth:`GitTests.test_unstaged_change_rejected_and_explicit_commit_works()`
	# @used-by :meth:`JournalTests.test_existing_same_request_is_not_ownership()`
	# @used-by :meth:`JournalTests.test_explicit_occupied_slot_and_overwrite_rejected()`
	# @used-by :meth:`JournalTests.test_o_journal_20_entry_bucketing_and_partial_range_normalization()`
	# @used-by :meth:`JournalTests.test_recovery_does_not_overwrite_conflict()`
	# @used-by :meth:`JournalTests.test_validation_checks_orphan_res_and_never_scans_neighbor_drafts()`
	# @used-by :meth:`SnapshotTests.test_changed_previous_copy_is_not_silently_replaced()`
	# @used-by :meth:`SnapshotTests.test_current_bytes_preserved_once_per_turn()`
	# @used-by :meth:`StatementTests.test_missing_test_not_masked_by_words_in_statement()`
	# @used-by :meth:`UpworkProjectTests.test_agent_data_dir_prefers_vai_directory()`
	# @used-by :meth:`test_analysis_workflow.MetricsTests.test_unknown_tokens_stay_unknown_and_duplicate_exports_are_not_summed()`
	# @used-by :meth:`test_df_article.ReferenceArticleTests.test_deleted_premise_blocks_rendering_until_dependents_are_resolved()`
	# @used-by :meth:`test_df_article.ResponseTests.test_procedural_filler()`
	# @used-by :meth:`test_df_article.ResponseTests.test_removal_claims_are_checked_against_the_file()`
	# @used-by :meth:`test_df_article.ResponseTests.test_repeated_answer_is_a_signal_only_for_the_later_answer()`
	# @used-by :meth:`test_df_article.SlopDetectionTests.test_cli_exit_codes()`
	# @used-by :meth:`test_df_article.SlopDetectionTests.test_project_bans_are_discovered_from_the_project_root()`
	# @used-by :meth:`test_onboarding.EvidenceTests.test_analysis_links_causes_to_concerns_and_methods_to_causes()`
	# @used-by :meth:`test_onboarding.EvidenceTests.test_cross_file_markdown_anchors_and_missing_file()`
	# @used-by :meth:`test_onboarding.EvidenceTests.test_json_pointer_is_checked()`
	# @used-by :meth:`test_onboarding.EvidenceTests.test_windows_file_uris_and_absolute_paths()`
	# @used-by :meth:`test_onboarding.InitializationTests.test_attachment_evidence_retained_with_hash()`
	# @used-by :meth:`test_onboarding.InitializationTests.test_cli_init_reuses_capture_without_browser()`
	# @used-by :meth:`test_onboarding.InitializationTests.test_existing_neighbor_material_is_untouched()`
	# @used-by :meth:`test_onboarding.IsolationTests.test_incomplete_journal_does_not_replace_context()`
	# @used-by :meth:`test_onboarding.IsolationTests.test_two_drafts_in_one_turn_have_distinct_archives()`
	# @used-by :meth:`test_onboarding.RegistrationTests.test_branch_is_reused_by_parent_and_date_with_other_assignments_preserved()`
	# @used-by :meth:`test_onboarding.RegistrationTests.test_existing_native_file_uri_is_matched_without_replacing_settings()`
	# @used-by :meth:`test_onboarding.RegistrationTests.test_global_install_preserves_other_customizations_and_is_idempotent()`
	# @used-by :meth:`test_onboarding.RegistrationTests.test_global_install_repairs_profile_without_rules_and_merges_missing_hooks()`
	# @used-by :meth:`test_onboarding.RegistrationTests.test_missing_or_wrong_folders_store_does_not_publish_ungrouped_project()`
	# @used-by :meth:`test_onboarding.RegistrationTests.test_parallel_registration_retains_all_assignments()`
	# @used-by :meth:`test_path_registry.PathRegistryTests.test_cross_root_relocation_workflow_completion_review_and_antigravity_registration()`
	# @used-by :meth:`test_path_registry.PathRegistryTests.test_custom_overlay_end_to_end_context_workflow_text_diagnostics_and_completion_canonicalization()`
	# @used-by :meth:`test_path_registry.PathRegistryTests.test_is_tracked_workspace_supports_registered_single_projects_and_declarative_opt_outs()`
	# @used-by :meth:`test_path_registry.PathRegistryTests.test_mid_process_overlay_creation_and_edit_invalidate_reverse_links_and_stay_fast()`
	# @used-by :meth:`test_path_registry.PathRegistryTests.test_project_overlay_dag_cascades_and_remains_isolated_per_project()`
	# @used-by :meth:`test_path_registry.PathRegistryTests.test_similar_projects_groups_symmetric_overlays_affiliated_paths_and_validation()`
	# @used-by :meth:`test_path_registry.PathRegistryTests.test_template_and_schema_error_paths_reject_cycles_unknowns_symlinks_and_conflicts()`
	# @used-by :meth:`test_path_registry.PathRegistryTests.test_transitive_escapes_literal_dollar_in_env_and_relative_slot_anchoring()`
	# @used-by :meth:`test_path_registry.PathRegistryTests.test_v1_journal_only_upgrade_preserves_v1_project_layout_and_historical_receipts()`
	# @used-by :meth:`test_path_registry.PathRegistryTests.test_v2_filesystem_auto_detection_journals_context_provenance_and_migration()`
	# @used-by :meth:`test_readable_links.ReadableReferenceTests.test_cli_readability_check_catches_original_encoding_and_accepts_readable_destination()`
	# @used-by :meth:`test_readable_links.ReadableReferenceTests.test_readable_navigation_links_can_address_a_directory()`
	# @used-by :meth:`test_readable_links.ReadableReferenceTests.test_readable_source_survives_a_renderer_that_encodes_its_href()`
	# @used-by :meth:`test_readable_links.ReadableReferenceTests.test_utf8_anchor_and_balanced_parentheses_need_no_url_encoding()`
	# @used-by :meth:`test_red_flags.RedFlagTests.setUp()`
	# @used-by :meth:`test_red_flags.RedFlagTests.test_legacy_top_block_moves_to_final_first_level_section_without_losing_text()`
	# @used-by :meth:`test_red_flags.RedFlagTests.test_standalone_input_never_updates_project_card()`
	# @used-by :meth:`test_text_core.ArticleIntegrityTests.test_render_diff_never_writes_target_and_force_cannot_publish_invalid_links()`
	# @used-by :meth:`test_text_core.ReplayTests.test_missing_output_uncovered_selector_and_empty_document_are_not_success()`
	# @used-by :meth:`test_text_core.SharedMechanicsTests.test_identical_answer_does_not_prove_nonexecution()`
	def put(self, name, text):
		path = self.root / name
		path.parent.mkdir(parents=True, exist_ok=True)
		path.write_bytes(text.encode('utf-8'))
		r = path
		return r
	# @used-by :meth:`JournalTests.test_no_target_is_not_success()`
	# @used-by :meth:`JournalTests.test_validation_checks_orphan_res_and_never_scans_neighbor_drafts()`
	# @used-by :meth:`test_df_article.ReferenceArticleTests.test_deleted_premise_blocks_rendering_until_dependents_are_resolved()`
	# @used-by :meth:`test_df_article.SlopDetectionTests.test_cli_exit_codes()`
	# @used-by :meth:`test_evidence_contract.EvidenceContractTests.test_malformed_properties_and_dependency_keep_field_diagnostics_in_cli()`
	# @used-by :meth:`test_onboarding.InitializationTests.test_cli_init_reuses_capture_without_browser()`
	# @used-by :meth:`test_readable_links.ReadableReferenceTests.test_cli_readability_check_catches_original_encoding_and_accepts_readable_destination()`
	# @used-by :meth:`test_red_flags.RedFlagTests.test_both_cli_entrypoints_sync_card_and_return_conflicts()`
	# @used-by :meth:`test_text_core.ArticleIntegrityTests.test_render_diff_never_writes_target_and_force_cannot_publish_invalid_links()`
	# @used-by :meth:`test_text_core.ReplayTests.test_missing_output_uncovered_selector_and_empty_document_are_not_success()`
	# @used-by :meth:`test_text_integration.TextBoundaryTests.test_cli_proposal_profile_and_fields_have_real_exit_status()`
	def cli(self, name, *args):
		return subprocess.run([sys.executable, str(SCRIPTS / (name + '.py')), *map(str, args)], cwd=self.root, capture_output=True, encoding='utf-8')
class JournalTests(TemporaryCase):
	# @used-by :mod:`unittest`
	def test_exact_bytes_and_no_keyword_authorization(self):
		req, res = ('  question\r\n\r\n', '[Source](https://www.example.org/a/?q=%20)\n')
		journal_dir = self.root / 'chat'
		step = journal.record_step(journal_dir, req, res)
		self.assertEqual((journal_dir / 'req/1.md').read_bytes(), req.encode())
		self.assertEqual((journal_dir / 'res/1.md').read_bytes(), res.encode())
		self.assertFalse((journal_dir / '.journal').exists())
		self.assertFalse((journal.state_dir(journal_dir) / '1.json').exists())
		self.assertTrue((journal.state_dir(journal_dir) / 'writer.lock').exists())
		self.assertEqual(journal.step_errors(journal_dir, step), [])
	# 2026-11-21
	# "Implement versioned 20-entry journal bucketing and journal-only upgrade engine":
	# https://github.com/dmitry-ai/harness/issues/108
	# @used-by :mod:`unittest`
	def test_o_journal_20_entry_bucketing_and_partial_range_normalization(self):
		self.assertEqual(journal.journal_bucket_name(1), '1\u201320')
		self.assertEqual(journal.journal_bucket_name(20), '1\u201320')
		self.assertEqual(journal.journal_bucket_name(21), '21\u201340')
		self.assertEqual(journal.journal_bucket_name(120), '101\u2013120')
		self.assertEqual(journal.journal_bucket_name(121), '121\u2013140')
		self.assertEqual(journal.journal_bucket_name(140), '121\u2013140')
		self.assertEqual(journal.journal_bucket_name(201), '201\u2013220')
		oj = self.root / '\ua66e'
		self.assertEqual(journal.detect_journal_version(oj), 3)
		s1 = journal.record_step(oj, 'First prompt', 'First answer  \n')
		self.assertEqual(s1, 1)
		self.assertTrue((oj / '\u227b/1\u201320/1.md').is_file())
		self.assertTrue((oj / '\u227a/1\u201320/1.md').is_file())
		s21 = journal.record_step(oj, 'Prompt 21', 'Answer 21  \n', target_step=21)
		self.assertEqual(s21, 21)
		self.assertTrue((oj / '\u227b/21\u201340/21.md').is_file())
		self.assertTrue((oj / '\u227a/21\u201340/21.md').is_file())
		self.assertEqual(journal.get_existing_step_ids(oj), {1, 21})
		self.assertEqual(journal.step_errors(oj, 21), [])
		part = self.root / 'partial_smokeday' / '\ua66e'
		self.put('partial_smokeday/\ua66e/\u227a/101\u2013120/120.md', 'Res 120  \n')
		self.put('partial_smokeday/\ua66e/\u227a/120\u2013140/121.md', 'Res 121  \n')
		self.put('partial_smokeday/\ua66e/\u227a/141.md', 'Res 141  \n')
		self.put('partial_smokeday/\ua66e/\u227b/120.md', 'Req 120')
		self.put('partial_smokeday/\ua66e/\u227b/121.md', 'Req 121')
		self.put('partial_smokeday/\ua66e/\u227b/141.md', 'Req 141')
		self.assertEqual(journal.detect_journal_version(part), 2)
		self.assertEqual(journal.find_step_file(part / '\u227a', 121), part / '\u227a/120\u2013140/121.md')
		upg = journal.upgrade_journal(part, project_root=self.root / 'partial_smokeday')
		self.assertTrue(upg['upgraded'])
		self.assertEqual(upg['from_version'], 2)
		self.assertEqual(upg['to_version'], 3)
		self.assertFalse((part / '\u227a/120\u2013140').exists())
		self.assertFalse((part / '\u227a/141.md').exists())
		self.assertTrue((part / '\u227a/121\u2013140/121.md').is_file())
		self.assertTrue((part / '\u227a/141\u2013160/141.md').is_file())
		self.assertTrue((part / '\u227b/101\u2013120/120.md').is_file())
		self.assertTrue((part / '\u227b/121\u2013140/121.md').is_file())
		self.assertTrue((part / '\u227b/141\u2013160/141.md').is_file())
		noop = journal.upgrade_journal(part, project_root=self.root / 'partial_smokeday')
		self.assertFalse(noop['upgraded'])
		self.assertEqual(noop['moved_files'], 0)
	# @used-by :mod:`unittest`
	def test_existing_same_request_is_not_ownership(self):
		self.put('req/7.md', 'same')
		self.put('res/9.md', 'orphan')
		self.assertEqual(journal.record_step(self.root, 'same', 'new'), 10)
		self.assertFalse((self.root / 'res/7.md').exists())
	# @used-by :mod:`unittest`
	def test_explicit_occupied_slot_and_overwrite_rejected(self):
		self.put('req/2.md', 'original')
		with self.assertRaises(FileExistsError):
			journal.record_step(self.root, 'replace', 'response', target_step=2)
		with self.assertRaises(ValueError):
			journal.record_step(self.root, 'replace', 'response', target_step=2, allow_overwrite=True)
		self.assertEqual((self.root / 'req/2.md').read_text(), 'original')
	# @used-by :mod:`unittest`
	def test_empty_payload_has_no_side_effect(self):
		with self.assertRaises(ValueError):
			journal.record_step(self.root / 'unused', 'req', '  ')
		self.assertFalse((self.root / 'unused').exists())
	# @used-by :mod:`unittest`
	def test_failed_second_write_recovers_with_token(self):
		actual = journal.create_bytes
		# @used-by :meth:`JournalTests.test_failed_second_write_recovers_with_token()`
		def failing(path, data):
			if 'res' == path.parent.name:
				raise OSError('simulated disk error')
			actual(path, data)
		with patch.object(journal, 'create_bytes', side_effect=failing):
			with self.assertRaises(RuntimeError):
				journal.record_step(self.root, 'request', 'response')
		receipt = journal.state_dir(self.root) / '1.json'
		state = json.loads(receipt.read_text())
		self.assertTrue(journal.step_errors(self.root, 1))
		with self.assertRaises(ValueError):
			journal.recover_step(self.root, 1, 'someone-else')
		journal.recover_step(self.root, 1, state['token'])
		self.assertFalse(receipt.exists())
		self.assertEqual(journal.step_errors(self.root, 1), [])
	# @used-by :mod:`unittest`
	def test_recovery_does_not_overwrite_conflict(self):
		actual = journal.create_bytes
		# @used-by :meth:`JournalTests.test_recovery_does_not_overwrite_conflict()`
		def failing(path, data):
			if 'res' == path.parent.name:
				raise OSError('simulated disk error')
			actual(path, data)
		with patch.object(journal, 'create_bytes', side_effect=failing):
			with self.assertRaises(RuntimeError):
				journal.record_step(self.root, 'req', 'res')
		receipt = journal.state_dir(self.root) / '1.json'
		state = json.loads(receipt.read_text())
		self.put('res/1.md', 'human correction')
		with self.assertRaises(FileExistsError):
			journal.recover_step(self.root, 1, state['token'])
		self.assertTrue(receipt.exists())
		self.assertTrue(journal.step_errors(self.root, 1))
	# @used-by :mod:`unittest`
	def test_process_crash_releases_lock_and_reservation_is_recoverable(self):
		code = "import os, sys\nfrom pathlib import Path\nsys.path.insert(0, sys.argv[1])\nfrom agent_tools import journal\noriginal = journal.create_bytes\ndef crash(path, data):\n    if path.parent.name == 'res':\n        os._exit(43)\n    original(path, data)\njournal.create_bytes = crash\njournal.record_step(Path(sys.argv[2]), 'request', 'response')\n"
		result = subprocess.run([sys.executable, '-c', code, str(SCRIPTS), str(self.root)])
		self.assertEqual(result.returncode, 43)
		receipt = journal.state_dir(self.root) / '1.json'
		state = json.loads(receipt.read_text())
		self.assertEqual(journal.record_step(self.root, 'next', 'answer'), 2)
		journal.recover_step(self.root, 1, state['token'])
		self.assertFalse(receipt.exists())
		self.assertEqual(journal.step_errors(self.root, 1), [])
	# @used-by :mod:`unittest`
	def test_concurrent_real_processes_same_request_get_distinct_pairs(self):
		# @used-by :meth:`JournalTests.test_concurrent_real_processes_same_request_get_distinct_pairs()`
		def run(index):
			# 2026-11-02
			# "Prevent journal-watch duplicate pairs on orphan steps, block direct journal writes bypassing answer-prepare, add recover-turn-violation, and harden watcher lifecycle":
			# https://github.com/dmitry-ai/harness/issues/36
			code = 'import sys; sys.path.insert(0, sys.argv[1]); from agent_tools.cli import main; raise SystemExit(main("record_step", sys.argv[2:]))'
			return subprocess.run([sys.executable, '-c', code, str(SCRIPTS), '--dir', str(self.root), '--req', 'identical request', '--res', f'response {index}'], cwd=self.root, capture_output=True, encoding='utf-8')
		with ThreadPoolExecutor(max_workers=6) as pool:
			results = list(pool.map(run, range(12)))
		for result in results:
			self.assertEqual(result.returncode, 0, result.stderr)
		self.assertEqual(journal.get_existing_step_ids(self.root), set(range(1, 13)))
		self.assertEqual({p.read_text() for p in (self.root / 'res').glob('*.md')}, {f'response {i}' for i in range(12)})
		self.assertEqual(list(journal.state_dir(self.root).glob('*.json')), [])
		for step in range(1, 13):
			self.assertEqual(journal.step_errors(self.root, step), [])
	# @used-by :mod:`unittest`
	def test_validation_checks_orphan_res_and_never_scans_neighbor_drafts(self):
		self.put('req/1.md', 'question')
		self.put('res/1.md', 'answer')
		self.put('Contracts/a/draft.md', '[bad](http://[invalid)')
		self.assertEqual(self.cli('validate_step', '--dir', self.root, '--step', 1).returncode, 0)
		self.put('res/2.md', 'orphan')
		self.assertNotEqual(self.cli('validate_step', '--dir', self.root, '--all').returncode, 0)
	# @used-by :mod:`unittest`
	def test_no_target_is_not_success(self):
		for name in ('validate_step', 'validate_links', 'validate_anchors', 'safe_commit'):
			self.assertNotEqual(self.cli(name).returncode, 0)
class LinkTests(unittest.TestCase):
	# @used-by :mod:`unittest`
	def test_real_http_redirect_anchor_and_404(self):
		class Handler(BaseHTTPRequestHandler):
			# @used-by :meth:`LinkTests.test_real_http_redirect_anchor_and_404()`
			def log_message(self, *args):
				pass
			# @used-by :meth:`LinkTests.test_real_http_redirect_anchor_and_404()`
			def do_GET(self):
				if '/redirect' == self.path:
					self.send_response(302)
					self.send_header('Location', '/page')
					self.end_headers()
				elif '/page' != self.path:
					self.send_error(404)
				else:
					self.send_response(200)
					self.send_header('Content-Type', 'text/html; charset=utf-8')
					self.end_headers()
					self.wfile.write('<div id="§x"></div>'.encode('utf-8'))
		server = HTTPServer(('127.0.0.1', 0), Handler)
		thread = threading.Thread(target=server.serve_forever, daemon=True)
		thread.start()
		try:
			base = f'http://127.0.0.1:{server.server_port}'
			results = check_network([base + '/redirect#%C2%A7x', base + '/missing#a'], anchors=True)
			self.assertEqual(results[0]['status'], 'found-in-source')
			self.assertEqual(results[0]['final_url'], base + '/page')
			self.assertEqual(results[1]['status'], 'fetch-error')
		finally:
			server.shutdown()
			thread.join(timeout=5)
			server.server_close()
	# @used-by :mod:`unittest`
	def test_markdown_reference_links_balanced_parentheses_and_html(self):
		text = '[nested](https://example.org/a_(b))\n[reference][x]\n\n[x]: https://example.org/ref\n\n<a href="https://example.org/html?a=1&amp;b=2">x</a>'
		urls, _ = references(text)
		self.assertEqual(urls, ['https://example.org/a_(b)', 'https://example.org/ref', 'https://example.org/html?a=1&b=2'])
	# @used-by :mod:`unittest`
	def test_code_samples_are_not_document_links(self):
		urls, _ = references('```md\n[example](https://example.org/code)\n```\n`https://example.org/inline`\n[actual](https://example.org/actual)')
		self.assertEqual(urls, ['https://example.org/actual'])
	# @used-by :mod:`unittest`
	def test_preserves_valid_urls_and_markdown(self):
		text = '[**example.org**/](https://www.example.org/a/?sig=x%2Fy&utm_key=part-of-signature#x)\nhttps://[::1]:8080/\n'
		self.assertEqual(validate_content(text), [])
	# @used-by :mod:`unittest`
	def test_invalid_port_is_diagnostic_not_crash(self):
		self.assertTrue(validate_content('https://example.org:wrong/'))
	# @used-by :mod:`unittest`
	def test_local_anchors_decode_and_are_case_sensitive(self):
		text = "<a name='§I.1'></a>\n[section](#%C2%A7I.1)"
		self.assertEqual(validate_content(text, local_anchors=True), [])
		self.assertTrue(validate_content(text.replace('#%C2%A7I.1', '#%C2%A7i.1'), local_anchors=True))
	# @used-by :mod:`unittest`
	def test_unique_urls_is_explicit_policy(self):
		text = '[x](https://example.org)\n[y](https://example.org)'
		self.assertEqual(validate_content(text), [])
		self.assertTrue(validate_content(text, unique_urls=True))
	# @used-by :mod:`unittest`
	def test_same_id_and_name_on_one_anchor_are_not_duplicates(self):
		self.assertEqual(validate_content('<a id="x" name="x"></a>\n[link](#x)', local_anchors=True), [])
	# @used-by :mod:`unittest`
	def test_failed_cached_fetch_reports_each_anchor(self):
		calls = []
		# @used-by :meth:`LinkTests.test_failed_cached_fetch_reports_each_anchor()`
		def fetch(url, timeout):
			calls.append(url)
			raise OSError('offline')
		results = check_network(['https://example.org#x', 'https://example.org#y'], anchors=True, fetcher=fetch)
		self.assertEqual(len(calls), 1)
		self.assertEqual([r['status'] for r in results], ['fetch-error', 'fetch-error'])
	# @used-by :mod:`unittest`
	def test_anchor_html_parser_handles_spacing_entities_and_case(self):
		# @used-by :meth:`LinkTests.test_anchor_html_parser_handles_spacing_entities_and_case()`
		def fetch(url, timeout):
			return Page(url, 200, 'text/html', '<div id = "A&amp;B"></div><a name=legacy></a>')
		urls = ['https://example.org#A%26B', 'https://example.org#legacy', 'https://example.org#a%26b']
		results = check_network(urls, anchors=True, fetcher=fetch)
		self.assertEqual([r['status'] for r in results], ['found-in-source', 'found-in-source', 'not-found-in-source'])
class SnapshotTests(TemporaryCase):
	# @used-by :mod:`unittest`
	def test_current_bytes_preserved_once_per_turn(self):
		(self.root / '.agents').mkdir()
		draft = self.put('Letters/draft.md', 'user change\r\n')
		saved = snapshot_draft(draft, 'turn_1')
		# 2026-10-14
		# "Implement /upwork-init onboarding workflow, CDP job extraction, A.A/A.F delegation, and Folders tree registration":
		# https://github.com/dmitry-ai/harness/issues/3
		self.assertTrue(saved.is_relative_to(self.root / 'ꘖ/data/.draft-snapshots'))
		self.assertFalse((draft.parent / '.draft-snapshots').exists())
		self.put('Letters/draft.md', 'agent revision')
		self.assertEqual(snapshot_draft(draft, 'turn_1'), saved)
		self.assertEqual(saved.read_bytes(), b'user change\r\n')
		self.assertEqual((draft.parent / 'draft.prev.md').read_bytes(), b'user change\r\n')
		second = snapshot_draft(draft, 'turn_2')
		self.assertEqual(second.read_bytes(), b'agent revision')
		self.assertEqual(saved.read_bytes(), b'user change\r\n')
	# @used-by :mod:`unittest`
	def test_changed_previous_copy_is_not_silently_replaced(self):
		draft = self.put('draft.md', 'before')
		snapshot_draft(draft, 'turn')
		self.put('draft.prev.md', 'external edit')
		with self.assertRaises(ValueError):
			snapshot_draft(draft, 'turn')
class ContextTests(TemporaryCase):
	# @used-by :mod:`unittest`
	def test_empty_final_never_falls_back_to_draft(self):
		draft = self.put('letter/result/EN/draft.md', 'draft')
		self.put('letter/result/EN/final.md', '  ')
		for path in (draft, self.root / 'letter'):
			with self.assertRaises(ValueError):
				resolve_letter_file(path)
	# @used-by :mod:`unittest`
	def test_final_without_draft_and_new_year_nested_letters(self):
		final = self.put('letters/2027/01/02/1/result/EN/final.md', 'final')
		self.put('letters/2027/01/02/1/result/EN/draft.md', 'draft')
		second = self.put('letters/2027/01/02/2/.md', 'second')
		self.assertEqual(discover_letters(self.root / 'letters'), [final, second])
	# @used-by :mod:`unittest`
	def test_sources_and_fences_preserved_in_configured_order(self):
		original = '# Title\n```python\nprint(1)\n```\n'
		self.put('kb.md', original)
		self.put('letters/2030/01/02/.md', 'client reply')
		manifest = {'version': 1, 'sections': [{'title': 'KB', 'files': ['kb.md']}, {'title': 'Correspondence', 'letters': [{'root': 'letters', 'author': 'Client'}]}]}
		content, sources = assemble(self.root, manifest)
		self.assertIn(original, content)
		self.assertIn('````markdown', content)
		self.assertIn('Author: Client', content)
		self.assertLess(content.index('# KB'), content.index('# Correspondence'))
		self.assertEqual(len(sources), 2)
	# @used-by :mod:`unittest`
	def test_missing_input_fails_and_dry_run_writes_nothing(self):
		config = self.put('context.json', json.dumps({'version': 1, 'output': 'out.md', 'sections': [{'title': 'KB', 'files': ['kb.md']}]}))
		with self.assertRaises(FileNotFoundError):
			generate(self.root, config)
		self.put('kb.md', 'source')
		generate(self.root, config, dry_run=True)
		self.assertFalse((self.root / 'out.md').exists())
		generate(self.root, config)
		self.assertTrue((self.root / 'out.md').exists())
		self.assertFalse((self.root / '.out.md.lock').exists())
		# 2026-10-14
		# "Implement /upwork-init onboarding workflow, CDP job extraction, A.A/A.F delegation, and Folders tree registration":
		# https://github.com/dmitry-ai/harness/issues/3
		self.assertTrue((self.root / 'ꘖ/data/context.lock').exists())
	# @used-by :mod:`unittest`
	def test_output_cannot_overwrite_input_or_escape_root(self):
		config = self.put('context.json', json.dumps({'version': 1, 'output': 'kb.md', 'sections': [{'title': 'KB', 'files': ['kb.md']}]}))
		self.put('kb.md', 'original')
		for output in (None, Path('../escape.md'), config):
			with self.assertRaises(ValueError):
				generate(self.root, config, output)
		self.assertEqual((self.root / 'kb.md').read_text(), 'original')
	# 2026-11-03
	# "Refactor generate_context.py to export only current timestamp and Agent KB excluding Evidence":
	# https://github.com/dmitry-ai/harness/issues/42
	# @used-by :mod:`unittest`
	def test_default_context_config_includes_agent_kb_and_excludes_evidence_subfolder(self):
		kb_main = self.put('ꘖ/KB/Overview.md', '# Overview\nAgent KB content\n')
		kb_evidence_doc = self.put('ꘖ/KB/Evidence.md', '# Evidence Document\nEvidence summary\n')
		self.put('ꘖ/KB/Evidence/capture.md', '# Raw Capture\nShould be excluded\n')
		self.put('ꘖ/KB/Evidence/nested/audit.md', '# Deep Capture\nShould be excluded\n')
		self.put('KB/Manual.md', '# Manual\nShould be excluded\n')
		# 2026-11-23
		# "Eliminate wall-clock race in context.generate and pre-lock flush race in storage.locked":
		# https://github.com/dmitry-ai/harness/issues/158
		fixed_now = datetime(2026, 11, 23, 12, 0, 0, tzinfo=timezone.utc)
		content, sources = assemble(self.root, now=fixed_now)
		self.assertIn('Generated: ', content)
		self.assertIn('# Overview', content)
		self.assertIn('# Evidence Document', content)
		self.assertNotIn('# Raw Capture', content)
		self.assertNotIn('# Deep Capture', content)
		self.assertNotIn('# Manual', content)
		self.assertEqual(set(sources), {kb_main.resolve(), kb_evidence_doc.resolve()})
		# 2026-11-23
		# "Eliminate wall-clock race in context.generate and pre-lock flush race in storage.locked":
		# https://github.com/dmitry-ai/harness/issues/158
		target, out_content, out_sources = generate(self.root, now=fixed_now)
		self.assertEqual(target, self.root / 'ꙮ/0/Context.md')
		self.assertTrue(target.is_file())
		self.assertEqual(out_content, content)
		self.assertEqual(set(out_sources), {kb_main.resolve(), kb_evidence_doc.resolve()})
	# 2026-11-03
	# "Refactor generate_context.py to export only current timestamp and Agent KB excluding Evidence":
	# https://github.com/dmitry-ai/harness/issues/42
	# @used-by :mod:`unittest`
	def test_generate_context_cli_supports_positional_root_and_default_config(self):
		from agent_tools.cli import main
		kb = self.put('ꘖ/KB/Findings.md', '# Findings\nAgent finding\n')
		self.put('ꘖ/KB/Evidence/run.md', '# Run\nExcluded\n')
		exit_code = main('generate_context', [str(self.root)])
		self.assertEqual(exit_code, 0)
		target = self.root / 'ꙮ/0/Context.md'
		self.assertTrue(target.is_file())
		text = target.read_text(encoding='utf-8')
		self.assertIn('Generated: ', text)
		self.assertIn('# Findings', text)
		self.assertNotIn('# Run', text)
class GitTests(TemporaryCase):
	# @used-by :meth:`GitTests.setUp()`
	# @used-by :meth:`GitTests.test_unrelated_staged_change_is_rejected()`
	# @used-by :meth:`GitTests.test_unstaged_change_rejected_and_explicit_commit_works()`
	def git(self, *args):
		result = subprocess.run(['git', '-C', str(self.root), *args], capture_output=True)
		self.assertEqual(result.returncode, 0, result.stderr)
		r = result.stdout
		return r
	# @used-by :mod:`unittest`
	# @see :meth:`TemporaryCase.setUp()`
	@override
	def setUp(self):
		super().setUp()
		self.git('init', '-q')
		self.git('config', 'user.name', 'Local Test')
		self.git('config', 'user.email', 'local-test@example.invalid')
		self.git('config', 'core.autocrlf', 'false')
		self.put('a space.md', 'before\n')
		self.put('b.md', 'other\n')
		self.git('add', '.')
		self.git('commit', '-qm', 'initial fixture')
	# @used-by :mod:`unittest`
	def test_unrelated_staged_change_is_rejected(self):
		self.put('a space.md', 'after\n')
		self.put('b.md', 'unrelated\n')
		self.git('add', '.')
		with self.assertRaises(ValueError):
			check_commit(self.root, ['a space.md'])
	# @used-by :mod:`unittest`
	def test_unstaged_change_rejected_and_explicit_commit_works(self):
		self.put('a space.md', 'staged\n')
		self.git('add', '--', 'a space.md')
		self.put('a space.md', 'later user change\n')
		with self.assertRaises(ValueError):
			check_commit(self.root, ['a space.md'])
		self.git('add', '--', 'a space.md')
		before = self.git('rev-parse', 'HEAD')
		# 2026-11-02
		# "Enforce GitHub Issue URL commit requirement across all repositories for agents while exempting human user commits by invocation context":
		# https://github.com/dmitry-ai/harness/issues/39
		with self.assertRaises(ValueError):
			commit(self.root, ['a space.md'], 'review only')
		commit(self.root, ['a space.md'], 'https://github.com/dmitry-ai/harness/issues/17')
		self.assertEqual(self.git('rev-parse', 'HEAD'), before)
		commit(self.root, ['a space.md'], 'https://github.com/dmitry-ai/harness/issues/17', execute=True)
		self.assertEqual(self.git('show', 'HEAD:a space.md'), b'later user change\n')
		self.assertEqual(self.git('show', 'HEAD:b.md'), b'other\n')
class StatementTests(TemporaryCase):
	# @used-by :mod:`unittest`
	def test_missing_test_not_masked_by_words_in_statement(self):
		self.put('1/.md', 'Methodology: Chrome CDP; curl checked response headers.\n[x](https://example.org)')
		self.assertTrue(validate_statements(self.root))
		self.put('1/Test.md', 'Actual test record')
		self.assertEqual(validate_statements(self.root), [])
# 2026-10-14
# "Implement /upwork-init onboarding workflow, CDP job extraction, A.A/A.F delegation, and Folders tree registration":
# https://github.com/dmitry-ai/harness/issues/3
class UpworkProjectTests(TemporaryCase):
	# @used-by :mod:`unittest`
	def test_agent_data_dir_prefers_vai_directory(self):
		(self.root / 'ꘖ').mkdir()
		draft = self.put('Letters/draft.md', 'v1\r\n')
		saved = snapshot_draft(draft, 'turn_vai')
		self.assertTrue(saved.is_relative_to(self.root / 'ꘖ/data/.draft-snapshots'))
		journal_dir = self.root / 'ꙮ/1 - Analysis'
		step = journal.record_step(journal_dir, 'req text', 'res text')
		self.assertEqual(step, 1)
		self.assertTrue((journal.state_dir(journal_dir) / 'writer.lock').exists())
		self.assertFalse((self.root / '.agents/data').exists())
if '__main__' == __name__:
	unittest.main()
