# 2026-11-24 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from pathlib import Path
from unittest.mock import patch
import json
import os
import subprocess
import sys
import tempfile
import unittest
WT_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = WT_ROOT / 'scripts'
if str(SCRIPTS) not in sys.path:
	sys.path.insert(0, str(SCRIPTS))
from agent_tools import github_issue, issue_lifecycle
from agent_tools.issues import IssueEvidenceWorkspace
from agent_tools.issues.parity import filter_turn_state_items
CID_A = '11111111-2222-3333-4444-555555555555'
CID_B = 'aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee'
def _init_code_repo(root: Path) -> Path:
	code = root / 'code'
	bare = root / 'remote.git'
	code.mkdir(parents=True)
	subprocess.run(['git', 'init', '--bare', '-b', 'main', str(bare)], check=True, capture_output=True)
	subprocess.run(['git', 'init', '-b', 'main', str(code)], check=True, capture_output=True)
	cfg = code / '.git/config'
	cfg.write_text(cfg.read_text(encoding='utf-8') + f'[user]\n\temail = test@example.com\n\tname = Test\n[remote "origin"]\n\turl = https://github.com/acme/demo.git\n\tpushurl = {bare.as_posix()}\n\tfetch = +refs/heads/*:refs/remotes/origin/*\n', encoding='utf-8')
	(code / 'storage.py').write_text('# https://github.com/acme/demo/issues/174\nVAL = 1\n', encoding='utf-8')
	subprocess.run(['git', '-C', str(code), 'add', 'storage.py'], check=True, capture_output=True)
	subprocess.run(['git', '-C', str(code), 'commit', '-m', 'https://github.com/acme/demo/issues/174'], check=True, capture_output=True)
	subprocess.run(['git', '-C', str(code), 'push', '-u', 'origin', 'main'], check=True, capture_output=True)
	return code
def _write_open_turn(turns_dir: Path, name: str, cid: str, platform: str='antigravity') -> Path:
	tfile = turns_dir / f'{name}.json'
	tfile.write_text(json.dumps({'status': 'open', 'platform': platform, 'conversation_id': cid, 'github_issues': {}}), encoding='utf-8')
	return tfile
