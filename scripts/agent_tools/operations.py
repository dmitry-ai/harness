"""Deterministic workflow operations exposed by the existing Upwork entrypoint."""

from pathlib import Path
import json

COMMANDS = ('status', 'resume', 'collect', 'capture-dom', 'extract', 'extract-file', 'check-project', 'stage',
            'question-add', 'question-claim', 'question-finish', 'question-handoff', 'question-search',
            'prepare-review', 'native-review-proof', 'record-review', 'adopt-requests', 'record-answer', 'metrics', 'source-ref', 'save-analysis', 'render-analysis')


def add_parsers(sub):
    for command in COMMANDS:
        parser = sub.add_parser(command, help={
            'resume': 'Continue the selected current-chat project from saved agent KB; no inspect/init',
            'status': 'Read-only current stage and agent KB navigation',
            'collect': 'Batch GET observations and extraction with persistent project cache',
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
            parser.add_argument('--cdp-port', type=int, default=9222)
            parser.add_argument('--refresh-reason')
        elif command in ('extract', 'extract-file'):
            parser.add_argument('source')
            parser.add_argument('--profile', choices=('html', 'shopify', 'tracking', 'document'), default='html' if command == 'extract' else 'document')
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
            elif command == 'question-search':
                parser.add_argument('--query', required=True)
                parser.add_argument('--useful', action='store_true')
                parser.add_argument('--method-change')
        elif command == 'prepare-review':
            parser.add_argument('--parent', required=True)
            parser.add_argument('--risk', choices=('routine', 'significant'), default='routine')
        elif command in ('native-review-proof', 'record-review'):
            parser.add_argument('--parent', required=True)
            parser.add_argument('--reviewer', required=True)
            if command == 'record-review':
                parser.add_argument('--report', required=True)
                parser.add_argument('--risk', choices=('routine', 'significant'), default='routine')
        elif command == 'source-ref':
            parser.add_argument('file')
            parser.add_argument('--part', action='append', default=[])


def analysis_root(file):
    file = Path(file).resolve()
    for parent in file.parents:
        if parent.name == 'ꘖ':
            return parent.parent
    return file.parent


def execute(args):
    from . import workflow as flow
    command = args.command
    if command == 'status':
        return flow.status(args.project)
    if command == 'resume':
        request = args.request_file.read_bytes().decode('utf-8') if args.request_file else None
        return flow.resume(args.project, args.reason, request)
    if command == 'check-project':
        return flow.check_project(args.project)
    if command == 'adopt-requests':
        return flow.adopt_requests(args.project, args.conversation)
    if command == 'record-answer':
        return flow.record_current_answer(args.project, args.response_file.read_bytes().decode('utf-8'))
    if command == 'save-analysis':
        from .analysis import save_analysis
        return save_analysis(args.project, args.candidate, args.expected_sha256)
    if command == 'collect':
        from .research import collect_plan, inside, json_data
        result = collect_plan(args.project, json.loads(args.plan.read_text(encoding='utf-8-sig')))
        if args.output:
            from .analysis import publish_owned
            target = inside(args.project, args.output)
            if not target.is_relative_to(Path(args.project).resolve() / 'ꘖ/KB/Evidence') or '/HTTP/' in target.as_posix() or '/Reviews/' in target.as_posix():
                raise ValueError('Collection report must be a project Evidence file outside immutable HTTP/Reviews observations')
            result['publication'] = publish_owned(target, json_data(result), source=args.plan)
        return result
    if command == 'extract':
        from .research import extract_observation
        return extract_observation(args.project, args.source, args.profile)
    if command == 'capture-dom':
        from .research import capture_dom
        return capture_dom(args.project, args.url, args.tab_id, port=args.cdp_port, refresh_reason=args.refresh_reason)
    if command == 'extract-file':
        from .research import extract_file
        return extract_file(args.project, args.source, args.profile)
    if command == 'stage':
        return flow.complete_stage(args.project, args.stage, args.input, args.output, note=args.note)
    if command == 'question-add':
        spec = json.loads(args.spec.read_text(encoding='utf-8-sig'))
        return flow.add_question(args.project, spec['id'], spec['question'], spec['impact'], spec['done_when'], spec['inputs'], spec['outputs'])
    if command == 'question-claim':
        return flow.claim_question(args.project, args.id, args.owner)
    if command == 'question-finish':
        return flow.finish_question(args.project, args.id, args.owner, args.output, args.gap)
    if command == 'question-handoff':
        return flow.handoff(args.project, args.id, args.previous_owner, args.new_owner, args.reason)
    if command == 'question-search':
        return flow.record_search(args.project, args.id, args.owner, args.query, args.useful, args.method_change)
    if command == 'native-review-proof':
        from .metrics import native_review_proof
        return native_review_proof(args.project, args.parent, args.reviewer)
    if command == 'prepare-review':
        return flow.prepare_review(args.project, args.parent, args.risk)
    if command == 'record-review':
        return flow.record_review(args.project, args.report, parent_id=args.parent, reviewer_id=args.reviewer, risk=args.risk)
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
