#!/usr/bin/env python3
"""从 linux/managed.json 生成 macOS plist 与 Windows .reg。

三个平台的策略集合必须同源，否则改一处忘一处就会分叉。所以只维护一份
linux/managed.json：macOS 直接由它生成（平台差异为零），Windows 由它
加上 windows/extra.json 里那批 Windows 专属策略生成。

用法（仓库根目录）:
    python3 tools/build.py

只依赖标准库。
"""

import json
import pathlib
import plistlib

ROOT = pathlib.Path(__file__).resolve().parent.parent
BASE = json.loads((ROOT / "linux" / "managed.json").read_text(encoding="utf-8"))
WIN_EXTRA = json.loads((ROOT / "windows" / "extra.json").read_text(encoding="utf-8"))

# EdgeUpdate 是独立注册表键，不属于 Edge 策略键，单独处理。
EDGE_UPDATE = {"CreateDesktopShortcutDefault": 0}

HEADER = """Windows Registry Editor Version 5.00

; ============================================================
; Microsoft Edge 去臃肿策略（Windows）
;
; 自动生成，不要直接改这个文件——改 linux/managed.json 与 windows/extra.json，
; 然后跑 python3 tools/build.py。
;
; 用法：双击 → 是 → 重启 Edge → edge://policy → 重新加载政策
;
; 撤销：删除下面两个注册表键
;   HKEY_LOCAL_MACHINE\\SOFTWARE\\Policies\\Microsoft\\Edge
;   HKEY_LOCAL_MACHINE\\SOFTWARE\\Policies\\Microsoft\\EdgeUpdate
;
; 注意：域管 / Intune 环境里组策略会覆盖这些值，edge://policy 的
; source 会显示 Platform 而不是 Registry。
; ============================================================

"""


def reg_value(value):
    if isinstance(value, bool):
        return "dword:00000001" if value else "dword:00000000"
    if isinstance(value, int):
        return f"dword:{value:08x}"
    return '"' + str(value).replace("\\", "\\\\").replace('"', '\\"') + '"'


def build_reg():
    lines = [HEADER.rstrip("\n"), "", "[HKEY_LOCAL_MACHINE\\SOFTWARE\\Policies\\Microsoft\\Edge]", ""]
    for name, value in BASE.items():
        lines.append(f'"{name}"={reg_value(value)}')
    lines += ["", "; ---- 仅 Windows 支持的策略 ----", ""]
    for name, value in WIN_EXTRA.items():
        lines.append(f'"{name}"={reg_value(value)}')
    lines += ["", "[HKEY_LOCAL_MACHINE\\SOFTWARE\\Policies\\Microsoft\\EdgeUpdate]", ""]
    for name, value in EDGE_UPDATE.items():
        lines.append(f'"{name}"={reg_value(value)}')
    # HEADER 里用的是 \n，统一压成 CRLF 再转 UTF-16，否则 regedit 会看到混合行尾
    body = "\n".join(lines).replace("\r\n", "\n").replace("\n", "\r\n") + "\r\n"
    # .reg 必须是 UTF-16LE + BOM，否则中文注释会被 regedit 读成乱码
    (ROOT / "windows" / "edge-debloat.reg").write_bytes(b"\xff\xfe" + body.encode("utf-16-le"))
    return len(BASE) + len(WIN_EXTRA) + len(EDGE_UPDATE)


def build_plist():
    out = {}
    for name, value in BASE.items():
        out[name] = value if isinstance(value, bool) else (
            value if isinstance(value, int) else str(value))
    with open(ROOT / "macos" / "com.microsoft.Edge.plist", "wb") as f:
        plistlib.dump(out, f, sort_keys=True)
    return len(out)


if __name__ == "__main__":
    n_reg = build_reg()
    n_plist = build_plist()
    print(f"linux/managed.json        {len(BASE)} 条")
    print(f"windows/edge-debloat.reg  {n_reg} 个值")
    print(f"macos/…plist              {n_plist} 条")
