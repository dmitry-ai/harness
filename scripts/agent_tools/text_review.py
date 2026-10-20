"""Independent, immutable reviews for a standalone article, proposal or letter.

Authorship, report assessments and verdict handling reuse the analysis review
engine. Only the subject and state differ: no five-stage analysis is required.
"""

from copy import deepcopy
from pathlib import Path
import json

from .research import inside, json_data
from .storage import locked, replace_bytes
from .text_claims import digest
from .text_workflow import _folder, _immutable, operation, refresh_check
from .review import (REVIEW_SCHEMA, REPORT_CONTRACT, _text, _report_object,
                     report_issues, authenticate_report, subject_digest,
                     _latest_for_subject, _unhandled_verdicts, _findings_closed,
                     significant_findings)

SCOPES = ('format', 'scope', 'evidence', 'relevance', 'kb_consistency', 'response')
TEXT_CHECKS = ('role_and_coverage', 'source_applicability', 'scope_alignment',
               'goal_relevance', 'semantic_deduplication', 'numeric_provenance')


def report_contract():
    value = deepcopy(REPORT_CONTRACT)
    value['required_scope'] = list(SCOPES)
    value['claim_review_fields'].append('text_checks')
    value['text_checks'] = {key: 'Authored assessment with concrete evidence and limits.' for key in TEXT_CHECKS}
    value['instruction'] = ('Review the exact request, baseline, diff and candidate. Check every substantive statement, '
        'including those labelled nonfactual. Test the actual claim, quantifier and scope; give a counterexample. '
        'Distinguish product documentation from this site, historical from current measurements, purpose from motive. '
        'Read saved primary bytes and fetch primary sources when necessary. Network access is allowed. '
        'Do not edit the document, KB, package or previous verdicts. Return one authored JSON report; no default verdict.')
    return value


def _state(root):
    path = _folder(root) / 'reviews.json'
    value = json.loads(path.read_text(encoding='utf-8')) if path.exists() else {'schema_version': 1, 'reviews': []}
    if value.get('schema_version') != 1 or not isinstance(value.get('reviews'), list):
        raise ValueError('Invalid text review history; preserve it for recovery')
    return value


def prepare(root, check, parent_id, spec=None):
    from .platforms.request_binding import native_project_fields
    root, spec = Path(root).resolve(), spec or {}
    if not _text(parent_id):
        raise ValueError('Observed parent conversation ID is required')
    checked, candidate = refresh_check(root, check)
    if checked['coverage'] != 'semantic':
        raise ValueError('A mechanical diff is not a substantive review subject')
    op, _ = operation(root, checked['operation'])
    flags = spec.get('task_flags', [])
    if not isinstance(flags, list) or any(not _text(x) for x in flags):
        raise ValueError('task_flags must name the current task changes')
    significant = any(c['materiality'] == 'significant' for c in checked['claims']) or bool(set(flags) & {
        'new_causal_analysis', 'architecture_change', 'pricing_change', 'admin_configuration', 'business_impact', 'material_analysis'})
    if spec.get('risk') not in (None, 'routine', 'significant'):
        raise ValueError('Review risk must be routine or significant')
    risk = 'significant' if significant or spec.get('risk') == 'significant' else 'routine'
    inputs = checked['inputs']
    value = {'schema_version': REVIEW_SCHEMA, 'kind': 'client_text', 'project_root': str(root),
        **native_project_fields(root), 'parent_id': parent_id, 'operation': op['id'], 'check': check,
        'scope': list(SCOPES), 'goal': op['goal'], 'requests': op['requests'], 'target': op['target'],
        'response': {'file': checked['candidate'], 'sha256': digest(candidate.encode()), 'bytes': len(candidate.encode())},
        'baseline': {'file': (_folder(root)/'operations'/op['id']/'base.bin').relative_to(root).as_posix(),
                     'sha256': digest((_folder(root)/'operations'/op['id']/'base.bin').read_bytes())},
        'diff': checked['diff'], 'manifest': checked['manifest'], 'claims': checked['claims'],
        'claim_versions': checked['claim_versions'], 'kb_inputs': {p: s for p, s in inputs.items() if p.endswith('.json') and '/Evidence/' not in p},
        'evidence_inputs': {p: s for p, s in inputs.items() if not (p.endswith('.json') and '/Evidence/' not in p)},
        'source_checks': (checked['manifest'] or {}).get('source_checks', []),
        'risk': risk, 'risk_basis': spec.get('basis', 'Computed from the actual referenced claim types and current task flags.'),
        'task_flags': flags}
    value['subject_sha256'] = subject_digest(value)
    if significant_findings(root, _state(root), value['subject_sha256']):
        value['risk'] = 'significant'
    raw = json_data(value)
    path = _immutable(_folder(root)/'reviews'/(digest(raw)+'-inputs.json'), raw)
    return {**value, 'package': path.relative_to(root).as_posix(), 'package_sha256': digest(raw),
            'required_independent_reviewers': 2 if value['risk'] == 'significant' else 1,
            'report_contract': report_contract()}


