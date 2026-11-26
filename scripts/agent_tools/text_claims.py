# 2026-10-20 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from copy import deepcopy
from pathlib import Path
from urllib.parse import urldefrag, urlsplit
from Df.Core.lib.sha256 import df_sha256
import json
import re
# 2026-11-13
# "Extract ClaimGraphValidator class and unify derived_from DAG traversals, numeric grounding, and primary quote verification across claims.py, text_claims.py, review.py, and evidence.py":
# https://github.com/dmitry-ai/harness/issues/62
from .claims import all_claims, claim_digest, claim_index, claim_locations, collect_claim_closure, contract_issues, evidence_contract_issues, standalone_numbers
from .research import inside, json_data
from .storage import create_bytes, replace_bytes, locked
# 2026-11-14
# "Generalize keyed section numbering (@key), section-reference validation, and profile dispatch across article.py, proposal.py, text_workflow.py, text_claims.py, and text_cli.py":
# https://github.com/dmitry-ai/harness/issues/70
from .text_sections import content_blocks as blocks
# 2026-10-20
# "Implement /df-article and /df-proposal client-text skills, AI-slop linter, scoped baseline diffs, and semantic § rendering":
# https://github.com/dmitry-ai/harness/issues/13
# 2026-10-31
# "Reorganize AI into universal harness repository, translate rules and documentation to English, format per P.md, and enforce issue-driven Git workflow":
# https://github.com/dmitry-ai/harness/issues/26
# 2026-11-26 "Extract general duplicated helpers into Df/Core and Df/Qa": https://github.com/dmitry-ai/harness/issues/378
# @used-by :func:`agent_tools.text_sources._attempt()`
# @used-by :func:`agent_tools.text_sources._evaluate()`
# @used-by :func:`agent_tools.text_sources.probe_links()`
# @used-by :func:`agent_tools.text_sources.read_source_check()`
# @used-by :func:`agent_tools.text_sources.save_source_check()`
# @used-by :func:`agent_tools.text_sources.source_integrity()`
# @used-by :func:`agent_tools.text_workflow._hash_or_none()`
# @used-by :func:`agent_tools.text_workflow.record_answer()`
# @used-by :func:`agent_tools.text_workflow.write_candidate_output()`
# @used-by :func:`evidence_inputs()`
# @used-by :func:`save_registry()`
# @used-by :func:`validate_map()`
# @used-by :meth:`agent_tools.text_workflow.ClientTextWorkspace._check_replay()`
# @used-by :meth:`agent_tools.text_workflow.ClientTextWorkspace._gate_target()`
# @used-by :meth:`agent_tools.text_workflow.ClientTextWorkspace.apply()`
# @used-by :meth:`agent_tools.text_workflow.ClientTextWorkspace.begin()`
# @used-by :meth:`agent_tools.text_workflow.ClientTextWorkspace.check()`
# @used-by :meth:`agent_tools.text_workflow.ClientTextWorkspace.operation()`
# @used-by :meth:`agent_tools.text_workflow.ClientTextWorkspace.read_check()`
# @used-by :meth:`agent_tools.text_workflow.TextIntegrityVerifier._add_artifact()`
# @used-by :meth:`agent_tools.text_workflow.TextIntegrityVerifier.reconciled_integrity()`
# @used-by :meth:`agent_tools.text_workflow.TextIntegrityVerifier.verify()`
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
def digest(data):
	return df_sha256(data)
# @used-by :func:`validate_map()`
def _nonempty(value):
	return isinstance(value, str) and bool(value.strip())
# @used-by :func:`validate_map()`
def _issue(code, detail, **extra):
	return {'code': code, 'message': detail, **extra}
