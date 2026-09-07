#!/usr/bin/env python3
"""
talk2clip 设置界面 — 热键 / 词库 / 选项

用法:
    python3 settings.py              # 打开设置窗口
    python3 settings.py --config     # 打印当前配置 JSON 后退出（供脚本检查）

所有改动实时保存到 config.json；运行中的 talk2clip 在下次识别时自动生效
（热键改动需重启 talk2clip）。
"""
import json
import os
import sys
import tkinter as tk
from tkinter import messagebox, ttk

HERE = os.path.dirname(os.path.abspath(__file__))
CONFIG = os.path.join(HERE, "config.json")

# 可选的快捷键（pynput Key 名 → 显示名）
HOTKEYS = [
    ("cmd_r", "右 ⌘ (Command)"),
    ("alt_r", "右 ⌥ (Option)"),
    ("ctrl_r", "右 ⌃ (Control)"),
    ("shift_r", "右 ⇧ (Shift)"),
    ("cmd", "左 ⌘ (Command)"),
    ("alt", "左 ⌥ (Option)"),
    ("ctrl", "左 ⌃ (Control)"),
    ("space", "空格 (Space)"),
    ("f5", "F5"),
    ("f6", "F6"),
]
HOTKEY_NAMES = {name: label for name, label in HOTKEYS}

MODELS = [
    ("tiny", "tiny（最快，基础准确率）"),
    ("base", "base（快，准确率一般）"),
    ("small", "small（推荐，准确率好）"),
    ("medium", "medium（最准，慢 3 倍）"),
]


