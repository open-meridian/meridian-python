"""SDK 0.33.0's helpers for contract v28, past what the suites ask: the OSI
symbol, a package's legs in lowest terms, the edge's quality checks and
their thresholds, a signal's robust baseline, the lifecycle's expectations
and releases, the ems's actions permitted, a licence's eligibility, and
latency reported."""

from __future__ import annotations

from datetime import UTC, date, datetime
from decimal import Decimal

import pytest

import meridian
from meridian.plugin.v1 import operations_pb2 as ops
from meridian.roles import Latency, chains, ems, lifecycle, packages
from meridian.roles.data import Wants
from meridian.roles.data.quality import (
    Baseline,
    EdgeChecks,
    OutlierThresholds,
    Thresholds,
    thresholds_from,
)
from meridian.suites import Recorder

NOW = 1_792_800_000_000_000_000


def usd(amount: str) -> meridian.Money:
    return meridian.Money(Decimal(amount), "USD")


# ── Chains ───────────────────────────────────────────────────────────────


def test_an_osi_symbol_is_21_characters_and_reads_back() -> None:
    symbol = chains.osi_symbol("AAPL", date(2026, 11, 20), "call", Decimal("230"))
    assert symbol == "AAPL  261120C00230000" and len(symbol) == 21
    assert chains.osi_terms(symbol) == ("AAPL", date(2026, 11, 20), "C", Decimal("230"))
    assert chains.osi_symbol("SPXW", "2026-12-18", "P", "5872.5") == "SPXW  261218P05872500"
    with pytest.raises(ValueError, match="at most 3 places"):
        chains.osi_symbol("AAPL", "2026-11-20", "call", "230.0001")
    with pytest.raises(ValueError, match="not a 21-character OSI symbol"):
        chains.osi_key("AAPL261120C230")


def test_an_option_series_carries_the_listed_option_templates_fields() -> None:
    series = chains.option_series(
        "INS-AAPL", "AAPL  261120P00230000", template_id="TPL-1", template_version="1",
        dataset="tradier-1:options", currency="USD", exercise_style="EXERCISE_STYLE_AMERICAN",
        settlement_method="SETTLEMENT_METHOD_PHYSICAL", deliverable=[("INS-AAPL", 100)],
    )  # fmt: skip
    assert series.meta is not None
    assert [s.entity_id for s in series.meta.subjects] == ["INS-AAPL"]
    assert series.meta.series_key[0].scheme == "occ_osi"
    fields = {f.path: f.value for f in series.fields}
    assert fields["put_or_call"] == "PUT_OR_CALL_PUT"
    assert fields["strike_price"] == "230 USD"
    assert fields["deliverable[0].quantity"] == "100"
    assert fields["option_root"] == "AAPL"


async def test_a_chain_is_read_page_by_page() -> None:
    recorder = Recorder("signal-1")
    pages = iter(
        [
            ops.ListSeriesResult(series=[ops.ListedSeries()], next_cursor="2"),
            ops.ListSeriesResult(series=[ops.ListedSeries()]),
        ]
    )
    recorder.answer("ListSeries", lambda _: next(pages))
    assert len(await chains.read_chain(recorder, "INS-AAPL", "2026-11-20")) == 2
    first = recorder.on("ListSeries")[0]
    assert (first.expiration_from, first.expiration_to) == ("2026-11-20", "2026-11-20")
    assert list(first.paths) == [] and first.page_size == 0, "every term, the lake's max page"


