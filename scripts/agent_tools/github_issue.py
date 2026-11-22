# 2026-11-22 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Enforce similar_projects parity gate, hooks, and documented CLI contract across turn completion and issue lifecycle":
# https://github.com/dmitry-ai/harness/issues/123
# 2026-11-21 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Support V2 `𝐒`/`𝐖` software subtrees and cross-root project relocations in Harness":
# https://github.com/dmitry-ai/harness/issues/113
# 2026-11-20 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Replace V2 verbal directory names with Ⰿ/♕/♙ symbols and add Antigravity hook runner":
# https://github.com/dmitry-ai/harness/issues/103
# 2026-11-20 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Wire V2 filesystem layout across Harness runtime subsystems and shared projections":
# https://github.com/dmitry-ai/harness/issues/101
# 2026-11-19 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Wire project path overlays across Harness subsystems with paths CLI and regression tests":
# https://github.com/dmitry-ai/harness/issues/96
# 2026-11-18 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Fix post-audit edge cases in parent-child issue validation and turn-scoped lifecycle checks":
# https://github.com/dmitry-ai/harness/issues/87
# 2026-11-18 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Enforce parent problem issues and per-subtask child issue commits across issue and Git lifecycle gates":
# https://github.com/dmitry-ai/harness/issues/84
# 2026-11-18 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Reject enumerated multi-item issue titles in df_github_issue.py and active turn lifecycle checks":
# https://github.com/dmitry-ai/harness/issues/83
# 2026-11-14 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Unify declarative CLI routers, scratch-verified --consume-input/stdin loading, and read-back mutations in cli_common.py":
# https://github.com/dmitry-ai/harness/issues/69
# 2026-11-13 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Extract issue_lifecycle.py from completion.py, fix open backlog-issue lifecycle gating, and consolidate Git/issue helpers in git_gate.py":
# https://github.com/dmitry-ai/harness/issues/53
# 2026-10-30 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Implement /df-github-issue skill and df_github_issue.py CLI with UTF-8 file input and mandatory API read-back verification":
# https://github.com/dmitry-ai/harness/issues/20
# 2026-10-31 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Reorganize AI into universal harness repository, translate rules and documentation to English, format per P.md, and enforce issue-driven Git workflow":
# https://github.com/dmitry-ai/harness/issues/26
# 2026-10-31 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Enforce universal harness.py CLI, automatic CDP browser fallback on JS shells, and Evidence verification for external links/anchors/quotes":
# https://github.com/dmitry-ai/harness/issues/27
# 2026-10-31 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Prevent rogue ꘖ directory outside harness meta repo, remove mirror logic, and recognize GIT_OPTIONAL_LOCKS in git gate":
# https://github.com/dmitry-ai/harness/issues/28
# 2026-10-31 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Enforce EXEC-5 code/issue lifecycle gate in answer-prepare, URL-only commit messages, git_shim/hook commit interception, and worktree isolation":
# https://github.com/dmitry-ai/harness/issues/31
# 2026-11-02 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Replace special-case grounding/locale regexes with universal locale, relational claim arity, standalone-number, capability, and review gates":
# https://github.com/dmitry-ai/harness/issues/37
# 2026-11-02 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Eliminate flashing Git console windows on Windows via CREATE_NO_WINDOW and journal-watch lifecycle skip":
# https://github.com/dmitry-ai/harness/issues/40
# 2026-11-06 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Enforce defect-to-issue filing gate in code repository audits, open-issue lifecycle separation, and recursive subagent trace aggregation":
# https://github.com/dmitry-ai/harness/issues/48
from __future__ import annotations
import argparse
import json
import os
from pathlib import Path
import re
import subprocess
import sys
from typing import Any
from .cli_common import add_arg_specs, consume_unchanged_files, dump_json
from .git_gate import is_issue_tracked_code_repo, verify_repo_issue_ready_for_close
from .runtime import HARNESS_META
from .source_grounding import verify_target_locale
REPO_RE = re.compile('^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$')
_COMMON_TAIL_SPECS = (('--target-locale', {'default': 'en-US', 'help': 'Expected target locale (default: en-US per TEXT-1).'}), ('--project-root', {'help': 'Optional explicit project root directory.'}), ('--consume-input', {'action': 'store_true', 'help': 'Delete input file(s) after verified publication.'}))
_REPO_SPEC = (('--repo', '-R'), {'required': True, 'help': 'Target repository in owner/repo format.'})
_TITLE_INTRO_SUBORD_RE = re.compile('^(?:when|if|unless|while|after|before|once|where|whenever|although|though|since|because|\\u0435\\u0441\\u043b\\u0438|\\u043a\\u043e\\u0433\\u0434\\u0430|\\u043f\\u043e\\u0441\\u043b\\u0435|\\u043f\\u043e\\u043a\\u0430)\\b[^,]*,\\s+', re.I)
_TITLE_INTRO_PREP_RE = re.compile('^(?:in|on|at|for|from|to|by|with|without|under|during|upon|inside|outside|across|via|through|per|\\u0432|\\u0432\\u043e|\\u043d\\u0430|\\u043f\\u0440\\u0438|\\u0431\\u0435\\u0437|\\u0434\\u043b\\u044f|\\u0438\\u0437|\\u043f\\u043e|\\u0447\\u0435\\u0440\\u0435\\u0437)\\s+(?:the\\s+)?[A-Za-z0-9_\\u0400-\\u04ff./:-]+(?:\\s+[A-Za-z0-9_\\u0400-\\u04ff./:-]+){0,6},\\s+', re.I)
_TITLE_OXFORD_TRIPLE_RE = re.compile('[^,;]+,\\s*[^,;]+,\\s*(?:and|or|&|\\u0438|\\u0438\\u043b\\u0438)(?:\\s|$)', re.I)
_TITLE_NON_OXFORD_TRIPLE_RE = re.compile('[^,;]+,\\s*(?!\\s*(?:and|or|&|\\u0438|\\u0438\\u043b\\u0438)\\b)[^,;]+?\\s+(?:and|or|&|\\u0438|\\u0438\\u043b\\u0438)\\s+\\S', re.I)
_TITLE_PLUS_SLASH_TRIPLE_RE = re.compile('(?:\\S+\\s+\\+\\s+[^+;:,]+?\\s+\\+\\s+\\S+|\\S+\\s+/\\s+[^/;:,]+?\\s+/\\s+\\S+)')
_PARENT_ARG_URL_RE = re.compile('^https://github\\.com/([A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+)/issues/(\\d+)/?$')
_PARENT_DECL_RE = re.compile('(?im)^\\s*(?:[-*+]\\s+)?(?:\\*\\*|__)?(?:parent(?:\\s+issue)?|subtask\\s+of|child\\s+of|part\\s+of)(?:(?:\\*\\*|__)\\s*[:\\u2014-]|\\s*[:\\u2014-]\\s*(?:\\*\\*|__)?)\\s*(?:(?:\\[[^\\]]*\\]\\()?https://github\\.com/([A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+)/issues/(\\d+)\\)?|#(\\d+)\\b)')
_M_SUBTASK_LINE_RE = re.compile('^(?:\\s*#{1,6}\\s+(?:\\d+(?:\\.\\d+)*\\.?\\s*)?|\\s*(?:[-*+]|\\d+[.)])\\s+)(?:\\*\\*|__|`|\\u00ab|"|\\\')*(?:(?i:implement|fix|add|enforce|update|resolve|subtask|method|\\u0440\\u0435\\u0430\\u043b\\u0438\\u0437\\u043e\\u0432\\u0430\\u0442\\u044c|\\u0438\\u0441\\u043f\\u0440\\u0430\\u0432\\u0438\\u0442\\u044c|\\u0434\\u043e\\u0431\\u0430\\u0432\\u0438\\u0442\\u044c|\\u043f\\u043e\\u0434\\u0437\\u0430\\u0434\\u0430\\u0447\\u0430|\\u043c\\u0435\\u0442\\u043e\\u0434)\\s+)?(?:\\*\\*|__|`|\\u00ab|"|\\\')*(?P<mid>M-(?:[A-Za-z]+-)*\\d+)[A-Za-z]?\\b', re.M)
_consume_files = consume_unchanged_files
def _strip_fenced_blocks(text: str) -> str:
	return re.sub('```[\\s\\S]*?```', '', text or '')
