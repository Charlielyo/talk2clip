# talk2clip

按住 `右 ⌘`（可在设置界面改）说话，松开自动转文字、进剪贴板并粘贴到光标处（macOS）。

- 识别走本地 [faster-whisper](https://github.com/SYSTRAN/faster-whisper)（离线、免费、不限量）
- 输出走 `pbcopy`（macOS 自带剪贴板，**无需任何权限**）
- 单文件、无 HTTP 服务、无 AI 对话、无界面依赖

## 依赖

```bash
pip install numpy sounddevice faster-whisper pynput rumps
```

首次识别会自动下载 whisper 模型（`small`，约 460MB，之后用缓存）。
想更轻量可改 `talk2clip.py` 顶部的 `MODEL = "tiny"`（~75MB，更快但中文准确率略低）。

## 使用

```bash
python3 talk2clip.py        # 常驻：菜单栏出现 🎙️ 图标，按住热键说话
python3 talk2clip.py --once # 无界面：等一次按键后自动退出
```

| 操作 | 效果 |
|---|---|
| 按住 `Option(⌥)+Space` 说话，松开 | 识别 → 复制到剪贴板 + 系统通知 |
| 说话停顿 1.2 秒 | 自动停止并识别（不用松手） |
| 点击菜单栏 🎙️ → 开始说话 / 停止 | 鼠标方式说话（热键失效时的备用） |
| 播放/播报时再按热键 | （当前为单次任务，安全） |

## 与旧 voice-hub (Jarvis) 的区别

| | talk2clip | voice-hub |
|---|---|---|
| 功能 | 只做 说话→剪贴板 | 语音打字+AI对话+播报+路由+5种界面 |
| 依赖 | sounddevice / whisper / pynput / rumps | 全包 + HTTP + 密钥 + hermes |
| 需要密钥 | 无 | STT/AI 密钥 |
| 需要网络 | 仅首次下载模型 | 全程 |
| 代码量 | ~200 行单文件 | 10+ 文件 |

## 已知事项（经验教训）

- macOS 15 上「辅助功能」授权对 CLI 二进制有系统 bug（面板显示已授权但实际不生效）；
  键盘监听请从**终端启动**（终端已授权「输入监控」即可继承），或手动给 python 添加「输入监控」权限。
- 剪贴板写入不需要任何 TCC 权限——这是本设计的关键简化。
- 启动热键时若看到 `This process is not trusted!` 警告，仍可先测菜单栏 🎙️ 方式。

## 设置界面

```bash
python3 settings.py     # 打开设置窗口
```

- **快捷键**：右⌘ / 右⌥ / 右⌃ / F5 / 空格…（改后需重启 talk2clip）
- **词库**：识别老错的词 → 正确的词，图形化增删，保存后立即生效（无需重启）
- **选项**：模型选择（tiny/base/small/medium）、自动粘贴开关

配置存储于 `config.json`（热键/模型/词库，可直接编辑或经设置界面管理）。
