# 2026-11-23 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path
import sys
import tempfile
import threading
import time
import unittest
SCRIPT_DIR = Path(__file__).resolve().parents[1] / 'scripts'
if str(SCRIPT_DIR) not in sys.path:
	sys.path.insert(0, str(SCRIPT_DIR))
from agent_tools.context import assemble, generate
from agent_tools.storage import locked
# 2026-11-23
# "Eliminate wall-clock race in context.generate and pre-lock flush race in storage.locked":
# https://github.com/dmitry-ai/harness/issues/158
class ContextAndStorageDeterminismTests(unittest.TestCase):
	def test_generate_accepts_explicit_now_for_deterministic_timestamp(self) -> None:
		with tempfile.TemporaryDirectory() as tmp:
			root = Path(tmp).resolve()
			kb = root / 'ꘖ/KB/Overview.md'
			kb.parent.mkdir(parents=True, exist_ok=True)
			kb.write_text('# Overview\nDeterministic body\n', encoding='utf-8')
			fixed_now = datetime(2026, 11, 23, 12, 34, 56, tzinfo=timezone.utc)
			expected_content, expected_sources = assemble(root, now=fixed_now)
			target, out_content, out_sources = generate(root, now=fixed_now)
			self.assertTrue(target.is_file())
			self.assertIn('Generated: 2026-11-23T12:34:56+00:00', out_content)
			self.assertEqual(out_content, expected_content)
			self.assertEqual(out_sources, expected_sources)
	def test_locked_concurrent_fresh_files_succeed_without_permission_error(self) -> None:
		with tempfile.TemporaryDirectory() as tmp:
			base = Path(tmp).resolve()
			for idx in range(15):
				lock_path = base / f'race-{idx}.lock'
				barrier = threading.Barrier(6)
				counter = [0]
				def _worker(p: Path=lock_path, b: threading.Barrier=barrier, c: list[int]=counter) -> int:
					b.wait()
					with locked(p, timeout=10):
						val = c[0]
						time.sleep(0.002)
						c[0] = val + 1
						r = c[0]
					return r
				with ThreadPoolExecutor(max_workers=6) as pool:
					results = list(pool.map(lambda _: _worker(), range(6)))
				self.assertEqual(sorted(results), [1, 2, 3, 4, 5, 6])
				self.assertEqual(counter[0], 6)
	def test_locked_create_on_held_zero_byte_lock_waits_without_permission_error(self) -> None:
		with tempfile.TemporaryDirectory() as tmp:
			lock_path = Path(tmp).resolve() / 'zero.lock'
			lock_path.write_bytes(b'')
			held = threading.Event()
			errors: list[BaseException] = []
			order: list[str] = []
			def _holder() -> None:
				try:
					with locked(lock_path, timeout=5, create=False):
						order.append('holder-acquired')
						held.set()
						time.sleep(0.15)
						order.append('holder-releasing')
				except BaseException as exc:
					held.set()
					errors.append(exc)
			t = threading.Thread(target=_holder)
			t.start()
			try:
				self.assertTrue(held.wait(timeout=5))
				with locked(lock_path, timeout=5, create=True):
					order.append('contender-acquired')
			finally:
				t.join(timeout=5)
			self.assertEqual(errors, [])
			self.assertEqual(order, ['holder-acquired', 'holder-releasing', 'contender-acquired'])
if '__main__' == __name__:
	unittest.main()
