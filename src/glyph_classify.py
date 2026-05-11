import unicodedata


def classify_glyph(ch: str) -> str:
    if len(ch) != 1:
        raise ValueError(f"classify_glyph expects one character, got {len(ch)}")

    codepoint = ord(ch)
    category = unicodedata.category(ch)

    if 0x0021 <= codepoint <= 0x007E and not ch.isalnum():
        if ch in ".,:;`'\"":
            return "punct_tiny"
        if ch in "-_~":
            return "punct_line"
        return "punct_small"
    if "0" <= ch <= "9":
        return "basic_latin_digit"
    if "A" <= ch <= "Z":
        return "basic_latin_upper"
    if "a" <= ch <= "z":
        return "basic_latin_lower"
    if 0xAC00 <= codepoint <= 0xD7A3:
        return "hangul_syllable"
    if 0x1100 <= codepoint <= 0x11FF or 0x3130 <= codepoint <= 0x318F:
        return "hangul_jamo"
    if category.startswith("P"):
        return "punctuation"
    if category.startswith("S"):
        return "symbol"
    if category.startswith("N"):
        return "number"
    if category.startswith("L"):
        return "letter"
    return "other"
