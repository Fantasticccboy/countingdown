from __future__ import annotations

import os
import sys
import threading
from collections.abc import Callable
from pathlib import Path
from queue import Empty, Queue
from typing import Any

_UI_QUEUE: Queue[Callable[[], None]] = Queue()
_TRAY_ICON: Any = {"icon": None}
_TRAY_THREAD: Any = {"thread": None}

# Windows：winotify 点击 Toast 时通过命名管道唤醒主进程（需 init + pump）
_WINOTIFY_NOTIFIER: Any = None
_TOAST_CLICK_HANDLER: Callable[[], None] | None = None
_WINOTIFY_OPEN_CB: Callable[[], None] | None = None


def enqueue_ui(fn: Callable[[], None]) -> None:
    """从托盘等非 UI 线程把操作投递到 Flet 主循环侧执行。"""
    _UI_QUEUE.put(fn)


def drain_ui_queue_once() -> None:
    while True:
        try:
            fn = _UI_QUEUE.get_nowait()
        except Empty:
            break
        try:
            fn()
        except Exception:
            pass


def winotify_listener_pump() -> None:
    """在主循环中调用，使 run_in_main_thread 的 Toast 点击回调得以执行。"""
    n = _WINOTIFY_NOTIFIER
    if n is None:
        return
    try:
        n.update()
    except Exception:
        pass


def set_toast_click_handler(handler: Callable[[], None] | None) -> None:
    """主进程内设置：用户点击 Toast 正文时执行（通常应 enqueue_ui + 显示窗口）。"""
    global _TOAST_CLICK_HANDLER
    _TOAST_CLICK_HANDLER = handler


def init_winotify_listener(app_id: str, script_path: str) -> bool:
    """
    注册 URL 协议并启动监听线程，使 Windows Toast 的 launch 能连回本进程。
    script_path 一般为入口 .py 的绝对路径；打包为 exe 时传 sys.executable。
    """
    global _WINOTIFY_NOTIFIER, _WINOTIFY_OPEN_CB
    if sys.platform != "win32" or _WINOTIFY_NOTIFIER is not None:
        return _WINOTIFY_NOTIFIER is not None
    try:
        from winotify import Notifier, Registry
    except Exception:
        return False
    path_abs = os.path.abspath(script_path)
    try:
        reg = Registry(app_id, script_path=path_abs)
        n = Notifier(reg)

        def _on_toast_open() -> None:
            h = _TOAST_CLICK_HANDLER
            if h:
                h()

        n.register_callback(_on_toast_open, run_in_main_thread=True)
        n.start()
        _WINOTIFY_NOTIFIER = n
        _WINOTIFY_OPEN_CB = _on_toast_open
        return True
    except Exception:
        _WINOTIFY_NOTIFIER = None
        _WINOTIFY_OPEN_CB = None
        return False


def notify_countdown_finished(body: str) -> None:
    """系统级通知（优先 Windows Toast；已 init winotify 时支持点击打开应用）。"""
    title = "倒计时结束"
    base = (body or "").strip() or "时间到。"
    hint = "\n（点击通知打开应用）"
    text_plain = base[:253] + "..." if len(base) > 256 else base
    text_clickable = base + hint
    if len(text_clickable) > 256:
        text_clickable = text_clickable[:253] + "..."
    if sys.platform == "win32":
        n = _WINOTIFY_NOTIFIER
        cb = _WINOTIFY_OPEN_CB
        if n is not None and cb is not None:
            try:
                toast = n.create_notification(
                    title=title,
                    msg=text_clickable,
                    launch=cb,
                )
                toast.show()
                return
            except Exception:
                pass
        try:
            from winotify import Notification

            toast = Notification(app_id="多倒计时", title=title, msg=text_plain)
            toast.show()
            return
        except Exception:
            pass
    try:
        from plyer import notification

        notification.notify(title=title, message=text_plain, app_name="多倒计时", timeout=6)
    except Exception:
        pass


def entry_script_path_for_winotify(main_file: str) -> str:
    """供 Registry 使用的入口路径：冻结 exe 用可执行文件，否则用 main 模块路径。"""
    if getattr(sys, "frozen", False):
        return os.path.abspath(sys.executable)
    return str(Path(main_file).resolve())


def _resolve_assets_ico_path() -> Path | None:
    """与主窗口/exe 相同：assets/countdown.ico 或 app.ico（开发目录或 PyInstaller _MEIPASS）。"""
    if getattr(sys, "frozen", False):
        meipass = getattr(sys, "_MEIPASS", None)
        if not meipass:
            return None
        base = Path(meipass)
    else:
        base = Path(__file__).resolve().parent.parent.parent
    for name in ("countdown.ico", "app.ico"):
        p = base / "assets" / name
        if p.is_file():
            return p
    return None


def _tray_image():
    """托盘图标尽量与 assets 中 ico 一致；缺失时回退为简单占位图。"""
    from PIL import Image, ImageDraw

    path = _resolve_assets_ico_path()
    if path is not None:
        try:
            img = Image.open(path)
            img.load()
            if getattr(img, "n_frames", 1) > 1:
                try:
                    best = None
                    best_area = 0
                    for i in range(img.n_frames):
                        img.seek(i)
                        w, h = img.size
                        a = w * h
                        if 16 <= w <= 256 and a > best_area:
                            best = img.copy()
                            best_area = a
                    if best is not None:
                        img = best
                except Exception:
                    img.seek(0)
            target = 64
            if img.size[0] != target or img.size[1] != target:
                try:
                    resample = Image.Resampling.LANCZOS
                except AttributeError:
                    resample = Image.LANCZOS  # type: ignore[attr-defined]
                img = img.resize((target, target), resample)
            return img.convert("RGBA")
        except Exception:
            pass

    w = 64
    img = Image.new("RGBA", (w, w), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    draw.ellipse((6, 6, w - 6, w - 6), fill=(211, 47, 47, 255))
    return img


def _stop_tray_icon() -> None:
    ic = _TRAY_ICON.get("icon")
    if ic is not None:
        try:
            ic.stop()
        except Exception:
            pass
        _TRAY_ICON["icon"] = None
    _TRAY_THREAD["thread"] = None


def start_tray(
    on_show: Callable[[], None],
    on_quit: Callable[[], None],
) -> None:
    """在 Windows 桌面启动托盘图标（仅 Windows；失败则静默）。"""
    if sys.platform != "win32":
        return
    if _TRAY_ICON["icon"] is not None:
        return
    try:
        import pystray
        from pystray import MenuItem as item
    except Exception:
        return

    def _show(_icon, _item) -> None:
        enqueue_ui(on_show)

    def _quit(_icon, _item) -> None:
        enqueue_ui(on_quit)

    # Windows：左键单击托盘图标会执行 default=True 的项（与常见「单击打开」一致；双击会先触发单击）
    menu = pystray.Menu(
        item("显示主窗口", _show, default=True),
        item("退出", _quit),
    )
    icon = pystray.Icon("countdown_app", _tray_image(), "多倒计时", menu)
    _TRAY_ICON["icon"] = icon

    def _run() -> None:
        try:
            icon.run()
        except Exception:
            pass

    t = threading.Thread(target=_run, daemon=True)
    _TRAY_THREAD["thread"] = t
    t.start()


def stop_tray() -> None:
    _stop_tray_icon()
