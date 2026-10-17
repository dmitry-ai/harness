"""Evidence-based KB generation: observations are not inferred client facts."""

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re

from .storage import create_bytes, replace_bytes
from .upwork_data import (
    canonical_job_url,
    classify_attachment,
    detect_client_videos,
    extract_attachment_markdown,
    extract_loom_video,
    format_kb_project_md,
    markdown_fence,
    structure_job_description,
)

from .analysis import SECTIONS, TITLES, validate_analysis, render_analysis, publish_owned


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


def sync_source_folder_attachments(project_root: Path, saved_attachments: list[dict] | None = None,
                                   asset_evidence: list[dict] | None = None) -> list[dict]:
    """Ensure every client-attached file is stored in both <project_root>/source/ and ꘖ/KB/Evidence/Attachments/."""
    from .upwork_extract import attachment_path
    root = Path(project_root).resolve()
    kb_dir = root / 'ꘖ' / 'KB'
    att_root = kb_dir / 'Evidence' / 'Attachments'
    source_dir = root / 'source'
    assets: list[dict] = []
    seen_digests: set[str] = set()

    def register_bytes(filename: str, payload: bytes, expected_sha: str | None = None):
        digest = hashlib.sha256(payload).hexdigest()
        if expected_sha and digest != expected_sha:
            raise ValueError(f'Attachment changed after capture: {filename}')
        folder = att_root / digest
        target = attachment_path(folder, filename)
        folder.mkdir(parents=True, exist_ok=True)
        if not target.exists():
            create_bytes(target, payload)
        source_dir.mkdir(parents=True, exist_ok=True)
        src_target = attachment_path(source_dir, target.name)
        if src_target.exists() and src_target.read_bytes() != payload:
            stem, suf = src_target.stem, src_target.suffix
            idx = 2
            while True:
                cand = source_dir / f'{stem} ({idx}){suf}'
                if not cand.exists() or cand.read_bytes() == payload:
                    src_target = cand
                    break
                idx += 1
        if not src_target.exists():
            create_bytes(src_target, payload)
        if digest not in seen_digests:
            seen_digests.add(digest)
            assets.append({
                'file': target.relative_to(kb_dir).as_posix(),
                'sha256': digest,
                'filename': target.name,
                'source_file': src_target.relative_to(root).as_posix(),
            })

    for item in saved_attachments or []:
        src_path = Path(item['path'])
        fname = item.get('filename') or item.get('name') or src_path.name
        register_bytes(fname, src_path.read_bytes(), item.get('sha256'))

    for item in asset_evidence or []:
        rel_file = item.get('file')
        if not rel_file:
            continue
        target = kb_dir / rel_file
        if target.is_file():
            register_bytes(target.name, target.read_bytes(), item.get('sha256'))

    if att_root.is_dir():
        for sha_dir in sorted(att_root.iterdir()):
            if sha_dir.is_dir() and re.fullmatch(r'[0-9a-f]{64}', sha_dir.name):
                for f in sorted(sha_dir.iterdir()):
                    if f.is_file():
                        register_bytes(f.name, f.read_bytes(), sha_dir.name)

    if source_dir.is_dir():
        for f in sorted(source_dir.iterdir()):
            if f.is_file():
                register_bytes(f.name, f.read_bytes())

    return assets


def _load_media_descriptions(project_root: Path, overrides: dict | None = None) -> dict[str, str]:
    root = Path(project_root).resolve()
    media_dir = root / 'ꘖ' / 'data' / 'media'
    store_file = media_dir / 'descriptions.json'
    descriptions: dict[str, str] = {}
    if store_file.is_file():
        try:
            loaded = json.loads(store_file.read_text(encoding='utf-8'))
            if isinstance(loaded, dict):
                descriptions.update({str(k): str(v) for k, v in loaded.items() if isinstance(v, str) and v.strip()})
        except Exception:
            pass
    if overrides and isinstance(overrides, dict):
        for k, v in overrides.items():
            if isinstance(v, str) and v.strip():
                descriptions[str(k)] = v.strip()
        media_dir.mkdir(parents=True, exist_ok=True)
        replace_bytes(store_file, json_bytes(descriptions))
    return descriptions


