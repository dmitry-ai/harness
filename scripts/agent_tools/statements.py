# 2026-11-24 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Add FILE-6 warning banner rule for out-of-workspace file-scattering recommendations":
# https://github.com/dmitry-ai/harness/issues/200
# 2026-11-24 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Enforce Markdown table ban and /df-analysis structural validation across response gates":
# https://github.com/dmitry-ai/harness/issues/181
# 2026-10-11 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Extract self-contained .agents toolkit, deterministic validation CLI, and rule architecture from wayse.pt":
# https://github.com/dmitry-ai/harness/issues/2
# 2026-10-31 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Reorganize AI into universal harness repository, translate rules and documentation to English, format per P.md, and enforce issue-driven Git workflow":
# https://github.com/dmitry-ai/harness/issues/26
from __future__ import annotations
from pathlib import Path
from urllib.parse import unquote, urlsplit
import json
import re
_AGAINST_RE = re.compile(r'(?i)(?:доводы\s+против|аргументы\s+против|(?:^|[\s(*_-])против\s*[:—–-]|arguments?\s+against|counterevidence|cons\s*[:—–-])')
_CMD_RE = re.compile(r'(?i)(?:^|[\s(\[])(?:/df-analysis|\$df-analysis|\[df-analysis\]\(slashCommand;df-analysis\))(?=$|[\s.,;:!?)\]])')
_DOC_HOST_PREFIXES = ('docs.', 'developer.', 'developers.', 'learn.', 'help.', 'support.', 'manual.', 'wiki.', 'devdocs.')
_DOC_HOST_SUFFIXES = ('.readthedocs.io', '.readthedocs.org')
_DOC_PATH_MARKERS = ('/docs/', '/documentation/', '/reference/', '/guide/', '/guides/', '/manual/', '/api/', '/wiki/', '/kb/', '/help/')
_FENCE_RE = re.compile(r'^\s*(`{3,}|~{3,})')
_FOR_RE = re.compile(r'(?i)(?:доводы\s+за|аргументы\s+за|(?:^|[\s(*_-])за\s*[:—–-]|arguments?\s+for|evidence\s+for|pros\s*[:—–-])')
_GH_ISSUE_URL_RE = re.compile(r'^https://github\.com/[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+/issues/\d+$')
_HYP_HEAD_RE = re.compile(r'(?i)^#{2,6}\s+(?:(?:H|Г)(?:-[A-Za-z0-9]+)*-\d+|(?:гипотеза|hypothesis)\s*\d+)\b')
_ITEM_LINE_RE = re.compile(r'(?i)^(?:[-*+]|\d+[.)])\s+(?:\*\*|__|`)*(?:(?:H|M|Г|М)(?:-[A-Za-z0-9]+)*-\d+|(?:гипотеза|hypothesis|способ|метод|method|solution|вариант)\s*\d+)\b')
_JSON_FENCE_RE = re.compile(r'```json[ \t]*\r?\n([\s\S]*?)\r?\n```')
_LINK_RE = re.compile(r'\[[^\]]+\]\([^)]+\)|https?://\S+|file://\S+')
_MET_HEAD_RE = re.compile(r'(?i)^#{2,6}\s+(?:(?:M|М)(?:-[A-Za-z0-9]+)*-\d+|(?:способ|метод|method|solution|вариант)\s*\d+)\b')
_PCT_RE = re.compile(r'\b\d+(?:[.,]\d+)?\s*%')
_PROB_HEAD_RE = re.compile(r'(?i)(?:проблем|problem|defect|сбо|ошибк|bug|failure|мета-?данн|metadata)')
_SUBHEAD_RE = re.compile(r'^(#{2,6})\s+(.+?)\s*$')
_TABLE_SEP_RE = re.compile(r'^\s*\|?\s*:?-{3,}:?\s*(?:\|\s*:?-{3,}:?\s*)+\|?\s*$|^\s*\|\s*:?-{3,}:?\s*\|\s*$')
_TOP_HEAD_RE = re.compile(r'^#\s+(\d+)\.?(?:\s+(.*))?$')
_VERBATIM_RE = re.compile(r'```|^\s*>\s*\S|«[^»]{4,}»|"[^"\n]{4,}"|`[^`\n]{3,}`', re.M)
def _check_item_fields(label: str, body: str, *, require_link: bool, kind: str) -> list[str]:
	errs: list[str] = []
	rule = 'DOC-2' if 'hypothesis' == kind else 'DOC-3'
	if require_link and (not _LINK_RE.search(body)):
		errs.append(f'{rule} / df-analysis: {kind} "{label}" must include a primary source link')
	if not _FOR_RE.search(body):
		errs.append(f'{rule} / df-analysis: {kind} "{label}" must state arguments for')
	if not _AGAINST_RE.search(body):
		errs.append(f'{rule} / df-analysis: {kind} "{label}" must state arguments against')
	if not _PCT_RE.search(body):
		errs.append(f'{rule} / df-analysis: {kind} "{label}" must state an analyst score in %')
	return errs
