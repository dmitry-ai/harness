# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from urllib.parse import unquote, urlsplit
import re
# 2026-11-26 "Move repository and grounding subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/382
_DOC_HOST_PREFIXES = ('docs.', 'developer.', 'developers.', 'learn.', 'help.', 'support.', 'manual.', 'wiki.', 'devdocs.')
_DOC_HOST_SUFFIXES = ('.readthedocs.io', '.readthedocs.org')
_DOC_PATH_MARKERS = ('/docs/', '/documentation/', '/reference/', '/guide/', '/guides/', '/manual/', '/api/', '/wiki/', '/kb/', '/help/')
_FENCE_RE = re.compile(r'^\s*(`{3,}|~{3,})')
_HYP_HEAD_RE = re.compile(r'(?i)^#{2,6}\s+(?:(?:H|\u0413)(?:-[A-Za-z0-9]+)*-\d+|(?:\u0433\u0438\u043f\u043e\u0442\u0435\u0437\u0430|hypothesis)\s*\d+)\b')
_ITEM_LINE_RE = re.compile(r'(?i)^(?:[-*+]|\d+[.)])\s+(?:\*\*|__|`)*(?:(?:H|M|\u0413|\u041c)(?:-[A-Za-z0-9]+)*-\d+|(?:\u0433\u0438\u043f\u043e\u0442\u0435\u0437\u0430|hypothesis|\u0441\u043f\u043e\u0441\u043e\u0431|\u043c\u0435\u0442\u043e\u0434|method|solution|\u0432\u0430\u0440\u0438\u0430\u043d\u0442)\s*\d+)\b')
_MET_HEAD_RE = re.compile(r'(?i)^#{2,6}\s+(?:(?:M|\u041c)(?:-[A-Za-z0-9]+)*-\d+|(?:\u0441\u043f\u043e\u0441\u043e\u0431|\u043c\u0435\u0442\u043e\u0434|method|solution|\u0432\u0430\u0440\u0438\u0430\u043d\u0442)\s*\d+)\b')
_SUBHEAD_RE = re.compile(r'^(#{2,6})\s+(.+?)\s*$')
_TABLE_SEP_RE = re.compile(r'^\s*\|?\s*:?-{3,}:?\s*(?:\|\s*:?-{3,}:?\s*)+\|?\s*$|^\s*\|\s*:?-{3,}:?\s*\|\s*$')
_TOP_HEAD_RE = re.compile(r'^#\s+(\d+)\.?(?:\s+(.*))?$')
# @used-by :func:`dfh_find_markdown_table_lines()`
def _is_table_header_pair(lines: list[tuple[int, str, bool]], idx: int) -> bool:
	_, raw, fenced = lines[idx]
	_, nxt, nxt_fenced = lines[idx + 1]
	stripped = raw.strip()
	return (not fenced) and (not nxt_fenced) and ('|' in stripped) and (not stripped.startswith('>')) and bool(_TABLE_SEP_RE.match(nxt))
# @used-by :func:`dfh_parse_section_items()`
def _parse_list_items(masked: list[tuple[int, str, bool]]) -> list[tuple[str, str]]:
	items: list[tuple[str, list[str]]] = []
	for _, raw, fenced in masked:
		if not fenced and _ITEM_LINE_RE.match(raw.strip()):
			items.append((raw.strip()[:60], [raw]))
		elif items:
			items[-1][1].append(raw)
	return [(k, '\n'.join(v)) for k, v in items]
