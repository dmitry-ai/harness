# 2026-10-15 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from collections import Counter
from pathlib import Path
import json
import os
import re
from .platforms.trace_common import parse_tool_args, summarize_token_records
# 2026-10-15
# "Eliminate redundant subagent searches with HTTP evidence caching, structured Analysis.json workflow, and in-chat resume":
# https://github.com/dmitry-ai/harness/issues/4
# @used-by :func:`agent_tools.cli_domains._op_metrics()`
# @used-by :func:`summarize_instance()`
# @used-by :meth:`test_analysis_workflow.MetricsTests.test_unknown_tokens_stay_unknown_and_duplicate_exports_are_not_summed()`
# @used-by :meth:`test_portability.CodexEvidenceTests.test_codex_token_metrics_use_response_usage_and_do_not_count_summaries()`
def summarize(paths, bindings=None):
	formats = []
	for path in paths:
		with Path(path).open(encoding='utf-8') as stream:
			first = next((json.loads(line) for line in stream if line.strip()), {})
		formats.append('session_meta' == first.get('type'))
	# 2026-10-15
	# "Unify Antigravity and OpenAI Codex adapters with build-native projections, parent-driven model selection, and cross-system continuation":
	# https://github.com/dmitry-ai/harness/issues/6
	if any(formats):
		if not all(formats):
			raise ValueError('Summarize native Codex and Antigravity traces separately; their accounting formats differ')
		from .platforms.codex import summarize as summarize_codex
		r = summarize_codex(paths, bindings)
	else:
		events, seen, error_results = ([], set(), 0)
		tools, urls, queries = (Counter(), Counter(), Counter())
		for raw_path in paths:
			path = Path(raw_path)
			cid = path.parent.parent.parent.name if 'logs' == path.parent.name and '.system_generated' == path.parent.parent.name else (path.parents[2].parent.name if path.name.startswith('transcript') else path.stem)
			for line in path.read_text(encoding='utf-8').splitlines():
				if not line.strip():
					continue
				record = json.loads(line)
				key = (cid, record.get('step_index'))
				if key in seen:
					events.append(('duplicate',))
					continue
				seen.add(key)
				if 'GENERIC' == record.get('type') and re.search('Encountered error in step execution|failed to read file|cannot find the file', record.get('content', ''), re.I):
					error_results += 1
				for call in record.get('tool_calls', []):
					tools[call['name']] += 1
					args = parse_tool_args(call.get('args', {}))
					if 'read_url_content' == call['name']:
						target = args.get('Url') or args.get('URL') or args.get('url')
						if isinstance(target, str):
							urls[target] += 1
					elif 'search_web' == call['name']:
						query = args.get('query') or args.get('Query') or args.get('SearchQuery')
						if isinstance(query, str):
							queries[' '.join(query.casefold().split())] += 1
				if 'PLANNER_RESPONSE' == record.get('type'):
					events.append(('generation', cid, record['step_index'], record))
		# 2026-11-14
		# "Consolidate token/stage summarize, native_review_proof, read-only SQLite, file:// helpers, and ProjectCleanupScanner across trace_common.py, antigravity.py, codex.py, metrics.py, and cleanup.py":
		# https://github.com/dmitry-ai/harness/issues/75
		r = summarize_token_records(events, bindings, tools=tools, extra={'observed_error_results': error_results, 'repeated_read_url_calls': sum((n - 1 for n in urls.values())), 'repeated_exact_search_queries': sum((n - 1 for n in queries.values())), 'interpretation': 'Observed native log counters; not quota percentage, currency or proof of content quality'})
	return r
