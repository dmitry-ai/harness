"""Create new Upwork workspaces from one capture; preserve existing human/agent work."""

import argparse
from datetime import date, datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import uuid
from zoneinfo import ZoneInfo

from .context import generate as generate_context
from .knowledge import create_once, json_bytes, populate_agent_kb, render_analysis, validate_analysis
from .storage import create_bytes, locked, replace_bytes
from .upwork_data import (canonical_job_url, normalize_job_id, format_kb_project_md,
                          extract_candidate_domains, extract_client_names, resolve_nuxt_devalue)
from .upwork_extract import attachment_path, extract_upwork_job

PRIMARY_AGENTS_DIR = Path(__file__).resolve().parents[2]
WORKSPACE_ROOT = next(p for p in PRIMARY_AGENTS_DIR.parents if (p / 'proposals' / 'daily').is_dir())
DAILY_PROPOSALS_ROOT = WORKSPACE_ROOT / 'proposals' / 'daily'
ANTIGRAVITY_PROJECTS_DIR = Path.home() / '.gemini' / 'config' / 'projects'
ANTIGRAVITY_FOLDERS_JSON = Path(r'C:\work\research\provision\code\Software\Google\AI\Antigravity\primary\tools\Folders\code\folders.json')
MODEL_IDS = {'AA': 'gemini-4-argon-high', 'AF': 'gemini-3.8-flash-high'}


def default_context_config():
    return {'version': 1, 'output': 'ꙮ/0/Context.md', 'sections': [
        {'title': 'Project', 'files': ['.md']},
        {'title': 'Manual KB', 'globs': ['KB/**/*.md'], 'optional': True},
        {'title': 'Agent KB', 'globs': ['ꘖ/KB/**/*.md'], 'optional': True},
        {'title': 'Analysis', 'journals': ['ꙮ/1 - Анализ'], 'optional': True},
        {'title': 'Proposals', 'globs': ['result/**/final/*.md', 'result/**/final.md'], 'optional': True},
        {'title': 'Correspondence', 'optional': True, 'letters': [
            {'root': 'Letters/my', 'author': 'Consultant', 'languages': ['EN', 'RU']},
            {'root': 'Letters/client', 'author': 'Client', 'languages': ['EN', 'RU']}]}]}


def request_day(value=None):
    return date.fromisoformat(value) if value else datetime.now(ZoneInfo('Europe/Istanbul')).date()


def validate_label(value):
    if (not value or len(value) > 120 or value != value.strip().rstrip('.')
            or re.search(r'[\\/:\x00-\x1f<>"|?*]', value)):
        raise ValueError('Project name must be a Windows-safe domain or short topic, without a URL scheme')
    return value


def configure_project(project_root, primary_agents_dir=PRIMARY_AGENTS_DIR, job_url=None, domain_or_topic=None):
    """Declare native discovery. Never delete, relocate, replace or convert existing files."""
    root, primary = Path(project_root).resolve(), Path(primary_agents_dir).resolve()
    agents = root / '.agents'
    if agents.is_symlink() or agents.is_junction():
        raise ValueError('Configuration must be project-local; existing linked directory is preserved')
    agents.mkdir(parents=True, exist_ok=True)
    rules = agents / 'rules'
    if rules.is_symlink() or rules.is_junction():
        raise ValueError('Local rules directory is linked; preserved without conversion')
    rules.mkdir(exist_ok=True)
    for kind in ('rules', 'skills', 'agents'):
        shared = primary / kind
        if not shared.is_dir():
            raise FileNotFoundError(shared)
        manifest = {'entries': [{'path': shared.as_posix()}]}
        create_once(agents / f'{kind}.json', json_bytes(manifest).decode('utf-8'))
    create_once(agents / 'context.json', json_bytes(default_context_config()).decode('utf-8'))
    create_once(rules / '90-project.md', '\n'.join([
        '---', 'trigger: always_on', 'description: "Параметры проекта"', '---', '', '# Проект',
        f'Вакансия: {job_url or "не указана"}.',
        f'Название каталога: `{domain_or_topic or root.name}`; принадлежность домена этим не доказана.',
        'KB и журнал: [KB-1](../../../AI/primary/result/.agents/rules/06-knowledge-base.md).', '']))
    # The shared rules already supply boundaries; local rules contain only this project's parameters.
    local = rules / '90-project.md'
    if local.is_file():
        # No assumptions about how relative file links would resolve in a different depth.
        text = local.read_text(encoding='utf-8')
        if '](../../../AI/' in text:
            local.write_text(text.replace('KB и журнал: [KB-1](../../../AI/primary/result/.agents/rules/06-knowledge-base.md).',
                                          'Пути и границы: общие правила KB-1 и FILE-4.'), encoding='utf-8')
    return agents


