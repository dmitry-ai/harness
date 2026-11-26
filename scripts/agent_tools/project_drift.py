# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Enforce project.domain_drift invariant in check-project and finalize":
# https://github.com/dmitry-ai/harness/issues/268
from __future__ import annotations
from pathlib import Path
import json
import re
# 2026-11-26 "Extract general duplicated helpers into Df/Core and Df/Qa": https://github.com/dmitry-ai/harness/issues/378
from Df.Core.lib.json_io import df_json_dict_load
from .diagnostics import problem
from .path_registry import project_paths
from .project_rename import resolve_promotable_target_domain
_CLIENT_NAME_RE = re.compile('(?:client|author|artist|owner|customer|founder|\\u043a\\u043b\\u0438\\u0435\\u043d\\u0442|\\u0430\\u0432\\u0442\\u043e\\u0440|\\u0445\\u0443\\u0434\\u043e\\u0436\\u043d\\u0438\\u043a|\\u0432\\u043b\\u0430\\u0434\\u0435\\u043b\\u0435\\u0446|\\u0437\\u0430\\u043a\\u0430\\u0437\\u0447\\u0438\\u043a|\\u043e\\u0441\\u043d\\u043e\\u0432\\u0430\\u0442\\u0435\\u043b\\u044c)[^.]{0,40}?\\b[A-Z\\u0410-\\u042f\\u0401][a-z\\u0430-\\u044f\\u0451]{1,25}\\s+[A-Z\\u0410-\\u042f\\u0401][a-z\\u0430-\\u044f\\u0451]{1,25}\\b', re.IGNORECASE)
_NAME_UNKNOWN_RE = re.compile('#\\s*1\\.1\\s+(?:Name|\\u0418\\u043c\\u044f)\\s*\\r?\\n\\s*(?:unknown|\\u043d\\u0435\\u0438\\u0437\\u0432\\u0435\\u0441\\u0442\\u043d\\u043e)\\b', re.IGNORECASE)
_REG_SUFFIX_RE = re.compile(r'\s+-\s+U\.P\.\d{4}\.\d{2}\.\d{2}$')
# @used-by :func:`_kb_identity_mismatch_issues()`
def _established_client_identity(value: dict) -> bool:
	return any((isinstance(c, dict) and ('verified' == c.get('verification_status') or 80 <= (c.get('probability_percent') or 0)) and _CLIENT_NAME_RE.search(c.get('essence') or '') for c in value.get('identity') or ()))
# @used-by :func:`analysis_card_sync_issues()`
def _kb_identity_mismatch_issues(pp, value: dict) -> list[dict]:
	r: list[dict] = []
	if _established_client_identity(value):
		for proj_file in (pp.manual_kb_dir / 'Project.md', pp.kb_dir / 'Project.md'):
			if proj_file.is_file() and _NAME_UNKNOWN_RE.search(proj_file.read_text(encoding='utf-8')):
				rel_proj = pp.rel_to_root(proj_file)
				r.append(problem('kb.identity_mismatch', rel_proj, f'Established client identity in Analysis.json is not synced to {rel_proj} (# 1.1 Name is still unknown)', file=proj_file))
	return r
# 2026-11-26 "Extract general duplicated helpers into Df/Core and Df/Qa": https://github.com/dmitry-ai/harness/issues/378
# @used-by :func:`_registered_title_mismatches()`
# @used-by :func:`domain_drift_issues()`
# @used-by :func:`require_no_domain_drift_for_finalize()`
# @used-by :meth:`test_df_core_qa_s10.DfCoreQaS10Tests.test_harness_callers_delegate_to_new_core_and_qa_helpers()`
def _load_json_dict(path: Path) -> dict | None:
	return df_json_dict_load(path)
# @used-by :func:`domain_drift_issues()`
def _registered_title_mismatches(pp, expected_domain: str) -> list[str]:
	r: list[str] = []
	data = _load_json_dict(pp.registrations_json)
	if None is not data:
		exp_low = expected_domain.casefold()
		for plat, entry in sorted(data.items()):
			if isinstance(entry, dict) and (entry.get('complete') or 'registered' == entry.get('status')):
				pname = str(entry.get('project_name') or '').strip()
				if pname and _REG_SUFFIX_RE.sub('', pname).strip().casefold() != exp_low:
					r.append(f'{plat}:{pname}')
	return r
# @used-by :meth:`agent_tools.workflow.ProjectHealthAuditor._analysis_card_issues()`
def analysis_card_sync_issues(pp, value: dict) -> list[dict]:
	from .knowledge import sync_website_card
	r: list[dict] = []
	overview_file = pp.path('overview_md', pp.root / '.md')
	website = sync_website_card(pp.root, value, check=True)
	if website['status'] not in ('published', 'unchanged'):
		r.append(problem('project.website', pp.rel_to_root(overview_file), 'Publish the explicit evidenced client/target website selection, or null if unidentified', file=overview_file))
	r.extend(_kb_identity_mismatch_issues(pp, value))
	r.extend(domain_drift_issues(pp.root, value))
	return r
# @used-by :func:`analysis_card_sync_issues()`
# @used-by :func:`require_no_domain_drift_for_finalize()`
def domain_drift_issues(root: Path | str, analysis_value: dict) -> list[dict]:
	pp = project_paths(root, exact_root=True)
	pj = _load_json_dict(pp.project_json)
	r: list[dict] = []
	if None is not pj and isinstance(analysis_value, dict) and (not pj.get('domain_drift_exempt')):
		expected, basis_id = resolve_promotable_target_domain(analysis_value, min_probability=75)
		if None is not expected:
			folder_label = pp.root.name.split(' - ', 1)[-1].strip()
			mismatches = [f'folder "{folder_label}"'] if folder_label.casefold() != expected.casefold() else []
			mismatches.extend(_registered_title_mismatches(pp, expected))
			if mismatches:
				actual = ', '.join(mismatches)
				msg = f'Project {actual} disagrees with resolved target domain "{expected}" ({basis_id}); run harness.py rename-project "{pp.root.as_posix()}" --domain {expected} or set domain_drift_exempt in \ua616/project.json'
				r.append(problem('project.domain_drift', pp.rel_to_root(pp.project_json), msg, file=pp.project_json))
	return r
# @used-by :meth:`agent_tools.workflow.WorkflowStateEngine._finalize_stage()`
def require_no_domain_drift_for_finalize(root: Path | str) -> None:
	pp = project_paths(root, exact_root=True)
	value = _load_json_dict(pp.kb_dir / 'Analysis.json')
	if None is not value:
		issues = domain_drift_issues(pp.root, value)
		if issues:
			raise ValueError(issues[0]['message'])
	scratch_dir = pp.scratch_dir
	if scratch_dir.is_dir() and any((p.is_file() for p in scratch_dir.rglob('*'))):
		raise ValueError('Clean or consume all temporary files in \ua616/data/scratch before finalizing')
# @used-by :meth:`agent_tools.workflow.WorkflowStateEngine._apply_complete_stage()`
def require_stage_project_valid(root: Path | str, check_fn, base_msg: str) -> None:
	chk = check_fn(root)
	if not chk['valid']:
		detail = '; '.join((i['message'] for i in chk['issues'][:3] if i.get('message')))
		raise ValueError(f'{base_msg}: {detail}' if detail else base_msg)
