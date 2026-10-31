# 2026-10-16 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Unify Antigravity and OpenAI Codex adapters with build-native projections, parent-driven model selection, and cross-system continuation":
# https://github.com/dmitry-ai/harness/issues/6
# 2026-10-31 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Reorganize AI into universal harness repository, translate rules and documentation to English, format per P.md, and enforce issue-driven Git workflow":
# https://github.com/dmitry-ai/harness/issues/26
import hashlib
import json
from pathlib import Path
import re
def text_project_id(root):
	root = Path(root).resolve()
	r = 'text-' + hashlib.sha256(str(root).encode('utf-8')).hexdigest()
	return r
def native_project_id(root):
	root = Path(root).resolve()
	job = root / 'ꘖ/project.json'
	if job.is_file():
		project = json.loads(job.read_text(encoding='utf-8-sig'))
		identifier = project.get('job_id') if isinstance(project, dict) else None
		if not isinstance(identifier, str) or not identifier.strip() or identifier.startswith('text-'):
			raise ValueError('Existing project.json needs its real Upwork job_id')
		r = identifier
	else:
		marker = root / 'ꘖ/data/text-project.json'
		if not marker.is_file():
			raise ValueError('No native project identity; initialize an explicit text workspace first')
		value = json.loads(marker.read_text(encoding='utf-8-sig'))
		if not isinstance(value, dict) or type(value.get('schema_version')) is not int or 1 != value['schema_version'] or ('client_text_workspace' != value.get('kind')) or (not _same_root(value.get('project_root'), root)) or (value.get('id') != text_project_id(root)):
			raise ValueError('Text workspace marker has the wrong root, kind, schema or internal ID')
		r = value['id']
	return r
def native_project_fields(root):
	identifier = native_project_id(root)
	is_text = identifier.startswith('text-')
	r = {'project_id': identifier, 'project_kind': 'client_text_workspace' if is_text else 'upwork_job', 'job_id': None if is_text else identifier}
	return r
def completion_project_id(root):
	root = Path(root).resolve()
	if not root.is_dir():
		raise ValueError('Completion needs an exact existing project directory')
	if (root / 'ꘖ/project.json').exists() or (root / 'ꘖ/data/text-project.json').exists():
		r = native_project_id(root)
	else:
		r = text_project_id(root)
	return r
def _canonical_root(value):
	path = Path(value).resolve()
	if path.name in ('code', '_') and (path.parent / 'code').is_dir() and (path.parent / '_').is_dir():
		path = path.parent.resolve()
	norm = str(path).replace('\\', '/').rstrip('/').lower()
	if norm in ('c:/work/upwork/code/ai', 'c:/work/upwork/code/ai/primary', 'c:/work/upwork/code/ai/primary/' + 'result', 'c:/work/research/provision/code/ai/harness'):
		r = 'c:/work/research/provision/code/ai/harness'
	else:
		r = norm
	return r
def _same_root(value, root):
	if not isinstance(value, str) or not value.strip() or (not Path(value).is_absolute()):
		r = False
	else:
		r = _canonical_root(value) == _canonical_root(root)
	return r
def _explicit(text, root, job_id):
	commands = re.findall('(?:/|\\$)upwork-init\\s+https?://[^\\s]*?~(\\d+)', text)
	if commands:
		r = (all(('~' + ident == job_id for ident in commands)), 'explicit-upwork-init')
	else:
		declarations = re.findall('(?im)(?:\\u043a\\u043e\\u0440\\u0435\\u043d\\u044c \\u043f\\u0440\\u043e\\u0435\\u043a\\u0442\\u0430|project root|\\u043f\\u0440\\u043e\\u0435\\u043a\\u0442)\\s*:\\s*([^\\r\\n]+)', text)
		if not declarations:
			r = (None, None)
		else:
			paths = [value.strip().strip('.,;:').strip('`"<>«»\'').strip('.,;:') for value in declarations]
			r = (all((_same_root(value, root) for value in paths)), 'explicit-project-root')
	return r
def scoped_inputs(root, job_id, inputs, contexts=(), *, until=None):
	events = [(step, 1, text, None) for step, text in inputs if None is until or step <= until]
	events += [(step, 0, path, source) for step, path, source in contexts if None is until or step <= until]
	events.sort(key=lambda item: (item[0], item[1]))
	legacy = not any((0 == kind for _, kind, _, _ in events))
	selected, active, previous_root, binding = ([], False, object(), None)
	for step, kind, value, source in events:
		if 0 == kind:
			normalized = str(Path(value).resolve()) if value else None
			if normalized != previous_root:
				previous_root, active = (normalized, _same_root(normalized, root))
				binding = {'kind': source, 'native_step': step, 'root': normalized}
			continue
		choice, source = _explicit(value, root, job_id)
		if None is not choice:
			active, legacy = (choice, False)
			binding = {'kind': source, 'native_step': step, 'root': str(Path(root).resolve())}
		elif legacy and (not active) and (not job_id.startswith('text-')) and (job_id in value):
			active = True
			binding = {'kind': 'legacy-native-job-id', 'native_step': step, 'job_id': job_id}
		if active and value.strip():
			selected.append((step, value, dict(binding)))
	r = (selected, active, binding)
	return r
