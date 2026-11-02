# 2026-10-20 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Implement /df-article and /df-proposal client-text skills, AI-slop linter, scoped baseline diffs, and semantic § rendering":
# https://github.com/dmitry-ai/harness/issues/13
# 2026-10-31 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Reorganize AI into universal harness repository, translate rules and documentation to English, format per P.md, and enforce issue-driven Git workflow":
# https://github.com/dmitry-ai/harness/issues/26
# 2026-11-03 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Separate publication admission from immutable historical integrity":
# https://github.com/dmitry-ai/harness/issues/41
from pathlib import Path
from copy import deepcopy
import difflib
import json
import re
import uuid
from urllib.parse import unquote
from .research import inside, json_data
from .storage import create_bytes, replace_bytes, locked, data_dir_for
from .text_claims import digest, validate_map, blocks
KINDS = ('article', 'proposal', 'letter')
def _folder(root):
	return Path(root).resolve() / 'ꘖ/data/texts'
def _read(path):
	return json.loads(Path(path).read_text(encoding='utf-8-sig'))
def _immutable(path, payload):
	path.parent.mkdir(parents=True, exist_ok=True)
	if not path.exists():
		create_bytes(path, payload)
	elif path.read_bytes() != payload:
		raise ValueError('Immutable text artifact differs: ' + str(path))
	r = path
	return r
def _index(root):
	file = _folder(root) / 'index.json'
	value = _read(file) if file.exists() else {'schema_version': 1, 'targets': {}, 'operations': []}
	if 1 != value.get('schema_version') or not isinstance(value.get('targets'), dict):
		raise ValueError('Invalid client-text index; preserve it for recovery')
	r = value
	return r
def _save_index(root, value):
	path = _folder(root) / 'index.json'
	replace_bytes(path, json_data(value))
def _target_bytes(path):
	if path.exists() and (not path.is_file()):
		raise ValueError('Text target must be a file')
	r = path.read_bytes() if path.exists() else None
	return r
def _document(root, name):
	root = Path(root).resolve()
	requested = root / name
	for path in (requested, *requested.parents):
		if path.is_relative_to(root) and (path.is_symlink() or (hasattr(path, 'is_junction') and path.is_junction())):
			raise ValueError('Text target indirection changed; protected bytes preserved')
	r = inside(root, name)
	return r
def _hash_or_none(value):
	return digest(value) if None is not value else None
def _find_registered(target):
	target = Path(target).resolve()
	for root in target.parents:
		file = _folder(root) / 'index.json'
		if file.is_file():
			state = _index(root)
			name = target.relative_to(root).as_posix()
			if name in state['targets'] or name in state.get('protected', []):
				return root
	return None
def write_candidate_output(path, payload, *, expected_sha256=None):
	path = Path(path).resolve()
	if None is not _find_registered(path):
		raise ValueError('Registered text target: use text-check/text-apply; formatter output is only a candidate')
	folder = data_dir_for(path)
	with locked(folder / 'text-candidates.lock'):
		previous = _target_bytes(path)
		if _hash_or_none(previous) != expected_sha256:
			raise ValueError('Existing output needs its current --expected-sha256; external version preserved')
		if None is not previous:
			_immutable(folder / 'text-output-history' / (digest(previous) + '.bin'), previous)
		if _target_bytes(path) != previous:
			raise ValueError('Output changed during candidate preparation')
		path.parent.mkdir(parents=True, exist_ok=True)
		if None is previous:
			create_bytes(path, payload)
		else:
			replace_bytes(path, payload)
	r = {'path': str(path), 'sha256': digest(payload), 'kind': 'candidate', 'publication_approved': False}
	return r
