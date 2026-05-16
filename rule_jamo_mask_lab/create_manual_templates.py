#!/usr/bin/env python3
"""Create manual template glyph folders from normalized pipeline outputs."""

from __future__ import annotations

import argparse
import re
import shutil
from pathlib import Path


UNICODE_RE = re.compile(r"(?:U\+?|uni)([A-Fa-f0-9]{4,6})", re.IGNORECASE)
IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".bmp", ".tif", ".tiff"}
HANGUL_START = 0xAC00
HANGUL_END = 0xD7A3


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Copy Hangul normalized glyph images into manual_templates/<font_stem> "
            "as UXXXX_original.png files."
        )
    )
    parser.add_argument("--input_dir", default="outputs/normalized", type=Path)
    parser.add_argument("--out_dir", default="manual_templates", type=Path)
    parser.add_argument("--font_stem", required=True)
    parser.add_argument(
        "--include_non_hangul",
        action="store_true",
        help="Also copy non-Hangul codepoints. The mask generator will skip/error them.",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Replace existing files in manual_templates/<font_stem>.",
    )
    return parser.parse_args()


def codepoint_from_path(path: Path) -> int | None:
    match = UNICODE_RE.search(path.stem)
    if not match:
        return None
    return int(match.group(1), 16)


def copy_hangul_templates(
    input_dir: Path,
    target_dir: Path,
    include_non_hangul: bool = False,
    overwrite: bool = False,
) -> tuple[int, int]:
    target_dir.mkdir(parents=True, exist_ok=True)

    copied = 0
    skipped = 0
    for source in sorted(input_dir.iterdir()):
        if not source.is_file() or source.suffix.lower() not in IMAGE_SUFFIXES:
            continue
        codepoint = codepoint_from_path(source)
        if codepoint is None:
            skipped += 1
            continue
        if not include_non_hangul and not HANGUL_START <= codepoint <= HANGUL_END:
            skipped += 1
            continue

        destination = target_dir / f"U{codepoint:04X}_original.png"
        if destination.exists() and not overwrite:
            skipped += 1
            continue
        shutil.copy2(source, destination)
        copied += 1

    return copied, skipped


def main() -> int:
    args = parse_args()
    if not args.input_dir.exists() or not args.input_dir.is_dir():
        raise SystemExit(
            f"input_dir does not exist: {args.input_dir}\n"
            "먼저 Docker 파이프라인을 --save-normalized 옵션으로 실행해서 "
            "outputs/normalized/uniXXXX.png 파일을 만들어 주세요."
        )

    target_dir = args.out_dir / args.font_stem
    copied, skipped = copy_hangul_templates(
        input_dir=args.input_dir,
        target_dir=target_dir,
        include_non_hangul=args.include_non_hangul,
        overwrite=args.overwrite,
    )

    print(
        f"manual_templates created: {target_dir} "
        f"({copied} copied, {skipped} skipped)"
    )
    if copied == 0:
        print("No files were copied. Check that input files are named like uniAC00.png.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
