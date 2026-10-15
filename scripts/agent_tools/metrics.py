"""Read-only native trace summaries. Never copy reasoning or convert tokens to money."""

from collections import Counter
from pathlib import Path
import json
import re


def summarize(paths, bindings=None):
    formats = []
    for path in paths:
        with Path(path).open(encoding='utf-8') as stream:
            first = next((json.loads(line) for line in stream if line.strip()), {})
        formats.append(first.get('type') == 'session_meta')
    if any(formats):
        if not all(formats):
            raise ValueError('Summarize native Codex and Antigravity traces separately; their accounting formats differ')
        from .platforms.codex import summarize as summarize_codex
        return summarize_codex(paths, bindings)
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


def native_requests(root, conversation_id, *, backend=None, platform=None):
    from .platforms import adapter
    return adapter(platform).native_requests(root, conversation_id, backend=backend)


def native_review_proof(root, parent_id, reviewer_id, *, backend=None, write=True, platform=None):
    from .platforms import adapter
    return adapter(platform).native_review_proof(root, parent_id, reviewer_id, backend=backend, write=write)


def verify_native_proof(root, native, package=None):
    from .platforms import adapter
    if not isinstance(native, dict) or not native.get('surface'):
        raise ValueError('Native review proof must declare its actual surface')
    return adapter(surface=native.get('surface')).verify_native_proof(root, native, package=package)


def wire_fields(data):
    from .platforms.antigravity import wire_fields as decode
    return decode(data)
