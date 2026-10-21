"""SDK 0.32.0, contract v27: the analytics component's v27 answer -- realized
P&L served (pnl version 2), a quoted price rounded once per unit (rulings
453 and 486), fiat legs inverted and crossed through the deployment's
pivots (462, 483), a reporting currency (459), a lot's cost missing (325)
and execution costs against the standard benchmarks (W12.1) -- and the
order path's, the rates slice's and the latency track's SDK parts."""

from __future__ import annotations

from decimal import Decimal
from fractions import Fraction
from pathlib import Path
from typing import Any

import pytest

import meridian
from meridian import analytics
from meridian.analytics import reference
from meridian.plugin.v1 import operations_pb2 as ops

CASES = Path(__file__).parent / "reference_cases"
USD = "INS-01J8XQ4M7K00000000CASHUSD"
EUR = "INS-01J8XQ4M7K00000000CASHEUR"
CHF = "INS-01J8XQ4M7K00000000CASHCHF"


def _answer(name: str) -> dict[str, Any]:
    return dict(reference.load(CASES / f"{name}.json")["answer"])


def _value(name: str, account: str, instrument: str) -> Decimal:
    for figure in _answer(name)["figures"]:
        if figure["account_id"] == account and figure["breakdown"][0]["value"] == instrument:
            return Decimal(figure["value"])
    raise KeyError((name, account, instrument))


# ── Analytics (W12) ─────────────────────────────────────────────────────────


def test_pnl_version_2_is_served_and_its_realized_case_is_live() -> None:
    """Rulings 320 and 396: the realized cases kept as v2 tests are live --
    asked of the component, the reference answering them."""
    job = analytics.job(analytics.measure("pnl", 2, by=["sleeve"]), accounts=["ACC-1"])
    assert job.measures[0].version == 2
    assert analytics.SERVED_VERSIONS["pnl"] == 2
    assert reference.definition_of("pnl", 2) is reference.LATER_DEFINITIONS[("pnl", 2)]
    answer = _answer("pnl-v2-realized")
    missing = [n for n in answer["not_evaluated"] if n["reason"].endswith("COST_MISSING")]
    assert [(n["account_id"], n["detail"]) for n in missing] == [("ACC-2", "")]


def test_a_quoted_price_past_18_places_is_rounded_once_per_unit() -> None:
    """Rulings 453 and 486: 12.345678 EUR × 1.085012345678901234 runs to 24
    places; rounded half to even to 18 per unit, then times 1000.5, exact,
    then once to the definition's scale."""
    per_unit = reference.round_half_even(
        Fraction(Decimal("12.345678")) * Fraction(Decimal("1.085012345678901234")), 18
    )
    # Exactly 13.395213045776406028766652: rounded up at the 18th place.
    assert per_unit == Decimal("13.395213045776406029")
    expected = reference.round_half_even(Fraction(per_unit) * Fraction(Decimal("1000.5")), 2)
    assert _value("quoted-price-past-18-places", "ACC-1", "INS-01J8XQ4M7K00000000000SAP") == (
        expected
    )
    # The built-in model a pricing plugin's answer is held to rounds alike.
    value, held = reference.value_per_unit(
        "quoted_price",
        "SAP",
        [("SAP", "close", "12.345678", "EUR"), ("EUR", "close", "1.085012345678901234", "USD")],
    )
    assert (value, held) == (per_unit, "USD")
    # A value within 18 places keeps its stated form.
    assert reference.value_per_unit("quoted_price", "X", [("X", "close", "2.50", "USD")]) == (
        Decimal("2.50"),
        "USD",
    )


def test_fiat_legs_are_inverted_and_crossed_through_the_pivot() -> None:
    """Ruling 462: a euro account's dollars through EURUSD inverted (1 ÷
    1.0850 to 18 places); bitcoin's own dollar price kept, its dollar leg
    inverted; francs to dollars crossed through the euro, the first pivot
    that is neither end, its franc leg inverted."""
    answer = _answer("inverted-and-crossed")
    assert answer["not_evaluated"] == []
    legs = {(leg["from_instrument_id"], leg["to_instrument_id"]): leg for leg in
            answer["provenance"]["conversion_legs"]}  # fmt: skip
    inverted = legs[(USD, EUR)]
    assert inverted["derivation"] == "CONVERSION_DERIVATION_INVERTED"
    assert Decimal(inverted["rate"]) == reference.round_half_even(1 / Fraction("1.0850"), 18)
    crossed = legs[(CHF, USD)]
    assert (crossed["derivation"], crossed["via_instrument_id"], crossed["dataset"]) == (
        "CONVERSION_DERIVATION_CROSSED",
        EUR,
        "",
    )
    sub = reference.round_half_even(1 / Fraction("0.9412"), 18)
    assert legs[(CHF, EUR)]["derivation"] == "CONVERSION_DERIVATION_INVERTED"
    assert Decimal(crossed["rate"]) == reference.round_half_even(
        Fraction(sub) * Fraction("1.0850"), 18
    )
    assert _value("inverted-and-crossed", "ACC-US", CHF) == reference.round_half_even(
        Fraction(Decimal(crossed["rate"])) * 1000, 2
    )
    # Each position's own price is named (ruling 460).
    prices = {p["instrument_id"]: p for p in answer["provenance"]["input_prices"]}
    assert prices["INS-01J8XQ4M7K0000000000NESN"]["row_key"].endswith("/close")


