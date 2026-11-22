# 2026-11-23 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Use native workspace priority and AST command parsing in request binding":
# https://github.com/dmitry-ai/harness/issues/129
# 2026-11-21 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Support V2 `𝐒`/`𝐖` software subtrees and cross-root project relocations in Harness":
# https://github.com/dmitry-ai/harness/issues/113
# 2026-11-21 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Remove text-based explicit-project-root override from request binding":
# https://github.com/dmitry-ai/harness/issues/112
# 2026-11-21 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Restrict explicit project root binding to full root labels":
# https://github.com/dmitry-ai/harness/issues/111
# 2026-11-19 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Wire project path overlays across Harness subsystems with paths CLI and regression tests":
# https://github.com/dmitry-ai/harness/issues/96
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
from ..path_registry import canonicalize_root_dir, project_paths, relocated_roots
def _raw_text_project_id(path_val):
	return 'text-' + hashlib.sha256(str(Path(path_val).resolve()).encode('utf-8')).hexdigest()
def text_project_id(root):
	return _raw_text_project_id(canonical_path(root))
def native_project_id(root):
	pp = project_paths(root, exact_root=True)
	root = pp.root
	job = pp.project_json
	if job.is_file():
		project = json.loads(job.read_text(encoding='utf-8-sig'))
		identifier = project.get('job_id') if isinstance(project, dict) else None
		if not isinstance(identifier, str) or not identifier.strip() or identifier.startswith('text-'):
			raise ValueError('Existing project.json needs its real Upwork job_id')
		r = identifier
	else:
		marker = pp.text_project_json
		if not marker.is_file():
			raise ValueError('No native project identity; initialize an explicit text workspace first')
		value = json.loads(marker.read_text(encoding='utf-8-sig'))
		saved_root = value.get('project_root') if isinstance(value, dict) else None
		valid_ids = {text_project_id(root)} | ({_raw_text_project_id(saved_root)} if isinstance(saved_root, str) and saved_root.strip() and Path(saved_root).is_absolute() else set())
		if not isinstance(value, dict) or type(value.get('schema_version')) is not int or 1 != value['schema_version'] or ('client_text_workspace' != value.get('kind')) or (not _same_root(saved_root, root)) or (value.get('id') not in valid_ids):
			raise ValueError('Text workspace marker has the wrong root, kind, schema or internal ID')
		r = value['id']
	return r
def native_project_fields(root):
	identifier = native_project_id(root)
	is_text = identifier.startswith('text-')
	r = {'project_id': identifier, 'project_kind': 'client_text_workspace' if is_text else 'upwork_job', 'job_id': None if is_text else identifier}
	return r
def completion_project_id(root):
	root_p = Path(root).resolve()
	if not root_p.is_dir():
		raise ValueError('Completion needs an exact existing project directory')
	pp = project_paths(root_p, exact_root=True)
	if pp.project_json.exists() or pp.text_project_json.exists():
		r = native_project_id(pp.root)
	else:
		r = text_project_id(pp.root)
	return r
# 2026-10-31 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Canonicalize relocated Codex, Antigravity, and Harness project roots and support v2Migrated gitFolder project resources":
# https://github.com/dmitry-ai/harness/issues/29
_RELOCATED_ROOTS = relocated_roots()
def canonical_path(value):
	return canonicalize_root_dir(value)
def _canonical_root(value):
	r = str(canonical_path(value)).replace('\\', '/').rstrip('/').lower()
	return r
def _same_root(value, root):
	if not isinstance(value, str) or not value.strip() or (not Path(value).is_absolute()):
		r = False
	else:
		r = _canonical_root(value) == _canonical_root(root)
	return r