async def test_a_chain_read_asks_only_for_what_its_page_shows() -> None:
    """Contract v28, amended 2026-10-28 (rulings 821, 833): the window, the
    terms drawn and the fields shown, each sent as asked."""
    recorder = Recorder("signal-1")
    recorder.answer("ListSeries", lambda _: ops.ListSeriesResult(series=[ops.ListedSeries()]))
    drawn = ["put_or_call", "strike_price", "expiration_date"]
    await chains.read_chain(recorder, "INS-AAPL", "2026-11-20", paths=drawn)
    assert list(recorder.on("ListSeries")[0].paths) == drawn
    recorder.answer("ListStatistics", lambda _: ops.ListStatisticsResult())
    await chains.read_open_interest(
        recorder, "INS-AAPL", "2026-10-23", expiration_from="2026-11-20",
        expiration_to="2026-11-20", fields=["meridian.v1.Statistic.value"],
    )  # fmt: skip
    asked = recorder.on("ListStatistics")[0]
    assert asked.all_series
    assert (asked.expiration_from, asked.expiration_to) == ("2026-11-20", "2026-11-20")
    assert list(asked.fields) == ["meridian.v1.Statistic.value"]
    recorder.answer("ListQuotes", lambda _: ops.ListQuotesResult())
    await recorder.list_quotes(
        subjects=[meridian.SubjectRef(entity_id="INS-AAPL")], all_series=True,
        expiration_from="2026-11-20", expiration_to="2026-11-20",
        fields=["meridian.v1.Quote.bid", "meridian.v1.Quote.ask"], page_size=500,
    )  # fmt: skip
    quotes = recorder.on("ListQuotes")[0]
    assert (quotes.expiration_from, list(quotes.fields)) == (
        "2026-11-20",
        ["meridian.v1.Quote.bid", "meridian.v1.Quote.ask"],
    )


async def test_an_underlyings_expirations_are_one_read() -> None:
    """Contract v28, amended 2026-10-28 (rulings 856, 858, 859): one
    ListExpirations, the type and the range sent as asked, each date once
    with its series count."""
    recorder = Recorder("signal-1")
    recorder.answer(
        "ListExpirations",
        lambda _: ops.ListExpirationsResult(
            expirations=[
                ops.Expiration(expiration_date="2026-11-20", series_count=212),
                ops.Expiration(expiration_date="2026-12-18", series_count=188),
            ]
        ),
    )
    found = await chains.read_expirations(
        recorder, "INS-AAPL", "2026-11-01", date(2026, 12, 31)
    )
    assert [(e.expiration_date, e.series_count) for e in found] == [
        ("2026-11-20", 212),
        ("2026-12-18", 188),
    ]
    asked = recorder.on("ListExpirations")
    assert len(asked) == 1
    assert asked[0].underlying_id == "INS-AAPL"
    assert asked[0].instrument_type == ops.INSTRUMENT_TYPE_LISTED_OPTION
    assert (asked[0].expiration_from, asked[0].expiration_to) == ("2026-11-01", "2026-12-31")
    await chains.read_expirations(recorder, "INS-ES", instrument_type="future")
    every = recorder.on("ListExpirations")[1]
    assert every.instrument_type == ops.INSTRUMENT_TYPE_FUTURE
    assert (every.expiration_from, every.expiration_to) == ("", "")


# ── Packages ─────────────────────────────────────────────────────────────


def test_a_packages_ratios_are_put_in_lowest_terms() -> None:
    legs = packages.legs(("INS-C1", "buy", 2, "open"), ("INS-C2", "sell", 4, "open"))
    assert [leg.ratio for leg in legs] == [1, 2]
    with pytest.raises(ValueError, match="2 to 16 legs"):
        packages.legs(("INS-C1", "buy", 1, "open"))
    with pytest.raises(ValueError, match="whole number"):
        packages.legs(("INS-C1", "buy", Decimal("1.5"), "open"), ("INS-C2", "sell", 1, "open"))


