# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
# 2026-11-26 "Move verification gate subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/381
class IssueCommentPreToolGate:
	NAME = 'ISSUE-COMMENT-GATE'
	PRIORITY = 126
	TOOLS = frozenset({'write_file', 'edit_file'})
	# @used-by :func:`agent_tools.gates.issue_comment.check()`
	# @used-by :func:`agent_tools.issue_comment_gate.evaluate_pre_tool_use_issue_comment()`
	def check(self, name: str, args: dict, payload: dict | None=None) -> str | None:
		r = None
		if name in ('write_file', 'edit_file'):
			from Df.Harness.Gate.IssueCommentChecker import IssueCommentChecker
			from Df.Harness.Gate.IssueCommentScanner import IssueCommentScanner
			from agent_tools.tdd_gate import _compute_edited_content, _git_head_text
			resolved = IssueCommentScanner.resolve_target(args, payload or {})
			if None is not resolved:
				repo_root, target, rel = resolved
				_, new_text, _, _ = _compute_edited_content(name, args, target)
				if None is not new_text:
					base = _git_head_text(repo_root, rel) if None is not repo_root else (target.read_text(encoding='utf-8', errors='replace') if target.is_file() else None)
					errs = IssueCommentChecker(rel, new_text, baseline_source=base).check()
					r = '; '.join(errs[:3]) if errs else None
		return r
