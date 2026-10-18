"""Connectivity's whole work (0.30.0; ruling 206): `meridian.roles.connectivity
.Trader` over a made-up venue held in memory, against the suites' `Recorder`
standing in for the sidecar -- a placement sent once with its ID as its
client order ID, fills as stated and as inferred into the book, a send never
answered resolved from the venue's orders, a restart sending nothing twice,
a cancel, a stop and a pause, a status not mapped, a rejection with nothing
sent, the catalogue on enabling trading, the trade date in the listing
market's zone, and the Trading page. FAKES ONLY: nothing here reaches a
broker. Alpaca's and Tradier's plugins run their own adapters and simulated
brokers through the same Trader in their tests."""

from __future__ import annotations

import asyncio
import json
from dataclasses import replace
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

import meridian
from meridian.operations import as_decimal
from meridian.plugin.v1 import operations_pb2 as ops
from meridian.roles import connectivity
from meridian.roles.connectivity import (
    Asked,
    Catalogue,
    Change,
    Sent,
    VenueOrder,
    VenueRefused,
    VenueUnanswered,
    testing,
)
from meridian.suites import Recorder
from meridian.testing import PageClient

#: A symbol whose send the made-up venue takes and never answers, and one it
#: refuses, and one whose order it holds in a status no mapping knows.
LOST, REFUSED, ODD = "LOST", "REFUSE", "ODD"


class FakeVenue:
    """A broker held in memory, read into the Trader's values."""

    statuses = {
        "open": connectivity.WORKING,
        "partially_filled": connectivity.WORKING,
        "filled": connectivity.FILLED,
        "canceled": connectivity.CANCELLED,
        "rejected": connectivity.REJECTED,
    }
    sides = {ops.SIDE_BUY: "buy", ops.SIDE_SELL: "sell"}
    sides_said = {"buy": ops.SIDE_BUY, "sell": ops.SIDE_SELL}
    source = "fakeb"

    def __init__(self, code: str) -> None:
        self.code = code
        self.held: dict[str, VenueOrder] = {}
        self.kept: list[tuple[str, dict[str, Any]]] = []
        self.asked: list[tuple[str, str]] = []

    def accounts(self) -> tuple[str, ...]:
        return (self.code,)

    def catalogue(self, code: str) -> Catalogue:
        return (
            (ops.ORDER_TYPE_LIMIT, (ops.TIME_IN_FORCE_DAY,)),
            (ops.ORDER_TYPE_MARKET, (ops.TIME_IN_FORCE_DAY,)),
        )

    def keep(self, name: str, record: dict[str, Any]) -> str:
        self.kept.append((name, record))
        return f"trading/2026-09/{name}-{len(self.kept)}.json"

    def place(self, code: str, asked: Asked) -> tuple[VenueOrder, str]:
        self.asked.append(("place", asked.placement_id))
        if asked.symbol == REFUSED:
            raise VenueRefused(
                "40310000", "insufficient buying power", self.keep("refused", {})
            )
        order_id = str(len(self.held) + 1)
        status = "held" if asked.symbol == ODD else "open"
        order = VenueOrder(order_id, asked.placement_id, status, symbol=asked.symbol,
                           side="buy", quantity=asked.quantity, limit=asked.limit,
                           placed_at=testing.NOW, updated_at=testing.NOW)  # fmt: skip
        self.held[order_id] = order
        if asked.symbol == LOST:
            raise VenueUnanswered("timed out", self.keep("lost", {}))
        return order, self.keep("placed", {"client_order_id": asked.placement_id})

    def orders(self, code: str) -> tuple[list[VenueOrder], str]:
        return list(self.held.values()), self.keep("orders", {})

    def cancel(self, code: str, order_id: str) -> str:
        self.asked.append(("cancel", order_id))
        held = self.held[order_id]
        if held.status == "filled":
            raise VenueRefused("422", "Order is not open", self.keep("refused", {}))
        self.held[order_id] = replace(held, status="canceled")
        return self.keep("cancelled", {})

    def replace(
        self, code: str, order: VenueOrder | None, order_id: str, change: Change
    ) -> tuple[VenueOrder | None, str]:
        self.asked.append(("replace", order_id))
        held = replace(self.held[order_id], limit=change.limit, quantity=change.quantity)
        self.held[order_id] = held
        return held, self.keep("replaced", {})

    def not_replaceable(self, change: Change) -> str:
        return "it changes no order's quantity" if change.quantity_changed else ""

    def fill(self, order_id: str, filled: str, average: str, *, last: bool = True,
             at: datetime = testing.NOW) -> None:  # fmt: skip
        held = self.held[order_id]
        grown = Decimal(filled) - held.filled
        self.held[order_id] = replace(
            held,
            filled=Decimal(filled),
            average=Decimal(average),
            last_fill=(grown, Decimal(average)) if last else None,
            status="filled" if Decimal(filled) == held.quantity else "partially_filled",
            filled_at=at,
            updated_at=at,
        )


