# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from pathlib import Path
from typing import Any
from Df.Core.lib.text.n.normalize import df_normalize
from Df.Harness.Arch.SpecValidator import SpecValidator
from Df.Harness.Arch.TriggerClassifier import TriggerClassifier
import re
REPO_RE = re.compile('^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$')
_CODE_SPAN_RE = re.compile('```.*?```|`[^`\\r\\n]+`', re.S)
_FENCED_RE = re.compile('```[\\s\\S]*?```')
_M_SUBTASK_LINE_RE = re.compile('^(?:\\s*#{1,6}\\s+(?:\\d+(?:\\.\\d+)*\\.?\\s*)?|\\s*(?:[-*+]|\\d+[.)])\\s+)(?:\\*\\*|__|`|\\u00ab|"|\\\')*(?:(?i:implement|fix|add|enforce|update|resolve|subtask|method|\\u0440\\u0435\\u0430\\u043b\\u0438\\u0437\\u043e\\u0432\\u0430\\u0442\\u044c|\\u0438\\u0441\\u043f\\u0440\\u0430\\u0432\\u0438\\u0442\\u044c|\\u0434\\u043e\\u0431\\u0430\\u0432\\u0438\\u0442\\u044c|\\u043f\\u043e\\u0434\\u0437\\u0430\\u0434\\u0430\\u0447\\u0430|\\u043c\\u0435\\u0442\\u043e\\u0434)\\s+)?(?:\\*\\*|__|`|\\u00ab|"|\\\')*(?P<mid>M-(?:[A-Za-z]+-)*\\d+)[A-Za-z]?\\b', re.M)
_PARENT_ARG_URL_RE = re.compile('^https://github\\.com/([A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+)/issues/(\\d+)/?$')
_PARENT_DECL_RE = re.compile('(?im)^\\s*(?:[-*+]\\s+)?(?:\\*\\*|__)?(?:parent(?:\\s+issue)?|subtask\\s+of|child\\s+of|part\\s+of)(?:(?:\\*\\*|__)\\s*[:\\u2014-]|\\s*[:\\u2014-]\\s*(?:\\*\\*|__)?)\\s*(?:(?:\\[[^\\]]*\\]\\()?https://github\\.com/([A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+)/issues/(\\d+)\\)?|#(\\d+)\\b)')
_PATTERN_RULES = (
	('full', re.compile('[^\\r\\n\\t]\\t[A-Za-z_]'), 'INLINE_TAB_ESCAPE', 'Contains inline TAB character immediately before an identifier (caused by PowerShell `t expansion)'),
	('full', re.compile('\\b\\d+(?::\\d+)*\\?\\d+(?::\\d+)*\\b'), 'QUESTION_MARK_RANGE', 'Contains digit?digit range (caused by piping non-ASCII en-dash/em-dash through PowerShell without UTF-8 $OutputEncoding)'),
	('full', re.compile('(?<![/.])\\b[A-Za-z]{2,}\\?[a-z]{2,}\\b'), 'QUESTION_MARK_WORD_JOIN', 'Contains word?word (caused by piping em-dash \u2014 through PowerShell without UTF-8 $OutputEncoding)'),
	('no_code', re.compile('[A-Za-z0-9)\\]]\\s+\\?\\s+[A-Za-z0-9(\\[]'), 'QUESTION_MARK_SPACED', 'Contains spaced " ? " in prose outside code (caused by piping em-dash \u2014 without UTF-8 $OutputEncoding)'),
	('full', re.compile('(?<![A-Za-z0-9_/])\\?[A-Z][A-Za-z0-9_-]*\\?'), 'QUESTION_MARK_QUOTES', 'Contains ?Word? (caused by piping \u00abWord\u00bb or curly quotes without UTF-8 $OutputEncoding)'),
	('full', re.compile('(?:^|[\\s(])\\?\\d+(?:\\.\\d+)+\\b'), 'QUESTION_MARK_SECTION', 'Contains ?N.M (caused by piping section sign \u00a7N.M without UTF-8 $OutputEncoding)'),
	('full', re.compile('\\\\`'), 'ESCAPED_BACKTICK', 'Contains literal \\` (bash-style escaped backtick in Markdown)'),
	('full', re.compile('(?:^|[\\s(])\\\\[A-Za-z0-9_./:$^*\\[\\]()=-]+(?:\\s+[A-Za-z0-9_./:$^*\\[\\]()=-]+)*\\\\(?=[\\s).,;:!?\\)]|$)'), 'BACKSLASH_WRAPPED_CODE', 'Contains \\token\\ wrapped in backslashes (caused by bash-style \\`token\\` inside PowerShell double quotes)'),
	('full', re.compile('(?<![A-Za-z0-9_$\\)\\]\\}`"\\\'-])->[A-Za-z_][A-Za-z0-9_]*'), 'EATEN_VARIABLE_ARROW', 'Contains bare ->method without object receiver (caused by PowerShell expanding $this or $var to empty string)'),
	('full', re.compile('\\(\\s*,\\s*\\)|\\(\\s*,\\s*[^)\\s]|(?<!,)\\bempty\\(\\s*\\)|\\?callable\\s+=\\s*null'), 'EATEN_VARIABLE_ARG', 'Contains empty function parameter/argument slot (caused by PowerShell expanding $var to empty string)'),
	('full', re.compile('<(?:type|argument|preference|plugin|virtualType|job|group)\\b[^>]*\\b(?:name|xsi:type|id|instance|method)=[^"\\\'\\s>]+'), 'UNQUOTED_XML_ATTR', 'Contains unquoted XML attribute (caused by PowerShell 5.1 stripping double quotes when passing --body $var)'),
	('strip', re.compile('(\\(\\s*\\\\?|\\b(?:version|from|to|in|at|with|by|for)\\s*`?)$'), 'TRUNCATED_END', 'Text ends abruptly with an unfinished token or open delimiter (caused by PowerShell `0 -> NUL byte truncation)'),
)
_PSEUDO_FENCE_RE = re.compile('^``[a-zA-Z]*$')
_REF_ID_RE = re.compile('(?:#(\\d+)\\b|https://github\\.com/[^\\s)]+/issues/(\\d+)\\b)')
_SLUG_PART_RE = re.compile('^[A-Za-z0-9_.-]+$')
_TECH_MARKERS = ('app/code/', 'vendor/', '::', '### Problem', '## 1. Root Cause', '## Summary')
_TITLE_INTRO_PREP_RE = re.compile('^(?:in|on|at|for|from|to|by|with|without|under|during|upon|inside|outside|across|via|through|per|\\u0432|\\u0432\\u043e|\\u043d\\u0430|\\u043f\\u0440\\u0438|\\u0431\\u0435\\u0437|\\u0434\\u043b\\u044f|\\u0438\\u0437|\\u043f\\u043e|\\u0447\\u0435\\u0440\\u0435\\u0437)\\s+(?:the\\s+)?[A-Za-z0-9_\\u0400-\\u04ff./:-]+(?:\\s+[A-Za-z0-9_\\u0400-\\u04ff./:-]+){0,6},\\s+', re.I)
_TITLE_INTRO_SUBORD_RE = re.compile('^(?:when|if|unless|while|after|before|once|where|whenever|although|though|since|because|\\u0435\\u0441\\u043b\\u0438|\\u043a\\u043e\\u0433\\u0434\\u0430|\\u043f\\u043e\\u0441\\u043b\\u0435|\\u043f\\u043e\\u043a\\u0430)\\b[^,]*,\\s+', re.I)
_TITLE_NON_OXFORD_TRIPLE_RE = re.compile('[^,;]+,\\s*(?!\\s*(?:and|or|&|\\u0438|\\u0438\\u043b\\u0438)\\b)[^,;]+?\\s+(?:and|or|&|\\u0438|\\u0438\\u043b\\u0438)\\s+\\S', re.I)
_TITLE_OXFORD_TRIPLE_RE = re.compile('[^,;]+,\\s*[^,;]+,\\s*(?:and|or|&|\\u0438|\\u0438\\u043b\\u0438)(?:\\s|$)', re.I)
_TITLE_PLUS_SLASH_TRIPLE_RE = re.compile('(?:\\S+\\s+\\+\\s+[^+;:,]+?\\s+\\+\\s+\\S+|\\S+\\s+/\\s+[^/;:,]+?\\s+/\\s+\\S+)')
# 2026-11-26 "Move repository and grounding subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/382
class Linter:
	__normalize_fn = None
	# @used-by :meth:`Linter.lint()`
	@staticmethod
	def __check_body_blocks(text: str, out: list[dict[str, Any]], *, check_structure_policy: bool, parent_number: int | None, repo: str | None, self_number: int | None) -> None:
		in_fence = False
		for lno, line in enumerate(text.splitlines(), 1):
			stripped = line.strip()
			if _PSEUDO_FENCE_RE.match(stripped):
				out.append({'code': 'BROKEN_CODE_FENCE', 'line': lno, 'message': f'Line {lno} has 2-backtick pseudo-fence "{stripped}" instead of 3 backticks (caused by doubled backticks in PowerShell @"..."@)'})
			if stripped.startswith('```'):
				in_fence = not in_fence
			elif not in_fence and 0 != line.count('`') % 2:
				out.append({'code': 'UNBALANCED_INLINE_BACKTICKS', 'line': lno, 'message': f"Line {lno} has an odd number of inline backticks ({line.count('`')})"})
		if in_fence:
			out.append({'code': 'UNCLOSED_CODE_FENCE', 'message': 'Markdown has an unclosed ``` fenced code block'})
		from Df.Harness.lib.grounding_md import dfh_find_markdown_table_lines
		from agent_tools.repo_link_gate import chat_repo_link_issues
		for tbl_ln in dfh_find_markdown_table_lines(text):
			out.append({'code': 'MARKDOWN_TABLE_FORBIDDEN', 'line': tbl_ln, 'message': f'Line {tbl_ln} contains a Markdown table, which is forbidden by DOC-4; rewrite as structured prose or a list'})
		for repo_err in chat_repo_link_issues(text):
			out.append({'code': 'REPO_LINK_FORBIDDEN', 'message': repo_err})
		Linter.__check_body_policy(text, out, check_structure_policy=check_structure_policy, parent_number=parent_number, repo=repo, self_number=self_number)
	# @used-by :meth:`Linter.__check_body_blocks()`
	@staticmethod
	def __check_body_policy(text: str, out: list[dict[str, Any]], *, check_structure_policy: bool, parent_number: int | None, repo: str | None, self_number: int | None) -> None:
		if 150 <= len(text) and '`' not in text and any((k in text for k in _TECH_MARKERS)):
			out.append({'code': 'STRIPPED_ALL_BACKTICKS', 'message': 'Technical issue body contains 0 backticks (caused by unescaped backticks in PowerShell double-quoted string)'})
		if None is not parent_number and (not Linter.body_references_parent(text, repo, parent_number)):
			repo_hint = repo or '<owner>/<repo>'
			out.append({'code': 'MISSING_PARENT_ISSUE_LINK', 'message': f'Child subtask issue body must explicitly link to parent issue #{parent_number} (e.g. "Parent: https://github.com/{repo_hint}/issues/{parent_number}")'})
		if check_structure_policy:
			m_roots = Linter.extract_unlinked_m_subtasks(text, self_number=self_number, parent_number=parent_number)
			if 2 <= len(m_roots):
				joined_m = ', '.join(m_roots)
				out.append({'code': 'BUNDLED_SUBTASKS_IN_SINGLE_ISSUE', 'message': f'Issue body bundles multiple autonomous remediation subtasks ({joined_m}); document the original problem in a parent issue and create a separate child issue (--parent <N>) with its own commit for each autonomous subtask'})
			if None is parent_number:
				Linter.check_arch_policy(text, out)
	# @used-by :meth:`Linter.lint()`
	@staticmethod
	def __check_encoding_and_patterns(text: str, out: list[dict[str, Any]]) -> None:
		if '\ufeff' in text:
			out.append({'code': 'UTF8_BOM', 'message': 'Contains UTF-8 BOM (U+FEFF), which breaks ATX Markdown headings at the start of a file'})
		if '\ufffd' in text:
			out.append({'code': 'UNICODE_REPLACEMENT', 'message': 'Contains Unicode replacement character (U+FFFD)'})
		for idx, ch in enumerate(text):
			code = ord(ch)
			if 32 > code and ch not in ('\r', '\n', '\t') or 127 == code:
				out.append({'code': 'CONTROL_CHAR', 'offset': idx, 'char': f'U+{code:04X}', 'message': f'Contains ASCII control character U+{code:04X} at offset {idx} (caused by PowerShell backtick escapes such as `0, `a, `b, `f, `v inside "..." or @"..."@)'})
				break
		views = {'full': text, 'no_code': _CODE_SPAN_RE.sub('', text), 'strip': text.strip()}
		for view_key, pat, code_name, msg in _PATTERN_RULES:
			if pat.search(views[view_key]):
				out.append({'code': code_name, 'message': msg})
	# @used-by :meth:`Linter.has_enumerated_slop_title()`
	@staticmethod
	def __clause_has_triple_enumeration(clause: str) -> bool:
		c = clause.strip()
		if not c:
			r = False
		elif 2 <= c.count(';') or bool(_TITLE_PLUS_SLASH_TRIPLE_RE.search(c)):
			r = True
		else:
			rest = _TITLE_INTRO_SUBORD_RE.sub('', c, count=1)
			if rest == c:
				rest = _TITLE_INTRO_PREP_RE.sub('', c, count=1)
			r = 2 <= rest.count(',') or bool(_TITLE_OXFORD_TRIPLE_RE.search(rest)) or bool(_TITLE_NON_OXFORD_TRIPLE_RE.search(rest))
		return r
	# @used-by :meth:`Linter.extract_unlinked_m_subtasks()`
	@staticmethod
	def __collect_m_subtask_groups(clean: str) -> dict[str, list[str]]:
		by_root: dict[str, list[str]] = {}
		cur_root: str | None = None
		for line in clean.splitlines():
			m = _M_SUBTASK_LINE_RE.match(line)
			if m:
				cur_root = m.group('mid').upper()
				by_root.setdefault(cur_root, []).append(line)
			elif None is not cur_root and line[:1] in (' ', '\t') and line.strip() and (not re.match('^\\s*#{1,6}\\s+', line)):
				by_root[cur_root].append(line)
			else:
				cur_root = None
		return by_root
	# @used-by :meth:`Linter.has_enumerated_slop_title()`
	@staticmethod
	def __has_backtick_enumeration(text: str) -> bool:
		r = False
		for m_bt in re.finditer('`([^`]+)`', text):
			inner_bt = m_bt.group(1)
			if 2 <= inner_bt.count(';') or bool(_TITLE_OXFORD_TRIPLE_RE.search(inner_bt)) or bool(_TITLE_NON_OXFORD_TRIPLE_RE.search(inner_bt)):
				r = True
				break
		return r
	# @used-by :meth:`Linter.parse_parent_arg()`
	@staticmethod
	def __parse_parent_str(s: str, repo: str | None, raw_parent) -> int:
		m_num, m_url = (re.fullmatch('#?(\\d+)', s), _PARENT_ARG_URL_RE.fullmatch(s))
		if m_num:
			val = int(m_num.group(1))
		elif m_url:
			if repo and m_url.group(1).lower() != repo.lower():
				raise ValueError(f'Parent issue URL repository {m_url.group(1)} does not match --repo {repo}')
			val = int(m_url.group(2))
		else:
			raise ValueError(f'Invalid --parent value "{raw_parent}"; expected issue number (#N) or GitHub issue URL')
		if 0 >= val:
			raise ValueError(f'Invalid --parent issue number: {raw_parent}')
		return val
	# @used-by :mod:`agent_tools.issues.linter`
	@classmethod
	def bind_normalize_fn(cls, fn) -> None:
		cls.__normalize_fn = fn
	# @used-by :func:`agent_tools.github_issue.body_references_parent_issue()`
	# @used-by :meth:`Linter.__check_body_policy()`
	@staticmethod
	def body_references_parent(body: str, repo: str | None, parent_number: int) -> bool:
		clean = Linter.strip_fenced_blocks(body)
		pnum = int(parent_number)
		url_hit = bool(repo and re.search(f'https://github\\.com/{re.escape(repo)}/issues/{pnum}(?![0-9])', clean, re.I))
		return url_hit or bool(re.search(f'(?<![A-Za-z0-9_/])#{pnum}\\b', clean))
	# @used-by :func:`agent_tools.issues.linter._check_arch_policy()`
	# @used-by :meth:`Linter.__check_body_policy()`
	@staticmethod
	def check_arch_policy(text: str, out: list[dict[str, Any]]) -> None:
		if TriggerClassifier().classify_markdown(text, is_issue=True, is_parent_issue=True)['triggered']:
			spec_res = SpecValidator().validate(text, require_full_fields=True)
			for err in spec_res['issues']:
				out.append({'code': err['code'], 'message': err['message']})
	# @used-by :func:`agent_tools.github_issue.extract_parent_issue_number()`
	# @used-by :meth:`Df.Harness.Git.IssueWorkflowVerifier.IssueWorkflowVerifier.__extract_parent()`
	# @used-by :meth:`Df.Harness.Issue.EvidenceWorkspace.EvidenceWorkspace.__build_issue_record()`
	# @used-by :meth:`Df.Harness.Issue.EvidenceWorkspace.EvidenceWorkspace.__parse_parent()`
	# @used-by :meth:`Df.Harness.Issue.IssueFetcher.IssueFetcher.fetch()`
	# @used-by :meth:`Df.Harness.Issue.IssueFirstEvaluator.IssueFirstEvaluator.__extract_evidence_parent()`
	# @used-by :meth:`Df.Harness.Issue.IssueFirstInheritor.IssueFirstInheritor.__evidence_parent_number()`
	@staticmethod
	def extract_parent_number(body: str, repo: str | None=None) -> int | None:
		clean = Linter.strip_fenced_blocks(body)
		m = _PARENT_DECL_RE.search(clean)
		if not m or (m.group(1) and repo and m.group(1).lower() != repo.lower()):
			r = None
		else:
			r = int(m.group(2) or m.group(3))
		return r
	# @used-by :func:`agent_tools.github_issue.extract_unlinked_m_subtask_roots()`
	# @used-by :meth:`Linter.__check_body_policy()`
	@staticmethod
	def extract_unlinked_m_subtasks(body: str, *, self_number: int | None=None, parent_number: int | None=None) -> list[str]:
		by_root = Linter.__collect_m_subtask_groups(Linter.strip_fenced_blocks(body))
		if 2 > len(by_root):
			r: list[str] = []
		else:
			excluded = {int(n) for n in (self_number, parent_number) if None is not n}
			unlinked: list[str] = []
			all_child_refs: set[int] = set()
			for root_id, root_lines in by_root.items():
				refs = {int(rm.group(1) or rm.group(2)) for rm in _REF_ID_RE.finditer('\n'.join(root_lines))} - excluded
				if not refs:
					unlinked.append(root_id)
				all_child_refs.update(refs)
			distinct_slots = len(all_child_refs) + (1 if unlinked else 0)
			r = unlinked if 2 <= len(unlinked) else list(by_root) if distinct_slots < len(by_root) else []
		return r
	# @used-by :func:`agent_tools.github_issue.has_enumerated_slop_title()`
	# @used-by :meth:`Linter.lint()`
	@staticmethod
	def has_enumerated_slop_title(title: str) -> bool:
		s = ' '.join((title or '').strip().split())
		r = bool(s and Linter.__has_backtick_enumeration(s))
		if s and (not r):
			s = re.sub('(?<=\\d),(?=\\d{3}\\b)', '', re.sub('`[^`]+`', 'CODE', s))
			while not r:
				m = re.search('\\(([^()]*)\\)|\\[([^\\[\\]]*)\\]', s)
				if not m:
					break
				inner = m.group(1) if None is not m.group(1) else m.group(2)
				r = Linter.__clause_has_triple_enumeration(inner)
				s = s[:m.start()] + 'GROUP' + s[m.end():]
			if not r:
				r = any((Linter.__clause_has_triple_enumeration(part) for part in re.split('\\s*(?::|\\u2014|--)\\s*', s)))
		return r
	# @used-by :func:`agent_tools.github_issue.lint_issue_markdown()`
	def lint(self, text: str, *, is_title: bool=False, target_locale: str='en-US', container_text: str | None=None, check_structure_policy: bool=True, parent_number: int | None=None, repo: str | None=None, self_number: int | None=None) -> list[dict[str, Any]]:
		from Df.Harness.Grounding.LocaleVerifier import LocaleVerifier
		r: list[dict[str, Any]] = []
		if not isinstance(text, str) or not text.strip():
			r.append({'code': 'EMPTY_TEXT', 'message': 'Text is empty or whitespace-only'})
		else:
			if is_title and check_structure_policy and self.has_enumerated_slop_title(text):
				r.append({'code': 'ENUMERATED_SLOP_TITLE', 'message': 'Issue title uses a multi-item enumeration ("X, Y, and Z"); state a single cohesive problem (parent issue) or a single autonomous subtask (child issue) instead of bundling multiple items'})
			self.__check_encoding_and_patterns(text, r)
			if not is_title:
				self.__check_body_blocks(text, r, check_structure_policy=check_structure_policy, parent_number=parent_number, repo=repo, self_number=self_number)
			r.extend(LocaleVerifier(text, target_locale=target_locale, container_text=container_text, is_title=is_title).verify())
		return r
	# @used-by :func:`agent_tools.github_issue.normalize_newlines()`
	# @used-by :meth:`test_df_harness_dedup_s8.DfHarnessDedupS8Tests.test_normalize_and_trim_delegation_to_df()`
	@classmethod
	def normalize_newlines(cls, text: str) -> str:
		return cls.__normalize_fn(text) if None is not cls.__normalize_fn else df_normalize(text)
	# @used-by :func:`agent_tools.github_issue.parse_parent_issue_arg()`
	@staticmethod
	def parse_parent_arg(raw_parent: str | int | None, repo: str | None=None) -> int | None:
		if None is raw_parent or (isinstance(raw_parent, str) and not raw_parent.strip()):
			r = None
		elif isinstance(raw_parent, int) and (not isinstance(raw_parent, bool)):
			if 0 >= raw_parent:
				raise ValueError(f'Invalid --parent issue number: {raw_parent}')
			r = raw_parent
		else:
			r = Linter.__parse_parent_str(str(raw_parent).strip(), repo, raw_parent)
		return r
	# @used-by :func:`Df.Harness.lib.issue.dfh_resolve_title()`
	# @used-by :func:`agent_tools.github_issue.read_utf8_no_bom_file()`
	# @used-by :meth:`Df.Harness.Issue.BatchRunner.BatchRunner.__load_spec()`
	# @used-by :meth:`Df.Harness.Issue.CloseCommentValidator.CloseCommentValidator.validate()`
	@staticmethod
	def read_utf8_no_bom_file(path_str: str) -> tuple[Path, bytes, str]:
		path = Path(path_str).resolve()
		if not path.is_file():
			raise FileNotFoundError(f'Input file not found: {path}')
		raw = path.read_bytes()
		try:
			text = raw.decode('utf-8')
		except UnicodeDecodeError as exc:
			raise ValueError(f'File {path} is not valid UTF-8: {exc}') from exc
		return (path, raw, text)
	# @used-by :meth:`Linter.body_references_parent()`
	# @used-by :meth:`Linter.extract_parent_number()`
	# @used-by :meth:`Linter.extract_unlinked_m_subtasks()`
	@staticmethod
	def strip_fenced_blocks(text: str) -> str:
		return _FENCED_RE.sub('', text or '')
	# @used-by :func:`agent_tools.github_issue._validate_repo()`
	# @used-by :meth:`Df.Harness.Issue.IssueFetcher.IssueFetcher.fetch()`
	@staticmethod
	def validate_repo(repo: str) -> str:
		if not REPO_RE.match(repo or ''):
			raise ValueError(f'Invalid GitHub repository "{repo}"; expected "owner/repo"')
		return repo
	# @used-by :meth:`Df.Harness.Issue.RepoTransferRunner.RepoTransferRunner.transfer()`
	@staticmethod
	def validate_slug_part(value: str, label: str) -> str:
		val = (value or '').strip()
		if not _SLUG_PART_RE.match(val):
			raise ValueError(f'Invalid {label} "{value}"')
		return val