async def test_a_package_fill_links_each_leg_to_the_package() -> None:
    recorder = Recorder("broker-1")
    await packages.report_fill(
        recorder, placement_id="PLC-1", venue_account_code="A-1", venue_execution_id="PKG",
        quantity=1, net_price=usd("1.85"),
        leg_fills=[packages.LegFill("INS-C1", "buy", Decimal(1), usd("4.20"), "L1")],
        trade_time_ns=NOW, trade_date="2026-10-23",
    )  # fmt: skip
    sent = recorder.on("ReportExecution")
    assert [s.multi_leg_reporting_type for s in sent] == [
        ops.MULTI_LEG_REPORTING_TYPE_PACKAGE,
        ops.MULTI_LEG_REPORTING_TYPE_LEG,
    ]
    assert sent[1].package_execution_id == "PKG" and sent[1].instrument_id == "INS-C1"


# ── Quality at the edge ──────────────────────────────────────────────────


def quote(key: str, bid: str, ask: str, at_ns: int = NOW) -> meridian.Quote:
    return meridian.Quote(
        meta=meridian.ObservationMeta(
            row_key=key,
            subjects=[meridian.SubjectRef(entity_id="INS-1")],
            source_times=[meridian.SourceTime(kind="event", at_ns=at_ns)],
        ),
        bid=usd(bid),
        ask=usd(ask),
    )


def judged(edge: EdgeChecks, *rows: meridian.Quote) -> list[tuple[object, tuple[str, ...]]]:
    out = []
    for row in rows:
        (kept,) = edge.judged("live", [row])
        out.append((kept.meta.quality, tuple(kept.meta.quality_reasons)))
    return out


def test_a_locked_quote_is_valid_and_one_crossed_within_tolerance_too() -> None:
    edge = EdgeChecks(
        thresholds={"live": Thresholds(crossed_tolerance=Decimal("0.01"))}, clock_ns=lambda: NOW
    )
    assert judged(edge, quote("1", "10.00", "10.00"), quote("2", "10.01", "10.00")) == [
        (None, ()),
        (None, ()),
    ]
    assert judged(edge, quote("3", "10.05", "10.00")) == [("invalid", ("crossed_quote",))]


def test_a_repeat_under_the_same_row_key_is_no_duplicate() -> None:
    edge = EdgeChecks(clock_ns=lambda: NOW)
    assert judged(edge, quote("1", "10", "11"), quote("1", "10", "11"))[1] == (None, ())
    assert judged(edge, quote("2", "10", "11"))[0] == ("suspicious", ("duplicate",))


def test_the_same_bar_over_another_interval_is_no_duplicate() -> None:
    """0.33.1: a bar says its values of its interval, so a day's bar equal to
    its one traded hour's, or the next hour's alike, is no duplicate; the
    same interval under a new row key still is."""
    hour = 3_600 * 10**9

    def bar(key: str, start: int, end: int, day: str = "") -> meridian.Bar:
        return meridian.Bar(
            meta=meridian.ObservationMeta(
                row_key=key, subjects=[meridian.SubjectRef(entity_id="INS-1")],
                valid_from_ns=start, valid_until_ns=end, business_date=day,
            ),
            open=usd("0.40"), high=usd("0.45"), low=usd("0.38"), close=usd("0.43"), volume=12,
        )  # fmt: skip

    edge = EdgeChecks(clock_ns=lambda: NOW)
    rows = [
        bar("h1", NOW - 3 * hour, NOW - 2 * hour),
        bar("h2", NOW - 2 * hour, NOW - hour),
        bar("d1", NOW - 24 * hour, NOW, "2026-10-09"),
        bar("d1-again", NOW - 24 * hour, NOW, "2026-10-09"),
    ]
    kept = edge.judged("bars", rows)
    assert [r.meta.quality for r in kept] == [None, None, None, "suspicious"]


def test_rows_after_a_gap_stay_suspicious_until_resynced() -> None:
    edge = EdgeChecks(clock_ns=lambda: NOW)
    assert not edge.sequenced("live", 1)
    assert edge.sequenced("live", 3)
    assert judged(edge, quote("a", "10", "11"), quote("b", "10", "12")) == [
        ("suspicious", ("sequence_gap",)),
        ("suspicious", ("sequence_gap",)),
    ]
    edge.resynced("live")
    assert not edge.sequenced("live", 1)  # a new connection numbers afresh
    assert judged(edge, quote("c", "10", "13")) == [(None, ())]


