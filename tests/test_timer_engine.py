from countdown_app.timer_engine import (
    MAX_TOTAL_SECONDS,
    CountdownEngine,
    CountdownState,
    format_duration,
    format_duration_friendly_cn,
)


def test_format_duration() -> None:
    assert format_duration(0) == "00:00:00"
    assert format_duration(65) == "00:01:05"
    assert format_duration(3600) == "01:00:00"
    assert format_duration(3661) == "01:01:01"
    assert format_duration(-3) == "00:00:00"


def test_format_duration_friendly_cn() -> None:
    assert format_duration_friendly_cn(0) == "0秒"
    assert format_duration_friendly_cn(600) == "10分钟"
    assert format_duration_friendly_cn(65) == "1分钟5秒"
    assert format_duration_friendly_cn(3600) == "1小时"
    assert format_duration_friendly_cn(3661) == "1小时1分钟1秒"


def test_last_started_total_cleared_on_reset() -> None:
    e = CountdownEngine()
    assert e.last_started_total_seconds is None
    assert e.start_from_inputs("0", "10", "0") is None
    assert e.last_started_total_seconds == 600
    e.reset()
    assert e.last_started_total_seconds is None


def test_t1_start_zero_rejected() -> None:
    e = CountdownEngine()
    assert e.start_from_inputs("0", "0", "0") is not None
    assert e.state is CountdownState.IDLE
    assert e.remaining_seconds == 0


def test_t2_start_one_five() -> None:
    e = CountdownEngine()
    assert e.start_from_inputs("0", "1", "5") is None
    assert e.state is CountdownState.RUNNING
    assert e.remaining_seconds == 65


def test_t3_ticks_to_finish() -> None:
    e = CountdownEngine()
    assert e.start_from_inputs("0", "1", "5") is None
    finished_once = False
    for _ in range(65):
        if e.tick_one_second():
            finished_once = True
    assert finished_once
    assert e.state is CountdownState.IDLE
    assert e.remaining_seconds == 0


def test_t4_pause_freezes_time() -> None:
    e = CountdownEngine()
    assert e.start_from_inputs("0", "0", "10") is None
    e.pause()
    for _ in range(20):
        e.tick_one_second()
    assert e.remaining_seconds == 10
    assert e.state is CountdownState.PAUSED


def test_t5_resume_then_tick() -> None:
    e = CountdownEngine()
    assert e.start_from_inputs("0", "0", "10") is None
    e.pause()
    e.resume()
    e.tick_one_second()
    assert e.remaining_seconds == 9


def test_t6_reset() -> None:
    e = CountdownEngine()
    assert e.start_from_inputs("0", "0", "5") is None
    e.reset()
    assert e.state is CountdownState.IDLE
    assert e.remaining_seconds == 0


def test_t7_invalid_minutes() -> None:
    e = CountdownEngine()
    assert e.start_from_inputs("0", "abc", "0") is not None
    assert e.state is CountdownState.IDLE


def test_t8_exceeds_max() -> None:
    e = CountdownEngine()
    minutes = str(MAX_TOTAL_SECONDS // 60 + 1)
    assert e.start_from_inputs("0", minutes, "0") is not None
    assert e.state is CountdownState.IDLE


def test_seconds_must_be_under_60() -> None:
    e = CountdownEngine()
    assert e.start_from_inputs("0", "0", "90") is not None
    assert e.state is CountdownState.IDLE


def test_minutes_must_be_under_60() -> None:
    e = CountdownEngine()
    assert e.start_from_inputs("0", "90", "0") is not None
    assert e.state is CountdownState.IDLE


def test_whitespace_trimmed() -> None:
    e = CountdownEngine()
    assert e.start_from_inputs("0", " 1 ", " 5 ") is None
    assert e.remaining_seconds == 65


def test_one_hour() -> None:
    e = CountdownEngine()
    assert e.start_from_inputs("1", "0", "0") is None
    assert e.remaining_seconds == 3600
    assert format_duration(e.remaining_seconds) == "01:00:00"


def test_combined_hms() -> None:
    e = CountdownEngine()
    assert e.start_from_inputs("1", "2", "3") is None
    assert e.remaining_seconds == 3600 + 120 + 3
