# 2026-10-30 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Implement /df-github-issue skill and df_github_issue.py CLI with UTF-8 file input and mandatory API read-back verification":
# https://github.com/dmitry-ai/harness/issues/20
# 2026-10-31 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Reorganize AI into universal harness repository, translate rules and documentation to English, format per P.md, and enforce issue-driven Git workflow":
# https://github.com/dmitry-ai/harness/issues/26
# 2026-10-31 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Enforce universal harness.py CLI, automatic CDP browser fallback on JS shells, and Evidence verification for external links/anchors/quotes":
# https://github.com/dmitry-ai/harness/issues/27
from __future__ import annotations
import argparse
import json
from pathlib import Path
import re
import subprocess
import sys
from typing import Any
REPO_RE = re.compile('^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$')
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
	r = (path, raw, text)
	return r
def lint_issue_markdown(text: str, *, is_title: bool=False) -> list[dict[str, Any]]:
	errors: list[dict[str, Any]] = []
	if not isinstance(text, str) or not text.strip():
		errors.append({'code': 'EMPTY_TEXT', 'message': 'Text is empty or whitespace-only'})
		r = errors
	else:
		if '\ufeff' in text:
			errors.append({'code': 'UTF8_BOM', 'message': 'Contains UTF-8 BOM (U+FEFF), which breaks ATX Markdown headings at the start of a file'})
		if '\ufffd' in text:
			errors.append({'code': 'UNICODE_REPLACEMENT', 'message': 'Contains Unicode replacement character (U+FFFD)'})
		for idx, ch in enumerate(text):
			code = ord(ch)
			if code < 32 and ch not in ('\r', '\n', '\t') or 127 == code:
				errors.append({'code': 'CONTROL_CHAR', 'offset': idx, 'char': f'U+{code:04X}', 'message': f'Contains ASCII control character U+{code:04X} at offset {idx} (caused by PowerShell backtick escapes such as `0, `a, `b, `f, `v inside "..." or @"..."@)'})
				break
		if re.search('[^\\r\\n\\t]\\t[A-Za-z_]', text):
			errors.append({'code': 'INLINE_TAB_ESCAPE', 'message': 'Contains inline TAB character immediately before an identifier (caused by PowerShell `t expansion)'})
		if re.search('\\b\\d+(?::\\d+)*\\?\\d+(?::\\d+)*\\b', text):
			errors.append({'code': 'QUESTION_MARK_RANGE', 'message': 'Contains digit?digit range (caused by piping non-ASCII en-dash/em-dash through PowerShell without UTF-8 $OutputEncoding)'})
		if re.search('(?<![/.])\\b[A-Za-z]{2,}\\?[a-z]{2,}\\b', text):
			errors.append({'code': 'QUESTION_MARK_WORD_JOIN', 'message': 'Contains word?word (caused by piping em-dash — through PowerShell without UTF-8 $OutputEncoding)'})
		no_code = re.sub('```.*?```|`[^`\\r\\n]+`', '', text, flags=re.S)
		if re.search('[A-Za-z0-9)\\]]\\s+\\?\\s+[A-Za-z0-9(\\[]', no_code):
			errors.append({'code': 'QUESTION_MARK_SPACED', 'message': 'Contains spaced " ? " in prose outside code (caused by piping em-dash — without UTF-8 $OutputEncoding)'})
		if re.search('(?<![A-Za-z0-9_/])\\?[A-Z][A-Za-z0-9_-]*\\?', text):
			errors.append({'code': 'QUESTION_MARK_QUOTES', 'message': 'Contains ?Word? (caused by piping «Word» or curly quotes without UTF-8 $OutputEncoding)'})
		if re.search('(?:^|[\\s(])\\?\\d+(?:\\.\\d+)+\\b', text):
			errors.append({'code': 'QUESTION_MARK_SECTION', 'message': 'Contains ?N.M (caused by piping section sign §N.M without UTF-8 $OutputEncoding)'})
		if re.search('\\\\`', text):
			errors.append({'code': 'ESCAPED_BACKTICK', 'message': 'Contains literal \\` (bash-style escaped backtick in Markdown)'})
		if re.search('(?:^|[\\s(])\\\\[A-Za-z0-9_./:$^*\\[\\]()=-]+(?:\\s+[A-Za-z0-9_./:$^*\\[\\]()=-]+)*\\\\(?=[\\s).,;:!?\\)]|$)', text):
			errors.append({'code': 'BACKSLASH_WRAPPED_CODE', 'message': 'Contains \\token\\ wrapped in backslashes (caused by bash-style \\`token\\` inside PowerShell double quotes)'})
		if re.search('(?<![A-Za-z0-9_$\\)\\]\\}`"\\\'-])->[A-Za-z_][A-Za-z0-9_]*', text):
			errors.append({'code': 'EATEN_VARIABLE_ARROW', 'message': 'Contains bare ->method without object receiver (caused by PowerShell expanding $this or $var to empty string)'})
		if re.search('\\(\\s*,\\s*\\)|\\(\\s*,\\s*[^)\\s]|(?<!,)\\bempty\\(\\s*\\)|\\?callable\\s+=\\s*null', text):
			errors.append({'code': 'EATEN_VARIABLE_ARG', 'message': 'Contains empty function parameter/argument slot (caused by PowerShell expanding $var to empty string)'})
		if re.search('<(?:type|argument|preference|plugin|virtualType|job|group)\\b[^>]*\\b(?:name|xsi:type|id|instance|method)=[^"\\\'\\s>]+', text):
			errors.append({'code': 'UNQUOTED_XML_ATTR', 'message': 'Contains unquoted XML attribute (caused by PowerShell 5.1 stripping double quotes when passing --body $var)'})
		if re.search('(\\(\\s*\\\\?|\\b(?:version|from|to|in|at|with|by|for)\\s*`?)$', text.strip()):
			errors.append({'code': 'TRUNCATED_END', 'message': 'Text ends abruptly with an unfinished token or open delimiter (caused by PowerShell `0 -> NUL byte truncation)'})
		if not is_title:
			in_fence = False
			for lno, line in enumerate(text.splitlines(), 1):
				stripped = line.strip()
				if re.match('^``[a-zA-Z]*$', stripped):
					errors.append({'code': 'BROKEN_CODE_FENCE', 'line': lno, 'message': f'Line {lno} has 2-backtick pseudo-fence "{stripped}" instead of 3 backticks (caused by doubled backticks in PowerShell @"..."@)'})
				if stripped.startswith('```'):
					in_fence = not in_fence
					continue
				if not in_fence and 0 != line.count('`') % 2:
					errors.append({'code': 'UNBALANCED_INLINE_BACKTICKS', 'line': lno, 'message': f"Line {lno} has an odd number of inline backticks ({line.count('`')})"})
			if in_fence:
				errors.append({'code': 'UNCLOSED_CODE_FENCE', 'message': 'Markdown has an unclosed ``` fenced code block'})
			if len(text) >= 150 and '`' not in text and any((k in text for k in ('app/code/', 'vendor/', '::', '### Problem', '## 1. Root Cause', '## Summary'))):
				errors.append({'code': 'STRIPPED_ALL_BACKTICKS', 'message': 'Technical issue body contains 0 backticks (caused by unescaped backticks in PowerShell double-quoted string)'})
		r = errors
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
	proc = subprocess.run(cmd, input=input_bytes, capture_output=True, check=False)
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
			if isinstance(obj, list):
				merged.extend(obj)
			else:
				merged.append(obj)
		r = merged
	return r
