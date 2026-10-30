"""A plugin's side of every case contract v28 adds to the role suites, each
through the SDK's v28 helpers: listed options' and futures' chains
(`meridian.roles.chains`), their lifecycle (`.lifecycle`), package orders
(`.packages`), a signal's derived series, saved scenarios and escalation
(`.signal`), the filings slice (`.data.filings`), the edge's quality checks
(`.data.quality`), the latency reports sent (`roles.Latency.report`) and the
stale-reference actions permitted (`roles.ems.ReferenceCheck.permitted`).

`DATA` holds the data suite's, which tests/test_lake.py's toy plugin maps;
`PRODUCERS` every other role's, which tests/order_path_cases.py's map
carries for tests/test_v22.py to run in each suite holding it.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from datetime import UTC, date, datetime
from decimal import Decimal

import meridian
from meridian.plugin.v1 import operations_pb2 as ops
from meridian.roles import Latency, chains, ems, lifecycle, packages, signal
from meridian.roles.data import Wants, filings
from meridian.roles.data.quality import Baseline, OutlierThresholds
from meridian.roles.data.testing import feed_delay
from meridian.suites import Recorder
from meridian.testing import caller_header

Producer = Callable[[Recorder], Awaitable[None]]

ACCOUNT = "ACC-1"
AAPL = "INS-01JC24AAPL00000000000001"
AAPL_CALL = "INS-01JC28AAPLC2611200000001"
AAPL_CALL_235 = "INS-01JC28AAPLC2611200000002"
APPLE = "ENT-01JC28APPLEINC000000000001"
LISTED_OPTION = "TPL-01JC28LISTEDOPTION0000001"
CALL = chains.osi_symbol("AAPL", "2026-11-20", "call", Decimal("230"))
PUT = chains.osi_symbol("AAPL", "2026-11-20", "put", Decimal("230"))
NOW_NS = 1_792_800_000_000_000_000
EXPIRY = date(2026, 11, 20)


def usd(amount: str) -> meridian.Money:
    return meridian.Money(Decimal(amount), "USD")


def heard(row: str, arm: str, message: object) -> Producer:
    async def produce(recorder: Recorder) -> None:
        recorder.answer(row, lambda _: message)

        async def kept(_: object) -> None:
            return None

        await recorder.receive(**{arm: kept})

    return produce


# ── The data suite ───────────────────────────────────────────────────────


async def records_a_chains_series(recorder: Recorder) -> None:
    series = [
        chains.option_series(
            AAPL,
            symbol,
            template_id=LISTED_OPTION,
            template_version="1",
            dataset=f"{recorder.identity.instance_id}:options",
            currency="USD",
            exercise_style="EXERCISE_STYLE_AMERICAN",
            settlement_method="SETTLEMENT_METHOD_PHYSICAL",
            deliverable=[(AAPL, 100)],
            valid_from_ns=NOW_NS,
            raw=recorder.raw_record("chains/AAPL/2026-11-20"),
        )  # fmt: skip
        for symbol in (CALL, PUT)
    ]
    await recorder.record_series(series=series)


async def records_open_interest(recorder: Recorder) -> None:
    oi = chains.statistic(
        AAPL, chains.osi_key(PUT), "open_interest", 12834, "2026-10-23",
        dataset=f"{recorder.identity.instance_id}:options", valid_from_ns=NOW_NS,
    )  # fmt: skip
    await recorder.record_statistics(statistics=[oi])


async def a_chain_row_is_never_resolved(recorder: Recorder) -> None:
    # The chain's quotes under the underlying, keyed by each series' OSI
    # symbol: no series is resolved, nothing minted.
    quotes = [
        meridian.Quote(
            meta=chains.series_meta(
                AAPL,
                chains.osi_key(symbol),
                row_key=f"{symbol}:q:{NOW_NS}",
                dataset=f"{recorder.identity.instance_id}:options",
                valid_from_ns=NOW_NS,
            ),  # fmt: skip
            bid=usd("4.10"),
            ask=usd("4.25"),
        )
        for symbol in (CALL, PUT)
    ]
    await recorder.record_quotes(quotes=quotes)


FILINGS = "filings"
EIGHT_K = filings.ref("0000320193-26-000105", "8-K")
TEN_K = filings.ref("0000320193-26-000107", "10-K")


async def _filer(recorder: Recorder) -> str:
    return await filings.Companies(recorder).filer(320193)


async def a_filing_recorded(recorder: Recorder) -> None:
    filer = await _filer(recorder)
    row = filings.filing(
        filer, EIGHT_K.accession_number, "8-K", "current_report", "2026-10-30",
        dataset=f"{recorder.identity.instance_id}:{FILINGS}", items=["2.02", "9.01"],
        valid_from_ns=NOW_NS, published_ns=NOW_NS + 600_000_000_000,
    )  # fmt: skip
    await recorder.record_filings(filings=[row])


def _eps(recorder: Recorder, filer: str, amount: str, filed_in: ops.FilingRef) -> object:
    return filings.fact(
        filer, "us-gaap:EarningsPerShareBasic", "2026-09-27", filed_in,
        dataset=f"{recorder.identity.instance_id}:facts",
        row_key="320193:us-gaap:EarningsPerShareBasic:USD/shares:2026-06-28:2026-09-27",
        amount=usd(amount), period_start="2026-06-28",
    )  # fmt: skip


async def a_fact_restated(recorder: Recorder) -> None:
    filer = await _filer(recorder)
    await recorder.record_reported_facts(facts=[_eps(recorder, filer, "1.85", EIGHT_K)])
    await recorder.record_reported_facts(facts=[_eps(recorder, filer, "1.84", TEN_K)])


async def a_fact_confirmed(recorder: Recorder) -> None:
    filer = await _filer(recorder)
    for filed_in in (EIGHT_K, TEN_K):
        await recorder.record_reported_facts(facts=[_eps(recorder, filer, "1.85", filed_in)])


THIRTEEN_F = filings.ref("0001067983-26-000045", "13F-HR")


async def a_complete_holdings_report(recorder: Recorder) -> None:
    holder = await filings.Companies(recorder).filer(1067983)
    report = filings.holdings_report(
        holder, THIRTEEN_F, "form_13f", "2026-09-30",
        dataset=f"{recorder.identity.instance_id}:13f", complete=True,
    )  # fmt: skip
    await recorder.record_holdings_reports(reports=[report])
    row = filings.holding(report, AAPL, "037833100", shares=300_000_000,
                          market_value=usd("69000000000"))  # fmt: skip
    await recorder.record_holdings(holdings=[row])


async def a_cusip_used_as_key(recorder: Recorder) -> None:
    holder = await filings.Companies(recorder).filer(1067983)
    found = await recorder.resolve_identifier(
        identifiers=[ops.Identifier(scheme=filings.CUSIP, value="037833100")], as_of_ns=NOW_NS
    )
    report = filings.holdings_report(
        holder, THIRTEEN_F, "form_13f", "2026-09-30",
        dataset=f"{recorder.identity.instance_id}:13f", complete=True,
    )  # fmt: skip
    row = filings.holding(report, found.instrument_id, "037833100", shares=300_000_000)
    await recorder.record_holdings(holdings=[row])


async def a_stake_crossed(recorder: Recorder) -> None:
    holder = await filings.Companies(recorder).filer(1067983)
    for n, (form, percent) in enumerate((("SC 13D", "5.2"), ("SC 13D/A", "7.9"))):
        filed = filings.ref(f"0001067983-26-00005{n}", form)
        report = filings.holdings_report(
            holder, filed, "schedule_13d", "2026-10-20",
            dataset=f"{recorder.identity.instance_id}:13dg",
        )  # fmt: skip
        await recorder.record_holdings_reports(reports=[report])
        row = filings.holding(report, AAPL, "037833100", percent_of_class=Decimal(percent))
        await recorder.record_holdings(holdings=[row])


async def a_dividend_declared(recorder: Recorder) -> None:
    issuer = await _filer(recorder)
    row = filings.dividend(
        AAPL, issuer, usd("0.26"), dataset=f"{recorder.identity.instance_id}:dividends",
        row_key=f"{EIGHT_K.accession_number}:dividend", declared_date="2026-10-30",
        ex_date="2026-11-10", record_date="2026-11-10", payment_date="2026-11-13",
        rule=("edgar_8k_dividend", 1), filed_in=EIGHT_K,
    )  # fmt: skip
    await recorder.record_corporate_actions(actions=[row])


async def a_rating_action(recorder: Recorder) -> None:
    companies = filings.Companies(recorder)
    rated = await companies.resolve(filings.LEI, "HWUPKR0MPOU8FGXBT394")
    rater = await companies.resolve(filings.LEI, "549300GBTL8FTQTB8Y20")
    row = filings.rating_action(
        rated, rater, "Aaa", "long-term issuer", "affirmed",
        dataset=f"{recorder.identity.instance_id}:ratings_moodys",
        row_key=f"moodys:issuer:{rated}:2026-05-02",
    )  # fmt: skip
    await recorder.record_rating_actions(actions=[row])


async def resolves_a_filer(recorder: Recorder) -> None:
    await _filer(recorder)


def _quote(n: int, bid: str, ask: str, at_ns: int) -> meridian.Quote:
    return meridian.Quote(
        meta=meridian.ObservationMeta(
            row_key=f"BTC-USD:q:{n}",
            subjects=[meridian.SubjectRef(entity_id="INS-suite-1")],
            source=ops.Source(dataset="suite-plugin:live"),
            source_times=[meridian.SourceTime(kind="event", at_ns=at_ns)],
        ),
        bid=usd(bid),
        ask=usd(ask),
    )


def _wants(recorder: Recorder) -> Wants:
    return Wants(recorder, ("live",), clock_ns=lambda: NOW_NS)


async def a_crossed_quote_is_recorded_invalid(recorder: Recorder) -> None:
    await _wants(recorder).record("quotes", [_quote(1, "62511.00", "62510.02", NOW_NS)], "live")


async def a_duplicate_is_recorded_suspicious(recorder: Recorder) -> None:
    wants = _wants(recorder)
    for n in (1, 2):  # the same quote again, under its new sequence number
        await wants.record("quotes", [_quote(n, "62510.00", "62510.02", NOW_NS)], "live")


async def rows_after_a_gap_are_suspicious(recorder: Recorder) -> None:
    wants = _wants(recorder)
    for n, bid in ((1, "62510.00"), (3, "62509.00")):
        wants.edge().sequenced("live", n)
        await wants.record("quotes", [_quote(n, bid, "62510.02", NOW_NS)], "live")


async def _aged(recorder: Recorder, latency: Latency) -> None:
    wants = _wants(recorder)
    wants.latency = latency
    await wants.record("quotes", [_quote(1, "62510.00", "62510.02", NOW_NS - 400_000)], "live")


DATA: dict[str, Producer] = {
    "records-a-chains-series": records_a_chains_series,
    "records-open-interest": records_open_interest,
    "a-chain-row-is-never-resolved": a_chain_row_is_never_resolved,
    "a-filing-recorded": a_filing_recorded,
    "a-fact-restated": a_fact_restated,
    "a-fact-confirmed": a_fact_confirmed,
    "a-complete-holdings-report": a_complete_holdings_report,
    "a-cusip-used-as-key": a_cusip_used_as_key,
    "a-stake-crossed": a_stake_crossed,
    "a-dividend-declared": a_dividend_declared,
    "a-rating-action": a_rating_action,
    "resolves-a-filer": resolves_a_filer,
    "a-crossed-quote-is-recorded-invalid": a_crossed_quote_is_recorded_invalid,
    "a-duplicate-is-recorded-suspicious": a_duplicate_is_recorded_suspicious,
    "rows-after-a-gap-are-suspicious": rows_after_a_gap_are_suspicious,
    "reports-its-feed-delay": feed_delay(_aged),
}


# ── The readers ──────────────────────────────────────────────────────────


async def reads_a_derived_series(recorder: Recorder) -> None:
    await signal.read_derived(recorder, AAPL, ["iv30"], "2025-10-23", "2026-10-23")


async def reads_a_saved_scenario_set(recorder: Recorder) -> None:
    await signal.read_scenarios(recorder, ["grid:price-by-date"])


async def asks_for_a_series_it_wants_to_order(recorder: Recorder) -> None:
    await chains.want_series(
        recorder, AAPL, chains.osi_key(PUT), note="Proposing a protective put",
        acting_for=caller_header("write"),
    )  # fmt: skip


async def reads_an_underlyings_chain(recorder: Recorder) -> None:
    await chains.read_chain(recorder, AAPL, EXPIRY)


async def reads_an_underlyings_expirations(recorder: Recorder) -> None:
    await chains.read_expirations(recorder, AAPL)


async def reads_open_interest_for_a_chain(recorder: Recorder) -> None:
    await chains.read_open_interest(recorder, AAPL, "2026-10-23")


async def reads_an_accounts_lifecycle_events(recorder: Recorder) -> None:
    await lifecycle.read_events(recorder, ACCOUNT, "2026-11-16", "2026-11-20")


async def reads_the_stale_reference_actions_permitted(recorder: Recorder) -> None:
    check = ems.ReferenceCheck(action=ems.WARN)
    assert await check.permitted(recorder) is False  # the deployment's default
    assert check.refuses


async def proposes_a_package(recorder: Recorder) -> None:
    spread = packages.legs(
        (AAPL_CALL, "buy", 1, "open"),
        (AAPL_CALL_235, "sell", 1, "open"),
    )
    await packages.propose(recorder, ACCOUNT, spread, 2, usd("1.85"),
                           acting_for=caller_header("write"))  # fmt: skip


async def reads_a_companys_filings(recorder: Recorder) -> None:
    await recorder.list_filings(
        subjects=[meridian.SubjectRef(entity_id=APPLE)], kinds=["current_report"]
    )


async def reads_reported_facts(recorder: Recorder) -> None:
    await recorder.list_reported_facts(
        subjects=[meridian.SubjectRef(entity_id=APPLE)],
        concepts=["us-gaap:EarningsPerShareBasic"],
    )


async def reads_who_holds_a_security(recorder: Recorder) -> None:
    await recorder.list_holdings(
        subjects=[meridian.SubjectRef(entity_id=AAPL)], from_date="2026-09-30",
        to_date="2026-09-30", kinds=["form_13f"],
    )  # fmt: skip


async def reads_declared_dividends(recorder: Recorder) -> None:
    await recorder.list_corporate_actions(
        subjects=[meridian.SubjectRef(entity_id=AAPL)], kinds=["cash_dividend"],
        from_date="2026-10-24",
    )  # fmt: skip


async def reads_a_rating_history(recorder: Recorder) -> None:
    await recorder.list_rating_actions(subjects=[meridian.SubjectRef(entity_id=APPLE)])


async def releases_an_unreported_expiry(recorder: Recorder) -> None:
    proposed = ops.LifecycleEvent(
        event_id="LCE-01JC28EXPIRY0000000000001", account_id=ACCOUNT, instrument_id=AAPL_CALL,
        kind=ops.LIFECYCLE_EVENT_KIND_EXPIRY, state=ops.LIFECYCLE_EVENT_STATE_PROPOSED,
        event_date="2026-11-20",
    )  # fmt: skip
    morning = datetime(2026, 11, 21, 15, 0, tzinfo=UTC)
    assert lifecycle.due_for_release(proposed, now=morning, reported=False, still_held=False)
    await lifecycle.release(
        recorder, proposed.event_id,
        "No report by the morning after; the statement no longer shows the position",
        acting_for=caller_header("write"),
    )  # fmt: skip


async def proposes_an_exercise_by_exception(recorder: Recorder) -> None:
    expected = lifecycle.exercise_by_exception(
        ACCOUNT, AAPL_CALL, 2, EXPIRY, put_or_call="call", strike=usd("230.00"),
        close=usd("233.18"), underlying_id=AAPL,
    )  # fmt: skip
    assert expected is not None
    await lifecycle.propose(recorder, [expected])


async def records_a_derived_series(recorder: Recorder) -> None:
    value = signal.derived(
        AAPL, "iv30", Decimal("27.84"), "2026-10-23",
        dataset=f"{recorder.identity.instance_id}:derived", unit="percent",
        definition="term_and_skew", version=1,
        inputs=[("tradier-1:options", NOW_NS), ("us-treasury-1:ust_par", NOW_NS)],
    )  # fmt: skip
    await recorder.record_derived_series(values=[value])


async def saves_a_scenario_set(recorder: Recorder) -> None:
    grid = meridian.operations.ScenarioSet(
        name="Price by date",
        axes=[signal.spot_steps([-20, 0, 20]), signal.date_steps([0, 7])],
    )
    row = signal.saved(
        "grid:price-by-date",
        dataset=f"{recorder.identity.instance_id}:scenarios",
        scenario_set=grid,
        description="The Scenario grid's rows and columns",
    )
    await recorder.record_scenarios(scenarios=[row])


async def escalates_an_outlier(recorder: Recorder) -> None:
    def close(n: int, price: str) -> ops.Price:
        return ops.Price(
            meta=ops.ObservationMeta(
                row_key=f"AAPL:2026-10-{n:02d}:close", version=1,
                subjects=[ops.SubjectRef(entity_id=AAPL)],
                source=ops.Source(dataset="tiingo-1:eod"),
            ),
            price=meridian.operations._money(usd(price), "price"),
        )  # fmt: skip

    baseline = Baseline(OutlierThresholds(warm_up=5, sigma_floor=Decimal("0.5")))
    rows = [close(n, p) for n, p in enumerate(("230.1", "231.4", "229.8", "232.0", "230.9"), 1)]
    rows.append(close(23, "2309.00"))  # a misplaced decimal point
    assert await signal.escalate(recorder, baseline, rows) == 1


# ── Those who report what a broker or venue states ───────────────────────


async def reports_an_expiry(recorder: Recorder) -> None:
    await lifecycle.report(
        recorder,
        lifecycle.expiry(ACCOUNT, AAPL_CALL, 2, EXPIRY, external_event_id="EXP-88120",
                         raw_record=recorder.raw_record("history/2026-11-23/expiry/88120")),
    )  # fmt: skip


async def reports_an_assignment(recorder: Recorder) -> None:
    await lifecycle.report(
        recorder,
        lifecycle.assignment(
            ACCOUNT, AAPL_CALL, 2, EXPIRY, deliveries=[(AAPL, -200, usd("230.00"))],
            cash=usd("46000.00"), external_event_id="TRD-ASSIGN-88120",
            raw_record=recorder.raw_record("history/2026-11-23/assignment/88120"),
        ),
    )  # fmt: skip


async def reports_a_package_fill(recorder: Recorder) -> None:
    await packages.report_fill(
        recorder, placement_id="PLC-01JC28SPREAD0000000000001", venue_account_code="SIM-ACCT-7",
        venue_execution_id="EX-PKG-1", quantity=2, net_price=usd("1.85"),
        leg_fills=[
            packages.LegFill(AAPL_CALL, "buy", Decimal(2), usd("4.20"), "EX-PKG-1-L1"),
            packages.LegFill(AAPL_CALL_235, "sell", Decimal(2), usd("2.35"), "EX-PKG-1-L2"),
        ],
        trade_time_ns=NOW_NS, trade_date="2026-10-23",
    )  # fmt: skip


async def reports_a_sessions_round_trip(recorder: Recorder) -> None:
    """The session's latency over an interval -- each venue call's round
    trip, a placement's acknowledgement -- as the SDK's Trader recorded it,
    sent by `Latency.report` (0.33.0)."""
    from test_connectivity_trader import Rig

    rig = Rig(recorder)
    held = rig.placement()
    rig.holds(held)
    await rig.hear(held)
    await rig.poll()
    assert await rig.latency.report() > 0


async def reports_its_pre_trade_checks_data_age(recorder: Recorder) -> None:
    """The `ems`'s reference price checked before a placement: its age at the
    `ems_check` hop recorded, then reported."""
    now = 1_792_300_010_000_000_000
    latency = Latency(recorder, clock_ns=lambda: now)
    check = ems.ReferenceCheck(after_ns={"equity": 5_000_000_000}, latency=latency,
                               clock_ns=lambda: now)  # fmt: skip
    price = ops.Price(
        meta=ops.ObservationMeta(
            source=ops.Source(dataset="alpaca-1:live"),
            source_times=[
                ops.SourceTime(kind=ops.SOURCE_TIME_KIND_EVENT, at_ns=now - 2_000_000_000)
            ],
        )
    )
    assert check.stale(price, asset_class="equity") is None
    assert await latency.report() > 0


PRODUCERS: dict[str, Producer] = {
    "reads-a-derived-series": reads_a_derived_series,
    "reads-a-saved-scenario-set": reads_a_saved_scenario_set,
    "asks-for-a-series-it-wants-to-order": asks_for_a_series_it_wants_to_order,
    "reads-an-underlyings-chain": reads_an_underlyings_chain,
    "reads-an-underlyings-expirations": reads_an_underlyings_expirations,
    "reads-the-stale-reference-actions-permitted": reads_the_stale_reference_actions_permitted,
    "reads-open-interest-for-a-chain": reads_open_interest_for_a_chain,
    "hears-a-statistic-recorded": heard(
        "StatisticsRecorded",
        "statistics_recorded",
        ops.StatisticsRecordedEvent(statistic=ops.Statistic()),
    ),
    "reads-an-accounts-lifecycle-events": reads_an_accounts_lifecycle_events,
    "hears-a-lifecycle-event-recorded": heard(
        "LifecycleEventRecorded",
        "lifecycle_event_recorded",
        ops.LifecycleEventRecordedEvent(event=ops.LifecycleEvent(account_id=ACCOUNT)),
    ),
    "proposes-a-package": proposes_a_package,
    "reads-a-companys-filings": reads_a_companys_filings,
    "reads-reported-facts": reads_reported_facts,
    "reads-who-holds-a-security": reads_who_holds_a_security,
    "reads-declared-dividends": reads_declared_dividends,
    "reads-a-rating-history": reads_a_rating_history,
    "hears-a-filing-recorded": heard(
        "FilingsRecorded", "filings_recorded", ops.FilingsRecordedEvent(filing=ops.Filing())
    ),
    "hears-a-dividend-declared": heard(
        "CorporateActionsRecorded",
        "corporate_actions_recorded",
        ops.CorporateActionsRecordedEvent(action=ops.CorporateActionAnnounced()),
    ),
    "releases-an-unreported-expiry": releases_an_unreported_expiry,
    "proposes-an-exercise-by-exception": proposes_an_exercise_by_exception,
    "records-a-derived-series": records_a_derived_series,
    "saves-a-scenario-set": saves_a_scenario_set,
    "escalates-an-outlier": escalates_an_outlier,
    "reports-an-expiry": reports_an_expiry,
    "reports-an-assignment": reports_an_assignment,
    "reports-a-package-fill": reports_a_package_fill,
    "reports-a-sessions-round-trip": reports_a_sessions_round_trip,
    "reports-its-pre-trade-checks-data-age": reports_its_pre_trade_checks_data_age,
}
