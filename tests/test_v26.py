"""Contract v26 (sdk-contract/the-analytics-component-contract; the lake's
bounded query, sdk-contract/the-lake-has-a-bounded-query-tool): the
analytics component's job and answer, the reference computations its
engine equals exactly, the `pricing` role, event groups, the agents'
demo-only guard, and model token counts.

What this SDK decides: typed builders for a job, checked as they are built
(Q1); an answer read with `computed_as` and `scenario_key` handled in every
value from v26 (the first release's Q13, Q14); the reference computations in
`decimal` and `fractions`, pinned as canonical-JSON cases with their hashes
(requirement 36); a pricing plugin's batches answered whole and caught up
after a restart; event groups kept by version, in force at a moment; the
guard's two keys read and shown, the book's refusal the book's.
"""

from __future__ import annotations

import asyncio
import json
from decimal import Decimal
from fractions import Fraction
from pathlib import Path
from typing import Any

import pytest

import meridian
from meridian import analytics
from meridian.analytics import reference
from meridian.analytics._canonical import answer_hash, canonical, decimal_text
from meridian.operations import as_money
from meridian.plugin.v1 import operations_pb2 as ops
from meridian.roles import connectivity, pricing
from meridian.roles.data import event_contracts
from meridian.suites import Recorder, check, run, suite, suites
from meridian.testing import caller_header
from meridian.v1 import sidecar_pb2

CASES = Path(__file__).parent / "reference_cases"
USD = "INS-01J8XQ4M7K00000000CASHUSD"
AAPL = "INS-01J8XQ4M7K0000000000AAPL"


def test_the_schema_is_contract_v26() -> None:
    assert meridian.SCHEMA_VERSION == "v27"
    fields = sidecar_pb2.CallerClaims.DESCRIPTOR.fields_by_name
    assert "demo_connectivity_instance_ids" in fields
    assert "model_tokens" in sidecar_pb2.HeartbeatRequest.DESCRIPTOR.fields_by_name
    assert sidecar_pb2.REFUSAL_REASON_AGENT_LIVE_ORDER


def test_the_v26_shapes_are_the_packages() -> None:
    for name in (
        "Job",
        "WhatIf",
        "WhatIfTrade",
        "PricedUnit",
        "ScenarioKey",
        "Sensitivity",
        "ComputedAs",
        "ScenarioKind",
        "NotEvaluatedReason",
        "EventGroup",
        "EventGroupFlag",
        "EventGroups",
        "analytics",
        "reached_environment",
        "connection_badge",
        "is_demo",
    ):
        assert name in meridian.__all__ and getattr(meridian, name) is not None


# ── Canonical JSON and the answer's hash (Q7) ───────────────────────────────


def test_canonical_json_is_rfc_8785s() -> None:
    # Members sorted by their names' UTF-16 code units, no whitespace, and
    # strings escaped as ECMAScript escapes them (RFC 8785 3.2.2, 3.2.3).
    assert canonical({"b": 1, "a": [True, None, "x"]}) == b'{"a":[true,null,"x"],"b":1}'
    # By UTF-16 code units: U+20AC before U+1F600's surrogates (D83D DE00),
    # and U+1F600 before U+FFFF, which a sort by code points would reverse.
    euro, grin, last = "€", "\U0001f600", "￿"
    assert canonical({grin: 2, euro: 1, "z": 3}) == f'{{"z":3,"{euro}":1,"{grin}":2}}'.encode()
    assert canonical({last: 2, grin: 1}) == f'{{"{grin}":1,"{last}":2}}'.encode()
    assert canonical('a\u000fb\n"c\\') == b'"a\\u000fb\\n\\"c\\\\"'
    assert canonical(Decimal("227.50")) == b'"227.50"'
    with pytest.raises(TypeError, match="no float"):
        canonical(1.5)
    with pytest.raises(ValueError, match="as a string"):
        canonical(2**53)


def test_a_decimal_is_its_stated_text() -> None:
    assert [decimal_text(Decimal(t)) for t in ("1.50", "0.005", "-0.005", "100", "-0.00")] == [
        "1.50",
        "0.005",
        "-0.005",
        "100",
        "0.00",
    ]


