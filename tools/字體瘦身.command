#!/bin/zsh
# Double-click in Finder: opens Terminal and asks for font files (drag them into the window).
# Creates tools/.venv on first run with the Python version in .python-version.
cd "$(dirname "$0")" || exit 1

if [[ ! -x .venv/bin/python ]]; then
  PY="python$(cut -d. -f1,2 .python-version)"
  if ! command -v "$PY" >/dev/null; then
    echo "找不到 $PY（版本寫在 tools/.python-version），請先安裝。"
    read -r "?按 Enter 關閉…"
    exit 1
  fi
  echo "第一次使用，正在準備環境…"
  "$PY" -m venv .venv && .venv/bin/pip -q --disable-pip-version-check install -r requirements.txt || {
    echo "環境準備失敗。"; read -r "?按 Enter 關閉…"; exit 1; }
fi

.venv/bin/python reduce_font.py
echo
read -r "?完成，按 Enter 關閉…"
