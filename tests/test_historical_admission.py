# 2026-11-03 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from copy import deepcopy
from contextlib import closing
from datetime import datetime, timedelta, timezone
from typing import override
import json
import os
from pathlib import Path
import shutil
import sqlite3
import time
import unittest
from unittest.mock import patch
import uuid
import test_turn_completion as native_fixtures
import test_text_integration as text_fixtures
from agent_tools import completion, path_registry, text_claims, text_review, text_sources, text_workflow
# 2026-11-24
# "Deduplicate historical admission fixtures and guard optional temp fsync":
# https://github.com/dmitry-ai/harness/issues/177
# @used-by :meth:`HistoricalAdmissionTests.test_proof_evidence_review_document_and_journal_changes_remain_conflicts()`
def _restore_tree_in_place(snapshot_dir: Path, work_dir: Path) -> None:
	for attempt in range(10):
		try:
			if work_dir.exists():
				shutil.rmtree(work_dir)
			break
		except PermissionError:
			if 9 == attempt:
				raise
			time.sleep(0.025)
	shutil.copytree(snapshot_dir, work_dir)
	path_registry.clear_registry_cache()
class Later(datetime):
	# @used-by :func:`Df.Core.lib.date.df_date()`
	# @used-by :func:`Df.Core.lib.date.df_date_from_timestamp_14()`
	# @used-by :func:`Df.Core.lib.date.df_now()`
	# @used-by :func:`Df.Core.lib.time.df_utc_iso()`
	# @used-by :func:`agent_tools.budget._active_window_5h_steps()`
	# @used-by :func:`agent_tools.cleanup_audit._istanbul_stamp()`
	# @used-by :func:`agent_tools.cleanup_audit.record_cleanup_answer_log()`
	# @used-by :func:`agent_tools.completion._now()`
	# @used-by :func:`agent_tools.context.assemble()`
	# @used-by :func:`agent_tools.knowledge.populate_agent_kb()`
	# @used-by :func:`agent_tools.project_rename_state._update_project_json()`
	# @used-by :func:`agent_tools.research.capture_dom()`
	# @used-by :func:`agent_tools.research.collect()`
	# @used-by :func:`agent_tools.research.observed_use()`
	# @used-by :func:`agent_tools.runtime.request_day()`
	# @used-by :func:`agent_tools.runtime_snapshot._activate_release()`
	# @used-by :func:`agent_tools.runtime_snapshot._promote_locked()`
	# @used-by :func:`agent_tools.text_browser.collect_cdp_dom()`
	# @used-by :func:`agent_tools.text_browser.collect_headless_dom()`
	# @used-by :func:`agent_tools.text_sources._attempt()`
	# @used-by :func:`agent_tools.text_sources._evaluate()`
	# @used-by :func:`agent_tools.upwork_extract.extract_upwork_job()`
	# @used-by :func:`agent_tools.upwork_project.initialize_upwork_project()`
	# @used-by :func:`agent_tools.workflow.now()`
	# @used-by :func:`test_worktree_isolation_gate._write_turn()`
	# @used-by :meth:`Df.Harness.Arch.ReviewStore.ReviewStore.record_review()`
	# @used-by :meth:`Df.Harness.Experiment.PlanPreparer.PlanPreparer.prepare_plan()`
	# @used-by :meth:`Df.Harness.Experiment.RunRecorder.RunRecorder.__init_run()`
	# @used-by :meth:`Df.Harness.Meta.Builders.Builders.build_journal()`
	# @used-by :meth:`Df.Harness.Meta.TimestampFormatter.TimestampFormatter.format_local()`
	# @used-by :meth:`Df.Harness.Project.RegistrationAttemptStarter.RegistrationAttemptStarter.__build_entry()`
	# @used-by :meth:`Df.Harness.Project.RegistrationStore.RegistrationStore.__build_entry()`
	# @used-by :meth:`Df.Harness.Tdd.MechanicalExemption.MechanicalExemption.record_exemption()`
	# @used-by :meth:`agent_tools.cleanup.ProjectCleanupScanner.__init__()`
	# @used-by :meth:`agent_tools.text_browser.GuardedCDP.capture_authenticated_dom()`
	# @used-by :meth:`test_cleanup.CleanupTests.test_legacy_conflicting_job_or_unowned_manifests_never_authorize_deletion()`
	# @used-by :meth:`test_cleanup.CleanupTests.test_legacy_historical_ids_are_compared_in_full_instead_of_their_numeric_prefix()`
	# @used-by :meth:`test_cleanup.CleanupTests.test_legacy_init_without_marker_is_discovered_and_old_file_uri_matches_native_registration()`
	# @used-by :meth:`test_cleanup.CleanupTests.test_legacy_native_id_conversation_preserves_project_with_unrelated_cwd()`
	# @used-by :meth:`test_experiments.ExperimentTests.native_fixture()`
	# @used-by :meth:`test_source_admission.SourceAdmissionTests.test_m4_collect_browser_public_and_authenticated_cdp_identity_provenance()`
	# @used-by :meth:`test_source_admission.SourceAdmissionTests.test_m5_intake_job_snapshot_source_check_provenance_and_attempt_isolation()`
	# @used-by :meth:`test_source_admission.SourceAdmissionTests.test_old_current_sources_expire_but_explicit_historical_editions_are_distinct()`
	# @used-by :meth:`test_source_admission.SourceAdmissionTests.test_valid_dom_capture_identity_can_resolve_the_http_channel_failure()`
	@classmethod
	def now(cls, tz=None):
		return datetime.now(timezone.utc) + timedelta(days=2)
