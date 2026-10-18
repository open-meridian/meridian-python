"""open-meridian 0.29.0 to 0.30.0: each role's common logic in the SDK.

A module a plugin kept byte for byte with its sibling says so in its
docstring -- "The same module in <one> and <other>" -- and is one of a
known few: market.py, products.py, contracts.py, raw.py and dgm.py (the
middle layer of Coinbase's and Kraken's plugins, and of Kalshi's and the
international Polymarket's). Each is rewritten whole into a re-export of the
SDK's names that replace it, so every import of it still resolves and the
plugin's own tests still pass:

- market.py: the venue's reading from `meridian.roles.data`, its values from
  `meridian.roles.data.pairs` (a module defining `Listed`) or
  `.event_contracts` (one defining `Contract` and `Cash`);
- products.py, contracts.py: the map from the kind's module;
- raw.py: `meridian.edge.RawStore` held to the module's own kind, its label
  and window kept, and its `tend` and `storage_root`;
- dgm.py: its `Dgm` the kind's `Feed` -- a pairs plugin's streaming through
  its own stream.py -- beside the names other modules import from it.

The connectivity layer Alpaca's and Tradier's plugins each kept (their
trading.py, in SnapTrade 0.16.0's shape) is recognised by its definitions
alone -- `class Trader`, `class Noted`, `class Venue(Protocol)`, `class
Watched` and `def trading_files` in one module -- and rewritten into a
re-export of `meridian.roles.connectivity`, its market zone and price places
kept: its `Trader` the SDK's in that zone, `Noted` the SDK's `Sent`, and
`fill_price` and `trade_date_of` as it had them.

What is recognised is the marker or the module's own definitions, never a
name alone, so a plugin's own module that shares a file name is left as it
is. Everything else -- importing from the SDK directly, the copied pages and
tests, the Makefile's suite-same, a copied stream.py, and the Trading page
and test rig a trading layer kept -- is left by hand. migration.toml, beside
this, records the rules.
"""

from __future__ import annotations

import re
import textwrap

from .. import Finding, Rewritten

#: The copied layer's own words for itself, module or test.
MARKER = re.compile(r"The same (module|file) in (\S+) and (\S+?)[\s.(]")
_SRC = re.compile(r"^src/[A-Za-z_][A-Za-z0-9_]*/([a-z_]+)\.py$")
_TEST = re.compile(r"^tests/(test_suite|test_dgm|test_page|test_raw|conftest)\.py$")

#: What a module this migration rewrote says first.
_MOVED = "Moved into the SDK (open-meridian 0.30.0)"
#: What a trading layer this migration rewrote says first.
_TRADER_MOVED = "Moved into the SDK (open-meridian 0.30.0): the connectivity role's work"
#: Whether the plugin copied a middle layer, read once from all its files.
_copied = False
#: Whether the plugin kept a trading layer, or had it rewritten.
_traded = False


def given(files: dict[str, str]) -> None:
    global _copied, _traded
    _copied = any(
        _SRC.match(path)
        and (MARKER.search(text) or (_MOVED in text and _TRADER_MOVED not in text))
        for path, text in files.items()
    )
    _traded = any(
        _SRC.match(path) and (_is_trader(text) or _TRADER_MOVED in text)
        for path, text in files.items()
    )


def _defines(text: str, *names: str) -> bool:
    return all(re.search(rf"^(class|def) {name}\b|^{name} = ", text, re.M) for name in names)


def _constant(text: str, name: str, otherwise: str) -> str:
    found = re.search(rf"^{name} = (.+)$", text, re.M)
    return found.group(1).strip() if found else otherwise


def _head(what: str, rule: str = "re-export-left") -> str:
    """A rewritten module's docstring: where its names went, and what to do."""
    said = (
        f"Moved into the SDK (open-meridian 0.30.0): {what}. This module only forwards to "
        "it, so every import of it still resolves; import from the SDK where it is used, "
        f"then delete this module (`meridian plugin migrate`, {rule})."
    )
    return '"""' + textwrap.fill(said, width=76) + '"""\n\n'


_READING = (
    "from meridian.roles.data import NANOS_PER_DAY as NANOS_PER_DAY\n"
    "from meridian.roles.data import NANOS_PER_SECOND as NANOS_PER_SECOND\n"
    "from meridian.roles.data import SECONDS_PER_DAY as SECONDS_PER_DAY\n"
    "from meridian.roles.data import Endpoint as Endpoint\n"
    "from meridian.roles.data import Health as Health\n"
    "from meridian.roles.data import Limits as Limits\n"
    "from meridian.roles.data import Session as Session\n"
    "from meridian.roles.data import Unread as Unread\n"
    "from meridian.roles.data import day_start as day_start\n"
    "from meridian.roles.data import json_decimal as json_decimal\n"
    "from meridian.roles.data import number as number\n"
    "from meridian.roles.data import utc_day as utc_day\n"
)


def _names(module: str, names: tuple[str, ...]) -> str:
    return "".join(f"from {module} import {name} as {name}\n" for name in names)