def test_a_token_leg_is_never_inverted() -> None:
    inputs = reference.load(CASES / "inverted-and-crossed.json")["inputs"]
    given = dict(inputs)
    # Bitcoin priced in the euro account's base only the other way round.
    given["market"] = [
        {**row, "subject_id": EUR, "instrument_id": "INS-01J8XQ4M7K00000000000BTC",
         "amount": "0.0000180"} if row["subject_id"] == "INS-01J8XQ4M7K00000000000BTC" else row
        for row in inputs["market"]
    ]  # fmt: skip
    answer = reference.compute(given).to_json()
    assert any(
        n["instrument_id"].endswith("BTC") and n["reason"].endswith("PRICE_MISSING")
        for n in answer["not_evaluated"]
    )


def test_a_reporting_currency_converts_money_and_leaves_weights() -> None:
    answer = _answer("reporting-currency")
    money = [f for f in answer["figures"] if f["measure"]["definition"] != "concentration"]
    assert {f["currency_instrument_id"] for f in money} == {EUR}
    weights = [f for f in answer["figures"] if f["measure"]["definition"] == "concentration"]
    assert {f["denominator"] for f in weights} == {"7275.00"}  # dollars, unconverted


def test_execution_costs_are_measured_against_each_benchmark() -> None:
    """The gaps spec's C3, C4 and C8: s × (price − mid) ÷ mid × 10⁴, half to
    even at 4 places; a stale quote unanswered, never imputed; no moment,
    not measured; the rows the lake keeps beside each account's means."""
    answer = _answer("execution-cost")
    rows = answer["execution_costs"]
    first = [r for r in rows if r["execution_id"].endswith("001")]
    by = {r["benchmark"]: r for r in first}
    assert by["TCA_BENCHMARK_DECISION"]["unanswered"] == "TCA_UNANSWERED_NO_QUOTE"
    assert by["TCA_BENCHMARK_DECISION"]["cost_bps"] is None
    assert by["TCA_BENCHMARK_ARRIVAL"]["cost_bps"] == str(
        reference.round_half_even(
            (Fraction("227.55") - Fraction("227.20")) / Fraction("227.20") * 10_000, 4
        )
    )
    assert by["TCA_BENCHMARK_ARRIVAL"]["fees_bps"] == "0.5493"
    sold = [r for r in rows if r["execution_id"].endswith("003")]
    assert [r["unanswered"] for r in sold][:3] == ["TCA_UNANSWERED_NOT_MEASURED"] * 3
    assert Decimal(sold[3]["cost_bps"]) > 0, "a sale below the mid is a cost"
    assert {f["breakdown"][0]["value"] for f in answer["figures"]} == {
        "TCA_BENCHMARK_ARRIVAL",
        "TCA_BENCHMARK_PLACEMENT_ARRIVAL",
        "TCA_BENCHMARK_MID_AT_FILL",
    }
    assert "execution_costs" not in _answer("valuation")


def test_a_job_is_over_one_account_or_more_as_the_component_refuses() -> None:
    for wrong, why in (
        (
            lambda: analytics.job(
                analytics.measure("implied_distribution", event_group="EVG-1")
            ),
            "one account or more",
        ),
        (lambda: analytics.job(analytics.measure("market_value"), accounts=[""]), "empty"),
        (
            lambda: analytics.job(
                analytics.measure("market_value"),
                accounts=["ACC-1"],
                business_date="2026-10-20",
                lake_as_of_ns=1,
            ),
            "business date",
        ),
    ):
        with pytest.raises(ValueError, match=why):
            wrong()
    job = analytics.job(
        analytics.measure("execution_cost"),
        accounts=["ACC-1"],
        business_date="2026-10-20",
        reporting_currency=EUR,
    )
    sent = ops.RunJobParams(job=meridian.operations._job(job, "job"))
    assert (sent.job.business_date, sent.job.reporting_currency) == ("2026-10-20", EUR)


# ── The rates slice (ruling 345; FDP items 1 to 5) ──────────────────────────

from meridian.roles.data import rates  # noqa: E402
from meridian.roles.data.testing import RATES_CASES, Lake, rates_producers  # noqa: E402
from meridian.suites import Recorder, check, suite  # noqa: E402
from rates_cases import DAY, PUBLISHED, RATES, SOFR  # noqa: E402


@pytest.mark.parametrize("name", RATES_CASES)
async def test_every_rates_case_passes_through_the_sdks_rates_helpers(name: str) -> None:
    made = rates_producers(RATES, source="ust", now_ns=PUBLISHED)
    recorder = Lake("rates-1")
    await made[name](recorder)
    assert check(suite("data").case(name), recorder) is None


async def test_a_same_day_revision_is_the_next_version_of_its_row_key() -> None:
    lake = Lake("rates-1")
    await rates_producers(RATES, source="nyfed", now_ns=PUBLISHED)["a-same-day-revision"](lake)
    keys = {r.meta.row_key for r in lake.rows("RecordRates")}
    assert len(keys) == 1 and next(iter(keys)).endswith("@INS-SOFR")
    assert lake.versions[("rate", next(iter(keys)))][0] == 2


async def test_a_tenor_not_published_is_no_row_never_a_zero() -> None:
    lake = Lake("rates-1")
    await rates_producers(RATES, source="ust", now_ns=PUBLISHED)["a-tenor-not-published"](lake)
    assert [rates.tenor_label(r.tenor) for r in lake.rows("RecordRates")] == ["1M", "10Y"]


