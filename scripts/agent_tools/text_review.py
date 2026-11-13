# 2026-11-13 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Consolidate review package reading, verdict recording, quorum checks, and content-addressed immutable receipts across review.py, text_review.py, text_workflow.py, text_sources.py, and storage.py":
# https://github.com/dmitry-ai/harness/issues/63
# 2026-10-20 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Implement /df-article and /df-proposal client-text skills, AI-slop linter, scoped baseline diffs, and semantic § rendering":
# https://github.com/dmitry-ai/harness/issues/13
# 2026-10-31 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Reorganize AI into universal harness repository, translate rules and documentation to English, format per P.md, and enforce issue-driven Git workflow":
# https://github.com/dmitry-ai/harness/issues/26
# 2026-11-03 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Verify saved publication approval independently of current publication policy":
# https://github.com/dmitry-ai/harness/issues/41
from copy import deepcopy
import json
from pathlib import Path
from .research import inside, json_data
from .review import REPORT_CONTRACT, REVIEW_SCHEMA, digest, findings_closed, has_unhandled_verdicts, is_nonempty_text, latest_for_subject, parse_report_object, prepare_verdict_record, quorum_satisfied, read_package_envelope, report_issues, resolve_addressed_reviews, significant_findings, subject_digest, verify_entry_native_proof
from .storage import locked, replace_bytes, write_immutable_bytes
from .text_workflow import _folder, operation, refresh_check
SCOPES = ('format', 'scope', 'evidence', 'relevance', 'kb_consistency', 'response')
TEXT_CHECKS = ('role_and_coverage', 'source_applicability', 'scope_alignment', 'goal_relevance', 'semantic_deduplication', 'numeric_provenance')
def report_contract():
	value = deepcopy(REPORT_CONTRACT)
	value['required_scope'] = list(SCOPES)
	value['claim_review_fields'].append('text_checks')
	value['text_checks'] = {key: 'Authored assessment with concrete evidence and limits.' for key in TEXT_CHECKS}
	value['source_reviews'] = {'required_when': 'The package has external source_checks', 'fields': ['url', 'receipt', 'assessment', 'outcome'], 'outcome': ['supported', 'unsupported'], 'instruction': 'Assess every cited external URL against a verified source receipt and its exact quote/anchor/edition; a reviewer may supply its own candidate-bound receipt.'}
	value['instruction'] = 'Review the exact request, baseline, diff and candidate. Check every substantive statement, including those labelled nonfactual. Test the actual claim, quantifier and scope; give a counterexample. Distinguish product documentation from this site, historical from current measurements, purpose from motive. Read saved primary bytes and fetch primary sources when necessary. Network access is allowed. Do not edit the document, KB, package or previous verdicts. Return one authored JSON report; no default verdict.'
	return value
def _state(root):
	path = _folder(root) / 'reviews.json'
	value = json.loads(path.read_text(encoding='utf-8')) if path.exists() else {'schema_version': 1, 'reviews': []}
	if 1 != value.get('schema_version') or not isinstance(value.get('reviews'), list):
		raise ValueError('Invalid text review history; preserve it for recovery')
	return value
