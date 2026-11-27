# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from collections import Counter
from pathlib import Path
from agent_tools.platforms.trace_common import parse_tool_args, summarize_token_records
import hashlib
import json
import os
import re
# 2026-11-26 "Move verification gate subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/381
class MetricsSummarizer:
	__ERROR_RES_RE = re.compile(r'Encountered error in step execution|failed to read file|cannot find the file', re.I)
	# @used-by :func:`agent_tools.metrics.summarize()`
	# @used-by :meth:`MetricsSummarizer.summarize_instance()`
	# @used-by :meth:`test_df_harness_s11_wave2b_meta.DfHarnessS11Wave2bMetaTests.test_meta_classes_render_headers_identity_transcripts_and_metrics()`
	def __init__(self, paths, bindings=None) -> None:
		self.__paths = list(paths)
		self.__bindings = bindings
	# @used-by :func:`agent_tools.metrics.summarize()`
	# @used-by :meth:`MetricsSummarizer.summarize_instance()`
	# @used-by :meth:`test_df_harness_s11_wave2b_meta.DfHarnessS11Wave2bMetaTests.test_meta_classes_render_headers_identity_transcripts_and_metrics()`
	def summarize(self) -> dict:
		formats = MetricsSummarizer.__detect_codex_formats(self.__paths)
		if any(formats):
			if not all(formats):
				raise ValueError('Summarize native Codex and Antigravity traces separately; their accounting formats differ')
			from agent_tools.platforms.codex import summarize as summarize_codex
			r = summarize_codex(self.__paths, self.__bindings)
		else:
			r = MetricsSummarizer.__summarize_ag_paths(self.__paths, self.__bindings)
		return r
	# @used-by :meth:`MetricsSummarizer.__save_executor_metadata()`
	@staticmethod
	def __append_executor_receipt(index_file: Path, receipt: dict, sha: str) -> None:
		from agent_tools.research import json_data
		from agent_tools.storage import locked, replace_bytes
		with locked(index_file.with_suffix('.lock')):
			index = json.loads(index_file.read_text(encoding='utf-8')) if index_file.exists() else {'schema_version': 1, 'snapshots': []}
			if 1 != index.get('schema_version') or not isinstance(index.get('snapshots'), list):
				raise ValueError('Unknown executor registry format; preserve and inspect')
			if not any((item.get('sha256') == sha for item in index['snapshots'])):
				index['snapshots'].append(receipt)
				replace_bytes(index_file, json_data(index))
	# @used-by :meth:`MetricsSummarizer.project_metrics()`
	@staticmethod
	def __collect_project_executors(root: Path, registry: Path) -> tuple[list[dict], list[str]]:
		from agent_tools.research import inside
		executors, issues = ([], [])
		if registry.exists():
			try:
				index = json.loads(registry.read_text(encoding='utf-8'))
				for receipt in index.get('snapshots', []):
					proof = inside(root, receipt['proof'])
					if hashlib.sha256(proof.read_bytes()).hexdigest() != receipt['sha256']:
						raise ValueError('Executor metadata proof changed')
					native = json.loads(proof.read_text(encoding='utf-8'))
					executors.append({key: native.get(key) for key in ('conversation_id', 'parent_id', 'role', 'surface', 'requested', 'observed', 'verification')})
			except (OSError, ValueError, KeyError, TypeError):
				issues.append('Executor registry/snapshot is missing, invalid or changed; preserve and inspect')
		return (executors, issues)
	# @used-by :meth:`MetricsSummarizer.project_metrics()`
	@staticmethod
	def __collect_project_reviews(root: Path, state: dict) -> list[dict]:
		from agent_tools.research import inside
		reviews = []
		for review in state['reviews']:
			report = json.loads(inside(root, review['report']).read_text(encoding='utf-8'))
			reviews.append({'reviewer_id': review['reviewer_id'], 'independent': review.get('independent', True), 'risk': review['risk'], 'result': report.get('result'), 'findings': dict(Counter((f.get('status', 'unknown') for f in report.get('findings', []))))})
		return reviews
	# @used-by :meth:`MetricsSummarizer.summarize()`
	@staticmethod
	def __detect_codex_formats(paths: list) -> list[bool]:
		formats: list[bool] = []
		for path in paths:
			with Path(path).open(encoding='utf-8') as stream:
				first = next((json.loads(line) for line in stream if line.strip()), {})
			formats.append('session_meta' == first.get('type'))
		return formats
	# @used-by :meth:`MetricsSummarizer.__scan_ag_file()`
	@staticmethod
	def __record_ag_tool_calls(record: dict, tools: Counter, urls: Counter, queries: Counter) -> None:
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
	# @used-by :meth:`MetricsSummarizer.summarize_instance()`
	@staticmethod
	def __resolve_instance_match(conversation_id, instance, platform) -> dict:
		from agent_tools.runtime import find_conversation_instance, instance_entry
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
		return found
	# @used-by :meth:`MetricsSummarizer.native_executor_metadata()`
	@staticmethod
	def __save_executor_metadata(root, result: dict) -> dict:
		from agent_tools.path_registry import project_paths
		from agent_tools.research import json_data
		from agent_tools.storage import write_immutable_bytes
		pp = project_paths(root, exact_root=True)
		root = pp.root
		payload = json_data(result)
		sha = hashlib.sha256(payload).hexdigest()
		target = write_immutable_bytes(pp.evidence_dir / 'Executors' / f"{result['conversation_id']}-{sha}.json", payload, diff_error='Immutable executor metadata changed')
		receipt = {'proof': target.relative_to(root).as_posix() if target.is_relative_to(root) else target.as_posix(), 'sha256': sha, 'conversation_id': result['conversation_id'], 'role': result['role'], 'surface': result['surface'], 'verification': result['verification']}
		MetricsSummarizer.__append_executor_receipt(pp.executors_json, receipt, sha)
		return {**result, **receipt}
	# @used-by :meth:`MetricsSummarizer.__summarize_ag_paths()`
	@staticmethod
	def __scan_ag_file(raw_path, seen: set, events: list, tools: Counter, urls: Counter, queries: Counter) -> int:
		path = Path(raw_path)
		cid = path.parent.parent.parent.name if 'logs' == path.parent.name and '.system_generated' == path.parent.parent.name else (path.parents[2].parent.name if path.name.startswith('transcript') else path.stem)
		err_cnt = 0
		for line in path.read_text(encoding='utf-8').splitlines():
			if not line.strip():
				continue
			record = json.loads(line)
			key = (cid, record.get('step_index'))
			if key in seen:
				events.append(('duplicate',))
				continue
			seen.add(key)
			if 'GENERIC' == record.get('type') and MetricsSummarizer.__ERROR_RES_RE.search(record.get('content', '')):
				err_cnt += 1
			MetricsSummarizer.__record_ag_tool_calls(record, tools, urls, queries)
			if 'PLANNER_RESPONSE' == record.get('type'):
				events.append(('generation', cid, record['step_index'], record))
		return err_cnt
	# @used-by :meth:`MetricsSummarizer.summarize()`
	@staticmethod
	def __summarize_ag_paths(paths: list, bindings) -> dict:
		events, seen, error_results = ([], set(), 0)
		tools, urls, queries = (Counter(), Counter(), Counter())
		for raw_path in paths:
			error_results += MetricsSummarizer.__scan_ag_file(raw_path, seen, events, tools, urls, queries)
		extra = {'observed_error_results': error_results, 'repeated_read_url_calls': sum((n - 1 for n in urls.values())), 'repeated_exact_search_queries': sum((n - 1 for n in queries.values())), 'interpretation': 'Observed native log counters; not quota percentage, currency or proof of content quality'}
		return summarize_token_records(events, bindings, tools=tools, extra=extra)
	# @used-by :func:`agent_tools.metrics.native_executor_metadata()`
	# @used-by :meth:`MetricsSummarizer.record_executor_metadata()`
	@staticmethod
	def native_executor_metadata(root, conversation_id, *, role='primary', parent_id=None, platform=None, backend=None, instance=None, write=False):
		from agent_tools.platforms import adapter
		if role not in ('primary', 'AA', 'AF', 'ARCH'):
			raise ValueError('Executor role must be primary, AA, AF or ARCH')
		platform, backend, resolved_instance = MetricsSummarizer.resolve_target(platform, backend, instance, conversation_id=conversation_id)
		kw = {'role': role, 'parent_id': parent_id, 'backend': backend}
		if None is not resolved_instance:
			kw['instance'] = resolved_instance
		result = adapter(platform).native_executor_metadata(root, conversation_id, **kw)
		return MetricsSummarizer.__save_executor_metadata(root, result) if write else result
	# @used-by :func:`agent_tools.metrics.native_requests()`
	@staticmethod
	def native_requests(root, conversation_id, *, backend=None, platform=None, instance=None):
		from agent_tools.platforms import adapter
		platform, backend, resolved_instance = MetricsSummarizer.resolve_target(platform, backend, instance, conversation_id=conversation_id)
		kw = {'backend': backend}
		if None is not resolved_instance:
			kw['instance'] = resolved_instance
		return adapter(platform).native_requests(root, conversation_id, **kw)
	# @used-by :func:`agent_tools.metrics.native_review_proof()`
	@staticmethod
	def native_review_proof(root, parent_id, reviewer_id, *, backend=None, write=True, platform=None, instance=None, wait_timeout=0.0, role='AA'):
		from agent_tools.platforms import adapter
		platform, backend, resolved_instance = MetricsSummarizer.resolve_target(platform, backend, instance, conversation_id=reviewer_id or parent_id)
		kw = {'backend': backend, 'write': write}
		if None is not resolved_instance:
			kw['instance'] = resolved_instance
		if 0.0 < float(wait_timeout or 0.0):
			kw['wait_timeout'] = float(wait_timeout)
		if 'AA' != role:
			kw['role'] = role
		return adapter(platform).native_review_proof(root, parent_id, reviewer_id, **kw)
	# @used-by :func:`agent_tools.metrics.native_tool_trace()`
	@staticmethod
	def native_tool_trace(root, request):
		from agent_tools.platforms import adapter
		if not isinstance(request, dict) or not request.get('surface') or 'events' in request:
			raise ValueError('Native trace needs a surface/session/selection; supplied events are not evidence')
		if set(request) - {'surface', 'conversation_id', 'call_ids', 'step_indices', 'native_profile_home', 'instance'}:
			raise ValueError('Native trace accepts only exact native source selectors')
		return adapter(surface=request['surface']).native_tool_trace(root, request)
	# @used-by :func:`agent_tools.metrics.project_metrics()`
	@staticmethod
	def project_metrics(root) -> dict:
		from agent_tools.path_registry import project_paths
		from agent_tools.research import bounded_metrics
		from agent_tools.workflow import load, stage_statuses
		pp = project_paths(root, exact_root=True)
		root = pp.root
		state = load(root)
		uses = json.loads(pp.metrics_json.read_text(encoding='utf-8')) if pp.metrics_json.exists() else None
		collector = None if None is uses else {**bounded_metrics(uses)['totals'], 'scope': 'Only recorded collector operations since instrumentation; earlier requests unknown'}
		questions = [{'id': q['id'], 'status': q['status'], 'searches': len(q.get('searches', [])), 'unsuccessful_searches': sum((not s['useful'] for s in q.get('searches', []))), 'method_changes': sum((bool(s.get('method_change')) for s in q.get('searches', []))), 'gap': q.get('gap')} for q in state['questions'].values()]
		reviews = MetricsSummarizer.__collect_project_reviews(root, state)
		executors, executor_issues = MetricsSummarizer.__collect_project_executors(root, pp.executors_json)
		return {'collector': collector, 'questions': questions, 'reviews': reviews, 'executors': executors, 'executor_issues': executor_issues, 'stages': stage_statuses(root, state), 'semantic_quality_verified': False, 'unrecorded_activity': 'unknown'}
	# @used-by unused
	@staticmethod
	def record_executor_metadata(root, conversation_id, *, role='primary', parent_id=None, platform=None, backend=None, instance=None):
		return MetricsSummarizer.native_executor_metadata(root, conversation_id, role=role, parent_id=parent_id, platform=platform, backend=backend, instance=instance, write=True)
	# @used-by unused
	@staticmethod
	def resolve_platform_and_backend(platform, backend, instance, conversation_id=None):
		return MetricsSummarizer.resolve_target(platform, backend, instance, conversation_id=conversation_id)[:2]
	# @used-by :func:`agent_tools.metrics._resolve_target()`
	# @used-by :meth:`MetricsSummarizer.native_executor_metadata()`
	# @used-by :meth:`MetricsSummarizer.native_requests()`
	# @used-by :meth:`MetricsSummarizer.native_review_proof()`
	# @used-by :meth:`MetricsSummarizer.resolve_platform_and_backend()`
	@staticmethod
	def resolve_target(platform, backend, instance, conversation_id=None):
		from agent_tools.runtime import _platform, find_conversation_instance, instance_entry
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
				platform, backend, resolved_instance = (matches[0]['platform'], matches[0]['backend_dir'], matches[0]['id'])
			elif 1 < len(matches):
				ids = ', '.join((f"{m['platform']}:{m['id']}" for m in matches))
				raise ValueError(f'Conversation UUID {conversation_id} exists in multiple instances ({ids}); pass --instance')
		return (platform, backend, resolved_instance)
	# @used-by :func:`agent_tools.metrics.summarize_instance()`
	@staticmethod
	def summarize_instance(conversation_id, *, instance=None, platform=None, bindings=None) -> dict:
		found = MetricsSummarizer.__resolve_instance_match(conversation_id, instance, platform)
		trace_file = found.get('trace_file')
		if not trace_file or (not Path(trace_file).is_file()):
			raise ValueError(f"Native trace file unavailable for {found['id']} / {conversation_id}: {found['system_paths']}")
		r = MetricsSummarizer([Path(trace_file)], bindings).summarize()
		r['instance'] = {'id': found['id'], 'platform': found['platform'], 'enabled': found['enabled'], 'backend_dir': found['backend_dir'], 'trace_file': trace_file, 'system_paths': found['system_paths']}
		return r
	# @used-by :func:`agent_tools.metrics.verify_native_proof()`
	@staticmethod
	def verify_native_proof(root, native, package=None):
		from agent_tools.platforms import adapter
		if not isinstance(native, dict) or not native.get('surface'):
			raise ValueError('Native review proof must declare its actual surface')
		return adapter(surface=native.get('surface')).verify_native_proof(root, native, package=package)
	# @used-by :func:`agent_tools.metrics.wire_fields()`
	@staticmethod
	def wire_fields(data):
		from agent_tools.platforms.antigravity import wire_fields as decode
		return decode(data)