def parse_parent_issue_arg(raw_parent: str | int | None, repo: str | None=None) -> int | None:
	if None is raw_parent:
		return None
	if isinstance(raw_parent, int) and (not isinstance(raw_parent, bool)):
		if 0 >= raw_parent:
			raise ValueError(f'Invalid --parent issue number: {raw_parent}')
		return raw_parent
	s = str(raw_parent).strip()
	if not s:
		return None
	m_num = re.fullmatch('#?(\\d+)', s)
	if m_num:
		val = int(m_num.group(1))
		if 0 >= val:
			raise ValueError(f'Invalid --parent issue number: {raw_parent}')
		return val
	m_url = _PARENT_ARG_URL_RE.fullmatch(s)
	if m_url:
		if repo and m_url.group(1).lower() != repo.lower():
			raise ValueError(f'Parent issue URL repository {m_url.group(1)} does not match --repo {repo}')
		val = int(m_url.group(2))
		if 0 >= val:
			raise ValueError(f'Invalid --parent issue number: {raw_parent}')
		return val
	raise ValueError(f'Invalid --parent value "{raw_parent}"; expected issue number (#N) or GitHub issue URL')
def extract_parent_issue_number(body: str, repo: str | None=None) -> int | None:
	clean = _strip_fenced_blocks(body)
	m = _PARENT_DECL_RE.search(clean)
	if not m:
		return None
	if m.group(1) and repo and (m.group(1).lower() != repo.lower()):
		return None
	return int(m.group(2) or m.group(3))
def body_references_parent_issue(body: str, repo: str | None, parent_number: int) -> bool:
	clean = _strip_fenced_blocks(body)
	pnum = int(parent_number)
	if repo and re.search(f'https://github\\.com/{re.escape(repo)}/issues/{pnum}(?![0-9])', clean, re.I):
		return True
	return bool(re.search(f'(?<![A-Za-z0-9_/])#{pnum}\\b', clean))
def extract_unlinked_m_subtask_roots(body: str, *, self_number: int | None=None, parent_number: int | None=None) -> list[str]:
	clean = _strip_fenced_blocks(body)
	by_root: dict[str, list[str]] = {}
	cur_root: str | None = None
	for line in clean.splitlines():
		m = _M_SUBTASK_LINE_RE.match(line)
		if m:
			cur_root = m.group('mid').upper()
			by_root.setdefault(cur_root, []).append(line)
			continue
		if None is not cur_root:
			if line[:1] in (' ', '\t') and line.strip() and (not re.match('^\\s*#{1,6}\\s+', line)):
				by_root[cur_root].append(line)
			else:
				cur_root = None
	roots = list(by_root)
	if 2 > len(roots):
		return []
	excluded = {int(n) for n in (self_number, parent_number) if None is not n}
	unlinked: list[str] = []
	all_child_refs: set[int] = set()
	for root_id, root_lines in by_root.items():
		group_text = '\n'.join(root_lines)
		refs = {int(rm.group(1) or rm.group(2)) for rm in re.finditer('(?:#(\\d+)\\b|https://github\\.com/[^\\s)]+/issues/(\\d+)\\b)', group_text)} - excluded
		if not refs:
			unlinked.append(root_id)
		all_child_refs.update(refs)
	if 2 <= len(unlinked):
		return unlinked
	distinct_slots = len(all_child_refs) + (1 if unlinked else 0)
	if distinct_slots < len(roots):
		return roots
	return []
def _clause_has_triple_enumeration(clause: str) -> bool:
	c = clause.strip()
	if not c:
		return False
	if 2 <= c.count(';') or bool(_TITLE_PLUS_SLASH_TRIPLE_RE.search(c)):
		return True
	rest = _TITLE_INTRO_SUBORD_RE.sub('', c, count=1)
	if rest == c:
		rest = _TITLE_INTRO_PREP_RE.sub('', c, count=1)
	return 2 <= rest.count(',') or bool(_TITLE_OXFORD_TRIPLE_RE.search(rest)) or bool(_TITLE_NON_OXFORD_TRIPLE_RE.search(rest))
def has_enumerated_slop_title(title: str) -> bool:
	s = ' '.join((title or '').strip().split())
	if not s:
		return False
	for m_bt in re.finditer('`([^`]+)`', s):
		inner_bt = m_bt.group(1)
		if 2 <= inner_bt.count(';') or bool(_TITLE_OXFORD_TRIPLE_RE.search(inner_bt)) or bool(_TITLE_NON_OXFORD_TRIPLE_RE.search(inner_bt)):
			return True
	s = re.sub('`[^`]+`', 'CODE', s)
	s = re.sub('(?<=\\d),(?=\\d{3}\\b)', '', s)
	while True:
		m = re.search('\\(([^()]*)\\)|\\[([^\\[\\]]*)\\]', s)
		if not m:
			break
		inner = m.group(1) if None is not m.group(1) else m.group(2)
		if _clause_has_triple_enumeration(inner):
			return True
		s = s[:m.start()] + 'GROUP' + s[m.end():]
	return any((_clause_has_triple_enumeration(part) for part in re.split('\\s*(?::|\\u2014|--)\\s*', s)))
def _run_verified_mutation(*, action: str, repo: str, consumable: list[tuple[Path, bytes]], target_locale: str, container_text: str | None, expected_title: str | None, expected_body: str | None, write_fn, read_fn, kind: str, id_key: str, consume_input: bool, project_root: str | Path | None, parent_number: int | None=None, self_number: int | None=None, check_structure_policy: bool=True, post_write_fn=None) -> int:
	eff_structure = check_structure_policy and ('comment' != kind)
	title_errors = lint_issue_markdown(expected_title, is_title=True, target_locale=target_locale, container_text=container_text, check_structure_policy=eff_structure) if None is not expected_title else []
	body_errors = lint_issue_markdown(expected_body, is_title=False, target_locale=target_locale, container_text=container_text, check_structure_policy=eff_structure, parent_number=parent_number, repo=repo, self_number=self_number) if None is not expected_body else []
	if title_errors or body_errors:
		err_out: dict[str, Any] = {'ok': False, 'action': action, 'stage': 'pre_flight_lint', 'repo': repo, 'body_errors': body_errors}
		if 'comment' != kind:
			err_out['title_errors'] = title_errors
		dump_json(err_out)
		r = 2
	else:
		ident = write_fn()
		fetched = read_fn(ident)
		remote_title = fetched.get('title') or ''
		remote_body = fetched.get('body') or ''
		eff_self = self_number if None is not self_number else ident if 'issue' == kind and isinstance(ident, int) else None
		post_title_errors = lint_issue_markdown(remote_title, is_title=True, target_locale=target_locale, container_text=container_text, check_structure_policy=eff_structure) if None is not expected_title else []
		post_body_errors = lint_issue_markdown(remote_body, is_title=False, target_locale=target_locale, container_text=container_text, check_structure_policy=eff_structure, parent_number=parent_number, repo=repo, self_number=eff_self) if None is not expected_body else []
		title_match = True if None is expected_title else normalize_newlines(remote_title) == normalize_newlines(expected_title)
		body_match = True if None is expected_body else normalize_newlines(remote_body) == normalize_newlines(expected_body)
		exact_match = title_match and body_match
		if exact_match and (not post_title_errors) and (not post_body_errors):
			extra_out = post_write_fn(ident, fetched) if None is not post_write_fn else None
			_persist_issue_evidence(consumable, repo, fetched, kind=kind, action=action, project_root=project_root, parent_number=parent_number)
			removed = _consume_files(consumable) if consume_input else []
			out_payload: dict[str, Any] = {'ok': True, 'action': action, 'repo': repo, id_key: ident, 'html_url': fetched.get('html_url'), 'verified': True, 'body_chars': len(remote_body), 'consumed_files': removed}
			if 'issue' == kind:
				eff_parent = parent_number if None is not parent_number else extract_parent_issue_number(remote_body, repo)
				if None is not eff_parent and eff_parent != ident:
					out_payload['parent_number'] = int(eff_parent)
					out_payload['parent_url'] = f'https://github.com/{repo}/issues/{int(eff_parent)}'
			if isinstance(extra_out, dict):
				out_payload.update(extra_out)
			dump_json(out_payload)
			r = 0
		else:
			post_out: dict[str, Any] = {'ok': False, 'action': action, 'stage': 'post_flight_readback', 'repo': repo, id_key: ident, 'html_url': fetched.get('html_url'), 'exact_match': exact_match, 'body_errors': post_body_errors}
			if 'comment' != kind:
				post_out['title_errors'] = post_title_errors
			dump_json(post_out)
			r = 2
	return r
