# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from pathlib import Path
from .rules_audit_checks import (
	MAX_ALWAYS_ON_BYTES,
	MAX_ALWAYS_ON_TOKENS,
	MAX_RULE_FILE_BYTES,
	WORKSPACE_AUTO_FILES,
	_FENCE_RE,
	_HTML_COMMENT_RE,
	check_budget_smells,
	check_cross_platform_leaks,
	check_html_comments,
	check_instruction_drift,
	check_links_and_blind_references,
	check_skill_leakage_duplicates,
)
from .rules_manifest import estimate_tokens, inspect_shared_rule, parse_rule_frontmatter
import re
_SEMANTIC_AUDIT_CHECKLIST = (
	'Read every listed shared rule file and skill file in full before issuing findings.  ',
	'Evaluate the four arXiv:2606.15828 §V-B configuration smells plus /doctor prompt-audit hygiene criteria:  ',
	'1. Skill Leakage — rare or domain-specific multi-step workflows remaining in always_on rules instead of skills or model_decision modules.  ',
	'1. Lint Leakage — mechanically enforceable style or formatting instructions that duplicate pre-commit or PreToolUse gates.  ',
	'1. Blind References — file or tool paths mentioned without stating their purpose and activation condition.  ',
	'1. Conflicting Instructions — contradictory, outdated, or cross-platform directives (advisory report only; verify every candidate with exact quotes because LLM precision on conflicts was 57% in arXiv:2606.15828).  ',
	'1. /doctor prompt-audit — obsolete clauses, duplicated rules, and concrete extraction candidates into skills or deterministic hooks.  ',
	'Report each finding neutrally with file path, line range, verbatim quote, smell category, and verdict (confirmed_defect, advisory_candidate, or no_defect_found).  ',
)
_SHARED_RULE_PATH_RE = re.compile(r'/rules/[^/]+\.md$', re.I)
# @used-by :func:`check_shared_rule_edit()`
def _check_shared_rule_content(target: Path, new_text: str) -> str | None:
	byte_len = len(new_text.encode('utf-8'))
	if MAX_RULE_FILE_BYTES < byte_len:
		r: str | None = f'RULES-BUDGET-GATE (PER_FILE_BUDGET): Shared rule {target.name} ({byte_len:,} bytes) exceeds the {MAX_RULE_FILE_BYTES:,}-byte per-file limit.'
	elif _HTML_COMMENT_RE.search(_FENCE_RE.sub('', new_text)):
		r = f'RULES-BUDGET-GATE (NON_STRIPPED_HTML_COMMENT): Shared rule {target.name} contains HTML comment(s) outside code fences; strip HTML comments from rules/*.md.'
	else:
		agg_bytes, agg_tokens = _prospective_always_on_totals(target, new_text)
		if MAX_ALWAYS_ON_BYTES < agg_bytes:
			r = f'RULES-BUDGET-GATE (AGGREGATE_ALWAYS_ON_BYTES): Aggregate always_on rules ({agg_bytes:,} bytes) would exceed the {MAX_ALWAYS_ON_BYTES:,}-byte budget.'
		elif MAX_ALWAYS_ON_TOKENS < agg_tokens:
			r = f'RULES-BUDGET-GATE (AGGREGATE_ALWAYS_ON_TOKENS): Aggregate always_on rules ({agg_tokens:,} estimated tokens) would exceed the {MAX_ALWAYS_ON_TOKENS:,}-token budget.'
		else:
			r = None
	return r
# @used-by :func:`audit_rules()`
def _inspect_workspace_auto_files(primary: Path, workspace: Path | None) -> list[dict]:
	roots: list[Path] = []
	for cand in (workspace, primary):
		if None is not cand:
			resolved = Path(cand).resolve()
			if resolved not in roots:
				roots.append(resolved)
	r: list[dict] = []
	for root in roots:
		for name in WORKSPACE_AUTO_FILES:
			fp = root / name
			if fp.is_file():
				raw = fp.read_bytes()
				txt = raw.decode('utf-8-sig', errors='replace')
				r.append({'path': fp, 'label': name if root == roots[0] else fp.as_posix(), 'bytes': len(raw), 'estimated_tokens': estimate_tokens(txt), 'text': txt})
	return r
# @used-by :func:`audit_rules()`
def _load_rule_entries(primary: Path, overrides: dict[Path, bytes] | None=None) -> list[dict]:
	ov = {Path(k).resolve(): v for k, v in (overrides or {}).items()}
	r: list[dict] = []
	for path in sorted((Path(primary) / 'rules').glob('*.md')):
		resolved = path.resolve()
		if resolved in ov:
			raw = ov[resolved]
			txt = raw.decode('utf-8-sig', errors='replace')
			meta = parse_rule_frontmatter(txt)
			r.append({'path': resolved, 'name': path.name, 'bytes': len(raw), 'lines': len(txt.splitlines()), 'words': len(txt.split()), 'estimated_tokens': estimate_tokens(txt), 'trigger': str(meta.get('trigger') or '').strip(), 'description': str(meta.get('description') or '').strip(), 'text': txt})
		else:
			item = inspect_shared_rule(path)
			item['text'] = path.read_text(encoding='utf-8-sig', errors='replace')
			r.append(item)
	return r
