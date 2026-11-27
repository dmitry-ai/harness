# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from pathlib import Path
import ast
CHAT_REPLY_CALL_SITES = frozenset({
	('Df/Harness/Workflow/AnswerRecorder.py', 'AnswerRecorder.record'),
	('Df/Harness/Workflow/FinalizeStageRunner.py', 'FinalizeStageRunner.run'),
	('agent_tools/completion.py', '_response_link_issues'),
	('agent_tools/response_grounding.py', 'ResponseEvidenceAuditor.__init__'),
})
CHAT_REPLY_HELPER_SITE = ('agent_tools/links.py', 'chat_reply_link_issues')
KB_DOCUMENT_READABLE_CALL_SITES = frozenset({
	('Df/Harness/Analysis/OwnedPublisher.py', 'OwnedPublisher.__check_links'),
	('Df/Harness/Project/CardSyncer.py', 'CardSyncer.__validate_inputs'),
	('Df/Harness/Project/OnceFileWriter.py', 'OnceFileWriter.write'),
	('Df/Harness/Workflow/HealthAuditor.py', 'HealthAuditor.__check_deliverable_links'),
	('agent_tools/links.py', 'validate_content'),
})
# 2026-11-26 "Move analysis workflow classes into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/380
class LinkAudit:
	# @used-by :func:`agent_tools.contract_invariants.audit_readable_link_call_sites()`
	# @used-by :meth:`test_df_harness_s11_wave2a.DfHarnessS11Wave2aTests.test_drift_red_flags_and_card_sync_classes()`
	def __init__(self, scripts_dir: Path, *, require_expected_chat_sites: bool=True) -> None:
		self.__base = Path(scripts_dir).resolve()
		self.__require_expected = require_expected_chat_sites
	# @used-by :meth:`LinkAudit.__collect()`
	def __call_name(self, call: ast.Call) -> str | None:
		fn = call.func
		if isinstance(fn, ast.Name):
			r: str | None = fn.id
		elif isinstance(fn, ast.Attribute):
			r = fn.attr
		else:
			r = None
		return r
	# @used-by :meth:`LinkAudit.audit()`
	def __collect(self, node: ast.AST, scope: tuple[str, ...], rel: str, out: list[tuple[str, str, str, object, int]]) -> None:
		next_scope = (*scope, node.name) if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)) else scope
		if isinstance(node, ast.Call):
			name = self.__call_name(node)
			if name in ('readable_link_issues', 'chat_reply_link_issues'):
				out.append((rel, '.'.join(next_scope), name, self.__kw_value(node), int(getattr(node, 'lineno', 0))))
		for child in ast.iter_child_nodes(node):
			self.__collect(child, next_scope, rel, out)
	# @used-by :meth:`LinkAudit.audit()`
	def __evaluate(self, rel: str, qual: str, name: str, kw_val: object, lineno: int) -> str | None:
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
	# @used-by :meth:`LinkAudit.__collect()`
	def __kw_value(self, call: ast.Call) -> object:
		r: object = None
		for kw in call.keywords:
			if 'allow_unencoded_file_uri' == kw.arg:
				r = kw.value.value if isinstance(kw.value, ast.Constant) else 'dynamic'
				break
		return r
	# @used-by :func:`agent_tools.contract_invariants.audit_readable_link_call_sites()`
	# @used-by :meth:`test_df_harness_s11_wave2a.DfHarnessS11Wave2aTests.test_drift_red_flags_and_card_sync_classes()`
	def audit(self) -> list[str]:
		hits: list[tuple[str, str, str, object, int]] = []
		for py_file in sorted(self.__base.rglob('*.py')):
			rel = py_file.relative_to(self.__base).as_posix()
			self.__collect(ast.parse(py_file.read_text(encoding='utf-8'), filename=rel), (), rel, hits)
		errs: list[str] = []
		seen_chat: set[tuple[str, str]] = set()
		for rel, qual, name, kw_val, lineno in hits:
			if 'chat_reply_link_issues' == name:
				seen_chat.add((rel, qual))
			err = self.__evaluate(rel, qual, name, kw_val, lineno)
			if None is not err:
				errs.append(err)
		if self.__require_expected:
			errs.extend((f'Expected chat_reply_link_issues call site missing: {m[0]} ({m[1]})' for m in sorted(CHAT_REPLY_CALL_SITES - seen_chat)))
		return errs