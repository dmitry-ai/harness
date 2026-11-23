# 2026-11-24 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Deduplicate historical admission fixtures and guard optional temp fsync":
# https://github.com/dmitry-ai/harness/issues/177
from __future__ import annotations
from pathlib import Path
from unittest.mock import patch
import os
import sys
import tempfile
import unittest
SCRIPTS = Path(__file__).resolve().parents[1] / 'scripts'
if str(SCRIPTS) not in sys.path:
	sys.path.insert(0, str(SCRIPTS))
from agent_tools import storage
class StorageFsyncGuardTests(unittest.TestCase):
	def test_fsync_runs_by_default_and_when_env_is_zero(self) -> None:
		with tempfile.TemporaryDirectory() as tmp:
			base = Path(tmp).resolve()
			with patch.dict(os.environ, {}, clear=False):
				os.environ.pop('HARNESS_TEST_NO_FSYNC', None)
				with patch.object(storage.os, 'fsync', wraps=os.fsync) as spy_def:
					storage.replace_bytes(base / 'a.bin', b'alpha')
					self.assertEqual(1, spy_def.call_count)
					self.assertEqual(b'alpha', (base / 'a.bin').read_bytes())
			with patch.dict(os.environ, {'HARNESS_TEST_NO_FSYNC': '0'}, clear=False):
				with patch.object(storage.os, 'fsync', wraps=os.fsync) as spy_zero:
					storage.replace_bytes(base / 'b.bin', b'beta')
					self.assertEqual(1, spy_zero.call_count)
					self.assertEqual(b'beta', (base / 'b.bin').read_bytes())
	def test_fsync_skipped_inside_tempdir_when_env_is_one(self) -> None:
		with tempfile.TemporaryDirectory() as tmp:
			target = Path(tmp).resolve() / 'fast.bin'
			with patch.dict(os.environ, {'HARNESS_TEST_NO_FSYNC': '1'}, clear=False):
				with patch.object(storage.os, 'fsync', wraps=os.fsync) as spy:
					storage.replace_bytes(target, b'fast-payload')
					self.assertEqual(0, spy.call_count)
					self.assertEqual(b'fast-payload', target.read_bytes())
	def test_fsync_still_runs_outside_tempdir_even_when_env_is_one(self) -> None:
		with tempfile.TemporaryDirectory() as tmp:
			base = Path(tmp).resolve()
			outside_dir = base / 'prod_like'
			fake_tmp = base / 'other_tmp'
			outside_dir.mkdir()
			fake_tmp.mkdir()
			target = outside_dir / 'critical.bin'
			with patch.dict(os.environ, {'HARNESS_TEST_NO_FSYNC': '1'}, clear=False), patch.object(storage.tempfile, 'gettempdir', return_value=str(fake_tmp)):
				with patch.object(storage.os, 'fsync', wraps=os.fsync) as spy:
					storage.replace_bytes(target, b'durable')
					self.assertEqual(1, spy.call_count)
					self.assertEqual(b'durable', target.read_bytes())
if '__main__' == __name__:
	unittest.main()
