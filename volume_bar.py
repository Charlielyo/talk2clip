#!/usr/bin/env python3
"""volume_bar.py — 录音时显示实时音量波形（7 根起伏竖条，松手消失）

用法（由 talk2clip 调用）:
    from volume_bar import VolumeBar
    bar = VolumeBar()        # 创建（主线程）
    bar.show(0.2)            # 显示并设置音量 0~1
    bar.update(0.5)          # 更新音量
    bar.hide()               # 消失
"""
import math
import threading
import time

import objc

try:
    from AppKit import (
        NSApplication, NSWindow, NSColor, NSScreen, NSView,
        NSWindowStyleMaskBorderless, NSWindowCollectionBehaviorCanJoinAllSpaces,
        NSBackingStoreBuffered, NSStatusWindowLevel, NSBezierPath,
        NSTimer, NSMakeRect)
    _OK = True
except ImportError:
    _OK = False

_BARS = 7          # 竖条数量
_BAR_W = 6         # 单条宽度
_GAP = 4           # 条间距


class _WaveView(NSView):
    """自定义绘制：根据 level 和相位画起伏竖条"""

    def initWithFrame_(self, frame):
        self = objc.super(_WaveView, self).initWithFrame_(frame)
        if self is not None:
            self.level = 0.0
            self.phase = 0.0
        return self

    def set_level(self, v):
        self.level = max(0.0, min(1.0, v))
        self.setNeedsDisplay_(True)

    def drawRect_(self, rect):
        NSColor.clearColor().setFill()
        NSBezierPath.fillRect_(rect)
        w = self.bounds().size.width
        h = self.bounds().size.height
        total = _BARS * _BAR_W + (_BARS - 1) * _GAP
        x0 = (w - total) / 2
        base_h = h * 0.18   # 静音时的基准高度
        for i in range(_BARS):
            # 波形: 基准 + 音量*(0.35 + 0.65*sin(相位 + i))，再加一点随机呼吸
            wave = 0.45 + 0.55 * math.sin(self.phase + i * 0.9)
            bh = base_h + self.level * h * 0.8 * wave
            bh = min(bh, h - 2)
            x = x0 + i * (_BAR_W + _GAP)
            y = (h - bh) / 2
            # 越响越亮（绿→黄绿→黄），透明度随音量
            g = 0.6 + 0.4 * self.level
            color = NSColor.colorWithCalibratedRed_green_blue_alpha_(
                0.25 - 0.15 * self.level, g, 0.35, 0.9)
            color.setFill()
            path = NSBezierPath.bezierPathWithRoundedRect_xRadius_yRadius_(
                NSMakeRect(x, y, _BAR_W, bh), _BAR_W / 2, _BAR_W / 2)
            path.fill()


class VolumeBar:
    """悬浮音量波形：屏幕顶部小窗，录音时显示，结束隐藏"""

    def __init__(self, width=110, height=56, margin_top=70):
        if not _OK:
            self._window = None
            self._view = None
            self._timer = None
            return
        app = NSApplication.sharedApplication()
        screen = NSScreen.mainScreen().frame()
        x = (screen.size.width - width) / 2
        y = screen.size.height - margin_top - height   # 顶部靠中，避开刘海

        self._window = NSWindow.alloc().initWithContentRect_styleMask_backing_defer_(
            NSMakeRect(x, y, width, height),
            NSWindowStyleMaskBorderless,
            NSBackingStoreBuffered,
            False)
        self._window.setLevel_(NSStatusWindowLevel)
        self._window.setOpaque_(False)
        self._window.setBackgroundColor_(NSColor.clearColor())
        self._window.setHasShadow_(False)
        self._window.setCollectionBehavior_(
            NSWindowCollectionBehaviorCanJoinAllSpaces)

        self._view = _WaveView.alloc().initWithFrame_(NSMakeRect(0, 0, width, height))
        self._window.setContentView_(self._view)

        self._level = 0.0
        self._lock = threading.Lock()
        self._t0 = time.time()

        # 15fps 动画：相位推进 + 重绘（仅窗口可见时）
        self._timer = NSTimer.scheduledTimerWithTimeInterval_target_selector_userInfo_repeats_(
            1 / 15, self, "tick:", None, True)
        self._timer.retain()

    def tick_(self, _t):
        if self._window.isVisible():
            with self._lock:
                lv = self._level
            self._view.set_level(lv)
            self._view.phase = (time.time() - self._t0) * 5.0   # 相位 5 rad/s
            self._view.setNeedsDisplay_(True)

    # ── 线程安全接口（实际 UI 更新走主队列）──
    def show(self, level=0.0):
        if not self._window:
            return
        self._set_level(level)
        self._run_on_main(lambda: self._window.orderFrontRegardless())

    def update(self, level):
        if not self._window:
            return
        self._set_level(level)

    def hide(self):
        if not self._window:
            return
        self._run_on_main(lambda: self._window.orderOut_(None))

    # ── 内部 ──
    def _set_level(self, v):
        with self._lock:
            self._level = max(0.0, min(1.0, v))

    def _run_on_main(self, fn):
        try:
            from Foundation import NSOperationQueue
            NSOperationQueue.mainQueue().addOperationWithBlock_(fn)
        except Exception:
            try:
                fn()
            except Exception:
                pass
