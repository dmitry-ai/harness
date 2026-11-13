# 2026-11-14 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Unify declarative CLI routers, scratch-verified --consume-input/stdin loading, and read-back mutations in cli_common.py":
# https://github.com/dmitry-ai/harness/issues/69
# 2026-11-10 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Isolate turn scratch answer files, decouple turn/journal locks, allow pre-delivery re-preparation, and add preemptive step/compaction budget gate":
# https://github.com/dmitry-ai/harness/issues/49
# 2026-11-04 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Scope research questions to active turn, distinguish factual KB notes from hypotheses, and reconcile unprepared chat deliveries":
# https://github.com/dmitry-ai/harness/issues/44
# 2026-10-15 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Eliminate redundant subagent searches with HTTP evidence caching, structured Analysis.json workflow, and in-chat resume":
# https://github.com/dmitry-ai/harness/issues/4
# 2026-10-31 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Reorganize AI into universal harness repository, translate rules and documentation to English, format per P.md, and enforce issue-driven Git workflow":
# https://github.com/dmitry-ai/harness/issues/26
# 2026-10-31 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Enforce universal harness.py CLI, automatic CDP browser fallback on JS shells, and Evidence verification for external links/anchors/quotes":
# https://github.com/dmitry-ai/harness/issues/27
# 2026-11-03 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Isolate post-finalize turns from authorize gate, reset readiness state, and enable conflict journal recovery":
# https://github.com/dmitry-ai/harness/issues/43
import json
from pathlib import Path
from .cli_common import add_arg_specs, consume_scratch_input, load_operation_input, read_input_bytes, read_input_json, read_input_text
from .completion import COMMANDS as COMPLETION_COMMANDS
COMMANDS = ('status', 'resume', 'collect', 'collect-http', 'collect-browser', 'capture-dom', 'extract', 'extract-file', 'sync-attachments', 'check-project', 'stage', 'question-add', 'question-claim', 'question-handoff', 'question-finish', 'question-search', 'prepare-review', 'review-input', 'native-review-proof', 'record-review', 'review-disposition', 'prepare-experiment', 'record-experiment', 'native-executor-metadata', 'adopt-requests', 'unadopt-requests', 'record-answer', 'metrics', 'source-ref', 'save-analysis', 'render-analysis', 'git-read', *COMPLETION_COMMANDS)
_COMMAND_HELP = {'check-project': 'All saved-source and local KB diagnostics; no network calls', 'collect': 'Batch GET/DOM observations and extraction with persistent project cache', 'collect-browser': 'Single-URL CDP browser DOM observation in the configured user browser profile', 'collect-http': 'Single-URL GET/DOM observation and extraction with persistent Evidence cache', 'render-analysis': 'Publish tracked Markdown; preserve unknown/manual edits', 'resume': 'Continue the selected current-chat project from saved agent KB; no inspect/init', 'status': 'Read-only current stage and agent KB navigation', 'sync-attachments': 'Sync client attachments to source/ and both KBs, including document/video/image transcriptions'}
_CONSUME_COMMANDS = {'collect', 'prepare-experiment', 'prepare-review', 'question-add', 'record-answer', 'record-experiment', 'record-review', 'save-analysis', 'sync-attachments'}
_PROJECT_SPECS = {
	'adopt-requests': (('--conversation', {'required': True}), ('--allow-finalized', {'action': 'store_true', 'help': 'Permit adopting requests even if initial analysis finalize stage is complete'})),
	'capture-dom': (('--url', {'required': True}), ('--tab-id', {'required': True}), ('--session-id', {'required': True, 'help': 'Explicit authorized runtime text.browser.sessions entry'}), ('--refresh-reason', {})),
	'collect': (('--plan', {'required': True, 'type': Path}), ('--output', {'help': 'Optional project-owned result JSON'}), ('--browser', {'choices': ('auto', 'always', 'never'), 'default': 'auto', 'help': 'Browser CDP fallback mode (default: auto)'}), ('--cdp-port', {'type': int, 'help': 'Optional explicit CDP port override'})),
	'collect-browser': (('--url', {'required': True, 'help': 'Single HTTP(S) URL to capture via user browser CDP and persist in \ua616/KB/Evidence/HTTP'}), ('--profile', {'choices': ('html', 'shopify', 'tracking', 'document', 'auto'), 'default': 'html'}), ('--scope', {'default': 'public'}), ('--refresh-reason', {}), ('--cdp-port', {'type': int, 'help': 'Optional explicit CDP port override'})),
	'collect-http': (('--url', {'required': True, 'help': 'Single HTTP(S) URL to fetch and persist in \ua616/KB/Evidence/HTTP'}), ('--profile', {'choices': ('html', 'shopify', 'tracking', 'document', 'auto'), 'default': 'auto'}), ('--scope', {'default': 'public'}), ('--refresh-reason', {}), ('--browser', {'choices': ('auto', 'always', 'never'), 'default': 'auto', 'help': 'Browser CDP fallback mode (default: auto)'}), ('--cdp-port', {'type': int, 'help': 'Optional explicit CDP port override'})),
	'extract': (('source', {}), ('--profile', {'choices': ('html', 'shopify', 'tracking', 'document'), 'default': 'html'})),
	'extract-file': (('source', {}), ('--profile', {'choices': ('html', 'shopify', 'tracking', 'document'), 'default': 'document'})),
	'native-executor-metadata': (('--conversation', {'required': True}), ('--save', {'action': 'store_true', 'help': 'Persist immutable native metadata; default is read-only'}), ('--role', {'choices': ('primary', 'AA', 'AF'), 'default': 'primary'}), ('--parent', {})),
	'native-review-proof': (('--parent', {'required': True}), ('--reviewer', {'required': True})),
	'prepare-experiment': (('--spec', {'required': True, 'type': Path}), ('--amendment-of', {}), ('--amendment-reason', {})),
	'prepare-review': (('--parent', {'required': True}), ('--spec', {'required': True, 'type': Path, 'help': 'Explicit risk/basis/request_scope/claim_ids/claims JSON'}), ('--response-file', {'required': True, 'type': Path, 'help': 'Exact candidate response; use - for stdin'})),
	'question-add': (('--spec', {'required': True, 'type': Path}),),
	'question-claim': (('id', {}), ('--owner', {'required': True})),
	'question-finish': (('id', {}), ('--owner', {'required': True}), ('--output', {'action': 'append', 'required': True}), ('--gap', {}), ('--results', {'required': True, 'type': Path, 'help': 'Structured experiment result list JSON; use - for stdin'})),
	'question-handoff': (('id', {}), ('--previous-owner', {'required': True}), ('--new-owner', {'required': True}), ('--reason', {'required': True})),
	'question-search': (('id', {}), ('--owner', {'required': True}), ('--query', {'required': True}), ('--useful', {'action': 'store_true'}), ('--method-change', {})),
	'record-answer': (('--response-file', {'required': True, 'type': Path}),),
	'record-experiment': (('--spec', {'required': True, 'type': Path}),),
	'record-review': (('--parent', {'required': True}), ('--reviewer', {'required': True}), ('--report', {'required': True}), ('--native-evidence', {'help': 'Separate native proof from the completed reviewer'})),
	'resume': (('--reason', {'required': True}), ('--request-file', {'type': Path, 'help': 'Exact current user message; kept in service state until final journal'})),
	'review-disposition': (('--review-id', {'required': True}), ('--finding-id', {'required': True}), ('--status', {'choices': ('resolved', 'rejected'), 'required': True}), ('--basis', {'required': True}), ('--evidence', {'action': 'append', 'required': True}), ('--parent', {'required': True})),
	'review-input': (('--package', {'required': True}),),
	'save-analysis': (('--candidate', {'required': True}), ('--expected-sha256', {})),
	'source-ref': (('file', {}), ('--part', {'action': 'append', 'default': []})),
	'sync-attachments': (('--media-descriptions', {'type': Path, 'help': 'Optional JSON mapping attachment filename/sha256/video URL to Markdown transcription/analysis'}), ('--no-fetch-videos', {'action': 'store_true', 'help': 'Skip network fetching for external video transcripts'})),
	'unadopt-requests': (('--conversation', {}), ('--request-id', {'action': 'append', 'default': [], 'help': 'Specific request ID(s) to unadopt'})),
}
_consumed = consume_scratch_input
_operation_input = load_operation_input
_read_input = read_input_bytes
def _execute_collect(args):
	from .research import collect_plan, compute_site_summary, inside, json_data
	payload = _operation_input(args, args.plan)
	plan = json.loads(payload.decode('utf-8-sig'))
	result = collect_plan(args.project, plan, browser=getattr(args, 'browser', 'auto'), cdp_port=getattr(args, 'cdp_port', None))
	if not args.output:
		r = result
	else:
		from .analysis import digest, publish_owned
		target = inside(args.project, args.output)
		if not target.is_relative_to(Path(args.project).resolve() / '\ua616/KB/Evidence') or '/HTTP/' in target.as_posix() or '/Reviews/' in target.as_posix():
			raise ValueError('Collection report must be a project Evidence file outside immutable HTTP/Reviews observations')
		receipts_file = Path(args.project).resolve() / '\ua616/data/rendered.json'
		if target.is_file() and receipts_file.is_file():
			try:
				receipts = json.loads(receipts_file.read_text(encoding='utf-8'))
				raw_prev = target.read_bytes()
				if receipts.get(str(target), {}).get('sha256') == digest(raw_prev):
					prev_data = json.loads(raw_prev.decode('utf-8'))
					if isinstance(prev_data, dict) and isinstance(prev_data.get('results'), list) and isinstance(result.get('results'), list):
						new_keys = {item.get('request_key') or (item.get('url'), item.get('observation')) for item in result['results'] if isinstance(item, dict)}
						kept = [item for item in prev_data['results'] if isinstance(item, dict) and (item.get('request_key') or (item.get('url'), item.get('observation'))) not in new_keys]
						if kept:
							merged_results = kept + result['results']
							result = {**result, 'results': merged_results, 'site_summary': compute_site_summary(args.project, merged_results), 'complete': bool(prev_data.get('complete', True) and result.get('complete', True))}
			except (OSError, ValueError):
				pass
		result['publication'] = publish_owned(target, json_data(result), source={'kind': 'collection-plan', 'sha256': digest(payload), 'plan': plan})
		r = result if 'conflict' == result['publication']['status'] else _consumed(args, args.plan, payload, result)
	return r
