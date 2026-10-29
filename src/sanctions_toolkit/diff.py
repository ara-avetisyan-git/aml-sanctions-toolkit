"""Compare two versions of the list: what was added, removed or changed."""
from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path

from .models import SanctionedParty

COMPARED_FIELDS = (
    "name",
    "aliases",
    "original_script_name",
    "dates_of_birth",
    "nationalities",
    "list_type",
    "comments",
)


@dataclass(frozen=True)
class FieldChange:
    field: str
    old: str
    new: str


@dataclass(frozen=True)
class ChangedParty:
    old: SanctionedParty
    new: SanctionedParty
    changes: tuple[FieldChange, ...]


@dataclass(frozen=True)
class DiffResult:
    added: tuple[SanctionedParty, ...]
    removed: tuple[SanctionedParty, ...]
    changed: tuple[ChangedParty, ...]


def _comparable(party: SanctionedParty, field: str):
    value = getattr(party, field)
    return tuple(sorted(value)) if isinstance(value, tuple) else value


def _fmt(value) -> str:
    return " | ".join(value) if isinstance(value, tuple) else str(value)


def diff_lists(old: list[SanctionedParty], new: list[SanctionedParty]) -> DiffResult:
    old_by_key = {p.key: p for p in old}
    new_by_key = {p.key: p for p in new}

    added = tuple(new_by_key[k] for k in sorted(new_by_key.keys() - old_by_key.keys()))
    removed = tuple(old_by_key[k] for k in sorted(old_by_key.keys() - new_by_key.keys()))

    changed: list[ChangedParty] = []
    for key in sorted(old_by_key.keys() & new_by_key.keys()):
        before, after = old_by_key[key], new_by_key[key]
        changes = tuple(
            FieldChange(f, _fmt(_comparable(before, f)), _fmt(_comparable(after, f)))
            for f in COMPARED_FIELDS
            if _comparable(before, f) != _comparable(after, f)
        )
        if changes:
            changed.append(ChangedParty(before, after, changes))
    return DiffResult(added, removed, tuple(changed))


def _cell(value) -> str:
    return str(value).replace("|", "\\|").replace("\n", " ")


def to_markdown(result: DiffResult, old_label: str = "old", new_label: str = "new") -> str:
    lines = [
        "# UN Consolidated List: change report",
        "",
        f"Compared **{old_label}** -> **{new_label}**",
        "",
        f"- Added: **{len(result.added)}**",
        f"- Removed: **{len(result.removed)}**",
        f"- Changed: **{len(result.changed)}**",
        "",
    ]
    for title, parties in (("Added", result.added), ("Removed", result.removed)):
        lines += [f"## {title}", ""]
        if not parties:
            lines += ["_None_", ""]
            continue
        lines += ["| Reference | Name | Type | Regime | Listed on |", "|---|---|---|---|---|"]
        for p in parties:
            lines.append(
                f"| {_cell(p.key)} | {_cell(p.name)} | {p.party_type} | {_cell(p.list_type)} | {_cell(p.listed_on)} |"
            )
        lines.append("")
    lines += ["## Changed", ""]
    if not result.changed:
        lines += ["_None_", ""]
    else:
        lines += ["| Reference | Name | Field | Before | After |", "|---|---|---|---|---|"]
        for item in result.changed:
            for ch in item.changes:
                lines.append(
                    f"| {_cell(item.new.key)} | {_cell(item.new.name)} | {ch.field} | {_cell(ch.old)} | {_cell(ch.new)} |"
                )
        lines.append("")
    return "\n".join(lines)


def write_csv(result: DiffResult, path: str | Path) -> None:
    with open(path, "w", newline="", encoding="utf-8-sig") as fh:
        writer = csv.writer(fh)
        writer.writerow(["change", "reference_number", "name", "party_type", "field", "before", "after"])
        for p in result.added:
            writer.writerow(["added", p.key, p.name, p.party_type, "", "", ""])
        for p in result.removed:
            writer.writerow(["removed", p.key, p.name, p.party_type, "", "", ""])
        for item in result.changed:
            for ch in item.changes:
                writer.writerow(["changed", item.new.key, item.new.name, item.new.party_type, ch.field, ch.old, ch.new])
