# 2026-11-28 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from pathlib import Path
from git_fixture_cache import clone_template_git_repo
import json
# 2026-11-28 "Implement hierarchical mixed-turn DOC-5 parser and problem-issue specification": https://github.com/dmitry-ai/harness/issues/428
# @used-by :mod:`test_problem_report_governance`
class ProblemReportFixtureBuilder:
	# @used-by :meth:`test_problem_metadata.ProblemMetadataTests.test_build_problem_metadata_and_cli_reject_unverified_closed_child_and_foreign_issues()`
	# @used-by :meth:`test_problem_report_governance.ProblemReportGovernanceTests.test_mixed_turn_hierarchical_schema_accepts_valid_and_rejects_flat_or_missing_sections()`
	# @used-by :meth:`test_problem_report_governance.ProblemReportGovernanceTests.test_problem_issue_specification_rejects_duplicate_closed_child_unverified_null_and_foreign_issues()`
	# @used-by :meth:`test_problem_report_governance.ProblemReportGovernanceTests.test_standalone_four_track_accepts_nested_and_rejects_flat_h1_and_allows_user_requested_open_issue()`
	def __init__(self, base: Path, *, repo: str='dmitry-ai/harness', cid: str='11111111-2222-4333-8444-555555555555', turn_key: str='tk-active-01') -> None:
		self.__base = Path(base).resolve()
		self.__repo = repo
		self.__cid = cid
		self.__turn_key = turn_key
		self.__proj = self.__base / 'proj'
		self.__ev_dir = self.__proj / '\ua616/KB/Evidence/GitHub' / repo.replace('/', '__')
		self.__turns_dir = self.__proj / '\ua616/data/turns'
		self.__issues: dict[int, dict] = {}
		self.__issue_actions: list[dict] = []
		self.__with_git = False
	# @used-by :meth:`ProblemReportFixtureBuilder.add_issue()`
	def __format_issue_body(self, num: int, body_text: str, *, owner_cid: str | None, owner_turn_key: str | None, parent_number: int | None, with_meta: bool) -> str:
		prefix = ''
		if with_meta:
			meta = {'Time': '2026-11-28 02:00:00 UTC+3', 'Issue': f'https://github.com/{self.__repo}/issues/{num}', 'Project': {'Name': 'Harness', 'Path': self.__proj.as_posix()}, 'Trace': {'Conversation ID': owner_cid or self.__cid, 'Turn': {'Key': owner_turn_key or self.__turn_key}}}
			prefix = '```json\n' + json.dumps(meta, ensure_ascii=False, indent='\t') + '\n```\n\n'
		parent_line = f'Parent: [Issue #{parent_number}](https://github.com/{self.__repo}/issues/{parent_number})  \n\n' if None is not parent_number else ''
		return f'{prefix}{parent_line}{body_text}\n'
	# @used-by :meth:`ProblemReportFixtureBuilder.build_workspace()`
	def __seed_git_repo(self) -> None:
		code_dir = self.__proj / '\u2c0f/\u227b/\u2655/\u26ef'
		clone_template_git_repo(code_dir, remote_url=f'https://github.com/{self.__repo}.git')
	# @used-by :meth:`test_problem_metadata.ProblemMetadataTests.test_build_problem_metadata_and_cli_reject_unverified_closed_child_and_foreign_issues()`
	# @used-by :meth:`test_problem_report_governance.ProblemReportGovernanceTests.test_mixed_turn_hierarchical_schema_accepts_valid_and_rejects_flat_or_missing_sections()`
	# @used-by :meth:`test_problem_report_governance.ProblemReportGovernanceTests.test_problem_issue_specification_rejects_duplicate_closed_child_unverified_null_and_foreign_issues()`
	# @used-by :meth:`test_problem_report_governance.ProblemReportGovernanceTests.test_standalone_four_track_accepts_nested_and_rejects_flat_h1_and_allows_user_requested_open_issue()`
	def add_issue(self, num: int, *, state: str='open', parent_number: int | None=None, owner_cid: str | None=None, owner_turn_key: str | None=None, title: str | None=None, body: str='Observed defect details.', action: str | None='create', step: int=4, with_meta: bool=True) -> ProblemReportFixtureBuilder:
		url = f'https://github.com/{self.__repo}/issues/{num}'
		rec = {'url': url, 'html_url': url, 'repo': self.__repo, 'kind': 'issue', 'number': num, 'issue_number': num, 'id': 900000 + num, 'title': title or f'Defect {num}', 'state': state, 'state_reason': 'completed' if 'closed' == state else None, 'body': self.__format_issue_body(num, body, owner_cid=owner_cid, owner_turn_key=owner_turn_key, parent_number=parent_number, with_meta=with_meta)}
		if None is not parent_number:
			rec.update(parent_number=parent_number, parent_url=f'https://github.com/{self.__repo}/issues/{parent_number}')
		self.__issues[num] = rec
		if None is not action:
			self.__issue_actions.append({'action': action, 'repo': self.__repo, 'number': num, 'url': url, 'state': state, 'parent_number': parent_number, 'step': step})
		return self
	# @used-by :meth:`test_problem_metadata.ProblemMetadataTests.test_build_problem_metadata_and_cli_reject_unverified_closed_child_and_foreign_issues()`
	# @used-by :meth:`test_problem_report_governance.ProblemReportGovernanceTests.test_mixed_turn_hierarchical_schema_accepts_valid_and_rejects_flat_or_missing_sections()`
	# @used-by :meth:`test_problem_report_governance.ProblemReportGovernanceTests.test_problem_issue_specification_rejects_duplicate_closed_child_unverified_null_and_foreign_issues()`
	# @used-by :meth:`test_problem_report_governance.ProblemReportGovernanceTests.test_standalone_four_track_accepts_nested_and_rejects_flat_h1_and_allows_user_requested_open_issue()`
	def build_workspace(self, *, requests: list[dict] | None=None, touched_files: list[str] | None=None, hook_crashes: list[dict] | None=None) -> dict:
		self.__ev_dir.mkdir(parents=True, exist_ok=True)
		self.__turns_dir.mkdir(parents=True, exist_ok=True)
		(self.__proj / '\ua66e').mkdir(parents=True, exist_ok=True)
		(self.__proj / '\ua616/paths.json').write_text('{"version": 1}\n', encoding='utf-8')
		if self.__with_git:
			self.__seed_git_repo()
		for num, rec in self.__issues.items():
			(self.__ev_dir / f'issue-{num}.json').write_text(json.dumps(rec, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
		reqs = requests if None is not requests else [{'id': f'{self.__cid}-0', 'text': 'Реализуй задачу и проверь результат.'}]
		gh_map = {act['url']: {'repo': act['repo'], 'number': act['number'], 'url': act['url'], 'state': act['state'], 'last_action': act['action'], 'actions': [act['action']], 'recorded_conversation_id': self.__cid, **({'parent_number': act['parent_number']} if None is not act.get('parent_number') else {})} for act in self.__issue_actions}
		turn_state = {'key': self.__turn_key, 'conversation_id': self.__cid, 'platform': 'antigravity', 'status': 'open', 'requests': reqs, 'github_issues': gh_map}
		state_file = self.__turns_dir / f'{self.__turn_key}.json'
		state_file.write_text(json.dumps(turn_state, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
		assert state_file.is_file(), f'Turn state missing: {state_file}'
		turn = {'turn_id': f'ag-{self.__cid}-0', 'start_step': 0, 'requests': reqs, 'owned': True, 'completed': False, 'aborted': False, 'touched_files': list(touched_files or ()), 'issue_actions': list(self.__issue_actions), 'exec5_violations': [], 'http_fetch_violations': [], 'issue_first_events': [], 'tdd_events': [], 'compaction': {}, 'delegation': {}, **({'hook_crashes': list(hook_crashes)} if None is not hook_crashes else {})}
		return {'root': self.__proj, 'repo': self.__repo, 'cid': self.__cid, 'turn_key': self.__turn_key, 'turn': turn, 'turn_state': turn_state, 'requests': reqs}
	# @used-by :meth:`test_problem_report_governance.ProblemReportGovernanceTests.test_mixed_turn_hierarchical_schema_accepts_valid_and_rejects_flat_or_missing_sections()`
	# @used-by :meth:`test_problem_report_governance.ProblemReportGovernanceTests.test_problem_issue_specification_rejects_duplicate_closed_child_unverified_null_and_foreign_issues()`
	# @used-by :meth:`test_problem_report_governance.ProblemReportGovernanceTests.test_standalone_four_track_accepts_nested_and_rejects_flat_h1_and_allows_user_requested_open_issue()`
	def mixed_problem_markdown(self, problem_specs: list[dict], *, src_link: str='https://example.com/log#line1', part1_title: str='# \U0001d678. Что сделано', part2_title: str='# \U0001d678\U0001d678. Новые проблемы', extra_h1: str='') -> str:
		lines = [part1_title, '', '## 1. Реализация основной задачи', '', 'Основная задача выполнена и подтверждена тестами.  ', '']
		if extra_h1:
			lines.extend([extra_h1, '', 'Лишний заголовок верхнего уровня.  ', ''])
		lines.extend([part2_title, ''])
		for idx, spec in enumerate(problem_specs, 1):
			iss_raw = spec.get('issue')
			iss = 'null' if None is iss_raw else f'"{iss_raw}"'
			title = spec.get('title') or f'Проблема {idx}'
			desc = spec.get('desc') or 'Сбой воспроизведён дословно: «exit status 1, timeout reached».'
			m1_extra = spec.get('m1_extra') or ''
			lines.extend([
				f'## {idx}. {title}', '',
				f'### {idx}.1. Метаданные', '',
				'```json', '{', '\t"Time": "2026-11-28 02:10:00 UTC+3",', f'\t"Issue": {iss},', f'\t"Project": {{"Name": "Harness", "Path": "{self.__proj.as_posix()}"}}', '}', '```', '',
				f'### {idx}.2. Описание', '', f'{desc}  ', '',
				f'### {idx}.3. Причины', '',
				f'#### H-{idx}-1. Основная причина', f'- Суть: Дефект подтверждён в [источнике](<{src_link}>).  ', '- Доводы за: Воспроизведено дословно по логам.  ', '- Доводы против: Вторичные факторы среды минимальны.  ', '- Оценка правдоподобности: 90% по прямому воспроизведению.  ', '',
				f'#### H-{idx}-2. Альтернативная гипотеза', f'- Суть: Внешнее вмешательство по [источнике](<{src_link}>).  ', '- Доводы за: Симптом похож на сбой среды.  ', '- Доводы против: Изолированный запуск повторяет ошибку.  ', '- Оценка правдоподобности: 10% по контрольному запуску.  ', '',
				'Архитектурный источник проблемы: базовый проект Harness (`dmitry-ai/harness`).  ', '',
				f'### {idx}.4. Виновник', '', 'Дефект внесён в базовом модуле Harness (`dmitry-ai/harness`); действующие тесты и шлюз `answer-check` пропустили его, обхода Журнала `ꙮ` не зафиксировано.  ', '',
				f'### {idx}.5. Способы устранения', '',
				f'#### M-{idx}-1. Системное исправление', f'{m1_extra}- Суть: Внедрить детерминированную проверку в базовом модуле.  ', '- Доводы за: Устраняет класс ошибок навсегда.  ', '- Доводы против: Требует регрессионных тестов.  ', '- Оценка: 95% по системной надёжности.  ', '',
				f'#### M-{idx}-2. Ручной контроль', '- Суть: Проверять вручную перед завершением хода.  ', '- Доводы за: Не требует кода.  ', '- Доводы против: Не защищает от повторения.  ', '- Оценка: 20% по системной надёжности.  ', '',
				f'### {idx}.6. Рекомендуемый план устранения', '', f'Реализовать `M-{idx}-1` отдельной задачей по открытому родительскому issue и подтвердить тестами.  ', '',
			])
		return '\n'.join(lines)
	# @used-by :meth:`test_problem_report_governance.ProblemReportGovernanceTests.test_standalone_four_track_accepts_nested_and_rejects_flat_h1_and_allows_user_requested_open_issue()`
	def standalone_four_track_markdown(self, issue_urls: tuple[str | None, str | None, str | None, str | None], *, src_link: str='https://example.com/log#line1', flat_h1: bool=False) -> str:
		sec_prefix = '#' if flat_h1 else '##'
		item_prefix = '##' if flat_h1 else '###'
		specs = (
			('Разбор проблемы §1: Основной сбой хука', '1', issue_urls[0], 'Хук завершился с дословной ошибкой: «JSON hook failed: exit status 1».'),
			('Разбор проблемы §2: Виновник и происхождение', '2', issue_urls[1], 'Агент A6 применил правку и проигнорировал «exit status 1».'),
			('Разбор проблемы §3: Пропуск тестами и проверками', '3', issue_urls[2], 'Прогон выдал «Ran 1180 tests ... OK», но тесты не проверили инвариант.'),
			('Разбор проблемы §4: Целостность Журнала ꙮ и отчётности', '4', issue_urls[3], 'Проведён аудит Журнала `ꙮ` (`FILE-3`): «exit status 1» не вызвал обход Журнала.'),
		)
		parts: list[str] = []
		for head, tag, iurl, desc in specs:
			iss = 'null' if None is iurl else f'"{iurl}"'
			parts.append(
				f'# {head}\n\n{sec_prefix} 0. Метаданные проблемы ({tag})\n\n```json\n{{\n\t"Time": "2026-11-28 02:10:00 UTC+3",\n\t"Issue": {iss},\n\t"Project": {{"Name": "Harness", "Path": "{self.__proj.as_posix()}"}}\n}}\n```\n\n'
				f'{sec_prefix} 1. Описание проблемы ({tag})\n\n{desc}  \n\n'
				f'{sec_prefix} 2. Анализ первопричин ({tag})\n\n'
				f'{item_prefix} H-{tag}-1. Основная причина\n- Суть: Подтверждено в [источнике](<{src_link}>).  \n- Доводы за: Воспроизведено дословно.  \n- Доводы против: Вторичные факторы малы.  \n- Оценка правдоподобности: 92% по прямому воспроизведению.  \n\n'
				f'{item_prefix} H-{tag}-2. Альтернативная версия\n- Суть: Сбой среды по [источнике](<{src_link}>).  \n- Доводы за: Внешний симптом схож.  \n- Доводы против: Опровергнуто локальным прогоном.  \n- Оценка правдоподобности: 10% по контрольному прогону.  \n\n'
				f'{sec_prefix} 3. Атрибуция исходного проекта ({tag})\n\nАрхитектурный владелец — базовый проект Harness (`dmitry-ai/harness`).  \n\n'
				f'{sec_prefix} 4. Постоянные системные решения ({tag})\n\n'
				f'{item_prefix} M-{tag}-1. Системное исправление\n- Суть: Добавить детерминированную проверку в базовый модуль.  \n- Доводы за: Устраняет первопричину.  \n- Доводы против: Требует новых тестов.  \n- Оценка: 95% по системной надёжности.  \n\n'
				f'{item_prefix} M-{tag}-2. Ручной обход\n- Суть: Проверять вручную.  \n- Доводы за: Нет правок кода.  \n- Доводы против: Ненадёжно.  \n- Оценка: 15% по системной надёжности.  \n'
			)
		return '\n---\n\n'.join(parts)
	# @used-by :meth:`test_problem_metadata.ProblemMetadataTests.test_build_problem_metadata_and_cli_reject_unverified_closed_child_and_foreign_issues()`
	# @used-by :meth:`test_problem_report_governance.ProblemReportGovernanceTests.test_mixed_turn_hierarchical_schema_accepts_valid_and_rejects_flat_or_missing_sections()`
	# @used-by :meth:`test_problem_report_governance.ProblemReportGovernanceTests.test_problem_issue_specification_rejects_duplicate_closed_child_unverified_null_and_foreign_issues()`
	# @used-by :meth:`test_problem_report_governance.ProblemReportGovernanceTests.test_standalone_four_track_accepts_nested_and_rejects_flat_h1_and_allows_user_requested_open_issue()`
	def with_git_repo(self) -> ProblemReportFixtureBuilder:
		self.__with_git = True
		return self