_CLAUDE_CMD_RE = re.compile('^\\s*(?:<command-message>[^<]*</command-message>\\s*)?<command-name>\\s*/?upwork-init\\s*</command-name>\\s*<command-args>([^<]*)</command-args>', re.I | re.S)
_UPWORK_JOB_URL_RE = re.compile('https?://[^\\s<>)"\\\'`]+?~(\\d+)(?=\\s|$|[.,;)\\]])')
_LEADING_CMD_RE = re.compile('^\\s*(?:/|\\$)upwork-init\\s+(https?://[^\\s<>)"\\\'`]+?~(\\d+)(?=\\s|$|[.,;)\\]]))', re.I)
_LEADING_NATIVE_CMD_RE = re.compile('^\\s*(?:(?:/|\\$)?upwork-init\\s+)?(https?://[^\\s<>)"\\\'`]+?~(\\d+)(?=\\s|$|[.,;)\\]]))', re.I)
_SLASH_LINK_HREF_RE = re.compile('^slashcommand;/?upwork-init$', re.I)
def _extract_leading_upwork_init_ids(text, *, meta=None):
	if not isinstance(text, str) or not text.strip():
		return []
	m_claude = _CLAUDE_CMD_RE.match(text)
	if m_claude:
		return ['~' + ident for ident in _UPWORK_JOB_URL_RE.findall(m_claude.group(1))]
	native_leading_upwork = False
	if isinstance(meta, dict):
		slash_cmds = meta.get('slash_commands') or []
		leading_names = [str(item.get('name') or '').strip().lower() for item in slash_cmds if isinstance(item, dict) and item.get('leading')]
		if leading_names:
			if 'upwork-init' not in leading_names:
				return []
			native_leading_upwork = True
	from ..source_grounding import markdown_parser
	tokens = markdown_parser().parse(text)
	if not tokens or 'paragraph_open' != tokens[0].type or 2 > len(tokens) or ('inline' != tokens[1].type):
		return []
	line_children = []
	for child in tokens[1].children or ():
		if child.type in ('softbreak', 'hardbreak'):
			break
		line_children.append(child)
	idx = 0
	while idx < len(line_children) and 'text' == line_children[idx].type and (not line_children[idx].content.strip()):
		idx += 1
	if idx >= len(line_children):
		return []
	first = line_children[idx]
	if 'link_open' == first.type and _SLASH_LINK_HREF_RE.fullmatch(str(first.attrGet('href') or '').strip()):
		depth = 1
		idx += 1
		while idx < len(line_children) and 0 < depth:
			if 'link_open' == line_children[idx].type:
				depth += 1
			elif 'link_close' == line_children[idx].type:
				depth -= 1
			idx += 1
		rest_parts = []
		for child in line_children[idx:]:
			if 'code_inline' == child.type:
				break
			if 'text' == child.type:
				rest_parts.append(child.content or '')
		m_rest = re.match('^\\s+(https?://[^\\s<>)"\\\'`]+?~(\\d+)(?=\\s|$|[.,;)\\]]))', ''.join(rest_parts))
		return ['~' + m_rest.group(2)] if m_rest else []
	if 'text' != first.type:
		return []
	parts = []
	for child in line_children[idx:]:
		if 'code_inline' == child.type:
			break
		if 'text' == child.type:
			parts.append(child.content or '')
	line_text = ''.join(parts)
	m_cmd = (_LEADING_NATIVE_CMD_RE if native_leading_upwork else _LEADING_CMD_RE).match(line_text)
	return ['~' + m_cmd.group(2)] if m_cmd else []
def _explicit_with_ids(text, job_id, *, meta=None):
	commands = _extract_leading_upwork_init_ids(text, meta=meta)
	if not commands:
		return (None, None, [])
	return (all((ident == job_id for ident in commands)), 'explicit-upwork-init', commands)
def _explicit(text, job_id, *, meta=None):
	choice, source, _ = _explicit_with_ids(text, job_id, meta=meta)
	return (choice, source)
def format_binding_diagnostic(expected_root, binding, *, expected_job_id=None):
	parts = []
	b = binding if isinstance(binding, dict) else None
	if None is b:
		parts.append('binding=none')
	else:
		if b.get('kind'):
			parts.append(f"binding={b['kind']}")
		if None is not b.get('native_step'):
			parts.append(f"native_step={b['native_step']}")
	if expected_root:
		parts.append(f'expected_root={expected_root}')
	if None is not b and 'root' in b:
		parts.append(f"observed_root={b['root'] or 'none'}")
	exp_jid = (b.get('expected_job_id') if None is not b else None) or expected_job_id
	if None is not b and b.get('observed_job_ids'):
		if exp_jid:
			parts.append(f'expected_job_id={exp_jid}')
		parts.append(f"observed_job_ids={','.join(b['observed_job_ids'])}")
	return ', '.join(parts)
def scoped_inputs(root, job_id, inputs, contexts=(), *, until=None):
	events = []
	for item in inputs:
		step, text = (item[0], item[1])
		meta = item[2] if 2 < len(item) else None
		if None is until or step <= until:
			events.append((step, 1, text, meta))
	events += [(step, 0, path, source) for step, path, source in contexts if None is until or step <= until]
	events.sort(key=lambda item: (item[0], item[1]))
	legacy = not any((0 == kind for _, kind, _, _ in events))
	selected, active, previous_root, binding, native_exact_match = ([], False, object(), None, False)
	for step, kind, value, source in events:
		if 0 == kind:
			normalized = str(canonical_path(value)) if value else None
			if normalized != previous_root:
				previous_root = normalized
				native_exact_match = _same_root(normalized, root)
				active = native_exact_match
				binding = {'kind': source, 'native_step': step, 'root': normalized}
			continue
		if job_id.startswith('text-') and native_exact_match:
			choice, cmd_source, cmd_ids = (None, None, [])
		else:
			choice, cmd_source, cmd_ids = _explicit_with_ids(value, job_id, meta=source)
		if None is not choice:
			active, legacy = (choice, False)
			if choice:
				binding = {'kind': cmd_source, 'native_step': step, 'root': str(Path(root).resolve())}
			else:
				binding = {'kind': cmd_source, 'native_step': step, 'root': str(Path(root).resolve()), 'expected_job_id': job_id, 'observed_job_ids': cmd_ids}
		elif legacy and (not active) and (not job_id.startswith('text-')) and (job_id in value):
			active = True
			binding = {'kind': 'legacy-native-job-id', 'native_step': step, 'job_id': job_id}
		if active and value.strip():
			selected.append((step, value, dict(binding)))
	r = (selected, active, binding)
	return r