def _consume_files(files: list[tuple[Path, bytes]]) -> list[str]:
	removed: list[str] = []
	for path, expected_bytes in files:
		if path.exists() and path.read_bytes() == expected_bytes:
			path.unlink()
			removed.append(str(path))
	r = removed
	return r
def _persist_issue_evidence(source_files: list[tuple[Path, bytes]], repo: str, fetched: dict[str, Any], *, kind: str='issue') -> str | None:
	if not isinstance(fetched, dict) or not fetched.get('html_url'):
		return None
	meta_dir = None
	for fpath, _ in source_files:
		for parent in fpath.resolve().parents:
			if 'ꘖ' == parent.name:
				meta_dir = parent
				break
		if None is not meta_dir:
			break
	if None is meta_dir:
		return None
	safe_repo = repo.replace('/', '__')
	ident = fetched.get('number') if 'issue' == kind else fetched.get('id')
	if None is ident:
		return None
	record = {'url': fetched.get('html_url'), 'html_url': fetched.get('html_url'), 'repo': repo, 'kind': kind, 'number': fetched.get('number'), 'id': fetched.get('id'), 'title': fetched.get('title') or f'{repo}#{ident}', 'state': fetched.get('state'), 'state_reason': fetched.get('state_reason'), 'body': fetched.get('body') or ''}
	payload_bytes = (json.dumps(record, ensure_ascii=False, indent=2) + '\n').encode('utf-8')
	target = meta_dir / 'KB/Evidence/GitHub' / safe_repo / f'{kind}-{ident}.json'
	target.parent.mkdir(parents=True, exist_ok=True)
	target.write_bytes(payload_bytes)
	if '_' == meta_dir.parent.name and (meta_dir.parent.parent / 'ꘖ').is_dir():
		mirror = meta_dir.parent.parent / 'ꘖ/KB/Evidence/GitHub' / safe_repo / f'{kind}-{ident}.json'
		mirror.parent.mkdir(parents=True, exist_ok=True)
		mirror.write_bytes(payload_bytes)
	return str(target)
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
	title_errors: list[dict[str, Any]] = []
	body_errors: list[dict[str, Any]] = []
	consumable: list[tuple[Path, bytes]] = []
	title = _resolve_title(args, consumable)
	if None is not title:
		title_errors = lint_issue_markdown(title, is_title=True)
	if args.body_file:
		_, _, body = read_utf8_no_bom_file(args.body_file)
		body_errors = lint_issue_markdown(body, is_title=False)
	valid = not title_errors and (not body_errors)
	out = {'valid': valid, 'title_errors': title_errors, 'body_errors': body_errors}
	print(json.dumps(out, ensure_ascii=False, indent=2))
	r = 0 if valid else 2
	return r
