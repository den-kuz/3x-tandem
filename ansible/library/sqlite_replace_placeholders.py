#!/usr/bin/python
# -*- coding: utf-8 -*-

from __future__ import annotations

import os
import re
import shutil
import sqlite3

from ansible.module_utils.basic import AnsibleModule

PLACEHOLDER_RE = re.compile(r"<([A-Za-z0-9_]+)>")


def _quote_ident(name: str) -> str:
    return '"' + name.replace('"', '""') + '"'


def _substitute(text: str, mapping: dict, fail_on_missing: bool) -> str:
    missing: set[str] = set()

    def repl(match: re.Match[str]) -> str:
        key = match.group(1)
        if key not in mapping:
            missing.add(key)
            return match.group(0)
        return str(mapping[key])

    result = PLACEHOLDER_RE.sub(repl, text)
    if missing and fail_on_missing:
        keys = ", ".join(f"<{k}>" for k in sorted(missing))
        raise ValueError(f"Нет значений в replace для плейсхолдеров: {keys}")
    return result


def _maybe_replace(value, mapping: dict, fail_on_missing: bool):
    if value is None:
        return value, False

    if isinstance(value, memoryview):
        value = bytes(value)

    if isinstance(value, bytes):
        try:
            text = value.decode("utf-8")
        except UnicodeDecodeError:
            return value, False
        new_text = _substitute(text, mapping, fail_on_missing)
        if new_text == text:
            return value, False
        return new_text.encode("utf-8"), True

    if not isinstance(value, str):
        if "<" not in str(value):
            return value, False
        value = str(value)

    if "<" not in value:
        return value, False

    new_text = _substitute(value, mapping, fail_on_missing)
    if new_text == value:
        return value, False
    return new_text, True


def prepare_sqlite_database(
    src: str,
    dest: str,
    mapping: dict,
    *,
    fail_on_missing: bool = True,
) -> int:
    src = os.path.abspath(src)
    dest = os.path.abspath(dest)

    if not os.path.isfile(src):
        raise FileNotFoundError(f"Исходная БД не найдена: {src}")

    os.makedirs(os.path.dirname(dest) or ".", exist_ok=True)
    if src != dest:
        shutil.copy2(src, dest)

    conn = sqlite3.connect(dest)
    conn.row_factory = sqlite3.Row
    replacements = 0

    try:
        cursor = conn.cursor()
        tables = [
            row[0]
            for row in cursor.execute(
                "SELECT name FROM sqlite_master "
                "WHERE type='table' AND name NOT LIKE 'sqlite_%'"
            )
        ]

        for table in tables:
            columns = [
                row[1]
                for row in cursor.execute(
                    f"PRAGMA table_info({_quote_ident(table)})"
                )
            ]
            if not columns:
                continue

            col_sql = ", ".join(_quote_ident(c) for c in columns)
            query = (
                f"SELECT rowid AS _sqlite_rowid_, {col_sql} "
                f"FROM {_quote_ident(table)}"
            )
            rows = cursor.execute(query).fetchall()

            for row in rows:
                rowid = row["_sqlite_rowid_"]
                updates: dict[str, object] = {}
                for column in columns:
                    new, changed = _maybe_replace(
                        row[column], mapping, fail_on_missing
                    )
                    if changed:
                        updates[column] = new

                if not updates:
                    continue

                set_sql = ", ".join(
                    f"{_quote_ident(col)}=?" for col in updates
                )
                cursor.execute(
                    f"UPDATE {_quote_ident(table)} SET {set_sql} WHERE rowid=?",
                    list(updates.values()) + [rowid],
                )
                replacements += len(updates)

        conn.commit()
    finally:
        conn.close()

    return replacements


def main() -> None:
    module = AnsibleModule(
        argument_spec={
            "src": {"type": "path", "required": True},
            "dest": {"type": "path", "required": True},
            "replace": {"type": "dict", "required": True},
            "fail_on_missing": {"type": "bool", "default": True},
        },
    )

    mapping = module.params["replace"]
    if not isinstance(mapping, dict):
        module.fail_json(msg="replace должен быть словарём")

    try:
        count = prepare_sqlite_database(
            module.params["src"],
            module.params["dest"],
            mapping,
            fail_on_missing=module.params["fail_on_missing"],
        )
    except FileNotFoundError as exc:
        module.fail_json(msg=str(exc))
    except (ValueError, RuntimeError) as exc:
        module.fail_json(msg=str(exc))
    except sqlite3.Error as exc:
        module.fail_json(msg=f"SQLite: {exc}")

    module.exit_json(changed=count > 0, replacements=count)


if __name__ == "__main__":
    main()