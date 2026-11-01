"""Listed options' and futures' chains (contract v28,
sdk-contract/listed-options-and-futures-contract; rulings 559 to 561).

A chain is read under its underlying, never minted: each series is a row
whose subject is the underlying's `INS-` record and whose `series_key` is
the series' public key -- the OCC's 21-character Options Symbology
Initiative symbol (`occ_osi`, W1.26) for an option, or a future's or future
option's exchange ticker as one `ticker` identifier carrying its venue's ISO
10383 MIC in `source` (W1.26, DESIGN28's sixth amendment). A series gets an
`INS-` record only when the deployment wants it (W6.37), minted by the
platform, so a data plugin recording a chain's series, quotes and
statistics never resolves a series (`a-chain-row-is-never-resolved`).

**A data plugin** records:

- each series of an underlying it lists (`RecordSeries`), its terms as the
  `listed_option`, `future` or `future_option` template's fields
  (`option_series`, `ListedSeries`), an adjustment the next version of the
  same row key;
- each series' open interest and volume per trading date
  (`RecordStatistics`; `statistic`), contracts for an option or a future;
- its quotes and trades of a series under the underlying with the series'
  key on the envelope (`series_meta`).

**A reader** (`portfolio`, `signal`, `reporting`, and the `oms` and `ems`
for an order's leg) reads an underlying's expirations (`read_expirations`,
`ListExpirations`: each date once with its series count, from the lake's
listing alone), its series for an expiration range
(`read_chain`, `ListSeries`) and its chain's open interest for a trading
date (`read_open_interest`, `ListStatistics` with `all_series`), asking only
for what its page shows (contract v28, amended 2026-10-28; ruling 821): the
expiration window shown, the terms drawn (`paths`) and the fields shown
(`fields`, dictionary entries such as `meridian.v1.Quote.bid`). A chain's
quotes are read the same way, `list_quotes(all_series=True,
expiration_from=..., expiration_to=..., fields=[...])`, never every
expiration paged and filtered in the plugin; and a
plugin about to order a series the deployment does not hold asks for it
(`want_series`, `RequestSeriesRecords` with the cause `order`), which the
deployment admin's series request rule allows.
"""

from __future__ import annotations

import re
from collections.abc import Sequence
from datetime import date
from decimal import Decimal
from typing import Any

from ..operations import (
    ListedSeries,
    ObservationMeta,
    SeriesWant,
    Statistic,
    SubjectRef,
    TemplateFieldValue,
    UnitValue,
)
from ..plugin.v1 import operations_pb2 as ops

#: The OCC's Options Symbology Initiative symbol's scheme (W1.26, 573).
OCC_OSI = "occ_osi"

_OSI = re.compile(r"^(?P<root>[A-Z0-9 ]{6})(?P<day>\d{6})(?P<right>[CP])(?P<strike>\d{8})$")
_RIGHTS = {"C": "PUT_OR_CALL_CALL", "P": "PUT_OR_CALL_PUT", "call": "C", "put": "P"}


def osi_symbol(
    root: str, expiration: date | str, put_or_call: str, strike: Decimal | str
) -> str:
    """The 21-character OSI symbol: the root padded with spaces to 6, the
    expiration as yymmdd, C or P, and the strike times 1,000 in 8 digits.
    `put_or_call` is `call`, `put`, `C` or `P`."""
    if isinstance(expiration, str):
        expiration = date.fromisoformat(expiration)
    right = _RIGHTS.get(put_or_call.lower(), put_or_call.upper())
    if right not in ("C", "P"):
        raise ValueError(f"put_or_call is {put_or_call!r}: call or put")
    if not 1 <= len(root) <= 6:
        raise ValueError(f"root is {root!r}: 1 to 6 characters")
    thousandths = Decimal(str(strike)) * 1000
    if thousandths != thousandths.to_integral_value() or not 0 <= thousandths < 10**8:
        raise ValueError(f"strike is {strike}: at most 3 places, below 100,000")
    return f"{root.upper():<6}{expiration:%y%m%d}{right}{int(thousandths):08d}"


