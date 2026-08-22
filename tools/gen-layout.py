#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
uskn75-kb レイアウト成果物ジェネレータ

入力（正本）は以下の2つだけで、本スクリプトは新しい数値を一切持たない:

  - split-jis75-tb.html  の LEFT / RIGHT 配列と circlePad() / encoders()  … 物理配置(u座標)
  - pcb-spec.md          の §4 ピンアサイン / §5 マトリクス表 / §5.5 エンコーダ … 論理配置

両者を突き合わせ、食い違いがあれば出力せずに落ちる。
（CLAUDE.md §6「配列図を変えたら pcb-spec §5 のマトリクス表と必ず同時に直す」の機械的な担保）

出力:
  kle-left.json / kle-right.json      … KLE raw。左上ラベル = "row,col"（VIA互換 / kbplacer 自動検出）
  matrix-left.csv / matrix-right.csv  … 全95キーの座標・行列位置・ラベル・ダイオード位置
  encoders-left.csv                   … エンコーダ3個の座標とピン割当

座標系: 原点はキー領域の左上（u座標 0,0）／ Y は下方向が正（KiCadと同じ）／ 1u = 19.05mm
"""

import csv
import json
import os
import re
import sys

U = 19.05                     # 1u [mm]
DIODE_DY = 5.1                # pcb-spec §6: スイッチ中心から下方5.1mm
DIODE_ROT = 90.0              # pcb-spec §6: 90度回転

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HTML = os.path.join(ROOT, "split-jis75-tb.html")
SPEC = os.path.join(ROOT, "pcb-spec.md")

# pcb-spec §7 / HANDOFF §3: プレートマウント・3箇所のみ
STABS = {("L", 4, 0): "2.25u",   # 左 LShift
         ("L", 5, 4): "2.25u",   # 左 Space
         ("R", 2, 8): "v2u"}     # 右 JIS Enter（縦2u）

# HANDOFF §2.4 内側増設列。右は Z行・最下段をトラックパッドが占有するため ROW0..3 のみ
INNER = {("L", 0, 7), ("L", 1, 7), ("L", 2, 6), ("L", 3, 6), ("L", 4, 6), ("L", 5, 5),
         ("R", 0, 0), ("R", 1, 0), ("R", 2, 0), ("R", 3, 0)}


def die(msg):
    sys.stderr.write("NG: %s\n" % msg)
    sys.exit(1)


# ---------------------------------------------------------------- 入力: HTML

def read_html_arrays():
    """split-jis75-tb.html の LEFT / RIGHT 配列を読む -> {name: [[ (label, x, w), ... ], ...]}"""
    src = open(HTML, encoding="utf-8").read()
    out = {}
    for name in ("LEFT", "RIGHT"):
        head = "const %s=" % name
        i = src.index(head) + len(head)
        depth = 0
        for j in range(i, len(src)):
            if src[j] == "[":
                depth += 1
            elif src[j] == "]":
                depth -= 1
                if depth == 0:
                    raw = src[i:j + 1]
                    break
        else:
            die("%s 配列の終端が見つからない" % name)
        rows = json.loads(raw.replace("'", '"'))
        out[name] = [[(k[0], float(k[1]), float(k[2]) if len(k) > 2 else 1.0)
                      for k in row] for row in rows]
    return out


def read_html_number(pattern, label):
    src = open(HTML, encoding="utf-8").read()
    m = re.search(pattern, src)
    if not m:
        die("HTML から %s を読めない" % label)
    return float(m.group(1))


def read_pad_geometry():
    """circlePad() の bx/by/bw/bh から開口中心を求める（u座標）"""
    src = open(HTML, encoding="utf-8").read()
    m = re.search(r"function circlePad\(\)\{\s*const bx=(-?[\d.]+)\*U,\s*by=([\d.]+)\*ROWH,"
                  r"\s*bw=([\d.]+)\*U,\s*bh=([\d.]+)\*ROWH;", src)
    if not m:
        die("circlePad() のジオメトリを読めない")
    bx, by, bw, bh = (float(g) for g in m.groups())
    return bx + bw / 2.0, by + bh / 2.0


def read_jis_enter():
    """jisEnter() の x1/x2/x3・y1/y2/y3 から JIS Enter の外形を求める（u座標）"""
    src = open(HTML, encoding="utf-8").read()
    i = src.index("function jisEnter()")
    body = src[i:i + 400]
    v = {}
    for name, unit in (("x1", "U"), ("x2", "U"), ("x3", "U"),
                       ("y1", "ROWH"), ("y2", "ROWH"), ("y3", "ROWH")):
        m = re.search(r"\b%s=([\d.]+)\*%s\b" % (name, unit), body)
        if not m:
            die("jisEnter() の %s を読めない" % name)
        v[name] = float(m.group(1))
    # 上段: x1..x2 (1.5u) を y1..y2、下段: x3..x2 (1.25u) を y2..y3
    return {"x_top": v["x1"], "x_bot": v["x3"], "x_right": v["x2"],
            "y_top": v["y1"], "y_mid": v["y2"], "y_bot": v["y3"]}


def read_encoder_geometry():
    """encoders() の bx/bw と縦ピッチから中心座標を求める（u座標）"""
    src = open(HTML, encoding="utf-8").read()
    m = re.search(r"const bx=(-?[\d.]+)\*U, by=\(i\*2\)\*ROWH\+GAP/2, bw=([\d.]+)\*U,"
                  r" bh=2\*ROWH-GAP;", src)
    if not m:
        die("encoders() のジオメトリを読めない")
    bx, bw = float(m.group(1)), float(m.group(2))
    cx = bx + bw / 2.0
    return [(cx, i * 2 + 1.0) for i in range(3)]     # by=i*2rows, bh=2rows -> 中心 = i*2+1


# ------------------------------------------------------------ 入力: pcb-spec

SPEC_SRC = None


def spec():
    global SPEC_SRC
    if SPEC_SRC is None:
        SPEC_SRC = open(SPEC, encoding="utf-8").read()
    return SPEC_SRC


def section(title):
    s = spec()
    i = s.index(title)
    m = re.search(r"\n#{2,3} ", s[i + len(title):])
    return s[i:i + len(title) + (m.start() if m else len(s))]


def read_matrix(half_title):
    """§5 のマトリクス表 -> [[cell or None, ...9], ...6]  ('—' と ENC押込 は None)"""
    body = section(half_title)
    rows = []
    for line in body.splitlines():
        m = re.match(r"\|\*\*ROW(\d)\*\*\|(.*)\|\s*$", line)
        if not m:
            continue
        cells = [c.strip() for c in m.group(2).split("|")]
        if len(cells) != 9:
            die("%s ROW%s の列数が %d（9でない）" % (half_title, m.group(1), len(cells)))
        rows.append([None if (c == "—" or "ENC" in c) else c for c in cells])
    if len(rows) != 6:
        die("%s の行数が %d（6でない）" % (half_title, len(rows)))
    return rows


def read_pins(half_title):
    """§4 のピンアサイン表 -> (rows_gpio[6], cols_gpio[9])"""
    body = section(half_title)
    def grab(key):
        m = re.search(r"\|\s*%s\s*\|\s*`([^`]+)`\s*\|" % key, body)
        if not m:
            die("§4 %s から %s を読めない" % (half_title, key))
        return [g.strip() for g in m.group(1).split(",")]
    rows = grab(r"ROW0\.\.ROW5")
    cols = grab(r"COL0\.\.COL8")
    if len(rows) != 6 or len(cols) != 9:
        die("§4 %s のGPIO本数が 6/9 でない (%d/%d)" % (half_title, len(rows), len(cols)))
    return rows, cols


def read_encoder_spec():
    """§5.5 の表 -> [{'x':mm,'y':mm,'a':gp,'b':gp,'row':n,'col':n}, ...]"""
    body = section("## 5.5 ロータリーエンコーダ（左半体）")
    out = []
    for line in body.splitlines():
        m = re.match(r"\|\s*ENC(\d)\s*\|\s*X\s*=\s*(-|−)?([\d.]+),\s*Y\s*=\s*([\d.]+)\s*\|"
                     r"\s*A/B\s*→\s*(GP\d+)/(GP\d+)\s*\|\s*ROW(\d)\s*×\s*COL(\d)\s*\|", line)
        if m:
            out.append({"n": int(m.group(1)),
                        "x": -float(m.group(3)) if m.group(2) else float(m.group(3)),
                        "y": float(m.group(4)),
                        "a": m.group(5), "b": m.group(6),
                        "row": int(m.group(7)), "col": int(m.group(8))})
    if len(out) != 3:
        die("§5.5 から読めたエンコーダが %d 個（3でない）" % len(out))
    return out


def read_pad_spec():
    body = section("## 3. トラックパッド開口")
    m = re.search(r"X\s*=\s*\*\*([\d.]+)\*\*\s*mm,\s*Y\s*=\s*([\d.]+)\s*mm", body)
    if not m:
        die("§3 からパッド中心座標を読めない")
    return float(m.group(1)), float(m.group(2))


def read_keyarea_spec():
    body = section("## 1. 基本諸元")
    m = re.search(r"\|\s*キー領域\s*\|\s*([\d.]+)\s*×\s*([\d.]+)\s*mm\s*\|"
                  r"\s*([\d.]+)\s*×\s*([\d.]+)\s*mm\s*\|", body)
    if not m:
        die("§1 からキー領域寸法を読めない")
    return (float(m.group(1)), float(m.group(2))), (float(m.group(3)), float(m.group(4)))


# -------------------------------------------------------------------- 突合

def near(a, b, tol=0.02):
    return abs(a - b) <= tol


def build(side, html_rows, matrix, extra_keys):
    """物理(HTML) と 論理(pcb-spec §5) を左から順に対応付ける"""
    keys = []
    n = 0
    for ri, row in enumerate(html_rows):
        phys = sorted(row, key=lambda k: k[1])
        for lbl, x, w in extra_keys.get(ri, []):
            phys.append((lbl, x, w))          # 右ROW2の JIS Enter を末尾(COL8)へ
        logical = [(ci, c) for ci, c in enumerate(matrix[ri]) if c is not None]
        if len(phys) != len(logical):
            die("%s ROW%d: 配列図 %d キー vs マトリクス表 %d キー"
                % (side, ri, len(phys), len(logical)))
        for (lbl, x, w), (ci, name) in zip(phys, logical):
            n += 1
            keys.append({"ref": "SW%d" % n, "diode": "D%d" % n, "idx": n,
                         "row": ri, "col": ci, "name": name, "disp": lbl,
                         "x": x, "w": w, "h": 1.0})
    return keys


# --------------------------------------------------------------- 出力: KLE

def kle(keys, meta_notes, jis_enter=None):
    """KLE raw JSON。左上ラベル(index0) = "row,col"（VIA互換 / kbplacer 自動検出）"""
    doc = [{"name": meta_notes["name"], "notes": meta_notes["notes"]}]
    by_row = {}
    for k in keys:
        by_row.setdefault(k["row"], []).append(k)
    for ri in sorted(by_row):
        line, cx = [], 0.0
        for k in sorted(by_row[ri], key=lambda k: k["x"]):
            p = {}
            if not near(k["x"], cx, 1e-9):
                p["x"] = round(k["x"] - cx, 4)
            if jis_enter and k["ref"] == jis_enter["ref"]:
                # ISO/JIS Enter: 主矩形 1.25u×2u、副矩形 1.5u×1u を 0.25u 左へ
                p.update({"w": 1.25, "h": 2, "w2": 1.5, "h2": 1, "x2": -0.25})
                cx = k["x"] + 1.25
            else:
                if not near(k["w"], 1.0, 1e-9):
                    p["w"] = k["w"]
                cx = k["x"] + k["w"]
            if p:
                line.append(p)
            line.append("%d,%d" % (k["row"], k["col"]))
        doc.append(line)
    return doc


def write_kle(path, doc):
    """1行1要素のコンパクト形式（KLE の Raw data にそのまま貼れる並び）"""
    j = lambda o: json.dumps(o, ensure_ascii=False, separators=(",", ":"))
    with open(path, "w", encoding="utf-8") as f:
        f.write("[\n")
        f.write(",\n".join("  " + j(row) for row in doc))
        f.write("\n]\n")


# --------------------------------------------------------------- 出力: CSV

CSV_COLS = ["ref", "row", "col", "row_gpio", "col_gpio", "name", "label_html",
            "x_mm", "y_mm", "w_u", "h_u", "rot_deg",
            "diode_ref", "diode_x_mm", "diode_y_mm", "diode_rot_deg", "stabilizer"]


def capsize(k):
    """キーキャップのサイズ表記"""
    return "JIS Enter(v2u)" if k["h"] == 2.0 else ("%gu" % k["w"])


def write_keycap_csv(path, left, right):
    """キーキャップのサイズ別数量（U5 キーキャップ方針の判断材料）"""
    import collections
    tot = collections.Counter()
    per = {"L": collections.Counter(), "R": collections.Counter()}
    inner = collections.Counter()
    for side, keys in (("L", left), ("R", right)):
        for k in keys:
            sz = capsize(k)
            tot[sz] += 1
            per[side][sz] += 1
            if (side, k["row"], k["col"]) in INNER:
                inner[sz] += 1
    order = sorted(tot, key=lambda s: (s.startswith("JIS"), float(s[:-1]) if s.endswith("u") and not s.startswith("JIS") else 0))
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["size", "left", "right", "total", "inner_column", "outside_inner"])
        for sz in order:
            w.writerow([sz, per["L"][sz], per["R"][sz], tot[sz], inner[sz],
                        tot[sz] - inner[sz]])
        w.writerow(["合計", len(left), len(right), len(left) + len(right),
                    sum(inner.values()), len(left) + len(right) - sum(inner.values())])
    return tot, inner


def write_matrix_csv(path, side, keys, rows_gpio, cols_gpio):
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(CSV_COLS)
        for k in keys:
            x = round(k["cx"] * U, 3)
            y = round(k["cy"] * U, 3)
            w.writerow([k["ref"], k["row"], k["col"],
                        rows_gpio[k["row"]], cols_gpio[k["col"]],
                        k["name"], k["disp"], x, y, k["w"], k["h"], 0,
                        k["diode"], x, round(y + DIODE_DY, 3), DIODE_ROT,
                        STABS.get((side, k["row"], k["col"]), "")])


# ---------------------------------------------------------------- 出力: py

PLACE_TMPL = '''#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
{title}

kbplacer が使えない場合の pcbnew 直接配置スクリプト（pcb-spec.md §8 手順2）。
KiCad の「ツール > スクリプトコンソール」で:

    exec(open("/path/to/{fname}").read())

座標は pcb-spec.md rev 1.2 準拠。原点はキー領域の左上（u座標 0,0）、Y は下方向が正。
ORIGIN_X_MM / ORIGIN_Y_MM で、その原点を基板シート上のどこへ置くかを決める。

生成元: tools/gen-layout.py（split-jis75-tb.html + pcb-spec.md から生成。手で編集しない）
"""