def cmd_create(args: argparse.Namespace) -> int:
	repo = _validate_repo(args.repo)
	consumable: list[tuple[Path, bytes]] = []
	title = _resolve_title(args, consumable)
	if not title:
		raise ValueError('Issue title is required (--title or --title-file)')
	b_path, b_raw, body = read_utf8_no_bom_file(args.body_file)
	consumable.append((b_path, b_raw))
	title_errors = lint_issue_markdown(title, is_title=True)
	body_errors = lint_issue_markdown(body, is_title=False)
	if title_errors or body_errors:
		print(json.dumps({'ok': False, 'action': 'create', 'stage': 'pre_flight_lint', 'title_errors': title_errors, 'body_errors': body_errors}, ensure_ascii=False, indent=2))
		r = 2
	else:
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
		created = _gh_api(f'repos/{repo}/issues', method='POST', payload=payload)
		number = created['number']
		fetched = _gh_api(f'repos/{repo}/issues/{number}', method='GET')
		remote_title = fetched.get('title') or ''
		remote_body = fetched.get('body') or ''
		post_title_errors = lint_issue_markdown(remote_title, is_title=True)
		post_body_errors = lint_issue_markdown(remote_body, is_title=False)
		exact_match = normalize_newlines(remote_title) == normalize_newlines(title) and normalize_newlines(remote_body) == normalize_newlines(body)
		if not exact_match or post_title_errors or post_body_errors:
			print(json.dumps({'ok': False, 'action': 'create', 'stage': 'post_flight_readback', 'repo': repo, 'number': number, 'html_url': fetched.get('html_url'), 'exact_match': exact_match, 'title_errors': post_title_errors, 'body_errors': post_body_errors}, ensure_ascii=False, indent=2))
			r = 2
		else:
			_persist_issue_evidence(consumable, repo, fetched, kind='issue')
			removed = _consume_files(consumable) if args.consume_input else []
			print(json.dumps({'ok': True, 'action': 'create', 'repo': repo, 'number': number, 'html_url': fetched.get('html_url'), 'verified': True, 'body_chars': len(remote_body), 'consumed_files': removed}, ensure_ascii=False, indent=2))
			r = 0
	return r
