# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from pathlib import Path
from Df.Core.lib.fs import df_path_suffix
from Df.Core.lib.git import df_git_root
from agent_tools.shell_audit import _GITHUB_ISSUE_URL_RE, normalize_host_path
import ast
import re
# 2026-11-26 "Move verification gate subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/381
class IssueCommentScanner:
	HASH_SUFFIXES = frozenset({'.awk', '.bash', '.pl', '.ps1', '.psd1', '.psm1', '.py', '.pyi', '.rb', '.sh', '.zsh'})
	SUPPORTED_SUFFIXES = frozenset({
		'.awk', '.bash', '.bat', '.c', '.cc', '.cjs', '.cmd', '.cpp', '.cs', '.css', '.cxx', '.h', '.hpp', '.html', '.hxx',
		'.java', '.js', '.jsx', '.kt', '.kts', '.less', '.mjs', '.php', '.phtml', '.pl', '.ps1', '.psd1', '.psm1', '.py',
		'.pyi', '.rb', '.scss', '.sh', '.sql', '.ts', '.tsx', '.vbs', '.xml', '.zsh',
	})
	XML_SUFFIXES = frozenset({'.html', '.xml'})
	__AUTHOR_RE = re.compile(r'Dmitrii\s+Fediuk\s+https://github\.com/dmitrii-fediuk', re.I)
	__BAT_CMT_RE = re.compile(r'^(?:rem\b|::)', re.I)
	__PREAMBLE_RE = re.compile(r'^(?:#!|<\?php\b|<\?xml\b|@echo\s+off\b)', re.I)
	__PY_BLOCK_TYPES = (ast.If, ast.For, ast.AsyncFor, ast.While, ast.With, ast.AsyncWith, ast.Try)
	__PY_DEF_TYPES = (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)
	__VBS_CMT_RE = re.compile(r'^(?:\'|rem\b)', re.I)
	# @used-by :meth:`Df.Harness.Gate.IssueCommentChecker.IssueCommentChecker.check()`
	def __init__(self, lines: list[str], suffix: str) -> None:
		self.__lines = lines
		self.__suffix = suffix
	# @used-by :meth:`IssueCommentScanner.construct_span()`
	@staticmethod
	def __brace_span(lines: list[str], start_line: int) -> tuple[int, int, str]:
		first = lines[start_line - 1].rstrip()
		if first.endswith(';') and '{' not in first:
			r = (start_line, start_line, 'stmt')
		else:
			end_line, seen = IssueCommentScanner.__scan_brace_end(lines, start_line)
			r = (start_line, end_line, 'block' if seen else 'stmt')
		return r
	# @used-by :meth:`IssueCommentScanner.__is_pure_comment_line()`
	@staticmethod
	def __is_line_comment_prefix(s: str, suffix: str) -> bool:
		if suffix in IssueCommentScanner.HASH_SUFFIXES:
			r = s.startswith('#')
		elif suffix in ('.php', '.phtml'):
			r = (s.startswith('#') and (not s.startswith('#['))) or s.startswith('//')
		elif suffix in ('.cmd', '.bat'):
			r = bool(IssueCommentScanner.__BAT_CMT_RE.match(s))
		elif '.vbs' == suffix:
			r = bool(IssueCommentScanner.__VBS_CMT_RE.match(s))
		elif '.sql' == suffix:
			r = s.startswith('--')
		else:
			r = s.startswith('//') and '.css' != suffix and suffix not in IssueCommentScanner.XML_SUFFIXES
		return r
	# @used-by :meth:`IssueCommentScanner.scan()`
	@staticmethod
	def __is_pure_comment_line(line: str, suffix: str, in_block: bool) -> tuple[bool, bool]:
		s = line.lstrip('\ufeff').strip()
		if in_block:
			r = (True, ('-->' if suffix in IssueCommentScanner.XML_SUFFIXES else '*/') not in s)
		elif suffix in IssueCommentScanner.XML_SUFFIXES and s.startswith('<!--'):
			r = (True, '-->' not in s)
		elif s.startswith('/*') and suffix not in IssueCommentScanner.XML_SUFFIXES:
			r = (True, '*/' not in s)
		else:
			r = (IssueCommentScanner.__is_line_comment_prefix(s, suffix), False)
		return r
	# @used-by :meth:`IssueCommentScanner.build_py_spans()`
	@staticmethod
	def __record_py_node(node: ast.AST, spans: dict[int, tuple[int, int, str]], class_methods: dict[int, list[tuple[int, int]]]) -> None:
		if isinstance(node, IssueCommentScanner.__PY_DEF_TYPES):
			decs = [int(d.lineno) for d in getattr(node, 'decorator_list', ())]
			st = min(decs) if decs else int(node.lineno)
			en = int(getattr(node, 'end_lineno', node.lineno) or node.lineno)
			kind = 'class' if isinstance(node, ast.ClassDef) else 'func'
			spans[st] = spans[int(node.lineno)] = (st, en, kind)
			if isinstance(node, ast.ClassDef):
				class_methods[st] = [(int(m.lineno), int(getattr(m, 'end_lineno', m.lineno) or m.lineno)) for m in node.body if isinstance(m, (ast.FunctionDef, ast.AsyncFunctionDef))]
		elif isinstance(node, IssueCommentScanner.__PY_BLOCK_TYPES):
			st = int(node.lineno)
			spans.setdefault(st, (st, int(getattr(node, 'end_lineno', st) or st), 'block'))
	# @used-by :meth:`IssueCommentScanner.__brace_span()`
	@staticmethod
	def __scan_brace_end(lines: list[str], start_line: int) -> tuple[int, bool]:
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
	# @used-by :meth:`IssueCommentScanner.scan()`
	@staticmethod
	def __scan_record_code(st: dict, idx: int, raw: str, s: str, suffix: str) -> None:
		if (not st['seen_code']) and 1 == idx and IssueCommentScanner.__PREAMBLE_RE.match(s):
			st['header_end'] = idx
		else:
			st['seen_code'] = True
			st['code_lines'].add(idx)
			t_urls = IssueCommentScanner.__trailing_comment_urls(raw, suffix)
			if t_urls:
				st['issue_lines'][idx] = t_urls
	# @used-by :meth:`IssueCommentScanner.scan()`
	@staticmethod
	def __scan_record_comment(st: dict, idx: int, raw: str) -> None:
		if IssueCommentScanner.__AUTHOR_RE.search(raw):
			st['author_lines'].append(idx)
		urls = _GITHUB_ISSUE_URL_RE.findall(raw)
		if urls:
			st['issue_lines'][idx] = urls
		if not st['seen_code']:
			st['header_end'] = idx
	# @used-by :meth:`IssueCommentScanner.__scan_record_code()`
	@staticmethod
	def __trailing_comment_urls(line: str, suffix: str) -> list[str]:
		r: list[str] = []
		if 'https://github.com/' in line and '/issues/' in line:
			pat = r'(?:<!--)' if suffix in IssueCommentScanner.XML_SUFFIXES else (r'(?:#)' if suffix in IssueCommentScanner.HASH_SUFFIXES else r'(?://|/\*|#)')
			for m in re.finditer(pat, line):
				prefix = line[:m.start()]
				if 0 == prefix.count("'") % 2 and 0 == prefix.count('"') % 2:
					r = _GITHUB_ISSUE_URL_RE.findall(line[m.start():])
					if r:
						break
		return r
	# @used-by :meth:`IssueCommentScanner.construct_span()`
	@staticmethod
	def __xml_span(lines: list[str], start_line: int) -> tuple[int, int, str]:
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
	# @used-by :meth:`Df.Harness.Gate.IssueCommentChecker.IssueCommentChecker.__check_diff_issue_lines()`
	@staticmethod
	def build_py_spans(source: str) -> tuple[dict[int, tuple[int, int, str]], dict[int, list[tuple[int, int]]]]:
		spans: dict[int, tuple[int, int, str]] = {}
		class_methods: dict[int, list[tuple[int, int]]] = {}
		try:
			tree = ast.parse(source or '')
		except SyntaxError:
			tree = None
		if None is not tree:
			for node in ast.walk(tree):
				IssueCommentScanner.__record_py_node(node, spans, class_methods)
		return (spans, class_methods)
	# @used-by :meth:`Df.Harness.Gate.IssueCommentChecker.IssueCommentChecker.__check_body_placement()`
	# @used-by :meth:`Df.Harness.Gate.IssueCommentChecker.IssueCommentChecker.__check_header_placement()`
	@staticmethod
	def construct_span(lines: list[str], start_line: int, suffix: str, py_spans: dict[int, tuple[int, int, str]]) -> tuple[int, int, str]:
		if suffix in ('.py', '.pyi') and start_line in py_spans:
			r = py_spans[start_line]
		elif suffix in IssueCommentScanner.XML_SUFFIXES:
			r = IssueCommentScanner.__xml_span(lines, start_line)
		elif suffix not in IssueCommentScanner.HASH_SUFFIXES and suffix not in ('.cmd', '.bat', '.vbs', '.sql'):
			r = IssueCommentScanner.__brace_span(lines, start_line)
		else:
			r = (start_line, start_line, 'stmt')
		return r
	# @used-by :meth:`Df.Harness.Gate.IssueCommentChecker.IssueCommentChecker.__check_added_issue_line()`
	@staticmethod
	def next_code_line(start_ln: int, code_lines: set[int], total: int) -> int | None:
		r = None
		for cand in range(start_ln + 1, total + 1):
			if cand in code_lines:
				r = cand
				break
		return r
	# @used-by :meth:`Df.Harness.Gate.IssueCommentPreToolGate.IssueCommentPreToolGate.check()`
	@staticmethod
	def resolve_target(args: dict, payload: dict) -> tuple[Path | None, Path, str] | None:
		raw_p = str(args.get('Path') or '').strip()
		r = None
		if raw_p:
			cwd_raw = str(payload.get('cwd') or '').strip()
			cand = normalize_host_path(raw_p)
			target = cand.resolve() if cand.is_absolute() else ((Path(cwd_raw).resolve() / cand).resolve() if cwd_raw else cand.resolve())
			if df_path_suffix(target) in IssueCommentScanner.SUPPORTED_SUFFIXES:
				repo = df_git_root(target.parent)
				rel = target.relative_to(repo).as_posix() if None is not repo and target.is_relative_to(repo) else target.name
				if not rel.casefold().startswith(('\ua616/', '\ua66e/', '.git/')):
					r = (repo, target, rel)
		return r
	# @used-by :meth:`Df.Harness.Gate.IssueCommentChecker.IssueCommentChecker.check()`
	def scan(self) -> dict:
		st = {'author_lines': [], 'code_lines': set(), 'header_end': 0, 'issue_lines': {}, 'seen_code': False}
		in_block = False
		for idx, raw in enumerate(self.__lines, 1):
			s = raw.lstrip('\ufeff').strip()
			is_cmt, in_block = IssueCommentScanner.__is_pure_comment_line(raw, self.__suffix, in_block) if s else (False, in_block)
			if is_cmt:
				IssueCommentScanner.__scan_record_comment(st, idx, raw)
			elif s:
				IssueCommentScanner.__scan_record_code(st, idx, raw, s, self.__suffix)
		return st
