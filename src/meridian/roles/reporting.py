"""A reporting plugin's common part (spec/plugin-pages-follow-their-role,
"reporting, a reporting plugin").

**First-use path.** Choose its settings (Settings); have it entitled to the
data it reads (a deployment admin, on Data sources); grant people read (a
deployment admin, access); read its reports (its report pages).

**Settings:** `reporting_currency()` ("Reporting currency"): every reporting
plugin values what the firm holds, so in a currency.

**Pages.** Manage: Datasets (`read_datasets`): each dataset it reads,
whether it is entitled to it and to which fields, and the misses; "Not
entitled yet" until a deployment admin entitles it on Data sources
(`meridian/roles/reporting/datasets.html`). Open and View: the plugin's
reports, its main report first -- its whole value, and the leeway.

**Figures:** "Last valued" and "Not priced" (`figures(...)`).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from ..client import Setting
from ..figures import Figure
from ._figures import Value, ordered

__all__ = ["DatasetRead", "DatasetsRead", "figures", "reporting_currency"]


def reporting_currency(
    *, default: str = "USD", description: str = "", roles: tuple[str, ...] = ()
) -> Any:
    """ "Reporting currency": what the plugin values every account in, an ISO
    4217 code, resolved by its code (contract v19)."""
    return Setting(
        "reporting_currency",
        str,
        label="Reporting currency",
        default=default,
        description=description
        or "The currency the reports value every account in: an ISO 4217 code.",
        roles=roles,
    )


@dataclass(frozen=True)
class DatasetRead:
    """One dataset it reads: whether it is entitled to it, to which fields
    (none: every field), and how many reads it missed."""

    dataset: str
    entitled: bool = False
    fields: list[str] = field(default_factory=list)
    misses: int = 0


@dataclass(frozen=True)
class DatasetsRead:
    """Datasets' common fields (`read_datasets`'s answer)."""

    datasets: list[DatasetRead] = field(default_factory=list)


def _not_priced(value: Any) -> str | None:
    return "warn" if isinstance(value, int) and value > 0 else None


def figures(*, last_valued: Value, not_priced: Value = None) -> list[Figure]:
    """The reporting role's figures, in its order: "Last valued" (a time,
    error with why when the last valuation failed) and "Not priced"
    (positions valued without a price, warn when any)."""
    return ordered(
        [("Last valued", last_valued, None), ("Not priced", not_priced, _not_priced)]
    )