def _check_item_group(items: list[tuple[str, str]], *, require_link: bool, kind: str, context: str) -> list[str]:
	rule = 'DOC-2' if 'hypothesis' == kind else 'DOC-3'
	errs: list[str] = []
	if 2 > len(items):
		errs.append(f'{rule} / df-analysis: {context} must evaluate at least 2 competing {kind} items (found {len(items)})')
	for label, body in items:
		errs.extend(_check_item_fields(label, body, require_link=require_link, kind=kind))
	return errs
def _check_problem_metadata(body: str) -> list[str]:
	m = _JSON_FENCE_RE.search(body or '')
	if None is m:
		r = ['DOC-5 / df-analysis: Section # 0 (Problem Metadata) must contain a fenced ```json metadata block']
	else:
		try:
			obj = json.loads(m.group(1))
		except ValueError as exc:
			r = [f'DOC-5 / df-analysis: Section # 0 JSON metadata block is invalid: {exc}']
		else:
			r = _validate_metadata_obj(obj)
	return r
def _check_problem_sections(sections: dict[int, tuple[str, str]]) -> list[str]:
	errs = [f'DOC-5 / df-analysis: Problem analysis is missing required top-level section # {num}' for num in range(5) if num not in sections]
	if 0 in sections:
		errs.extend(_check_problem_metadata(sections[0][1]))
	if 1 in sections:
		body1 = sections[1][1].strip()
		if 15 > len(body1) or (not _VERBATIM_RE.search(body1)):
			errs.append('DOC-5 / df-analysis: Section # 1 (Problem Description) must include verbatim diagnostic messages or quoted output')
	if 2 in sections:
		errs.extend(_check_item_group(_parse_section_items(sections[2][1]), require_link=True, kind='hypothesis', context='Section # 2 (Root Cause Analysis)'))
	if 3 in sections and 10 > len(sections[3][1].strip()):
		errs.append('DOC-5 / df-analysis: Section # 3 (Source Project Attribution) must identify the owning source project')
	if 4 in sections:
		errs.extend(_check_item_group(_parse_section_items(sections[4][1]), require_link=False, kind='solution method', context='Section # 4 (Systemic Solutions)'))
	return errs
def _detect_mode(text: str, sections: dict[int, tuple[str, str]], requests: list | tuple, mode: str) -> str:
	if mode in ('general', 'problem'):
		r = mode
	else:
		has_s0_meta = 0 in sections and bool(_PROB_HEAD_RE.search(sections[0][0]))
		has_s1_prob = 1 in sections and bool(_PROB_HEAD_RE.search(sections[1][0])) and bool({2, 3, 4} & set(sections))
		if has_s0_meta or has_s1_prob:
			r = 'problem'
		elif _requests_invoke_df_analysis(requests):
			r = 'problem' if 0 in sections else 'general'
		else:
			hyps, mets = _parse_explicit_items(text)
			r = 'general' if hyps or mets else 'none'
	return r
