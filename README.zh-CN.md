# talk2clip 🎙️📋

[English](README.md) | **中文**

**按住右 ⌘ 说话，松开 — 文字直接落在光标处。**
*(macOS 按住说话 → 本地离线语音识别 → 自动粘贴)*

一个轻量、完全离线、隐私友好的 macOS 语音输入工具：

- 🔥 **单动作触发**：按住**右 ⌘**（可自选任意键）→ 说话 → 松开 → 文字进入光标处
- 🧠 **本地 AI 识别**：[faster-whisper](https://github.com/SYSTRAN/faster-whisper) — 离线、免费、不限量、无云端、无 API Key
- 📋 **剪贴板 + 自动粘贴**：识别结果自动复制并粘贴
- 🌊 **视觉反馈**：漂浮**胶囊波形**（40fps）实时显示说话音量
- 🇨🇳↔🇬🇧 **中英文自动检测**（可选）、**自动加标点**（可选）、**词库修正**
- 🖥️ **设置界面**：热键 / 模型 / 词库 / 选项，全部可视化点击
- 🚀 **开机自启**（可选，LaunchAgent）

无云端、无账号、数据不离开你的 Mac。

---

## 快速开始

```bash
git clone <本仓库> talk2clip && cd talk2clip
./install.sh          # 创建 .venv、安装依赖、生成 config.json
```

然后**下载模型**（`.pt` 483MB → 转换后 `model.bin` 247MB，一次性；见 [模型](#模型)）：

```bash
# 方法 A — Azure CDN 直连（国内外都稳定，绕开 huggingface 429）：
curl -L -o /tmp/small.pt 'https://openaipublic.azureedge.net/main/whisper/models/9ecf779972d90ba49c06d968637d720dd632c55bbf19d441fb42bf17a411e794/small.pt'
.venv/bin/python3 convert_pt_to_ct2.py /tmp/small.pt models/faster-whisper-small

# 方法 B — 拷贝 CT2 格式模型（如从 HuggingFace 下载 Systran/faster-whisper-small）
# 放到 models/faster-whisper-small/
```

### 授权（仅首次）

| 权限 | 位置 | 用途 |
|---|---|---|
| 输入监控 | 系统设置 → 隐私与安全性 → **输入监控** | 加 Terminal（热键监听） |
| 辅助功能 | 系统设置 → 隐私与安全性 → **辅助功能** | 加 Terminal + `/usr/bin/osascript`（自动粘贴） |

> **macOS 15 注意**：CLI 二进制的权限授权有系统 bug（面板添加了但不生效）。
> 请通过**终端**运行（`./启动talk2clip.command` 或 `./run.sh`）并给**终端本身**授权——
> 子进程会继承。这是经过验证的唯一可靠路径。

### 使用

| 操作 | 方式 |
|---|---|
| 说话 → 出字 | 按住**右 ⌘**，说话，松开 — 文字出现在光标处 |
| 改热键 / 模型 / 词库 | 双击 `打开设置.command`（或 `./run.sh settings.py`） |
| 启动 | 双击 **talk2clip.app**（在 `/Applications`）/ `启动talk2clip.command` / 或开启开机自启（见下） |
| 退出 | `pkill -f talk2clip.py` |

*可选热键：右 ⌘ / 右 ⌥ / 右 ⌃ / 右 ⇧ / ⌘ / ⌥ / ⌃ / 空格 / F5-F20（config.json 的 `hotkey`）*

---

## 功能与配置（`config.json`）

| 配置项 | 默认值 | 含义 |
|---|---|---|
| `hotkey` | `cmd_r` | pynput 键名，如 `alt_r` = 右 Option |
| `model` | `small` | tiny / base / small / medium（越大越准越慢） |
| `beam_size` | `5` | 解码搜索宽度（5=准，1=快） |
| `auto_paste` | `true` | 识别后自动粘贴（失败降级为仅剪贴板） |
| `corrections` | `{}` | 词库：`{"总是听错的词": "正确词"}` — 立即生效 |
| `auto_lang` | `false` | 中英文自动检测（失败回退中文） |
| `add_punct` | `false` | 自动加标点（，。？规则法） |

以上全部可通过**设置界面**修改，无需碰代码。

### 模型

Whisper 模型**不随仓库分发**（保持仓库轻量）。加载顺序：
1. `models/faster-whisper-<MODEL>/`（项目本地，推荐）
2. HuggingFace 缓存
3. 联网下载（兜底；可用 `HF_ENDPOINT` 切镜像）

`convert_pt_to_ct2.py` 把官方 OpenAI `small.pt`（Azure CDN 下载，无需 HuggingFace）
转换为 faster-whisper 的 CTranslate2 格式 — 适合国内 huggingface.co 被限流（429）的用户。

---

## 架构

```
talk2clip.py       核心：热键(pynput) → 录音(sounddevice) → 识别(faster-whisper)
                   → 剪贴板(pbcopy) → 粘贴(Quartz CGEventPost / osascript 回退)
settings.py        设置界面：热键/模型/词库/选项（tkinter）
volume_bar.py      录音时漂浮胶囊波形动画（PyObjC，40fps）
convert_pt_to_ct2.py   .pt → CTranslate2 转换器（模型制备）
launchd/           开机自启 LaunchAgent plist
```

总计约 1000 行，无 HTTP 服务、无云端、无需构建。

## 开机自启（可选）

```bash
cp launchd/com.charlie.talk2clip.plist ~/Library/LaunchAgents/
launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/com.charlie.talk2clip.plist
```

LaunchAgent 通过**终端**启动 talk2clip（保证热键/辅助功能权限链——macOS 15 上
launchd 直接启动的进程收不到键盘事件），并自动隐藏终端窗口。

## 常见问题

| 现象 | 解决 |
|---|---|
| 热键无反应 | 检查「输入监控」里有 Terminal；重启 talk2clip |
| 不自动粘贴 | 检查「辅助功能」有 Terminal + `/usr/bin/osascript`；看终端 `⚠` 输出 |
| 粘贴了两遍 | 有重複实例 — 已用 pidfile 防护；`pkill -f talk2clip.py` 后只启动一次 |
| 噪音/繁体字 | 开 `auto_lang`，词库加 `corrections`，或换 `medium` 模型 |
| 模型下载 429（国内）| 用上面「方法 A」：Azure CDN + `convert_pt_to_ct2.py` |

## License

[MIT](LICENSE)。基于开源：[faster-whisper](https://github.com/SYSTRAN/faster-whisper)、[sounddevice](https://python-sounddevice.readthedocs.io/)、[pynput](https://github.com/moses-palmer/pynput)、[rumps](https://github.com/jaredks/rumps)、[opencc](https://github.com/siara-cc/OpenCC_zh)。Whisper 模型归 OpenAI（MIT 权重）。
