"""Remove unused native registrations while keeping the complete daily archive."""

from contextlib import nullcontext
from datetime import datetime, timedelta, timezone
import base64
import json
import os
from pathlib import Path
import re
import sqlite3
from urllib.parse import unquote, urlsplit
from zoneinfo import ZoneInfo

from .runtime import PRIMARY, platform_name, settings
from .storage import create_bytes, locked, replace_bytes


def record_cleanup_answer(body, *, now=None, log_root=None):
    """Publish the actual final answer once, with an Istanbul timestamp."""
    if not isinstance(body, str) or not body.strip():
        raise ValueError('Cleanup answer must not be empty')
    moment = now or datetime.now(timezone.utc)
    if moment.tzinfo is None or moment.utcoffset() is None:
        raise ValueError('Cleanup report time must include a timezone')
    local = moment.astimezone(ZoneInfo('Europe/Istanbul'))
    offset = int(local.utcoffset().total_seconds() / 60)
    hours, minutes = divmod(abs(offset), 60)
    zone = f'UTC{"+" if offset >= 0 else "-"}{hours}' + (f':{minutes:02d}' if minutes else '')
    timestamp = f'{local:%Y-%m-%d %H:%M} {zone}'
    answer = timestamp + '\n\n' + body
    payload = answer.encode('utf-8')
    root = Path(log_root or Path(settings()['workspace_root']) / 'AI/log/cleanup').absolute()
    directory = root / f'{local:%Y/%m}'
    if linked(directory):
        raise ValueError('Cleanup log directory must not be linked')
    directory.mkdir(parents=True, exist_ok=True)
    number = 1
    while True:
        suffix = '' if number == 1 else f'--{number}'
        target = directory / f'{local:%d--%H-%M}{suffix}.md'
        try:
            create_bytes(target, payload)
            break
        except FileExistsError:
            number += 1
    if target.read_bytes() != payload:
        raise OSError('Cleanup answer log read-back mismatch')
    return {'path': str(target), 'timestamp': timestamp, 'answer': answer}


def path_key(value):
    if isinstance(value, os.PathLike):
        value = os.fspath(value)
    if not isinstance(value, str) or not value:
        raise ValueError('Missing workspace path')
    if value.startswith('file:'):
        uri = urlsplit(value)
        value = unquote(uri.path)
        host = unquote(uri.netloc)
        if re.fullmatch(r'[A-Za-z]:', host):
            # Older Antigravity versions emitted file://C:/... without the
            # third slash. It is a local drive, not a UNC server named C:.
            value = host + value
        elif host and host.casefold() != 'localhost':
            value = '//' + host + value
        if re.match(r'^/[A-Za-z]:/', value):
            value = value[1:]
    if value.startswith('\\\\?\\'):
        value = '\\\\' + value[8:] if value.startswith('\\\\?\\UNC\\') else value[4:]
    if not Path(value).is_absolute():
        raise ValueError('Workspace path must be absolute')
    return str(Path(value).resolve()).replace('\\', '/').rstrip('/').casefold()


def linked(path):
    return any(p.is_symlink() or p.is_junction() for p in (path, *path.parents))


def _json(path):
    if linked(path):
        raise ValueError(f'Linked store preserved: {path}')
    value = json.loads(path.read_text(encoding='utf-8-sig'))
    if not isinstance(value, dict):
        raise ValueError(f'Expected a JSON object: {path}')
    return value


def _age(root, state, config):
    if state.get('created_at'):
        created = datetime.fromisoformat(state['created_at'].replace('Z', '+00:00'))
        if created.tzinfo is None:
            raise ValueError('created_at must include its timezone')
        return created, 'project.created_at'
    # Legacy init stored a date, not a timestamp. Windows birth time never makes
    # a copied/restored directory older. Else use the end of that whole day.
    day = datetime.fromisoformat(state['request_date']).replace(tzinfo=ZoneInfo(config['timezone']))
    birth = getattr(root.stat(), 'st_birthtime', None)
    if birth is not None:
        return max(day, datetime.fromtimestamp(birth, timezone.utc)), 'legacy-directory-birthtime'
    return day + timedelta(days=1), 'legacy-request-day-upper-bound'


