# 2026-10-17 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from contextlib import nullcontext
from Df.Core.lib.sha256 import df_sha256
import json
import os
from pathlib import Path
import re
# 2026-11-19
# "Wire project path overlays across Harness subsystems with paths CLI and regression tests":
# https://github.com/dmitry-ai/harness/issues/96
from .path_registry import store_path
# 2026-10-31
# "Reorganize AI into universal harness repository, translate rules and documentation to English, format per P.md, and enforce issue-driven Git workflow":
# https://github.com/dmitry-ai/harness/issues/26
from .runtime import HARNESS_META, PRIMARY, settings
from .storage import create_bytes, locked, replace_bytes
from .upwork_data import normalize_job_id
# 2026-11-19
# "Wire project path overlays across Harness subsystems with paths CLI and regression tests":
# https://github.com/dmitry-ai/harness/issues/96
INCOMING = store_path('incoming_dir')
DAILY = Path(settings()['workspace_root']) / settings()['daily_root']
CAPTURE_NAME = re.compile('^(0[12][A-Za-z0-9]+)-([A-Za-z0-9-]{8,})$')
WEB_SUFFIXES = {'.html', '.htm', '.json', '.xml', '.mjs', '.js', '.css', '.txt', '.png', '.jpg', '.jpeg', '.webp'}
INDEX_MARKER = '<!-- upwork-intake:generated v1 -->\n'
# @used-by :func:`commit_capture()`
def _bytes(value):
	return (json.dumps(value, ensure_ascii=False, indent=2) + '\n').encode('utf-8')
# 2026-11-26 "Extract general duplicated helpers into Df/Core and Df/Qa": https://github.com/dmitry-ai/harness/issues/378
# @used-by :func:`_receipt()`
# @used-by :func:`_remaining()`
# @used-by :func:`_retired()`
# @used-by :func:`_snapshot()`
# @used-by :func:`_validate_new()`
# @used-by :func:`_validate_receipt()`
# @used-by :func:`commit_capture()`
def _hash(payload):
	return df_sha256(payload)
# @used-by :func:`_plain()`
# @used-by :func:`_receipt()`
def _linked(path):
	return path.is_symlink() or (hasattr(path, 'is_junction') and path.is_junction())
# @used-by :func:`_inventory()`
# @used-by :func:`_read()`
# @used-by :func:`_validate_new()`
# @used-by :func:`_within()`
# @used-by :func:`commit_capture()`
# @used-by :func:`drain_incoming()`
def _plain(path):
	path = Path(os.path.abspath(path))
	if any((_linked(p) for p in (path, *path.parents))):
		raise ValueError(f'Linked path is preserved: {path}')
	r = path
	return r
# @used-by :func:`_index()`
# @used-by :func:`_project()`
# @used-by :func:`_receipt()`
# @used-by :func:`_restore()`
# @used-by :func:`_retired()`
# @used-by :func:`_snapshot()`
# @used-by :func:`_validate_receipt()`
# @used-by :func:`commit_capture()`
def _within(root, relative):
	relative = Path(str(relative).replace('\\', '/'))
	if relative.is_absolute() or '..' in relative.parts or (not relative.parts):
		raise ValueError('Evidence path must be relative and remain inside its owner')
	target = _plain(root / relative)
	if not target.is_relative_to(root):
		raise ValueError('Evidence path escapes its owner')
	r = target
	return r
# @used-by :func:`_index()`
# @used-by :func:`_inventory()`
# @used-by :func:`_project()`
# @used-by :func:`_receipt()`
# @used-by :func:`_snapshot()`
# @used-by :func:`_validate_receipt()`
# @used-by :func:`commit_capture()`
def _read(path):
	path = _plain(path)
	before = path.stat()
	payload = path.read_bytes()
	after = path.stat()
	if (before.st_ino, before.st_size, before.st_mtime_ns, before.st_ctime_ns) != (after.st_ino, after.st_size, after.st_mtime_ns, after.st_ctime_ns):
		raise ValueError(f'Concurrent file change; staging is preserved: {path}')
	r = payload
	return r
# @used-by :func:`_remaining()`
# @used-by :func:`commit_capture()`
def _inventory(capture):
	result, dirs = ({}, set())
	if capture.exists():
		for parent, children, names in os.walk(capture, followlinks=False):
			parent = _plain(parent)
			for name in children:
				path = _plain(parent / name)
				dirs.add(path.relative_to(capture).as_posix())
			for name in names:
				path = _plain(parent / name)
				if not path.is_file():
					raise ValueError(f'Non-file staging material is preserved: {path}')
				result[path.relative_to(capture).as_posix()] = _read(path)
	r = (result, dirs)
	return r