# 2026-11-19
# "Wire project path overlays across Harness subsystems with paths CLI and regression tests":
# https://github.com/dmitry-ai/harness/issues/96
# @used-by :func:`agent_tools.text_sources.check_claim_sources()`
# @used-by :func:`save_registry()`
# @used-by :func:`validate_map()`
# @used-by :meth:`agent_tools.text_workflow.ClientTextWorkspace.check()`
# @used-by :meth:`agent_tools.text_workflow.TextIntegrityVerifier.claim_snapshot()`
def registry_path(root, reference=None):
	from .path_registry import project_paths
	pp = project_paths(root, exact_root=True)
	kb_resolved = pp.kb_dir.resolve()
	if None is reference or ('ꘖ/KB/TextClaims.json' == reference and kb_resolved != (pp.root / 'ꘖ/KB').resolve() and (not (pp.root / reference).exists())):
		path = (kb_resolved / 'TextClaims.json').resolve()
	else:
		path = inside(pp.root, reference)
	if not path.is_relative_to(kb_resolved) or '.json' != path.suffix:
		raise ValueError('The text claim registry must be an explicit agent KB JSON file')
	r = path
	return r
# @used-by :func:`agent_tools.text_sources.check_claim_sources()`
# @used-by :func:`validate_map()`
# @used-by :meth:`agent_tools.text_workflow.ClientTextWorkspace.check()`
# @used-by :meth:`agent_tools.text_workflow.TextIntegrityVerifier.claim_snapshot()`
def subset(value, identifiers):
	if not isinstance(value, dict) or 3 != value.get('schema_version'):
		raise ValueError('Text claims require schema_version 3; legacy prose remains readable')
	claims = all_claims(value)
	ids = [c.get('id') for c in claims]
	if any((not isinstance(x, str) for x in ids)) or len(ids) != len(set(ids)):
		raise ValueError('Claim IDs must be unique throughout the registry')
	# 2026-11-13
	# "Extract ClaimGraphValidator class and unify derived_from DAG traversals, numeric grounding, and primary quote verification across claims.py, text_claims.py, review.py, and evidence.py":
	# https://github.com/dmitry-ai/harness/issues/62
	needed = set(collect_claim_closure(identifiers, claim_index(value), include_addresses=True, unknown_prefix='Unknown text claim: '))
	r = {'schema_version': 3, 'facts': []}
	for _, section, item in claim_locations(value):
		if item['id'] in needed:
			r.setdefault(section, []).append(item)
	return r
# 2026-11-13
# "Extract ClaimGraphValidator class and unify derived_from DAG traversals, numeric grounding, and primary quote verification across claims.py, text_claims.py, review.py, and evidence.py":
# https://github.com/dmitry-ai/harness/issues/62
# @used-by :func:`validate_map()`
def primary_numbers(claim, index, seen=None):
	seen = set() if None is seen else seen
	ident = claim.get('id')
	if ident in seen:
		r = set()
	else:
		dep_ids = [d.get('claim_id') for d in claim.get('derived_from', []) if isinstance(d, dict) and d.get('claim_id') not in seen]
		closure_claims = [claim] + [index[cid] for cid in collect_claim_closure(dep_ids, index) if cid != ident and cid not in seen]
		values = set()
		for item in closure_claims:
			corpus = '\n'.join((str(ref.get('quote', '')) for ref in item.get('evidence', [])))
			calculation = item.get('calculation')
			if isinstance(calculation, dict):
				corpus += '\n' + str(calculation.get('result', ''))
			for tok in re.findall('(?<![\\w])\\d+(?:[.,]\\d+)*', corpus):
				norm = tok.replace(',', '.')
				values.add(norm)
				values.update(norm.split('.'))
		r = values
	return r