# 2026-11-03
# "Replace persistent journal daemon with foreground-only idempotent reconciliation":
# https://github.com/dmitry-ai/harness/issues/41
class HistoricalAdmissionTests(unittest.TestCase):
	# 2026-11-26
	# "Apply cross-reference annotations across Harness Python and JavaScript":
	# https://github.com/dmitry-ai/harness/issues/305
	# @used-by :meth:`unittest.TestCase.setUp()`
	# @used-by :mod:`unittest`
	# @see :meth:`unittest.TestCase.setUp()`
	@override
	def setUp(self):
		# 2026-11-24
		# "Deduplicate historical admission fixtures and guard optional temp fsync":
		# https://github.com/dmitry-ai/harness/issues/177
		self.enterContext(patch.dict(os.environ, {'HARNESS_TEST_NO_FSYNC': '1'}))
		self.enterContext(patch('agent_tools.metrics.verify_native_proof', side_effect=lambda root, native, package=None: native))
	# @used-by :meth:`HistoricalAdmissionTests.test_aged_real_source_and_nested_semantic_approval_preserve_both_platforms()`
	# @used-by :meth:`HistoricalAdmissionTests.test_explicit_reconciled_baseline_preserves_history_without_granting_publication()`
	# @used-by :meth:`HistoricalAdmissionTests.test_failed_semantic_admission_is_not_granted_by_a_later_valid_apply()`
	# @used-by :meth:`HistoricalAdmissionTests.test_historical_successor_lineage_preserves_history_when_later_reviewer_trace_is_unverified()`
	# @used-by :meth:`HistoricalAdmissionTests.test_later_conflicting_probe_rejects_new_publication_but_preserves_history()`
	# @used-by :meth:`HistoricalAdmissionTests.test_later_legitimate_applied_revision_does_not_invalidate_old_answer()`
	# @used-by :meth:`HistoricalAdmissionTests.test_legacy_record_has_visible_proof_gap_and_unchanged_history()`
	# @used-by :meth:`HistoricalAdmissionTests.test_new_admission_still_rejects_aged_sources_and_cannot_recover_failed_gate()`
	# @used-by :meth:`HistoricalAdmissionTests.test_proof_evidence_review_document_and_journal_changes_remain_conflicts()`
	# @used-by :meth:`HistoricalAdmissionTests.test_real_pre_change_legacy_conflict_remains_conflict_permanently()`
	# @used-by :meth:`HistoricalAdmissionTests.test_real_pre_change_legacy_record_reports_legacy_proof_gap_and_remains_stable()`
	# @used-by :meth:`HistoricalAdmissionTests.test_reconciliation_receipt_tampering_or_deletion_remains_conflict()`
	# @used-by :meth:`HistoricalAdmissionTests.test_replaying_an_older_applied_target_is_not_a_later_legitimate_revision()`
	# @used-by :meth:`HistoricalAdmissionTests.test_selected_review_entry_mutation_or_deletion_remains_conflict()`
	# @used-by :meth:`HistoricalAdmissionTests.test_unreconciled_target_edit_temporary_conflict_preserves_original_delivery_provenance()`
	# @used-by :meth:`HistoricalAdmissionTests.test_unrelated_registry_revision_and_target_do_not_invalidate_selected_history()`
	# @used-by :meth:`HistoricalAdmissionTests.test_unrelated_review_entry_does_not_reapprove_or_invalidate_history()`
	def fixture(self, platform='codex', *, applied=True):
		text = text_fixtures.TextReviewTests()
		text.setUp()
		self.addCleanup(text.doCleanups)
		text.candidate = '1. The captured page contains Alternative: https://example.org/source.\n'
		self.check_and_review(text)
		if applied:
			self.assertEqual(text_workflow.apply(text.project, text.checked['check'])['status'], 'applied')
		case = native_fixtures.CompletionCase() if platform == 'codex' else native_fixtures.AntigravityCompletionTests()
		case.setUp()
		self.addCleanup(case.doCleanups)
		case.project = text.project
		request = text.op['requests'][0]
		if platform == 'codex':
			case.rows = [case.meta(), *case.turn_rows(case.turn, request)]
			case.write()
			backend = case.home
		else:
			case.rows = [{'step_index': 0, 'type': 'USER_INPUT', 'content': request}]
			case.write()
			with closing(sqlite3.connect(case.backend / 'conversation_summaries.db')) as connection:
				connection.execute('UPDATE conversation_summaries SET workspace_uris=?', (json.dumps([case.project.as_uri()]),))
				connection.commit()
			with closing(sqlite3.connect(case.backend / 'conversations' / (case.cid + '.db'))) as connection:
				connection.execute('UPDATE steps SET step_payload=? WHERE idx=0', (native_fixtures.wire(19, native_fixtures.wire(2, request.encode())),))
				connection.commit()
			backend = case.backend
		case.kwargs = {'conversation': case.cid, 'platform': platform, 'backend': backend}
		case.text = text
		case.response = 'Updated the proposal.\n'
		return case
	# @used-by :meth:`HistoricalAdmissionTests.fixture()`
	# @used-by :meth:`HistoricalAdmissionTests.test_explicit_reconciled_baseline_preserves_history_without_granting_publication()`
	# @used-by :meth:`HistoricalAdmissionTests.test_historical_successor_lineage_preserves_history_when_later_reviewer_trace_is_unverified()`
	# @used-by :meth:`HistoricalAdmissionTests.test_later_legitimate_applied_revision_does_not_invalidate_old_answer()`
	# @used-by :meth:`HistoricalAdmissionTests.test_replaying_an_older_applied_target_is_not_a_later_legitimate_revision()`
	def check_and_review(self, text):
		registry = json.loads((text.project / 'ꘖ/KB/TextClaims.json').read_text(encoding='utf-8'))
		ref = deepcopy(registry['facts'][0]['evidence'][0])
		ref['documentation'] = False
		source = text_sources.save_source_check(text.project, text.candidate, {'url': ref['source'], 'currency': 'current', 'currency_basis': 'Current synthetic capture for the publication/history integration test.', 'evidence': ref})
		self.assertTrue(source['valid'], source)
		manifest = text.manifest(text.candidate)
		manifest['source_checks'] = [source['source_check']]
		text.checked = text_workflow.check(text.project, text.op['id'], text.candidate, manifest)
		self.assertTrue(text.checked['valid'], text.checked['issues'])
		self.assertEqual(text.checked['coverage'], 'semantic')
		package = text.package()
		report = text.report(package)
		report['source_reviews'] = [{'url': ref['source'], 'receipt': source['source_check'], 'assessment': 'The saved literal page supports this one captured-page assertion.', 'outcome': 'supported'}]
		reviewer = str(uuid.uuid4())
		final = json.dumps(report, ensure_ascii=False)
		native = {'surface': 'codex-ui', 'status': 'completed', 'parent_id': text.parent, 'reviewer_id': reviewer, 'final_response': final, 'final_response_sha256': text_claims.digest(final.encode())}
		proof = text.project_file('ꘖ/KB/Evidence/Reviews/' + reviewer + '-fixture.json', json.dumps(native))
		text.review = text_review.record(text.project, final.encode(), parent_id=text.parent, reviewer_id=reviewer, native_evidence=proof.relative_to(text.project).as_posix())
		text.source = source
	# @used-by :meth:`HistoricalAdmissionTests.test_aged_real_source_and_nested_semantic_approval_preserve_both_platforms()`
	# @used-by :meth:`HistoricalAdmissionTests.test_explicit_reconciled_baseline_preserves_history_without_granting_publication()`
	# @used-by :meth:`HistoricalAdmissionTests.test_historical_successor_lineage_preserves_history_when_later_reviewer_trace_is_unverified()`
	# @used-by :meth:`HistoricalAdmissionTests.test_later_conflicting_probe_rejects_new_publication_but_preserves_history()`
	# @used-by :meth:`HistoricalAdmissionTests.test_later_legitimate_applied_revision_does_not_invalidate_old_answer()`
	# @used-by :meth:`HistoricalAdmissionTests.test_legacy_record_has_visible_proof_gap_and_unchanged_history()`
	# @used-by :meth:`HistoricalAdmissionTests.test_proof_evidence_review_document_and_journal_changes_remain_conflicts()`
	# @used-by :meth:`HistoricalAdmissionTests.test_real_pre_change_legacy_conflict_remains_conflict_permanently()`
	# @used-by :meth:`HistoricalAdmissionTests.test_real_pre_change_legacy_record_reports_legacy_proof_gap_and_remains_stable()`
	# @used-by :meth:`HistoricalAdmissionTests.test_reconciliation_receipt_tampering_or_deletion_remains_conflict()`
	# @used-by :meth:`HistoricalAdmissionTests.test_replaying_an_older_applied_target_is_not_a_later_legitimate_revision()`
	# @used-by :meth:`HistoricalAdmissionTests.test_selected_review_entry_mutation_or_deletion_remains_conflict()`
	# @used-by :meth:`HistoricalAdmissionTests.test_unreconciled_target_edit_temporary_conflict_preserves_original_delivery_provenance()`
	# @used-by :meth:`HistoricalAdmissionTests.test_unrelated_registry_revision_and_target_do_not_invalidate_selected_history()`
	# @used-by :meth:`HistoricalAdmissionTests.test_unrelated_review_entry_does_not_reapprove_or_invalidate_history()`
	def deliver(self, case):
		prepared = completion.prepare(case.project, case.response, **case.kwargs)
		self.assertTrue(prepared['ready'])
		case.finish(case.response)
		first = completion.sync(case.project, **case.kwargs)
		self.assertTrue(first['valid'], first)
		self.assertEqual(first['turns'][0]['status'], 'delivered')
		self.assertTrue(first['turns'][0]['preparation_verified'])
		return first
	# @used-by :func:`agent_tools.issues.repo_commands.run_audit_repo()`
	# @used-by :meth:`HistoricalAdmissionTests.test_legacy_record_has_visible_proof_gap_and_unchanged_history()`
	# @used-by :meth:`HistoricalAdmissionTests.test_proof_evidence_review_document_and_journal_changes_remain_conflicts()`
	# @used-by :meth:`HistoricalAdmissionTests.test_real_pre_change_legacy_conflict_remains_conflict_permanently()`
	# @used-by :meth:`HistoricalAdmissionTests.test_real_pre_change_legacy_record_reports_legacy_proof_gap_and_remains_stable()`
	# @used-by :meth:`HistoricalAdmissionTests.test_unreconciled_target_edit_temporary_conflict_preserves_original_delivery_provenance()`
	# @used-by :meth:`agent_tools.issues.service.GitHubIssueService._execute_edit()`
	# @used-by :meth:`agent_tools.issues.service.GitHubIssueService._parse_edit_inputs()`
	# @used-by :meth:`agent_tools.issues.service.GitHubIssueService.cmd_edit()`
	def state(self, case):
		path = next((case.project / 'ꘖ/data/turns').glob('*.json'))
		return path, json.loads(path.read_text(encoding='utf-8'))
	# @used-by :meth:`HistoricalAdmissionTests.test_aged_real_source_and_nested_semantic_approval_preserve_both_platforms()`
	# @used-by :meth:`HistoricalAdmissionTests.test_explicit_reconciled_baseline_preserves_history_without_granting_publication()`
	# @used-by :meth:`HistoricalAdmissionTests.test_historical_successor_lineage_preserves_history_when_later_reviewer_trace_is_unverified()`
	# @used-by :meth:`HistoricalAdmissionTests.test_later_conflicting_probe_rejects_new_publication_but_preserves_history()`
	# @used-by :meth:`HistoricalAdmissionTests.test_later_legitimate_applied_revision_does_not_invalidate_old_answer()`
	# @used-by :meth:`HistoricalAdmissionTests.test_unrelated_registry_revision_and_target_do_not_invalidate_selected_history()`
	# @used-by :meth:`HistoricalAdmissionTests.test_unrelated_review_entry_does_not_reapprove_or_invalidate_history()`
	def assert_stable(self, case):
		before = case.project_snapshot()
		with patch('agent_tools.text_sources.datetime', Later):
			for _ in range(2):
				result = completion.sync(case.project, **case.kwargs)
				self.assertTrue(result['valid'], result)
				self.assertEqual(result['turns'][0]['status'], 'delivered')
				self.assertTrue(result['turns'][0]['delivery_verified'])
		self.assertEqual(case.project_snapshot(), before)
	# @used-by :mod:`unittest`
	def test_aged_real_source_and_nested_semantic_approval_preserve_both_platforms(self):
		for platform in ('codex', 'antigravity'):
			with self.subTest(platform=platform):
				case = self.fixture(platform)
				with patch.object(text_review, 'authorize', wraps=text_review.authorize) as authorize:
					self.assertTrue(text_workflow.gate(case.project)['valid'])
					self.assertGreater(authorize.call_count, 0)
				self.deliver(case)
				with patch('agent_tools.text_sources.datetime', Later):
					with self.assertRaisesRegex(ValueError, 'source|Source|stale'):
						text_workflow.gate_requests([case.project], case.text.op['requests'], case.response)
				self.assert_stable(case)
	# @used-by :mod:`unittest`
	def test_new_admission_still_rejects_aged_sources_and_cannot_recover_failed_gate(self):
		for platform in ('codex', 'antigravity'):
			with self.subTest(platform=platform):
				case = self.fixture(platform)
				with patch('agent_tools.text_sources.datetime', Later):
					with self.assertRaisesRegex(ValueError, 'source|Source|stale'):
						completion.prepare(case.project, case.response, **case.kwargs)
				case.finish(case.response)
				result = completion.sync(case.project, **case.kwargs)
				self.assertFalse(result['valid'], result)
				self.assertEqual(result['turns'][0]['status'], 'conflict')
				self.assertIn('prior preparation/admission gate failed', result['turns'][0]['detail'])
				self.assertFalse((case.project / 'ꙮ/1 - Analysis/res/1.md').exists())
				# 2026-11-21
				# "Wire automatic journal upgrade and bucketed step resolution across Harness subsystems":
				# https://github.com/dmitry-ai/harness/issues/109
				self.assertFalse((case.project / 'ꙮ/≺/1–20/1.md').exists())
	# @used-by :mod:`unittest`
	def test_proof_evidence_review_document_and_journal_changes_remain_conflicts(self):
		for platform in ('codex', 'antigravity'):
			case = self.fixture(platform)
			self.deliver(case)
			# 2026-11-24
			# "Deduplicate historical admission fixtures and guard optional temp fsync":
			# https://github.com/dmitry-ai/harness/issues/177
			snap_dir = case.project.parent / f'_delivered_snapshot_{platform}'
			shutil.copytree(case.project, snap_dir)
			_, base_state = self.state(case)
			recorded = base_state.get('journal_record') or base_state['prepared']
			entry = text_workflow._index(case.project)['targets'][case.text.op['target']]
			paths = {'proof': Path(recorded['admission']['file']), 'source': case.project / case.text.source['source_check'], 'evidence': case.project / 'ꘖ/KB' / case.text.source['spec']['evidence']['observation'], 'check': case.project / case.text.checked['check'], 'applied': case.project / entry['receipt'], 'review': case.project / case.text.review['report'], 'target': case.text.target, 'journal': Path(recorded['response_file']), 'group': Path(recorded['group_file'])}
			for kind in ('proof', 'source', 'evidence', 'check', 'applied', 'review', 'target', 'journal', 'group'):
				for mutation in ('change', 'delete'):
					with self.subTest(platform=platform, kind=kind, mutation=mutation):
						_restore_tree_in_place(snap_dir, case.project)
						path = paths[kind]
						if kind == 'evidence':
							path = path.with_name('response.bin')
						self.assertTrue(path.resolve().is_relative_to(case.project.resolve()))
						if mutation == 'delete':
							path.unlink()
						else:
							path.write_bytes(path.read_bytes() + b'\nTampered bytes')
						result = completion.sync(case.project, **case.kwargs)
						self.assertFalse(result['valid'], result)
						self.assertEqual(result['turns'][0]['status'], 'conflict')
	# @used-by :mod:`unittest`
	def test_legacy_record_has_visible_proof_gap_and_unchanged_history(self):
		for platform in ('codex', 'antigravity'):
			with self.subTest(platform=platform):
				case = self.fixture(platform)
				self.deliver(case)
				path, state = self.state(case)
				for field in ('prepared', 'journal_record', 'delivery'):
					if state.get(field):
						state[field].pop('admission', None)
						state[field].pop('group_sha256', None)
				path.write_text(json.dumps(state), encoding='utf-8')
				recorded = state.get('journal_record') or state['prepared']
				group_path = Path(recorded['group_file'])
				group = json.loads(group_path.read_text(encoding='utf-8'))
				group.pop('admission', None)
				group_path.write_text(json.dumps(group), encoding='utf-8')
				before = case.project_snapshot()
				with patch('agent_tools.text_sources.datetime', Later):
					result = completion.sync(case.project, **case.kwargs)
				self.assertTrue(result['valid'], result)
				self.assertEqual(result['turns'][0]['admission_verification']['status'], 'legacy_proof_gap')
				self.assertEqual(case.project_snapshot(), before)
	# @used-by :mod:`unittest`
	def test_unrelated_registry_revision_and_target_do_not_invalidate_selected_history(self):
		for platform in ('codex', 'antigravity'):
			with self.subTest(platform=platform):
				case = self.fixture(platform)
				self.deliver(case)
				registry = json.loads((case.project / 'ꘖ/KB/TextClaims.json').read_text(encoding='utf-8'))
				other = deepcopy(registry['facts'][0])
				other['id'] = 'F-UNRELATED'
				for index, ref in enumerate(other['evidence'], 1):
					ref['id'] = 'E-UNRELATED-' + str(index)
				registry['facts'].append(other)
				text_claims.save_registry(case.project, registry, expected_sha256=text_claims.digest((case.project / 'ꘖ/KB/TextClaims.json').read_bytes()))
				case.text.start('1. Unrelated original.\n', target='result/EN/other.md', requests=['Edit another target.'])
				self.assert_stable(case)
	# @used-by :mod:`unittest`
	def test_later_conflicting_probe_rejects_new_publication_but_preserves_history(self):
		from agent_tools.research import Response
		for platform in ('codex', 'antigravity'):
			with self.subTest(platform=platform):
				case = self.fixture(platform)
				self.deliver(case)
				probe = text_sources.probe_links(case.project, case.text.candidate, fetcher=lambda url, *args: Response(url, 500, 'text/html', b'Unavailable source'))
				self.assertTrue(probe['findings'])
				with self.assertRaisesRegex(ValueError, 'source|Source|conflicting'):
					text_workflow.gate_requests([case.project], case.text.op['requests'], case.response)
				self.assert_stable(case)
	# @used-by :mod:`unittest`
	def test_selected_review_entry_mutation_or_deletion_remains_conflict(self):
		for platform in ('codex', 'antigravity'):
			for mutation in ('change', 'delete'):
				with self.subTest(platform=platform, mutation=mutation):
					case = self.fixture(platform)
					self.deliver(case)
					path = case.project / 'ꘖ/data/texts/reviews.json'
					state = json.loads(path.read_text(encoding='utf-8'))
					if mutation == 'delete':
						state['reviews'].clear()
					else:
						state['reviews'][0]['result'] = 'needs_changes'
					path.write_text(json.dumps(state), encoding='utf-8')
					result = completion.sync(case.project, **case.kwargs)
					self.assertFalse(result['valid'], result)
					self.assertEqual(result['turns'][0]['status'], 'conflict')
	# @used-by :mod:`unittest`
	def test_unrelated_review_entry_does_not_reapprove_or_invalidate_history(self):
		for platform in ('codex', 'antigravity'):
			with self.subTest(platform=platform):
				case = self.fixture(platform)
				self.deliver(case)
				path = case.project / 'ꘖ/data/texts/reviews.json'
				state = json.loads(path.read_text(encoding='utf-8'))
				other = deepcopy(state['reviews'][0])
				other.update(id='unrelated-review', reviewer_id=str(uuid.uuid4()), subject_sha256='00' * 32)
				state['reviews'].append(other)
				path.write_text(json.dumps(state), encoding='utf-8')
				self.assert_stable(case)
	# @used-by :mod:`unittest`
	def test_later_legitimate_applied_revision_does_not_invalidate_old_answer(self):
		for platform in ('codex', 'antigravity'):
			with self.subTest(platform=platform):
				case = self.fixture(platform)
				self.deliver(case)
				text = case.text
				text.op = text_workflow.begin(text.project, {'kind': 'proposal', 'mode': 'edit', 'changes': 'prose', 'target': text.op['target'], 'goal': 'Revise the captured-page wording.', 'requests': ['Apply the later document revision.']})
				text.candidate = '1. The captured page contains the concern: https://example.org/source.\n'
				self.check_and_review(text)
				self.assertEqual(text_workflow.apply(text.project, text.checked['check'])['status'], 'applied')
				self.assert_stable(case)
	# @used-by :mod:`unittest`
	def test_failed_semantic_admission_is_not_granted_by_a_later_valid_apply(self):
		for platform in ('codex', 'antigravity'):
			with self.subTest(platform=platform):
				case = self.fixture(platform, applied=False)
				original = case.text.target.read_bytes()
				case.text.target.write_bytes(b'Unadmitted changed document.\n')
				with self.assertRaisesRegex(ValueError, 'apply receipt|applied'):
					completion.prepare(case.project, case.response, **case.kwargs)
				case.text.target.write_bytes(original)
				self.assertEqual(text_workflow.apply(case.project, case.text.checked['check'])['status'], 'applied')
				self.assertTrue(text_workflow.gate(case.project)['valid'])
				case.finish(case.response)
				result = completion.sync(case.project, **case.kwargs)
				self.assertFalse(result['valid'], result)
				self.assertIn('prior preparation/admission gate failed', result['turns'][0]['detail'])
	# @used-by :mod:`unittest`
	def test_replaying_an_older_applied_target_is_not_a_later_legitimate_revision(self):
		for platform in ('codex', 'antigravity'):
			with self.subTest(platform=platform):
				case = self.fixture(platform)
				text = case.text
				index_path = case.project / 'ꘖ/data/texts/index.json'
				old_entry = deepcopy(json.loads(index_path.read_text(encoding='utf-8'))['targets'][text.op['target']])
				old_bytes = text.target.read_bytes()
				text.op = text_workflow.begin(text.project, {'kind': 'proposal', 'mode': 'edit', 'changes': 'prose', 'target': text.op['target'], 'goal': 'Revise the captured-page wording.', 'requests': ['Apply the newer captured-page revision.']})
				text.candidate = '1. The captured page contains the concern: https://example.org/source.\n'
				self.check_and_review(text)
				text_workflow.apply(text.project, text.checked['check'])
				self.deliver(case)
				index = json.loads(index_path.read_text(encoding='utf-8'))
				index['targets'][text.op['target']] = old_entry
				index_path.write_text(json.dumps(index), encoding='utf-8')
				text.target.write_bytes(old_bytes)
				result = completion.sync(case.project, **case.kwargs)
				self.assertFalse(result['valid'], result)
				self.assertEqual(result['turns'][0]['status'], 'conflict')
	# @used-by :meth:`HistoricalAdmissionTests.test_explicit_reconciled_baseline_preserves_history_without_granting_publication()`
	# @used-by :meth:`HistoricalAdmissionTests.test_reconciliation_receipt_tampering_or_deletion_remains_conflict()`
	def reconcile_manual_baseline(self, case):
		text = case.text
		manual = b'1. The captured page contains the concern: https://example.org/source.\n'
		text.target.write_bytes(manual)
		text.op = text_workflow.begin(text.project, {'kind': 'proposal', 'mode': 'edit', 'changes': 'prose', 'target': text.op['target'], 'goal': 'Reconcile the manual baseline, then review a new revision.', 'requests': ['Reconcile this exact edited baseline.'], 'reconcile_sha256': text_claims.digest(manual)})
		return json.loads((case.project / 'ꘖ/data/texts/index.json').read_text(encoding='utf-8'))['targets'][text.op['target']]
	# @used-by :mod:`unittest`
	def test_explicit_reconciled_baseline_preserves_history_without_granting_publication(self):
		for platform in ('codex', 'antigravity'):
			with self.subTest(platform=platform):
				case = self.fixture(platform)
				self.deliver(case)
				self.reconcile_manual_baseline(case)
				with self.assertRaisesRegex(ValueError, 'baseline, not publication approval'):
					text_workflow.gate(case.project, publication=True)
				self.assert_stable(case)
				text = case.text
				text.candidate = '1. The captured page contains the concern and Alternative: https://example.org/source.\n'
				self.check_and_review(text)
				self.assertEqual(text_workflow.apply(text.project, text.checked['check'])['status'], 'applied')
				self.assertTrue(text_workflow.gate(text.project, publication=True)['valid'])
				self.assert_stable(case)
	# @used-by :mod:`unittest`
	def test_reconciliation_receipt_tampering_or_deletion_remains_conflict(self):
		for platform in ('codex', 'antigravity'):
			for mutation in ('change', 'delete'):
				with self.subTest(platform=platform, mutation=mutation):
					case = self.fixture(platform)
					self.deliver(case)
					entry = self.reconcile_manual_baseline(case)
					path = case.project / entry['reconciliation']
					if mutation == 'delete':
						path.unlink()
					else:
						path.write_bytes(path.read_bytes() + b'\nTampered reconciliation')
					result = completion.sync(case.project, **case.kwargs)
					self.assertFalse(result['valid'], result)
					self.assertEqual(result['turns'][0]['status'], 'conflict')
	# @used-by :mod:`unittest`
	def test_real_pre_change_legacy_record_reports_legacy_proof_gap_and_remains_stable(self):
		for platform in ('codex', 'antigravity'):
			with self.subTest(platform=platform):
				case = self.fixture(platform)
				self.deliver(case)
				path, state = self.state(case)
				recorded = state.get('journal_record') or state['prepared']
				group_path = Path(recorded['group_file'])
				group = json.loads(group_path.read_text(encoding='utf-8'))
				group.pop('admission', None)
				group_path.write_text(json.dumps(group), encoding='utf-8')
				prep = deepcopy(state.get('prepared'))
				if prep:
					prep.pop('admission', None)
					prep.pop('group_sha256', None)
				legacy_state = {
					'schema_version': 1,
					'key': state['key'],
					'project_root': str(case.project),
					'platform': platform,
					'native_backend': str(case.kwargs['backend']),
					'conversation_id': case.cid,
					'native_turn_id': state['native_turn_id'],
					'native_start_step': state['native_start_step'],
					'requests': state['requests'],
					'role': 'primary',
					'journal_required': True,
					'journal': state['journal'],
					'status': 'delivered',
					'prepared': prep,
					'delivery': {
						'journal_steps': recorded['journal_steps'],
						'response_sha256': recorded['response_sha256'],
						'response_file': recorded['response_file'],
						'recorded_at': recorded.get('recorded_at', '2026-10-24T05:54:00+00:00'),
						'group_file': recorded['group_file'],
						'reused_complete_journal_group': True,
						'verified': True,
						'source_file': state['delivery']['source_file'],
						'final_step': state['delivery']['final_step'],
						'native_response_sha256': state['delivery']['native_response_sha256'],
						'completion_provenance': 'existing_journal',
						'preparation_verified': False,
						'exec5_check': state.get('exec5_check', {'verified': True}),
						'verified_at': state['delivery']['verified_at'],
					},
					'journal_record': {
						'journal_steps': recorded['journal_steps'],
						'response_sha256': recorded['response_sha256'],
						'response_file': recorded['response_file'],
						'recorded_at': recorded.get('recorded_at', '2026-10-24T05:54:00+00:00'),
						'group_file': recorded['group_file'],
						'reused_complete_journal_group': True,
					},
					'exec5_check': state.get('exec5_check', {'verified': True}),
					'recovered_after_delivery': False,
				}
				path.write_text(json.dumps(legacy_state), encoding='utf-8')
				before = case.project_snapshot()
				with patch('agent_tools.text_sources.datetime', Later):
					result = completion.sync(case.project, **case.kwargs)
				self.assertTrue(result['valid'], result)
				self.assertEqual(result['turns'][0]['status'], 'delivered')
				self.assertTrue(result['turns'][0]['delivery_verified'])
				self.assertEqual(result['turns'][0]['admission_verification']['status'], 'legacy_proof_gap')
				self.assertEqual(case.project_snapshot(), before)
	# @used-by :mod:`unittest`
	def test_real_pre_change_legacy_conflict_remains_conflict_permanently(self):
		for platform in ('codex', 'antigravity'):
			with self.subTest(platform=platform):
				case = self.fixture(platform)
				self.deliver(case)
				path, state = self.state(case)
				recorded = state.get('journal_record') or state['prepared']
				group_path = Path(recorded['group_file'])
				group = json.loads(group_path.read_text(encoding='utf-8'))
				group.pop('admission', None)
				group_path.write_text(json.dumps(group), encoding='utf-8')
				prep = deepcopy(state.get('prepared'))
				if prep:
					prep.pop('admission', None)
					prep.pop('group_sha256', None)
				legacy_conflict = {
					'schema_version': 1,
					'key': state['key'],
					'project_root': str(case.project),
					'platform': platform,
					'native_backend': str(case.kwargs['backend']),
					'conversation_id': case.cid,
					'native_turn_id': state['native_turn_id'],
					'native_start_step': state['native_start_step'],
					'requests': state['requests'],
					'role': 'primary',
					'journal_required': True,
					'journal': state['journal'],
					'status': 'conflict',
					'prepared': prep,
					'delivery': {
						'verified': False,
						'native_response_sha256': state['delivery']['native_response_sha256'],
						'source_file': state['delivery']['source_file'],
						'final_step': state['delivery']['final_step'],
						'native_requests': state['requests'],
						'conflict_evidence': 'ꘖ/data/conflicts/' + state['key'] + '-legacy.txt',
						'detail': 'Historical pre-change conflict',
						'retryable': False,
					},
					'journal_record': {
						'journal_steps': recorded['journal_steps'],
						'response_sha256': recorded['response_sha256'],
						'response_file': recorded['response_file'],
						'recorded_at': recorded.get('recorded_at', '2026-10-24T05:54:00+00:00'),
						'group_file': recorded['group_file'],
						'reused_complete_journal_group': True,
					},
					'exec5_check': state.get('exec5_check', {'verified': True}),
					'recovered_after_delivery': False,
				}
				path.write_text(json.dumps(legacy_conflict), encoding='utf-8')
				before = case.project_snapshot()
				with patch('agent_tools.text_sources.datetime', Later):
					result = completion.sync(case.project, **case.kwargs)
				self.assertFalse(result['valid'])
				self.assertEqual(result['turns'][0]['status'], 'conflict')
				self.assertFalse(result['turns'][0]['delivery_verified'])
				self.assertEqual(result['turns'][0]['admission_verification']['status'], 'legacy_proof_gap')
				self.assertEqual(case.project_snapshot(), before)
	# @used-by :mod:`unittest`
	def test_historical_successor_lineage_preserves_history_when_later_reviewer_trace_is_unverified(self):
		for platform in ('codex', 'antigravity'):
			with self.subTest(platform=platform):
				case = self.fixture(platform)
				self.deliver(case)
				text = case.text
				text.op = text_workflow.begin(text.project, {'kind': 'proposal', 'mode': 'edit', 'changes': 'prose', 'target': text.op['target'], 'goal': 'Revise the captured-page wording.', 'requests': ['Apply the later document revision.']})
				text.candidate = '1. The captured page contains the concern: https://example.org/source.\n'
				self.check_and_review(text)
				applied = text_workflow.apply(text.project, text.checked['check'])
				self.assertEqual(applied['status'], 'applied')
				with patch('agent_tools.metrics.verify_native_proof', side_effect=ValueError('Reviewer session trace was archived or mutated')):
					self.assert_stable(case)
					applied_path = text.project / applied['receipt']
					saved_applied = json.loads(applied_path.read_text(encoding='utf-8'))
					with self.assertRaisesRegex(ValueError, 'Reviewer session trace was archived or mutated'):
						text_review.approval_integrity(text.project, saved_applied['approval'], require_live_proof=True)
	# @used-by :mod:`unittest`
	def test_unreconciled_target_edit_temporary_conflict_preserves_original_delivery_provenance(self):
		for platform in ('codex', 'antigravity'):
			with self.subTest(platform=platform):
				case = self.fixture(platform)
				self.deliver(case)
				_, state_before = self.state(case)
				original_verified_at = state_before['delivery']['verified_at']
				original_provenance = state_before['delivery']['completion_provenance']
				original_bytes = case.text.target.read_bytes()
				case.text.target.write_bytes(b'1. Hand-edited target without reconcile.\n')
				result_conflict = completion.sync(case.project, **case.kwargs)
				self.assertFalse(result_conflict['valid'])
				self.assertEqual(result_conflict['turns'][0]['status'], 'conflict')
				_, state_conflict = self.state(case)
				self.assertIn('prior_verified_delivery', state_conflict)
				case.text.target.write_bytes(original_bytes)
				result_restored = completion.sync(case.project, **case.kwargs)
				self.assertTrue(result_restored['valid'])
				self.assertEqual(result_restored['turns'][0]['status'], 'delivered')
				_, state_restored = self.state(case)
				self.assertEqual(state_restored['delivery']['verified_at'], original_verified_at)
				self.assertEqual(state_restored['delivery']['completion_provenance'], original_provenance)
				self.assertNotIn('prior_verified_delivery', state_restored)
