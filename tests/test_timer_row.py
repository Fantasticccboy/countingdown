from datetime import datetime

import flet as ft

from countdown_app.recents_store import RecentsStore
from countdown_app.timer_engine import CountdownState
from countdown_app.timer_row import TimerRow


class FakePage:
    def __init__(self) -> None:
        self.update_calls = 0
        self.dialogs = []

    def update(self) -> None:
        self.update_calls += 1

    def show_dialog(self, dialog) -> None:
        self.dialogs.append(dialog)

    def pop_dialog(self) -> None:
        if self.dialogs:
            self.dialogs.pop()


def _build_timer_row(tmp_path, monkeypatch) -> TimerRow:
    monkeypatch.setattr(
        "countdown_app.recents_store.Path.home",
        lambda: tmp_path,
    )
    recents = RecentsStore()
    row = TimerRow(
        page=FakePage(),
        on_removed=lambda _row: None,
        can_remove=lambda: True,
        recents=recents,
        on_recents_changed=lambda: None,
    )
    row.refresh_controls()
    return row


def test_apply_selected_today_time_fills_inputs_without_starting(
    tmp_path, monkeypatch
) -> None:
    row = _build_timer_row(tmp_path, monkeypatch)

    ok = row._apply_selected_today_time(
        12,
        1,
        0,
        now=datetime(2026, 5, 7, 12, 0, 0),
    )

    assert ok is True
    assert row.field_hours.value == "0"
    assert row.field_minutes.value == "1"
    assert row.field_seconds.value == "0"
    assert row.engine.state is CountdownState.IDLE
    assert row.engine.remaining_seconds == 0
    assert row.txt_error.value == ""


def test_apply_selected_today_time_rejects_past_value_without_overwriting_inputs(
    tmp_path, monkeypatch
) -> None:
    row = _build_timer_row(tmp_path, monkeypatch)
    row._apply_hms(0, 5, 0)

    ok = row._apply_selected_today_time(
        14,
        59,
        59,
        now=datetime(2026, 5, 7, 15, 0, 0),
    )

    assert ok is False
    assert row.field_hours.value == "0"
    assert row.field_minutes.value == "5"
    assert row.field_seconds.value == "0"
    assert row.txt_error.value == "该时间点已过去，请重新选择"


def test_time_picker_button_disabled_while_running(tmp_path, monkeypatch) -> None:
    row = _build_timer_row(tmp_path, monkeypatch)
    assert row.btn_pick_time.disabled is False

    assert row.engine.start_from_inputs("0", "0", "10") is None
    row.refresh_controls()

    assert row.btn_pick_time.disabled is True


def test_time_picker_button_disabled_while_paused(tmp_path, monkeypatch) -> None:
    row = _build_timer_row(tmp_path, monkeypatch)

    assert row.engine.start_from_inputs("0", "0", "10") is None
    row.engine.pause()
    row.refresh_controls()

    assert row.btn_pick_time.disabled is True


def test_pick_time_uses_cupertino_bottom_sheet_with_fixed_picker_widths(
    tmp_path, monkeypatch
) -> None:
    row = _build_timer_row(tmp_path, monkeypatch)
    row._next_selectable_today_time = lambda _now: (12, 34, 56)

    row._on_pick_time_click(None)

    dialog = row._page.dialogs[-1]
    assert isinstance(dialog, ft.CupertinoBottomSheet)

    content = dialog.content
    assert isinstance(content, ft.Column)
    pickers_row = content.controls[1]
    assert isinstance(pickers_row, ft.Row)

    picker_columns = pickers_row.controls
    assert len(picker_columns) == 3
    picker_widths = [column.controls[1].width for column in picker_columns]
    assert picker_widths == [96, 96, 96]