# 2026-10-19 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Prevent reviewer prompt poisoning, enforce read-only reviewer isolation, verify numerical claims, and require multi-template SEO/DNS checks":
# https://github.com/dmitry-ai/harness/issues/12
def prepare(root, check, parent_id, spec=None):
	from .platforms.request_binding import native_project_fields
	root_p, spec_d = (Path(root).resolve(), spec or {})
	if not is_nonempty_text(parent_id):
		raise ValueError('Observed parent conversation ID is required')
	checked, candidate = refresh_check(root_p, check)
	if 'semantic' != checked['coverage']:
		raise ValueError('A mechanical diff is not a substantive review subject')
	op, _ = operation(root_p, checked['operation'])
	flags = spec_d.get('task_flags', [])
	if not isinstance(flags, list) or any((not is_nonempty_text(x) for x in flags)):
		raise ValueError('task_flags must name the current task changes')
	significant = any(('significant' == c['materiality'] for c in checked['claims'])) or bool(set(flags) & {'new_causal_analysis', 'architecture_change', 'pricing_change', 'admin_configuration', 'business_impact', 'material_analysis'})
	if spec_d.get('risk') not in (None, 'routine', 'significant'):
		raise ValueError('Review risk must be routine or significant')
	risk = 'significant' if significant or 'significant' == spec_d.get('risk') else 'routine'
	inputs = checked['inputs']
	value = {'schema_version': REVIEW_SCHEMA, 'kind': 'client_text', 'project_root': str(root_p), **native_project_fields(root_p), 'parent_id': parent_id, 'operation': op['id'], 'check': check, 'scope': list(SCOPES), 'goal': op['goal'], 'requests': op['requests'], 'target': op['target'], 'response': {'file': checked['candidate'], 'sha256': digest(candidate.encode()), 'bytes': len(candidate.encode())}, 'baseline': {'file': (_folder(root_p) / 'operations' / op['id'] / 'base.bin').relative_to(root_p).as_posix(), 'sha256': digest((_folder(root_p) / 'operations' / op['id'] / 'base.bin').read_bytes())}, 'diff': checked['diff'], 'manifest': checked['manifest'], 'claims': checked['claims'], 'claim_versions': checked['claim_versions'], 'kb_inputs': {p: s for p, s in inputs.items() if p.endswith('.json') and '/Evidence/' not in p}, 'evidence_inputs': {p: s for p, s in inputs.items() if not (p.endswith('.json') and '/Evidence/' not in p)}, 'source_checks': checked['source_checks'], 'risk': risk, 'risk_basis': spec_d.get('basis', 'Computed from the actual referenced claim types and current task flags.'), 'task_flags': flags}
	value['subject_sha256'] = subject_digest(value)
	if significant_findings(root_p, _state(root_p), value['subject_sha256']):
		value['risk'] = 'significant'
	raw = json_data(value)
	path = write_immutable_bytes(_folder(root_p) / 'reviews' / (digest(raw) + '-inputs.json'), raw, diff_error='Immutable text review artifact differs')
	return {**value, 'package': path.relative_to(root_p).as_posix(), 'package_sha256': digest(raw), 'required_independent_reviewers': 2 if 'significant' == value['risk'] else 1, 'report_contract': report_contract()}
def read_package(root, reference, *, require_current=True, applied=False):
	root_p, _, value, _ = read_package_envelope(root, reference, expected_kind='client_text', error_msg='Invalid immutable text review package')
	if digest(inside(root_p, value['baseline']['file']).read_bytes()) != value['baseline']['sha256']:
		raise ValueError('Reviewed baseline bytes changed')
	if require_current:
		from .platforms.request_binding import native_project_fields
		if any((value.get(k) != v for k, v in native_project_fields(root_p).items())):
			raise ValueError('Text workspace identity changed')
		checked, _ = refresh_check(root_p, value['check'], applied=applied)
		op, _ = operation(root_p, checked['operation'])
		if checked['inputs'] != {**value['kb_inputs'], **value['evidence_inputs']} or checked['claims'] != value['claims'] or checked['manifest'] != value['manifest'] or (checked['diff'] != value['diff']) or (op['requests'] != value['requests']):
			raise ValueError('Review no longer covers the exact request, diff, claim map or primary versions')
		if 'routine' == value['risk'] and significant_findings(root_p, _state(root_p), value['subject_sha256']):
			raise ValueError('Significant finding requires a new significant package and two independent reviewers')
	return value
def _source_reviews(root, data, package, candidate):
	from .text_sources import read_source_check
	required = {read_source_check(root, candidate, ref)['url'] for ref in package.get('source_checks', [])}
	values = data.get('source_reviews', [])
	if not isinstance(values, list):
		raise ValueError('source_reviews must be an authored list')
	seen, inputs = (set(), {})
	for item in values:
		if not isinstance(item, dict) or item.get('url') not in required or item['url'] in seen or (not is_nonempty_text(item.get('assessment'))) or (item.get('outcome') not in ('supported', 'unsupported')):
			raise ValueError('Assess each exact source URL once with receipt, basis and an explicit outcome')
		observed = read_source_check(root, candidate, item['receipt'])
		if observed['url'] != item['url']:
			raise ValueError('Reviewer source receipt belongs to another URL')
		if 'approved' == data.get('result') and 'supported' != item['outcome']:
			raise ValueError('An unsupported cited source cannot receive publication approval')
		seen.add(item['url'])
		inputs.update(observed['inputs'])
	if 'approved' == data.get('result') and required != seen:
		raise ValueError('Approval needs a receipt-bound assessment of every external source')
	return inputs