_PAIRS_VALUES = (
    "MAKER",
    "TAKER",
    "Asset",
    "Candle",
    "Listed",
    "Market",
    "Print",
    "Tick",
    "Top",
)
_CONTRACT_VALUES = (
    "DETERMINED", "DISPUTED", "FINAL", "PROPOSED", "Cash", "Contract", "Market", "Resolution",
    "Tick", "Top",
)  # fmt: skip
_ROLE = ("Counts", "Heard", "Standing", "Venue", "cancelled")
_PAIRS_WORK = (
    "BAR", "DAILY", "DAILY_EVERY_SECONDS", "EVERY", "LATEST_DAYS", "LIVE", "LIVE_EVERY_SECONDS",
    "PRICE", "QUOTE", "REMAP_SECONDS", "TRADE", "TRADES",
)  # fmt: skip
_CONTRACT_WORK = (
    "LIVE", "MOST_DESCRIPTION", "NOT_A_CONTRACT", "NOT_READ", "OUTCOME_EVERY_SECONDS",
    "OUTCOMES", "PAYOUT_DIFFERS", "PRICE", "QUOTE", "REREAD_SECONDS",
)  # fmt: skip


def _market(text: str) -> str | None:
    if _defines(text, "Listed", "Candle"):
        return (
            _head(
                "a pairs venue's values are meridian.roles.data.pairs's, and its reading "
                "meridian.roles.data's"
            )
            + _READING
            + _names("meridian.roles.data.pairs", _PAIRS_VALUES)
        )
    if _defines(text, "Contract", "Cash"):
        return (
            _head(
                "an event-contract venue's values are meridian.roles.data.event_contracts's, "
                "and its reading meridian.roles.data's"
            )
            + _READING
            + _names("meridian.roles.data.event_contracts", _CONTRACT_VALUES)
        )
    return None


def _raw(text: str) -> str | None:
    if not _defines(text, "RawStore"):
        return None
    kind = _constant(text, "KIND", '"responses"')
    label = _constant(text, "LABEL", '"Raw responses"')
    window = _constant(text, "WINDOW_DAYS", "30")
    head = _head("raw records as files are meridian.edge.RawStore")
    return (
        head
        + f'''from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import Any

from meridian.edge import RawStore as _RawStore
from meridian.edge import StoredUnit as Unit
from meridian.edge import storage_root as _storage_root

KIND = {kind}
LABEL = {label}
WINDOW_DAYS = {window}

__all__ = ["KIND", "LABEL", "WINDOW_DAYS", "RawStore", "Unit", "storage_root", "tend"]


class RawStore(_RawStore):
    """meridian.edge.RawStore, holding this plugin's one kind."""

    def __init__(self, root: Path) -> None:
        super().__init__(root, KIND)


def storage_root() -> Path:
    return _storage_root("meridian-data-")


async def tend(plugin: Any, store: _RawStore, window_days: int, past: str, today: date) -> None:
    await store.tend(plugin, window_days, past, today)
'''
    )


def _dgm(text: str) -> str | None:
    if "ProductMap" in text and _defines(text, "Dgm"):
        streams = "from .stream import" in text
        head = _head("a pairs venue's work is meridian.roles.data.pairs.Feed")
        body = "from __future__ import annotations\n\n"
        if streams:
            body += "from dataclasses import dataclass\n\n"
        body += _names("meridian.roles.data", _ROLE)
        body += _names("meridian.roles.data.pairs", _PAIRS_WORK)
        body += "from meridian.roles.data.pairs import Feed as Feed\n"
        if streams:
            body += (
                "from meridian.roles.data.pairs import StreamFactory\n\n"
                "from .stream import Stream\n\n\n"
                "@dataclass\n"
                "class Dgm(Feed):\n"
                '    """The SDK\'s Feed, streaming through this plugin\'s own stream."""\n\n'
                "    stream_factory: StreamFactory | None = Stream\n"
            )
        else:
            body += "\nDgm = Feed\n"
        return head + body
    if "ContractMap" in text and _defines(text, "Dgm"):
        head = _head(
            "an event-contract venue's work is meridian.roles.data.event_contracts.Feed"
        )
        return (
            head
            + _names("meridian.roles.data", _ROLE)
            + _names("meridian.roles.data.event_contracts", _CONTRACT_WORK)
            + "from meridian.roles.data.event_contracts import Feed as Feed\n\n"
            + "Dgm = Feed\n"
        )
    return None


def _map(text: str) -> str | None:
    if _defines(text, "ProductMap"):
        return _head("the product map is meridian.roles.data.pairs's") + _names(
            "meridian.roles.data.pairs", ("Mapped", "ProductMap")
        )
    if _defines(text, "ContractMap"):
        return _head("the contract map is meridian.roles.data.event_contracts's") + _names(
            "meridian.roles.data.event_contracts", ("ContractMap", "Mapped", "Recorded")
        )
    return None


def _is_trader(text: str) -> bool:
    """A trading layer in SnapTrade 0.16.0's shape, by its own definitions."""
    return _defines(text, "Trader", "Noted", "Watched", "trading_files") and bool(
        re.search(r"^class Venue\(Protocol\):", text, re.M)
    )


