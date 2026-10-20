"""Client text uses the existing v3 evidence contract without requiring five analysis stages.

The registry, paragraph map and reviews are service data. No internal IDs are
inserted into the document. Exact excerpts and hashes bind judgments to bytes;
neither an ID nor a successful structural check establishes semantic entailment.
"""

from copy import deepcopy
from pathlib import Path
from urllib.parse import urldefrag, urlsplit
import hashlib
import json
import re

from .claims import (all_claims, claim_locations, claim_index, claim_digest,
                     contract_issues, evidence_contract_issues, standalone_numbers)
from .research import inside, json_data
from .storage import create_bytes, replace_bytes, locked


def digest(data):
    return hashlib.sha256(data).hexdigest()


def _nonempty(value):
    return isinstance(value, str) and bool(value.strip())


def _issue(code, detail, **extra):
    return {'code': code, 'message': detail, **extra}


def registry_path(root, reference='ꘖ/KB/TextClaims.json'):
    path = inside(root, reference)
    if not path.is_relative_to(Path(root).resolve() / 'ꘖ/KB') or path.suffix != '.json':
        raise ValueError('The text claim registry must be an explicit agent KB JSON file')
    return path


def subset(value, identifiers):
    """Validate exactly the referenced closure; unrelated legacy work is not a prerequisite."""
    if not isinstance(value, dict) or value.get('schema_version') != 3:
        raise ValueError('Text claims require schema_version 3; legacy prose remains readable')
    claims = all_claims(value)
    ids = [c.get('id') for c in claims]
    if any(not isinstance(x, str) for x in ids) or len(ids) != len(set(ids)):
        raise ValueError('Claim IDs must be unique throughout the registry')
    index, needed, pending = claim_index(value), set(), list(identifiers)
    while pending:
        ident = pending.pop()
        if ident in needed:
            continue
        if ident not in index:
            raise ValueError('Unknown text claim: ' + str(ident))
        needed.add(ident)
        item = index[ident]
        pending.extend(d.get('claim_id') for d in item.get('derived_from', []) if isinstance(d, dict))
        pending.extend(item.get('addresses', []))
    result = {'schema_version': 3, 'facts': []}
    for _, section, item in claim_locations(value):
        if item['id'] in needed:
            result.setdefault(section, []).append(item)
    return result


def primary_numbers(claim, index, seen=None):
    """Use quoted observations and verified calculations, never the author's essence as proof."""
    seen = set() if seen is None else seen
    if claim['id'] in seen:
        return set()
    seen = seen | {claim['id']}
    corpus = '\n'.join(str(ref.get('quote', '')) for ref in claim.get('evidence', []))
    calculation = claim.get('calculation')
    if isinstance(calculation, dict):
        corpus += '\n' + str(calculation.get('result', ''))
    values = {v.replace(',', '.') for v in re.findall(r'(?<![\w])\d+(?:[.,]\d+)*', corpus)}
    for value in list(values):
        values.update(value.split('.'))
    for dep in claim.get('derived_from', []):
        if dep.get('claim_id') in index:
            values.update(primary_numbers(index[dep['claim_id']], index, seen))
    return values


def evidence_inputs(root, value):
    """Bind the actual referenced bytes, including an HTTP body and provenance metadata."""
    from .evidence import local_file
    result = {}
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
                    if name == 'experiment':
                        data = json.loads(source.read_text(encoding='utf-8'))
                        for artifact in data.get('artifacts', []):
                            if artifact.get('path'):
                                add(inside(root, artifact['path']))
    return result


def blocks(text, kind):
    """Addressable content blocks supplied by the format engine, excluding grouping-only nodes."""
    if kind == 'article':
        from .article import scan, parse_sections
        lines = scan(text)
        sections = parse_sections(lines)
        result = []
        for section in sections:
            body = [line for line in lines if section.line < line.no <= section.end
                    and line.kind not in ('heading', 'anchor', 'blank')]
            if not body:
                continue
            raw = '\n'.join(line.raw for line in body)
            prose = '\n'.join(line.raw for line in body if line.kind == 'prose')
            result.append({'section': section.key, 'line': section.line, 'text': raw, 'prose': prose})
        return result
    if kind == 'proposal':
        from .proposal import parse_blocks
        from .text_core import scan
        lines = scan(text)
        parsed = parse_blocks(lines)
        result = []
        first = parsed[0].line if parsed else len(lines)+1
        preface = [line for line in lines if line.no < first and line.kind != 'blank']
        if preface:
            result.append({'section': 'preface', 'line': preface[0].no,
                           'text': '\n'.join(line.raw for line in preface),
                           'prose': '\n'.join(line.raw for line in preface if line.kind == 'prose')})
        for block in parsed:
            own = [line for line in lines if block.line <= line.no <= block.end and line.kind != 'blank']
            raw = '\n'.join(line.raw for line in own)
            prose = '\n'.join(block.body if line.no == block.line else line.raw
                              for line in own if line.kind == 'prose')
            if raw:
                result.append({'section': block.key, 'line': block.line, 'text': raw, 'prose': prose})
        return result
    if kind != 'letter':
        raise ValueError('Choose article, proposal or letter')
    result = []
    for index, match in enumerate(re.finditer(r'(?ms)\S.*?(?=\n\s*\n|\Z)', text), 1):
        result.append({'section': str(index), 'line': text.count('\n', 0, match.start()) + 1,
                       'text': match.group(), 'prose': match.group()})
    return result