class Rig(testing.Rig):
    instance = "broker"
    code = "ACC-NUMBER-1"
    source = "fakeb"

    def connect(self, broker: Any) -> Any:
        self.fake = broker or FakeVenue(self.code)
        return self.fake


def run(work: Any) -> None:
    asyncio.run(work)


def placed(recorder: Recorder, *, quantity: str = "10", **rig: Any) -> Rig:
    made = Rig(recorder, **rig)
    held = made.placement(quantity=quantity)
    made.holds(held)
    run(made.hear(held))
    return made


def events(recorder: Recorder) -> list[str]:
    return [ops.PlacementEvent.Name(p.event) for p in recorder.on("ReportPlacement")]


def test_a_placement_is_sent_once_with_its_id_as_the_client_order_id() -> None:
    recorder = Recorder("broker")
    rig = placed(recorder)
    (order,) = rig.fake.held.values()
    assert order.client_order_id == "PLC-01JAE00000000000000000001" and order.symbol == "AAPL"
    (sent,) = recorder.on("ReportPlacement")
    assert sent.event == ops.PLACEMENT_EVENT_ACKNOWLEDGED and sent.venue_order_id == "1"
    assert sent.raw_record.key.startswith("trading/")
    assert rig.trader.working and rig.fake.asked == [("place", order.client_order_id)]


def test_fills_as_stated_and_as_inferred_go_into_the_book_once() -> None:
    recorder = Recorder("broker")
    rig = placed(recorder)
    rig.fake.fill("1", "4", "230")
    run(rig.poll(2))
    rig.fake.fill("1", "10", "231.2", last=False)
    run(rig.poll(2))
    fills = recorder.on("ReportExecution")
    assert [as_decimal(f.quantity) for f in fills] == [Decimal(4), Decimal(6)]
    assert [f.venue_execution_id for f in fills] == ["1:4", "1:10"]
    assert [f.kind for f in fills] == [ops.EXECUTION_KIND_VENUE_REPORTED,
                                       ops.EXECUTION_KIND_INFERRED]  # fmt: skip
    assert as_decimal(fills[1].price.amount) == Decimal(232)
    assert all(f.computed_settlement_date == "2026-09-30" for f in fills)
    assert all(f.trade_date == "2026-09-29" for f in fills)


def test_a_fills_trade_date_is_the_listing_markets_day() -> None:
    recorder = Recorder("broker")
    rig = placed(recorder)
    rig.fake.fill("1", "10", "230", at=datetime(2026, 9, 30, 2, 0, tzinfo=UTC))
    run(rig.poll())
    (fill,) = recorder.on("ReportExecution")
    assert fill.trade_date == "2026-09-29", "22:00 in New York is still the 29th"


def test_a_send_never_answered_is_resolved_from_the_orders_never_sent_again() -> None:
    recorder = Recorder("broker")
    rig = placed(recorder, symbol=LOST)
    assert events(recorder) == ["PLACEMENT_EVENT_OUTCOME_UNKNOWN"]
    run(rig.poll())
    assert events(recorder)[-1] == "PLACEMENT_EVENT_ACKNOWLEDGED"
    assert [a for a in rig.fake.asked if a[0] == "place"] == [
        ("place", "PLC-01JAE00000000000000000001")
    ]


