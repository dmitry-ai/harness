# 2026-11-27 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
import json
from pathlib import Path
import re
from urllib.parse import urldefrag, urlsplit
from Df.Core.lib.sha256 import df_sha256
from Df.Harness.lib.research import dfh_inside
from agent_tools.claims import all_claims, claim_index, claim_locations, collect_claim_closure
# 2026-11-27 "Move repository and grounding subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/382
# @used-by :func:`_collect_ref_inputs()`
def _add_local_input(root: Path, path: Path, result: dict[str, str]) -> None:
	resolved = Path(path).resolve()
	root_resolved = Path(root).resolve()
	if not resolved.is_relative_to(root_resolved) or not resolved.is_file():
		raise ValueError('Referenced primary artifact is missing or outside the project')
	result[resolved.relative_to(root_resolved).as_posix()] = dfh_text_digest(resolved.read_bytes())
# @used-by :func:`dfh_evidence_inputs()`
def _collect_ref_inputs(root, ref: dict, result: dict[str, str], local_file) -> None:
	if ref.get('observation'):
		meta = local_file(root, ref['observation'])
		_add_local_input(root, meta, result)
		_add_local_input(root, meta.with_name('response.bin'), result)
	if not urlsplit(ref.get('source', '')).scheme:
		_add_local_input(root, local_file(root, urldefrag(ref['source'])[0]), result)
	for name in ('manifest', 'experiment'):
		if ref.get(name):
			source = local_file(root, ref[name])
			_add_local_input(root, source, result)
			if 'experiment' == name:
				for artifact in json.loads(source.read_text(encoding='utf-8')).get('artifacts', []):
					if artifact.get('path'):
						_add_local_input(root, dfh_inside(root, artifact['path']), result)
# @used-by :func:`Df.Harness.lib.text_sources.dfh_check_claim_sources()`
# @used-by :meth:`Df.Harness.Text.ClaimMapValidator.ClaimMapValidator.__load_registry()`
# @used-by :meth:`Df.Harness.Text.IntegrityVerifier.IntegrityVerifier.__find_snapshot()`
# @used-by :meth:`Df.Harness.Text.WorkspaceCheckRunner.WorkspaceCheckRunner.__persist_check()`
def dfh_claim_subset(value, identifiers) -> dict:
	if not isinstance(value, dict) or 3 != value.get('schema_version'):
		raise ValueError('Text claims require schema_version 3; legacy prose remains readable')
	claims = all_claims(value)
	ids = [c.get('id') for c in claims]
	if any((not isinstance(x, str) for x in ids)) or len(ids) != len(set(ids)):
		raise ValueError('Claim IDs must be unique throughout the registry')
	needed = set(collect_claim_closure(identifiers, claim_index(value), include_addresses=True, unknown_prefix='Unknown text claim: '))
	r: dict = {'schema_version': 3, 'facts': []}
	for _, section, item in claim_locations(value):
		if item['id'] in needed:
			r.setdefault(section, []).append(item)
	return r
# @used-by :func:`Df.Harness.lib.text_sources.dfh_check_claim_sources()`
# @used-by :meth:`Df.Harness.Text.ClaimMapValidator.ClaimMapValidator.__load_registry()`
# @used-by :meth:`Df.Harness.Text.IntakeSourceEvaluator.IntakeSourceEvaluator.evaluate()`
# @used-by :meth:`Df.Harness.Text.SourceEvaluator.SourceEvaluator.evaluate()`
def dfh_evidence_inputs(root, value: dict) -> dict[str, str]:
	from agent_tools.evidence import local_file
	result: dict[str, str] = {}
	for claim in all_claims(value):
		for ref in claim.get('evidence', []):
			_collect_ref_inputs(root, ref, result, local_file)
	return result
