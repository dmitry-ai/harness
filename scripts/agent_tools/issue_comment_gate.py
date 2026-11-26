# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from pathlib import Path
import ast
import difflib
import re
from .shell_audit import _GITHUB_ISSUE_URL_RE, normalize_host_path
from .tdd_gate import _compute_edited_content, _git_head_text, _git_index_text
_AUTHOR_RE = re.compile(r'Dmitrii\s+Fediuk\s+https://github\.com/dmitrii-fediuk', re.I)
_BAT_CMT_RE = re.compile(r'^(?:rem\b|::)', re.I)
_HASH_SUFFIXES = frozenset({'.awk', '.bash', '.pl', '.ps1', '.psd1', '.psm1', '.py', '.pyi', '.rb', '.sh', '.zsh'})
_IMPORT_LINE_RE = re.compile(r'^\s*(?:from\s+\S+\s+import\b|import\b|package\b|use\b|#include\b|#pragma\b|using\b|(?:const|let|var)\s+[\w{},\s]+\s*=\s*require\s*\()')
_PREAMBLE_RE = re.compile(r'^(?:#!|<\?php\b|<\?xml\b|@echo\s+off\b)', re.I)
_PY_BLOCK_TYPES = (ast.If, ast.For, ast.AsyncFor, ast.While, ast.With, ast.AsyncWith, ast.Try)
_PY_DEF_TYPES = (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)
_SUPPORTED_SUFFIXES = frozenset({
	'.awk', '.bash', '.bat', '.c', '.cc', '.cjs', '.cmd', '.cpp', '.cs', '.css', '.cxx', '.h', '.hpp', '.html', '.hxx',
	'.java', '.js', '.jsx', '.kt', '.kts', '.less', '.mjs', '.php', '.phtml', '.pl', '.ps1', '.psd1', '.psm1', '.py',
	'.pyi', '.rb', '.scss', '.sh', '.sql', '.ts', '.tsx', '.vbs', '.xml', '.zsh',
})
_VBS_CMT_RE = re.compile(r'^(?:\'|rem\b)', re.I)
_XML_SUFFIXES = frozenset({'.html', '.xml'})
def _brace_span(lines: list[str], start_line: int) -> tuple[int, int, str]:
	first = lines[start_line - 1].rstrip()
	if first.endswith(';') and '{' not in first:
		r = (start_line, start_line, 'stmt')
	else:
		end_line, seen = _scan_brace_end(lines, start_line)
		r = (start_line, end_line, 'block' if seen else 'stmt')
	return r
def _build_py_spans(source: str) -> tuple[dict[int, tuple[int, int, str]], dict[int, list[tuple[int, int]]]]:
	spans: dict[int, tuple[int, int, str]] = {}
	class_methods: dict[int, list[tuple[int, int]]] = {}
	try:
		tree = ast.parse(source or '')
	except SyntaxError:
		tree = None
	if None is not tree:
		for node in ast.walk(tree):
			_record_py_node(node, spans, class_methods)
	return (spans, class_methods)
def _check_added_issue_line(rel_label: str, ln: int, cur_lines: list[str], cur_scan: dict, diff_info: dict, py_info: tuple, suffix: str) -> str | None:
	r: str | None = None
	changed_code, del_anchors = (diff_info['changed_code'], diff_info['del_anchors'])
	if ln in cur_scan['code_lines']:
		if changed_code and ln not in changed_code:
			r = f'ISSUE-COMMENT-GATE (MISPLACED_ISSUE_COMMENT): Inline issue URL comment in {rel_label}:{ln} sits on an unchanged line; place it at the modified block or function header'
	else:
		nxt = _next_code_line(ln, cur_scan['code_lines'], len(cur_lines))
		if ln <= cur_scan['header_end'] and None is not nxt:
			r = _check_header_placement(rel_label, ln, nxt, cur_lines, changed_code, del_anchors, py_info, suffix, comment_only=bool(diff_info.get('comment_only')))
		elif changed_code or del_anchors:
			r = _check_body_placement(rel_label, ln, nxt, cur_lines, changed_code, del_anchors, py_info, suffix)
	return r