def cmd_edit(args: argparse.Namespace) -> int:
	repo = _validate_repo(args.repo)
	number = args.issue
	consumable: list[tuple[Path, bytes]] = []
	title = _resolve_title(args, consumable)
	body = None
	if args.body_file:
		b_path, b_raw, body = read_utf8_no_bom_file(args.body_file)
		consumable.append((b_path, b_raw))
	if None is title and None is body and (None is args.state):
		raise ValueError('At least one of --title/--title-file, --body-file, or --state must be provided')
	title_errors = lint_issue_markdown(title, is_title=True) if None is not title else []
	body_errors = lint_issue_markdown(body, is_title=False) if None is not body else []
	if title_errors or body_errors:
		print(json.dumps({'ok': False, 'action': 'edit', 'stage': 'pre_flight_lint', 'repo': repo, 'number': number, 'title_errors': title_errors, 'body_errors': body_errors}, ensure_ascii=False, indent=2))
		r = 2
	else:
		payload: dict[str, Any] = {}
		if None is not title:
			payload['title'] = title
		if None is not body:
			payload['body'] = body
		if None is not args.state:
			payload['state'] = args.state
		_gh_api(f'repos/{repo}/issues/{number}', method='PATCH', payload=payload)
		fetched = _gh_api(f'repos/{repo}/issues/{number}', method='GET')
		remote_title = fetched.get('title') or ''
		remote_body = fetched.get('body') or ''
		post_title_errors = lint_issue_markdown(remote_title, is_title=True) if None is not title else []
		post_body_errors = lint_issue_markdown(remote_body, is_title=False) if None is not body else []
		title_match = True if None is title else normalize_newlines(remote_title) == normalize_newlines(title)
		body_match = True if None is body else normalize_newlines(remote_body) == normalize_newlines(body)
		exact_match = title_match and body_match
		if not exact_match or post_title_errors or post_body_errors:
			print(json.dumps({'ok': False, 'action': 'edit', 'stage': 'post_flight_readback', 'repo': repo, 'number': number, 'html_url': fetched.get('html_url'), 'exact_match': exact_match, 'title_errors': post_title_errors, 'body_errors': post_body_errors}, ensure_ascii=False, indent=2))
			r = 2
		else:
			_persist_issue_evidence(consumable, repo, fetched, kind='issue')
			removed = _consume_files(consumable) if args.consume_input else []
			print(json.dumps({'ok': True, 'action': 'edit', 'repo': repo, 'number': number, 'html_url': fetched.get('html_url'), 'verified': True, 'body_chars': len(remote_body), 'consumed_files': removed}, ensure_ascii=False, indent=2))
			r = 0
	return r
def cmd_comment(args: argparse.Namespace) -> int:
	repo = _validate_repo(args.repo)
	b_path, b_raw, body = read_utf8_no_bom_file(args.body_file)
	consumable = [(b_path, b_raw)]
	body_errors = lint_issue_markdown(body, is_title=False)
	if body_errors:
		print(json.dumps({'ok': False, 'action': 'comment', 'stage': 'pre_flight_lint', 'repo': repo, 'body_errors': body_errors}, ensure_ascii=False, indent=2))
		r = 2
	else:
		if None is not args.comment_id:
			res = _gh_api(f'repos/{repo}/issues/comments/{args.comment_id}', method='PATCH', payload={'body': body})
			comment_id = res['id']
		elif None is args.issue:
			raise ValueError('Either --issue <number> or --comment-id <id> is required')
		else:
			res = _gh_api(f'repos/{repo}/issues/{args.issue}/comments', method='POST', payload={'body': body})
			comment_id = res['id']
		fetched = _gh_api(f'repos/{repo}/issues/comments/{comment_id}', method='GET')
		remote_body = fetched.get('body') or ''
		post_errors = lint_issue_markdown(remote_body, is_title=False)
		exact_match = normalize_newlines(remote_body) == normalize_newlines(body)
		if not exact_match or post_errors:
			print(json.dumps({'ok': False, 'action': 'comment', 'stage': 'post_flight_readback', 'repo': repo, 'comment_id': comment_id, 'html_url': fetched.get('html_url'), 'exact_match': exact_match, 'body_errors': post_errors}, ensure_ascii=False, indent=2))
			r = 2
		else:
			_persist_issue_evidence(consumable, repo, fetched, kind='comment')
			removed = _consume_files(consumable) if args.consume_input else []
			print(json.dumps({'ok': True, 'action': 'comment', 'repo': repo, 'comment_id': comment_id, 'html_url': fetched.get('html_url'), 'verified': True, 'body_chars': len(remote_body), 'consumed_files': removed}, ensure_ascii=False, indent=2))
			r = 0
	return r
