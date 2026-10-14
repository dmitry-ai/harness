"""Evidence-based KB generation: observations are not inferred client facts."""

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re

from .storage import create_bytes
from .upwork_data import canonical_job_url, markdown_fence

SECTIONS = ('identity', 'concerns', 'misconceptions', 'causes', 'methods')
TITLES = ('Идентификация клиента', 'Источники беспокойства', 'Возможные заблуждения',
          'Причины проблемы у этого клиента', 'Способы решения')


def json_bytes(value):
    return (json.dumps(value, ensure_ascii=False, indent=2) + '\n').encode('utf-8')


def create_once(path: Path, content: str):
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists():
        create_bytes(path, content.encode('utf-8'))


def validate_analysis(value: dict) -> None:
    """Check the reviewable claim graph; truth still requires checking its evidence."""
    if not isinstance(value, dict):
        raise ValueError('Analysis must be a JSON object')
    ids, references = set(), []
    for section in SECTIONS:
        items = value.get(section)
        if not isinstance(items, list):
            raise ValueError(f'Analysis requires list: {section}')
        notes = value.get('notes') or {}
        if not isinstance(notes, dict):
            raise ValueError('Analysis notes must be an object')
        if not items and not (isinstance(notes.get(section), str) and notes[section].strip()):
            raise ValueError(f'Empty {section}: explain what is unknown/not established')
        for item in items:
            if not isinstance(item, dict):
                raise ValueError(f'{section}: each claim must be an object')
            ident = item.get('id', '')
            if not re.fullmatch(r'[A-Z][A-Z0-9-]*', ident) or ident in ids:
                raise ValueError(f'Invalid or duplicate claim ID: {ident}')
            ids.add(ident)
            addresses = item.get('addresses', [])
            if not isinstance(addresses, list) or any(not isinstance(x, str) for x in addresses):
                raise ValueError(f'{ident}: addresses must be a list of claim IDs')
            references.extend(addresses)
            score = item.get('score_percent' if section == 'methods' else 'probability_percent')
            if type(score) is not int or not 0 <= score <= 100:
                raise ValueError(f'{ident}: assessment must be an integer from 0 to 100')
            if not all(isinstance(item.get(k), str) and item[k].strip() for k in ('essence', 'assessment_basis')):
                raise ValueError(f'{ident}: essence and assessment_basis are required')
            if section == 'methods' and not (isinstance(item.get('criterion'), str) and item['criterion'].strip()):
                raise ValueError(f'{ident}: method score requires a criterion')
            if section in ('causes', 'methods') and not item.get('addresses'):
                raise ValueError(f'{ident}: link causes to concerns, methods to causes/tasks')
            for side in ('for', 'against'):
                arguments = item.get(side)
                if not isinstance(arguments, list) or not arguments:
                    raise ValueError(f'{ident}: concrete arguments {side} are required')
                for argument in arguments:
                    if not isinstance(argument, dict) or not all(isinstance(argument.get(k), str) and argument[k].strip()
                               for k in ('argument', 'source', 'quote')):
                        raise ValueError(f'{ident}: each argument needs source and exact quote')
                    if argument.get('documentation') and ('#' not in argument['source'] or not argument['source'].split('#', 1)[1]):
                        raise ValueError(f'{ident}: documentation needs a section anchor')
    if set(references) - ids:
        raise ValueError(f'Unknown claim references: {sorted(set(references) - ids)}')
    concerns = {x['id'] for x in value['concerns']}
    causes = {x['id'] for x in value['causes']}
    for item in value['causes']:
        if not set(item['addresses']) & concerns:
            raise ValueError(f'{item["id"]}: cause must address a concern')
    for item in value['methods']:
        if not set(item['addresses']) & (concerns | causes):
            raise ValueError(f'{item["id"]}: method must address a cause or task')


def render_analysis(value: dict) -> str:
    validate_analysis(value)
    lines = []
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
                for argument in item[side]:
                    lines.extend([argument['argument'],
                                  '> ' + argument['quote'].replace('\n', '\n> '),
                                  f'[Источник]({argument["source"]})', ''])
            if key == 'methods':
                lines.append(f'Оценка: {item["score_percent"]}% ({item["criterion"]}).')
            else:
                lines.append(f'Экспертная правдоподобность: {item["probability_percent"]}%.')
            lines.extend([item['assessment_basis'], ''])
    return '\n'.join(lines)