# @used-by :func:`commit_capture()`
def _project(capture, daily):
	# 2026-11-19
	# "Wire project path overlays across Harness subsystems with paths CLI and regression tests":
	# https://github.com/dmitry-ai/harness/issues/96
	from .path_registry import project_paths
	match = CAPTURE_NAME.fullmatch(capture.name)
	if not match:
		raise ValueError('Unknown/manual capture directory is preserved')
	job_id = normalize_job_id('~' + match[1])
	reg_file = store_path('upwork_projects_index') if daily.resolve() == DAILY.resolve() and (not (daily / 'ꘖ/data/projects.json').exists()) else _within(daily, 'ꘖ/data/projects.json')
	registry = json.loads(_read(reg_file).decode('utf-8-sig'))
	if not isinstance(registry, dict) or job_id not in registry:
		raise ValueError('Capture has no registered project; staging is preserved')
	project = _within(daily, registry[job_id])
	pp = project_paths(project, exact_root=True)
	state = json.loads(_read(_within(project, pp.rel_to_root(pp.project_json))).decode('utf-8-sig'))
	if not isinstance(state, dict) or state.get('job_id') != job_id or True is not state.get('initialized'):
		raise ValueError('Project initialization is incomplete; staging is preserved')
	r = (project, state)
	return r
# @used-by :func:`_receipt()`
# @used-by :func:`_validate_receipt()`
def _snapshot(project, state, source):
	# 2026-11-19
	# "Wire project path overlays across Harness subsystems with paths CLI and regression tests":
	# https://github.com/dmitry-ai/harness/issues/96
	from .path_registry import project_paths
	pp = project_paths(project, exact_root=True)
	if not isinstance(source, dict) or source.get('job_id') != state['job_id']:
		raise ValueError('The capture source does not match the initialized project')
	snapshot = _within(project, state['snapshot'])
	evidence = _within(project, pp.rel_to_root(pp.evidence_dir))
	kb_dir = _within(project, pp.rel_to_root(pp.kb_dir))
	if not snapshot.is_relative_to(evidence):
		raise ValueError('The initialized snapshot must belong to project Evidence')
	payload = _read(snapshot)
	saved = json.loads(payload.decode('utf-8-sig'))
	clean = {k: v for k, v in source.items() if k not in ('saved_attachments', 'cookies')}
	if not isinstance(saved, dict) or {k: v for k, v in saved.items() if 'asset_evidence' != k} != clean:
		raise ValueError('The permanent snapshot differs from this capture; staging is preserved')
	assets = source.get('saved_attachments') or []
	permanent = saved.get('asset_evidence') or []
	if sorted((x['sha256'] for x in assets)) != sorted((x['sha256'] for x in permanent)):
		raise ValueError('The permanent snapshot does not retain every attachment')
	for asset in permanent:
		target = _within(kb_dir, asset['file'])
		if not target.is_relative_to(evidence) or _hash(_read(target)) != asset['sha256']:
			raise ValueError('A permanent attachment is missing or changed; staging is preserved')
	r = {'file': snapshot.relative_to(project).as_posix(), 'sha256': _hash(payload), 'transform': 'Drop transport saved_attachments/cookies; add verified project asset_evidence.'}
	return r
# @used-by :func:`_receipt()`
def _validate_new(capture, source, files, dirs):
	if not isinstance(source, dict) or source.get('job_id') != '~' + CAPTURE_NAME.fullmatch(capture.name)[1]:
		raise ValueError('Capture directory and source job IDs differ')
	if source.get('cookies'):
		raise ValueError('Capture contains transport credentials; automatic evidence archive is deferred')
	declared = set()
	for asset in source.get('saved_attachments') or []:
		path = _plain(asset['path'])
		if not path.is_relative_to(capture):
			raise ValueError('Source attachment belongs outside this staging capture')
		relative = path.relative_to(capture).as_posix()
		if not relative.startswith('attachments/') or _hash(files[relative]) != asset['sha256']:
			raise ValueError('A captured attachment is missing or changed')
		declared.add(relative)
	for name in files:
		path = Path(name)
		known = name in ('source.json', 'site.json', 'request.txt', 'products.json_limit=250') or name in declared or (1 == len(path.parts) and path.suffix.lower() in WEB_SUFFIXES)
		if not known:
			raise ValueError(f'Unknown/manual file is preserved: {name}')
	if dirs - {'attachments'}:
		raise ValueError('Unknown/manual staging directories are preserved')