# 2026-10-15
# "Eliminate redundant subagent searches with HTTP evidence caching, structured Analysis.json workflow, and in-chat resume":
# https://github.com/dmitry-ai/harness/issues/4
# 2026-10-31
# "Reorganize AI into universal harness repository, translate rules and documentation to English, format per P.md, and enforce issue-driven Git workflow":
# https://github.com/dmitry-ai/harness/issues/26
# @used-by :func:`agent_tools.cli_domains._op_metrics()`
# @used-by :meth:`test_path_registry.PathRegistryTests.test_cross_root_relocation_workflow_completion_review_and_antigravity_registration()`
# @used-by :meth:`test_resume_exports.ResumeExportTests.test_failed_extraction_keeps_saved_observation_and_reuses_it()`
def project_metrics(root):
	from .path_registry import project_paths
	from .workflow import load, stage_statuses
	# 2026-11-19
	# "Wire project path overlays across Harness subsystems with paths CLI and regression tests":
	# https://github.com/dmitry-ai/harness/issues/96
	pp = project_paths(root, exact_root=True)
	root = pp.root
	state = load(root)
	path = pp.metrics_json
	uses = json.loads(path.read_text(encoding='utf-8')) if path.exists() else None
	from .research import bounded_metrics, inside
	# 2026-10-17
	# "Enforce complete client attachment ingestion, verbatim media transcription, and intake-drain staging":
	# https://github.com/dmitry-ai/harness/issues/7
	collector = None if None is uses else {**bounded_metrics(uses)['totals'], 'scope': 'Only recorded collector operations since instrumentation; earlier requests unknown'}
	questions = [{'id': q['id'], 'status': q['status'], 'searches': len(q.get('searches', [])), 'unsuccessful_searches': sum((not s['useful'] for s in q.get('searches', []))), 'method_changes': sum((bool(s.get('method_change')) for s in q.get('searches', []))), 'gap': q.get('gap')} for q in state['questions'].values()]
	reviews = []
	for review in state['reviews']:
		# 2026-11-22
		# "Support V2 `𝐒`/`𝐖` software subtrees and cross-root project relocations in Harness":
		# https://github.com/dmitry-ai/harness/issues/113
		report = json.loads(inside(root, review['report']).read_text(encoding='utf-8'))
		reviews.append({'reviewer_id': review['reviewer_id'], 'independent': review.get('independent', True), 'risk': review['risk'], 'result': report.get('result'), 'findings': dict(Counter((f.get('status', 'unknown') for f in report.get('findings', []))))})
	# 2026-10-18
	# "Enforce pre-registered experiment plans, claim-to-test alignment, native reviewer provenance, and executor metadata verification":
	# https://github.com/dmitry-ai/harness/issues/10
	executors, executor_issues = ([], [])
	registry = pp.executors_json
	if registry.exists():
		import hashlib
		try:
			index = json.loads(registry.read_text(encoding='utf-8'))
			for receipt in index.get('snapshots', []):
				proof = inside(root, receipt['proof'])
				if hashlib.sha256(proof.read_bytes()).hexdigest() != receipt['sha256']:
					raise ValueError('Executor metadata proof changed')
				native = json.loads(proof.read_text(encoding='utf-8'))
				executors.append({key: native.get(key) for key in ('conversation_id', 'parent_id', 'role', 'surface', 'requested', 'observed', 'verification')})
		except (OSError, ValueError, KeyError, TypeError):
			executor_issues.append('Executor registry/snapshot is missing, invalid or changed; preserve and inspect')
	return {'collector': collector, 'questions': questions, 'reviews': reviews, 'executors': executors, 'executor_issues': executor_issues, 'stages': stage_statuses(root, state), 'semantic_quality_verified': False, 'unrecorded_activity': 'unknown'}
# 2026-11-18
# "Externalize agent environments and per-instance system paths into runtime.json":
# https://github.com/dmitry-ai/harness/issues/86
# @used-by :func:`agent_tools.cli_domains._op_metrics()`
# @used-by :meth:`test_instances_config.RuntimeInstancesTests.test_cross_instance_handoff_and_audit_resolve_antigravity_and_disabled_codex_traces()`
def summarize_instance(conversation_id, *, instance=None, platform=None, bindings=None):
	from .runtime import find_conversation_instance, instance_entry, platform_name as resolve_platform
	if instance:
		entry = instance_entry(instance, platform=platform, include_disabled=True)
		matches = find_conversation_instance(conversation_id, platform=entry['platform'], include_disabled=True)
		found = next((m for m in matches if m['id'] == entry['id']), None)
		if not found:
			raise ValueError(f"Conversation {conversation_id} was not found in instance {entry['id']}")
	else:
		matches = find_conversation_instance(conversation_id, platform=platform, include_disabled=True)
		if not matches:
			raise ValueError(f'Conversation {conversation_id} was not found in any runtime.json instance')
		if 1 < len(matches):
			ids = ', '.join((f"{m['platform']}:{m['id']}" for m in matches))
			raise ValueError(f'Conversation {conversation_id} found in multiple instances ({ids}); pass --instance')
		found = matches[0]
	trace_file = found.get('trace_file')
	if not trace_file or (not Path(trace_file).is_file()):
		raise ValueError(f"Native trace file unavailable for {found['id']} / {conversation_id}: {found['system_paths']}")
	r = summarize([Path(trace_file)], bindings)
	r['instance'] = {'id': found['id'], 'platform': found['platform'], 'enabled': found['enabled'], 'backend_dir': found['backend_dir'], 'trace_file': trace_file, 'system_paths': found['system_paths']}
	return r
