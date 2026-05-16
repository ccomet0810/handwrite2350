import { $ } from "../dom.js";

const measureCanvas = document.createElement("canvas");
const measureCtx = measureCanvas.getContext("2d");

export function applyInkBox(element, char) {
  const box = measureGlyph(char);
  element.style.setProperty("--inkW", `${box.width}px`);
  element.style.setProperty("--inkH", `${box.height}px`);
}

export function refreshInkBoxes() {
  document.querySelectorAll(".cell[data-char]").forEach((cell) => applyInkBox(cell, cell.dataset.char));
}

function measureGlyph(char) {
  const size = Number($("#glyphSize").value);
  const family = getComputedStyle(document.documentElement).getPropertyValue("--fontFamily");

  measureCtx.font = `${size}px ${family}`;
  const metrics = measureCtx.measureText(char);
  const width = (metrics.actualBoundingBoxLeft || 0) + (metrics.actualBoundingBoxRight || metrics.width || size);
  const height = (metrics.actualBoundingBoxAscent || size * 0.8) + (metrics.actualBoundingBoxDescent || size * 0.2);

  return {
    width: Math.max(1, Math.ceil(width)),
    height: Math.max(1, Math.ceil(height)),
  };
}
