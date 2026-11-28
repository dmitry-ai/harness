# 2026-11-28 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from pathlib import Path
import json
import sys
import unittest
_SCRIPTS = Path(__file__).resolve().parents[1] / 'scripts'
if str(_SCRIPTS) not in sys.path:
	sys.path.insert(0, str(_SCRIPTS))
from Df.Harness.Grounding.ResponseAuditor import ResponseAuditor
from Df.Harness.Research.UserUrlPolicy import UserUrlPolicy
from test_agent_tools import TemporaryCase
# 2026-11-28 "Enforce non-www user URL policy with KB alias grounding": https://github.com/dmitry-ai/harness/issues/416
class UserUrlPolicyTests(TemporaryCase):
	# @used-by :meth:`UserUrlPolicyTests.test_broken_apex_keeps_www_and_blocks_false_alias()`
	# @used-by :meth:`UserUrlPolicyTests.test_policy_helpers_classification_and_immutability()`
	# @used-by :meth:`UserUrlPolicyTests.test_response_auditor_aliases_www_subpages_and_blocks_authored_www()`
	def __seed_http_obs(self, slug: str, meta: dict, html: str='') -> Path:
		obs_dir = self.root / f'\ua616/KB/Evidence/HTTP/{slug}'
		obs_dir.mkdir(parents=True, exist_ok=True)
		(obs_dir / 'observation.json').write_text(json.dumps(meta, ensure_ascii=False), encoding='utf-8')
		if html:
			(obs_dir / 'response.bin').write_text(html, encoding='utf-8')
		return obs_dir / 'observation.json'
	# @used-by :meth:`UserUrlPolicyTests.test_broken_apex_keeps_www_and_blocks_false_alias()`
	# @used-by :meth:`UserUrlPolicyTests.test_response_auditor_aliases_www_subpages_and_blocks_authored_www()`
	# @used-by :meth:`UserUrlPolicyTests.test_uncaptured_client_intake_www_url_has_no_deadlock()`
	def __seed_upwork_project(self, label: str, kb_text: str, websites: list[dict] | None=None) -> None:
		(self.root / '\ua616/KB').mkdir(parents=True, exist_ok=True)
		(self.root / '\U0001f56e').mkdir(parents=True, exist_ok=True)
		(self.root / '\ua616/project.json').write_text(json.dumps({'job_id': '~02416000', 'label': label, 'fs_version': 2}), encoding='utf-8')
		(self.root / '\ua616/KB/Website.md').write_text(kb_text, encoding='utf-8')
		if None is not websites:
			(self.root / '\ua616/KB/Analysis.json').write_text(json.dumps({'websites': websites}), encoding='utf-8')
	# @used-by :mod:`unittest`
	def test_broken_apex_keeps_www_and_blocks_false_alias(self):
		self.__seed_upwork_project('broken-apex.test', '# Site\nhttps://www.broken-apex.test/info\n', [{'url': 'https://www.broken-apex.test/', 'role': 'target', 'basis_id': 'H-1'}])
		self.__seed_http_obs('apex-fail', {'url': 'https://broken-apex.test/', 'status': None, 'error': 'URLError: Name or service not known'})
		self.__seed_http_obs('www-info', {'url': 'https://www.broken-apex.test/info', 'final_url': 'https://www.broken-apex.test/info', 'status': 200, 'content_type': 'text/html'}, '<html><head><title>Broken Apex Info</title></head><body><h1 id="details">Details</h1><p>Only www host resolves in DNS for this site.</p></body></html>')
		ok_errs = ResponseAuditor(self.root, 'See [Broken Apex Info](https://www.broken-apex.test/info#details).  \n', []).validate()
		self.assertEqual([], ok_errs)
		bad_alias_errs = ResponseAuditor(self.root, 'See [Broken Apex Info](https://broken-apex.test/info#details).  \n', []).validate()
		self.assertTrue(any(('VERIFY-1' in e or 'KB-1' in e for e in bad_alias_errs)), bad_alias_errs)
	# @used-by :mod:`unittest`
	def test_policy_helpers_classification_and_immutability(self):
		self.assertEqual('blueskypeptide.com', UserUrlPolicy.apex_host('https://www.blueskypeptide.com/contact'))
		self.assertEqual('www.localhost', UserUrlPolicy.apex_host('https://www.localhost/test'))
		self.assertTrue(UserUrlPolicy.is_www_host('https://www.blueskypeptide.com/'))
		self.assertFalse(UserUrlPolicy.is_www_host('https://blueskypeptide.com/'))
		self.assertEqual('https://blueskypeptide.com/a?x=1#top', UserUrlPolicy.strip_www('https://www.blueskypeptide.com/a?x=1#top'))
		self.assertEqual('https://blueskypeptide.com', UserUrlPolicy.format_card_url('https://www.blueskypeptide.com/'))
		self.assertEqual('https://www.broken.test', UserUrlPolicy.format_card_url('https://www.broken.test/', failed_apex_hosts=frozenset({'broken.test'})))
		self.assertEqual(('working', 'blueskypeptide.com'), UserUrlPolicy.classify_observation({'url': 'https://blueskypeptide.com/', 'final_url': 'https://www.blueskypeptide.com/', 'status': 200}))
		self.assertEqual(('failed', 'dead.test'), UserUrlPolicy.classify_observation({'url': 'https://dead.test/', 'status': None, 'error': 'gaierror'}))
		self.assertEqual((None, None), UserUrlPolicy.classify_observation({'url': 'https://ok.test/missing-page', 'status': 404}))
		self.__seed_http_obs('r1', {'url': 'https://retry.test/', 'status': 503})
		self.__seed_http_obs('r2', {'url': 'https://retry.test/', 'final_url': 'https://www.retry.test/', 'status': 200})
		pol = UserUrlPolicy.from_evidence_dir(self.root / '\ua616/KB/Evidence')
		self.assertEqual(frozenset(), pol.client_site_hosts)
		self.assertIn('retry.test', pol.working_apex_hosts)
		self.assertNotIn('retry.test', pol.failed_apex_hosts)
		self.assertTrue(pol.check_urls(['https://www.retry.test/path']))
		self.assertEqual([], pol.check_urls(['https://www.unrelated-third-party.example/doc']))
	# @used-by :mod:`unittest`
	def test_response_auditor_aliases_www_subpages_and_blocks_authored_www(self):
		self.__seed_upwork_project('blueskypeptide.com', '# Site\nhttps://www.blueskypeptide.com/contact\nhttps://www.forum.test/t/topic-slug/42\n', [{'url': 'https://www.blueskypeptide.com/', 'role': 'target', 'basis_id': 'H-1'}])
		self.__seed_http_obs('root-redir', {'url': 'https://blueskypeptide.com/', 'final_url': 'https://www.blueskypeptide.com/', 'status': 200, 'content_type': 'text/html'}, '<html><head><title>Blue Sky Peptide</title></head><body><h1>Home</h1></body></html>')
		self.__seed_http_obs('contact', {'url': 'https://www.blueskypeptide.com/contact', 'final_url': 'https://www.blueskypeptide.com/contact', 'status': 200, 'content_type': 'text/html'}, '<html><head><title>Contact Blue Sky</title></head><body><h2 id="support">Support</h2><p>Reach our peptide support team by email any weekday.</p></body></html>')
		self.__seed_http_obs('forum', {'url': 'https://www.forum.test/t/topic-slug/42', 'final_url': 'https://www.forum.test/t/topic-slug/42', 'status': 200, 'content_type': 'application/json'}, json.dumps({'id': 42, 'title': 'Discourse Forum Topic Title', 'url': 'https://www.forum.test/t/topic-slug/42'}))
		good_md = 'See [Contact Blue Sky](https://blueskypeptide.com/contact#support) («Reach our peptide support team by email any weekday.») and [Discourse Forum Topic Title](https://forum.test/t/42).  \n'
		self.assertEqual([], ResponseAuditor(self.root, good_md, []).validate())
		quote_ok = 'Original quote: «Visit https://www.blueskypeptide.com/contact» and "https://www.blueskypeptide.com/contact" and `https://www.blueskypeptide.com/contact`.  \n\n> https://www.blueskypeptide.com/contact\n\n```text\nhttps://www.blueskypeptide.com/contact\n```\n'
		self.assertEqual([], ResponseAuditor(self.root, quote_ok, []).validate())
		bad_link = ResponseAuditor(self.root, 'See [Contact Blue Sky](https://www.blueskypeptide.com/contact#support).  \n', []).validate()
		self.assertTrue(any(('LINK-5' in e and 'www.' in e for e in bad_link)), bad_link)
		bad_bare = ResponseAuditor(self.root, 'Bare URL https://www.blueskypeptide.com/contact is authored.  \n', []).validate()
		self.assertTrue(any(('LINK-5' in e and 'www.' in e for e in bad_bare)), bad_bare)
	# @used-by :mod:`unittest`
	def test_uncaptured_client_intake_www_url_has_no_deadlock(self):
		self.__seed_upwork_project('blueskypeptide.com', '# Site\nhttps://www.blueskypeptide.com/admin\n', [{'url': 'https://www.blueskypeptide.com/', 'role': 'target', 'basis_id': 'H-1'}])
		reqs = [{'text': 'Please fix https://www.blueskypeptide.com/admin in our store.'}]
		ok_errs = ResponseAuditor(self.root, 'Check [Admin portal](https://blueskypeptide.com/admin).  \n', reqs).validate()
		self.assertEqual([], ok_errs)
		www_errs = ResponseAuditor(self.root, 'Check [Admin portal](https://www.blueskypeptide.com/admin).  \n', reqs).validate()
		self.assertTrue(any(('LINK-5' in e and 'www.' in e for e in www_errs)), www_errs)
if '__main__' == __name__:
	unittest.main()