def test_the_hash_is_sha256_over_the_canonical_json() -> None:
    import hashlib

    inputs = {"engine_version": "0.1.0", "job": {"account_ids": ["ACC-1"]}}
    assert answer_hash(inputs) == "sha256:" + hashlib.sha256(canonical(inputs)).hexdigest()
    reordered = {"job": {"account_ids": ["ACC-1"]}, "engine_version": "0.1.0"}
    assert answer_hash(reordered) == answer_hash(inputs)


# ── The reference computations, pinned (requirement 36) ─────────────────────


def _cases() -> list[Path]:
    return sorted(CASES.glob("*.json"))


def test_the_reference_cases_are_pinned() -> None:
    assert {path.stem for path in _cases()} == {
        "valuation",
        "stale-and-unconverted",
        "event-group",
        "event-group-not-exhaustive",
        "resolved-in-a-stablecoin",
        "historical-var-and-es",
        "what-if",
        "pnl-v2-realized",
        # Contract v27's (tests/test_v27.py).
        "quoted-price-past-18-places",
        "inverted-and-crossed",
        "reporting-currency",
        "execution-cost",
    }


@pytest.mark.parametrize("path", _cases(), ids=lambda path: path.stem)
def test_each_reference_case_is_canonical_and_answers_as_pinned(path: Path) -> None:
    case = reference.load(path)  # refused unless canonical, byte for byte
    answer = reference.compute(case["inputs"])
    assert answer.to_json() == case["answer"], f"{path.name}: tools/write_reference_cases.py"
    assert answer.answer_hash == answer_hash(case["inputs"])
    # The wire's mirror carries it whole, and reads back to the same JSON;
    # an execution_cost job's rows are the lake's (W10.11), never the answer's.
    on_the_wire = {k: v for k, v in case["answer"].items() if k != "execution_costs"}
    assert analytics.answer_json(analytics.answer_message(case["answer"])) == on_the_wire


def _figures(name: str, definition: str) -> list[dict[str, Any]]:
    case = reference.load(CASES / f"{name}.json")
    return [f for f in case["answer"]["figures"] if f["measure"]["definition"] == definition]


def test_the_event_group_case_is_designs_fixture() -> None:
    """fixtures/analytics/read-job-answer.yaml: each outcome's mid over the
    sum of the mids, 0.42 over 1.05; 100 YES bought at 0.42 pay 58.00."""
    distribution = _figures("event-group", "implied_distribution")
    base = [f for f in distribution if f["scenario_key"]["kind"] == "SCENARIO_KIND_BASE"]
    assert Decimal(base[0]["value"]) == Decimal("1.05")
    first = distribution[1]
    assert (Decimal(first["numerator"]), Decimal(first["denominator"])) == (
        Decimal("0.42"),
        Decimal("1.05"),
    )
    reference_case = reference.load(CASES / "event-group.json")
    # The fixture's own account: 100 YES at 0.42, and nothing else in the group.
    alone = json.loads(json.dumps(reference_case["inputs"]))
    alone["positions"] = [p for p in alone["positions"] if p["quantity"] == "100"]
    payoffs = reference.compute(alone).figures
    yes = [f for f in payoffs if f.measure[0] == "resolution_payoff"][0]
    assert yes.value == Decimal("58.00")


def test_a_group_not_exhaustive_answers_raw_prices_and_none_of_the_named() -> None:
    case = reference.load(CASES / "event-group-not-exhaustive.json")
    reasons = {n["reason"] for n in case["answer"]["not_evaluated"]}
    assert reasons == {"NOT_EVALUATED_REASON_GROUP_NOT_EXHAUSTIVE"}
    kinds = [
        f["scenario_key"]["kind"]
        for f in _figures("event-group-not-exhaustive", "resolution_payoff")
    ]
    assert kinds[-1] == "SCENARIO_KIND_NONE_OF_THE_NAMED"


def test_a_value_is_rounded_once_half_to_even() -> None:
    assert reference.round_half_even(Fraction(5, 1000), 2) == Decimal("0.00")
    assert reference.round_half_even(Fraction(15, 1000), 2) == Decimal("0.02")
    assert reference.round_half_even(Fraction(-25, 1000), 2) == Decimal("-0.02")
    assert reference.round_half_even(Fraction(1, 3), 4) == Decimal("0.3333")
    # Summed unrounded, then rounded: 3 × 0.335 is 1.005, never 3 × 0.34.
    assert reference.round_half_even(3 * Fraction(Decimal("0.335")), 2) == Decimal("1.00")


