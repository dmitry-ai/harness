# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from pathlib import Path
from typing import Any
from Df.Harness.lib.cli import dfh_collect_urls
from Df.Harness.lib.cli_input import dfh_consume_scratch_input, dfh_load_operation_input, dfh_read_input_json, dfh_read_input_text
from Df.Harness.lib.path_resolve import dfh_load_registry, dfh_project_paths
from Df.Harness.lib.path_schema import dfh_canonicalize_root_dir
import json
# 2026-11-26 "Move turn lifecycle subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/383
# @used-by :func:`_op_prepare_experiment()`
# @used-by :func:`_op_question_add()`
# @used-by :func:`_op_record_experiment()`
# @used-by :func:`_op_save_analysis()`
# @used-by :func:`_op_sync_attachments()`
def _load_consumed(args: Any, path: Any, fn, *extra_args, **extra_kwargs) -> Any:
	payload = dfh_load_operation_input(args, path)
	result = fn(*extra_args, json.loads(payload.decode('utf-8-sig')), **extra_kwargs)
	return dfh_consume_scratch_input(args, path, payload, result)
# @used-by :func:`dfh_execute_collect()`
# @used-by :meth:`test_df_harness_s11_wave2d_cli_cov.DfHarnessS11Wave2dCliCovTests.test_cli_domain_ops_all_handlers_and_collect_merge()`
def _merge_prior_collection(project: Any, target: Path, receipts_file: Path, result: dict, digest_fn, summary_fn) -> dict:
	r = result
	if target.is_file() and receipts_file.is_file():
		try:
			receipts = json.loads(receipts_file.read_text(encoding='utf-8'))
			raw_prev = target.read_bytes()
			if receipts.get(str(target), {}).get('sha256') == digest_fn(raw_prev):
				prev_data = json.loads(raw_prev.decode('utf-8'))
				if isinstance(prev_data, dict) and isinstance(prev_data.get('results'), list) and isinstance(result.get('results'), list):
					new_keys = {item.get('request_key') or (item.get('url'), item.get('observation')) for item in result['results'] if isinstance(item, dict)}
					kept = [item for item in prev_data['results'] if isinstance(item, dict) and (item.get('request_key') or (item.get('url'), item.get('observation'))) not in new_keys]
					if kept:
						merged = kept + result['results']
						r = {**result, 'results': merged, 'site_summary': summary_fn(project, merged), 'complete': bool(prev_data.get('complete', True) and result.get('complete', True))}
		except (OSError, ValueError):
			pass
	return r
# @used-by :mod:`Df.Harness.lib.cli_domain_ops`
def _op_adopt_requests(args: Any) -> Any:
	from agent_tools import workflow as flow
	return flow.adopt_requests(args.project, args.conversation, allow_finalized=getattr(args, 'allow_finalized', False))
# @used-by :mod:`Df.Harness.lib.cli_domain_ops`
def _op_capture_dom(args: Any) -> Any:
	from agent_tools.research import capture_dom
	return capture_dom(args.project, args.url, args.tab_id, session_id=args.session_id, refresh_reason=args.refresh_reason)
# @used-by :mod:`Df.Harness.lib.cli_domain_ops`
def _op_check_project(args: Any) -> Any:
	from agent_tools import workflow as flow
	return flow.check_project(args.project)
# @used-by :mod:`Df.Harness.lib.cli_domain_ops`
def _op_collect(args: Any) -> Any:
	return dfh_execute_collect(args)
# @used-by :mod:`Df.Harness.lib.cli_domain_ops`
def _op_collect_browser(args: Any) -> Any:
	from agent_tools.research import collect_browser, collect_browser_batch
	urls = dfh_collect_urls(args, require_nonempty=True)
	fn = collect_browser if 1 == len(urls) else collect_browser_batch
	return fn(args.project, urls[0] if 1 == len(urls) else urls, profile=args.profile, scope=args.scope, session_id=getattr(args, 'session_id', None), refresh_reason=args.refresh_reason, cdp_port=getattr(args, 'cdp_port', None))
# @used-by :mod:`Df.Harness.lib.cli_domain_ops`
def _op_collect_http(args: Any) -> Any:
	from agent_tools.research import collect_http, collect_http_batch
	urls = dfh_collect_urls(args, require_nonempty=True)
	fn = collect_http if 1 == len(urls) else collect_http_batch
	return fn(args.project, urls[0] if 1 == len(urls) else urls, profile=args.profile, scope=args.scope, session_id=getattr(args, 'session_id', None), refresh_reason=args.refresh_reason, browser=getattr(args, 'browser', 'auto'), cdp_port=getattr(args, 'cdp_port', None))