def resolve_or_create_project_dir(job_id, domain_or_topic, date_str=None, daily_root=DAILY_PROPOSALS_ROOT):
    job_id, label, day = normalize_job_id(job_id), validate_label(domain_or_topic), request_day(date_str)
    daily = Path(daily_root).resolve()
    state = daily / 'ꘖ' / 'data'
    with locked(state / 'projects.lock'):
        index_file = state / 'projects.json'
        index = json.loads(index_file.read_text(encoding='utf-8')) if index_file.exists() else {}
        if job_id in index:
            target = (daily / index[job_id]).resolve()
            if not target.is_relative_to(daily) or not target.is_dir():
                raise ValueError('Project registry points to a missing or external directory')
            return target
        parent = daily / f'{day.year:04d}' / f'{day.month:02d}' / f'{day.day:02d}'
        parent.mkdir(parents=True, exist_ok=True)
        numbers = []
        for child in parent.iterdir():
            match = re.match(r'^(\d+) - ', child.name)
            if child.is_dir() and match:
                numbers.append(int(match[1]))
                overview = child / '.md'
                if overview.is_file() and canonical_job_url(job_id) in overview.read_text(encoding='utf-8'):
                    index[job_id] = child.relative_to(daily).as_posix()
                    replace_bytes(index_file, json_bytes(index))
                    return child
        target = parent / f'{max(numbers, default=0) + 1} - {label}'
        target.mkdir(exist_ok=False)
        index[job_id] = target.relative_to(daily).as_posix()
        replace_bytes(index_file, json_bytes(index))
        return target


def register_antigravity_project(project_dir, domain_or_topic, date_str=None,
                                projects_dir=ANTIGRAVITY_PROJECTS_DIR,
                                folders_json_path=ANTIGRAVITY_FOLDERS_JSON):
    root, projects = Path(project_dir).resolve(), Path(projects_dir)
    day = request_day(date_str) if date_str else date(int(root.parents[2].name), int(root.parents[1].name), int(root.parent.name))
    name = f'{domain_or_topic} - U.P.{day:%Y.%m.%d}'
    with locked(projects / 'ꘖ' / 'data' / 'registration.lock'):
        ident, payload, destination = None, None, None
        for path in projects.glob('*.json'):
            item = json.loads(path.read_text(encoding='utf-8-sig'))
            resources = (item.get('projectResources') or {}).get('resources') or []
            if any(Path(res.get('folderUri', '')).resolve() == root for res in resources):
                ident, payload, destination = item.get('id') or path.stem, item, path
                break
        if ident is None:
            ident = str(uuid.uuid4())
            destination = projects / f'{ident}.json'
            payload = {'id': ident, 'name': name,
                       'projectResources': {'resources': [{'folderUri': root.as_posix()}]},
                       'settings': {}, 'isWorkspaceOnly': False}
            create_bytes(destination, json_bytes(payload))
        folder_id = None
        folders = Path(folders_json_path)
        if folders.is_file():
            before = folders.read_bytes()
            listing = json.loads(before.decode('utf-8-sig'))
            nodes, assignments = listing.setdefault('folders', []), listing.setdefault('assignments', {})
            parent = None
            for part in ('Upwork', 'Proposals', f'{day.year:04d}', f'{day.month:02d}', f'{day.day:02d}'):
                node = next((x for x in nodes if x['name'] == part and x.get('parentId') == parent), None)
                if node is None:
                    node = {'id': f'folder-{uuid.uuid4().hex[:16]}', 'name': part, 'parentId': parent,
                            'order': max((int(x.get('order', 0)) for x in nodes if x.get('parentId') == parent), default=-1) + 1}
                    nodes.append(node)
                parent = node['id']
            folder_id = parent
            assignments[ident] = parent
            if folders.read_bytes() != before:
                raise RuntimeError('Folders changed concurrently; no external changes overwritten')
            if json_bytes(listing) != before:
                replace_bytes(folders, json_bytes(listing))
        return {'project_id': ident, 'project_name': payload['name'], 'project_file': str(destination), 'folder_id': folder_id}