def normalize_newlines(text: str) -> str:
	return text.replace('\r\n', '\n').replace('\r', '\n')
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
def lint_issue_markdown(text: str, *, is_title: bool=False, target_locale: str='en-US', container_text: str | None=None, check_structure_policy: bool=True, parent_number: int | None=None, repo: str | None=None, self_number: int | None=None) -> list[dict[str, Any]]:
	r: list[dict[str, Any]] = []
	if not isinstance(text, str) or not text.strip():
		r.append({'code': 'EMPTY_TEXT', 'message': 'Text is empty or whitespace-only'})
	else:
		if is_title and check_structure_policy and has_enumerated_slop_title(text):
			r.append({'code': 'ENUMERATED_SLOP_TITLE', 'message': 'Issue title uses a multi-item enumeration ("X, Y, and Z"); state a single cohesive problem (parent issue) or a single autonomous subtask (child issue) instead of bundling multiple items'})
		if '\ufeff' in text:
			r.append({'code': 'UTF8_BOM', 'message': 'Contains UTF-8 BOM (U+FEFF), which breaks ATX Markdown headings at the start of a file'})
		if '\ufffd' in text:
			r.append({'code': 'UNICODE_REPLACEMENT', 'message': 'Contains Unicode replacement character (U+FFFD)'})
		for idx, ch in enumerate(text):
			code = ord(ch)
			if 32 > code and ch not in ('\r', '\n', '\t') or 127 == code:
				r.append({'code': 'CONTROL_CHAR', 'offset': idx, 'char': f'U+{code:04X}', 'message': f'Contains ASCII control character U+{code:04X} at offset {idx} (caused by PowerShell backtick escapes such as `0, `a, `b, `f, `v inside "..." or @"..."@)'})
				break
		no_code = re.sub('```.*?```|`[^`\\r\\n]+`', '', text, flags=re.S)
		pattern_checks = (
			(text, '[^\\r\\n\\t]\\t[A-Za-z_]', 'INLINE_TAB_ESCAPE', 'Contains inline TAB character immediately before an identifier (caused by PowerShell `t expansion)'),
			(text, '\\b\\d+(?::\\d+)*\\?\\d+(?::\\d+)*\\b', 'QUESTION_MARK_RANGE', 'Contains digit?digit range (caused by piping non-ASCII en-dash/em-dash through PowerShell without UTF-8 $OutputEncoding)'),
			(text, '(?<![/.])\\b[A-Za-z]{2,}\\?[a-z]{2,}\\b', 'QUESTION_MARK_WORD_JOIN', 'Contains word?word (caused by piping em-dash \u2014 through PowerShell without UTF-8 $OutputEncoding)'),
			(no_code, '[A-Za-z0-9)\\]]\\s+\\?\\s+[A-Za-z0-9(\\[]', 'QUESTION_MARK_SPACED', 'Contains spaced " ? " in prose outside code (caused by piping em-dash \u2014 without UTF-8 $OutputEncoding)'),
			(text, '(?<![A-Za-z0-9_/])\\?[A-Z][A-Za-z0-9_-]*\\?', 'QUESTION_MARK_QUOTES', 'Contains ?Word? (caused by piping \u00abWord\u00bb or curly quotes without UTF-8 $OutputEncoding)'),
			(text, '(?:^|[\\s(])\\?\\d+(?:\\.\\d+)+\\b', 'QUESTION_MARK_SECTION', 'Contains ?N.M (caused by piping section sign \u00a7N.M without UTF-8 $OutputEncoding)'),
			(text, '\\\\`', 'ESCAPED_BACKTICK', 'Contains literal \\` (bash-style escaped backtick in Markdown)'),
			(text, '(?:^|[\\s(])\\\\[A-Za-z0-9_./:$^*\\[\\]()=-]+(?:\\s+[A-Za-z0-9_./:$^*\\[\\]()=-]+)*\\\\(?=[\\s).,;:!?\\)]|$)', 'BACKSLASH_WRAPPED_CODE', 'Contains \\token\\ wrapped in backslashes (caused by bash-style \\`token\\` inside PowerShell double quotes)'),
			(text, '(?<![A-Za-z0-9_$\\)\\]\\}`"\\\'-])->[A-Za-z_][A-Za-z0-9_]*', 'EATEN_VARIABLE_ARROW', 'Contains bare ->method without object receiver (caused by PowerShell expanding $this or $var to empty string)'),
			(text, '\\(\\s*,\\s*\\)|\\(\\s*,\\s*[^)\\s]|(?<!,)\\bempty\\(\\s*\\)|\\?callable\\s+=\\s*null', 'EATEN_VARIABLE_ARG', 'Contains empty function parameter/argument slot (caused by PowerShell expanding $var to empty string)'),
			(text, '<(?:type|argument|preference|plugin|virtualType|job|group)\\b[^>]*\\b(?:name|xsi:type|id|instance|method)=[^"\\\'\\s>]+', 'UNQUOTED_XML_ATTR', 'Contains unquoted XML attribute (caused by PowerShell 5.1 stripping double quotes when passing --body $var)'),
			(text.strip(), '(\\(\\s*\\\\?|\\b(?:version|from|to|in|at|with|by|for)\\s*`?)$', 'TRUNCATED_END', 'Text ends abruptly with an unfinished token or open delimiter (caused by PowerShell `0 -> NUL byte truncation)'),
		)
		for hay, pat, code_name, msg in pattern_checks:
			if re.search(pat, hay):
				r.append({'code': code_name, 'message': msg})
		if not is_title:
			in_fence = False
			for lno, line in enumerate(text.splitlines(), 1):
				stripped = line.strip()
				if re.match('^``[a-zA-Z]*$', stripped):
					r.append({'code': 'BROKEN_CODE_FENCE', 'line': lno, 'message': f'Line {lno} has 2-backtick pseudo-fence "{stripped}" instead of 3 backticks (caused by doubled backticks in PowerShell @"..."@)'})
				if stripped.startswith('```'):
					in_fence = not in_fence
				elif not in_fence and 0 != line.count('`') % 2:
					r.append({'code': 'UNBALANCED_INLINE_BACKTICKS', 'line': lno, 'message': f"Line {lno} has an odd number of inline backticks ({line.count('`')})"})
			if in_fence:
				r.append({'code': 'UNCLOSED_CODE_FENCE', 'message': 'Markdown has an unclosed ``` fenced code block'})
			if 150 <= len(text) and '`' not in text and any((k in text for k in ('app/code/', 'vendor/', '::', '### Problem', '## 1. Root Cause', '## Summary'))):
				r.append({'code': 'STRIPPED_ALL_BACKTICKS', 'message': 'Technical issue body contains 0 backticks (caused by unescaped backticks in PowerShell double-quoted string)'})
			if None is not parent_number and (not body_references_parent_issue(text, repo, parent_number)):
				r.append({'code': 'MISSING_PARENT_ISSUE_LINK', 'message': f'Child subtask issue body must explicitly link to parent issue #{parent_number} (e.g. "Parent: https://github.com/{repo or "<owner>/<repo>"}/issues/{parent_number}")'})
			if check_structure_policy:
				m_roots = extract_unlinked_m_subtask_roots(text, self_number=self_number, parent_number=parent_number)
				if 2 <= len(m_roots):
					r.append({'code': 'BUNDLED_SUBTASKS_IN_SINGLE_ISSUE', 'message': f'Issue body bundles multiple autonomous remediation subtasks ({", ".join(m_roots)}); document the original problem in a parent issue and create a separate child issue (--parent <N>) with its own commit for each autonomous subtask'})
		r.extend(verify_target_locale(text, target_locale=target_locale, container_text=container_text, is_title=is_title))
	return r
def _validate_repo(repo: str) -> str:
	if not REPO_RE.match(repo or ''):
		raise ValueError(f'Invalid GitHub repository "{repo}"; expected "owner/repo"')
	r = repo
	return r
