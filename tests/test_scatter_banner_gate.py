# 2026-11-24 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Add FILE-6 warning banner rule for out-of-workspace file-scattering recommendations":
# https://github.com/dmitry-ai/harness/issues/200
from __future__ import annotations
from pathlib import Path
import json
import subprocess
import sys
import tempfile
import unittest
WT_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_DIR = WT_ROOT / 'scripts'
if str(SCRIPT_DIR) not in sys.path:
	sys.path.insert(0, str(SCRIPT_DIR))
from agent_tools import completion, links, statements
from agent_tools.response_grounding import ResponseEvidenceAuditor
import check_markdown_slop
_BORDER = '*' * 63
_BANNER_LINE = 'Я, ПИДОРАС, ПРЕДЛАГАЮ РАСКИДЫВАТЬ КАКАШКИ ПО ТВОЕМУ КОМПЬЮТЕРУ.'
_FENCED_BANNER = f'```text\n{_BORDER}\n{_BANNER_LINE}\n{_BORDER}\n```'
_BARE_BANNER = f'{_BORDER}  \n{_BANNER_LINE}  \n{_BORDER}  '
_M1_SCATTER_BODY = """**Суть**:  
Перенести `worktrees_dir` из `${DATA_DIR}/worktrees` во вне-репозиторный корень (`${LOCALAPPDATA}/harness/worktrees/<repo_hash>/<task>`).  

**Доводы за**:  
- Изолирует worktree от `git add .` во внешнем репозитории.  

**Доводы против**:  
- Конфликтует с границами workspace и раскидывает файлы по компьютеру.  

**Оценка**: `20%` (критерий: чистота workspace).  
"""
def _make_m2_safe_body(transcript_uri: str='file:///C:/Users/dfedi/AppData/Roaming/Antigravity-A6/home/.gemini/antigravity/brain/abc/transcript_full.jsonl') -> str:
	return f"""## M-2. Авто-изоляция внутри проекта (`install-global` -> `$HOME/.config/git/ignore`)

**Суть**:  
Оставить `worktrees_dir` внутри рабочего пространства проекта (`ꘖ/data/worktrees`) и прописать паттерн в штатном `$HOME/.config/git/ignore`, не переносить файлы в `%LOCALAPPDATA%/harness`.  

**Доводы за**:  
- Все рабочие файлы остаются внутри проекта; подтверждено по [transcript]({transcript_uri}).  

**Доводы против**:  
- Вынос в `%LOCALAPPDATA%/harness` или `/tmp/worktrees` здесь намеренно отвергнут.  

**Оценка**: `92%` (критерий: сохранность границ проекта).  
"""
_M2_SAFE_BODY = _make_m2_safe_body()
def _make_two_method_doc(m1_prefix: str='', *, transcript_uri: str | None=None) -> str:
	head = '## M-1. Вынос `worktrees_dir` за пределы любых Git-рабочих деревьев во внешнее хранилище\n\n'
	mid = f'{m1_prefix}\n\n' if m1_prefix else ''
	m2_body = _make_m2_safe_body(transcript_uri) if None is not transcript_uri else _M2_SAFE_BODY
	return head + mid + _M1_SCATTER_BODY + '\n' + m2_body
