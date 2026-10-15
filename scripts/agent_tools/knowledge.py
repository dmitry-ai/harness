"""Evidence-based KB generation: observations are not inferred client facts."""

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re

from .storage import create_bytes
from .upwork_data import canonical_job_url, markdown_fence

from .analysis import SECTIONS, TITLES, validate_analysis, render_analysis


def json_bytes(value):
    return (json.dumps(value, ensure_ascii=False, indent=2) + "\n").encode("utf-8")


def create_once(path: Path, content: str):
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists():
        create_bytes(path, content.encode("utf-8"))


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
