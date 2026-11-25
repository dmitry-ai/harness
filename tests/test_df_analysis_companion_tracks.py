# 2026-11-25 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Require separate companion /df-analysis tracks for every complex problem analysis":
# https://github.com/dmitry-ai/harness/issues/249
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
from agent_tools import completion, df_analysis, links, native_profiles
import check_markdown_slop
_BANNER = (
	'```text\n'
	+ '*' * 63 + '\n'
	+ 'Я, ПИДОРАС, ПРЕДЛАГАЮ РАСКИДЫВАТЬ КАКАШКИ ПО ТВОЕМУ КОМПЬЮТЕРУ.\n'
	+ '*' * 63 + '\n'
	+ '```'
)
def _block_en(header: str, tag: str, issue_url: str | None, desc: str, src_link: str, m1_body: str='') -> str:
	iss = 'null' if None is issue_url else f'"{issue_url}"'
	m1_text = m1_body if m1_body else '- Essence: Enforce a deterministic invariant inside the owning module.  \n'
	return (
		f'# {header}\n\n'
		f'# 0. Problem Metadata ({tag})\n\n'
		'```json\n'
		'{\n'
		'\t"Time": "2026-11-25 23:00:00 UTC+3",\n'
		f'\t"Issue": {iss},\n'
		'\t"Project": {"Name": "Harness", "Path": "C:/work/research/provision/code/AI/harness"}\n'
		'}\n'
		'```\n\n'
		f'# 1. Problem Description ({tag})\n\n'
		f'{desc}  \n\n'
		f'# 2. Root Cause Analysis ({tag})\n\n'
		f'## H-{tag}-1. Primary mechanism\n'
		f'- Essence: Direct defect confirmed in [source](<{src_link}>).  \n'
		'- Arguments for: Reproduced verbatim in observed logs.  \n'
		'- Arguments against: Secondary timing noise remains minor.  \n'
		'- Plausibility: 90% based on direct reproduction.  \n\n'
		f'## H-{tag}-2. Alternative environmental factor\n'
		f'- Essence: External host interference noted in [source](<{src_link}>).  \n'
		'- Arguments for: Host timeout is visible externally.  \n'
		'- Arguments against: Direct local run reproduces without host noise.  \n'
		'- Plausibility: 15% based on controlled repro.  \n\n'
		f'# 3. Source Project Attribution ({tag})\n\n'
		'The architectural owner is Harness (`dmitry-ai/harness`).  \n\n'
		f'# 4. Permanent Systemic Solutions ({tag})\n\n'
		f'## M-{tag}-1. Systemic guardrail\n'
		f'{m1_text}'
		'- Arguments for: Eliminates the defect permanently at its source.  \n'
		'- Arguments against: Requires dedicated regression tests.  \n'
		'- Score: 95% for systemic elimination.  \n\n'
		f'## M-{tag}-2. Manual workaround\n'
		'- Essence: Document a checklist reminder for operators.  \n'
		'- Arguments for: Zero code changes required.  \n'
		'- Arguments against: Fails silently under pressure.  \n'
		'- Score: 20% for systemic elimination.  \n'
	)