def osi_terms(symbol: str) -> tuple[str, date, str, Decimal]:
    """An OSI symbol's root, expiration, `C` or `P`, and strike."""
    found = _OSI.match(symbol)
    if found is None:
        raise ValueError(f"{symbol!r} is not a 21-character OSI symbol")
    day = found.group("day")
    expiration = date(2000 + int(day[:2]), int(day[2:4]), int(day[4:]))
    strike = (Decimal(found.group("strike")) / 1000).normalize()
    return found.group("root").rstrip(), expiration, found.group("right"), strike


def osi_key(symbol: str) -> list[ops.Identifier]:
    """An option series' key: its OSI symbol under `occ_osi`."""
    osi_terms(symbol)  # refused here rather than by the lake
    return [ops.Identifier(scheme=OCC_OSI, value=symbol)]


def series_meta(
    underlying_id: str,
    series_key: Sequence[ops.Identifier],
    *,
    row_key: str,
    dataset: str,
    valid_from_ns: int = 0,
    business_date: date | str = "",
    raw: ops.RawRecordRef | None = None,
    **more: Any,
) -> ObservationMeta:
    """The envelope of a chain row: the underlying as its subject and the
    series' key, never the series' own record."""
    return ObservationMeta(
        row_key=row_key[:128],
        subjects=[SubjectRef(entity_id=underlying_id)],
        series_key=tuple(series_key),
        source=ops.Source(dataset=dataset),
        valid_from_ns=valid_from_ns,
        business_date=business_date,
        raw=raw,
        **more,
    )


def option_series(
    underlying_id: str,
    symbol: str,
    *,
    template_id: str,
    template_version: str,
    dataset: str,
    currency: str,
    exercise_style: str,
    settlement_method: str,
    contract_multiplier: Decimal | int = 100,
    deliverable: Sequence[tuple[str, Decimal | int]] = (),
    settlement_time: str = "",
    valid_from_ns: int = 0,
    raw: ops.RawRecordRef | None = None,
) -> ListedSeries:
    """One option series as the `listed_option` template's fields, from its
    OSI symbol: `exercise_style` and `settlement_method` by the template's
    values (EXERCISE_STYLE_AMERICAN, SETTLEMENT_METHOD_PHYSICAL), the strike
    in `currency`, and each deliverable component an instrument and its
    quantity (100 shares of the underlying for a standard contract)."""
    root, expiration, right, strike = osi_terms(symbol)
    fields = [
        ("underlying_instrument_id", underlying_id),
        ("put_or_call", _RIGHTS[right]),
        ("strike_price", f"{strike:f} {currency}"),
        ("expiration_date", expiration.isoformat()),
        ("exercise_style", exercise_style),
        ("settlement_method", settlement_method),
        ("contract_multiplier", str(contract_multiplier)),
        ("option_root", root),
    ]
    if settlement_time:
        fields.append(("settlement_time", settlement_time))
    for n, (instrument_id, quantity) in enumerate(deliverable):
        fields.append((f"deliverable[{n}].instrument_id", instrument_id))
        fields.append((f"deliverable[{n}].quantity", str(quantity)))
    return ListedSeries(
        meta=series_meta(
            underlying_id,
            osi_key(symbol),
            row_key=symbol,
            dataset=dataset,
            valid_from_ns=valid_from_ns,
            raw=raw,
        ),  # fmt: skip
        template_id=template_id,
        template_version=template_version,
        fields=[TemplateFieldValue(path=path, value=value) for path, value in fields],
    )


#: A statistic's row key suffix, by kind.
_SUFFIX = {"open_interest": "OI", "volume": "VOL"}


def statistic(
    underlying_id: str,
    series_key: Sequence[ops.Identifier],
    kind: str,
    value: Decimal | int,
    business_date: date | str,
    *,
    dataset: str,
    unit: str = "contracts",
    valid_from_ns: int = 0,
    raw: ops.RawRecordRef | None = None,
) -> Statistic:
    """One series' statistic for a trading date -- `open_interest` or
    `volume` -- in contracts, keyed by its series and the date."""
    day = business_date if isinstance(business_date, str) else business_date.isoformat()
    key = series_key[0].value if series_key else underlying_id
    return Statistic(
        meta=series_meta(
            underlying_id,
            series_key,
            row_key=f"{key}:{day}:{_SUFFIX.get(kind, kind)}",
            dataset=dataset,
            valid_from_ns=valid_from_ns,
            business_date=day,
            raw=raw,
        ),  # fmt: skip
        kind=kind,
        value=UnitValue(value=value, unit=unit),
    )