def test_a_local_record_and_a_missing_nav_are_never_zero() -> None:
    case = reference.load(CASES / "valuation.json")
    reasons = {(n["instrument_id"][-5:], n["reason"]) for n in case["answer"]["not_evaluated"]}
    assert ("0ZZTP", "NOT_EVALUATED_REASON_LOCAL_RECORD") in reasons
    assert ("SPAXX", "NOT_EVALUATED_REASON_PRICE_MISSING") in reasons


def test_a_crypto_asset_converts_leg_by_leg_never_at_par() -> None:
    value, held = reference.value_per_unit(
        "quoted_price",
        "INS-BTC",
        [("INS-BTC", "close", "60000.50", "INS-USDT"), ("INS-USDT", "close", "0.9998", USD)],
    )
    assert (value, held) == (Decimal("60000.50") * Decimal("0.9998"), USD)
    # A stablecoin held as cash: its own price, the same figure either way.
    cash, _ = reference.value_per_unit(
        "cash", "INS-USDT", [("INS-USDT", "close", "0.9998", USD)]
    )
    assert cash == Decimal("0.9998")


def test_historical_var_is_the_order_statistic_and_es_the_mean_beyond() -> None:
    var = _figures("historical-var-and-es", "historical_var")
    es = _figures("historical-var-and-es", "expected_shortfall")
    base_var = Decimal(var[0]["value"])
    base_es = Decimal(es[0]["value"])
    assert base_es >= base_var > 0
    # The event contract left out, its exact resolution worst case beside.
    assert var[1]["scenario_key"]["kind"] == "SCENARIO_KIND_OUTCOME"
    assert Decimal(var[1]["value"]) == Decimal("42.00")


def test_the_reference_refuses_a_definition_it_does_not_hold() -> None:
    case = reference.load(CASES / "what-if.json")
    inputs = json.loads(json.dumps(case["inputs"]))
    inputs["job"]["measures"] = [{"definition": "market_value", "version": 2}]
    with pytest.raises(ValueError, match="no definition market_value v2"):
        reference.compute(inputs)


def _components(figures: list[dict[str, Any]]) -> set[str]:
    return {
        b["value"] for f in figures for b in f["breakdown"] if b["breakdown"] == "component"
    }


def test_pnl_v1_is_unrealized_alone_and_v2_adds_realized() -> None:
    # Ruling 320: v1 ("Unrealized P&L") answers one component, after the
    # measure's own breakdowns; no v1 case carries a realized component.
    for path in _cases():
        v1 = [f for f in _figures(path.stem, "pnl") if f["measure"]["version"] == 1]
        assert _components(v1) <= {"unrealized"}, path.stem
    valuation = _figures("valuation", "pnl")
    assert valuation and all(
        [b["breakdown"] for b in f["breakdown"]] == ["sleeve", "component"] for f in valuation
    )
    assert "closed_lots" not in reference.load(CASES / "valuation.json")["inputs"]
    # v2 (v27's) is computed by the reference and pinned, never asked in v26.
    v2 = _figures("pnl-v2-realized", "pnl")
    assert {f["measure"]["version"] for f in v2} == {2}
    assert _components(v2) == {"unrealized", "realized"}
    realized = {
        (f["account_id"], f["breakdown"][0]["value"]): f["value"]
        for f in v2
        if f["breakdown"][1]["value"] == "realized"
    }
    assert realized[("ACC-1", "core")] == "100.00"
    assert realized[("ACC-1", "hedge")] == "-30.40"
    assert reference.UNREALIZED_PNL == "Unrealized P&L"
    assert reference.definition_of("pnl", 1).parameters == (
        ("unrealized", "market_value_less_open_lots_cost"),
    )
    assert analytics.measure("pnl", 2).version == 2
    with pytest.raises(ValueError, match="pnl v3 is not served in contract v27; up to v2 is$"):
        analytics.measure("pnl", 3)
    with pytest.raises(
        ValueError, match="exposure v2 is not served in contract v27; up to v1 is$"
    ):
        analytics.measure("exposure", 2)


# ── Typed builders and an answer read (Q1, Q13, Q14) ────────────────────────