def validate_map(root, text, kind, manifest):
    issues, inputs, mapped, assessment = [], {}, {}, []
    if not isinstance(manifest, dict) or manifest.get('schema_version') != 1 or not isinstance(manifest.get('blocks'), list):
        return {'valid': False, 'issues': [_issue('text.map', 'A schema 1 paragraph map is required')],
                'inputs': {}, 'claims': [], 'claim_versions': {}}
    try:
        actual = {block['section']: block for block in blocks(text, kind)}
        for item in manifest['blocks']:
            if not isinstance(item, dict) or not _nonempty(item.get('key')) or not _nonempty(item.get('section')):
                issues.append(_issue('text.block', 'Each block needs a stable key and current section')); continue
            section, key = item['section'], item['key']
            if section in mapped or key in {b['key'] for b in mapped.values()}:
                issues.append(_issue('text.duplicate_key', 'A section and stable key must each occur once', key=key)); continue
            mapped[section] = item
            block = actual.get(section)
            if not block or digest(block['text'].encode()) != item.get('text_sha256'):
                issues.append(_issue('text.block_version', 'Map does not match exact current block bytes', key=key)); continue
            if item.get('role') not in ('observation', 'documented', 'inference', 'recommendation', 'context', 'nonfactual'):
                issues.append(_issue('text.role', 'Choose the block role explicitly', key=key))
            if not _nonempty(item.get('goal_basis')) or not _nonempty(item.get('new_content')):
                issues.append(_issue('text.relevance', 'Explain the goal contribution and new information', key=key))
            if not isinstance(item.get('claim_ids'), list) or len(item['claim_ids']) != len(set(item['claim_ids'])):
                issues.append(_issue('text.claims', 'Record unique supporting claim IDs', key=key))
            elif not item['claim_ids'] and item.get('role') != 'nonfactual':
                issues.append(_issue('text.unsourced', 'A substantive block must identify its KB claims', key=key))
            if item.get('role') == 'nonfactual' and not _nonempty(item.get('nonfactual_basis')):
                issues.append(_issue('text.nonfactual', 'A salutation/offer/question needs its exact nonfactual purpose; review confirms this classification', key=key))
        if set(actual) != set(mapped):
            issues.append(_issue('text.coverage', 'Map must cover every content block exactly once', missing=sorted(set(actual)-set(mapped)), extra=sorted(set(mapped)-set(actual))))
        all_ids = {ident for item in mapped.values() for ident in item.get('claim_ids', []) if isinstance(ident, str)}
        value, index, registry = {'schema_version': 3, 'facts': []}, {}, None
        if all_ids:
            registry = registry_path(root, manifest.get('registry', 'ꘖ/KB/TextClaims.json'))
            whole = json.loads(registry.read_text(encoding='utf-8-sig'))
            value = subset(whole, all_ids)
            issues.extend(contract_issues(value))
            if not issues:
                issues.extend(evidence_contract_issues(root, value))
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
                if status == 'limited' and (not _nonempty(item.get('qualification')) or item['qualification'] not in block['prose']):
                    issues.append(_issue('text.qualification', 'A limited claim needs its exact visible qualification', key=item['key'], claim_id=ident))
                nums.update(primary_numbers(claim, index))
                if ident in used and item.get('role') != 'inference':
                    if not _nonempty(item.get('reuse_basis')):
                        issues.append(_issue('text.repeat', 'A fact is introduced twice; remove the repetition or justify distinct scope/comparison', key=item['key'], previous=used[ident]))
                else:
                    used[ident] = item['key']
            # Paragraph IDs, versions, URLs and real code identifiers are not measurements.
            missing = standalone_numbers(block['prose']) - nums
            if missing and ids:
                issues.append(_issue('text.number', 'Numeric figures need primary operands or a verified calculation', key=item['key'], numbers=sorted(missing)))
            assessment.append({'claim_id': item['key'], 'essence': block['prose'] or block['text'],
                               'response_excerpt': block['prose'] or block['text'], 'section': section,
                               'role': item.get('role'), 'kb_claim_ids': ids,
                               'kb_claim_versions': {i: claim_digest(index[i]) for i in ids if i in index},
                               'qualification': item.get('qualification'),
                               'goal_basis': item.get('goal_basis'), 'new_content': item.get('new_content'),
                               'reuse_basis': item.get('reuse_basis'), 'nonfactual_basis': item.get('nonfactual_basis'),
                               'materiality': 'significant' if any(index[i].get('materiality') in ('significant', 'critical') or
                                   index[i].get('category') == 'causal' or set(index[i].get('properties', [])) &
                                   {'causality', 'business_impact', 'architecture_change', 'pricing_change', 'admin_configuration'}
                                   for i in ids if i in index) else 'routine'})
    except (ValueError, OSError, KeyError, TypeError) as exc:
        issues.append(_issue('text.map_input', str(exc)))
    return {'valid': not issues, 'issues': issues, 'inputs': inputs, 'claims': assessment,
            'claim_versions': {i: claim_digest(c) for i, c in index.items()} if 'index' in locals() else {}}


