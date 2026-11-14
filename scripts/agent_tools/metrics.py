# 2026-11-14 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Consolidate token/stage summarize, native_review_proof, read-only SQLite, file:// helpers, and ProjectCleanupScanner across trace_common.py, antigravity.py, codex.py, metrics.py, and cleanup.py":
# https://github.com/dmitry-ai/harness/issues/75
# 2026-11-13 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Consolidate review package reading, verdict recording, quorum checks, and content-addressed immutable receipts across review.py, text_review.py, text_workflow.py, text_sources.py, and storage.py":
# https://github.com/dmitry-ai/harness/issues/63
# 2026-10-15 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Eliminate redundant subagent searches with HTTP evidence caching, structured Analysis.json workflow, and in-chat resume":
# https://github.com/dmitry-ai/harness/issues/4
# 2026-10-31 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Reorganize AI into universal harness repository, translate rules and documentation to English, format per P.md, and enforce issue-driven Git workflow":
# https://github.com/dmitry-ai/harness/issues/26
from collections import Counter
from pathlib import Path
import json
import re
from .platforms.trace_common import parse_tool_args, summarize_token_records
def summarize(paths, bindings=None):
	formats = []
	for path in paths:
		with Path(path).open(encoding='utf-8') as stream:
			first = next((json.loads(line) for line in stream if line.strip()), {})
		formats.append('session_meta' == first.get('type'))
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
		r = summarize_token_records(events, bindings, tools=tools, extra={'observed_error_results': error_results, 'repeated_read_url_calls': sum((n - 1 for n in urls.values())), 'repeated_exact_search_queries': sum((n - 1 for n in queries.values())), 'interpretation': 'Observed native log counters; not quota percentage, currency or proof of content quality'})
	return r
def project_metrics(root):
	from .workflow import load, stage_statuses
	root = Path(root).resolve()
	state = load(root)
	path = root / 'ꘖ/data/research-metrics.json'
	uses = json.loads(path.read_text(encoding='utf-8')) if path.exists() else None
	from .research import bounded_metrics
	collector = None if None is uses else {**bounded_metrics(uses)['totals'], 'scope': 'Only recorded collector operations since instrumentation; earlier requests unknown'}
	questions = [{'id': q['id'], 'status': q['status'], 'searches': len(q.get('searches', [])), 'unsuccessful_searches': sum((not s['useful'] for s in q.get('searches', []))), 'method_changes': sum((bool(s.get('method_change')) for s in q.get('searches', []))), 'gap': q.get('gap')} for q in state['questions'].values()]
	reviews = []
	for review in state['reviews']:
		report = json.loads((root / review['report']).read_text(encoding='utf-8'))
		reviews.append({'reviewer_id': review['reviewer_id'], 'independent': review.get('independent', True), 'risk': review['risk'], 'result': report.get('result'), 'findings': dict(Counter((f.get('status', 'unknown') for f in report.get('findings', []))))})
	executors, executor_issues = ([], [])
	registry = root / 'ꘖ/data/executors.json'
	if registry.exists():
		import hashlib
		from .research import inside
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
def native_requests(root, conversation_id, *, backend=None, platform=None):
	from .platforms import adapter
	return adapter(platform).native_requests(root, conversation_id, backend=backend)
# 2026-10-18 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Enforce pre-registered experiment plans, claim-to-test alignment, native reviewer provenance, and executor metadata verification":
# https://github.com/dmitry-ai/harness/issues/10
def native_review_proof(root, parent_id, reviewer_id, *, backend=None, write=True, platform=None):
	from .platforms import adapter
	return adapter(platform).native_review_proof(root, parent_id, reviewer_id, backend=backend, write=write)
# 2026-10-18 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Enforce pre-registered experiment plans, claim-to-test alignment, native reviewer provenance, and executor metadata verification":
# https://github.com/dmitry-ai/harness/issues/10
def verify_native_proof(root, native, package=None):
	from .platforms import adapter
	if not isinstance(native, dict) or not native.get('surface'):
		raise ValueError('Native review proof must declare its actual surface')
	return adapter(surface=native.get('surface')).verify_native_proof(root, native, package=package)
def native_executor_metadata(root, conversation_id, *, role='primary', parent_id=None, platform=None, backend=None, write=False):
	from .platforms import adapter
	if role not in ('primary', 'AA', 'AF'):
		raise ValueError('Executor role must be primary, AA or AF')
	result = adapter(platform).native_executor_metadata(root, conversation_id, role=role, parent_id=parent_id, backend=backend)
	return _save_executor_metadata(root, result) if write else result
def _save_executor_metadata(root, result):
	import hashlib
	from .research import json_data
	from .storage import locked, replace_bytes, write_immutable_bytes
	root = Path(root).resolve()
	payload = json_data(result)
	sha = hashlib.sha256(payload).hexdigest()
	target = write_immutable_bytes(root / 'ꘖ/KB/Evidence/Executors' / f"{result['conversation_id']}-{sha}.json", payload, diff_error='Immutable executor metadata changed')
	receipt = {'proof': target.relative_to(root).as_posix(), 'sha256': sha, 'conversation_id': result['conversation_id'], 'role': result['role'], 'surface': result['surface'], 'verification': result['verification']}
	index_file = root / 'ꘖ/data/executors.json'
	with locked(index_file.with_suffix('.lock')):
		index = json.loads(index_file.read_text(encoding='utf-8')) if index_file.exists() else {'schema_version': 1, 'snapshots': []}
		if 1 != index.get('schema_version') or not isinstance(index.get('snapshots'), list):
			raise ValueError('Unknown executor registry format; preserve and inspect')
		if not any((item.get('sha256') == sha for item in index['snapshots'])):
			index['snapshots'].append(receipt)
			replace_bytes(index_file, json_data(index))
	return {**result, **receipt}
def record_executor_metadata(root, conversation_id, *, role='primary', parent_id=None, platform=None, backend=None):
	return native_executor_metadata(root, conversation_id, role=role, parent_id=parent_id, platform=platform, backend=backend, write=True)
def native_tool_trace(root, request):
	from .platforms import adapter
	if not isinstance(request, dict) or not request.get('surface') or 'events' in request:
		raise ValueError('Native trace needs a surface/session/selection; supplied events are not evidence')
	if set(request) - {'surface', 'conversation_id', 'call_ids', 'step_indices', 'native_profile_home'}:
		raise ValueError('Native trace accepts only exact native source selectors')
	return adapter(surface=request['surface']).native_tool_trace(root, request)
def wire_fields(data):
	from .platforms.antigravity import wire_fields as decode
	return decode(data)