def test_a_job_is_built_and_checked_as_it_is_built() -> None:
    job = analytics.job(
        analytics.measure("exposure", by=["asset_class", "currency"]),
        analytics.measure("implied_distribution", event_group="EVG-1"),
        accounts=["ACC-12"],
        what_if=analytics.what_if("ACC-12", analytics.trade(AAPL, "buy", Decimal("10"))),
    )
    sent = ops.RunJobParams(job=meridian.operations._job(job, "job"))
    assert [m.definition for m in sent.job.measures] == ["exposure", "implied_distribution"]
    assert list(sent.job.measures[0].breakdowns) == ["asset_class", "currency"]
    assert sent.job.what_if.trades[0].side == ops.SIDE_BUY
    for wrong, why in (
        (lambda: analytics.measure("exposure", by=["currency", "currency"]), "twice"),
        (lambda: analytics.measure("exposure", 0), "1 or more"),
        (lambda: analytics.measure("resolution_payoff"), "names none"),
        (lambda: analytics.measure("exposure", event_group="EVG-1"), "not over an event"),
        (lambda: analytics.job(), "at least one measure"),
        (lambda: analytics.job(analytics.measure("exposure")), "names none"),
        (lambda: analytics.trade(AAPL, "buy", Decimal(0)), "above zero"),
        (
            lambda: analytics.job(
                analytics.measure("market_value"),
                accounts=["ACC-1"],
                what_if=analytics.what_if("ACC-2", analytics.trade(AAPL, "buy", 1)),
            ),
            "not among the job's",
        ),
    ):
        with pytest.raises(ValueError, match=why):
            wrong()


def _answer(**figure: Any) -> analytics.Answer:
    return analytics.Answer(
        ops.ReadJobAnswerResult(job_id="JOB-1", figures=[ops.Figure(**figure)])
    )


def test_an_answer_reads_every_computed_as_and_scenario_key() -> None:
    unset = _answer(measure=ops.MeasureRef(definition="exposure", version=1))
    (figure,) = unset.figures()
    assert figure.computed_as == "exact" and figure.scenario == "SCENARIO_KIND_BASE"
    modelled = _answer(computed_as=ops.COMPUTED_AS_MODEL)
    assert modelled.figures()[0].computed_as == "model"
    later = _answer(computed_as=9, scenario_key=ops.ScenarioKey(kind=9))
    assert later.figures()[0].computed_as == "model", "a later value is never read as exact"
    day = _answer(scenario_key=ops.ScenarioKey(kind=ops.SCENARIO_KIND_HISTORICAL_DAY))
    assert day.figures(scenario="historical_day") and not day.figures(scenario="base")


def test_a_weight_is_compared_by_cross_multiplication() -> None:
    weight = _answer(
        numerator=meridian.operations._decimal(Decimal("1"), "n"),
        denominator=meridian.operations._decimal(Decimal("3"), "d"),
    ).figures()[0]
    assert weight.weight == Fraction(1, 3)
    assert weight.compare(Decimal("0.3333")) == 1
    assert weight.compare(Decimal("0.3334")) == -1


async def test_a_job_answered_later_is_waited_for_by_its_finishing() -> None:
    recorder = Recorder("reporting-1")
    recorder.answer("RunJob", lambda _: ops.RunJobResult(answered_inline=False, job_id="JOB-9"))
    finished = ops.JobFinishedEvent(job_id="JOB-9", sequence=4)
    recorder.answer(
        "ListFinishedJobs",
        lambda params: ops.ListFinishedJobsResult(
            finished=[finished] if params.after_sequence < 4 else [], sequence=4
        ),
    )
    recorder.answer(
        "ReadJobAnswer", lambda params: ops.ReadJobAnswerResult(job_id=params.job_id)
    )
    jobs = analytics.Jobs(poll_seconds=0.01, timeout_seconds=1)
    answer = await jobs.run(
        recorder, analytics.job(analytics.measure("pnl"), accounts=["ACC-1"])
    )
    assert answer.job_id == "JOB-9" and jobs.sequence == 4
    # Caught up once more: nothing new, read after the sequence seen.
    assert await jobs.catch_up(recorder) == 0
    assert recorder.on("ListFinishedJobs")[-1].after_sequence == 4


async def test_a_job_answered_inline_is_not_waited_for() -> None:
    recorder = Recorder("reporting-1")
    recorder.answer(
        "RunJob",
        lambda _: ops.RunJobResult(
            answered_inline=True, job_id="JOB-1", answer=ops.JobAnswer(job_id="JOB-1")
        ),
    )
    answer = await analytics.Jobs().run(
        recorder, analytics.job(analytics.measure("pnl"), accounts=["ACC-1"])
    )
    assert answer.job_id == "JOB-1" and recorder.on("ReadJobAnswer") == []


