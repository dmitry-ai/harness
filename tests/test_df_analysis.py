# 2026-11-24 Dmitrii Fediuk https://github.com/dmitrii-fediuk
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
from agent_tools import completion, df_analysis, research
from agent_tools.issues.linter import IssueMarkdownLinter
from agent_tools.response_grounding import ResponseEvidenceAuditor
import check_markdown_slop
# 2026-11-25
# "Require separate companion /df-analysis tracks for every complex problem analysis":
# https://github.com/dmitry-ai/harness/issues/249
# 2026-11-26 "Ban file:/// links for GitHub repositories and ground tagged GitHub URLs": https://github.com/dmitry-ai/harness/issues/264
_VALID_PROBLEM_RU = """# 0. Мета-данные проблемы

```json
{
	"Time": "2026-11-24 01:30:00 UTC+3",
	"Issue": "https://github.com/dmitry-ai/harness/issues/181",
	"Project": {
		"Name": "Harness",
		"Path": "C:/work/research/provision/code/AI/harness"
	}
}
```

# 1. Описание проблемы

При проверке ответа валидатор пропустил таблицу Markdown, хотя в логе вывода было зафиксировано: «exit code 0, issues: []».  

# 2. Причины проблемы

## H-1. Пропуск строк с `|` в `scan_doc4_sentence_issues`

- Суть: обработчик [hook_runtime.py](https://example.com/harness/hook_runtime.py#L22) исключает строки, начинающиеся с `|`.  
- Доводы за: дословное условие `not stripped.startswith(('#', '|', '---', '===', '>'))` пропускает заголовки и разделители таблиц.  
- Доводы против: отдельные пайпы в обычной прозе не являются таблицами и требуют проверки строки-разделителя.  
- Оценка правдоподобности: 90%.  

## H-2. Отсутствие проверки таблиц в `answer-prepare`

- Суть: исполнитель [completion.py](https://example.com/harness/completion.py#L321) не вызывает проверку таблиц `DOC-4`.  
- Доводы за: `AnswerPreparationRunner.run()` вызывает только `response_source_and_kb_issues`, а не `markdown_slop_issues`.  
- Доводы против: при правке `hook_runtime.py` `PreToolUse` уже ловит запись `.md`, но прямой вызов `answer-prepare` всё равно остаётся уязвим.  
- Оценка правдоподобности: 85%.  

# 3. Источник проблемы

Источником проблемы является базовый проект более высокого уровня — Harness (`dmitry-ai/harness`), а не клиентский workspace, где проявился сбой.  

# 4. Устранение проблемы

## M-1. Единый детектор GFM-таблиц в `df_analysis.py` и подключение ко всем шлюзам

- Суть: реализовать проверку пары «строка заголовка + разделитель `| --- |`» вне code fences и подключить её к `hook_runtime.py`, `issues/linter.py` и `response_grounding.py`.  
- Доводы за: единая точка правды без дублирования и нулевые ложные срабатывания на одиночных `|` в прозе.  
- Доводы против: требует обновления нескольких точек интеграции и отдельных тестов.  
- Оценка: 95%.  

## M-2. Проверка только в `PreToolUse`-хуке `check_markdown_slop.py`

- Суть: добавить регулярное выражение для таблиц только внутри `check_markdown_slop.py`.  
- Доводы за: минимальный объём правок в одном файле.  
- Доводы против: не защищает `answer-prepare`, Codex и `df_github_issue.py`, оставляя обходной путь.  
- Оценка: 30%.  

---

# Разбор задачи §2: кто конкретно внёс дефект пропуска таблиц

# 0. Мета-данные проблемы (§2)

```json
{
	"Time": "2026-11-24 01:31:00 UTC+3",
	"Issue": "https://github.com/dmitry-ai/harness/issues/181",
	"Project": {
		"Name": "Harness",
		"Path": "C:/work/research/provision/code/AI/harness"
	}
}
```

# 1. Описание проблемы (§2)

Виновником пропуска таблиц стала правка в `hook_runtime.py`, добавившая пропуск строк с `|` («not stripped.startswith(('#', '|', '---', '===', '>'))») без проверки разделителя GFM.  

# 2. Причины проблемы (§2)

## H-2-1. Упрощённый фильтр строк в коммите первичного автора

- Суть: автор коммита в [hook_runtime.py](https://example.com/harness/hook_runtime.py#L22) исключил строки с `|` целиком.  
- Доводы за: строка присутствует напрямую в исходном файле.  
- Доводы против: могла преследоваться цель избежать ложных срабатываний на prose-пайпах.  
- Оценка правдоподобности: 90%.  

## H-2-2. Отсутствие ревью-гейта на инварианты `DOC-4`

- Суть: при приёмке в [completion.py](https://example.com/harness/completion.py#L321) не требовалась проверка таблиц.  
- Доводы за: валидатор вызывался не на всех шлюзах.  
- Доводы против: вторичный фактор относительно самой правки.  
- Оценка правдоподобности: 60%.  

# 3. Источник проблемы (§2)

Архитектурным источником является базовый проект Harness (`dmitry-ai/harness`).  

# 4. Устранение проблемы (§2)

## M-2-1. Единый гейт проверки `DOC-4` при приземлении

- Суть: проверять инварианты `DOC-4` на уровне общего валидатора и pre-commit.  
- Доводы за: блокирует регрессию любого автора до слияния в `main`.  
- Доводы против: добавляет миллисекунды на проверку Markdown.  
- Оценка: 95%.  

## M-2-2. Ручной аудит коммитов

- Суть: проверять правки `hook_runtime.py` вручную.  
- Доводы за: не требует кода.  
- Доводы против: не масштабируется и допускает пропуски.  
- Оценка: 20%.  

---

# Разбор задачи §3: почему тесты не помешали виновнику §2

# 0. Мета-данные проблемы (§3)

```json
{
	"Time": "2026-11-24 01:32:00 UTC+3",
	"Issue": "https://github.com/dmitry-ai/harness/issues/181",
	"Project": {
		"Name": "Harness",
		"Path": "C:/work/research/provision/code/AI/harness"
	}
}
```

# 1. Описание проблемы (§3)

Тестовый набор прошёл со статусом «OK» и не поймал пропуск GFM-таблиц в `hook_runtime.py` и `answer-prepare`.  

# 2. Причины проблемы (§3)

## H-3-1. Отсутствие негативной фикстуры с GFM-таблицей

- Суть: в тестах [hook_runtime.py](https://example.com/harness/hook_runtime.py#L22) отсутствовал кейс с парой заголовка и разделителя `| --- |`.  
- Доводы за: тесты проверяли только разрывы предложений, но не таблицы.  
- Доводы против: часть проверок покрывала лишь `check_markdown_slop.py`.  
- Оценка правдоподобности: 92%.  

## H-3-2. Несвязанность тестов `PreToolUse` и `answer-prepare`

- Суть: шлюз [completion.py](https://example.com/harness/completion.py#L321) тестировался отдельно от `hook_runtime.py`.  
- Доводы за: интеграционного теста на все три шлюза не существовало.  
- Доводы против: это следствие отсутствия общего детектора.  
- Оценка правдоподобности: 75%.  

# 3. Источник проблемы (§3)

Владельцем тестового контура является Harness (`dmitry-ai/harness`).  

# 4. Устранение проблемы (§3)

## M-3-1. Сквозной регрессионный тест таблиц на всех шлюзах

- Суть: добавить `test_df_analysis.py`, проверяющий блокировку таблиц в `hook_runtime`, `linter` и `answer-prepare`.  
- Доводы за: детерминированно ловит любую регрессию и защищён `Test Ratchet`.  
- Доводы против: требует поддержки фикстур.  
- Оценка: 95%.  

## M-3-2. Проверка только unit-тестом парсера

- Суть: тестировать только функцию поиска строк таблицы без интеграции со шлюзами.  
- Доводы за: проще написать.  
- Доводы против: не поймает отключение вызова в `completion.py`.  
- Оценка: 40%.  

---

# Разбор задачи §4: аудит Журнала `ꙮ` и контура отчётности

# 0. Мета-данные проблемы (§4)

```json
{
	"Time": "2026-11-24 01:33:00 UTC+3",
	"Issue": null,
	"Project": {
		"Name": "Harness",
		"Path": "C:/work/research/provision/code/AI/harness"
	}
}
```

# 1. Описание проблемы (§4)

Проведён аудит контура Журнала `ꙮ` (`FILE-3`): обхода `answer-prepare` не зафиксировано («exit code 0, issues: []»), однако ответ с запрещённой таблицей мог быть записан в `ꙮ` без блокировки.  

# 2. Причины проблемы (§4)

## H-4-1. Пропуск проверки таблиц внутри `answer-prepare`

- Суть: при записи в `ꙮ` шлюз [completion.py](https://example.com/harness/completion.py#L321) не отклонял таблицы.  
- Доводы за: `ResponseEvidenceAuditor` не вызывал `analysis_gate_issues`.  
- Доводы против: сам механизм записи пары в `ꙮ` и `Stop Gate` сработал штатно.  
- Оценка правдоподобности: 90%.  

## H-4-2. Отсутствие пост-проверки `Stop Gate` по `DOC-4`

- Суть: `Stop Gate` опирается на `prepared` из [completion.py](https://example.com/harness/completion.py#L321) без повторного анализа контента.  
- Доводы за: `Stop Gate` доверяет чеку `answer-prepare`.  
- Доводы против: дублирование проверки в `Stop Gate` избыточно при исправлении `answer-prepare`.  
- Оценка правдоподобности: 35%.  

# 3. Источник проблемы (§4)

Владельцем контура Журнала `ꙮ` является Harness (`dmitry-ai/harness`).  

# 4. Устранение проблемы (§4)

## M-4-1. Подключить `analysis_gate_issues` прямо в `ResponseEvidenceAuditor`

- Суть: запускать валидацию таблиц и `/df-analysis` до записи в `ꙮ` на каждом вызове `answer-check` и `answer-prepare`.  
- Доводы за: не пропускает невалидные отчёты ни в чат, ни в `ꙮ`.  
- Доводы против: требует поддержания актуальных фикстур в тестах.  
- Оценка: 96%.  

## M-4-2. Предупреждение без блокировки записи в `ꙮ`

- Суть: писать предупреждение в лог без отклонения `answer-prepare`.  
- Доводы за: не блокирует публикацию.  
- Доводы против: позволяет нарушениям `DOC-4` попадать в Журнал `ꙮ`.  
- Оценка: 15%.  
"""
_VALID_GENERAL_EN = """# Analysis

## H-1. Cache staleness

- Essence: stale entries persist in [cache.py](https://example.com/cache#ttl).  
- Arguments for: TTL is never checked on read.  
- Arguments against: cold starts still reproduce the delay.  
- Plausibility: 70%.  

## H-2. Lock contention

- Essence: concurrent writes serialize on [storage.py](https://example.com/storage#lock).  
- Arguments for: observed lock wait spikes under parallel tests.  
- Arguments against: single-threaded repro still lags by 200 ms.  
- Plausibility: 65%.  

## M-1. Per-key sharded locks

- Essence: shard locks by normalized entity key.  
- Arguments for: removes cross-entity blocking permanently.  
- Arguments against: requires migrating existing lock directory cleanup.  
- Score: 90%.  

## M-2. Raise lock timeout

- Essence: increase retry timeout to 60 seconds.  
- Arguments for: trivial one-line change.  
- Arguments against: masks the root cause without removing contention.  
- Score: 20%.  
"""
# 2026-11-24
# "Enforce Markdown table ban and /df-analysis structural validation across response gates":
# https://github.com/dmitry-ai/harness/issues/181
class DfAnalysisGatesTests(unittest.TestCase):
	def test_analysis_check_cli_validates_problem_and_rejects_broken_input(self) -> None:
		with tempfile.TemporaryDirectory() as tmp:
			root = Path(tmp).resolve()
			good_file = root / 'good.md'
			bad_file = root / 'bad.md'
			good_file.write_text(_VALID_PROBLEM_RU, encoding='utf-8')
			bad_file.write_text('# 0. Мета-данные проблемы\n\n```json\n{"Time": "2026-11-24 01:00:00 UTC+3"}\n```\n\n# 1. Описание проблемы\nБез цитат.\n', encoding='utf-8')
			cli = str(SCRIPT_DIR / 'harness.py')
			ok_p = subprocess.run([sys.executable, cli, 'analysis-check', str(root), '--response-file', str(good_file), '--mode', 'problem'], capture_output=True, text=True, encoding='utf-8', check=False)
			self.assertEqual(0, ok_p.returncode, ok_p.stderr or ok_p.stdout)
			self.assertTrue(json.loads(ok_p.stdout)['valid'])
			bad_p = subprocess.run([sys.executable, cli, 'analysis-check', str(root), '--response-file', str(bad_file), '--mode', 'problem'], capture_output=True, text=True, encoding='utf-8', check=False)
			self.assertEqual(2, bad_p.returncode)
			self.assertFalse(json.loads(bad_p.stdout)['valid'])
	def test_documentation_link_requires_anchor_when_observation_has_anchors(self) -> None:
		with tempfile.TemporaryDirectory() as tmp:
			proj = Path(tmp).resolve()
			doc_url = 'https://docs.python.org/3/library/pathlib.html'
			blog_url = 'https://example.com/news/release-notes'
			doc_html = b'<html><head><title>pathlib docs</title></head><body><h1 id="pathlib-object-oriented-filesystem-paths">pathlib</h1><h2 id="basic-use">Basic use</h2><p>Pure paths provide computational operations.</p></body></html>'
			blog_html = b'<html><head><title>Release Notes</title></head><body><h1 id="top">Release Notes</h1><p>Version 2 shipped.</p></body></html>'
			research.collect_http(proj, doc_url, fetcher=lambda u, h, t: research.Response(u, 200, 'text/html', doc_html), browser='never')
			research.collect_http(proj, blog_url, fetcher=lambda u, h, t: research.Response(u, 200, 'text/html', blog_html), browser='never')
			no_anchor = f'See [pathlib]({doc_url}).'
			errs_no_anchor = ResponseEvidenceAuditor(proj, no_anchor, []).validate()
			self.assertTrue(any('LINK-2' in e and '#anchor' in e for e in errs_no_anchor), errs_no_anchor)
			with_anchor = f'See [pathlib]({doc_url}#basic-use).'
			self.assertEqual([], ResponseEvidenceAuditor(proj, with_anchor, []).validate())
			with_exc = f'See [pathlib]({doc_url}) (`anchor_exception`: section Basic use).'
			self.assertEqual([], ResponseEvidenceAuditor(proj, with_exc, []).validate())
			non_doc = f'See [Release Notes]({blog_url}).'
			self.assertEqual([], ResponseEvidenceAuditor(proj, non_doc, []).validate())
	def test_general_df_analysis_requires_multiple_hypotheses_methods_and_template_fields(self) -> None:
		reqs = [{'text': '/df-analysis Analyze build latency'}]
		self.assertEqual([], df_analysis.validate_df_analysis(_VALID_GENERAL_EN, requests=reqs, mode='auto'))
		single_h = '## H-1. Only cause\n- Essence: see [a](https://example.com/a#s).\n- Arguments for: fast.\n- Arguments against: weak.\n- Plausibility: 80%.\n'
		errs_single = df_analysis.validate_df_analysis(single_h, requests=reqs, mode='auto')
		self.assertTrue(any('at least 2' in e for e in errs_single), errs_single)
		missing_fields = '## H-1. First\n- Essence: no link here.\n- Arguments for: yes.\n\n## H-2. Second\n- Essence: see [b](https://example.com/b#s).\n- Arguments for: yes.\n- Arguments against: no.\n- Plausibility: 40%.\n'
		errs_fields = df_analysis.validate_df_analysis(missing_fields, requests=reqs, mode='auto')
		self.assertTrue(any('link' in e.lower() for e in errs_fields), errs_fields)
		self.assertTrue(any('against' in e.lower() for e in errs_fields), errs_fields)
		self.assertTrue(any('%' in e for e in errs_fields), errs_fields)
		self.assertEqual([], df_analysis.validate_df_analysis('Задача выполнена успешно.  \n', requests=[{'text': 'Fix typo'}], mode='auto'))
	def test_markdown_table_blocked_across_doc4_hook_linter_and_grounding(self) -> None:
		with tempfile.TemporaryDirectory() as tmp:
			proj = Path(tmp).resolve()
			table_doc = '# Summary\n\n| Col A | Col B |\n| --- | --- |\n| 1 | 2 |\n'
			fenced_table = '# Summary\n\n```markdown\n| Col A | Col B |\n| --- | --- |\n| 1 | 2 |\n```\n'
			prose_pipe = 'Options `auto|always|never` and plain text a | b stay allowed.  \n'
			hook_errs = check_markdown_slop.markdown_slop_issues(table_doc)
			self.assertTrue(any('Markdown table' in e for e in hook_errs), hook_errs)
			self.assertEqual([], check_markdown_slop.markdown_slop_issues(fenced_table))
			self.assertEqual([], check_markdown_slop.markdown_slop_issues(prose_pipe))
			lint_errs = IssueMarkdownLinter().lint(table_doc, is_title=False)
			self.assertTrue(any('MARKDOWN_TABLE_FORBIDDEN' == e['code'] for e in lint_errs), lint_errs)
			self.assertEqual([], IssueMarkdownLinter().lint(fenced_table, is_title=False))
			aud_errs = ResponseEvidenceAuditor(proj, table_doc, []).validate()
			self.assertTrue(any('Markdown table' in e for e in aud_errs), aud_errs)
			chk = completion.check_answer(proj, table_doc)
			self.assertFalse(chk['valid'])
	def test_problem_analysis_auto_triggers_and_enforces_all_five_sections(self) -> None:
		self.assertEqual([], df_analysis.validate_df_analysis(_VALID_PROBLEM_RU, mode='auto'))
		no_issue_key = _VALID_PROBLEM_RU.replace('\t"Issue": "https://github.com/dmitry-ai/harness/issues/181",\n', '')
		errs_no_issue = df_analysis.validate_df_analysis(no_issue_key, mode='auto')
		self.assertTrue(any('"Issue"' in e for e in errs_no_issue), errs_no_issue)
		null_issue = _VALID_PROBLEM_RU.replace('"https://github.com/dmitry-ai/harness/issues/181"', 'null')
		self.assertEqual([], df_analysis.validate_df_analysis(null_issue, mode='auto'))
		no_verbatim = _VALID_PROBLEM_RU.replace('«exit code 0, issues: []»', 'все прошло тихо')
		errs_no_quote = df_analysis.validate_df_analysis(no_verbatim, mode='auto')
		self.assertTrue(any('verbatim' in e.lower() for e in errs_no_quote), errs_no_quote)
		missing_s3 = _VALID_PROBLEM_RU.replace('# 3. Источник проблемы\n\nИсточником проблемы является базовый проект более высокого уровня — Harness (`dmitry-ai/harness`), а не клиентский workspace, где проявился сбой.  \n\n', '')
		errs_s3 = df_analysis.validate_df_analysis(missing_s3, mode='auto')
		self.assertTrue(any('# 3' in e for e in errs_s3), errs_s3)
if '__main__' == __name__:
	unittest.main()