def _gh_api(endpoint: str, *, method: str='GET', payload: dict[str, Any] | None=None, paginate: bool=False) -> Any:
	cmd = ['gh', 'api', endpoint]
	if 'GET' != method:
		cmd.extend(['-X', method])
	if paginate:
		cmd.append('--paginate')
	input_bytes = None
	if None is not payload:
		cmd.extend(['--input', '-'])
		input_bytes = json.dumps(payload, ensure_ascii=False).encode('utf-8')
	proc = subprocess.run(cmd, input=input_bytes, capture_output=True, check=False, creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
	if 0 != proc.returncode:
		stderr = proc.stderr.decode('utf-8', errors='replace').strip()
		stdout = proc.stdout.decode('utf-8', errors='replace').strip()
		raise RuntimeError(f'gh api {method} {endpoint} failed (exit {proc.returncode}): {stderr or stdout}')
	raw_out = proc.stdout.decode('utf-8')
	if not raw_out.strip():
		r = None
	elif not (paginate and raw_out.lstrip().startswith('[')):
		r = json.loads(raw_out)
	else:
		decoder = json.JSONDecoder()
		idx = 0
		merged: list[Any] = []
		n = len(raw_out)
		while idx < n:
			while idx < n and raw_out[idx].isspace():
				idx += 1
			if idx >= n:
				break
			obj, idx = decoder.raw_decode(raw_out, idx)
			if not isinstance(obj, list):
				merged.append(obj)
			else:
				merged.extend(obj)
		r = merged
	return r
def _repo_matches_github_slug(code_repo: Path, repo: str) -> bool:
	cfg_file = code_repo / '.git/config'
	r = False
	if cfg_file.is_file():
		try:
			cfg_text = cfg_file.read_text(encoding='utf-8', errors='replace')
			r = bool(re.search(f'github\\.com[:/]{re.escape(repo)}(?:\\.git)?/?(?:\\s|$)', cfg_text, re.I))
		except OSError:
			r = False
	return r
def _find_local_code_repo(repo: str, project_root: str | Path | None=None, source_files: list[tuple[Path, bytes]] | None=None) -> Path | None:
	from .path_registry import project_paths, store_value
	r = None
	v2_code_rels = ('\u2c0f/\u227b/\u2655/\u26ef', 'Artifacts/\u227b/Deliverables/\u26ef')
	candidates: list[Path] = []
	if None is not project_root and str(project_root).strip():
		pr = Path(project_root).resolve()
		try:
			pp = project_paths(pr)
			candidates.extend([*pp.code_repos, *pp.auxiliary_repos.values()])
		except (OSError, ValueError):
			pass
		candidates.extend([pr, pr / 'code', *(pr / rel for rel in v2_code_rels), pr.parent, pr.parent / 'code', *(pr.parent / rel for rel in v2_code_rels)])
	for fpath, _ in source_files or []:
		resolved = fpath.resolve()
		try:
			pp_f = project_paths(resolved)
			candidates.extend([*pp_f.code_repos, *pp_f.auxiliary_repos.values()])
		except (OSError, ValueError):
			pass
		for anc in (resolved, *resolved.parents):
			candidates.extend([anc, anc / 'code', *(anc / rel for rel in v2_code_rels)])
	cwd = Path.cwd().resolve()
	for anc in (cwd, *cwd.parents):
		candidates.extend([anc, anc / 'code', *(anc / rel for rel in v2_code_rels)])
	seen: set[Path] = set()
	for cand in candidates:
		if cand not in seen:
			seen.add(cand)
			if cand.is_dir() and _repo_matches_github_slug(cand, repo):
				r = cand
				break
	if None is r:
		try:
			from .path_registry import _candidate_discovery_roots, load_registry
			reg = load_registry()
			_, disc_roots = _candidate_discovery_roots(reg)
			for d_root in disc_roots:
				try:
					pp_d = project_paths(d_root, registry=reg)
					for cand in (*pp_d.code_repos, *pp_d.auxiliary_repos.values()):
						if cand not in seen:
							seen.add(cand)
							if cand.is_dir() and _repo_matches_github_slug(cand, repo):
								r = cand
								break
				except (OSError, ValueError):
					continue
				if None is not r:
					break
		except (OSError, ValueError):
			pass
	if None is r:
		for raw_search_root in store_value('code_repo_search_roots'):
			search_root = Path(raw_search_root)
			if not search_root.is_dir():
				continue
			try:
				for pattern in ('*/.git/config', '**/code/.git/config', '**/\u26ef/.git/config', '**/\U0001d412/.git/config'):
					for cfg in search_root.glob(pattern):
						code_dir = cfg.parent.parent.resolve()
						if code_dir not in seen:
							seen.add(code_dir)
							if _repo_matches_github_slug(code_dir, repo):
								r = code_dir
								break
					if None is not r:
						break
			except OSError:
				pass
			if None is not r:
				break
	return r
find_local_code_repo = _find_local_code_repo
def _meta_dir_for_project_root(proj_root: Path) -> Path | None:
	from .path_registry import project_paths
	proj_root = proj_root.resolve()
	try:
		pp = project_paths(proj_root)
		if pp.agent_dir.is_dir() or pp.has_overlay or 2 <= pp.fs_version or (pp.root / '_').is_dir():
			return pp.agent_dir
	except (OSError, ValueError):
		pass
	if (proj_root / '_/\ua616').is_dir() or (proj_root / '_').is_dir():
		r = proj_root / '_' / '\ua616'
	elif (proj_root / '\ua616').is_dir():
		r = proj_root / '\ua616'
	else:
		r = None
	return r
def _issue_target_for_path(target_path: Path) -> tuple[Path, Path] | None:
	from .path_registry import project_paths, store_path, workspace_override
	target_path = target_path.resolve()
	try:
		pp = project_paths(target_path)
		if None is not workspace_override(pp.root):
			return (store_path('github_evidence_dir'), pp.turns_dir)
		if pp.agent_dir.is_dir() or pp.has_overlay or 2 <= pp.fs_version or (pp.root / '_').is_dir() or pp.turns_dir.is_dir() or pp.evidence_dir.is_dir():
			return (pp.evidence_dir / 'GitHub', pp.turns_dir)
	except (OSError, ValueError):
		pass
	if (target_path / '_/\ua616').is_dir() or (target_path / '_').is_dir():
		ag = target_path / '_' / '\ua616'
		return (ag / 'KB/Evidence/GitHub', ag / 'data/turns')
	if (target_path / '\ua616').is_dir():
		ag = target_path / '\ua616'
		return (ag / 'KB/Evidence/GitHub', ag / 'data/turns')
	return None
def _resolve_issue_targets(source_files: list[tuple[Path, bytes]], repo: str, project_root: str | Path | None=None) -> list[tuple[Path, Path]]:
	from .path_registry import project_paths, store_path, store_value, workspace_override
	r: list[tuple[Path, Path]] = []
	def _add(pair: tuple[Path, Path] | None) -> None:
		if None is not pair:
			norm = (pair[0].resolve(), pair[1].resolve())
			if norm not in r:
				r.append(norm)
	if None is not project_root and str(project_root).strip():
		pr = Path(project_root).resolve()
		hit = _issue_target_for_path(pr)
		if None is hit:
			pp = project_paths(pr)
			hit = (store_path('github_evidence_dir'), pp.turns_dir) if None is not workspace_override(pp.root) else (pp.evidence_dir / 'GitHub', pp.turns_dir)
		_add(hit)
	code_repo = _find_local_code_repo(repo, project_root=project_root, source_files=source_files)
	if None is not code_repo:
		_add(_issue_target_for_path(code_repo))
	for fpath, _ in source_files:
		try:
			_add(_issue_target_for_path(fpath))
		except (OSError, ValueError):
			pass
	primary_repo = str(store_value('primary_github_repo') or '').lower()
	if not r or (primary_repo and primary_repo == repo.lower()):
		_add((store_path('github_evidence_dir'), store_path('data_dir') / 'turns'))
	return r
def _record_issue_in_open_turns(turns_dir: Path, repo: str, record: dict[str, Any], action: str | None) -> None:
	issue_num = record.get('number') or record.get('issue_number')
	if None is issue_num:
		m = re.search('/issues/(\\d+)\\b', str(record.get('html_url') or record.get('url') or ''))
		if m:
			issue_num = int(m.group(1))
	if turns_dir.is_dir() and None is not issue_num:
		issue_url = f'https://github.com/{repo}/issues/{issue_num}'
		codex_tid = (os.environ.get('CODEX_THREAD_ID') or '').strip()
		has_non_codex_open = False
		loaded_turns: list[tuple[Path, dict[str, Any]]] = []
		for tfile in turns_dir.glob('*.json'):
			if tfile.name.endswith(('-checkpoint-recovery.json', '-violation-recovery.json', '-similar-exemptions.json')):
				continue
			try:
				tdata = json.loads(tfile.read_text(encoding='utf-8'))
			except (OSError, ValueError):
				continue
			if not isinstance(tdata, dict) or 'open' != tdata.get('status'):
				continue
			loaded_turns.append((tfile, tdata))
			if 'codex' != str(tdata.get('platform') or '').strip().lower():
				has_non_codex_open = True
		for tfile, tdata in loaded_turns:
			t_plat = str(tdata.get('platform') or '').strip().lower()
			t_cid = str(tdata.get('conversation_id') or '').strip()
			if codex_tid:
				if t_cid != codex_tid:
					continue
			elif has_non_codex_open and 'codex' == t_plat:
				continue
			gh_issues = tdata.setdefault('github_issues', {})
			prev = gh_issues.get(issue_url) if isinstance(gh_issues.get(issue_url), dict) else {}
			state = record.get('state') or prev.get('state') or ('closed' if 'close' == action else 'open')
			comment_ids = list(prev.get('comment_ids') or [])
			if 'comment' == record.get('kind') and None is not record.get('id') and (record.get('id') not in comment_ids):
				comment_ids.append(record.get('id'))
			actions = list(prev.get('actions') or [])
			act_name = action or record.get('kind', 'issue')
			if act_name and act_name not in actions:
				actions.append(act_name)
			parent_num = record.get('parent_number') if isinstance(record.get('parent_number'), int) else prev.get('parent_number')
			entry: dict[str, Any] = {'repo': repo, 'number': issue_num, 'url': issue_url, 'state': state, 'state_reason': record.get('state_reason') or prev.get('state_reason'), 'last_action': act_name, 'actions': actions, 'comment_ids': comment_ids}
			if codex_tid:
				entry['recorded_conversation_id'] = codex_tid
				entry['recorded_platform'] = 'codex'
			elif has_non_codex_open:
				entry['recorded_platform'] = 'non_codex'
			if isinstance(parent_num, int) and parent_num != issue_num:
				entry['parent_number'] = parent_num
				entry['parent_url'] = f'https://github.com/{repo}/issues/{parent_num}'
			gh_issues[issue_url] = entry
			try:
				tfile.write_bytes((json.dumps(tdata, ensure_ascii=False, indent=2) + '\n').encode('utf-8'))
			except OSError:
				pass
def _load_saved_issue_container_text(source_files: list[tuple[Path, bytes]], repo: str, issue_num: int | None, project_root: str | Path | None=None) -> str | None:
	r = None
	if None is not issue_num:
		safe_repo = repo.replace('/', '__')
		for gh_root, _ in _resolve_issue_targets(source_files, repo, project_root=project_root):
			cand = gh_root / safe_repo / f'issue-{int(issue_num)}.json'
			if cand.is_file():
				try:
					data = json.loads(cand.read_text(encoding='utf-8'))
					if isinstance(data, dict):
						r = f"{data.get('title') or ''}\n{data.get('body') or ''}".strip() or None
						break
				except (OSError, ValueError):
					continue
	return r
def _find_existing_issue_comments(source_files: list[tuple[Path, bytes]], repo: str, issue_num: int, project_root: str | Path | None=None) -> list[int]:
	safe_repo = repo.replace('/', '__')
	r: list[int] = []
	for gh_root, _ in _resolve_issue_targets(source_files, repo, project_root=project_root):
		gh_dir = gh_root / safe_repo
		if not gh_dir.is_dir():
			continue
		for cfile in sorted(gh_dir.glob('comment-*.json')):
			try:
				data = json.loads(cfile.read_text(encoding='utf-8'))
			except (OSError, ValueError):
				continue
			if not isinstance(data, dict):
				continue
			cid = data.get('id')
			c_iss = data.get('issue_number') or data.get('number')
			if None is c_iss:
				m = re.search('/issues/(\\d+)\\b', str(data.get('html_url') or data.get('url') or ''))
				if m:
					c_iss = int(m.group(1))
			if int(issue_num) == c_iss and isinstance(cid, int) and (cid not in r):
				r.append(cid)
	return r
def _saved_issue_parent_number(source_files: list[tuple[Path, bytes]], repo: str, issue_num: int | None, project_root: str | Path | None=None) -> int | None:
	r = None
	if None is not issue_num:
		safe_repo = repo.replace('/', '__')
		for gh_root, _ in _resolve_issue_targets(source_files, repo, project_root=project_root):
			cand = gh_root / safe_repo / f'issue-{int(issue_num)}.json'
			if cand.is_file():
				try:
					data = json.loads(cand.read_text(encoding='utf-8'))
				except (OSError, ValueError):
					continue
				iss_obj = data.get('issue') if isinstance(data, dict) and isinstance(data.get('issue'), dict) else data
				if isinstance(iss_obj, dict):
					pnum = iss_obj.get('parent_number')
					if isinstance(pnum, int) and (not isinstance(pnum, bool)) and pnum != int(issue_num):
						r = pnum
						break
					r = extract_parent_issue_number(str(iss_obj.get('body') or ''), repo)
					if None is not r and r != int(issue_num):
						break
					r = None
	return r
def _verify_and_persist_parent_issue(source_files: list[tuple[Path, bytes]], repo: str, parent_number: int, *, self_number: int | None=None, project_root: str | Path | None=None) -> dict[str, Any]:
	pnum = int(parent_number)
	if None is not self_number and pnum == int(self_number):
		raise ValueError(f'Issue #{self_number} cannot reference itself as --parent')
	safe_repo = repo.replace('/', '__')
	existing_data = None
	for gh_root, _ in _resolve_issue_targets(source_files, repo, project_root=project_root):
		cand = gh_root / safe_repo / f'issue-{pnum}.json'
		if cand.is_file():
			try:
				loaded = json.loads(cand.read_text(encoding='utf-8'))
				if isinstance(loaded, dict) and (loaded.get('html_url') or loaded.get('url')):
					existing_data = loaded.get('issue') if isinstance(loaded.get('issue'), dict) else loaded
					break
			except (OSError, ValueError):
				continue
	if None is existing_data:
		fetched_parent = _gh_api(f'repos/{repo}/issues/{pnum}', method='GET')
		if not isinstance(fetched_parent, dict) or 'pull_request' in fetched_parent:
			raise ValueError(f'Parent target #{pnum} in {repo} is not a valid GitHub issue')
		_persist_issue_evidence(source_files, repo, fetched_parent, kind='issue', action=None, project_root=project_root)
		existing_data = fetched_parent
	return existing_data
def _try_link_github_sub_issue(repo: str, parent_number: int, child_id: Any) -> bool:
	if not isinstance(child_id, int) or isinstance(child_id, bool) or 0 >= child_id:
		return False
	try:
		_gh_api(f'repos/{repo}/issues/{int(parent_number)}/sub_issues', method='POST', payload={'sub_issue_id': int(child_id)})
		return True
	except RuntimeError:
		return False
def find_tracked_child_issues(repo: str, parent_number: int, *, project_root: str | Path | None=None, code_repo: Path | None=None) -> list[dict[str, Any]]:
	pnum = int(parent_number)
	targets = _resolve_issue_targets([], repo, project_root=project_root)
	if None is not code_repo:
		extra = _issue_target_for_path(Path(code_repo).resolve().parent)
		if None is not extra:
			norm_extra = (extra[0].resolve(), extra[1].resolve())
			if norm_extra not in targets:
				targets.append(norm_extra)
	safe_repo = repo.replace('/', '__')
	by_num: dict[int, dict[str, Any]] = {}
	for gh_root, _ in targets:
		gh_dir = gh_root / safe_repo
		if not gh_dir.is_dir():
			continue
		for ifile in sorted(gh_dir.glob('issue-*.json')):
			try:
				data = json.loads(ifile.read_text(encoding='utf-8'))
			except (OSError, ValueError):
				continue
			iss_obj = data.get('issue') if isinstance(data, dict) and isinstance(data.get('issue'), dict) else data
			if not isinstance(iss_obj, dict):
				continue
			num = iss_obj.get('number') or iss_obj.get('issue_number')
			if not isinstance(num, int) or isinstance(num, bool) or num == pnum or num in by_num:
				continue
			body = str(iss_obj.get('body') or '')
			raw_parent = iss_obj.get('parent_number')
			eff_parent = raw_parent if isinstance(raw_parent, int) and (not isinstance(raw_parent, bool)) else extract_parent_issue_number(body, repo)
			if eff_parent != pnum:
				continue
			state = str(iss_obj.get('state') or 'open').strip().lower()
			url = str(iss_obj.get('html_url') or iss_obj.get('url') or f'https://github.com/{repo}/issues/{num}')
			by_num[num] = {'number': num, 'url': url, 'state': state, 'state_reason': iss_obj.get('state_reason'), 'parent_number': pnum}
	return [by_num[k] for k in sorted(by_num)]
def _persist_issue_evidence(source_files: list[tuple[Path, bytes]], repo: str, fetched: dict[str, Any], *, kind: str='issue', action: str | None=None, project_root: str | Path | None=None, parent_number: int | None=None) -> str | None:
	ident = fetched.get('number') if isinstance(fetched, dict) and 'issue' == kind else fetched.get('id') if isinstance(fetched, dict) else None
	r: str | None = None
	if isinstance(fetched, dict) and fetched.get('html_url') and (None is not ident):
		safe_repo = repo.replace('/', '__')
		m_iss = re.search('/issues/(\\d+)\\b', str(fetched.get('html_url') or fetched.get('issue_url') or ''))
		issue_number = fetched.get('number') or (int(m_iss.group(1)) if m_iss else None)
		record = {'url': fetched.get('html_url'), 'html_url': fetched.get('html_url'), 'repo': repo, 'kind': kind, 'number': fetched.get('number'), 'issue_number': issue_number, 'id': fetched.get('id'), 'title': fetched.get('title') or f'{repo}#{ident}', 'state': fetched.get('state'), 'state_reason': fetched.get('state_reason'), 'body': fetched.get('body') or ''}
		if 'issue' == kind:
			eff_parent = parent_number if None is not parent_number else _saved_issue_parent_number(source_files, repo, issue_number, project_root=project_root) or extract_parent_issue_number(record['body'], repo)
			if None is not eff_parent and eff_parent != issue_number:
				record['parent_number'] = int(eff_parent)
				record['parent_url'] = f'https://github.com/{repo}/issues/{int(eff_parent)}'
		payload_bytes = (json.dumps(record, ensure_ascii=False, indent=2) + '\n').encode('utf-8')
		for gh_root, turns_dir in _resolve_issue_targets(source_files, repo, project_root=project_root):
			target = gh_root / safe_repo / f'{kind}-{ident}.json'
			target.parent.mkdir(parents=True, exist_ok=True)
			target.write_bytes(payload_bytes)
			if None is r:
				r = str(target)
			_record_issue_in_open_turns(turns_dir, repo, record, action)
	return r
def _resolve_title(args: argparse.Namespace, consumable: list[tuple[Path, bytes]]) -> str | None:
	if getattr(args, 'title_file', None):
		t_path, t_raw, t_text = read_utf8_no_bom_file(args.title_file)
		consumable.append((t_path, t_raw))
		r = t_text.strip()
	elif None is not getattr(args, 'title', None):
		r = args.title.strip()
	else:
		r = None
	return r
def cmd_lint(args: argparse.Namespace) -> int:
	consumable: list[tuple[Path, bytes]] = []
	target_locale = getattr(args, 'target_locale', 'en-US') or 'en-US'
	repo = _validate_repo(args.repo) if getattr(args, 'repo', None) else None
	parent_num = parse_parent_issue_arg(getattr(args, 'parent', None), repo)
	title = _resolve_title(args, consumable)
	title_errors = lint_issue_markdown(title, is_title=True, target_locale=target_locale) if None is not title else []
	body_errors = lint_issue_markdown(read_utf8_no_bom_file(args.body_file)[2], is_title=False, target_locale=target_locale, parent_number=parent_num, repo=repo) if args.body_file else []
	valid = not title_errors and (not body_errors)
	dump_json({'valid': valid, 'title_errors': title_errors, 'body_errors': body_errors})
	return 0 if valid else 2
def cmd_create(args: argparse.Namespace) -> int:
	repo = _validate_repo(args.repo)
	consumable: list[tuple[Path, bytes]] = []
	target_locale = getattr(args, 'target_locale', 'en-US') or 'en-US'
	project_root = getattr(args, 'project_root', None)
	parent_num = parse_parent_issue_arg(getattr(args, 'parent', None), repo)
	title = _resolve_title(args, consumable)
	if not title:
		raise ValueError('Issue title is required (--title or --title-file)')
	b_path, b_raw, body = read_utf8_no_bom_file(args.body_file)
	consumable.append((b_path, b_raw))
	eff_parent = parent_num if None is not parent_num else extract_parent_issue_number(body, repo)
	payload: dict[str, Any] = {'title': title, 'body': body}
	if args.label:
		labels = [lbl.strip() for item in args.label for lbl in item.split(',') if lbl.strip()]
		if labels:
			payload['labels'] = labels
	if args.assignee:
		assignees = [a.strip() for item in args.assignee for a in item.split(',') if a.strip()]
		if assignees:
			payload['assignees'] = assignees
	if None is not args.milestone:
		payload['milestone'] = args.milestone
	def _write_issue() -> int:
		if None is not eff_parent:
			_verify_and_persist_parent_issue(consumable, repo, eff_parent, project_root=project_root)
		return _gh_api(f'repos/{repo}/issues', method='POST', payload=payload)['number']
	def _after_create(_ident: int, fetched: dict[str, Any]) -> dict[str, Any] | None:
		if None is not eff_parent:
			return {'sub_issue_linked': _try_link_github_sub_issue(repo, eff_parent, fetched.get('id'))}
		return None
	return _run_verified_mutation(action='create', repo=repo, consumable=consumable, target_locale=target_locale, container_text=None, expected_title=title, expected_body=body, write_fn=_write_issue, read_fn=lambda num: _gh_api(f'repos/{repo}/issues/{num}', method='GET'), kind='issue', id_key='number', consume_input=args.consume_input, project_root=project_root, parent_number=eff_parent, post_write_fn=_after_create)
def cmd_edit(args: argparse.Namespace) -> int:
	repo = _validate_repo(args.repo)
	number = args.issue
	consumable: list[tuple[Path, bytes]] = []
	target_locale = getattr(args, 'target_locale', 'en-US') or 'en-US'
	project_root = getattr(args, 'project_root', None)
	parent_num = parse_parent_issue_arg(getattr(args, 'parent', None), repo)
	if None is not parent_num and int(parent_num) == int(number):
		raise ValueError(f'Issue #{number} cannot reference itself as --parent')
	title = _resolve_title(args, consumable)
	body = None
	if args.body_file:
		b_path, b_raw, body = read_utf8_no_bom_file(args.body_file)
		consumable.append((b_path, b_raw))
	if None is title and None is body and (None is args.state) and (None is parent_num):
		raise ValueError('At least one of --title/--title-file, --body-file, --state, or --parent must be provided')
	body_parent = extract_parent_issue_number(body, repo) if None is not body else None
	if None is not body_parent and int(body_parent) == int(number):
		raise ValueError(f'Issue #{number} cannot reference itself as --parent')
	active_parent = parent_num if None is not parent_num else body_parent
	eff_parent = active_parent if None is not active_parent else _saved_issue_parent_number(consumable, repo, number, project_root=project_root)
	if None is title and None is body and (None is args.state) and (None is not parent_num):
		fetched = _gh_api(f'repos/{repo}/issues/{number}', method='GET')
		remote_title = fetched.get('title') or ''
		remote_body = fetched.get('body') or ''
		title_errors = lint_issue_markdown(remote_title, is_title=True, target_locale=target_locale)
		body_errors = lint_issue_markdown(remote_body, is_title=False, target_locale=target_locale, parent_number=parent_num, repo=repo, self_number=number)
		if title_errors or body_errors:
			dump_json({'ok': False, 'action': 'edit', 'stage': 'pre_flight_lint', 'repo': repo, 'number': number, 'title_errors': title_errors, 'body_errors': body_errors})
			return 2
		_verify_and_persist_parent_issue(consumable, repo, parent_num, self_number=number, project_root=project_root)
		linked = _try_link_github_sub_issue(repo, parent_num, fetched.get('id'))
		_persist_issue_evidence(consumable, repo, fetched, kind='issue', action='edit', project_root=project_root, parent_number=parent_num)
		dump_json({'ok': True, 'action': 'edit', 'repo': repo, 'number': number, 'html_url': fetched.get('html_url'), 'verified': True, 'parent_number': int(parent_num), 'parent_url': f'https://github.com/{repo}/issues/{int(parent_num)}', 'sub_issue_linked': linked, 'body_chars': len(remote_body), 'consumed_files': []})
		return 0
	if None is not parent_num and None is body:
		current_remote = _gh_api(f'repos/{repo}/issues/{number}', method='GET')
		remote_body = current_remote.get('body') or ''
		body_errors = lint_issue_markdown(remote_body, is_title=False, target_locale=target_locale, parent_number=parent_num, repo=repo, self_number=number)
		if body_errors:
			dump_json({'ok': False, 'action': 'edit', 'stage': 'pre_flight_lint', 'repo': repo, 'number': number, 'body_errors': body_errors})
			return 2
	container_text = _load_saved_issue_container_text(consumable, repo, number, project_root=project_root)
	payload = {k: v for k, v in (('title', title), ('body', body), ('state', args.state)) if None is not v}
	def _write_edit() -> int:
		if None is not active_parent:
			_verify_and_persist_parent_issue(consumable, repo, active_parent, self_number=number, project_root=project_root)
		_gh_api(f'repos/{repo}/issues/{number}', method='PATCH', payload=payload)
		return number
	def _after_edit(_ident: int, fetched: dict[str, Any]) -> dict[str, Any] | None:
		if None is not active_parent:
			return {'sub_issue_linked': _try_link_github_sub_issue(repo, active_parent, fetched.get('id'))}
		return None
	return _run_verified_mutation(action='edit', repo=repo, consumable=consumable, target_locale=target_locale, container_text=container_text, expected_title=title, expected_body=body, write_fn=_write_edit, read_fn=lambda num: _gh_api(f'repos/{repo}/issues/{num}', method='GET'), kind='issue', id_key='number', consume_input=args.consume_input, project_root=project_root, parent_number=eff_parent, self_number=number, post_write_fn=_after_edit)
def cmd_comment(args: argparse.Namespace) -> int:
	repo = _validate_repo(args.repo)
	b_path, b_raw, body = read_utf8_no_bom_file(args.body_file)
	consumable = [(b_path, b_raw)]
	target_locale = getattr(args, 'target_locale', 'en-US') or 'en-US'
	container_text = _load_saved_issue_container_text(consumable, repo, getattr(args, 'issue', None), project_root=getattr(args, 'project_root', None))
	existing_cids = _find_existing_issue_comments(consumable, repo, args.issue, project_root=getattr(args, 'project_root', None)) if None is args.comment_id and None is not args.issue and (not getattr(args, 'allow_additional_comment', False)) else []
	if existing_cids:
		dump_json({'ok': False, 'action': 'comment', 'stage': 'idempotent_comment_gate', 'repo': repo, 'issue': args.issue, 'existing_comment_ids': existing_cids, 'error': f'EXEC-5 / SCOPE-2: Issue #{args.issue} already has tracked comment(s) {existing_cids} in KB/Evidence/GitHub; use --comment-id {existing_cids[-1]} to update the existing comment in place instead of posting a duplicate comment (or pass --allow-additional-comment if explicitly instructed)'})
		r = 2
	else:
		def _write_comment() -> int:
			if None is not args.comment_id:
				res = _gh_api(f'repos/{repo}/issues/comments/{args.comment_id}', method='PATCH', payload={'body': body})
			elif None is args.issue:
				raise ValueError('Either --issue <number> or --comment-id <id> is required')
			else:
				res = _gh_api(f'repos/{repo}/issues/{args.issue}/comments', method='POST', payload={'body': body})
			return res['id']
		r = _run_verified_mutation(action='comment', repo=repo, consumable=consumable, target_locale=target_locale, container_text=container_text, expected_title=None, expected_body=body, write_fn=_write_comment, read_fn=lambda cid: _gh_api(f'repos/{repo}/issues/comments/{cid}', method='GET'), kind='comment', id_key='comment_id', consume_input=args.consume_input, project_root=getattr(args, 'project_root', None))
	return r
def cmd_close(args: argparse.Namespace) -> int:
	repo = _validate_repo(args.repo)
	number = args.issue
	consumable: list[tuple[Path, bytes]] = []
	target_locale = getattr(args, 'target_locale', 'en-US') or 'en-US'
	project_root = getattr(args, 'project_root', None)
	container_text = _load_saved_issue_container_text(consumable, repo, number, project_root=project_root)
	comment_body = None
	c_errors: list[dict[str, Any]] = []
	if args.comment_file:
		c_path, c_raw, comment_body = read_utf8_no_bom_file(args.comment_file)
		consumable.append((c_path, c_raw))
		c_errors = lint_issue_markdown(comment_body, is_title=False, target_locale=target_locale, container_text=container_text, check_structure_policy=False)
	commit_err: str | None = None
	if not c_errors and 'completed' == getattr(args, 'reason', 'completed'):
		code_repo = _find_local_code_repo(repo, project_root=project_root, source_files=consumable)
		if None is not code_repo and is_issue_tracked_code_repo(code_repo):
			try:
				verify_repo_issue_ready_for_close(code_repo, repo, number, project_root=project_root)
			except (ValueError, RuntimeError) as exc:
				commit_err = str(exc)
	if c_errors:
		dump_json({'ok': False, 'action': 'close', 'stage': 'pre_flight_comment_lint', 'repo': repo, 'number': number, 'comment_errors': c_errors})
		r = 2
	elif commit_err:
		dump_json({'ok': False, 'action': 'close', 'stage': 'pre_flight_commit_check', 'repo': repo, 'number': number, 'error': commit_err})
		r = 2
	else:
		comment_id = None
		comment_ok = True
		if None is not comment_body:
			created_comment = _gh_api(f'repos/{repo}/issues/{number}/comments', method='POST', payload={'body': comment_body})
			comment_id = created_comment['id']
			fetched_comment = _gh_api(f'repos/{repo}/issues/comments/{comment_id}', method='GET')
			remote_c = fetched_comment.get('body') or ''
			if normalize_newlines(remote_c) == normalize_newlines(comment_body) and (not lint_issue_markdown(remote_c, is_title=False, target_locale=target_locale, container_text=container_text, check_structure_policy=False)):
				_persist_issue_evidence(consumable, repo, fetched_comment, kind='comment', action='comment', project_root=project_root)
			else:
				dump_json({'ok': False, 'action': 'close', 'stage': 'post_flight_comment_readback', 'repo': repo, 'number': number, 'comment_id': comment_id})
				comment_ok = False
		if not comment_ok:
			r = 2
		else:
			_gh_api(f'repos/{repo}/issues/{number}', method='PATCH', payload={'state': 'closed', 'state_reason': args.reason})
			fetched = _gh_api(f'repos/{repo}/issues/{number}', method='GET')
			if 'closed' != fetched.get('state'):
				dump_json({'ok': False, 'action': 'close', 'stage': 'post_flight_state_check', 'repo': repo, 'number': number, 'state': fetched.get('state')})
				r = 2
			else:
				_persist_issue_evidence(consumable, repo, fetched, kind='issue', action='close', project_root=project_root)
				removed = _consume_files(consumable) if args.consume_input else []
				close_repo = code_repo if 'completed' == getattr(args, 'reason', 'completed') else _find_local_code_repo(repo, project_root=project_root, source_files=consumable)
				pending_peers = _pending_similar_peer_slugs(close_repo, repo=repo, project_root=project_root, source_files=consumable)
				res_payload: dict[str, Any] = {'ok': True, 'action': 'close', 'repo': repo, 'number': number, 'state': fetched.get('state'), 'state_reason': fetched.get('state_reason'), 'comment_id': comment_id, 'html_url': fetched.get('html_url'), 'verified': True, 'consumed_files': removed}
				if pending_peers:
					res_payload['similar_projects_pending'] = pending_peers
				dump_json(res_payload)
				r = 0
	return r
def _pending_similar_peer_slugs(code_repo: Path | None, *, repo: str, project_root: str | Path | None=None, source_files: list[tuple[Path, bytes]]=()) -> list[str]:
	if None is code_repo:
		return []
	try:
		from .issue_lifecycle import similar_project_repo_slugs
		from .path_registry import project_paths
		pp_repo = project_paths(code_repo)
	except (OSError, ValueError):
		return []
	peer_slugs: list[str] = []
	seen_slugs: set[str] = set()
	for peer in pp_repo.similar_projects:
		for slug in similar_project_repo_slugs(peer):
			if slug.lower() not in seen_slugs:
				seen_slugs.add(slug.lower())
				peer_slugs.append(slug)
	if not peer_slugs:
		return []
	turn_dirs: list[Path] = []
	for _, tdir in _resolve_issue_targets(source_files, repo, project_root=project_root):
		if tdir not in turn_dirs:
			turn_dirs.append(tdir)
	if pp_repo.turns_dir not in turn_dirs:
		turn_dirs.append(pp_repo.turns_dir)
	recorded_repos: set[str] = set()
	for tdir in turn_dirs:
		if not tdir.is_dir():
			continue
		for tfile in tdir.glob('*.json'):
			if tfile.name.endswith(('-checkpoint-recovery.json', '-violation-recovery.json', '-similar-exemptions.json')):
				continue
			try:
				tdata = json.loads(tfile.read_text(encoding='utf-8'))
			except (OSError, ValueError):
				continue
			if not isinstance(tdata, dict) or 'open' != tdata.get('status'):
				continue
			gh_raw = tdata.get('github_issues') or {}
			items = gh_raw.values() if isinstance(gh_raw, dict) else gh_raw if isinstance(gh_raw, list) else ()
			for item in items:
				if not isinstance(item, dict):
					continue
				acts = {str(a) for a in (item.get('actions') or ()) if a}
				if item.get('last_action'):
					acts.add(str(item['last_action']))
				if acts & {'create', 'edit', 'comment'}:
					r_slug = str(item.get('repo') or '').strip().lower()
					if r_slug:
						recorded_repos.add(r_slug)
	return [s for s in peer_slugs if s.lower() not in recorded_repos]
def cmd_audit_repo(args: argparse.Namespace) -> int:
	repo = _validate_repo(args.repo)
	target_locale = getattr(args, 'target_locale', 'en-US') or 'en-US'
	strict_structure = bool(getattr(args, 'strict_structure', False))
	raw_items = _gh_api(f'repos/{repo}/issues?state={args.state}&per_page=100', method='GET', paginate=True) or []
	issues = sorted((item for item in raw_items if 'pull_request' not in item), key=lambda x: x['number'])
	corrupted_issues: list[dict[str, Any]] = []
	issue_containers: dict[int, str] = {}
	for iss in issues:
		issue_containers[iss['number']] = f"{iss.get('title') or ''}\n{iss.get('body') or ''}".strip()
		t_errs = lint_issue_markdown(iss.get('title') or '', is_title=True, target_locale=target_locale, check_structure_policy=strict_structure)
		b_errs = lint_issue_markdown(iss.get('body') or '', is_title=False, target_locale=target_locale, check_structure_policy=strict_structure)
		if t_errs or b_errs:
			corrupted_issues.append({'number': iss['number'], 'title': iss.get('title'), 'html_url': iss.get('html_url'), 'title_errors': t_errs, 'body_errors': b_errs})
	corrupted_comments: list[dict[str, Any]] = []
	comments_count = 0
	if args.include_comments:
		raw_comments = _gh_api(f'repos/{repo}/issues/comments?per_page=100', method='GET', paginate=True) or []
		comments_count = len(raw_comments)
		for c in raw_comments:
			issue_num = int(c['issue_url'].rstrip('/').split('/')[-1])
			c_errs = lint_issue_markdown(c.get('body') or '', is_title=False, target_locale=target_locale, container_text=issue_containers.get(issue_num), check_structure_policy=False)
			if c_errs:
				corrupted_comments.append({'comment_id': c['id'], 'issue_number': issue_num, 'html_url': c.get('html_url'), 'body_errors': c_errs})
	valid = not corrupted_issues and (not corrupted_comments)
	dump_json({'valid': valid, 'repo': repo, 'issue_count': len(issues), 'comment_count': comments_count, 'corrupted_issue_count': len(corrupted_issues), 'corrupted_comment_count': len(corrupted_comments), 'corrupted_issues': corrupted_issues, 'corrupted_comments': corrupted_comments})
	return 0 if valid else 2
def build_parser() -> argparse.ArgumentParser:
	r = argparse.ArgumentParser(prog='df_github_issue.py', description='Create, edit, close, comment, and audit GitHub issues with UTF-8 file input and read-back verification.')
	sub = r.add_subparsers(dest='subcommand', required=True)
	sub_defs = (
		('lint', 'Validate issue title/body Markdown offline.', cmd_lint, ((('--repo', '-R'), {'help': 'Optional owner/repo slug for validating parent issue URLs.'}), (('--parent', '-p'), {'help': 'Parent problem issue number or URL for a child subtask issue.'}), ('--title', {'help': 'Issue title string.'}), ('--title-file', {'help': 'UTF-8 file containing issue title.'}), ('--body-file', {'required': True, 'help': 'UTF-8 file containing issue/comment Markdown body.'}), ('--target-locale', {'default': 'en-US', 'help': 'Expected target locale (default: en-US per TEXT-1).'}))),
		('create', 'Create a GitHub issue from a UTF-8 file and verify via API read-back.', cmd_create, (_REPO_SPEC, (('--parent', '-p'), {'help': 'Parent problem issue number or URL for a child subtask issue.'}), (('--title', '-t'), {'help': 'Issue title string.'}), ('--title-file', {'help': 'UTF-8 file containing issue title.'}), (('--body-file', '-F'), {'required': True, 'help': 'UTF-8 file containing issue Markdown body.'}), (('--label', '-l'), {'action': 'append', 'help': 'Issue label(s), repeatable or comma-separated.'}), (('--assignee', '-a'), {'action': 'append', 'help': 'Assignee login(s), repeatable or comma-separated.'}), (('--milestone', '-m'), {'type': int, 'help': 'Milestone number.'}), *_COMMON_TAIL_SPECS)),
		('edit', 'Update a GitHub issue from a UTF-8 file and verify via API read-back.', cmd_edit, (_REPO_SPEC, (('--issue', '-i'), {'type': int, 'required': True, 'help': 'Issue number.'}), (('--parent', '-p'), {'help': 'Parent problem issue number or URL for a child subtask issue.'}), (('--title', '-t'), {'help': 'Updated issue title string.'}), ('--title-file', {'help': 'UTF-8 file containing updated issue title.'}), (('--body-file', '-F'), {'help': 'UTF-8 file containing updated issue Markdown body.'}), ('--state', {'choices': ['open', 'closed'], 'help': 'Optional state change.'}), *_COMMON_TAIL_SPECS)),
		('comment', 'Add or edit an issue comment from a UTF-8 file and verify via API read-back.', cmd_comment, (_REPO_SPEC, (('--issue', '-i'), {'type': int, 'help': 'Issue number (for creating a new comment).'}), (('--comment-id', '-c'), {'type': int, 'help': 'Comment ID (for editing an existing comment).'}), (('--body-file', '-F'), {'required': True, 'help': 'UTF-8 file containing comment Markdown body.'}), ('--allow-additional-comment', {'action': 'store_true', 'help': 'Explicitly allow creating an additional comment on an issue that already has a tracked comment.'}), *_COMMON_TAIL_SPECS)),
		('close', 'Close a GitHub issue with optional verified comment from a UTF-8 file.', cmd_close, (_REPO_SPEC, (('--issue', '-i'), {'type': int, 'required': True, 'help': 'Issue number.'}), (('--reason', '-r'), {'choices': ['completed', 'not_planned'], 'default': 'completed', 'help': 'Closure reason.'}), (('--comment-file', '-F'), {'help': 'Optional UTF-8 file containing closing comment Markdown.'}), *_COMMON_TAIL_SPECS)),
		('audit-repo', 'Audit all issues and comments in a repository for syntax/encoding corruption.', cmd_audit_repo, (_REPO_SPEC, ('--state', {'choices': ['all', 'open', 'closed'], 'default': 'all', 'help': 'Issue state filter.'}), ('--include-comments', {'action': 'store_true', 'default': True, 'help': 'Audit issue comments as well.'}), ('--strict-structure', {'action': 'store_true', 'help': 'Also flag historical issues with enumerated titles or bundled subtask bodies.'}), ('--target-locale', {'default': 'en-US', 'help': 'Expected target locale (default: en-US per TEXT-1).'}))),
	)
	for name, help_text, fn, specs in sub_defs:
		p = sub.add_parser(name, help=help_text)
		add_arg_specs(p, specs)
		p.set_defaults(func=fn)
	return r
def main(argv: list[str] | None=None) -> int:
	parser = build_parser()
	try:
		args = parser.parse_args(argv)
		r = args.func(args)
	except Exception as exc:
		dump_json({'ok': False, 'error': str(exc)}, stream=sys.stderr)
		r = 1
	return r
if '__main__' == __name__:
	raise SystemExit(main())