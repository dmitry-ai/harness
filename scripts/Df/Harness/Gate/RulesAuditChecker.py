# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from pathlib import Path
from agent_tools import links
import re
# 2026-11-26 "Move verification gate subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/381
class RulesAuditChecker:
	FENCE_RE = re.compile(r'```[\s\S]*?```')
	HTML_COMMENT_RE = re.compile(r'<!--[\s\S]*?-->')
	MAX_ALWAYS_ON_BYTES = 24000
	MAX_ALWAYS_ON_TOKENS = 7000
	MAX_RULE_FILE_BYTES = 6000
	WORKSPACE_AUTO_FILES = ('AGENTS.md', 'GEMINI.md')
	__BACKTICK_DOC_RE = re.compile(r'`((?:scripts|references|skills|platforms)/[^`\s]+|runtime\.json|paths\.json|validate_links\.py)`')
	__BARE_LEAD_RE = re.compile(r'^(?:see|read|check|refer\s+to|consult|also\s+see)\s+', re.I)
	__CODEX_LEAK_RE = re.compile(r'(?:--platform\s+codex\b|\bCODEX_THREAD_ID\b|\bCODEX_HOME\b|^#\s*Codex\b)', re.I | re.M)
	__CONTEXT_HINT_RE = re.compile(r'\b(?:when|before|after|only|for\s+(?:the|a|any|all|turning|creating|editing|handling|resolving|validating|checking|running)|unless|whenever|during|per|via|defined\s+in|documented\s+in|configured\s+in)\b', re.I)
	__FENCE_BLOCK_RE = re.compile(r'```[^\n]*\n([\s\S]*?)```')
	__MD_DOC_LINK_RE = re.compile(r'\[[^\]]+\]\(\s*<?\.\./[^)>\s]+>?\s*\)')
	__STALE_ALL_ALWAYS_RE = re.compile(r'all\s+shared\s+rules\s+remain\s+`?always_on`?', re.I)
	__STALE_ANSWER_MD_RE = re.compile(r'scratch/answer\.md\b')
	__VAGUE_TAIL_RE = re.compile(r'\bfor\s+(?:details|more\s+info(?:rmation)?|reference)\b', re.I)
	# @used-by :meth:`Df.Harness.Gate.RulesAuditor.RulesAuditor.audit()`
	def __init__(self, entries: list[dict], workspace_files: list[dict], primary: Path, *, max_file_bytes: int=MAX_RULE_FILE_BYTES, max_always_on_bytes: int=MAX_ALWAYS_ON_BYTES, max_always_on_tokens: int=MAX_ALWAYS_ON_TOKENS) -> None:
		self.__entries = entries
		self.__workspace_files = workspace_files
		self.__primary = primary
		self.__max_file_bytes = max_file_bytes
		self.__max_always_on_bytes = max_always_on_bytes
		self.__max_always_on_tokens = max_always_on_tokens
	# @used-by :meth:`RulesAuditChecker.check_skill_leakage_duplicates()`
	@staticmethod
	def __collect_skill_fingerprints(primary: Path) -> tuple[dict[str, str], dict[str, str]]:
		blocks: dict[str, str] = {}
		long_lines: dict[str, str] = {}
		for sp in sorted((Path(primary) / 'skills').glob('*/SKILL.md')):
			rel = f'skills/{sp.parent.name}/SKILL.md'
			txt = sp.read_text(encoding='utf-8-sig', errors='replace')
			for blk in RulesAuditChecker.__extract_fenced_blocks(txt):
				blocks.setdefault(blk, rel)
			for ln in RulesAuditChecker.__extract_long_proc_lines(txt):
				long_lines.setdefault(ln, rel)
		return (blocks, long_lines)
	# @used-by :meth:`RulesAuditChecker.__collect_skill_fingerprints()`
	# @used-by :meth:`RulesAuditChecker.check_skill_leakage_duplicates()`
	@staticmethod
	def __extract_fenced_blocks(text: str) -> list[str]:
		r: list[str] = []
		for m in RulesAuditChecker.__FENCE_BLOCK_RE.finditer(text or ''):
			lines = [' '.join(ln.strip().split()) for ln in m.group(1).splitlines() if ln.strip()]
			joined = '\n'.join(lines)
			if 3 <= len(lines) and 60 <= len(joined):
				r.append(joined)
		return r
	# @used-by :meth:`RulesAuditChecker.__collect_skill_fingerprints()`
	# @used-by :meth:`RulesAuditChecker.check_skill_leakage_duplicates()`
	@staticmethod
	def __extract_long_proc_lines(text: str) -> list[str]:
		body = RulesAuditChecker.FENCE_RE.sub('', text or '')
		r: list[str] = []
		for raw in body.splitlines():
			norm = ' '.join(raw.strip().split())
			if 90 <= len(norm) and (not norm.startswith(('#', '---', 'trigger:', 'description:', 'name:'))):
				r.append(norm)
		return r
	# @used-by :meth:`RulesAuditChecker.check_links_and_blind_references()`
	@staticmethod
	def __is_blind_reference_line(raw_line: str) -> bool:
		r = False
		if raw_line.strip() and (not re.match(r'^\s+[-*]\s+', raw_line)):
			has_doc = bool(RulesAuditChecker.__BACKTICK_DOC_RE.search(raw_line) or RulesAuditChecker.__MD_DOC_LINK_RE.search(raw_line))
			if has_doc:
				stripped = RulesAuditChecker.__MD_DOC_LINK_RE.sub('', RulesAuditChecker.__BACKTICK_DOC_RE.sub('', raw_line))
				words = [w for w in re.findall(r'[A-Za-z0-9_]+', stripped) if 1 < len(w)]
				is_vague_lead = bool(RulesAuditChecker.__BARE_LEAD_RE.match(raw_line.strip())) and (not RulesAuditChecker.__CONTEXT_HINT_RE.search(stripped) or bool(RulesAuditChecker.__VAGUE_TAIL_RE.search(stripped)))
				r = 6 > len(words) or is_vague_lead
		return r
	# @used-by :meth:`RulesAuditChecker.check_budget_smells()`
	# @used-by :meth:`RulesAuditChecker.check_cross_platform_leaks()`
	# @used-by :meth:`RulesAuditChecker.check_html_comments()`
	# @used-by :meth:`RulesAuditChecker.check_instruction_drift()`
	# @used-by :meth:`RulesAuditChecker.check_links_and_blind_references()`
	# @used-by :meth:`RulesAuditChecker.check_skill_leakage_duplicates()`
	@staticmethod
	def __issue(code: str, file_label: str, detail: str) -> dict[str, str]:
		return {'code': code, 'file': file_label, 'detail': detail}
	# @used-by :meth:`RulesAuditChecker.check_links_and_blind_references()`
	@staticmethod
	def __strip_frontmatter(text: str) -> str:
		m = re.match(r'^---\r?\n.*?\r?\n---\r?\n?', text or '', re.S)
		return text[m.end():] if m else (text or '')
	# @used-by :func:`agent_tools.rules_audit_checks.check_budget_smells()`
	# @used-by :meth:`RulesAuditChecker.check()`
	@staticmethod
	def check_budget_smells(entries: list[dict], workspace_files: list[dict], *, max_file_bytes: int=MAX_RULE_FILE_BYTES, max_always_on_bytes: int=MAX_ALWAYS_ON_BYTES, max_always_on_tokens: int=MAX_ALWAYS_ON_TOKENS) -> list[dict]:
		r: list[dict] = []
		for entry in entries:
			if max_file_bytes < entry['bytes']:
				r.append(RulesAuditChecker.__issue('PER_FILE_BUDGET', f"rules/{entry['name']}", f"Rule file is {entry['bytes']:,} bytes (limit {max_file_bytes:,} bytes)"))
		always = [e for e in entries if 'always_on' == e['trigger']]
		total_bytes = sum((e['bytes'] for e in always)) + sum((w['bytes'] for w in workspace_files))
		total_tokens = sum((e['estimated_tokens'] for e in always)) + sum((w['estimated_tokens'] for w in workspace_files))
		if max_always_on_bytes < total_bytes:
			r.append(RulesAuditChecker.__issue('AGGREGATE_ALWAYS_ON_BYTES', 'rules/*', f'Aggregate always_on plus workspace auto-loaded rules is {total_bytes:,} bytes (limit {max_always_on_bytes:,} bytes)'))
		if max_always_on_tokens < total_tokens:
			r.append(RulesAuditChecker.__issue('AGGREGATE_ALWAYS_ON_TOKENS', 'rules/*', f'Aggregate always_on plus workspace auto-loaded rules is {total_tokens:,} estimated tokens (limit {max_always_on_tokens:,} tokens)'))
		return r
	# @used-by :func:`agent_tools.rules_audit_checks.check_cross_platform_leaks()`
	# @used-by :meth:`RulesAuditChecker.check()`
	@staticmethod
	def check_cross_platform_leaks(entries: list[dict], workspace_files: list[dict]) -> list[dict]:
		r: list[dict] = []
		targets = [(f"rules/{e['name']}", e['text']) for e in entries] + [(w['label'], w['text']) for w in workspace_files]
		for label, text in targets:
			m = RulesAuditChecker.__CODEX_LEAK_RE.search(RulesAuditChecker.FENCE_RE.sub('', text))
			if m:
				r.append(RulesAuditChecker.__issue('CROSS_PLATFORM_CODEX_LEAK', label, f'Antigravity-loaded file contains Codex-only directive {m.group(0)!r}'))
		return r
	# @used-by :func:`agent_tools.rules_audit_checks.check_html_comments()`
	# @used-by :meth:`RulesAuditChecker.check()`
	@staticmethod
	def check_html_comments(entries: list[dict]) -> list[dict]:
		r: list[dict] = []
		for entry in entries:
			stripped = RulesAuditChecker.FENCE_RE.sub('', entry['text'])
			found = RulesAuditChecker.HTML_COMMENT_RE.findall(stripped)
			if found:
				r.append(RulesAuditChecker.__issue('NON_STRIPPED_HTML_COMMENT', f"rules/{entry['name']}", f'Found {len(found)} HTML comment(s) outside code fences in shared rule'))
		return r
	# @used-by :func:`agent_tools.rules_audit_checks.check_instruction_drift()`
	# @used-by :meth:`RulesAuditChecker.check()`
	@staticmethod
	def check_instruction_drift(entries: list[dict], primary: Path) -> list[dict]:
		r: list[dict] = []
		has_model_decision = any(('model_decision' == e['trigger'] for e in entries))
		for entry in entries:
			if has_model_decision and RulesAuditChecker.__STALE_ALL_ALWAYS_RE.search(entry['text']):
				r.append(RulesAuditChecker.__issue('INSTRUCTION_DRIFT', f"rules/{entry['name']}", 'Rule still claims all shared rules remain always_on while model_decision rules exist'))
			if RulesAuditChecker.__STALE_ANSWER_MD_RE.search(entry['text']):
				r.append(RulesAuditChecker.__issue('INSTRUCTION_DRIFT', f"rules/{entry['name']}", 'Stale scratch/answer.md reference; use answer-<turn_key>.md'))
		codex_md = Path(primary) / 'platforms/codex.md'
		if codex_md.is_file() and RulesAuditChecker.__STALE_ANSWER_MD_RE.search(codex_md.read_text(encoding='utf-8-sig', errors='replace')):
			r.append(RulesAuditChecker.__issue('INSTRUCTION_DRIFT', 'platforms/codex.md', 'Stale scratch/answer.md reference in Codex adapter; use answer-<turn_key>.md'))
		return r
	# @used-by :func:`agent_tools.rules_audit_checks.check_links_and_blind_references()`
	# @used-by :meth:`RulesAuditChecker.check()`
	@staticmethod
	def check_links_and_blind_references(entries: list[dict]) -> list[dict]:
		r: list[dict] = []
		for entry in entries:
			label = f"rules/{entry['name']}"
			for err in links.validate_file(entry['path'], local_anchors=True, readable_links=True):
				r.append(RulesAuditChecker.__issue('BROKEN_LINK', label, err))
			body = RulesAuditChecker.FENCE_RE.sub('', RulesAuditChecker.__strip_frontmatter(entry['text']))
			for idx, raw_line in enumerate(body.splitlines(), 1):
				if RulesAuditChecker.__is_blind_reference_line(raw_line):
					r.append(RulesAuditChecker.__issue('BLIND_REFERENCE', label, f'Line {idx} references a document without purpose or activation context: {raw_line.strip()[:100]}'))
		return r
	# @used-by :func:`agent_tools.rules_audit_checks.check_skill_leakage_duplicates()`
	# @used-by :meth:`RulesAuditChecker.check()`
	@staticmethod
	def check_skill_leakage_duplicates(entries: list[dict], primary: Path) -> list[dict]:
		r: list[dict] = []
		skill_blocks, skill_lines = RulesAuditChecker.__collect_skill_fingerprints(primary)
		for entry in entries:
			if 'always_on' != entry['trigger']:
				continue
			label = f"rules/{entry['name']}"
			for blk in RulesAuditChecker.__extract_fenced_blocks(entry['text']):
				if blk in skill_blocks:
					r.append(RulesAuditChecker.__issue('SKILL_LEAKAGE_DUPLICATE', label, f'Duplicated fenced CLI/procedure block also defined in {skill_blocks[blk]}'))
			for ln in RulesAuditChecker.__extract_long_proc_lines(entry['text']):
				if ln in skill_lines:
					r.append(RulesAuditChecker.__issue('SKILL_LEAKAGE_DUPLICATE', label, f'Duplicated procedure line also defined in {skill_lines[ln]}: {ln[:80]}'))
		return r
	# @used-by :meth:`Df.Harness.Gate.RulesAuditor.RulesAuditor.audit()`
	def check(self) -> list[dict]:
		return [
			*RulesAuditChecker.check_budget_smells(self.__entries, self.__workspace_files, max_file_bytes=self.__max_file_bytes, max_always_on_bytes=self.__max_always_on_bytes, max_always_on_tokens=self.__max_always_on_tokens),
			*RulesAuditChecker.check_html_comments(self.__entries),
			*RulesAuditChecker.check_cross_platform_leaks(self.__entries, self.__workspace_files),
			*RulesAuditChecker.check_links_and_blind_references(self.__entries),
			*RulesAuditChecker.check_instruction_drift(self.__entries, self.__primary),
			*RulesAuditChecker.check_skill_leakage_duplicates(self.__entries, self.__primary),
		]
