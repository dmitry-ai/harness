# 2026-11-24 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from collections import Counter
from pathlib import Path
from ..shell_audit import parse_issue_url
from .classifier import _norm_posix
from .substantive import _ASSERTION_LINE_RE
import difflib
import json
import re
_RATCHET_OK_LINE_RE = re.compile(r'(?im)^\s*(?:[-*+]\s+)?(?:`|\*\*|__)?RATCHET-OK(?:\*\*|__|`)?\s*:\s*(.+?)\s*$')
_RATCHET_SLOP_RE = re.compile(
	r'(?i)^(?:updat(?:e|ed|ing)|fix(?:ed|ing)?|adjust(?:ed|ing)?|chang(?:e|ed|ing)|adapt(?:ed|ing)?|relax(?:ed|ing)?|align(?:ed|ing)?)'
	r'\s+(?:the\s+|failing\s+|broken\s+|existing\s+)?tests?(?:\s+expectations?)?'
	r'\s+(?:to\s+(?:pass|match|fit|align|reflect)|so\s+(?:it|ci|tests?)\s+(?:pass|turn)|for\s+(?:new|current)\s+(?:code|output|implementation))'
)
_SKIP_MARKER_RE = re.compile(
	r'(?:@unittest\.skip\w*\b'
	r'|@pytest\.mark\.skip\w*\b'
	r'|\bself\.skipTest\s*\('
	r'|\b(?:it|test|describe)\.skip\s*\('
	r'|\b(?:xit|xtest|xdescribe)\s*\('
	r'|\[(?:Ignore|Skip)\b'
	r'|\[(?:Fact|Theory)\s*\([^\)]*\bSkip\s*='
	r'|\bt\.Skip(?:f|Now)?\s*\('
	r'|#\[ignore\]'
	r'|\$this->markTestSkipped\s*\()'
)
_TEST_DEF_RE = re.compile(
	r'^\s*(?:(?:async\s+)?def\s+test_\w+\s*\('
	r'|(?:public|private|protected)?\s*(?:static\s+)?function\s+test\w*\s*\('
	r'|(?:it|test|describe)\s*\('
	r'|\[(?:Fact|Theory|Test|TestMethod)\b'
	r'|@Test\b'
	r'|func\s+Test\w*\s*\('
	r'|#\[test\]'
	r'|(?:Describe|Context|It)\s+[\'"]'
	r'|@test\s+[\'"])'
)
# @used-by :func:`ratchet_diff_violations()`
def _diff_added_removed(old_lines: list[str], new_lines: list[str]) -> tuple[list[str], Counter]:
	removed: list[str] = []
	added: list[str] = []
	for line in difflib.unified_diff(old_lines, new_lines, lineterm='', n=0):
		if line.startswith(('---', '+++', '@@')):
			continue
		if line.startswith('-'):
			removed.append(line[1:])
		elif line.startswith('+'):
			added.append(line[1:])
	return (removed, Counter(ln.strip() for ln in added if ln.strip()))
# @used-by :func:`find_ratchet_approval()`
def _find_issue_ratchet_approval(file_path: str | Path, roots: list[Path], issue_urls: list[str] | tuple[str, ...]) -> dict | None:
	from ..issue_lifecycle import evidence_issue_files
	r = None
	base_root = roots[0]
	for raw_url in issue_urls or ():
		parsed = parse_issue_url(str(raw_url).strip())
		if None is not parsed:
			slug, num = parsed
			for ev_path in evidence_issue_files(base_root, slug, f'issue-{num}.json', candidate_repos=roots):
				hit = _match_issue_evidence_file(ev_path, raw_url, file_path)
				if None is not hit:
					r = hit
					break
		if None is not r:
			break
	return r
# @used-by :func:`find_ratchet_approval()`
def _find_receipt_ratchet_approval(file_path: str | Path, receipts: list[dict]) -> dict | None:
	r = None
	for item in receipts:
		reason = str(item.get('reason') or '').strip()
		target = str(item.get('file') or item.get('target') or '').strip()
		ok, _ = validate_ratchet_reason(reason)
		if ok and _match_ratchet_target(target, file_path):
			r = {'file': target, 'reason': reason, 'source': 'turn_receipt'}
			break
	return r
# @used-by :func:`_load_turn_ratchet_receipts()`
def _load_receipt_file(rf: Path) -> list[dict]:
	r: list[dict] = []
	try:
		data = json.loads(rf.read_text(encoding='utf-8'))
	except (OSError, ValueError):
		data = None
	raw_list = data.get('approvals') if isinstance(data, dict) else data
	if isinstance(raw_list, list):
		r = [entry for entry in raw_list if isinstance(entry, dict)]
	return r