# 2026-11-18
# "Externalize agent environments and per-instance system paths into runtime.json":
# https://github.com/dmitry-ai/harness/issues/86
# @used-by :func:`_resolve_platform_and_backend()`
# @used-by :func:`native_executor_metadata()`
# @used-by :func:`native_requests()`
# @used-by :func:`native_review_proof()`
def _resolve_target(platform, backend, instance, conversation_id=None):
	from .runtime import _platform, find_conversation_instance, instance_entry
	resolved_instance = instance
	if instance and (None is platform or None is backend):
		entry = instance_entry(instance, platform=platform, include_disabled=True)
		platform = platform or entry['platform']
		if None is backend:
			sp = entry['system_paths']
			backend = sp.get('backend_dir') or sp.get('home')
	elif None is platform and None is backend and None is instance and conversation_id and not _platform.get() and not os.environ.get('UPWORK_PLATFORM'):
		matches = find_conversation_instance(conversation_id, include_disabled=True)
		if 1 == len(matches):
			platform = matches[0]['platform']
			backend = matches[0]['backend_dir']
			resolved_instance = matches[0]['id']
		elif 1 < len(matches):
			ids = ', '.join((f"{m['platform']}:{m['id']}" for m in matches))
			raise ValueError(f'Conversation UUID {conversation_id} exists in multiple instances ({ids}); pass --instance')
	return (platform, backend, resolved_instance)
# @used-by unused
def _resolve_platform_and_backend(platform, backend, instance, conversation_id=None):
	return _resolve_target(platform, backend, instance, conversation_id=conversation_id)[:2]
# 2026-10-15
# "Unify Antigravity and OpenAI Codex adapters with build-native projections, parent-driven model selection, and cross-system continuation":
# https://github.com/dmitry-ai/harness/issues/6
# @used-by :meth:`agent_tools.workflow.WorkflowStateEngine.adopt_requests()`
# @used-by :meth:`test_instances_config.RuntimeInstancesTests.test_antigravity_verify_native_proof_tool_trace_and_custom_system_paths()`
# @used-by :meth:`test_instances_config.RuntimeInstancesTests.test_instance_flag_and_codex_auto_lookup_for_handoff_and_audit()`
# @used-by :meth:`test_resume_exports.ResumeExportTests.test_native_requests_preserve_exact_bytes_and_current_job_scope()`
# @used-by :meth:`test_resume_exports.ResumeExportTests.test_unknown_native_format_does_not_reconstruct_request()`
def native_requests(root, conversation_id, *, backend=None, platform=None, instance=None):
	from .platforms import adapter
	# 2026-11-18
	# "Externalize agent environments and per-instance system paths into runtime.json":
	# https://github.com/dmitry-ai/harness/issues/86
	platform, backend, resolved_instance = _resolve_target(platform, backend, instance, conversation_id=conversation_id)
	kw = {'backend': backend}
	if None is not resolved_instance:
		kw['instance'] = resolved_instance
	return adapter(platform).native_requests(root, conversation_id, **kw)
