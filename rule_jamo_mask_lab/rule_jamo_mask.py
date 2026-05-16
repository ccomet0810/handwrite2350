"""Rule-based draft jamo slot mask generation for Hangul glyph images.

This module intentionally uses simple image-processing heuristics. It creates
draft masks for human cleanup, not final segmentation labels.
"""

from __future__ import annotations

import csv
import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable

import cv2
import numpy as np
from PIL import Image


MASK_COLORS = {
    "background": (255, 255, 255),
    "cho": (255, 0, 0),
    "jung": (0, 255, 0),
    "jong": (0, 0, 255),
    "ignore": (128, 128, 128),
}

CHOSEONG = [
    "ㄱ",
    "ㄲ",
    "ㄴ",
    "ㄷ",
    "ㄸ",
    "ㄹ",
    "ㅁ",
    "ㅂ",
    "ㅃ",
    "ㅅ",
    "ㅆ",
    "ㅇ",
    "ㅈ",
    "ㅉ",
    "ㅊ",
    "ㅋ",
    "ㅌ",
    "ㅍ",
    "ㅎ",
]
JUNGSEONG = [
    "ㅏ",
    "ㅐ",
    "ㅑ",
    "ㅒ",
    "ㅓ",
    "ㅔ",
    "ㅕ",
    "ㅖ",
    "ㅗ",
    "ㅘ",
    "ㅙ",
    "ㅚ",
    "ㅛ",
    "ㅜ",
    "ㅝ",
    "ㅞ",
    "ㅟ",
    "ㅠ",
    "ㅡ",
    "ㅢ",
    "ㅣ",
]
JONGSEONG = [
    "",
    "ㄱ",
    "ㄲ",
    "ㄳ",
    "ㄴ",
    "ㄵ",
    "ㄶ",
    "ㄷ",
    "ㄹ",
    "ㄺ",
    "ㄻ",
    "ㄼ",
    "ㄽ",
    "ㄾ",
    "ㄿ",
    "ㅀ",
    "ㅁ",
    "ㅂ",
    "ㅄ",
    "ㅅ",
    "ㅆ",
    "ㅇ",
    "ㅈ",
    "ㅊ",
    "ㅋ",
    "ㅌ",
    "ㅍ",
    "ㅎ",
]

VERTICAL_VOWELS = {0, 1, 2, 3, 4, 5, 6, 7, 20}
HORIZONTAL_VOWELS = {8, 12, 13, 17, 18}
COMPLEX_VOWELS = {9, 10, 11, 14, 15, 16, 19}

IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".bmp", ".tif", ".tiff"}
UNICODE_RE = re.compile(r"(?:U\+?|uni)([A-Fa-f0-9]{4,6})", re.IGNORECASE)


@dataclass
class HangulDecomposition:
    char: str
    unicode: str
    l_index: int
    v_index: int
    t_index: int
    cho: str
    jung: str
    jong: str
    has_jong: bool
    layout_type: str


@dataclass
class Component:
    component_id: int
    bbox: tuple[int, int, int, int]
    center: tuple[float, float]
    area: int
    fill_ratio: float
    assigned_slot: str = "ignore"
    confidence: float = 0.0
    reason: str = ""


@dataclass
class GlyphResult:
    input_path: str
    mask_path: str
    char: str
    unicode: str
    status: str
    warnings: list[str]
    metadata_path: str