# 2026-11-24
# "Isolate per-conversation github_issues recording and turn-state filtering":
# https://github.com/dmitry-ai/harness/issues/195
class IssueConversationIsolationTests(unittest.TestCase):
	def test_analytical_turn_ignores_foreign_and_legacy_broadcast_issues_with_dirty_repo(self) -> None:
		with tempfile.TemporaryDirectory() as tmp:
			proj = Path(tmp).resolve() / 'proj'
			code = _init_code_repo(proj)
			(code / 'storage.py').write_text('# https://github.com/acme/demo/issues/177\n# https://github.com/acme/demo/issues/174\nVAL = 2\n', encoding='utf-8')
			turns_dir = proj / '_/\ua616/data/turns'
			turns_dir.mkdir(parents=True)
			_write_open_turn(turns_dir, 'turn_a', CID_A)
			_write_open_turn(turns_dir, 'turn_b', CID_B)
			url_174 = 'https://github.com/acme/demo/issues/174'
			polluted_state = {'status': 'open', 'platform': 'antigravity', 'conversation_id': CID_B, 'github_issues': {url_174: {'repo': 'acme/demo', 'number': 174, 'url': url_174, 'state': 'closed', 'last_action': 'close', 'actions': ['close'], 'recorded_platform': 'non_codex'}}}
			res = issue_lifecycle.code_and_issue_lifecycle_status(proj, {'touched_files': [], 'issue_actions': []}, turn_state=polluted_state)
			self.assertTrue(res['verified'], res['violations'])
			self.assertEqual({}, res['touched_repos'])
	def test_cli_parser_accepts_optional_conversation_flag(self) -> None:
		parser = github_issue.build_parser()
		parsed_create = parser.parse_args(['create', '--repo', 'acme/demo', '--title', 'T', '--body-file', 'b.md', '--conversation', CID_A])
		parsed_fetch = parser.parse_args(['fetch', '--repo', 'acme/demo', '--issue', '10', '--conversation', CID_B])
		self.assertEqual(CID_A, parsed_create.conversation)
		self.assertEqual(CID_B, parsed_fetch.conversation)
	def test_filter_rejects_legacy_non_codex_broadcast_and_competing_untagged_entries(self) -> None:
		url_foreign = 'https://github.com/acme/demo/issues/174'
		url_own = 'https://github.com/acme/demo/issues/190'
		legacy_broadcast = {'url': url_foreign, 'recorded_platform': 'non_codex', 'last_action': 'close'}
		untagged = {'url': url_foreign, 'last_action': 'close'}
		own_tagged = {'url': url_own, 'recorded_platform': 'antigravity', 'recorded_conversation_id': CID_B, 'last_action': 'create'}
		self.assertEqual([], filter_turn_state_items([legacy_broadcast], CID_B, 'antigravity', set()))
		self.assertEqual([legacy_broadcast], filter_turn_state_items([legacy_broadcast], CID_B, 'antigravity', {url_foreign}))
		self.assertEqual([own_tagged], filter_turn_state_items([legacy_broadcast, untagged, own_tagged], CID_B, 'antigravity', set(), has_competing_open_turns=True))
		self.assertEqual([untagged], filter_turn_state_items([untagged], CID_B, 'antigravity', set(), has_competing_open_turns=False))
	def test_record_issue_isolates_by_antigravity_env_metadata_and_explicit_arg(self) -> None:
		ws = IssueEvidenceWorkspace()
		rec = {'kind': 'issue', 'number': 174, 'state': 'closed', 'html_url': 'https://github.com/acme/demo/issues/174'}
		with tempfile.TemporaryDirectory() as tmp:
			turns_dir = Path(tmp) / 'turns'
			turns_dir.mkdir()
			fa = _write_open_turn(turns_dir, 'turn_a', CID_A)
			fb = _write_open_turn(turns_dir, 'turn_b', CID_B)
			with patch.dict(os.environ, {'ANTIGRAVITY_CONVERSATION_ID': CID_A}, clear=True):
				ws.record_issue_in_open_turns(turns_dir, 'acme/demo', rec, 'close')
			da, db = (json.loads(fa.read_text(encoding='utf-8')), json.loads(fb.read_text(encoding='utf-8')))
			self.assertEqual(CID_A, da['github_issues']['https://github.com/acme/demo/issues/174']['recorded_conversation_id'])
			self.assertEqual('antigravity', da['github_issues']['https://github.com/acme/demo/issues/174']['recorded_platform'])
			self.assertEqual({}, db['github_issues'])
			meta_json = json.dumps({'tool': {'conversationId': CID_B, 'stepIndex': 5}})
			rec2 = {'kind': 'issue', 'number': 190, 'state': 'open', 'html_url': 'https://github.com/acme/demo/issues/190'}
			with patch.dict(os.environ, {'ANTIGRAVITY_SOURCE_METADATA': meta_json}, clear=True):
				ws.record_issue_in_open_turns(turns_dir, 'acme/demo', rec2, 'create')
			da2, db2 = (json.loads(fa.read_text(encoding='utf-8')), json.loads(fb.read_text(encoding='utf-8')))
			self.assertNotIn('https://github.com/acme/demo/issues/190', da2['github_issues'])
			self.assertEqual(CID_B, db2['github_issues']['https://github.com/acme/demo/issues/190']['recorded_conversation_id'])
			rec3 = {'kind': 'issue', 'number': 195, 'state': 'open', 'html_url': 'https://github.com/acme/demo/issues/195'}
			with patch.dict(os.environ, {}, clear=True):
				ws.record_issue_in_open_turns(turns_dir, 'acme/demo', rec3, 'create', conversation_id=CID_A)
			da3, db3 = (json.loads(fa.read_text(encoding='utf-8')), json.loads(fb.read_text(encoding='utf-8')))
			self.assertEqual(CID_A, da3['github_issues']['https://github.com/acme/demo/issues/195']['recorded_conversation_id'])
			self.assertNotIn('https://github.com/acme/demo/issues/195', db3['github_issues'])
	def test_record_issue_skips_broadcast_when_env_unknown_with_multiple_open_turns(self) -> None:
		ws = IssueEvidenceWorkspace()
		rec = {'kind': 'issue', 'number': 199, 'state': 'open', 'html_url': 'https://github.com/acme/demo/issues/199'}
		with tempfile.TemporaryDirectory() as tmp:
			turns_dir = Path(tmp) / 'turns'
			turns_dir.mkdir()
			fa = _write_open_turn(turns_dir, 'turn_a', CID_A)
			fb = _write_open_turn(turns_dir, 'turn_b', CID_B)
			with patch.dict(os.environ, {}, clear=True):
				ws.record_issue_in_open_turns(turns_dir, 'acme/demo', rec, 'create')
			self.assertEqual({}, json.loads(fa.read_text(encoding='utf-8'))['github_issues'])
			self.assertEqual({}, json.loads(fb.read_text(encoding='utf-8'))['github_issues'])
if '__main__' == __name__:
	unittest.main()