# 2026-10-20 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Implement /df-article and /df-proposal client-text skills, AI-slop linter, scoped baseline diffs, and semantic § rendering":
# https://github.com/dmitry-ai/harness/issues/13
def begin(root, spec):
	root = Path(root).resolve(strict=True)
	if not isinstance(spec, dict) or spec.get('kind') not in KINDS:
		raise ValueError('Explicit text kind article/proposal/letter is required')
	if spec.get('mode') not in ('edit', 'propose', 'inspect') or spec.get('changes') not in ('prose', 'links', 'renumber'):
		raise ValueError('Declare result mode and allowed change kind')
	if not isinstance(spec.get('goal'), str) or not spec['goal'].strip():
		raise ValueError('The current task goal is required')
	if not isinstance(spec.get('requests'), list) or not spec['requests'] or any((not isinstance(x, str) or not x.strip() for x in spec['requests'])):
		raise ValueError('Preserve the exact current requests in the operation')
	allowed = spec.get('allow_sections', [])
	if not isinstance(allowed, list) or any((not isinstance(x, str) or not x for x in allowed)):
		raise ValueError('allow_sections is a list of exact section IDs or explicit inclusive ranges')
	requested = root / spec.get('target', '')
	if any((p.is_symlink() or (hasattr(p, 'is_junction') and p.is_junction()) for p in (requested, *requested.parents) if p.exists() and p.is_relative_to(root))):
		raise ValueError('Text target indirections need an explicit resolved ordinary file')
	target = inside(root, spec.get('target', ''))
	if target == root or target.is_relative_to(root / 'ꘖ'):
		raise ValueError('Choose an explicit user document outside agent service storage')
	if any((p.is_symlink() or (hasattr(p, 'is_junction') and p.is_junction()) for p in (target, *target.parents) if p.exists() and p.is_relative_to(root))):
		raise ValueError('Text target indirections need an explicit resolved ordinary file')
	current = _target_bytes(target)
	if None is current and 'inspect' == spec['mode']:
		raise ValueError('Inspect requires an existing document')
	protected = {}
	for name in spec.get('protected', []):
		file = inside(root, name)
		if file == target:
			raise ValueError('A protected document cannot be the writable target')
		protected[file.relative_to(root).as_posix()] = _hash_or_none(_target_bytes(file))
	ident = uuid.uuid4().hex
	operation = {**deepcopy(spec), 'schema_version': 1, 'id': ident, 'root': str(root), 'target': target.relative_to(root).as_posix(), 'base_sha256': _hash_or_none(current), 'base_exists': None is not current, 'protected_versions': protected, 'reconciliation': None}
	previous = target.with_name('draft.prev.md')
	if None is not current and 'draft.md' == target.name and ('edit' == spec['mode']) and (previous.relative_to(root).as_posix() in protected) and (_target_bytes(previous) != current):
		raise ValueError('Draft snapshot would overwrite protected draft.prev.md; all protected bytes preserved')
	with locked(_folder(root) / 'writer.lock'):
		state = _index(root)
		previous = state['targets'].get(operation['target'])
		folder = _folder(root) / 'operations' / ident
		if previous and previous.get('sha256') != operation['base_sha256']:
			if 'reconcile_sha256' not in spec or spec['reconcile_sha256'] != operation['base_sha256']:
				raise ValueError('Registered output changed outside the workflow; read and explicitly reconcile its current SHA256 first')
			baseline = _immutable(folder / 'base.bin', current or b'')
			reconciliation = {'schema_version': 1, 'kind': 'baseline_reconciliation', 'root': str(root), 'target': operation['target'], 'document_kind': spec['kind'], 'operation': ident, 'previous': deepcopy(previous), 'baseline': {'file': baseline.relative_to(root).as_posix(), 'sha256': operation['base_sha256']}}
			raw = json_data(reconciliation)
			file = _immutable(folder / (digest(raw) + '-reconciled.json'), raw)
			operation['reconciliation'] = file.relative_to(root).as_posix()
			state['targets'][operation['target']] = {'sha256': operation['base_sha256'], 'kind': spec['kind'], 'receipt': None, 'reconciliation': operation['reconciliation']}
		_immutable(folder / 'base.bin', current or b'')
		_immutable(folder / 'operation.json', json_data(operation))
		if None is not current and 'draft.md' == target.name and ('edit' == spec['mode']):
			from .snapshot import snapshot_draft
			snapshot_draft(target, 'text-' + ident)
		if _target_bytes(target) != current:
			raise ValueError('Target changed during capture; snapshot retained, external edit preserved')
		state['operations'].append(ident)
		state['protected'] = sorted(set(state.get('protected', [])) | set(protected))
		state['targets'].setdefault(operation['target'], {'sha256': operation['base_sha256'], 'kind': spec['kind'], 'receipt': None})
		_save_index(root, state)
		identity = root / 'ꘖ/data/text-project.json'
		if not (root / 'ꘖ/project.json').exists() and (not identity.exists()):
			from .platforms.request_binding import text_project_id
			_immutable(identity, json_data({'schema_version': 1, 'kind': 'client_text_workspace', 'project_root': str(root), 'id': text_project_id(root)}))
	r = operation
	return r
