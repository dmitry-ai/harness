# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from pathlib import Path
from Df.Core.lib.fs import df_path_suffix
from Df.Harness.Gate.IssueCommentScanner import IssueCommentScanner
import difflib
import re
# 2026-11-26 "Move verification gate subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/381
class IssueCommentChecker:
	__IMPORT_LINE_RE = re.compile(r'^\s*(?:from\s+\S+\s+import\b|import\b|package\b|use\b|#include\b|#pragma\b|using\b|(?:const|let|var)\s+[\w{},\s]+\s*=\s*require\s*\()')
	# @used-by :func:`agent_tools.issue_comment_gate.check_issue_comment_violations()`
	# @used-by :meth:`Df.Harness.Gate.IssueCommentPreToolGate.IssueCommentPreToolGate.check()`
	# @used-by :meth:`Df.Harness.Gate.IssueCommentStagedGate.IssueCommentStagedGate.verify()`
	# @used-by :meth:`test_df_harness_s11_wave2b_gate.DfHarnessS11Wave2bGateTests.test_gate_thin_pretool_shims_and_checkers()`
	# @used-by :meth:`test_df_harness_s11_wave2b_gate_cov.DfHarnessS11Wave2bGateCovTests.test_issue_comment_checker_and_scanner_cover_py_js_and_xml()`
	# @used-by :meth:`test_df_harness_s11_wave2b_tail_cov.DfHarnessS11Wave2bTailCovTests.test_gate_bulk_size_external_issue_and_subproc()`
	def __init__(self, path: str | Path, source: str, *, baseline_source: str | None=None) -> None:
		self.__path = Path(path)
		self.__source = source or ''
		self.__baseline_source = baseline_source
	# @used-by :meth:`IssueCommentChecker.__check_diff_issue_lines()`
	@staticmethod
	def __check_added_issue_line(rel_label: str, ln: int, cur_lines: list[str], cur_scan: dict, diff_info: dict, py_info: tuple, suffix: str) -> str | None:
		r: str | None = None
		changed_code, del_anchors = (diff_info['changed_code'], diff_info['del_anchors'])
		if ln in cur_scan['code_lines']:
			if changed_code and ln not in changed_code:
				r = f'ISSUE-COMMENT-GATE (MISPLACED_ISSUE_COMMENT): Inline issue URL comment in {rel_label}:{ln} sits on an unchanged line; place it at the modified block or function header'
		else:
			nxt = IssueCommentScanner.next_code_line(ln, cur_scan['code_lines'], len(cur_lines))
			if ln <= cur_scan['header_end'] and None is not nxt:
				r = IssueCommentChecker.__check_header_placement(rel_label, ln, nxt, cur_lines, changed_code, del_anchors, py_info, suffix, comment_only=bool(diff_info.get('comment_only')))
			elif changed_code or del_anchors:
				r = IssueCommentChecker.__check_body_placement(rel_label, ln, nxt, cur_lines, changed_code, del_anchors, py_info, suffix)
		return r
	# @used-by :meth:`IssueCommentChecker.check()`
	@staticmethod
	def __check_author_headers(rel_label: str, cur_scan: dict, base_scan: dict | None) -> list[str]:
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
	# @used-by :meth:`IssueCommentChecker.__check_added_issue_line()`
	@staticmethod
	def __check_body_placement(rel_label: str, ln: int, nxt: int | None, cur_lines: list[str], changed_code: set[int], del_anchors: set[int], py_info: tuple, suffix: str) -> str | None:
		r: str | None = None
		if None is nxt:
			if not any((2 >= abs(d - ln) for d in del_anchors)):
				r = f'ISSUE-COMMENT-GATE (MISPLACED_ISSUE_COMMENT): Issue URL comment at {rel_label}:{ln} has no modified code block below it'
		else:
			st, en, kind = IssueCommentScanner.construct_span(cur_lines, nxt, suffix, py_info[0])
			in_span = nxt in changed_code or any((st <= c <= en for c in changed_code)) or any((st - 1 <= d <= en + 1 for d in del_anchors))
			if not in_span:
				nearest = min(changed_code or del_anchors, key=lambda x: abs(x - ln))
				r = f'ISSUE-COMMENT-GATE (MISPLACED_ISSUE_COMMENT): Issue URL comment at {rel_label}:{ln} does not precede modified code (nearest change at line {nearest})'
			elif 'class' == kind and st not in changed_code:
				r = IssueCommentChecker.__check_class_scope(rel_label, ln, st, en, changed_code, py_info[1])
		return r
	# @used-by :meth:`IssueCommentChecker.__check_body_placement()`
	@staticmethod
	def __check_class_scope(rel_label: str, ln: int, st: int, en: int, changed_code: set[int], class_methods: dict[int, list[tuple[int, int]]]) -> str | None:
		r: str | None = None
		methods = class_methods.get(st, ())
		touched = [m for m in methods if any((m[0] <= c <= m[1] for c in changed_code))]
		outside = [c for c in changed_code if st <= c <= en and (not any((m[0] <= c <= m[1] for m in methods)))]
		if 2 <= len(methods) and 1 == len(touched) and (not outside):
			r = f'ISSUE-COMMENT-GATE (MISPLACED_ISSUE_COMMENT): Issue URL comment at {rel_label}:{ln} sits on class header while only method at line {touched[0][0]} changed; place it at the modified block or method header'
		return r
	# @used-by :meth:`IssueCommentChecker.check()`
	@staticmethod
	def __check_diff_issue_lines(rel_label: str, source: str, base_lines: list[str], cur_lines: list[str], base_scan: dict, cur_scan: dict, suffix: str) -> list[str]:
		from Df.Harness.Tdd.CommentDiff import CommentDiff
		errs: list[str] = []
		diff_info = IssueCommentChecker.__diff_changes(base_lines, cur_lines, base_scan, cur_scan)
		if CommentDiff.is_comment_only(rel_label, '\n'.join(base_lines), source):
			diff_info['changed_code'], diff_info['del_anchors'], diff_info['comment_only'] = (set(), set(), True)
		base_urls = {u for urls in base_scan['issue_lines'].values() for u in urls}
		if 0.70 > len(diff_info['changed_code']) / max(1, len(cur_scan['code_lines'])):
			py_info = IssueCommentScanner.build_py_spans(source) if suffix in ('.py', '.pyi') else ({}, {})
			for ln in sorted(diff_info['added_issue']):
				if any((u not in base_urls for u in cur_scan['issue_lines'][ln])):
					err = IssueCommentChecker.__check_added_issue_line(rel_label, ln, cur_lines, cur_scan, diff_info, py_info, suffix)
					if None is not err:
						errs.append(err)
		return errs
	# @used-by :meth:`IssueCommentChecker.__check_added_issue_line()`
	@staticmethod
	def __check_header_placement(rel_label: str, ln: int, nxt: int, cur_lines: list[str], changed_code: set[int], del_anchors: set[int], py_info: tuple, suffix: str, *, comment_only: bool=False) -> str | None:
		r: str | None = None
		direct = nxt in changed_code or any((1 >= abs(d - nxt) for d in del_anchors))
		if not direct:
			is_imp = bool(IssueCommentChecker.__IMPORT_LINE_RE.match(cur_lines[nxt - 1]))
			st, en, kind = IssueCommentScanner.construct_span(cur_lines, nxt, suffix, py_info[0])
			in_unit = (not is_imp) and kind in ('func', 'class', 'block') and (comment_only or any((st <= c <= en for c in changed_code)))
			if not in_unit:
				r = f'ISSUE-COMMENT-GATE (HEADER_DUMPED_ISSUE_COMMENT): Issue URL comment at {rel_label}:{ln} is dumped in the file header above unchanged line {nxt}; place it immediately before the modified block or function/method header'
		return r
	# @used-by :meth:`IssueCommentChecker.__check_diff_issue_lines()`
	@staticmethod
	def __diff_changes(base_lines: list[str], cur_lines: list[str], base_scan: dict, cur_scan: dict) -> dict:
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
	# @used-by :func:`agent_tools.issue_comment_gate.check_issue_comment_violations()`
	# @used-by :meth:`Df.Harness.Gate.IssueCommentPreToolGate.IssueCommentPreToolGate.check()`
	# @used-by :meth:`Df.Harness.Gate.IssueCommentStagedGate.IssueCommentStagedGate.verify()`
	# @used-by :meth:`test_df_harness_s11_wave2b_gate.DfHarnessS11Wave2bGateTests.test_gate_thin_pretool_shims_and_checkers()`
	# @used-by :meth:`test_df_harness_s11_wave2b_gate_cov.DfHarnessS11Wave2bGateCovTests.test_issue_comment_checker_and_scanner_cover_py_js_and_xml()`
	# @used-by :meth:`test_df_harness_s11_wave2b_tail_cov.DfHarnessS11Wave2bTailCovTests.test_gate_bulk_size_external_issue_and_subproc()`
	def check(self) -> list[str]:
		suffix = df_path_suffix(self.__path)
		errs: list[str] = []
		if suffix in IssueCommentScanner.SUPPORTED_SUFFIXES:
			rel_label = self.__path.as_posix()
			cur_lines = self.__source.splitlines()
			cur_scan = IssueCommentScanner(cur_lines, suffix).scan()
			base_lines = self.__baseline_source.splitlines() if None is not self.__baseline_source else None
			base_scan = IssueCommentScanner(base_lines, suffix).scan() if None is not base_lines else None
			errs.extend(IssueCommentChecker.__check_author_headers(rel_label, cur_scan, base_scan))
			if None is not base_scan and base_scan['code_lines']:
				errs.extend(IssueCommentChecker.__check_diff_issue_lines(rel_label, self.__source, base_lines, cur_lines, base_scan, cur_scan, suffix))
		return errs