def initialize_upwork_project(url_or_id, domain_or_topic=None, site_note=None, date_str=None,
                              daily_root=DAILY_PROPOSALS_ROOT, primary_agents_dir=PRIMARY_AGENTS_DIR,
                              cdp_port=9222, extracted_data=None, register_antigravity=None,
                              antigravity_projects_dir=ANTIGRAVITY_PROJECTS_DIR,
                              antigravity_folders_json=ANTIGRAVITY_FOLDERS_JSON, tab_id=None):
    job_id, day = normalize_job_id(url_or_id), request_day(date_str)
    data = extracted_data if extracted_data is not None else extract_upwork_job(job_id, cdp_port=cdp_port, tab_id=tab_id)
    if data.get('job_id') != job_id or not data.get('title') or not data.get('description'):
        raise ValueError('A capture with matching job ID, title and full description is required')
    label = domain_or_topic or ' '.join(re.findall(r'[\w-]+', data['title'])[:5])
    root = resolve_or_create_project_dir(job_id, label, day.isoformat(), daily_root)
    (root / 'ꘖ').mkdir(exist_ok=True)
    with locked(root / 'ꘖ' / 'data' / 'init.lock'):
        state_file = root / 'ꘖ' / 'project.json'
        state = json.loads(state_file.read_text(encoding='utf-8')) if state_file.exists() else {'job_id': job_id, 'initialized': False}
        if state['job_id'] != job_id:
            raise ValueError('Project identity mismatch')
        configure_project(root, primary_agents_dir, canonical_job_url(job_id), label)
        for folder in ('KB', 'ꘖ/KB', 'ꙮ/0', 'ꙮ/1 - Анализ/req', 'ꙮ/1 - Анализ/res'):
            (root / folder).mkdir(parents=True, exist_ok=True)
        if not state['initialized']:
            create_once(root / '.md', f'# {data["title"]}\n{canonical_job_url(job_id)}\n')
            create_once(root / 'KB' / 'Project.md', format_kb_project_md(data, domain=label, site_note=site_note))
        assets = []
        for asset in data.get('saved_attachments') or []:
            source = Path(asset['path'])
            payload = source.read_bytes()
            digest = hashlib.sha256(payload).hexdigest()
            if digest != asset['sha256']:
                raise ValueError(f'Attachment changed after capture: {source}')
            folder = root / 'ꘖ' / 'KB' / 'Evidence' / 'Attachments' / digest
            target = attachment_path(folder, asset['filename'])
            folder.mkdir(parents=True, exist_ok=True)
            if not target.exists():
                create_bytes(target, payload)
            assets.append({'file': target.relative_to(root / 'ꘖ' / 'KB').as_posix(), 'sha256': digest})
        source_data = {**data, 'asset_evidence': assets}
        snapshot = populate_agent_kb(root, source_data, domain=label, site_note=site_note, date_str=day.isoformat())
        state.update(initialized=True, snapshot=str(snapshot.relative_to(root)), request_date=day.isoformat())
        replace_bytes(state_file, json_bytes(state))
        target, _, _ = generate_context(root, root / '.agents/context.json')
    should_register = register_antigravity if register_antigravity is not None else Path(daily_root).resolve() == DAILY_PROPOSALS_ROOT.resolve()
    info = register_antigravity_project(root, root.name.split(' - ', 1)[1],
                                      projects_dir=antigravity_projects_dir,
                                      folders_json_path=antigravity_folders_json) if should_register else None
    return {'project_dir': str(root), 'job_id': job_id, 'domain_or_topic': label,
            'context_path': str(target), 'snapshot': str(snapshot), 'antigravity': info,
            'analysis_status': 'pending; initialization is not a completed analysis'}