def operation(root, ident):
	if not isinstance(ident, str) or not re.fullmatch('[a-f0-9]{32}', ident):
		raise ValueError('Use the exact operation ID returned by text-begin')
	result = _read(_folder(root) / 'operations' / ident / 'operation.json')
	if result.get('root') != str(Path(root).resolve()) or result.get('id') != ident:
		raise ValueError('Text operation belongs to another workspace')
	base = (_folder(root) / 'operations' / ident / 'base.bin').read_bytes()
	if (digest(base) if result['base_exists'] else None) != result['base_sha256']:
		raise ValueError('Captured baseline bytes changed')
	r = (result, base)
	return r
def _mechanical_projection(text, kind, mode):
	from .text_core import scan
	from .text_core import normalize_external_refs, external_section_ref
	from .article import parse_sections, ANCHOR_LINK, SECTION_LABEL, part_at
	lines = scan(text)
	if 'article' == kind:
		sections = parse_sections(lines)
		identities = {s.key: str(i) for i, s in enumerate(sections)}
	elif 'proposal' != kind:
		identities = {}
	else:
		from .proposal import parse_blocks
		sections = parse_blocks(lines)
		identities = {str(s.key): str(i) for i, s in enumerate(sections)}
	def prose(value, current):
		protected = '`+[^`]*`+|«[^»]*»|“[^”]*”|(?<!\\w)"[^"\\n]+"'
		if 'renumber' == mode:
			protected += '|!?\\[[^\\]\\n]*\\]\\(<?https?://[^)]+\\)|<https?://[^>]+>|https?://[^\\s<>"\\x27]+'
		parts = re.split('(' + protected + ')', value)
		for i in range(0, len(parts), 2):
			item = parts[i]
			if 'links' == mode:
				from .links import _bare_urls
				def link(match):
					label, url = match.groups()
					visible = unquote(re.sub('[*`]', '', label))
					address = unquote(re.sub('^https?://', '', url.rstrip('>')))
					r = 'URL' if visible.rstrip('/') in (address.rstrip('/'), url.rstrip('>')) else label + '(URL)'
					return r
				item = re.sub('\\[([^\\]]+)\\]\\(<?(https?://[^)]+)\\)', link, item)
				def bare(match):
					url = next(_bare_urls(match.group()))
					r = 'URL' + match.group()[len(url):]
					return r
				item = re.sub('https?://\\S+', bare, item)
			else:
				item = normalize_external_refs(item)
				item = ANCHOR_LINK.sub(lambda m: 'REF:' + identities.get(m[2].lstrip('§'), 'MISSING:' + m[2]), item)
				def ref(match):
					if external_section_ref(item, match):
						r = match.group()
					else:
						target = match.group(1)
						if 'article' == kind and (not re.match('^[IVXLC]+\\.', target)):
							target = current + '.' + target
						r = 'REF:' + identities.get(target, 'MISSING:' + target)
					return r
				item = re.sub('§+([IVXLC]+\\.\\d+(?:\\.\\d+)*|\\d+(?:\\.\\d+)*)', ref, item)
				if 'proposal' == kind:
					item = re.sub('^\\s*\\d+(?:\\.\\d+)*\\.\\s*', '', item)
			parts[i] = item
		r = ''.join(parts)
		return r
	out = []
	for line, raw in zip(lines, text.splitlines(True)):
		ending = raw[len(line.raw):]
		if 'renumber' == mode and 'anchor' == line.kind:
			continue
		if 'renumber' == mode and 'heading' == line.kind:
			value = re.sub('^(#{2,6}\\s+)\\d+(?:\\.\\d+)*\\.?\\s*', '\\1', line.raw)
			out.append(value + ending)
			continue
		out.append((prose(line.raw, part_at(lines, line.no)) if 'prose' == line.kind else line.raw) + ending)
	return ''.join(out)
def _scope_blocks(text, kind):
	from .text_core import scan
	if 'letter' == kind:
		r = blocks(text, kind)
	else:
		from .article import parse_sections
		from .proposal import parse_blocks
		lines = scan(text)
		parsed = parse_sections(lines) if 'article' == kind else parse_blocks(lines)
		starts = {node.line: node.key for node in parsed}
		output, key = ({}, 'preface')
		for line, raw in zip(lines, text.splitlines(True)):
			if line.no in starts:
				key = starts[line.no]
			elif 'article' == kind and re.match('^#\\s+[IVXLC]+\\.', line.raw):
				key = '$part:' + line.raw
			output[key] = output.get(key, '') + raw
		r = [{'section': key, 'text': value} for key, value in output.items()]
	return r
