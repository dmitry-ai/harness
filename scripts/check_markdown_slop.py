# 2026-10-21 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Enforce CommonMark two-space hard line breaks (DOC-4), ban unsolicited bullet lists, and add PreToolUse hook check_markdown_slop.py":
# https://github.com/dmitry-ai/harness/issues/14
# 2026-10-31 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Reorganize AI into universal harness repository, translate rules and documentation to English, format per P.md, and enforce issue-driven Git workflow":
# https://github.com/dmitry-ai/harness/issues/26
# 2026-11-01 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Eliminate local/external quote, metric, and identifier fabrication via local source grounding, Stop hook, fresh-read provenance, and A.A audit gates":
# https://github.com/dmitry-ai/harness/issues/34
import json
from pathlib import Path
import re
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent))
from agent_tools.source_grounding import local_source_grounding_issues
ABBREVIATIONS = '\\b(?:\\u0433|\\u0433\\u0433|\\u0442\\.\\u0434|\\u0442\\.\\u043f|\\u0441\\u043c|\\u0438\\u043c|\\u0434\\u0440|\\u043f\\u0440|\\u0443\\u043b|\\u0434|\\u043a\\u0432|\\u0440\\u0438\\u0441|\\u0442\\u0430\\u0431\\u043b|\\u0441\\u0442|\\u043f|\\u0447|\\u0440\\u0443\\u0431|\\u0442\\u044b\\u0441|\\u043c\\u043b\\u043d|\\u043c\\u043b\\u0440\\u0434|\\u0430\\u043d\\u0433\\u043b|\\u0440\\u0443\\u0441|\\u043d\\u0430\\u043f\\u0440|\\u043e\\u043a|vs|Mr|Mrs|Ms|Dr|St|Inc|Ltd|Co|Jr|Sr|e\\.g|i\\.e)\\.'
ABBR_RE = re.compile(ABBREVIATIONS, re.IGNORECASE)
MULTI_SENT_RE = re.compile('(?:[\\u0410-\\u044f\\u0401\\u0451A-Za-z0-9\\u00ab\\u00bb"(),:-]+\\s+){2,}[\\u0410-\\u044f\\u0401\\u0451A-Za-z0-9]+[.!?]\\s+[\\u0410-\\u042f\\u0401A-Z][a-z\\u0430-\\u044f\\u0451A-Za-z0-9]')
def is_abbreviation_end(text):
	r = bool(ABBR_RE.search(text.rstrip()))
	return r
def _infer_project_root(target: Path) -> Path:
	for anc in (target.parent, *target.parents):
		if anc.name in ('\ua616', '\ua66e', '_') and anc.parent.is_dir():
			return anc.parent
	return target.parent
def check_markdown_content(content, path=None):
	r = None
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
				r = f'Line {i + 1}: multiple sentences detected on a single line (rule DOC-4). Every sentence must start on a new physical line.\nFragment: {stripped[:80]}'
				break
			if i + 1 < len(lines):
				next_stripped = lines[i + 1].strip()
				if next_stripped and (not next_stripped.startswith(('#', '```', '~~~', '---', '===', '>', '|'))) and (not re.match('^(?:[-*+]|\\d+\\.)\\s+', next_stripped)) and (not (line.endswith('  ') or line.endswith('\\'))):
					r = f"Line {i + 1}: run-on text without a CommonMark hard line break detected. The line continues to the next without a blank line or two trailing spaces ('  \\n').\nLine: {stripped[:70]}"
					break
		if None is r and path:
			p_obj = Path(path)
			norm_p = path.replace('\\', '/').lower()
			if norm_p.endswith('/kb/analysis.md') and (p_obj.parent / 'source.md').is_file():
				issues = local_source_grounding_issues(_infer_project_root(p_obj), content, doc_path=p_obj)
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
			if name in ('write_file', 'edit_file') and path and path.lower().endswith('.md') and ('/req/' not in normalized_path):
				content = args.get('Content') if 'write_file' == name else args.get('Replacement')
				violation = check_markdown_content(content, path if 'write_file' == name else None)
				if violation:
					decision = {'decision': 'deny', 'reason': f'REJECTED (DOC-4 / VERIFY-1 Anti-Slop Hook): {violation}'}
	except Exception:
		decision = {'decision': 'allow'}
	sys.stdout.write(json.dumps(decision, ensure_ascii=False))
if '__main__' == __name__:
	main()