def test_a_source_time_ahead_of_the_clock_is_invalid_and_a_late_row_stale() -> None:
    edge = EdgeChecks(
        thresholds={"live": Thresholds(stale_after_ns=5_000_000_000)}, clock_ns=lambda: NOW
    )
    ahead = quote("1", "10", "11", NOW + 2_000_000_000)
    late = quote("2", "10", "12", NOW - 9_000_000_000)
    assert judged(edge, ahead) == [("invalid", ("implausible_timestamp",))]
    assert judged(edge, late)[0] == ("suspicious", ("stale", "out_of_order"))


def test_a_plugins_own_judgement_is_only_ever_escalated() -> None:
    edge = EdgeChecks(clock_ns=lambda: NOW)
    row = quote("1", "10", "11")
    assert row.meta is not None
    held = meridian.Quote(
        meta=meridian.ObservationMeta(
            **{**row.meta.__dict__, "quality": "invalid", "quality_reasons": ["schema"]}
        ),
        bid=row.bid,
        ask=row.ask,
    )
    assert judged(edge, held) == [("invalid", ("schema",))]


def test_the_admins_thresholds_are_read_in_seconds() -> None:
    held = thresholds_from(
        [
            {
                "dataset": "live",
                "stale_after": 30,
                "crossed_tolerance": "0.02",
                "future_skew_max": "",
            }
        ]
    )
    assert held["live"] == Thresholds(
        crossed_tolerance=Decimal("0.02"),
        out_of_order_tolerance_ns=1_000_000_000,
        future_skew_max_ns=1_000_000_000,
        stale_after_ns=30_000_000_000,
    )


async def test_rows_pulled_for_a_read_of_the_past_are_not_judged() -> None:
    recorder = Recorder("data-1")
    wants = Wants(recorder, ("live",), clock_ns=lambda: NOW)
    await wants.record("quotes", [quote("1", "11", "10")], "live", want_id="WNT-PAST")
    assert recorder.on("RecordQuotes")[0].quotes[0].meta.quality == 0
    await wants.record("quotes", [quote("2", "11", "10")], "live")
    assert recorder.on("RecordQuotes")[1].quotes[0].meta.quality == ops.QUALITY_STATE_INVALID


def test_a_robust_baseline_judges_after_its_warm_up_and_is_not_moved_by_an_outlier() -> None:
    baseline = Baseline(OutlierThresholds(warm_up=3, sigma_floor=Decimal("0.1")))
    for value in ("100", "101", "99"):
        assert baseline.judge("X", Decimal(value)) == ("valid", ())
    assert baseline.judge("X", Decimal("100.5")) == ("valid", ())
    assert baseline.judge("X", Decimal("120"))[0] == "invalid"
    assert baseline.judge("X", Decimal("120"))[0] == "invalid"  # still: never held
    baseline.reseed("X")
    assert baseline.judge("X", Decimal("120")) == ("valid", ())


# ── Lifecycle ────────────────────────────────────────────────────────────


def test_an_exercise_by_exception_is_expected_only_a_cent_in_the_money() -> None:
    def expected(close: str, right: str = "call") -> object:
        return lifecycle.exercise_by_exception(
            "ACC-1", "INS-C", 2, "2026-11-20", put_or_call=right, strike=usd("230.00"),
            close=usd(close), underlying_id="INS-AAPL",
        )  # fmt: skip

    assert expected("230.00") is None and expected("230.009") is None
    held = expected("230.01")
    assert isinstance(held, meridian.LifecycleEvent)
    assert held.deliveries[0].quantity == 200 and held.cash == usd("-46000.00")
    put = expected("229.00", "put")
    assert isinstance(put, meridian.LifecycleEvent) and put.deliveries[0].quantity == -200