async def test_a_job_that_never_finishes_times_out_saying_so() -> None:
    recorder = Recorder("reporting-1")
    recorder.answer("RunJob", lambda _: ops.RunJobResult(answered_inline=False, job_id="JOB-2"))
    jobs = analytics.Jobs(poll_seconds=0.01, timeout_seconds=0.05)
    with pytest.raises(TimeoutError, match="JOB-2 did not finish"):
        await jobs.run(recorder, analytics.job(analytics.measure("pnl"), accounts=["ACC-1"]))


# ── The pricing role (W12.3) ────────────────────────────────────────────────


def _unit(close: str, kind: int = ops.SCENARIO_KIND_BASE, day: str = "") -> ops.PricingUnit:
    return ops.PricingUnit(
        instrument_id=AAPL,
        template_version="2",
        scenario_key=ops.ScenarioKey(kind=kind, business_date=day),
        inputs=[
            ops.MarketObjectValue(
                subject_id=AAPL,
                kind="close",
                value=ops.Money(
                    amount=meridian.operations._decimal(Decimal(close), "close"),
                    currency_code="USD",
                ),
                dataset="alpaca-1:daily",
            )
        ],
    )


def _batch(*units: ops.PricingUnit, sequence: int = 17) -> ops.PriceBatchRequest:
    return ops.PriceBatchRequest(
        batch_id=f"PBT-{sequence}", model_id="quoted_price", model_version=1,
        units=list(units), sequence=sequence,
    )  # fmt: skip


def test_the_reference_model_is_design_fixtures_equity_case() -> None:
    """fixtures/analytics/price-batch.yaml: a close of 227.50 USD."""
    money = pricing.reference_model(_batch(), _unit("227.50"))
    assert money == meridian.Money(amount=Decimal("227.50"), currency_code="USD")


def test_a_pricing_plugin_passes_its_suite_with_the_built_in_model(tmp_path: Path) -> None:
    models = {"quoted_price": pricing.reference_model}

    def delivered(*batches: ops.PriceBatchRequest):  # type: ignore[no-untyped-def]
        async def produce(recorder: Recorder) -> None:
            recorder.answer("PriceBatch", lambda _: list(batches))
            await recorder.receive(price_batch=pricing.Pricer(recorder, models).heard)

        return produce

    async def restarted(recorder: Recorder) -> None:
        kept = pricing.Sequence(tmp_path / "pricing.json")
        kept.note(16)
        again = pricing.Sequence(tmp_path / "pricing.json")
        assert again.value == 16, "the sequence survives the restart"
        recorder.answer(
            "ListPriceBatches",
            lambda p: ops.ListPriceBatchesResult(
                batches=[_batch(_unit("1.00"))] if p.after_sequence < 17 else [], sequence=17
            ),
        )
        await pricing.Pricer(recorder, models, sequence=again).catch_up()

    days = [_unit("226.10", ops.SCENARIO_KIND_HISTORICAL_DAY, "2026-10-15")]
    report = run(
        "pricing",
        {
            "answers-a-batch": delivered(_batch(_unit("227.50"))),
            "answers-every-scenario-of-a-batch": delivered(_batch(*days)),
            "equals-the-built-in-model": delivered(_batch(_unit("227.50"))),
            "carries-no-sensitivity": delivered(_batch(_unit("227.50"))),
            "reads-the-batches-waiting-after-a-restart": restarted,
        },
    )
    assert report.passed, report.failures


async def test_a_model_raising_leaves_the_whole_batch_unanswered() -> None:
    def broken(batch: ops.PriceBatchRequest, unit: ops.PricingUnit) -> meridian.Money:
        raise ValueError("no close")

    recorder = Recorder("pricing-1")
    pricer = pricing.Pricer(recorder, {"quoted_price": broken})
    assert await pricer.answer(_batch(_unit("1.00"), _unit("2.00"))) is None
    assert recorder.on("AnswerPriceBatch") == [] and "no close" in pricer.unanswered["PBT-17"]


