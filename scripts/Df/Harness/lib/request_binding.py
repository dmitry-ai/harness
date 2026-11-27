# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from pathlib import Path
from Df.Harness.lib.path_resolve import dfh_load_registry, dfh_project_paths
from Df.Harness.lib.path_schema import dfh_canonicalize_root_dir
import hashlib
import json
import re
# 2026-11-26 "Move turn lifecycle subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/383
_CLAUDE_CMD_RE = re.compile('^\\s*(?:<command-message>[^<]*</command-message>\\s*)?<command-name>\\s*/?upwork-init\\s*</command-name>\\s*<command-args>([^<]*)</command-args>', re.I | re.S)
_LEADING_CMD_RE = re.compile('^\\s*(?:/|\\$)upwork-init\\s+(https?://[^\\s<>)"\\\'`]+?~(\\d+)(?=\\s|$|[.,;)\\]]))', re.I)
_LEADING_NATIVE_CMD_RE = re.compile('^\\s*(?:(?:/|\\$)?upwork-init\\s+)?(https?://[^\\s<>)"\\\'`]+?~(\\d+)(?=\\s|$|[.,;)\\]]))', re.I)
_SLASH_LINK_HREF_RE = re.compile('^slashcommand;/?upwork-init$', re.I)
_UPWORK_JOB_URL_RE = re.compile('https?://[^\\s<>)"\\\'`]+?~(\\d+)(?=\\s|$|[.,;)\\]])')
_USER_REQUEST_WRAPPER_RE = re.compile('^\\s*<USER_REQUEST>\\r?\\n([\\s\\S]*?)\\r?\\n</USER_REQUEST>(?:\\s*(?:<(?:ADDITIONAL_METADATA|USER_SETTINGS_CHANGE|SYSTEM_MESSAGE)>[\\s\\S]*)?)?\\s*$')
# @used-by :func:`dfh_scoped_inputs()`
def _apply_input_event(root, job_id: str, step: int, value: str, source, state: dict) -> None:
	if job_id.startswith('text-') and state['native_exact_match']:
		choice, cmd_source, cmd_ids = (None, None, [])
	else:
		choice, cmd_source, cmd_ids = dfh_explicit_with_ids(value, job_id, meta=source)
	if None is not choice:
		state['active'], state['legacy'] = (choice, False)
		base = {'kind': cmd_source, 'native_step': step, 'root': str(Path(root).resolve())}
		state['binding'] = base if choice else {**base, 'expected_job_id': job_id, 'observed_job_ids': cmd_ids}
	elif state['legacy'] and (not state['active']) and (not job_id.startswith('text-')) and (job_id in value):
		state['active'] = True
		state['binding'] = {'kind': 'legacy-native-job-id', 'native_step': step, 'job_id': job_id}
	if state['active'] and value.strip():
		state['selected'].append((step, value, dict(state['binding'])))
# @used-by :func:`dfh_format_binding_diagnostic()`
def _binding_parts(b: dict | None) -> list[str]:
	if None is b:
		r = ['binding=none']
	else:
		r = []
		if b.get('kind'):
			r.append(f"binding={b['kind']}")
		if None is not b.get('native_step'):
			r.append(f"native_step={b['native_step']}")
	return r
# @used-by :func:`dfh_scoped_inputs()`
def _build_scope_events(inputs, contexts, until) -> list:
	events = []
	for item in inputs:
		step, text = (item[0], item[1])
		meta = item[2] if 2 < len(item) else None
		if None is until or step <= until:
			events.append((step, 1, text, meta))
	events += [(step, 0, path, source) for step, path, source in contexts if None is until or step <= until]
	events.sort(key=lambda item: (item[0], item[1]))
	return events
# @used-by :func:`dfh_same_root()`
def _canonical_root(value) -> str:
	return str(dfh_canonical_path(value)).replace('\\', '/').rstrip('/').lower()
# @used-by :func:`dfh_extract_leading_upwork_init_ids()`
def _extract_from_paragraph(cleaned: str, native_upwork: bool) -> list[str]:
	children = _first_paragraph_line_children(cleaned)
	idx = 0
	while idx < len(children) and 'text' == children[idx].type and (not children[idx].content.strip()):
		idx += 1
	if idx >= len(children):
		r: list[str] = []
	elif 'link_open' == children[idx].type and _SLASH_LINK_HREF_RE.fullmatch(str(children[idx].attrGet('href') or '').strip()):
		r = _slash_link_upwork_ids(children, idx)
	elif 'text' == children[idx].type:
		r = _plain_text_upwork_ids(children, idx, native_upwork)
	else:
		r = []
	return r
