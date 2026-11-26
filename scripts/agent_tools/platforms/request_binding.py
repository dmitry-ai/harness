# 2026-10-16 Dmitrii Fediuk https://github.com/dmitrii-fediuk
import hashlib
import json
from pathlib import Path
import re
# 2026-11-19
# "Wire project path overlays across Harness subsystems with paths CLI and regression tests":
# https://github.com/dmitry-ai/harness/issues/96
from ..path_registry import canonicalize_root_dir, project_paths, relocated_roots
# 2026-11-22
# "Support V2 `𝐒`/`𝐖` software subtrees and cross-root project relocations in Harness":
# https://github.com/dmitry-ai/harness/issues/113
# @used-by :func:`native_project_id()`
# @used-by :func:`text_project_id()`
def _raw_text_project_id(path_val):
	return 'text-' + hashlib.sha256(str(Path(path_val).resolve()).encode('utf-8')).hexdigest()
# 2026-10-20
# "Implement /df-article and /df-proposal client-text skills, AI-slop linter, scoped baseline diffs, and semantic § rendering":
# https://github.com/dmitry-ai/harness/issues/13
# @used-by :func:`completion_project_id()`
# @used-by :func:`native_project_id()`
# @used-by :func:`test_arch_review_cli._init_text_workspace()`
# @used-by :meth:`agent_tools.text_workflow.ClientTextWorkspace.begin()`
# @used-by :meth:`test_text_native_binding.TextNativeBindingTests.setUp()`
def text_project_id(root):
	return _raw_text_project_id(canonical_path(root))
# 2026-10-20
# "Implement /df-article and /df-proposal client-text skills, AI-slop linter, scoped baseline diffs, and semantic § rendering":
# https://github.com/dmitry-ai/harness/issues/13
# @used-by :func:`agent_tools.completion.begin()`
# @used-by :func:`agent_tools.platforms.antigravity._request_scope()`
# @used-by :func:`agent_tools.platforms.antigravity.require_current_binding()`
# @used-by :func:`agent_tools.platforms.codex._request_scope()`
# @used-by :func:`agent_tools.platforms.codex.require_current_binding()`
# @used-by :func:`completion_project_id()`
# @used-by :func:`native_project_fields()`
# @used-by :meth:`test_path_registry.PathRegistryTests.test_cross_root_relocation_workflow_completion_review_and_antigravity_registration()`
# @used-by :meth:`test_text_native_binding.TextNativeBindingTests.test_existing_real_job_identity_wins_and_invalid_job_file_cannot_fall_back()`
# @used-by :meth:`test_text_native_binding.TextNativeBindingTests.test_internal_identity_is_explicit_and_validated_without_creating_upwork_state()`
def native_project_id(root):
	# 2026-11-19
	# "Wire project path overlays across Harness subsystems with paths CLI and regression tests":
	# https://github.com/dmitry-ai/harness/issues/96
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
		# 2026-11-22
		# "Support V2 `𝐒`/`𝐖` software subtrees and cross-root project relocations in Harness":
		# https://github.com/dmitry-ai/harness/issues/113
		saved_root = value.get('project_root') if isinstance(value, dict) else None
		valid_ids = {text_project_id(root)} | ({_raw_text_project_id(saved_root)} if isinstance(saved_root, str) and saved_root.strip() and Path(saved_root).is_absolute() else set())
		if not isinstance(value, dict) or type(value.get('schema_version')) is not int or 1 != value['schema_version'] or ('client_text_workspace' != value.get('kind')) or (not _same_root(saved_root, root)) or (value.get('id') not in valid_ids):
			raise ValueError('Text workspace marker has the wrong root, kind, schema or internal ID')
		r = value['id']
	return r
# 2026-10-20
# "Implement /df-article and /df-proposal client-text skills, AI-slop linter, scoped baseline diffs, and semantic § rendering":
# https://github.com/dmitry-ai/harness/issues/13
# @used-by :func:`agent_tools.platforms.trace_common.build_native_review_proof()`
# @used-by :func:`agent_tools.text_review.prepare()`
# @used-by :func:`agent_tools.text_review.read_package()`
def native_project_fields(root):
	identifier = native_project_id(root)
	is_text = identifier.startswith('text-')
	r = {'project_id': identifier, 'project_kind': 'client_text_workspace' if is_text else 'upwork_job', 'job_id': None if is_text else identifier}
	return r
