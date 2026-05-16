import { L, N_COUNT, S_BASE, T, T_COUNT, V, V_COUNT } from "./constants.js";

export function cpHex(char) {
  return `U+${char.codePointAt(0).toString(16).toUpperCase().padStart(4, "0")}`;
}

export function syllable(l, v, t = 0) {
  return String.fromCodePoint(S_BASE + (l * V_COUNT + v) * T_COUNT + t);
}

export function decompose(char) {
  const cp = char.codePointAt(0);
  if (cp < 0xac00 || cp > 0xd7a3) return null;

  const s = cp - S_BASE;
  const l = Math.floor(s / N_COUNT);
  const v = Math.floor((s % N_COUNT) / T_COUNT);
  const t = s % T_COUNT;

  return { l, v, t, lLabel: L[l], vLabel: V[v], tLabel: T[t] || "없음" };
}

export function classify(char) {
  const parts = decompose(char);
  if (parts) return classifyHangul(parts);
  if (/[A-Z]/.test(char)) return char === "I" ? "latin_upper_narrow" : "MW".includes(char) ? "latin_upper_wide" : "latin_upper";
  if (/[a-z]/.test(char)) return classifyLowerLatin(char);
  if (/[0-9]/.test(char)) return char === "1" ? "digit_one" : "digit";
  if (".,".includes(char)) return "punct_bottom";
  if (":;".includes(char)) return "punct_middle";
  if ("\"'`^".includes(char)) return "punct_top";
  if ("-_=".includes(char)) return "punct_horizontal";
  if ("()[]{}".includes(char)) return "punct_bracket";
  if ("/\\|".includes(char)) return "punct_slash";
  if ("@#$%&".includes(char)) return "punct_large_symbol";
  if ("+*<>~".includes(char)) return "punct_operator";
  return "symbol";
}

export function shortGroupName(group) {
  return group
    .replace("hangul_", "H_")
    .replace("horizontal", "hori")
    .replace("_no_final", "_NF")
    .replace("_with_final", "_WF");
}

function classifyHangul(parts) {
  let base = "hangul_vertical";
  if ([8, 12].includes(parts.v)) base = "hangul_horizontal_top";
  if ([13, 17].includes(parts.v)) base = "hangul_horizontal_bottom";
  if (parts.v === 18) base = "hangul_horizontal_flat";
  if ([9, 10, 11].includes(parts.v)) base = "hangul_mixed_top";
  if ([14, 15, 16].includes(parts.v)) base = "hangul_mixed_bottom";
  if (parts.v === 19) base = "hangul_mixed_flat";
  return `${base}${parts.t ? "_with_final" : "_no_final"}`;
}

function classifyLowerLatin(char) {
  if (char === "i") return "latin_lower_i";
  if (char === "j") return "latin_lower_j";
  if (char === "t") return "latin_lower_t";
  if ("mw".includes(char)) return "latin_lower_wide";
  if ("bdfhkl".includes(char)) return "latin_lower_ascender";
  if ("gpqy".includes(char)) return "latin_lower_descender";
  return "latin_lower_xheight";
}