# @used-by :func:`agent_tools.statements.external_anchor_issues()`
# @used-by :meth:`Df.Harness.Grounding.ResponseAuditor.ResponseAuditor.__check_link_observations()`
# @used-by :meth:`test_df_harness_s11_wave2c_grounding.DfHarnessS11Wave2CGroundingTests.test_df_analysis_problem_tracks_scatter_banner_and_statements()`
def dfh_external_anchor_issues(label: str, href: str, norm_url: str, observed_anchors: dict[str, set[str]], response: str) -> list[str]:
	errs: list[str] = []
	frag = urlsplit(href).fragment
	anchors = observed_anchors.get(norm_url)
	if frag and (not re.fullmatch(r'L\d+(?:-L?\d+)?', frag)) and (None is not anchors):
		if frag not in anchors and unquote(frag) not in anchors and ('anchor_exception' not in response):
			errs.append(f'VERIFY-1 / LINK-2: External link [{label}]({href}) references anchor "#{frag}" which is absent from the saved observation in \ua616/KB/Evidence')
	elif (not frag) and dfh_is_documentation_url(href) and anchors and ('anchor_exception' not in response):
		errs.append(f'VERIFY-1 / LINK-2: Documentation link [{label}]({href}) omits a section #anchor despite {len(anchors)} available anchor(s) in the saved observation (cite an exact #anchor or record anchor_exception)')
	return errs
# @used-by :func:`agent_tools.statements._extract_top_sections()`
# @used-by :meth:`Df.Harness.Grounding.ScatterBannerAuditor.ScatterBannerAuditor.audit()`
def dfh_extract_top_sections(text: str) -> dict[int, tuple[str, str]]:
	sections: dict[int, tuple[str, list[str]]] = {}
	cur: int | None = None
	for _, raw, fenced in dfh_mask_fenced_lines(text):
		m = _TOP_HEAD_RE.match(raw.strip()) if not fenced else None
		if None is not m:
			cur = int(m.group(1))
			sections[cur] = ((m.group(2) or '').strip(), [])
		elif None is not cur:
			sections[cur][1].append(raw)
	return {k: (title, '\n'.join(lines)) for k, (title, lines) in sections.items()}
# @used-by :func:`agent_tools.statements.find_markdown_table_lines()`
# @used-by :func:`dfh_markdown_table_issues()`
# @used-by :meth:`Df.Harness.Issue.Linter.Linter.__check_body_blocks()`
def dfh_find_markdown_table_lines(text: str) -> list[int]:
	masked = dfh_mask_fenced_lines(text)
	hits: list[int] = []
	idx = 0
	while idx + 1 < len(masked):
		if _is_table_header_pair(masked, idx):
			hits.append(masked[idx][0])
			idx += 2
			while idx < len(masked) and (not masked[idx][2]) and ('|' in masked[idx][1]):
				idx += 1
		else:
			idx += 1
	return hits
# @used-by :func:`agent_tools.statements.is_documentation_url()`
# @used-by :func:`dfh_external_anchor_issues()`
def dfh_is_documentation_url(url: str) -> bool:
	parsed = urlsplit((url or '').strip())
	host = (parsed.hostname or '').lower()
	path = (parsed.path or '').lower()
	return host.startswith(_DOC_HOST_PREFIXES) or host.endswith(_DOC_HOST_SUFFIXES) or any((m in path for m in _DOC_PATH_MARKERS)) or (host in ('github.com', 'raw.githubusercontent.com') and path.endswith('.md'))
# @used-by :func:`agent_tools.statements.markdown_table_issues()`
# @used-by :meth:`Df.Harness.Grounding.CliCommandAuditor.CliCommandAuditor.response_turn_gate_issues()`
# @used-by :meth:`Df.Harness.Grounding.DfAnalysisValidator.DfAnalysisValidator.analysis_gate_issues()`
# @used-by :meth:`test_df_harness_s11_wave2c_grounding.DfHarnessS11Wave2CGroundingTests.test_df_analysis_problem_tracks_scatter_banner_and_statements()`
def dfh_markdown_table_issues(text: str) -> list[str]:
	return [f'DOC-4 Line {ln}: Markdown table detected; Markdown tables are forbidden by rule DOC-4 (rewrite as structured prose or a list).' for ln in dfh_find_markdown_table_lines(text)]