def scope_issues(op, base, candidate):
	issues = []
	if 'inspect' == op['mode'] and candidate != base.decode('utf-8'):
		issues.append({'code': 'text.inspect_write', 'message': 'Inspect cannot change the document'})
	if op['changes'] in ('links', 'renumber') and _mechanical_projection(base.decode('utf-8'), op['kind'], op['changes']) != _mechanical_projection(candidate, op['kind'], op['changes']):
		issues.append({'code': 'text.scope', 'message': 'Candidate changes content outside the declared mechanical operation'})
	allowed = op.get('allow_sections', [])
	if allowed:
		before = _scope_blocks(base.decode('utf-8'), op['kind'])
		after = {b['section']: b['text'] for b in _scope_blocks(candidate, op['kind'])}
		names = [b['section'] for b in before]
		permit = set()
		for name in allowed:
			if name in names:
				permit.update((key for key in names if key == name or key.startswith(name + '.')))
			elif 1 != name.count('-'):
				issues.append({'code': 'text.allow', 'message': 'Unknown allowed section: ' + name})
			else:
				first, last = name.split('-')
				if first not in names or last not in names or names.index(first) > names.index(last):
					issues.append({'code': 'text.allow', 'message': 'Invalid allowed section range: ' + name})
				else:
					chosen = names[names.index(first):names.index(last) + 1]
					permit.update((key for key in names if any((key == node or key.startswith(node + '.') for node in chosen))))
		for block in before:
			if block['section'] not in permit and after.get(block['section']) != block['text']:
				issues.append({'code': 'text.outside_scope', 'message': 'Changed or removed section outside scope: ' + block['section']})
		for name in set(after) - set(names):
			if name not in permit and (not any((name.startswith(parent + '.') for parent in permit))):
				issues.append({'code': 'text.outside_scope', 'message': 'Added section outside scope: ' + name})
	r = issues
	return r
def _lint(text, kind, path, profile=None):
	if 'proposal' == kind:
		from .proposal import lint_text
		r = lint_text(text, path=path, profile=profile)
	else:
		from .article import lint_text
		r = lint_text(text, kind=kind, path=path, **{'link_style': profile['link_style']} if (profile or {}).get('link_style') else {})
	return r