def test_a_refusal_is_the_placement_rejected_as_the_venue_said() -> None:
    recorder = Recorder("broker")
    placed(recorder, symbol=REFUSED)
    (rejected,) = recorder.on("ReportPlacement")
    assert rejected.rejection_reason == ops.REJECTION_REASON_VENUE_REJECTED
    assert (rejected.rejection_as_reported.scheme, rejected.rejection_as_reported.code) == (
        "fakeb:error", "40310000",
    )  # fmt: skip


def test_a_restart_never_sends_a_placement_twice(tmp_path: Path) -> None:
    recorder = Recorder("broker")
    rig = placed(recorder, sent=Sent(tmp_path / "trading" / "sent.json"))
    assert json.loads((tmp_path / "trading" / "sent.json").read_text()) == [
        "PLC-01JAE00000000000000000001"
    ]
    again = Recorder("broker")
    restarted = Rig(again, sent=Sent(tmp_path / "trading" / "sent.json"), broker=rig.fake)
    restarted.holds(restarted.placement())
    run(restarted.trader.start())
    run(restarted.poll())
    assert [a for a in rig.fake.asked if a[0] == "place"] == [
        ("place", "PLC-01JAE00000000000000000001")
    ]
    assert events(again) == ["PLACEMENT_EVENT_ACKNOWLEDGED"]


def test_a_cancel_the_ems_asks_for_is_sent_and_read_back() -> None:
    recorder = Recorder("broker")
    rig = placed(recorder)
    held = rig.placement(state=ops.PLACEMENT_STATE_WORKING, venue_order_id="1")
    asked = testing.asking(held, ops.PLACEMENT_CHANGE_KIND_CANCEL)
    rig.holds(asked)
    run(rig.hear(asked))
    assert ("cancel", "1") in rig.fake.asked
    run(rig.poll())
    assert events(recorder)[-1] == "PLACEMENT_EVENT_CANCELLED"


def test_a_replace_is_sent_and_one_not_offered_rejected_with_nothing_sent() -> None:
    recorder = Recorder("broker")
    rig = placed(recorder)
    held = rig.placement(state=ops.PLACEMENT_STATE_WORKING, venue_order_id="1")
    asked = testing.asking(held, ops.PLACEMENT_CHANGE_KIND_REPLACE,
                           limit_price=testing.money("229.50"))  # fmt: skip
    rig.holds(asked)
    run(rig.hear(asked))
    replaced = recorder.on("ReportPlacement")[-1]
    assert replaced.event == ops.PLACEMENT_EVENT_REPLACED
    assert as_decimal(replaced.limit_price.amount) == Decimal("229.50")
    bigger = testing.asking(held, ops.PLACEMENT_CHANGE_KIND_REPLACE, "CRQ-2",
                            quantity=testing.decimal("15"))  # fmt: skip
    rig.holds(bigger)
    run(rig.hear(bigger))
    refused = recorder.on("ReportPlacement")[-1]
    assert refused.rejection_reason == ops.REJECTION_REASON_UNSUPPORTED
    assert [a for a in rig.fake.asked if a[0] == "replace"] == [("replace", "1")]


def test_a_stop_cancels_at_the_venue_naming_the_stop_and_a_pause_holds() -> None:
    recorder = Recorder("broker")
    rig = placed(recorder)
    run(rig.instruct(ops.TRADING_INSTRUCTION_VALUE_STOP))
    (change,) = recorder.on("RequestPlacementChange")
    assert change.cause.entry_id == "ENT-stop-1" and ("cancel", "1") in rig.fake.asked
    paused = Recorder("broker")
    held_back = Rig(paused)
    run(held_back.instruct(ops.TRADING_INSTRUCTION_VALUE_PAUSE))
    queued = held_back.placement()
    held_back.holds(queued)
    run(held_back.hear(queued))
    assert paused.on("ReportPlacement") == []
    run(held_back.instruct(ops.TRADING_INSTRUCTION_VALUE_ACTIVE))
    assert events(paused) == ["PLACEMENT_EVENT_ACKNOWLEDGED"]