def decompose_hangul_syllable(char: str) -> HangulDecomposition:
    """Return Unicode Hangul syllable decomposition and rough vowel layout."""
    code = ord(char)
    if not 0xAC00 <= code <= 0xD7A3:
        raise ValueError(f"not a precomposed Hangul syllable: {char!r}")

    syllable_index = code - 0xAC00
    l_index = syllable_index // (21 * 28)
    v_index = (syllable_index % (21 * 28)) // 28
    t_index = syllable_index % 28
    if v_index in VERTICAL_VOWELS:
        layout_type = "vertical"
    elif v_index in HORIZONTAL_VOWELS:
        layout_type = "horizontal"
    else:
        layout_type = "complex"

    return HangulDecomposition(
        char=char,
        unicode=f"U{code:04X}",
        l_index=l_index,
        v_index=v_index,
        t_index=t_index,
        cho=CHOSEONG[l_index],
        jung=JUNGSEONG[v_index],
        jong=JONGSEONG[t_index],
        has_jong=t_index > 0,
        layout_type=layout_type,
    )


def char_from_path(path: Path, allow_template_suffix: bool = False) -> tuple[str, str]:
    """Infer a Hangul syllable from a filename such as UAC00.png."""
    stem = path.stem
    if allow_template_suffix and stem.endswith("_original"):
        stem = stem[: -len("_original")]

    match = UNICODE_RE.search(stem)
    if match:
        code = int(match.group(1), 16)
        char = chr(code)
        if 0xAC00 <= code <= 0xD7A3:
            return char, f"U{code:04X}"
        raise ValueError(f"{path.name}: Unicode code is not a Hangul syllable")

    for char in stem:
        if 0xAC00 <= ord(char) <= 0xD7A3:
            return char, f"U{ord(char):04X}"
    raise ValueError(f"{path.name}: cannot infer Hangul syllable from filename")


def iter_image_paths(input_dir: Path, recursive: bool = False) -> Iterable[Path]:
    pattern = "**/*" if recursive else "*"
    for path in sorted(input_dir.glob(pattern)):
        if path.is_file() and path.suffix.lower() in IMAGE_SUFFIXES:
            yield path


def load_grayscale(path: Path) -> np.ndarray:
    image = Image.open(path).convert("L")
    return np.array(image)


def extract_foreground(gray: np.ndarray, threshold: int) -> np.ndarray:
    """Foreground is darker than threshold."""
    return gray < threshold


def connected_components(foreground: np.ndarray, min_area: int) -> list[Component]:
    labels_count, labels, stats, centroids = cv2.connectedComponentsWithStats(
        foreground.astype(np.uint8), connectivity=8
    )
    components: list[Component] = []
    for label in range(1, labels_count):
        x, y, w, h, area = stats[label]
        if int(area) < min_area:
            continue
        fill_ratio = float(area) / float(max(w * h, 1))
        components.append(
            Component(
                component_id=int(label),
                bbox=(int(x), int(y), int(w), int(h)),
                center=(float(centroids[label][0]), float(centroids[label][1])),
                area=int(area),
                fill_ratio=fill_ratio,
            )
        )
    return components


