"""Analysis contracts and owned rendering. No network or model calls."""

from pathlib import Path
import hashlib
import json
import re

from .diagnostics import problem, require_valid
from .storage import create_bytes, data_dir_for, locked, replace_bytes

SECTIONS = ('identity', 'concerns', 'misconceptions', 'causes', 'methods')
TITLES = ('Идентификация клиента', 'Источники беспокойства', 'Возможные заблуждения',
          'Причины проблемы у этого клиента', 'Способы решения')


def analysis_issues(value):
    issues, claims, references = [], {}, []
    def add(code, field, message, ident=None, hint=None):
        issues.append(problem(code, field, message, claim_id=ident, hint=hint))
    if not isinstance(value, dict):
        return [problem('analysis.object', '/', 'Analysis must be a JSON object')]
    if type(value.get('schema_version', 1)) is not int or value.get('schema_version', 1) not in (1, 2):
        add('analysis.version', '/schema_version', 'Supported versions: legacy 1 and 2')
    notes = value.get('notes', {})
    if not isinstance(notes, dict):
        add('analysis.notes', '/notes', 'Analysis notes must be an object'); notes = {}
    registry = value.get('sources', {})
    if not isinstance(registry, dict):
        add('source.registry', '/sources', 'Sources must be an object'); registry = {}
    for source_id, source in registry.items():
        if not isinstance(source, str) or not source.strip():
            add('source.registry', f'/sources/{source_id}', 'Source ID must resolve to a nonempty source URI')
    for section in SECTIONS:
        items = value.get(section)
        if not isinstance(items, list):
            add('analysis.section', '/' + section, f'Analysis requires list: {section}'); continue
        if not items and not (isinstance(notes.get(section), str) and notes[section].strip()):
            add('analysis.empty', '/' + section, 'Explain what is unknown/not established in notes')
        for index, item in enumerate(items):
            field = f'/{section}/{index}'
            if not isinstance(item, dict):
                add('claim.object', field, 'Each claim must be an object'); continue
            ident = item.get('id')
            if not isinstance(ident, str) or not re.fullmatch(r'[A-Z][A-Z0-9-]*', ident) or ident in claims:
                add('claim.id', field + '/id', 'Invalid or duplicate claim ID', str(ident))
            else:
                claims[ident] = section
            for key in ('essence', 'assessment_basis') + (('criterion',) if section == 'methods' else ()):
                if not isinstance(item.get(key), str) or not item[key].strip():
                    add('claim.required', field + '/' + key, f'{key} is required', ident)
            score_key = 'score_percent' if section == 'methods' else 'probability_percent'
            score = item.get(score_key)
            if type(score) is not int or not 0 <= score <= 100:
                add('claim.score', field + '/' + score_key, 'Assessment must be an integer from 0 to 100', ident)
            addresses = item.get('addresses', [])
            if not isinstance(addresses, list) or any(not isinstance(x, str) for x in addresses):
                add('claim.addresses', field + '/addresses', 'addresses must be a list of claim IDs', ident)
            else:
                references.append((field, ident, section, addresses))
                if section in ('causes', 'methods') and not addresses:
                    add('claim.addresses', field + '/addresses', 'Link causes to concerns, methods to causes/tasks', ident)
            for side in ('for', 'against'):
                arguments = item.get(side)
                if not isinstance(arguments, list):
                    add('argument.list', field + '/' + side, f'{side} must be a list', ident); continue
                if not arguments:
                    gap = item.get('counterevidence', {}) if side == 'against' else {}
                    if side != 'against' or not valid_gap(gap):
                        add('argument.empty', field + '/' + side,
                            'Concrete arguments required; empty against needs documented counterevidence status', ident)
                for number, arg in enumerate(arguments):
                    af = f'{field}/{side}/{number}'
                    if not isinstance(arg, dict):
                        add('argument.object', af, 'Each argument must be an object', ident); continue
                    for key in ('argument', 'quote'):
                        if not isinstance(arg.get(key), str) or not arg[key].strip():
                            add('argument.required', af + '/' + key, f'{key} is required', ident)
                    source = source_uri(arg, registry)
                    if not isinstance(source, str) or not source.strip():
                        add('argument.source', af + '/source', 'Needs a source or a resolvable source_id', ident)
                    if arg.get('source') and arg.get('source_id'):
                        add('argument.source', af, 'Use source or source_id, not two competing references', ident)
                    if arg.get('documentation') and isinstance(source, str) and ('#' not in source or not source.split('#', 1)[1]):
                        locator = arg.get('anchor_exception')
                        if not isinstance(locator, dict) or not all(isinstance(locator.get(k), str) and locator[k].strip() for k in ('section', 'observation')):
                            add('documentation.locator', af + '/anchor_exception',
                                'Documentation needs a section anchor or section + saved observation', ident,
                                'collect the page; record its section and observation URI; verify evidence')
    for field, ident, section, addresses in references:
        for target in addresses:
            if target not in claims:
                add('claim.reference', field + '/addresses', f'Unknown claim reference: {target}', ident)
        allowed = ('concerns',) if section == 'causes' else ('concerns', 'causes')
        if section in ('causes', 'methods') and addresses and not any(claims.get(x) in allowed for x in addresses):
            add('claim.reference_kind', field + '/addresses', 'Reference must address a concern or applicable cause', ident)
    from .red_flags import red_flag_issues
    issues.extend(red_flag_issues(value, claims))
    return issues