# ── Reading a chain ──────────────────────────────────────────────────────


async def read_expirations(
    plugin: Any,
    underlying_id: str,
    expiration_from: date | str = "",
    expiration_to: date | str = "",
    *,
    instrument_type: str = "listed_option",
) -> list[ops.Expiration]:
    """An underlying's expirations of a listed type, in date order, each with
    how many series the lake's listing holds expiring then (`series_count`):
    within the range where either end is named, every expiration where none
    is (contract v28, amended 2026-10-28; rulings 856, 858 and 859).

    One call, answered from the listing without reading a series: a page
    chooses its expiration with this, then reads only that expiration's
    series (`read_chain`), never every series to keep each date once. A
    reader not entitled to the chain's dataset is named in the answer's
    `unanswered`; `plugin.list_expirations` returns the whole answer."""
    answer = await plugin.list_expirations(
        underlying_id=underlying_id,
        instrument_type=instrument_type,
        expiration_from=expiration_from,
        expiration_to=expiration_to,
    )
    return list(answer.expirations)


async def read_chain(
    plugin: Any,
    underlying_id: str,
    expiration_from: date | str,
    expiration_to: date | str = "",
    *,
    instrument_type: str = "listed_option",
    paths: Sequence[str] = (),
) -> list[ops.ListedSeries]:
    """An underlying's listed series expiring in the range (one expiration
    when `expiration_to` is left out), every page read.

    `paths` names the template paths a page draws (`put_or_call`,
    `strike_price`, `expiration_date`); none answers every term. No page size
    is asked, so the lake fills each page to about 512 KiB, the most it
    answers (rulings 816 and 823): one expiration of a large chain is one
    page."""
    rows: list[ops.ListedSeries] = []
    cursor = ""
    while True:
        page = await plugin.list_series(
            subjects=[SubjectRef(entity_id=underlying_id)],
            instrument_type=instrument_type,
            expiration_from=expiration_from,
            expiration_to=expiration_to or expiration_from,
            paths=list(paths),
            cursor=cursor,
        )
        rows.extend(page.series)
        cursor = page.next_cursor
        if not cursor:
            return rows


async def read_open_interest(
    plugin: Any,
    underlying_id: str,
    business_date: date | str = "",
    *,
    expiration_from: date | str = "",
    expiration_to: date | str = "",
    fields: Sequence[str] = (),
) -> list[ops.Statistic]:
    """The open interest of every series of an underlying's chain for a
    trading date (the latest where none is named), every page read: of the
    series expiring from `expiration_from` to `expiration_to` where either is
    named (the lake's listing says which), and only the `fields` named
    (`meridian.v1.Statistic.value`), every field where none is."""
    rows: list[ops.Statistic] = []
    cursor = ""
    while True:
        page = await plugin.list_statistics(
            subjects=[SubjectRef(entity_id=underlying_id)],
            kinds=["open_interest"],
            business_date=business_date,
            all_series=True,
            expiration_from=expiration_from,
            expiration_to=expiration_to,
            fields=list(fields),
            cursor=cursor,
        )
        rows.extend(page.statistics)
        cursor = page.next_cursor
        if not cursor:
            return rows


async def want_series(
    plugin: Any,
    underlying_id: str,
    series_key: Sequence[ops.Identifier],
    *,
    cause: str = "order",
    note: str = "",
    acting_for: str | None = None,
) -> Any:
    """Ask for a series' `INS-` record (W6.37): the deployment holds one
    already, the platform mints it under the deployment's series request
    rule, or the request waits for an admin; the answer says which."""
    return await plugin.request_series_records(
        series=[
            SeriesWant(
                series_key=tuple(series_key),
                underlying_instrument_id=underlying_id,
                cause=cause,
            )
        ],
        note=note,
        acting_for=acting_for,
    )