def load():
    try:
        with open(CONFIG, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def save(cfg):
    with open(CONFIG, "w", encoding="utf-8") as f:
        json.dump(cfg, f, ensure_ascii=False, indent=2)


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("talk2clip 设置")
        self.geometry("460x560")
        self.cfg = load()

        # ── 热键区 ──
        ttk.LabelFrame(self, text=" 快捷键（按住说话） ").pack(fill="x", padx=12, pady=(12, 6))
        frm_hk = ttk.Frame(self)
        frm_hk.pack(fill="x", padx=24)
        ttk.Label(frm_hk, text="选择快捷键:").grid(row=0, column=0, sticky="w")
        # 初始值：config 键名 → 显示格式（"cmd_r" → "cmd_r（右 ⌘ (Command)）"）
        raw_hk = self.cfg.get("hotkey", "cmd_r")
        hk_display = next((f"{n}（{label}）" for n, label in HOTKEYS if n == raw_hk), raw_hk)
        self.hk_var = tk.StringVar(value=hk_display)
        hk_box = ttk.Combobox(frm_hk, textvariable=self.hk_var, state="readonly", width=24)
        hk_box["values"] = [f"{n}（{label}）" for n, label in HOTKEYS]
        hk_box.grid(row=0, column=1, padx=8, pady=4)
        self.hk_label = ttk.Label(frm_hk, text="", foreground="#888")
        self.hk_label.grid(row=1, column=0, columnspan=2, sticky="w", pady=(0, 4))
        self._update_hk_label()

        btn = ttk.Button(self, text="保存设置", command=self.save_settings)
        btn.pack(pady=(6, 10), fill="x", padx=12)

        # ── 选项区 ──
        frm_opt = ttk.LabelFrame(self, text=" 选项 ")
        frm_opt.pack(fill="x", padx=12, pady=6)
        self.paste_var = tk.BooleanVar(value=self.cfg.get("auto_paste", True))
        ttk.Checkbutton(frm_opt, text="识别后自动粘贴到光标处",
                        variable=self.paste_var).pack(anchor="w", padx=12, pady=4)
        self.lang_var = tk.BooleanVar(value=self.cfg.get("auto_lang", False))
        ttk.Checkbutton(frm_opt, text="中英文自动检测（关=固定中文）",
                        variable=self.lang_var).pack(anchor="w", padx=12, pady=4)
        self.punct_var = tk.BooleanVar(value=self.cfg.get("add_punct", False))
        ttk.Checkbutton(frm_opt, text="自动加标点（逗号/问号/句号）",
                        variable=self.punct_var).pack(anchor="w", padx=12, pady=4)
        frm_model = ttk.Frame(frm_opt)
        frm_model.pack(fill="x", padx=12, pady=(4, 8))
        ttk.Label(frm_model, text="识别模型:").pack(side="left")
        self.model_var = tk.StringVar(value=self.cfg.get("model", "small"))
        mbox = ttk.Combobox(frm_model, textvariable=self.model_var, state="readonly", width=28)
        mbox["values"] = [n for n, _ in MODELS]
        mbox.pack(side="left", padx=8)

        # ── 词库区 ──
        frm_dict = ttk.LabelFrame(self, text=" 词库修正（识别老错的词 → 正确的词） ")
        frm_dict.pack(fill="both", expand=True, padx=12, pady=6)

        frm_add = ttk.Frame(frm_dict)
        frm_add.pack(fill="x", padx=8, pady=(6, 2))
        ttk.Label(frm_add, text="错的:").pack(side="left")
        self.wrong_var = tk.StringVar()
        ttk.Entry(frm_add, textvariable=self.wrong_var, width=14).pack(side="left", padx=4)
        ttk.Label(frm_add, text="→ 对的:").pack(side="left")
        self.right_var = tk.StringVar()
        ttk.Entry(frm_add, textvariable=self.right_var, width=14).pack(side="left", padx=4)
        ttk.Button(frm_add, text="添加", command=self.add_correction).pack(side="left", padx=4)

        self.tree = ttk.Treeview(frm_dict, columns=("wrong", "right"), show="headings", height=8)
        self.tree.heading("wrong", text="识别错的词")
        self.tree.heading("right", text="修正为")
        self.tree.column("wrong", width=200)
        self.tree.column("right", width=200)
        self.tree.pack(fill="both", expand=True, padx=8, pady=4)

        btn_del = ttk.Button(frm_dict, text="删除选中", command=self.delete_correction)
        btn_del.pack(pady=(0, 6))

        self._refresh_corrections()

    def _update_hk_label(self):
        v = self.hk_var.get()
        name = v.split("（")[0].strip()   # 从 "cmd_r（右 ⌘ (Command)）" 提取键名
        self.hk_label.config(text=f"当前: {HOTKEY_NAMES.get(name, name)}（热键改变需重启 talk2clip 生效）")

    def _refresh_corrections(self):
        self.tree.delete(*self.tree.get_children())
        for wrong, right in self.cfg.get("corrections", {}).items():
            self.tree.insert("", "end", values=(wrong, right))

    def add_correction(self):
        wrong = self.wrong_var.get().strip()
        right = self.right_var.get().strip()
        if not wrong or not right:
            messagebox.showwarning("提示", "请填写「错的词」和「对的词」")
            return
        self.cfg.setdefault("corrections", {})[wrong] = right
        save(self.cfg)
        self._refresh_corrections()
        self.wrong_var.set("")
        self.right_var.set("")
        messagebox.showinfo("已保存", "词库已添加，下次识别立即生效。")

    def delete_correction(self):
        sel = self.tree.selection()
        if not sel:
            return
        wrong = self.tree.item(sel[0])["values"][0]
        self.cfg.get("corrections", {}).pop(wrong, None)
        save(self.cfg)
        self._refresh_corrections()

    def save_settings(self):
        self.cfg["hotkey"] = self.hk_var.get().split("（")[0].strip()   # 只存键名
        self.cfg["model"] = self.model_var.get()
        self.cfg["auto_paste"] = self.paste_var.get()
        self.cfg["auto_lang"] = self.lang_var.get()
        self.cfg["add_punct"] = self.punct_var.get()
        save(self.cfg)
        messagebox.showinfo(
            "已保存",
            "设置已保存。\n词库/选项立即生效；热键改动需重启 talk2clip\n"
            "(退出后重新双击 启动talk2clip.command)",
        )


def main():
    if "--config" in sys.argv:
        print(json.dumps(load(), ensure_ascii=False, indent=2))
        sys.exit(0)
    App().mainloop()


if __name__ == "__main__":
    main()
