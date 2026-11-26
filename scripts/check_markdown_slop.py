# 2026-10-21 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from pathlib import Path
import re
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent))
# 2026-11-24
# "Unify PreToolUse/Stop JSON hook harnesses, turns/*.json iterators, DOC-4 sentence scanning, and GitHub Evidence resolvers":
# https://github.com/dmitry-ai/harness/issues/79
from agent_tools.hook_runtime import ABBREVIATIONS, ABBR_RE, MULTI_SENT_RE, iter_turn_state_files, run_json_hook, scan_doc4_sentence_issues
# 2026-11-26 "Ban file:/// links for GitHub repositories and ground tagged GitHub URLs": https://github.com/dmitry-ai/harness/issues/264
def _check_doc_grounding_and_links(proj_root: Path, content: str, p_obj: Path) -> str | None:
	from agent_tools.repo_link_gate import file_repo_link_issues, is_skipped_repo_link_doc
	# 2026-11-24
	# "Convert PreToolUse hook entry points to lazy tool-scoped imports":
	# https://github.com/dmitry-ai/harness/issues/187
	from agent_tools.source_grounding import local_source_grounding_issues
	issues = list(local_source_grounding_issues(proj_root, content, doc_path=p_obj))
	if not is_skipped_repo_link_doc(p_obj):
		issues.extend(file_repo_link_issues(p_obj, content, repo_root=proj_root))
	return _format_grounding_issues(issues) if issues else None
# 2026-11-10
# "Isolate turn scratch answer files, allow pre-delivery response re-preparation, and enforce preemptive step/compaction budget stop":
# https://github.com/dmitry-ai/harness/issues/49
def _check_turn_budget_gate(proj_root: Path, target: Path) -> str | None:
	# 2026-11-24
	# "Convert PreToolUse hook entry points to lazy tool-scoped imports":
	# https://github.com/dmitry-ai/harness/issues/187
	from agent_tools.path_registry import project_paths
	# 2026-11-19
	# "Wire project path overlays across Harness subsystems with paths CLI and regression tests":
	# https://github.com/dmitry-ai/harness/issues/96
	pp = project_paths(proj_root)
	norm_p = target.as_posix().lower()
	r = None
	# 2026-11-20
	# "Replace V2 verbal directory names with Ⰿ/♕/♙ symbols and add Antigravity hook runner":
	# https://github.com/dmitry-ai/harness/issues/103
	if any((seg in norm_p for seg in pp.deliverable_segments)) and '/\ua616/' not in norm_p and '/\ua66e/' not in norm_p and '/\u26ef/' not in norm_p:
		# 2026-11-24
		# "Unify PreToolUse/Stop JSON hook harnesses, turns/*.json iterators, DOC-4 sentence scanning, and GitHub Evidence resolvers":
		# https://github.com/dmitry-ai/harness/issues/79
		for _, tdata in iter_turn_state_files(pp.turns_dir, exclude_hyphen=True):
			if tdata.get('status') in ('open', 'prepared', 'preparation_unverified'):
				bcheck = tdata.get('budget_check') or {}
				if bcheck.get('graceful_checkpoint_required') and (not bcheck.get('continuation_saved')):
					r = 'Turn Budget & Graceful Checkpoint Gate (M-4): active turn exceeded safe compaction/step budget (checkpoint_count >= 2, tool_step_count >= 120, or 5h window >= 400); persist verified findings to ꘖ/KB/Evidence/ and ꘖ/data/continuation.md and complete the turn via answer-prepare before generating new client deliverables'
					break
	return r