def legacy_initialization(root):
    """Recognize pre-project.json init through its independent saved outputs."""
    agents = root / '.agents'
    rule = agents / 'rules/90-project.md'
    kb = root / 'KB/Project.md'
    manifests = [agents / (kind + '.json') for kind in ('rules', 'skills', 'agents')]
    if not all(p.is_file() for p in [rule, kb, *manifests]):
        return None
    for kind, manifest in zip(('rules', 'skills', 'agents'), manifests):
        entries = _json(manifest).get('entries')
        if not isinstance(entries, list):
            raise ValueError('Legacy discovery manifest requires entries[]')
        paths = [Path(entry['path']) for entry in entries if isinstance(entry, dict) and isinstance(entry.get('path'), str)]
        if not any((p if p.is_absolute() else agents / p).resolve() == (PRIMARY / kind).resolve() for p in paths):
            return None
    if linked(rule) or linked(kb):
        raise ValueError('Linked legacy initialization evidence preserved')
    pattern = r'https?://(?:www\.)?upwork\.com/jobs/[^\s`"<>]*?(~[A-Za-z0-9]+)'
    ids = set(re.findall(pattern, rule.read_text(encoding='utf-8-sig')))
    current = re.search(r'^#\s*2\.\s*Текущий проект клиента[^\n]*\n(.*?)(?=^#\s|\Z)',
                        kb.read_text(encoding='utf-8-sig'), re.M | re.S)
    current_ids = re.findall(pattern, current.group(1)) if current else []
    if len(ids) != 1 or not current_ids or current_ids[0] not in ids:
        raise ValueError('Legacy project rule and current-job KB do not establish one job ID')
    if not re.fullmatch(r'~\d+', current_ids[0]):
        raise ValueError('Unsupported historical job ID preserved without cleanup')
    day = datetime(int(root.parents[2].name), int(root.parents[1].name), int(root.parent.name)).date()
    return {'job_id': current_ids[0], 'initialized': True, 'request_date': day.isoformat()}


def candidates(daily, config, now):
    values, issues = [], []
    for root in sorted(daily.glob('????/??/??/*')):
        if not root.is_dir():
            continue
        marker = root / 'ꘖ/project.json'
        try:
            if linked(marker) or not root.resolve().is_relative_to(daily):
                raise ValueError('Linked or escaped archive entry preserved')
            state = _json(marker) if marker.exists() else legacy_initialization(root)
            if state is None:
                continue
            if state.get('initialized') is not True or not re.fullmatch(r'~\d+', state.get('job_id', '')):
                continue
            created, basis = _age(root, state, config)
            values.append({'root': str(root.resolve()), 'job_id': state['job_id'],
                           'initialization_basis': 'project.json' if marker.exists() else 'legacy-manifests-rule-and-kb',
                           'created_at': created.isoformat(), 'age_basis': basis,
                           'old_enough': now - created > timedelta(days=3)})
        except (OSError, ValueError, TypeError, KeyError) as exc:
            issues.append({'root': str(root), 'error': str(exc)})
    return values, issues


def antigravity_projects(directory, root):
    matches = []
    for path in sorted(directory.glob('*.json')):
        value = _json(path)
        resources = (value.get('projectResources') or {}).get('resources') or []
        roots = [path_key(res['folderUri']) for res in resources if res.get('folderUri')]
        if path_key(root) in roots:
            if roots != [path_key(root)]:
                raise ValueError('Antigravity multi-root project preserved')
            if not value.get('id') or path.stem != value['id']:
                raise ValueError('Antigravity project identity is ambiguous')
            matches.append({'id': value['id'], 'file': str(path), 'sha': path.read_bytes()})
    # An interrupted native-delete -> Folders publication keeps only the IDs
    # needed to finish that exact operation, outside the historical archive.
    pending_file = directory / 'ꘖ/data/cleanup-pending.json'
    pending = _json(pending_file) if pending_file.exists() else {}
    for saved in pending.get(path_key(root), {}).get('projects', []):
        ident = saved['id']
        if not isinstance(ident, str) or not re.fullmatch(r'[a-f0-9-]{36}', ident):
            raise ValueError('Invalid pending Antigravity cleanup identity')
        path = directory / (ident + '.json')
        if not any(p['id'] == ident for p in matches):
            if path.exists():
                raise ValueError('Pending Antigravity project changed its workspace')
            payload = base64.b64decode(saved['payload'], validate=True)
            restored = json.loads(payload.decode('utf-8-sig'))
            roots = [path_key(r['folderUri']) for r in restored['projectResources']['resources']]
            if restored.get('id') != ident or roots != [path_key(root)]:
                raise ValueError('Pending Antigravity payload changed identity')
            matches.append({'id': ident, 'file': str(path), 'sha': None, 'restore': payload})
    return matches


