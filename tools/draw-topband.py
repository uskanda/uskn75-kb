# -*- coding: utf-8 -*-
"""上端の帯（Y=−26〜0）への MCU と半体間 USB-C キットの配置案（U15①）を figures/ へ描く。

外形は pcb-spec.md §2、スイッチ座標は place-left.py / place-right.py（gen-layout.py の出力）から写した。
MCU の外形 21×51（Pico 系）、キット 20×15（pcb-spec.md §6）。配置座標はこのスクリプトが持つ案であり、
仕様として確定したら pcb-spec.md §2 / §9 U15 に転記する。

    python3 tools/draw-topband.py   # matplotlib が要る
"""
import os
import re

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager
from matplotlib.patches import Circle, Polygon, Rectangle

FONT = "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"
font_manager.fontManager.addfont(FONT)
plt.rcParams["font.family"] = font_manager.FontProperties(fname=FONT).get_name()

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "..", "figures")

OUTLINE = {
    "left": [(-32.5, -26), (164.9, -26), (164.9, 117.3), (126.8, 117.3), (126.8, 136.35), (92.25, 136.35), (92.25, 117.3), (-32.5, 117.3)],
    "right": [(-24.0, -26), (236.4, -26), (236.4, 117.3), (65.85, 117.3), (65.85, 136.35), (31.3, 136.35), (31.3, 117.3), (-24.0, 117.3)],
}
MCU_W, MCU_H = 51.0, 21.0   # 長辺を X に沿わせる
KIT_W, KIT_H = 20.0, 15.0   # 差し込み口のある辺（20mm）を Y=−26 の外周に揃える

# 配置案。(x0, y0) は左下ではなく左上（Y は下が正）
PLAN = {
    "right": {
        # 右上はキーが無い（X 185.7〜236.4 / Y −26〜76。PrtSc・BS・EnterU の右、↑ の上）ので MCU を縦に置ける
        "mcu": dict(x0=200.5, y0=-26.0, label="RP2040-Plus\n（マスタ）\nUSB-C は\n後ろ −Y 向き\n→ PC へ", usb="-y"),
        "kit": dict(x0=-22.0, y0=-26.0, label="半体間 USB-C キット\n差し込み口は後ろ −Y 向き"),
    },
    "left": {
        "mcu": dict(x0=-32.5, y0=-23.5, label="Pico（スレーブ）\nmicro-USB は左端 −X 向き（書き込み用）", usb="-x"),
        "kit": dict(x0=164.9 - 20.0 - 2.0, y0=-26.0, label="半体間 USB-C キット\n差し込み口は後ろ −Y 向き"),
    },
}


def switches(path):
    txt = open(path).read()
    return [(float(x), float(y)) for _, x, y in re.findall(r'\("(SW\d+)",\s*([\d.-]+),\s*([\d.-]+)', txt)]


