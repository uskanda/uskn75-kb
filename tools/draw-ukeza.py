# -*- coding: utf-8 -*-
"""受け座（挟む案・U12 検討中）の断面図と平面図を figures/ へ描く。

寸法は pcb-spec.md §3 / §9 U2 の 2026-09-19 実測値と、MX スイッチの
「プレート天面 → PCB 天面 5.0mm」。プレート厚 1.5・PCB 厚 1.6 は仮定。
スイッチ座標は place-right.py（gen-layout.py の出力）から写した。

    python3 tools/draw-ukeza.py   # matplotlib が要る
"""
import math
import os
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager
from matplotlib.patches import Rectangle, Polygon, Circle, Wedge

fp = font_manager.FontProperties(fname="/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc")
plt.rcParams["font.family"] = fp.get_name()
font_manager.fontManager.addfont("/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc")

T_LIP = 0.5      # リップ厚（案A）
T_PLATE = 1.5    # プレート厚（仮定）
Z_PCB_TOP = 5.0  # MX: プレート天面→PCB天面
T_PCB = 1.6
R_MOD = 17.5
R_LIP = 16.5     # Ø33.0
R_HOLE = 17.65   # Ø35.3
R_OPEN = 21.0    # Ø42
R_IN, R_OUT = 16.0, 17.0     # 当たり面 Ø32〜34
R_RING_OD = 23.0             # Ø46
Z_MOD_BOT = T_LIP + 1.25
Z_J1 = T_LIP + 5.5
J1_R_OUT, J1_W = 14.5, 2.5   # J1 外側の辺 r、径方向幅

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "figures")

C = dict(plate="#b8c4d6", mod="#c0392b", ovl="#f4d7d1", ring="#2e8b57", pcb="#3b6e3b", j1="#f0f0f0", ffc="#e6b422")

# ---------------- 断面 ----------------
fig, ax = plt.subplots(figsize=(14, 9))
X = 30
for s in (-1, 1):
    x0, x1 = (R_HOLE, X) if s > 0 else (-X, -R_HOLE)
    ax.add_patch(Rectangle((x0, 0), x1 - x0, T_PLATE, color=C["plate"], ec="k", lw=0.8))
    lx0, lx1 = (R_LIP, R_HOLE) if s > 0 else (-R_HOLE, -R_LIP)
    ax.add_patch(Rectangle((lx0, 0), lx1 - lx0, T_LIP, color="#7f93b3", ec="k", lw=0.8))
ax.add_patch(Rectangle((-R_MOD, T_LIP), 2 * R_MOD, 0.25, color=C["ovl"], ec="k", lw=0.8))
ax.add_patch(Rectangle((-R_MOD, T_LIP + 0.25), 2 * R_MOD, 1.0, color=C["mod"], ec="k", lw=0.8))
ax.add_patch(Rectangle((-J1_R_OUT, Z_MOD_BOT), J1_W, Z_J1 - Z_MOD_BOT, color=C["j1"], ec="k", lw=0.8))
ffc_x = -J1_R_OUT + J1_W / 2
ax.plot([ffc_x, ffc_x, ffc_x + 2.5, 12], [Z_MOD_BOT + 1.0, Z_J1 + 0.6, Z_PCB_TOP + T_PCB + 1.4, Z_PCB_TOP + T_PCB + 1.4],
        color=C["ffc"], lw=3, solid_capstyle="round")
for s in (-1, 1):
    x0, x1 = (R_IN, R_RING_OD) if s > 0 else (-R_RING_OD, -R_IN)
    ax.add_patch(Rectangle((x0, Z_MOD_BOT), x1 - x0, Z_PCB_TOP - Z_MOD_BOT, color=C["ring"], ec="k", lw=0.8))
    cx0, cx1 = (R_IN, R_OUT) if s > 0 else (-R_OUT, -R_IN)
    ax.add_patch(Rectangle((cx0, Z_MOD_BOT - 0.06), cx1 - cx0, 0.12, color="#ffd400", ec=None))
for s in (-1, 1):
    x0, x1 = (R_OPEN, X) if s > 0 else (-X, -R_OPEN)
    ax.add_patch(Rectangle((x0, Z_PCB_TOP), x1 - x0, T_PCB, color=C["pcb"], ec="k", lw=0.8))

# 寸法線: 右側に並べ、文字は右端の列に揃える
TX = 47.5
def dim(x, z0, z1, text, ty):
    ax.annotate("", (x, z0), (x, z1), arrowprops=dict(arrowstyle="<->", lw=0.9, shrinkA=0, shrinkB=0))
    for z in (z0, z1):
        ax.plot([x - 0.5, x + 0.5], [z, z], color="k", lw=0.5)
    ax.annotate(text, (x + 0.3, (z0 + z1) / 2), (TX, ty), fontsize=10, va="center", ha="left",
                arrowprops=dict(arrowstyle="-", lw=0.6, color="gray"))
