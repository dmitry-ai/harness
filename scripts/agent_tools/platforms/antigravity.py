"""Antigravity-specific manifests, registrations and verified native traces."""
from pathlib import Path
from datetime import date
from urllib.parse import unquote
import hashlib
import json
import re
import sqlite3
import uuid

from ..runtime import platform_settings, request_day
from ..research import json_data
from ..knowledge import json_bytes
from ..storage import create_bytes, replace_bytes, locked

ANTIGRAVITY_PROJECTS_DIR = Path.home() / '.gemini/config/projects'
ANTIGRAVITY_FOLDERS_JSON = Path(platform_settings('antigravity')['folders_json'])

def folder_path(uri):
    path = unquote(uri[7:]) if uri.startswith('file://') else uri
    if re.match(r'^/[A-Za-z]:/', path):
        path = path[1:]
    return Path(path).resolve()


def register_antigravity_project(project_dir, domain_or_topic, date_str=None,
                                projects_dir=ANTIGRAVITY_PROJECTS_DIR,
                                folders_json_path=ANTIGRAVITY_FOLDERS_JSON):
    root, projects = Path(project_dir).resolve(), Path(projects_dir)
    day = request_day(date_str) if date_str else date(int(root.parents[2].name), int(root.parents[1].name), int(root.parent.name))
    name = f'{domain_or_topic} - U.P.{day:%Y.%m.%d}'
    with locked(projects / 'ꘖ' / 'data' / 'registration.lock'):
        folders = Path(folders_json_path)
        # Folders is our installed add-on, not a native Antigravity field.
        # Reject a missing/broken store before publishing an ungrouped project.
        before = folders.read_bytes()
        listing = json.loads(before.decode('utf-8-sig'))
        nodes, assignments = listing.get('folders'), listing.get('projectFolderMap')
        if not isinstance(nodes, list) or not isinstance(assignments, dict):
            raise ValueError('Folders requires folders[] and projectFolderMap{}')
        branch = ('Upwork', 'Proposals', f'{day.year:04d}', f'{day.month:02d}', f'{day.day:02d}')
        parent = None
        for part in branch:
            node = next((x for x in nodes if x['name'].casefold() == part.casefold()
                         and x.get('parentId') == parent), None)
            if node is None:
                node = {'id': f'folder-{uuid.uuid4().hex[:16]}', 'name': part,
                        'parentId': parent, 'color': '#10b981', 'isExpanded': True}
                nodes.append(node)
            parent = node['id']
        ident, payload, destination = None, None, None
        for path in projects.glob('*.json'):
            item = json.loads(path.read_text(encoding='utf-8-sig'))
            resources = (item.get('projectResources') or {}).get('resources') or []
            if any(folder_path(res.get('folderUri', '')) == root for res in resources):
                ident, payload, destination = item.get('id') or path.stem, item, path
                break
        if ident is None:
            ident = str(uuid.uuid4())
            destination = projects / f'{ident}.json'
            payload = {'id': ident, 'name': name,
                       'projectResources': {'resources': [{'folderUri': root.as_uri()}]},
                       'settings': {}, 'isWorkspaceOnly': False}
            create_bytes(destination, json_bytes(payload))
        assignments[ident] = parent
        if folders.read_bytes() != before:
            raise RuntimeError('Folders changed concurrently; retry registration')
        if json_bytes(listing) != before:
            replace_bytes(folders, json_bytes(listing))
        effective = json.loads(folders.read_text(encoding='utf-8-sig'))
        if effective['projectFolderMap'].get(ident) != parent:
            raise RuntimeError('Project folder assignment did not persist; retry registration')
        return {'project_id': ident, 'project_name': payload['name'], 'project_file': str(destination),
                'folder_id': parent, 'folder_path': ' / '.join(branch), 'folders_file': str(folders)}


