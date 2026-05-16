import { $, $$ } from "./dom.js";
import { MODES } from "./constants.js";

export function collectDom() {
  return {
    proof: $("#proof"),
    status: $("#status"),
    statusText: $("#statusText"),
    progressBar: $("#progressBar"),
    cellInfo: $("#cellInfo"),
    fileName: $("#fileName"),
    modes: $("#modes"),
    sentencePanel: $("#sentencePanel"),
    cellInfoPanel: $("#cellInfoPanel"),
    sentenceInput: $("#sentenceInput"),
  };
}

export function setStatus(dom, text, pct = 0) {
  dom.statusText.textContent = text;
  dom.progressBar.style.width = `${Math.max(0, Math.min(100, pct))}%`;
  dom.status.classList.toggle("active", Boolean(text && !text.startsWith("READY")));
}

export function syncPanels(dom, state) {
  const sentenceMode = state.mode === "sentence";
  dom.sentencePanel.classList.toggle("is-hidden", !sentenceMode);
  dom.cellInfoPanel.classList.toggle("is-hidden", sentenceMode);
}

export function setupModes(dom, state, onChange) {
  MODES.forEach(([id, label]) => {
    const button = document.createElement("button");
    button.type = "button";
    button.className = "mode-button";
    button.dataset.mode = id;
    button.textContent = label;
    button.addEventListener("click", () => onChange(id));
    dom.modes.appendChild(button);
  });

  syncModeButtons(state);
}

export function syncModeButtons(state) {
  $$(".mode-button").forEach((button) => {
    button.classList.toggle("active", button.dataset.mode === state.mode);
  });
}

export function updateViewerCss() {
  const cellW = $("#cellW").value;
  const cellH = $("#cellH").value;
  const glyphSize = $("#glyphSize").value;

  document.documentElement.style.setProperty("--cellW", `${cellW}px`);
  document.documentElement.style.setProperty("--cellH", `${cellH}px`);
  document.documentElement.style.setProperty("--glyphSize", `${glyphSize}px`);

  $("#cellWOut").textContent = cellW;
  $("#cellHOut").textContent = cellH;
  $("#glyphSizeOut").textContent = glyphSize;

  document.body.classList.toggle("show-center", $("#centerGuide").checked);
  document.body.classList.toggle("show-baseline", $("#baselineGuide").checked);
  document.body.classList.toggle("show-box", $("#boxGuide").checked);
}