def cmd_close(args: argparse.Namespace) -> int:
	repo = _validate_repo(args.repo)
	number = args.issue
	consumable: list[tuple[Path, bytes]] = []
	comment_id = None
	if args.comment_file:
		c_path, c_raw, comment_body = read_utf8_no_bom_file(args.comment_file)
		consumable.append((c_path, c_raw))
		c_errors = lint_issue_markdown(comment_body, is_title=False)
		if c_errors:
			print(json.dumps({'ok': False, 'action': 'close', 'stage': 'pre_flight_comment_lint', 'repo': repo, 'number': number, 'comment_errors': c_errors}, ensure_ascii=False, indent=2))
			return 2
		created_comment = _gh_api(f'repos/{repo}/issues/{number}/comments', method='POST', payload={'body': comment_body})
		comment_id = created_comment['id']
		fetched_comment = _gh_api(f'repos/{repo}/issues/comments/{comment_id}', method='GET')
		remote_c = fetched_comment.get('body') or ''
		if normalize_newlines(remote_c) != normalize_newlines(comment_body) or lint_issue_markdown(remote_c, is_title=False):
			print(json.dumps({'ok': False, 'action': 'close', 'stage': 'post_flight_comment_readback', 'repo': repo, 'number': number, 'comment_id': comment_id}, ensure_ascii=False, indent=2))
			return 2
		_persist_issue_evidence(consumable, repo, fetched_comment, kind='comment')
	payload: dict[str, Any] = {'state': 'closed', 'state_reason': args.reason}
	_gh_api(f'repos/{repo}/issues/{number}', method='PATCH', payload=payload)
	fetched = _gh_api(f'repos/{repo}/issues/{number}', method='GET')
	if 'closed' != fetched.get('state'):
		print(json.dumps({'ok': False, 'action': 'close', 'stage': 'post_flight_state_check', 'repo': repo, 'number': number, 'state': fetched.get('state')}, ensure_ascii=False, indent=2))
		return 2
	_persist_issue_evidence(consumable, repo, fetched, kind='issue')
	removed = _consume_files(consumable) if args.consume_input else []
	print(json.dumps({'ok': True, 'action': 'close', 'repo': repo, 'number': number, 'state': fetched.get('state'), 'state_reason': fetched.get('state_reason'), 'comment_id': comment_id, 'html_url': fetched.get('html_url'), 'verified': True, 'consumed_files': removed}, ensure_ascii=False, indent=2))
	return 0
def cmd_audit_repo(args: argparse.Namespace) -> int:
	repo = _validate_repo(args.repo)
	raw_items = _gh_api(f'repos/{repo}/issues?state={args.state}&per_page=100', method='GET', paginate=True) or []
	issues = [item for item in raw_items if 'pull_request' not in item]
	issues.sort(key=lambda x: x['number'])
	corrupted_issues: list[dict[str, Any]] = []
	for iss in issues:
		t_errs = lint_issue_markdown(iss.get('title') or '', is_title=True)
		b_errs = lint_issue_markdown(iss.get('body') or '', is_title=False)
		if t_errs or b_errs:
			corrupted_issues.append({'number': iss['number'], 'title': iss.get('title'), 'html_url': iss.get('html_url'), 'title_errors': t_errs, 'body_errors': b_errs})
	corrupted_comments: list[dict[str, Any]] = []
	comments_count = 0
	if args.include_comments:
		raw_comments = _gh_api(f'repos/{repo}/issues/comments?per_page=100', method='GET', paginate=True) or []
		comments_count = len(raw_comments)
		for c in raw_comments:
			c_errs = lint_issue_markdown(c.get('body') or '', is_title=False)
			if c_errs:
				issue_num = int(c['issue_url'].rstrip('/').split('/')[-1])
				corrupted_comments.append({'comment_id': c['id'], 'issue_number': issue_num, 'html_url': c.get('html_url'), 'body_errors': c_errs})
	valid = not corrupted_issues and (not corrupted_comments)
	print(json.dumps({'valid': valid, 'repo': repo, 'issue_count': len(issues), 'comment_count': comments_count, 'corrupted_issue_count': len(corrupted_issues), 'corrupted_comment_count': len(corrupted_comments), 'corrupted_issues': corrupted_issues, 'corrupted_comments': corrupted_comments}, ensure_ascii=False, indent=2))
	r = 0 if valid else 2
	return r
