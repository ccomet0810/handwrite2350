from concurrent.futures import ProcessPoolExecutor, as_completed
import argparse
import os
from pathlib import Path
import subprocess
import time

import cv2
import numpy as np


CELLS_DIR = Path("outputs/cells")
SVG_DIR = Path("/app/outputs/svg")
TMP_DIR = Path("/app/outputs/tmp")
NORMALIZED_DIR = Path("/app/outputs/normalized")
REPORT_PATH = Path("/app/outputs/trace_report.txt")
CHARSET_PATH = Path("charsets/basiclatin_ksx1001.txt")

DEFAULT_GLYPH_SIZE = 512
DEFAULT_GLYPH_PADDING = 48
CELL_EXTENSIONS = {".png"}


def parse_args():
    parser = argparse.ArgumentParser(description="Trace handwrite2350 cell PNGs to SVG")
    parser.add_argument("--cells-dir", default=str(CELLS_DIR))
    parser.add_argument("--charset", default=str(CHARSET_PATH))
    parser.add_argument("--workers", type=int)
    parser.add_argument("--glyph-size", type=int, default=DEFAULT_GLYPH_SIZE)
    parser.add_argument("--glyph-padding", type=int, default=DEFAULT_GLYPH_PADDING)
    parser.add_argument("--save-normalized", action="store_true")
    return parser.parse_args()


def default_worker_count():
    cpu_count = os.cpu_count() or 1
    return max(1, cpu_count - 1)


def load_charset(path=CHARSET_PATH):
    return Path(path).read_text(encoding="utf-8").replace("\r", "").replace("\n", "")


def list_cell_images(cells_dir=CELLS_DIR):
    cells_path = Path(cells_dir)
    if not cells_path.exists():
        return []

    image_paths = []
    for page_dir in sorted(path for path in cells_path.iterdir() if path.is_dir()):
        image_paths.extend(
            sorted(
                path
                for path in page_dir.iterdir()
                if path.is_file() and path.suffix.lower() in CELL_EXTENSIONS
            )
        )
    return image_paths


def unicode_svg_path(char, svg_dir=SVG_DIR):
    return Path(svg_dir) / f"uni{ord(char):04X}.svg"


def unicode_normalized_path(char, normalized_dir=NORMALIZED_DIR):
    return Path(normalized_dir) / f"uni{ord(char):04X}.png"


def list_svg_files(svg_dir=SVG_DIR):
    path = Path(svg_dir)
    if not path.exists():
        return []
    return sorted(path.rglob("*.svg"))


def is_basic_latin_punctuation(char):
    codepoint = ord(char)
    return 0x0021 <= codepoint <= 0x007E and not char.isalnum()


def decode_cell_image(task):
    if "gray_bytes" in task:
        height, width = task["gray_shape"]
        image = np.frombuffer(task["gray_bytes"], dtype=np.uint8).reshape(
            int(height),
            int(width),
        )
        source = f"{task.get('page', 'memory')} r{task.get('row', -1):02d}_c{task.get('col', -1):02d}"
    elif "binary_bytes" in task:
        height, width = task["binary_shape"]
        image = np.frombuffer(task["binary_bytes"], dtype=np.uint8).reshape(
            int(height),
            int(width),
        )
        source = f"{task.get('page', 'memory')} r{task.get('row', -1):02d}_c{task.get('col', -1):02d}"
    elif "binary_png" in task:
        data = np.frombuffer(task["binary_png"], dtype=np.uint8)
        image = cv2.imdecode(data, cv2.IMREAD_GRAYSCALE)
        source = f"{task.get('page', 'memory')} r{task.get('row', -1):02d}_c{task.get('col', -1):02d}"
    else:
        cell_path = Path(task["cell_path"])
        image = cv2.imread(str(cell_path), cv2.IMREAD_GRAYSCALE)
        source = str(cell_path)

    if image is None:
        raise ValueError(f"failed to read cell image: {source}")
    return image, source


def threshold_for_bbox(gray):
    _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY | cv2.THRESH_OTSU)
    black_pixels = np.count_nonzero(binary == 0)
    white_pixels = np.count_nonzero(binary == 255)
    if black_pixels > white_pixels:
        gray = cv2.bitwise_not(gray)
        binary = cv2.bitwise_not(binary)
    return gray, binary


def threshold_final(gray):
    if min(gray.shape[:2]) >= 3:
        gray = cv2.GaussianBlur(gray, (3, 3), 0.35)
    _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY | cv2.THRESH_OTSU)
    black_pixels = np.count_nonzero(binary == 0)
    white_pixels = np.count_nonzero(binary == 255)
    if black_pixels > white_pixels:
        binary = cv2.bitwise_not(binary)
    return binary