def _check_author_headers(rel_label: str, cur_scan: dict, base_scan: dict | None) -> list[str]:
	errs: list[str] = []
	cur_auth = cur_scan['author_lines']
	base_cnt = len(base_scan['author_lines']) if None is not base_scan else 0
	if 1 < len(cur_auth) and (None is base_scan or base_cnt < len(cur_auth)):
		errs.append(f'ISSUE-COMMENT-GATE (DUPLICATE_AUTHOR_HEADER): Author header appears {len(cur_auth)} times in {rel_label} at line(s) {cur_auth[:5]}; write Dmitrii Fediuk once in the file header')
	cur_out = [ln for ln in cur_auth if cur_scan['header_end'] < ln]
	base_out = len([ln for ln in base_scan['author_lines'] if base_scan['header_end'] < ln]) if None is not base_scan else 0
	if cur_out and base_out < len(cur_out):
		errs.append(f'ISSUE-COMMENT-GATE (AUTHOR_OUTSIDE_HEADER): Author line in {rel_label} at line(s) {cur_out[:5]} appears below the file header; keep author line once at the top of the file')
	return errs
def _check_body_placement(rel_label: str, ln: int, nxt: int | None, cur_lines: list[str], changed_code: set[int], del_anchors: set[int], py_info: tuple, suffix: str) -> str | None:
	r: str | None = None
	if None is nxt:
		if not any((2 >= abs(d - ln) for d in del_anchors)):
			r = f'ISSUE-COMMENT-GATE (MISPLACED_ISSUE_COMMENT): Issue URL comment at {rel_label}:{ln} has no modified code block below it'
	else:
		st, en, kind = _construct_span(cur_lines, nxt, suffix, py_info[0])
		in_span = nxt in changed_code or any((st <= c <= en for c in changed_code)) or any((st - 1 <= d <= en + 1 for d in del_anchors))
		if not in_span:
			nearest = min(changed_code or del_anchors, key=lambda x: abs(x - ln))
			r = f'ISSUE-COMMENT-GATE (MISPLACED_ISSUE_COMMENT): Issue URL comment at {rel_label}:{ln} does not precede modified code (nearest change at line {nearest})'
		elif 'class' == kind and st not in changed_code:
			r = _check_class_scope(rel_label, ln, st, en, changed_code, py_info[1])
	return r
def _check_class_scope(rel_label: str, ln: int, st: int, en: int, changed_code: set[int], class_methods: dict[int, list[tuple[int, int]]]) -> str | None:
	r: str | None = None
	methods = class_methods.get(st, ())
	touched = [m for m in methods if any((m[0] <= c <= m[1] for c in changed_code))]
	outside = [c for c in changed_code if st <= c <= en and (not any((m[0] <= c <= m[1] for m in methods)))]
	if 2 <= len(methods) and 1 == len(touched) and (not outside):
		r = f'ISSUE-COMMENT-GATE (MISPLACED_ISSUE_COMMENT): Issue URL comment at {rel_label}:{ln} sits on class header while only method at line {touched[0][0]} changed; place it at the modified block or method header'
	return r
def _check_diff_issue_lines(rel_label: str, source: str, base_lines: list[str], cur_lines: list[str], base_scan: dict, cur_scan: dict, suffix: str) -> list[str]:
	from .tdd.comment_diff import is_comment_only_diff
	errs: list[str] = []
	diff_info = _diff_changes(base_lines, cur_lines, base_scan, cur_scan)
	# 2026-11-26 "Fix comment-only diff and denied-write gate false positives": https://github.com/dmitry-ai/harness/issues/276
	if is_comment_only_diff(rel_label, '\n'.join(base_lines), source):
		diff_info['changed_code'], diff_info['del_anchors'], diff_info['comment_only'] = (set(), set(), True)
	base_urls = {u for urls in base_scan['issue_lines'].values() for u in urls}
	if 0.70 > len(diff_info['changed_code']) / max(1, len(cur_scan['code_lines'])):
		py_info = _build_py_spans(source) if suffix in ('.py', '.pyi') else ({}, {})
		for ln in sorted(diff_info['added_issue']):
			if any((u not in base_urls for u in cur_scan['issue_lines'][ln])):
				err = _check_added_issue_line(rel_label, ln, cur_lines, cur_scan, diff_info, py_info, suffix)
				if None is not err:
					errs.append(err)
	return errs
