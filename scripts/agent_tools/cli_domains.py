# 2026-11-23 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from pathlib import Path
import json
from .cli_common import consume_scratch_input, load_operation_input, read_input_json, read_input_text
def _collect_urls(args, *, require_nonempty: bool=True) -> list[str]:
	legacy_single = getattr(args, 'url', None)
	raw = [*(getattr(args, 'urls_pos', None) or ()), *(getattr(args, 'url_list', None) or ()), *([legacy_single] if isinstance(legacy_single, str) and legacy_single.strip() else ())]
	urls = [str(u).strip() for u in raw if isinstance(u, str) and str(u).strip()]
	if require_nonempty and (not urls):
		raise ValueError('Provide at least one URL via positional <URL> or --url <URL>')
	return urls
def _load_consumed(args, path, fn, *extra_args, **extra_kwargs):
	payload = load_operation_input(args, path)
	result = fn(*extra_args, json.loads(payload.decode('utf-8-sig')), **extra_kwargs)
	return consume_scratch_input(args, path, payload, result)
def _op_adopt_requests(args):
	from . import workflow as flow
	return flow.adopt_requests(args.project, args.conversation, allow_finalized=getattr(args, 'allow_finalized', False))
def _op_capture_dom(args):
	from .research import capture_dom
	return capture_dom(args.project, args.url, args.tab_id, session_id=args.session_id, refresh_reason=args.refresh_reason)
def _op_check_project(args):
	from . import workflow as flow
	return flow.check_project(args.project)
def _op_collect(args):
	from .operations import _execute_collect
	return _execute_collect(args)
def _op_collect_browser(args):
	from .research import collect_browser, collect_browser_batch
	urls = _collect_urls(args, require_nonempty=True)
	fn = collect_browser if 1 == len(urls) else collect_browser_batch
	return fn(args.project, urls[0] if 1 == len(urls) else urls, profile=args.profile, scope=args.scope, session_id=getattr(args, 'session_id', None), refresh_reason=args.refresh_reason, cdp_port=getattr(args, 'cdp_port', None))
def _op_collect_http(args):
	from .research import collect_http, collect_http_batch
	urls = _collect_urls(args, require_nonempty=True)
	fn = collect_http if 1 == len(urls) else collect_http_batch
	return fn(args.project, urls[0] if 1 == len(urls) else urls, profile=args.profile, scope=args.scope, session_id=getattr(args, 'session_id', None), refresh_reason=args.refresh_reason, browser=getattr(args, 'browser', 'auto'), cdp_port=getattr(args, 'cdp_port', None))
def _op_evidence_query(args):
	from .research import evidence_query
	return evidence_query(args.project, urls=_collect_urls(args, require_nonempty=False), include_anchors=bool(getattr(args, 'anchors', False)), grep_pattern=getattr(args, 'grep', None), context_lines=int(getattr(args, 'context_lines', 2)), max_matches=int(getattr(args, 'max_matches', 20)))
def _op_extract(args):
	from .research import extract_observation
	return extract_observation(args.project, args.source, args.profile)
def _op_extract_file(args):
	from .research import extract_file
	return extract_file(args.project, args.source, args.profile)
def _op_git_read(args):
	from .git_gate import read_git
	extra = [f'--{flag}' for flag in ('short', 'stat', 'check') if getattr(args, flag, False)] + list(args.git_args)
	return read_git(args.project, args.git_subcommand, extra)
def _op_metrics(args):
	from .metrics import project_metrics, summarize, summarize_instance
	bindings = read_input_json(args.bindings, encoding='utf-8') if args.bindings else None
	if args.traces:
		r = summarize(args.traces, bindings)
	elif getattr(args, 'conversation', None):
		r = summarize_instance(args.conversation, instance=getattr(args, 'instance', None), platform=getattr(args, 'platform', None), bindings=bindings)
	else:
		raise ValueError('Provide trace file paths or --conversation')
	if args.project:
		r['project'] = project_metrics(args.project)
	return r
def _op_native_executor_metadata(args):
	from .metrics import native_executor_metadata, record_executor_metadata
	callback = record_executor_metadata if args.save else native_executor_metadata
	return callback(args.project, args.conversation, role=args.role, parent_id=args.parent, instance=getattr(args, 'instance', None))