def normalize_cell_bitmap(image, char, glyph_size, glyph_padding, source):
    gray, binary_for_bbox = threshold_for_bbox(image)

    ys, xs = np.where(binary_for_bbox == 0)
    if len(xs) == 0 or len(ys) == 0:
        raise ValueError(f"empty glyph bitmap after threshold: {source}")

    if is_basic_latin_punctuation(char):
        crop = gray
    else:
        x0, x1 = xs.min(), xs.max() + 1
        y0, y1 = ys.min(), ys.max() + 1
        crop = gray[y0:y1, x0:x1]

    crop_height, crop_width = crop.shape

    target_size = glyph_size - glyph_padding * 2
    if target_size <= 0:
        raise ValueError(
            f"glyph padding is too large for glyph size: size={glyph_size}, padding={glyph_padding}"
        )

    scale = min(target_size / crop_width, target_size / crop_height)
    if is_basic_latin_punctuation(char):
        scale = min(scale, 1.0)

    new_width = max(1, int(round(crop_width * scale)))
    new_height = max(1, int(round(crop_height * scale)))

    interpolation = cv2.INTER_LANCZOS4 if scale >= 1.0 else cv2.INTER_AREA
    resized = cv2.resize(crop, (new_width, new_height), interpolation=interpolation)
    resized = threshold_final(resized)

    canvas = np.full((glyph_size, glyph_size), 255, dtype=np.uint8)
    x_offset = (glyph_size - new_width) // 2
    y_offset = (glyph_size - new_height) // 2
    canvas[y_offset : y_offset + new_height, x_offset : x_offset + new_width] = resized

    return canvas


def make_pbm_bytes(binary_image):
    black_mask = binary_image == 0
    height, width = black_mask.shape
    header = f"P4\n{width} {height}\n".encode("ascii")
    packed = np.packbits(black_mask.astype(np.uint8), axis=1, bitorder="big")
    return header + packed.tobytes()


def trace_glyph_task(task):
    index = task["index"]
    char = task["char"]
    codepoint = ord(char)
    svg_path = Path(task["svg_dir"]) / f"uni{codepoint:04X}.svg"

    try:
        image, source = decode_cell_image(task)
        normalized = normalize_cell_bitmap(
            image,
            char,
            task["glyph_size"],
            task["glyph_padding"],
            source,
        )
        if task["save_normalized"]:
            normalized_path = Path(task["normalized_dir"]) / f"uni{codepoint:04X}.png"
            if not cv2.imwrite(str(normalized_path), normalized):
                raise ValueError(f"failed to write normalized glyph: {normalized_path}")

        result = subprocess.run(
            ["potrace", "-", "-s", "-o", "-"],
            input=make_pbm_bytes(normalized),
            check=True,
            capture_output=True,
            text=False,
        )
        svg_path.write_bytes(result.stdout)
        return {"ok": True, "index": index, "svg_path": str(svg_path)}
    except Exception as exc:
        return {
            "ok": False,
            "index": index,
            "file": task.get("cell_path", f"{task.get('page', 'memory')} r{task.get('row', -1):02d}_c{task.get('col', -1):02d}"),
            "char": char,
            "unicode": f"U+{codepoint:04X}",
            "error": f"{type(exc).__name__}: {exc}",
        }


def cleanup_empty_tmp_dir():
    if TMP_DIR.exists() and not any(TMP_DIR.iterdir()):
        TMP_DIR.rmdir()


def clear_output_dirs(save_normalized):
    SVG_DIR.mkdir(parents=True, exist_ok=True)
    for old_svg in list_svg_files(SVG_DIR):
        old_svg.unlink()
    if TMP_DIR.exists():
        for old_pbm in TMP_DIR.glob("*.pbm"):
            old_pbm.unlink()

    if save_normalized:
        NORMALIZED_DIR.mkdir(parents=True, exist_ok=True)
        for old_png in NORMALIZED_DIR.rglob("*.png"):
            old_png.unlink()


