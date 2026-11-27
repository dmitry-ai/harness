# 2026-11-27 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
import json
from pathlib import Path
from Df.Harness.lib.text_claims import dfh_text_digest
from agent_tools.storage import create_bytes, data_dir_for, locked, replace_bytes, write_immutable_bytes
# 2026-11-27 "Move repository and grounding subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/382
APPLIED_CHECK_KEYS = ('operation', 'target', 'kind', 'base_sha256', 'candidate_sha256', 'coverage', 'inputs', 'claim_versions', 'candidate', 'manifest', 'source_checks')
# @used-by :func:`dfh_write_candidate_output()`
def dfh_find_registered_text(target) -> Path | None:
	from Df.Harness.Text.Workspace import Workspace
	resolved = Path(target).resolve()
	r = None
	for root in resolved.parents:
		file = dfh_text_folder(root) / 'index.json'
		if file.is_file():
			state = Workspace(root).index()
			name = resolved.relative_to(root).as_posix()
			if name in state['targets'] or name in state.get('protected', []):
				r = root
				break
	return r
# @used-by :meth:`Df.Harness.Git.CommitVerifier.CommitVerifier.verify()`
# @used-by :meth:`Df.Harness.Workflow.FinalizeStageRunner.FinalizeStageRunner.run()`
def dfh_gate_paths(paths, *, response=None) -> list:
	from Df.Harness.Text.Workspace import Workspace
	selected = {Path(path).resolve() for path in paths}
	r = []
	for root in dfh_text_roots(selected):
		ws = Workspace(root)
		r.append(ws.gate(response=response, targets=[name for name in ws.index()['targets'] if (root / name).resolve() in selected]))
	return r
# @used-by :func:`Df.Harness.lib.admission_ops.dfh_capture_admission()`
# @used-by :func:`Df.Harness.lib.blocked_report_ops._check_text_workflow_gate()`
# @used-by :func:`Df.Harness.lib.completion_record._commit_or_verify_journal_group()`
# @used-by :func:`Df.Harness.lib.journal_records.dfh_record_step()`
# @used-by :meth:`test_historical_admission.HistoricalAdmissionTests.test_aged_real_source_and_nested_semantic_approval_preserve_both_platforms()`
# @used-by :meth:`test_historical_admission.HistoricalAdmissionTests.test_later_conflicting_probe_rejects_new_publication_but_preserves_history()`
# @used-by :meth:`test_text_workflow.TextTransactionTests.test_workspace_and_integrity_verifier_single_pass_invariants()`
def dfh_gate_requests(paths, requests, response, *, capture: bool=False) -> list:
	from Df.Harness.Text.Workspace import Workspace
	r = []
	for root in dfh_text_roots(paths):
		res = Workspace(root).gate_requests_for_root(requests, response, capture=capture)
		if None is not res:
			r.append(res)
	return r
# @used-by :meth:`Df.Harness.Text.Workspace.Workspace.__validate_target_and_protected()`
# @used-by :meth:`Df.Harness.Text.Workspace.Workspace.document()`
def dfh_has_linked_ancestor(root: Path, target: Path, *, require_exists: bool=True) -> bool:
	return any((p.is_symlink() or (hasattr(p, 'is_junction') and p.is_junction()) for p in (target, *target.parents) if (not require_exists or p.exists()) and p.is_relative_to(root)))
# @used-by :func:`dfh_write_candidate_output()`
# @used-by :meth:`Df.Harness.Text.IntegrityVerifier.IntegrityVerifier.__verify_target_lineage()`
# @used-by :meth:`Df.Harness.Text.IntegrityVerifier.IntegrityVerifier.applied_integrity()`
# @used-by :meth:`Df.Harness.Text.Workspace.Workspace.__collect_protected()`
# @used-by :meth:`Df.Harness.Text.Workspace.Workspace.__gate_target()`
# @used-by :meth:`Df.Harness.Text.Workspace.Workspace.apply()`
# @used-by :meth:`Df.Harness.Text.Workspace.Workspace.begin()`
# @used-by :meth:`Df.Harness.Text.WorkspaceCheckRunner.WorkspaceCheckRunner.__collect_target_and_lint_issues()`
def dfh_hash_or_none(value) -> str | None:
	return dfh_text_digest(value) if None is not value else None
# @used-by :func:`dfh_write_candidate_output()`
# @used-by :meth:`Df.Harness.Text.Workspace.Workspace.__ensure_workspace_identity()`
# @used-by :meth:`Df.Harness.Text.Workspace.Workspace.__persist_applied()`
# @used-by :meth:`Df.Harness.Text.Workspace.Workspace.__reconcile_if_changed()`
# @used-by :meth:`Df.Harness.Text.Workspace.Workspace.begin()`
# @used-by :meth:`Df.Harness.Text.WorkspaceCheckRunner.WorkspaceCheckRunner.__check_replay()`
# @used-by :meth:`Df.Harness.Text.WorkspaceCheckRunner.WorkspaceCheckRunner.__persist_check()`
def dfh_immutable_text(path: Path, payload: bytes) -> Path:
	return write_immutable_bytes(path, payload, diff_error='Immutable text artifact differs: ' + str(path))
