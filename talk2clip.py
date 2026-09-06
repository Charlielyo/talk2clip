#!/usr/bin/env python3
"""
talk2clip — 轻量语音转文字（按住说话 → 识别 → 剪贴板）

用法:
    python3 talk2clip.py            # 带上菜单栏图标常驻
    python3 talk2clip.py --once     # 无界面：启动后等一次按键就退出

热键: Option+Shift+Space 按住说话，松开自动识别并复制到剪贴板。
识别用本地 faster-whisper（离线、免费），输出用 pbcopy（macOS 剪贴板）。
"""

import io
import os
import subprocess
import sys
import threading
import time
import wave

# ═══ 配置（写死的最小化配置，可自行修改）═══
HK_MODS = ("option",)              # 热键修饰键（按住即可，无需额外组合）
HK_KEY = "space"                  # 热键主键
RATE = 16000                      # 采样率
MAX_SEC = 30                      # 最长录音
SILENCE_SEC = 1.2                 # 静音多久自动停止
NOISE_THRESH = 0.015              # 开始说话的阈值
SILENCE_THRESH = 0.008            # 静音阈值
MIN_SEC = 0.3                     # 最短有效音频
LANG = "zh"                       # whisper 语言
MODEL = "small"                   # 模型大小: tiny/base/small/medium（越大越准越慢）
BEAM_SIZE = 5                     # 解码搜索宽度，越大越准（5=准，1=快）
INITIAL_PROMPT = "以下是普通话的句子。"  # 提示词：减少繁体/英文误输出，提升中文倾向
TO_SIMPLIFIED = True              # 繁体→简体（whisper 常输出繁体，opencc 转换）
HF_ENDPOINT = "https://hf-mirror.com"  # HuggingFace 镜像（国内直连 huggingface.co 会 429）
AUTO_PASTE = True                 # 松手识别后自动粘贴到光标处（需辅助功能授权；失败则仅剪贴板）

# ═══ 依赖导入（缺失时给出安装提示）═══
try:
    import numpy as np
    import sounddevice as sd
except ImportError:
    print("缺少依赖，请先运行:  pip install numpy sounddevice")
    sys.exit(1)

_whisper_model = None
_model_lock = threading.Lock()


def get_model():
    """懒加载 whisper 模型（读取本地缓存模型目录，无需联网下载）

    优先顺序:
      1. 项目目录 models/faster-whisper-<MODEL>/（手动放置，最可控）
      2. HF 缓存中的 faster-whisper-<MODEL>（huggingface_hub 缓存，离线可用）
    """
    global _whisper_model
    with _model_lock:
        if _whisper_model is None:
            from faster_whisper import WhisperModel

            # 本地优先：项目内 models 目录
            local = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                 "models", f"faster-whisper-{MODEL}")
            if os.path.isdir(local):
                path = local
                print(f"✅ 使用本地模型: {MODEL}（项目 models/ 目录）", flush=True)
            else:
                # HF 缓存（huggingface_hub snapshot）
                import glob
                snaps = glob.glob(
                    os.path.expanduser(
                        f"~/.cache/huggingface/hub/models--Systran--faster-whisper-{MODEL}/snapshots/*"))
                if snaps:
                    path = snaps[0]
                    print(f"✅ 使用本地模型: {MODEL}（HF 缓存）", flush=True)
                else:
                    # 兜底：联网下载（国内用镜像）
                    print(f"⏳ 下载 whisper 模型 {MODEL}（首次会下载，耐心等）…", flush=True)
                    os.environ.setdefault("HF_ENDPOINT", HF_ENDPOINT)
                    path = MODEL
            _whisper_model = WhisperModel(path, device="cpu", compute_type="int8")
            print("✅ whisper 模型就绪", flush=True)
        return _whisper_model


# ═══ 录音 ═══
_stop_flag = {"stop": False}   # 全局停止标志：松手时置 True，立即结束录音
_min_sec = RATE * MIN_SEC      # 最短有效音频（帧数）


def record_once():
    """按住说话：返回 1D numpy 音频；松开（stop_capture）或静音超时自动结束。"""
    import sounddevice as sd
    buf = []
    state = {"started": False, "silent_at": None}   # 可变状态放 dict，回调内外共享
    _stop_flag["stop"] = False   # 每次开始录音重置

    def cb(indata, frames, t, status):
        buf.append(indata.copy())
        rms = float(np.sqrt(np.mean(indata ** 2)))
        if rms > NOISE_THRESH:
            state["started"] = True
            state["silent_at"] = None
        elif state["started"] and rms < SILENCE_THRESH:
            if state["silent_at"] is None:
                state["silent_at"] = time.time()

    print("🎙️ 录音中…（松开右⌘即发送 / 静音自动断）", flush=True)
    deadline = time.time() + MAX_SEC
    with sd.InputStream(samplerate=RATE, channels=1, dtype="float32", callback=cb):
        while not _stop_flag["stop"] and time.time() < deadline:
            time.sleep(0.05)
            sa = state["silent_at"]
            if sa and time.time() - sa > SILENCE_SEC:
                break
    if not buf:
        return None
    audio = np.concatenate(buf, axis=0).reshape(-1)   # 压平为 1D
    if len(audio) < _min_sec:
        print("（太短，忽略）", flush=True)
        return None
    return audio