def run_trace(
    cells_dir=CELLS_DIR,
    charset_path=CHARSET_PATH,
    cell_records=None,
    workers=None,
    glyph_size=DEFAULT_GLYPH_SIZE,
    glyph_padding=DEFAULT_GLYPH_PADDING,
    save_normalized=False,
):
    start = time.perf_counter()
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)

    chars = load_charset(charset_path)
    direct_trace_mode = cell_records is not None
    cell_paths = [] if direct_trace_mode else list_cell_images(cells_dir)
    records = sorted(cell_records or [], key=lambda item: item["index"])
    input_mode = (
        "grayscale crop, resize, final threshold"
        if direct_trace_mode and records and "gray_bytes" in records[0]
        else "binary crop"
        if direct_trace_mode
        else "cell image file"
    )
    worker_count = max(1, int(workers)) if workers else default_worker_count()
    input_count = len(records) if direct_trace_mode else len(cell_paths)
    target_count = min(len(chars), input_count)
    failures = []
    success_count = 0

    if glyph_size <= 0:
        raise ValueError(f"glyph_size must be positive: {glyph_size}")
    if glyph_padding < 0 or glyph_padding * 2 >= glyph_size:
        raise ValueError(
            f"glyph_padding must fit inside glyph_size: size={glyph_size}, padding={glyph_padding}"
        )

    if input_count == 0:
        report = "No cell input found. Skipped SVG tracing.\n"
        REPORT_PATH.write_text(report, encoding="utf-8")
        print(report, end="")
        return True

    clear_output_dirs(save_normalized)

    tasks = []
    for order_index in range(target_count):
        glyph_index = records[order_index]["index"] if direct_trace_mode else order_index
        task = {
            "index": glyph_index,
            "char": chars[glyph_index],
            "svg_dir": str(SVG_DIR),
            "normalized_dir": str(NORMALIZED_DIR),
            "glyph_size": glyph_size,
            "glyph_padding": glyph_padding,
            "save_normalized": save_normalized,
        }
        if direct_trace_mode:
            record = records[order_index]
            task.update(
                {
                    "page": record["page"],
                    "row": record["row"],
                    "col": record["col"],
                }
            )
            if "gray_bytes" in record:
                task.update(
                    {
                        "gray_bytes": record["gray_bytes"],
                        "gray_shape": record["gray_shape"],
                    }
                )
            else:
                task.update(
                    {
                        "binary_bytes": record["binary_bytes"],
                        "binary_shape": record["binary_shape"],
                    }
                )
        else:
            task["cell_path"] = str(cell_paths[order_index])
        tasks.append(task)

    with ProcessPoolExecutor(max_workers=worker_count) as executor:
        futures = [executor.submit(trace_glyph_task, task) for task in tasks]
        for future in as_completed(futures):
            result = future.result()
            if result["ok"]:
                success_count += 1
            else:
                failures.append(
                    "index={index} file={file} char={char} unicode={unicode} error={error}".format(
                        **result
                    )
                )

    if input_count < len(chars):
        for index in range(input_count, len(chars)):
            char = chars[index]
            failures.append(
                f"index={index} file=<missing> char={char} "
                f"unicode=U+{ord(char):04X} error=missing cell input"
            )

    if input_count > len(chars):
        failures.append(f"extra cell inputs ignored: {input_count - len(chars)}")

    cleanup_empty_tmp_dir()
    elapsed = time.perf_counter() - start
    normalized_count = (
        len(list(NORMALIZED_DIR.rglob("*.png")))
        if save_normalized and NORMALIZED_DIR.exists()
        else 0
    )

    lines = [
        "handwrite2350 SVG trace report",
        "=" * 40,
        f"total glyph count: {len(chars)}",
        f"cell inputs found: {input_count}",
        f"direct trace mode: {direct_trace_mode}",
        f"input mode: {input_mode}",
        f"success count: {success_count}",
        f"failed count: {len(failures)}",
        f"worker count: {worker_count}",
        f"glyph size: {glyph_size}",
        f"glyph padding: {glyph_padding}",
        f"save_normalized: {save_normalized}",
        f"normalized PNG count: {normalized_count}",
        f"SVG files in {SVG_DIR}: {len(list_svg_files(SVG_DIR))}",
        f"elapsed time: {elapsed:.2f}s",
        "",
        "failed glyph list:",
    ]
    lines.extend(sorted(failures) if failures else ["None"])

    report = "\n".join(lines) + "\n"
    REPORT_PATH.write_text(report, encoding="utf-8")
    print(report, end="")
    return success_count == len(chars) and not failures


if __name__ == "__main__":
    args = parse_args()
    raise SystemExit(
        0
        if run_trace(
            args.cells_dir,
            args.charset,
            workers=args.workers,
            glyph_size=args.glyph_size,
            glyph_padding=args.glyph_padding,
            save_normalized=args.save_normalized,
        )
        else 1
    )
