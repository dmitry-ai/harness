# 2026-11-21 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Add read-only answer-check pre-flight validation command to harness CLI":
# https://github.com/dmitry-ai/harness/issues/117
# 2026-11-20 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Replace V2 verbal directory names with Ⰿ/♕/♙ symbols and add Antigravity hook runner":
# https://github.com/dmitry-ai/harness/issues/103
# 2026-11-20 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Wire V2 filesystem layout across Harness runtime subsystems and shared projections":
# https://github.com/dmitry-ai/harness/issues/101
# 2026-11-19 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Wire project path overlays across Harness subsystems with paths CLI and regression tests":
# https://github.com/dmitry-ai/harness/issues/96
# 2026-11-10 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Enforce local_source_grounding_issues across touched client deliverables, require post-compaction re-read of evicted tool outputs, and close A.A review bypass":
# https://github.com/dmitry-ai/harness/issues/50
# 2026-11-10 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Isolate turn scratch answer files, decouple turn/journal locks, allow pre-delivery re-preparation, and add preemptive step/compaction budget gate":
# https://github.com/dmitry-ai/harness/issues/49
# 2026-10-21 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Enforce CommonMark two-space hard line breaks (DOC-4), ban unsolicited bullet lists, and add PreToolUse hook check_markdown_slop.py":
# https://github.com/dmitry-ai/harness/issues/14
# 2026-10-31 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Reorganize AI into universal harness repository, translate rules and documentation to English, format per P.md, and enforce issue-driven Git workflow":
# https://github.com/dmitry-ai/harness/issues/26
# 2026-11-01 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Eliminate local/external quote, metric, and identifier fabrication via local source grounding, Stop hook, fresh-read provenance, and A.A audit gates":
# https://github.com/dmitry-ai/harness/issues/34
# 2026-11-02 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Replace special-case grounding/locale regexes with universal locale, relational claim arity, standalone-number, capability, and review gates":
# https://github.com/dmitry-ai/harness/issues/37
import json
from pathlib import Path
import re
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent))
from agent_tools.path_registry import project_paths, resolve_project_root
from agent_tools.source_grounding import local_source_grounding_issues
ABBREVIATIONS = '\\b(?:\\u0433|\\u0433\\u0433|\\u0442\\.\\u0434|\\u0442\\.\\u043f|\\u0441\\u043c|\\u0438\\u043c|\\u0434\\u0440|\\u043f\\u0440|\\u0443\\u043b|\\u0434|\\u043a\\u0432|\\u0440\\u0438\\u0441|\\u0442\\u0430\\u0431\\u043b|\\u0441\\u0442|\\u043f|\\u0447|\\u0440\\u0443\\u0431|\\u0442\\u044b\\u0441|\\u043c\\u043b\\u043d|\\u043c\\u043b\\u0440\\u0434|\\u0430\\u043d\\u0433\\u043b|\\u0440\\u0443\\u0441|\\u043d\\u0430\\u043f\\u0440|\\u043e\\u043a|vs|Mr|Mrs|Ms|Dr|St|Inc|Ltd|Co|Jr|Sr|e\\.g|i\\.e)\\.'
ABBR_RE = re.compile(ABBREVIATIONS, re.IGNORECASE)
MULTI_SENT_RE = re.compile('(?:[\\u0410-\\u044f\\u0401\\u0451A-Za-z0-9\\u00ab\\u00bb"(),:-]+\\s+){2,}[\\u0410-\\u044f\\u0401\\u0451A-Za-z0-9]+[.!?]\\s+[\\u0410-\\u042f\\u0401A-Z][a-z\\u0430-\\u044f\\u0451A-Za-z0-9]')
def is_abbreviation_end(text):
	r = bool(ABBR_RE.search(text.rstrip()))
	return r
def _is_request_journal_file(norm_p: str) -> bool:
	return '/req/' in norm_p or bool(re.search('(?:^|/)\\ua66e/(?:[^/]+/)?\\u227b/', norm_p))
def _infer_project_root(target: Path) -> Path:
	resolved = resolve_project_root(target)
	if resolved != target.resolve().parent or (resolved / '\ua616').is_dir() or (resolved / '_/\ua616').is_dir() or (resolved / '\ua66e').is_dir() or (resolved / '\U0001f56e').is_dir():
		return resolved
	cwd_res = resolve_project_root(Path.cwd().resolve())
	if (cwd_res / '\ua616').is_dir() or (cwd_res / '_/\ua616').is_dir() or (cwd_res / '\ua66e').is_dir() or (cwd_res / '\U0001f56e').is_dir():
		return cwd_res
	return resolved