def build_project_extra_sources(project_root: Path, data: dict, assets: list[dict] | None = None,
                                *, fetch_videos: bool = True) -> list[dict]:
    """Build ordered list of extra project sources (attached documents, videos, images) for both KBs."""
    root = Path(project_root).resolve()
    kb_dir = root / 'ꘖ' / 'KB'
    if assets is None:
        assets = sync_source_folder_attachments(root, data.get('saved_attachments'), data.get('asset_evidence'))
    descriptions = _load_media_descriptions(root, data.get('media_descriptions'))

    extra_sources: list[dict] = []
    doc_markdowns: list[str] = []

    for asset in assets:
        target = kb_dir / asset['file']
        if not target.is_file():
            continue
        fname = asset.get('filename') or target.name
        sha = asset['sha256']
        payload = target.read_bytes()
        src_copy = root / 'source' / fname
        if not src_copy.exists():
            src_copy.parent.mkdir(parents=True, exist_ok=True)
            create_bytes(src_copy, payload)
        kind = classify_attachment(fname, payload)
        custom_body = descriptions.get(fname) or descriptions.get(sha)

        if kind == 'document':
            body = custom_body or extract_attachment_markdown(target, payload)
            doc_markdowns.append(body)
            extra_sources.append({
                'kind': 'document',
                'name': fname,
                'heading': f'Описание в `{fname}`',
                'body': body,
                'sha256': sha,
                'file': asset['file'],
                'source_file': asset.get('source_file') or f'source/{fname}',
            })
        elif kind == 'image':
            body = custom_body or ''
            extra_sources.append({
                'kind': 'image',
                'name': fname,
                'heading': f'Описание в `{fname}`',
                'body': body,
                'sha256': sha,
                'file': asset['file'],
                'source_file': asset.get('source_file') or f'source/{fname}',
            })

    videos = detect_client_videos(data.get('description') or '', doc_markdowns, assets)
    media_dir = root / 'ꘖ' / 'data' / 'media'
    for v in videos:
        v_key = v.get('url') or v.get('filename') or v.get('video_id') or ''
        v_key_www = re.sub(r'^https?://(?!www\.)', 'https://www.', v_key) if v_key.startswith('http') else ''
        v_key_nowww = re.sub(r'^https?://www\.', 'https://', v_key) if v_key.startswith('http') else ''
        custom_body = (
            descriptions.get(v_key)
            or (descriptions.get(v_key_www) if v_key_www else None)
            or (descriptions.get(v_key_nowww) if v_key_nowww else None)
            or (descriptions.get(v['video_id']) if v.get('video_id') else None)
            or (descriptions.get(v['filename']) if v.get('filename') else None)
        )
        body = custom_body or ''
        if not body and v.get('kind') == 'loom' and v.get('url'):
            cache_file = media_dir / f"loom-{v['video_id']}.json"
            if cache_file.is_file():
                try:
                    cached = json.loads(cache_file.read_text(encoding='utf-8'))
                    body = cached.get('markdown') or ''
                except Exception:
                    body = ''
            if not body and fetch_videos:
                try:
                    loom_info = extract_loom_video(v['url'])
                    media_dir.mkdir(parents=True, exist_ok=True)
                    replace_bytes(cache_file, json_bytes(loom_info))
                    body = loom_info.get('markdown') or ''
                except Exception:
                    body = ''
        extra_sources.append({
            'kind': 'video',
            'name': v.get('filename') or v.get('url') or v['label'],
            'url': v.get('url'),
            'video_id': v.get('video_id'),
            'sha256': v.get('sha256'),
            'file': next((a['file'] for a in assets if a.get('sha256') == v.get('sha256')), None) if v.get('sha256') else None,
            'source_file': f"source/{v['filename']}" if v.get('filename') else None,
            'heading': v['heading'],
            'body': body,
        })

    return extra_sources


