"""Download and parse the UN Security Council Consolidated List (XML)."""
from __future__ import annotations

import tempfile
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from xml.etree.ElementTree import Element

from defusedxml import ElementTree as ET  # hardened against XML bombs / XXE

from .models import SanctionedParty

UN_CONSOLIDATED_URL = "https://scsanctions.un.org/resources/xml/en/consolidated.xml"


@dataclass(frozen=True)
class ParsedList:
    date_generated: str
    parties: tuple[SanctionedParty, ...]


def _text(el: Element, tag: str) -> str:
    child = el.find(tag)
    if child is None or child.text is None:
        return ""
    return child.text.strip()


def _values(el: Element, tag: str) -> tuple[str, ...]:
    """Collect text of <TAG><VALUE>..</VALUE></TAG> (or plain <TAG>..</TAG>) children."""
    out: list[str] = []
    for node in el.findall(tag):
        vals = [(v.text or "").strip() for v in node.findall("VALUE")]
        if not vals:
            vals = [(node.text or "").strip()]
        out.extend(v for v in vals if v)
    return tuple(dict.fromkeys(out))  # de-duplicate, keep order


def _aliases(el: Element, tag: str) -> tuple[str, ...]:
    names = (_text(a, "ALIAS_NAME") for a in el.findall(tag))
    return tuple(dict.fromkeys(n for n in names if n))


def _dates_of_birth(el: Element) -> tuple[str, ...]:
    out: list[str] = []
    for dob in el.findall("INDIVIDUAL_DATE_OF_BIRTH"):
        exact = _text(dob, "DATE")
        year = _text(dob, "YEAR")
        start, end = _text(dob, "FROM_YEAR"), _text(dob, "TO_YEAR")
        if exact:
            out.append(exact)
        elif year:
            out.append(year)
        elif start and end:
            out.append(f"{start}-{end}")
    return tuple(dict.fromkeys(out))


def _parse_individual(el: Element) -> SanctionedParty:
    parts = [_text(el, f) for f in ("FIRST_NAME", "SECOND_NAME", "THIRD_NAME", "FOURTH_NAME")]
    return SanctionedParty(
        reference_number=_text(el, "REFERENCE_NUMBER"),
        data_id=_text(el, "DATAID"),
        party_type="individual",
        name=" ".join(p for p in parts if p),
        aliases=_aliases(el, "INDIVIDUAL_ALIAS"),
        original_script_name=_text(el, "NAME_ORIGINAL_SCRIPT"),
        dates_of_birth=_dates_of_birth(el),
        nationalities=_values(el, "NATIONALITY"),
        list_type=_text(el, "UN_LIST_TYPE"),
        listed_on=_text(el, "LISTED_ON"),
        last_updated=_values(el, "LAST_DAY_UPDATED"),
        comments=_text(el, "COMMENTS1"),
    )


def _parse_entity(el: Element) -> SanctionedParty:
    return SanctionedParty(
        reference_number=_text(el, "REFERENCE_NUMBER"),
        data_id=_text(el, "DATAID"),
        party_type="entity",
        name=_text(el, "FIRST_NAME"),
        aliases=_aliases(el, "ENTITY_ALIAS"),
        original_script_name=_text(el, "NAME_ORIGINAL_SCRIPT"),
        list_type=_text(el, "UN_LIST_TYPE"),
        listed_on=_text(el, "LISTED_ON"),
        last_updated=_values(el, "LAST_DAY_UPDATED"),
        comments=_text(el, "COMMENTS1"),
    )


def parse_file(path: str | Path) -> ParsedList:
    """Parse a consolidated.xml file into normalized records."""
    root = ET.parse(str(path)).getroot()
    if root.tag != "CONSOLIDATED_LIST":
        raise ValueError(f"Unexpected root element <{root.tag}>; not a UN consolidated list.")
    parties = [_parse_individual(e) for e in root.findall("INDIVIDUALS/INDIVIDUAL")]
    parties += [_parse_entity(e) for e in root.findall("ENTITIES/ENTITY")]
    return ParsedList(date_generated=root.get("dateGenerated", ""), parties=tuple(parties))


def download(out_dir: str | Path = "data/raw", url: str = UN_CONSOLIDATED_URL, timeout: int = 60) -> Path:
    """Download the list, validate it parses, and save as consolidated_<date>.xml."""
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    request = urllib.request.Request(url, headers={"User-Agent": "sanctions-toolkit/0.1"})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        payload = response.read()
    with tempfile.NamedTemporaryFile(delete=False, suffix=".xml", dir=out_dir) as tmp:
        tmp.write(payload)
        tmp_path = Path(tmp.name)
    try:
        parsed = parse_file(tmp_path)  # refuse to keep anything that is not a valid list
    except Exception:
        tmp_path.unlink(missing_ok=True)
        raise
    stamp = (parsed.date_generated or datetime.now(timezone.utc).isoformat())[:10]
    target = out_dir / f"consolidated_{stamp}.xml"
    tmp_path.replace(target)
    return target
