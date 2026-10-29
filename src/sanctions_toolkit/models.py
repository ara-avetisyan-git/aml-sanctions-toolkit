from __future__ import annotations

from dataclasses import dataclass
from typing import Iterator


@dataclass(frozen=True)
class SanctionedParty:
    """One individual or entity from the UN Consolidated List (normalized)."""

    reference_number: str
    data_id: str
    party_type: str  # "individual" | "entity"
    name: str
    aliases: tuple[str, ...] = ()
    original_script_name: str = ""
    dates_of_birth: tuple[str, ...] = ()
    nationalities: tuple[str, ...] = ()
    list_type: str = ""  # sanctions regime / committee
    listed_on: str = ""
    last_updated: tuple[str, ...] = ()
    comments: str = ""

    @property
    def key(self) -> str:
        """Stable identifier used to match records between two list versions."""
        return self.reference_number or self.data_id

    def all_names(self) -> Iterator[tuple[str, str]]:
        """Yield (name, kind) for every name that should be screened against."""
        if self.name:
            yield self.name, "primary"
        if self.original_script_name:
            yield self.original_script_name, "original_script"
        for alias in self.aliases:
            yield alias, "alias"
