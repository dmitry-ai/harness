# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Separate --domain and --topic init labels with kebab-case rejection":
# https://github.com/dmitry-ai/harness/issues/266
from __future__ import annotations
from pathlib import Path
import json
import os
import subprocess
import sys
import tempfile
import unittest
WT_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = WT_ROOT / 'scripts'
TESTS = WT_ROOT / 'tests'
for p in (SCRIPTS, TESTS):
	if str(p) not in sys.path:
		sys.path.insert(0, str(p))
HARNESS_PY = SCRIPTS / 'harness.py'
def _iso_env(home: Path) -> dict[str, str]:
	return {**os.environ, 'USERPROFILE': str(home), 'HOME': str(home), 'APPDATA': str(home / 'AppData/Roaming'), 'HARNESS_TEST_NO_FSYNC': '1', 'GIT_OPTIONAL_LOCKS': '0', 'PYTHONIOENCODING': 'utf-8'}
def _write_capture(base: Path, job_id: str='~022124567641351805598') -> Path:
	from test_onboarding import source
	cap = base / 'capture/source.json'
	cap.parent.mkdir(parents=True, exist_ok=True)
	cap.write_text(json.dumps({**source(job_id), 'url': f'https://upwork.com/jobs/{job_id}'}, ensure_ascii=False), encoding='utf-8')
	return cap
def _run_init(base: Path, *extra: str) -> subprocess.CompletedProcess:
	cap = _write_capture(base)
	env = _iso_env(base / 'home')
	return subprocess.run([sys.executable, str(HARNESS_PY), 'init', '~022124567641351805598', '--from-json', str(cap), '--date', '2026-11-23', '--daily-root', str(base / 'daily'), '--no-register', *extra], cwd=str(base), env=env, stdin=subprocess.DEVNULL, capture_output=True, text=True, encoding='utf-8', timeout=60, check=False)
class ProjectLabelValidationTests(unittest.TestCase):
	def test_init_cli_domain_records_domain_label_kind(self) -> None:
		with tempfile.TemporaryDirectory() as tmp:
			base = Path(tmp).resolve()
			proc = _run_init(base, '--domain', 'blueskypeptide.com')
			self.assertEqual(0, proc.returncode, proc.stderr)
			out = json.loads(proc.stdout)
			proj = Path(out['project_dir'])
			self.assertEqual('1 - blueskypeptide.com', proj.name)
			state = json.loads((proj / '\ua616/project.json').read_text(encoding='utf-8'))
			self.assertEqual('domain', state.get('label_kind'))
			self.assertEqual('blueskypeptide.com', state.get('label'))
			self.assertNotIn('label_warning', out)
	def test_init_cli_legacy_topic_via_domain_warns_and_marks_provisional(self) -> None:
		with tempfile.TemporaryDirectory() as tmp:
			base = Path(tmp).resolve()
			proc = _run_init(base, '--domain', 'Topic')
			self.assertEqual(0, proc.returncode, proc.stderr)
			out = json.loads(proc.stdout)
			proj = Path(out['project_dir'])
			state = json.loads((proj / '\ua616/project.json').read_text(encoding='utf-8'))
			self.assertEqual('provisional_topic', state.get('label_kind'))
			self.assertEqual('Topic', state.get('label'))
			self.assertTrue(out.get('label_warning'))
	def test_init_cli_rejects_kebab_slug_and_bad_domain_with_exit_2(self) -> None:
		bad_cases = (
			('--domain', 'magento-nextjs-ga4-reporting'),
			('--domain', 'shopify-bundle-elixir'),
			('--domain', 'www.blueskypeptide.com'),
			('--domain', 'robots.txt'),
			('--topic', 'magento-nextjs-ga4-reporting'),
			('--domain', 'blueskypeptide.com', '--topic', 'Magento & GA4'),
		)
		for flags in bad_cases:
			with self.subTest(flags=flags), tempfile.TemporaryDirectory() as tmp:
				base = Path(tmp).resolve()
				proc = _run_init(base, *flags)
				self.assertEqual(2, proc.returncode, f'Expected exit 2 for {flags}, got {proc.returncode}: {proc.stdout}\n{proc.stderr}')
				self.assertFalse((base / 'daily').exists())
	def test_init_cli_topic_records_provisional_topic_label_kind(self) -> None:
		with tempfile.TemporaryDirectory() as tmp:
			base = Path(tmp).resolve()
			proc = _run_init(base, '--topic', 'Magento & GA4')
			self.assertEqual(0, proc.returncode, proc.stderr)
			out = json.loads(proc.stdout)
			proj = Path(out['project_dir'])
			self.assertEqual('1 - Magento & GA4', proj.name)
			state = json.loads((proj / '\ua616/project.json').read_text(encoding='utf-8'))
			self.assertEqual('provisional_topic', state.get('label_kind'))
			self.assertEqual('Magento & GA4', state.get('label'))
	def test_validate_label_and_helpers_enforce_slug_and_domain_rules(self) -> None:
		from agent_tools import upwork_project as up
		from agent_tools.project_labels import LabelValidationError, is_kebab_slug, is_valid_domain_label, resolve_init_label
		self.assertTrue(is_kebab_slug('magento-nextjs-ga4-reporting'))
		self.assertTrue(is_kebab_slug('shopify-bundle-elixir'))
		self.assertFalse(is_kebab_slug('magento-e2e'))
		self.assertFalse(is_kebab_slug('Magento & GA4'))
		self.assertTrue(is_valid_domain_label('blueskypeptide.com'))
		self.assertTrue(is_valid_domain_label('sub.example.co.uk'))
		self.assertFalse(is_valid_domain_label('www.blueskypeptide.com'))
		self.assertFalse(is_valid_domain_label('robots.txt'))
		self.assertFalse(is_valid_domain_label('next.js'))
		with self.assertRaises(LabelValidationError):
			up.validate_label('magento-nextjs-ga4-reporting')
		lbl, kind, warn = resolve_init_label(domain='blueskypeptide.com')
		self.assertEqual(('blueskypeptide.com', 'domain', None), (lbl, kind, warn))
		lbl2, kind2, warn2 = resolve_init_label(topic='Magento & GA4')
		self.assertEqual(('Magento & GA4', 'provisional_topic', None), (lbl2, kind2, warn2))
if '__main__' == __name__:
	unittest.main()
