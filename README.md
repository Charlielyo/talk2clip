# talk2clip 🎙️📋

**Hold right ⌘, speak, release — text lands in your cursor.**

[English](README.md) | [中文](README.zh-CN.md)
*(macOS 按住说话 → 本地离线语音识别 → 自动粘贴到光标处)*

A lightweight, fully offline, privacy-friendly voice-to-text tool for macOS:

- 🔥 **Single action**: hold **right ⌘** (or any key you choose) → speak → release → text is inserted at your cursor
- 🧠 **Local AI recognition** via [faster-whisper](https://github.com/SYSTRAN/faster-whisper) — offline, free, unlimited, no cloud, no API keys
- 📋 **Clipboard + auto-paste**: text is copied and pasted automatically
- 🌊 **Visual feedback**: floating capsule audio-wave (40fps) shows live volume while you speak
- 🇨🇳↔🇬🇧 **Auto language detect** (optional), **auto punctuation** (optional), **correction dictionary**
- 🖥️ **Settings GUI**: hotkey / model / dictionary / options, all clickable
- 🚀 **Launch at login** (optional, via LaunchAgent)

No cloud, no account, no data leaves your Mac.

---

## Quick start

```bash
git clone <this-repo> talk2clip && cd talk2clip
./install.sh          # creates .venv, installs deps, writes config.json
```

Then **download the model** (`.pt` 483MB → converted `model.bin` 247MB, one-time; see [Model](#model)):

```bash
# Method A — from Azure CDN (works in CN & anywhere):
curl -L -o /tmp/small.pt 'https://openaipublic.azureedge.net/main/whisper/models/9ecf779972d90ba49c06d968637d720dd632c55bbf19d441fb42bf17a411e794/small.pt'
.venv/bin/python3 convert_pt_to_ct2.py /tmp/small.pt models/faster-whisper-small

# Method B — copy a CT2-format model (e.g. Systran/faster-whisper-small from HuggingFace)
# into `models/faster-whisper-small/`
```

### Grant permissions (first run only)

| Permission | Where | What |
|---|---|---|
| 输入监控 | System Settings → Privacy & Security → **Input Monitoring** | Terminal (so hotkey listener works) |
| 辅助功能 | System Settings → Privacy & Security → **Accessibility** | Terminal + `/usr/bin/osascript` (so auto-paste works) |

> **macOS 15 note**: permission for CLI binaries is glitchy (adds but doesn't apply).
> Run via **Terminal** (`./启动talk2clip.command` or `./run.sh`) and grant
> **Terminal** itself — the child process inherits it. This is the supported path.

### Usage

| Action | How |
|---|---|
| Speak → text | Hold **right ⌘**, say something, release — text appears at cursor |
| Change hotkey / model / dictionary | Double-click `打开设置.command` (or `./run.sh settings.py`) |
| Start | Double-click **talk2clip.app** (in `/Applications`), `启动talk2clip.command`, or enable login-autostart (see below) |
| Quit | menu-bar icon → Quit, or `./run.sh quit` |

*Hotkey options: right ⌘ / right ⌥ / right ⌃ / right ⇧ / ⌘ / ⌥ / ⌃ / Space / F5-F20 (config.json `hotkey`).*

---

## Features & config (`config.json`)

| Key | Default | Meaning |
|---|---|---|
| `hotkey` | `cmd_r` | pynput Key name, e.g. `alt_r` = right Option |
| `model` | `small` | tiny / base / small / medium (bigger = better, slower) |
| `beam_size` | `5` | decode beam (5 = accurate, 1 = fast) |
| `auto_paste` | `true` | paste at cursor after recognition (falls back to clipboard-only) |
| `corrections` | `{}` | dictionary: `{"misheard word": "correct word"}` — applies instantly |
| `auto_lang` | `false` | auto-detect Chinese/English (falls back to Chinese on failure) |
| `add_punct` | `false` | rule-based punctuation (，。？) |

Everything above is editable via **settings GUI** — no need to touch code.

### Model

Whisper model is **not bundled** (repo stays small). It is loaded from:
1. `models/faster-whisper-<MODEL>/` (project-local, recommended)
2. HuggingFace cache
3. Online download (last resort; uses `HF_ENDPOINT` mirror if set)

`convert_pt_to_ct2.py` converts the official OpenAI `small.pt` (from Azure CDN,
no HuggingFace needed) to faster-whisper CTranslate2 format — offline-friendly
for users in CN whose access to huggingface.co is rate-limited (429).

---

## Architecture

```
talk2clip.py       core: hotkey (pynput) → record (sounddevice) → transcribe (faster-whisper)
                   → clipboard (pbcopy) → paste (Quartz CGEventPost / osascript fallback)
settings.py        GUI: hotkey/model/dictionary/options (tkinter, stdlib)
volume_bar.py      floating wave animation while recording (PyObjC, optional)
convert_pt_to_ct2.py   .pt → CTranslate2 converter (for model prep)
launchd/           LaunchAgent plist for login autostart
```

~1000 lines total, no HTTP server, no cloud service, no build step.

## Login autostart (optional)

```bash
cp launchd/com.charlie.talk2clip.plist ~/Library/LaunchAgents/
launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/com.charlie.talk2clip.plist
```

The LaunchAgent launches talk2clip *via Terminal* (so the hotkey/accessibility
permission chain works — launching directly from launchd cannot receive key
events on macOS 15) and auto-hides the Terminal window.

## Troubleshooting

| Symptom | Fix |
|---|---|
| Hotkey does nothing | Check Input Monitoring has Terminal; restart talk2clip |
| No auto-paste | Check Accessibility has Terminal + `/usr/bin/osascript`; watch terminal output for `⚠` |
| Text pasted twice | Another instance is running — we guard with a pidfile; quit via menu-bar icon or `./run.sh quit`, then start once |
| Noise/traditional chars | Enable `auto_lang`, add words to `corrections`, or switch `model` to `medium` |
| Model download 429 (CN) | Use Method A above (Azure CDN) + `convert_pt_to_ct2.py` |

## License

[MIT](LICENSE). Built on open sources: [faster-whisper](https://github.com/SYSTRAN/faster-whisper), [sounddevice](https://python-sounddevice.readthedocs.io/), [pynput](https://github.com/moses-palmer/pynput), [rumps](https://github.com/jaredks/rumps), [opencc](https://github.com/siara-cc/OpenCC_zh). Whisper models belong to OpenAI (MIT-licensed weights per [openai/whisper](https://github.com/openai/whisper)).
