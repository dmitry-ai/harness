"""Create new Upwork workspaces from one capture; preserve existing human/agent work."""

import argparse
import hashlib
import json
from pathlib import Path
import re
import sqlite3
import sys

from .context import generate as generate_context
from .knowledge import create_once, json_bytes, populate_agent_kb, render_analysis, validate_analysis
from .storage import create_bytes, locked, replace_bytes
from .upwork_data import canonical_job_url, normalize_job_id, format_kb_project_md
from .upwork_extract import attachment_path, extract_upwork_job

from .runtime import PRIMARY as PRIMARY_AGENTS_DIR, settings, platform_name, platform_settings, role_settings, request_day, using
from .platforms.antigravity import register_antigravity_project, ANTIGRAVITY_PROJECTS_DIR, ANTIGRAVITY_FOLDERS_JSON
WORKSPACE_ROOT = Path(settings()['workspace_root']).resolve()
DAILY_PROPOSALS_ROOT = WORKSPACE_ROOT / settings()['daily_root']


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





def validate_label(value):
    if (not value or len(value) > 120 or value != value.strip().rstrip('.')
            or re.search(r'[\\/:\x00-\x1f<>"|?*]', value)):
        raise ValueError('Project name must be a Windows-safe domain or short topic, without a URL scheme')
    return value


def configure_project(project_root, primary_agents_dir=PRIMARY_AGENTS_DIR, job_url=None, domain_or_topic=None, *, platform=None):
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
        if kind == 'rules':
            manifest['entries'].append({'path': 'rules'})
        path = agents / f'{kind}.json'
        if path.exists() and not isinstance(json.loads(path.read_text(encoding='utf-8-sig')), dict):
            raise ValueError(f'Native manifest must be a JSON object; preserved: {path}')
        create_once(path, json_bytes(manifest).decode('utf-8'))
    create_once(agents / 'context.json', json_bytes(default_context_config()).decode('utf-8'))
    create_once(rules / '90-project.md', '\n'.join([
        '---', 'trigger: always_on', 'description: "Параметры проекта"', '---', '', '# Проект',
        f'Вакансия: {job_url or "не указана"}.',
        f'Название каталога: `{domain_or_topic or root.name}`; принадлежность домена этим не доказана.',
        'Пути и границы: общие правила KB-1 и FILE-4.', '']))
    from .configuration import configure_codex_project
    configure_codex_project(root, primary, job_url, domain_or_topic)
    return agents


def install_global_customizations(config_dir=None):
    config = Path(config_dir) if config_dir is not None else Path.home() / '.gemini' / 'config'
    result = {}
    with locked(config / 'ꘖ' / 'data' / 'customizations.lock'):
        for kind in ('skills', 'agents'):
            target = config / f'{kind}.json'
            payload = json.loads(target.read_text(encoding='utf-8-sig')) if target.exists() else {'entries': []}
            entry = {'path': (PRIMARY_AGENTS_DIR / kind).as_posix()}
            if entry not in payload.setdefault('entries', []):
                payload['entries'].append(entry)
                replace_bytes(target, json_bytes(payload))
            result[kind] = str(target)
    return result





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





def initialize_upwork_project(url_or_id, domain_or_topic=None, date_str=None,
                              daily_root=DAILY_PROPOSALS_ROOT, primary_agents_dir=PRIMARY_AGENTS_DIR,
                              extracted_data=None, register_antigravity=None,
                              antigravity_projects_dir=ANTIGRAVITY_PROJECTS_DIR,
                              antigravity_folders_json=ANTIGRAVITY_FOLDERS_JSON, site_hypothesis=None,
                              platform=None, register_native=None):
    platform = platform_name(platform)
    job_id, day = normalize_job_id(url_or_id), request_day(date_str)
    if extracted_data is None:
        raise ValueError('Capture once with inspect; initialize from that capture')
    data = extracted_data
    if not isinstance(data, dict):
        raise ValueError('Capture must be a JSON object')
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
        configure_project(root, primary_agents_dir, canonical_job_url(job_id), root.name.split(' - ', 1)[-1], platform=platform)
        for folder in ('KB', 'ꘖ/KB', 'ꙮ/0', 'ꙮ/1 - Анализ/req', 'ꙮ/1 - Анализ/res'):
            (root / folder).mkdir(parents=True, exist_ok=True)
        if not state['initialized']:
            create_once(root / '.md', f'# {data["title"]}\n{canonical_job_url(job_id)}\n')
            create_once(root / 'KB' / 'Project.md', format_kb_project_md(
                {**data, **({'site_hypothesis': site_hypothesis} if site_hypothesis else {})}))
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
        snapshot = populate_agent_kb(root, source_data)
        state.update(initialized=True, snapshot=str(snapshot.relative_to(root)))
        state.setdefault('request_date', day.isoformat())
        replace_bytes(state_file, json_bytes(state))
        target, _, _ = generate_context(root, root / '.agents/context.json')
    should_register = register_native if register_native is not None else register_antigravity
    if should_register is None:
        should_register = Path(daily_root).resolve() == DAILY_PROPOSALS_ROOT.resolve()
    initial_day = state['request_date']
    info = None
    if should_register:
        if platform == 'antigravity':
            info = register_antigravity_project(root, root.name.split(' - ', 1)[1], initial_day,
                projects_dir=antigravity_projects_dir, folders_json_path=antigravity_folders_json)
            save_registration(root, platform, info)
        else:
            info = register_project(root, root.name.split(' - ', 1)[1], initial_day, platform=platform)
    return {'project_dir': str(root), 'job_id': job_id, 'domain_or_topic': label,
            'context_path': str(target), 'snapshot': str(snapshot), 'registration': info, 'platform': platform,
            'antigravity': info if platform == 'antigravity' else None,
            'analysis_status': 'pending; initialization is not a completed analysis'}


