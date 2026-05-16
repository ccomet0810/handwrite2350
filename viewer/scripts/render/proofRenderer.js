import { BASIC_LATIN_CHARS, HANGUL_GROUPS, L, T, V } from "../constants.js";
import { classify, shortGroupName, syllable } from "../glyph.js";
import { setStatus, syncPanels } from "../ui.js";
import { appendSection, createCell, matrixHead, matrixRow } from "./elements.js";

export class ProofRenderer {
  constructor(dom, state) {
    this.dom = dom;
    this.state = state;
  }

  async render() {
    this.state.renderToken += 1;
    const token = this.state.renderToken;

    syncPanels(this.dom, this.state);

    if (!this.state.fontReady) {
      this.dom.proof.className = "proof-area empty";
      this.dom.proof.textContent = "폰트를 선택하면 프루프가 표시됩니다.";
      return;
    }

    this.clearProof();
    setStatus(this.dom, "RENDER", 8);

    if (this.state.mode === "basic") await this.renderBasic(token);
    if (this.state.mode === "noFinal") await this.renderNoFinal(token);
    if (this.state.mode === "finals") await this.renderFinals(token);
    if (this.state.mode === "hangulAll") await this.renderHangulAll(token);
    if (this.state.mode === "hangulGroups") await this.renderHangulGroups(token);
    if (this.state.mode === "all2444") await this.renderAll(token);
    if (this.state.mode === "sentence") this.renderSentence();

    if (this.isCurrent(token)) setStatus(this.dom, `READY ${this.state.cps.size}`, 100);
  }

  clearProof() {
    this.dom.proof.className = "proof-area";
    this.dom.proof.replaceChildren();
  }

  isCurrent(token) {
    return token === this.state.renderToken;
  }

  async renderBasic(token) {
    await this.appendFlowSection("Basic Latin", Array.from(BASIC_LATIN_CHARS), token);
  }

  async renderNoFinal(token) {
    const [, body] = appendSection(this.dom.proof, "Hangul no-final matrix");
    body.appendChild(matrixHead(V));

    for (let l = 0; l < L.length && this.isCurrent(token); l += 1) {
      const row = matrixRow(L[l], V.length);
      for (let v = 0; v < V.length; v += 1) row.appendChild(createCell(syllable(l, v, 0), this.state, this.dom));
      body.appendChild(row);
      if (l % 3 === 0) await yieldUI();
    }
  }

  async renderFinals(token) {
    const [, body] = appendSection(this.dom.proof, "Hangul final matrix / onset ㅇ");
    body.appendChild(matrixHead(T.map((value) => value || "없음")));

    const ieung = 11;
    for (let v = 0; v < V.length && this.isCurrent(token); v += 1) {
      const row = matrixRow(V[v], T.length);
      for (let t = 0; t < T.length; t += 1) row.appendChild(createCell(syllable(ieung, v, t), this.state, this.dom));
      body.appendChild(row);
      if (v % 2 === 0) await yieldUI();
    }
  }

  async renderHangulAll(token) {
    const [, body] = appendSection(this.dom.proof, "Hangul all / onset sections");

    for (let l = 0; l < L.length && this.isCurrent(token); l += 1) {
      const block = document.createElement("div");
      block.className = "onset-block";
      block.appendChild(matrixHead(T.map((value) => value || "없음"), {
        className: "onset-head",
        cornerClassName: "onset-corner",
        cornerText: L[l],
      }));

      for (let v = 0; v < V.length; v += 1) {
        const row = matrixRow(V[v], T.length);
        for (let t = 0; t < T.length; t += 1) row.appendChild(createCell(syllable(l, v, t), this.state, this.dom));
        block.appendChild(row);
      }

      body.appendChild(block);
      await yieldUI();
    }
  }

  async renderHangulGroups(token) {
    for (const group of HANGUL_GROUPS) {
      if (!this.isCurrent(token)) return;

      const chars = [];
      for (let l = 0; l < L.length; l += 1) {
        for (let v = 0; v < V.length; v += 1) {
          for (let t = 0; t < T.length; t += 1) {
            const char = syllable(l, v, t);
            if (classify(char) === group && this.state.cps.has(char.codePointAt(0))) chars.push(char);
          }
        }
      }

      if (chars.length) await this.appendFlowSection(shortGroupName(group), chars, token, { showMissing: false });
    }
  }

  async renderAll(token) {
    const chars = [];
    for (let cp = 0x21; cp <= 0x7e; cp += 1) chars.push(String.fromCodePoint(cp));

    Array.from(this.state.cps)
      .filter((cp) => cp >= 0xac00 && cp <= 0xd7a3)
      .sort((a, b) => a - b)
      .forEach((cp) => chars.push(String.fromCodePoint(cp)));

    await this.appendFlowSection(`All visible glyphs / ${chars.length}`, chars, token);
  }

  renderSentence() {
    const [, body] = appendSection(this.dom.proof, "Text");
    const wrap = document.createElement("div");
    const guides = document.createElement("div");
    const text = document.createElement("div");

    wrap.className = "preview-wrap";
    guides.className = "sentence-guides";
    guides.innerHTML = '<span class="hline"></span><span class="baseline"></span><span class="boxline"></span>';
    text.className = "preview-text";
    text.textContent = this.dom.sentenceInput.value;

    wrap.append(guides, text);
    body.appendChild(wrap);
  }

  async appendFlowSection(title, chars, token, options = {}) {
    const { batch = 180, showMissing = true } = options;
    const [, body] = appendSection(this.dom.proof, title);
    const grid = document.createElement("div");

    grid.className = "flow-grid";
    body.appendChild(grid);

    for (let i = 0; i < chars.length && this.isCurrent(token); i += 1) {
      grid.appendChild(createCell(chars[i], this.state, this.dom, { forcePresent: !showMissing }));
      if (i % batch === 0) await yieldUI();
    }
  }
}

function yieldUI() {
  return new Promise((resolve) => setTimeout(resolve, 0));
}