async def test_a_batch_is_answered_under_each_units_scenario() -> None:
    recorder = Recorder("pricing-1")
    await pricing.Pricer(recorder, {"quoted_price": pricing.reference_model}).answer(
        _batch(_unit("10.00", ops.SCENARIO_KIND_HISTORICAL_DAY, "2026-10-15"), _unit("11.00"))
    )
    (answered,) = recorder.on("AnswerPriceBatch")
    assert [
        (v.scenario_key.kind, as_money(v.value_per_unit).amount) for v in answered.values
    ] == [
        (ops.SCENARIO_KIND_HISTORICAL_DAY, Decimal("10.00")),
        (ops.SCENARIO_KIND_BASE, Decimal("11.00")),
    ]
    assert list(answered.sensitivities) == []


# ── Event groups (W3.29, W3.30) ─────────────────────────────────────────────


def _group(version: int, valid_from: int, members: tuple[str, ...] = ("INS-A", "INS-B")) -> Any:
    return ops.EventGroup(
        event_group_id="EVG-1", member_instrument_ids=list(members), version=version,
        valid_from_ns=valid_from, sequence=version,
        exhaustive=(
            ops.EVENT_GROUP_FLAG_TRUE if version > 1 else ops.EVENT_GROUP_FLAG_NOT_STATED
        ),
    )  # fmt: skip


def test_the_version_in_force_at_a_moment_is_read() -> None:
    groups = meridian.EventGroups()
    assert groups.apply(_group(1, 100)) and groups.apply(
        _group(2, 200, ("INS-A", "INS-B", "INS-C"))
    )
    assert not groups.apply(_group(2, 200)), "a version held changes nothing"
    assert groups.group("EVG-1", at_ns=150).version == 1  # type: ignore[union-attr]
    assert groups.group("EVG-1").version == 2  # type: ignore[union-attr]
    assert groups.holding("INS-C", at_ns=150) == []
    assert [g.version for g in groups.holding("INS-C")] == [2]
    assert not groups.exhaustive(groups.versions("EVG-1")[0])
    assert groups.exhaustive(groups.versions("EVG-1")[1])


async def test_groups_are_caught_up_after_the_sequence_seen() -> None:
    recorder = Recorder("signal-1")
    recorder.answer(
        "ListEventGroups",
        lambda p: ops.ListEventGroupsResult(
            event_groups=[_group(1, 100), _group(2, 200)] if p.after_sequence < 2 else [],
            sequence=2,
        ),
    )
    groups = meridian.EventGroups()
    assert await groups.catch_up(recorder) == 2
    assert await groups.catch_up(recorder) == 0
    assert recorder.on("ListEventGroups")[-1].after_sequence == 2


def test_a_flag_the_venue_does_not_state_is_not_stated_never_false() -> None:
    assert event_contracts.flag(None) == ops.EVENT_GROUP_FLAG_NOT_STATED
    assert event_contracts.flag(False) == ops.EVENT_GROUP_FLAG_FALSE
    assert event_contracts.stated(ops.EVENT_GROUP_FLAG_UNSPECIFIED) is None


def test_every_role_but_pricing_hears_and_reads_an_event_group_by_the_sdk() -> None:
    for role, held in suites().items():
        names = {case.name for case in held.cases}
        assert ("hears-and-reads-an-event-group" in names) == (role != "pricing"), role


def test_the_data_suites_event_group_cases_are_about_outcomes() -> None:
    held = suite("data")
    assert held.case("reports-an-event-group").about == "outcomes"
    flagged = held.case("reports-a-flag-the-venue-does-not-state")
    assert flagged.expect[0].fields == {"exhaustive": "EVENT_GROUP_FLAG_NOT_STATED"}


# ── The agents' demo-only guard (W11.38, W11.39) ────────────────────────────


def test_environment_offers_paper_and_defaults_to_the_demo() -> None:
    paper = meridian.environment(demo="paper", demo_label="Practice")
    assert [c.value for c in paper.choices] == ["live", "paper"] and paper.default == "paper"
    assert [c.label for c in paper.choices] == ["Live", "Practice"]
    sandbox = meridian.environment()
    assert [c.value for c in sandbox.choices] == ["live", "sandbox"]
    assert sandbox.default == "sandbox"
    with pytest.raises(ValueError, match="sandbox or paper"):
        meridian.environment(demo="demo")


def test_the_environment_reached_is_read_from_the_host() -> None:
    hosts = {
        "live": ["api-fxtrade.oanda.com"],
        "paper": ["api-fxpractice.oanda.com"],
    }
    assert (
        meridian.reached_environment("https://api-fxpractice.oanda.com/v3/accounts", **hosts)
        == "paper"
    )
    assert meridian.reached_environment("API-FXTRADE.OANDA.COM", **hosts) == "live"
    assert meridian.reached_environment("https://elsewhere.example/v3", **hosts) == ""