# @used-by :func:`commit_capture()`
def _receipt(project, capture, state, files, dirs):
	# 2026-11-19
	# "Wire project path overlays across Harness subsystems with paths CLI and regression tests":
	# https://github.com/dmitry-ai/harness/issues/96
	from .path_registry import project_paths
	pp = project_paths(project, exact_root=True)
	ev_rel = pp.rel_to_root(pp.evidence_dir)
	source = json.loads(files['source.json'].decode('utf-8-sig'))
	_validate_new(capture, source, files, dirs)
	snapshot = _snapshot(project, state, source)
	sizes = {len(payload) for payload in files.values()}
	known = {}
	evidence = _within(project, ev_rel)
	for parent, children, names in os.walk(evidence, followlinks=False):
		children[:] = [name for name in children if not _linked(Path(parent) / name)]
		for name in names:
			path = Path(parent) / name
			if not _linked(path) and path.is_file() and (path.stat().st_size in sizes):
				known.setdefault(_hash(_read(path)), path.relative_to(project).as_posix())
	entries = []
	for name, payload in sorted(files.items()):
		digest = _hash(payload)
		if digest not in known:
			suffix = Path(name).suffix.lower()
			suffix = suffix if suffix in ('.json', '.txt', '.xml', '.png', '.jpg', '.jpeg', '.webp') else suffix + '.txt'
			known[digest] = f'{ev_rel}/Intake/objects/{digest}{suffix}'
		entries.append({'original_relative_provenance': name, 'sha256': digest, 'bytes': len(payload), 'durable_file': known[digest], 'transform': 'identity'})
	r = {'version': 1, 'capture_id': capture.name, 'job_id': source['job_id'], 'status': 'prepared', 'original_directory_provenance': str(capture), 'original_paths_are_provenance_only': True, 'snapshot': snapshot, 'entries': entries}
	return r
# @used-by :func:`agent_tools.claims._manifest_primary()`
# @used-by :func:`commit_capture()`
def _validate_receipt(receipt, capture, project, state):
	# 2026-11-19
	# "Wire project path overlays across Harness subsystems with paths CLI and regression tests":
	# https://github.com/dmitry-ai/harness/issues/96
	from .path_registry import project_paths
	ev_rel = project_paths(project, exact_root=True).rel_to_root(project_paths(project, exact_root=True).evidence_dir)
	if not isinstance(receipt, dict) or 1 != receipt.get('version') or receipt.get('capture_id') != capture.name or (receipt.get('job_id') != state['job_id']) or (receipt.get('original_directory_provenance') != str(capture)) or (receipt.get('status') not in ('prepared', 'drained')):
		raise ValueError('Unknown/manual intake receipt is preserved')
	names = set()
	evidence_dir = _within(project, ev_rel)
	for entry in receipt['entries']:
		name = entry['original_relative_provenance']
		_within(capture, name)
		target = _within(project, entry['durable_file'])
		if name in names or not re.fullmatch('[0-9a-f]{64}', entry['sha256']) or (not target.is_relative_to(evidence_dir)) or ('identity' != entry['transform']) or (len(_read(target)) != entry['bytes']) or (_hash(_read(target)) != entry['sha256']):
			raise ValueError('A permanent intake object is missing or changed; staging is preserved')
		names.add(name)
	original = next((x for x in receipt['entries'] if 'source.json' == x['original_relative_provenance']))
	source = json.loads(_read(_within(project, original['durable_file'])).decode('utf-8-sig'))
	if _snapshot(project, state, source) != receipt['snapshot']:
		raise ValueError('The permanent snapshot changed during intake; staging is preserved')
# @used-by :func:`_remaining()`
# @used-by :func:`_restore()`
# @used-by :func:`commit_capture()`
# @used-by :meth:`test_intake.IntakeTests.test_concurrent_replacement_during_retirement_keeps_both_versions()`
def _retired(capture, name):
	original = _within(capture, name)
	r = original.with_name('.intake-retired-' + _hash(name.encode('utf-8'))[:24])
	return r