def _check_header_placement(rel_label: str, ln: int, nxt: int, cur_lines: list[str], changed_code: set[int], del_anchors: set[int], py_info: tuple, suffix: str, *, comment_only: bool=False) -> str | None:
	r: str | None = None
	direct = nxt in changed_code or any((1 >= abs(d - nxt) for d in del_anchors))
	if not direct:
		is_imp = bool(_IMPORT_LINE_RE.match(cur_lines[nxt - 1]))
		st, en, kind = _construct_span(cur_lines, nxt, suffix, py_info[0])
		in_unit = (not is_imp) and kind in ('func', 'class', 'block') and (comment_only or any((st <= c <= en for c in changed_code)))
		if not in_unit:
			r = f'ISSUE-COMMENT-GATE (HEADER_DUMPED_ISSUE_COMMENT): Issue URL comment at {rel_label}:{ln} is dumped in the file header above unchanged line {nxt}; place it immediately before the modified block or function/method header'
	return r
def _construct_span(lines: list[str], start_line: int, suffix: str, py_spans: dict[int, tuple[int, int, str]]) -> tuple[int, int, str]:
	if suffix in ('.py', '.pyi') and start_line in py_spans:
		r = py_spans[start_line]
	elif suffix in _XML_SUFFIXES:
		r = _xml_span(lines, start_line)
	elif suffix not in _HASH_SUFFIXES and suffix not in ('.cmd', '.bat', '.vbs', '.sql'):
		r = _brace_span(lines, start_line)
	else:
		r = (start_line, start_line, 'stmt')
	return r
def _diff_changes(base_lines: list[str], cur_lines: list[str], base_scan: dict, cur_scan: dict) -> dict:
	changed_code: set[int] = set()
	added_issue: set[int] = set()
	del_anchors: set[int] = set()
	for tag, i1, i2, j1, j2 in difflib.SequenceMatcher(None, base_lines, cur_lines).get_opcodes():
		if 'equal' == tag:
			continue
		for ln in range(j1 + 1, j2 + 1):
			if ln in cur_scan['code_lines']:
				changed_code.add(ln)
			if ln in cur_scan['issue_lines']:
				added_issue.add(ln)
		if tag in ('delete', 'replace') and any((bl in base_scan['code_lines'] for bl in range(i1 + 1, i2 + 1))):
			del_anchors.add(min(max(1, j1 + 1), max(1, len(cur_lines))))
	return {'added_issue': added_issue, 'changed_code': changed_code, 'del_anchors': del_anchors}
def _find_git_root(path: Path) -> Path | None:
	r = None
	for anc in (path.parent, *path.parent.parents):
		if (anc / '.git').exists():
			r = anc
			break
	return r
def _is_line_comment_prefix(s: str, suffix: str) -> bool:
	if suffix in _HASH_SUFFIXES:
		r = s.startswith('#')
	elif suffix in ('.php', '.phtml'):
		r = (s.startswith('#') and (not s.startswith('#['))) or s.startswith('//')
	elif suffix in ('.cmd', '.bat'):
		r = bool(_BAT_CMT_RE.match(s))
	elif '.vbs' == suffix:
		r = bool(_VBS_CMT_RE.match(s))
	elif '.sql' == suffix:
		r = s.startswith('--')
	else:
		r = s.startswith('//') and '.css' != suffix and suffix not in _XML_SUFFIXES
	return r
