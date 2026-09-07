#!/usr/bin/env python3
"""volume_bar.py — 录音时显示实时音量悬浮条（松手自动消失，不依赖菜单栏）

用法（由 talk2clip 调用）:
    from volume_bar import VolumeBar
    bar = VolumeBar()        # 创建（主线程）
    bar.show(0.2)            # 显示并设置音量 0~1
    bar.update(0.5)          # 更新音量
    bar.hide()               # 消失
"""
import threading

try:
    from AppKit import (
        NSApplication, NSWindow, NSColor, NSScreen,
        NSWindowStyleMaskBorderless, NSWindowCollectionBehaviorCanJoinAllSpaces,
        NSBackingStoreBuffered, NSStatusWindowLevel)
    from Foundation import NSMakeRect
    _OK = True
except ImportError:
    _OK = False


class VolumeBar:
    """悬浮音量条：屏幕顶部小横条，录音时显示，结束隐藏"""

    def __init__(self, width=180, height=10, margin_top=60):
        if not _OK:
            self._window = None
            return
        app = NSApplication.sharedApplication()
        screen = NSScreen.mainScreen().frame()
        x = (screen.size.width - width) / 2
        y = screen.size.height - margin_top - height   # 顶部往下靠中，避开刘海

        self._window = NSWindow.alloc().initWithContentRect_styleMask_backing_defer_(
            NSMakeRect(x, y, width, height),
            NSWindowStyleMaskBorderless,
            NSBackingStoreBuffered,
            False)
        self._window.setLevel_(NSStatusWindowLevel)       # 悬浮在所有窗口之上
        self._window.setOpaque_(False)
        self._window.setBackgroundColor_(NSColor.clearColor())
        self._window.setHasShadow_(False)
        self._window.setCollectionBehavior_(
            NSWindowCollectionBehaviorCanJoinAllSpaces)    # 全空间可见

        # 内部音量填充视图（颜色配置；绘制见 _redraw）
        self._fill = NSColor.colorWithCalibratedRed_green_blue_alpha_(0.1, 0.8, 0.4, 0.85)
        self._bg = NSColor.colorWithCalibratedRed_green_blue_alpha_(0, 0, 0, 0.35)

        self._level = 0.0
        self._lock = threading.Lock()
        self._dirty = False

    # ── 线程安全接口（实际 UI 更新走主线程队列）──
    def show(self, level=0.0):
        if not self._window:
            return
        self._set_level(level)
        self._run_on_main(lambda: self._window.orderFrontRegardless())

    def update(self, level):
        if not self._window:
            return
        self._set_level(level)
        self._run_on_main(self._redraw)

    def hide(self):
        if not self._window:
            return
        self._run_on_main(lambda: self._window.orderOut_(None))

    # ── 内部 ──
    def _set_level(self, v):
        with self._lock:
            self._level = max(0.0, min(1.0, v))

    def _redraw(self):
        with self._lock:
            level = self._level
        # 简化实现：背景色透明度随音量变化（绿色调）
        self._window.setBackgroundColor_(
            NSColor.colorWithCalibratedRed_green_blue_alpha_(0.2, 0.9, 0.4, 0.4 + 0.5 * level))
        self._window.displayIfNeeded()

    def _run_on_main(self, fn):
        try:
            from Foundation import NSOperationQueue
            NSOperationQueue.mainQueue().addOperationWithBlock_(fn)
        except Exception:
            try:
                fn()
            except Exception:
                pass
