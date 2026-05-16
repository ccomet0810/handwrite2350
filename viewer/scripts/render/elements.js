import { createElement } from "../dom.js";
import { classify, cpHex, decompose } from "../glyph.js";
import { applyInkBox } from "./measure.js";

export function appendSection(proof, title) {
  const section = createElement("section", "proof-section");
  const heading = createElement("h2", "section-title", title);
  const body = createElement("div", "section-body");

  section.append(heading, body);
  proof.appendChild(section);
  return [section, body];
}

export function matrixHead(labels, options = {}) {
  const head = createElement("div", options.className ? `matrix-head ${options.className}` : "matrix-head");
  head.style.setProperty("--cols", labels.length);
  head.appendChild(headerCell(options.cornerText || "", options.cornerClassName));
  labels.forEach((label) => head.appendChild(headerCell(label)));
  return head;
}

export function matrixRow(label, cols) {
  const row = createElement("div", "matrix-row");
  row.style.setProperty("--cols", cols);
  row.appendChild(rowLabel(label));
  return row;
}

export function createCell(char, state, dom, options = {}) {
  const present = options.forcePresent || state.cps.has(char.codePointAt(0));
  const cell = createElement("button", `cell${present ? "" : " missing"}`);
  const hline = createElement("span", "hline");
  const baseline = createElement("span", "baseline");
  const boxline = createElement("span", "boxline");
  const charNode = createElement("span", "glyph", char);

  cell.type = "button";
  cell.dataset.char = char;
  cell.title = `${char} ${cpHex(char)} ${classify(char)}${present ? "" : " MISSING"}`;
  cell.append(hline, baseline, boxline, charNode);
  cell.addEventListener("click", () => showInfo(dom, char, present));
  applyInkBox(cell, char);
  return cell;
}

function headerCell(text, extraClassName = "") {
  const className = extraClassName || !text ? "header-cell corner-cell" : "header-cell";
  const cell = createElement("div", `${className}${extraClassName ? ` ${extraClassName}` : ""}`, text);
  return cell;
}

function rowLabel(text) {
  return createElement("div", "row-label", text);
}

function showInfo(dom, char, present) {
  const parts = decompose(char);
  const lines = [char, cpHex(char), present ? "present" : "missing", classify(char)];

  if (parts) {
    lines.push(`L ${parts.l}: ${parts.lLabel}`, `V ${parts.v}: ${parts.vLabel}`, `T ${parts.t}: ${parts.tLabel}`);
  }

  dom.cellInfo.textContent = lines.join("\n");
}