# 2026-10-20 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Implement /df-article and /df-proposal client-text skills, AI-slop linter, scoped baseline diffs, and semantic § rendering":
# https://github.com/dmitry-ai/harness/issues/13
def check(root, ident, candidate, manifest=None, *, run_replay=False, replay_record=None, warning_dispositions=None, applied=False):
	from .text_core import replay, changed_command_lines
	root = Path(root).resolve()
	op, base = operation(root, ident)
	if not isinstance(candidate, str):
		raise ValueError('Candidate must be exact UTF-8 text')
	target = _document(root, op['target'])
	issues = scope_issues(op, base, candidate)
	expected_target = digest(candidate.encode()) if applied else op['base_sha256']
	if _hash_or_none(_target_bytes(target)) != expected_target:
		issues.append({'code': 'text.conflict', 'message': 'User target changed after capture; reconcile without overwriting it'})
	for name, sha in op['protected_versions'].items():
		if _hash_or_none(_target_bytes(inside(root, name))) != sha:
			issues.append({'code': 'text.protected', 'message': 'Protected file changed: ' + name})
	findings = _lint(candidate, op['kind'], target, op.get('profile'))
	issues += [{'code': f.rule, 'message': f.message, 'line': f.line} for f in findings if 'error' == f.severity]
	warning_dispositions = warning_dispositions or {}
	for finding in findings:
		basis = warning_dispositions.get(f'{finding.rule}:{finding.line}')
		if 'warning' == finding.severity and (not isinstance(basis, str) or not basis.strip()):
			issues.append({'code': 'text.warning', 'message': 'Resolve or substantively explain warning: ' + finding.format()})
	mechanical = op['changes'] in ('links', 'renumber') and (not scope_issues(op, base, candidate))
	mapped = {'valid': True, 'issues': [], 'inputs': {}, 'claims': [], 'claim_versions': {}}
	if not mechanical and 'inspect' != op['mode']:
		mapped = validate_map(root, candidate, op['kind'], manifest)
		issues.extend(mapped['issues'])
	from .text_sources import validate_source_checks
	sources = validate_source_checks(root, candidate, (manifest or {}).get('source_checks', []))
	issues.extend(sources['issues'])
	changed = changed_command_lines(candidate, base.decode('utf-8'))
	replay_data = []
	if changed:
		if run_replay:
			replay_data = replay(candidate, only=changed, contracts=(manifest or {}).get('commands'), shell=op.get('shell'))
			payload = json_data({'schema_version': 1, 'operation': ident, 'candidate_sha256': digest(candidate.encode()), 'lines': changed, 'results': replay_data})
			replay_path = _immutable(_folder(root) / 'operations' / ident / (digest(payload) + '-replay.json'), payload)
			replay_record = replay_path.relative_to(root).as_posix()
		elif not replay_record:
			issues.append({'code': 'text.replay_missing', 'message': 'New/changed commands require an explicit replay of exactly these blocks', 'lines': changed})
		else:
			replay_path = inside(root, replay_record)
			stored = _read(replay_path)
			if replay_path.name != digest(replay_path.read_bytes()) + '-replay.json' or stored.get('operation') != ident or stored.get('candidate_sha256') != digest(candidate.encode()) or (stored.get('lines') != changed):
				raise ValueError('Replay receipt does not cover the exact changed command blocks')
			replay_data = stored['results']
		if replay_data and (len(replay_data) != len(changed) or any(('match' != r.get('status') for r in replay_data))):
			issues.append({'code': 'text.replay', 'message': 'Changed command coverage or execution failed', 'results': replay_data})
	result = {'schema_version': 1, 'operation': ident, 'root': str(root), 'target': op['target'], 'kind': op['kind'], 'base_sha256': op['base_sha256'], 'candidate_sha256': digest(candidate.encode()), 'valid': not issues, 'issues': issues, 'coverage': 'mechanical' if mechanical else 'semantic', 'inputs': {**mapped['inputs'], **sources['inputs']}, 'claims': mapped['claims'], 'claim_versions': mapped['claim_versions'], 'source_checks': sources['checks'], 'manifest': manifest, 'replay_record': replay_record, 'warning_dispositions': warning_dispositions, 'diff': ''.join(difflib.unified_diff(base.decode('utf-8').splitlines(True), candidate.splitlines(True), fromfile='before/' + op['target'], tofile='after/' + op['target']))}
	if result['claim_versions']:
		from .text_claims import registry_path, subset
		registry = registry_path(root, (manifest or {}).get('registry', 'ꘖ/KB/TextClaims.json'))
		result['claim_snapshot'] = subset(_read(registry), result['claim_versions'])
	folder = _folder(root) / 'operations' / ident
	source = _immutable(folder / (result['candidate_sha256'] + '.md'), candidate.encode())
	result['candidate'] = source.relative_to(root).as_posix()
	payload = json_data(result)
	receipt = _immutable(folder / (digest(payload) + '-check.json'), payload)
	return {**result, 'check': receipt.relative_to(root).as_posix()}
def read_check(root, reference):
	file = inside(root, reference)
	data = _read(file)
	if file.name != digest(file.read_bytes()) + '-check.json' or data.get('root') != str(Path(root).resolve()):
		raise ValueError('Invalid/changed text check receipt')
	candidate = inside(root, data['candidate']).read_bytes()
	if digest(candidate) != data['candidate_sha256']:
		raise ValueError('Candidate bytes changed after checking')
	r = (data, candidate.decode('utf-8'))
	return r
def refresh_check(root, reference, *, applied=False):
	saved, candidate = read_check(root, reference)
	current = check(root, saved['operation'], candidate, saved['manifest'], replay_record=saved['replay_record'], warning_dispositions=saved['warning_dispositions'], applied=applied)
	if not current['valid'] or current['inputs'] != saved['inputs'] or current['claim_versions'] != saved['claim_versions']:
		raise ValueError('Text check is stale or failed: ' + json.dumps(current['issues'], ensure_ascii=False))
	r = (current, candidate)
	return r