def test_a_connection_is_demo_only_while_both_keys_say_so() -> None:
    assert meridian.is_demo("paper", "paper") and meridian.is_demo("sandbox", "sandbox")
    assert not meridian.is_demo("paper", "") and not meridian.is_demo("", "paper")
    assert meridian.connection_badge("paper", "paper") == "Demo"
    assert meridian.connection_badge("live", "live") == "Live"
    assert meridian.connection_badge("", "") == "Live"
    assert meridian.connection_badge("paper", "live") == "Live (environment not confirmed)"
    assert meridian.connection_badge("live", "sandbox") == "Live (environment not confirmed)"


def test_the_caller_says_what_the_book_would_refuse_an_agent() -> None:
    agent = meridian.Caller.from_header(
        caller_header(
            "write",
            delegation_id="DLG-1",
            connectivity_instance_ids=["live-1", "demo-1"],
            demo_connectivity_instance_ids=["demo-1"],
        )  # fmt: skip
    )
    assert agent.demo_connectivity_instance_ids == frozenset({"demo-1"})
    assert (
        agent.agents_act and agent.agent_refused("live-1") and not agent.agent_refused("demo-1")
    )
    assert not agent.agent_refused("live-1", guard_on=False)
    person = meridian.Caller.from_header(caller_header("write"))
    assert not person.agents_act and not person.agent_refused("live-1")
    service = meridian.Caller.from_header(
        caller_header(
            "write",
            subject="SA-1",
            subject_kind=meridian.SubjectKind.SUBJECT_KIND_SERVICE_ACCOUNT,
        )
    )
    assert service.agent_refused("live-1")
    prepared = meridian.Caller.from_header(caller_header("write", prepared_call_id="PRC-1"))
    assert not prepared.agent_refused("live-1")


def test_the_guards_five_ems_cases_pass_as_an_ems_does_them() -> None:
    from order_path_cases import PRODUCERS

    for name in (
        "agent-placement-on-a-live-connection-refused",
        "agent-placement-on-a-demo-connection",
        "person-makes-an-agents-prepared-live-placement",
        "agent-accept-to-a-new-order-on-a-live-connection-refused",
        "setting-and-session-disagree-counts-live",
        "reads-the-agents-guard",
    ):
        recorder = Recorder("ems-1")
        asyncio.run(PRODUCERS[name](recorder))
        assert check(suite("ems").case(name), recorder) is None, name


async def test_the_trader_publishes_the_environment_its_venue_reached() -> None:
    from meridian.roles.connectivity import testing

    class Reached:
        statuses: dict[str, str] = {}
        sides: dict[int, str] = {}
        sides_said: dict[str, int] = {}
        source = "venue"
        environment = "paper"

        def accounts(self) -> tuple[str, ...]:
            return ("CODE-1",)

        def catalogue(self, code: str) -> Any:
            return ((ops.ORDER_TYPE_LIMIT, (ops.TIME_IN_FORCE_DAY,)),)

        def keep(self, name: str, record: Any) -> str:
            return name

    class Rig(testing.Rig):
        def connect(self, broker: Any) -> connectivity.Venue:
            return Reached()  # type: ignore[return-value]

    recorder = Recorder("connectivity")
    rig = Rig(recorder)
    await rig.trader.publish()
    (sent,) = recorder.on("ReportVenueCatalogue")
    assert sent.catalogue.environment == "paper"
    rig.venue.environment = "live"  # type: ignore[attr-defined]
    await rig.trader.publish()
    assert recorder.on("ReportVenueCatalogue")[-1].catalogue.environment == "live"


def test_custodys_thin_holding_is_about_securities() -> None:
    """A custodian holding only cash and currencies marks it not presented."""
    case = suite("custody").case("records-a-thinly-described-holding-unresolved")
    assert case.about == "securities"
    report = run(
        "custody",
        {},
        not_presented={case.name: "this custodian holds only cash and currencies"},
    )
    assert case.name in report.not_presented and case.name not in report.failures


# ── The agent-tools track: the lake's bounded query and model tokens ────────


