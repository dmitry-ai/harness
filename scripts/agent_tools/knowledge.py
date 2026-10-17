"""Evidence-based KB generation: observations are not inferred client facts."""

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re

from .storage import create_bytes
from .upwork_data import canonical_job_url, markdown_fence

from .analysis import SECTIONS, TITLES, validate_analysis, render_analysis


def website_issues(value):
    """A site selection is explicit and linked to identity evidence, never a folder name."""
    from urllib.parse import urlsplit
    from .diagnostics import problem
    if 'websites' not in value:
        return []
    sites = value['websites']
    identities = {claim['id'] for claim in (value.get('identity') or []) if isinstance(claim, dict) and isinstance(claim.get('id'), str)} if isinstance(value.get('identity'), list) else set()
    if not isinstance(sites, list) or not sites:
        return [problem('websites.list', '/websites', 'Record an evidenced website or an explicit unidentified selection')]
    issues = []
    for index, site in enumerate(sites):
        field = f'/websites/{index}'
        if (not isinstance(site, dict) or not isinstance(site.get('basis_id'), str)
                or site['basis_id'] not in identities or site.get('role') not in ('client', 'target')):
            issues.append(problem('websites.basis', field, 'Use client/target and a current identity claim ID'))
            continue
        url = site.get('url')
        if url is not None:
            try:
                if not isinstance(url, str):
                    raise ValueError('Website URL must be a string')
                parsed = urlsplit(url)
                valid = parsed.scheme in ('https', 'http') and parsed.hostname and not parsed.username and not parsed.password and not any(c.isspace() for c in url)
                _ = parsed.port
            except (TypeError, ValueError):
                valid = False
            if not valid:
                issues.append(problem('websites.url', field + '/url', 'Use an HTTP(S) URL or null for an unidentified site'))
    return issues


def sync_website_card(root, value, *, selections=None, check=False):
    from .analysis import digest
    from .project_card import sync_block
    root = Path(root).resolve()
    metadata = root / 'ꘖ/data/rendered.json'
    state = json.loads(metadata.read_bytes()) if metadata.exists() else {}
    cached = state.get(str(root / '.md'), {}).get('managed_blocks', {}).get('websites', {}).get('data')
    selected = selections if selections is not None else value.get('websites', cached)
    if selected is None:
        return {'status': 'unassessed', 'target': str(root / '.md')}
    checked = {**value, 'websites': selected}
    if website_issues(checked):
        raise ValueError(website_issues(checked))
    identities = {claim['id']: (index, claim) for index, claim in enumerate(value['identity'])}
    stored, lines = [], ['## Сайт клиента и проекта', '']
    for site in selected:
        index, claim = identities[site['basis_id']]
        sha = digest(json_bytes(claim))
        if site.get('basis_sha256', sha) != sha:
            return {'status': 'conflict', 'target': str(root / '.md'), 'detail': 'Website identity evidence changed; reassess its explicit selection'}
        label = 'Сайт клиента' if site['role'] == 'client' else 'Целевой сайт проекта'
        url = site.get('url')
        address = f'[{url}]({url})' if url else '**не установлен по доступным данным**'
        probability = claim.get('probability_percent')
        assessment = f' Оценка идентификации: {probability}%.' if probability is not None else ''
        lines.append(f'- **{label}:** {address}.{assessment} [Основание: {claim["id"]}](<ꘖ/KB/Analysis.json#/identity/{index}>).')
        stored.append({'url': url, 'role': site['role'], 'basis_id': site['basis_id'], 'basis_sha256': sha})
    result = sync_block(root, root / '.md', 'websites', '\n'.join(lines) + '\n', position='after-title',
                        check=check, source=root / 'ꘖ/KB/Analysis.json', attributes=stored)
    return result


def sync_initial_website(root, snapshot, hypothesis=None):
    """Show the supplied site at creation; a candidate domain alone proves nothing."""
    from .project_card import sync_block
    root = Path(root).resolve()
    if hypothesis:
        if 'website_url' not in hypothesis:
            return {'status': 'unassessed'}  # Legacy hypothesis; never guess from a label.
        url = hypothesis['website_url']
        site = {'url': url, 'role': 'target', 'basis_id': hypothesis.get('id')}
        issues = website_issues({'identity': [hypothesis], 'websites': [site]})
        if issues:
            raise ValueError(issues)
        address = f'[{url}]({url})' if url else '**не установлен**'
        content = (f'## Сайт клиента и проекта\n\n**Целевой сайт проекта:** {address}. '
                   f'Оценка гипотезы: {hypothesis["probability_percent"]}%. '
                   f'[Основание: {hypothesis["id"]}](KB/Project.md#13-сайт).\n')
        source = root / 'KB/Project.md'
    else:
        source = Path(snapshot).resolve()
        content = ('## Сайт клиента и проекта\n\nURL пока не установлен первичным извлечением; '
                   'идентификация требует анализа. '
                   f'[Исходная вакансия](<{source.relative_to(root).as_posix()}#/description>).\n')
    return sync_block(root, root / '.md', 'websites', content, source=source)


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