def _render_projects_md(data: dict, url: str, source_link: str, extra_sources: list[dict], project_root: Path | None = None) -> str:
    fence = markdown_fence(data.get('description', ''), '`')
    projects = [
        '# Проекты', '', '## F-PROJECT-1', f'[Текущая вакансия]({url}).',
        fence + 'markdown', data.get('title', ''), data.get('description', ''), fence,
        f'[Исходный текст]({source_link}#/description).', '',
    ]
    for idx, extra in enumerate(extra_sources, start=1):
        ebody = (extra.get('body') or '').strip()
        efence = markdown_fence(ebody, '`')
        projects.extend([
            f'## F-PROJECT-ATTACHMENT-{idx}',
            f"### {extra['heading']}",
        ])
        has_src = bool(extra.get('source_file') and (project_root is None or (project_root / extra['source_file']).is_file()))
        if extra.get('file') and has_src:
            projects.append(f"[Первичный файл](<{extra['file']}>) · [Файл в source](<../../{extra['source_file']}>).")
        elif extra.get('file'):
            projects.append(f"[Первичный файл](<{extra['file']}>).")
        elif extra.get('url'):
            projects.append(f"[Видеоисточник]({extra['url']}).")
        if ebody:
            projects.extend([efence + 'markdown', ebody, efence])
        projects.append('')

    projects.extend([
        '## F-PROJECT-2',
        'История, фактически возвращённая страницей; связь всех заказов с одним сайтом не установлена.',
        '```json',
        json.dumps({k: data.get(k) for k in ('work_history', 'open_jobs', 'related_descriptions', 'coverage')},
                   ensure_ascii=False, indent=2),
        '```',
        f'[Снимок]({source_link}).', '',
    ])
    return '\n'.join(projects)


def _render_evidence_md(asset_evidence: list[dict], extra_sources: list[dict], project_root: Path | None = None) -> str | None:
    if not asset_evidence and not extra_sources:
        return None
    ev_lines = ['# Вложения', '']
    extra_by_sha = {e.get('sha256'): e for e in extra_sources if e.get('sha256')}
    for x in asset_evidence:
        fname = Path(x['file']).name
        sha = x['sha256']
        ev_lines.append(f'## {fname}')
        has_src = project_root is None or (project_root / 'source' / fname).is_file()
        if has_src:
            ev_lines.append(f'[{fname}](<{x["file"]}>) · [source/{fname}](<../../source/{fname}>) — SHA-256 `{sha}`.')
        else:
            ev_lines.append(f'[{fname}](<{x["file"]}>) — SHA-256 `{sha}`.')
        ext = extra_by_sha.get(sha)
        if ext and (ext.get('body') or '').strip():
            ebody = ext['body'].strip()
            bfence = markdown_fence(ebody, '`')
            ev_lines.extend(['', bfence + 'markdown', ebody, bfence])
        ev_lines.append('')
    for e in extra_sources:
        if e.get('kind') == 'video' and e.get('url') and not e.get('sha256'):
            ev_lines.append(f"## {e['heading']}")
            ev_lines.append(f"[{e['url']}]({e['url']}).")
            if (e.get('body') or '').strip():
                ebody = e['body'].strip()
                bfence = markdown_fence(ebody, '`')
                ev_lines.extend(['', bfence + 'markdown', ebody, bfence])
            ev_lines.append('')
    return '\n'.join(ev_lines).rstrip() + '\n'


def populate_agent_kb(project_root: Path, data: dict):
    kb = project_root / 'ꘖ' / 'KB'
    evidence = kb / 'Evidence'
    evidence.mkdir(parents=True, exist_ok=True)
    # Paths, cookies, and derived extra_sources are transport/derived state, not raw capture snapshot.
    source = {k: v for k, v in data.items() if k not in ('saved_attachments', 'cookies', 'extra_sources', 'media_descriptions', 'site_hypothesis')}
    if 'asset_evidence' in source and isinstance(source['asset_evidence'], list):
        source['asset_evidence'] = [{'file': x['file'], 'sha256': x['sha256']} for x in source['asset_evidence']]
    raw = json_bytes(source)
    fingerprint = hashlib.sha256(raw).hexdigest()
    snapshot = evidence / f'{fingerprint}.json'
    if not snapshot.exists():
        create_bytes(snapshot, raw)
    source_link = f'Evidence/{fingerprint}.json'
    when = data.get('observed_at') or datetime.now(timezone.utc).isoformat(timespec='seconds')
    url = canonical_job_url(data['job_id'])

    extra_sources = data.get('extra_sources')
    if extra_sources is None:
        extra_sources = build_project_extra_sources(project_root, data, data.get('asset_evidence'))

    manual = project_root / 'KB' / 'Project.md'
    if manual.is_file():
        create_once(kb / 'Project.md', manual.read_bytes().decode('utf-8'))
    else:
        create_once(kb / 'Project.md', format_kb_project_md({**data, 'extra_sources': extra_sources}))

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

    create_once(kb / 'Projects.md', _render_projects_md(data, url, source_link, extra_sources, project_root))
    ev_md = _render_evidence_md(source.get('asset_evidence') or [], extra_sources, project_root)
    if ev_md is not None:
        create_once(kb / 'Evidence.md', ev_md)
    create_once(kb / 'Glossary.md', '# Термины\n\nОпределения добавляются при использовании; каждый термин — со ссылкой на источник.\n')
    create_once(kb / '.md', '# База знаний\n\n'
                '[Клиент](Client.md) · [Сайт](Website.md) · [Проекты](Projects.md) · '
                '[Термины](Glossary.md) · [Первичное описание](Project.md).\n\n'
                'F — наблюдение или цитируемые слова источника; H — гипотеза; M — способ решения.\n'
                'Для H/M: суть, за, против, оценка в %, основание оценки; ссылки ведут к первичным данным.\n')
    return snapshot