def _op_native_review_proof(args):
	from .metrics import native_review_proof
	# 2026-11-24
	# "Clarify verbatim target_claim contract and add native-review-proof wait timeout":
	# https://github.com/dmitry-ai/harness/issues/212
	return native_review_proof(args.project, args.parent, args.reviewer, instance=getattr(args, 'instance', None), wait_timeout=float(getattr(args, 'wait_timeout', 0.0)))
def _op_prepare_experiment(args):
	from .experiments import prepare_experiment
	return _load_consumed(args, args.spec, lambda spec: prepare_experiment(args.project, spec, amendment_of=args.amendment_of, amendment_reason=args.amendment_reason))
def _op_prepare_review(args):
	from . import workflow as flow
	if '-' == str(args.spec) and '-' == str(args.response_file):
		raise ValueError('Only one prepare-review input may use stdin')
	spec_payload = load_operation_input(args, args.spec)
	payload = load_operation_input(args, args.response_file)
	res = flow.prepare_review(args.project, args.parent, json.loads(spec_payload.decode('utf-8-sig')), payload.decode('utf-8'))
	return consume_scratch_input(args, args.response_file, payload, consume_scratch_input(args, args.spec, spec_payload, res))
def _op_question_add(args):
	from . import workflow as flow
	return _load_consumed(args, args.spec, lambda spec: flow.add_question(args.project, spec['id'], spec['question'], spec['impact'], spec['done_when'], spec['inputs'], spec['outputs'], requirements=spec.get('requirements')))
def _op_question_claim(args):
	from . import workflow as flow
	return flow.claim_question(args.project, args.id, args.owner)
def _op_question_finish(args):
	from . import workflow as flow
	return flow.finish_question(args.project, args.id, args.owner, args.output, args.gap, results=read_input_json(args.results))
def _op_question_handoff(args):
	from . import workflow as flow
	return flow.handoff(args.project, args.id, args.previous_owner, args.new_owner, args.reason)
def _op_question_search(args):
	from . import workflow as flow
	return flow.record_search(args.project, args.id, args.owner, args.query, args.useful, args.method_change)
def _op_record_answer(args):
	from . import workflow as flow
	payload = load_operation_input(args, args.response_file)
	return consume_scratch_input(args, args.response_file, payload, flow.record_current_answer(args.project, payload.decode('utf-8')))
def _op_record_experiment(args):
	from .experiments import record_experiment
	return _load_consumed(args, args.spec, lambda spec: record_experiment(args.project, spec))
def _op_record_review(args):
	from . import workflow as flow
	# 2026-11-24
	# "Include required package keys in REPORT_CONTRACT and resolve record-review paths":
	# https://github.com/dmitry-ai/harness/issues/223
	report_path = _resolve_project_input(args.project, args.report)
	payload = load_operation_input(args, report_path)
	return consume_scratch_input(args, report_path, payload, flow.record_review(args.project, payload, parent_id=args.parent, reviewer_id=args.reviewer, native_evidence=args.native_evidence))
def _op_render_analysis(args):
	from .analysis import publish_analysis
	r = publish_analysis(args.input, args.output)
	# 2026-11-26 "Add transactional rename-project command with automatic domain promotion": https://github.com/dmitry-ai/harness/issues/267
	if getattr(args, 'promote_domain', False) and 'conflict' != r.get('status'):
		from .operations import analysis_root
		from .project_rename import apply_domain_promotion
		r = apply_domain_promotion(analysis_root(args.input), json.loads(Path(args.input).read_text(encoding='utf-8-sig')), r)
	return r
def _op_resume(args):
	from . import workflow as flow
	return flow.resume(args.project, args.reason, read_input_text(args.request_file, encoding='utf-8') if args.request_file else None)
def _op_review_disposition(args):
	from . import workflow as flow
	return flow.record_review_disposition(args.project, args.review_id, args.finding_id, args.status, args.basis, args.evidence, args.parent)
def _op_review_input(args):
	from . import workflow as flow
	return flow.review_input(args.project, args.package)
