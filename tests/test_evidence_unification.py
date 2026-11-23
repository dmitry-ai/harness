# 2026-11-23 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# https://github.com/dmitry-ai/harness/issues/76
import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from agent_tools import links, markdown_links, source_grounding
class EvidenceUnificationTests(unittest.TestCase):
	def test_decode_file_uri_handles_windows_relative_and_remote(self):
		self.assertEqual('C:/foo bar/baz.md', links.decode_file_uri('file:///C:/foo%20bar/baz.md#sec'))
		self.assertEqual('C:/a/b.txt', links.decode_file_uri('file://localhost/C:/a/b.txt', reject_remote=True))
		self.assertEqual('KB/note 1.md', links.decode_file_uri('KB/note%201.md#top'))
		with self.assertRaises(ValueError):
			links.decode_file_uri('file://remote-host/share/a.md', reject_remote=True)
	def test_evidence_loader_full_probe_and_bundle_modes(self):
		from agent_tools import evidence_loader
		with tempfile.TemporaryDirectory() as tmp:
			root = Path(tmp)
			obs_dir = root / '\ua616' / 'KB' / 'Evidence' / 'HTTP' / 'obs1'
			obs_dir.mkdir(parents=True)
			html_body = '<html><head><title>Doc Title</title></head><body><h1 id="sec1">Heading</h1><p>Verified phrase here.</p></body></html>'
			raw = html_body.encode('utf-8')
			(obs_dir / 'response.bin').write_bytes(raw)
			meta = {'schema_version': 1, 'url': 'https://example.com/doc', 'final_url': 'https://example.com/doc', 'status': 200, 'kind': 'http', 'content_type': 'text/html; charset=utf-8', 'charset': 'utf-8', 'body_sha256': hashlib.sha256(raw).hexdigest(), 'body_bytes': len(raw), 'observation': 'Evidence/HTTP/obs1/observation.json'}
			obs_json = obs_dir / 'observation.json'
			obs_json.write_text(json.dumps(meta), encoding='utf-8')
			idx_dir = root / '\ua616' / 'data'
			idx_dir.mkdir(parents=True)
			(idx_dir / 'http-index.json').write_text(json.dumps({'k1': {'observation': 'Evidence/HTTP/obs1/observation.json'}}), encoding='utf-8')
			obs_ref, loaded_meta = evidence_loader.resolve_http_observation(root, 'https://example.com/doc')
			self.assertEqual('Evidence/HTTP/obs1/observation.json', obs_ref)
			self.assertEqual(200, loaded_meta['status'])
			content = evidence_loader.load_observation_content(root, obs_ref, loaded_meta, fragment='sec1')
			self.assertEqual('html', content['kind'])
			self.assertIn('sec1', content['data']['anchors'])
			self.assertEqual('http-ok', evidence_loader.probe_observation_status(root, loaded_meta, 'https://example.com/doc', 'sec1'))
			self.assertEqual('anchor-unverified', evidence_loader.probe_observation_status(root, loaded_meta, 'https://example.com/doc', 'missing'))
			bundle = evidence_loader.load_observation_bundle(obs_json, meta, max_bytes=1024 * 1024)
			self.assertTrue(bundle['valid'])
			self.assertIn('Doc Title', bundle['titles'])
			self.assertIn('sec1', bundle['anchors'])
	def test_evidence_loader_rejects_empty_shell_bundle(self):
		from agent_tools import evidence_loader
		with tempfile.TemporaryDirectory() as tmp:
			obs_dir = Path(tmp) / 'obs2'
			obs_dir.mkdir()
			meta = {'url': 'https://example.com/app', 'final_url': 'https://example.com/app', 'status': 200, 'kind': 'http', 'content_type': 'text/html'}
			obs_json = obs_dir / 'observation.json'
			obs_json.write_text(json.dumps(meta), encoding='utf-8')
			(obs_dir / 'extracted-html.json').write_text(json.dumps({'browser_check_required': True, 'word_count': 0, 'headings': []}), encoding='utf-8')
			bundle = evidence_loader.load_observation_bundle(obs_json, meta, max_bytes=1024 * 1024)
			self.assertFalse(bundle['valid'])
			self.assertIn('browser_check_required', bundle['reason'])
	def test_markdown_parser_and_inline_segments_shared(self):
		md = markdown_links.parser(preserve_links=True)
		tokens = md.parse('See [My Label](https://example.com/a%20b) and bare https://example.org/x')[1].children
		segs = list(markdown_links.iter_inline_segments(tokens))
		link_segs = [s for s in segs if 'link' == s[0]]
		self.assertEqual([('link', 'https://example.com/a%20b', 'My Label')], link_segs)
		self.assertEqual([('https://example.com/a%20b', 'My Label')], list(markdown_links.inline_links(tokens)))
		self.assertIn('My Label', markdown_links.numeric_text('See [My Label](https://example.com/a) and [example.com](https://example.com/b)'))
	def test_standalone_source_hydration_uses_tier0_index(self):
		with tempfile.TemporaryDirectory() as tmp:
			sample = Path(tmp) / 'solo.json'
			sample.write_text(json.dumps({'k': 'Unique hydration value 42'}), encoding='utf-8')
			info_a = source_grounding.Tier0SourceIndex.hydrate_standalone(sample)
			info_b = source_grounding._load_local_source_info(sample, root=None)
			self.assertEqual(info_a['sha256'], info_b['sha256'])
			self.assertIn('unique hydration value 42', info_a['norm'])
if '__main__' == __name__:
	unittest.main()
