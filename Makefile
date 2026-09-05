# 検証の入口。ハーネスの Stop hook と verify スキルがこの target を呼ぶ。
# この repo にビルドとテストは無い。決定的な検査は gen-layout.py の突合だけ。
SHELL := /usr/bin/env bash

.PHONY: verify verify-layout

verify: verify-layout ## この repo に当てはまる検査をすべて実行する
	@echo "verify: ok"

# tools/gen-layout.py は split-jis75-tb.html と pcb-spec.md を突き合わせ、
# 1 つでも食い違えば出力せずにエラー終了する。生成物に差分が出た場合も失敗とする。
verify-layout:
	@if command -v python3 >/dev/null; then \
	  echo "[layout] python3 tools/gen-layout.py"; \
	  python3 tools/gen-layout.py > /dev/null || exit 1; \
	  if [ -n "$$(git status --porcelain -- kle-left.json kle-right.json matrix-left.csv matrix-right.csv encoders-left.csv keycap-sizes.csv place-left.py place-right.py)" ]; then \
	    echo "[layout] 生成物がコミット済みの内容と一致しない。gen-layout.py の出力を確認してコミットすること"; \
	    git status --porcelain -- kle-left.json kle-right.json matrix-left.csv matrix-right.csv encoders-left.csv keycap-sizes.csv place-left.py place-right.py; \
	    exit 1; \
	  fi; \
	else echo "[layout] skipped (python3 が無い)"; fi
