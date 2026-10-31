# 2026-10-15 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Eliminate redundant subagent searches with HTTP evidence caching, structured Analysis.json workflow, and in-chat resume":
# https://github.com/dmitry-ai/harness/issues/4
# 2026-10-31 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Reorganize AI into universal harness repository, translate rules and documentation to English, format per P.md, and enforce issue-driven Git workflow":
# https://github.com/dmitry-ai/harness/issues/26
from pathlib import Path
import json
import sys
from .completion import COMMANDS as COMPLETION_COMMANDS
COMMANDS = ('status', 'resume', 'collect', 'collect-http', 'capture-dom', 'extract', 'extract-file', 'sync-attachments', 'check-project', 'stage', 'question-add', 'question-claim', 'question-finish', 'question-handoff', 'question-search', 'prepare-review', 'review-input', 'native-review-proof', 'record-review', 'review-disposition', 'prepare-experiment', 'record-experiment', 'native-executor-metadata', 'adopt-requests', 'record-answer', 'metrics', 'source-ref', 'save-analysis', 'render-analysis', 'git-read', *COMPLETION_COMMANDS)
def add_parsers(sub):
	for command in COMMANDS:
		parser = sub.add_parser(command, help={'resume': 'Continue the selected current-chat project from saved agent KB; no inspect/init', 'status': 'Read-only current stage and agent KB navigation', 'collect': 'Batch GET observations and extraction with persistent project cache', 'collect-http': 'Single-URL GET observation and extraction with persistent Evidence cache', 'sync-attachments': 'Sync client attachments to source/ and both KBs, including document/video/image transcriptions', 'check-project': 'All saved-source and local KB diagnostics; no network calls', 'render-analysis': 'Publish tracked Markdown; preserve unknown/manual edits'}.get(command, 'Internal ' + command + ' operation'))
		if command in COMPLETION_COMMANDS:
			from .completion import add_parser_arguments
			add_parser_arguments(parser, command)
			continue
		if 'metrics' == command:
			parser.add_argument('traces', nargs='+', type=Path)
			parser.add_argument('--bindings', type=Path, help='conversation ID -> stage/first_step/last_step intervals')
			parser.add_argument('--project', type=Path, help='Optional exact project: observed cache/search/review metrics')
			continue
		if 'render-analysis' == command:
			parser.add_argument('input', type=Path)
			parser.add_argument('--output', type=Path)
			continue
		if 'git-read' == command:
			from .runtime import settings
			parser.add_argument('project', nargs='?', type=Path, default=Path(settings()['workspace_root']).resolve())
			parser.add_argument('git_subcommand', choices=('status', 'diff', 'log', 'rev-parse', 'show', 'ls-files'), nargs='?', default='status')
			parser.add_argument('--short', action='store_true')
			parser.add_argument('--stat', action='store_true')
			parser.add_argument('--check', action='store_true')
			parser.add_argument('--arg', dest='git_args', action='append', default=[])
			continue
		parser.add_argument('project', type=Path, help='Exact existing project root from the current chat')
		if command in ('record-answer', 'save-analysis', 'collect', 'question-add', 'sync-attachments', 'prepare-review', 'record-review', 'prepare-experiment', 'record-experiment'):
			parser.add_argument('--consume-input', action='store_true', help='After success remove an unchanged input only from project ꘖ/data/scratch; use - for stdin')
		if 'resume' == command:
			parser.add_argument('--reason', required=True)
			parser.add_argument('--request-file', type=Path, help='Exact current user message; kept in service state until final journal')
		elif 'adopt-requests' == command:
			parser.add_argument('--conversation', required=True)
		elif 'record-answer' == command:
			parser.add_argument('--response-file', required=True, type=Path)
		elif 'save-analysis' == command:
			parser.add_argument('--candidate', required=True)
			parser.add_argument('--expected-sha256')
		elif 'collect' == command:
			parser.add_argument('--plan', required=True, type=Path)
			parser.add_argument('--output', help='Optional project-owned result JSON')
		elif 'collect-http' == command:
			parser.add_argument('--url', required=True, help='Single HTTP(S) URL to fetch and persist in ꘖ/KB/Evidence/HTTP')
			parser.add_argument('--profile', choices=('html', 'shopify', 'tracking', 'document', 'auto'), default='auto')
			parser.add_argument('--scope', default='public')
			parser.add_argument('--refresh-reason')
		elif 'capture-dom' == command:
			parser.add_argument('--url', required=True)
			parser.add_argument('--tab-id', required=True)
			parser.add_argument('--session-id', required=True, help='Explicit authorized runtime text.browser.sessions entry')
			parser.add_argument('--refresh-reason')
		elif command in ('extract', 'extract-file'):
			parser.add_argument('source')
			parser.add_argument('--profile', choices=('html', 'shopify', 'tracking', 'document'), default='html' if 'extract' == command else 'document')
		elif 'sync-attachments' == command:
			parser.add_argument('--media-descriptions', type=Path, help='Optional JSON mapping attachment filename/sha256/video URL to Markdown transcription/analysis')
			parser.add_argument('--no-fetch-videos', action='store_true', help='Skip network fetching for external video transcripts')
		elif 'stage' == command:
			from .workflow import STAGES
			parser.add_argument('stage', choices=STAGES)
			parser.add_argument('--input', action='append', required=True)
			parser.add_argument('--output', action='append', required=True)
			parser.add_argument('--note')
		elif 'question-add' == command:
			parser.add_argument('--spec', type=Path, required=True)
		elif command.startswith('question-'):
			parser.add_argument('id')
			if 'question-handoff' != command:
				parser.add_argument('--owner', required=True)
			else:
				parser.add_argument('--previous-owner', required=True)
				parser.add_argument('--new-owner', required=True)
				parser.add_argument('--reason', required=True)
			if 'question-finish' == command:
				parser.add_argument('--output', action='append', required=True)
				parser.add_argument('--gap')
				parser.add_argument('--results', required=True, type=Path, help='Structured experiment result list JSON; use - for stdin')
			elif 'question-search' == command:
				parser.add_argument('--query', required=True)
				parser.add_argument('--useful', action='store_true')
				parser.add_argument('--method-change')
		elif 'prepare-review' == command:
			parser.add_argument('--parent', required=True)
			parser.add_argument('--spec', required=True, type=Path, help='Explicit risk/basis/request_scope/claim_ids/claims JSON')
			parser.add_argument('--response-file', required=True, type=Path, help='Exact candidate response; use - for stdin')
		elif 'review-input' == command:
			parser.add_argument('--package', required=True)
		elif command in ('native-review-proof', 'record-review'):
			parser.add_argument('--parent', required=True)
			parser.add_argument('--reviewer', required=True)
			if 'record-review' == command:
				parser.add_argument('--report', required=True)
				parser.add_argument('--native-evidence', help='Separate native proof from the completed reviewer')
		elif 'review-disposition' == command:
			parser.add_argument('--review-id', required=True)
			parser.add_argument('--finding-id', required=True)
			parser.add_argument('--status', choices=('resolved', 'rejected'), required=True)
			parser.add_argument('--basis', required=True)
			parser.add_argument('--evidence', action='append', required=True)
			parser.add_argument('--parent', required=True)
		elif 'record-experiment' == command:
			parser.add_argument('--spec', required=True, type=Path)
		elif 'prepare-experiment' == command:
			parser.add_argument('--spec', required=True, type=Path)
			parser.add_argument('--amendment-of')
			parser.add_argument('--amendment-reason')
		elif 'native-executor-metadata' == command:
			parser.add_argument('--conversation', required=True)
			parser.add_argument('--save', action='store_true', help='Persist immutable native metadata; default is read-only')
			parser.add_argument('--role', choices=('primary', 'AA', 'AF'), default='primary')
			parser.add_argument('--parent')
		elif 'source-ref' == command:
			parser.add_argument('file')
			parser.add_argument('--part', action='append', default=[])
