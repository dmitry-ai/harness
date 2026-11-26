# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Verify explicit user stop consent in clarifications during answer checks":
# https://github.com/dmitry-ai/harness/issues/375
from __future__ import annotations
from pathlib import Path
import json
import subprocess
import sys
import tempfile
import types
import unittest
WT_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = WT_ROOT / 'scripts'
if str(SCRIPTS) not in sys.path:
	sys.path.insert(0, str(SCRIPTS))
from agent_tools import issue_lifecycle, repo_tags, scope_deferral
from agent_tools.gates import run_answer_gates
SLUG = 'dmitry-ai/antigravity-addons'
STEP_100_102_CLARIFICATIONS = [{
	'ask_step': 100,
	'answer_step': 102,
	'asked_at': '2026-11-26T12:42:49Z',
	'answered_at': '2026-11-26T16:23:39+03:00',
	'questions': ['\u041a\u0430\u043a\u043e\u0439 \u043f\u043e\u0440\u044f\u0434\u043e\u043a \u0432\u044b\u043f\u043e\u043b\u043d\u0435\u043d\u0438\u044f \u043f\u0440\u0435\u0434\u043f\u043e\u0447\u0442\u0438\u0442\u0435\u043b\u0435\u043d?'],
	'answers': [{
		'id': 'A4',
		'text': '(Recommended) \u0412\u044b\u043f\u043e\u043b\u043d\u044f\u0442\u044c \u043f\u043e\u044d\u0442\u0430\u043f\u043d\u043e \u0447\u0435\u0440\u0435\u0437 parent + child issues \u0432 \u0438\u0437\u043e\u043b\u0438\u0440\u043e\u0432\u0430\u043d\u043d\u043e\u043c worktree: \u043d\u0430\u0447\u0430\u0442\u044c \u0441\u0440\u0430\u0437\u0443 \u0441 \u043f\u043e\u043b\u043d\u043e\u0433\u043e \u043f\u043e\u0440\u0442\u0430 \u00a7\u00a72\u20137 (+ \u00a79 \u043f\u0440\u0438 \u043d\u0430\u0445\u043e\u0434\u043a\u0430\u0445), \u0444\u0438\u043a\u0441\u0438\u0440\u0443\u044f \u043f\u0440\u043e\u0433\u0440\u0435\u0441\u0441 \u0432 continuation.md \u0434\u043b\u044f \u043f\u0435\u0440\u0435\u0445\u043e\u0434\u0430 \u043a \u00a7\u00a78\u201311 \u0431\u0435\u0437 \u043f\u043e\u0442\u0435\u0440\u0438 \u043a\u043e\u043d\u0442\u0435\u043a\u0441\u0442\u0430',
	}],
}]
# @used-by :meth:`ClarificationStopConsentTests.test_explicit_user_stop_consent_in_clarifications_unblocks_deferral()`
# @used-by :meth:`ClarificationStopConsentTests.test_step_100_102_real_clarifications_rejected_with_open_deferred_children()`
def _build_fixture(base: Path) -> tuple[Path, dict]:
	bare = base / 'remote.git'
	subprocess.run(['git', 'init', '--bare', str(bare)], check=True, capture_output=True, stdin=subprocess.DEVNULL, timeout=30)
	project = base / 'proj'
	(project / '_/\ua616').mkdir(parents=True)
	code_repo = project / 'code'
	code_repo.mkdir()
	for cmd in (['init'],):
		subprocess.run(['git', *cmd], cwd=code_repo, check=True, capture_output=True, stdin=subprocess.DEVNULL, timeout=30)
	cfg = code_repo / '.git/config'
	cfg.write_text(cfg.read_text(encoding='utf-8') + f'[user]\n\temail = test@example.com\n\tname = Test\n[remote "origin"]\n\turl = https://github.com/{SLUG}.git\n\tpushurl = {bare.as_posix()}\n\tfetch = +refs/heads/*:refs/remotes/origin/*\n[url "{bare.as_posix()}"]\n\tinsteadOf = https://github.com/{SLUG}.git\n', encoding='utf-8')
	url_p, url_c1, url_c2 = (f'https://github.com/{SLUG}/issues/319', f'https://github.com/{SLUG}/issues/321', f'https://github.com/{SLUG}/issues/337')
	f_c1 = code_repo / 'p1.py'
	f_c1.write_text(f'# {url_c1}\nx = 1\n', encoding='utf-8')
	for args in (['add', 'p1.py'], ['commit', '-m', url_c1]):
		subprocess.run(['git', *args], cwd=code_repo, check=True, capture_output=True, stdin=subprocess.DEVNULL, timeout=30)
	repo_tags.ensure_commit_tag(code_repo, push=False)
	for args in (['branch', '-M', 'main'], ['push', '-u', 'origin', 'main', '--tags']):
		subprocess.run(['git', *args], cwd=code_repo, check=True, capture_output=True, stdin=subprocess.DEVNULL, timeout=30)
	safe_slug = SLUG.replace('/', '__')
	ev_dir = project / f'_/\ua616/KB/Evidence/GitHub/{safe_slug}'
	ev_dir.mkdir(parents=True)
	(ev_dir / 'issue-319.json').write_text(json.dumps({'url': url_p, 'number': 319, 'state': 'open', 'title': 'Parent', 'body': '# Scope\nDetails.\n'}), encoding='utf-8')
	(ev_dir / 'issue-321.json').write_text(json.dumps({'url': url_c1, 'number': 321, 'parent_number': 319, 'state': 'closed', 'title': 'Phase 1', 'body': 'Parent: #319\n'}), encoding='utf-8')
	(ev_dir / 'issue-337.json').write_text(json.dumps({'url': url_c2, 'number': 337, 'parent_number': 319, 'state': 'open', 'title': 'Phase 2', 'body': 'Parent: #319\n'}), encoding='utf-8')
	turn = {
		'touched_files': [str(f_c1)],
		'issue_actions': [
			{'action': 'create', 'repo': SLUG, 'number': 319, 'url': url_p, 'state': 'open'},
			{'action': 'create', 'repo': SLUG, 'number': 321, 'url': url_c1, 'state': 'open', 'parent_number': 319},
			{'action': 'close', 'repo': SLUG, 'number': 321, 'url': url_c1, 'state': 'closed', 'parent_number': 319},
			{'action': 'create', 'repo': SLUG, 'number': 337, 'url': url_c2, 'state': 'open', 'parent_number': 319},
		],
	}
	return (project, turn)