def test_a_status_no_mapping_knows_is_an_unknown_outcome_as_reported() -> None:
    recorder = Recorder("broker")
    rig = placed(recorder, symbol=ODD)
    run(rig.poll())
    unknown = recorder.on("ReportPlacement")[-1]
    assert unknown.unknown_reason == ops.UNKNOWN_REASON_VENUE_STATUS_NOT_MAPPED
    assert unknown.status_as_reported.code == "held"


def test_a_read_only_account_rejects_with_nothing_sent_and_enabling_publishes() -> None:
    recorder = Recorder("broker")
    rig = placed(recorder, enabled=False)
    (rejected,) = recorder.on("ReportPlacement")
    assert rejected.rejection_reason == ops.REJECTION_REASON_UNSUPPORTED
    assert not [a for a in rig.fake.asked if a[0] == "place"]
    run(rig.trader.start())
    assert not recorder.on("ReportVenueCatalogue")[-1].catalogue.order_types
    run(rig.trader.enable(rig.code, {"enabled_by": "local|ada"}))
    offered = recorder.on("ReportVenueCatalogue")[-1].catalogue
    assert {t.order_type for t in offered.order_types} == {ops.ORDER_TYPE_LIMIT,
                                                           ops.ORDER_TYPE_MARKET}  # fmt: skip
    assert offered.execution_acknowledgement == ops.EXECUTION_ACKNOWLEDGEMENT_NONE


def test_the_trading_page_shows_counts_and_codes_only() -> None:
    recorder = Recorder("broker")
    rig = placed(recorder)
    run(rig.trader.poll())
    pages = meridian.Pages("Fake broker", kit="0.12.0")

    @pages.page("/admin/connections", "Trading", levels="admin",
                answers=connectivity.TradingRead, name="read_trading")  # fmt: skip
    def trading(request: meridian.Request) -> meridian.Response:
        read = connectivity.trading_read(
            rig.trader, [meridian.roles.data.Credential("API key", False)], "Paper"
        )
        return pages.answer("meridian/roles/connectivity/trading.html", read, venue="Fake",
                            may_enable=True, enable="/admin/connections/enable")  # fmt: skip

    client = PageClient(pages)
    shown = client.get("/admin/connections", "admin").text
    assert "No key yet" in shown and "ACC-NUMBER-1" in shown and "Enabled" in shown
    data = client.call_tool("read_trading", level="admin").data
    assert data["accounts"][0]["order_types"] == ["limit", "market"]
    assert data["working"] == 1 and data["environment"] == "Paper"
    assert connectivity.trading_read(None, [], "Live").accounts == []


def test_a_trader_is_told_its_market_zone() -> None:
    rig = Rig(Recorder("broker"))
    assert rig.trader.market_zone == ZoneInfo("America/New_York")
    assert rig.trader.price_places == connectivity.PRICE_PLACES == 8


def test_number_is_one_function_for_both_roles() -> None:
    """Ruling 212: `number` is defined once and both roles re-export it. What
    a broker sends -- its figures as text, JSON numbers read as Decimals or
    ints, missing or empty -- reads the same as connectivity's own did; what
    the contract's Decimal cannot carry (not finite, past 18 places or 38
    digits) is no number for either role."""
    from meridian.roles import data

    assert connectivity.number is data.number
    sent: list[tuple[object, Decimal | None]] = [
        ("10", Decimal(10)),
        ("230.50", Decimal("230.50")),
        (10, Decimal(10)),
        (Decimal("11.2"), Decimal("11.2")),
        ("-0.25", Decimal("-0.25")),
        (None, None),
        ("", None),
        ("n/a", None),
        (True, None),
        (0.1, None),
        ([1], None),
    ]
    for value, read in sent:
        assert connectivity.number(value) == read, value
    for beyond in ("NaN", "Infinity", "1." + "0" * 19, "1" * 39):
        assert connectivity.number(beyond) is None, beyond