def _block_ru(header: str, tag: str, issue_url: str | None, desc: str, src_link: str, m1_body: str='') -> str:
	iss = 'null' if None is issue_url else f'"{issue_url}"'
	m1_text = m1_body if m1_body else '- Суть: Закрыть дефект системной проверкой в базовом модуле.  \n'
	return (
		f'# {header}\n\n'
		f'# 0. Метаданные проблемы ({tag})\n\n'
		'```json\n'
		'{\n'
		'\t"Time": "2026-11-25 23:00:00 UTC+3",\n'
		f'\t"Issue": {iss},\n'
		'\t"Project": {"Name": "Harness", "Path": "C:/work/research/provision/code/AI/harness"}\n'
		'}\n'
		'```\n\n'
		f'# 1. Описание проблемы ({tag})\n\n'
		f'{desc}  \n\n'
		f'# 2. Анализ первопричин ({tag})\n\n'
		f'## H-{tag}-1. Основная причина\n'
		f'- Суть: Прямое подтверждение в [артефакте](<{src_link}>).  \n'
		'- Доводы за: Воспроизведено дословно по логам и коду.  \n'
		'- Доводы против: Вторичные факторы среды дают малый вклад.  \n'
		'- Оценка правдоподобия: 92% по прямому воспроизведению.  \n\n'
		f'## H-{tag}-2. Альтернативная версия\n'
		f'- Суть: Внешнее вмешательство хоста по [артефакту](<{src_link}>).  \n'
		'- Доводы за: Внешний симптом совпадает с ошибкой хоста.  \n'
		'- Доводы против: Изолированный локальный прогон повторяет сбой.  \n'
		'- Оценка правдоподобия: 10% по контрольному прогону.  \n\n'
		f'# 3. Атрибуция исходного проекта ({tag})\n\n'
		'Архитектурный владелец — базовый проект Harness (`dmitry-ai/harness`).  \n\n'
		f'# 4. Постоянные системные решения ({tag})\n\n'
		f'## M-{tag}-1. Системное исправление\n'
		f'{m1_text}'
		'- Доводы за: Устраняет первопричину навсегда без костылей.  \n'
		'- Доводы против: Требует отдельных регрессионных тестов.  \n'
		'- Оценка эксперта: 95% по критерию системной надёжности.  \n\n'
		f'## M-{tag}-2. Ручной обход\n'
		'- Суть: Полагаться на ручную проверку перед завершением хода.  \n'
		'- Доводы за: Не требует правок кода.  \n'
		'- Доводы против: Не защищает от повторения ошибки.  \n'
		'- Оценка эксперта: 20% по критерию системной надёжности.  \n'
	)
def _four_track_en(src_link: str, *, m1_primary: str='') -> str:
	parts = [
		_block_en('Analysis 1: Hook timeout failure', '1', 'https://github.com/dmitry-ai/harness/issues/245', 'PreToolUse timed out with verbatim error: `exit status 1, stderr: `. ', src_link, m1_body=m1_primary),
		_block_en('Analysis 2: Culprit and provenance attribution', '2', 'https://github.com/dmitry-ai/harness/issues/246', 'Agent A6 promoted commit `7ee1e54` and ignored verbatim `JSON hook failed` errors.', src_link),
		_block_en('Analysis 3: Test and verification escape', '3', 'https://github.com/dmitry-ai/harness/issues/247', 'Full suite reported `Ran 1180 tests ... OK` while omitting multi-commit subprocess budgets.', src_link),
		_block_en('Analysis 4: Journal and reporting integrity', '4', 'https://github.com/dmitry-ai/harness/issues/248', 'Agent output bypassed Journal `ꙮ` (`FILE-3`) after `Stop hook blocked termination` fell open.', src_link),
	]
	return '\n---\n\n'.join(parts)
def _four_track_ru(src_link: str, *, m1_primary: str='') -> str:
	parts = [
		_block_ru('Разбор задачи §1: падение хука при выполнении хода', '1', 'https://github.com/dmitry-ai/harness/issues/245', 'Хук завершился с дословной ошибкой: «JSON hook failed: exit status 1».', src_link, m1_body=m1_primary),
		_block_ru('Разбор задачи §2: кто конкретно сломал работу агенту §1', '2', 'https://github.com/dmitry-ai/harness/issues/246', 'Агент A6 активировал снимок `7ee1e54` и проигнорировал три падения «exit status 1».', src_link),
		_block_ru('Разбор задачи §3: почему тесты не помешали виновнику §2', '3', 'https://github.com/dmitry-ai/harness/issues/247', 'Прогон выдал «Ran 1180 tests ... OK», но не проверял бюджет `subprocess.run`.', src_link),
		_block_ru('Разбор задачи §4: обход Журнала ꙮ и контур отчётности', '4', 'https://github.com/dmitry-ai/harness/issues/248', 'После «Stop hook blocked termination» отчёт ушёл в UI в обход Журнала `ꙮ` (`FILE-3`).', src_link),
	]
	return '\n---\n\n'.join(parts)