def analysis_root(file):
	file = Path(file).resolve()
	for parent in file.parents:
		if 'ꘖ' == parent.name:
			return parent.parent
	return file.parent
def _read_input(path):
	return sys.stdin.buffer.read() if '-' == str(path) else Path(path).read_bytes()
def _consumed(args, path, payload, result):
	if not getattr(args, 'consume_input', False) or '-' == str(path):
		r = result
	else:
		from .storage import data_dir_for
		target = Path(path).resolve()
		scratch_dirs = [data_dir_for(args.project) / 'scratch', Path(args.project).resolve() / 'ꘖ/data/scratch']
		if not any((target.is_relative_to(s) for s in scratch_dirs)) or Path(path).is_symlink() or any((p.is_junction() for p in (target, *target.parents) if p.exists())):
			raise ValueError('Consumed input must be an ordinary file inside project ꘖ/data/scratch')
		if 'conflict' == result.get('status') or False is result.get('complete') or False is result.get('valid'):
			r = result
		else:
			if target.exists() and target.read_bytes() == payload:
				target.unlink()
				result['consumed_input'] = str(target)
			r = result
	return r
def _operation_input(args, path):
	if getattr(args, 'consume_input', False) and '-' != str(path):
		from .storage import data_dir_for
		target = Path(path).resolve()
		scratch_dirs = [data_dir_for(args.project) / 'scratch', Path(args.project).resolve() / 'ꘖ/data/scratch']
		if not any((target.is_relative_to(s) for s in scratch_dirs)) or Path(path).is_symlink() or any((p.is_junction() for p in (target, *target.parents) if p.exists())):
			raise ValueError('Consumed input must be an ordinary file inside project ꘖ/data/scratch')
	r = _read_input(path)
	return r