def assign_components(
    components: list[Component],
    decomposition: HangulDecomposition,
    image_shape: tuple[int, int],
    strict: bool = False,
) -> list[str]:
    """Assign connected components to draft jamo slots using location rules."""
    height, width = image_shape
    warnings: list[str] = []
    if not components:
        return ["no foreground components found"]

    total_area = sum(component.area for component in components)
    if len(components) == 1:
        warnings.append("single connected component; likely touching strokes")
        if strict:
            components[0].assigned_slot = "ignore"
            components[0].confidence = 0.0
            components[0].reason = "strict: single connected component"
            return warnings
    if len(components) > 12:
        warnings.append(f"too many components for simple slot rules: {len(components)}")

    glyph_bbox = _union_bbox(components)
    gx, gy, gw, gh = glyph_bbox
    split_x = gx + gw * (0.52 if decomposition.layout_type == "vertical" else 0.58)
    split_y = gy + gh * (0.62 if decomposition.has_jong else 0.55)
    jong_y = gy + gh * 0.64

    for component in components:
        x, y, w, h = component.bbox
        cx, cy = component.center
        area_fraction = component.area / max(total_area, 1)
        spans_x = x < split_x < x + w
        spans_y = y < split_y < y + h
        crosses_relevant_split = _crosses_relevant_split(
            decomposition, spans_x=spans_x, spans_y=spans_y, cy=cy, jong_y=jong_y
        )
        too_large = area_fraction > 0.72 or (w * h) > (width * height * 0.72)

        if too_large:
            component.assigned_slot = "ignore" if strict else _large_component_guess(
                decomposition, cx, cy, split_x, split_y, jong_y
            )
            component.confidence = 0.15 if strict else 0.35
            component.reason = "component too large for reliable slot split"
            warnings.append(
                f"component {component.component_id} too large; assigned {component.assigned_slot}"
            )
            continue

        if decomposition.has_jong and cy >= jong_y:
            confidence = _distance_confidence(cy - jong_y, gh)
            component.assigned_slot = "jong"
            component.confidence = confidence
            component.reason = "has final consonant and component is in lower band"
        elif decomposition.layout_type == "vertical":
            component.assigned_slot = "jung" if cx >= split_x else "cho"
            component.confidence = _distance_confidence(abs(cx - split_x), gw)
            component.reason = "vertical vowel: right band=jung, left band=cho"
        elif decomposition.layout_type == "horizontal":
            component.assigned_slot = "jung" if cy >= split_y else "cho"
            component.confidence = _distance_confidence(abs(cy - split_y), gh)
            component.reason = "horizontal vowel: lower band=jung, upper band=cho"
        else:
            right_score = cx / max(width, 1)
            lower_score = cy / max(height, 1)
            if right_score > 0.52 or lower_score > 0.56:
                component.assigned_slot = "jung"
                component.confidence = min(0.85, 0.45 + max(right_score - 0.52, lower_score - 0.56))
                component.reason = "complex vowel: right/lower component likely jung"
            else:
                component.assigned_slot = "cho"
                component.confidence = 0.55
                component.reason = "complex vowel: upper-left component likely cho"

        if strict and (component.confidence < 0.55 or crosses_relevant_split):
            warnings.append(
                f"component {component.component_id} ambiguous; ignored in strict mode"
            )
            component.assigned_slot = "ignore"
            component.reason += "; strict ambiguity guard"
            component.confidence = min(component.confidence, 0.35)
        elif component.confidence < 0.55 or crosses_relevant_split:
            warnings.append(
                f"component {component.component_id} low confidence or crosses split lines"
            )

    _warn_missing_slots(components, decomposition, warnings)
    return warnings


def build_rgb_mask(labels: np.ndarray, components: list[Component]) -> np.ndarray:
    mask = np.full((*labels.shape, 3), MASK_COLORS["background"], dtype=np.uint8)
    for component in components:
        color = MASK_COLORS.get(component.assigned_slot, MASK_COLORS["ignore"])
        mask[labels == component.component_id] = color
    return mask


def component_label_image(foreground: np.ndarray) -> np.ndarray:
    return cv2.connectedComponentsWithStats(foreground.astype(np.uint8), connectivity=8)[1]


def save_overlay(gray: np.ndarray, mask: np.ndarray, path: Path, alpha: float = 0.42) -> None:
    base = np.stack([gray, gray, gray], axis=-1).astype(np.float32)
    colored = mask.astype(np.float32)
    active = np.any(mask != np.array(MASK_COLORS["background"], dtype=np.uint8), axis=-1)
    overlay = base.copy()
    overlay[active] = base[active] * (1.0 - alpha) + colored[active] * alpha
    Image.fromarray(np.clip(overlay, 0, 255).astype(np.uint8)).save(path)