def _check_turn_budget_gate(proj_root: Path, target: Path) -> str | None:
	pp = project_paths(proj_root)
	norm_p = target.as_posix().lower()
	if not any((seg in norm_p for seg in pp.deliverable_segments)) or '/\ua616/' in norm_p or '/\ua66e/' in norm_p or '/\u26ef/' in norm_p:
		return None
	turns_dir = pp.turns_dir
	if not turns_dir.is_dir():
		return None
	for tf in turns_dir.glob('*.json'):
		if '-' in tf.stem:
			continue
		try:
			tdata = json.loads(tf.read_text(encoding='utf-8'))
		except (OSError, ValueError):
			continue
		if isinstance(tdata, dict) and tdata.get('status') in ('open', 'prepared', 'preparation_unverified'):
			bcheck = tdata.get('budget_check') or {}
			if bcheck.get('graceful_checkpoint_required') and (not bcheck.get('continuation_saved')):
				return 'Turn Budget & Graceful Checkpoint Gate (M-4): active turn exceeded safe compaction/step budget (checkpoint_count >= 2, tool_step_count >= 120, or 5h window >= 400); persist verified findings to ꘖ/KB/Evidence/ and ꘖ/data/continuation.md and complete the turn via answer-prepare before generating new client deliverables'
	return None
def markdown_slop_issues(content: str) -> list[str]:
	issues: list[str] = []
	if content and isinstance(content, str):
		lines = content.split('\n')
		in_code_block = False
		in_frontmatter = False
		for i, line in enumerate(lines):
			stripped = line.strip()
			if 0 == i and '---' == stripped:
				in_frontmatter = True
				continue
			if in_frontmatter:
				if '---' == stripped:
					in_frontmatter = False
				continue
			if stripped.startswith(('```', '~~~')):
				in_code_block = not in_code_block
				continue
			if in_code_block or not stripped or stripped.startswith(('#', '|', '---', '===', '>')):
				continue
			cleaned = re.sub('`[^`]*`', 'code', line)
			cleaned = re.sub('\\[([^\\]]+)\\]\\([^)]+\\)', '\\1', cleaned)
			cleaned = re.sub('\\u00ab[^\\u00bb]*\\u00bb', '\u00abquote\u00bb', cleaned)
			cleaned = re.sub(ABBREVIATIONS, 'abbr', cleaned, flags=re.IGNORECASE)
			if MULTI_SENT_RE.search(cleaned):
				issues.append(f'DOC-4 Line {i + 1}: multiple sentences detected on a single line (rule DOC-4). Every sentence must start on a new physical line.\nFragment: {stripped[:80]}')
			if i + 1 < len(lines):
				next_stripped = lines[i + 1].strip()
				if next_stripped and (not next_stripped.startswith(('#', '```', '~~~', '---', '===', '>', '|'))) and (not re.match('^(?:[-*+]|\\d+\\.)\\s+', next_stripped)) and (not (line.endswith('  ') or line.endswith('\\'))):
					issues.append(f"DOC-4 Line {i + 1}: run-on text without a CommonMark hard line break detected. The line continues to the next without a blank line or two trailing spaces ('  \\n').\nLine: {stripped[:70]}")
	return issues
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
					issues = local_source_grounding_issues(proj_root, content, doc_path=p_obj)
					if issues:
						r = '; '.join(issues[:3])
	return r
def main():
	decision = {'decision': 'allow'}
	try:
		raw_input = sys.stdin.read()
		if raw_input.strip():
			payload = json.loads(raw_input)
			tool_call = payload.get('toolCall', {})
			name = tool_call.get('name', '')
			args = tool_call.get('args', {})
			path = args.get('Path', '')
			normalized_path = path.replace('\\', '/').lower()
			if name in ('write_file', 'edit_file') and path and path.lower().endswith('.md') and (not _is_request_journal_file(normalized_path)):
				if 'write_file' == name:
					content = args.get('Content')
				else:
					content = args.get('Replacement')
					p_file = Path(path)
					target_str = args.get('Target')
					if p_file.is_file() and isinstance(target_str, str) and target_str and isinstance(content, str):
						try:
							raw_doc = p_file.read_text(encoding='utf-8')
							if target_str in raw_doc:
								content = raw_doc.replace(target_str, content)
						except OSError:
							pass
				violation = check_markdown_content(content, path)
				if violation:
					decision = {'decision': 'deny', 'reason': f'REJECTED (DOC-4 / VERIFY-1 Anti-Slop Hook): {violation}'}
	except Exception:
		decision = {'decision': 'allow'}
	sys.stdout.write(json.dumps(decision, ensure_ascii=False))
if '__main__' == __name__:
	main()
