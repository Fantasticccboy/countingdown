from __future__ import annotations

import asyncio
import os
import sys
import time
from pathlib import Path

# 允许从仓库根目录执行：python src/countdown_app/main.py
_src_root = Path(__file__).resolve().parent.parent
if str(_src_root) not in sys.path:
    sys.path.insert(0, str(_src_root))


def _prefer_bundled_flet_desktop() -> None:
    """
    PyInstaller 包内已含 flet_desktop/app（flet pack 时打入）。
    若不设置 FLET_VIEW_PATH，flet_desktop 会走 ensure_client_cached()，
    在用户目录无缓存时从 GitHub 拉取 zip。此处优先指向包内 flet.exe，实现离线启动。
    """
    if sys.platform != "win32":
        return
    if getattr(sys, "frozen", False):
        meipass = getattr(sys, "_MEIPASS", None)
        if meipass:
            bundled = Path(meipass) / "flet_desktop" / "app" / "flet" / "flet.exe"
            if bundled.is_file():
                os.environ.setdefault("FLET_VIEW_PATH", str(bundled.parent))


_prefer_bundled_flet_desktop()

import flet as ft

from countdown_app import desktop_integration
from countdown_app.recents_store import RecentsStore
from countdown_app.settings_store import SettingsStore
from countdown_app.timer_row import TimerRow

MAX_TIMERS = 20


def _resolve_app_icon_path() -> str | None:
    """
    与 exe 使用同一套图标：仓库根目录 assets/ 下任一则可（优先 countdown.ico）。
    打包时请 -i 指向同一文件，并附带 --add-data（见 README）。
    """
    if sys.platform != "win32":
        return None
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
            try:
                return str(p.resolve())
            except OSError:
                return str(p)
    return None


def _apply_window_icon(page: ft.Page) -> None:
    """设置原生窗口图标；路径用绝对路径，避免打包后相对路径失效。"""
    ico = _resolve_app_icon_path()
    if not ico:
        return
    page.window.icon = ico


