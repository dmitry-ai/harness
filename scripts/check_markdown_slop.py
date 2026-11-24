# 2026-11-24 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Convert PreToolUse hook entry points to lazy tool-scoped imports":
# https://github.com/dmitry-ai/harness/issues/187
# 2026-11-24 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# https://github.com/dmitry-ai/harness/issues/79
# 2026-11-21 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Add read-only answer-check pre-flight validation command to harness CLI":
# https://github.com/dmitry-ai/harness/issues/117
# 2026-10-21 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Enforce CommonMark two-space hard line breaks (DOC-4), ban unsolicited bullet lists, and add PreToolUse hook check_markdown_slop.py":
# https://github.com/dmitry-ai/harness/issues/14
from pathlib import Path
import re
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent))
from agent_tools.hook_runtime import ABBREVIATIONS, ABBR_RE, MULTI_SENT_RE, iter_turn_state_files, run_json_hook, scan_doc4_sentence_issues
def _check_turn_budget_gate(proj_root: Path, target: Path) -> str | None:
	from agent_tools.path_registry import project_paths
	pp = project_paths(proj_root)
	norm_p = target.as_posix().lower()
	r = None
	if any((seg in norm_p for seg in pp.deliverable_segments)) and '/\ua616/' not in norm_p and '/\ua66e/' not in norm_p and '/\u26ef/' not in norm_p:
		for _, tdata in iter_turn_state_files(pp.turns_dir, exclude_hyphen=True):
			if tdata.get('status') in ('open', 'prepared', 'preparation_unverified'):
				bcheck = tdata.get('budget_check') or {}
				if bcheck.get('graceful_checkpoint_required') and (not bcheck.get('continuation_saved')):
					r = 'Turn Budget & Graceful Checkpoint Gate (M-4): active turn exceeded safe compaction/step budget (checkpoint_count >= 2, tool_step_count >= 120, or 5h window >= 400); persist verified findings to ꘖ/KB/Evidence/ and ꘖ/data/continuation.md and complete the turn via answer-prepare before generating new client deliverables'
					break
	return r
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
def _infer_project_root(target: Path) -> Path:
	from agent_tools.path_registry import resolve_project_root
	resolved = resolve_project_root(target)
	markers = ('\ua616', '_/\ua616', '\ua66e', '\U0001f56e')
	if resolved != target.resolve().parent or any(((resolved / m).is_dir() for m in markers)):
		r = resolved
	else:
		cwd_res = resolve_project_root(Path.cwd().resolve())
		r = cwd_res if any(((cwd_res / m).is_dir() for m in markers)) else resolved
	return r
def _is_request_journal_file(norm_p: str) -> bool:
	return '/req/' in norm_p or bool(re.search('(?:^|/)\\ua66e/(?:[^/]+/)?\\u227b/', norm_p))
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
def check_markdown_content(content, path=None):
	r = None
	if content and isinstance(content, str):
		slop = markdown_slop_issues(content)
		if slop:
			r = re.sub('^DOC-4\\s+', '', slop[0])
		if None is r and path:
			p_obj = Path(path)
			norm_p = path.replace('\\', '/').lower()
			if not _is_request_journal_file(norm_p) and '/source/' not in norm_p and 'source.md' != p_obj.name.lower():
				proj_root = _infer_project_root(p_obj)
				r = _check_turn_budget_gate(proj_root, p_obj)
				if None is r:
					from agent_tools.source_grounding import local_source_grounding_issues
					issues = local_source_grounding_issues(proj_root, content, doc_path=p_obj)
					if issues:
						r = '; '.join(issues[:3])
	return r
def is_abbreviation_end(text):
	return bool(ABBR_RE.search(text.rstrip()))
def markdown_slop_issues(content: str) -> list[str]:
	return scan_doc4_sentence_issues(content, mode='hook')
def main():
	run_json_hook(_evaluate_payload)
if '__main__' == __name__:
	main()