# 2026-10-18
# "Enforce pre-registered experiment plans, claim-to-test alignment, native reviewer provenance, and executor metadata verification":
# https://github.com/dmitry-ai/harness/issues/10
# @used-by :func:`agent_tools.cli_domains._op_native_review_proof()`
# @used-by :func:`test_finalized_project_contract._complete_review_and_finalize()`
# @used-by :meth:`Df.Harness.Arch.ReviewStore.ReviewStore.authenticate_report()`
# @used-by :meth:`test_analysis_workflow.NativeReviewTests.test_af_or_terminal_quota_error_is_not_an_independent_completed_aa_review()`
# @used-by :meth:`test_analysis_workflow.NativeReviewTests.test_full_workflow_requires_native_review_and_current_kb_then_exports_complete_context()`
# @used-by :meth:`test_analysis_workflow.NativeReviewTests.test_native_review_rejects_prompt_bias_and_reviewer_isolation_violations()`
# @used-by :meth:`test_analysis_workflow.NativeReviewTests.test_parent_model_selection_allowed_and_observed_mismatch_rejected()`
# @used-by :meth:`test_analysis_workflow.NativeReviewTests.test_significant_risk_cannot_finish_with_one_independent_aa()`
# @used-by :meth:`test_arch_review_cli.ArchReviewCliTests.test_codex_native_review_proof_and_verify_support_arch_role()`
# @used-by :meth:`test_chat_reply_link_issues_m5.ChatReplyLinkIssuesM5Tests.test_finalize_stage_accepts_unencoded_file_uri_chat_links()`
# @used-by :meth:`test_portability.CodexEvidenceTests.test_codex_workflow_reviews_current_kb_and_exports_exact_native_request_and_reply()`
# @used-by :meth:`test_portability.CodexEvidenceTests.test_native_windows_extended_path_keeps_the_profile_boundary()`
# @used-by :meth:`test_portability.CodexEvidenceTests.test_parent_can_select_another_model_and_effort_with_native_proof()`
# @used-by :meth:`test_portability.CodexEvidenceTests.test_review_provenance_checks_parent_completion_model_and_assignment()`
def native_review_proof(root, parent_id, reviewer_id, *, backend=None, write=True, platform=None, instance=None, wait_timeout=0.0, role='AA'):
	from .platforms import adapter
	platform, backend, resolved_instance = _resolve_target(platform, backend, instance, conversation_id=reviewer_id or parent_id)
	kw = {'backend': backend, 'write': write}
	if None is not resolved_instance:
		kw['instance'] = resolved_instance
	# 2026-11-24
	# "Clarify verbatim target_claim contract and add native-review-proof wait timeout":
	# https://github.com/dmitry-ai/harness/issues/212
	if 0.0 < float(wait_timeout or 0.0):
		kw['wait_timeout'] = float(wait_timeout)
	# 2026-11-26
	# "Add arch-auditor subagent role and content-addressed review CLI":
	# https://github.com/dmitry-ai/harness/issues/361
	if 'AA' != role:
		kw['role'] = role
	return adapter(platform).native_review_proof(root, parent_id, reviewer_id, **kw)
# 2026-10-18
# "Enforce pre-registered experiment plans, claim-to-test alignment, native reviewer provenance, and executor metadata verification":
# https://github.com/dmitry-ai/harness/issues/10
# @used-by :func:`agent_tools.review.authenticate_report()`
# @used-by :func:`agent_tools.review.verify_entry_native_proof()`
# @used-by :meth:`Df.Harness.Arch.ReviewStore.ReviewStore.authenticate_report()`
# @used-by :meth:`test_portability.CodexEvidenceTests.test_parent_can_select_another_model_and_effort_with_native_proof()`
# @used-by :meth:`test_portability.CodexEvidenceTests.test_review_provenance_checks_parent_completion_model_and_assignment()`
def verify_native_proof(root, native, package=None):
	from .platforms import adapter
	if not isinstance(native, dict) or not native.get('surface'):
		raise ValueError('Native review proof must declare its actual surface')
	return adapter(surface=native.get('surface')).verify_native_proof(root, native, package=package)
# 2026-10-18
# "Enforce pre-registered experiment plans, claim-to-test alignment, native reviewer provenance, and executor metadata verification":
# https://github.com/dmitry-ai/harness/issues/10
# @used-by :func:`agent_tools.cli_domains._op_native_executor_metadata()`
# @used-by :func:`record_executor_metadata()`
# @used-by :meth:`test_arch_review_cli.ArchReviewCliTests.test_cli_prepare_input_record_needs_changes_and_check_text_roundtrip()`
# @used-by :meth:`test_instances_config.RuntimeInstancesTests.test_antigravity_verify_native_proof_tool_trace_and_custom_system_paths()`
# @used-by :meth:`test_instances_config.RuntimeInstancesTests.test_instance_flag_and_codex_auto_lookup_for_handoff_and_audit()`
def native_executor_metadata(root, conversation_id, *, role='primary', parent_id=None, platform=None, backend=None, instance=None, write=False):
	from .platforms import adapter
	if role not in ('primary', 'AA', 'AF', 'ARCH'):
		raise ValueError('Executor role must be primary, AA, AF or ARCH')
	platform, backend, resolved_instance = _resolve_target(platform, backend, instance, conversation_id=conversation_id)
	kw = {'role': role, 'parent_id': parent_id, 'backend': backend}
	if None is not resolved_instance:
		kw['instance'] = resolved_instance
	result = adapter(platform).native_executor_metadata(root, conversation_id, **kw)
	return _save_executor_metadata(root, result) if write else result
