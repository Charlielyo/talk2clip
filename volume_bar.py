#!/usr/bin/env python3
"""volume_bar.py — 录音波形指示（紧凑胶囊，40fps，独立线程驱动动画）

设计：
  - 紧凑胶囊 170×46，半透明深色底，两端半圆
  - 15 根圆角波形柱：中心最高、两侧渐低；每根相位错开涌动
  - 蓝紫渐变 + 发光描边；音量越大越亮、跳动越猛
  - 动画驱动：独立 daemon 线程 40fps → 主队列派发重绘
    （不依赖 NSTimer/runloop，任何主循环环境都能动，rumps 下已验证可靠）

用法（由 talk2clip 调用）:
    from volume_bar import VolumeBar
    bar = VolumeBar()
    bar.show(0.2)   # 显示
    bar.update(0.5) # 更新音量 0~1
    bar.hide()      # 消失
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
        NSMakeRect)
    _OK = True
except ImportError:
    _OK = False

_FPS = 40.0
WIDTH = 170.0
HEIGHT = 46.0
N_BARS = 15
_MODE_KEY = "default"    # 'default' | 'thread'（线程驱动；default 亦可，实为线程驱动）


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

        # 半透明深色胶囊背景
        NSColor.clearColor().setFill()
        NSBezierPath.fillRect_(rect)
        NSColor.colorWithCalibratedWhite_alpha_(0.08, 0.42).setFill()
        NSBezierPath.bezierPathWithRoundedRect_xRadius_yRadius_(
            NSMakeRect(1, 1, w - 2, h - 2), h / 2 - 1, h / 2 - 1).fill()

        n = N_BARS
        bar_w = 3.6
        gap = 6.5
        total = n * bar_w + (n - 1) * gap
        x0 = cx - total / 2
        center_idx = (n - 1) / 2
        max_h = h * 0.40

        for i in range(n):
            d = abs(i - center_idx) / center_idx
            falloff = 0.28 + 0.72 * math.cos(d * math.pi / 2)
            # 涌动：不同频率快慢叠加，避免单调
            wave = 0.45 + 0.55 * abs(
                math.sin(t * 1.0 + i * 0.9) * 0.65 +
                math.sin(t * 2.3 + i * 1.7) * 0.35)
            amp = lv * falloff * wave
            bh = max(1.5, max_h * amp)
            x = x0 + i * (bar_w + gap)

            hue_t = 1.0 - d
            r = 0.32 + 0.60 * hue_t * (0.45 + 0.55 * lv)
            g = 0.60 + 0.38 * hue_t
            b = 1.0
            alpha = 0.45 + 0.55 * lv

            # 发光层
            NSColor.colorWithCalibratedRed_green_blue_alpha_(r, g, b, alpha * 0.30).setFill()
            NSBezierPath.bezierPathWithRoundedRect_xRadius_yRadius_(
                NSMakeRect(x - 1.2, cy - bh - 1.2, bar_w + 2.4, bh * 2 + 2.4),
                (bar_w + 2.4) / 2, (bar_w + 2.4) / 2).fill()
            # 实心层
            NSColor.colorWithCalibratedRed_green_blue_alpha_(r, g, b, alpha).setFill()
            NSBezierPath.bezierPathWithRoundedRect_xRadius_yRadius_(
                NSMakeRect(x, cy - bh, bar_w, bh * 2), bar_w / 2, bar_w / 2).fill()


class VolumeBar:
    """紧凑胶囊波形：录音时显示，结束隐藏；40fps 线程驱动"""

    def __init__(self, margin_top=90):
        if not _OK:
            self._window = None
            self._view = None
            self._alive = False
            return
        app = NSApplication.sharedApplication()
        screen = NSScreen.mainScreen().frame()
        x = (screen.size.width - WIDTH) / 2
        y = screen.size.height - margin_top - HEIGHT

        self._window = NSWindow.alloc().initWithContentRect_styleMask_backing_defer_(
            NSMakeRect(x, y, WIDTH, HEIGHT),
            NSWindowStyleMaskBorderless,
            NSBackingStoreBuffered,
            False)
        self._window.setLevel_(NSStatusWindowLevel)
        self._window.setOpaque_(False)
        self._window.setBackgroundColor_(NSColor.clearColor())
        self._window.setHasShadow_(False)
        self._window.setCollectionBehavior_(NSWindowCollectionBehaviorCanJoinAllSpaces)

        self._view = _WaveView.alloc().initWithFrame_(NSMakeRect(0, 0, WIDTH, HEIGHT))
        self._window.setContentView_(self._view)

        self._level = 0.0
        self._lock = threading.Lock()
        self._t0 = time.time()
        self._alive = True

        # 独立线程驱动 40fps（不依赖 runloop/NSTimer —— rumps 环境 NSTimer 不触发）
        threading.Thread(target=self._loop, daemon=True,
                         name="volume-bar-anim").start()

    def _loop(self):
        while self._alive:
            try:
                with self._lock:
                    lv = self._level
                if self._window.isVisible():
                    self._view.level = lv
                    self._view.t = (time.time() - self._t0) * 2.6
                    # Cocoa UI 调用必须在主线程 → 主队列派发重绘
                    self._run_on_main(lambda: self._view.setNeedsDisplay_(True))
            except Exception:
                pass
            time.sleep(1 / _FPS)

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
