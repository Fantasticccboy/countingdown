"""
保证桌面应用全局仅运行一个实例（重复启动时退出）。

Windows：命名互斥体（Named Mutex）。
其他平台：绑定本机固定回环端口（若需多开调试可设环境变量 COUNTDOWN_ALLOW_MULTI=1）。
"""

from __future__ import annotations

import os
import socket
import sys

_ERROR_ALREADY_EXISTS = 183
_MUTEX_NAME = "Local\\CountdownFletApp.SingleInstance.v1"
_LOCK_PORT = 45197
_lock_socket: socket.socket | None = None


def allow_multi_instance() -> bool:
    return os.environ.get("COUNTDOWN_ALLOW_MULTI", "").strip().lower() in (
        "1",
        "true",
        "yes",
    )


def try_acquire_single_instance() -> bool:
    """
    若本进程应作为唯一实例继续运行，返回 True；
    若已有实例在运行，返回 False（调用方应提示并退出）。
    """
    if allow_multi_instance():
        return True

    if sys.platform == "win32":
        return _try_acquire_windows_mutex()

    return _try_acquire_loopback_lock()


def _try_acquire_windows_mutex() -> bool:
    import ctypes

    kernel32 = ctypes.windll.kernel32
    kernel32.SetLastError(0)
    mutex = kernel32.CreateMutexW(None, True, _MUTEX_NAME)
    if not mutex:
        return True
    err = kernel32.GetLastError()
    if err == _ERROR_ALREADY_EXISTS:
        return False
    return True


def _try_acquire_loopback_lock() -> bool:
    global _lock_socket
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    except OSError:
        pass
    try:
        s.bind(("127.0.0.1", _LOCK_PORT))
        s.listen(1)
    except OSError:
        try:
            s.close()
        except OSError:
            pass
        return False
    _lock_socket = s
    return True


def notify_second_instance_blocked() -> None:
    """已有实例在运行时，给用户的简短提示（仅 Windows 弹窗；其他平台可静默）。"""
    if sys.platform != "win32":
        print("多倒计时已在运行。", file=sys.stderr)
        return
    try:
        import ctypes

        ctypes.windll.user32.MessageBoxW(
            0,
            "多倒计时已在运行，请勿重复启动。",
            "多倒计时",
            0x40,
        )
    except Exception:
        print("多倒计时已在运行。", file=sys.stderr)