async def test_a_rate_not_held_is_reported_once_a_day_and_not_recorded() -> None:
    recorder = Recorder("rates-1")
    recorder.answer(
        "ResolveIdentifier",
        lambda _: ops.ResolveIdentifierResult(
            found=False, miss_reason=ops.MISS_REASON_NOT_FOUND
        ),
    )
    feed = rates.Feed(recorder, "nyfed", clock_ns=lambda: PUBLISHED)
    assert await feed.subject(SOFR) == ""
    assert await feed.subject(SOFR) == ""
    assert len(recorder.on("ReportMissingInstrument")) == 1
    asked = recorder.on("ResolveIdentifier")[0]
    assert asked.stated_asset_class == ops.ASSET_CLASS_REFERENTIAL


def test_a_publishers_tenor_labels_read_as_the_wires() -> None:
    for label, (count, unit, said) in {
        "1 Mo": (1, "month", "1M"),
        "13 WEEKS": (13, "week", "13W"),
        "10 Yr": (10, "year", "10Y"),
        "3M": (3, "month", "3M"),
        "ON": (1, "overnight", "ON"),
        "30-year": (30, "year", "30Y"),
    }.items():
        held = rates.tenor(label)
        assert (held.count, held.unit) == (count, unit)
        assert rates.tenor_label(held) == said
    for wrong in ("1.5 Month", "soon", "0M"):
        with pytest.raises(ValueError, match="maturity"):
            rates.tenor(wrong)
    assert rates.tenor_days(rates.tenor("1Y")) > rates.tenor_days(rates.tenor("6M"))
    with pytest.raises(TypeError, match="float"):
        rates.percent(4.31)  # type: ignore[arg-type]


async def test_a_curve_is_read_for_a_date_in_tenor_order_every_page() -> None:
    recorder = Recorder("reporting-1")

    def point(label: str) -> ops.Rate:
        held = rates.tenor(label)
        return ops.Rate(tenor=ops.Tenor(count=held.count, unit=ops.TenorUnit.Value(
            f"TENOR_UNIT_{str(held.unit).upper()}")))  # fmt: skip

    pages = iter([
        ops.ListRatesResult(rates=[point("10Y"), point("1M")], next_cursor="2"),
        ops.ListRatesResult(rates=[point("3M")]),
    ])  # fmt: skip
    recorder.answer("ListRates", lambda _: next(pages))
    curve = await rates.read_curve(recorder, "INS-PAR", DAY)
    assert [rates.tenor_label(r.tenor) for r in curve] == ["1M", "3M", "10Y"]
    asked = recorder.on("ListRates")
    assert len(asked) == 2 and asked[1].cursor == "2" and asked[0].business_date == DAY
    assert check(suite("reporting").case("reads-a-curve-for-a-date"), recorder) is None


# ── Latency, liveness and trading sessions (W4.16, W10.4, W3.19) ────────────

from meridian.roles import Histogram, Latency, Liveness, confirmed_ns, ems, in_session  # noqa: E402
from meridian.roles._latency import bucket_of, value_of  # noqa: E402


def test_the_histogram_is_hdrhistograms_layout_at_two_significant_digits() -> None:
    # 1 µs lowest (its unit 512 ns, HdrHistogram's floor of log2), 2
    # significant digits: 256 sub-buckets per doubling.
    assert bucket_of(0) == 0
    assert value_of(bucket_of(1_000)) <= 1_000 < value_of(bucket_of(1_000) + 1)
    for value in (1_000, 41_000_000, 999_999_999, 3_600 * 10**9):
        index = bucket_of(value)
        assert value_of(index) <= value < value_of(index + 1)
    for value in (250_000, 41_000_000, 999_999_999, 3_600 * 10**9):
        index = bucket_of(value)
        # Two significant digits past 200 of its lowest unit: a bucket is
        # within 1% of its values, as HdrHistogram's layout guarantees.
        assert (value_of(index + 1) - value_of(index)) / value <= 0.01
    assert bucket_of(10**15) == bucket_of(3_600 * 10**9), "held to an hour"
    held = Histogram()
    for ms in range(1, 101):
        held.record(ms * 1_000_000)
    assert abs(held.percentile(99) - 99_000_000) <= 990_000
    assert held.percentile(50) <= 50_500_000 and held.total == 100


async def test_latency_is_sent_as_sparse_snapshots_every_interval() -> None:
    recorder = Recorder("oanda-1")
    clock = iter(range(0, 10**12, 10**10))
    latency = Latency(
        recorder,
        clock_ns=lambda: next(clock),
        ceilings=meridian.ceilings_from([{"session": "", "rtt_p99": 250, "backlog_max": 100}]),
    )
    latency.rtt("pricing-stream", 41_000_000)
    latency.count("pricing-stream", reconnects=1)
    latency.age("oanda-1:live", "AGE_HOP_EDGE", 120_000_000, session="pricing-stream")
    sent = await latency.report()
    assert sent == 2
    snapshots = recorder.on("ReportLatency")[0].snapshots
    session, age = snapshots
    assert (session.session, session.metric, session.counters.reconnects) == (
        "pricing-stream",
        ops.LATENCY_METRIC_RTT,
        1,
    )
    assert session.ceilings.rtt_p99_ns == 250_000_000 and session.ceilings.backlog_max == 100
    assert [b.count for b in session.histogram.buckets] == [1]
    assert (age.dataset, age.hop, age.metric) == (
        "oanda-1:live",
        ops.AGE_HOP_EDGE,
        ops.LATENCY_METRIC_AGE,
    )
    shown = latency.session_latency()[0]
    assert shown.rtt.p99_ns and shown.reconnects == 1
    assert shown.feed_delay[0].dataset == "oanda-1:live"
    assert shown.ceiling is not None and shown.ceiling.rtt_p99_ns == 250_000_000
    # The next interval sends its counters alone, histograms reset.
    await latency.report()
    again = recorder.on("ReportLatency")[1].snapshots
    assert [s.histogram.total for s in again] == [0]


