"""SDK 0.35.3, first: a row delivered latest value first is keyed by its own
kind of row.

0.35.2 read every row with a `kind` field as a price (`record.price`), so a
rate or a statistic -- a kind and no price -- raised `AttributeError: price`
on every delivery, and the hearing loop (`follow`) failed with it: the
plugin sample-options on dev, its views over a chain's statistics. Each kind
of row a stream or a view delivers latest value first is handed on here
through `delivered`, two of one key keeping only the later, two of two keys
both.
"""

from __future__ import annotations

from typing import Any

import pytest

from meridian.operations import CONFLATED
from meridian.plugin.v1 import operations_pb2 as ops
from meridian.receive import _Latest

SPY, AAPL = "INS-SPY", "INS-AAPL"


def _meta(sequence: int, *, subject: str = AAPL, **more: Any) -> ops.ObservationMeta:
    # No dataset named: the datasets' listing is not asked for.
    return ops.ObservationMeta(
        subjects=[ops.SubjectRef(entity_id=subject)],
        source=ops.Source(venue_id="VEN-1"),
        sequence=sequence,
        row_key=f"row-{sequence}",
        **more,
    )


def _osi(value: str) -> list[ops.Identifier]:
    return [ops.Identifier(scheme="occ_osi", value=value)]


def _usd() -> ops.Money:
    return ops.Money(currency_code="USD")


#: Each kind of row a stream or a view delivers latest value first: two
#: records of one key (the second recorded first, so the first is
#: superseded), and one of another key, which supersedes neither.
ROWS: dict[str, tuple[Any, Any, Any]] = {
    "PricesRecorded": (
        ops.Price(meta=_meta(1), kind=ops.PRICE_KIND_LAST, price=_usd()),
        ops.Price(meta=_meta(2), kind=ops.PRICE_KIND_LAST, price=_usd()),
        # A v29 price in yield: no money price, its asset none.
        ops.Price(meta=_meta(3), kind=ops.PRICE_KIND_LAST, basis=ops.PRICE_BASIS_YIELD),
    ),
    "QuotesRecorded": (
        ops.Quote(meta=_meta(1, series_key=_osi("AAPL  261120P00230000")), bid=_usd()),
        ops.Quote(meta=_meta(2, series_key=_osi("AAPL  261120P00230000")), bid=_usd()),
        # Another series of the same underlying's chain.
        ops.Quote(meta=_meta(3, series_key=_osi("AAPL  261120C00235000")), bid=_usd()),
    ),
    "BarsRecorded": (
        ops.Bar(meta=_meta(1, valid_from_ns=60), close=_usd()),
        ops.Bar(meta=_meta(2, valid_from_ns=60), close=_usd()),
        ops.Bar(meta=_meta(3, valid_from_ns=120), close=_usd()),
    ),
    "RatesRecorded": (
        ops.Rate(meta=_meta(1, subject=SPY), kind=1, tenor=ops.Tenor(count=1, unit=1)),
        ops.Rate(meta=_meta(2, subject=SPY), kind=1, tenor=ops.Tenor(count=1, unit=1)),
        ops.Rate(meta=_meta(3, subject=SPY), kind=1, tenor=ops.Tenor(count=3, unit=1)),
    ),
    "StatisticsRecorded": (
        ops.Statistic(
            meta=_meta(1, business_date="2026-10-30", series_key=_osi("AAPL  261120P00230000")),
            kind=1,
        ),
        ops.Statistic(
            meta=_meta(2, business_date="2026-10-30", series_key=_osi("AAPL  261120P00230000")),
            kind=1,
        ),
        ops.Statistic(
            meta=_meta(3, business_date="2026-10-30", series_key=_osi("AAPL  261120C00235000")),
            kind=1,
        ),
    ),
    "SeriesRecorded": (
        ops.ListedSeries(meta=_meta(1, series_key=_osi("AAPL  261120P00230000"))),
        ops.ListedSeries(meta=_meta(2, series_key=_osi("AAPL  261120P00230000"))),
        ops.ListedSeries(meta=_meta(3, series_key=_osi("AAPL  261120C00235000"))),
    ),
}


def test_every_row_delivered_latest_value_first_is_tested_here() -> None:
    assert {row.name for row in CONFLATED if row.within} == set(ROWS)


@pytest.mark.parametrize("name", sorted(ROWS))
async def test_each_row_is_keyed_by_its_own_kind_through_delivered(name: str) -> None:
    (row,) = [each for each in CONFLATED if each.name == name]
    heard: list[int] = []

    async def hand(given: Any) -> None:
        heard.append(getattr(given.message, row.within).meta.sequence)

    latest = _Latest(None, list(CONFLATED), {name: hand}, ())  # type: ignore[arg-type]
    older, newer, other = ROWS[name]

    def delivery(record: Any) -> ops.Delivery:
        made = ops.Delivery(meta=ops.DeliveryMeta(row=name))
        getattr(getattr(made, row.arm), row.within).CopyFrom(record)
        return made

    # Recorded older, other, newer: the newer handed first, so the older of
    # its key is dropped, and the other key's -- recorded before the newer --
    # is handed on beside it, superseded by nothing.
    for record, sequence in ((older, 1), (other, 2), (newer, 3)):
        record.meta.sequence = sequence
    for record in (newer, older, other):
        await latest.delivered(delivery(record))
    assert heard == [3, 2]


def test_a_views_copy_keeps_a_curves_points_apart() -> None:
    """A view keyed a rate by its kind alone, so it kept one point of a
    curve; the points' tenors tell them apart, as the lake conflates them."""
    from meridian.views import _latest_key

    one, three, again = ROWS["RatesRecorded"][1], ROWS["RatesRecorded"][2], ops.Rate()
    again.CopyFrom(one)
    assert _latest_key(one) != _latest_key(three)
    assert _latest_key(one) == _latest_key(again)
    price = ROWS["PricesRecorded"][0]
    assert _latest_key(price).endswith("\x1f")  # nothing added for a price