def valid_gap(gap):
    return (isinstance(gap, dict) and gap.get('status') in ('not_found', 'unavailable')
        and isinstance(gap.get('reviewed_sources'), list) and bool(gap['reviewed_sources'])
        and all(isinstance(x, str) and x.strip() for x in gap['reviewed_sources'])
        and isinstance(gap.get('limitations'), str) and bool(gap['limitations'].strip()))


def source_uri(argument, registry):
    if 'source_id' in argument:
        ident = argument.get('source_id')
        return registry.get(ident) if isinstance(ident, str) and ident else None
    return argument.get('source')


def validate_analysis(value):
    require_valid(analysis_issues(value))


def save_analysis(root, candidate, expected_sha256=None):
    """Commit a schema-valid candidate against the exact current agent draft, with history."""
    from .research import inside
    root = Path(root).resolve()
    candidate = inside(root, candidate)
    value = json.loads(candidate.read_text(encoding='utf-8-sig'))
    validate_analysis(value)
    payload = (json.dumps(value, ensure_ascii=False, indent=2) + '\n').encode()
    target = root / 'ꘖ/KB/Analysis.json'
    target.parent.mkdir(parents=True, exist_ok=True)
    with locked(root / 'ꘖ/data/analysis.lock'):
        previous = target.read_bytes() if target.exists() else None
        if previous is not None and digest(previous) != expected_sha256:
            raise ValueError('Analysis changed or expected hash was not supplied; read current KB and reconcile the candidate')
        if previous is None and expected_sha256 is not None:
            raise ValueError('Expected existing analysis is missing; preserve candidate and inspect state')
        if previous is not None and previous != payload:
            archive = root / 'ꘖ/data/analysis-history' / (digest(previous) + '.json')
            archive.parent.mkdir(parents=True, exist_ok=True)
            if not archive.exists():
                create_bytes(archive, previous)
        if (target.read_bytes() if target.exists() else None) != previous:
            raise ValueError('Analysis changed during commit; external edit preserved')
        if previous is None:
            create_bytes(target, payload)
        elif previous != payload:
            replace_bytes(target, payload)
    return {'target': str(target), 'sha256': digest(payload), 'schema_valid': True,
            'evidence_checked': False, 'detail': 'Update dependent agent KB modules before independent review'}


def iter_arguments(value):
    registry = value.get('sources', {})
    registry = registry if isinstance(registry, dict) else {}
    for section in SECTIONS:
        for index, item in enumerate(value.get(section, []) if isinstance(value.get(section), list) else []):
            if not isinstance(item, dict):
                continue
            for side in ('for', 'against'):
                for number, arg in enumerate(item.get(side, []) if isinstance(item.get(side), list) else []):
                    if isinstance(arg, dict):
                        yield item.get('id'), f'/{section}/{index}/{side}/{number}', arg, source_uri(arg, registry)