# @used-by :func:`_check_shared_rule_content()`
def _prospective_always_on_totals(target: Path, new_text: str) -> tuple[int, int]:
	rules_dir = target.parent
	resolved_target = target.resolve()
	meta = parse_rule_frontmatter(new_text)
	total_bytes = len(new_text.encode('utf-8')) if 'always_on' == meta.get('trigger') else 0
	total_tokens = estimate_tokens(new_text) if 'always_on' == meta.get('trigger') else 0
	for sib in sorted(rules_dir.glob('*.md')) if rules_dir.is_dir() else ():
		if sib.resolve() != resolved_target:
			info = inspect_shared_rule(sib)
			if 'always_on' == info['trigger']:
				total_bytes += info['bytes']
				total_tokens += info['estimated_tokens']
	return (total_bytes, total_tokens)
# @used-by :func:`check_shared_rule_edit()`
def _prospective_rule_text(name: str, args: dict, target: Path) -> str | None:
	r = None
	if 'write_file' == name:
		raw = args.get('Content')
		r = raw if isinstance(raw, str) else None
	elif 'edit_file' == name:
		tgt = args.get('Target')
		repl = args.get('Replacement')
		if isinstance(tgt, str) and isinstance(repl, str) and target.is_file():
			old = target.read_text(encoding='utf-8-sig', errors='replace')
			r = old.replace(tgt, repl) if tgt in old else None
	return r
# @used-by :func:`verify_staged_rules_audit()`
def _read_staged_overrides(repo_root: Path, staged_paths: list[str], use_index: bool) -> dict[Path, bytes]:
	r: dict[Path, bytes] = {}
	if use_index:
		from .tdd.enforcement import _git_index_text
		for rel in staged_paths:
			norm = rel.replace('\\', '/')
			if norm.startswith('rules/') and norm.endswith('.md'):
				txt = _git_index_text(repo_root, norm)
				if None is not txt:
					r[(repo_root / norm).resolve()] = txt.encode('utf-8')
	return r
# @used-by :func:`verify_staged_rules_audit()`
def _touches_audit_surface(staged_paths: list[str]) -> bool:
	r = False
	for rel in staged_paths:
		norm = rel.replace('\\', '/')
		if norm.startswith(('rules/', 'skills/', 'platforms/')) or norm in WORKSPACE_AUTO_FILES:
			r = True
			break
	return r
# 2026-11-26
# "Add deterministic rules-audit CLI and aggregate budget enforcement":
# https://github.com/dmitry-ai/harness/issues/244
# @used-by :func:`agent_tools.cli_registry._exec_rules_audit()`
# @used-by :func:`agent_tools.rules_manifest._build_doctor_rule_meta()`
# @used-by :func:`verify_staged_rules_audit()`
# @used-by :meth:`test_arch_rules_contract.ArchRulesContractTests.test_architecture_rule_is_compact_always_on_and_passes_doctor_and_rules_audit()`
# @used-by :meth:`test_ask_question_pre_tool_gate.AskQuestionPreToolGateTests.test_pre_tool_gate_blocks_stop_gate_bypass_and_docs_codify_rule()`
# @used-by :meth:`test_cli_command_grounding.CliCommandGroundingTests.test_exec2_rule_contains_shadow_replay_requirement_and_passes_rules_audit()`
# @used-by :meth:`test_diff_executability_contract.DiffExecutabilityContractTests.test_docs_and_rules_codify_contract_within_rules_audit_budgets()`
# @used-by :meth:`test_repo_tags_docs.RepoTagsDocsTests.test_rules_and_docs_codify_daily_tagging_and_link6_within_budgets()`
# @used-by :meth:`test_rules_audit.RulesAuditTests.test_detects_broken_links_blind_references_drift_and_skill_leakage()`
# @used-by :meth:`test_rules_audit.RulesAuditTests.test_detects_budget_html_comment_and_cross_platform_codex_leaks()`
# @used-by :meth:`test_snapshot_latency_and_delegation_policy.SnapshotLatencyAndDelegationPolicyTests.test_delegation_rule_and_worktree_doc_codify_multi_track_policy_and_pass_audits()`
def audit_rules(primary: str | Path, *, workspace: str | Path | None=None, max_file_bytes: int=MAX_RULE_FILE_BYTES, max_always_on_bytes: int=MAX_ALWAYS_ON_BYTES, max_always_on_tokens: int=MAX_ALWAYS_ON_TOKENS, overrides: dict[Path, bytes] | None=None) -> dict:
	prim = Path(primary).resolve()
	ws = Path(workspace).resolve() if None is not workspace else None
	entries = _load_rule_entries(prim, overrides=overrides)
	ws_files = _inspect_workspace_auto_files(prim, ws)
	issues = [
		*check_budget_smells(entries, ws_files, max_file_bytes=max_file_bytes, max_always_on_bytes=max_always_on_bytes, max_always_on_tokens=max_always_on_tokens),
		*check_html_comments(entries),
		*check_cross_platform_leaks(entries, ws_files),
		*check_links_and_blind_references(entries),
		*check_instruction_drift(entries, prim),
		*check_skill_leakage_duplicates(entries, prim),
	]
	always = [e for e in entries if 'always_on' == e['trigger']]
	always_bytes = sum((e['bytes'] for e in always))
	always_tokens = sum((e['estimated_tokens'] for e in always))
	ws_bytes = sum((w['bytes'] for w in ws_files))
	ws_tokens = sum((w['estimated_tokens'] for w in ws_files))
	return {'valid': not issues, 'primary': prim.as_posix(), 'workspace': ws.as_posix() if None is not ws else None, 'rule_count': len(entries), 'always_on_count': len(always), 'model_decision_count': sum((1 for e in entries if 'model_decision' == e['trigger'])), 'always_on_bytes': always_bytes, 'always_on_estimated_tokens': always_tokens, 'workspace_auto_bytes': ws_bytes, 'total_always_on_bytes': always_bytes + ws_bytes, 'total_always_on_tokens': always_tokens + ws_tokens, 'limits': {'max_file_bytes': max_file_bytes, 'max_always_on_bytes': max_always_on_bytes, 'max_always_on_tokens': max_always_on_tokens}, 'issue_count': len(issues), 'issues': issues}
