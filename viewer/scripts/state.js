export function createInitialState() {
  return {
    fontReady: false,
    fontName: "ProofFont",
    cps: new Set(),
    mode: "hangulAll",
    renderToken: 0,
  };
}
