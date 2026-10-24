"""Each role's common logic, tested once here (0.30.0; sdk-contract/the-sdk-
carries-each-roles-common-logic): the data role's wants, recording, licences,
restart backfill and venue (`meridian.roles.data`), raw records as files
(`meridian.edge.RawStore`), and connectivity's placement bookkeeping
(`meridian.roles.connectivity`), each against the suites' `Recorder` standing
in for the sidecar."""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from pathlib import Path
from typing import Any

import pytest

import meridian
from meridian.edge import RawStore
from meridian.operations import _decimal
from meridian.plugin.v1 import operations_pb2 as ops
from meridian.roles import connectivity
from meridian.roles.data import (
    BATCH,
    Health,
    Unread,
    Venue,
    Wants,
    iso_time,
    number,
    unconverted,
)
from meridian.suites import Recorder

NOW = 1_791_633_600 * 1_000_000_000


def _price(key: str) -> meridian.Price:
    return meridian.Price(
        meta=meridian.ObservationMeta(
            row_key=key,
            subjects=[meridian.SubjectRef(entity_id="INS-1")],
            source=ops.Source(dataset="data:live"),
            valid_from_ns=NOW,
        ),
        kind="last",
        price=meridian.Money(Decimal("1.5"), "USD"),
        basis="per_unit",
    )


def _want(want_id: str, key: str, subjects: list[str], standing: bool = False) -> Any:
    return ops.ObservationsWantedEvent(
        want_id=want_id,
        dataset=f"data:{key}",
        data_type="meridian.v1.Price",
        subjects=[ops.SubjectRef(entity_id=s) for s in subjects],
        standing=standing,
    )


def _wants(recorder: Recorder) -> Wants:
    return Wants(recorder, ("daily", "live"), clock_ns=lambda: NOW)


class _Heard:
    def __init__(self, message: Any) -> None:
        self.message = message


# ── Wants ───────────────────────────────────────────────────────────────


async def test_rows_go_in_the_lakes_batches_and_are_counted_overall_and_per_dataset() -> None:
    recorder = Recorder("data")
    recorder.answer("RecordPrices", lambda p: ops.RecordPricesResult(recorded=len(p.prices)))
    wants = _wants(recorder)
    sent = await wants.record(
        "prices", [_price(f"k{n}") for n in range(BATCH + 7)], "live", "W-1"
    )
    assert sent == BATCH + 7
    assert [len(p.prices) for p in recorder.on("RecordPrices")] == [BATCH, 7]
    assert all(p.want_id == "W-1" for p in recorder.on("RecordPrices"))
    assert wants.counts.recorded == BATCH + 7 == wants.sent_to("live").recorded
    assert wants.sent_to("live").last_ns == NOW and wants.sent_to("daily").recorded == 0


async def test_rows_kept_apart_count_to_their_dataset_alone() -> None:
    recorder = Recorder("data")
    wants = _wants(recorder)
    recorder.answer("RecordOutcomes", lambda p: ops.RecordOutcomesResult(recorded=1))
    outcome = meridian.Outcome(
        meta=meridian.ObservationMeta(
            row_key="X:outcome",
            subjects=[meridian.SubjectRef(entity_id="INS-1")],
            source=ops.Source(dataset="data:outcomes"),
            valid_from_ns=NOW,
        ),
        determination="pays",
        stage="final",
        settlement_value=meridian.Money(Decimal(1), "USD"),
        determination_as_reported=ops.AsReported(scheme="v:result", code="yes", text="Yes"),
    )
    await wants.record("outcomes", [outcome], "outcomes", overall=False)
    assert wants.sent_to("outcomes").recorded == 1 and wants.counts.recorded == 0
    with pytest.raises(ValueError, match="is not one of"):
        await wants.record("candles", [], "daily")


async def test_a_want_is_answered_declined_by_reason_and_kept_for_its_page() -> None:
    recorder = Recorder("data")
    wants = _wants(recorder)

    async def answer(want: Any, key: str, subjects: list[str], kinds: Any) -> dict[str, str]:
        assert key == "live"
        wants.stand(want, subjects, kinds)
        return {"INS-2": "not_covered", "INS-3": "not_covered", "INS-4": "source_silent"}

    await wants.hear(
        _Heard(_want("W-1", "live", ["INS-1", "INS-2", "INS-3", "INS-4"], True)), answer
    )
    declined = {
        (d.reason, tuple(s.entity_id for s in d.subjects)) for d in recorder.on("DeclineWant")
    }
    assert declined == {
        (ops.UNANSWERED_REASON_NOT_COVERED, ("INS-2", "INS-3")),
        (ops.UNANSWERED_REASON_SOURCE_SILENT, ("INS-4",)),
    }
    [heard] = wants.heard
    assert (heard.want_id, heard.asked, heard.subjects, heard.declined, heard.standing) == (
        "W-1",
        "latest",
        4,
        3,
        True,
    )
    assert wants.counts.wants == 1 and wants.sent_to("live").declined == 3
    assert set(wants.standing) == {"W-1"} and wants.standing_of("live")
    assert wants.withdraw("W-1") is not None and not wants.standing


