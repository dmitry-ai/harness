# 2026-11-23 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Add deterministic FIFO repository landing lease with reactive wait":
# https://github.com/dmitry-ai/harness/issues/163
from __future__ import annotations
from pathlib import Path
import sys
import tempfile
import threading
import time
import unittest
HARNESS_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = HARNESS_ROOT / 'scripts'
if str(SCRIPTS) not in sys.path:
	sys.path.insert(0, str(SCRIPTS))
from agent_tools import links
import check_markdown_slop
class LandingLeaseTests(unittest.TestCase):
	def test_acquire_and_release_lifecycle(self):
		from agent_tools.landing_lease import acquire_lease, lease_status, release_lease
		with tempfile.TemporaryDirectory() as td:
			repo = Path(td) / 'repo'
			repo.mkdir()
			leases_dir = Path(td) / 'leases'
			r1 = acquire_lease(repo, 'agent-a', leases_dir=leases_dir)
			self.assertTrue(r1['acquired'])
			r2 = acquire_lease(repo, 'agent-b', wait=False, leases_dir=leases_dir)
			self.assertFalse(r2['acquired'])
			self.assertEqual(r2['position'], 1)
			st = lease_status(repo, leases_dir=leases_dir)
			self.assertFalse(st['free'])
			self.assertEqual(st['holder']['owner'], 'agent-a')
			rel = release_lease(repo, 'agent-a', leases_dir=leases_dir)
			self.assertTrue(rel['released'])
			r2_next = acquire_lease(repo, 'agent-b', wait=False, leases_dir=leases_dir)
			self.assertTrue(r2_next['acquired'])
			release_lease(repo, 'agent-b', leases_dir=leases_dir)
	def test_cli_land_acquire_status_release(self):
		from agent_tools.upwork_project import main as cli_main
		with tempfile.TemporaryDirectory() as td:
			repo = Path(td) / 'repo'
			repo.mkdir()
			self.assertEqual(cli_main(['land-acquire', str(repo), '--owner', 'cli-owner', '--ttl', '60']), 0)
			self.assertEqual(cli_main(['land-status', str(repo)]), 0)
			self.assertEqual(cli_main(['land-release', str(repo), '--owner', 'cli-owner']), 0)
	def test_exec4_documents_fifo_lease_and_swarm(self):
		rule_doc = HARNESS_ROOT / 'rules/08-execution-and-tools.md'
		text = rule_doc.read_text(encoding='utf-8')
		self.assertEqual(links.validate_file(rule_doc, local_anchors=True, readable_links=True), [])
		self.assertEqual(check_markdown_slop.markdown_slop_issues(text), [])
		self.assertIn('land-acquire', text)
		self.assertIn('swarm', text)
	def test_fifo_ordering_prevents_starvation(self):
		from agent_tools.landing_lease import acquire_lease, release_lease
		with tempfile.TemporaryDirectory() as td:
			repo = Path(td) / 'repo'
			repo.mkdir()
			leases_dir = Path(td) / 'leases'
			order: list[str] = []
			order_lock = threading.Lock()
			self.assertTrue(acquire_lease(repo, 'agent-1', leases_dir=leases_dir)['acquired'])
			order.append('agent-1')
			self.assertFalse(acquire_lease(repo, 'agent-2', wait=False, leases_dir=leases_dir)['acquired'])
			self.assertFalse(acquire_lease(repo, 'agent-3', wait=False, leases_dir=leases_dir)['acquired'])
			def _waiter(name: str, poll: float) -> None:
				res = acquire_lease(repo, name, wait=True, timeout=10.0, poll_interval=poll, leases_dir=leases_dir)
				self.assertTrue(res['acquired'])
				with order_lock:
					order.append(name)
				time.sleep(0.1)
				release_lease(repo, name, leases_dir=leases_dir)
			t3 = threading.Thread(target=_waiter, args=('agent-3', 0.02))
			t2 = threading.Thread(target=_waiter, args=('agent-2', 0.08))
			t3.start()
			t2.start()
			time.sleep(0.15)
			release_lease(repo, 'agent-1', leases_dir=leases_dir)
			t2.join(timeout=8.0)
			t3.join(timeout=8.0)
			self.assertEqual(order, ['agent-1', 'agent-2', 'agent-3'])
	def test_stale_dead_pid_and_expired_ttl_evicted(self):
		from agent_tools.landing_lease import acquire_lease, release_lease
		with tempfile.TemporaryDirectory() as td:
			repo = Path(td) / 'repo'
			repo.mkdir()
			leases_dir = Path(td) / 'leases'
			acquire_lease(repo, 'dead-agent', pid=99999999, leases_dir=leases_dir)
			r_live = acquire_lease(repo, 'live-agent', wait=False, leases_dir=leases_dir)
			self.assertTrue(r_live['acquired'])
			release_lease(repo, 'live-agent', leases_dir=leases_dir)
			acquire_lease(repo, 'short-ttl', ttl=0.05, leases_dir=leases_dir)
			time.sleep(0.1)
			r_after = acquire_lease(repo, 'next-agent', wait=False, leases_dir=leases_dir)
			self.assertTrue(r_after['acquired'])
			release_lease(repo, 'next-agent', leases_dir=leases_dir)
	def test_wait_timeout_cleans_up_queue_entry(self):
		from agent_tools.landing_lease import acquire_lease, lease_status, release_lease
		with tempfile.TemporaryDirectory() as td:
			repo = Path(td) / 'repo'
			repo.mkdir()
			leases_dir = Path(td) / 'leases'
			acquire_lease(repo, 'holder', leases_dir=leases_dir)
			res = acquire_lease(repo, 'impatient', wait=True, timeout=0.15, poll_interval=0.05, leases_dir=leases_dir)
			self.assertFalse(res['acquired'])
			self.assertTrue(res['timed_out'])
			st = lease_status(repo, leases_dir=leases_dir)
			self.assertEqual(st['queue'], [])
			release_lease(repo, 'holder', leases_dir=leases_dir)
if '__main__' == __name__:
	unittest.main()
