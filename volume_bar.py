#!/usr/bin/env python3
"""volume_bar.py — Siri 风格光球音量指示（录音时显示，松手消失）

用法（由 talk2clip 调用）:
    from volume_bar import VolumeBar
    bar = VolumeBar()        # 创建（主线程）
    bar.show(0.2)            # 显示并设置音量 0~1
    bar.update(0.5)          # 更新音量
    bar.hide()               # 消失

视觉：径向渐变光球（蓝→紫），音量越大越亮、脉冲越快；40fps 动画。
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
        NSGradient, NSTimer, NSMakeRect)
    _OK = True
except ImportError:
    _OK = False

_FPS = 40.0           # 动画帧率（平滑且省电）
_SIZE = 120           # 光球直径


class _OrbView(NSView):
    """径向渐变光球绘制"""

    def initWithFrame_(self, frame):
        self = objc.super(_OrbView, self).initWithFrame_(frame)
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
        cx, cy = w / 2, h / 2
        lv = self.level
        pulse = 0.5 + 0.5 * math.sin(self.phase)          # 呼吸脉冲 0~1

        # 外圈光晕（半透明，随音量+脉冲变大）
        halo_r = _SIZE * 0.5 * (0.85 + 0.25 * pulse * (0.4 + 0.6 * lv))
        for gi in range(5, 0, -1):                        # 5 层晕
            a = 0.05 * gi * (0.5 + 0.5 * lv)
            NSGradient.alloc().initWithStartingColor_endingColor_(
                NSColor.colorWithCalibratedRed_green_blue_alpha_(0.35, 0.75, 1.0, 0),
                NSColor.colorWithCalibratedRed_green_blue_alpha_(0.45, 0.4, 1.0, a)
            ).drawInRect_angle_(
                NSMakeRect(cx - halo_r * gi / 2.6, cy - halo_r * gi / 2.6,
                           halo_r * gi / 1.3, halo_r * gi / 1.3), 90)
        # 核心球（亮蓝→紫，音量越亮）
        core_r = _SIZE * 0.36 * (0.9 + 0.18 * pulse * (0.35 + 0.65 * lv))
        cr = 0.32 + 0.35 * lv
        cg = 0.72 + 0.20 * lv
        cb = 1.0
        grad = NSGradient.alloc().initWithStartingColor_endingColor_(
            NSColor.colorWithCalibratedRed_green_blue_alpha_(cr, cg, cb, 1.0),
            NSColor.colorWithCalibratedRed_green_blue_alpha_(0.30, 0.25, 0.85, 0.95))
        grad.drawInRect_angle_(NSMakeRect(cx - core_r, cy - core_r, core_r * 2, core_r * 2), 120)
        # 高光点（左上白点）
        hl_r = core_r * 0.38
        NSGradient.alloc().initWithStartingColor_endingColor_(
            NSColor.colorWithCalibratedWhite_alpha_(1.0, 0.85),
            NSColor.colorWithCalibratedWhite_alpha_(1.0, 0)
        ).drawInRect_angle_(NSMakeRect(cx - core_r * 0.55, cy + core_r * 0.1, hl_r, hl_r), 45)


class VolumeBar:
    """Siri 光球：录音时显示，结束隐藏"""

    def __init__(self, margin_top=80):
        if not _OK:
            self._window = None
            self._view = None
            self._timer = None
            return
        app = NSApplication.sharedApplication()
        screen = NSScreen.mainScreen().frame()
        x = (screen.size.width - _SIZE) / 2
        y = screen.size.height - margin_top - _SIZE

        self._window = NSWindow.alloc().initWithContentRect_styleMask_backing_defer_(
            NSMakeRect(x, y, _SIZE, _SIZE),
            NSWindowStyleMaskBorderless,
            NSBackingStoreBuffered,
            False)
        self._window.setLevel_(NSStatusWindowLevel)
        self._window.setOpaque_(False)
        self._window.setBackgroundColor_(NSColor.clearColor())
        self._window.setHasShadow_(False)
        self._window.setCollectionBehavior_(NSWindowCollectionBehaviorCanJoinAllSpaces)

        self._view = _OrbView.alloc().initWithFrame_(NSMakeRect(0, 0, _SIZE, _SIZE))
        self._window.setContentView_(self._view)

        self._level = 0.0
        self._lock = threading.Lock()
        self._t0 = time.time()

        # 40fps 动画（仅窗口可见时重绘，省电）
        self._timer = NSTimer.scheduledTimerWithTimeInterval_target_selector_userInfo_repeats_(
            1 / _FPS, self, "tick:", None, True)
        self._timer.retain()

    def tick_(self, _t):
        if self._window.isVisible():
            with self._lock:
                lv = self._level
            self._view.set_level(lv)
            self._view.phase = (time.time() - self._t0) * 4.5   # 脉冲 4.5 rad/s
            self._view.setNeedsDisplay_(True)

    # ── 线程安全接口 ──
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
