from __future__ import annotations

from enum import Enum


class CountdownState(str, Enum):
    IDLE = "idle"
    RUNNING = "running"
    PAUSED = "paused"


MAX_TOTAL_SECONDS = 86400


def format_duration(seconds: int) -> str:
    """将剩余秒数格式化为 HH:MM:SS。"""
    seconds = max(0, int(seconds))
    h, rem = divmod(seconds, 3600)
    m, s = divmod(rem, 60)
    return f"{h:02d}:{m:02d}:{s:02d}"


def format_duration_friendly_cn(seconds: int) -> str:
    """口语化中文时长，用于无名称时的通知文案。"""
    seconds = max(0, int(seconds))
    h, r = divmod(seconds, 3600)
    m, s = divmod(r, 60)
    if h and m and s:
        return f"{h}小时{m}分钟{s}秒"
    if h and m:
        return f"{h}小时{m}分钟"
    if h and s:
        return f"{h}小时{s}秒"
    if h:
        return f"{h}小时"
    if m and s:
        return f"{m}分钟{s}秒"
    if m:
        return f"{m}分钟"
    if s:
        return f"{s}秒"
    return "0秒"


def _parse_component(raw: str) -> tuple[int | None, str | None]:
    """解析时/分/秒字段。成功返回 (数值, None)，失败返回 (None, 错误信息)。"""
    s = raw.strip()
    if s == "":
        return 0, None
    try:
        v = int(s, 10)
        return v, None
    except ValueError:
        return None, "请输入非负整数（时/分/秒）"


class CountdownEngine:
    """与 UI 无关的倒计时状态机。"""

    def __init__(self) -> None:
        self._state = CountdownState.IDLE
        self._remaining = 0
        self._last_started_total: int | None = None

    @property
    def state(self) -> CountdownState:
        return self._state

    @property
    def remaining_seconds(self) -> int:
        return self._remaining

    @property
    def last_started_total_seconds(self) -> int | None:
        """本次最近一次成功「开始」时的总秒数；重置后清空。"""
        return self._last_started_total

    def start_from_inputs(
        self,
        hours_str: str,
        minutes_str: str,
        seconds_str: str,
    ) -> str | None:
        """
        从空闲状态开始倒计时（时、分、秒；分与秒须为 0–59）。
        成功返回 None；失败返回错误文案（不改变状态）。
        """
        if self._state is not CountdownState.IDLE:
            return "请先重置后再开始新的倒计时"

        h, err = _parse_component(hours_str)
        if err:
            return err
        m, err = _parse_component(minutes_str)
        if err:
            return err
        sec, err = _parse_component(seconds_str)
        if err:
            return err
        assert h is not None and m is not None and sec is not None

        if h < 0 or m < 0 or sec < 0:
            return "时、分、秒不能为负数"

        if m >= 60:
            return "分钟请小于 60，或换算到小时"
        if sec >= 60:
            return "秒数请小于 60，或换算到分钟"

        total = h * 3600 + m * 60 + sec
        if total <= 0:
            return "总时长必须大于 0"
        if total > MAX_TOTAL_SECONDS:
            return "总时长不能超过 24 小时"

        self._remaining = total
        self._last_started_total = total
        self._state = CountdownState.RUNNING
        return None

    def pause(self) -> None:
        if self._state is CountdownState.RUNNING:
            self._state = CountdownState.PAUSED

    def resume(self) -> None:
        if self._state is CountdownState.PAUSED:
            self._state = CountdownState.RUNNING

    def reset(self) -> None:
        self._state = CountdownState.IDLE
        self._remaining = 0
        self._last_started_total = None

    def tick_one_second(self) -> bool:
        """
        运行中每秒调用一次。
        若本次 tick 导致从运行中刚好走到结束，返回 True；否则 False。
        """
        if self._state is not CountdownState.RUNNING:
            return False
        if self._remaining <= 0:
            self._state = CountdownState.IDLE
            self._remaining = 0
            return False

        self._remaining -= 1
        if self._remaining <= 0:
            self._remaining = 0
            self._state = CountdownState.IDLE
            return True
        return False