class ScatterBannerGateTests(unittest.TestCase):
	def test_analysis_check_and_answer_check_enforce_file6_banner(self) -> None:
		with tempfile.TemporaryDirectory() as tmp:
			proj = Path(tmp).resolve()
			tr_file = proj / 'AppData/Roaming/Antigravity-A6/home/.gemini/antigravity/brain/abc/transcript_full.jsonl'
			tr_file.parent.mkdir(parents=True, exist_ok=True)
			tr_file.write_text('{}\n', encoding='utf-8')
			tr_uri = f'file:///{tr_file.as_posix()}'
			bad_doc = _make_two_method_doc(transcript_uri=tr_uri)
			good_doc = _make_two_method_doc(_FENCED_BANNER, transcript_uri=tr_uri)
			bad_errs = statements.validate_df_analysis(bad_doc, mode='auto')
			self.assertTrue(any('FILE-6' in e and 'M-1' in e for e in bad_errs), bad_errs)
			self.assertEqual([], statements.validate_df_analysis(good_doc, mode='auto'))
			aud_bad = ResponseEvidenceAuditor(proj, bad_doc, []).validate()
			self.assertTrue(any('FILE-6' in e for e in aud_bad), aud_bad)
			self.assertEqual([], ResponseEvidenceAuditor(proj, good_doc, []).validate())
			self.assertFalse(completion.check_answer(proj, bad_doc)['valid'])
			self.assertTrue(completion.check_answer(proj, good_doc)['valid'])
			cli = str(SCRIPT_DIR / 'harness.py')
			bad_file, good_file = (proj / 'bad.md', proj / 'good.md')
			bad_file.write_text(bad_doc, encoding='utf-8')
			good_file.write_text(good_doc, encoding='utf-8')
			p_bad = subprocess.run([sys.executable, cli, 'analysis-check', str(proj), '--response-file', str(bad_file)], capture_output=True, text=True, encoding='utf-8', check=False)
			self.assertEqual(2, p_bad.returncode, p_bad.stderr or p_bad.stdout)
			self.assertFalse(json.loads(p_bad.stdout)['valid'])
			p_good = subprocess.run([sys.executable, cli, 'analysis-check', str(proj), '--response-file', str(good_file)], capture_output=True, text=True, encoding='utf-8', check=False)
			self.assertEqual(0, p_good.returncode, p_good.stderr or p_good.stdout)
			self.assertTrue(json.loads(p_good.stdout)['valid'])
	def test_banner_must_be_exact_uppercase_and_at_start_of_recommendation(self) -> None:
		lower_banner = f'```text\n{_BORDER}\n{_BANNER_LINE.lower()}\n{_BORDER}\n```'
		short_border = f'```text\n{"*" * 10}\n{_BANNER_LINE}\n{"*" * 10}\n```'
		buried = '## M-1. Вынос кэша в `%LOCALAPPDATA%/mytool`\n\n**Суть**:  \nХранить кэш в `%LOCALAPPDATA%/mytool`.  \n\n' + _FENCED_BANNER + '\n\n**Доводы за**:  \n- Быстро.  \n\n**Доводы против**:  \n- Мусор.  \n\n**Оценка**: `10%`.  \n\n' + _M2_SAFE_BODY
		self.assertTrue(any('FILE-6' in e for e in statements.validate_df_analysis(_make_two_method_doc(lower_banner), mode='auto')))
		self.assertTrue(any('FILE-6' in e for e in statements.validate_df_analysis(_make_two_method_doc(short_border), mode='auto')))
		self.assertTrue(any('FILE-6' in e for e in statements.validate_df_analysis(buried, mode='auto')))
		self.assertEqual([], statements.validate_df_analysis(_make_two_method_doc(_BARE_BANNER), mode='auto'))
	def test_detects_english_and_standalone_scattering_recommendations(self) -> None:
		en_bad = '## M-1. Store build cache in `/tmp/harness-cache`\n\n- Essence: Move cache directories outside the workspace into `/tmp/harness-cache` or `../shared-cache`.  \n- Arguments for: avoids repo clutter.  \n- Arguments against: scatters files on disk.  \n- Score: 15%.  \n\n## M-2. Keep cache inside `.cache/`\n\n- Essence: Keep build cache under the project root.  \n- Arguments for: self-contained workspace.  \n- Arguments against: needs gitignore entry.  \n- Score: 90%.  \n'
		en_good = en_bad.replace('- Essence:', f'{_FENCED_BANNER}\n\n- Essence:', 1)
		self.assertTrue(any('FILE-6' in e and 'M-1' in e for e in statements.validate_df_analysis(en_bad, mode='auto')))
		self.assertEqual([], statements.validate_df_analysis(en_good, mode='auto'))
		standalone_bad = '## Рекомендация\n\nПеренести временные логи проекта в `%APPDATA%\\my-agent\\logs`.  \n'
		standalone_good = f'## Рекомендация\n\n{_FENCED_BANNER}\n\nПеренести временные логи проекта в `%APPDATA%\\my-agent\\logs`.  \n'
		self.assertTrue(any('FILE-6' in e for e in statements.validate_df_analysis(standalone_bad, mode='auto')))
		self.assertEqual([], statements.validate_df_analysis(standalone_good, mode='auto'))
	def test_does_not_false_positive_on_safe_methods_native_configs_or_prose(self) -> None:
		safe_two = _M2_SAFE_BODY + '\n## M-3. Отделение реального профиля пользователя от `%USERPROFILE%` инстанса\n\n**Суть**:  \nЧитать `OS_USER_HOME` отдельно от переопределённого `%USERPROFILE%` и удалить устаревшую запись `~/.git-credentials`.  \n\n**Доводы за**:  \n- Устраняет сбой определения профиля.  \n\n**Доводы против**:  \n- Требует доп. тестов для `%APPDATA%`.  \n\n**Оценка**: `95%`.  \n'
		self.assertEqual([], statements.validate_df_analysis(safe_two, mode='auto'))
		prose = 'Правило `FILE-6` запрещает без предупреждающей блямбы рекомендовать перенос файлов в `${LOCALAPPDATA}/harness/worktrees` или `/tmp/foo`.  \n'
		self.assertEqual([], statements.validate_df_analysis(prose, mode='auto'))
	def test_rules_and_skill_codify_file6_banner_and_pass_lint(self) -> None:
		file_rule = WT_ROOT / 'rules/01-file-boundaries.md'
		stmt_rule = WT_ROOT / 'rules/04-statement-structure.md'
		skill_doc = WT_ROOT / 'skills/df-analysis/SKILL.md'
		turn_doc = WT_ROOT / 'references/turn-completion.md'
		readme_doc = WT_ROOT / 'scripts/README-agent-tools.md'
		for doc in (file_rule, stmt_rule, skill_doc, turn_doc, readme_doc):
			self.assertEqual([], links.validate_file(doc, local_anchors=True, readable_links=True), f'Link errors in {doc.name}')
			self.assertEqual([], check_markdown_slop.markdown_slop_issues(doc.read_text(encoding='utf-8')), f'DOC-4 errors in {doc.name}')
		file_bytes = file_rule.read_bytes()
		self.assertLess(len(file_bytes), 10000, 'rules/01-file-boundaries.md must remain compact')
		file_text = file_bytes.decode('utf-8')
		for token in ('## FILE-6', _BORDER, _BANNER_LINE, 'LOCALAPPDATA', 'analysis-check'):
			self.assertIn(token, file_text, f'Missing {token!r} in rules/01-file-boundaries.md')
		self.assertIn('FILE-6', stmt_rule.read_text(encoding='utf-8'))
		self.assertIn('FILE-6', skill_doc.read_text(encoding='utf-8'))
		self.assertIn('FILE-6', turn_doc.read_text(encoding='utf-8'))
		self.assertIn('FILE-6', readme_doc.read_text(encoding='utf-8'))
if '__main__' == __name__:
	unittest.main()