# @used-by :func:`find_ratchet_approval()`
def _load_turn_ratchet_receipts(project_root: Path | None) -> list[dict]:
	r: list[dict] = []
	if None is not project_root:
		for td in _turn_receipt_dirs(project_root):
			if td.is_dir():
				for rf in td.glob('*-ratchet-ok.json'):
					r.extend(_load_receipt_file(rf))
	return r
# @used-by :func:`_find_issue_ratchet_approval()`
def _match_issue_evidence_file(ev_path: Path, raw_url: str, file_path: str | Path) -> dict | None:
	r = None
	try:
		data = json.loads(ev_path.read_text(encoding='utf-8'))
		iss = data.get('issue') if isinstance(data, dict) and isinstance(data.get('issue'), dict) else data
		body = str((iss or {}).get('body') or '')
	except (OSError, ValueError):
		body = ''
	for target_spec, reason in _parse_ratchet_ok_lines(body):
		ok, _ = validate_ratchet_reason(reason)
		if ok and _match_ratchet_target(target_spec, file_path):
			r = {'file': target_spec, 'issue_url': raw_url, 'reason': reason, 'source': str(ev_path)}
			break
	return r
# @used-by :func:`_find_receipt_ratchet_approval()`
# @used-by :func:`_match_issue_evidence_file()`
def _match_ratchet_target(target_spec: str, file_path: str | Path) -> bool:
	spec = _norm_posix((target_spec or '').strip().strip('`"\'')).lstrip('./').lower()
	if not spec:
		r = False
	elif '*' == spec or 'all' == spec:
		r = True
	else:
		fp = _norm_posix(file_path).lstrip('./').lower()
		r = fp == spec or fp.endswith('/' + spec) or Path(fp).name.lower() == spec
	return r
# @used-by :func:`_match_issue_evidence_file()`
def _parse_ratchet_ok_lines(body: str) -> list[tuple[str, str]]:
	r: list[tuple[str, str]] = []
	for m in _RATCHET_OK_LINE_RE.finditer(body or ''):
		rest = m.group(1).strip()
		m_split = re.match(r'^([^\s—–:-]+(?:/[^\s—–:-]+)*)\s*(?:—|–|--|:|-)\s*(.+)$', rest)
		if m_split and ('.' in m_split.group(1) or '/' in m_split.group(1) or '*' == m_split.group(1)):
			r.append((m_split.group(1).strip(), m_split.group(2).strip()))
		else:
			r.append(('*', rest))
	return r
# @used-by :func:`find_ratchet_approval()`
def _ratchet_approval_roots(project_root: Path | None, repo_root: Path | None) -> list[Path]:
	r: list[Path] = []
	for cand in (project_root, repo_root):
		if None is not cand:
			rc = Path(cand).resolve()
			if rc not in r:
				r.append(rc)
	if not r:
		r.append(Path.cwd().resolve())
	return r
# @used-by :func:`ratchet_diff_violations()`
def _removed_line_violations(rel_path: str, removed: list[str], added_counts: Counter) -> list[str]:
	r: list[str] = []
	for rem in removed:
		stripped = rem.strip()
		if not stripped or stripped.startswith(('#', '//', '/*', '*')):
			continue
		if 0 < added_counts[stripped]:
			added_counts[stripped] -= 1
		elif _TEST_DEF_RE.match(rem):
			r.append(f'TDD-RATCHET: Existing test definition deleted or modified in {rel_path} ("{stripped[:100]}") without audited RATCHET-OK approval.')
		elif _ASSERTION_LINE_RE.search(rem):
			r.append(f'TDD-RATCHET: Existing assertion deleted or altered in {rel_path} ("{stripped[:100]}") without audited RATCHET-OK approval.')
	return r
# @used-by :func:`_load_turn_ratchet_receipts()`
# @used-by :func:`agent_tools.tdd.mechanical._candidate_recipe_dirs()`
def _turn_receipt_dirs(project_root: Path) -> list[Path]:
	from ..path_registry import project_paths
	r = [Path(project_root) / '\ua616/data/turns', Path(project_root) / '_/\ua616/data/turns']
	try:
		td = project_paths(project_root).turns_dir
		if td not in r:
			r.insert(0, td)
	except (OSError, ValueError):
		pass
	return r