# @used-by :func:`agent_tools.statements._mask_fenced_lines()`
# @used-by :func:`dfh_extract_top_sections()`
# @used-by :func:`dfh_find_markdown_table_lines()`
# @used-by :func:`dfh_parse_explicit_items()`
# @used-by :func:`dfh_parse_section_items()`
# @used-by :meth:`Df.Harness.Grounding.DfAnalysisValidator.DfAnalysisValidator.__requests_invoke_df_analysis()`
# @used-by :meth:`Df.Harness.Grounding.DfAnalysisValidator.DfAnalysisValidator.validate()`
# @used-by :meth:`Df.Harness.Grounding.ScatterBannerAuditor.ScatterBannerAuditor.__parse_standalone()`
def dfh_mask_fenced_lines(text: str) -> list[tuple[int, str, bool]]:
	out: list[tuple[int, str, bool]] = []
	in_fence, marker, in_fm = (False, '', False)
	for idx, raw in enumerate((text or '').splitlines(), 1):
		stripped = raw.strip()
		if in_fm or (1 == idx and '---' == stripped):
			in_fm = not (in_fm and '---' == stripped)
			out.append((idx, raw, True))
		else:
			m = _FENCE_RE.match(stripped)
			if None is not m:
				in_fence, marker = (False, '') if in_fence and stripped.startswith(marker * 3) else ((True, m.group(1)[0]) if not in_fence else (in_fence, marker))
				out.append((idx, raw, True))
			else:
				out.append((idx, raw, in_fence))
	return out
# @used-by :func:`agent_tools.statements._parse_explicit_items()`
# @used-by :meth:`Df.Harness.Grounding.DfAnalysisValidator.DfAnalysisValidator.__validate_general()`
# @used-by :meth:`Df.Harness.Grounding.DfAnalysisValidator.DfAnalysisValidator.validate()`
# @used-by :meth:`Df.Harness.Grounding.ScatterBannerAuditor.ScatterBannerAuditor.__collect_candidates()`
def dfh_parse_explicit_items(text: str) -> tuple[list[tuple[str, str]], list[tuple[str, str]]]:
	hyps: list[tuple[str, list[str]]] = []
	mets: list[tuple[str, list[str]]] = []
	cur: list[str] | None = None
	for _, raw, fenced in dfh_mask_fenced_lines(text):
		stripped = raw.strip()
		if not fenced and _HYP_HEAD_RE.match(stripped):
			hyps.append((stripped.lstrip('#').strip(), [raw]))
			cur = hyps[-1][1]
		elif not fenced and _MET_HEAD_RE.match(stripped):
			mets.append((stripped.lstrip('#').strip(), [raw]))
			cur = mets[-1][1]
		elif not fenced and re.match(r'^#{1,6}\s+', stripped):
			cur = None
		elif None is not cur:
			cur.append(raw)
	return ([(k, '\n'.join(v)) for k, v in hyps], [(k, '\n'.join(v)) for k, v in mets])
# @used-by :func:`agent_tools.statements._parse_section_items()`
# @used-by :meth:`Df.Harness.Grounding.DfAnalysisValidator.DfAnalysisValidator.__check_problem_sections()`
# @used-by :meth:`Df.Harness.Grounding.ScatterBannerAuditor.ScatterBannerAuditor.__collect_candidates()`
# @used-by :meth:`test_df_harness_s11_wave2c_cov_grounding.DfHarnessS11Wave2CCovGroundingTests.test_df_analysis_validator_general_and_section_lists()`
def dfh_parse_section_items(body: str) -> list[tuple[str, str]]:
	masked = dfh_mask_fenced_lines(body)
	levels = [len(m.group(1)) for _, raw, fenced in masked if (not fenced) and (m := _SUBHEAD_RE.match(raw.strip()))]
	if not levels:
		r = _parse_list_items(masked)
	else:
		top_lvl = min(levels)
		items: list[tuple[str, list[str]]] = []
		for _, raw, fenced in masked:
			m = _SUBHEAD_RE.match(raw.strip()) if not fenced else None
			if None is not m and len(m.group(1)) == top_lvl:
				items.append((m.group(2).strip(), [raw]))
			elif items:
				items[-1][1].append(raw)
		r = [(k, '\n'.join(v)) for k, v in items]
	return r