def native_review_proof(root, parent_id, reviewer_id, *, backend=None, write=True):
    """Require an actual child self conversation and its successful final native step."""
    backend = Path(backend) if backend else Path.home() / '.gemini/antigravity'
    if not all(re.fullmatch(r'[a-f0-9-]{36}', x) for x in (parent_id, reviewer_id)):
        raise ValueError('Native parent/reviewer UUIDs required')
    conn = sqlite3.connect((backend / 'conversation_summaries.db').resolve().as_uri() + '?mode=ro', uri=True)
    conn.row_factory = sqlite3.Row
    try:
        child = conn.execute('SELECT parent_conversation_id,agent_name FROM conversation_summaries WHERE conversation_id=?', (reviewer_id,)).fetchone()
    finally:
        conn.close()
    if child is None or child['parent_conversation_id'] != parent_id or child['agent_name'] != 'self':
        raise ValueError('Native trace does not establish an independent self/A.A child of this parent')
    log = backend / 'brain' / reviewer_id / '.system_generated/logs/transcript_full.jsonl'
    rows = [json.loads(line) for line in log.read_text(encoding='utf-8').splitlines() if line.strip()]
    last = rows[-1] if rows else {}
    if last.get('type') != 'PLANNER_RESPONSE' or last.get('tool_calls') or not last.get('content', '').strip():
        raise ValueError('Reviewer has no successful final response in the native trace')
    conn = sqlite3.connect((backend / 'conversations' / (reviewer_id + '.db')).resolve().as_uri() + '?mode=ro', uri=True)
    try:
        final = conn.execute('SELECT idx,step_type,status FROM steps ORDER BY idx DESC LIMIT 1').fetchone()
    finally:
        conn.close()
    if not final or final[0] != last['step_index'] or final[1] != 15 or final[2] != 3:
        raise ValueError('Native database reports an unfinished/failed later reviewer step')
    parent_log = backend / 'brain' / parent_id / '.system_generated/logs/transcript_full.jsonl'
    project = json.loads((Path(root) / 'ꘖ/project.json').read_text(encoding='utf-8'))
    parent_inputs = [json.loads(line) for line in parent_log.read_text(encoding='utf-8').splitlines() if line.strip()]
    if not any(x.get('type') == 'USER_INPUT' and project['job_id'] in x.get('content', '') for x in parent_inputs):
        raise ValueError('Parent conversation does not belong to the selected job')
    initial_prompt = rows[0].get('content', '')
    invocation = None
    for row in parent_inputs:
        for call in row.get('tool_calls', []):
            if call.get('name') != 'invoke_subagent':
                continue
            subs = call.get('args', {}).get('Subagents', [])
            if isinstance(subs, str):
                try: subs = json.loads(subs)
                except ValueError: subs = []
            for sub in subs if isinstance(subs, list) else []:
                if isinstance(sub, dict) and sub.get('TypeName') == 'self' and sub.get('Prompt') and sub['Prompt'] in initial_prompt:
                    if sub.get('Model') != 'inherit':
                        raise ValueError('Native A.A reviewer was not requested with the inherited parent model')
                    invocation = row['step_index']
    if invocation is None:
        raise ValueError('Matching native self/inherit invocation is not established')
    def observed_models(cid, step=None):
        database = backend / 'conversations' / (cid + '.db')
        connection = sqlite3.connect(database.resolve().as_uri() + '?mode=ro', uri=True)
        try:
            columns = {r[1] for r in connection.execute('PRAGMA table_info(steps)')}
            if 'metadata' not in columns:
                return set()
            metadata = connection.execute('SELECT metadata FROM steps WHERE step_type=15 AND status=3' + (' AND idx=?' if step is not None else ''), (step,) if step is not None else ()).fetchall()
            ids = set()
            for (blob,) in metadata:
                try:
                    ids.update(value for field, kind, value in wire_fields(blob or b'') if field == 11 and kind == 0 and value)
                except (ValueError, IndexError):
                    return set()
            return ids
        finally:
            connection.close()
    parent_models, child_models = observed_models(parent_id, invocation), observed_models(reviewer_id)
    if parent_models and child_models and not child_models.issubset(parent_models):
        raise ValueError('Observed reviewer model differs from the inherited A.A model')
    proof = {'surface': 'antigravity-ui', 'parent_id': parent_id, 'reviewer_id': reviewer_id, 'agent_name': 'self',
             'status': 'completed', 'model_verification': 'same observed model IDs; exact version/High unverified' if parent_models and child_models else 'inherit requested; actual version/High unverified',
             'observed_model_ids': sorted(child_models), 'invocation_step': invocation,
             'native_log': str(log), 'native_log_sha256': hashlib.sha256(log.read_bytes()).hexdigest(),
             'final_step': last['step_index'], 'final_response_sha256': hashlib.sha256(last['content'].encode()).hexdigest(),
             'parent_log': str(parent_log), 'job_id': project['job_id']}
    target = Path(root) / 'ꘖ/KB/Evidence/Reviews' / (reviewer_id + '-' + proof['native_log_sha256'][:16] + '-native.json')
    payload = json_data(proof)
    if not write:
        return {'proof': target.relative_to(Path(root).resolve()).as_posix(), **proof}
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists():
        if target.read_bytes() != payload:
            raise ValueError('Existing reviewer proof changed; preserve both and recheck native progress')
    else:
        create_bytes(target, payload)
    return {'proof': target.relative_to(Path(root).resolve()).as_posix(), **proof}