# 2026-10-18
# "Enforce pre-registered experiment plans, claim-to-test alignment, native reviewer provenance, and executor metadata verification":
# https://github.com/dmitry-ai/harness/issues/10
# @used-by :func:`native_executor_metadata()`
def _save_executor_metadata(root, result):
	import hashlib
	from .path_registry import project_paths
	from .research import json_data
	from .storage import locked, replace_bytes, write_immutable_bytes
	# 2026-11-19
	# "Wire project path overlays across Harness subsystems with paths CLI and regression tests":
	# https://github.com/dmitry-ai/harness/issues/96
	pp = project_paths(root, exact_root=True)
	root = pp.root
	payload = json_data(result)
	sha = hashlib.sha256(payload).hexdigest()
	# 2026-11-13
	# "Consolidate review package reading, verdict recording, quorum checks, and content-addressed immutable receipts across review.py, text_review.py, text_workflow.py, text_sources.py, and storage.py":
	# https://github.com/dmitry-ai/harness/issues/63
	target = write_immutable_bytes(pp.evidence_dir / 'Executors' / f"{result['conversation_id']}-{sha}.json", payload, diff_error='Immutable executor metadata changed')
	receipt = {'proof': target.relative_to(root).as_posix() if target.is_relative_to(root) else target.as_posix(), 'sha256': sha, 'conversation_id': result['conversation_id'], 'role': result['role'], 'surface': result['surface'], 'verification': result['verification']}
	index_file = pp.executors_json
	with locked(index_file.with_suffix('.lock')):
		index = json.loads(index_file.read_text(encoding='utf-8')) if index_file.exists() else {'schema_version': 1, 'snapshots': []}
		if 1 != index.get('schema_version') or not isinstance(index.get('snapshots'), list):
			raise ValueError('Unknown executor registry format; preserve and inspect')
		if not any((item.get('sha256') == sha for item in index['snapshots'])):
			index['snapshots'].append(receipt)
			replace_bytes(index_file, json_data(index))
	return {**result, **receipt}
# @used-by :func:`agent_tools.cli_domains._op_native_executor_metadata()`
# @used-by :meth:`test_executor_metadata.ExecutorMetadataTests.test_immutable_executor_snapshots_cover_all_roles_and_can_be_reused()`
def record_executor_metadata(root, conversation_id, *, role='primary', parent_id=None, platform=None, backend=None, instance=None):
	return native_executor_metadata(root, conversation_id, role=role, parent_id=parent_id, platform=platform, backend=backend, instance=instance, write=True)
# 2026-10-18
# "Enforce pre-registered experiment plans, claim-to-test alignment, native reviewer provenance, and executor metadata verification":
# https://github.com/dmitry-ai/harness/issues/10
# @used-by :meth:`agent_tools.experiments.ExperimentRunValidator._ingest_artifacts_and_trace()`
# @used-by :meth:`agent_tools.experiments.ExperimentRunValidator._verify_saved_artifacts()`
# @used-by :meth:`test_experiments.ExperimentTests.test_actual_namespaced_cua_read_is_recognized_but_text_header_does_not_prove_identity()`
# @used-by :meth:`test_experiments.ExperimentTests.test_supplied_native_events_are_rejected()`
def native_tool_trace(root, request):
	from .platforms import adapter
	if not isinstance(request, dict) or not request.get('surface') or 'events' in request:
		raise ValueError('Native trace needs a surface/session/selection; supplied events are not evidence')
	# 2026-11-18
	# "Externalize agent environments and per-instance system paths into runtime.json":
	# https://github.com/dmitry-ai/harness/issues/86
	if set(request) - {'surface', 'conversation_id', 'call_ids', 'step_indices', 'native_profile_home', 'instance'}:
		raise ValueError('Native trace accepts only exact native source selectors')
	return adapter(surface=request['surface']).native_tool_trace(root, request)
# @used-by unused
def wire_fields(data):
	from .platforms.antigravity import wire_fields as decode
	return decode(data)