def test_a_proposal_is_released_only_the_morning_after_with_no_position() -> None:
    proposed = ops.LifecycleEvent(
        state=ops.LIFECYCLE_EVENT_STATE_PROPOSED, event_date="2026-11-20"
    )
    evening = datetime(2026, 11, 20, 22, tzinfo=UTC)
    morning = datetime(2026, 11, 21, 9, tzinfo=UTC)
    assert not lifecycle.due_for_release(
        proposed, now=evening, reported=False, still_held=False
    )
    assert lifecycle.due_for_release(proposed, now=morning, reported=False, still_held=False)
    assert not lifecycle.due_for_release(proposed, now=morning, reported=False, still_held=True)
    assert not lifecycle.due_for_release(proposed, now=morning, reported=True, still_held=False)


async def test_a_report_is_sent_once_on_the_brokers_own_id() -> None:
    recorder = Recorder("tradier-1")
    await lifecycle.report(recorder, lifecycle.expiry("ACC-1", "INS-C", 2, "2026-11-20",
                                                      external_event_id="88120"))  # fmt: skip
    assert recorder.on("RecordLifecycleEvent")[0].idempotency_key == "tradier-1:88120"
    with pytest.raises(ValueError, match="broker's ID"):
        await lifecycle.report(recorder, lifecycle.expiry("ACC-1", "INS-C", 2, "2026-11-20"))
    with pytest.raises(ValueError, match="note"):
        await lifecycle.release(recorder, "LCE-1", " ")


# ── The ems's actions permitted, a licence's eligibility, latency sent ───


async def test_warn_is_honoured_only_where_the_deployment_permits_it() -> None:
    check = ems.ReferenceCheck(action=ems.WARN)
    assert not check.refuses  # unread: the admin's choice, as 0.32.x applied it
    recorder = Recorder("ems-1")
    recorder.answer(
        "ReadStaleReferenceActionsPermitted",
        lambda _: ops.ReadStaleReferenceActionsPermittedResult(warn_permitted=True),
    )
    assert await check.permitted(recorder) and not check.refuses
    assert ems.ReferenceCheck(action=ems.REFUSE, warn_permitted=True).refuses


def test_a_licence_states_who_may_take_its_dataset() -> None:
    licence = meridian.DatasetLicence(
        eligibility=meridian.DataEligibility(
            uses=["personal"], buyer_revenue_below=Decimal("1000000"),
            buyer_revenue_currency_code="USD",
        )
    )  # fmt: skip
    wire = licence._wire().eligibility
    assert list(wire.uses) == [meridian.v1.sidecar_pb2.DATA_USE_PERSONAL]
    assert wire.buyer_revenue_currency_code == "USD" and wire.buyer_revenue_below.low == 1000000
    with pytest.raises(ValueError, match="ISO 4217"):
        meridian.DataEligibility(buyer_revenue_at_least=1)
    with pytest.raises(ValueError, match="personal or commercial"):
        meridian.DataEligibility(uses=["research"])


async def test_latency_is_reported_in_batches_and_a_refusal_kept() -> None:
    recorder = Recorder("oanda-1")
    latency = Latency(recorder)
    latency.rtt("pricing-stream", 41_000_000)
    latency.age("oanda-1:live", "AGE_HOP_EDGE", 120_000_000)
    assert await latency.report() == 2 and latency.sent == 2


def test_the_admins_quality_settings_are_typed_tables() -> None:
    columns = [c.name for c in meridian.dataset_thresholds().columns]
    assert columns[-3:] == ["crossed_tolerance", "out_of_order_tolerance", "future_skew_max"]
    outliers = meridian.quality_thresholds()
    assert outliers.name == "quality_thresholds"
    assert [c.name for c in outliers.columns] == [
        "dataset", "outlier_sigma", "sigma_floor", "warm_up", "invalid_sigma",
        "cross_source_tolerance",
    ]  # fmt: skip