# @used-by :func:`agent_tools.text_sources._evaluate()`
# @used-by :func:`agent_tools.text_sources.check_claim_sources()`
# @used-by :func:`validate_map()`
def evidence_inputs(root, value):
	from .evidence import local_file
	result = {}
	# @used-by :func:`evidence_inputs()`
	def add(path):
		path = Path(path).resolve()
		if not path.is_relative_to(Path(root).resolve()) or not path.is_file():
			raise ValueError('Referenced primary artifact is missing or outside the project')
		result[path.relative_to(Path(root).resolve()).as_posix()] = digest(path.read_bytes())
	for claim in all_claims(value):
		for ref in claim.get('evidence', []):
			if ref.get('observation'):
				meta = local_file(root, ref['observation'])
				add(meta)
				add(meta.with_name('response.bin'))
			if not urlsplit(ref.get('source', '')).scheme:
				add(local_file(root, urldefrag(ref['source'])[0]))
			for name in ('manifest', 'experiment'):
				if ref.get(name):
					source = local_file(root, ref[name])
					add(source)
					if 'experiment' == name:
						data = json.loads(source.read_text(encoding='utf-8'))
						for artifact in data.get('artifacts', []):
							if artifact.get('path'):
								add(inside(root, artifact['path']))
	r = result
	return r
