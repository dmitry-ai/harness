#!/usr/bin/env python3
import json
import re
import sys

# Сокращения, не являющиеся концом предложения
ABBREVIATIONS = (
    r'\b(?:г|гг|т\.д|т\.п|см|им|др|пр|ул|д|кв|рис|табл|ст|п|ч|руб|тыс|млн|млрд|'
    r'англ|рус|напр|ок|vs|Mr|Mrs|Ms|Dr|St|Inc|Ltd|Co|Jr|Sr|e\.g|i\.e)\.'
)
ABBR_RE = re.compile(ABBREVIATIONS, re.IGNORECASE)

# Множественные предложения на одной строке
MULTI_SENT_RE = re.compile(
    r'(?:[А-Яа-яЁёA-Za-z0-9«»"(),:-]+\s+){2,}[А-Яа-яЁёA-Za-z0-9]+[.!?]\s+[А-ЯЁA-Z][a-zа-яёA-Za-z0-9]'
)


def is_abbreviation_end(text):
    clean = text.rstrip()
    return bool(ABBR_RE.search(clean))


def check_markdown_content(content):
    if not content or not isinstance(content, str):
        return None

    lines = content.split('\n')
    in_code_block = False
    in_frontmatter = False

    for i, line in enumerate(lines):
        stripped = line.strip()

        # Frontmatter
        if i == 0 and stripped == '---':
            in_frontmatter = True
            continue
        if in_frontmatter:
            if stripped == '---':
                in_frontmatter = False
            continue

        # Блоки кода ``` / ~~~
        if stripped.startswith(('```', '~~~')):
            in_code_block = not in_code_block
            continue
        if in_code_block:
            continue

        # Пропуск пустых строк, заголовков, таблиц и горизонтальных линий
        if not stripped or stripped.startswith(('#', '|', '---', '===', '>')):
            continue

        # 1. Проверка на множественные предложения на одной строке (SENT-SPLIT)
        # Очищаем от инлайн-кода, ссылок и кавычек
        cleaned = re.sub(r'`[^`]*`', 'code', line)
        cleaned = re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', cleaned)
        cleaned = re.sub(r'«[^»]*»', '«цитата»', cleaned)
        cleaned = re.sub(ABBREVIATIONS, 'abbr', cleaned, flags=re.IGNORECASE)

        if MULTI_SENT_RE.search(cleaned):
            return (
                f"Строка {i + 1}: обнаружено несколько предложений на одной строке (правило DOC-4). "
                f"Каждое предложение должно начинаться с новой физической строки.\n"
                f"Фрагмент: {stripped[:80]}"
            )

        # 2. Проверка на склейку строк без 2 пробелов на конце (нейрослоп)
        # Если текущая строка заканчивается знаком препинания (. ! ?) или текстом,
        # а следующая строка — не пустая, не заголовок и не маркер списка,
        # при этом текущая строка НЕ заканчивается двумя пробелами ('  ') и НЕ заканчивается обратным слешем ('\\').
        if i + 1 < len(lines):
            next_line = lines[i + 1]
            next_stripped = next_line.strip()

            # Если следующая строка не пустая и не специальный markdown-элемент
            if (
                next_stripped
                and not next_stripped.startswith(('#', '```', '~~~', '---', '===', '>', '|'))
                and not re.match(r'^(?:[-*+]|\d+\.)\s+', next_stripped)
            ):
                # Проверяем окончание текущей строки
                # Допустимо: заканчивается на '  ' (два пробела) или на '\\'
                if not (line.endswith('  ') or line.endswith('\\')):
                    # Если это обычный текст или строка внутри пункта списка
                    return (
                        f"Строка {i + 1}: обнаружен слитный текст (нейрослоп) без CommonMark hard break. "
                        f"Строка переходит на следующую без пустой строки и без двух пробелов на конце ('  \\n'). "
                        f"В рендерере этот текст склеится в нечитаемый монолит.\n"
                        f"Строка: {stripped[:70]}"
                    )

    return None


def main():
    try:
        raw_input = sys.stdin.read()
        if not raw_input.strip():
            sys.stdout.write(json.dumps({"decision": "allow"}))
            return

        payload = json.loads(raw_input)
        tool_call = payload.get("toolCall", {})
        name = tool_call.get("name", "")
        args = tool_call.get("args", {})

        if name not in ("write_file", "edit_file"):
            sys.stdout.write(json.dumps({"decision": "allow"}))
            return

        path = args.get("Path", "")
        if not path or not path.lower().endswith(".md"):
            sys.stdout.write(json.dumps({"decision": "allow"}))
            return

        # Исключаем логи запросов пользователя
        normalized_path = path.replace("\\", "/").lower()
        if "/req/" in normalized_path:
            sys.stdout.write(json.dumps({"decision": "allow"}))
            return

        content = args.get("Content") if name == "write_file" else args.get("Replacement")
        violation = check_markdown_content(content)

        if violation:
            sys.stdout.write(
                json.dumps(
                    {
                        "decision": "deny",
                        "reason": f"ОТКЛОНЕНО (DOC-4 Anti-Slop Hook): {violation}",
                    },
                    ensure_ascii=False,
                )
            )
            return

        sys.stdout.write(json.dumps({"decision": "allow"}))

    except Exception as e:
        # В случае внутренней ошибки хука не ломаем пайплайн намертво, но логируем
        sys.stdout.write(json.dumps({"decision": "allow"}))


if __name__ == "__main__":
    main()
