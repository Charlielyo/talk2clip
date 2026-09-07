#!/usr/bin/env python3
"""volume_bar.py — 录音波形指示（胶囊形态，40fps 高帧率）

设计：
  - 半透明深色胶囊（圆角 = 窗口高度一半，永远不是方的）
  - 21 根圆角波形柱，中心最高、两侧渐低（音频频谱经典形态）
  - 每根柱相位错开跳动（abs(sin(t + i))），看起来像真实声波涌动
  - 蓝紫渐变：中心亮蓝白 → 两侧紫；音量越大越亮、跳动幅度越大
  - 双图层：外圈发光描边 + 内圈实心，制造光感

用法（由 talk2clip 调用）:
    from volume_bar import VolumeBar
    bar = VolumeBar()
    bar.show(0.2)    # 显示
    bar.update(0.5)  # 更新音量 0~1
    bar.hide()       # 消失
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

_FPS = 40.0
_WIDTH = 260.0       # 窗口宽（胶囊）
_HEIGHT = 64.0       # 窗口高（圆角半径 = 32 → 两端半圆）
_N_BARS = 21         # 波形柱数（奇数，中心有柱）


class _WaveView(NSView):
    """胶囊背景 + 发光波形柱"""

    def initWithFrame_(self, frame):
        self = objc.super(_WaveView, self).initWithFrame_(frame)
        if self is not None:
            self.level = 0.0
            self.t = 0.0
        return self

    def drawRect_(self, rect):
        w, h = self.bounds().size.width, self.bounds().size.height
        cx, cy = w / 2, h / 2
        lv = self.level
        t = self.t

        # 1) 半透明深色胶囊背景（衬托发光波形）
        NSColor.clearColor().setFill()
        NSBezierPath.fillRect_(rect)
        NSColor.colorWithCalibratedWhite_alpha_(0.10, 0.38).setFill()
        NSBezierPath.bezierPathWithRoundedRect_xRadius_yRadius_(
            NSMakeRect(1, 1, w - 2, h - 2), h / 2 - 1, h / 2 - 1).fill()

        # 2) 波形柱
        n = _N_BARS
        bar_w = 4.5
        gap = 6.0
        total = n * bar_w + (n - 1) * gap
        x0 = cx - total / 2
        center_idx = (n - 1) / 2
        max_h = h * 0.42           # 最大半高（柱从中线向上下对称伸展）

        for i in range(n):
            d = abs(i - center_idx) / center_idx                      # 0中心 → 1边缘
            falloff = 0.30 + 0.70 * math.cos(d * math.pi / 2)         # 中心最高，两侧渐低
            wave = abs(math.sin(t + i * 0.85))                        # 相位错开跳动
            amp = lv * falloff * (0.20 + 0.80 * wave)
            bh = max(2.0, max_h * amp)                               # 柱半高
            x = x0 + i * (bar_w + gap)

            # 颜色：中心亮蓝白 → 两侧紫；音量越大越亮
            hue_t = 1.0 - d
            r = 0.30 + 0.62 * hue_t * (0.45 + 0.55 * lv)
            g = 0.58 + 0.40 * hue_t
            b = 1.0
            alpha = 0.50 + 0.50 * lv

            # 发光层（外圈，低透明度）
            NSColor.colorWithCalibratedRed_green_blue_alpha_(r, g, b, alpha * 0.32).setFill()
            NSBezierPath.bezierPathWithRoundedRect_xRadius_yRadius_(
                NSMakeRect(x - 1.5, cy - bh - 1.5, bar_w + 3, bh * 2 + 3),
                (bar_w + 3) / 2, (bar_w + 3) / 2).fill()
            # 实心层
            NSColor.colorWithCalibratedRed_green_blue_alpha_(r, g, b, alpha).setFill()
            NSBezierPath.bezierPathWithRoundedRect_xRadius_yRadius_(
                NSMakeRect(x, cy - bh, bar_w, bh * 2), bar_w / 2, bar_w / 2).fill()


class VolumeBar:
    """胶囊波形指示：录音时显示，结束隐藏"""

    def __init__(self, margin_top=100):
        if not _OK:
            self._window = None
            self._view = None
            self._timer = None
            return
        app = NSApplication.sharedApplication()
        screen = NSScreen.mainScreen().frame()
        x = (screen.size.width - _WIDTH) / 2
        y = screen.size.height - margin_top - _HEIGHT

        self._window = NSWindow.alloc().initWithContentRect_styleMask_backing_defer_(
            NSMakeRect(x, y, _WIDTH, _HEIGHT),
            NSWindowStyleMaskBorderless,
            NSBackingStoreBuffered,
            False)
        self._window.setLevel_(NSStatusWindowLevel)
        self._window.setOpaque_(False)
        self._window.setBackgroundColor_(NSColor.clearColor())
        self._window.setHasShadow_(False)
        self._window.setCollectionBehavior_(NSWindowCollectionBehaviorCanJoinAllSpaces)

        self._view = _WaveView.alloc().initWithFrame_(NSMakeRect(0, 0, _WIDTH, _HEIGHT))
        self._window.setContentView_(self._view)

        self._level = 0.0
        self._lock = threading.Lock()
        self._t0 = time.time()

        # 40fps 动画（仅窗口可见时重绘）
        self._timer = NSTimer.scheduledTimerWithTimeInterval_target_selector_userInfo_repeats_(
            1 / _FPS, self, "tick:", None, True)
        self._timer.retain()

    def tick_(self, _t):
        if self._window.isVisible():
            with self._lock:
                lv = self._level
            self._view.set_level(lv)
            self._view.t = (time.time() - self._t0) * 2.4   # 波形涌动速度
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