async def main(page: ft.Page) -> None:
    page.title = "多倒计时"
    store = SettingsStore()
    stop_tick = [True]
    last_geom_save = [0.0]
    close_dialog_open = [False]

    rows: list[TimerRow] = []
    recents_store = RecentsStore()

    timers_column = ft.Column(spacing=0, scroll=ft.ScrollMode.AUTO, expand=True)

    def notify_recents_changed() -> None:
        for r in rows:
            r.refresh_controls()
        page.update()

    def sync_add_button() -> None:
        btn_add.disabled = len(rows) >= MAX_TIMERS

    def remove_row(tr: TimerRow) -> None:
        rows.remove(tr)
        timers_column.controls.remove(tr.root)
        for r in rows:
            r.refresh_controls()
        sync_add_button()
        page.update()

    def add_row() -> None:
        if len(rows) >= MAX_TIMERS:
            return
        tr = TimerRow(
            page,
            remove_row,
            lambda: len(rows) > 1,
            recents_store,
            notify_recents_changed,
        )
        rows.append(tr)
        timers_column.controls.append(tr.root)
        for r in rows:
            r.refresh_controls()
        sync_add_button()
        page.update()

    def on_add(_: ft.ControlEvent) -> None:
        add_row()

    btn_add = ft.Button(
        content="添加倒计时",
        icon=ft.Icons.ADD,
        on_click=on_add,
    )

    async def show_and_front() -> None:
        page.window.visible = True
        page.window.skip_task_bar = False
        page.update()
        try:
            await page.window.to_front()
        except Exception:
            pass

    def sync_window_into_store() -> None:
        if page.web:
            return
        try:
            wl = page.window.left
            wt = page.window.top
            ww = page.window.width
            wh = page.window.height
            if wl is None or wt is None or ww is None or wh is None:
                return
            store.save_window_rect(float(wl), float(wt), float(ww), float(wh))
        except (TypeError, ValueError):
            pass

    async def shutdown_app() -> None:
        stop_tick[0] = False
        desktop_integration.stop_tray()
        sync_window_into_store()
        try:
            await page.window.destroy()
        except Exception:
            os._exit(0)

    def tray_show() -> None:
        desktop_integration.enqueue_ui(lambda: page.run_task(show_and_front))

    def tray_quit() -> None:
        desktop_integration.enqueue_ui(lambda: page.run_task(shutdown_app))

    def hide_to_tray() -> None:
        if page.web:
            return
        page.window.visible = False
        page.window.skip_task_bar = True
        desktop_integration.start_tray(tray_show, tray_quit)
        page.update()

    def maybe_save_window_geom() -> None:
        if page.web:
            return
        now = time.monotonic()
        if now - last_geom_save[0] < 0.35:
            return
        last_geom_save[0] = now
        try:
            wl = page.window.left
            wt = page.window.top
            ww = page.window.width
            wh = page.window.height
            if wl is None or wt is None or ww is None or wh is None:
                return
            store.save_window_rect(float(wl), float(wt), float(ww), float(wh))
        except (TypeError, ValueError):
            pass

    def apply_remembered_close_behavior() -> None:
        if store.settings.close_behavior_is_tray:
            hide_to_tray()
        else:
            page.run_task(shutdown_app)

    def show_close_choice_dialog() -> None:
        if page.web or close_dialog_open[0]:
            return
        close_dialog_open[0] = True
        chk_remember = ft.Checkbox(label="记住我的选择", value=False)
        close_popped = [False]

        def dismiss() -> None:
            close_dialog_open[0] = False
            if close_popped[0]:
                return
            close_popped[0] = True
            try:
                page.pop_dialog()
            except Exception:
                pass

        def on_tray(_: ft.ControlEvent) -> None:
            if chk_remember.value:
                store.settings.close_behavior_remembered = True
                store.settings.close_behavior_is_tray = True
                store.save()
            dismiss()
            hide_to_tray()

        def on_quit(_: ft.ControlEvent) -> None:
            if chk_remember.value:
                store.settings.close_behavior_remembered = True
                store.settings.close_behavior_is_tray = False
                store.save()
            dismiss()
            page.run_task(shutdown_app)

        page.show_dialog(
            ft.AlertDialog(
                title=ft.Text("关闭窗口"),
                content=ft.Column(
                    [
                        ft.Text("请选择关闭方式："),
                        chk_remember,
                    ],
                    tight=True,
                    spacing=12,
                ),
                actions=[
                    ft.TextButton(content="隐藏到托盘", on_click=on_tray),
                    ft.TextButton(content="退出应用", on_click=on_quit),
                ],
                on_dismiss=lambda _: dismiss(),
            )
        )

    def on_window_event(e: ft.WindowEvent) -> None:
        if page.web:
            return
        if e.type in (ft.WindowEventType.MOVED, ft.WindowEventType.RESIZED):
            maybe_save_window_geom()
        elif e.type == ft.WindowEventType.CLOSE:
            if store.settings.close_behavior_remembered:
                apply_remembered_close_behavior()
            else:
                show_close_choice_dialog()

    def on_page_close(_: ft.ControlEvent) -> None:
        stop_tick[0] = False
        desktop_integration.stop_tray()

    def refresh_pin_button() -> None:
        on = (
            page.window.always_on_top
            if not page.web
            else store.settings.always_on_top
        )
        btn_pin.icon = ft.Icons.PUSH_PIN if on else ft.Icons.PUSH_PIN_OUTLINED
        btn_pin.tooltip = "已置顶（点击取消）" if on else "窗口置顶"
        try:
            btn_pin.update()
        except Exception:
            pass

    def on_pin_click(_: ft.ControlEvent) -> None:
        if page.web:
            return
        store.settings.always_on_top = not store.settings.always_on_top
        store.save()
        page.window.always_on_top = store.settings.always_on_top
        refresh_pin_button()
        page.update()

    btn_pin = ft.IconButton(
        icon=(
            ft.Icons.PUSH_PIN
            if store.settings.always_on_top
            else ft.Icons.PUSH_PIN_OUTLINED
        ),
        tooltip=(
            "已置顶（点击取消）"
            if store.settings.always_on_top
            else "窗口置顶"
        ),
        on_click=on_pin_click,
    )

    if page.web:
        btn_pin.disabled = True

    page.window.width = int(store.settings.window_width or 580)
    page.window.height = int(store.settings.window_height or 720)
    if not page.web:
        _apply_window_icon(page)
        page.window.always_on_top = store.settings.always_on_top
        page.window.prevent_close = True
        page.window.on_event = on_window_event
        if store.settings.has_saved_window_rect():
            page.window.left = store.settings.window_left
            page.window.top = store.settings.window_top
            page.window.width = int(store.settings.window_width or 580)
            page.window.height = int(store.settings.window_height or 720)

    page.on_close = on_page_close

    add_row()

    page.add(
        ft.Column(
            [
                ft.Row(
                    [
                        ft.Text("多倒计时", size=22, weight=ft.FontWeight.W_500),
                        ft.Row(
                            [btn_pin, btn_add],
                            spacing=4,
                            tight=True,
                        ),
                    ],
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                ),
                timers_column,
            ],
            expand=True,
            spacing=12,
        )
    )

    if not page.web and sys.platform == "win32":
        desktop_integration.set_toast_click_handler(
            lambda: desktop_integration.enqueue_ui(
                lambda: page.run_task(show_and_front)
            )
        )
        desktop_integration.init_winotify_listener(
            "多倒计时",
            desktop_integration.entry_script_path_for_winotify(__file__),
        )

    async def ui_pump() -> None:
        while stop_tick[0]:
            desktop_integration.drain_ui_queue_once()
            desktop_integration.winotify_listener_pump()
            await asyncio.sleep(0.08)

    async def tick_loop() -> None:
        while stop_tick[0]:
            await asyncio.sleep(1)
            if not stop_tick[0]:
                break
            finished_lines: list[str] = []
            for tr in rows:
                if tr.engine.tick_one_second():
                    finished_lines.append(tr.finish_notification_line())
                tr.refresh_controls()
            page.update()
            if finished_lines:
                finish_popped = [False]

                def dismiss_finish(_=None) -> None:
                    if finish_popped[0]:
                        return
                    finish_popped[0] = True
                    if not page.web:
                        page.window.always_on_top = store.settings.always_on_top
                        refresh_pin_button()
                    try:
                        page.pop_dialog()
                    except Exception:
                        pass

                body = "\n".join(f"· {line}" for line in finished_lines)
                if not page.web:
                    page.window.always_on_top = True
                    refresh_pin_button()
                    await show_and_front()
                desktop_integration.notify_countdown_finished(body)
                page.show_dialog(
                    ft.AlertDialog(
                        title=ft.Text("倒计时结束"),
                        content=ft.Text(body),
                        actions=[
                            ft.TextButton(
                                content="确定",
                                on_click=dismiss_finish,
                            ),
                        ],
                        on_dismiss=dismiss_finish,
                    )
                )

    sync_add_button()
    page.update()

    if not page.web:
        if not store.settings.has_saved_window_rect():
            await page.window.center()

    async def reapply_window_icon_after_ready() -> None:
        """Flet 桌面壳就绪后再设一次图标，并避开首帧路径未就绪的情况。"""
        await asyncio.sleep(0.25)
        if not page.web:
            _apply_window_icon(page)
            page.update()

    page.run_task(ui_pump)
    page.run_task(tick_loop)
    if not page.web:
        page.run_task(reapply_window_icon_after_ready)


