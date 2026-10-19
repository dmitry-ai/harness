"""Deterministic workflow operations exposed by the existing Upwork entrypoint."""

from pathlib import Path
import json
import sys

COMMANDS = ('status', 'resume', 'collect', 'capture-dom', 'extract', 'extract-file', 'sync-attachments', 'check-project', 'stage',
            'question-add', 'question-claim', 'question-finish', 'question-handoff', 'question-search',
            'prepare-review', 'review-input', 'native-review-proof', 'record-review', 'review-disposition', 'prepare-experiment', 'record-experiment', 'native-executor-metadata', 'adopt-requests', 'record-answer', 'metrics', 'source-ref', 'save-analysis', 'render-analysis')


def add_parsers(sub):
    for command in COMMANDS:
        parser = sub.add_parser(command, help={
            'resume': 'Continue the selected current-chat project from saved agent KB; no inspect/init',
            'status': 'Read-only current stage and agent KB navigation',
            'collect': 'Batch GET observations and extraction with persistent project cache',
            'sync-attachments': 'Sync client attachments to source/ and both KBs, including document/video/image transcriptions',
            'check-project': 'All saved-source and local KB diagnostics; no network calls',
            'render-analysis': 'Publish tracked Markdown; preserve unknown/manual edits'
        }.get(command, 'Internal ' + command + ' operation'))
        if command == 'metrics':
            parser.add_argument('traces', nargs='+', type=Path)
            parser.add_argument('--bindings', type=Path, help='conversation ID -> stage/first_step/last_step intervals')
            parser.add_argument('--project', type=Path, help='Optional exact project: observed cache/search/review metrics')
            continue
        if command == 'render-analysis':
            parser.add_argument('input', type=Path)
            parser.add_argument('--output', type=Path)
            continue
        parser.add_argument('project', type=Path, help='Exact existing project root from the current chat')
        if command in ('record-answer', 'save-analysis', 'collect', 'question-add', 'sync-attachments', 'prepare-review', 'record-review', 'prepare-experiment', 'record-experiment'):
            parser.add_argument('--consume-input', action='store_true', help='After success remove an unchanged input only from project ꘖ/data/scratch; use - for stdin')
        if command == 'resume':
            parser.add_argument('--reason', required=True)
            parser.add_argument('--request-file', type=Path, help='Exact current user message; kept in service state until final journal')
        elif command == 'adopt-requests':
            parser.add_argument('--conversation', required=True)
        elif command == 'record-answer':
            parser.add_argument('--response-file', required=True, type=Path)
        elif command == 'save-analysis':
            parser.add_argument('--candidate', required=True)
            parser.add_argument('--expected-sha256')
        elif command == 'collect':
            parser.add_argument('--plan', required=True, type=Path)
            parser.add_argument('--output', help='Optional project-owned result JSON')
        elif command == 'capture-dom':
            parser.add_argument('--url', required=True)
            parser.add_argument('--tab-id', required=True)
            parser.add_argument('--cdp-port', type=int)
            parser.add_argument('--refresh-reason')
        elif command in ('extract', 'extract-file'):
            parser.add_argument('source')
            parser.add_argument('--profile', choices=('html', 'shopify', 'tracking', 'document'), default='html' if command == 'extract' else 'document')
        elif command == 'sync-attachments':
            parser.add_argument('--media-descriptions', type=Path, help='Optional JSON mapping attachment filename/sha256/video URL to Markdown transcription/analysis')
            parser.add_argument('--no-fetch-videos', action='store_true', help='Skip network fetching for external video transcripts')
        elif command == 'stage':
            from .workflow import STAGES
            parser.add_argument('stage', choices=STAGES)
            parser.add_argument('--input', action='append', required=True)
            parser.add_argument('--output', action='append', required=True)
            parser.add_argument('--note')
        elif command == 'question-add':
            parser.add_argument('--spec', type=Path, required=True)
        elif command.startswith('question-'):
            parser.add_argument('id')
            if command == 'question-handoff':
                parser.add_argument('--previous-owner', required=True)
                parser.add_argument('--new-owner', required=True)
                parser.add_argument('--reason', required=True)
            else:
                parser.add_argument('--owner', required=True)
            if command == 'question-finish':
                parser.add_argument('--output', action='append', required=True)
                parser.add_argument('--gap')
                parser.add_argument('--results', required=True, type=Path, help='Structured experiment result list JSON; use - for stdin')
            elif command == 'question-search':
                parser.add_argument('--query', required=True)
                parser.add_argument('--useful', action='store_true')
                parser.add_argument('--method-change')
        elif command == 'prepare-review':
            parser.add_argument('--parent', required=True)
            parser.add_argument('--spec', required=True, type=Path, help='Explicit risk/basis/request_scope/claim_ids/claims JSON')
            parser.add_argument('--response-file', required=True, type=Path, help='Exact candidate response; use - for stdin')
        elif command == 'review-input':
            parser.add_argument('--package', required=True)
        elif command in ('native-review-proof', 'record-review'):
            parser.add_argument('--parent', required=True)
            parser.add_argument('--reviewer', required=True)
            if command == 'record-review':
                parser.add_argument('--report', required=True)
                parser.add_argument('--native-evidence', help='Separate native proof from the completed reviewer')
        elif command == 'review-disposition':
            parser.add_argument('--review-id', required=True)
            parser.add_argument('--finding-id', required=True)
            parser.add_argument('--status', choices=('resolved', 'rejected'), required=True)
            parser.add_argument('--basis', required=True)
            parser.add_argument('--evidence', action='append', required=True)
            parser.add_argument('--parent', required=True)
        elif command == 'record-experiment':
            parser.add_argument('--spec', required=True, type=Path)
        elif command == 'prepare-experiment':
            parser.add_argument('--spec', required=True, type=Path)
            parser.add_argument('--amendment-of')
            parser.add_argument('--amendment-reason')
        elif command == 'native-executor-metadata':
            parser.add_argument('--conversation', required=True)
            parser.add_argument('--save', action='store_true', help='Persist immutable native metadata; default is read-only')
            parser.add_argument('--role', choices=('primary', 'AA', 'AF'), default='primary')
            parser.add_argument('--parent')
        elif command == 'source-ref':
            parser.add_argument('file')
            parser.add_argument('--part', action='append', default=[])