import pcbnew

ORIGIN_X_MM = 100.0          # 仕様原点(0,0) をシート上のどこへ置くか
ORIGIN_Y_MM = 100.0
FLIP_DIODES_TO_BACK = False  # True にすると D* を裏面へ回す（pcb-spec §6: ダイオードは裏面実装）
                             # 既に裏面配置済みのフットプリントを使っているなら False のままでよい

# (ref, x_mm, y_mm, rot_deg)
SWITCHES = [
{switches}
]

# ダイオードは pcb-spec §6 に従い「スイッチ中心から下方 5.1mm・90度回転」。
# カソード向き(COL2ROW)が逆に出る場合は rot を -90 と読み替えること。
DIODES = [
{diodes}
]

{extra}

def _pt(x_mm, y_mm):
    nm = (pcbnew.FromMM(x_mm + ORIGIN_X_MM), pcbnew.FromMM(y_mm + ORIGIN_Y_MM))
    try:
        return pcbnew.VECTOR2I(*nm)      # KiCad 7/8/9
    except AttributeError:
        return pcbnew.wxPoint(*nm)       # KiCad 5/6


def place(board, table, flip=False):
    missing = []
    for ref, x, y, rot in table:
        fp = board.FindFootprintByReference(ref)
        if fp is None:
            missing.append(ref)
            continue
        fp.SetPosition(_pt(x, y))
        fp.SetOrientationDegrees(rot)
        if flip and fp.GetLayer() != pcbnew.B_Cu:
            try:
                fp.Flip(fp.GetPosition(), False)
            except TypeError:                    # KiCad 9 は引数の型が異なる
                print("  !! %s の裏面反転に失敗。手動で反転してください" % ref)
    return missing