def to_wav_bytes(audio) -> bytes:
    b = io.BytesIO()
    with wave.open(b, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(RATE)
        w.writeframes((audio.flatten() * 32767).astype(np.int16).tobytes())
    return b.getvalue()


def transcribe(audio) -> str:
    # faster-whisper 原生接受 float32 numpy 数组（16kHz 单声道）
    segs, _ = get_model().transcribe(
        np.asarray(audio, dtype=np.float32).reshape(-1),
        language=LANG, beam_size=BEAM_SIZE, vad_filter=True,
        initial_prompt=INITIAL_PROMPT)
    text = "".join(s.text for s in segs).strip()
    if TO_SIMPLIFIED:
        try:
            text = _to_simplified(text)
        except Exception:
            pass  # opencc 不可用时保留原结果
    return text


def _to_simplified(text: str) -> str:
    """繁体→简体（whisper 常输出繁体，用户输入界面多为简体）"""
    global _opencc
    if _opencc is None:
        from opencc import OpenCC
        _opencc = OpenCC("t2s")
    return _opencc.convert(text)


_opencc = None


# ═══ 输出到剪贴板 ═══
def copy_to_clipboard(text: str):
    p = subprocess.run(["pbcopy"], input=text.encode("utf-8"))
    return p.returncode == 0


def paste_at_cursor():
    """把剪贴板内容粘贴到当前光标处（Cmd+V，需终端/进程有辅助功能授权）"""
    try:
        r = subprocess.run(
            ["osascript", "-e",
             'tell application "System Events" to keystroke "v" using {command down}'],
            capture_output=True, timeout=5)
        return r.returncode == 0
    except Exception:
        return False


def notify(text: str):
    """终端 + 系统通知双提示"""
    print(f"📋 已复制到剪贴板: {text}", flush=True)
    try:
        subprocess.run(
            ["osascript", "-e",
             f'display notification "{text[:40]}" with title "talk2clip"'],
            capture_output=True, timeout=5)
    except Exception:
        pass


# ═══ 主流程（按键按下=开录，按键松开=识别）═══
def start_capture():
    threading.Thread(target=record_worker, daemon=True).start()


def record_worker():
    global recording
    if recording:
        return
    recording = True
    try:
        audio = record_once()
        if audio is None:
            return
        text = transcribe(audio)
        if text and copy_to_clipboard(text):
            notify(text)
            if AUTO_PASTE:
                ok = paste_at_cursor()
                if not ok:
                    print("⚠ 自动粘贴失败（需给终端授权「辅助功能」），已复制到剪贴板可手动 Cmd+V",
                          flush=True)
    except Exception as e:
        print(f"❌ 出错: {e}", flush=True)
    finally:
        recording = False


def stop_capture():
    """松手即停：置停止标志，录音循环立即结束并开始识别"""
    _stop_flag["stop"] = True


recording = False

# ═══ 热键（右 Command 按住说话；pynput 原生支持 Key.cmd_r 区分左右⌘）═══
def start_hotkey():
    try:
        from pynput import keyboard
    except ImportError:
        print("⚠ 缺少 pynput（pip install pynput）", flush=True)
        return None

    key = keyboard.Key.cmd_r   # 右 Command（keycode 54）

    pressed = [False]

    def on_press(k):
        if not pressed[0] and k == key:
            pressed[0] = True
            start_capture()

    def on_release(k):
        if pressed[0] and k == key:
            pressed[0] = False
            stop_capture()

    listener = keyboard.Listener(on_press=on_press, on_release=on_release)
    listener.start()
    return listener


# ═══ 菜单栏图标（rumps，可选）═══
def start_menu():
    try:
        import rumps
    except ImportError:
        return False

    class App(rumps.App):
        def __init__(self):
            super().__init__("talk2clip", title="🎙️")
            self.menu = [
                rumps.MenuItem("🎤 开始说话", callback=self._start),
                rumps.MenuItem("🛑 停止", callback=self._stop),
                None,
                rumps.MenuItem("🚪 退出", callback=self._exit),
            ]

        def _start(self, _):
            start_capture()

        def _stop(self, _):
            stop_capture()

        def _exit(self, _):
            rumps.quit_application()

    App().run()
    return True


def main():
    listener = start_hotkey()
    if listener is None:
        print("⚠ 热键启动失败：请先给终端/python3 授权「输入监控」或「辅助功能」")
    else:
        print("✅ 热键已启动：按住 右 ⌘ (右Command) 说话，松开复制")
    print("   也可用菜单栏 🎙️ 图标点击说话", flush=True)

    if "--once" in sys.argv:
        # 无界面模式：等 20 秒或按键一次即退出
        time.sleep(20)
        return
    start_menu()  # 菜单栏常驻


if __name__ == "__main__":
    main()