def _connection(database):
    if not database.is_file() or linked(database):
        raise ValueError(f'Native history unavailable: {database}')
    connection = sqlite3.connect(database.resolve().as_uri() + '?mode=ro', uri=True, timeout=5)
    connection.row_factory = sqlite3.Row
    connection.execute('PRAGMA query_only=ON')
    return connection


def conversations(root, ag_projects, backend, homes, catalog):
    """Count every chat, including archived/empty/subagent chats, by ID or root."""
    wanted = path_key(root)
    def belongs(path):
        key = path_key(path)
        return key == wanted or key.startswith(wanted + '/')
    counts = {}
    connection = _connection(backend / 'conversation_summaries.db')
    try:
        ids = {p['id'] for p in ag_projects}
        count = 0
        for row in connection.execute('SELECT project_id, workspace_uris FROM conversation_summaries'):
            uris = json.loads(row['workspace_uris']) if row['workspace_uris'] else []
            if not isinstance(uris, list):
                raise ValueError('Unknown Antigravity workspace_uris format')
            if row['project_id'] in ids or any(belongs(uri) for uri in uris):
                count += 1
        counts['antigravity'] = count
    finally:
        connection.close()
    for profile, home in homes.items():
        ids = {p['bindings'][profile] for p in catalog}
        databases = list(home.glob('state_*.sqlite'))
        if not databases:
            raise ValueError(f'Native Codex history unavailable: {profile}')
        found = set()
        for database in databases:
            connection = _connection(database)
            try:
                for row in connection.execute('SELECT id, project_id, cwd FROM threads'):
                    if row['project_id'] in ids or belongs(row['cwd']):
                        found.add(row['id'])
            finally:
                connection.close()
        counts['codex:' + profile] = len(found)
    return counts


def catalog_projects(catalog, root, homes):
    if (not isinstance(catalog, dict) or not isinstance(catalog.get('projects'), dict)
            or not isinstance(catalog.get('profiles'), dict)):
        raise ValueError('Shared-Projects catalogue unavailable')
    if set(catalog['profiles']) != set(homes):
        raise ValueError('Configured Codex profiles differ from Shared-Projects')
    matches = []
    for ident, project in catalog['projects'].items():
        roots = [path_key(path) for path in project['rootPaths']]
        if path_key(root) not in roots:
            continue
        if roots != [path_key(root)]:
            raise ValueError('Codex multi-root project preserved')
        bindings = {}
        for profile, data in catalog['profiles'].items():
            binding = data['bindings'].get(ident)
            if not binding or not binding.get('desktopId'):
                raise ValueError('Codex profile binding is missing')
            bindings[profile] = binding['desktopId']
        matches.append({'id': ident, 'bindings': bindings, 'cleanup_hold': bool(project.get('cleanupHold'))})
    if len(matches) > 1:
        raise ValueError('Ambiguous Shared-Projects root')
    return matches


