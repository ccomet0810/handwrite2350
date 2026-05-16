#!/usr/bin/env python3
"""CLI for the Rule-based Jamo Slot Mask Generator."""

from __future__ import annotations

import argparse
from pathlib import Path

from rule_jamo_mask import generate_for_directory


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Generate draft RGB jamo-slot masks from Hangul glyph images using "
            "thresholding, connected components, and layout heuristics."
        )
    )
    parser.add_argument("--input_dir", required=True, type=Path)
    parser.add_argument("--out_dir", required=True, type=Path)
    parser.add_argument("--threshold", type=int, default=180)
    parser.add_argument("--min_area", type=int, default=8)
    parser.add_argument("--save_components", action="store_true")
    parser.add_argument("--save_overlay", action="store_true")
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Ignore ambiguous components instead of assigning a low-confidence slot.",
    )
    parser.add_argument(
        "--allow_template_suffix",
        action="store_true",
        help="Treat filenames like UAC00_original.png as UAC00.",
    )
    parser.add_argument("--recursive", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if not args.input_dir.exists() or not args.input_dir.is_dir():
        raise SystemExit(f"input_dir does not exist or is not a directory: {args.input_dir}")
    if not 0 <= args.threshold <= 255:
        raise SystemExit("--threshold must be in the range 0..255")
    if args.min_area < 1:
        raise SystemExit("--min_area must be >= 1")

    results = generate_for_directory(
        input_dir=args.input_dir,
        out_dir=args.out_dir,
        threshold=args.threshold,
        min_area=args.min_area,
        save_components=args.save_components,
        save_overlay_preview=args.save_overlay,
        strict=args.strict,
        allow_template_suffix=args.allow_template_suffix,
        recursive=args.recursive,
    )
    warnings = sum(1 for result in results if result.warnings)
    print(
        "Rule-based Jamo Slot Mask Generator complete: "
        f"{len(results)} masks, {warnings} warning(s). "
        f"Summary: {args.out_dir / 'summary.tsv'}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