def _apply_github_download_proxy() -> None:
    """
    flet_desktop 用环境变量 FLET_CLIENT_URL 覆盖默认 GitHub 下载地址。
    若只配置了「代理前缀」，在此拼出完整 URL（与常见 GitHub 文件加速站用法一致）。
    已设置 FLET_CLIENT_URL 时不修改。
    """
    if os.environ.get("FLET_CLIENT_URL"):
        return
    proxy = (
        os.environ.get("FLET_GITHUB_PROXY", "").strip().rstrip("/")
        or os.environ.get("COUNTDOWN_GITHUB_PROXY", "").strip().rstrip("/")
    )
    if not proxy:
        return
    import flet_desktop.version as _fdv

    ver = _fdv.version
    if sys.platform == "win32":
        artifact = "flet-windows.zip"
    elif sys.platform == "darwin":
        artifact = "flet-macos.tar.gz"
    else:
        # Linux 包名与发行版相关，请直接设置 FLET_CLIENT_URL
        return
    upstream = (
        f"https://github.com/flet-dev/flet/releases/download/v{ver}/{artifact}"
    )
    os.environ["FLET_CLIENT_URL"] = f"{proxy}/{upstream}"


def _patch_flet_desktop_download_headers() -> None:
    """
    flet_desktop 用 urllib.request.urlretrieve 拉取 zip，默认 User-Agent 含 Python-urllib，
    常被 GitHub、CDN、第三方加速站直接 403。在进程内替换为浏览器 UA（可用环境变量覆盖）。
    """
    if os.environ.get("FLET_SKIP_DOWNLOAD_UA_PATCH", "").strip().lower() in (
        "1",
        "true",
        "yes",
    ):
        return

    import urllib.error
    import urllib.request

    _default_ua = (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
    )
    _ua = os.environ.get("FLET_DOWNLOAD_USER_AGENT", "").strip() or _default_ua

    _orig = urllib.request.urlretrieve

    def _urlretrieve(
        url: str,
        filename: str | None = None,
        reporthook=None,
        data: bytes | None = None,
    ):
        if filename is None:
            return _orig(url, filename, reporthook, data)

        req = urllib.request.Request(
            url,
            data=data,
            headers={
                "User-Agent": _ua,
                "Accept": "*/*",
                "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
            },
        )
        try:
            with urllib.request.urlopen(req, timeout=600) as resp:
                hdrs = resp.headers
                bs = 8 * 1024
                size = -1
                if "Content-Length" in hdrs:
                    size = int(hdrs["Content-Length"])
                read = 0
                blocknum = 0
                if reporthook is not None:
                    reporthook(blocknum, bs, size)
                with open(filename, "wb") as out:
                    while True:
                        chunk = resp.read(bs)
                        if not chunk:
                            break
                        read += len(chunk)
                        out.write(chunk)
                        blocknum += 1
                        if reporthook is not None:
                            reporthook(blocknum, bs, size)
                if size >= 0 and read < size:
                    raise urllib.error.ContentTooShortError(
                        "retrieval incomplete: got only %i out of %i bytes"
                        % (read, size),
                        (filename, hdrs),
                    )
                return filename, hdrs
        except Exception:
            if os.path.isfile(filename):
                try:
                    os.remove(filename)
                except OSError:
                    pass
            raise

    urllib.request.urlretrieve = _urlretrieve


if __name__ == "__main__":
    _patch_flet_desktop_download_headers()
    _apply_github_download_proxy()
    # 打包后已优先 FLET_VIEW_PATH 指向包内 flet；开发机无缓存时仍可能下载 zip。
    # 网络不稳时可改用浏览器调试：
    #   set COUNTDOWN_FLET_WEB=1
    #   python src/countdown_app/main.py
    _web = os.environ.get("COUNTDOWN_FLET_WEB", "").strip().lower() in (
        "1",
        "true",
        "yes",
    )
    ft.run(main, view=ft.AppView.WEB_BROWSER if _web else ft.AppView.FLET_APP)