def populate_agent_kb(project_root: Path, data: dict):
    kb = project_root / 'ꘖ' / 'KB'
    evidence = kb / 'Evidence'
    evidence.mkdir(parents=True, exist_ok=True)
    # Paths and cookies are transport state, not source evidence.
    source = {k: v for k, v in data.items() if k not in ('saved_attachments', 'cookies')}
    raw = json_bytes(source)
    fingerprint = hashlib.sha256(raw).hexdigest()
    snapshot = evidence / f'{fingerprint}.json'
    if not snapshot.exists():
        create_bytes(snapshot, raw)
    source_link = f'Evidence/{fingerprint}.json'
    when = data.get('observed_at') or datetime.now(timezone.utc).isoformat(timespec='seconds')
    url = canonical_job_url(data['job_id'])
    manual = project_root / 'KB' / 'Project.md'
    if manual.is_file():
        create_once(kb / 'Project.md', manual.read_bytes().decode('utf-8'))

    buyer = data.get('buyer') or {}
    client = ['# Клиент', '', '## F-CLIENT-1',
              f'Снимок карточки Upwork получен {when}: [вакансия]({url}).', '',
              '## F-CLIENT-2', 'Поля аккаунта в этом снимке; это сведения платформы, а не независимая проверка:',
              '```json', json.dumps(buyer, ensure_ascii=False, indent=2), '```',
              f'[Снимок]({source_link}#/buyer).', '']
    if data.get('client_names'):
        client.extend(['## F-CLIENT-3', 'Совпадения эвристики имён в отзывах; личность заказчика не установлена:',
                       '```json', json.dumps(data['client_names'], ensure_ascii=False, indent=2), '```',
                       f'[Отзывы]({source_link}#/client_names).', ''])
    create_once(kb / 'Client.md', '\n'.join(client))

    website = ['# Сайт', '', '## F-SITE-1',
               'Принадлежность сайта не установлена автоматическим извлечением.',
               'Название папки и найденные URL не являются подтверждением принадлежности.', '',
               '## F-SITE-2', 'Домены, упомянутые в исходных текстах:',
               '```json', json.dumps(data.get('candidate_domains') or [], ensure_ascii=False, indent=2), '```',
               f'[Снимок]({source_link}#/candidate_domains).', '']
    create_once(kb / 'Website.md', '\n'.join(website))
    fence = markdown_fence(data.get('description', ''), '`')
    projects = ['# Проекты', '', '## F-PROJECT-1', f'[Текущая вакансия]({url}).',
                fence + 'markdown', data.get('title', ''), data.get('description', ''), fence,
                f'[Исходный текст]({source_link}#/description).', '', '## F-PROJECT-2',
                'История, фактически возвращённая страницей; связь всех заказов с одним сайтом не установлена.',
                '```json', json.dumps({k: data.get(k) for k in ('work_history', 'open_jobs', 'related_descriptions', 'coverage')},
                                     ensure_ascii=False, indent=2), '```',
                f'[Снимок]({source_link}).', '']
    create_once(kb / 'Projects.md', '\n'.join(projects))
    if data.get('asset_evidence'):
        create_once(kb / 'Evidence.md', '# Вложения\n\n' + '\n'.join(
            f'[{Path(x["file"]).name}]({x["file"]}) — SHA-256 `{x["sha256"]}`.' for x in data['asset_evidence']) + '\n')
    create_once(kb / 'Glossary.md', '# Термины\n\nОпределения добавляются при использовании; каждый термин — со ссылкой на источник.\n')
    create_once(kb / '.md', '# База знаний\n\n'
                '[Клиент](Client.md) · [Сайт](Website.md) · [Проекты](Projects.md) · '
                '[Термины](Glossary.md) · [Первичное описание](Project.md).\n\n'
                'F — наблюдение или цитируемые слова источника; H — гипотеза; M — способ решения.\n'
                'Для H/M: суть, за, против, оценка в %, основание оценки; ссылки ведут к первичным данным.\n')
    return snapshot