def save_extracted_components(
    gray: np.ndarray,
    labels: np.ndarray,
    components: list[Component],
    out_dir: Path,
) -> None:
    counters = {"cho": 0, "jung": 0, "jong": 0, "ignore": 0}
    out_dir.mkdir(parents=True, exist_ok=True)
    for component in components:
        slot = component.assigned_slot
        if slot not in counters:
            slot = "ignore"
        x, y, w, h = component.bbox
        component_mask = labels[y : y + h, x : x + w] == component.component_id
        crop = np.full((h, w), 255, dtype=np.uint8)
        crop[component_mask] = gray[y : y + h, x : x + w][component_mask]
        name = f"{slot}_{counters[slot]}.png"
        counters[slot] += 1
        Image.fromarray(crop).save(out_dir / name)


def generate_for_image(
    image_path: Path,
    out_dir: Path,
    threshold: int = 180,
    min_area: int = 8,
    save_components: bool = False,
    save_overlay_preview: bool = False,
    strict: bool = False,
    allow_template_suffix: bool = False,
) -> GlyphResult:
    char, unicode_name = char_from_path(image_path, allow_template_suffix)
    decomposition = decompose_hangul_syllable(char)
    gray = load_grayscale(image_path)
    foreground = extract_foreground(gray, threshold)
    labels = component_label_image(foreground)
    components = connected_components(foreground, min_area)
    warnings = assign_components(components, decomposition, gray.shape, strict=strict)
    mask = build_rgb_mask(labels, components)

    out_dir.mkdir(parents=True, exist_ok=True)
    mask_path = out_dir / f"{unicode_name}.png"
    Image.fromarray(mask).save(mask_path)

    overlay_path = None
    if save_overlay_preview:
        overlay_dir = out_dir / "overlay_previews"
        overlay_dir.mkdir(parents=True, exist_ok=True)
        overlay_path = overlay_dir / f"{unicode_name}_overlay.png"
        save_overlay(gray, mask, overlay_path)

    components_dir = None
    if save_components:
        components_dir = out_dir / "extracted_components" / unicode_name
        save_extracted_components(gray, labels, components, components_dir)

    metadata_dir = out_dir / "metadata"
    metadata_dir.mkdir(parents=True, exist_ok=True)
    metadata_path = metadata_dir / f"{unicode_name}_meta.json"
    metadata = {
        "char": char,
        "unicode": unicode_name,
        "input_path": str(image_path),
        "mask_path": str(mask_path),
        "overlay_path": str(overlay_path) if overlay_path else None,
        "components_dir": str(components_dir) if components_dir else None,
        "threshold": threshold,
        "min_area": min_area,
        "strict": strict,
        "decomposition": {
            "cho": decomposition.cho,
            "jung": decomposition.jung,
            "jong": decomposition.jong,
            "l_index": decomposition.l_index,
            "v_index": decomposition.v_index,
            "t_index": decomposition.t_index,
        },
        "layout_type": decomposition.layout_type,
        "has_jong": decomposition.has_jong,
        "components": [
            {
                **asdict(component),
                "bbox": list(component.bbox),
                "center": [round(component.center[0], 3), round(component.center[1], 3)],
                "confidence": round(component.confidence, 3),
            }
            for component in components
        ],
        "warnings": warnings,
    }
    metadata_path.write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )

    status = "warning" if warnings else "ok"
    return GlyphResult(
        input_path=str(image_path),
        mask_path=str(mask_path),
        char=char,
        unicode=unicode_name,
        status=status,
        warnings=warnings,
        metadata_path=str(metadata_path),
    )