def test_a_value_is_confirmed_by_its_datasets_liveness_after_it() -> None:
    liveness = Liveness()
    assert liveness.keep(ops.DatasetLiveness(dataset="oanda-1:live", alive_at_ns=50))
    assert not liveness.keep(ops.DatasetLiveness(dataset="oanda-1:live", alive_at_ns=40))
    price = ops.Price(
        meta=ops.ObservationMeta(
            source=ops.Source(dataset="oanda-1:live"),
            source_times=[ops.SourceTime(kind=ops.SOURCE_TIME_KIND_EVENT, at_ns=10)],
        )
    )
    assert confirmed_ns(price) == 10 and confirmed_ns(price, liveness) == 50


def _sessions() -> ops.TradingSessions:
    weekdays = [ops.WEEKDAY_MONDAY + n for n in range(5)]
    return ops.TradingSessions(
        time_zone="America/New_York",
        sessions=[
            ops.TradingSession(weekdays=weekdays, start_minute=570, end_minute=960),
            ops.TradingSession(
                weekdays=weekdays, start_minute=960, end_minute=1200, extended=True
            ),
        ],
        early_closes=[
            ops.TradingSessionDay(
                date="2026-11-27",
                sessions=[ops.TradingSession(start_minute=570, end_minute=780)],
            )
        ],
    )


def _ny(text: str) -> int:
    from datetime import datetime
    from zoneinfo import ZoneInfo

    at = datetime.fromisoformat(text).replace(tzinfo=ZoneInfo("America/New_York"))
    return int(at.timestamp()) * 10**9


def test_a_moment_is_in_session_by_the_venues_sessions_and_early_closes() -> None:
    sessions = _sessions()
    assert in_session(sessions, _ny("2026-10-20T10:00"))
    assert not in_session(sessions, _ny("2026-10-20T17:00"))
    assert in_session(sessions, _ny("2026-10-20T17:00"), extended=True)
    assert not in_session(sessions, _ny("2026-10-24T10:00")), "a Saturday"
    assert in_session(sessions, _ny("2026-11-27T12:00"))
    assert not in_session(sessions, _ny("2026-11-27T14:00")), "the early close"


async def test_the_ems_refuses_or_warns_on_a_stale_reference_in_session_only() -> None:
    now = _ny("2026-10-20T10:00")
    recorder = Recorder("desk-1")
    latency = Latency(recorder, clock_ns=lambda: now)
    price = ops.Price(
        meta=ops.ObservationMeta(
            source=ops.Source(dataset="alpaca-1:live"),
            source_times=[
                ops.SourceTime(kind=ops.SOURCE_TIME_KIND_EVENT, at_ns=now - 9 * 10**9)
            ],
        )
    )
    dataset = ops.DatasetRef(dataset="alpaca-1:live", stale_after_ns=30 * 10**9)
    refuse = ems.ReferenceCheck(
        after_ns=ems.after_ns([{"asset_class": "equity", "after_seconds": "5"}]),
        latency=latency,
        clock_ns=lambda: now,
    )
    stale = refuse.stale(price, dataset=dataset, asset_class="equity", sessions=_sessions())
    assert stale is not None and (stale.age_ns, stale.ceiling_ns) == (9 * 10**9, 5 * 10**9)
    await refuse.hold(recorder, "ORD-1", stale)
    held = recorder.on("SetWorkingCondition")[0]
    assert (held.condition, held.hold_cause) == (
        ops.ORDER_CONDITION_HELD,
        ops.HOLD_CAUSE_REFERENCE_PRICE_STALE,
    )
    assert refuse.placement(stale) == {}
    warn = ems.ReferenceCheck(
        action="warn", after_ns={"equity": 5 * 10**9}, clock_ns=lambda: now
    )
    assert warn.placement(stale) == {"stale_reference": stale}
    # A delayed dataset is judged against its delay plus the ceiling.
    delayed = ops.DatasetRef(dataset="alpaca-1:live", declared_delay_ns=15 * 10**9)
    assert refuse.stale(price, dataset=delayed, asset_class="equity") is None
    # Out of session nothing is stale.
    saturday = ems.ReferenceCheck(
        after_ns={"equity": 1}, clock_ns=lambda: _ny("2026-10-24T10:00")
    )
    assert saturday.stale(price, asset_class="equity", sessions=_sessions()) is None
    assert latency.ages, "its age recorded at the ems_check hop"


def test_an_rfq_placements_quotes_are_offered_best_first() -> None:
    def quote(n: int, price: str, side: int = ops.SIDE_SELL) -> ops.PlacementQuote:
        return ops.PlacementQuote(
            quote_id=f"PQT-{n}",
            side=side,
            price=ops.Money(amount=meridian.operations._decimal(Decimal(price), "p")),
            received_at_ns=n,
            outcome=ops.PLACEMENT_QUOTE_OUTCOME_OPEN,
        )

    offers = ops.Placement(quotes=[quote(1, "1.0852"), quote(2, "1.0850"), quote(3, "1.0851")])
    assert [q.quote_id for q in ems.open_quotes(offers)] == ["PQT-2", "PQT-3", "PQT-1"]
    bids = ops.Placement(
        quotes=[quote(1, "1.0848", ops.SIDE_BUY), quote(2, "1.0849", ops.SIDE_BUY)]
    )
    assert [q.quote_id for q in ems.open_quotes(bids)] == ["PQT-2", "PQT-1"]