# @used-by :meth:`Df.Harness.Text.IntegrityVerifier.IntegrityVerifier.__find_snapshot()`
# @used-by :meth:`Df.Harness.Text.Workspace.Workspace.index()`
# @used-by :meth:`Df.Harness.Text.Workspace.Workspace.operation_meta()`
# @used-by :meth:`Df.Harness.Text.WorkspaceCheckRunner.WorkspaceCheckRunner.__persist_check()`
def dfh_read_json_sig(path) -> dict:
	return json.loads(Path(path).read_text(encoding='utf-8-sig'))
# @used-by :meth:`Df.Harness.Text.CliRunner.CliRunner.__workspace_handlers()`
# @used-by :meth:`test_df_harness_s11_wave2c_cov_text.DfHarnessS11Wave2CCovTextTests.test_cli_runner_source_render_and_text_helpers()`
# @used-by :meth:`test_text_integration.TextReviewTests.test_independent_routine_verdict_apply_and_exact_journal()`
def dfh_record_text_answer(root, journal, requests, response, turn) -> dict:
	from agent_tools.journal import record_answer as save
	steps = save(Path(journal), requests, response, turn, admission_roots=[root, journal])
	return {'journal_steps': steps, 'response_sha256': dfh_text_digest(response.encode()), 'delivery_verified': False}
# @used-by :func:`dfh_write_candidate_output()`
# @used-by :meth:`Df.Harness.Text.IntegrityVerifier.IntegrityVerifier.__verify_target_lineage()`
# @used-by :meth:`Df.Harness.Text.IntegrityVerifier.IntegrityVerifier.applied_integrity()`
# @used-by :meth:`Df.Harness.Text.Workspace.Workspace.__collect_protected()`
# @used-by :meth:`Df.Harness.Text.Workspace.Workspace.__gate_target()`
# @used-by :meth:`Df.Harness.Text.Workspace.Workspace.__validate_target_and_protected()`
# @used-by :meth:`Df.Harness.Text.Workspace.Workspace.apply()`
# @used-by :meth:`Df.Harness.Text.Workspace.Workspace.begin()`
# @used-by :meth:`Df.Harness.Text.WorkspaceCheckRunner.WorkspaceCheckRunner.__collect_target_and_lint_issues()`
def dfh_target_bytes(path: Path) -> bytes | None:
	if path.exists() and (not path.is_file()):
		raise ValueError('Text target must be a file')
	return path.read_bytes() if path.exists() else None
# @used-by :func:`Df.Harness.lib.text_review.dfh_text_review_state()`
# @used-by :func:`Df.Harness.lib.text_sources.dfh_source_attempt()`
# @used-by :func:`dfh_find_registered_text()`
# @used-by :func:`dfh_text_roots()`
# @used-by :meth:`Df.Harness.Text.ReviewPreparer.ReviewPreparer.__build_payload()`
# @used-by :meth:`Df.Harness.Text.ReviewPreparer.ReviewPreparer.prepare()`
# @used-by :meth:`Df.Harness.Text.ReviewRecorder.ReviewRecorder.record()`
# @used-by :meth:`Df.Harness.Text.SourceProber.SourceProber.probe()`
# @used-by :meth:`Df.Harness.Text.SourceReceiptStore.SourceReceiptStore.save()`
def dfh_text_folder(root) -> Path:
	from agent_tools.path_registry import project_paths
	return project_paths(root, exact_root=True).data_dir / 'texts'
# @used-by :func:`dfh_gate_paths()`
# @used-by :func:`dfh_gate_requests()`
def dfh_text_roots(paths) -> list[Path]:
	from agent_tools.path_registry import canonicalize_root_dir
	roots: set[Path] = set()
	for value in paths:
		path = canonicalize_root_dir(value)
		for root in (path, *path.parents):
			if (dfh_text_folder(root) / 'index.json').is_file():
				roots.add(root)
	return sorted(roots)
# @used-by :meth:`Df.Harness.Text.CliRunner.CliRunner.__write_rendered()`
# @used-by :meth:`test_text_workflow.TextTransactionTests.test_formatter_cannot_overwrite_a_document_protected_by_the_operation()`
# @used-by :meth:`test_text_workflow.TextTransactionTests.test_registered_target_cannot_be_overwritten_via_formatter()`
# @used-by :meth:`test_text_workflow.TextTransactionTests.test_unregistered_candidate_output_requires_cas_and_keeps_history()`
def dfh_write_candidate_output(path, payload: bytes, *, expected_sha256=None) -> dict:
	resolved = Path(path).resolve()
	if None is not dfh_find_registered_text(resolved):
		raise ValueError('Registered text target: use text-check/text-apply; formatter output is only a candidate')
	folder = data_dir_for(resolved)
	with locked(folder / 'text-candidates.lock'):
		previous = dfh_target_bytes(resolved)
		if dfh_hash_or_none(previous) != expected_sha256:
			raise ValueError('Existing output needs its current --expected-sha256; external version preserved')
		if None is not previous:
			dfh_immutable_text(folder / 'text-output-history' / (dfh_text_digest(previous) + '.bin'), previous)
		if dfh_target_bytes(resolved) != previous:
			raise ValueError('Output changed during candidate preparation')
		resolved.parent.mkdir(parents=True, exist_ok=True)
		if None is previous:
			create_bytes(resolved, payload)
		else:
			replace_bytes(resolved, payload)
	return {'path': str(resolved), 'sha256': dfh_text_digest(payload), 'kind': 'candidate', 'publication_approved': False}
