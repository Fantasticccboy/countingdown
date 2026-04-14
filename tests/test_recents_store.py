from countdown_app.recents_store import RecentsStore
from countdown_app.timer_engine import MAX_TOTAL_SECONDS


def test_remember_and_most_recent(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(
        "countdown_app.recents_store.Path.home",
        lambda: tmp_path,
    )
    s = RecentsStore()
    assert s.most_recent() is None
    s.remember(0, 25, 0)
    assert s.most_recent() == (0, 25, 0)
    s.remember(1, 0, 0)
    assert s.most_recent() == (1, 0, 0)


def test_dedupe_by_total_seconds(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(
        "countdown_app.recents_store.Path.home",
        lambda: tmp_path,
    )
    s = RecentsStore()
    s.remember(0, 5, 0)
    s.remember(0, 10, 0)
    s.remember(0, 5, 0)
    assert s.most_recent() == (0, 5, 0)
    # 仍保留 10 分在第二位（实现为去重后插入队首，故列表应含两条）
    assert len(s._items) == 2


def test_remember_from_total_seconds(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(
        "countdown_app.recents_store.Path.home",
        lambda: tmp_path,
    )
    s = RecentsStore()
    s.remember_from_total_seconds(3661)
    assert s.most_recent() == (1, 1, 1)


def test_ignore_invalid_total(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(
        "countdown_app.recents_store.Path.home",
        lambda: tmp_path,
    )
    s = RecentsStore()
    s.remember(0, 0, 0)
    assert s.most_recent() is None
    s.remember(25, 0, 0)
    assert s.most_recent() is None
    s.remember(0, 0, 1)
    assert s.most_recent() == (0, 0, 1)
    s.remember_from_total_seconds(MAX_TOTAL_SECONDS + 1)
    assert s.most_recent() == (0, 0, 1)
