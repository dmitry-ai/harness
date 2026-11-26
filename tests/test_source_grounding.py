# 2026-11-14 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from pathlib import Path
import json
import sys
import tempfile
import unittest
from unittest.mock import patch
SCRIPT_DIR = Path(__file__).resolve().parents[1] / 'scripts'
if str(SCRIPT_DIR) not in sys.path:
	sys.path.insert(0, str(SCRIPT_DIR))
from agent_tools import grounding_domains, source_grounding
# 2026-11-14
# "Consolidate dual Tier 0 source caches into Tier0SourceIndex, extract LocalSourceGroundingAuditor, and isolate hosting domain rules in source_grounding.py":
# https://github.com/dmitry-ai/harness/issues/54
class SourceGroundingRefactorTests(unittest.TestCase):
	def test_auditor_and_domain_rules_deduplicate_ledger_tuples(self) -> None:
		with tempfile.TemporaryDirectory() as tmp:
			root = Path(tmp)
			ev_dir = root / '\ua616' / 'KB' / 'Evidence'
			ev_dir.mkdir(parents=True, exist_ok=True)
			srv = ev_dir / 'srv_metrics.json'
			srv.write_text(json.dumps({'plan': 'M4', 'vcpu': None, 'mem_total': 16384, 'swap_total': 0}), encoding='utf-8')
			source_grounding.sync_fact_ledger(root)
			prose = f'Plan M4 uses 8 vcpu and active swapping per [Source](<{srv.as_posix()}>).  \n'
			auditor = source_grounding.LocalSourceGroundingAuditor(root, prose)
			issues = auditor.run()
			self.assertEqual(3, len(issues), issues)
			self.assertEqual(len(auditor.ledger_tuples), len({(t['entity'], t['attribute'], t['value'], t['source_locator']) for t in auditor.ledger_tuples}))
			self.assertTrue(any(('vcpu=null in \ua616/KB/Evidence/srv_metrics.json' in item for item in issues)), issues)
			self.assertTrue(any(('swap_total=0 in \ua616/KB/Evidence/srv_metrics.json' in item for item in issues)), issues)
			dom = grounding_domains.extract_domain_entities('Ticket 1465836 on Plan XL checks mem_total.')
			self.assertEqual(['mem_total'], dom['metrics'])
			self.assertEqual(['PLAN XL'], dom['plans_norm'])
			self.assertEqual(['1465836'], dom['tickets'])
	def test_tier0_source_index_schema_upgrade_and_single_read(self) -> None:
		with tempfile.TemporaryDirectory() as tmp:
			root = Path(tmp)
			data_dir = root / '\ua616' / 'data'
			data_dir.mkdir(parents=True, exist_ok=True)
			stale_cache = data_dir / 'grounding-cache.json'
			stale_cache.write_text(json.dumps({'version': 1, 'files': {'stale.json': {'sha256': '00'}}}), encoding='utf-8')
			ticket_src = root / 'tickets' / '7654321' / 'source.md'
			ticket_src.parent.mkdir(parents=True, exist_ok=True)
			ticket_src.write_text('# Ticket 7654321\nmem_total: 8192\n', encoding='utf-8')
			idx = source_grounding.Tier0SourceIndex.for_root(root)
			orig_read = Path.read_bytes
			read_calls: list[str] = []
			def tracked_read(self_path: Path) -> bytes:
				if self_path.resolve() == ticket_src.resolve():
					read_calls.append(self_path.name)
				return orig_read(self_path)
			with patch.object(Path, 'read_bytes', tracked_read):
				ledger = idx.sync_ledger()
				disc = idx.discover_entities('Inspect ticket 7654321 mem_total.')
				info = idx.load_source_info(ticket_src)
			self.assertEqual(1, len(read_calls))
			self.assertEqual(1, ledger['tuple_count'])
			self.assertEqual('tickets/7654321/source.md', info['fact_tuples'][0]['source_locator'])
			self.assertEqual('tickets/7654321/source.md', disc[0]['path'])
			saved_cache = json.loads(stale_cache.read_text(encoding='utf-8'))
			self.assertEqual(2, saved_cache['version'])
			self.assertNotIn('stale.json', saved_cache['files'])
	# 2026-11-23
	# "Configure default user locale for language-neutral commands in TEXT-1 and locale gate":
	# https://github.com/dmitry-ai/harness/issues/131
	def test_language_neutral_slash_commands_enforce_user_default_locale_without_breaking_english_requests(self) -> None:
		from agent_tools import completion, runtime
		self.assertEqual('ru', runtime.default_user_locale())
		en_reply = 'The inspection command failed because the browser rejected the side-effect evaluation.'
		ru_reply = 'Команда проверки завершилась с ошибкой при чтении состояния вкладки в браузере.'
		for neutral_req in (
			'/upwork-init  https://upwork.com/jobs/~022124567641351805598',
			'$upwork-init https://upwork.com/jobs/~022124567641351805598',
			'/upwork-cleanup',
			'[upwork-init](slashCommand;upwork-init)  https://upwork.com/jobs/~022124567641351805598',
			'<command-name>/upwork-init</command-name>\n<command-args>https://upwork.com/jobs/~022124567641351805598</command-args>',
			'C:\\work\\research\\provision\\code\\AI\\harness\\readme.md',
		):
			self.assertEqual('', source_grounding.extract_authored_prose(neutral_req), neutral_req)
			errs = source_grounding.verify_target_locale(en_reply, target_locale='und', container_text=neutral_req, allow_explicit_english_request=True, min_target_ratio=0.01, min_alpha=20, default_locale='ru')
			self.assertEqual(['LOCALE_MISMATCH'], [e['code'] for e in errs], neutral_req)
			ok_ru = source_grounding.verify_target_locale(ru_reply, target_locale='und', container_text=neutral_req, allow_explicit_english_request=True, min_target_ratio=0.01, min_alpha=20, default_locale='ru')
			self.assertEqual([], ok_ru, neutral_req)
			comp_errs = completion._intermediate_or_language_issues([{'text': neutral_req}], en_reply)
			self.assertTrue(any(('TEXT-1:' in m for m in comp_errs)), (neutral_req, comp_errs))
			self.assertEqual([], completion._intermediate_or_language_issues([{'text': neutral_req}], ru_reply), neutral_req)
		for english_req in (
			'Explain this error in detail',
			'Fix it',
			'Hi',
			'/upwork-init https://upwork.com/jobs/~022124567641351805598 Answer in English',
			'/upwork-init https://upwork.com/jobs/~022124567641351805598\nAnalyze this job in detail',
		):
			ok_en = source_grounding.verify_target_locale(en_reply, target_locale='und', container_text=english_req, allow_explicit_english_request=True, min_target_ratio=0.01, min_alpha=20, default_locale='ru')
			self.assertEqual([], ok_en, english_req)
			self.assertEqual([], completion._intermediate_or_language_issues([{'text': english_req}], en_reply), english_req)
		self.assertEqual([], source_grounding.verify_target_locale(en_reply, target_locale='und', container_text='/upwork-init https://upwork.com/jobs/~02', allow_explicit_english_request=True, min_target_ratio=0.01, min_alpha=20, default_locale=None))
		self.assertEqual([], source_grounding.verify_target_locale(en_reply, target_locale='und', container_text='', allow_explicit_english_request=True, min_target_ratio=0.01, min_alpha=20, default_locale='ru'))
if '__main__' == __name__:
	unittest.main()