# ── The data role: edge age, liveness, declared delay, terms (479) ──────────


async def test_a_wants_rows_carry_their_edge_age_and_a_heartbeat_its_liveness() -> None:
    from meridian.roles import data

    recorder = Recorder("oanda-1")
    latency = Latency(recorder, clock_ns=lambda: 2_000)
    wants = data.Wants(recorder, ("live",), clock_ns=lambda: 2_000, latency=latency)
    price = meridian.Price(
        meta=meridian.ObservationMeta(
            row_key="EUR_USD:live",
            source=ops.Source(dataset="oanda-1:live"),
            source_times=[meridian.SourceTime(kind="event", at_ns=1_500)],
        ),
        kind="mid",
        price=meridian.Money(Decimal("1.0850"), "USD"),
    )
    await wants.record("prices", [price], "live")
    assert latency.ages[("oanda-1:live", ops.AGE_HOP_EDGE)].min_ns == 500
    # Pulled for a read of the past: no age recorded.
    await wants.record("prices", [price], "live", want_id="WNT-PAST")
    assert latency.ages[("oanda-1:live", ops.AGE_HOP_EDGE)].total == 1
    await wants.liveness("live", venue_id="VEN-01JOANDA")
    alive = recorder.on("RecordLiveness")[0].liveness[0]
    assert (alive.dataset, alive.venue_id, alive.alive_at_ns) == (
        "oanda-1:live",
        "VEN-01JOANDA",
        2_000,
    )


def test_a_licence_sets_both_derived_use_answers_and_a_dataset_its_delay() -> None:
    from meridian.v1 import sidecar_pb2

    assert meridian.DatasetLicence(derived_use=True)._wire().derived_use_terms == (
        sidecar_pb2.DERIVED_USE_NOT_RESTRICTED
    )
    plain = meridian.DatasetLicence(kept=True)
    assert (plain.derived_use, plain.derived_use_terms) == (False, "internal_only")
    licensed = meridian.DatasetLicence(derived_use_terms="redistribution_needs_licence")
    assert licensed.derived_use is True
    assert licensed._to_json()["derived_use_terms"] == "redistribution_needs_licence"
    with pytest.raises(ValueError, match="disagrees"):
        meridian.DatasetLicence(derived_use=False, derived_use_terms="not_restricted")
    delayed = meridian.DatasetDeclaration(
        key="delayed",
        vendor="Tiingo",
        data_types=["meridian.v1.Price"],
        modes=["pull"],
        declared_delay_ns=15 * 60 * 10**9,
    )
    assert delayed._wire().declared_delay_ns == 15 * 60 * 10**9
    assert delayed._to_json()["declared_delay_ns"] == 15 * 60 * 10**9
    with pytest.raises(ValueError, match="declared_delay_ns"):
        meridian.DatasetDeclaration(
            key="x", vendor="v", data_types=["meridian.v1.Price"], modes=["pull"],
            declared_delay_ns=-1,
        )  # fmt: skip


def test_latencys_settings_are_typed_tables_and_a_choice() -> None:
    @meridian.settings
    class Config:
        session_ceilings: list = meridian.session_ceilings()  # type: ignore[type-arg]
        dataset_thresholds: list = meridian.dataset_thresholds()  # type: ignore[type-arg]
        stale_reference_action: str = meridian.stale_reference_action()
        stale_reference_after: list = meridian.stale_reference_after()  # type: ignore[type-arg]

    declared = {s.name: s for s in Config.declared()}  # type: ignore[attr-defined]
    assert [c.name for c in declared["session_ceilings"].columns][:3] == [
        "connection",
        "session",
        "rtt_p99",
    ]
    assert declared["stale_reference_action"].default == "refuse"
    assert [c.value for c in declared["stale_reference_action"].choices] == ["refuse", "warn"]
    ceilings = meridian.ceilings_from(
        [{"connection": "c", "session": "fix-order", "rtt_p99": 2000, "gaps_per_hour": 3}]
    )
    held = ceilings("fix-order")
    assert (held.rtt_p99_ns, held.gaps_per_hour) == (2_000_000_000, 3)
    assert ceilings("other") is None


# ── Connectivity: placement types, RFQ quotes, latency, the queued fixes ────

from datetime import UTC, datetime  # noqa: E402

from meridian.roles.connectivity import (  # noqa: E402
    WORKING,
    Asked,
    Change,
    VenueOrder,
    VenueQuote,
    testing,
)

CODE = "RFQ-ACCT-1"
WHEN = datetime(2026, 9, 29, 14, 30, tzinfo=UTC)