# 2026-10-23
# "Implement turn-completion contract, journal watcher, primary source admission, and Codex root AGENTS.md loader":
# https://github.com/dmitry-ai/harness/issues/16
# @used-by :meth:`agent_tools.platforms.antigravity.AntigravityTurnScanner._load_context()`
# @used-by :meth:`agent_tools.platforms.codex.CodexTurnScanner._load_context()`
# @used-by :meth:`test_continuation_binding.AntigravityContinuationTests.test_quoted_and_non_leading_upwork_init_never_override_or_poison_and_support_cross_platform_commands()`
def completion_project_id(root):
	root_p = Path(root).resolve()
	if not root_p.is_dir():
		raise ValueError('Completion needs an exact existing project directory')
	# 2026-11-19
	# "Wire project path overlays across Harness subsystems with paths CLI and regression tests":
	# https://github.com/dmitry-ai/harness/issues/96
	pp = project_paths(root_p, exact_root=True)
	if pp.project_json.exists() or pp.text_project_json.exists():
		r = native_project_id(pp.root)
	else:
		r = text_project_id(pp.root)
	return r
# 2026-10-31
# "Canonicalize relocated Codex, Antigravity, and Harness project roots and support v2Migrated gitFolder project resources":
# https://github.com/dmitry-ai/harness/issues/29
# 2026-11-19
# "Wire project path overlays across Harness subsystems with paths CLI and regression tests":
# https://github.com/dmitry-ai/harness/issues/96
_RELOCATED_ROOTS = relocated_roots()
# @used-by :func:`_canonical_root()`
# @used-by :func:`agent_tools.platforms.antigravity._project_roots()`
# @used-by :func:`agent_tools.platforms.antigravity._workspace_context()`
# @used-by :func:`scoped_inputs()`
# @used-by :func:`text_project_id()`
def canonical_path(value):
	return canonicalize_root_dir(value)
# 2026-10-31
# "Reorganize AI into universal harness repository, translate rules and documentation to English, format per P.md, and enforce issue-driven Git workflow":
# https://github.com/dmitry-ai/harness/issues/26
# @used-by :func:`_same_root()`
def _canonical_root(value):
	r = str(canonical_path(value)).replace('\\', '/').rstrip('/').lower()
	return r
# 2026-10-16
# "Unify Antigravity and OpenAI Codex adapters with build-native projections, parent-driven model selection, and cross-system continuation":
# https://github.com/dmitry-ai/harness/issues/6
# @used-by :func:`native_project_id()`
# @used-by :func:`scoped_inputs()`
# @used-by :meth:`test_continuation_binding.AntigravityContinuationTests.test_git_folder_project_id_fallback_and_relocated_root_canonicalization()`
def _same_root(value, root):
	if not isinstance(value, str) or not value.strip() or (not Path(value).is_absolute()):
		r = False
	else:
		r = _canonical_root(value) == _canonical_root(root)
	return r
# 2026-11-23
# "Use native workspace priority and AST command parsing in request binding":
# https://github.com/dmitry-ai/harness/issues/129
_CLAUDE_CMD_RE = re.compile('^\\s*(?:<command-message>[^<]*</command-message>\\s*)?<command-name>\\s*/?upwork-init\\s*</command-name>\\s*<command-args>([^<]*)</command-args>', re.I | re.S)
_UPWORK_JOB_URL_RE = re.compile('https?://[^\\s<>)"\\\'`]+?~(\\d+)(?=\\s|$|[.,;)\\]])')
_LEADING_CMD_RE = re.compile('^\\s*(?:/|\\$)upwork-init\\s+(https?://[^\\s<>)"\\\'`]+?~(\\d+)(?=\\s|$|[.,;)\\]]))', re.I)
_LEADING_NATIVE_CMD_RE = re.compile('^\\s*(?:(?:/|\\$)?upwork-init\\s+)?(https?://[^\\s<>)"\\\'`]+?~(\\d+)(?=\\s|$|[.,;)\\]]))', re.I)
_SLASH_LINK_HREF_RE = re.compile('^slashcommand;/?upwork-init$', re.I)
# 2026-11-24
# "Use canonical native inputs and strip USER_REQUEST in native_review_proof":
# https://github.com/dmitry-ai/harness/issues/210
_USER_REQUEST_WRAPPER_RE = re.compile('^\\s*<USER_REQUEST>\\r?\\n([\\s\\S]*?)\\r?\\n</USER_REQUEST>(?:\\s*(?:<(?:ADDITIONAL_METADATA|USER_SETTINGS_CHANGE|SYSTEM_MESSAGE)>[\\s\\S]*)?)?\\s*$')
# 2026-11-24
# "Use canonical native inputs and strip USER_REQUEST in native_review_proof":
# https://github.com/dmitry-ai/harness/issues/210
# @used-by :func:`_extract_leading_upwork_init_ids()`
def _slash_link_upwork_ids(line_children, idx):
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
# 2026-11-24
# "Use canonical native inputs and strip USER_REQUEST in native_review_proof":
# https://github.com/dmitry-ai/harness/issues/210
# @used-by :func:`_extract_leading_upwork_init_ids()`
def _strip_user_request_wrapper(text):
	r = ''
	if isinstance(text, str) and text.strip():
		m_wrap = _USER_REQUEST_WRAPPER_RE.match(text)
		r = m_wrap.group(1) if m_wrap else text
	return r
