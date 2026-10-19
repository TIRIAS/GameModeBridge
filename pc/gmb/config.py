"""설정 로드, 검증, 저장 (CLAUDE.md 9장, 11장 설정 파일 값 검증).

설정 값은 명령으로 실행하거나 eval 하지 않음. games는 exe 파일 이름 형식만 허용함.
"""

import json
import os
import re
from dataclasses import dataclass
from pathlib import Path

# 파일 이름만 허용함 (한글 등 유니코드 글자 포함). 경로 구분자, 따옴표, 셸 특수 문자는 거부함
_EXE_NAME = re.compile(r"^\w[\w .\-()\[\]]{0,99}\.exe$", re.IGNORECASE)
MODES = ("dry-run", "live")
DEFAULT_DATA = {
    "games": [],
    "poll_interval_sec": 2,
    "mode": "dry-run",
    "sa_store_path": "%APPDATA%/GameModeBridge/sa.bin",
    "log_path": "%APPDATA%/GameModeBridge/logs/gamemode.log",
}


class ConfigError(ValueError):
    pass


@dataclass(frozen=True)
class Config:
    games: tuple[str, ...]
    poll_interval_sec: float = 2.0
    mode: str = "dry-run"
    sa_store_path: Path | None = None
    log_path: Path | None = None


def default_path() -> Path:
    return Path(os.environ["APPDATA"]) / "GameModeBridge" / "config.json"


def is_valid_exe_name(name: object) -> bool:
    return isinstance(name, str) and bool(_EXE_NAME.match(name))


def _expand(path: str) -> Path:
    return Path(os.path.expandvars(path))


def _unique(games: list[str]) -> tuple[str, ...]:
    # 대소문자만 다른 중복은 하나로 합침. 표시용으로 처음 적은 표기를 유지함
    unique: dict[str, str] = {}
    for g in games:
        unique.setdefault(g.lower(), g)
    return tuple(unique.values())


def parse(data: dict) -> Config:
    if not isinstance(data, dict):
        raise ConfigError("설정은 JSON 객체여야 함")
    games = data.get("games", [])
    if not isinstance(games, list):
        raise ConfigError("games는 목록이어야 함")
    for g in games:
        if not is_valid_exe_name(g):
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
    return Config(_unique(games), float(poll), mode, **paths)


def _read(path: Path) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        raise ConfigError(f"설정 파일이 없음: {path}") from None
    except json.JSONDecodeError as e:
        raise ConfigError(f"설정 파일 JSON 오류: {e}") from None


def _write(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.replace(tmp, path)


def load(path: Path) -> Config:
    return parse(_read(path))


def load_or_create(path: Path) -> Config:
    """설정 파일이 없으면 기본값(감지 목록 비어 있음, 드라이런)으로 만듦."""
    if not path.exists():
        _write(path, DEFAULT_DATA)
    return load(path)


def _update(path: Path, key: str, value) -> Config:
    """설정 값 하나만 바꿔 저장함. 다른 설정 값은 그대로 둠. 검증에 실패하면 저장하지 않음."""
    data = _read(path)
    data[key] = value
    cfg = parse(data)
    _write(path, data)
    return cfg


def save_games(path: Path, games: list[str]) -> Config:
    return _update(path, "games", list(_unique(games)))


def save_mode(path: Path, mode: str) -> Config:
    return _update(path, "mode", mode)


def add_games(current: list[str], picked_paths: list[str]) -> tuple[list[str], list[str]]:
    """파일 탐색기에서 고른 exe 경로들의 파일 이름을 목록에 추가함. (새 목록, 거부된 이름)을 돌려줌."""
    games = list(current)
    known = {g.lower() for g in games}
    rejected = []
    for p in picked_paths:
        name = Path(p).name
        if not is_valid_exe_name(name):
            rejected.append(name)
        elif name.lower() not in known:
            games.append(name)
            known.add(name.lower())
    return games, rejected
