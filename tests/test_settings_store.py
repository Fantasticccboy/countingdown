import json

from countdown_app.settings_store import AppSettings, SettingsStore


def test_roundtrip(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(
        "countdown_app.settings_store.Path.home",
        lambda: tmp_path,
    )
    s = SettingsStore()
    s.settings.always_on_top = True
    s.settings.close_behavior_remembered = True
    s.settings.close_behavior_is_tray = True
    s.save_window_rect(100.0, 200.0, 580.0, 720.0)
    s2 = SettingsStore()
    assert s2.settings.always_on_top is True
    assert s2.settings.close_behavior_remembered is True
    assert s2.settings.close_behavior_is_tray is True
    assert s2.settings.window_left == 100.0
    assert s2.settings.has_saved_window_rect() is True


def test_has_saved_window_rect_false() -> None:
    a = AppSettings()
    assert a.has_saved_window_rect() is False


def test_migrate_close_to_tray(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(
        "countdown_app.settings_store.Path.home",
        lambda: tmp_path,
    )
    cfg = tmp_path / ".countdown_app" / "settings.json"
    cfg.parent.mkdir(parents=True, exist_ok=True)
    cfg.write_text(
        json.dumps({"close_to_tray": True, "always_on_top": False}),
        encoding="utf-8",
    )
    s = SettingsStore()
    assert s.settings.close_behavior_remembered is True
    assert s.settings.close_behavior_is_tray is True
