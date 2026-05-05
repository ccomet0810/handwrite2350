import json
import subprocess
from pathlib import Path


CHARSET_PATH = Path("charsets/basiclatin_ksx1001.txt")
SVG_DIR = Path("/app/outputs/svg")
FONTS_DIR = Path("/app/outputs/fonts")
REPORT_PATH = Path("/app/outputs/font_build_report.txt")
FONT_INFO_BUILD_PATH = Path("/app/outputs/font_info_build.json")
FONTFORGE_SCRIPT_PATH = Path("src/fontforge_build.py")


def list_svg_files(svg_dir=SVG_DIR):
    path = Path(svg_dir)
    if not path.exists():
        return []

    return sorted(path.rglob("*.svg"))


def count_svg_files(svg_dir=SVG_DIR):
    return len(list_svg_files(svg_dir))


def has_svg_files(svg_dir=SVG_DIR):
    return count_svg_files(svg_dir) > 0


def run_font_build(
    font_info,
    charset_path=CHARSET_PATH,
    svg_dir=SVG_DIR,
    font_quality="fast",
):
    svg_count = count_svg_files(svg_dir)
    print(f"SVG files found in {Path(svg_dir)}: {svg_count}\n", end="")

    if svg_count == 0:
        print("No SVG files found. Skipped TTF generation.\n", end="")
        return True

    FONTS_DIR.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    FONT_INFO_BUILD_PATH.write_text(
        json.dumps(font_info, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    command = [
        "fontforge",
        "-lang=py",
        "-script",
        str(FONTFORGE_SCRIPT_PATH),
        "--charset",
        str(charset_path),
        "--svg-dir",
        str(svg_dir),
        "--fonts-dir",
        str(FONTS_DIR),
        "--font-info",
        str(FONT_INFO_BUILD_PATH),
        "--report",
        str(REPORT_PATH),
        "--quality",
        font_quality,
    ]

    try:
        result = subprocess.run(
            command,
            check=True,
            capture_output=True,
            text=True,
        )
    except subprocess.CalledProcessError as exc:
        details = (exc.stderr or exc.stdout or str(exc)).strip()
        REPORT_PATH.write_text(
            "handwrite2350 font build report\n"
            "========================================\n"
            f"FontForge command failed: {details}\n",
            encoding="utf-8",
        )
        print(REPORT_PATH.read_text(encoding="utf-8"), end="")
        return False

    if result.stdout:
        print(result.stdout, end="")
    if result.stderr:
        print(result.stderr, end="")

    if REPORT_PATH.exists():
        print(REPORT_PATH.read_text(encoding="utf-8"), end="")

    return True