def _issues(data, package, candidate, *, root=None):
	issues = report_issues(data, package, candidate=candidate)
	for item in data.get('claim_reviews', []):
		if isinstance(item, dict):
			checks = item.get('text_checks')
			if not isinstance(checks, dict) or any((not is_nonempty_text(checks.get(key)) for key in TEXT_CHECKS)):
				issues.append(str(item.get('claim_id')) + ': assess source applicability, scope, role, relevance, deduplication and numerical provenance')
	if None is not root:
		try:
			_source_reviews(root, data, package, candidate)
		except (OSError, ValueError, KeyError, TypeError) as exc:
			issues.append(str(exc))
	return issues
# 2026-10-19 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Prevent reviewer prompt poisoning, enforce read-only reviewer isolation, verify numerical claims, and require multi-template SEO/DNS checks":
# https://github.com/dmitry-ai/harness/issues/12
def record(root, report, *, parent_id, reviewer_id, native_evidence):
	from .workflow import hashes, now
	root_r = Path(root).resolve()
	prepared = prepare_verdict_record(root_r, report, parent_id=parent_id, reviewer_id=reviewer_id, native_evidence=native_evidence, allow_self=False, package_reader=read_package, issue_checker=lambda d, p, c: _issues(d, p, c, root=root_r), reviews_dir_fn=lambda r_p, sha: _folder(r_p) / 'reviews' / sha, artifact_prefix_fn=lambda _rev, rid: rid, diff_error='Immutable text review artifact differs')
	data, package, ident = (prepared['data'], prepared['package'], prepared['review_id'])
	proof_paths = prepared['proof_paths'] + list(_source_reviews(root_r, data, package, prepared['candidate']))
	with locked(_folder(root_r) / 'review-writer.lock'):
		state = _state(root_r)
		old = {item['id']: item for item in state['reviews']}
		addressed, extra_proofs = resolve_addressed_reviews(root_r, data, package, prepared['independent'], state['reviews'])
		entry = {'schema_version': REVIEW_SCHEMA, 'id': ident, 'package': prepared['package_path'], 'package_sha256': prepared['package_sha'], 'parent_id': parent_id, 'reviewer_id': reviewer_id, 'role': 'AA', 'independent': prepared['independent'], 'risk': package['risk'], 'subject_sha256': package['subject_sha256'], 'result': data['result'], 'report': prepared['report_rel'], 'authored_response': prepared['authored_rel'], 'native_evidence': native_evidence, 'proof': hashes(root_r, proof_paths + extra_proofs), 'dispositions': [], 'addresses_reviews': addressed, 'model_verification': prepared['native'].get('model_verification', 'unverified'), 'time': now()}
		if ident not in old:
			state['reviews'].append(entry)
			replace_bytes(_folder(root_r) / 'reviews.json', json_data(state))
	return entry