def save_registry(root, candidate, *, expected_sha256=None, reference='ꘖ/KB/TextClaims.json', reassessments=None):
    """Versioned facts and automatic transitive staleness; never silently update a conclusion's hash."""
    root, value = Path(root).resolve(), deepcopy(candidate)
    if not isinstance(value, dict) or value.get('schema_version') != 3:
        raise ValueError('Text claim registry requires schema_version 3')
    path = registry_path(root, reference)
    with locked(root / 'ꘖ/data/text-claims.lock'):
        previous = path.read_bytes() if path.exists() else None
        if (digest(previous) if previous is not None else None) != expected_sha256:
            raise ValueError('Claim registry changed; read current bytes and reconcile')
        old = claim_index(json.loads(previous)) if previous else {}
        index = claim_index(value)
        changed = {i for i, c in index.items() if i not in old or claim_digest(c) != claim_digest(old[i])} | (set(old)-set(index))
        invalidated, reassessments = [], reassessments or {}
        pending = set(changed) & set(old)
        while pending:
            current = pending.pop()
            for ident, claim in index.items():
                if ident == current or ident in invalidated or ident not in old:
                    continue
                if not any(d.get('claim_id') == current for d in claim.get('derived_from', [])):
                    continue
                # A parent's annotation or note cannot revalidate changed premises.
                # First persist staleness; a later, separately reviewed revision may
                # restore a supported claim against the new primary versions.
                claim['superseded_dependencies'] = deepcopy(claim.get('derived_from', []))
                claim['verification_status'] = 'stale'
                claim['missing_checks'] = list(dict.fromkeys([*claim.get('missing_checks', []), 'Reassess the changed primary premise: ' + current]))
                invalidated.append(ident)
                pending.add(ident)
        # Stale records retain old dependencies in history; current links identify what must be reassessed.
        for _ in range(len(index)+1):
            for ident in invalidated:
                for dep in index[ident].get('derived_from', []):
                    if dep.get('claim_id') in index:
                        dep['sha256'] = claim_digest(index[dep['claim_id']])
        issues = contract_issues(value) + evidence_contract_issues(root, value)
        if issues:
            raise ValueError(json.dumps(issues, ensure_ascii=False))
        payload = json_data(value)
        history = root / 'ꘖ/data/text-claim-history'
        history.mkdir(parents=True, exist_ok=True)
        if previous is not None:
            archive = history / (digest(previous) + '.json')
            if not archive.exists():
                create_bytes(archive, previous)
        if (path.read_bytes() if path.exists() else None) != previous:
            raise ValueError('Claim registry changed during validation; external edit preserved')
        if previous is None:
            path.parent.mkdir(parents=True, exist_ok=True)
            create_bytes(path, payload)
        else:
            replace_bytes(path, payload)
    return {'registry': path.relative_to(root).as_posix(), 'sha256': digest(payload),
            'changed_claims': sorted(changed), 'invalidated_claims': sorted(invalidated),
            'detail': 'Dependent text approvals are checked against exact claim revisions before use'}
