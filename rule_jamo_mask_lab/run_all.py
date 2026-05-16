#!/usr/bin/env python3
"""One-command runner for the rule-based jamo slot mask experiment."""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path


LAB_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = LAB_DIR.parent
if str(LAB_DIR) not in sys.path:
    sys.path.insert(0, str(LAB_DIR))

from create_manual_templates import (
    HANGUL_END,
    HANGUL_START,
    IMAGE_SUFFIXES,
    codepoint_from_path,
)
from rule_jamo_mask import generate_for_directory_ordered


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build manual template inputs and draft RGB jamo masks in one command."
    )
    parser.add_argument("--font_stem", required=True)
    parser.add_argument("--work_dir", type=Path, default=Path("rule_jamo_mask_lab/work"))
    parser.add_argument("--normalized_dir", type=Path, default=Path("outputs/normalized"))
    parser.add_argument("--samples_dir", type=Path, default=Path("samples"))
    parser.add_argument("--outputs_dir", type=Path, default=Path("outputs"))
    parser.add_argument("--docker_image", default="handwrite2350")
    parser.add_argument("--workers", type=int, default=8)
    parser.add_argument("--threshold", type=int, default=180)
    parser.add_argument("--min_area", type=int, default=8)
    parser.add_argument("--strict", action="store_true")
    parser.add_argument(
        "--clean",
        action="store_true",
        help="Delete the current rule_jamo_mask_lab/work/<font_stem> run folder first.",
    )
    parser.add_argument(
        "--no_auto_normalized",
        action="store_true",
        help="Fail if normalized glyphs are missing instead of running Docker first.",
    )
    parser.add_argument(
        "--skip_docker_build",
        action="store_true",
        help="Use an existing Docker image when normalized glyphs must be generated.",
    )
    return parser.parse_args()


def has_normalized_glyphs(path: Path) -> bool:
    return path.exists() and any(path.glob("uni*.png"))


def run_command(command: list[str]) -> None:
    print("+ " + " ".join(command), flush=True)
    subprocess.run(command, cwd=PROJECT_ROOT, check=True)


def ensure_normalized(args: argparse.Namespace) -> None:
    if has_normalized_glyphs(args.normalized_dir):
        print(f"[ok] normalized glyphs found: {args.normalized_dir}")
        return

    if args.no_auto_normalized:
        raise SystemExit(
            f"normalized glyphs not found: {args.normalized_dir}\n"
            "먼저 폰트 파이프라인을 --save-normalized로 실행하거나, "
            "--no_auto_normalized 없이 다시 실행하세요."
        )

    print("[info] normalized glyphs not found; running Docker font pipeline first.")
    if not args.skip_docker_build:
        run_command(["docker", "build", "-t", args.docker_image, "."])

    run_command(
        [
            "docker",
            "run",
            "--rm",
            "-v",
            f"{(PROJECT_ROOT / args.samples_dir).resolve()}:/app/samples",
            "-v",
            f"{(PROJECT_ROOT / args.outputs_dir).resolve()}:/app/outputs",
            args.docker_image,
            "--save-normalized",
            "--workers",
            str(args.workers),
            "--family-name",
            args.font_stem,
        ]
    )

    if not has_normalized_glyphs(args.normalized_dir):
        raise SystemExit(f"Docker finished, but normalized glyphs are still missing: {args.normalized_dir}")


def copy_normalized_glyphs(source_dir: Path, target_dir: Path) -> tuple[int, int]:
    target_dir.mkdir(parents=True, exist_ok=True)
    copied = 0
    skipped = 0
    for source in sorted(source_dir.iterdir()):
        if not source.is_file() or source.suffix.lower() not in IMAGE_SUFFIXES:
            continue
        codepoint = codepoint_from_path(source)
        if codepoint is None or not HANGUL_START <= codepoint <= HANGUL_END:
            skipped += 1
            continue
        destination = target_dir / f"uni{codepoint:04X}.png"
        shutil.copy2(source, destination)
        copied += 1
    return copied, skipped


def main() -> int:
    args = parse_args()
    if args.threshold < 0 or args.threshold > 255:
        raise SystemExit("--threshold must be in the range 0..255")
    if args.min_area < 1:
        raise SystemExit("--min_area must be >= 1")

    ensure_normalized(args)

    run_dir = args.work_dir / args.font_stem
    if args.clean and run_dir.exists():
        shutil.rmtree(run_dir)

    input_dir = run_dir / "00_input_glyphs"
    mask_dir = run_dir / "01_rgb_masks"
    overlay_dir = run_dir / "02_overlay_previews"
    metadata_dir = run_dir / "03_metadata"
    components_dir = run_dir / "04_extracted_components"
    report_dir = run_dir / "05_reports"

    normalized_copied, normalized_skipped = copy_normalized_glyphs(
        args.normalized_dir, input_dir
    )

    results = generate_for_directory_ordered(
        input_dir=input_dir,
        mask_dir=mask_dir,
        metadata_dir=metadata_dir,
        report_dir=report_dir,
        overlay_dir=overlay_dir,
        components_root=components_dir,
        threshold=args.threshold,
        min_area=args.min_area,
        strict=args.strict,
        allow_template_suffix=False,
    )

    warnings = sum(1 for result in results if result.warnings)
    print()
    print("[done] Rule-based Jamo Slot Mask Lab complete")
    print(f"  run: {run_dir}")
    print(f"  00 input glyphs: {input_dir} ({normalized_copied} copied, {normalized_skipped} skipped)")
    print(f"  01 RGB masks: {mask_dir} ({len(results)} masks)")
    print(f"  02 overlays: {overlay_dir}")
    print(f"  03 metadata: {metadata_dir}")
    print(f"  04 components: {components_dir}")
    print(f"  05 reports: {report_dir}")
    print(f"  warnings: {warnings}")
    print(f"  summary: {report_dir / 'summary.tsv'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