# @used-by :func:`commit_capture()`
def _remaining(receipt, capture):
	files, dirs = _inventory(capture)
	allowed_dirs = {parent.as_posix() for e in receipt['entries'] for parent in Path(e['original_relative_provenance']).parents if parent != Path('.')}
	if dirs - allowed_dirs:
		raise ValueError('New/manual staging directory appeared; staging is preserved')
	expected = {}
	for entry in receipt['entries']:
		name = entry['original_relative_provenance']
		retired = _retired(capture, name).relative_to(capture).as_posix()
		if name in files and retired in files:
			raise ValueError('Concurrent replacement is preserved alongside retired evidence')
		for candidate in (name, retired):
			if candidate in files:
				if _hash(files[candidate]) != entry['sha256']:
					raise ValueError('Concurrent staging change; every remaining file is preserved')
				expected[candidate] = entry
	if set(files) != set(expected):
		raise ValueError('New/manual staging files appeared; staging is preserved')
	r = expected
	return r
# @used-by :func:`commit_capture()`
def _restore(receipt, capture):
	for entry in receipt['entries']:
		original = _within(capture, entry['original_relative_provenance'])
		retired = _retired(capture, entry['original_relative_provenance'])
		if retired.exists() and (not original.exists()):
			os.rename(retired, original)
# @used-by :func:`commit_capture()`
# @used-by :meth:`test_intake.IntakeTests.test_concurrent_edit_after_copy_is_preserved_and_not_silently_replanned()`
def _index(project):
	# 2026-11-19
	# "Wire project path overlays across Harness subsystems with paths CLI and regression tests":
	# https://github.com/dmitry-ai/harness/issues/96
	from .path_registry import project_paths
	pp = project_paths(project, exact_root=True)
	kb_rel = pp.rel_to_root(pp.kb_dir)
	ev_rel = pp.rel_to_root(pp.evidence_dir)
	ev_in_kb = Path(ev_rel).relative_to(kb_rel).as_posix() if Path(ev_rel).is_relative_to(kb_rel) else 'Evidence'
	target = _within(project, f'{kb_rel}/Intake.md')
	if target.exists() and (not _read(target).decode('utf-8-sig').startswith(INDEX_MARKER)):
		raise ValueError('Manual KB/Intake.md is preserved; intake drain is deferred')
	lines = [INDEX_MARKER.rstrip(), '# Source Materials', '', 'Previous paths in receipts record provenance only. Working links point to permanent evidence.', '']
	for path in sorted(_within(project, f'{ev_rel}/Intake').glob('*.json')):
		receipt = json.loads(_read(path).decode('utf-8-sig'))
		lines.extend([f"## {receipt['capture_id']}", '', f'[Receipt]({ev_in_kb}/Intake/{path.name}).', ''])
		for entry in receipt['entries']:
			relative = Path(entry['durable_file']).relative_to(kb_rel).as_posix()
			label = entry['original_relative_provenance'].replace('[', '\\[').replace(']', '\\]')
			lines.append(f"- [{label}](<{relative}>) — SHA-256 `{entry['sha256']}`.")
		lines.append('')
	from .analysis import publish_owned
	publication = publish_owned(target, '\n'.join(lines) + '\n', history=False)
	if 'conflict' == publication['status']:
		raise ValueError('Intake index was manually changed; preserve it and reconcile the publication candidate')
	from .project_card import sync_block
	navigation = sync_block(project, _within(project, f'{kb_rel}/.md'), 'intake-navigation', '## Source Materials\n\n[Saved sources and import receipts](Intake.md).\n', position='append', source=target)
	if 'conflict' == navigation['status']:
		raise ValueError('Intake navigation was manually changed; staging is preserved for reconciliation')