def _is_pure_comment_line(line: str, suffix: str, in_block: bool) -> tuple[bool, bool]:
	s = line.lstrip('\ufeff').strip()
	if in_block:
		r = (True, ('-->' if suffix in _XML_SUFFIXES else '*/') not in s)
	elif suffix in _XML_SUFFIXES and s.startswith('<!--'):
		r = (True, '-->' not in s)
	elif s.startswith('/*') and suffix not in _XML_SUFFIXES:
		r = (True, '*/' not in s)
	else:
		r = (_is_line_comment_prefix(s, suffix), False)
	return r
def _next_code_line(start_ln: int, code_lines: set[int], total: int) -> int | None:
	r = None
	for cand in range(start_ln + 1, total + 1):
		if cand in code_lines:
			r = cand
			break
	return r
def _record_py_node(node: ast.AST, spans: dict[int, tuple[int, int, str]], class_methods: dict[int, list[tuple[int, int]]]) -> None:
	if isinstance(node, _PY_DEF_TYPES):
		decs = [int(d.lineno) for d in getattr(node, 'decorator_list', ())]
		st = min(decs) if decs else int(node.lineno)
		en = int(getattr(node, 'end_lineno', node.lineno) or node.lineno)
		kind = 'class' if isinstance(node, ast.ClassDef) else 'func'
		spans[st] = spans[int(node.lineno)] = (st, en, kind)
		if isinstance(node, ast.ClassDef):
			class_methods[st] = [(int(m.lineno), int(getattr(m, 'end_lineno', m.lineno) or m.lineno)) for m in node.body if isinstance(m, (ast.FunctionDef, ast.AsyncFunctionDef))]
	elif isinstance(node, _PY_BLOCK_TYPES):
		st = int(node.lineno)
		spans.setdefault(st, (st, int(getattr(node, 'end_lineno', st) or st), 'block'))
def _resolve_comment_target(args: dict, payload: dict) -> tuple[Path | None, Path, str] | None:
	raw_p = str(args.get('Path') or '').strip()
	r = None
	if raw_p:
		cwd_raw = str(payload.get('cwd') or '').strip()
		cand = normalize_host_path(raw_p)
		target = cand.resolve() if cand.is_absolute() else ((Path(cwd_raw).resolve() / cand).resolve() if cwd_raw else cand.resolve())
		if target.suffix.lower() in _SUPPORTED_SUFFIXES:
			repo = _find_git_root(target)
			rel = target.relative_to(repo).as_posix() if None is not repo and target.is_relative_to(repo) else target.name
			if not rel.casefold().startswith(('\ua616/', '\ua66e/', '.git/')):
				r = (repo, target, rel)
	return r
def _scan_brace_end(lines: list[str], start_line: int) -> tuple[int, bool]:
	depth, seen, end_line = (0, False, start_line)
	for idx in range(start_line - 1, len(lines)):
		opens = lines[idx].count('{')
		seen = seen or 0 < opens
		depth += opens - lines[idx].count('}')
		if seen and 0 >= depth:
			end_line = idx + 1
			break
		if (not seen) and idx >= start_line:
			break
	return (end_line, seen)
def _scan_lines(lines: list[str], suffix: str) -> dict:
	st = {'author_lines': [], 'code_lines': set(), 'header_end': 0, 'issue_lines': {}, 'seen_code': False}
	in_block = False
	for idx, raw in enumerate(lines, 1):
		s = raw.lstrip('\ufeff').strip()
		is_cmt, in_block = _is_pure_comment_line(raw, suffix, in_block) if s else (False, in_block)
		if is_cmt:
			_scan_record_comment(st, idx, raw)
		elif s:
			_scan_record_code(st, idx, raw, s, suffix)
	return st
def _scan_record_code(st: dict, idx: int, raw: str, s: str, suffix: str) -> None:
	if (not st['seen_code']) and 1 == idx and _PREAMBLE_RE.match(s):
		st['header_end'] = idx
	else:
		st['seen_code'] = True
		st['code_lines'].add(idx)
		t_urls = _trailing_comment_urls(raw, suffix)
		if t_urls:
			st['issue_lines'][idx] = t_urls