def generate_for_image_ordered(
    image_path: Path,
    mask_dir: Path,
    metadata_dir: Path,
    overlay_dir: Path | None = None,
    components_root: Path | None = None,
    threshold: int = 180,
    min_area: int = 8,
    strict: bool = False,
    allow_template_suffix: bool = False,
) -> GlyphResult:
    char, unicode_name = char_from_path(image_path, allow_template_suffix)
    decomposition = decompose_hangul_syllable(char)
    gray = load_grayscale(image_path)
    foreground = extract_foreground(gray, threshold)
    labels = component_label_image(foreground)
    components = connected_components(foreground, min_area)
    warnings = assign_components(components, decomposition, gray.shape, strict=strict)
    mask = build_rgb_mask(labels, components)

    mask_dir.mkdir(parents=True, exist_ok=True)
    mask_path = mask_dir / f"{unicode_name}.png"
    Image.fromarray(mask).save(mask_path)

    overlay_path = None
    if overlay_dir is not None:
        overlay_dir.mkdir(parents=True, exist_ok=True)
        overlay_path = overlay_dir / f"{unicode_name}_overlay.png"
        save_overlay(gray, mask, overlay_path)

    components_dir = None
    if components_root is not None:
        components_dir = components_root / unicode_name
        save_extracted_components(gray, labels, components, components_dir)

    metadata_dir.mkdir(parents=True, exist_ok=True)
    metadata_path = metadata_dir / f"{unicode_name}_meta.json"
    metadata = {
        "char": char,
        "unicode": unicode_name,
        "input_path": str(image_path),
        "mask_path": str(mask_path),
        "overlay_path": str(overlay_path) if overlay_path else None,
        "components_dir": str(components_dir) if components_dir else None,
        "threshold": threshold,
        "min_area": min_area,
        "strict": strict,
        "decomposition": {
            "cho": decomposition.cho,
            "jung": decomposition.jung,
            "jong": decomposition.jong,
            "l_index": decomposition.l_index,
            "v_index": decomposition.v_index,
            "t_index": decomposition.t_index,
        },
        "layout_type": decomposition.layout_type,
        "has_jong": decomposition.has_jong,
        "components": [
            {
                **asdict(component),
                "bbox": list(component.bbox),
                "center": [round(component.center[0], 3), round(component.center[1], 3)],
                "confidence": round(component.confidence, 3),
            }
            for component in components
        ],
        "warnings": warnings,
    }
    metadata_path.write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )

    status = "warning" if warnings else "ok"
    return GlyphResult(
        input_path=str(image_path),
        mask_path=str(mask_path),
        char=char,
        unicode=unicode_name,
        status=status,
        warnings=warnings,
        metadata_path=str(metadata_path),
    )


def generate_for_directory_ordered(
    input_dir: Path,
    mask_dir: Path,
    metadata_dir: Path,
    report_dir: Path,
    overlay_dir: Path | None = None,
    components_root: Path | None = None,
    threshold: int = 180,
    min_area: int = 8,
    strict: bool = False,
    allow_template_suffix: bool = False,
) -> list[GlyphResult]:
    results: list[GlyphResult] = []
    rows: list[dict[str, str]] = []

    for image_path in iter_image_paths(input_dir, recursive=False):
        try:
            result = generate_for_image_ordered(
                image_path=image_path,
                mask_dir=mask_dir,
                metadata_dir=metadata_dir,
                overlay_dir=overlay_dir,
                components_root=components_root,
                threshold=threshold,
                min_area=min_area,
                strict=strict,
                allow_template_suffix=allow_template_suffix,
            )
            results.append(result)
            warnings = "; ".join(result.warnings) if result.warnings else "-"
            rows.append(
                {
                    "font_stem": input_dir.parent.name,
                    "char": result.char,
                    "unicode": result.unicode,
                    "status": result.status,
                    "warnings": warnings,
                    "input_path": result.input_path,
                    "mask_path": result.mask_path,
                    "metadata_path": result.metadata_path,
                }
            )
        except Exception as exc:
            rows.append(
                {
                    "font_stem": input_dir.parent.name,
                    "char": "",
                    "unicode": image_path.stem,
                    "status": "error",
                    "warnings": str(exc),
                    "input_path": str(image_path),
                    "mask_path": "",
                    "metadata_path": "",
                }
            )

    _write_summary(report_dir / "summary.tsv", rows)
    return results