# 2026-10-20 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Implement /df-article and /df-proposal client-text skills, AI-slop linter, scoped baseline diffs, and semantic § rendering":
# https://github.com/dmitry-ai/harness/issues/13
def apply(root, reference):
	root = Path(root).resolve()
	with locked(_folder(root) / 'writer.lock'):
		checked, candidate = refresh_check(root, reference)
		op, base = operation(root, checked['operation'])
		if 'edit' != op['mode']:
			raise ValueError('This operation only proposes/inspects; it cannot write the user target')
		approval = None
		if 'semantic' == checked['coverage']:
			from .text_review import authorize
			approval = authorize(root, reference)
		target = _document(root, op['target'])
		if _hash_or_none(_target_bytes(target)) != op['base_sha256']:
			raise ValueError('Concurrent user edit preserved; reconcile a new operation')
		previous = deepcopy(_index(root)['targets'].get(op['target']))
		if previous is None or previous.get('sha256') != op['base_sha256']:
			raise ValueError('The applied revision requires its exact registered predecessor')
		payload = candidate.encode('utf-8')
		if op['base_exists']:
			replace_bytes(target, payload)
		else:
			target.parent.mkdir(parents=True, exist_ok=True)
			create_bytes(target, payload)
		if target.read_bytes() != payload:
			raise OSError('Applied text read-back differs')
		receipt = {k: checked[k] for k in ('operation', 'target', 'kind', 'base_sha256', 'candidate_sha256', 'coverage', 'inputs', 'claim_versions', 'candidate', 'manifest', 'source_checks')}
		receipt.update(schema_version=1, check=reference, approval=approval, status='applied', previous=previous)
		raw = json_data(receipt)
		path = _immutable(_folder(root) / 'operations' / op['id'] / (digest(raw) + '-applied.json'), raw)
		state = _index(root)
		state['targets'][op['target']] = {'sha256': digest(payload), 'kind': op['kind'], 'receipt': path.relative_to(root).as_posix()}
		_save_index(root, state)
	r = {**receipt, 'receipt': path.relative_to(root).as_posix(), 'sha256': digest(payload)}
	return r
def gate(root, *, targets=None, response=None, publication=False, capture=False):
	root = Path(root).resolve()
	state, issues = (_index(root), [])
	selected = set(targets) if None is not targets else set(state['targets'])
	for name, entry in state['targets'].items():
		if name not in selected:
			continue
		target = _document(root, name)
		if _hash_or_none(_target_bytes(target)) != entry['sha256']:
			issues.append('Text target changed without a current apply receipt: ' + name)
			continue
		if not entry.get('receipt'):
			if publication:
				issues.append('Text target has only a baseline, not publication approval: ' + name)
			continue
		file = inside(root, entry['receipt'])
		saved = _read(file)
		if file.name != digest(file.read_bytes()) + '-applied.json' or saved.get('candidate_sha256') != entry['sha256']:
			issues.append('Applied receipt changed: ' + name)
			continue
		from .text_sources import validate_source_checks
		sources = validate_source_checks(root, target.read_bytes().decode('utf-8'), saved.get('source_checks', []))
		issues.extend((item['message'] for item in sources['issues']))
		for path, expected in saved['inputs'].items():
			if not inside(root, path).is_file() or digest(inside(root, path).read_bytes()) != expected:
				issues.append('Text evidence/registry changed; recheck dependent text: ' + name)
		if publication and 'semantic' != saved['coverage']:
			issues.append('Mechanical edit does not assert semantic publication readiness: ' + name)
		if saved.get('approval'):
			from .text_review import authorize
			try:
				authorize(root, saved['check'], applied=True)
			except (OSError, ValueError) as exc:
				issues.append(name + ': ' + str(exc))
	if None is not response and state['targets']:
		from .text_core import check_response
		findings = check_response(root / 'ꘖ/data/answer-candidate.md', text=response, against=[inside(root, p) for p in selected if p in state['targets'] and inside(root, p).is_file()])
		issues.extend((f.format() for f in findings if 'error' == f.severity or 'RESP-CLAIM' == f.rule))
	if issues:
		raise ValueError('\n'.join(issues))
	r = {'valid': True, 'targets_checked': sorted(selected & set(state['targets'])), 'publication': publication}
	if capture:
		r['integrity'] = integrity_snapshot(root, {name: state['targets'][name] for name in r['targets_checked']})
	return r
def _claim_snapshot(root, checked):
	from .claims import all_claims, claim_digest
	from .text_claims import registry_path, subset
	versions = checked.get('claim_versions', {})
	if not versions:
		return None
	registry = registry_path(root, (checked.get('manifest') or {}).get('registry', 'ꘖ/KB/TextClaims.json'))
	reference = registry.relative_to(root).as_posix()
	snapshot = checked.get('claim_snapshot')
	if snapshot is None:
		candidates = [registry]
		if reference in checked['inputs']:
			candidates.append(root / 'ꘖ/data/text-claim-history' / (checked['inputs'][reference] + '.json'))
		for path in candidates:
			try:
				candidate = subset(_read(path), versions)
				if {claim['id']: claim_digest(claim) for claim in all_claims(candidate)} == versions:
					snapshot = candidate
					break
			except (OSError, ValueError, KeyError, TypeError):
				continue
	if not isinstance(snapshot, dict) or {claim['id']: claim_digest(claim) for claim in all_claims(snapshot)} != versions:
		raise ValueError('Original admitted claim revisions are missing or changed')
	return {'registry': reference, 'versions': versions, 'snapshot': snapshot}
