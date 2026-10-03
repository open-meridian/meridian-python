"""What the edge keeps of its own (contract v11): the helpers, the
declaration, and the role suites' runner."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

import meridian
from meridian import edge
from meridian.declaration import Declaration, NotCarried, Storage, main
from meridian.edge import (
    as_reported,
    backfill,
    derived,
    raw_record,
    reported,
    second_source,
    supplied,
    within_retention,
)
from meridian.suites import Recorder, check, names, run, suite


def test_a_value_as_reported_carries_three_bounded_parts_the_code_again_for_no_words() -> None:
    held = as_reported("myvendor:account-type", "INDIVIDUAL")
    assert (held.scheme, held.code, held.text) == (
        "myvendor:account-type",
        "INDIVIDUAL",
        "INDIVIDUAL",
    )
    with pytest.raises(ValueError, match="scheme is 0 characters"):
        as_reported("", "X")
    with pytest.raises(ValueError, match="code is 129 characters"):
        as_reported("s", "x" * 129)


def test_provenance_is_each_of_the_four_kinds_with_what_names_it() -> None:
    record = raw_record("activities/A/1", "snaptrade-1")
    assert derived("quantity", "cash net of funds").kind == "PROVENANCE_KIND_DERIVED"
    assert supplied("settle_date_quantity", "local|ada").person == "local|ada"
    assert second_source("institution", "a registry", record).raw_record == record
    assert reported("pending", record).kind == "PROVENANCE_KIND_REPORTED"
    with pytest.raises(ValueError):
        raw_record("")


def test_a_backfill_names_its_version_and_reaches_back_only_its_retention() -> None:
    assert backfill("v11", "raw_record").field == "raw_record"
    with pytest.raises(ValueError, match="v<N>"):
        backfill("11", "raw_record")
    day = 86_400 * 10**9
    assert within_retention(received_at_ns=0, now_ns=30 * day, retention_days=30)
    assert not within_retention(received_at_ns=0, now_ns=31 * day, retention_days=30)


SETTINGS = (
    meridian.Setting(name="consumer_key", label="Consumer key", secret=True, required=True),
    meridian.Setting(name="region", label="Region"),
)


def test_a_declaration_names_its_secrets_from_its_settings_and_never_a_value() -> None:
    declaration = Declaration(
        settings=SETTINGS,
        not_carried=[
            NotCarried("custody", "myvendor:position", "open_pnl", "no_contract_meaning")
        ],
        storage=Storage(retention_days=2555),
    )
    wire = declaration.to_wire()
    assert list(wire.secret_settings) == ["consumer_key"]
    assert wire.storage.retention_days == 2555
    assert declaration.to_json()["not_carried"][0]["reason"] == "no_contract_meaning"
    assert declaration.refused_for(["custody"]) is None
    assert "not a role held" in (declaration.refused_for(["portfolio"]) or "")
    storage_only = Declaration(storage=Storage(retention_days=30))
    assert "no edge role" in (storage_only.refused_for(["portfolio"]) or "")
    with pytest.raises(ValueError):
        NotCarried("custody", "s", "n", "lost")  # type: ignore[arg-type]
    with pytest.raises(ValueError):
        Storage(retention_days=0)


DECLARED = Declaration(settings=SETTINGS, storage=Storage(retention_days=30))


def test_the_declaration_prints_as_json_for_the_upload(
    capsys: pytest.CaptureFixture[str],
) -> None:
    assert main(["tests.test_edge:DECLARED"]) == 0
    printed = json.loads(capsys.readouterr().out)
    assert printed == {
        "not_carried": [],
        "secret_settings": ["consumer_key"],
        "storage": {"retention_days": 30},
    }
    assert main(["tests.test_edge:SETTINGS"]) == 1
    assert main([]) == 2


# ── The custody suite ───────────────────────────────────────────────────────


def test_the_custody_suite_is_carried_with_a_case_for_every_value_of_the_sync_state() -> None:
    held = suite("custody")
    assert held.since == "v11"
    assert "sync-holdings-unavailable" in names("custody")
    closed = [
        case.name for case in held.cases if case.closed_list.endswith("SyncStatusEvent.state")
    ]
    assert len(closed) == 6


async def _sync(recorder: Recorder, state: str) -> None:
    await recorder.report_sync_status(
        source="toy", external_account_id="A-1", connection_healthy=True, state=state
    )


def _toy_producers(holdings_unavailable_as: str) -> dict[str, object]:
    states = {
        "sync-current": "SYNC_STATE_CURRENT",
        "sync-stale": "SYNC_STATE_STALE",
        "sync-needs-sign-in": "SYNC_STATE_NEEDS_SIGN_IN",
        "sync-disabled": "SYNC_STATE_DISABLED",
        "sync-delayed-by-design": "SYNC_STATE_DELAYED_BY_DESIGN",
        "sync-holdings-unavailable": holdings_unavailable_as,
    }

    def producer(state: str):  # type: ignore[no-untyped-def]
        async def produce(recorder: Recorder) -> None:
            await _sync(recorder, state)

        return produce

    return {name: producer(state) for name, state in states.items()}


def test_a_plugin_sending_stale_for_holdings_unavailable_fails_the_suite() -> None:
    # The spec's requirement 21: the suite holds every value of the role's
    # closed lists, so 0.6.0's mistake fails it.
    good = run("custody", _toy_producers("SYNC_STATE_HOLDINGS_UNAVAILABLE"))
    assert "sync-holdings-unavailable" in good.passed_cases
    bad = run("custody", _toy_producers("SYNC_STATE_STALE"))
    assert (
        "is SYNC_STATE_STALE, not SYNC_STATE_HOLDINGS_UNAVAILABLE"
        in bad.failures["sync-holdings-unavailable"]
    )
    # A case nobody maps is a failure, never a pass.
    assert bad.failures["cash-net-of-a-fund-counted-in-cash"].startswith("no producer")
    assert not bad.passed


def test_only_a_closed_list_case_may_be_not_presented_and_only_saying_why() -> None:
    report = run(
        "custody",
        {},
        not_presented={
            "sync-delayed-by-design": "the source is never late by design",
            "fund-larger-than-cash": "never happens",
            "sync-stale": "",
        },
    )
    assert report.not_presented == {
        "sync-delayed-by-design": "the source is never late by design"
    }
    assert "required" in report.failures["fund-larger-than-cash"]
    assert "says why" in report.failures["sync-stale"]


async def test_a_net_cash_row_with_its_provenance_matches_the_sweep_case() -> None:
    recorder = Recorder("toy-1")
    await recorder.record_holding(
        statement_id="S",
        instrument_id="LCL-cash",
        quantity=1023,
        side="long",
        raw_record=recorder.raw_record("balances/A/1"),
        provenance=[derived("quantity", "cash net of money market funds")],
    )
    await recorder.record_holding(
        statement_id="S", instrument_id="LCL-fund", quantity=500, side="long"
    )
    await recorder.resolve_identifier(
        identifiers=[meridian.Identifier(scheme="symbol", value="SYNXX", source="toy")],
        stated_asset_class="fund",
        stated_instrument_type="money_market_fund",
    )
    assert check(suite("custody").case("cash-net-of-a-fund-counted-in-cash"), recorder) is None
    assert recorder.sent[0].params.raw_record.instance_id == "toy-1"


def test_the_granted_storage_is_where_the_deployment_mounted_it(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv(edge.STORAGE_DIR, raising=False)
    assert edge.storage_dir() is None
    monkeypatch.setenv(edge.STORAGE_DIR, "/var/lib/meridian/storage")
    assert edge.storage_dir() == Path("/var/lib/meridian/storage")