# @used-by :func:`_extract_from_paragraph()`
def _first_paragraph_line_children(text: str) -> list:
	from agent_tools.source_grounding import markdown_parser
	tokens = markdown_parser().parse(text)
	r: list = []
	if tokens and 'paragraph_open' == tokens[0].type and 2 <= len(tokens) and 'inline' == tokens[1].type:
		for child in tokens[1].children or ():
			if child.type in ('softbreak', 'hardbreak'):
				break
			r.append(child)
	return r
# @used-by :func:`dfh_extract_leading_upwork_init_ids()`
def _has_leading_native_upwork(meta) -> tuple[bool, bool]:
	skip, native_upwork = (False, False)
	if isinstance(meta, dict):
		slash_cmds = meta.get('slash_commands') or []
		leading_names = [str(item.get('name') or '').strip().lower() for item in slash_cmds if isinstance(item, dict) and item.get('leading')]
		if leading_names:
			if 'upwork-init' not in leading_names:
				skip = True
			else:
				native_upwork = True
	return (skip, native_upwork)
# @used-by :func:`_extract_from_paragraph()`
def _plain_text_upwork_ids(line_children: list, idx: int, native_leading_upwork: bool) -> list[str]:
	parts = []
	for child in line_children[idx:]:
		if 'code_inline' == child.type:
			break
		if 'text' == child.type:
			parts.append(child.content or '')
	m_cmd = (_LEADING_NATIVE_CMD_RE if native_leading_upwork else _LEADING_CMD_RE).match(''.join(parts))
	return ['~' + m_cmd.group(2)] if m_cmd else []
# @used-by :func:`_extract_from_paragraph()`
def _slash_link_upwork_ids(line_children: list, idx: int) -> list[str]:
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
# @used-by :func:`dfh_extract_leading_upwork_init_ids()`
def _strip_user_request_wrapper(text) -> str:
	r = ''
	if isinstance(text, str) and text.strip():
		m_wrap = _USER_REQUEST_WRAPPER_RE.match(text)
		r = m_wrap.group(1) if m_wrap else text
	return r
# @used-by :func:`dfh_native_project_id()`
def _validate_text_project_marker(pp, root: Path) -> str:
	marker = pp.text_project_json
	if not marker.is_file():
		raise ValueError('No native project identity; initialize an explicit text workspace first')
	value = json.loads(marker.read_text(encoding='utf-8-sig'))
	saved_root = value.get('project_root') if isinstance(value, dict) else None
	valid_ids = {dfh_text_project_id(root)} | ({dfh_raw_text_project_id(saved_root)} if isinstance(saved_root, str) and saved_root.strip() and Path(saved_root).is_absolute() else set())
	if not isinstance(value, dict) or int is not type(value.get('schema_version')) or 1 != value['schema_version'] or 'client_text_workspace' != value.get('kind') or (not dfh_same_root(saved_root, root)) or value.get('id') not in valid_ids:
		raise ValueError('Text workspace marker has the wrong root, kind, schema or internal ID')
	return value['id']
# @used-by :func:`Df.Harness.lib.ag_inputs._resolve_ws_context_entry()`
# @used-by :func:`Df.Harness.lib.ag_inputs.dfh_project_roots()`
# @used-by :func:`_canonical_root()`
# @used-by :func:`dfh_scoped_inputs()`
# @used-by :func:`dfh_text_project_id()`
def dfh_canonical_path(value) -> Path:
	return dfh_canonicalize_root_dir(value, dfh_load_registry())
# @used-by :func:`dfh_review_project_id()`
# @used-by :meth:`Df.Harness.Platform.Antigravity.TurnScanner.TurnScanner.__load_context()`
# @used-by :meth:`Df.Harness.Platform.Codex.TurnScanner.TurnScanner.__load_context()`
# @used-by :meth:`test_arch_review_cli.ArchReviewCliTests.test_review_project_id_and_fields_support_bare_code_workspace_for_arch_only()`
# @used-by :meth:`test_continuation_binding.AntigravityContinuationTests.test_quoted_and_non_leading_upwork_init_never_override_or_poison_and_support_cross_platform_commands()`
def dfh_completion_project_id(root) -> str:
	root_p = Path(root).resolve()
	if not root_p.is_dir():
		raise ValueError('Completion needs an exact existing project directory')
	pp = dfh_project_paths(root_p, exact_root=True)
	return dfh_native_project_id(pp.root) if pp.project_json.exists() or pp.text_project_json.exists() else dfh_text_project_id(pp.root)
