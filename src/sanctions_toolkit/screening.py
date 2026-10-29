"""Fuzzy name screening of a customer file against the UN list.

Decision logic is deliberately simple and explainable (see docs/METHODOLOGY.md).
"""
from __future__ import annotations

import csv
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from rapidfuzz import fuzz, process

from .models import SanctionedParty
from .normalize import extract_years, normalize_name

CLEAR = "CLEAR"
REVIEW = "REVIEW"
POTENTIAL_MATCH = "POTENTIAL MATCH"

# A subset match (e.g. customer omits a middle name) is a real signal, but weaker
# than a full-name match, so it is capped below 100.
SET_MATCH_FACTOR = 0.95

FIELDNAMES = [
    "customer_id", "customer_name", "customer_dob", "status", "name_score",
    "matched_name", "matched_name_kind", "dob_check", "un_reference",
    "party_type", "regime", "listed_on", "list_version",
]


@dataclass(frozen=True)
class Customer:
    customer_id: str
    name: str
    date_of_birth: str = ""


def name_score(a: str, b: str) -> float:
    """Similarity of two normalized names, 0-100."""
    ta, tb = a.split(), b.split()
    score = float(fuzz.token_sort_ratio(a, b))
    if min(len(ta), len(tb)) >= 2:  # never let a single common token drive a subset match
        score = max(score, fuzz.token_set_ratio(a, b) * SET_MATCH_FACTOR)
    return score


def dob_check(customer_dob: str, party: SanctionedParty) -> str:
    """'match' | 'mismatch' | 'n/a' (year-level comparison; UN dates are often partial)."""
    customer_years = extract_years(customer_dob)
    party_years: set[int] = set()
    for value in party.dates_of_birth:
        party_years |= extract_years(value)
    if not customer_years or not party_years:
        return "n/a"
    return "match" if customer_years & party_years else "mismatch"


def decide(score: float, dob: str, review_threshold: float, match_threshold: float) -> str:
    if score >= match_threshold:
        status = POTENTIAL_MATCH
    elif score >= review_threshold:
        status = REVIEW
    else:
        return CLEAR
    if status == REVIEW and dob == "match":
        status = POTENTIAL_MATCH  # corroborated by date of birth
    elif status == POTENTIAL_MATCH and dob == "mismatch":
        status = REVIEW  # never auto-clear: UN dates of birth can be approximate
    return status


class ScreeningIndex:
    """All screenable names (primary, original script, aliases) in normalized form."""

    def __init__(self, parties: Iterable[SanctionedParty]):
        self.parties = list(parties)
        self.choices: list[str] = []
        self.owners: list[int] = []
        self.kinds: list[str] = []
        seen: set[tuple[int, str]] = set()
        for idx, party in enumerate(self.parties):
            for raw, kind in party.all_names():
                norm = normalize_name(raw)
                if not norm or (idx, norm) in seen:
                    continue
                seen.add((idx, norm))
                self.choices.append(norm)
                self.owners.append(idx)
                self.kinds.append(kind)

    def _candidates(self, query: str, cutoff: float, limit: int = 40) -> set[int]:
        scorers = [fuzz.token_sort_ratio]
        if len(query.split()) >= 2:
            scorers.append(fuzz.token_set_ratio)
        found: set[int] = set()
        for scorer in scorers:
            for _, _, idx in process.extract(query, self.choices, scorer=scorer, score_cutoff=cutoff, limit=limit):
                found.add(idx)
        return found

    def best_matches(self, name: str, min_score: float, top_n: int = 3) -> list[tuple[float, int, int]]:
        """Return up to top_n (score, party_index, choice_index), best name per party."""
        query = normalize_name(name)
        if not query:
            return []
        best: dict[int, tuple[float, int]] = {}
        for choice_idx in self._candidates(query, cutoff=max(min_score - 10, 0)):
            score = name_score(query, self.choices[choice_idx])
            if score < min_score:
                continue
            owner = self.owners[choice_idx]
            if owner not in best or score > best[owner][0]:
                best[owner] = (score, choice_idx)
        ranked = sorted(((s, o, c) for o, (s, c) in best.items()), key=lambda t: -t[0])
        return ranked[:top_n]


def screen_customers(
    customers: Iterable[Customer],
    parties: Iterable[SanctionedParty],
    list_version: str = "",
    review_threshold: float = 80.0,
    match_threshold: float = 90.0,
    top_n: int = 3,
) -> list[dict]:
    """Screen customers; returns one row per hit, or one CLEAR row per customer without hits."""
    index = ScreeningIndex(parties)
    rows: list[dict] = []
    for customer in customers:
        hits = index.best_matches(customer.name, min_score=review_threshold, top_n=top_n)
        base = {
            "customer_id": customer.customer_id,
            "customer_name": customer.name,
            "customer_dob": customer.date_of_birth,
            "list_version": list_version,
        }
        if not hits:
            rows.append({**base, "status": CLEAR, "name_score": "", "matched_name": "",
                         "matched_name_kind": "", "dob_check": "n/a", "un_reference": "",
                         "party_type": "", "regime": "", "listed_on": ""})
            continue
        for score, party_idx, choice_idx in hits:
            party = index.parties[party_idx]
            dob = dob_check(customer.date_of_birth, party)
            rows.append({
                **base,
                "status": decide(score, dob, review_threshold, match_threshold),
                "name_score": round(score, 1),
                "matched_name": index.choices[choice_idx],
                "matched_name_kind": index.kinds[choice_idx],
                "dob_check": dob,
                "un_reference": party.key,
                "party_type": party.party_type,
                "regime": party.list_type,
                "listed_on": party.listed_on,
            })
    return rows


def read_customers(path: str | Path) -> list[Customer]:
    """CSV with columns: customer_id, name, [date_of_birth]."""
    with open(path, newline="", encoding="utf-8-sig") as fh:
        reader = csv.DictReader(fh)
        missing = {"customer_id", "name"} - set(reader.fieldnames or [])
        if missing:
            raise ValueError(f"Customer file is missing columns: {', '.join(sorted(missing))}")
        return [
            Customer(row["customer_id"].strip(), row["name"].strip(), (row.get("date_of_birth") or "").strip())
            for row in reader
        ]


def write_results(rows: list[dict], path: str | Path) -> None:
    with open(path, "w", newline="", encoding="utf-8-sig") as fh:
        writer = csv.DictWriter(fh, fieldnames=FIELDNAMES)
        writer.writeheader()
        writer.writerows(rows)


def summarize(rows: list[dict]) -> Counter:
    """Count customers by their worst status."""
    rank = {CLEAR: 0, REVIEW: 1, POTENTIAL_MATCH: 2}
    worst: dict[str, str] = {}
    for row in rows:
        cid = row["customer_id"]
        if cid not in worst or rank[row["status"]] > rank[worst[cid]]:
            worst[cid] = row["status"]
    return Counter(worst.values())