# @used-by :func:`agent_tools.tdd.enforcement._eval_shell_test_deletes()`
# @used-by :func:`agent_tools.tdd.enforcement._eval_test_ratchet_and_fitting()`
# @used-by :func:`agent_tools.tdd.enforcement._verify_staged_test_file()`
# @used-by :meth:`test_tdd_completion.TddTurnCompletionAndCliTests.test_cli_ratchet_ok_and_tdd_check_commands()`
# @used-by :meth:`test_tdd_decomposition.TddDecompositionTests.test_ratchet_module_behavior_and_parity()`
# @used-by :meth:`test_tdd_gate.TddGateCoreTests.test_shell_code_write_targets_and_ratchet_issue_evidence()`
# @used-by :mod:`agent_tools.tdd_gate`
# @used-by :mod:`agent_tools.tdd`
def find_ratchet_approval(file_path: str | Path, *, repo_root: Path | None=None, project_root: Path | None=None, turn_receipts: list[dict] | None=None, issue_urls: list[str] | tuple[str, ...]=()) -> dict | None:
	receipts = list(turn_receipts or ())
	if None is not project_root:
		receipts.extend(_load_turn_ratchet_receipts(project_root))
	elif None is not repo_root:
		receipts.extend(_load_turn_ratchet_receipts(repo_root))
	r = _find_receipt_ratchet_approval(file_path, receipts)
	if None is r:
		r = _find_issue_ratchet_approval(file_path, _ratchet_approval_roots(project_root, repo_root), issue_urls)
	return r
# 2026-11-24
# "Decompose tdd_gate.py into modular TDD verification package":
# https://github.com/dmitry-ai/harness/issues/169
# @used-by :func:`agent_tools.tdd.enforcement._eval_test_ratchet_and_fitting()`
# @used-by :func:`agent_tools.tdd.enforcement._verify_staged_test_file()`
# @used-by :meth:`test_tdd_decomposition.TddDecompositionTests.test_ratchet_module_behavior_and_parity()`
# @used-by :meth:`test_tdd_gate.TddGateCoreTests.test_ratchet_diff_guard_and_ratchet_ok_validation()`
# @used-by :mod:`agent_tools.tdd_gate`
# @used-by :mod:`agent_tools.tdd`
def ratchet_diff_violations(rel_path: str, old_text: str, new_text: str | None, *, approval: dict | None=None) -> list[str]:
	approved = None is not approval and validate_ratchet_reason(str(approval.get('reason') or ''))[0]
	if approved:
		r: list[str] = []
	elif None is new_text:
		r = [f'TDD-RATCHET: Deleting existing test file {rel_path} is prohibited without audited RATCHET-OK approval.']
	else:
		old_lines = old_text.splitlines()
		new_lines = new_text.splitlines()
		removed, added_counts = _diff_added_removed(old_lines, new_lines)
		r = _removed_line_violations(rel_path, removed, added_counts)
		old_skip = sum(1 for ln in old_lines if _SKIP_MARKER_RE.search(ln))
		new_skip = sum(1 for ln in new_lines if _SKIP_MARKER_RE.search(ln))
		if new_skip > old_skip:
			r.append(f'TDD-RATCHET: Existing test file {rel_path} adds skip/ignore marker(s) ({old_skip} -> {new_skip}) without audited RATCHET-OK approval.')
	return r
# @used-by :func:`_find_receipt_ratchet_approval()`
# @used-by :func:`_match_issue_evidence_file()`
# @used-by :func:`agent_tools.completion.ratchet_ok()`
# @used-by :func:`ratchet_diff_violations()`
# @used-by :meth:`test_tdd_decomposition.TddDecompositionTests.test_ratchet_module_behavior_and_parity()`
# @used-by :meth:`test_tdd_gate.TddGateCoreTests.test_ratchet_diff_guard_and_ratchet_ok_validation()`
# @used-by :mod:`agent_tools.tdd_gate`
# @used-by :mod:`agent_tools.tdd`
def validate_ratchet_reason(reason: str) -> tuple[bool, str | None]:
	cleaned = ' '.join((reason or '').strip().split())
	if 30 > len(cleaned):
		r = (False, 'RATCHET-OK reason must be at least 30 characters explaining why the old expectation changed and by whose decision.')
	elif _RATCHET_SLOP_RE.search(cleaned):
		r = (False, 'RATCHET-OK reason cannot be a test-fitting excuse ("updating test to pass/match implementation"); cite the requirement/user decision or physical contract change.')
	else:
		r = (True, None)
	return r