# @used-by :meth:`agent_tools.text_workflow.ClientTextWorkspace.check()`
# @used-by :meth:`test_text_workflow.TextMapTests.test_explicit_offer_can_be_nonfactual_without_a_registry()`
# @used-by :meth:`test_text_workflow.TextMapTests.test_numeric_measurement_cannot_come_from_claim_wording_alone()`
# @used-by :meth:`test_text_workflow.TextMapTests.test_stale_block_bytes_or_missing_coverage_fail()`
# @used-by :meth:`test_text_workflow.TextMapTests.test_substantive_paragraph_cannot_be_unmapped_or_unsourced()`
def validate_map(root, text, kind, manifest):
	issues, inputs, mapped, assessment = ([], {}, {}, [])
	if not isinstance(manifest, dict) or 1 != manifest.get('schema_version') or (not isinstance(manifest.get('blocks'), list)):
		r = {'valid': False, 'issues': [_issue('text.map', 'A schema 1 paragraph map is required')], 'inputs': {}, 'claims': [], 'claim_versions': {}}
	else:
		try:
			actual = {block['section']: block for block in blocks(text, kind)}
			for item in manifest['blocks']:
				if not isinstance(item, dict) or not _nonempty(item.get('key')) or (not _nonempty(item.get('section'))):
					issues.append(_issue('text.block', 'Each block needs a stable key and current section'))
					continue
				section, key = (item['section'], item['key'])
				if section in mapped or key in {b['key'] for b in mapped.values()}:
					issues.append(_issue('text.duplicate_key', 'A section and stable key must each occur once', key=key))
					continue
				mapped[section] = item
				block = actual.get(section)
				if not block or digest(block['text'].encode()) != item.get('text_sha256'):
					issues.append(_issue('text.block_version', 'Map does not match exact current block bytes', key=key))
					continue
				if item.get('role') not in ('observation', 'documented', 'inference', 'recommendation', 'context', 'nonfactual'):
					issues.append(_issue('text.role', 'Choose the block role explicitly', key=key))
				if not _nonempty(item.get('goal_basis')) or not _nonempty(item.get('new_content')):
					issues.append(_issue('text.relevance', 'Explain the goal contribution and new information', key=key))
				if not isinstance(item.get('claim_ids'), list) or len(item['claim_ids']) != len(set(item['claim_ids'])):
					issues.append(_issue('text.claims', 'Record unique supporting claim IDs', key=key))
				elif not item['claim_ids'] and 'nonfactual' != item.get('role'):
					issues.append(_issue('text.unsourced', 'A substantive block must identify its KB claims', key=key))
				if 'nonfactual' == item.get('role') and (not _nonempty(item.get('nonfactual_basis'))):
					issues.append(_issue('text.nonfactual', 'A salutation/offer/question needs its exact nonfactual purpose; review confirms this classification', key=key))
			if set(actual) != set(mapped):
				issues.append(_issue('text.coverage', 'Map must cover every content block exactly once', missing=sorted(set(actual) - set(mapped)), extra=sorted(set(mapped) - set(actual))))
			all_ids = {ident for item in mapped.values() for ident in item.get('claim_ids', []) if isinstance(ident, str)}
			value, index, registry = ({'schema_version': 3, 'facts': []}, {}, None)
			if all_ids:
				registry = registry_path(root, manifest.get('registry'))
				whole = json.loads(registry.read_text(encoding='utf-8-sig'))
				value = subset(whole, all_ids)
				issues.extend(contract_issues(value))
				if not issues:
					# 2026-11-13
					# "Extract ClaimGraphValidator class and unify derived_from DAG traversals, numeric grounding, and primary quote verification across claims.py, text_claims.py, review.py, and evidence.py":
					# https://github.com/dmitry-ai/harness/issues/62
					issues.extend(evidence_contract_issues(root, value, skip_structural=True))
				inputs[registry.relative_to(Path(root).resolve()).as_posix()] = digest(registry.read_bytes())
				index = claim_index(value)
				if not issues:
					inputs.update(evidence_inputs(root, value))
			used = {}
			for section, item in mapped.items():
				block = actual.get(section)
				if not block:
					continue
				ids = item.get('claim_ids', [])
				nums = set()
				for ident in ids:
					if ident not in index:
						continue
					claim = index[ident]
					status = claim.get('verification_status')
					if status in ('unverified', 'unavailable', 'stale'):
						issues.append(_issue('text.unverified', 'An unresolved/stale claim cannot support client prose', key=item['key'], claim_id=ident))
					# 2026-10-22
					# "Ban conditional conjunctions in limited claim qualifications and isolate closed admin access from proven public storefront facts":
					# https://github.com/dmitry-ai/harness/issues/15
					if 'limited' == status:
						qualification = item.get('qualification')
						if not _nonempty(qualification) or qualification not in block['prose']:
							issues.append(_issue('text.qualification', 'A limited claim needs its exact visible qualification', key=item['key'], claim_id=ident))
						elif re.search('^(?:if|whether|when|unless|\\u0435\\u0441\\u043b\\u0438|\\u043f\\u0440\\u0438 \\u0443\\u0441\\u043b\\u043e\\u0432\\u0438\\u0438|\\u0432 \\u0441\\u043b\\u0443\\u0447\\u0430\\u0435)\\b', qualification.strip(), re.I):
							issues.append(_issue('text.qualification_lazy', 'A conditional conjunction is not a valid claim qualification; name the technical boundary or operational access restriction', key=item['key'], claim_id=ident))
					nums.update(primary_numbers(claim, index))
					if not (ident in used and 'inference' != item.get('role')):
						used[ident] = item['key']
					elif not _nonempty(item.get('reuse_basis')):
						issues.append(_issue('text.repeat', 'A fact is introduced twice; remove the repetition or justify distinct scope/comparison', key=item['key'], previous=used[ident]))
				missing = standalone_numbers(block['prose']) - nums
				if missing and ids:
					issues.append(_issue('text.number', 'Numeric figures need primary operands or a verified calculation', key=item['key'], numbers=sorted(missing)))
				assessment.append({'claim_id': item['key'], 'essence': block['prose'] or block['text'], 'response_excerpt': block['prose'] or block['text'], 'section': section, 'role': item.get('role'), 'kb_claim_ids': ids, 'kb_claim_versions': {i: claim_digest(index[i]) for i in ids if i in index}, 'qualification': item.get('qualification'), 'goal_basis': item.get('goal_basis'), 'new_content': item.get('new_content'), 'reuse_basis': item.get('reuse_basis'), 'nonfactual_basis': item.get('nonfactual_basis'), 'materiality': 'significant' if any((index[i].get('materiality') in ('significant', 'critical') or 'causal' == index[i].get('category') or set(index[i].get('properties', [])) & {'causality', 'business_impact', 'architecture_change', 'pricing_change', 'admin_configuration'} for i in ids if i in index)) else 'routine'})
		except (ValueError, OSError, KeyError, TypeError) as exc:
			issues.append(_issue('text.map_input', str(exc)))
		r = {'valid': not issues, 'issues': issues, 'inputs': inputs, 'claims': assessment, 'claim_versions': {i: claim_digest(c) for i, c in index.items()} if 'index' in locals() else {}}
	return r