async def test_a_bounded_query_names_its_fields_and_limit() -> None:
    recorder = Recorder("reporting-1")
    await recorder.query_lake(
        kind="bars", subjects=[meridian.SubjectRef(entity_id=AAPL)],
        fields=["meridian.v1.Bar.close"], row_limit=10_000,
    )  # fmt: skip
    (sent,) = recorder.on("QueryLake")
    assert (sent.kind, sent.row_limit, list(sent.fields)) == (
        "bars",
        10_000,
        ["meridian.v1.Bar.close"],
    )


async def test_model_tokens_ride_the_heartbeat(
    sidecar: tuple[Any, str], monkeypatch: pytest.MonkeyPatch
) -> None:
    service, address = sidecar
    monkeypatch.setattr(meridian.client, "HEARTBEAT_SECONDS", 0.01)
    plugin = await meridian.connect(address)
    try:
        plugin.count_model_tokens(
            "in-cluster/qwen2.5-7b", 120, 30, subject="local|ada", client_name="Claude"
        )
        plugin.count_model_tokens(
            "in-cluster/qwen2.5-7b", 80, 20, subject="local|ada", client_name="Claude"
        )
        plugin.count_model_tokens("in-cluster/qwen2.5-7b", 5, 1)
        beats = await service.beats_from(service.mark())
        counted = {
            (t.endpoint, t.subject, t.client_name): (t.input_tokens, t.output_tokens)
            for t in beats[-1].model_tokens
        }
        assert counted == {
            ("in-cluster/qwen2.5-7b", "local|ada", "Claude"): (200, 50),
            ("in-cluster/qwen2.5-7b", "", ""): (5, 1),
        }
    finally:
        await plugin.leave()


async def test_a_65th_model_token_count_is_refused(sidecar: tuple[Any, str]) -> None:
    _, address = sidecar
    plugin = await meridian.connect(address, heartbeat=False)
    try:
        for n in range(64):
            plugin.count_model_tokens(f"endpoint-{n}", 1, 1)
        with pytest.raises(ValueError, match="at most 64"):
            plugin.count_model_tokens("endpoint-64", 1, 1)
        with pytest.raises(ValueError, match="a count"):
            plugin.count_model_tokens("endpoint-1", -1, 0)
        plugin.count_model_tokens("endpoint-1", 1, 1)  # an endpoint held already adds
        assert plugin.model_tokens[("endpoint-1", "", "")] == (2, 2)
    finally:
        await plugin.leave()


# ── A contract's ticker (ruling 312) ────────────────────────────────────────


async def test_an_event_contract_is_sent_with_its_ticker_beside_its_symbol() -> None:
    """The venue's own market ticker under the contract's `ticker` scheme,
    its venue's MIC in source -- what core's stand-in mints on -- beside the
    source-scoped symbol sent before."""
    from fake_venues import contracts_venue

    recorder = Recorder("fakev-1")
    feed = event_contracts.Feed(
        recorder,
        contracts_venue.market(contracts_venue.NOW_NS),
        event_contracts.ContractMap(),
        clock_ns=lambda: contracts_venue.NOW_NS,
    )
    await feed.member_id("BASE-1")
    (resolve,) = recorder.on("ResolveIdentifier")
    assert [(i.scheme, i.value, i.source) for i in resolve.identifiers] == [
        ("symbol", "BASE-1", "fakev"),
        ("ticker", "BASE-1", "XFKE"),
    ]


async def test_a_venue_with_no_mic_names_its_ticker_by_its_venue_id() -> None:
    from fake_venues import contracts_venue

    market = contracts_venue.market(contracts_venue.NOW_NS)
    market.venue_identifiers = (("symbol", "fakev", "fakev"),)
    recorder = Recorder("fakev-1")
    feed = event_contracts.Feed(recorder, market, event_contracts.ContractMap())
    ticker = await feed._ticker(await feed.contract("BASE-1"))  # type: ignore[arg-type]
    assert ticker is not None and ticker.scheme == "ticker"
    assert ticker.source.startswith("VEN-")
    unheld = event_contracts.Feed(Recorder("fakev-2"), market, event_contracts.ContractMap())
    unheld.plugin.answer(
        "ResolveVenue",
        lambda _: ops.ResolveVenueResult(found=False, miss_reason=ops.MISS_REASON_NOT_FOUND),
    )
    assert await unheld._ticker(await unheld.contract("BASE-1")) is None  # type: ignore[arg-type]
