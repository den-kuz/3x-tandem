#!/usr/bin/python
# -*- coding: utf-8 -*-

from __future__ import annotations

import os
from collections.abc import Callable

from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils.env_dotenv import (
    parse_dotenv_lines,
    read_dotenv_file,
    upsert_dotenv_lines,
)
from ansible.module_utils.secret_generators import (
    gen_secret,
    reality_keypair,
    reality_keypair_valid,
    wireguard_keypair,
    wireguard_keypair_valid,
)

try:
    import fcntl
except ImportError:  # pragma: no cover
    fcntl = None

_PAIR_SPECS: dict[
    str,
    tuple[str, str, Callable[[], dict[str, str]], Callable[[str, str], bool]],
] = {
    "reality_keypair": (
        "GEN_REALITY_PRIVATE",
        "GEN_REALITY_PUBLIC",
        reality_keypair,
        reality_keypair_valid,
    ),
    "wireguard_keypair": (
        "GEN_WIREGUARD_PRIVATE",
        "GEN_WIREGUARD_PUBLIC",
        wireguard_keypair,
        wireguard_keypair_valid,
    ),
    "wireguard_secret_keypair": (
        "GEN_WIREGUARD_SECRET_PRIVATE",
        "GEN_WIREGUARD_SECRET_PUBLIC",
        wireguard_keypair,
        wireguard_keypair_valid,
    ),
}


def _flock_exclusive(handle) -> None:
    if fcntl is not None:
        fcntl.flock(handle.fileno(), fcntl.LOCK_EX)


def _funlock(handle) -> None:
    if fcntl is not None:
        fcntl.flock(handle.fileno(), fcntl.LOCK_UN)


def _require(store: dict[str, str], key: str) -> str:
    value = (store.get(key) or "").strip()
    if not value:
        raise ValueError(f"Нет {key} в файле")
    return value


def _resolve_keypair(
    prefix: str,
    store: dict[str, str],
    private_name: str,
    public_name: str,
    generate_pair: Callable[[], dict[str, str]],
    valid_pair: Callable[[str, str], bool],
    *,
    do_generate: bool,
    pending: dict[str, str],
    created: list[str],
) -> None:
    priv_key = f"{prefix}{private_name}"
    pub_key = f"{prefix}{public_name}"
    priv_val = (store.get(priv_key) or "").strip()
    pub_val = (store.get(pub_key) or "").strip()

    if not do_generate:
        priv_val = _require(store, priv_key)
        pub_val = _require(store, pub_key)
        if not valid_pair(priv_val, pub_val):
            raise ValueError(f"{priv_key} и {pub_key} не составляют пару")
        return

    if priv_val and pub_val and valid_pair(priv_val, pub_val):
        return

    pair = generate_pair()
    pending[priv_key] = pair["private_key"]
    pending[pub_key] = pair["public_key"]
    created.extend([priv_key, pub_key])


def _ensure_host_secrets(
    path: str,
    prefix: str,
    items: dict,
    *,
    do_generate: bool,
) -> tuple[dict[str, str], list[str], bool]:
    if not isinstance(items, dict) or not items:
        raise ValueError("items должен быть непустым словарём")
    if not prefix.strip():
        raise ValueError("prefix не может быть пустым")

    directory = os.path.dirname(os.path.abspath(path))
    if directory:
        os.makedirs(directory, exist_ok=True)

    if do_generate:
        open(path, "a", encoding="utf-8").close()
    elif not os.path.isfile(path):
        raise ValueError(f"Файл не найден: {path}. Выполните: make setup (или make setup tag=3x)")

    mode = "r+" if do_generate else "r"
    with open(path, mode, encoding="utf-8") as handle:
        if do_generate:
            _flock_exclusive(handle)
        try:
            handle.seek(0)
            lines = handle.read().splitlines()
            store = parse_dotenv_lines(lines)
            created: list[str] = []
            pending: dict[str, str] = {}
            changed = False
            skip: set[str] = set()

            for method, (priv, pub, gen, valid) in _PAIR_SPECS.items():
                if not any(
                    isinstance(s, dict) and s.get("method") == method
                    for s in items.values()
                ):
                    continue
                _resolve_keypair(
                    prefix,
                    store,
                    priv,
                    pub,
                    gen,
                    valid,
                    do_generate=do_generate,
                    pending=pending,
                    created=created,
                )
                skip.update({priv, pub})

            for name, spec in items.items():
                if name in skip:
                    continue
                if not isinstance(spec, dict) or "method" not in spec:
                    raise ValueError(f"Для {name!r} нужен объект с ключом method")
                if spec["method"] in _PAIR_SPECS:
                    continue

                key = f"{prefix}{name}"
                if (store.get(key) or "").strip():
                    continue

                if not do_generate:
                    _require(store, key)
                    continue

                pending[key] = gen_secret(spec["method"], spec)
                created.append(key)

            if pending:
                lines = upsert_dotenv_lines(lines, pending)
                handle.seek(0)
                handle.truncate()
                handle.write("\n".join(lines).rstrip() + "\n")
                handle.flush()
                os.fsync(handle.fileno())
                changed = True

            all_vars = dict(store)
            all_vars.update(pending)
        finally:
            if do_generate:
                _funlock(handle)

    return all_vars, created, changed


def main() -> None:
    module = AnsibleModule(
        argument_spec={
            "path": {"type": "path", "required": True},
            "prefix": {"type": "str"},
            "items": {"type": "dict"},
            "generate": {"type": "bool", "default": False},
        },
        supports_check_mode=True,
    )

    path = os.path.abspath(module.params["path"])
    prefix = (module.params.get("prefix") or "").strip()
    items = module.params.get("items") or {}
    do_generate = bool(module.params.get("generate"))

    has_scope = bool(prefix and items)

    if has_scope and do_generate and module.check_mode:
        module.exit_json(changed=False, vars={}, created=[])

    if not has_scope:
        try:
            all_vars = read_dotenv_file(path)
        except FileNotFoundError as exc:
            module.fail_json(msg=str(exc))
        module.exit_json(changed=False, vars=all_vars, created=[])
        return

    if prefix and not items:
        module.fail_json(msg="Указан prefix, но нет items")
    if items and not prefix:
        module.fail_json(msg="Указаны items, но нет prefix")

    try:
        all_vars, created, changed = _ensure_host_secrets(
            path, prefix, items, do_generate=do_generate
        )
    except ValueError as exc:
        module.fail_json(msg=str(exc))
    except OSError as exc:
        module.fail_json(msg=f"Не удалось обновить {path}: {exc}")

    module.exit_json(changed=changed, vars=all_vars, created=created)


if __name__ == "__main__":
    main()