def _scan_record_comment(st: dict, idx: int, raw: str) -> None:
	if _AUTHOR_RE.search(raw):
		st['author_lines'].append(idx)
	urls = _GITHUB_ISSUE_URL_RE.findall(raw)
	if urls:
		st['issue_lines'][idx] = urls
	if not st['seen_code']:
		st['header_end'] = idx
def _trailing_comment_urls(line: str, suffix: str) -> list[str]:
	r: list[str] = []
	if 'https://github.com/' in line and '/issues/' in line:
		pat = r'(?:<!--)' if suffix in _XML_SUFFIXES else (r'(?:#)' if suffix in _HASH_SUFFIXES else r'(?://|/\*|#)')
		for m in re.finditer(pat, line):
			prefix = line[:m.start()]
			if 0 == prefix.count("'") % 2 and 0 == prefix.count('"') % 2:
				r = _GITHUB_ISSUE_URL_RE.findall(line[m.start():])
				if r:
					break
	return r
def _xml_span(lines: list[str], start_line: int) -> tuple[int, int, str]:
	m = re.match(r'^\s*<([A-Za-z_][\w:.-]*)\b', lines[start_line - 1])
	end_line, kind = (start_line, 'stmt')
	if None is not m:
		close_tok = f'</{m.group(1)}>'
		if '/>' not in lines[start_line - 1] and close_tok not in lines[start_line - 1]:
			kind = 'block'
			for idx in range(start_line, len(lines)):
				if close_tok in lines[idx] or ('/>' in lines[idx] and '<' not in lines[idx]):
					end_line = idx + 1
					break
	return (start_line, end_line, kind)
# 2026-11-26
# "Add PreToolUse and pre-commit gate for issue-comment placement":
# https://github.com/dmitry-ai/harness/issues/273
def check_issue_comment_violations(path: str | Path, source: str, *, baseline_source: str | None=None) -> list[str]:
	p = Path(path)
	suffix = p.suffix.lower()
	errs: list[str] = []
	if suffix in _SUPPORTED_SUFFIXES:
		rel_label = p.as_posix()
		cur_lines = (source or '').splitlines()
		cur_scan = _scan_lines(cur_lines, suffix)
		base_lines = baseline_source.splitlines() if None is not baseline_source else None
		base_scan = _scan_lines(base_lines, suffix) if None is not base_lines else None
		errs.extend(_check_author_headers(rel_label, cur_scan, base_scan))
		if None is not base_scan and base_scan['code_lines']:
			errs.extend(_check_diff_issue_lines(rel_label, source, base_lines, cur_lines, base_scan, cur_scan, suffix))
	return errs
def evaluate_pre_tool_use_issue_comment(name: str, args: dict, payload: dict) -> str | None:
	r = None
	if name in ('write_file', 'edit_file'):
		resolved = _resolve_comment_target(args, payload)
		if None is not resolved:
			repo_root, target, rel = resolved
			_, new_text, _, _ = _compute_edited_content(name, args, target)
			if None is not new_text:
				base = _git_head_text(repo_root, rel) if None is not repo_root else (target.read_text(encoding='utf-8', errors='replace') if target.is_file() else None)
				errs = check_issue_comment_violations(rel, new_text, baseline_source=base)
				r = '; '.join(errs[:3]) if errs else None
	return r
def verify_staged_issue_comment_placement(repo_root: Path, staged_paths: list[str], *, use_index: bool=True) -> list[str]:
	repo = Path(repo_root).resolve()
	violations: list[str] = []
	for rel in staged_paths or ():
		if Path(rel).suffix.lower() not in _SUPPORTED_SUFFIXES or rel.casefold().startswith(('\ua616/', '\ua66e/', '.git/')):
			continue
		fpath = repo / rel
		text = _git_index_text(repo, rel) if use_index else (fpath.read_text(encoding='utf-8', errors='replace') if fpath.is_file() else None)
		if None is not text:
			violations.extend(check_issue_comment_violations(rel, text, baseline_source=_git_head_text(repo, rel)))
	return violations