def _load_consumed_json(args, path, fn, *extra_args, **extra_kwargs):
	payload = _operation_input(args, path)
	result = fn(*extra_args, json.loads(payload.decode('utf-8-sig')), **extra_kwargs)
	return _consumed(args, path, payload, result)
def add_parsers(sub):
	from .completion import add_parser_arguments
	from .runtime import settings
	from .workflow import STAGES
	standalone = {
		'git-read': (('project', {'nargs': '?', 'type': Path, 'default': Path(settings()['workspace_root']).resolve()}), ('git_subcommand', {'choices': ('status', 'diff', 'log', 'rev-parse', 'show', 'ls-files'), 'nargs': '?', 'default': 'status'}), ('--short', {'action': 'store_true'}), ('--stat', {'action': 'store_true'}), ('--check', {'action': 'store_true'}), ('--arg', {'dest': 'git_args', 'action': 'append', 'default': []})),
		'metrics': (('traces', {'nargs': '+', 'type': Path}), ('--bindings', {'type': Path, 'help': 'conversation ID -> stage/first_step/last_step intervals'}), ('--project', {'type': Path, 'help': 'Optional exact project: observed cache/search/review metrics'})),
		'render-analysis': (('input', {'type': Path}), ('--output', {'type': Path})),
	}
	stage_specs = (('stage', {'choices': STAGES}), ('--input', {'action': 'append', 'required': True}), ('--output', {'action': 'append', 'required': True}), ('--note', {}))
	for command in COMMANDS:
		parser = sub.add_parser(command, help=_COMMAND_HELP.get(command, 'Internal ' + command + ' operation'))
		if command in COMPLETION_COMMANDS:
			add_parser_arguments(parser, command)
		elif command in standalone:
			add_arg_specs(parser, standalone[command])
		else:
			specs = [('project', {'type': Path, 'help': 'Exact existing project root from the current chat'})]
			if command in _CONSUME_COMMANDS:
				specs.append(('--consume-input', {'action': 'store_true', 'help': 'After success remove an unchanged input only from project \ua616/data/scratch; use - for stdin'}))
			specs.extend(stage_specs if 'stage' == command else _PROJECT_SPECS.get(command, ()))
			add_arg_specs(parser, specs)
