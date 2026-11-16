from __future__ import annotations

import os
import re

_ENV_LINE = re.compile(r"^([A-Za-z_][A-Za-z0-9_]*)=(.*)$")


def unquote(value: str) -> str:
    value = value.strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in ('"', "'"):
        inner = value[1:-1]
        if value[0] == '"':
            inner = inner.replace("\\n", "\n").replace('\\"', '"').replace("\\\\", "\\")
        return inner
    return value


def quote(value: str) -> str:
    if re.fullmatch(r"[A-Za-z0-9_./:@+-]+", value):
        return value
    escaped = value.replace("\\", "\\\\").replace('"', '\\"')
    return f'"{escaped}"'


def parse_dotenv_lines(lines: list[str]) -> dict[str, str]:
    data: dict[str, str] = {}
    for line in lines:
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        match = _ENV_LINE.match(stripped)
        if not match:
            continue
        data[match.group(1)] = unquote(match.group(2))
    return data


def read_dotenv_file(path: str) -> dict[str, str]:
    if not os.path.isfile(path):
        raise FileNotFoundError(f"Файл не найден: {path}")
    with open(path, encoding="utf-8") as handle:
        return parse_dotenv_lines(handle.read().splitlines())


parse_dotenv_file = read_dotenv_file


def upsert_dotenv_lines(lines: list[str], updates: dict[str, str]) -> list[str]:
    seen: set[str] = set()
    result = list(lines)

    for index, line in enumerate(result):
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        match = _ENV_LINE.match(stripped)
        if not match:
            continue
        key = match.group(1)
        if key in updates:
            result[index] = f"{key}={quote(updates[key])}"
            seen.add(key)

    new_keys = [key for key in updates if key not in seen]
    if new_keys:
        if result and result[-1].strip():
            result.append("")
        result.append("# auto-generated")
        for key in new_keys:
            result.append(f"{key}={quote(updates[key])}")
    return result