# @used-by :mod:`Df.Harness.lib.cli_domain_ops`
def _op_evidence_query(args: Any) -> Any:
	from agent_tools.research import evidence_query
	return evidence_query(args.project, urls=dfh_collect_urls(args, require_nonempty=False), include_anchors=bool(getattr(args, 'anchors', False)), grep_pattern=getattr(args, 'grep', None), context_lines=int(getattr(args, 'context_lines', 2)), max_matches=int(getattr(args, 'max_matches', 20)))
# @used-by :mod:`Df.Harness.lib.cli_domain_ops`
def _op_extract(args: Any) -> Any:
	from agent_tools.research import extract_observation
	return extract_observation(args.project, args.source, args.profile)
# @used-by :mod:`Df.Harness.lib.cli_domain_ops`
def _op_extract_file(args: Any) -> Any:
	from agent_tools.research import extract_file
	return extract_file(args.project, args.source, args.profile)
# @used-by :mod:`Df.Harness.lib.cli_domain_ops`
def _op_git_read(args: Any) -> Any:
	from agent_tools.git_gate import read_git
	extra = [f'--{flag}' for flag in ('short', 'stat', 'check') if getattr(args, flag, False)] + list(args.git_args)
	return read_git(args.project, args.git_subcommand, extra)
# @used-by :mod:`Df.Harness.lib.cli_domain_ops`
def _op_metrics(args: Any) -> Any:
	from agent_tools.metrics import project_metrics, summarize, summarize_instance
	bindings = dfh_read_input_json(args.bindings, encoding='utf-8') if args.bindings else None
	if args.traces:
		r = summarize(args.traces, bindings)
	elif getattr(args, 'conversation', None):
		r = summarize_instance(args.conversation, instance=getattr(args, 'instance', None), platform=getattr(args, 'platform', None), bindings=bindings)
	else:
		raise ValueError('Provide trace file paths or --conversation')
	if args.project:
		r['project'] = project_metrics(args.project)
	return r
# @used-by :mod:`Df.Harness.lib.cli_domain_ops`
def _op_native_executor_metadata(args: Any) -> Any:
	from agent_tools.metrics import native_executor_metadata, record_executor_metadata
	callback = record_executor_metadata if args.save else native_executor_metadata
	return callback(args.project, args.conversation, role=args.role, parent_id=args.parent, instance=getattr(args, 'instance', None))
# @used-by :mod:`Df.Harness.lib.cli_domain_ops`
def _op_native_review_proof(args: Any) -> Any:
	from agent_tools.metrics import native_review_proof
	return native_review_proof(args.project, args.parent, args.reviewer, instance=getattr(args, 'instance', None), wait_timeout=float(getattr(args, 'wait_timeout', 0.0)))
# @used-by :mod:`Df.Harness.lib.cli_domain_ops`
def _op_prepare_experiment(args: Any) -> Any:
	from agent_tools.experiments import prepare_experiment
	return _load_consumed(args, args.spec, lambda spec: prepare_experiment(args.project, spec, amendment_of=args.amendment_of, amendment_reason=args.amendment_reason))
# @used-by :mod:`Df.Harness.lib.cli_domain_ops`
def _op_prepare_review(args: Any) -> Any:
	from agent_tools import workflow as flow
	if '-' == str(args.spec) and '-' == str(args.response_file):
		raise ValueError('Only one prepare-review input may use stdin')
	spec_payload = dfh_load_operation_input(args, args.spec)
	payload = dfh_load_operation_input(args, args.response_file)
	res = flow.prepare_review(args.project, args.parent, json.loads(spec_payload.decode('utf-8-sig')), payload.decode('utf-8'))
	return dfh_consume_scratch_input(args, args.response_file, payload, dfh_consume_scratch_input(args, args.spec, spec_payload, res))
# @used-by :mod:`Df.Harness.lib.cli_domain_ops`
def _op_question_add(args: Any) -> Any:
	from agent_tools import workflow as flow
	return _load_consumed(args, args.spec, lambda spec: flow.add_question(args.project, spec['id'], spec['question'], spec['impact'], spec['done_when'], spec['inputs'], spec['outputs'], requirements=spec.get('requirements')))