# 2026-10-17
# "Enforce complete client attachment ingestion, verbatim media transcription, and intake-drain staging":
# https://github.com/dmitry-ai/harness/issues/7
# @used-by :func:`agent_tools.upwork_project.run()`
# @used-by :func:`drain_incoming()`
# @used-by :meth:`test_intake.IntakeTests.commit()`
def commit_capture(capture, *, incoming_root=INCOMING, daily_root=DAILY, apply=False):
	# 2026-11-19
	# "Wire project path overlays across Harness subsystems with paths CLI and regression tests":
	# https://github.com/dmitry-ai/harness/issues/96
	from .path_registry import project_paths
	capture, incoming, daily = (Path(capture), Path(incoming_root), Path(daily_root))
	report = {'capture': str(capture), 'status': 'retained', 'drained': False}
	receipt = None
	try:
		incoming, daily = (_plain(incoming), _plain(daily))
		capture = _plain(capture if capture.is_absolute() else incoming / capture)
		report['capture'] = str(capture)
		if capture.parent != incoming:
			raise ValueError('Only one immediate managed incoming capture may be drained')
		project, state = _project(capture, daily)
		pp = project_paths(project, exact_root=True)
		data_rel = pp.rel_to_root(pp.data_dir)
		pj_rel = pp.rel_to_root(pp.project_json)
		kb_rel = pp.rel_to_root(pp.kb_dir)
		ev_rel = pp.rel_to_root(pp.evidence_dir)
		report['project'] = str(project)
		with locked(_within(project, f'{data_rel}/init.lock')) if apply else nullcontext():
			state = json.loads(_read(_within(project, pj_rel)).decode('utf-8-sig'))
			if not isinstance(state, dict) or True is not state.get('initialized') or state.get('job_id') != '~' + CAPTURE_NAME.fullmatch(capture.name)[1]:
				raise ValueError('Project initialization changed; staging is preserved')
			manifest = _within(project, f'{ev_rel}/Intake/{capture.name}.json')
			if manifest.exists():
				receipt = json.loads(_read(manifest).decode('utf-8-sig'))
				_validate_receipt(receipt, capture, project, state)
			else:
				files, dirs = _inventory(capture)
				receipt = _receipt(project, capture, state, files, dirs)
			report.update(manifest=str(manifest), files=len(receipt['entries']), bytes=sum((x['bytes'] for x in receipt['entries'])), evidence_index=str(_within(project, f'{kb_rel}/Intake.md')), durable_inputs={x['original_relative_provenance']: str(_within(project, x['durable_file'])) for x in receipt['entries'] if x['original_relative_provenance'] in ('source.json', 'site.json', 'request.txt')})
			_remaining(receipt, capture)
			if not apply:
				r = {**report, 'status': 'planned'}
			else:
				if not manifest.exists():
					for entry in receipt['entries']:
						target = _within(project, entry['durable_file'])
						if not target.exists():
							payload = files[entry['original_relative_provenance']]
							target.parent.mkdir(parents=True, exist_ok=True)
							create_bytes(target, payload)
					_validate_receipt(receipt, capture, project, state)
					manifest.parent.mkdir(parents=True, exist_ok=True)
					create_bytes(manifest, _bytes(receipt))
				_index(project)
				_remaining(receipt, capture)
				for entry in receipt['entries']:
					name = entry['original_relative_provenance']
					original = _within(capture, name)
					if original.exists():
						if _hash(_read(original)) != entry['sha256']:
							raise ValueError('Concurrent staging change; drain deferred')
						os.rename(original, _retired(capture, name))
				_remaining(receipt, capture)
				_validate_receipt(receipt, capture, project, state)
				for entry in receipt['entries']:
					remaining = _remaining(receipt, capture)
					retired = _retired(capture, entry['original_relative_provenance'])
					if retired.relative_to(capture).as_posix() in remaining:
						retired.unlink()
				if capture.exists():
					_, dirs = _inventory(capture)
					for relative in sorted(dirs, key=lambda x: len(Path(x).parts), reverse=True):
						_within(capture, relative).rmdir()
					capture.rmdir()
				if 'drained' != receipt['status']:
					receipt['status'] = 'drained'
					replace_bytes(manifest, _bytes(receipt))
				r = {**report, 'status': 'drained', 'drained': True}
	except (OSError, ValueError, KeyError, TypeError, StopIteration) as exc:
		if apply and None is not receipt:
			try:
				_restore(receipt, capture)
			except (OSError, ValueError):
				pass
		r = {**report, 'reason': str(exc)}
	return r
# 2026-10-17
# "Enforce complete client attachment ingestion, verbatim media transcription, and intake-drain staging":
# https://github.com/dmitry-ai/harness/issues/7
# @used-by :func:`agent_tools.upwork_project.run()`
def drain_incoming(capture=None, *, incoming_root=INCOMING, daily_root=DAILY, apply=False):
	incoming = _plain(incoming_root)
	paths = [Path(capture)] if None is not capture else sorted(incoming.iterdir()) if incoming.exists() else []
	captures = [commit_capture(path, incoming_root=incoming, daily_root=daily_root, apply=apply) for path in paths]
	r = {'applied': apply, 'complete': all((x['status'] in ('planned', 'drained') for x in captures)), 'captures': captures, 'retained': sum(('retained' == x['status'] for x in captures))}
	return r
