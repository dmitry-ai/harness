# Команды и служебные данные

Все команды ниже выполняет агент. `<scripts>` — `AI/primary/result/.agents/scripts`, `<root>` — точный корень поручения.
`df_text.py`, `df_article.py` и `df_proposal.py` импортируют один CLI; два последних выбирают формат по умолчанию.
UTF-8 JSON/Markdown можно передать через `-` из stdin. Выход `0` — соответствующая проверка прошла, `1` — содержательные замечания, `2` — неверный вход или отказ операции.

## Диагностика и формат

```text
python <scripts>/df_text.py diagnose <root> --platform codex --profile C1
python <scripts>/df_article.py lint <file> --kind article --json
python <scripts>/df_proposal.py lint <file> --profile <profile.json>
python <scripts>/df_text.py lint <letter> --kind letter
python <scripts>/df_article.py lint <file> --network --project <root>
python <scripts>/df_article.py source <file> -o <separate-source>
python <scripts>/df_article.py render <source> --previous <file> --diff
python <scripts>/df_proposal.py render <source> -o <separate-candidate>
python <scripts>/df_proposal.py fields --fields <fields.json> --limits <limits.json>
```

Профиль proposal: `numbering: nested|flat`, `voice: technical|offer`; дополнительные параметры не заменяют требования текущего задания.
`fields.json` сопоставляет точные названия полей с отправляемым текстом, `limits.json` — с подтверждёнными лимитами каждого поля. По умолчанию длина считается как UTF-16 в браузере; `--count-mode unicode` нужен только при подтверждённом другом счётчике.
Статья допускает профиль `link_style: markdown` для явной проверки голых URL.
Профиль `formatted` проверяет совпадение домена, пути, query и fragment в видимой подписи и адресе перехода; технический URL в подписи не создаёт самостоятельных числовых тезисов. [Контракт ссылок](sources.md#подписи-ссылок-и-числа).
Внешняя ссылка определяется по явно названному документу: `11 CCR §7025`, `RFC 9110 §15.4.3`, `ISO 27001:2022 §5.1`. Общий разбор поддерживает RFC/ISO/IEC/IEEE/EN и числовые CCR/CFR/USC; внутренние ссылки разрешаются по карте пунктов.
Рендер сохраняет номер внешнего параграфа, убирает пробел после `§` в авторской прозе и фиксирует коррекцию в `external_references_normalized`; код и буквальные цитаты сохраняются.
`source/render -o` создают отдельный кандидат. Для существующего выходного файла необходим его текущий `--expected-sha256`; предыдущие байты сохраняются в истории. Эти команды не перезаписывают зарегистрированный целевой или защищённый документ.

## Контракт правки

`begin <root> --spec <operation.json>` (синоним `guard`) сохраняет реальные байты baseline; JSON:

```json
{
  "kind": "proposal",
  "target": "result/EN/draft.md",
  "mode": "propose",
  "changes": "prose",
  "goal": "Explain the established tracking defect and the applicable repair.",
  "requests": ["Дословный текущий запрос пользователя"],
  "allow_sections": [],
  "protected": ["result/EN/draft.working.md"]
}
```

`kind`: article/proposal/letter; `mode`: edit/propose/inspect; `changes`: prose/links/renumber.
Пустой `allow_sections` означает весь целевой документ; непустой — точные пункты вместе с их детьми или включённый диапазон `I.16-I.20`/`2-4`.
Ограниченная правка проверяет также заголовки, группировки, якоря и неизменяемые переводы строк.
`protected` содержит только явно защищаемые документы; их отсутствие тоже фиксируется. Не объявляй защищённым целевой файл.
Для согласования внешней правки уже зарегистрированного документа укажи `reconcile_sha256` его фактически прочитанной текущей версии; это сбрасывает прежний допуск, не откатывает авторские байты.
`shell` задаёт явный Bash для этой операции; `profile` — профиль формата.

## KB и карта абзацев

```text
python <scripts>/df_text.py claims-save <root> --candidate <registry.json>
python <scripts>/df_text.py claims-save <root> --candidate <revision.json> --expected-sha256 <current-registry-hash>
python <scripts>/df_text.py sources <root> --claim <claim-id> --claim <other-id>
python <scripts>/df_text.py source-check <root> --candidate <candidate> --spec <source.json>
```

Реестр по умолчанию — `ꘖ/KB/TextClaims.json`. `--registry` выбирает другой явный JSON в агентской KB.
Схема3, типы тезисов, происхождение и локаторы — в [существующем контракте](../../skills/upwork-init/references/evidence-contract.md).
Самостоятельному тексту достаточно `{"schema_version":3,"facts":[…]}`; гипотезы и рекомендации располагаются в предусмотренных контрактом разделах, если они нужны.
Требуемые ссылки/цитаты получают наблюдения через общий сборщик `upwork_project.py collect`, `capture-dom`, зарегистрированный intake либо контракт эксперимента. Нельзя заполнять observation выдуманным отчётом.
`sources` проверяет ровно замыкание перечисленных тезисов; неверная цитата, хеш или локатор дают отказ. Семантическую применимость проверяет A.A.
Для внешних URL кандидата `source-check` сохраняет отдельные обязательные квитанции; их пути перечисляются в `manifest.source_checks`. Схема спецификации, срок действия, DOM, неудачные запросы и замена источника описаны в [контракте источников](sources.md#наблюдение-и-квитанция).

Карта кандидата имеет схему1:

```json
{
  "schema_version": 1,
  "registry": "ꘖ/KB/TextClaims.json",
  "blocks": [{
    "key": "form-observation",
    "section": "1",
    "text_sha256": "SHA256 точных байтов text этого блока",
    "role": "observation",
    "goal_basis": "Какой вопрос читателя разрешает этот пункт",
    "new_content": "Какое новое содержание он добавляет",
    "claim_ids": ["F-FORM-1"]
  }]
}
```

`text_claims.blocks(candidate, kind)` возвращает точные `section`, `text`, `prose`, `line` для расчёта хешей; статья не дублирует дочерние доказательства в группирующем родителе, proposal включает продолжения пункта и отдельный preface.
Для письма блоки — абзацы с номерами `1`, `2` и т.д. Ключ сохраняется при перенумерации и редакции блока; содержание, хеш и роль перепроверяются.
Роли: observation/documented/inference/recommendation/context/nonfactual.
У `nonfactual` нужны пустой `claim_ids` и конкретный `nonfactual_basis`; это допустимо для предложения услуги или приветствия, а не для утверждений о системе.
Ограниченный тезис требует `qualification`, дословно присутствующего в тексте; повторное введение факта — предметного `reuse_basis`, который оценивает рецензент.
`commands` сопоставляет строку ограждения с явными `exit`, `stdout`, при необходимости `stderr`; отсутствие контракта означает ожидаемый код0 и сравнение с цитатой в документе.

## Проверка и рецензия

```text
python <scripts>/df_text.py check <root> --operation <ID> --candidate <candidate> --manifest <map.json> --run-replay
python <scripts>/df_text.py review-prepare <root> --check <check-path> --parent <native-parent-id> --spec <risk.json>
python <scripts>/df_text.py review-input <root> --package <package-path>
python <scripts>/upwork_project.py native-review-proof <root> --platform codex --reviewer <native-child-id> --parent <native-parent-id>
python <scripts>/df_text.py review-record <root> --report <authored-report> --parent <native-parent-id> --reviewer <native-child-id> --native-evidence <proof-path>
python <scripts>/df_text.py review-status <root> --check <check-path>
python <scripts>/df_text.py apply <root> --check <check-path>
```

Пути check/package/proof относительны корню и берутся из реальных результатов команд.
`risk.json`: `risk: routine|significant`, предметное `basis`, `task_flags` текущего поручения; фактический существенный тезис повышает риск независимо от подписи routine.
Нативная рецензия запускается штатным субагентом текущей системы. В родительском вызове укажи путь пакета; дочерний агент сначала выполняет `review-input`, затем возвращает авторский JSON окончательным сообщением.
Точные поля отчёта, включая `claim_reviews[].test_alignment`, `text_checks` и `source_reviews`, команда `review-input` отдаёт в `report_contract`; не переписывай этот контракт в другой схеме.
Родитель фиксирует отдельную нативную квитанцию и передаёт отчёт через `review-record`. Подделанные/self отчёты не дают допуск тексту.
Для Antigravity передай `--platform antigravity`; Codex C1/C2 определяется по текущему `CODEX_HOME` или явному `--codex-profile` общего инструмента. Историю другого профиля можно читать только при наличии соответствующего поручения пользователя.

Для механической правки корректный `check` не требует карты блоков или нового содержательного одобрения; проверки внешних источников обязательны. Она не получает статус семантической готовности к отправке.
`--warnings` принимает JSON `{"RULE:line":"Предметное решение предупреждения"}`.
При повторной проверке используется сохранённый неизменяемый replay из `--replay-record`; подстановка квитанции от другого кандидата запрещена.
`propose` и `inspect` не допускают `apply`.

## Ответ и завершение

```text
python <scripts>/df_text.py response <answer> --against <target> --journal <journal>
python <scripts>/upwork_project.py answer-prepare <root> --response-file <answer> --platform codex
python <scripts>/df_text.py finalize <root>
python <scripts>/df_text.py finalize <root> --publication
```

`answer-prepare` получает точные запросы из текущего нативного хода, сохраняет ответ и проверяет связанные допуски; Antigravity передаёт `--platform antigravity --conversation <native-uuid>`.
Начало хода и независимая проверка доставки описаны в [общем контракте](../turn-completion.md#нативная-сверка).
Низкоуровневый `df_text.py record-answer <root> --journal <journal> --request-file <request> --response-file <answer> --turn <stable-turn-id>` остаётся для совместимости и восстановления; несколько `--request-file` связывают запросы с одним ответом, повтор допускается только при тех же байтах.
Штатные `record_step`, `record-answer`, finalize анализа и `safe_commit` обращаются к тем же проверкам для связанных текущим поручением/явным списком целевых файлов.
`finalize` проверяет зарегистрированные документы явно выбранного текстового корня; `--publication` дополнительно требует действующий содержательный допуск. Это проверка, а не отправка.
Состояние хранится в `ꘖ/data/texts`: immutable baseline, operation, candidate, check/replay/apply receipts, версии review и index. Исходные доказательства остаются в KB/Evidence; временные вводы можно удалить после сохранения устойчивых квитанций.

## CDP

`browser-check <root> --spec <session.json>` читает актуальные `/json/version` и `/json/list`, проверяет профиль/target через нативный CDP и возвращает `unknown` при недоступном доказательстве.
Спецификация: `session_id`, текущий `target_id`, при необходимости точный `target_url`.
Разрешённые сессии задаются только `runtime.json → text.browser.sessions`; для каждой задаются surface browser/codex/antigravity, loopback endpoint либо Antigravity devtools_active_port, профиль с наблюдаемым command-line argument и target_url_patterns.
Клиентское окно/аккаунт выбираются по поручению и реальному наблюдению; этот документ не разрешает случайный профиль.
Профили C1/C2 используют ссылку `profile: {platform: codex, name: C1|C2, argument: --codex-home}` только если именно этот аргумент фактически доступен в данной сборке. Если аргумент не наблюдается, статус остаётся unknown.
`GuardedCDP` — кооперативный адаптер, не глобальная блокировка остальных инструментов. Нативную автоматизацию Codex/Antigravity не подключай как обход отказа CDP.
