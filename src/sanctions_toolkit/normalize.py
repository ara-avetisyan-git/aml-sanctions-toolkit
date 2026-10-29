"""Name normalization: transliteration, accent stripping, variant folding."""
from __future__ import annotations

import re
import unicodedata

# Simplified Eastern Armenian -> Latin (readable, not a strict ISO 9985 scheme).
_ARMENIAN = {
    "ա": "a", "բ": "b", "գ": "g", "դ": "d", "ե": "e", "զ": "z", "է": "e",
    "ը": "y", "թ": "t", "ժ": "zh", "ի": "i", "լ": "l", "խ": "kh", "ծ": "ts",
    "կ": "k", "հ": "h", "ձ": "dz", "ղ": "gh", "ճ": "ch", "մ": "m", "յ": "y",
    "ն": "n", "շ": "sh", "ո": "o", "չ": "ch", "պ": "p", "ջ": "j", "ռ": "r",
    "ս": "s", "վ": "v", "տ": "t", "ր": "r", "ց": "ts", "ւ": "v", "փ": "p",
    "ք": "k", "օ": "o", "ֆ": "f", "և": "ev",
}

# Russian / Ukrainian Cyrillic -> Latin (BGN/PCGN-like, simplified).
_CYRILLIC = {
    "а": "a", "б": "b", "в": "v", "г": "g", "д": "d", "е": "e", "ё": "e",
    "ж": "zh", "з": "z", "и": "i", "й": "y", "к": "k", "л": "l", "м": "m",
    "н": "n", "о": "o", "п": "p", "р": "r", "с": "s", "т": "t", "у": "u",
    "ф": "f", "х": "kh", "ц": "ts", "ч": "ch", "ш": "sh", "щ": "shch",
    "ъ": "", "ы": "y", "ь": "", "э": "e", "ю": "yu", "я": "ya",
    "і": "i", "ї": "yi", "є": "ye", "ґ": "g",
}

_TRANSLIT = {**_ARMENIAN, **_CYRILLIC}

_SPECIAL = {"ß": "ss", "ø": "o", "æ": "ae", "đ": "d", "ł": "l", "ı": "i"}

# Common spelling variants folded to one canonical token. Extend as needed.
VARIANTS = {
    "mohammed": "muhammad",
    "mohamed": "muhammad",
    "mohammad": "muhammad",
    "muhammed": "muhammad",
    "mahammad": "muhammad",
}

# Particles that are often written, joined or omitted inconsistently.
PARTICLES = {"al", "el"}


def transliterate(text: str) -> str:
    """Lowercase and transliterate Armenian and Cyrillic characters to Latin."""
    text = text.lower().replace("ու", "u").replace("եւ", "ev")
    return "".join(_TRANSLIT.get(ch, ch) for ch in text)


def _strip_accents(text: str) -> str:
    text = "".join(_SPECIAL.get(ch, ch) for ch in text)
    decomposed = unicodedata.normalize("NFKD", text)
    return "".join(ch for ch in decomposed if not unicodedata.combining(ch))


def normalize_name(name: str) -> str:
    """Canonical comparison form of a person or company name.

    Returns an empty string when nothing screenable is left
    (e.g. a name written only in a script that is not transliterated).
    """
    text = unicodedata.normalize("NFKC", name or "")
    text = _strip_accents(transliterate(text))
    text = re.sub(r"[^a-z0-9]+", " ", text)
    tokens = [VARIANTS.get(tok, tok) for tok in text.split()]
    tokens = [tok for tok in tokens if tok not in PARTICLES]
    return " ".join(tokens)


_YEAR_RE = re.compile(r"(?<!\d)(1[89]\d{2}|20\d{2})(?!\d)")
_RANGE_RE = re.compile(r"^\s*(\d{4})\s*-\s*(\d{4})\s*$")


def extract_years(value: str) -> set[int]:
    """Extract birth year(s) from '1970-05-04', '04.05.1970', '1970' or '1970-1975'."""
    if not value:
        return set()
    rng = _RANGE_RE.match(value)
    if rng:
        start, end = int(rng.group(1)), int(rng.group(2))
        if start <= end and end - start <= 30:
            return set(range(start, end + 1))
    return {int(y) for y in _YEAR_RE.findall(value)}