def execute(args):
	from . import workflow as flow
	command = args.command
	if command in COMPLETION_COMMANDS:
		from .completion import execute as complete
		return complete(args)
	if 'status' == command:
		return flow.status(args.project)
	if 'resume' == command:
		request = _read_input(args.request_file).decode('utf-8') if args.request_file else None
		return flow.resume(args.project, args.reason, request)
	if 'check-project' == command:
		return flow.check_project(args.project)
	if 'adopt-requests' == command:
		return flow.adopt_requests(args.project, args.conversation)
	if 'record-answer' == command:
		payload = _operation_input(args, args.response_file)
		result = flow.record_current_answer(args.project, payload.decode('utf-8'))
		return _consumed(args, args.response_file, payload, result)
	if 'save-analysis' == command:
		from .analysis import save_analysis
		from .research import inside
		candidate = args.candidate if '-' == str(args.candidate) else inside(args.project, args.candidate)
		payload = _operation_input(args, candidate)
		result = save_analysis(args.project, json.loads(payload.decode('utf-8-sig')), args.expected_sha256)
		return _consumed(args, candidate, payload, result)
	if 'collect' == command:
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
								result = {**result, 'results': merged_results, 'site_summary': compute_site_summary(args.project, merged_results), 'complete': bool(prev_data.get('complete', True) and result.get('complete', True))}
				except (OSError, ValueError):
					pass
			result['publication'] = publish_owned(target, json_data(result), source={'kind': 'collection-plan', 'sha256': digest(payload), 'plan': plan})
			if 'conflict' == result['publication']['status']:
				return result
			return _consumed(args, args.plan, payload, result)
		return result
	if 'collect-http' == command:
		from .research import collect_http
		return collect_http(args.project, args.url, profile=args.profile, scope=args.scope, refresh_reason=args.refresh_reason)
	if 'extract' == command:
		from .research import extract_observation
		return extract_observation(args.project, args.source, args.profile)
	if 'capture-dom' == command:
		from .research import capture_dom
		return capture_dom(args.project, args.url, args.tab_id, session_id=args.session_id, refresh_reason=args.refresh_reason)
	if 'extract-file' == command:
		from .research import extract_file
		return extract_file(args.project, args.source, args.profile)
	if 'sync-attachments' == command:
		from .knowledge import sync_project_attachments_and_kb
		descriptions, payload = (None, None)
		if args.media_descriptions:
			payload = _operation_input(args, args.media_descriptions)
			descriptions = json.loads(payload.decode('utf-8-sig'))
		result = sync_project_attachments_and_kb(args.project, descriptions, fetch_videos=not args.no_fetch_videos)
		return _consumed(args, args.media_descriptions, payload, result) if args.media_descriptions else result
	if 'stage' == command:
		return flow.complete_stage(args.project, args.stage, args.input, args.output, note=args.note)
	if 'question-add' == command:
		payload = _operation_input(args, args.spec)
		spec = json.loads(payload.decode('utf-8-sig'))
		result = flow.add_question(args.project, spec['id'], spec['question'], spec['impact'], spec['done_when'], spec['inputs'], spec['outputs'], requirements=spec.get('requirements'))
		return _consumed(args, args.spec, payload, result)
	if 'question-claim' == command:
		return flow.claim_question(args.project, args.id, args.owner)
	if 'question-finish' == command:
		return flow.finish_question(args.project, args.id, args.owner, args.output, args.gap, results=json.loads(_read_input(args.results).decode('utf-8-sig')))
	if 'question-handoff' == command:
		return flow.handoff(args.project, args.id, args.previous_owner, args.new_owner, args.reason)
	if 'question-search' == command:
		return flow.record_search(args.project, args.id, args.owner, args.query, args.useful, args.method_change)
	if 'native-review-proof' == command:
		from .metrics import native_review_proof
		return native_review_proof(args.project, args.parent, args.reviewer)
	if 'prepare-review' == command:
		if '-' == str(args.spec) and '-' == str(args.response_file):
			raise ValueError('Only one prepare-review input may use stdin')
		spec_payload = _operation_input(args, args.spec)
		payload = _operation_input(args, args.response_file)
		result = flow.prepare_review(args.project, args.parent, json.loads(spec_payload.decode('utf-8-sig')), payload.decode('utf-8'))
		result = _consumed(args, args.spec, spec_payload, result)
		return _consumed(args, args.response_file, payload, result)
	if 'review-input' == command:
		return flow.review_input(args.project, args.package)
	if 'record-review' == command:
		payload = _operation_input(args, args.report)
		result = flow.record_review(args.project, payload, parent_id=args.parent, reviewer_id=args.reviewer, native_evidence=args.native_evidence)
		return _consumed(args, args.report, payload, result)
	if 'review-disposition' == command:
		return flow.record_review_disposition(args.project, args.review_id, args.finding_id, args.status, args.basis, args.evidence, args.parent)
	if 'record-experiment' == command:
		from .experiments import record_experiment
		payload = _operation_input(args, args.spec)
		result = record_experiment(args.project, json.loads(payload.decode('utf-8-sig')))
		return _consumed(args, args.spec, payload, result)
	if 'prepare-experiment' == command:
		from .experiments import prepare_experiment
		payload = _operation_input(args, args.spec)
		result = prepare_experiment(args.project, json.loads(payload.decode('utf-8-sig')), amendment_of=args.amendment_of, amendment_reason=args.amendment_reason)
		return _consumed(args, args.spec, payload, result)
	if 'native-executor-metadata' == command:
		from .metrics import native_executor_metadata, record_executor_metadata
		callback = record_executor_metadata if args.save else native_executor_metadata
		return callback(args.project, args.conversation, role=args.role, parent_id=args.parent)
	if 'metrics' == command:
		from .metrics import summarize
		bindings = json.loads(args.bindings.read_text(encoding='utf-8')) if args.bindings else None
		result = summarize(args.traces, bindings)
		if args.project:
			from .metrics import project_metrics
			result['project'] = project_metrics(args.project)
		return result
	if 'source-ref' == command:
		from .evidence import source_reference
		return {'source': source_reference(args.project, args.file, args.part)}
	if 'render-analysis' == command:
		from .analysis import publish_analysis
		return publish_analysis(args.input, args.output)
	if 'git-read' == command:
		from .git_gate import read_git
		extra = [f'--{flag}' for flag in ('short', 'stat', 'check') if getattr(args, flag, False)] + list(args.git_args)
		return read_git(args.project, args.git_subcommand, extra)
	raise ValueError('Unknown workflow command')