# 2026-10-19 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Prevent reviewer prompt poisoning, enforce read-only reviewer isolation, verify numerical claims, and require multi-template SEO/DNS checks":
# https://github.com/dmitry-ai/harness/issues/12
def authorize(root, check, *, applied=False):
	from .workflow import receipt_current
	root_p, state = (Path(root).resolve(), _state(root))
	checked, _ = refresh_check(root_p, check, applied=applied)
	groups, diagnostics = ({}, [])
	for entry in state['reviews']:
		try:
			package = read_package(root_p, entry['package'], applied=applied)
			if package['check'] != check or package['operation'] != checked['operation'] or package['response']['sha256'] != checked['candidate_sha256']:
				continue
			if not receipt_current(root_p, {'inputs': entry['proof']}) or not entry.get('independent'):
				raise ValueError('Independent native review proof changed or is missing')
			data = parse_report_object(inside(root_p, entry['report']).read_text(encoding='utf-8'))
			if _issues(data, package, inside(root_p, package['response']['file']).read_text(encoding='utf-8'), root=root_p):
				raise ValueError('Reviewer assessment is incomplete')
			verify_entry_native_proof(root_p, entry)
			if 'approved' != entry['result'] or not findings_closed(root_p, entry):
				continue
			groups.setdefault(entry['package'], (package, []))[1].append(entry)
		except (OSError, ValueError, KeyError, TypeError) as exc:
			diagnostics.append(str(exc))
	r = None
	for reference, (package, reviews) in reversed(list(groups.items())):
		latest = latest_for_subject(state, package)
		if not has_unhandled_verdicts(root_p, state, package, latest):
			eligible = [entry for entry in reviews if latest[entry['reviewer_id']]['id'] == entry['id']]
			if quorum_satisfied(root_p, state, package, latest, eligible, allow_falsifier_or_cached=False):
				r = {'package': reference, 'package_sha256': digest(inside(root_p, reference).read_bytes()), 'risk': package['risk'], 'subject_sha256': package['subject_sha256'], 'review_ids': [entry['id'] for entry in eligible]}
				break
	if None is r:
		raise ValueError('Current independent text approval is required; significant claims need two reviewers' + (': ' + '; '.join(dict.fromkeys(diagnostics)) if diagnostics else ''))
	return r
def approval_integrity(root, approval, *, versioned_inputs=(), require_live_proof=True):
	root_p = Path(root).resolve()
	if not isinstance(approval, dict) or not isinstance(approval.get('review_ids'), list):
		raise ValueError('Saved publication approval is missing')
	package = read_package(root_p, approval['package'], require_current=False)
	package_file = inside(root_p, approval['package'])
	if digest(package_file.read_bytes()) != approval.get('package_sha256') or package['subject_sha256'] != approval.get('subject_sha256') or package['risk'] != approval.get('risk'):
		raise ValueError('Saved publication approval identity changed')
	inputs = {approval['package']: digest(package_file.read_bytes())}
	for item in (package['response'], package['baseline']):
		inputs[item['file']] = item['sha256']
	entries = {entry['id']: entry for entry in _state(root_p)['reviews']}
	eligible, reviews = (set(), [])
	for ident in approval['review_ids']:
		entry = entries.get(ident)
		if not entry or entry.get('package') != approval['package'] or entry.get('package_sha256') != approval['package_sha256'] or entry.get('subject_sha256') != approval['subject_sha256'] or ('approved' != entry.get('result')) or (not entry.get('independent')):
			raise ValueError('Saved independent publication review changed or is missing')
		for name, expected in entry['proof'].items():
			if name not in versioned_inputs:
				if digest(inside(root_p, name).read_bytes()) != expected:
					raise ValueError('Saved publication review input changed: ' + name)
				inputs[name] = expected
		data = parse_report_object(inside(root_p, entry['report']).read_text(encoding='utf-8'))
		if 'approved' != data.get('result') or data.get('package') != approval['package']:
			raise ValueError('Saved publication review no longer matches its admitted report')
		if require_live_proof:
			if _issues(data, package, inside(root_p, package['response']['file']).read_text(encoding='utf-8')):
				raise ValueError('Saved publication review no longer matches its admitted report')
			verify_entry_native_proof(root_p, entry, error_msg='Saved review differs from its original native response')
		elif entry.get('native_evidence'):
			native_file = inside(root_p, entry['native_evidence'])
			if native_file.exists():
				try:
					native = json.loads(native_file.read_text(encoding='utf-8'))
					if native.get('final_response_sha256') and digest(inside(root_p, entry['authored_response']).read_bytes()) != native.get('final_response_sha256'):
						raise ValueError('Saved review differs from its recorded native response')
				except (json.JSONDecodeError, OSError):
					pass
		eligible.add(entry['reviewer_id'])
		reviews.append(deepcopy(entry))
	if len(eligible) < (2 if 'significant' == package['risk'] else 1):
		raise ValueError('Saved publication approval lacks its required independent reviewers')
	return {'files': inputs, 'reviews': reviews}