def _extract_top_sections(text: str) -> dict[int, tuple[str, str]]:
	sections: dict[int, tuple[str, list[str]]] = {}
	cur: int | None = None
	for _, raw, fenced in _mask_fenced_lines(text):
		m = _TOP_HEAD_RE.match(raw.strip()) if not fenced else None
		if None is not m:
			cur = int(m.group(1))
			sections[cur] = ((m.group(2) or '').strip(), [])
		elif None is not cur:
			sections[cur][1].append(raw)
	return {k: (title, '\n'.join(lines)) for k, (title, lines) in sections.items()}
def _is_table_header_pair(lines: list[tuple[int, str, bool]], idx: int) -> bool:
	_, raw, fenced = lines[idx]
	_, nxt, nxt_fenced = lines[idx + 1]
	stripped = raw.strip()
	return (not fenced) and (not nxt_fenced) and ('|' in stripped) and (not stripped.startswith('>')) and bool(_TABLE_SEP_RE.match(nxt))
def _mask_fenced_lines(text: str) -> list[tuple[int, str, bool]]:
	out: list[tuple[int, str, bool]] = []
	in_fence, marker, in_fm = (False, '', False)
	for idx, raw in enumerate((text or '').splitlines(), 1):
		stripped = raw.strip()
		if in_fm or (1 == idx and '---' == stripped):
			in_fm = not (in_fm and '---' == stripped)
			out.append((idx, raw, True))
			continue
		m = _FENCE_RE.match(stripped)
		if None is not m:
			in_fence, marker = (False, '') if in_fence and stripped.startswith(marker * 3) else ((True, m.group(1)[0]) if not in_fence else (in_fence, marker))
			out.append((idx, raw, True))
		else:
			out.append((idx, raw, in_fence))
	return out
def _parse_explicit_items(text: str) -> tuple[list[tuple[str, str]], list[tuple[str, str]]]:
	hyps: list[tuple[str, list[str]]] = []
	mets: list[tuple[str, list[str]]] = []
	cur: list[str] | None = None
	for _, raw, fenced in _mask_fenced_lines(text):
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
def _parse_list_items(masked: list[tuple[int, str, bool]]) -> list[tuple[str, str]]:
	items: list[tuple[str, list[str]]] = []
	for _, raw, fenced in masked:
		if not fenced and _ITEM_LINE_RE.match(raw.strip()):
			items.append((raw.strip()[:60], [raw]))
		elif items:
			items[-1][1].append(raw)
	return [(k, '\n'.join(v)) for k, v in items]
def _parse_section_items(body: str) -> list[tuple[str, str]]:
	masked = _mask_fenced_lines(body)
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
def _requests_invoke_df_analysis(requests: list | tuple) -> bool:
	r = False
	for req in requests or ():
		raw = str(req.get('text') or req.get('content') or '') if isinstance(req, dict) else str(req or '')
		plain = '\n'.join((line for _, line, fenced in _mask_fenced_lines(raw) if not fenced))
		if _CMD_RE.search(plain):
			r = True
			break
	return r
def _validate_general(text: str, explicit_cmd: bool) -> list[str]:
	hyps, mets = _parse_explicit_items(text)
	errs: list[str] = []
	if explicit_cmd and (not hyps) and (not mets):
		errs.append('DOC-2 / DOC-3 / df-analysis: /df-analysis response must present evaluated hypotheses (H-*) and/or solution methods (M-*)')
	if hyps:
		errs.extend(_check_item_group(hyps, require_link=True, kind='hypothesis', context='Hypothesis analysis'))
	if mets:
		errs.extend(_check_item_group(mets, require_link=False, kind='solution method', context='Solution method analysis'))
	return errs
