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


def test_empty_games_allowed():
    # 트레이에서 나중에 추가할 수 있으므로 빈 목록도 허용함
    assert config.parse({}).games == ()
    assert config.parse({"games": []}).games == ()


@pytest.mark.parametrize("name", ["검은사막.exe", "Game Launcher (x64).exe", "eldenring.exe"])
def test_unicode_and_spaces_allowed(name):
    assert config.is_valid_exe_name(name)


def test_load_or_create_writes_default(tmp_path):
    path = tmp_path / "sub" / "config.json"
    cfg = config.load_or_create(path)
    assert path.exists() and cfg.games == () and cfg.mode == "dry-run"


def test_save_games_keeps_other_settings(tmp_path):
    path = tmp_path / "config.json"
    path.write_text(json.dumps({"games": ["a.exe"], "mode": "live", "poll_interval_sec": 3}), encoding="utf-8")
    cfg = config.save_games(path, ["b.exe", "B.EXE", "c.exe"])
    assert cfg.games == ("b.exe", "c.exe")
    saved = json.loads(path.read_text(encoding="utf-8"))
    assert saved == {"games": ["b.exe", "c.exe"], "mode": "live", "poll_interval_sec": 3}


def test_save_games_rejects_invalid_without_writing(tmp_path):
    path = tmp_path / "config.json"
    path.write_text(json.dumps({"games": ["a.exe"]}), encoding="utf-8")
    with pytest.raises(config.ConfigError):
        config.save_games(path, ["bad;name.exe"])
    assert json.loads(path.read_text(encoding="utf-8"))["games"] == ["a.exe"]


def test_save_mode_keeps_other_settings_and_validates(tmp_path):
    path = tmp_path / "config.json"
    path.write_text(json.dumps({"games": ["a.exe"]}), encoding="utf-8")
    assert config.save_mode(path, "live").mode == "live"
    assert json.loads(path.read_text(encoding="utf-8")) == {"games": ["a.exe"], "mode": "live"}
    with pytest.raises(config.ConfigError):
        config.save_mode(path, "fast")
    assert json.loads(path.read_text(encoding="utf-8"))["mode"] == "live"


def test_add_games_from_picked_paths():
    games, rejected = config.add_games(
        ["EXCEL.EXE"],
        [r"C:\Program Files\Office\excel.exe", r"D:\Games\Elden Ring\eldenring.exe", r"C:\x\bad&name.exe"],
    )
    assert games == ["EXCEL.EXE", "eldenring.exe"]  # 대소문자만 다른 중복은 추가 안 함
    assert rejected == ["bad&name.exe"]