def prune_folders(value, removed_ids):
    """Only prune branches that lose a project during this operation."""
    nodes, assignments = value['folders'], value['projectFolderMap']
    if not isinstance(nodes, list) or not isinstance(assignments, dict):
        raise ValueError('Invalid Folders store')
    by_id = {node['id']: node for node in nodes}
    if len(by_id) != len(nodes):
        raise ValueError('Duplicate Folders identities')
    affected = set()
    for ident in removed_ids:
        folder = assignments.get(ident)
        seen = set()
        while folder is not None:
            if folder in seen or folder not in by_id:
                raise ValueError('Broken Folders ancestry')
            seen.add(folder)
            affected.add(folder)
            folder = by_id[folder].get('parentId')
    for ident in removed_ids:
        assignments.pop(ident, None)
    removed = []
    while True:
        empty = {ident for ident in affected if ident in by_id
                 and ident not in assignments.values()
                 and not any(n.get('parentId') == ident for n in by_id.values())}
        if not empty:
            break
        for ident in empty:
            removed.append(ident)
            del by_id[ident]
    value['folders'] = [n for n in nodes if n['id'] in by_id]
    for key in ('collapsedFolders', 'collapsedFolderIds'):
        if key in value:
            value[key] = [ident for ident in value[key] if ident not in removed]
    return removed


def _finish_pending(directory, root):
    path = directory / 'ꘖ/data/cleanup-pending.json'
    if not path.exists():
        return
    pending = _json(path)
    pending.pop(path_key(root), None)
    if pending:
        replace_bytes(path, (json.dumps(pending, ensure_ascii=False, indent=2) + '\n').encode())
    else:
        path.unlink()


def restore_antigravity(root, directory, folders):
    with locked(directory / 'ꘖ/data/registration.lock'):
        path = directory / 'ꘖ/data/cleanup-pending.json'
        if not path.exists():
            return {'complete': True, 'restored_projects': []}
        pending = _json(path).get(path_key(root))
        if not pending:
            return {'complete': True, 'restored_projects': []}
        restored = []
        for project in antigravity_projects(directory, root):
            if project['sha'] is None:
                target = Path(project['file'])
                if linked(target) or target.parent.resolve() != directory.resolve():
                    raise ValueError('Unsafe Antigravity restoration path')
                create_bytes(target, project['restore'])
                restored.append(project['id'])
        before = folders.read_bytes()
        value = _json(folders)
        ids = {n['id'] for n in value['folders']}
        for node in pending['folders']:
            if node['id'] not in ids:
                value['folders'].append(node)
                ids.add(node['id'])
        for ident, folder in pending['assignments'].items():
            value['projectFolderMap'].setdefault(ident, folder)
        if (any(folder not in ids for folder in value['projectFolderMap'].values())
                or any(n.get('parentId') is not None and n['parentId'] not in ids for n in value['folders'])):
            raise ValueError('Restored Folders ancestry is incomplete')
        if folders.read_bytes() != before:
            raise ValueError('Folders changed during restoration')
        replace_bytes(folders, (json.dumps(value, ensure_ascii=False, indent=2) + '\n').encode())
        _finish_pending(directory, root)
        return {'complete': True, 'restored_projects': restored}


def remove_antigravity(root, directory, folders, expected, check):
    with locked(directory / 'ꘖ/data/registration.lock'):
        check()
        current = antigravity_projects(directory, root)
        if [(p['id'], p['sha']) for p in current] != [(p['id'], p['sha']) for p in expected]:
            raise ValueError('Antigravity registration changed; retry cleanup')
        before = folders.read_bytes()
        value = _json(folders)
        original = json.loads(before.decode('utf-8-sig'))
        pruned = prune_folders(value, [p['id'] for p in current])
        if folders.read_bytes() != before:
            raise ValueError('Folders changed; retry cleanup')
        pending_file = directory / 'ꘖ/data/cleanup-pending.json'
        pending = _json(pending_file) if pending_file.exists() else {}
        by_id = {node['id']: node for node in original['folders']}
        ancestry = set()
        for project in current:
            ancestor = original['projectFolderMap'].get(project['id'])
            seen = set()
            while ancestor is not None:
                if ancestor in seen or ancestor not in by_id:
                    raise ValueError('Invalid pending Folders ancestry')
                seen.add(ancestor)
                ancestry.add(ancestor)
                ancestor = by_id[ancestor].get('parentId')
        pending.setdefault(path_key(root), {
            'projects': [{'id': p['id'], 'payload': base64.b64encode(p['sha'] if p['sha'] is not None else p['restore']).decode('ascii')}
                         for p in current],
            'folders': [node for node in original['folders'] if node['id'] in ancestry],
            'assignments': {p['id']: original['projectFolderMap'][p['id']] for p in current
                            if p['id'] in original['projectFolderMap']}})
        replace_bytes(pending_file, (json.dumps(pending, ensure_ascii=False, indent=2) + '\n').encode())
        removed = []
        for project in current:
            path = Path(project['file'])
            actual = path.read_bytes() if path.exists() else None
            if path.parent.resolve() != directory.resolve() or linked(path) or actual != project['sha']:
                raise ValueError('Native project changed before removal')
            check()
            if linked(path) or (path.read_bytes() if path.exists() else None) != project['sha']:
                raise ValueError('Native project changed during the final conversation check')
            if actual is not None:
                path.unlink()
            removed.append(project['id'])
        # Do not unassign or prune a still-existing native project. If this
        # publication fails, the pending IDs allow the next run to finish it.
        check()
        if folders.read_bytes() != before:
            raise ValueError('Folders changed after native deletion; retry cleanup')
        payload = (json.dumps(value, ensure_ascii=False, indent=2) + '\n').encode()
        replace_bytes(folders, payload)
        if folders.read_bytes() != payload:
            raise ValueError('Folders did not confirm cleanup; retry')
        return {'complete': True, 'removed_projects': removed, 'removed_folders': pruned, 'awaiting_commit': True}