def generate_for_directory(
    input_dir: Path,
    out_dir: Path,
    threshold: int = 180,
    min_area: int = 8,
    save_components: bool = False,
    save_overlay_preview: bool = False,
    strict: bool = False,
    allow_template_suffix: bool = False,
    recursive: bool = False,
) -> list[GlyphResult]:
    results: list[GlyphResult] = []
    rows: list[dict[str, str]] = []

    for image_path in iter_image_paths(input_dir, recursive=recursive):
        relative_parent = image_path.parent.relative_to(input_dir)
        target_dir = out_dir / relative_parent if recursive else out_dir
        try:
            result = generate_for_image(
                image_path=image_path,
                out_dir=target_dir,
                threshold=threshold,
                min_area=min_area,
                save_components=save_components,
                save_overlay_preview=save_overlay_preview,
                strict=strict,
                allow_template_suffix=allow_template_suffix,
            )
            results.append(result)
            warnings = "; ".join(result.warnings) if result.warnings else "-"
            rows.append(
                {
                    "font_stem": str(relative_parent) if str(relative_parent) != "." else input_dir.name,
                    "char": result.char,
                    "unicode": result.unicode,
                    "status": result.status,
                    "warnings": warnings,
                    "input_path": result.input_path,
                    "mask_path": result.mask_path,
                    "metadata_path": result.metadata_path,
                }
            )
        except Exception as exc:  # Keep batch generation useful on mixed folders.
            unicode_name = image_path.stem
            rows.append(
                {
                    "font_stem": str(relative_parent) if str(relative_parent) != "." else input_dir.name,
                    "char": "",
                    "unicode": unicode_name,
                    "status": "error",
                    "warnings": str(exc),
                    "input_path": str(image_path),
                    "mask_path": "",
                    "metadata_path": "",
                }
            )

    _write_summary(out_dir / "summary.tsv", rows)
    return results


def _write_summary(path: Path, rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "font_stem",
        "char",
        "unicode",
        "status",
        "warnings",
        "input_path",
        "mask_path",
        "metadata_path",
    ]
    with path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames, delimiter="\t")
        writer.writeheader()
        writer.writerows(rows)


def _union_bbox(components: list[Component]) -> tuple[int, int, int, int]:
    x0 = min(component.bbox[0] for component in components)
    y0 = min(component.bbox[1] for component in components)
    x1 = max(component.bbox[0] + component.bbox[2] for component in components)
    y1 = max(component.bbox[1] + component.bbox[3] for component in components)
    return x0, y0, x1 - x0, y1 - y0


def _distance_confidence(distance: float, span: float) -> float:
    return round(float(min(0.95, max(0.35, 0.45 + distance / max(span, 1.0)))), 3)


def _large_component_guess(
    decomposition: HangulDecomposition,
    cx: float,
    cy: float,
    split_x: float,
    split_y: float,
    jong_y: float,
) -> str:
    if decomposition.has_jong and cy >= jong_y:
        return "jong"
    if decomposition.layout_type == "vertical":
        return "jung" if cx >= split_x else "cho"
    if decomposition.layout_type == "horizontal":
        return "jung" if cy >= split_y else "cho"
    return "ignore"


def _crosses_relevant_split(
    decomposition: HangulDecomposition,
    spans_x: bool,
    spans_y: bool,
    cy: float,
    jong_y: float,
) -> bool:
    if decomposition.has_jong and cy >= jong_y:
        return spans_y
    if decomposition.layout_type == "vertical":
        return spans_x
    if decomposition.layout_type == "horizontal":
        return spans_y
    return spans_x or spans_y


def _warn_missing_slots(
    components: list[Component],
    decomposition: HangulDecomposition,
    warnings: list[str],
) -> None:
    assigned = {component.assigned_slot for component in components}
    required = {"cho", "jung"}
    if decomposition.has_jong:
        required.add("jong")
    missing = sorted(required - assigned)
    if missing:
        warnings.append(f"missing assigned slots: {', '.join(missing)}")