dim(31.5, 0, T_LIP, f"リップ厚 {T_LIP}（= 沈み込み量 U4）", -1.3)
dim(33.5, 0, Z_MOD_BOT, f"天面 → モジュール裏面 {Z_MOD_BOT}（実測 1.25 + リップ）", 0.3)
dim(35.5, Z_MOD_BOT, Z_PCB_TOP, f"受け座の厚み {Z_PCB_TOP - Z_MOD_BOT:.2f}（= 5.0 − {Z_MOD_BOT}）", 5.1)
dim(37.5, 0, Z_PCB_TOP, "プレート天面 → PCB 天面 5.0（MX スイッチが決める）", 1.9)
dim(39.5, 0, Z_J1, f"天面 → J1 先端 {Z_J1}（実測 5.5 + リップ）", 3.5)
dim(41.5, Z_PCB_TOP, Z_PCB_TOP + T_PCB, "PCB 厚 1.6 → J1 先端は穴の中に収まる", 6.7)
# 荷重
ax.annotate("", (0, T_LIP + 0.05), (0, -1.3), arrowprops=dict(arrowstyle="-|>", lw=2.5, color="k"))
ax.text(0.6, -0.7, "指で押す力", fontsize=11, va="center")
for s in (-1, 1):
    ax.annotate("", (s * 16.5, Z_PCB_TOP - 0.1), (s * 16.5, Z_MOD_BOT + 0.15), arrowprops=dict(arrowstyle="-|>", lw=2, color="#ffd400"))
    ax.annotate("", (s * 22, Z_PCB_TOP + 0.6), (s * 22, Z_MOD_BOT + 0.3), arrowprops=dict(arrowstyle="-|>", lw=2, color="#ffd400"))
ax.text(8, -0.7, "荷重の経路（黄矢印）: オーバーレイ → モジュール PCB → 受け座 → メイン PCB 天面。圧縮だけ", fontsize=9.5, ha="left", va="center", color="#8a6d00")
# 番号付き注記
notes = [
    ((-24, T_PLATE / 2), "① プレート（PETG 自製。厚 1.5 は仮定、パッド周りは 1.5 以下）"),
    ((R_LIP + 0.6, T_LIP / 2), "② リップ 内径 Ø33.0。モジュールは下から入れてここで止まる"),
    ((-16.5, Z_MOD_BOT), "③ 当たり面 Ø32〜34（黄、幅 1mm）。裏面の縁 1.5mm 幅だけに当てる"),
    ((-20, 3.5), "④ 受け座（平ワッシャー、PETG）。内径 Ø32 貫通、外径 Ø46。外周部はプレート裏に当てない（隙間 0.25）"),
    ((-22, Z_PCB_TOP + 0.05), "⑤ 受け座は PCB の Ø42 穴縁に片側 2mm 載る。PCB に穴は要らない"),
    ((-J1_R_OUT + J1_W / 2, Z_J1 - 0.3), "⑥ J1（2.5×9.0、突出 4.25）。FFC は真下へ抜けて PCB 裏面で曲げ、基板側コネクタへ"),
]
for i, (xy, text) in enumerate(notes):
    ax.annotate(text[:1], xy, xy, fontsize=11, ha="center", va="center", color="k",
                bbox=dict(boxstyle="circle,pad=0.1", fc="white", ec="k", lw=0.6))
    ax.text(-31, 8.0 + i * 0.7, text, fontsize=10, va="center")
ax.text(-X + 0.5, Z_PCB_TOP + T_PCB / 2, "メイン PCB", color="w", va="center", fontsize=10)
ax.text(4, Z_PCB_TOP + T_PCB / 2, "Ø42 開口（受け座は通らない。通るのは J1 と FFC だけ）", ha="center", va="center", fontsize=10)
ax.text(-6, T_LIP + 0.75, "モジュール（Ø35.0、PCB + オーバーレイ 1.25）", color="w", fontsize=10, ha="center", va="center")
ax.axhline(0, color="k", lw=0.5, ls=":")
ax.set_xlim(-X - 2, X + 45); ax.set_ylim(11.8, -2.0)
ax.set_aspect(2.6); ax.set_xlabel("開口中心からの距離 [mm]（左が J1 ＝ 9時側。縦は 2.6 倍に引き伸ばし）"); ax.set_ylabel("Z [mm]（プレート天面 = 0、下が正）")
ax.set_title(f"挟む案の断面（リップ {T_LIP}mm の場合。リップ 1.0 なら受け座 2.75、J1 先端 6.5）", fontsize=13)
fig.tight_layout(); fig.savefig(os.path.join(OUT, "ukeza-section.png"), dpi=150)