# @used-by :meth:`Df.Harness.Text.ClaimMapValidator.ClaimMapValidator.__check_claim()`
def dfh_primary_numbers(claim: dict, index: dict, seen=None) -> set[str]:
	seen_set = set() if None is seen else seen
	ident = claim.get('id')
	if ident in seen_set:
		r: set[str] = set()
	else:
		dep_ids = [d.get('claim_id') for d in claim.get('derived_from', []) if isinstance(d, dict) and d.get('claim_id') not in seen_set]
		closure_claims = [claim] + [index[cid] for cid in collect_claim_closure(dep_ids, index) if cid != ident and cid not in seen_set]
		r = set()
		for item in closure_claims:
			corpus = '\n'.join((str(ref.get('quote', '')) for ref in item.get('evidence', [])))
			calculation = item.get('calculation')
			if isinstance(calculation, dict):
				corpus += '\n' + str(calculation.get('result', ''))
			for tok in re.findall('(?<![\\w])\\d+(?:[.,]\\d+)*', corpus):
				norm = tok.replace(',', '.')
				r.add(norm)
				r.update(norm.split('.'))
	return r
# @used-by :func:`Df.Harness.lib.text_sources.dfh_check_claim_sources()`
# @used-by :meth:`Df.Harness.Text.ClaimMapValidator.ClaimMapValidator.__load_registry()`
# @used-by :meth:`Df.Harness.Text.ClaimRegistryStore.ClaimRegistryStore.save()`
# @used-by :meth:`Df.Harness.Text.IntegrityVerifier.IntegrityVerifier.claim_snapshot()`
# @used-by :meth:`Df.Harness.Text.WorkspaceCheckRunner.WorkspaceCheckRunner.__persist_check()`
def dfh_registry_path(root, reference=None) -> Path:
	from agent_tools.path_registry import project_paths
	pp = project_paths(root, exact_root=True)
	kb_resolved = pp.kb_dir.resolve()
	if None is reference or ('ꘖ/KB/TextClaims.json' == reference and kb_resolved != (pp.root / 'ꘖ/KB').resolve() and (not (pp.root / reference).exists())):
		path = (kb_resolved / 'TextClaims.json').resolve()
	else:
		path = dfh_inside(pp.root, reference)
	if not path.is_relative_to(kb_resolved) or '.json' != path.suffix:
		raise ValueError('The text claim registry must be an explicit agent KB JSON file')
	return path
