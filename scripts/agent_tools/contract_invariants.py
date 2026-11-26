# 2026-11-25 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from pathlib import Path
import ast
# 2026-11-25
# "Enforce call-site policy registry and hook parity contract invariants":
# https://github.com/dmitry-ai/harness/issues/236
CHAT_REPLY_CALL_SITES = frozenset({
	('agent_tools/completion.py', '_response_link_issues'),
	('agent_tools/response_grounding.py', 'ResponseEvidenceAuditor.__init__'),
	('agent_tools/workflow.py', 'WorkflowStateEngine._finalize_stage'),
	('agent_tools/workflow.py', 'WorkflowStateEngine.record_current_answer'),
})
CHAT_REPLY_HELPER_SITE = ('agent_tools/links.py', 'chat_reply_link_issues')
KB_DOCUMENT_READABLE_CALL_SITES = frozenset({
	('agent_tools/analysis.py', 'publish_owned'),
	('agent_tools/knowledge.py', 'create_once'),
	('agent_tools/links.py', 'validate_content'),
	('agent_tools/project_card.py', 'sync_block'),
	('agent_tools/workflow.py', 'ProjectHealthAuditor.check_project'),
})
def _allow_unencoded_kw_value(call: ast.Call) -> object:
	r: object = None
	for kw in call.keywords:
		if 'allow_unencoded_file_uri' == kw.arg:
			r = kw.value.value if isinstance(kw.value, ast.Constant) else 'dynamic'
			break
	return r
def _call_name(call: ast.Call) -> str | None:
	fn = call.func
	if isinstance(fn, ast.Name):
		r: str | None = fn.id
	elif isinstance(fn, ast.Attribute):
		r = fn.attr
	else:
		r = None
	return r
def _collect_link_calls(node: ast.AST, scope: tuple[str, ...], rel: str, out: list[tuple[str, str, str, object, int]]) -> None:
	next_scope = (*scope, node.name) if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)) else scope
	if isinstance(node, ast.Call):
		name = _call_name(node)
		if name in ('readable_link_issues', 'chat_reply_link_issues'):
			out.append((rel, '.'.join(next_scope), name, _allow_unencoded_kw_value(node), int(getattr(node, 'lineno', 0))))
	for child in ast.iter_child_nodes(node):
		_collect_link_calls(child, next_scope, rel, out)
def _evaluate_call_site(rel: str, qual: str, name: str, kw_val: object, lineno: int) -> str | None:
	site = (rel, qual)
	if 'chat_reply_link_issues' == name:
		r = None if site in CHAT_REPLY_CALL_SITES else f'Unregistered chat_reply_link_issues call site at {rel}:{lineno} ({qual})'
	elif CHAT_REPLY_HELPER_SITE == site:
		r = None if True is kw_val else f'{rel}:{lineno} ({qual}) must pass allow_unencoded_file_uri=True'
	elif site in KB_DOCUMENT_READABLE_CALL_SITES:
		r = None if kw_val in (None, False) else f'KB document site {rel}:{lineno} ({qual}) must not set allow_unencoded_file_uri={kw_val!r}'
	else:
		r = f'Unregistered readable_link_issues call site at {rel}:{lineno} ({qual}); use chat_reply_link_issues for chat replies or register KB site'
	return r
def audit_readable_link_call_sites(scripts_dir: Path, *, require_expected_chat_sites: bool=True) -> list[str]:
	base = Path(scripts_dir).resolve()
	hits: list[tuple[str, str, str, object, int]] = []
	for py_file in sorted(base.rglob('*.py')):
		rel = py_file.relative_to(base).as_posix()
		tree = ast.parse(py_file.read_text(encoding='utf-8'), filename=rel)
		_collect_link_calls(tree, (), rel, hits)
	errs: list[str] = []
	seen_chat: set[tuple[str, str]] = set()
	for rel, qual, name, kw_val, lineno in hits:
		if 'chat_reply_link_issues' == name:
			seen_chat.add((rel, qual))
		err = _evaluate_call_site(rel, qual, name, kw_val, lineno)
		if None is not err:
			errs.append(err)
	if require_expected_chat_sites:
		for missing in sorted(CHAT_REPLY_CALL_SITES - seen_chat):
			errs.append(f'Expected chat_reply_link_issues call site missing: {missing[0]} ({missing[1]})')
	return errs