def _op_save_analysis(args):
	from .research import inside
	cand = args.candidate if '-' == str(args.candidate) else inside(args.project, args.candidate)
	# 2026-11-24
	# "Prevent context compaction with schema-help CLI and staged analysis merge":
	# https://github.com/dmitry-ai/harness/issues/217
	if getattr(args, 'merge', False) or getattr(args, 'partial', False):
		from .analysis_merge import save_merged_analysis
		r = _load_consumed(args, cand, lambda data: save_merged_analysis(args.project, data, args.expected_sha256, partial=bool(getattr(args, 'partial', False))))
	else:
		from .analysis import save_analysis
		r = _load_consumed(args, cand, lambda data: save_analysis(args.project, data, args.expected_sha256))
	# 2026-11-26 "Add transactional rename-project command with automatic domain promotion": https://github.com/dmitry-ai/harness/issues/267
	if getattr(args, 'promote_domain', False) and (not getattr(args, 'partial', False)):
		from .project_rename import apply_domain_promotion
		r = apply_domain_promotion(args.project, json.loads(Path(r['target']).read_text(encoding='utf-8-sig')), r)
	return r
def _op_source_ref(args):
	from .evidence import source_reference
	return {'source': source_reference(args.project, args.file, args.part)}
def _op_stage(args):
	from . import workflow as flow
	return flow.complete_stage(args.project, args.stage, args.input, args.output, note=args.note)
def _op_status(args):
	from . import workflow as flow
	return flow.status(args.project)
# 2026-11-24
# "Include required package keys in REPORT_CONTRACT and resolve record-review paths":
# https://github.com/dmitry-ai/harness/issues/223
def _resolve_project_input(project, raw_path):
	r = raw_path
	if isinstance(raw_path, str) and '-' != raw_path and (not Path(raw_path).is_absolute()):
		from .research import inside
		proj_cand = inside(project, raw_path)
		if proj_cand.is_file() or (not Path(raw_path).is_file()):
			r = str(proj_cand)
	return r
def _op_sync_attachments(args):
	from .knowledge import sync_project_attachments_and_kb
	if not args.media_descriptions:
		r = sync_project_attachments_and_kb(args.project, None, fetch_videos=not args.no_fetch_videos)
	else:
		r = _load_consumed(args, args.media_descriptions, lambda desc: sync_project_attachments_and_kb(args.project, desc, fetch_videos=not args.no_fetch_videos))
	return r
def _op_unadopt_requests(args):
	from . import workflow as flow
	return flow.unadopt_requests(args.project, args.conversation, request_ids=args.request_id)
# 2026-11-23
# "Replace monolithic CLI router with declarative registry and modular docs":
# https://github.com/dmitry-ai/harness/issues/168
OPERATION_HANDLERS = {
	'adopt-requests': _op_adopt_requests,
	'capture-dom': _op_capture_dom,
	'check-project': _op_check_project,
	'collect': _op_collect,
	'collect-browser': _op_collect_browser,
	'collect-http': _op_collect_http,
	'evidence-query': _op_evidence_query,
	'extract': _op_extract,
	'extract-file': _op_extract_file,
	'git-read': _op_git_read,
	'metrics': _op_metrics,
	'native-executor-metadata': _op_native_executor_metadata,
	'native-review-proof': _op_native_review_proof,
	'prepare-experiment': _op_prepare_experiment,
	'prepare-review': _op_prepare_review,
	'question-add': _op_question_add,
	'question-claim': _op_question_claim,
	'question-finish': _op_question_finish,
	'question-handoff': _op_question_handoff,
	'question-search': _op_question_search,
	'record-answer': _op_record_answer,
	'record-experiment': _op_record_experiment,
	'record-review': _op_record_review,
	'render-analysis': _op_render_analysis,
	'resume': _op_resume,
	'review-disposition': _op_review_disposition,
	'review-input': _op_review_input,
	'save-analysis': _op_save_analysis,
	'source-ref': _op_source_ref,
	'stage': _op_stage,
	'status': _op_status,
	'sync-attachments': _op_sync_attachments,
	'unadopt-requests': _op_unadopt_requests,
}