# ---------------- 平面 ----------------
fig, ax = plt.subplots(figsize=(10, 10))
cx, cy = 6.48, 76.20
switches = {"SW21": (14.29, 47.62, "Q行左端"), "SW46": (17.62, 104.78, "右Space"), "SW30": (38.10, 66.67, "H"),
            "SW38": (47.62, 85.72, "Z行"), "SW22": (33.34, 47.62, "Q行")}
# PCB と開口
ax.add_patch(Rectangle((-24, cy - 34), 24 + 55, 68, color="#dfeadf", ec="k", lw=0.8))
ax.add_patch(Circle((cx, cy), R_OPEN, color="white", ec="k", lw=0.8))

ax.text(-23.5, cy - 33, "メイン PCB（左端 X=−24）", fontsize=9, va="top")
# スイッチ胴体
for ref, (x, y, name) in switches.items():
    ax.add_patch(Rectangle((x - 7, y - 7), 14, 14, color="#c9c9c9", ec="k", lw=0.8))
    ax.text(x, y, f"{ref}\n{name}", ha="center", va="center", fontsize=9)
# 受け座外形（Ø46、SW21 / SW46 方向をえぐる）
import numpy as np
th = np.linspace(0, 2 * math.pi, 720)
pts = []
for t in th:
    r = R_RING_OD
    for x, y in [(switches["SW21"][0], switches["SW21"][1]), (switches["SW46"][0], switches["SW46"][1])]:
        # 胴体 + 0.5mm 逃げの正方形に当たる半径
        for rr in np.arange(21.0, R_RING_OD, 0.05):
            px, py = cx + rr * math.cos(t), cy + rr * math.sin(t)
            if abs(px - x) <= 7.5 and abs(py - y) <= 7.5:
                r = min(r, rr - 0.05); break
    pts.append((cx + r * math.cos(t), cy + r * math.sin(t)))
ax.add_patch(Polygon(pts, closed=True, color=C["ring"], alpha=0.45, ec="k", lw=1))
ax.add_patch(Circle((cx, cy), R_OPEN, fill=False, ec="k", lw=1.2, ls=(0, (4, 2))))
ax.add_patch(Circle((cx, cy), R_IN, color="white", ec="k", lw=0.8))
ax.add_patch(Wedge((cx, cy), R_OUT, 0, 360, width=R_OUT - R_IN, color="#ffd400", ec="k", lw=0.5))
# 平らな部分（12時・6時）とモジュール外形・J1
ax.add_patch(Circle((cx, cy), R_MOD, fill=False, ec="#c0392b", lw=1.2, ls="--"))
ax.add_patch(Rectangle((cx - J1_R_OUT, cy - 4.5), J1_W, 9.0, color="#f0f0f0", ec="k", lw=0.8))
ax.text(cx - J1_R_OUT + J1_W / 2, cy, "J1", ha="center", va="center", fontsize=9)
# J1 の爪
for s in (-1, 1):
    y0 = cy + 4.8 if s > 0 else cy - 6.0
    ax.add_patch(Rectangle((cx - R_IN, y0), 1.5, 1.2, color=C["ring"], ec="k", lw=0.6))
ax.text(cx - R_IN - 0.5, cy + 7.5, "J1 を挟む爪\n（部品と当たらないか要現物確認）", ha="right", fontsize=8.5)
# 注記
ax.text(cx, cy + 12.5, "内径 Ø32 貫通\n（J1・FFC・裏面部品はこの中）", ha="center", fontsize=9)
ax.text(cx, cy - 15.6, "当たり面 Ø32〜34（黄）", ha="center", fontsize=9, color="#8a6d00")
ax.text(cx + 22, cy + 22, "受け座 外径 Ø46（緑）\nSW21 と SW46 の方向だけ\n胴体から 0.5mm 逃げてえぐる\n→ これが受け座の回り止め", fontsize=9.5, va="top")
ax.text(cx - 29.5, cy - 30, "赤破線: モジュール外形 Ø35.0（プレートの Ø35.3 穴で拘束）\n黒破線: メイン PCB の Ø42 開口。緑はその外へ 2mm 掛かって PCB 天面に載る", fontsize=8.5, va="top")
ax.set_xlim(-26, 58); ax.set_ylim(cy + 36, cy - 36); ax.set_aspect("equal")
ax.set_xlabel("X [mm]（キー領域左上が原点）"); ax.set_ylabel("Y [mm]（下が正）")
ax.set_title("挟む案の平面（プレートを外して上から見た受け座とスイッチ胴体）", fontsize=13)
fig.tight_layout(); fig.savefig(os.path.join(OUT, "ukeza-plan.png"), dpi=150)
print("ok")