def render_analysis(value):
    validate_analysis(value)
    from .red_flags import render_red_flags
    lines = [render_red_flags(value)] if value.get('red_flags') else []
    for number, (key, title) in enumerate(zip(SECTIONS, TITLES), 1):
        lines.extend([f'# {number}. {title}', ''])
        if not value[key]:
            lines.extend([value['notes'][key], ''])
        for item in value[key]:
            lines.extend([f'## {item["id"]}', item['essence'], ''])
            if item.get('addresses'):
                lines.extend(['Основания: ' + ', '.join(f'[{i}](#{i.lower()})' for i in item['addresses']) + '.', ''])
            for side, label in (('for', 'За'), ('against', 'Против')):
                lines.append(f'### {label}')
                for arg in item[side]:
                    source = source_uri(arg, value.get('sources', {}))
                    lines.extend([arg['argument'], '> ' + arg['quote'].replace('\n', '\n> '), f'[Источник]({source})', ''])
                    if arg.get('anchor_exception'):
                        locator = arg['anchor_exception']
                        lines.extend([f'Раздел: {locator["section"]}.', f'[Проверка адреса]({locator["observation"]})', ''])
                if side == 'against' and not item[side]:
                    gap = item['counterevidence']
                    lines.extend([f'Статус контрдоказательств: {gap["status"]}.', gap['limitations'], ''])
                    lines.extend(f'[Рассмотренный источник]({x})' for x in gap['reviewed_sources'])
                    lines.append('')
            if key == 'methods':
                lines.append(f'Оценка: {item["score_percent"]}% ({item["criterion"]}).')
            else:
                lines.append(f'Экспертная правдоподобность: {item["probability_percent"]}%.')
            lines.extend([item['assessment_basis'], ''])
    return '\n'.join(lines)


def publish_analysis(source, target=None):
    """Render the report and synchronize its screening block in the project card."""
    from .red_flags import sync_project_red_flags
    source = Path(source).resolve()
    value = json.loads(source.read_text(encoding='utf-8-sig'))
    result = publish_owned(target or source.with_suffix('.md'), render_analysis(value), source=source)
    # Arbitrary standalone inputs must not mutate an unrelated project card.
    if source.name == 'Analysis.json' and source.parent.name == 'KB' and source.parent.parent.name == 'ꘖ':
        card = sync_project_red_flags(source.parents[2], value)
        result['project_card'] = card
        if card['status'] == 'conflict':
            result['status'] = 'conflict'
    return result


def digest(data):
    return hashlib.sha256(data).hexdigest()


def publish_owned(target, content, *, source=None):
    """Only update bytes previously published by this tool; preserve unknown edits."""
    target = Path(target).resolve()
    payload = content.encode('utf-8') if isinstance(content, str) else content
    state_dir = data_dir_for(target)
    state_file = state_dir / 'rendered.json'
    with locked(state_dir / 'render.lock'):
        receipt = json.loads(state_file.read_text(encoding='utf-8')) if state_file.exists() else {}
        key = str(target)
        previous = target.read_bytes() if target.exists() else None
        expected = receipt.get(key, {}).get('sha256')
        if previous is not None and previous != payload and digest(previous) != expected:
            candidate = state_dir / 'render-candidates' / (digest(key.encode())[:16] + '-' + digest(payload)[:16] + target.suffix)
            candidate.parent.mkdir(parents=True, exist_ok=True)
            if not candidate.exists():
                create_bytes(candidate, payload)
            return {'status': 'conflict', 'target': str(target), 'candidate': str(candidate),
                    'detail': 'Existing file is untracked or changed; preserved for reconciliation'}
        if previous is not None and previous != payload:
            archive = state_dir / 'render-history' / digest(key.encode())[:16] / (digest(previous) + target.suffix)
            archive.parent.mkdir(parents=True, exist_ok=True)
            if not archive.exists():
                create_bytes(archive, previous)
        target.parent.mkdir(parents=True, exist_ok=True)
        if (target.read_bytes() if target.exists() else None) != previous:
            raise ValueError('Target changed during publication; preserve the external edit and retry reconciliation')
        if previous != payload:
            replace_bytes(target, payload)
        if target.read_bytes() != payload:
            raise OSError('Published file failed read-back verification')
        receipt[key] = {'sha256': digest(payload), 'source': str(source) if source else None}
        replace_bytes(state_file, (json.dumps(receipt, ensure_ascii=False, indent=2) + '\n').encode())
    return {'status': 'unchanged' if previous == payload else 'published', 'target': str(target), 'sha256': digest(payload)}