def _applied_integrity(root, name, entry, *, require_live_proof=True):
	root = Path(root).resolve()
	if _index(root)['targets'].get(name) != entry or _hash_or_none(_target_bytes(_document(root, name))) != entry['sha256']:
		raise ValueError('Registered text target changed without its applied version: ' + name)
	files, claims, reviews = ({}, [], [])
	def add(reference, expected=None):
		actual = digest(inside(root, reference).read_bytes())
		if expected is not None and actual != expected:
			raise ValueError('Admitted text artifact changed: ' + reference)
		if reference in files and files[reference] != actual:
			raise ValueError('Conflicting admitted text artifact versions')
		files[reference] = actual
	if entry.get('receipt'):
		path = inside(root, entry['receipt'])
		saved = _read(path)
		if path.name != digest(path.read_bytes()) + '-applied.json' or saved.get('status') != 'applied' or saved.get('target') != name or saved.get('candidate_sha256') != entry['sha256']:
			raise ValueError('Applied text receipt changed: ' + name)
		checked, candidate = read_check(root, saved['check'])
		if checked.get('valid') is not True or any((saved.get(key) != checked.get(key) for key in ('operation', 'target', 'kind', 'base_sha256', 'candidate_sha256', 'coverage', 'inputs', 'claim_versions', 'candidate', 'manifest', 'source_checks'))):
			raise ValueError('Applied text no longer matches its admitted check')
		op, _ = operation(root, saved['operation'])
		if op['target'] != name or op['base_sha256'] != saved['base_sha256']:
			raise ValueError('Applied text operation identity changed')
		claim = _claim_snapshot(root, checked)
		versioned = {claim['registry']} if claim else set()
		if claim:
			claims.append(claim)
		for reference, expected in saved['inputs'].items():
			if reference not in versioned:
				add(reference, expected)
		for reference in (entry['receipt'], saved['check'], checked['candidate'], (_folder(root) / 'operations' / op['id'] / 'operation.json').relative_to(root).as_posix(), (_folder(root) / 'operations' / op['id'] / 'base.bin').relative_to(root).as_posix()):
			add(reference)
		from .text_sources import source_integrity
		for reference in saved.get('source_checks', []):
			for source, expected in source_integrity(root, candidate, reference)['inputs'].items():
				add(source, expected)
		if saved.get('approval'):
			from .text_review import approval_integrity
			approval = approval_integrity(root, saved['approval'], versioned_inputs=versioned, require_live_proof=require_live_proof)
			reviews = approval['reviews']
			for reference, expected in approval['files'].items():
				add(reference, expected)
	elif entry.get('reconciliation'):
		for reference, expected in _reconciled_integrity(root, name, entry)['files'].items():
			add(reference, expected)
	return {'target': name, 'entry': deepcopy(entry), 'files': files, 'claims': claims, 'reviews': reviews}
def integrity_snapshot(root, entries):
	root = Path(root).resolve()
	return {'schema_version': 1, 'root': str(root), 'targets': [_applied_integrity(root, name, entry) for name, entry in sorted(entries.items())]}
def _reconciled_integrity(root, name, entry):
	reference = entry.get('reconciliation')
	if not reference or entry.get('receipt'):
		raise ValueError('Explicit text baseline reconciliation is missing: ' + name)
	path = inside(root, reference)
	raw = path.read_bytes()
	saved = json.loads(raw)
	if path.name != digest(raw) + '-reconciled.json' or saved.get('schema_version') != 1 or saved.get('kind') != 'baseline_reconciliation' or saved.get('root') != str(Path(root).resolve()) or saved.get('target') != name or saved.get('document_kind') != entry.get('kind') or not isinstance(saved.get('previous'), dict) or saved.get('baseline', {}).get('sha256') != entry.get('sha256'):
		raise ValueError('Explicit text baseline reconciliation identity changed: ' + name)
	op, base = operation(root, saved['operation'])
	if op.get('reconciliation') != reference or op['target'] != name or op['kind'] != entry['kind'] or op['base_sha256'] != entry['sha256'] or 'reconcile_sha256' not in op or op['reconcile_sha256'] != entry['sha256'] or saved['baseline']['file'] != (_folder(root) / 'operations' / op['id'] / 'base.bin').relative_to(root).as_posix():
		raise ValueError('Explicit text reconciliation no longer matches the captured baseline operation: ' + name)
	files = {reference: digest(raw), saved['baseline']['file']: digest(base), (_folder(root) / 'operations' / op['id'] / 'operation.json').relative_to(root).as_posix(): digest((_folder(root) / 'operations' / op['id'] / 'operation.json').read_bytes())}
	return {'previous': saved['previous'], 'files': files}