class RfqVenue:
    """A dealer-to-client venue in memory: it takes DMA and RFQ placements,
    answers a quote request with two dealers' quotes, and makes an order of
    the quote accepted."""

    statuses = {"open": WORKING, "filled": "filled"}
    sides = {ops.SIDE_BUY: "buy", ops.SIDE_SELL: "sell"}
    sides_said = {"buy": ops.SIDE_BUY, "sell": ops.SIDE_SELL}
    source = "dealers"

    def __init__(self) -> None:
        self.kept: list[tuple[str, dict[str, Any]]] = []
        self.requested: list[Asked] = []
        self.accepted: list[str] = []
        self.placed: list[Asked] = []
        self.expire = False

    def accounts(self) -> tuple[str, ...]:
        return (CODE,)

    def catalogue(self, code: str) -> Any:
        return (
            (ops.ORDER_TYPE_LIMIT, (ops.TIME_IN_FORCE_DAY, ops.TIME_IN_FORCE_GOOD_TILL_DATE)),
            (ops.ORDER_TYPE_REQUEST_FOR_QUOTE, (ops.TIME_IN_FORCE_DAY,)),
        )

    def placement_types(self, code: str) -> tuple[int, ...]:
        return (ops.PLACEMENT_TYPE_RFQ,)

    def keep(self, name: str, record: dict[str, Any]) -> str:
        self.kept.append((name, record))
        return f"rfq/{name}-{len(self.kept)}"

    def place(self, code: str, asked: Asked) -> tuple[VenueOrder, str]:
        self.placed.append(asked)
        return VenueOrder("V-1", asked.placement_id, "open", placed_at=WHEN), self.keep("p", {})

    def orders(self, code: str) -> tuple[list[VenueOrder], str]:
        return [], self.keep("orders", {})

    def cancel(self, code: str, order_id: str) -> str:
        return ""

    def replace(self, code: str, order: Any, order_id: str, change: Change) -> Any:
        return None, ""

    def not_replaceable(self, change: Change) -> str:
        return ""

    def request_quotes(self, code: str, asked: Asked) -> tuple[str, str]:
        self.requested.append(asked)
        return "QR-1", self.keep("quote-request", {"client_order_id": asked.placement_id})

    def quotes(self, code: str, request_id: str) -> tuple[list[VenueQuote], str]:
        status = "expired" if self.expire else "open"
        return [
            VenueQuote("DLR-A", "Q-A", "sell", Decimal("1.0852"), Decimal(1_000_000),
                       received_at=WHEN, status=status),
            VenueQuote("DLR-B", "Q-B", "sell", Decimal("1.0850"), Decimal(1_000_000),
                       received_at=WHEN),
        ], self.keep("quotes", {"request": request_id})  # fmt: skip

    def accept_quote(
        self, code: str, request_id: str, quote: VenueQuote, asked: Asked
    ) -> tuple[VenueOrder, str]:
        self.accepted.append(quote.dealer_quote_id)
        return VenueOrder("V-RFQ-1", asked.placement_id, "open", placed_at=WHEN), self.keep(
            "accepted", {"quote": quote.dealer_quote_id}
        )


class RfqRig(testing.Rig):
    instance = "dealers-1"
    code = CODE
    source = "dealers"

    def connect(self, broker: Any) -> Any:
        return broker or RfqVenue()


def _minted(params: Any) -> ops.ReportPlacementQuoteResult:
    quote = ops.PlacementQuote(
        quote_id=params.quote_id or f"PQT-{params.dealer_quote_id}",
        dealer_quote_id=params.dealer_quote_id,
    )
    return ops.ReportPlacementQuoteResult(placement=ops.Placement(quotes=[quote]))


async def test_an_rfq_placement_records_each_dealers_quote_and_accepts_the_pick() -> None:
    recorder = Recorder("dealers-1")
    recorder.answer(
        "ResolveVenue",
        lambda p: ops.ResolveVenueResult(
            found=True, venue=ops.VenueRecord(venue_id=f"VEN-{p.identifiers[0].value}")
        ),
    )
    recorder.answer("ReportPlacementQuote", _minted)
    rig = RfqRig(recorder)
    held = rig.placement(placement_type=ops.PLACEMENT_TYPE_RFQ)
    rig.holds(held, order_type=ops.ORDER_TYPE_REQUEST_FOR_QUOTE)
    await rig.hear(held)
    venue = rig.venue
    assert [a.placement_id for a in venue.requested] == [held.placement_id]
    first = recorder.on("ReportPlacementQuote")
    assert [(q.dealer_id, q.dealer_quote_id, q.outcome) for q in first] == [
        ("VEN-DLR-A", "Q-A", ops.PLACEMENT_QUOTE_OUTCOME_OPEN),
        ("VEN-DLR-B", "Q-B", ops.PLACEMENT_QUOTE_OUTCOME_OPEN),
    ]
    assert check(suite("connectivity").case("records-a-dealers-quote-on-an-rfq-placement"),
                 recorder) is None  # fmt: skip
    # A quote expiring is recorded once, on the next read.
    venue.expire = True
    await rig.poll()
    await rig.poll()
    expired = [q for q in recorder.on("ReportPlacementQuote") if q.quote_id == "PQT-Q-A"]
    assert [q.outcome for q in expired] == [ops.PLACEMENT_QUOTE_OUTCOME_EXPIRED]
    # The ems picks the second dealer's: accepted once, the other not picked.
    picked = ops.Placement()
    picked.CopyFrom(held)
    picked.picked_quote_id = "PQT-Q-B"
    picked.quotes.extend(
        [
            ops.PlacementQuote(quote_id="PQT-Q-A", dealer_id="VEN-DLR-A", dealer_quote_id="Q-A",
                               outcome=ops.PLACEMENT_QUOTE_OUTCOME_EXPIRED),
            ops.PlacementQuote(quote_id="PQT-Q-B", dealer_id="VEN-DLR-B", dealer_quote_id="Q-B",
                               side=ops.SIDE_SELL, outcome=ops.PLACEMENT_QUOTE_OUTCOME_PICKED,
                               price=testing.money("1.0850")),
        ]
    )  # fmt: skip
    await rig.hear(picked)
    await rig.hear(picked)
    assert venue.accepted == ["Q-B"]
    outcomes = [(q.quote_id, q.outcome) for q in recorder.on("ReportPlacementQuote")][-1:]
    assert outcomes == [("PQT-Q-B", ops.PLACEMENT_QUOTE_OUTCOME_ACCEPTED)]
    acknowledged = recorder.on("ReportPlacement")[-1]
    assert acknowledged.venue_order_id == "V-RFQ-1"


