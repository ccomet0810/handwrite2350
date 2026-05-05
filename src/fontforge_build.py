import argparse
import json
import os
import time

import fontforge
import psMat


SPACE_CODEPOINT = 0x0020


def parse_args():
    parser = argparse.ArgumentParser(description="Build handwrite2350 TTF with FontForge")
    parser.add_argument("--charset", required=True)
    parser.add_argument("--svg-dir", required=True)
    parser.add_argument("--fonts-dir", required=True)
    parser.add_argument("--font-info", required=True)
    parser.add_argument("--report", required=True)
    parser.add_argument("--quality", choices=["fast", "high"], default="fast")
    return parser.parse_args()


def load_charset(path):
    with open(path, "r", encoding="utf-8") as file:
        return file.read().replace("\r", "").replace("\n", "")


def load_font_info(path):
    with open(path, "r", encoding="utf-8") as file:
        return json.load(file)


def glyph_width(codepoint):
    if codepoint == SPACE_CODEPOINT:
        return 500
    if 0x0021 <= codepoint <= 0x007E:
        return 600
    return 1000


def is_basic_latin_punctuation(codepoint):
    char = chr(codepoint)
    return 0x0021 <= codepoint <= 0x007E and not char.isalnum()


def target_geometry(codepoint):
    width = glyph_width(codepoint)
    if 0x0021 <= codepoint <= 0x007E:
        return width, 430, 140
    return width, 820, 80


def svg_path_for_codepoint(svg_dir, codepoint):
    return os.path.join(svg_dir, "uni%04X.svg" % codepoint)


def append_sfnt_name(font, name_id, value):
    if not value:
        return
    try:
        font.appendSFNTName("English (US)", name_id, value)
    except Exception:
        pass


def apply_font_metadata(font, font_info):
    family_name = font_info.get("family_name", "Handwrite2350")
    style_name = font_info.get("style_name", "Regular")
    full_name = font_info.get("full_name", family_name + " " + style_name)
    postscript_name = font_info.get("postscript_name", "Handwrite2350-Regular")
    version = font_info.get("version", "Version 1.000")

    font.encoding = "UnicodeFull"
    font.em = 1000
    font.ascent = 880
    font.descent = 120
    font.familyname = family_name
    font.fullname = full_name
    font.fontname = postscript_name
    font.version = version
    font.copyright = font_info.get("copyright", "")

    append_sfnt_name(font, "Family", family_name)
    append_sfnt_name(font, "SubFamily", style_name)
    append_sfnt_name(font, "Fullname", full_name)
    append_sfnt_name(font, "PostScriptName", postscript_name)
    append_sfnt_name(font, "Version", version)
    append_sfnt_name(font, "Manufacturer", font_info.get("manufacturer", ""))
    append_sfnt_name(font, "Designer", font_info.get("designer", ""))
    append_sfnt_name(font, "Descriptor", font_info.get("description", ""))
    append_sfnt_name(font, "Copyright", font_info.get("copyright", ""))
    append_sfnt_name(font, "License", font_info.get("license", ""))


def create_space_glyph(font):
    glyph = font.createChar(SPACE_CODEPOINT)
    glyph.width = glyph_width(SPACE_CODEPOINT)
    return glyph


def import_glyph(font, codepoint, svg_path, quality):
    glyph = font.createChar(codepoint)
    glyph.width = glyph_width(codepoint)

    import_start = time.time()
    glyph.importOutlines(svg_path)
    import_time = time.time() - import_start

    cleanup_start = time.time()
    if quality == "high":
        glyph.correctDirection()
        glyph.removeOverlap()
        if not is_basic_latin_punctuation(codepoint):
            normalize_glyph_geometry(glyph, codepoint)
    else:
        fit_glyph_fast(glyph, codepoint)
    cleanup_time = time.time() - cleanup_start

    glyph.width = glyph_width(codepoint)
    return glyph, import_time, cleanup_time