def read_package(root, reference, *, require_current=True, applied=False):
    root = Path(root).resolve()
    path = inside(root, reference)
    raw = path.read_bytes()
    value = json.loads(raw)
    if (not isinstance(value, dict) or value.get('kind') != 'client_text' or value.get('schema_version') != REVIEW_SCHEMA
            or path.name != digest(raw)+'-inputs.json' or value.get('project_root') != str(root)
            or value.get('subject_sha256') != subject_digest(value)):
        raise ValueError('Invalid immutable text review package')
    if digest(inside(root, value['response']['file']).read_bytes()) != value['response']['sha256']:
        raise ValueError('Reviewed candidate bytes changed')
    if digest(inside(root, value['baseline']['file']).read_bytes()) != value['baseline']['sha256']:
        raise ValueError('Reviewed baseline bytes changed')
    if require_current:
        from .platforms.request_binding import native_project_fields
        if any(value.get(k) != v for k, v in native_project_fields(root).items()):
            raise ValueError('Text workspace identity changed')
        checked, _ = refresh_check(root, value['check'], applied=applied)
        op, _ = operation(root, checked['operation'])
        if (checked['inputs'] != {**value['kb_inputs'], **value['evidence_inputs']} or checked['claims'] != value['claims']
                or checked['manifest'] != value['manifest'] or checked['diff'] != value['diff'] or op['requests'] != value['requests']):
            raise ValueError('Review no longer covers the exact request, diff, claim map or primary versions')
        if value['risk'] == 'routine' and significant_findings(root, _state(root), value['subject_sha256']):
            raise ValueError('Significant finding requires a new significant package and two independent reviewers')
    return value


def _issues(data, package, candidate):
    issues = report_issues(data, package)
    for item in data.get('claim_reviews', []):
        if not isinstance(item, dict):
            continue
        checks = item.get('text_checks')
        if not isinstance(checks, dict) or any(not _text(checks.get(key)) for key in TEXT_CHECKS):
            issues.append(str(item.get('claim_id'))+': assess source applicability, scope, role, relevance, deduplication and numerical provenance')
        if item.get('outcome') == 'qualified' and item.get('response_qualification', '') not in candidate:
            issues.append('A qualification must occur verbatim in the reviewed document')
    return issues