def _replace_section2_in_project_md(existing_md: str, data: dict, extra_sources: list[dict]) -> str:
    """Replace only '# 2. Текущий проект клиента' in KB/Project.md while preserving # 1 and # 3."""
    fresh_md = format_kb_project_md({**data, 'extra_sources': extra_sources})
    m_fresh = re.search(r'(?m)^# 2\. Текущий проект клиента\n(.*?)(?=^# 3\. Прошлые проекты клиента\n|\Z)', fresh_md, re.S)
    if not m_fresh:
        return fresh_md
    sec2_block = '# 2. Текущий проект клиента\n' + m_fresh.group(1)
    m_exist = re.search(r'(?m)^# 2\. Текущий проект клиента\n(.*?)(?=^# 3\. Прошлые проекты клиента\n|\Z)', existing_md, re.S)
    if not m_exist:
        return fresh_md
    return existing_md[:m_exist.start()] + sec2_block + existing_md[m_exist.end():]


def sync_project_attachments_and_kb(project_root: Path, media_descriptions: dict | None = None,
                                    *, fetch_videos: bool = True) -> dict:
    """Synchronize source/ folder, extract all attached documents/videos/images, and update both KBs."""
    root = Path(project_root).resolve()
    pj_file = root / 'ꘖ' / 'project.json'
    if not pj_file.is_file():
        raise ValueError(f'Missing project.json in {root}')
    pj = json.loads(pj_file.read_text(encoding='utf-8'))
    snapshot_path = root / pj['snapshot']
    snapshot_data = json.loads(snapshot_path.read_text(encoding='utf-8'))
    source_link = snapshot_path.relative_to(root / 'ꘖ' / 'KB').as_posix()
    url = canonical_job_url(pj['job_id'])

    assets = sync_source_folder_attachments(root, asset_evidence=snapshot_data.get('asset_evidence'))
    merged_data = {**snapshot_data, 'asset_evidence': assets}
    if media_descriptions:
        merged_data['media_descriptions'] = media_descriptions
    extra_sources = build_project_extra_sources(root, merged_data, assets, fetch_videos=fetch_videos)

    manual_kb = root / 'KB' / 'Project.md'
    agent_kb_proj = root / 'ꘖ' / 'KB' / 'Project.md'
    if manual_kb.is_file():
        updated_proj_md = _replace_section2_in_project_md(manual_kb.read_text(encoding='utf-8'), merged_data, extra_sources)
    else:
        updated_proj_md = format_kb_project_md({**merged_data, 'extra_sources': extra_sources})
    replace_bytes(manual_kb, updated_proj_md.encode('utf-8'))
    replace_bytes(agent_kb_proj, updated_proj_md.encode('utf-8'))

    projects_md = _render_projects_md(merged_data, url, source_link, extra_sources)
    replace_bytes(root / 'ꘖ' / 'KB' / 'Projects.md', projects_md.encode('utf-8'))

    ev_md = _render_evidence_md([{'file': a['file'], 'sha256': a['sha256']} for a in assets], extra_sources)
    if ev_md is not None:
        replace_bytes(root / 'ꘖ' / 'KB' / 'Evidence.md', ev_md.encode('utf-8'))

    return {
        'project_root': str(root),
        'source_files': [a['source_file'] for a in assets],
        'extra_sources': [{'kind': e['kind'], 'name': e['name'], 'heading': e['heading'], 'has_body': bool((e.get('body') or '').strip())} for e in extra_sources],
    }

