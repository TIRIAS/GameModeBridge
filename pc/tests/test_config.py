import json

import pytest

from gmb import config


def test_valid_config_and_defaults(monkeypatch):
    monkeypatch.setenv("APPDATA", "C:/AppData")
    cfg = config.parse({"games": ["VALORANT-Win64-Shipping.exe", "eldenring.EXE"],
                        "log_path": "%APPDATA%/GameModeBridge/logs/gamemode.log"})
    assert cfg.games == ("VALORANT-Win64-Shipping.exe", "eldenring.EXE")
    assert cfg.poll_interval_sec == 2.0
    assert cfg.mode == "dry-run"
    assert str(cfg.log_path).replace("\\", "/") == "C:/AppData/GameModeBridge/logs/gamemode.log"


def test_duplicate_games_removed():
    assert config.parse({"games": ["a.exe", "A.EXE"]}).games == ("a.exe",)  # 처음 표기 유지


def test_example_file_is_valid():
    from pathlib import Path
    config.load(Path(__file__).resolve().parents[1] / "config.example.json")


@pytest.mark.parametrize("name", [
    "", "game", "game.bat", "..\\game.exe", "C:\\Games\\game.exe", "dir/game.exe",
    "game.exe & calc.exe", "game.exe;calc", "\"game.exe\"", ".exe", "x" * 120 + ".exe", 123,
])
def test_invalid_exe_names_rejected(name):
    with pytest.raises(config.ConfigError):
        config.parse({"games": [name]})


@pytest.mark.parametrize("data", [
    [],
    {},
    {"games": []},
    {"games": "a.exe"},
    {"games": ["a.exe"], "poll_interval_sec": 0},
    {"games": ["a.exe"], "poll_interval_sec": 61},
    {"games": ["a.exe"], "poll_interval_sec": True},
    {"games": ["a.exe"], "mode": "fast"},
    {"games": ["a.exe"], "log_path": 5},
])
def test_invalid_config_rejected(data):
    with pytest.raises(config.ConfigError):
        config.parse(data)


def test_load_missing_and_broken_file(tmp_path):
    with pytest.raises(config.ConfigError):
        config.load(tmp_path / "none.json")
    bad = tmp_path / "bad.json"
    bad.write_text("{", encoding="utf-8")
    with pytest.raises(config.ConfigError):
        config.load(bad)
    good = tmp_path / "good.json"
    good.write_text(json.dumps({"games": ["a.exe"]}), encoding="utf-8")
    assert config.load(good).games == ("a.exe",)