def record(root, report, *, parent_id, reviewer_id, native_evidence):
    from .workflow import hashes, now
    root = Path(root).resolve()
    source = report if isinstance(report, bytes) else inside(root, report).read_bytes()
    data = _report_object(source.decode('utf-8-sig'))
    reference = data.get('package')
    package = read_package(root, reference)
    package_sha = digest(inside(root, reference).read_bytes())
    if data.get('package_sha256') != package_sha or package['parent_id'] != parent_id:
        raise ValueError('Report package hash or observed parent differs')
    candidate = inside(root, package['response']['file']).read_text(encoding='utf-8')
    issues = _issues(data, package, candidate)
    if issues:
        raise ValueError('\n'.join(issues))
    independent, proof_paths, native, raw = authenticate_report(root, package, reference, data, source,
        parent_id=parent_id, reviewer_id=reviewer_id, native_evidence=native_evidence, allow_self=False)
    ident = digest((package_sha+'\0'+reviewer_id+'\0'+digest(raw)).encode())
    folder = _folder(root)/'reviews'/package_sha
    authored = _immutable(folder/(ident+'-authored.txt'), raw)
    report_path = _immutable(folder/(ident+'-report.json'), json_data(data))
    proof_paths += [authored.relative_to(root).as_posix(), report_path.relative_to(root).as_posix()]
    for finding in data['findings']:
        if finding.get('status') in ('resolved', 'rejected'):
            evidence = finding['evidence'] if isinstance(finding['evidence'], list) else [finding['evidence']]
            proof_paths += [inside(root, item).relative_to(root).as_posix() for item in evidence]
    addresses = data.get('addresses_reviews', [])
    if not isinstance(addresses, list):
        raise ValueError('addresses_reviews must be an authored list')
    with locked(_folder(root)/'review-writer.lock'):
        state = _state(root)
        old = {entry['id']: entry for entry in state['reviews']}
        addressed = []
        for resolution in addresses:
            prior = old.get(resolution.get('review_id')) if isinstance(resolution, dict) else None
            if (data['result'] != 'approved' or not prior or prior['subject_sha256'] != package['subject_sha256']
                    or not _text(resolution.get('basis')) or not isinstance(resolution.get('evidence'), list) or not resolution['evidence']):
                raise ValueError('Only an authored independent approval can resolve an exact prior verdict, with basis and evidence')
            addressed.append(prior['id'])
            proof_paths += [inside(root, item).relative_to(root).as_posix() for item in resolution['evidence']]
        if len(addressed) != len(set(addressed)):
            raise ValueError('Duplicate addressed review')
        entry = {'schema_version': REVIEW_SCHEMA, 'id': ident, 'package': reference, 'package_sha256': package_sha,
            'parent_id': parent_id, 'reviewer_id': reviewer_id, 'role': 'AA', 'independent': independent,
            'risk': package['risk'], 'subject_sha256': package['subject_sha256'], 'result': data['result'],
            'report': report_path.relative_to(root).as_posix(), 'authored_response': authored.relative_to(root).as_posix(),
            'native_evidence': native_evidence, 'proof': hashes(root, proof_paths), 'dispositions': [],
            'addresses_reviews': addressed, 'model_verification': native.get('model_verification', 'unverified'), 'time': now()}
        if ident not in old:
            state['reviews'].append(entry)
            replace_bytes(_folder(root)/'reviews.json', json_data(state))
    return entry


def authorize(root, check, *, applied=False):
    from .workflow import receipt_current
    from .metrics import verify_native_proof
    root, state = Path(root).resolve(), _state(root)
    checked, _ = refresh_check(root, check, applied=applied)
    groups, diagnostics = {}, []
    for entry in state['reviews']:
        try:
            package = read_package(root, entry['package'], applied=applied)
            if (package['check'] != check or package['operation'] != checked['operation']
                    or package['response']['sha256'] != checked['candidate_sha256']):
                continue
            if not receipt_current(root, {'inputs': entry['proof']}) or not entry.get('independent'):
                raise ValueError('Independent native review proof changed or is missing')
            data = _report_object(inside(root, entry['report']).read_text(encoding='utf-8'))
            if _issues(data, package, inside(root, package['response']['file']).read_text(encoding='utf-8')):
                raise ValueError('Reviewer assessment is incomplete')
            native = json.loads(inside(root, entry['native_evidence']).read_text(encoding='utf-8'))
            observed = verify_native_proof(root, native, package=Path(entry['package']).name)
            if digest(inside(root, entry['authored_response']).read_bytes()) != observed.get('final_response_sha256'):
                raise ValueError('Saved report differs from the actual native authored final response')
            if entry['result'] != 'approved' or not _findings_closed(root, entry):
                continue
            groups.setdefault(entry['package'], (package, []))[1].append(entry)
        except (OSError, ValueError, KeyError, TypeError) as exc:
            diagnostics.append(str(exc))
    for reference, (package, reviews) in reversed(list(groups.items())):
        latest = _latest_for_subject(state, package)
        if _unhandled_verdicts(root, state, package, latest):
            continue
        eligible = [entry for entry in reviews if latest[entry['reviewer_id']]['id'] == entry['id']]
        required = 2 if package['risk'] == 'significant' else 1
        if len({entry['reviewer_id'] for entry in eligible}) >= required:
            return {'package': reference, 'package_sha256': digest(inside(root, reference).read_bytes()),
                    'risk': package['risk'], 'subject_sha256': package['subject_sha256'],
                    'review_ids': [entry['id'] for entry in eligible]}
    raise ValueError('Current independent text approval is required; significant claims need two reviewers'
                     + (': '+'; '.join(dict.fromkeys(diagnostics)) if diagnostics else ''))