# @used-by :mod:`Df.Harness.lib.cli_domain_ops`
def _op_question_claim(args: Any) -> Any:
	from agent_tools import workflow as flow
	return flow.claim_question(args.project, args.id, args.owner)
# @used-by :mod:`Df.Harness.lib.cli_domain_ops`
def _op_question_finish(args: Any) -> Any:
	from agent_tools import workflow as flow
	return flow.finish_question(args.project, args.id, args.owner, args.output, args.gap, results=dfh_read_input_json(args.results))
# @used-by :mod:`Df.Harness.lib.cli_domain_ops`
def _op_question_handoff(args: Any) -> Any:
	from agent_tools import workflow as flow
	return flow.handoff(args.project, args.id, args.previous_owner, args.new_owner, args.reason)
# @used-by :mod:`Df.Harness.lib.cli_domain_ops`
def _op_question_search(args: Any) -> Any:
	from agent_tools import workflow as flow
	return flow.record_search(args.project, args.id, args.owner, args.query, args.useful, args.method_change)
# @used-by :mod:`Df.Harness.lib.cli_domain_ops`
def _op_record_answer(args: Any) -> Any:
	from agent_tools import workflow as flow
	payload = dfh_load_operation_input(args, args.response_file)
	return dfh_consume_scratch_input(args, args.response_file, payload, flow.record_current_answer(args.project, payload.decode('utf-8')))
# @used-by :mod:`Df.Harness.lib.cli_domain_ops`
def _op_record_experiment(args: Any) -> Any:
	from agent_tools.experiments import record_experiment
	return _load_consumed(args, args.spec, lambda spec: record_experiment(args.project, spec))
# @used-by :meth:`test_review_contract_package_and_paths_m6.ReviewContractPackageAndPathsM6Tests.test_record_review_resolves_project_relative_report_from_foreign_cwd()`
# @used-by :mod:`Df.Harness.lib.cli_domain_ops`
def _op_record_review(args: Any) -> Any:
	from agent_tools import workflow as flow
	report_path = _resolve_project_input(args.project, args.report)
	payload = dfh_load_operation_input(args, report_path)
	return dfh_consume_scratch_input(args, report_path, payload, flow.record_review(args.project, payload, parent_id=args.parent, reviewer_id=args.reviewer, native_evidence=args.native_evidence))
# @used-by :mod:`Df.Harness.lib.cli_domain_ops`
def _op_render_analysis(args: Any) -> Any:
	from agent_tools.analysis import publish_analysis
	r = publish_analysis(args.input, args.output)
	if getattr(args, 'promote_domain', False) and 'conflict' != r.get('status'):
		from agent_tools.project_rename import apply_domain_promotion
		r = apply_domain_promotion(dfh_analysis_root(args.input), json.loads(Path(args.input).read_text(encoding='utf-8-sig')), r)
	return r
# @used-by :mod:`Df.Harness.lib.cli_domain_ops`
def _op_resume(args: Any) -> Any:
	from agent_tools import workflow as flow
	return flow.resume(args.project, args.reason, dfh_read_input_text(args.request_file, encoding='utf-8') if args.request_file else None)
# @used-by :mod:`Df.Harness.lib.cli_domain_ops`
def _op_review_disposition(args: Any) -> Any:
	from agent_tools import workflow as flow
	return flow.record_review_disposition(args.project, args.review_id, args.finding_id, args.status, args.basis, args.evidence, args.parent)
# @used-by :mod:`Df.Harness.lib.cli_domain_ops`
def _op_review_input(args: Any) -> Any:
	from agent_tools import workflow as flow
	return flow.review_input(args.project, args.package)
# @used-by :mod:`Df.Harness.lib.cli_domain_ops`
def _op_save_analysis(args: Any) -> Any:
	from agent_tools.research import inside
	cand = args.candidate if '-' == str(args.candidate) else inside(args.project, args.candidate)
	if getattr(args, 'merge', False) or getattr(args, 'partial', False):
		from agent_tools.analysis_merge import save_merged_analysis
		r = _load_consumed(args, cand, lambda data: save_merged_analysis(args.project, data, args.expected_sha256, partial=bool(getattr(args, 'partial', False))))
	else:
		from agent_tools.analysis import save_analysis
		r = _load_consumed(args, cand, lambda data: save_analysis(args.project, data, args.expected_sha256))
	if getattr(args, 'promote_domain', False) and (not getattr(args, 'partial', False)):
		from agent_tools.project_rename import apply_domain_promotion
		r = apply_domain_promotion(args.project, json.loads(Path(r['target']).read_text(encoding='utf-8-sig')), r)
	return r