fig, axes = plt.subplots(2, 1, figsize=(15, 11))
for ax, side, title in ((axes[0], "left", "左半体（スレーブ）"), (axes[1], "right", "右半体（マスタ）")):
    ax.add_patch(Polygon(OUTLINE[side], closed=True, color="#e3ecdf", ec="k", lw=1))
    xs = [p[0] for p in OUTLINE[side]]
    ax.add_patch(Rectangle((min(xs), -26), max(xs) - min(xs), 26, color="#fff2c6", ec="none"))
    ax.text((min(xs) + max(xs)) / 2 - 10, -4, "上端の帯 Y=−26〜0（黄。スイッチもソケットも無い）", ha="center", va="center", fontsize=9.5, color="#7a5c00")
    for x, y in switches(os.path.join(HERE, "..", f"place-{side}.py")):
        ax.add_patch(Rectangle((x - 7, y - 7), 14, 14, color="#cfd6d3", ec="#889", lw=0.4))
    if side == "right":
        ax.add_patch(Circle((6.48, 76.20), 21.0, color="white", ec="k", lw=0.8))
        ax.text(6.48, 76.2, "Ø42", ha="center", va="center", fontsize=9)
    if side == "left":
        for y in (19.05, 57.15, 95.25):
            ax.add_patch(Circle((-17.145, y), 6.0, color="#d9c7ea", ec="k", lw=0.6))
    p = PLAN[side]
    m = p["mcu"]
    mw, mh = (MCU_H, MCU_W) if m["usb"] == "-y" else (MCU_W, MCU_H)
    ax.add_patch(Rectangle((m["x0"], m["y0"]), mw, mh, color="#3f8f5f", ec="k", lw=0.8))
    if m["usb"] == "-y":
        ax.add_patch(Rectangle((m["x0"] + mw / 2 - 4.5, m["y0"] - 1.5), 9.0, 3.0, color="#222", ec="k"))
    else:
        ux = m["x0"] + mw if m["usb"] == "+x" else m["x0"] - 3.0
        ax.add_patch(Rectangle((ux, m["y0"] + mh / 2 - 4.5), 3.0, 9.0, color="#222", ec="k"))
    ax.text(m["x0"] + mw / 2, m["y0"] + mh / 2, m["label"], ha="center", va="center", fontsize=9, color="w")
    if side == "right":
        ax.add_patch(Rectangle((185.7, -26), 236.4 - 185.7, 102.2, fill=False, ec="#3f8f5f", lw=1, ls="--"))
        ax.text(233, 60, "キーの無い領域\nX 185.7〜236.4\nY −26〜76.2", ha="right", va="center", fontsize=8.5, color="#2a6a44")
    k = p["kit"]
    ax.add_patch(Rectangle((k["x0"], k["y0"]), KIT_W, KIT_H, color="#c8722a", ec="k", lw=0.8))
    ax.add_patch(Rectangle((k["x0"] + 5.5, k["y0"] - 1.5), 9.0, 3.0, color="#222", ec="k"))
    kx = k["x0"] + KIT_W + 2 if side == "right" else k["x0"] - 2
    ax.text(kx, -18.5, k["label"], ha="left" if side == "right" else "right", va="center", fontsize=9)
    ax.text(m["x0"] + mw / 2, -34.0 if side == "right" else -30.5,
            f"MCU 外形 X {m['x0']:.1f}〜{m['x0'] + mw:.1f} / Y {m['y0']:.1f}〜{m['y0'] + mh:.1f}", ha="center", va="bottom", fontsize=8.5)
    ax.text(k["x0"] + KIT_W / 2, -30.5 if side == "left" else -33.5, f"キット X {k['x0']:.1f}〜{k['x0'] + KIT_W:.1f} / Y −26.0〜−11.0", ha="center", va="bottom", fontsize=8.5)
    if side == "right":
        ax.annotate("", (m["x0"] + mw / 2, -28.5), (k["x0"] + KIT_W / 2, -28.5), arrowprops=dict(arrowstyle="<->", lw=0.8, color="#a00"))
        ax.text(100, -29.0, f"どちらも後ろ向きだが、口の中心どうしは {m['x0'] + mw / 2 - k['x0'] - KIT_W / 2:.0f}mm 離れる（取り違え防止 §12）", ha="center", va="bottom", fontsize=9, color="#a00")
    ax.set_title(title, fontsize=13, loc="left")
    ax.set_xlim(-40, 245)
    ax.set_ylim(140, -40)
    ax.set_aspect("equal")
    ax.set_xlabel("X [mm]")
    ax.set_ylabel("Y [mm]（下が正）")
fig.suptitle("MCU と半体間 USB-C キットの配置案（U15①）。PC 用も半体間も、ケーブルは後ろ（−Y）から出る", fontsize=13)
fig.tight_layout()
fig.savefig(os.path.join(OUT, "topband-plan.png"), dpi=130)
print("ok")