def fit_glyph_fast(glyph, codepoint):
    if is_basic_latin_punctuation(codepoint):
        return

    try:
        xmin, ymin, xmax, ymax = glyph.boundingBox()
    except Exception:
        return

    glyph_box_width = xmax - xmin
    glyph_box_height = ymax - ymin
    if glyph_box_width <= 0 or glyph_box_height <= 0:
        return

    advance_width, target_height, bottom_margin = target_geometry(codepoint)
    target_width = advance_width * 0.82
    scale = min(target_width / glyph_box_width, target_height / glyph_box_height)

    glyph.transform(psMat.translate(-xmin, -ymin))
    if scale > 0 and abs(scale - 1.0) > 0.01:
        glyph.transform(psMat.scale(scale))

    try:
        xmin, ymin, xmax, ymax = glyph.boundingBox()
    except Exception:
        return

    glyph_box_width = xmax - xmin
    x_offset = (advance_width - glyph_box_width) / 2 - xmin
    y_offset = bottom_margin - ymin
    glyph.transform(psMat.translate(x_offset, y_offset))


def normalize_glyph_geometry(glyph, codepoint):
    try:
        xmin, ymin, xmax, ymax = glyph.boundingBox()
    except Exception:
        return

    glyph_box_width = xmax - xmin
    glyph_box_height = ymax - ymin
    if glyph_box_width <= 0 or glyph_box_height <= 0:
        return

    advance_width, target_height, bottom_margin = target_geometry(codepoint)
    target_width = advance_width * 0.82
    scale = min(target_width / glyph_box_width, target_height / glyph_box_height)

    glyph.transform(psMat.translate(-xmin, -ymin))
    glyph.transform(psMat.scale(scale))

    xmin, ymin, xmax, ymax = glyph.boundingBox()
    glyph_box_width = xmax - xmin
    x_offset = (advance_width - glyph_box_width) / 2 - xmin
    y_offset = bottom_margin - ymin
    glyph.transform(psMat.translate(x_offset, y_offset))


def write_report(path, lines):
    with open(path, "w", encoding="utf-8") as file:
        file.write("\n".join(lines) + "\n")


def main():
    args = parse_args()
    timings = {
        "create font time": 0.0,
        "metadata time": 0.0,
        "import SVG total time": 0.0,
        "glyph cleanup time": 0.0,
        "generate TTF time": 0.0,
    }

    chars = load_charset(args.charset)
    font_info = load_font_info(args.font_info)
    os.makedirs(args.fonts_dir, exist_ok=True)

    start = time.time()
    font = fontforge.font()
    timings["create font time"] += time.time() - start

    start = time.time()
    apply_font_metadata(font, font_info)
    timings["metadata time"] += time.time() - start

    create_space_glyph(font)

    imported_count = 0
    missing = []
    failed = []

    for index, char in enumerate(chars):
        codepoint = ord(char)
        svg_path = svg_path_for_codepoint(args.svg_dir, codepoint)

        if not os.path.exists(svg_path):
            missing.append("index=%d unicode=U+%04X file=%s" % (index, codepoint, svg_path))
            glyph = font.createChar(codepoint)
            glyph.width = glyph_width(codepoint)
            continue

        try:
            _, import_time, cleanup_time = import_glyph(
                font,
                codepoint,
                svg_path,
                args.quality,
            )
            timings["import SVG total time"] += import_time
            timings["glyph cleanup time"] += cleanup_time
            imported_count += 1
        except Exception as exc:
            failed.append(
                "index=%d unicode=U+%04X file=%s error=%s: %s"
                % (index, codepoint, svg_path, type(exc).__name__, exc)
            )
            glyph = font.createChar(codepoint)
            glyph.width = glyph_width(codepoint)

    output_path = os.path.join(
        args.fonts_dir,
        "%s.ttf" % font_info.get("postscript_name", "Handwrite2350-Regular"),
    )
    start = time.time()
    font.generate(output_path)
    timings["generate TTF time"] += time.time() - start
    font.close()

    problem_list = missing + failed
    lines = [
        "handwrite2350 font build report",
        "========================================",
        "total charset count: %d" % len(chars),
        "imported SVG count: %d" % imported_count,
        "missing SVG count: %d" % len(missing),
        "generated font path: %s" % output_path,
        "font quality: %s" % args.quality,
        "create font time: %.2fs" % timings["create font time"],
        "import SVG total time: %.2fs" % timings["import SVG total time"],
        "glyph cleanup time: %.2fs" % timings["glyph cleanup time"],
        "metadata time: %.2fs" % timings["metadata time"],
        "generate TTF time: %.2fs" % timings["generate TTF time"],
        "failed glyph count: %d" % len(problem_list),
        "",
        "failed glyph list:",
    ]
    lines.extend(problem_list if problem_list else ["None"])
    write_report(args.report, lines)


if __name__ == "__main__":
    main()