async def test_a_placement_type_the_venue_does_not_take_is_rejected_unsupported() -> None:
    recorder = Recorder("dealers-1")
    rig = RfqRig(recorder)
    held = rig.placement(placement_type=ops.PLACEMENT_TYPE_CARE)
    rig.holds(held)
    await rig.hear(held)
    rejected = recorder.on("ReportPlacement")[0]
    assert rejected.rejection_reason == ops.REJECTION_REASON_UNSUPPORTED
    assert (
        rig.venue.kept[-1][1]["stated"]["why"]
        == "the account's catalogue lists no such placement type"
    )
    await rig.trader.publish(fresh=True)
    catalogue = recorder.on("ReportVenueCatalogue")[0].catalogue
    assert list(catalogue.placement_types) == [ops.PLACEMENT_TYPE_DMA, ops.PLACEMENT_TYPE_RFQ]


async def test_a_good_till_date_order_is_asked_with_its_expiry_and_latency_kept() -> None:
    recorder = Recorder("dealers-1")
    rig = RfqRig(recorder)
    held = rig.placement(tif=ops.TIME_IN_FORCE_GOOD_TILL_DATE)
    rig.holds(held, expire_date="2026-10-30")
    order = rig.orders[0]
    order.expire_date = "2026-10-30"
    await rig.hear(held)
    assert rig.venue.placed[0].expire_date == "2026-10-30"
    shown = rig.latency.session_latency()
    assert shown and shown[0].session == "orders"
    assert rig.latency.sessions["orders"].histograms[ops.LATENCY_METRIC_ORDER_ACK].total == 1


async def test_a_venue_originated_order_is_resolved_by_every_identifier_it_states() -> None:
    from meridian.roles.connectivity._trader import Originated

    recorder = Recorder("dealers-1")
    recorder.answer(
        "ResolveIdentifier",
        lambda _: ops.ResolveIdentifierResult(found=True, instrument_id="INS-X"),
    )
    rig = RfqRig(recorder)
    figi = ops.Identifier(scheme="figi", value="BBG000B9XRY4")
    order = VenueOrder("V-9", "", "filled", symbol="AAPL", identifiers=(figi,), currency="USD")
    held = Originated(
        venue_order_id="V-9", code=CODE, client_order_id="", symbol="AAPL", side=1
    )
    assert await rig.trader._originated_instrument(rig.venue, held, WHEN, order)
    asked = recorder.on("ResolveIdentifier")[0]
    assert [i.scheme for i in asked.identifiers] == ["figi", "symbol"]
    assert asked.stated_currency == "USD" and held.currency == "USD"
    assert not recorder.on("ResolveInstrument"), (
        "the stated currency is taken, not the record's"
    )


async def test_a_replace_rejected_unsupported_names_its_venue_account() -> None:
    recorder = Recorder("dealers-1")
    rig = RfqRig(recorder)
    held = rig.placement()
    rig.holds(held)
    await rig.hear(held)
    working = rig.placement(state=ops.PLACEMENT_STATE_WORKING, venue_order_id="V-1")
    asked = testing.asking(
        working,
        ops.PLACEMENT_CHANGE_KIND_REPLACE,
        time_in_force=ops.TIME_IN_FORCE_IMMEDIATE_OR_CANCEL,
    )
    rig.holds(asked)
    await rig.hear(asked)
    named, said = rig.venue.kept[-1]
    assert named == "offered" and said["venue_account_code"] == CODE


# ── Event contracts: a range member's bounds (464), keep_events ─────────────

from fake_venues import contracts_venue  # noqa: E402
from meridian.roles.data import event_contracts  # noqa: E402


async def test_a_range_members_bounds_are_reported_with_its_group_and_events_kept() -> None:
    v = contracts_venue
    lake = Lake(v.VENUE)
    feed = event_contracts.Feed(
        lake, v.market(v.NOW_NS), event_contracts.ContractMap(), clock_ns=lambda: v.NOW_NS
    )
    contract = await feed.contract(v.EVENT.members[0])
    assert contract is not None
    bounded = event_contracts.Contract(
        code=contract.code,
        title=contract.title,
        binary=True,
        payout=contract.payout,
        floor=event_contracts.Bound(Decimal("89"), True),
        cap=event_contracts.Bound(Decimal("90"), False),
        bound_unit="degrees_f",
    )
    asked = feed.market.contract

    def with_bounds(code: str, watching: bool = False) -> Any:
        return bounded if code == contract.code else asked(code, watching)

    feed.market.contract = with_bounds  # type: ignore[method-assign]
    feed.contracts = event_contracts.ContractMap()
    for code in v.EVENT.members:
        await lake.held(feed, code)
    await feed.report_event(v.EVENT)
    sent = lake.on("ReportEventGroup")[0]
    assert [(b.bound_unit, b.floor.inclusive, b.cap.inclusive) for b in sent.member_bounds] == [
        ("degrees_f", True, False)
    ]
    # keep_events: read once first served, reported, and not again unchanged.
    mapped = feed.contracts.mapped()
    ref = mapped[0].contract.market if mapped else ""
    feed.market.event = lambda r: v.EVENT if r == ref else None  # type: ignore[attr-defined]
    if ref:
        clock = iter([0.0, 1.0, 2.0, 700.0, 701.0])
        assert await feed.keep_events(once=True, clock=lambda: next(clock)) in (0, 1)
        assert await feed.keep_events(once=True, clock=lambda: next(clock)) == 0