# @used-by :meth:`ClarificationStopConsentTests.test_explicit_user_stop_consent_in_clarifications_unblocks_deferral()`
# @used-by :meth:`ClarificationStopConsentTests.test_step_100_102_real_clarifications_rejected_with_open_deferred_children()`
def _gate_ctx(turn: dict, value: dict, lifecycle_chk: dict, response: str) -> dict:
	return {'role': 'primary', 'blocked_report': False, 'turn': turn, 'value': value, 'response': response, 'doc4_errs': [], 'link_errs': [], 'prob_errs': [], 'source_errs': [], 'lang_errs': [], 'exec5_chk': {'verified': True, 'violations': []}, 'http_chk': {'verified': True, 'violations': []}, 'comp_chk': {'verified': True}, 'evicted_cited': [], 'del_chk': {'verified': True}, 'issue_first_chk': {'verified': True, 'violations': []}, 'lifecycle_chk': lifecycle_chk, 'tdd_chk': {'verified': True, 'violations': []}, 'wf_errs': []}
# 2026-11-26
# "Verify explicit user stop consent in clarifications during answer checks":
# https://github.com/dmitry-ai/harness/issues/375
class ClarificationStopConsentTests(unittest.TestCase):
	# @used-by :mod:`unittest`
	def test_explicit_user_stop_consent_in_clarifications_unblocks_deferral(self) -> None:
		with tempfile.TemporaryDirectory() as tmp:
			project, base_turn = _build_fixture(Path(tmp))
			ru_clar = [{'ask_step': 10, 'answer_step': 12, 'questions': ['Stop after Phase 1?'], 'answers': [{'id': 'A1', 'text': '\u041e\u0441\u0442\u0430\u043d\u043e\u0432\u0438 \u0445\u043e\u0434 \u043f\u043e\u0441\u043b\u0435 \u0424\u0430\u0437\u044b 1 \u0438 \u0432\u0435\u0440\u043d\u0438 \u0443\u043f\u0440\u0430\u0432\u043b\u0435\u043d\u0438\u0435 \u0434\u043e \u00a7\u00a78, 10, 11.'}]}]
			turn_ru = {**base_turn, 'clarifications': ru_clar}
			lc_ru = issue_lifecycle.code_and_issue_lifecycle_status(project, turn_ru, turn_state={})
			self.assertTrue(lc_ru['verified'], lc_ru['violations'])
			self.assertTrue(lc_ru.get('deferred_children'), lc_ru)
			issues_ru, checks_ru = run_answer_gates(_gate_ctx(turn_ru, {'clarifications': ru_clar}, lc_ru, 'Phase 2 deferred per user confirmation A1.'))
			self.assertTrue(checks_ru['scope_deferral'], issues_ru)
			self.assertEqual([], issues_ru)
			en_clar = [{'ask_step': 10, 'answer_step': 12, 'questions': ['Stop now?'], 'answers': [{'id': 'A1', 'text': 'Stop the turn after Phase 1 and return control before Phase 2.'}]}]
			turn_en = {**base_turn, 'clarifications': en_clar}
			lc_en = issue_lifecycle.code_and_issue_lifecycle_status(project, turn_en, turn_state={})
			self.assertTrue(lc_en['verified'], lc_en['violations'])
	# @used-by :mod:`unittest`
	def test_runner_scope_deferral_and_raw_output_fallback(self) -> None:
		deferred_lc = {'deferred_children': [{'parent': f'https://github.com/{SLUG}/issues/319', 'children': [f'https://github.com/{SLUG}/issues/337']}]}
		fails: list[tuple[str, str]] = []
		runner_fail = types.SimpleNamespace(turn={}, value={}, response='Phase 1 done.', blocked_report=False, _fail_gate=lambda g, m: fails.append((g, m)))
		scope_deferral.check_runner_scope_deferral(runner_fail, deferred_lc)
		self.assertFalse(runner_fail.value['scope_deferral_check']['verified'])
		self.assertEqual('scope_deferral', fails[0][0])
		raw_clar = [{'ask_step': 5, 'answer_step': 6, 'raw_output': 'A1: Stop this turn after Phase 1.'}]
		fails_ok: list[tuple[str, str]] = []
		runner_ok = types.SimpleNamespace(turn={'clarifications': raw_clar}, value={}, response='Phase 2 deferred per user confirmation A1.', blocked_report=False, _fail_gate=lambda g, m: fails_ok.append((g, m)))
		scope_deferral.check_runner_scope_deferral(runner_ok, deferred_lc)
		self.assertTrue(runner_ok.value['scope_deferral_check']['verified'])
		self.assertEqual([], fails_ok)
	# @used-by :mod:`unittest`
	def test_step_100_102_real_clarifications_rejected_with_open_deferred_children(self) -> None:
		with tempfile.TemporaryDirectory() as tmp:
			project, base_turn = _build_fixture(Path(tmp))
			turn = {**base_turn, 'clarifications': STEP_100_102_CLARIFICATIONS}
			lc = issue_lifecycle.code_and_issue_lifecycle_status(project, turn, turn_state={'clarifications': STEP_100_102_CLARIFICATIONS})
			self.assertFalse(lc['verified'], lc)
			self.assertTrue(lc.get('deferred_children'), lc)
			issues, checks = run_answer_gates(_gate_ctx(turn, {'clarifications': STEP_100_102_CLARIFICATIONS}, lc, 'Phase 1 completed; #337 left open.'))
			self.assertFalse(checks['scope_deferral'])
			sd_msgs = [it['message'] for it in issues if 'scope_deferral' == it['gate_id']]
			self.assertTrue(sd_msgs, issues)
			self.assertTrue(any(('A4' in m and 'issues/337' in m for m in sd_msgs)), sd_msgs)
if '__main__' == __name__:
	unittest.main()