# @used-by :mod:`Df.Harness.lib.cli_domain_ops`
def _op_source_ref(args: Any) -> Any:
	from agent_tools.evidence import source_reference
	return {'source': source_reference(args.project, args.file, args.part)}
# @used-by :mod:`Df.Harness.lib.cli_domain_ops`
def _op_stage(args: Any) -> Any:
	from agent_tools import workflow as flow
	return flow.complete_stage(args.project, args.stage, args.input, args.output, note=args.note)
# @used-by :mod:`Df.Harness.lib.cli_domain_ops`
def _op_status(args: Any) -> Any:
	from agent_tools import workflow as flow
	return flow.status(args.project)
# @used-by :mod:`Df.Harness.lib.cli_domain_ops`
def _op_sync_attachments(args: Any) -> Any:
	from agent_tools.knowledge import sync_project_attachments_and_kb
	if not args.media_descriptions:
		r = sync_project_attachments_and_kb(args.project, None, fetch_videos=not args.no_fetch_videos)
	else:
		r = _load_consumed(args, args.media_descriptions, lambda desc: sync_project_attachments_and_kb(args.project, desc, fetch_videos=not args.no_fetch_videos))
	return r
# @used-by :mod:`Df.Harness.lib.cli_domain_ops`
def _op_unadopt_requests(args: Any) -> Any:
	from agent_tools import workflow as flow
	return flow.unadopt_requests(args.project, args.conversation, request_ids=args.request_id)
# @used-by :func:`_op_record_review()`
# @used-by :meth:`test_df_harness_s11_wave2d_cli_cov.DfHarnessS11Wave2dCliCovTests.test_cli_domain_ops_all_handlers_and_collect_merge()`
def _resolve_project_input(project: Any, raw_path: Any) -> Any:
	r = raw_path
	if isinstance(raw_path, str) and '-' != raw_path and (not Path(raw_path).is_absolute()):
		from agent_tools.research import inside
		proj_cand = inside(project, raw_path)
		if proj_cand.is_file() or (not Path(raw_path).is_file()):
			r = str(proj_cand)
	return r
# @used-by :func:`_op_render_analysis()`
# @used-by :meth:`Df.Harness.Upwork.CliRunner.CliRunner.run()`
# @used-by :meth:`test_df_harness_s11_wave2d_cli_cov.DfHarnessS11Wave2dCliCovTests.test_cli_domain_ops_all_handlers_and_collect_merge()`
def dfh_analysis_root(file: str | Path) -> Path:
	file_p = Path(file).resolve()
	r = file_p.parent
	for parent in file_p.parents:
		if '\ua616' == parent.name:
			r = dfh_canonicalize_root_dir(parent.parent, dfh_load_registry())
			break
	return r
# @used-by :func:`_op_collect()`
def dfh_execute_collect(args: Any) -> Any:
	from agent_tools.research import collect_plan, compute_site_summary, inside, json_data
	payload = dfh_load_operation_input(args, args.plan)
	plan = json.loads(payload.decode('utf-8-sig'))
	result = collect_plan(args.project, plan, browser=getattr(args, 'browser', 'auto'), cdp_port=getattr(args, 'cdp_port', None), session_id=getattr(args, 'session_id', None))
	if not args.output:
		r = result
	else:
		from agent_tools.analysis import digest, publish_owned
		pp = dfh_project_paths(args.project, exact_root=True)
		target = inside(pp.root, args.output)
		if not target.is_relative_to(pp.evidence_dir.resolve()) or '/HTTP/' in target.as_posix() or '/Reviews/' in target.as_posix():
			raise ValueError('Collection report must be a project Evidence file outside immutable HTTP/Reviews observations')
		result = _merge_prior_collection(args.project, target, pp.rendered_json, result, digest, compute_site_summary)
		result['publication'] = publish_owned(target, json_data(result), source={'kind': 'collection-plan', 'sha256': digest(payload), 'plan': plan})
		r = result if 'conflict' == result['publication']['status'] else dfh_consume_scratch_input(args, args.plan, payload, result)
	return r
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