# 2026-11-24
# "Unify PreToolUse/Stop JSON hook harnesses, turns/*.json iterators, DOC-4 sentence scanning, and GitHub Evidence resolvers":
# https://github.com/dmitry-ai/harness/issues/79
def _evaluate_payload(payload: dict) -> dict:
	tool_call = payload.get('toolCall', {})
	name, args = (tool_call.get('name', ''), tool_call.get('args', {}))
	path = args.get('Path', '')
	norm_p = path.replace('\\', '/').lower()
	decision = {'decision': 'allow'}
	if name in ('write_file', 'edit_file') and path and path.lower().endswith('.md') and (not _is_request_journal_file(norm_p)):
		content = _resolve_markdown_content(name, args, path)
		violation = check_markdown_content(content, path)
		if violation:
			decision = {'decision': 'deny', 'reason': f'REJECTED (DOC-4 / VERIFY-1 Anti-Slop Hook): {violation}'}
	return decision
# 2026-11-01
# "Eliminate local/external quote, metric, and identifier fabrication via local source grounding, Stop hook, fresh-read provenance, and A.A audit gates":
# https://github.com/dmitry-ai/harness/issues/34
def _infer_project_root(target: Path) -> Path:
	# 2026-11-24
	# "Convert PreToolUse hook entry points to lazy tool-scoped imports":
	# https://github.com/dmitry-ai/harness/issues/187
	from agent_tools.path_registry import resolve_project_root
	# 2026-11-19
	# "Wire project path overlays across Harness subsystems with paths CLI and regression tests":
	# https://github.com/dmitry-ai/harness/issues/96
	resolved = resolve_project_root(target)
	# 2026-11-20
	# "Wire V2 filesystem layout across Harness runtime subsystems and shared projections":
	# https://github.com/dmitry-ai/harness/issues/101
	markers = ('\ua616', '_/\ua616', '\ua66e', '\U0001f56e')
	if resolved != target.resolve().parent or any(((resolved / m).is_dir() for m in markers)):
		r = resolved
	else:
		# 2026-11-10
		# "Enforce source grounding and review.authorize across external client deliverables, edit_file calls, and post-compaction tool outputs":
		# https://github.com/dmitry-ai/harness/issues/50
		cwd_res = resolve_project_root(Path.cwd().resolve())
		r = cwd_res if any(((cwd_res / m).is_dir() for m in markers)) else resolved
	return r
# 2026-11-24
# "Skip blocking grounding on scratch drafts and add line locations to diagnostics":
# https://github.com/dmitry-ai/harness/issues/214
def _format_grounding_issues(issues: list[str]) -> str:
	unique = list(dict.fromkeys(issues))
	return unique[0] if 1 == len(unique) else f'{len(unique)} grounding issues: ' + '; '.join(unique)
# 2026-11-20
# "Wire V2 filesystem layout across Harness runtime subsystems and shared projections":
# https://github.com/dmitry-ai/harness/issues/101
def _is_request_journal_file(norm_p: str) -> bool:
	return '/req/' in norm_p or bool(re.search('(?:^|/)\\ua66e/(?:[^/]+/)?\\u227b/', norm_p))
# 2026-11-24
# "Skip blocking grounding on scratch drafts and add line locations to diagnostics":
# https://github.com/dmitry-ai/harness/issues/214
def _is_scratch_draft_file(norm_p: str) -> bool:
	return '/data/scratch/' in norm_p
# 2026-11-10
# "Enforce source grounding and review.authorize across external client deliverables, edit_file calls, and post-compaction tool outputs":
# https://github.com/dmitry-ai/harness/issues/50
# 2026-11-24
# "Unify PreToolUse/Stop JSON hook harnesses, turns/*.json iterators, DOC-4 sentence scanning, and GitHub Evidence resolvers":
# https://github.com/dmitry-ai/harness/issues/79
def _resolve_markdown_content(name: str, args: dict, path: str):
	if 'write_file' == name:
		content = args.get('Content')
	else:
		content = args.get('Replacement')
		p_file, target_str = (Path(path), args.get('Target'))
		if p_file.is_file() and isinstance(target_str, str) and target_str and isinstance(content, str):
			try:
				raw_doc = p_file.read_text(encoding='utf-8')
				if target_str in raw_doc:
					content = raw_doc.replace(target_str, content)
			except OSError:
				pass
	return content