async def test_an_answer_that_raises_declines_every_subject_source_silent() -> None:
    recorder = Recorder("data")
    wants = _wants(recorder)

    async def failing(*_: Any) -> dict[str, str]:
        raise OSError("the venue did not answer")

    await wants.hear(_Heard(_want("W-2", "daily", ["INS-1", "INS-2"])), failing)
    [declined] = recorder.on("DeclineWant")
    assert (
        declined.reason == ops.UNANSWERED_REASON_SOURCE_SILENT and len(declined.subjects) == 2
    )


async def test_a_want_of_another_instances_dataset_is_heard_under_no_key() -> None:
    recorder = Recorder("data")
    wants = _wants(recorder)
    keys: list[str] = []

    async def answer(want: Any, key: str, subjects: list[str], kinds: Any) -> dict[str, str]:
        keys.append(key)
        return {}

    event = _want("W-3", "live", ["INS-1"])
    event.dataset = "another-1:live"
    await wants.hear(_Heard(event), answer)
    assert keys == [""] and wants.dataset("live") == "data:live"


async def test_licences_are_its_own_datasets_and_a_refusal_is_said_once() -> None:
    recorder = Recorder("data")
    recorder.answer(
        "ListDatasets",
        lambda _: ops.ListDatasetsResult(
            licences=[
                ops.DatasetLicence(dataset="data:daily"),
                ops.DatasetLicence(dataset="other-1:daily"),
            ]
        ),
    )
    wants = _wants(recorder)
    assert await wants.read_licences() == frozenset({"data:daily"})

    def refused(_: Any) -> Any:
        raise meridian.NotGranted("platform.lake.query.list-datasets", "not granted")

    recorder.answer("ListDatasets", refused)
    assert await wants.read_licences() == frozenset({"data:daily"}) and not wants.reads_licences
    assert await wants.read_licences() == frozenset({"data:daily"})
    assert len(recorder.on("ListDatasets")) == 2


async def test_a_restarts_gap_is_read_once_per_subject_and_counted() -> None:
    recorder = Recorder("data")
    last = ops.Trade(
        meta=ops.ObservationMeta(
            row_key="P:t:1",
            subjects=[ops.SubjectRef(entity_id="INS-1")],
            source=ops.Source(dataset="data:trades"),
            valid_from_ns=NOW,
        )
    )
    recorder.answer("ListTrades", lambda _: ops.ListTradesResult(trades=[last]))
    recorder.answer("RecordTrades", lambda p: ops.RecordTradesResult(recorded=len(p.trades)))
    wants = Wants(recorder, ("trades",), clock_ns=lambda: NOW)
    missed = meridian.Trade(
        meta=meridian.ObservationMeta(
            row_key="P:t:2",
            subjects=[meridian.SubjectRef(entity_id="INS-1")],
            source=ops.Source(dataset="data:trades"),
            valid_from_ns=NOW,
        ),
        price=meridian.Money(Decimal(1), "USD"),
        quantity=Decimal("2"),
    )

    async def history(_: ops.Trade) -> list[meridian.Trade]:
        return [missed]

    assert await wants.backfill(["INS-1"], history, "trades") == 1
    assert await wants.backfill(["INS-1"], history, "trades") == 0, "once per process"
    assert wants.sent_to("trades").recorded == 1 and wants.backfilled == {"INS-1"}

    def refused(_: Any) -> Any:
        raise meridian.NotGranted("platform.lake.query.list-trades", "not granted")

    recorder.answer("ListTrades", refused)
    assert await wants.backfill(["INS-2"], history, "trades") == 0, "said, and it goes on"


# ── The venue ───────────────────────────────────────────────────────────


async def test_the_venue_is_resolved_once_and_one_not_held_reported_once() -> None:
    recorder = Recorder("data")
    venue = Venue()
    named = (("iso10383", "XFKE", ""),)
    assert await venue.resolve(recorder, named, "fakev", NOW)
    assert await venue.resolve(recorder, named, "fakev", NOW)
    assert len(recorder.on("ResolveVenue")) == 1 and not venue.missing
    recorder.answer("ResolveVenue", lambda _: ops.ResolveVenueResult(found=False))
    missing = Venue()
    assert await missing.resolve(recorder, named, "fakev", NOW) == ""
    [reported] = recorder.on("ReportMissingVenue")
    assert reported.source == "fakev" and missing.missing
    said = unconverted("fakev", [Unread("price", "")], missing, "Fake Events")
    assert [(u.scheme, u.code, u.text) for u in said] == [
        ("fakev:price", "?", "?"),
        ("fakev:venue", "fakev", "Fake Events"),
    ]
    long = unconverted("v" * 70, [Unread("f", "x" * 300)])[0]
    assert (len(long.scheme), len(long.code), len(long.text)) == (64, 128, 256)