def build_parser() -> argparse.ArgumentParser:
	parser = argparse.ArgumentParser(prog='df_github_issue.py', description='Create, edit, close, comment, and audit GitHub issues with UTF-8 file input and read-back verification.')
	sub = parser.add_subparsers(dest='subcommand', required=True)
	p_lint = sub.add_parser('lint', help='Validate issue title/body Markdown offline.')
	p_lint.add_argument('--title', help='Issue title string.')
	p_lint.add_argument('--title-file', help='UTF-8 file containing issue title.')
	p_lint.add_argument('--body-file', required=True, help='UTF-8 file containing issue/comment Markdown body.')
	p_lint.set_defaults(func=cmd_lint)
	p_create = sub.add_parser('create', help='Create a GitHub issue from a UTF-8 file and verify via API read-back.')
	p_create.add_argument('--repo', '-R', required=True, help='Target repository in owner/repo format.')
	p_create.add_argument('--title', '-t', help='Issue title string.')
	p_create.add_argument('--title-file', help='UTF-8 file containing issue title.')
	p_create.add_argument('--body-file', '-F', required=True, help='UTF-8 file containing issue Markdown body.')
	p_create.add_argument('--label', '-l', action='append', help='Issue label(s), repeatable or comma-separated.')
	p_create.add_argument('--assignee', '-a', action='append', help='Assignee login(s), repeatable or comma-separated.')
	p_create.add_argument('--milestone', '-m', type=int, help='Milestone number.')
	p_create.add_argument('--consume-input', action='store_true', help='Delete input file(s) after verified creation.')
	p_create.set_defaults(func=cmd_create)
	p_edit = sub.add_parser('edit', help='Update a GitHub issue from a UTF-8 file and verify via API read-back.')
	p_edit.add_argument('--repo', '-R', required=True, help='Target repository in owner/repo format.')
	p_edit.add_argument('--issue', '-i', type=int, required=True, help='Issue number.')
	p_edit.add_argument('--title', '-t', help='Updated issue title string.')
	p_edit.add_argument('--title-file', help='UTF-8 file containing updated issue title.')
	p_edit.add_argument('--body-file', '-F', help='UTF-8 file containing updated issue Markdown body.')
	p_edit.add_argument('--state', choices=['open', 'closed'], help='Optional state change.')
	p_edit.add_argument('--consume-input', action='store_true', help='Delete input file(s) after verified update.')
	p_edit.set_defaults(func=cmd_edit)
	p_comment = sub.add_parser('comment', help='Add or edit an issue comment from a UTF-8 file and verify via API read-back.')
	p_comment.add_argument('--repo', '-R', required=True, help='Target repository in owner/repo format.')
	p_comment.add_argument('--issue', '-i', type=int, help='Issue number (for creating a new comment).')
	p_comment.add_argument('--comment-id', '-c', type=int, help='Comment ID (for editing an existing comment).')
	p_comment.add_argument('--body-file', '-F', required=True, help='UTF-8 file containing comment Markdown body.')
	p_comment.add_argument('--consume-input', action='store_true', help='Delete input file after verified publication.')
	p_comment.set_defaults(func=cmd_comment)
	p_close = sub.add_parser('close', help='Close a GitHub issue with optional verified comment from a UTF-8 file.')
	p_close.add_argument('--repo', '-R', required=True, help='Target repository in owner/repo format.')
	p_close.add_argument('--issue', '-i', type=int, required=True, help='Issue number.')
	p_close.add_argument('--reason', '-r', choices=['completed', 'not_planned'], default='completed', help='Closure reason.')
	p_close.add_argument('--comment-file', '-F', help='Optional UTF-8 file containing closing comment Markdown.')
	p_close.add_argument('--consume-input', action='store_true', help='Delete comment file after verified closure.')
	p_close.set_defaults(func=cmd_close)
	p_audit = sub.add_parser('audit-repo', help='Audit all issues and comments in a repository for syntax/encoding corruption.')
	p_audit.add_argument('--repo', '-R', required=True, help='Target repository in owner/repo format.')
	p_audit.add_argument('--state', choices=['all', 'open', 'closed'], default='all', help='Issue state filter.')
	p_audit.add_argument('--include-comments', action='store_true', default=True, help='Audit issue comments as well.')
	p_audit.set_defaults(func=cmd_audit_repo)
	r = parser
	return r
def main(argv: list[str] | None=None) -> int:
	parser = build_parser()
	try:
		args = parser.parse_args(argv)
		r = args.func(args)
	except Exception as exc:
		print(json.dumps({'ok': False, 'error': str(exc)}, ensure_ascii=False, indent=2), file=sys.stderr)
		r = 1
	return r
if '__main__' == __name__:
	raise SystemExit(main())