def analysis_root(file):
    file = Path(file).resolve()
    for parent in file.parents:
        if parent.name == 'ꘖ':
            return parent.parent
    return file.parent


def _read_input(path):
    return sys.stdin.buffer.read() if str(path) == '-' else Path(path).read_bytes()


def _consumed(args, path, payload, result):
    if not getattr(args, 'consume_input', False) or str(path) == '-':
        return result
    target = Path(path).resolve()
    scratch = Path(args.project).resolve() / 'ꘖ/data/scratch'
    if not target.is_relative_to(scratch) or Path(path).is_symlink() or any(p.is_junction() for p in (target, *target.parents) if p.exists()):
        raise ValueError('Consumed input must be an ordinary file inside project ꘖ/data/scratch')
    if result.get('status') == 'conflict' or result.get('complete') is False or result.get('valid') is False:
        return result
    if target.exists() and target.read_bytes() == payload:
        target.unlink()
        result['consumed_input'] = str(target)
    return result


def _operation_input(args, path):
    if getattr(args, 'consume_input', False) and str(path) != '-':
        # Validate the deletion scope before the operation changes any state.
        target = Path(path).resolve()
        if (not target.is_relative_to(Path(args.project).resolve() / 'ꘖ/data/scratch')
                or Path(path).is_symlink()
                or any(p.is_junction() for p in (target, *target.parents) if p.exists())):
            raise ValueError('Consumed input must be an ordinary file inside project ꘖ/data/scratch')
    return _read_input(path)


