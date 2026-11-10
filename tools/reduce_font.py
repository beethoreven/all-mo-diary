"""Shrink a font file for the 全心日記 font list before uploading it.

Usage:
    Double-click 字體瘦身.command in Finder, then drag font files into the Terminal window.
    Or from the tools/ folder: .venv/bin/python reduce_font.py <font files...> [--out ../reduced_fonts]

For each input this writes three files to the output folder:
  <name>.otf      the shrunk font, which is what the phone installs and loads
  <name>.otf.gz   the same file gzip-compressed, which is what gets uploaded and downloaded
  <name>.json     size, SHA-256 and glyph-count details that the admin page needs

Why it shrinks (measured 2026-11-10 on the user's fonts):
  The "_fixed" OTF files keep fractional coordinates (e.g. 811.3333) and are
  barely subroutinized, so each glyph stores its full outline. Re-subroutinizing
  with AFDKO tx (via cffsubr) shares repeated outline pieces and stores
  coordinates to 0.01 units. Files shrink by about 50% (TW-Kai: 112 → 56 MB),
  and the largest outline change is around 0.004 units on a 1000-unit em, which
  is far below one pixel on any phone. gzip saves roughly another 30% on download.

TrueType (.ttf) fonts have no CFF table to re-subroutinize, so they are only
gzip-compressed.

Large fonts are slow: TW-Kai takes about 15 minutes on an Intel Mac.
"""

from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import random
import shlex
import shutil
import subprocess
import sys
import time
from pathlib import Path

import cffsubr
from fontTools.pens.areaPen import AreaPen
from fontTools.ttLib import TTFont

# After shrinking, a glyph's area may differ from the original by at most this
# fraction of em² (1000×1000 units → 10 unit²). Measured worst case: 2.4 unit².
MAX_AREA_DIFF_EM2 = 1e-5
SAMPLE_GLYPHS = 1500


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def check_same(original: Path, reduced: Path) -> float:
    """Return the largest glyph-area difference over a random glyph sample. Exits on a char-map mismatch."""
    a, b = TTFont(original, lazy=True), TTFont(reduced, lazy=True)
    if a.getBestCmap() != b.getBestCmap():
        sys.exit(f"{reduced.name}: character map changed while shrinking. Not using this output.")
    ga, gb = a.getGlyphSet(), b.getGlyphSet()
    names = a.getGlyphOrder()
    random.seed(0)
    worst = 0.0
    for name in random.sample(names, min(SAMPLE_GLYPHS, len(names))):
        pa, pb = AreaPen(ga), AreaPen(gb)
        ga[name].draw(pa)
        gb[name].draw(pb)
        if ga[name].width != gb[name].width:
            sys.exit(f"{reduced.name}: glyph {name} changed width while shrinking.")
        worst = max(worst, abs(pa.value - pb.value))
    upem = a["head"].unitsPerEm
    if worst > MAX_AREA_DIFF_EM2 * upem * upem:
        sys.exit(f"{reduced.name}: glyph outlines changed more than expected (area diff {worst:.1f}).")
    return worst


def reduce_one(src: Path, out_dir: Path, name: str) -> dict:
    started = time.monotonic()
    font = TTFont(src)
    if "glyf" in font or "CFF " not in font:
        kind = "TrueType" if "glyf" in font else "other"
        dst = out_dir / f"{name}{src.suffix.lower()}"
        shutil.copyfile(src, dst)
    else:
        kind = "CFF"
        cffsubr.subroutinize(font)
        dst = out_dir / f"{name}.otf"
        font.save(dst)
    font.close()

    worst = check_same(src, dst) if kind == "CFF" else 0.0

    gz = dst.with_name(dst.name + ".gz")
    with dst.open("rb") as fin, gzip.open(gz, "wb", compresslevel=9) as fout:
        shutil.copyfileobj(fin, fout, 1 << 20)

    info_font = TTFont(dst, lazy=True)
    info = {
        "source": src.name,
        "family": info_font["name"].getDebugName(1),
        "full_name": info_font["name"].getDebugName(4),
        "license": (info_font["name"].getDebugName(13) or "").strip(),
        "outline": kind,
        "glyphs": info_font["maxp"].numGlyphs,
        "characters": len(info_font.getBestCmap() or {}),
        "original_bytes": src.stat().st_size,
        "font_file": dst.name,
        "font_bytes": dst.stat().st_size,
        "font_sha256": sha256(dst),
        "download_file": gz.name,
        "download_bytes": gz.stat().st_size,
        "download_sha256": sha256(gz),
        "max_area_diff": round(worst, 3),
        "seconds": round(time.monotonic() - started),
    }
    (out_dir / f"{name}.json").write_text(json.dumps(info, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return info


def parse_dropped(line: str) -> list[Path]:
    """Turn what Terminal pastes when files are dragged in (backslash-escaped or quoted, space-separated) into paths."""
    try:
        parts = shlex.split(line)
    except ValueError:
        parts = [line.strip()]
    return [Path(p).expanduser() for p in parts if p.strip()]


def run(fonts: list[Path], out: Path) -> bool:
    """Shrink each font. Returns False when one was skipped or failed."""
    out.mkdir(parents=True, exist_ok=True)
    ok = True
    mb = 1024 * 1024
    for src in fonts:
        if not src.is_file():
            print(f"✗ 找不到檔案：{src}")
            ok = False
            continue
        if src.suffix.lower() not in (".otf", ".ttf"):
            print(f"✗ {src.name}：只支援 .otf 和 .ttf（.ttc 這種字型集合不支援）")
            ok = False
            continue
        print(f"… {src.name} 處理中（大檔要好幾分鐘，請不要關掉視窗）")
        try:
            info = reduce_one(src, out, src.stem)
        except SystemExit as e:  # check_same() refuses a bad output with sys.exit(message)
            print(f"✗ {e}")
            ok = False
            continue
        print(f"✓ {src.name}：{info['original_bytes'] / mb:.1f} MB → 手機上 {info['font_bytes'] / mb:.1f} MB，"
              f"下載 {info['download_bytes'] / mb:.1f} MB（{info['seconds']} 秒）")
    return ok


def interactive(out: Path) -> None:
    print("字體瘦身工具")
    print(f"輸出位置：{out}\n")
    while True:
        line = input("把字體檔拖進這個視窗（可以一次拖好幾個），再按 Enter；直接按 Enter 結束：\n> ")
        fonts = parse_dropped(line)
        if not fonts:
            break
        run(fonts, out)
        print()
    if sys.platform == "darwin" and out.exists():
        subprocess.run(["open", str(out)], check=False)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("fonts", nargs="*", type=Path, help="font files; leave empty to be asked interactively")
    parser.add_argument("--out", type=Path, default=Path(__file__).resolve().parent.parent / "reduced_fonts")
    args = parser.parse_args()
    if not args.fonts:
        interactive(args.out)
    elif not run(args.fonts, args.out):
        sys.exit(1)


if __name__ == "__main__":
    main()