def test_a_venues_figure_is_read_from_its_text_never_a_float() -> None:
    assert number("0.000012345678901234") == Decimal("0.000012345678901234")
    assert number(0.1) is None and number(True) is None and number("NaN") is None
    assert number("1." + "0" * 19) is None, "past the contract's 18 places"
    assert iso_time(0) == "" and iso_time(NOW) == "2026-10-10T12:00:00Z"
    assert Health().healthy and not Health(calls=1, last_failed_ns=1).healthy


# ── Raw records as files ────────────────────────────────────────────────

DAY_NS = 86_400 * 1_000_000_000
OCT_1 = 1_790_812_800 * 1_000_000_000


class Mover:
    """The SDK's moves, as a plugin calls them, recorded."""

    def __init__(self) -> None:
        self.moved: list[tuple[str, str, int]] = []
        self.stored: Any = None

    async def archive_unit(self, kind: str, unit: str, **span: int) -> None:
        self.moved.append(("archived", unit, span["record_count"]))

    async def delete_unit(self, kind: str, unit: str, **span: int) -> None:
        self.moved.append(("deleted", unit, span["record_count"]))


def _kept(root: Path) -> RawStore:
    store = RawStore(root)
    for day in range(10):
        at = OCT_1 + day * DAY_NS
        store.keep("candles", "BTC-USD", {"received_at_ns": at, "body": "[]", "status": 200})
        store.keep_line("ticker", "BTC-USD", {"received_at_ns": at + 1, "body": str(day)})
    return store


def test_each_day_is_one_unit_counting_its_records(tmp_path: Path) -> None:
    units = _kept(tmp_path).units()
    assert [u.unit for u in units][:2] == ["responses/2026-10-01", "responses/2026-10-02"]
    assert all(u.records == 2 for u in units) and len(units) == 10


async def test_days_past_the_window_are_archived_and_today_never(tmp_path: Path) -> None:
    store, mover = _kept(tmp_path), Mover()
    await store.tend(mover, 3, "archived", date(2026, 10, 10))
    assert [m[1] for m in mover.moved] == [f"responses/2026-10-0{d}" for d in range(1, 7)]
    assert mover.stored[0].record_kind == "responses" and mover.stored[0].record_count == 20


async def test_kept_moves_nothing_and_deleted_deletes(tmp_path: Path) -> None:
    store, mover = _kept(tmp_path), Mover()
    await store.tend(mover, 3, "kept", date(2026, 10, 10))
    assert not mover.moved
    await store.tend(mover, 8, "deleted", date(2026, 10, 10))
    assert mover.moved == [("deleted", "responses/2026-10-01", 2)]


async def test_a_move_refused_keeps_the_unit(tmp_path: Path) -> None:
    store = _kept(tmp_path)

    class Refusing(Mover):
        async def archive_unit(self, kind: str, unit: str, **span: int) -> None:
            raise meridian.MeridianError("no archive")

    await store.tend(Refusing(), 3, "archived", date(2026, 10, 10))
    assert len(store.units()) == 10


def test_a_live_line_names_its_place_and_a_repeat_names_it_again(tmp_path: Path) -> None:
    store = RawStore(tmp_path, kind="answers")
    first = store.keep_line("ticker", "X", {"received_at_ns": OCT_1, "body": "a"})
    again = store.keep_line("ticker", "X", {"received_at_ns": OCT_1 + 5, "body": "a"})
    other = store.keep_line("ticker", "X", {"received_at_ns": OCT_1 + 9, "body": "b"})
    assert first == again == "answers/2026-10-01/ticker/X.jsonl#0"
    assert other.endswith("#1") and store.received(again, 0) == OCT_1
    assert store.get(other) == {"received_at_ns": OCT_1 + 9, "body": "b"}
    assert store.get("answers/2026-10-01/ticker/X.jsonl#7") is None
    assert [r["body"] for r in store.records()] == ["a", "b"]


# ── Connectivity's placement bookkeeping ────────────────────────────────