def _verify_applied_successor(root, name, current, original):
	entry, visited = (current, set())
	while entry != original:
		reference = entry.get('receipt') or entry.get('reconciliation')
		if not reference or reference in visited:
			raise ValueError('Current text is not a proven applied successor of the admitted version: ' + name)
		visited.add(reference)
		if not entry.get('receipt'):
			entry = _reconciled_integrity(root, name, entry)['previous']
			continue
		path = inside(root, reference)
		raw = path.read_bytes()
		saved = json.loads(raw)
		if path.name != digest(raw) + '-applied.json' or saved.get('status') != 'applied' or saved.get('target') != name or saved.get('candidate_sha256') != entry.get('sha256') or saved.get('kind') != entry.get('kind'):
			raise ValueError('Applied text successor identity changed: ' + name)
		previous = saved.get('previous')
		if not isinstance(previous, dict) or previous.get('sha256') != saved.get('base_sha256'):
			raise ValueError('Applied text successor has no exact predecessor: ' + name)
		entry = previous
	return {'valid': True, 'scope': 'exact_applied_successor_lineage'}
def verify_integrity(graph):
	from .claims import all_claims, claim_digest
	if not isinstance(graph, dict) or graph.get('schema_version') != 1 or not isinstance(graph.get('root'), str) or not Path(graph['root']).is_absolute() or not isinstance(graph.get('targets'), list):
		raise ValueError('Invalid historical text integrity graph')
	root = Path(graph['root']).resolve()
	with locked(_folder(root) / 'writer.lock'):
		state = _index(root)
		for target in graph['targets']:
			for reference, expected in target['files'].items():
				if digest(inside(root, reference).read_bytes()) != expected:
					raise ValueError('Historical admitted artifact changed: ' + reference)
			for claim in target['claims']:
				if {item['id']: claim_digest(item) for item in all_claims(claim['snapshot'])} != claim['versions']:
					raise ValueError('Historical admitted claim snapshot changed')
			if target.get('reviews'):
				from .text_review import _state
				reviews = {entry['id']: entry for entry in _state(root)['reviews']}
				if any((reviews.get(entry['id']) != entry for entry in target['reviews'])):
					raise ValueError('Historical admitted publication review changed or is missing')
			name = target['target']
			current = state['targets'].get(name)
			if current is None:
				raise ValueError('Historical text target registration is missing: ' + name)
			if current != target['entry']:
				if not current.get('receipt') and not current.get('reconciliation'):
					raise ValueError('Later text version has no applied receipt: ' + name)
				_verify_applied_successor(root, name, current, target['entry'])
				_applied_integrity(root, name, current, require_live_proof=False)
			elif _hash_or_none(_target_bytes(_document(root, name))) != target['entry']['sha256']:
				raise ValueError('Historical text target changed without an applied revision: ' + name)
	return {'valid': True, 'scope': 'original_admitted_artifacts'}
def _roots(paths):
	roots = set()
	for value in paths:
		path = Path(value).resolve()
		for root in (path, *path.parents):
			if (_folder(root) / 'index.json').is_file():
				roots.add(root)
	r = sorted(roots)
	return r
def gate_paths(paths, *, response=None):
	selected = {Path(path).resolve() for path in paths}
	r = [gate(root, response=response, targets=[name for name in _index(root)['targets'] if (root / name).resolve() in selected]) for root in _roots(selected)]
	return r
def gate_requests(paths, requests, response, *, capture=False):
	results = []
	for root in _roots(paths):
		state, selected = (_index(root), set())
		for ident in state['operations']:
			op, _ = operation(root, ident)
			if set(op['requests']) & set(requests):
				selected.add(op['target'])
		if selected:
			results.append(gate(root, targets=selected, response=response, capture=capture))
	r = results
	return r
def record_answer(root, journal, requests, response, turn):
	from .journal import record_answer as save
	gate_requests([root], requests, response)
	steps = save(Path(journal), requests, response, turn)
	r = {'journal_steps': steps, 'response_sha256': digest(response.encode()), 'delivery_verified': False}
	return r