def register_project(project, label=None, day=None, *, platform=None):
    from .platforms import adapter
    root = Path(project).resolve()
    if day is None:
        state = json.loads((root / 'ꘖ/project.json').read_text(encoding='utf-8'))
        day = state['request_date']
    label = label or root.name.split(' - ', 1)[-1]
    result = adapter(platform).register(root, label, day)
    save_registration(root, platform_name(platform), result)
    return result


def save_registration(root, platform, result):
    path = root / 'ꘖ/data/registrations.json'
    with locked(root / 'ꘖ/data/registration.lock'):
        receipts = json.loads(path.read_text(encoding='utf-8')) if path.exists() else {}
        receipts[platform] = result
        replace_bytes(path, json_bytes(receipts))


def doctor(primary=PRIMARY_AGENTS_DIR):
    primary = Path(primary)
    files = sorted((primary / 'rules').glob('*.md'))
    sizes = {p.name: p.stat().st_size for p in files}
    if not files or any(size >= 24000 for size in sizes.values()):
        raise ValueError('Rules are missing or exceed the 24,000-byte per-file limit')
    if any(not re.search(r'^trigger: always_on\s*$', p.read_text(encoding='utf-8'), re.M) for p in files):
        raise ValueError('Every shared rule must remain always_on')
    from .operations import COMMANDS
    version_files = sorted(p for p in primary.rglob('*') if p.is_file() and p.suffix in ('.py', '.md', '.json') and '__pycache__' not in p.parts)
    tool_version = hashlib.sha256(b''.join(p.relative_to(primary).as_posix().encode() + hashlib.sha256(p.read_bytes()).digest() for p in version_files)).hexdigest()
    return {'tool_version': tool_version, 'rules': len(files), 'rule_bytes': sum(sizes.values()), 'per_file_bytes': sizes,
            'skills': sorted(p.parent.name for p in (primary / 'skills').glob('*/SKILL.md')),
            'resolved_role_defaults': {role: role_settings(platform_name(), role) for role in ('AA', 'AF')},
            'subagent_policy': platform_settings().get('subagents', {'selection': 'configured_roles'}),
            'surface': platform_settings()['surface'], 'delegation': platform_settings()['delegation'],
            'actual_session_models_verified': False,
            'paths': {'rules': [str(p.resolve()) for p in files], 'reference': str((primary / 'scripts/README-agent-tools.md').resolve()),
                      'analysis_contract': str((primary / 'scripts/agent_tools/analysis.py').resolve()),
                      'workflow_reference': str((primary / 'skills/upwork-init/references/workflow.md').resolve()),
                      'examples': str((primary / 'skills/upwork-init/references').resolve()),
                      'example_files': [str(p.resolve()) for p in sorted((primary / 'skills/upwork-init/references').glob('*.json'))]},
            'workflow_commands': list(COMMANDS), 'internal_knowledge': 'ꘖ/KB',
            'context_purpose': 'complete external export for Gemini DeepThink or another external agent'}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    inspect = sub.add_parser('inspect', help='Capture the selected tab once, including attachments')
    inspect.add_argument('url')
    inspect.add_argument('--output', required=True, type=Path)
    inspect.add_argument('--tab-id')
    inspect.add_argument('--cdp-port', type=int)
    init = sub.add_parser('init', help='Initialize from an existing capture without browser requests')
    init.add_argument('url')
    init.add_argument('--from-json', required=True, type=Path)
    init.add_argument('--domain')
    init.add_argument('--date')
    init.add_argument('--site-hypothesis', type=Path, help='Four-part identity hypothesis with evidence and expert probability')
    init.add_argument('--daily-root', type=Path, default=DAILY_PROPOSALS_ROOT)
    init.add_argument('--no-register', action='store_true')
    config = sub.add_parser('configure', help='Create missing native manifests; preserve existing configuration')
    config.add_argument('project', type=Path)
    register = sub.add_parser('register', help='Register an existing project in Antigravity and its Folders branch')
    register.add_argument('project', type=Path)
    register.add_argument('--domain')
    validate = sub.add_parser('validate-analysis', help='Check all five analysis stages and their evidence graph')
    validate.add_argument('input', type=Path)
    validate.add_argument('--render', type=Path)
    validate.add_argument('--format', choices=('text', 'json'), default='text')
    validate.add_argument('--evidence', action='store_true', help='Verify saved sources and quotes without network requests')
    sub.add_parser('doctor', help='Check discovery inputs, always_on rules, size and model settings')
    sub.add_parser('install-global', help='Register only the shared skill and worker in native global manifests')
    build = sub.add_parser('build-native', help='Generate/check native projections from canonical policy and runtime')
    build.add_argument('--root', type=Path)
    build.add_argument('--check', action='store_true')
    from .operations import COMMANDS, add_parsers, execute, analysis_root
    add_parsers(sub)
    for child in sub.choices.values():
        child.add_argument('--platform', choices=tuple(settings()['platforms']))
        child.add_argument('--codex-profile', choices=tuple(settings()['platforms']['codex']['homes']))
    args = parser.parse_args(argv)
    with using(args.platform, args.codex_profile):
        return run(args)