# ── Shared pages: Trading, one Connection for both roles (457), raw records ─

import re  # noqa: E402
from dataclasses import dataclass as _dataclass  # noqa: E402
from dataclasses import field as _field  # noqa: E402

from meridian.roles import connectivity as _connectivity  # noqa: E402
from meridian.roles import data as _data  # noqa: E402
from meridian.testing import PageClient  # noqa: E402


@_dataclass
class _State:
    trader: Any = None
    venue: Any = None
    scope: Any = _field(default_factory=meridian.AccountScope)
    store: dict[str, Any] = _field(default_factory=dict)
    values: dict[str, Any] = _field(default_factory=dict)


def _rigged() -> tuple[RfqRig, _State]:
    recorder = Recorder("dealers-1")
    rig = RfqRig(recorder)
    rig.trader.reached = (CODE, "OTHER-ACCT")
    venue = rig.venue
    venue.environment = "paper"  # type: ignore[attr-defined]
    return rig, _State(trader=rig.trader, venue=venue, scope=rig.scope)


def _words() -> dict[str, Any]:
    return {
        "venue": "Dealers",
        "credentials": lambda: [_data.Credential("API key", True)],
        "environment": lambda: "Paper (simulated money)",
        "environment_setting": lambda: "paper",
    }


def test_the_trading_page_is_the_sdks_with_its_badge_its_acts_and_sessions() -> None:
    rig, state = _rigged()
    rig.latency.rtt("orders", 12_000_000)
    pages = meridian.Pages("Dealers", kit="0.12.0")
    _connectivity.trading_pages(pages, lambda: state, latency=lambda: rig.latency, **_words())
    client = PageClient(pages, rig.recorder)
    shown = client.get(_connectivity.TRADING, "admin").text
    for said in ("Demo", "paper host", "<h2>Sessions</h2>", "Enable trading"):
        assert said in shown, said
    data = client.call_tool("read_trading", level="admin").data
    assert (data["badge"], data["reached_environment"]) == ("Demo", "paper")
    assert data["session_latency"][0]["session"] == "orders"
    checked = client.call_tool(
        "check_enable_trading", {"venue_account_code": "OTHER-ACCT"}, level="admin"
    )
    assert "Would enable trading on OTHER-ACCT" in checked.data["said"]
    refused = client.call_tool(
        "check_enable_trading", {"venue_account_code": "NOT-REACHED"}, level="admin"
    )
    assert refused.outcome == "refused"
    enabled = client.call_tool(
        "enable_trading", {"venue_account_code": "OTHER-ACCT"}, level="admin"
    )
    assert enabled.status == 200 and rig.trader.trading_on("OTHER-ACCT")


def test_a_plugin_holding_data_and_connectivity_draws_one_connection() -> None:
    rig, state = _rigged()
    pages = meridian.Pages("Dealers", kit="0.12.0")

    async def connection(request: Any) -> _data.ConnectionRead:
        return _data.ConnectionRead(
            mode="Sandbox", credentials=[_data.Credential("API key", True)]
        )

    _connectivity.connection_pages(pages, lambda: state, connection, **_words())
    client = PageClient(pages, rig.recorder)
    shown = client.get("/", "admin").text
    sections = re.findall(r"<h2>([^<]*)</h2>", shown)
    assert sections == [
        "Key", "Limits and use", "Stream", "Sessions", "Environment", "Accounts", "Placements",
    ]  # fmt: skip
    data = client.call_tool("read_connection", level="admin").data
    assert data["mode"] == "Sandbox" and data["trading"]["badge"] == "Demo"
    assert (
        client.call_tool(
            "check_enable_trading", {"venue_account_code": "OTHER-ACCT"}, level="admin"
        ).data["venue_account_code"]
        == "OTHER-ACCT"
    )
    with pytest.raises(KeyError, match="no tool read_trading"):
        client.call_tool("read_trading", level="admin")


def test_raw_records_show_a_record_to_a_reader_of_its_mapped_account() -> None:
    rig, state = _rigged()
    state.store["trading/placed-1"] = {"client_order_id": "PLC-1"}
    pages = meridian.Pages("Dealers", kit="0.12.0")
    _connectivity.raw_records_page(pages, lambda: state, kinds=[], why="read in the book")
    reader = PageClient(pages, rig.recorder, read=[testing.ACCOUNT])
    shown = reader.get(_connectivity.RAW, "read", ref="trading/placed-1").text
    assert "The record" in shown and "PLC-1" in shown
    stranger = PageClient(pages, rig.recorder, read=["ACC-ELSEWHERE"])
    assert (
        "The record" not in stranger.get(_connectivity.RAW, "read", ref="trading/placed-1").text
    )