def doctor(primary=PRIMARY_AGENTS_DIR):
    primary = Path(primary)
    files = sorted((primary / 'rules').glob('*.md'))
    sizes = {p.name: p.stat().st_size for p in files}
    if not files or any(size >= 24000 for size in sizes.values()):
        raise ValueError('Rules are missing or exceed the 24,000-byte per-file limit')
    if any(not re.search(r'^trigger: always_on\s*$', p.read_text(encoding='utf-8'), re.M) for p in files):
        raise ValueError('Every shared rule must remain always_on')
    return {'rules': len(files), 'rule_bytes': sum(sizes.values()), 'per_file_bytes': sizes,
            'skills': sorted(p.parent.name for p in (primary / 'skills').glob('*/SKILL.md')),
            'models': MODEL_IDS, 'effort': 'high'}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    inspect = sub.add_parser('inspect', help='Capture the selected tab once, including attachments')
    inspect.add_argument('url')
    inspect.add_argument('--output', required=True, type=Path)
    inspect.add_argument('--tab-id')
    inspect.add_argument('--cdp-port', default=9222, type=int)
    init = sub.add_parser('init', help='Initialize from an existing capture without browser requests')
    init.add_argument('url')
    init.add_argument('--from-json', required=True, type=Path)
    init.add_argument('--domain')
    init.add_argument('--date')
    init.add_argument('--daily-root', type=Path, default=DAILY_PROPOSALS_ROOT)
    init.add_argument('--no-register', action='store_true')
    config = sub.add_parser('configure', help='Create missing native manifests; preserve existing configuration')
    config.add_argument('project', type=Path)
    validate = sub.add_parser('validate-analysis', help='Check all five analysis stages and their evidence graph')
    validate.add_argument('input', type=Path)
    validate.add_argument('--render', type=Path)
    sub.add_parser('doctor', help='Check discovery inputs, always_on rules, size and model settings')
    run = sub.add_parser('run-agent', help='Run AA or AF with an explicit native model ID and effort')
    run.add_argument('--role', choices=MODEL_IDS, required=True)
    run.add_argument('--prompt-file', type=Path, required=True)
    run.add_argument('--project', type=Path, required=True)
    run.add_argument('--timeout', type=int, default=600)
    args = parser.parse_args(argv)
    try:
        if args.command == 'doctor':
            result = doctor()
        elif args.command == 'configure':
            result = {'configuration': str(configure_project(args.project))}
        elif args.command == 'inspect':
            if args.output.exists():
                raise FileExistsError('Capture exists; reuse it with init --from-json')
            args.output.parent.mkdir(parents=True, exist_ok=True)
            result = extract_upwork_job(args.url, cdp_port=args.cdp_port, tab_id=args.tab_id,
                                        attachments_dir=args.output.parent / 'attachments')
            create_bytes(args.output, json_bytes(result))
            result = {'capture': str(args.output), 'job_id': result['job_id'], 'coverage': result['coverage']}
        elif args.command == 'init':
            data = json.loads(args.from_json.read_text(encoding='utf-8-sig'))
            for asset in data.get('saved_attachments') or []:
                if not Path(asset['path']).resolve().is_relative_to(args.from_json.parent.resolve()):
                    raise ValueError('Attachment must belong to the capture directory')
            result = initialize_upwork_project(args.url, args.domain, date_str=args.date,
                daily_root=args.daily_root, extracted_data=data,
                register_antigravity=False if args.no_register else None)
        elif args.command == 'validate-analysis':
            value = json.loads(args.input.read_text(encoding='utf-8-sig'))
            rendered = render_analysis(value)
            if args.render:
                args.render.parent.mkdir(parents=True, exist_ok=True)
                create_bytes(args.render, rendered.encode('utf-8'))
            result = {'valid': True, 'claims': sum(len(value[key]) for key in value if key in ('identity', 'concerns', 'misconceptions', 'causes', 'methods'))}
        else:
            command = ['agy', '--model', MODEL_IDS[args.role], '--effort', 'high', '--output-format', 'json',
                       '--print-timeout', f'{args.timeout}s', '--print', args.prompt_file.read_text(encoding='utf-8')]
            if args.role == 'AF':
                command[1:1] = ['--agent', 'af-worker']
            completed = subprocess.run(command, cwd=args.project, timeout=args.timeout + 30)
            return completed.returncode
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    except (OSError, ValueError, KeyError, RuntimeError) as exc:
        print(f'ERROR: {exc}', file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