def run(args):
    from .operations import COMMANDS, execute, analysis_root
    try:
        if args.command in COMMANDS:
            result = execute(args)
            print(json.dumps(result, ensure_ascii=False, indent=2))
            if result.get('valid') is False or result.get('complete') is False or result.get('content_available_for_all') is False or result.get('error') or result.get('status') == 'conflict' or result.get('publication', {}).get('status') == 'conflict':
                return 2
            return 0
        if args.command == 'doctor':
            result = doctor()
        elif args.command == 'build-native':
            from .configuration import build_native
            result = build_native(args.root, check=args.check)
        elif args.command == 'install-global':
            result = install_global_customizations()
        elif args.command == 'configure':
            result = {'configuration': str(configure_project(args.project))}
        elif args.command == 'register':
            if not args.project.is_dir():
                raise FileNotFoundError(args.project)
            result = register_project(args.project, args.domain)
        elif args.command == 'inspect':
            if args.output.exists():
                raise FileExistsError('Capture exists; reuse it with init --from-json')
            args.output.parent.mkdir(parents=True, exist_ok=True)
            result = extract_upwork_job(args.url, cdp_port=args.cdp_port or platform_settings()['browser']['cdp_port'], tab_id=args.tab_id,
                                        attachments_dir=args.output.parent / 'attachments')
            create_bytes(args.output, json_bytes(result))
            result = {'capture': str(args.output), 'job_id': result['job_id'], 'coverage': result['coverage']}
        elif args.command == 'init':
            data = json.loads(args.from_json.read_text(encoding='utf-8-sig'))
            if not isinstance(data, dict):
                raise ValueError('Capture must be a JSON object')
            for asset in data.get('saved_attachments') or []:
                if not Path(asset['path']).resolve().is_relative_to(args.from_json.parent.resolve()):
                    raise ValueError('Attachment must belong to the capture directory')
            result = initialize_upwork_project(args.url, args.domain, date_str=args.date,
                daily_root=args.daily_root, extracted_data=data,
                site_hypothesis=json.loads(args.site_hypothesis.read_text(encoding='utf-8')) if args.site_hypothesis else None,
                register_native=False if args.no_register else None)
        elif args.command == 'validate-analysis':
            value = json.loads(args.input.read_text(encoding='utf-8-sig'))
            from .analysis import analysis_issues, publish_analysis
            issues = analysis_issues(value)
            if args.evidence and isinstance(value, dict):
                from .evidence import evidence_issues
                issues.extend(evidence_issues(analysis_root(args.input), value))
            for issue in issues:
                if not issue.get('file'):
                    issue['file'] = str(args.input.resolve())
            result = {'valid': not issues, 'issues': issues, 'evidence_checked': args.evidence, 'semantic_truth_verified': False}
            if issues:
                if args.format == 'json':
                    print(json.dumps(result, ensure_ascii=False, indent=2))
                else:
                    print('\n'.join(f"{x['code']} {x.get('claim_id', '')} {x['field']}: {x['message']}" for x in issues))
                return 1
            if args.render:
                result['publication'] = publish_analysis(args.input, args.render)
                if result['publication']['status'] == 'conflict':
                    print(json.dumps(result, ensure_ascii=False, indent=2)); return 2
            result['claims'] = sum(len(value[key]) for key in ('identity', 'concerns', 'misconceptions', 'causes', 'methods'))
        print(json.dumps(result, ensure_ascii=False, indent=2))
        if result.get('valid') is False or result.get('complete') is False or (result.get('registration') or {}).get('complete') is False:
            return 2
        return 0
    except (OSError, ValueError, KeyError, TypeError, RuntimeError, sqlite3.Error) as exc:
        if args.command in COMMANDS or getattr(args, 'format', None) == 'json':
            print(json.dumps({'valid': False, 'issues': [{'code': 'operation.input', 'field': '/', 'message': str(exc)}]}, ensure_ascii=False, indent=2))
        else:
            print(f'ERROR: {type(exc).__name__}: {exc}', file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