def cleanup_projects(*, apply=False, daily_root=None, now=None, config=None, ag_directory=None,
                     ag_backend=None, folders=None, control=None):
    config = config or settings()
    daily = Path(daily_root or Path(config['workspace_root']) / config['daily_root']).absolute()
    if linked(daily) or not daily.is_dir():
        raise ValueError('Daily archive must be an existing unlinked directory')
    daily = daily.resolve()
    now = now or datetime.now(timezone.utc)
    if now.tzinfo is None:
        raise ValueError('Cleanup time must include a timezone')
    directory = Path(ag_directory or Path.home() / '.gemini/config/projects').absolute()
    backend = Path(ag_backend or Path.home() / '.gemini/antigravity').absolute()
    folder_file = Path(folders or config['platforms']['antigravity']['folders_json']).absolute()
    homes = {name: Path(home) for name, home in config['platforms']['codex']['homes'].items()}
    if not directory.is_dir() or linked(directory) or linked(folder_file):
        raise ValueError('Antigravity native stores unavailable or linked')
    if directory.is_relative_to(daily) or folder_file.is_relative_to(daily):
        raise ValueError('Native stores must be outside the preserved daily archive')
    if control is None:
        from .platforms.codex import shared_control
        control = shared_control
    result = {'complete': True, 'mode': 'apply' if apply else 'dry-run', 'platform': platform_name(),
              'cutoff': (now - timedelta(days=3)).isoformat(), 'archive_preserved': str(daily),
              'projects': [], 'issues': []}
    lock = PRIMARY.parent / 'ꘖ/data/cleanup.lock'
    with locked(lock) if apply else nullcontext():
        found, issues = candidates(daily, config, now)
        result['discovery'] = {
            'verified_projects': len(found),
            'modern_projects': sum(p['initialization_basis'] == 'project.json' for p in found),
            'legacy_projects': sum(p['initialization_basis'] != 'project.json' for p in found),
            'excluded_with_conversations': 0,
            'unresolved_entries': len(issues),
        }
        try:
            catalog = control({'command': 'shared-catalog'})
            if not isinstance(catalog, dict):
                raise RuntimeError('Shared-Projects is initializing; retry cleanup')
            _json(folder_file)
        except (OSError, ValueError, RuntimeError) as exc:
            result.update(complete=False, issues=[*issues, {'error': str(exc)}])
            return result

        def recover_preserved(entry, root, cx):
            if not apply:
                return
            try:
                entry['antigravity_recovery'] = restore_antigravity(root, directory, folder_file)
                if cx:
                    current_cx = catalog_projects(control({'command': 'shared-catalog'}), root, homes)
                    if any(p['cleanup_hold'] for p in current_cx):
                        entry['recovery'] = control({'command': 'shared-cleanup-project', 'preserve': True,
                            'sharedId': cx[0]['id'], 'rootPaths': [str(root)], 'bindings': cx[0]['bindings']})
                        if entry['recovery'].get('complete') is not True:
                            result['complete'] = False
            except (OSError, ValueError, RuntimeError) as recovery_error:
                entry['recovery_error'] = str(recovery_error)
                result['complete'] = False

        # A chat excludes a workspace regardless of whether old init evidence
        # can identify its job. Resolve that exclusion before publishing issues;
        # it never supplies provenance or authorizes deletion of an empty root.
        for issue in issues:
            root = Path(issue['root'])
            try:
                if linked(root) or not root.resolve().is_relative_to(daily):
                    raise ValueError('Linked or escaped archive entry preserved')
                ag = antigravity_projects(directory, root)
                cx = catalog_projects(catalog, root, homes)
                counts = conversations(root, ag, backend, homes, cx)
                if any(counts.values()):
                    entry = {'root': str(root), 'status': 'preserved', 'conversations': counts}
                    result['projects'].append(entry)
                    result['discovery']['excluded_with_conversations'] += 1
                    recover_preserved(entry, root, cx)
                    continue
            except (OSError, ValueError, RuntimeError, KeyError, TypeError, sqlite3.Error):
                pass
            result['issues'].append(issue)
        result['discovery']['unresolved_entries'] = len(result['issues'])

        for item in found:
            root = Path(item['root'])
            entry = {**item, 'status': 'recent' if not item['old_enough'] else 'checking'}
            result['projects'].append(entry)
            if not item['old_enough']:
                continue
            cx, ag = [], []
            try:
                ag = antigravity_projects(directory, root)
                cx = catalog_projects(catalog, root, homes)
                def check():
                    counts = conversations(root, ag, backend, homes, cx)
                    entry['conversations'] = counts
                    if any(counts.values()):
                        raise ValueError('Project has conversations')
                check()
                if not ag and not cx:
                    entry['status'] = 'already-absent'
                    continue
                entry['status'] = 'eligible'
                entry['native_projects'] = {'antigravity': [p['id'] for p in ag], 'codex': [p['id'] for p in cx]}
                if not apply:
                    continue
                check()
                if cx:
                    entry['codex'] = control({'command': 'shared-cleanup-project',
                        'deferCommit': True,
                        'sharedId': cx[0]['id'], 'rootPaths': [str(root)], 'bindings': cx[0]['bindings'],
                        'antigravity': {'database': str(backend / 'conversation_summaries.db'),
                                        'projectIds': [p['id'] for p in ag]}})
                    if entry['codex'].get('complete') is not True:
                        entry['status'] = 'pending'
                        result['complete'] = False
                        continue
                if ag:
                    entry['antigravity'] = remove_antigravity(root, directory, folder_file, ag, check)
                if cx:
                    entry['codex_commit'] = control({'command': 'shared-cleanup-project', 'commit': True,
                        'sharedId': cx[0]['id'], 'rootPaths': [str(root)], 'bindings': cx[0]['bindings'],
                        'antigravity': {'database': str(backend / 'conversation_summaries.db'),
                                        'projectIds': [p['id'] for p in ag]}})
                    if entry['codex_commit'].get('complete') is not True:
                        entry['status'] = 'pending'
                        result['complete'] = False
                        continue
                with locked(directory / 'ꘖ/data/registration.lock'):
                    _finish_pending(directory, root)
                entry['status'] = 'removed'
                catalog = control({'command': 'shared-catalog'})
            except (OSError, ValueError, RuntimeError, KeyError, TypeError, sqlite3.Error) as exc:
                # A final native call can discover a chat after the initial
                # checks. Recover from the native stores, never from old counts.
                try:
                    entry['conversations'] = conversations(root, ag, backend, homes, cx)
                except (OSError, ValueError, TypeError, sqlite3.Error):
                    pass
                entry.update(status='preserved' if any(entry.get('conversations', {}).values()) else 'blocked', error=str(exc))
                if entry['status'] == 'preserved':
                    recover_preserved(entry, root, cx)
                if entry['status'] == 'blocked':
                    result['complete'] = False
        if result['issues']:
            result['complete'] = False
    result['counts'] = {name: sum(p['status'] == name for p in result['projects'])
                        for name in ('recent', 'preserved', 'eligible', 'removed', 'pending', 'blocked', 'already-absent')}
    return result