# 2026-11-19
# "Wire project path overlays across Harness subsystems with paths CLI and regression tests":
# https://github.com/dmitry-ai/harness/issues/96
# @used-by :func:`agent_tools.text_cli.main()`
# @used-by :meth:`test_evidence_contract.ClaimGraphValidatorTests.test_collect_claim_closure_and_save_registry_single_structural_pass()`
# @used-by :meth:`test_historical_admission.HistoricalAdmissionTests.test_unrelated_registry_revision_and_target_do_not_invalidate_selected_history()`
# @used-by :meth:`test_path_registry.PathRegistryTests.test_custom_overlay_end_to_end_context_workflow_text_diagnostics_and_completion_canonicalization()`
# @used-by :meth:`test_text_workflow.TextClaimRevisionTests.test_a_self_authored_note_is_not_a_native_reassessment_of_changed_evidence()`
# @used-by :meth:`test_text_workflow.TextClaimRevisionTests.test_primary_revision_marks_all_transitive_dependents_stale_and_archives_old_bytes()`
# @used-by :meth:`test_text_workflow.TextClaimRevisionTests.test_registry_compare_and_swap_never_overwrites_manual_revision()`
# @used-by :meth:`test_text_workflow.TextWorkspaceCase.registry()`
def save_registry(root, candidate, *, expected_sha256=None, reference=None, reassessments=None):
	from .path_registry import project_paths
	pp = project_paths(root, exact_root=True)
	root, value = (pp.root, deepcopy(candidate))
	if not isinstance(value, dict) or 3 != value.get('schema_version'):
		raise ValueError('Text claim registry requires schema_version 3')
	path = registry_path(root, reference)
	with locked(pp.data_dir / 'text-claims.lock'):
		previous = path.read_bytes() if path.exists() else None
		if (digest(previous) if None is not previous else None) != expected_sha256:
			raise ValueError('Claim registry changed; read current bytes and reconcile')
		old = claim_index(json.loads(previous)) if previous else {}
		index = claim_index(value)
		changed = {i for i, c in index.items() if i not in old or claim_digest(c) != claim_digest(old[i])} | set(old) - set(index)
		invalidated, reassessments = ([], reassessments or {})
		pending = set(changed) & set(old)
		while pending:
			current = pending.pop()
			for ident, claim in index.items():
				if ident == current or ident in invalidated or ident not in old:
					continue
				if not any((d.get('claim_id') == current for d in claim.get('derived_from', []))):
					continue
				claim['superseded_dependencies'] = deepcopy(claim.get('derived_from', []))
				claim['verification_status'] = 'stale'
				claim['missing_checks'] = list(dict.fromkeys([*claim.get('missing_checks', []), 'Reassess the changed primary premise: ' + current]))
				invalidated.append(ident)
				pending.add(ident)
		for _ in range(len(index) + 1):
			for ident in invalidated:
				for dep in index[ident].get('derived_from', []):
					if dep.get('claim_id') in index:
						dep['sha256'] = claim_digest(index[dep['claim_id']])
		issues = contract_issues(value)
		if not issues:
			issues = evidence_contract_issues(root, value, skip_structural=True)
		if issues:
			raise ValueError(json.dumps(issues, ensure_ascii=False))
		payload = json_data(value)
		history = pp.data_dir / 'text-claim-history'
		history.mkdir(parents=True, exist_ok=True)
		if None is not previous:
			archive = history / (digest(previous) + '.json')
			if not archive.exists():
				create_bytes(archive, previous)
		if (path.read_bytes() if path.exists() else None) != previous:
			raise ValueError('Claim registry changed during validation; external edit preserved')
		if None is not previous:
			replace_bytes(path, payload)
		else:
			path.parent.mkdir(parents=True, exist_ok=True)
			create_bytes(path, payload)
	r = {'registry': path.relative_to(root).as_posix(), 'sha256': digest(payload), 'changed_claims': sorted(changed), 'invalidated_claims': sorted(invalidated), 'detail': 'Dependent text approvals are checked against exact claim revisions before use'}
	return r
