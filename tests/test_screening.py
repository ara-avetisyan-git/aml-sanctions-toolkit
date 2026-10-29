from pathlib import Path

from sanctions_toolkit.cli import main
from sanctions_toolkit.screening import (
    POTENTIAL_MATCH, REVIEW, CLEAR, read_customers, screen_customers, summarize, decide,
)
from sanctions_toolkit.un_loader import parse_file

DATA = Path(__file__).parent / "data"


def _status_by_customer():
    parsed = parse_file(DATA / "sample_old.xml")
    customers = read_customers(DATA / "customers.csv")
    rows = screen_customers(customers, parsed.parties, list_version=parsed.date_generated)
    best = {}
    rank = {CLEAR: 0, REVIEW: 1, POTENTIAL_MATCH: 2}
    for r in rows:
        if r["customer_id"] not in best or rank[r["status"]] > rank[best[r["customer_id"]]["status"]]:
            best[r["customer_id"]] = r
    return best


def test_missing_middle_name_is_flagged():
    assert _status_by_customer()["C001"]["status"] == POTENTIAL_MATCH


def test_cyrillic_customer_matches_original_script():
    row = _status_by_customer()["C002"]
    assert row["status"] == POTENTIAL_MATCH
    assert row["un_reference"] == "TEST.001"
    assert row["dob_check"] == "match"


def test_armenian_script_customer_matches_with_dob():
    row = _status_by_customer()["C003"]
    assert row["status"] == POTENTIAL_MATCH
    assert row["un_reference"] == "TEST.002"
    assert row["dob_check"] == "match"


def test_dob_mismatch_downgrades_to_review_not_clear():
    row = _status_by_customer()["C004"]
    assert row["dob_check"] == "mismatch"
    assert row["status"] == REVIEW


def test_unrelated_customer_is_clear():
    assert _status_by_customer()["C005"]["status"] == CLEAR


def test_spelling_variant_of_muhammad():
    assert _status_by_customer()["C006"]["status"] == POTENTIAL_MATCH


def test_decide_rules():
    assert decide(95, "n/a", 80, 90) == POTENTIAL_MATCH
    assert decide(95, "mismatch", 80, 90) == REVIEW
    assert decide(85, "match", 80, 90) == POTENTIAL_MATCH
    assert decide(85, "mismatch", 80, 90) == REVIEW
    assert decide(70, "match", 80, 90) == CLEAR


def test_cli_end_to_end(tmp_path, capsys):
    out = tmp_path / "results.csv"
    code = main(["screen", "--list", str(DATA / "sample_old.xml"),
                 "--customers", str(DATA / "customers.csv"), "--output", str(out)])
    assert code == 0 and out.exists()
    assert "Screened 7 customers" in capsys.readouterr().out
