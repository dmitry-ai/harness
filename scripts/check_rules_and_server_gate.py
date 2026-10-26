#!/usr/bin/env python3
"""PreToolUse hook for enforcing rules token budget (auto-splitting) and server hygiene (no remote backups)."""

import json
import re
import sys


def check_rules_budget(name: str, args: dict) -> str | None:
    path = args.get("Path", "")
    if not path:
        return None
    normalized = path.replace("\\", "/").lower()
    if "/.agents/rules/" not in normalized:
        return None

    content = args.get("Content") if name == "write_file" else args.get("Replacement")
    if not content:
        return None

    byte_len = len(content.encode("utf-8"))

    if normalized.endswith("90-project.md"):
        if byte_len > 4000:
            return (
                f"Размер Карты 90-project.md ({byte_len} байт) превышает лимит 4000 байт во избежание "
                f"выпадения из системного промпта Antigravity. Запусти "
                f"'python C:/work/upwork/code/.agents/scripts/split_project_rules.py' для авторазбиения "
                f"или вынеси новый раздел в отдельный модуль .agents/rules/9X-<тема>.md."
            )
    elif re.search(r'/9[1-9]-[^/]+\.md$', normalized):
        if byte_len > 6000:
            return (
                f"Размер модуля правил {path} ({byte_len} байт) превышает лимит 6000 байт. "
                f"Разбей его на более компактные тематические модули."
            )

    return None


def check_server_hygiene(name: str, args: dict) -> str | None:
    # 1. Direct run_command checks
    if name == "run_command":
        cmd = args.get("CommandLine", "")
        is_server_cmd = bool(re.search(r'\b(nxcli\.io|nxcli\.net|ssh\.exe|ssh\s+)\b', cmd, re.IGNORECASE))
        backup_pattern = re.search(r'(\.bak\b|\.backup\b|\.orig\b|_backup\w*|cp\s+.*\.bak)', cmd, re.IGNORECASE)
        if is_server_cmd and backup_pattern:
            return (
                "Создание резервных копий (*.bak, *.backup, _backup, *.orig) на удалённых серверах "
                "категорически запрещено! Используй локальный Git."
            )

    # 2. Scratch scripts with remote SSH commands
    if name in ("write_file", "edit_file"):
        content = args.get("Content") if name == "write_file" else args.get("Replacement")
        if content and isinstance(content, str):
            is_server_script = bool(re.search(r'\b(nxcli\.io|nxcli\.net|ssh\.exe)\b', content, re.IGNORECASE))
            has_backup_cmd = bool(re.search(r'(\.bak\b|\.backup\b|\.orig\b|_backup\w*|cp\s+.*\.bak)', content, re.IGNORECASE))
            if is_server_script and has_backup_cmd:
                return (
                    "Скрипт содержит команды создания резервных копий на сервере (*.bak, *.backup, _backup)! "
                    "Создание бэкапов на удалённых серверах категорически запрещено! Используй локальный Git."
                )

    return None


def main():
    try:
        raw = sys.stdin.read()
        if not raw.strip():
            sys.stdout.write(json.dumps({"decision": "allow"}))
            return

        payload = json.loads(raw)
        tool_call = payload.get("toolCall", {})
        name = tool_call.get("name", "")
        args = tool_call.get("args", {})

        # Rule 1: Rules Budget Gate
        rule_err = check_rules_budget(name, args)
        if rule_err:
            sys.stdout.write(json.dumps({
                "decision": "deny",
                "reason": f"ОТКЛОНЕНО (RULES-BUDGET-GATE): {rule_err}"
            }, ensure_ascii=False))
            return

        # Rule 2: Server Hygiene Gate
        server_err = check_server_hygiene(name, args)
        if server_err:
            sys.stdout.write(json.dumps({
                "decision": "deny",
                "reason": f"ОТКЛОНЕНО (SERVER-HYGIENE-GATE): {server_err}"
            }, ensure_ascii=False))
            return

        sys.stdout.write(json.dumps({"decision": "allow"}))

    except Exception:
        sys.stdout.write(json.dumps({"decision": "allow"}))


if __name__ == "__main__":
    main()