def analysis_root(file):
	file = Path(file).resolve()
	r = file.parent
	for parent in file.parents:
		if '\ua616' == parent.name:
			r = parent.parent
			break
	return r
def execute(args):
	from . import workflow as flow
	command = args.command
	if command in COMPLETION_COMMANDS:
		from .completion import execute as complete
		r = complete(args)
	elif 'status' == command:
		r = flow.status(args.project)
	elif 'resume' == command:
		r = flow.resume(args.project, args.reason, read_input_text(args.request_file, encoding='utf-8') if args.request_file else None)
	elif 'check-project' == command:
		r = flow.check_project(args.project)
	elif 'adopt-requests' == command:
		r = flow.adopt_requests(args.project, args.conversation, allow_finalized=getattr(args, 'allow_finalized', False))
	elif 'unadopt-requests' == command:
		r = flow.unadopt_requests(args.project, args.conversation, request_ids=args.request_id)
	elif 'record-answer' == command:
		payload = _operation_input(args, args.response_file)
		r = _consumed(args, args.response_file, payload, flow.record_current_answer(args.project, payload.decode('utf-8')))
	elif 'save-analysis' == command:
		from .analysis import save_analysis
		from .research import inside
		cand = args.candidate if '-' == str(args.candidate) else inside(args.project, args.candidate)
		r = _load_consumed_json(args, cand, lambda data: save_analysis(args.project, data, args.expected_sha256))
	elif 'collect' == command:
		r = _execute_collect(args)
	elif 'collect-http' == command:
		from .research import collect_http
		r = collect_http(args.project, args.url, profile=args.profile, scope=args.scope, refresh_reason=args.refresh_reason, browser=getattr(args, 'browser', 'auto'), cdp_port=getattr(args, 'cdp_port', None))
	elif 'collect-browser' == command:
		from .research import collect_browser
		r = collect_browser(args.project, args.url, profile=args.profile, scope=args.scope, refresh_reason=args.refresh_reason, cdp_port=getattr(args, 'cdp_port', None))
	elif 'extract' == command:
		from .research import extract_observation
		r = extract_observation(args.project, args.source, args.profile)
	elif 'capture-dom' == command:
		from .research import capture_dom
		r = capture_dom(args.project, args.url, args.tab_id, session_id=args.session_id, refresh_reason=args.refresh_reason)
	elif 'extract-file' == command:
		from .research import extract_file
		r = extract_file(args.project, args.source, args.profile)
	elif 'sync-attachments' == command:
		from .knowledge import sync_project_attachments_and_kb
		if not args.media_descriptions:
			r = sync_project_attachments_and_kb(args.project, None, fetch_videos=not args.no_fetch_videos)
		else:
			r = _load_consumed_json(args, args.media_descriptions, lambda desc: sync_project_attachments_and_kb(args.project, desc, fetch_videos=not args.no_fetch_videos))
	elif 'stage' == command:
		r = flow.complete_stage(args.project, args.stage, args.input, args.output, note=args.note)
	elif 'question-add' == command:
		r = _load_consumed_json(args, args.spec, lambda spec: flow.add_question(args.project, spec['id'], spec['question'], spec['impact'], spec['done_when'], spec['inputs'], spec['outputs'], requirements=spec.get('requirements')))
	elif 'question-claim' == command:
		r = flow.claim_question(args.project, args.id, args.owner)
	elif 'question-finish' == command:
		r = flow.finish_question(args.project, args.id, args.owner, args.output, args.gap, results=read_input_json(args.results))
	elif 'question-handoff' == command:
		r = flow.handoff(args.project, args.id, args.previous_owner, args.new_owner, args.reason)
	elif 'question-search' == command:
		r = flow.record_search(args.project, args.id, args.owner, args.query, args.useful, args.method_change)
	elif 'native-review-proof' == command:
		from .metrics import native_review_proof
		r = native_review_proof(args.project, args.parent, args.reviewer)
	elif 'prepare-review' == command:
		if '-' == str(args.spec) and '-' == str(args.response_file):
			raise ValueError('Only one prepare-review input may use stdin')
		spec_payload = _operation_input(args, args.spec)
		payload = _operation_input(args, args.response_file)
		res = flow.prepare_review(args.project, args.parent, json.loads(spec_payload.decode('utf-8-sig')), payload.decode('utf-8'))
		r = _consumed(args, args.response_file, payload, _consumed(args, args.spec, spec_payload, res))
	elif 'review-input' == command:
		r = flow.review_input(args.project, args.package)
	elif 'record-review' == command:
		payload = _operation_input(args, args.report)
		r = _consumed(args, args.report, payload, flow.record_review(args.project, payload, parent_id=args.parent, reviewer_id=args.reviewer, native_evidence=args.native_evidence))
	elif 'review-disposition' == command:
		r = flow.record_review_disposition(args.project, args.review_id, args.finding_id, args.status, args.basis, args.evidence, args.parent)
	elif 'record-experiment' == command:
		from .experiments import record_experiment
		r = _load_consumed_json(args, args.spec, lambda spec: record_experiment(args.project, spec))
	elif 'prepare-experiment' == command:
		from .experiments import prepare_experiment
		r = _load_consumed_json(args, args.spec, lambda spec: prepare_experiment(args.project, spec, amendment_of=args.amendment_of, amendment_reason=args.amendment_reason))
	elif 'native-executor-metadata' == command:
		from .metrics import native_executor_metadata, record_executor_metadata
		callback = record_executor_metadata if args.save else native_executor_metadata
		r = callback(args.project, args.conversation, role=args.role, parent_id=args.parent)
	elif 'metrics' == command:
		from .metrics import project_metrics, summarize
		r = summarize(args.traces, read_input_json(args.bindings, encoding='utf-8') if args.bindings else None)
		if args.project:
			r['project'] = project_metrics(args.project)
	elif 'source-ref' == command:
		from .evidence import source_reference
		r = {'source': source_reference(args.project, args.file, args.part)}
	elif 'render-analysis' == command:
		from .analysis import publish_analysis
		r = publish_analysis(args.input, args.output)
	elif 'git-read' != command:
		raise ValueError('Unknown workflow command')
	else:
		from .git_gate import read_git
		extra = [f'--{flag}' for flag in ('short', 'stat', 'check') if getattr(args, flag, False)] + list(args.git_args)
		r = read_git(args.project, args.git_subcommand, extra)
	return r
