"""Read-only native trace summaries. Never copy reasoning or convert tokens to money."""

from collections import Counter
from pathlib import Path
import hashlib
import json
import re
import sqlite3

from .research import json_data
from .storage import create_bytes


def summarize(paths, bindings=None):
    records, seen, duplicates = [], set(), 0
    tools, phases, urls, queries = Counter(), {}, Counter(), Counter()
    error_results = 0
    totals = Counter(); missing = Counter()
    for path in paths:
        path = Path(path)
        cid = path.parents[2].parent.name if path.name.startswith('transcript') else path.stem
        # Native layout: <cid>/.system_generated/logs/transcript_full.jsonl.
        if path.parent.name == 'logs' and path.parent.parent.name == '.system_generated':
            cid = path.parent.parent.parent.name
        for line in path.read_text(encoding='utf-8').splitlines():
            if not line.strip():
                continue
            record = json.loads(line)
            key = (cid, record.get('step_index'))
            if key in seen:
                duplicates += 1; continue
            seen.add(key)
            if record.get('type') == 'GENERIC' and re.search(r'Encountered error in step execution|failed to read file|cannot find the file', record.get('content', ''), re.I):
                error_results += 1
            for call in record.get('tool_calls', []):
                tools[call['name']] += 1
                args = call.get('args', {})
                if isinstance(args, str):
                    try: args = json.loads(args)
                    except ValueError: args = {}
                if not isinstance(args, dict):
                    continue
                if call['name'] == 'read_url_content':
                    target = args.get('Url') or args.get('URL') or args.get('url')
                    if isinstance(target, str): urls[target] += 1
                if call['name'] == 'search_web':
                    query = args.get('query') or args.get('Query') or args.get('SearchQuery')
                    if isinstance(query, str): queries[' '.join(query.casefold().split())] += 1
            if record.get('type') != 'PLANNER_RESPONSE':
                continue
            stage = 'unassigned'
            for interval in (bindings or {}).get(cid, []):
                if interval['first_step'] <= record['step_index'] <= interval['last_step']:
                    stage = interval['stage']; break
            group = phases.setdefault(stage, {'known': Counter(), 'missing': Counter(), 'generations': 0})
            group['generations'] += 1
            for field in ('input_tokens', 'cache_read_tokens', 'output_tokens'):
                value = record.get(field)
                if type(value) is int and value >= 0:
                    totals[field] += value; group['known'][field] += value
                else:
                    missing[field] += 1; group['missing'][field] += 1
            records.append({'conversation_id': cid, 'step': record['step_index'], 'stage': stage})
    def result(known, unavailable):
        return {field: {'known_sum': known[field], 'unreported_records': unavailable[field],
                       'complete_total': known[field] if not unavailable[field] else None}
                for field in ('input_tokens', 'cache_read_tokens', 'output_tokens')}
    return {'generations': len(records), 'duplicate_records_ignored': duplicates, 'tokens': result(totals, missing),
            'tools': dict(tools), 'phases': {stage: {'generations': g['generations'], 'tokens': result(g['known'], g['missing'])} for stage, g in phases.items()},
            'observed_error_results': error_results,
            'repeated_read_url_calls': sum(n - 1 for n in urls.values()),
            'repeated_exact_search_queries': sum(n - 1 for n in queries.values()),
            'interpretation': 'Observed native log counters; not quota percentage, currency or proof of content quality'}


def project_metrics(root):
    from .workflow import load, stage_statuses
    root = Path(root).resolve()
    state = load(root)
    path = root / 'ꘖ/data/research-metrics.json'
    uses = json.loads(path.read_text(encoding='utf-8')) if path.exists() else None
    collector = None if uses is None else {
        'uses': len(uses), 'cache_hits': sum(x.get('cached') is True for x in uses),
        'fresh_attempts': sum(x.get('cached') is False for x in uses),
        'failed_attempts': sum(bool(x.get('error')) for x in uses),
        'http_unavailable': sum(x.get('kind') == 'http' and (x.get('status') or 0) >= 400 for x in uses),
        'scope': 'Only recorded collector operations since instrumentation; earlier requests unknown'}
    questions = []
    for question in state['questions'].values():
        searches = question.get('searches', [])
        questions.append({'id': question['id'], 'status': question['status'], 'searches': len(searches),
            'unsuccessful_searches': sum(not s['useful'] for s in searches),
            'method_changes': sum(bool(s.get('method_change')) for s in searches), 'gap': question.get('gap')})
    reviews = []
    for review in state['reviews']:
        report = json.loads((root / review['report']).read_text(encoding='utf-8'))
        reviews.append({'reviewer_id': review['reviewer_id'], 'independent': review.get('independent', True),
            'risk': review['risk'], 'result': report.get('result'),
            'findings': dict(Counter(f.get('status', 'unknown') for f in report.get('findings', [])))})
    return {'collector': collector, 'questions': questions, 'reviews': reviews, 'stages': stage_statuses(root, state),
            'semantic_quality_verified': False, 'unrecorded_activity': 'unknown'}


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


def verify_native_proof(root, native):
    """Reject model-authored identity assertions without their real source trace."""
    result = native_review_proof(root, native.get('parent_id', ''), native.get('reviewer_id', ''), write=False)
    for field in ('native_log_sha256', 'final_response_sha256', 'final_step', 'job_id'):
        if native.get(field) != result.get(field):
            raise ValueError('Review proof differs from the current native trace')


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