_ZONE = re.compile(r'^MARKET_ZONE = ZoneInfo\("([^"]+)"\)$', re.M)
_CONNECTIVITY = (
    "CANCELLED", "DONE_FOR_DAY", "EXPIRED", "FILLED", "REJECTED", "REPLACED", "SUSPENDED",
    "WORKING", "Asked", "Catalogue", "Change", "Fill", "Originated", "Sent", "Shown", "Venue",
    "VenueOrder", "VenueRefused", "VenueUnanswered", "Watched", "Worked", "basis_of", "bust_id",
    "execution_id", "filled_in_book", "moment", "number", "symbol_of", "trading_files",
)  # fmt: skip


def _trader(text: str) -> str | None:
    zone = _ZONE.search(text)
    if zone is None or not _is_trader(text):
        return None
    places = _constant(text, "PRICE_PLACES", "8")
    head = _head(
        "the connectivity role's work is meridian.roles.connectivity's, its Trader in "
        "this plugin's market zone",
        "trader-re-export-left",
    )
    return (
        head
        + """from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Any
from zoneinfo import ZoneInfo

from meridian.roles import connectivity as _connectivity
"""
        + _names("meridian.roles.connectivity", _CONNECTIVITY)
        + f'''
#: The places a fill's price worked out from two averages is rounded to.
PRICE_PLACES = {places}
#: The listing market's day a fill's trade date is in.
MARKET_ZONE = ZoneInfo("{zone.group(1)}")

Noted = Sent


def fill_price(
    before: Decimal, average_before: Decimal | None, after: Decimal, average_after: Decimal
) -> tuple[Decimal, bool]:
    return _connectivity.fill_price(before, average_before, after, average_after, PRICE_PLACES)


def trade_date_of(at: datetime) -> date:
    return at.astimezone(MARKET_ZONE).date()


class Trader(_connectivity.Trader):
    """meridian.roles.connectivity.Trader, in this plugin's market zone."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        kwargs.setdefault("market_zone", MARKET_ZONE)
        kwargs.setdefault("price_places", PRICE_PLACES)
        super().__init__(*args, **kwargs)
'''
    )


_REWRITERS = {"market": _market, "raw": _raw, "dgm": _dgm, "products": _map, "contracts": _map}


def rewrite(path: str, text: str) -> Rewritten:
    matched = _SRC.match(path)
    if matched is not None and not MARKER.search(text):
        traded = _trader(text)
        if traded is not None:
            return Rewritten(traded, ("copied-trader-onto-sdk",))
    if matched is None or not MARKER.search(text):
        return Rewritten(text)
    rewriter = _REWRITERS.get(matched.group(1))
    replaced = rewriter(text) if rewriter else None
    if replaced is None:
        return Rewritten(text)
    return Rewritten(replaced, ("copied-module-onto-sdk",))


_CONNECT = re.compile(r"\.stream\.connect\s*=[^=]")


def left(path: str, text: str) -> list[Finding]:
    if path == "pyproject.toml":
        return [Finding("suite-same-retired", path, 0, "")] if _copied else []
    found: list[Finding] = []
    if _copied and path.endswith(".py"):
        for number, line in enumerate(text.splitlines(), 1):
            if _CONNECT.search(line):
                found.append(Finding("stream-connect-assigned", path, number, line.strip()))
    return found + _copies(path, text) + _trading(path, text)


#: A trading layer's page records, and the test rig it kept.
_TRADING_READ = re.compile(r"^class (TradingRead|AccountTrading)\b", re.M)
_RIG = re.compile(r"^class Rig\b", re.M)


def _trading(path: str, text: str) -> list[Finding]:
    if not _traded or not path.endswith(".py") or _TRADER_MOVED in text:
        return []
    if _SRC.match(path) and _is_trader(text):
        return [Finding("trader-by-hand", path, 1, text.splitlines()[0])]
    found = _TRADING_READ.search(text)
    if _SRC.match(path) and found is not None:
        line = text[: found.start()].count("\n") + 1
        return [Finding("trading-page-onto-sdk", path, line, text.splitlines()[line - 1])]
    rig = _RIG.search(text)
    if path.startswith("tests/") and rig is not None and "Trader(" in text:
        line = text[: rig.start()].count("\n") + 1
        return [Finding("trading-rig-onto-sdk", path, line, text.splitlines()[line - 1])]
    return []


def _copies(path: str, text: str) -> list[Finding]:
    if _TRADER_MOVED in text and path.endswith(".py"):
        return [Finding("trader-re-export-left", path, 1, text.splitlines()[0])]
    if _MOVED in text and path.endswith(".py"):
        return [Finding("re-export-left", path, 1, text.splitlines()[0])]
    found = MARKER.search(text)
    if found is None:
        return []
    line = text[: found.start()].count("\n") + 1
    said = text.splitlines()[line - 1].strip()
    matched = _SRC.match(path)
    if matched is not None and matched.group(1) == "page":
        return [Finding("copied-page", path, line, said)]
    if matched is not None and matched.group(1) == "stream":
        return [Finding("stream-is-the-plugins", path, line, said)]
    if _TEST.match(path):
        return [Finding("copied-tests", path, line, said)]
    return []
