"""설정 로드 및 검증 (CLAUDE.md 9장, 11장 설정 파일 값 검증).

설정 값은 명령으로 실행하거나 eval 하지 않음. games는 exe 파일 이름 형식만 허용함.
"""

import json
import os
import re
from dataclasses import dataclass
from pathlib import Path

# 경로 구분자, 따옴표, 셸 특수 문자 등을 막고 파일 이름만 허용함
_EXE_NAME = re.compile(r"^[A-Za-z0-9][A-Za-z0-9 _.\-()\[\]]{0,99}\.exe$", re.IGNORECASE)
MODES = ("dry-run", "live")


class ConfigError(ValueError):
    pass


@dataclass(frozen=True)
class Config:
    games: tuple[str, ...]
    poll_interval_sec: float = 2.0
    mode: str = "dry-run"
    sa_store_path: Path | None = None
    log_path: Path | None = None


def _expand(path: str) -> Path:
    return Path(os.path.expandvars(path))


def parse(data: dict) -> Config:
    if not isinstance(data, dict):
        raise ConfigError("설정은 JSON 객체여야 함")
    games = data.get("games")
    if not isinstance(games, list) or not games:
        raise ConfigError("games는 비어 있지 않은 목록이어야 함")
    for g in games:
        if not isinstance(g, str) or not _EXE_NAME.match(g):
            raise ConfigError(f"games 항목은 exe 파일 이름만 허용함: {g!r}")
    poll = data.get("poll_interval_sec", 2)
    if isinstance(poll, bool) or not isinstance(poll, (int, float)) or not 1 <= poll <= 60:
        raise ConfigError("poll_interval_sec는 1~60 사이 숫자여야 함")
    mode = data.get("mode", "dry-run")
    if mode not in MODES:
        raise ConfigError(f"mode는 {', '.join(MODES)} 중 하나여야 함")
    paths = {}
    for key in ("sa_store_path", "log_path"):
        value = data.get(key)
        if value is not None and not isinstance(value, str):
            raise ConfigError(f"{key}는 문자열이어야 함")
        paths[key] = _expand(value) if value else None
    # 대소문자만 다른 중복은 하나로 합침. 표시용으로 처음 적은 표기를 유지함
    unique = {}
    for g in games:
        unique.setdefault(g.lower(), g)
    return Config(tuple(unique.values()), float(poll), mode, **paths)


def load(path: Path) -> Config:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        raise ConfigError(f"설정 파일이 없음: {path} (config.example.json을 복사하여 만드세요)") from None
    except json.JSONDecodeError as e:
        raise ConfigError(f"설정 파일 JSON 오류: {e}") from None
    return parse(data)
