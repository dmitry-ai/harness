---
name: upwork-init
description: >-
  Быстрая детерминированная инициализация папки нового проекта Upwork, заполнение KB/Project.md,
  портирование в ꘖ/KB/, сборка ꙮ/0/Context.md и выполнение первичного анализа по URL вакансии
  (алиас слэш-команды /analyze-project).
---

# Инициализация и первичный анализ проекта Upwork (`/upwork-init`)

При вызове `/upwork-init <url>` следуй полной инструкции навыка [`analyze-project`](../analyze-project/SKILL.md):
1. Выполни `python "C:\work\upwork\code\AI\primary\result\.agents\scripts\upwork_project.py" inspect "<url>"` и изучи вложения.
2. Установи домен клиента или тему проекта и запусти `python "C:\work\upwork\code\AI\primary\result\.agents\scripts\upwork_project.py" init "<url>" --domain "<domain_or_topic>"`.
3. Обогати `ꘖ/KB/`, подготовь первичный анализ по вопросам §26.1 и §26.2 в формате гипотез (§27), запиши шаг 1 в `ꙮ/1 - Анализ/`, проверь `#anchor`, пересобери `ꙮ/0/Context.md` и очисти временные файлы в `ꘖ/data/`.