class DfAnalysisCompanionTracksTests(unittest.TestCase):
	def test_bundled_companion_topics_inside_single_block_still_rejected(self) -> None:
		bundled = _block_ru(
			'Разбор проблемы целиком',
			'1',
			'https://github.com/dmitry-ai/harness/issues/245',
			'Хук упал с «exit status 1»; виновник — агент A6; тесты не помешали виновнику (`Ran 1180 tests OK`); агент писал в обход Журнала `ꙮ`.',
			'https://example.com/trace#step1',
		)
		errs = df_analysis.validate_df_analysis(bundled, mode='auto')
		self.assertTrue(any('4 separate' in e for e in errs), errs)
	def test_four_blocks_missing_or_merged_companion_track_rejected(self) -> None:
		src = 'https://example.com/log#line1'
		missing_test = '\n---\n\n'.join([
			_block_en('Analysis 1: Primary defect', '1', 'https://github.com/dmitry-ai/harness/issues/245', 'Primary error: `exit status 1`.', src),
			_block_en('Analysis 1B: Secondary symptom', '1b', 'https://github.com/dmitry-ai/harness/issues/245', 'Secondary error: `timeout reached`.', src),
			_block_en('Analysis 2: Culprit attribution', '2', 'https://github.com/dmitry-ai/harness/issues/246', 'Who introduced the regression: commit `7ee1e54`.', src),
			_block_en('Analysis 4: Journal integrity', '4', 'https://github.com/dmitry-ai/harness/issues/248', 'Unjournaled reply bypassed Journal `ꙮ` under `FILE-3`.', src),
		])
		errs_missing = df_analysis.validate_df_analysis(missing_test, mode='auto')
		self.assertTrue(any('test' in e.lower() for e in errs_missing), errs_missing)
		merged_two = '\n---\n\n'.join([
			_block_en('Analysis 1: Primary defect', '1', 'https://github.com/dmitry-ai/harness/issues/245', 'Primary error: `exit status 1`.', src),
			_block_en('Analysis 2: Culprit and why tests failed to catch it', '2', 'https://github.com/dmitry-ai/harness/issues/246', 'Culprit commit `7ee1e54` escaped because tests failed to check subprocess count.', src),
			_block_en('Analysis 3: Extra performance note', '3', 'https://github.com/dmitry-ai/harness/issues/247', 'Latency measured at `11.8s` on cold disk.', src),
			_block_en('Analysis 4: Journal integrity', '4', 'https://github.com/dmitry-ai/harness/issues/248', 'Reply bypassed Journal `ꙮ` (`FILE-3`) after `Stop Gate` fail-open.', src),
		])
		errs_merged = df_analysis.validate_df_analysis(merged_two, mode='auto')
		self.assertTrue(any('distinct' in e.lower() or 'separate' in e.lower() for e in errs_merged), errs_merged)
	def test_four_separate_problem_analyses_validated_independently_ru_and_en(self) -> None:
		with tempfile.TemporaryDirectory() as tmp:
			proj = Path(tmp).resolve()
			ev = proj / 'trace.log'
			ev.write_text('JSON hook failed: exit status 1\n', encoding='utf-8')
			src = f'file:///{ev.as_posix()}'
			ru_doc = _four_track_ru(src)
			en_doc = _four_track_en(src)
			self.assertEqual([], df_analysis.validate_df_analysis(ru_doc, mode='auto'))
			self.assertEqual([], df_analysis.validate_df_analysis(en_doc, mode='auto'))
			self.assertTrue(completion.check_answer(proj, ru_doc)['valid'])
			broken_block2 = ru_doc.replace('# 3. Атрибуция исходного проекта (2)\n\nАрхитектурный владелец — базовый проект Harness (`dmitry-ai/harness`).  \n\n', '')
			errs_b2 = df_analysis.validate_df_analysis(broken_block2, mode='auto')
			self.assertTrue(any('# 3' in e for e in errs_b2), errs_b2)
			broken_block1_issue = en_doc.replace('\t"Issue": "https://github.com/dmitry-ai/harness/issues/245",\n', '')
			errs_b1 = df_analysis.validate_df_analysis(broken_block1_issue, mode='auto')
			self.assertTrue(any('"Issue"' in e for e in errs_b1), errs_b1)
			cli = str(SCRIPT_DIR / 'harness.py')
			ok_f = proj / 'ok.md'
			ok_f.write_text(ru_doc, encoding='utf-8')
			proc = subprocess.run([sys.executable, cli, 'analysis-check', str(proj), '--response-file', str(ok_f), '--mode', 'problem'], stdin=subprocess.DEVNULL, capture_output=True, text=True, encoding='utf-8', check=False, timeout=30)
			self.assertEqual(0, proc.returncode, proc.stderr or proc.stdout)
			self.assertTrue(json.loads(proc.stdout)['valid'])
	def test_general_mode_and_non_problem_responses_unaffected(self) -> None:
		self.assertEqual([], df_analysis.validate_df_analysis('Задача выполнена успешно.  \n', requests=[{'text': 'Fix typo'}], mode='auto'))
		general = (
			'## H-1. Cache staleness\n- Essence: see [doc](https://example.com/a#s).  \n- Arguments for: TTL missed.  \n- Arguments against: cold run lags.  \n- Plausibility: 65%.  \n\n'
			'## H-2. Lock wait\n- Essence: see [doc](https://example.com/b#s).  \n- Arguments for: spikes under load.  \n- Arguments against: single run lags.  \n- Plausibility: 55%.  \n'
		)
		self.assertEqual([], df_analysis.validate_df_analysis(general, requests=[{'text': '/df-analysis Compare options'}], mode='auto'))
	def test_scatter_banner_enforced_in_earlier_problem_blocks(self) -> None:
		src = 'https://example.com/log#s'
		scatter_m1 = '- Суть: Перенести временные файлы в `%LOCALAPPDATA%/harness/tmp`.  \n'
		bad_doc = _four_track_ru(src, m1_primary=scatter_m1)
		errs = df_analysis.validate_df_analysis(bad_doc, mode='auto')
		self.assertTrue(any('FILE-6' in e for e in errs), errs)
		good_doc = _four_track_ru(src, m1_primary=f'{_BANNER}\n\n{scatter_m1}')
		self.assertEqual([], df_analysis.validate_df_analysis(good_doc, mode='auto'))
	def test_single_problem_block_rejected_when_companion_tracks_missing(self) -> None:
		single = _block_en('Analysis 1: Hook timeout failure', '1', 'https://github.com/dmitry-ai/harness/issues/245', 'PreToolUse failed with verbatim `exit status 1`.', 'https://example.com/log#s')
		errs = df_analysis.validate_df_analysis(single, mode='auto')
		self.assertTrue(any('4 separate' in e for e in errs), errs)
		self.assertTrue(any('culprit' in e.lower() for e in errs), errs)
		self.assertTrue(any('test' in e.lower() for e in errs), errs)
		self.assertTrue(any('journal' in e.lower() for e in errs), errs)
	def test_skill_rules_and_docs_codify_mandatory_separate_companion_tracks(self) -> None:
		skills = native_profiles._skills(WT_ROOT)
		skill_path = skills['df-analysis'][0]
		stmt_rule = WT_ROOT / 'rules/04-statement-structure.md'
		turn_doc = WT_ROOT / 'references/turn-completion.md'
		readme_doc = WT_ROOT / 'scripts/README-agent-tools.md'
		perf_tmpl = WT_ROOT / 'skills/df--harness--improvement--performance/references/report-template.md'
		for doc in (skill_path, stmt_rule, turn_doc, readme_doc, perf_tmpl):
			self.assertEqual([], links.validate_file(doc, local_anchors=True, readable_links=True), f'Link errors in {doc.name}')
			self.assertEqual([], check_markdown_slop.markdown_slop_issues(doc.read_text(encoding='utf-8')), f'DOC-4 errors in {doc.name}')
		skill_text = skill_path.read_text(encoding='utf-8')
		for token in ('four separate', 'Culprit', 'Test', 'Journal', 'FILE-3', 'never merge'):
			self.assertIn(token.lower(), skill_text.lower(), f'Missing {token!r} in skills/df-analysis/SKILL.md')
		stmt_bytes = stmt_rule.read_bytes()
		self.assertLess(len(stmt_bytes), 12000, 'rules/04-statement-structure.md must remain compact')
		stmt_text = stmt_bytes.decode('utf-8').lower()
		for token in ('four separate', 'culprit', 'test', 'journal'):
			self.assertIn(token, stmt_text, f'Missing {token!r} in rules/04-statement-structure.md')
if '__main__' == __name__:
	unittest.main()
