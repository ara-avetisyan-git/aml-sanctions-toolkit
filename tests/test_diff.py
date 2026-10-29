from pathlib import Path

from sanctions_toolkit.diff import diff_lists, to_markdown
from sanctions_toolkit.un_loader import parse_file

DATA = Path(__file__).parent / "data"


def _diff():
    old = parse_file(DATA / "sample_old.xml")
    new = parse_file(DATA / "sample_new.xml")
    return diff_lists(list(old.parties), list(new.parties))


def test_added_removed_changed():
    result = _diff()
    assert [p.key for p in result.added] == ["TEST.005"]
    assert [p.key for p in result.removed] == ["TEST.004"]
    assert [c.new.key for c in result.changed] == ["TEST.002"]
    assert result.changed[0].changes[0].field == "aliases"


def test_identical_lists_have_no_diff():
    old = parse_file(DATA / "sample_old.xml")
    result = diff_lists(list(old.parties), list(old.parties))
    assert not (result.added or result.removed or result.changed)


def test_markdown_report_mentions_every_change():
    report = to_markdown(_diff(), "2026-10-01", "2026-10-02")
    assert "TEST.005" in report and "TEST.004" in report and "Aramik Testian" in report
