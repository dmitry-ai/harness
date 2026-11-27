# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from pathlib import Path
from Df.Harness.Gate.RulesAuditChecker import RulesAuditChecker
from Df.Harness.Gate.RulesManifest import RulesManifest
import re
# 2026-11-26 "Move verification gate subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/381
class RulesAuditor:
	__SEMANTIC_AUDIT_CHECKLIST = (
		'Read every listed shared rule file and skill file in full before issuing findings.  ',
		'Evaluate the four arXiv:2606.15828 §V-B configuration smells plus /doctor prompt-audit hygiene criteria:  ',
		'1. Skill Leakage — rare or domain-specific multi-step workflows remaining in always_on rules instead of skills or model_decision modules.  ',
		'1. Lint Leakage — mechanically enforceable style or formatting instructions that duplicate pre-commit or PreToolUse gates.  ',
		'1. Blind References — file or tool paths mentioned without stating their purpose and activation condition.  ',
		'1. Conflicting Instructions — contradictory, outdated, or cross-platform directives (advisory report only; verify every candidate with exact quotes because LLM precision on conflicts was 57% in arXiv:2606.15828).  ',
		'1. /doctor prompt-audit — obsolete clauses, duplicated rules, and concrete extraction candidates into skills or deterministic hooks.  ',
		'Report each finding neutrally with file path, line range, verbatim quote, smell category, and verdict (confirmed_defect, advisory_candidate, or no_defect_found).  ',
	)
	__SHARED_RULE_PATH_RE = re.compile(r'/rules/[^/]+\.md$', re.I)
	# @used-by :func:`agent_tools.rules_audit.audit_rules()`
	# @used-by :meth:`Df.Harness.Gate.RulesManifest.RulesManifest.__build_doctor_rule_meta()`
	# @used-by :meth:`RulesAuditor.verify_staged()`
	# @used-by :meth:`test_df_harness_s11_wave2b_gate.DfHarnessS11Wave2bGateTests.test_gate_staged_and_repo_checks()`
	# @used-by :meth:`test_df_harness_s11_wave2b_gate_cov.DfHarnessS11Wave2bGateCovTests.test_rules_auditor_subprocess_and_xref_checker()`
	def __init__(self, primary: str | Path, *, workspace: str | Path | None=None, max_file_bytes: int=RulesAuditChecker.MAX_RULE_FILE_BYTES, max_always_on_bytes: int=RulesAuditChecker.MAX_ALWAYS_ON_BYTES, max_always_on_tokens: int=RulesAuditChecker.MAX_ALWAYS_ON_TOKENS, overrides: dict[Path, bytes] | None=None) -> None:
		self.__primary = Path(primary).resolve()
		self.__workspace = Path(workspace).resolve() if None is not workspace else None
		self.__max_file_bytes = max_file_bytes
		self.__max_always_on_bytes = max_always_on_bytes
		self.__max_always_on_tokens = max_always_on_tokens
		self.__overrides = overrides
	# @used-by :meth:`RulesAuditor.check_shared_rule_edit()`
	@staticmethod
	def __check_shared_rule_content(target: Path, new_text: str) -> str | None:
		byte_len = len(new_text.encode('utf-8'))
		if RulesAuditChecker.MAX_RULE_FILE_BYTES < byte_len:
			r: str | None = f'RULES-BUDGET-GATE (PER_FILE_BUDGET): Shared rule {target.name} ({byte_len:,} bytes) exceeds the {RulesAuditChecker.MAX_RULE_FILE_BYTES:,}-byte per-file limit.'
		elif RulesAuditChecker.HTML_COMMENT_RE.search(RulesAuditChecker.FENCE_RE.sub('', new_text)):
			r = f'RULES-BUDGET-GATE (NON_STRIPPED_HTML_COMMENT): Shared rule {target.name} contains HTML comment(s) outside code fences; strip HTML comments from rules/*.md.'
		else:
			agg_bytes, agg_tokens = RulesAuditor.__prospective_always_on_totals(target, new_text)
			if RulesAuditChecker.MAX_ALWAYS_ON_BYTES < agg_bytes:
				r = f'RULES-BUDGET-GATE (AGGREGATE_ALWAYS_ON_BYTES): Aggregate always_on rules ({agg_bytes:,} bytes) would exceed the {RulesAuditChecker.MAX_ALWAYS_ON_BYTES:,}-byte budget.'
			elif RulesAuditChecker.MAX_ALWAYS_ON_TOKENS < agg_tokens:
				r = f'RULES-BUDGET-GATE (AGGREGATE_ALWAYS_ON_TOKENS): Aggregate always_on rules ({agg_tokens:,} estimated tokens) would exceed the {RulesAuditChecker.MAX_ALWAYS_ON_TOKENS:,}-token budget.'
			else:
				r = None
		return r
	# @used-by :meth:`RulesAuditor.audit()`
	@staticmethod
	def __inspect_workspace_auto_files(primary: Path, workspace: Path | None) -> list[dict]:
		roots: list[Path] = []
		for cand in (workspace, primary):
			if None is not cand:
				resolved = Path(cand).resolve()
				if resolved not in roots:
					roots.append(resolved)
		r: list[dict] = []
		for root in roots:
			for name in RulesAuditChecker.WORKSPACE_AUTO_FILES:
				fp = root / name
				if fp.is_file():
					raw = fp.read_bytes()
					txt = raw.decode('utf-8-sig', errors='replace')
					r.append({'path': fp, 'label': name if root == roots[0] else fp.as_posix(), 'bytes': len(raw), 'estimated_tokens': RulesManifest.estimate_tokens(txt), 'text': txt})
		return r
	# @used-by :meth:`RulesAuditor.audit()`
	@staticmethod
	def __load_rule_entries(primary: Path, overrides: dict[Path, bytes] | None=None) -> list[dict]:
		ov = {Path(k).resolve(): v for k, v in (overrides or {}).items()}
		r: list[dict] = []
		for path in sorted((Path(primary) / 'rules').glob('*.md')):
			resolved = path.resolve()
			if resolved in ov:
				raw = ov[resolved]
				txt = raw.decode('utf-8-sig', errors='replace')
				meta = RulesManifest.parse_frontmatter(txt)
				r.append({'path': resolved, 'name': path.name, 'bytes': len(raw), 'lines': len(txt.splitlines()), 'words': len(txt.split()), 'estimated_tokens': RulesManifest.estimate_tokens(txt), 'trigger': str(meta.get('trigger') or '').strip(), 'description': str(meta.get('description') or '').strip(), 'text': txt})
			else:
				item = RulesManifest.inspect_rule(path)
				item['text'] = path.read_text(encoding='utf-8-sig', errors='replace')
				r.append(item)
		return r
	# @used-by :meth:`RulesAuditor.__check_shared_rule_content()`
	@staticmethod
	def __prospective_always_on_totals(target: Path, new_text: str) -> tuple[int, int]:
		rules_dir = target.parent
		resolved_target = target.resolve()
		meta = RulesManifest.parse_frontmatter(new_text)
		total_bytes = len(new_text.encode('utf-8')) if 'always_on' == meta.get('trigger') else 0
		total_tokens = RulesManifest.estimate_tokens(new_text) if 'always_on' == meta.get('trigger') else 0
		for sib in sorted(rules_dir.glob('*.md')) if rules_dir.is_dir() else ():
			if sib.resolve() != resolved_target:
				info = RulesManifest.inspect_rule(sib)
				if 'always_on' == info['trigger']:
					total_bytes += info['bytes']
					total_tokens += info['estimated_tokens']
		return (total_bytes, total_tokens)
	# @used-by :meth:`RulesAuditor.check_shared_rule_edit()`
	@staticmethod
	def __prospective_rule_text(name: str, args: dict, target: Path) -> str | None:
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
	# @used-by :meth:`RulesAuditor.verify_staged()`
	@staticmethod
	def __read_staged_overrides(repo_root: Path, staged_paths: list[str], use_index: bool) -> dict[Path, bytes]:
		r: dict[Path, bytes] = {}
		if use_index:
			from Df.Harness.Tdd.Enforcement import Enforcement
			for rel in staged_paths:
				norm = rel.replace('\\', '/')
				if norm.startswith('rules/') and norm.endswith('.md'):
					txt = Enforcement.git_index_text(repo_root, norm)
					if None is not txt:
						r[(repo_root / norm).resolve()] = txt.encode('utf-8')
		return r
	# @used-by :meth:`RulesAuditor.verify_staged()`
	@staticmethod
	def __touches_audit_surface(staged_paths: list[str]) -> bool:
		r = False
		for rel in staged_paths:
			norm = rel.replace('\\', '/')
			if norm.startswith(('rules/', 'skills/', 'platforms/')) or norm in RulesAuditChecker.WORKSPACE_AUTO_FILES:
				r = True
				break
		return r
	# @used-by :func:`agent_tools.rules_audit.build_semantic_audit_brief()`
	# @used-by :meth:`test_df_harness_s11_wave2b_gate_cov.DfHarnessS11Wave2bGateCovTests.test_rules_auditor_subprocess_and_xref_checker()`
	@staticmethod
	def build_semantic_brief(primary: str | Path, *, workspace: str | Path | None=None) -> str:
		prim = Path(primary).resolve()
		ws_label = Path(workspace).resolve().as_posix() if None is not workspace else prim.as_posix()
		rules = [f'- `{p.as_posix()}`' for p in sorted((prim / 'rules').glob('*.md'))]
		skills = [f'- `{p.as_posix()}`' for p in sorted((prim / 'skills').glob('*/SKILL.md'))]
		lines = ['# Neutral Read-Only A.A Semantic Rules Audit Brief', '', 'Role: independent read-only A.A auditor (REVIEW-1 / REVIEW-4; do not modify files or invoke hidden model sessions).  ', f'Primary Harness root: `{prim.as_posix()}`.  ', f'Workspace root: `{ws_label}`.  ', *RulesAuditor.__SEMANTIC_AUDIT_CHECKLIST, 'Shared rules to read in full:  ', *rules, 'Skills to cross-check for leakage or duplication:  ', *skills]
		return '\n'.join(lines) + '\n'
	# @used-by :func:`agent_tools.rules_audit.check_shared_rule_edit()`
	# @used-by :meth:`Df.Harness.Gate.RulesBudgetGate.RulesBudgetGate.check()`
	# @used-by :meth:`test_df_harness_s11_wave2b_gate_cov.DfHarnessS11Wave2bGateCovTests.test_rules_auditor_subprocess_and_xref_checker()`
	# @used-by :meth:`test_df_harness_s11_wave2b_tail_cov.DfHarnessS11Wave2bTailCovTests.test_gate_registry_repo_tag_and_rules_auditor()`
	@staticmethod
	def check_shared_rule_edit(name: str, args: dict) -> str | None:
		r = None
		raw_path = str(args.get('Path') or '').strip()
		norm = raw_path.replace('\\', '/')
		if norm and ('/.agents/rules/' not in norm.lower()) and RulesAuditor.__SHARED_RULE_PATH_RE.search(norm):
			target = Path(raw_path)
			new_text = RulesAuditor.__prospective_rule_text(name, args, target)
			is_harness_dir = (target.parent.parent / 'paths.json').is_file() or (target.parent.parent / 'runtime.json').is_file()
			if None is not new_text and (is_harness_dir or bool(RulesManifest.parse_frontmatter(new_text).get('trigger'))):
				r = RulesAuditor.__check_shared_rule_content(target, new_text)
		return r
	# @used-by :func:`agent_tools.rules_audit.format_rules_audit_text()`
	# @used-by :meth:`test_df_harness_s11_wave2b_gate_cov.DfHarnessS11Wave2bGateCovTests.test_rules_auditor_subprocess_and_xref_checker()`
	@staticmethod
	def format_text(report: dict) -> str:
		if report.get('semantic_brief'):
			r = str(report['semantic_brief'])
		else:
			status = 'PASS' if report.get('valid') else 'FAIL'
			lines = [f"rules-audit {status}: rules={report['rule_count']} always_on={report['always_on_count']} model_decision={report['model_decision_count']} total_always_on_bytes={report['total_always_on_bytes']} total_always_on_tokens={report['total_always_on_tokens']} issues={report['issue_count']}"]
			for item in report.get('issues') or ():
				lines.append(f"- [{item['code']}] {item['file']}: {item['detail']}")
			r = '\n'.join(lines) + '\n'
		return r
	# @used-by :func:`agent_tools.rules_audit.verify_staged_rules_audit()`
	# @used-by :meth:`Df.Harness.Gate.StagedGates.StagedGates.verify()`
	# @used-by :meth:`test_df_harness_s11_wave2b_tail_cov.DfHarnessS11Wave2bTailCovTests.test_gate_registry_repo_tag_and_rules_auditor()`
	@staticmethod
	def verify_staged(repo_root: Path, staged_paths: list[str], *, use_index: bool=True) -> list[str]:
		r: list[str] = []
		repo = Path(repo_root).resolve()
		if (repo / 'rules').is_dir() and RulesAuditor.__touches_audit_surface(staged_paths):
			overrides = RulesAuditor.__read_staged_overrides(repo, staged_paths, use_index)
			rep = RulesAuditor(repo, workspace=repo, overrides=overrides).audit()
			r = [f"RULES-AUDIT ({item['code']}): {item['file']} — {item['detail']}" for item in rep['issues']]
		return r
	# @used-by :func:`agent_tools.rules_audit.audit_rules()`
	# @used-by :meth:`Df.Harness.Gate.RulesManifest.RulesManifest.__build_doctor_rule_meta()`
	# @used-by :meth:`RulesAuditor.verify_staged()`
	# @used-by :meth:`test_df_harness_s11_wave2b_gate.DfHarnessS11Wave2bGateTests.test_gate_staged_and_repo_checks()`
	# @used-by :meth:`test_df_harness_s11_wave2b_gate_cov.DfHarnessS11Wave2bGateCovTests.test_rules_auditor_subprocess_and_xref_checker()`
	def audit(self) -> dict:
		entries = RulesAuditor.__load_rule_entries(self.__primary, overrides=self.__overrides)
		ws_files = RulesAuditor.__inspect_workspace_auto_files(self.__primary, self.__workspace)
		issues = RulesAuditChecker(entries, ws_files, self.__primary, max_file_bytes=self.__max_file_bytes, max_always_on_bytes=self.__max_always_on_bytes, max_always_on_tokens=self.__max_always_on_tokens).check()
		always = [e for e in entries if 'always_on' == e['trigger']]
		always_bytes = sum((e['bytes'] for e in always))
		always_tokens = sum((e['estimated_tokens'] for e in always))
		ws_bytes = sum((w['bytes'] for w in ws_files))
		ws_tokens = sum((w['estimated_tokens'] for w in ws_files))
		return {'valid': not issues, 'primary': self.__primary.as_posix(), 'workspace': self.__workspace.as_posix() if None is not self.__workspace else None, 'rule_count': len(entries), 'always_on_count': len(always), 'model_decision_count': sum((1 for e in entries if 'model_decision' == e['trigger'])), 'always_on_bytes': always_bytes, 'always_on_estimated_tokens': always_tokens, 'workspace_auto_bytes': ws_bytes, 'total_always_on_bytes': always_bytes + ws_bytes, 'total_always_on_tokens': always_tokens + ws_tokens, 'limits': {'max_file_bytes': self.__max_file_bytes, 'max_always_on_bytes': self.__max_always_on_bytes, 'max_always_on_tokens': self.__max_always_on_tokens}, 'issue_count': len(issues), 'issues': issues}