# @used-by :func:`Df.Harness.lib.completion_recovery._is_handoff_candidate()`
# @used-by :meth:`test_df_harness_s11_wave2d_platform_cov.DfHarnessS11Wave2dPlatformCovTests.test_trace_effects_review_and_clarifications()`
def dfh_explicit(text, job_id: str, *, meta=None):
	choice, source, _ = dfh_explicit_with_ids(text, job_id, meta=meta)
	return (choice, source)
# @used-by :func:`_apply_input_event()`
# @used-by :func:`dfh_explicit()`
def dfh_explicit_with_ids(text, job_id: str, *, meta=None):
	commands = dfh_extract_leading_upwork_init_ids(text, meta=meta)
	return (None, None, []) if not commands else (all((ident == job_id for ident in commands)), 'explicit-upwork-init', commands)
# @used-by :func:`Df.Harness.lib.hook_stop_ops.dfh_handoff_matches_user_step()`
# @used-by :func:`dfh_explicit_with_ids()`
# @used-by :meth:`test_df_harness_s11_wave2d.DfHarnessS11Wave2DTests.test_platform_subsystem_classes()`
# @used-by :meth:`test_native_review_binding_m4.NativeReviewBindingM4Tests.test_extract_leading_upwork_init_strips_outer_user_request_wrapper()`
def dfh_extract_leading_upwork_init_ids(text, *, meta=None) -> list[str]:
	cleaned = _strip_user_request_wrapper(text)
	if not cleaned.strip():
		r: list[str] = []
	else:
		m_claude = _CLAUDE_CMD_RE.match(cleaned)
		if m_claude:
			r = ['~' + ident for ident in _UPWORK_JOB_URL_RE.findall(m_claude.group(1))]
		else:
			skip, native_upwork = _has_leading_native_upwork(meta)
			r = [] if skip else _extract_from_paragraph(cleaned, native_upwork)
	return r
# @used-by :func:`Df.Harness.lib.ag_inputs.dfh_require_current_binding()`
# @used-by :func:`Df.Harness.lib.codex_trace.dfh_codex_require_current_binding()`
# @used-by :func:`Df.Harness.lib.completion_core.dfh_active_turn()`
# @used-by :func:`Df.Harness.lib.hook_pre_invocation_ops._diagnose_no_active_turn()`
def dfh_format_binding_diagnostic(expected_root, binding, *, expected_job_id=None) -> str:
	b = binding if isinstance(binding, dict) else None
	parts = _binding_parts(b)
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
# @used-by :func:`Df.Harness.lib.trace_review.dfh_build_native_review_proof()`
# @used-by :meth:`Df.Harness.Text.ReviewPackageReader.ReviewPackageReader.read()`
# @used-by :meth:`Df.Harness.Text.ReviewPreparer.ReviewPreparer.__build_payload()`
# @used-by :meth:`test_arch_review_cli.ArchReviewCliTests.test_review_project_id_and_fields_support_bare_code_workspace_for_arch_only()`
def dfh_native_project_fields(root, *, role: str='AA') -> dict:
	identifier = dfh_review_project_id(root, role=role)
	pp = dfh_project_paths(root, exact_root=True)
	kind = 'upwork_job' if pp.project_json.is_file() else ('client_text_workspace' if pp.text_project_json.is_file() else 'code_workspace')
	return {'project_id': identifier, 'project_kind': kind, 'job_id': identifier if 'upwork_job' == kind else None}