def execute(args):
    from . import workflow as flow
    command = args.command
    if command == 'status':
        return flow.status(args.project)
    if command == 'resume':
        request = _read_input(args.request_file).decode('utf-8') if args.request_file else None
        return flow.resume(args.project, args.reason, request)
    if command == 'check-project':
        return flow.check_project(args.project)
    if command == 'adopt-requests':
        return flow.adopt_requests(args.project, args.conversation)
    if command == 'record-answer':
        payload = _operation_input(args, args.response_file)
        result = flow.record_current_answer(args.project, payload.decode('utf-8'))
        return _consumed(args, args.response_file, payload, result)
    if command == 'save-analysis':
        from .analysis import save_analysis
        from .research import inside
        candidate = args.candidate if str(args.candidate) == '-' else inside(args.project, args.candidate)
        payload = _operation_input(args, candidate)
        result = save_analysis(args.project, json.loads(payload.decode('utf-8-sig')), args.expected_sha256)
        return _consumed(args, candidate, payload, result)
    if command == 'collect':
        from .research import collect_plan, compute_site_summary, inside, json_data
        payload = _operation_input(args, args.plan)
        plan = json.loads(payload.decode('utf-8-sig'))
        result = collect_plan(args.project, plan)
        if args.output:
            from .analysis import publish_owned, digest
            target = inside(args.project, args.output)
            if not target.is_relative_to(Path(args.project).resolve() / 'ꘖ/KB/Evidence') or '/HTTP/' in target.as_posix() or '/Reviews/' in target.as_posix():
                raise ValueError('Collection report must be a project Evidence file outside immutable HTTP/Reviews observations')
            receipts_file = Path(args.project).resolve() / 'ꘖ/data/rendered.json'
            if target.is_file() and receipts_file.is_file():
                try:
                    receipts = json.loads(receipts_file.read_text(encoding='utf-8'))
                    raw_prev = target.read_bytes()
                    if receipts.get(str(target), {}).get('sha256') == digest(raw_prev):
                        prev_data = json.loads(raw_prev.decode('utf-8'))
                        if isinstance(prev_data, dict) and isinstance(prev_data.get('results'), list) and isinstance(result.get('results'), list):
                            new_keys = {r.get('request_key') or (r.get('url'), r.get('observation')) for r in result['results'] if isinstance(r, dict)}
                            kept = [r for r in prev_data['results'] if isinstance(r, dict) and (r.get('request_key') or (r.get('url'), r.get('observation'))) not in new_keys]
                            if kept:
                                merged_results = kept + result['results']
                                result = {**result, 'results': merged_results,
                                          'site_summary': compute_site_summary(args.project, merged_results),
                                          'complete': bool(prev_data.get('complete', True) and result.get('complete', True))}
                except (OSError, ValueError):
                    pass
            result['publication'] = publish_owned(target, json_data(result), source={
                'kind': 'collection-plan', 'sha256': digest(payload), 'plan': plan})
            if result['publication']['status'] == 'conflict':
                return result
            return _consumed(args, args.plan, payload, result)
        return result
    if command == 'extract':
        from .research import extract_observation
        return extract_observation(args.project, args.source, args.profile)
    if command == 'capture-dom':
        from .research import capture_dom
        from .runtime import platform_settings
        port = args.cdp_port or platform_settings()['browser']['cdp_port']
        return capture_dom(args.project, args.url, args.tab_id, port=port, refresh_reason=args.refresh_reason)
    if command == 'extract-file':
        from .research import extract_file
        return extract_file(args.project, args.source, args.profile)
    if command == 'sync-attachments':
        from .knowledge import sync_project_attachments_and_kb
        descriptions, payload = None, None
        if args.media_descriptions:
            payload = _operation_input(args, args.media_descriptions)
            descriptions = json.loads(payload.decode('utf-8-sig'))
        result = sync_project_attachments_and_kb(args.project, descriptions, fetch_videos=not args.no_fetch_videos)
        return _consumed(args, args.media_descriptions, payload, result) if args.media_descriptions else result
    if command == 'stage':
        return flow.complete_stage(args.project, args.stage, args.input, args.output, note=args.note)
    if command == 'question-add':
        payload = _operation_input(args, args.spec)
        spec = json.loads(payload.decode('utf-8-sig'))
        result = flow.add_question(args.project, spec['id'], spec['question'], spec['impact'], spec['done_when'], spec['inputs'], spec['outputs'], requirements=spec.get('requirements'))
        return _consumed(args, args.spec, payload, result)
    if command == 'question-claim':
        return flow.claim_question(args.project, args.id, args.owner)
    if command == 'question-finish':
        return flow.finish_question(args.project, args.id, args.owner, args.output, args.gap, results=json.loads(_read_input(args.results).decode('utf-8-sig')))
    if command == 'question-handoff':
        return flow.handoff(args.project, args.id, args.previous_owner, args.new_owner, args.reason)
    if command == 'question-search':
        return flow.record_search(args.project, args.id, args.owner, args.query, args.useful, args.method_change)
    if command == 'native-review-proof':
        from .metrics import native_review_proof
        return native_review_proof(args.project, args.parent, args.reviewer)
    if command == 'prepare-review':
        if str(args.spec) == '-' and str(args.response_file) == '-':
            raise ValueError('Only one prepare-review input may use stdin')
        spec_payload = _operation_input(args, args.spec)
        payload = _operation_input(args, args.response_file)
        result = flow.prepare_review(args.project, args.parent, json.loads(spec_payload.decode('utf-8-sig')), payload.decode('utf-8'))
        result = _consumed(args, args.spec, spec_payload, result)
        return _consumed(args, args.response_file, payload, result)
    if command == 'review-input':
        return flow.review_input(args.project, args.package)
    if command == 'record-review':
        payload = _operation_input(args, args.report)
        result = flow.record_review(args.project, payload, parent_id=args.parent, reviewer_id=args.reviewer, native_evidence=args.native_evidence)
        return _consumed(args, args.report, payload, result)
    if command == 'review-disposition':
        return flow.record_review_disposition(args.project, args.review_id, args.finding_id, args.status, args.basis, args.evidence, args.parent)
    if command == 'record-experiment':
        from .experiments import record_experiment
        payload = _operation_input(args, args.spec)
        result = record_experiment(args.project, json.loads(payload.decode('utf-8-sig')))
        return _consumed(args, args.spec, payload, result)
    if command == 'prepare-experiment':
        from .experiments import prepare_experiment
        payload = _operation_input(args, args.spec)
        result = prepare_experiment(args.project, json.loads(payload.decode('utf-8-sig')),
            amendment_of=args.amendment_of, amendment_reason=args.amendment_reason)
        return _consumed(args, args.spec, payload, result)
    if command == 'native-executor-metadata':
        from .metrics import native_executor_metadata, record_executor_metadata
        callback = record_executor_metadata if args.save else native_executor_metadata
        return callback(args.project, args.conversation, role=args.role, parent_id=args.parent)
    if command == 'metrics':
        from .metrics import summarize
        bindings = json.loads(args.bindings.read_text(encoding='utf-8')) if args.bindings else None
        result = summarize(args.traces, bindings)
        if args.project:
            from .metrics import project_metrics
            result['project'] = project_metrics(args.project)
        return result
    if command == 'source-ref':
        from .evidence import source_reference
        return {'source': source_reference(args.project, args.file, args.part)}
    if command == 'render-analysis':
        from .analysis import publish_analysis
        return publish_analysis(args.input, args.output)
    raise ValueError('Unknown workflow command')