def wire_fields(data):
    def number(offset):
        value, shift = 0, 0
        while True:
            byte = data[offset]; offset += 1; value |= (byte & 127) << shift
            if byte < 128: return value, offset
            shift += 7
            if shift > 70: raise ValueError('Unsupported native protobuf varint')
    offset, result = 0, []
    while offset < len(data):
        tag, offset = number(offset); field, kind = tag >> 3, tag & 7
        if not field: raise ValueError('Unsupported native protobuf field')
        if kind == 0: value, offset = number(offset)
        elif kind == 2:
            size, offset = number(offset); value = data[offset:offset + size]; offset += size
            if len(value) != size: raise ValueError('Native protobuf field is truncated')
        elif kind in (1, 5):
            size = 8 if kind == 1 else 4; value = data[offset:offset + size]; offset += size
        else: raise ValueError('Unsupported native protobuf encoding')
        result.append((field, kind, value))
    return result


def native_requests(root, conversation_id, *, backend=None):
    """Exact USER_INPUT bytes from the current task's native DB, not expanded summaries."""
    if not re.fullmatch(r'[a-f0-9-]{36}', conversation_id):
        raise ValueError('Exact current native conversation UUID required')
    backend = Path(backend) if backend else Path.home() / '.gemini/antigravity'
    project = json.loads((Path(root) / 'ꘖ/project.json').read_text(encoding='utf-8'))
    conn = sqlite3.connect((backend / 'conversations' / (conversation_id + '.db')).resolve().as_uri() + '?mode=ro', uri=True)
    try:
        rows = conn.execute('SELECT idx,step_format,step_payload FROM steps WHERE step_type=14 AND status=3 ORDER BY idx').fetchall()
    finally: conn.close()
    requests, active = [], False
    for index, format_id, payload in rows:
        if format_id != 0:
            raise ValueError('Native request format is unsupported; save exact requests from the current chat, without reconstruction')
        try:
            message = next(value for field, kind, value in wire_fields(payload) if field == 19 and kind == 2)
            text = next(value.decode('utf-8') for field, kind, value in wire_fields(message) if field == 2 and kind == 2)
        except (IndexError, StopIteration, UnicodeError) as exc:
            raise ValueError('Exact native user text is unavailable; do not reconstruct it from summaries') from exc
        command = re.search(r'/upwork-init\s+https?://[^\s]+/~(\d+)', text)
        if command:
            active = ('~' + command[1]) == project['job_id']
        elif not active and project['job_id'] in text:
            active = True
        if active and text.strip():
            requests.append({'id': f'{conversation_id}-{index}', 'text': text, 'native_conversation_id': conversation_id, 'native_step': index})
    if not requests:
        raise ValueError('Native requests do not identify this project')
    return requests


def verify_native_proof(root, native, package=None):
    result = native_review_proof(root, native.get('parent_id', ''), native.get('reviewer_id', ''), write=False)
    for field in ('native_log_sha256', 'final_response_sha256', 'final_step', 'job_id'):
        if native.get(field) != result.get(field):
            raise ValueError('Review proof differs from the current native trace')
    if package:
        with Path(result['native_log']).open(encoding='utf-8') as stream:
            prompt = json.loads(stream.readline()).get('content', '')
        if package not in prompt:
            raise ValueError('Native reviewer was not assigned this immutable KB review package')
    return result


def register(project_dir, domain_or_topic, date_str=None):
    return register_antigravity_project(project_dir, domain_or_topic, date_str)
