import { $ } from "./dom.js";
import { parseCmap } from "./fontParser.js";
import { ProofRenderer } from "./render/proofRenderer.js";
import { refreshInkBoxes } from "./render/measure.js";
import { createInitialState } from "./state.js";
import { collectDom, setStatus, setupModes, syncModeButtons, updateViewerCss } from "./ui.js";

export class ViewerApp {
  constructor() {
    this.state = createInitialState();
    this.dom = collectDom();
    this.renderer = new ProofRenderer(this.dom, this.state);
  }

  init() {
    setupModes(this.dom, this.state, (mode) => this.setMode(mode));
    this.bindEvents();
    this.updateControls();
    this.renderer.render();
  }

  setMode(mode) {
    this.state.mode = mode;
    syncModeButtons(this.state);
    this.renderer.render();
  }

  updateControls() {
    updateViewerCss();
    refreshInkBoxes();
  }

  bindEvents() {
    $("#fontFile").addEventListener("change", (event) => {
      const file = event.target.files[0];
      if (file) this.loadFont(file).catch((error) => this.handleFontError(error));
    });

    ["cellW", "cellH", "glyphSize", "centerGuide", "baselineGuide", "boxGuide"].forEach((id) => {
      $(`#${id}`).addEventListener("input", () => this.updateControls());
    });

    this.dom.sentenceInput.addEventListener("input", () => {
      const preview = document.querySelector(".preview-text");
      if (preview && this.state.mode === "sentence") preview.textContent = this.dom.sentenceInput.value;
    });
  }

  async loadFont(file) {
    this.dom.fileName.textContent = file.name;
    setStatus(this.dom, "LOAD", 12);

    const buffer = await file.arrayBuffer();
    this.state.cps = parseCmap(buffer.slice(0));

    const fontFace = new FontFace(this.state.fontName, buffer.slice(0));
    await fontFace.load();
    document.fonts.add(fontFace);

    document.documentElement.style.setProperty("--fontFamily", `'${this.state.fontName}', system-ui, sans-serif`);
    this.state.fontReady = true;
    await this.renderer.render();
  }

  handleFontError(error) {
    console.error(error);
    this.state.fontReady = false;
    setStatus(this.dom, "ERROR", 0);
    this.dom.proof.className = "proof-area empty";
    this.dom.proof.textContent = String(error);
  }
}
