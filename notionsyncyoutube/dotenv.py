from __future__ import annotations

import os
from pathlib import Path


def load_dotenv_if_present(path: str | Path = ".env") -> None:
    dotenv_path = Path(path)

    if not dotenv_path.exists():
        return

    for raw_line in dotenv_path.read_text(encoding="utf-8").splitlines():
        key, value = parse_dotenv_line(raw_line)

        if key and key not in os.environ:
            os.environ[key] = value


def parse_dotenv_line(line: str) -> tuple[str | None, str]:
    stripped = line.strip()

    if not stripped or stripped.startswith("#"):
        return None, ""

    if stripped.startswith("export "):
        stripped = stripped[len("export ") :].strip()

    if "=" not in stripped:
        return None, ""

    key, value = stripped.split("=", 1)
    key = key.strip()
    value = strip_dotenv_value(value.strip())

    if not key:
        return None, ""

    return key, value


def strip_dotenv_value(value: str) -> str:
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
        return value[1:-1]

    return value