# 2026-10-21
# "Enforce CommonMark two-space hard line breaks (DOC-4), ban unsolicited bullet lists, and add PreToolUse hook check_markdown_slop.py":
# https://github.com/dmitry-ai/harness/issues/14
# 2026-10-31
# "Reorganize AI into universal harness repository, translate rules and documentation to English, format per P.md, and enforce issue-driven Git workflow":
# https://github.com/dmitry-ai/harness/issues/26
def check_markdown_content(content, path=None):
	r = None
	if content and isinstance(content, str):
		# 2026-11-21
		# "Add read-only answer-check pre-flight validation command to harness CLI":
		# https://github.com/dmitry-ai/harness/issues/117
		slop = markdown_slop_issues(content)
		if slop:
			r = re.sub('^DOC-4\\s+', '', slop[0])
		# 2026-11-01
		# "Eliminate local/external quote, metric, and identifier fabrication via local source grounding, Stop hook, fresh-read provenance, and A.A audit gates":
		# https://github.com/dmitry-ai/harness/issues/34
		if None is r and path:
			p_obj = Path(path)
			norm_p = path.replace('\\', '/').lower()
			# 2026-11-02
			# "Replace special-case grounding/locale regexes with universal locale, relational claim arity, standalone-number, capability, and review gates":
			# https://github.com/dmitry-ai/harness/issues/37
			# 2026-11-20
			# "Wire V2 filesystem layout across Harness runtime subsystems and shared projections":
			# https://github.com/dmitry-ai/harness/issues/101
			if not _is_request_journal_file(norm_p) and '/source/' not in norm_p and 'source.md' != p_obj.name.lower():
				proj_root = _infer_project_root(p_obj)
				# 2026-11-10
				# "Isolate turn scratch answer files, allow pre-delivery response re-preparation, and enforce preemptive step/compaction budget stop":
				# https://github.com/dmitry-ai/harness/issues/49
				r = _check_turn_budget_gate(proj_root, p_obj)
				# 2026-11-24
				# "Skip blocking grounding on scratch drafts and add line locations to diagnostics":
				# https://github.com/dmitry-ai/harness/issues/214
				if None is r and (not _is_scratch_draft_file(norm_p)):
					# 2026-11-26 "Ban file:/// links for GitHub repositories and ground tagged GitHub URLs": https://github.com/dmitry-ai/harness/issues/264
					r = _check_doc_grounding_and_links(proj_root, content, p_obj)
	return r
# 2026-10-21
# "Enforce CommonMark two-space hard line breaks (DOC-4), ban unsolicited bullet lists, and add PreToolUse hook check_markdown_slop.py":
# https://github.com/dmitry-ai/harness/issues/14
def is_abbreviation_end(text):
	return bool(ABBR_RE.search(text.rstrip()))
# 2026-11-21
# "Add read-only answer-check pre-flight validation command to harness CLI":
# https://github.com/dmitry-ai/harness/issues/117
# 2026-11-24
# "Unify PreToolUse/Stop JSON hook harnesses, turns/*.json iterators, DOC-4 sentence scanning, and GitHub Evidence resolvers":
# https://github.com/dmitry-ai/harness/issues/79
def markdown_slop_issues(content: str) -> list[str]:
	return scan_doc4_sentence_issues(content, mode='hook')
# 2026-10-21
# "Enforce CommonMark two-space hard line breaks (DOC-4), ban unsolicited bullet lists, and add PreToolUse hook check_markdown_slop.py":
# https://github.com/dmitry-ai/harness/issues/14
# 2026-11-24
# "Unify PreToolUse/Stop JSON hook harnesses, turns/*.json iterators, DOC-4 sentence scanning, and GitHub Evidence resolvers":
# https://github.com/dmitry-ai/harness/issues/79
def main():
	run_json_hook(_evaluate_payload)
if '__main__' == __name__:
	main()
