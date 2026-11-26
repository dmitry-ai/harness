# 2026-11-24 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
WT_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = WT_ROOT / 'scripts'
if str(SCRIPTS) not in sys.path:
	sys.path.insert(0, str(SCRIPTS))
from agent_tools import source_grounding as sg
def _setup_project(root: Path) -> tuple[Path, Path]:
	ev = root / '\ua616/KB/Evidence'
	ev.mkdir(parents=True, exist_ok=True)
	pad = 'alpha beta gamma delta ' * 240
	p_a = ev / 'a.txt'
	p_b = ev / 'b.txt'
	p_a.write_text(f'> *Quoted* alpha—record 41201 confirmed.\n{pad}', encoding='utf-8')
	p_b.write_text(f'Secondary beta–metric 52302 verified.\n{pad}', encoding='utf-8')
	return (p_a, p_b)
# 2026-11-24
# "Cache normalized text and numeric tokens in source_grounding active corpus":
# https://github.com/dmitry-ai/harness/issues/216
class GroundingCorpusCacheM9Tests(unittest.TestCase):
	def test_corpus_cache_matches_uncached_norm_and_isolates_observed_texts(self) -> None:
		with tempfile.TemporaryDirectory() as tmp:
			root = Path(tmp).resolve()
			_setup_project(root)
			url = 'https://example.com/guide'
			doc = f'See [a](\ua616/KB/Evidence/a.txt) and [guide]({url}): observed 63403 and \u00abQuoted alpha-record 41201 confirmed\u00bb.\n'
			shared_cache: dict = {}
			obs_ok = {url: ['Guide notes 63403 on page.\n' + ('omega ' * 800)]}
			obs_missing = {url: ['Guide notes 77777 on page.\n' + ('omega ' * 800)]}
			aud1 = sg.LocalSourceGroundingAuditor(root, doc, observed_texts=obs_ok, cache=shared_cache)
			errs_ok = aud1.run()
			self.assertEqual([], errs_ok)
			errs_missing = sg.LocalSourceGroundingAuditor(root, doc, observed_texts=obs_missing, cache=shared_cache).run()
			self.assertTrue(any(('63403' in e for e in errs_missing)))
	def test_repeated_blocks_avoid_per_block_re_normalization_and_tokenization(self) -> None:
		with tempfile.TemporaryDirectory() as tmp:
			root = Path(tmp).resolve()
			_setup_project(root)
			url = 'https://example.com/spec'
			ext_body = 'Spec states 63403 items.\n' + ('epsilon zeta eta ' * 300)
			obs = {url: [ext_body]}
			blocks = [f'Block {idx} cites [a](\ua616/KB/Evidence/a.txt), [b](\ua616/KB/Evidence/b.txt), and [spec]({url}) confirming 41201, 52302, and 63403.' for idx in range(1, 13)]
			blocks.append('Final block cites [a](\ua616/KB/Evidence/a.txt) with ungrounded 98765 events.')
			doc = '\n\n'.join(blocks) + '\n'
			orig_norm = sg.norm_quote_text
			orig_nums = sg._source_numeric_tokens
			large_norm_calls = 0
			large_num_calls = 0
			def _count_norm(val: str) -> str:
				nonlocal large_norm_calls
				if 4000 <= len(val or ''):
					large_norm_calls += 1
				return orig_norm(val)
			def _count_nums(val: str) -> set[str]:
				nonlocal large_num_calls
				if 4000 <= len(val or ''):
					large_num_calls += 1
				return orig_nums(val)
			with patch.object(sg, 'norm_quote_text', side_effect=_count_norm), patch.object(sg, '_source_numeric_tokens', side_effect=_count_nums):
				errs = sg.LocalSourceGroundingAuditor(root, doc, observed_texts=obs).run()
			self.assertTrue(any(('98765' in e for e in errs)))
			self.assertFalse(any(('41201' in e or '52302' in e or '63403' in e for e in errs)))
			self.assertLessEqual(large_norm_calls, 3)
			self.assertLessEqual(large_num_calls, 3)
if '__main__' == __name__:
	unittest.main()