# @used-by :func:`Df.Harness.lib.text_sources._write_attempt_if_newer()`
# @used-by :func:`Df.Harness.lib.text_sources.dfh_source_attempt()`
# @used-by :func:`Df.Harness.lib.text_workflow.dfh_hash_or_none()`
# @used-by :func:`Df.Harness.lib.text_workflow.dfh_record_text_answer()`
# @used-by :func:`Df.Harness.lib.text_workflow.dfh_write_candidate_output()`
# @used-by :func:`_add_local_input()`
# @used-by :meth:`Df.Harness.Text.ClaimMapValidator.ClaimMapValidator.__load_registry()`
# @used-by :meth:`Df.Harness.Text.ClaimMapValidator.ClaimMapValidator.__validate_block_entry()`
# @used-by :meth:`Df.Harness.Text.ClaimRegistryStore.ClaimRegistryStore.__persist()`
# @used-by :meth:`Df.Harness.Text.ClaimRegistryStore.ClaimRegistryStore.save()`
# @used-by :meth:`Df.Harness.Text.IntegrityVerifier.IntegrityVerifier.__add_artifact()`
# @used-by :meth:`Df.Harness.Text.IntegrityVerifier.IntegrityVerifier.__verify_target_artifacts()`
# @used-by :meth:`Df.Harness.Text.IntegrityVerifier.IntegrityVerifier.reconciled_integrity()`
# @used-by :meth:`Df.Harness.Text.SourceEvaluator.SourceEvaluator.__verify_dom_identity()`
# @used-by :meth:`Df.Harness.Text.SourceIntegrityChecker.SourceIntegrityChecker.check()`
# @used-by :meth:`Df.Harness.Text.SourceProber.SourceProber.probe()`
# @used-by :meth:`Df.Harness.Text.SourceReceiptReader.SourceReceiptReader.read()`
# @used-by :meth:`Df.Harness.Text.SourceReceiptStore.SourceReceiptStore.save()`
# @used-by :meth:`Df.Harness.Text.Workspace.Workspace.__gate_applied_receipt()`
# @used-by :meth:`Df.Harness.Text.Workspace.Workspace.__persist_applied()`
# @used-by :meth:`Df.Harness.Text.Workspace.Workspace.__reconcile_if_changed()`
# @used-by :meth:`Df.Harness.Text.Workspace.Workspace.apply()`
# @used-by :meth:`Df.Harness.Text.Workspace.Workspace.operation()`
# @used-by :meth:`Df.Harness.Text.Workspace.Workspace.read_check()`
# @used-by :meth:`Df.Harness.Text.WorkspaceCheckRunner.WorkspaceCheckRunner.__check_replay()`
# @used-by :meth:`Df.Harness.Text.WorkspaceCheckRunner.WorkspaceCheckRunner.__persist_check()`
# @used-by :meth:`Df.Harness.Text.WorkspaceCheckRunner.WorkspaceCheckRunner.run()`
# @used-by :meth:`test_df_harness_s11_wave2c_text_flow.DfHarnessS11Wave2CTextFlowTests.test_claims_sources_and_cli_runner_classes()`
# @used-by :meth:`test_historical_admission.HistoricalAdmissionTests.check_and_review()`
# @used-by :meth:`test_historical_admission.HistoricalAdmissionTests.reconcile_manual_baseline()`
# @used-by :meth:`test_historical_admission.HistoricalAdmissionTests.test_unrelated_registry_revision_and_target_do_not_invalidate_selected_history()`
# @used-by :meth:`test_source_admission.SourceAdmissionTests.test_full_native_review_fixture_requires_and_preserves_source_assessments()`
# @used-by :meth:`test_source_admission.SourceAdmissionTests.test_m5_intake_job_snapshot_source_check_provenance_and_attempt_isolation()`
# @used-by :meth:`test_source_admission.SourceAdmissionTests.test_real_http_failure_and_redirect_are_saved_once_per_base_url()`
# @used-by :meth:`test_source_admission.SourceAdmissionTests.test_valid_dom_capture_identity_can_resolve_the_http_channel_failure()`
# @used-by :meth:`test_text_integration.TextReviewTests.record_fixture()`
# @used-by :meth:`test_text_workflow.TextClaimRevisionTests.test_primary_revision_marks_all_transitive_dependents_stale_and_archives_old_bytes()`
# @used-by :meth:`test_text_workflow.TextTransactionTests.test_formatter_cannot_overwrite_a_document_protected_by_the_operation()`
# @used-by :meth:`test_text_workflow.TextTransactionTests.test_registered_target_cannot_be_overwritten_via_formatter()`
# @used-by :meth:`test_text_workflow.TextTransactionTests.test_unregistered_candidate_output_requires_cas_and_keeps_history()`
# @used-by :meth:`test_text_workflow.TextWorkspaceCase.manifest()`
def dfh_text_digest(data) -> str:
	return df_sha256(data)
# @used-by :meth:`Df.Harness.Text.ClaimMapValidator.ClaimMapValidator.__audit_block()`
# @used-by :meth:`Df.Harness.Text.ClaimMapValidator.ClaimMapValidator.__check_claim()`
# @used-by :meth:`Df.Harness.Text.ClaimMapValidator.ClaimMapValidator.__run_validation()`
# @used-by :meth:`Df.Harness.Text.ClaimMapValidator.ClaimMapValidator.__validate_block_entry()`
# @used-by :meth:`Df.Harness.Text.ClaimMapValidator.ClaimMapValidator.__validate_block_fields()`
# @used-by :meth:`Df.Harness.Text.ClaimMapValidator.ClaimMapValidator.validate()`
def dfh_text_issue(code: str, detail: str, **extra) -> dict:
	return {'code': code, 'message': detail, **extra}
# @used-by :meth:`Df.Harness.Text.ClaimMapValidator.ClaimMapValidator.__check_claim()`
# @used-by :meth:`Df.Harness.Text.ClaimMapValidator.ClaimMapValidator.__validate_block_entry()`
# @used-by :meth:`Df.Harness.Text.ClaimMapValidator.ClaimMapValidator.__validate_block_fields()`
def dfh_text_nonempty(value) -> bool:
	return isinstance(value, str) and bool(value.strip())
