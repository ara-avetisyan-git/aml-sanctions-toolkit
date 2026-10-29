from pathlib import Path

import pytest

from sanctions_toolkit.un_loader import parse_file

DATA = Path(__file__).parent / "data"


def test_parse_counts_and_metadata():
    parsed = parse_file(DATA / "sample_old.xml")
    assert parsed.date_generated.startswith("2026-10-01")
    assert len(parsed.parties) == 4
    assert {p.party_type for p in parsed.parties} == {"individual", "entity"}


def test_individual_fields():
    parsed = parse_file(DATA / "sample_old.xml")
    ivan = next(p for p in parsed.parties if p.reference_number == "TEST.001")
    assert ivan.name == "IVAN IVANOVICH TESTOV"
    assert ivan.aliases == ("Vanya Testoff",)
    assert ivan.original_script_name == "Иван Иванович Тестов"
    assert ivan.dates_of_birth == ("1970-05-04",)
    assert ivan.nationalities == ("Testland",)


def test_date_of_birth_variants():
    parsed = {p.reference_number: p for p in parse_file(DATA / "sample_old.xml").parties}
    assert parsed["TEST.002"].dates_of_birth == ("1980",)
    assert parsed["TEST.003"].dates_of_birth == ("1972-1975",)


def test_rejects_non_un_xml(tmp_path):
    bad = tmp_path / "bad.xml"
    bad.write_text("<html><body/></html>", encoding="utf-8")
    with pytest.raises(ValueError):
        parse_file(bad)