# @used-by :func:`Df.Harness.lib.ag_inputs.dfh_request_scope()`
# @used-by :func:`Df.Harness.lib.codex_trace.dfh_codex_request_scope()`
# @used-by :func:`Df.Harness.lib.completion_commands._try_launcher_handoff()`
# @used-by :func:`dfh_completion_project_id()`
# @used-by :func:`dfh_review_project_id()`
# @used-by :meth:`test_path_registry.PathRegistryTests.test_cross_root_relocation_workflow_completion_review_and_antigravity_registration()`
# @used-by :meth:`test_text_native_binding.TextNativeBindingTests.test_existing_real_job_identity_wins_and_invalid_job_file_cannot_fall_back()`
# @used-by :meth:`test_text_native_binding.TextNativeBindingTests.test_internal_identity_is_explicit_and_validated_without_creating_upwork_state()`
def dfh_native_project_id(root) -> str:
	pp = dfh_project_paths(root, exact_root=True)
	job = pp.project_json
	if job.is_file():
		project = json.loads(job.read_text(encoding='utf-8-sig'))
		identifier = project.get('job_id') if isinstance(project, dict) else None
		if not isinstance(identifier, str) or (not identifier.strip()) or identifier.startswith('text-'):
			raise ValueError('Existing project.json needs its real Upwork job_id')
		r = identifier
	else:
		r = _validate_text_project_marker(pp, pp.root)
	return r
# @used-by :func:`_validate_text_project_marker()`
# @used-by :func:`dfh_text_project_id()`
def dfh_raw_text_project_id(path_val) -> str:
	return 'text-' + hashlib.sha256(str(Path(path_val).resolve()).encode('utf-8')).hexdigest()
# @used-by :func:`Df.Harness.lib.ag_inputs.dfh_require_current_binding()`
# @used-by :func:`Df.Harness.lib.codex_trace.dfh_codex_require_current_binding()`
# @used-by :func:`dfh_native_project_fields()`
# @used-by :meth:`test_arch_review_cli.ArchReviewCliTests.test_review_project_id_and_fields_support_bare_code_workspace_for_arch_only()`
def dfh_review_project_id(root, *, role: str='AA') -> str:
	return dfh_completion_project_id(root) if 'ARCH' == role else dfh_native_project_id(root)
# @used-by :func:`_validate_text_project_marker()`
# @used-by :func:`dfh_scoped_inputs()`
# @used-by :meth:`test_continuation_binding.AntigravityContinuationTests.test_git_folder_project_id_fallback_and_relocated_root_canonicalization()`
def dfh_same_root(value, root) -> bool:
	if not isinstance(value, str) or (not value.strip()) or (not Path(value).is_absolute()):
		r = False
	else:
		r = _canonical_root(value) == _canonical_root(root)
	return r
# @used-by :func:`Df.Harness.lib.ag_inputs.dfh_request_scope()`
# @used-by :func:`Df.Harness.lib.codex_trace.dfh_codex_request_scope()`
# @used-by :meth:`test_continuation_binding.AntigravityContinuationTests.test_quoted_and_non_leading_upwork_init_never_override_or_poison_and_support_cross_platform_commands()`
# @used-by :meth:`test_native_review_binding_m4.NativeReviewBindingM4Tests.test_extract_leading_upwork_init_strips_outer_user_request_wrapper()`
# @used-by :meth:`test_text_native_binding.TextNativeBindingTests.test_internal_id_or_text_root_never_substitutes_for_actual_cwd()`
def dfh_scoped_inputs(root, job_id: str, inputs, contexts=(), *, until=None):
	events = _build_scope_events(inputs, contexts, until)
	state = {'selected': [], 'active': False, 'legacy': not any((0 == kind for _, kind, _, _ in events)), 'previous_root': object(), 'binding': None, 'native_exact_match': False}
	for step, kind, value, source in events:
		if 0 == kind:
			normalized = str(dfh_canonical_path(value)) if value else None
			if normalized != state['previous_root']:
				state['previous_root'] = normalized
				state['native_exact_match'] = dfh_same_root(normalized, root)
				state['active'] = state['native_exact_match']
				state['binding'] = {'kind': source, 'native_step': step, 'root': normalized}
		else:
			_apply_input_event(root, job_id, step, value, source, state)
	return (state['selected'], state['active'], state['binding'])
# @used-by :func:`_validate_text_project_marker()`
# @used-by :func:`dfh_completion_project_id()`
# @used-by :func:`test_arch_review_cli._init_text_workspace()`
# @used-by :meth:`Df.Harness.Text.Workspace.Workspace.__ensure_workspace_identity()`
# @used-by :meth:`test_text_native_binding.TextNativeBindingTests.setUp()`
def dfh_text_project_id(root) -> str:
	return dfh_raw_text_project_id(dfh_canonical_path(root))
