from __future__ import annotations

from collections.abc import Callable
from datetime import datetime, timedelta

import flet as ft

from countdown_app.recents_store import RecentsStore
from countdown_app.time_presets import TIME_PRESETS
from countdown_app.timer_engine import (
    CountdownEngine,
    CountdownState,
    format_duration,
    format_duration_friendly_cn,
    seconds_until_today_time,
)


class TimerRow:
    """单个倒计时行：引擎 + 控件绑定。"""

    def __init__(
        self,
        page: ft.Page,
        on_removed: Callable[["TimerRow"], None],
        can_remove: Callable[[], bool],
        recents: RecentsStore,
        on_recents_changed: Callable[[], None],
    ) -> None:
        self._page = page
        self._on_removed = on_removed
        self._can_remove = can_remove
        self._recents = recents
        self._on_recents_changed = on_recents_changed
        self.engine = CountdownEngine()

        _time_col_w = 72
        _gap = 8

        self.name_field = ft.TextField(
            hint_text="可选，如：煮面",
            max_length=32,
        )
        self.field_hours = ft.TextField(
            hint_text="0",
            width=_time_col_w,
            keyboard_type=ft.KeyboardType.NUMBER,
            text_align=ft.TextAlign.CENTER,
            input_filter=ft.NumbersOnlyInputFilter(),
            on_change=self._on_hours_change,
            on_focus=self._on_time_focus,
        )
        self.field_minutes = ft.TextField(
            hint_text="0",
            width=_time_col_w,
            keyboard_type=ft.KeyboardType.NUMBER,
            text_align=ft.TextAlign.CENTER,
            input_filter=ft.NumbersOnlyInputFilter(),
            on_change=self._on_minutes_change,
            on_focus=self._on_time_focus,
        )
        self.field_seconds = ft.TextField(
            hint_text="0–59",
            width=_time_col_w,
            keyboard_type=ft.KeyboardType.NUMBER,
            text_align=ft.TextAlign.CENTER,
            input_filter=ft.NumbersOnlyInputFilter(),
            on_change=self._on_seconds_change,
            on_focus=self._on_time_focus,
        )

        _hdr_style = ft.TextThemeStyle.LABEL_MEDIUM
        _hdr_color = ft.Colors.ON_SURFACE_VARIANT
        labels_row = ft.Row(
            spacing=_gap,
            controls=[
                ft.Container(
                    expand=1,
                    content=ft.Text(
                        "名称",
                        theme_style=_hdr_style,
                        color=_hdr_color,
                    ),
                ),
                ft.Container(
                    width=_time_col_w,
                    content=ft.Text(
                        "时",
                        theme_style=_hdr_style,
                        color=_hdr_color,
                        text_align=ft.TextAlign.CENTER,
                    ),
                ),
                ft.Container(
                    width=_time_col_w,
                    content=ft.Text(
                        "分",
                        theme_style=_hdr_style,
                        color=_hdr_color,
                        text_align=ft.TextAlign.CENTER,
                    ),
                ),
                ft.Container(
                    width=_time_col_w,
                    content=ft.Text(
                        "秒",
                        theme_style=_hdr_style,
                        color=_hdr_color,
                        text_align=ft.TextAlign.CENTER,
                    ),
                ),
            ],
        )
        inputs_row = ft.Row(
            spacing=_gap,
            vertical_alignment=ft.CrossAxisAlignment.START,
            controls=[
                ft.Container(expand=1, content=self.name_field),
                ft.Container(width=_time_col_w, content=self.field_hours),
                ft.Container(width=_time_col_w, content=self.field_minutes),
                ft.Container(width=_time_col_w, content=self.field_seconds),
            ],
        )
        self.txt_error = ft.Text(value="", color=ft.Colors.RED, size=12)
        self.lbl_time = ft.Text(
            value=format_duration(0),
            size=32,
            weight=ft.FontWeight.W_600,
        )
        self.btn_start = ft.Button(content="开始")
        self.btn_pause = ft.Button(content="暂停", disabled=True)
        self.btn_reset = ft.Button(content="重置", disabled=True)
        self.btn_remove = ft.Button(content="删除", disabled=True)

        self.btn_start.on_click = self._on_start
        self.btn_pause.on_click = self._on_pause
        self.btn_reset.on_click = self._on_reset
        self.btn_remove.on_click = self._on_remove_click

        def _preset_handler(hh: int, mm: int, ss: int):
            def _(_e: ft.ControlEvent) -> None:
                self._apply_hms(hh, mm, ss)

            return _

        self._preset_buttons: list[ft.OutlinedButton] = []
        for label, ph, pm, ps in TIME_PRESETS:
            self._preset_buttons.append(
                ft.OutlinedButton(
                    content=label,
                    on_click=_preset_handler(ph, pm, ps),
                )
            )

        self.btn_recent = ft.OutlinedButton(
            content="最近（暂无）",
            on_click=self._on_recent_click,
        )
        self.btn_pick_time = ft.OutlinedButton(
            content="选择时间点",
            on_click=self._on_pick_time_click,
        )

        shortcuts_row = ft.Row(
            [self.btn_recent, self.btn_pick_time, *self._preset_buttons],
            spacing=6,
            wrap=True,
        )

        inner = ft.Column(
            [
                labels_row,
                inputs_row,
                ft.Text(
                    "快捷时长",
                    size=12,
                    theme_style=ft.TextThemeStyle.LABEL_SMALL,
                    color=ft.Colors.ON_SURFACE_VARIANT,
                ),
                shortcuts_row,
                ft.Row(
                    [self.lbl_time],
                    alignment=ft.MainAxisAlignment.CENTER,
                ),
                self.txt_error,
                ft.Row(
                    [
                        self.btn_start,
                        self.btn_pause,
                        self.btn_reset,
                        self.btn_remove,
                    ],
                    spacing=8,
                    wrap=True,
                ),
            ],
            spacing=8,
        )

        self.root = ft.Container(
            content=inner,
            padding=ft.Padding.symmetric(horizontal=12, vertical=10),
            border=ft.Border.all(1, ft.Colors.OUTLINE_VARIANT),
            border_radius=8,
            margin=ft.Margin.only(bottom=4),
        )

    def title(self) -> str:
        n = (self.name_field.value or "").strip()
        return n if n else "未命名倒计时"

    def finish_notification_line(self) -> str:
        """结束通知/弹窗单行文案：含名称+时长，或无名称时的口语化时长。"""
        total = self.engine.last_started_total_seconds or 0
        clock = format_duration(total)
        human = format_duration_friendly_cn(total)
        name = (self.name_field.value or "").strip()
        if name:
            return f"「{name}」（{clock}）倒计时已结束"
        return f"{human}（{clock}）倒计时已结束"

    def _clear_error(self) -> None:
        self.txt_error.value = ""
        self.field_hours.error = None
        self.field_minutes.error = None
        self.field_seconds.error = None

    def _show_error(self, msg: str) -> None:
        self.txt_error.value = msg

    def _on_hours_change(self, _: ft.ControlEvent) -> None:
        self._sanitize_time_input(self.field_hours)

    def _on_minutes_change(self, _: ft.ControlEvent) -> None:
        self._sanitize_time_input(self.field_minutes)

    def _on_seconds_change(self, _: ft.ControlEvent) -> None:
        self._sanitize_time_input(self.field_seconds)

    def _on_time_focus(self, e: ft.ControlEvent) -> None:
        c = e.control
        if isinstance(c, ft.TextField) and c.error is not None:
            c.error = None
            self._page.update()

    def _sanitize_time_input(self, field: ft.TextField) -> None:
        raw = field.value or ""
        had_minus = any(
            ch in raw for ch in ("-", "\u2212", "\u2013", "\u2014")
        )
        cleaned = "".join(c for c in raw if c.isdigit())
        if had_minus:
            field.value = cleaned
            field.error = "不能输入负数"
            self._page.update()
            return
        if raw != cleaned:
            field.value = cleaned
            field.error = "仅允许输入 0–9"
            self._page.update()
            return
        field.error = None
        self._page.update()

    def _on_recent_click(self, _: ft.ControlEvent) -> None:
        mr = self._recents.most_recent()
        if mr is None:
            return
        self._apply_hms(*mr)

    def _can_edit_duration(self) -> bool:
        return (
            self.engine.state is CountdownState.IDLE
            and self.engine.remaining_seconds == 0
        )

    def _apply_hms(self, h: int, m: int, s: int) -> None:
        if not self._can_edit_duration():
            return
        self._clear_error()
        self.field_hours.value = str(h)
        self.field_minutes.value = str(m)
        self.field_seconds.value = str(s)
        self._page.update()

    def _next_selectable_today_time(
        self, now: datetime
    ) -> tuple[int, int, int] | None:
        next_second = now.replace(microsecond=0) + timedelta(seconds=1)
        if next_second.date() != now.date():
            return None
        return next_second.hour, next_second.minute, next_second.second

    def _sync_picker_text_styles(
        self, picker: ft.CupertinoPicker, texts: list[ft.Text]
    ) -> None:
        selected = picker.selected_index
        for idx, text in enumerate(texts):
            is_selected = idx == selected
            text.color = (
                ft.Colors.ON_SURFACE if is_selected else ft.Colors.ON_SURFACE_VARIANT
            )
            text.weight = (
                ft.FontWeight.W_700 if is_selected else ft.FontWeight.W_500
            )
            text.size = 22 if is_selected else 18

    def _build_time_picker(
        self,
        label: str,
        max_value: int,
        selected_index: int,
    ) -> tuple[ft.Column, ft.CupertinoPicker]:
        texts = [
            ft.Text(
                f"{value:02d}",
                text_align=ft.TextAlign.CENTER,
                color=ft.Colors.ON_SURFACE_VARIANT,
                weight=ft.FontWeight.W_500,
                size=18,
            )
            for value in range(max_value + 1)
        ]
        picker = ft.CupertinoPicker(
            controls=texts,
            selected_index=selected_index,
            item_extent=36,
            width=96,
            height=180,
            use_magnifier=True,
            magnification=1.08,
            squeeze=1.15,
        )

        def on_change(_: ft.ControlEvent) -> None:
            self._sync_picker_text_styles(picker, texts)
            self._page.update()

        picker.on_change = on_change
        self._sync_picker_text_styles(picker, texts)

        column = ft.Column(
            [
                ft.Text(
                    label,
                    size=12,
                    theme_style=ft.TextThemeStyle.LABEL_SMALL,
                    color=ft.Colors.ON_SURFACE_VARIANT,
                    text_align=ft.TextAlign.CENTER,
                ),
                picker,
            ],
            spacing=8,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            tight=True,
        )
        return column, picker

    def _dismiss_dialog(self) -> None:
        try:
            self._page.pop_dialog()
        except Exception:
            pass

    def _apply_selected_today_time(
        self,
        hour: int,
        minute: int,
        second: int,
        *,
        now: datetime | None = None,
    ) -> bool:
        if not self._can_edit_duration():
            return False
        current = now or datetime.now()
        remaining = seconds_until_today_time(current, hour, minute, second)
        if remaining is None:
            self._show_error("该时间点已过去，请重新选择")
            self._page.update()
            return False
        hh, rem = divmod(remaining, 3600)
        mm, ss = divmod(rem, 60)
        self._apply_hms(hh, mm, ss)
        return True

    def _on_pick_time_click(self, _: ft.ControlEvent) -> None:
        if not self._can_edit_duration():
            return
        default_selection = self._next_selectable_today_time(datetime.now())
        if default_selection is None:
            self._show_error("今天已没有可选时间点，请直接输入时长")
            self._page.update()
            return

        hour_column, hour_picker = self._build_time_picker(
            "时", 23, default_selection[0]
        )
        minute_column, minute_picker = self._build_time_picker(
            "分", 59, default_selection[1]
        )
        second_column, second_picker = self._build_time_picker(
            "秒", 59, default_selection[2]
        )

        def on_confirm(_: ft.ControlEvent) -> None:
            ok = self._apply_selected_today_time(
                hour_picker.selected_index,
                minute_picker.selected_index,
                second_picker.selected_index,
            )
            if ok:
                self._dismiss_dialog()

        sheet_content = ft.Column(
            [
                ft.Text(
                    "滚动选择今天稍后的时、分、秒，确认后仅回填倒计时时长。",
                    size=13,
                    color=ft.Colors.ON_SURFACE_VARIANT,
                    text_align=ft.TextAlign.CENTER,
                ),
                ft.Row(
                    [hour_column, minute_column, second_column],
                    alignment=ft.MainAxisAlignment.CENTER,
                    spacing=16,
                ),
                ft.Row(
                    [
                        ft.CupertinoButton(
                            content="取消",
                            color=ft.Colors.ON_SURFACE_VARIANT,
                            on_click=lambda _: self._dismiss_dialog(),
                        ),
                        ft.CupertinoButton(
                            content="确定",
                            on_click=on_confirm,
                        ),
                    ],
                    alignment=ft.MainAxisAlignment.END,
                ),
            ],
            tight=True,
            spacing=12,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        )

        self._page.show_dialog(
            ft.CupertinoBottomSheet(
                modal=True,
                height=320,
                padding=ft.Padding.only(left=16, top=16, right=16, bottom=20),
                content=sheet_content,
            )
        )

    def _refresh_shortcut_buttons(self) -> None:
        can_edit = self._can_edit_duration()
        mr = self._recents.most_recent()
        self.btn_recent.disabled = not can_edit or mr is None
        self.btn_pick_time.disabled = not can_edit
        if mr is None:
            self.btn_recent.content = "最近（暂无）"
        else:
            hh, mm, ss = mr
            self.btn_recent.content = (
                f"最近 {format_duration(hh * 3600 + mm * 60 + ss)}"
            )
        for b in self._preset_buttons:
            b.disabled = not can_edit

    def refresh_controls(self) -> None:
        st = self.engine.state
        self.lbl_time.value = format_duration(self.engine.remaining_seconds)
        rem0 = self.engine.remaining_seconds == 0

        if st is CountdownState.IDLE and rem0:
            self.btn_start.content = "开始"
            self.btn_start.disabled = False
            self.btn_pause.disabled = True
            self.btn_reset.disabled = True
            self.btn_remove.disabled = not self._can_remove()
            self.name_field.disabled = False
            self.field_hours.disabled = False
            self.field_minutes.disabled = False
            self.field_seconds.disabled = False
        elif st is CountdownState.RUNNING:
            self.btn_start.disabled = True
            self.btn_pause.disabled = False
            self.btn_reset.disabled = False
            self.btn_remove.disabled = True
            self.name_field.disabled = True
            self.field_hours.disabled = True
            self.field_minutes.disabled = True
            self.field_seconds.disabled = True
        elif st is CountdownState.PAUSED:
            self.btn_start.content = "继续"
            self.btn_start.disabled = False
            self.btn_pause.disabled = True
            self.btn_reset.disabled = False
            self.btn_remove.disabled = True
            self.name_field.disabled = True
            self.field_hours.disabled = True
            self.field_minutes.disabled = True
            self.field_seconds.disabled = True

        self._refresh_shortcut_buttons()

    def _on_start(self, _: ft.ControlEvent) -> None:
        self._clear_error()
        if self.engine.state is CountdownState.PAUSED:
            self.engine.resume()
            self.refresh_controls()
            self._page.update()
            return
        err = self.engine.start_from_inputs(
            self.field_hours.value or "",
            self.field_minutes.value or "",
            self.field_seconds.value or "",
        )
        if err:
            self._show_error(err)
            self._page.update()
            return
        self._recents.remember_from_total_seconds(self.engine.remaining_seconds)
        self._on_recents_changed()

    def _on_pause(self, _: ft.ControlEvent) -> None:
        self.engine.pause()
        self.refresh_controls()
        self._page.update()

    def _on_reset(self, _: ft.ControlEvent) -> None:
        self._clear_error()
        self.engine.reset()
        self.refresh_controls()
        self._page.update()

    def _on_remove_click(self, _: ft.ControlEvent) -> None:
        if self.engine.state is not CountdownState.IDLE or self.engine.remaining_seconds != 0:
            return
        if not self._can_remove():
            return
        self._on_removed(self)
