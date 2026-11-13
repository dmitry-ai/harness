# 2026-11-14 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Unify declarative CLI routers, scratch-verified --consume-input/stdin loading, and read-back mutations in cli_common.py":
# https://github.com/dmitry-ai/harness/issues/69
import argparse
import hashlib
import io
import json
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch
SCRIPT_DIR = Path(__file__).resolve().parents[1] / 'scripts'
if str(SCRIPT_DIR) not in sys.path:
	sys.path.insert(0, str(SCRIPT_DIR))
from agent_tools import cli, cli_common, github_issue, text_cli, upwork_project
class CliCommonTests(unittest.TestCase):
	def test_declarative_arg_specs_and_routers_parse_expected_flags(self):
		parser = argparse.ArgumentParser(prog='demo')
		cli_common.add_arg_specs(parser, (('target', {'type': Path}), (('--output', '-o'), {'type': Path}), ('--check', {'action': 'store_true'})))
		parsed = parser.parse_args(['in.md', '-o', 'out.md', '--check'])
		self.assertEqual(Path('in.md'), parsed.target)
		self.assertEqual(Path('out.md'), parsed.output)
		self.assertTrue(parsed.check)
		gh_parser = github_issue.build_parser()
		gh_args = gh_parser.parse_args(['create', '-R', 'owner/repo', '-t', 'Title', '-F', 'body.md', '--consume-input'])
		self.assertEqual('owner/repo', gh_args.repo)
		self.assertTrue(gh_args.consume_input)
		self.assertEqual(0, cli_common.result_exit_code({'valid': True, 'complete': True}))
		self.assertEqual(2, cli_common.result_exit_code({'status': 'conflict'}))
		for fn, argv in ((upwork_project.main, ['--help']), (text_cli.main, ['--help']), (cli.main, ['validate_links', '--help'])):
			with patch('sys.stdout', new_callable=io.StringIO), self.assertRaises(SystemExit) as ctx:
				if fn is cli.main:
					fn(argv[0], argv[1:])
				else:
					fn(argv)
			self.assertEqual(0, ctx.exception.code)
	def test_scratch_consumption_sha256_and_parallel_answer_guard(self):
		with tempfile.TemporaryDirectory() as tmp:
			proj = Path(tmp) / 'proj'
			scratch = proj / '\ua616/data/scratch'
			turns = proj / '\ua616/data/turns'
			scratch.mkdir(parents=True)
			turns.mkdir(parents=True)
			f = scratch / 'item.json'
			raw = b'{"ok": true}'
			f.write_bytes(raw)
			sha = hashlib.sha256(raw).hexdigest()
			args = SimpleNamespace(command='record-answer', project=proj, consume_input=True, expected_sha256=sha)
			self.assertEqual(raw, cli_common.load_operation_input(args, f))
			with self.assertRaisesRegex(ValueError, 'SHA-256 mismatch'):
				cli_common.load_operation_input(SimpleNamespace(command='record-answer', project=proj, consume_input=False, expected_sha256='0' * 64), f)
			res = cli_common.consume_scratch_input(args, f, raw, {'valid': True})
			self.assertFalse(f.exists())
			self.assertIn('consumed_input', res)
			(turns / 'otherturn.json').write_text(json.dumps({'status': 'open', 'conversation_id': 'conv-other'}), encoding='utf-8')
			shared_ans = scratch / 'answer.md'
			shared_ans.write_text('body', encoding='utf-8')
			ans_args = SimpleNamespace(command='answer-prepare', project=proj, conversation='conv-me', consume_input=True, expected_sha256=None)
			with self.assertRaisesRegex(ValueError, 'answer-<turn_key>\\.md'):
				cli_common.load_operation_input(ans_args, shared_ans)
if '__main__' == __name__:
	unittest.main()
