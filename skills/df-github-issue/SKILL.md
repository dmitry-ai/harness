---
name: df-github-issue
description: "Создаёт, редактирует, комментирует, закрывает и проверяет GitHub issues через файловый UTF-8 вход и API read-back без искажений PowerShell; используй при /df-github-issue и любой работе с GitHub issues."
---
# Работа с GitHub Issues без синтаксических искажений

Общий инструмент: `C:/work/upwork/code/AI/primary/result/.agents/scripts/df_github_issue.py`.  
Любое создание, редактирование, комментирование, закрытие и проверка GitHub issues в Windows PowerShell выполняются только через этот инструмент и UTF-8 файл без BOM.  

## Запрещённые шаблоны вызова `gh` в PowerShell

Никогда не передавай Markdown-текст описания или комментария через аргументы командной строки или неконфигурированный конвейер PowerShell:  
- Запрещено `--body "..."`, `-b "..."`, `--body @"..."@`, `--comment "..."`: внутри двойных кавычек PowerShell символ `` ` `` является escape-префиксом, поэтому `` `0 `` превращается в `NUL` (`0x00`) и обрывает описание на первом нулевом байте в `CreateProcessW`, `` `a ``/`` `b ``/`` `f ``/`` `t ``/`` `v `` превращаются в управляющие ASCII-символы (`0x07`, `0x08`, `0x0C`, `0x09`, `0x0B`), все одиночные обратные кавычки `` ` `` удаляются, bash-экранирование `` \`код\` `` превращается в `\код\`, а переменные `$this` / `$var` раскрываются в пустую строку.  
- Запрещено передавать переменную `--body $body` нативному процессу `gh.exe`: в Windows PowerShell 5.1 (`Legacy` argument passing) внутренние двойные кавычки `"` не экранируются при сборке командной строки, поэтому `CommandLineToArgvW` удаляет кавычки из XML/HTML-атрибутов (`<argument name="session">` превращается в `<argument name=session>`) или ломает разбор аргументов на пробелах.  
- Запрещено передавать `@'...'@ | gh issue create --body-file -` или `@'...'@ | python -` без предварительной установки UTF-8 без BOM: по умолчанию `$OutputEncoding` в Windows PowerShell 5.1 равен `US-ASCII`, из-за чего тире `–`/`—`, кавычки `«»` и `§` заменяются на `?`, а при UTF-8 с преамбулой в начало тела записывается `U+FEFF` (`UTF-8 BOM`), ломающий заголовок первой строки (`\ufeff### Problem`).  

## Обязательный порядок работы

1. Запиши полный Markdown-текст описания или комментария в UTF-8 файл без BOM внутри `ꘖ/data/scratch/` (или временного scratch-каталога беседы) штатным инструментом `write_file`.  
2. Выполни нужную операцию через `df_github_issue.py`:  
   - Предварительная проверка Markdown-файла без сетевых вызовов:  
     `python "C:/work/upwork/code/AI/primary/result/.agents/scripts/df_github_issue.py" lint --title "<заголовок>" --body-file "<путь/к/body.md>"`  
   - Создание issue с автоматической проверкой синтаксиса до отправки, передачей JSON в `gh api` по UTF-8 stdin и побайтовой сверкой прочитанного с GitHub результата:  
     `python "C:/work/upwork/code/AI/primary/result/.agents/scripts/df_github_issue.py" create --repo <owner/repo> --title "<заголовок>" --body-file "<путь/к/body.md>" [--label "<метки>"] --consume-input`  
   - Редактирование существующего issue с полной сверкой:  
     `python "C:/work/upwork/code/AI/primary/result/.agents/scripts/df_github_issue.py" edit --repo <owner/repo> --issue <N> --body-file "<путь/к/body.md>" [--title "<новый заголовок>"] --consume-input`  
   - Добавление или исправление комментария к issue:  
     `python "C:/work/upwork/code/AI/primary/result/.agents/scripts/df_github_issue.py" comment --repo <owner/repo> (--issue <N> | --comment-id <ID>) --body-file "<путь/к/comment.md>" --consume-input`  
   - Закрытие issue с проверенным комментарием:  
     `python "C:/work/upwork/code/AI/primary/result/.agents/scripts/df_github_issue.py" close --repo <owner/repo> --issue <N> [--reason completed|not_planned] [--comment-file "<путь/к/comment.md>"] --consume-input`  
   - Аудит всех открытых и закрытых issues и комментариев репозитория на синтаксические/кодировочные повреждения:  
     `python "C:/work/upwork/code/AI/primary/result/.agents/scripts/df_github_issue.py" audit-repo --repo <owner/repo> --include-comments`  
3. Если заголовок содержит кавычки `"`, `$` или обратные кавычки `` ` ``, запиши заголовок в отдельный UTF-8 файл и передай `--title-file "<путь/к/title.txt>"`.  
4. Считай операцию успешной только при коде возврата `0` и `"verified": true` в JSON-ответе инструмента.  