async def test_a_placement_is_noted_before_its_send_and_never_sent_twice(
    tmp_path: Path,
) -> None:
    recorder = Recorder("broker")
    sent = connectivity.Sent(tmp_path / "trading" / "sent.json")
    calls: list[str] = []

    async def send() -> tuple[str, str]:
        assert "PLC-1" in sent, "noted before it is sent"
        calls.append("PLC-1")
        return "ORD-9", "trading/2026-10-10/place-1.json"

    placed = await connectivity.place_once(recorder, sent, "PLC-1", send, source="broker")
    assert (placed.state, placed.answer, placed.raw_key) == (
        "placed",
        "ORD-9",
        "trading/2026-10-10/place-1.json",
    )
    restarted = connectivity.Sent(tmp_path / "trading" / "sent.json")
    again = await connectivity.place_once(recorder, restarted, "PLC-1", send, source="broker")
    assert again.state == "sent_before" and calls == ["PLC-1"] and list(restarted) == ["PLC-1"]


async def test_a_refusal_is_rejected_and_no_answer_is_an_unknown_outcome() -> None:
    recorder = Recorder("broker")
    sent = connectivity.Sent(None)

    async def refused() -> tuple[str, str]:
        raise connectivity.VenueRefused("40310000", "insufficient buying power", "raw/1")

    async def lost() -> tuple[str, str]:
        raise connectivity.VenueUnanswered("timed out", "raw/2")

    assert (
        await connectivity.place_once(recorder, sent, "PLC-1", refused, source="broker")
    ).state == "rejected"
    assert (
        await connectivity.place_once(recorder, sent, "PLC-2", lost, source="broker")
    ).state == "unknown"
    rejected, unknown = recorder.on("ReportPlacement")
    assert rejected.event == ops.PLACEMENT_EVENT_REJECTED
    assert rejected.rejection_reason == ops.REJECTION_REASON_VENUE_REJECTED
    assert (rejected.rejection_as_reported.scheme, rejected.rejection_as_reported.code) == (
        "broker:error",
        "40310000",
    )
    assert unknown.event == ops.PLACEMENT_EVENT_OUTCOME_UNKNOWN
    assert unknown.unknown_reason == ops.UNKNOWN_REASON_REQUEST_UNANSWERED
    assert unknown.raw_record.key == "raw/2"


async def test_an_unknown_outcome_is_resolved_from_the_venues_orders_by_its_tag() -> None:
    orders = [{"id": "ORD-1", "client": "PLC-1"}, {"id": "ORD-2", "client": ""}]
    found = connectivity.resolve_unanswered(["PLC-1", "PLC-3"], orders, lambda o: o["client"])
    assert found == {"PLC-1": orders[0]}
    recorder = Recorder("broker")
    await connectivity.report_status_not_mapped(recorder, "PLC-1", "held", "broker", "raw/3")
    [said] = recorder.on("ReportPlacement")
    assert said.unknown_reason == ops.UNKNOWN_REASON_VENUE_STATUS_NOT_MAPPED
    assert (said.status_as_reported.scheme, said.status_as_reported.code) == (
        "broker:order-status",
        "held",
    )


def test_a_fill_is_the_same_fill_however_often_it_is_read() -> None:
    assert connectivity.execution_id("ORD-1", Decimal("3.000")) == "ORD-1:3"
    assert connectivity.bust_id("ORD-1:3") == "ORD-1:3:busted"
    assert connectivity.fill_price(Decimal(1), Decimal("10"), Decimal(3), Decimal("11"), 4) == (
        Decimal("11.5"),
        False,
    )
    price, rounded = connectivity.fill_price(Decimal(0), None, Decimal(3), Decimal("10.1"), 2)
    assert (price, rounded) == (Decimal("10.1"), False)
    price, rounded = connectivity.fill_price(
        Decimal(1), Decimal(1), Decimal(4), Decimal("1.1"), 2
    )
    assert (price, rounded) == (Decimal("1.13"), True), "3.40 over 3, half-even to 2 places"


def test_what_the_book_holds_filled_takes_each_bust_off() -> None:
    def execution(eid: str, qty: str, venue: str = "", supersedes: str = "") -> ops.Execution:
        return ops.Execution(
            execution_id=eid,
            placement_id="PLC-1",
            venue_execution_id=venue,
            supersedes=supersedes,
            quantity=_decimal(Decimal(qty), "quantity"),
        )

    held = [
        execution("E1", "2", "ORD-1:2"),
        execution("E2", "1", "ORD-1:3"),
        execution("E3", "0", "ORD-1:3:busted", supersedes="E2"),
        execution("E4", "5", "ORD-2:5"),
    ]
    assert connectivity.filled_in_book("PLC-1", held) == Decimal(7)
    assert connectivity.filled_in_book("PLC-1", held, besides="ORD-2") == Decimal(2)
    assert connectivity.filled_in_book("PLC-2", held) == Decimal(0)