def main():
    board = pcbnew.GetBoard()
    missing = place(board, SWITCHES)
    missing += place(board, DIODES, FLIP_DIODES_TO_BACK)
{extra_call}
    pcbnew.Refresh()
    print("{title}")
    print("  配置: SW %d / D %d{extra_count_fmt}" % (len(SWITCHES), len(DIODES){extra_count_arg}))
    if missing:
        print("  !! 見つからないフットプリント: " + ", ".join(missing))
    else:
        print("  すべて配置しました")


main()
'''


def fmt_rows(rows):
    return "\n".join('    ("%s", %.3f, %.3f, %.1f),' % r for r in rows)


# -------------------------------------------------------------------- main

def main():
    html = read_html_arrays()
    enc_geom = read_encoder_geometry()
    enc_spec = read_encoder_spec()
    je = read_jis_enter()

    # --- 右半体の JIS Enter を物理キーとして注入（HTML では jisEnter() で別描画）
    #     スイッチ中心は縦2uの軸（下段1.25uの中心線）上、行 y_top..y_bot の中央
    enter_cx = (je["x_bot"] + je["x_right"]) / 2.0
    enter_cy = (je["y_top"] + je["y_bot"]) / 2.0
    extra_right = {2: [("Enter", je["x_bot"], je["x_right"] - je["x_bot"])]}

    left = build("L", html["LEFT"], read_matrix("### 左半体（6×9）"), {})
    right = build("R", html["RIGHT"], read_matrix("### 右半体（6×9）"), extra_right)

    # --- 中心座標を確定
    enter_ref = None
    for k in left:
        k["cx"], k["cy"] = k["x"] + k["w"] / 2.0, k["row"] + 0.5
    for k in right:
        if k["name"] == "Enter" and k["row"] == 2 and k["col"] == 8:
            k["cx"], k["cy"], k["h"] = enter_cx, enter_cy, 2.0
            enter_ref = k["ref"]
        else:
            k["cx"], k["cy"] = k["x"] + k["w"] / 2.0, k["row"] + 0.5

    # --- 突合1: キー数
    if len(left) != 43:
        die("左半体のキー数が %d（43でない）" % len(left))
    if len(right) != 52:
        die("右半体のキー数が %d（52でない）" % len(right))

    # --- 突合2: パッド開口中心（HTML circlePad vs pcb-spec §3）
    pcx, pcy = read_pad_geometry()
    scx, scy = read_pad_spec()
    if not (near(pcx * U, scx) and near(pcy * U, scy)):
        die("パッド中心が不一致: HTML (%.2f, %.2f) vs §3 (%.2f, %.2f)"
            % (pcx * U, pcy * U, scx, scy))

    # --- 突合3: エンコーダ中心（HTML encoders() vs pcb-spec §5.5）
    for (gx, gy), e in zip(enc_geom, enc_spec):
        if not (near(gx * U, e["x"], 0.02) and near(gy * U, e["y"], 0.02)):
            die("ENC%d の中心が不一致: HTML (%.3f, %.3f) vs §5.5 (%.2f, %.2f)"
                % (e["n"], gx * U, gy * U, e["x"], e["y"]))

    # --- 突合4: キー領域寸法（HTML 配列の外接 vs pcb-spec §1）
    (lw, lh), (rw, rh) = read_keyarea_spec()
    l_x0 = min([k["x"] for k in left] + [g[0] - 0.65 for g in enc_geom])   # エンコーダ列を含む
    l_x1 = max(k["x"] + k["w"] for k in left)
    r_x0 = min(k["x"] for k in right)
    r_x1 = max(k["x"] + k["w"] for k in right)
    for got, want, what in (((l_x1 - l_x0) * U, lw, "左キー領域 幅"),
                            (6 * U, lh, "左キー領域 高さ"),
                            ((r_x1 - r_x0) * U, rw, "右キー領域 幅"),
                            ((pcy + 1.025) * U, rh, "右キー領域 高さ")):
        if not near(got, want, 0.06):
            die("%s が不一致: 算出 %.2fmm vs §1 %.2fmm" % (what, got, want))

    # --- 突合5: マトリクスに現れる ENC 押込の行列位置が §5.5 と一致するか
    body = section("### 左半体（6×9）")
    for e in enc_spec:
        pat = r"\|\*\*ROW%d\*\*\|(?:[^|]*\|){%d}\*\*ENC%d 押込\*\*\|" % (e["row"], e["col"], e["n"])
        if not re.search(pat, body):
            die("§5 の表で ENC%d 押込が ROW%d×COL%d にない" % (e["n"], e["row"], e["col"]))

    lr_gpio, lc_gpio = read_pins("### 左半体（Raspberry Pi Pico / スレーブ）")
    rr_gpio, rc_gpio = read_pins("### 右半体（RP2040-Plus / マスタ）")

    notes = ("生成物。手で編集しない。生成元は tools/gen-layout.py "
             "（入力: split-jis75-tb.html の配列 + pcb-spec.md rev 1.2 §4/§5/§5.5）。"
             "左上ラベルは row,col（VIA互換 / kbplacer が自動検出）。"
             "1u=19.05mm・原点はキー領域左上・Y下向き正。"
             "ロータリーエンコーダは含まない（encoders-left.csv 参照）。")

    out = lambda n: os.path.join(ROOT, n)

    write_kle(out("kle-left.json"),
              kle(left, {"name": "uskn75-kb left (rev 1.2)", "notes": notes}))
    write_kle(out("kle-right.json"),
              kle(right, {"name": "uskn75-kb right (rev 1.2)", "notes": notes},
                  jis_enter={"ref": enter_ref}))

    write_matrix_csv(out("matrix-left.csv"), "L", left, lr_gpio, lc_gpio)
    write_matrix_csv(out("matrix-right.csv"), "R", right, rr_gpio, rc_gpio)

    # --- 突合6: INNER / STABS が実在するキーを指しているか
    have = {("L", k["row"], k["col"]) for k in left} | {("R", k["row"], k["col"]) for k in right}
    for label, table in (("INNER", INNER), ("STABS", set(STABS))):
        missing = table - have
        if missing:
            die("%s に実在しないキー: %s" % (label, sorted(missing)))
    cap_tot, cap_inner = write_keycap_csv(out("keycap-sizes.csv"), left, right)

    # --- encoders-left.csv
    enc_rows, enc_d_rows = [], []
    with open(out("encoders-left.csv"), "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["ref", "x_mm", "y_mm", "rot_deg", "enc_a_gpio", "enc_b_gpio",
                    "push_row", "push_col", "push_row_gpio", "push_col_gpio",
                    "diode_ref", "diode_x_mm", "diode_y_mm", "diode_rot_deg", "note"])
        for (gx, gy), e in zip(enc_geom, enc_spec):
            x, y = round(gx * U, 3), round(gy * U, 3)
            dref = "D%d" % (len(left) + e["n"])
            w.writerow(["ENC%d" % e["n"], x, y, 0, e["a"], e["b"],
                        e["row"], e["col"], lr_gpio[e["row"]], lc_gpio[e["col"]],
                        dref, x, round(y + DIODE_DY, 3), DIODE_ROT,
                        "EC11互換 縦型プッシュ付き。回転はGPIO直結でマトリクス非参加、"
                        "押込のみ COL8 へ"])
            enc_rows.append(("ENC%d" % e["n"], x, y, 0.0))
            enc_d_rows.append((dref, x, round(y + DIODE_DY, 3), DIODE_ROT))

    # --- place-*.py
    def sw_rows(keys):
        return [(k["ref"], round(k["cx"] * U, 3), round(k["cy"] * U, 3), 0.0) for k in keys]

    def d_rows(keys):
        return [(k["diode"], round(k["cx"] * U, 3), round(k["cy"] * U + DIODE_DY, 3), DIODE_ROT)
                for k in keys]

    encoders_block = ("# (ref, x_mm, y_mm, rot_deg)  EC11本体（回転はGPIO直結・押込のみ COL8）\n"
                      "ENCODERS = [\n%s\n]\n\n"
                      "# エンコーダ押込スイッチ用のダイオード（DIODES と同じ扱い）\n"
                      "ENCODER_DIODES = [\n%s\n]\n"
                      % (fmt_rows(enc_rows), fmt_rows(enc_d_rows)))

    with open(out("place-left.py"), "w", encoding="utf-8") as f:
        f.write(PLACE_TMPL.format(
            title="uskn75-kb 左半体 フットプリント配置 (pcb-spec rev 1.2)",
            fname="place-left.py",
            switches=fmt_rows(sw_rows(left)),
            diodes=fmt_rows(d_rows(left)),
            extra=encoders_block,
            extra_call="    missing += place(board, ENCODERS)\n"
                       "    missing += place(board, ENCODER_DIODES, FLIP_DIODES_TO_BACK)",
            extra_count_fmt=" / ENC %d / ENC用D %d",
            extra_count_arg=", len(ENCODERS), len(ENCODER_DIODES)"))

    with open(out("place-right.py"), "w", encoding="utf-8") as f:
        f.write(PLACE_TMPL.format(
            title="uskn75-kb 右半体 フットプリント配置 (pcb-spec rev 1.2)",
            fname="place-right.py",
            switches=fmt_rows(sw_rows(right)),
            diodes=fmt_rows(d_rows(right)),
            extra="", extra_call="", extra_count_fmt="", extra_count_arg=""))

    print("OK 突合完了")
    print("  キー数            : 左 %d / 右 %d / 計 %d" % (len(left), len(right), len(left) + len(right)))
    print("  パッド開口中心    : (%.2f, %.2f) mm  = §3" % (pcx * U, pcy * U))
    print("  エンコーダ中心    : " + " / ".join("(%.3f, %.2f)" % (g[0] * U, g[1] * U) for g in enc_geom))
    print("  キー領域          : 左 %.2f×%.2f / 右 %.2f×%.2f mm  = §1"
          % ((l_x1 - l_x0) * U, 6 * U, (r_x1 - r_x0) * U, (pcy + 1.025) * U))
    print("  JIS Enter         : %s 中心 (%.3f, %.3f) mm / 縦2u" % (enter_ref, enter_cx * U, enter_cy * U))
    print("  ダイオード        : D1..D%d（左は D%d..D%d がエンコーダ押込）"
          % (len(right), len(left) + 1, len(left) + 3))
    print("  キーキャップ      : " + " / ".join("%s×%d" % (s, n) for s, n in sorted(cap_tot.items())))
    print("                      うち内側増設列（刻印が重複し汎用/無刻印で埋める分）%d 個" % sum(cap_inner.values()))
    print("  出力: keycap-sizes.csv / kle-{left,right}.json / matrix-{left,right}.csv / encoders-left.csv / place-{left,right}.py")


main()