# @used-by :func:`agent_tools.cli_registry._exec_rules_audit()`
def build_semantic_audit_brief(primary: str | Path, *, workspace: str | Path | None=None) -> str:
	prim = Path(primary).resolve()
	ws_label = Path(workspace).resolve().as_posix() if None is not workspace else prim.as_posix()
	rules = [f'- `{p.as_posix()}`' for p in sorted((prim / 'rules').glob('*.md'))]
	skills = [f'- `{p.as_posix()}`' for p in sorted((prim / 'skills').glob('*/SKILL.md'))]
	lines = ['# Neutral Read-Only A.A Semantic Rules Audit Brief', '', 'Role: independent read-only A.A auditor (REVIEW-1 / REVIEW-4; do not modify files or invoke hidden model sessions).  ', f'Primary Harness root: `{prim.as_posix()}`.  ', f'Workspace root: `{ws_label}`.  ', *_SEMANTIC_AUDIT_CHECKLIST, 'Shared rules to read in full:  ', *rules, 'Skills to cross-check for leakage or duplication:  ', *skills]
	return '\n'.join(lines) + '\n'
# @used-by :func:`agent_tools.gates.rules_budget.check()`
def check_shared_rule_edit(name: str, args: dict) -> str | None:
	r = None
	raw_path = str(args.get('Path') or '').strip()
	norm = raw_path.replace('\\', '/')
	if norm and ('/.agents/rules/' not in norm.lower()) and _SHARED_RULE_PATH_RE.search(norm):
		target = Path(raw_path)
		new_text = _prospective_rule_text(name, args, target)
		is_harness_dir = (target.parent.parent / 'paths.json').is_file() or (target.parent.parent / 'runtime.json').is_file()
		if None is not new_text and (is_harness_dir or bool(parse_rule_frontmatter(new_text).get('trigger'))):
			r = _check_shared_rule_content(target, new_text)
	return r
# @used-by :func:`agent_tools.cli_registry._format_rules_audit()`
def format_rules_audit_text(report: dict) -> str:
	if report.get('semantic_brief'):
		r = str(report['semantic_brief'])
	else:
		status = 'PASS' if report.get('valid') else 'FAIL'
		lines = [f"rules-audit {status}: rules={report['rule_count']} always_on={report['always_on_count']} model_decision={report['model_decision_count']} total_always_on_bytes={report['total_always_on_bytes']} total_always_on_tokens={report['total_always_on_tokens']} issues={report['issue_count']}"]
		for item in report.get('issues') or ():
			lines.append(f"- [{item['code']}] {item['file']}: {item['detail']}")
		r = '\n'.join(lines) + '\n'
	return r
# @used-by :func:`agent_tools.staged_gates.verify_staged_extra_gates()`
def verify_staged_rules_audit(repo_root: Path, staged_paths: list[str], *, use_index: bool=True) -> list[str]:
	r: list[str] = []
	repo = Path(repo_root).resolve()
	if (repo / 'rules').is_dir() and _touches_audit_surface(staged_paths):
		overrides = _read_staged_overrides(repo, staged_paths, use_index)
		rep = audit_rules(repo, workspace=repo, overrides=overrides)
		r = [f"RULES-AUDIT ({item['code']}): {item['file']} — {item['detail']}" for item in rep['issues']]
	return r