def _validate_metadata_obj(obj: object) -> list[str]:
	errs: list[str] = []
	if not isinstance(obj, dict):
		errs.append('DOC-5 / df-analysis: Section # 0 JSON metadata must be a JSON object')
	else:
		if 'Issue' not in obj:
			errs.append('DOC-5 / df-analysis: Section # 0 metadata is missing mandatory "Issue" key')
		else:
			val = obj['Issue']
			if None is not val and (not (isinstance(val, str) and _GH_ISSUE_URL_RE.fullmatch(val.strip().rstrip('/')))):
				errs.append('DOC-5 / df-analysis: Section # 0 "Issue" must be a valid GitHub issue URL or null (non-GitHub workspace)')
		for req_key in ('Time', 'Project'):
			if req_key not in obj:
				errs.append(f'DOC-5 / df-analysis: Section # 0 metadata is missing required "{req_key}" key')
	return errs
def analysis_gate_issues(response: str, *, requests: list | tuple=()) -> list[str]:
	return [*markdown_table_issues(response), *validate_df_analysis(response, requests=requests, mode='auto')]
def external_anchor_issues(label: str, href: str, norm_url: str, observed_anchors: dict[str, set[str]], response: str) -> list[str]:
	errs: list[str] = []
	frag = urlsplit(href).fragment
	anchors = observed_anchors.get(norm_url)
	if frag and (not re.fullmatch(r'L\d+(?:-L?\d+)?', frag)) and (None is not anchors):
		if frag not in anchors and unquote(frag) not in anchors and ('anchor_exception' not in response):
			errs.append(f'VERIFY-1 / LINK-2: External link [{label}]({href}) references anchor "#{frag}" which is absent from the saved observation in \ua616/KB/Evidence')
	elif (not frag) and is_documentation_url(href) and anchors and ('anchor_exception' not in response):
		errs.append(f'VERIFY-1 / LINK-2: Documentation link [{label}]({href}) omits a section #anchor despite {len(anchors)} available anchor(s) in the saved observation (cite an exact #anchor or record anchor_exception)')
	return errs
def find_markdown_table_lines(text: str) -> list[int]:
	masked = _mask_fenced_lines(text)
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
def is_documentation_url(url: str) -> bool:
	parsed = urlsplit((url or '').strip())
	host = (parsed.hostname or '').lower()
	path = (parsed.path or '').lower()
	return host.startswith(_DOC_HOST_PREFIXES) or host.endswith(_DOC_HOST_SUFFIXES) or any((m in path for m in _DOC_PATH_MARKERS)) or (host in ('github.com', 'raw.githubusercontent.com') and path.endswith('.md'))
def markdown_table_issues(text: str) -> list[str]:
	return [f'DOC-4 Line {ln}: Markdown table detected; Markdown tables are forbidden by rule DOC-4 (rewrite as structured prose or a list).' for ln in find_markdown_table_lines(text)]
def validate_df_analysis(response: str, *, requests: list | tuple=(), mode: str='auto') -> list[str]:
	from .metadata import strip_leading_metadata_header
	from .scatter_banner import validate_scatter_banners
	body = strip_leading_metadata_header(response or '')
	sections = _extract_top_sections(body)
	eff_mode = _detect_mode(body, sections, requests, mode)
	if 'problem' == eff_mode:
		r = _check_problem_sections(sections)
	elif 'general' == eff_mode:
		r = _validate_general(body, _requests_invoke_df_analysis(requests) or 'general' == mode)
	else:
		r = []
	r.extend(validate_scatter_banners(body, sections=sections, mode=eff_mode))
	return r
def validate_statements(directory: Path) -> list[str]:
	directory = Path(directory)
	if not directory.is_dir():
		r = [f'Missing statement directory: {directory}']
	else:
		entries = sorted((p for p in directory.iterdir() if p.is_dir() and p.name.isdigit()))
		if not entries:
			r = [f'No statement directories: {directory}']
		else:
			errors = []
			for entry in entries:
				for name in ('.md', 'Test.md'):
					path = entry / name
					try:
						if not path.read_text(encoding='utf-8').strip():
							errors.append(f'Empty file: {path}')
					except (OSError, UnicodeError) as exc:
						errors.append(f'{path}: {exc}')
			r = errors
	return r
