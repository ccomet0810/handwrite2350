export const L = ["ㄱ", "ㄲ", "ㄴ", "ㄷ", "ㄸ", "ㄹ", "ㅁ", "ㅂ", "ㅃ", "ㅅ", "ㅆ", "ㅇ", "ㅈ", "ㅉ", "ㅊ", "ㅋ", "ㅌ", "ㅍ", "ㅎ"];
export const V = ["ㅏ", "ㅐ", "ㅑ", "ㅒ", "ㅓ", "ㅔ", "ㅕ", "ㅖ", "ㅗ", "ㅘ", "ㅙ", "ㅚ", "ㅛ", "ㅜ", "ㅝ", "ㅞ", "ㅟ", "ㅠ", "ㅡ", "ㅢ", "ㅣ"];
export const T = ["", "ㄱ", "ㄲ", "ㄳ", "ㄴ", "ㄵ", "ㄶ", "ㄷ", "ㄹ", "ㄺ", "ㄻ", "ㄼ", "ㄽ", "ㄾ", "ㄿ", "ㅀ", "ㅁ", "ㅂ", "ㅄ", "ㅅ", "ㅆ", "ㅇ", "ㅈ", "ㅊ", "ㅋ", "ㅌ", "ㅍ", "ㅎ"];

export const S_BASE = 0xac00;
export const V_COUNT = 21;
export const T_COUNT = 28;
export const N_COUNT = V_COUNT * T_COUNT;

export const MODES = [
  ["hangulAll", "한글 전체"],
  ["noFinal", "한글 무받침"],
  ["finals", "한글 받침"],
  ["hangulGroups", "한글 유형별"],
  ["basic", "Basic Latin"],
  ["all2444", "전체 보기"],
  ["sentence", "문장 입력"],
];

export const HANGUL_GROUPS = [
  "hangul_vertical_no_final",
  "hangul_vertical_with_final",
  "hangul_horizontal_top_no_final",
  "hangul_horizontal_top_with_final",
  "hangul_horizontal_bottom_no_final",
  "hangul_horizontal_bottom_with_final",
  "hangul_horizontal_flat_no_final",
  "hangul_horizontal_flat_with_final",
  "hangul_mixed_top_no_final",
  "hangul_mixed_top_with_final",
  "hangul_mixed_bottom_no_final",
  "hangul_mixed_bottom_with_final",
  "hangul_mixed_flat_no_final",
  "hangul_mixed_flat_with_final",
];

export const BASIC_LATIN_CHARS = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789.,:;!?'\"`^-_+=*/\\|()[]{}<>@#$%&~";