# 2026-11-23
# "Use native workspace priority and AST command parsing in request binding":
# https://github.com/dmitry-ai/harness/issues/129
# 2026-11-24
# "Use canonical native inputs and strip USER_REQUEST in native_review_proof":
# https://github.com/dmitry-ai/harness/issues/210
# @used-by :func:`_explicit_with_ids()`
# @used-by :func:`agent_tools.stop_hook_guard.handoff_matches_user_step()`
# @used-by :meth:`test_native_review_binding_m4.NativeReviewBindingM4Tests.test_extract_leading_upwork_init_strips_outer_user_request_wrapper()`
def _extract_leading_upwork_init_ids(text, *, meta=None):
	text = _strip_user_request_wrapper(text)
	if not text.strip():
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
		return _slash_link_upwork_ids(line_children, idx)
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
# 2026-11-23
# "Use native workspace priority and AST command parsing in request binding":
# https://github.com/dmitry-ai/harness/issues/129
# @used-by :func:`_explicit()`
# @used-by :func:`scoped_inputs()`
def _explicit_with_ids(text, job_id, *, meta=None):
	commands = _extract_leading_upwork_init_ids(text, meta=meta)
	if not commands:
		return (None, None, [])
	return (all((ident == job_id for ident in commands)), 'explicit-upwork-init', commands)
# 2026-11-21
# "Remove text-based explicit-project-root override from request binding":
# https://github.com/dmitry-ai/harness/issues/112
# 2026-11-23
# "Use native workspace priority and AST command parsing in request binding":
# https://github.com/dmitry-ai/harness/issues/129
# @used-by :func:`agent_tools.completion.handoff_launcher_turn()`
def _explicit(text, job_id, *, meta=None):
	choice, source, _ = _explicit_with_ids(text, job_id, meta=meta)
	return (choice, source)
# 2026-11-23
# "Use native workspace priority and AST command parsing in request binding":
# https://github.com/dmitry-ai/harness/issues/129
# @used-by :func:`agent_tools.completion._active()`
# @used-by :func:`agent_tools.platforms.antigravity.require_current_binding()`
# @used-by :func:`agent_tools.platforms.codex.require_current_binding()`
# @used-by :func:`check_pre_invocation._binding_violation_message()`
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
# 2026-10-16
# "Unify Antigravity and OpenAI Codex adapters with build-native projections, parent-driven model selection, and cross-system continuation":
# https://github.com/dmitry-ai/harness/issues/6
# @used-by :func:`agent_tools.platforms.antigravity._request_scope()`
# @used-by :func:`agent_tools.platforms.codex._request_scope()`
# @used-by :meth:`test_continuation_binding.AntigravityContinuationTests.test_quoted_and_non_leading_upwork_init_never_override_or_poison_and_support_cross_platform_commands()`
# @used-by :meth:`test_native_review_binding_m4.NativeReviewBindingM4Tests.test_extract_leading_upwork_init_strips_outer_user_request_wrapper()`
# @used-by :meth:`test_text_native_binding.TextNativeBindingTests.test_internal_id_or_text_root_never_substitutes_for_actual_cwd()`
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
		# 2026-11-23
		# "Use native workspace priority and AST command parsing in request binding":
		# https://github.com/dmitry-ai/harness/issues/129
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
