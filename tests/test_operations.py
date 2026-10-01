"""The typed operations, from the plugin's side (spec/typed-sidecar-operations).

Against the fake sidecar: what these hold is the client's half -- the params
each operation sends, numbers carried exactly or refused, the sidecar's fields
never offered, and a refusal turned into this package's terms. What the
sidecar does with them is meridian-core's to test, and the interop suite's.
"""

from __future__ import annotations

import inspect
from decimal import Decimal

import grpc
import pytest

import meridian
from conftest import FakeSidecar
from meridian import CallFailed, Identifier, Money, NotGranted, NotLinked
from meridian.plugin.v1 import operations_pb2
from meridian.v1 import sidecar_pb2


async def connected(sidecar: tuple[FakeSidecar, str]) -> meridian.Plugin:
    _, address = sidecar
    return await meridian.connect(address, heartbeat=False)


def integer_and_scale(sent: operations_pb2.Decimal) -> tuple[int, int]:
    return (sent.high << 64) | sent.low, sent.scale


async def test_a_number_crosses_as_its_integer_and_its_own_scale(sidecar) -> None:
    service, _ = sidecar
    plugin = await connected(sidecar)
    try:
        result = await plugin.record_holding(
            statement_id="S-1",
            quantity=Decimal("12.5"),
            market_value=Money(Decimal("2812.50"), "USD"),
            external_account_id="ext-1",
        )
    finally:
        await plugin.leave()
    assert result.holding_id == "H-1"
    (sent,) = service.operations.sent
    assert isinstance(sent, operations_pb2.RecordHoldingParams)
    assert integer_and_scale(sent.quantity) == (125, 1)
    # The scale is the Decimal's own: 2812.50 is not normalised to 2812.5.
    assert integer_and_scale(sent.market_value.amount) == (281_250, 2)
    assert sent.market_value.currency_code == "USD"
    assert sent.external_account_id == "ext-1"
    assert meridian.as_decimal(sent.quantity) == Decimal("12.5")
    assert str(meridian.as_money(sent.market_value).amount) == "2812.50"


@pytest.mark.parametrize(
    "quantity",
    [
        # spec/quantities-carry-their-own-scale, requirement 7: Alpaca's ninth
        # decimal, a hundred billion units, and those at eighteen decimals.
        Decimal("0.000000001"),
        Decimal("100000000000"),
        Decimal("100000000000.000000000000000001"),
        100_000_000_000,
        Decimal("-5"),
        Decimal("0"),
        Decimal("99999999999999999999.999999999999999999"),
    ],
)
async def test_a_number_reads_back_exactly_as_it_was_sent(sidecar, quantity: Decimal) -> None:
    service, _ = sidecar
    plugin = await connected(sidecar)
    try:
        await plugin.record_holding(
            quantity=quantity, market_value=Money(Decimal("0.00"), "USD")
        )
    finally:
        await plugin.leave()
    (sent,) = service.operations.sent
    back = meridian.as_decimal(sent.quantity)
    assert back == quantity
    assert str(back) == str(quantity)
    # Presence survives a zero, so a zero is sent rather than left unset.
    assert sent.HasField("quantity") and sent.HasField("market_value")


@pytest.mark.parametrize(
    ("quantity", "refusal", "says"),
    [
        (Decimal("0.0000000000000000001"), ValueError, "quantity has 19 decimal places"),
        (Decimal("1" * 39), ValueError, "quantity has more than 38 digits"),
        (Decimal("1E+38"), ValueError, "quantity has more than 38 digits"),
        (Decimal("NaN"), ValueError, "quantity is not a finite number"),
        (Decimal("Infinity"), ValueError, "quantity is not a finite number"),
        (0.1, TypeError, "quantity is a Decimal or an int, not float"),
        (True, TypeError, "quantity is a Decimal or an int, not bool"),
        ("1.5", TypeError, "quantity is a Decimal or an int, not str"),
    ],
)
async def test_a_number_that_cannot_cross_exactly_is_refused_before_anything_is_sent(
    sidecar, quantity: object, refusal: type[Exception], says: str
) -> None:
    service, _ = sidecar
    plugin = await connected(sidecar)
    try:
        with pytest.raises(refusal, match=says):
            await plugin.record_holding(
                quantity=quantity,  # type: ignore[arg-type]
                market_value=Money(Decimal(0), "USD"),
            )
    finally:
        await plugin.leave()
    assert service.operations.sent == [], "nothing is sent for a refused number"


@pytest.mark.parametrize(
    ("market_value", "refusal", "says"),
    [
        (Money(0.1, "USD"), TypeError, "market_value is a Decimal or an int, not float"),
        (Money(Decimal("1e-19"), "USD"), ValueError, "market_value has 19 decimal places"),
        (Decimal("2812.50"), TypeError, "market_value is a meridian.Money, not Decimal"),
        ((Decimal(1), "USD"), TypeError, "market_value is a meridian.Money, not tuple"),
    ],
)
async def test_an_amount_is_a_money_and_refused_like_any_number(
    sidecar, market_value: object, refusal: type[Exception], says: str
) -> None:
    service, _ = sidecar
    plugin = await connected(sidecar)
    try:
        with pytest.raises(refusal, match=says):
            await plugin.record_holding(
                quantity=Decimal(1),
                market_value=market_value,  # type: ignore[arg-type]
            )
    finally:
        await plugin.leave()
    assert service.operations.sent == []


def test_the_sidecars_own_fields_are_not_offered() -> None:
    # A plugin cannot set what it has no parameter for (stamped.tsv).
    holding = inspect.signature(meridian.Plugin.record_holding).parameters
    status = inspect.signature(meridian.Plugin.report_sync_status).parameters
    missing = inspect.signature(meridian.Plugin.report_missing_instrument).parameters
    assert "account_id" not in holding and "account_id" not in status
    assert "publisher_instance_id" not in missing
    assert "external_account_id" in holding


async def test_identifiers_travel_as_the_plugin_facing_mirror(sidecar) -> None:
    service, _ = sidecar
    plugin = await connected(sidecar)
    try:
        answer = await plugin.resolve_identifier(
            identifiers=[Identifier(scheme="symbol", value="AAPL", source="snaptrade")],
            as_of_ns=1,
        )
    finally:
        await plugin.leave()
    assert answer.found and answer.instrument_id == "INS-1"
    (sent,) = service.operations.sent
    assert [i.value for i in sent.identifiers] == ["AAPL"]  # type: ignore[attr-defined]


@pytest.mark.parametrize(
    "given",
    ["fund", "ASSET_CLASS_FUND", meridian.AssetClass.ASSET_CLASS_FUND],
)
async def test_an_asset_class_is_the_enums_in_the_spelling_it_was_ruled(sidecar, given) -> None:
    # sdk-contract/asset-class-is-an-enum: equity, debt, fund, derivative,
    # crypto_asset, event_contract, cash -- or the enum's own name or value.
    service, _ = sidecar
    plugin = await connected(sidecar)
    try:
        await plugin.report_missing_instrument(
            source="snaptrade",
            asset_class=given,
            identifiers=[Identifier(scheme="symbol", value="VTI", source="snaptrade")],
        )
    finally:
        await plugin.leave()
    (sent,) = service.operations.sent
    assert sent.asset_class == operations_pb2.ASSET_CLASS_FUND  # type: ignore[attr-defined]


async def test_a_miss_may_say_no_class(sidecar) -> None:
    # A publisher that does not know the class sends none; a stub may lack one.
    service, _ = sidecar
    plugin = await connected(sidecar)
    try:
        await plugin.report_missing_instrument(source="snaptrade", asset_class="")
        await plugin.report_missing_instrument(source="snaptrade")
    finally:
        await plugin.leave()
    assert [s.asset_class for s in service.operations.sent] == [0, 0]  # type: ignore[attr-defined]


@pytest.mark.parametrize("given", ["EQUITY", "Equity", "equities", "etf", 99, True])
async def test_an_asset_class_the_contract_does_not_define_is_refused_before_sending(
    sidecar, given
) -> None:
    # Free text made EQUITY, Equity and equities three classes; an ETF is a
    # type under fund, not a class. None of them reaches the sidecar.
    service, _ = sidecar
    plugin = await connected(sidecar)
    try:
        with pytest.raises(ValueError, match="asset_class") as refused:
            await plugin.report_missing_instrument(source="snaptrade", asset_class=given)
    finally:
        await plugin.leave()
    assert "equity, debt, fund, derivative, crypto_asset, event_contract, cash" in str(
        refused.value
    )
    assert not service.operations.sent


@pytest.mark.parametrize(
    ("code", "raised", "kind"),
    [
        (grpc.StatusCode.PERMISSION_DENIED, NotGranted, None),
        (grpc.StatusCode.FAILED_PRECONDITION, CallFailed, "refused"),
        (grpc.StatusCode.UNAVAILABLE, CallFailed, "no handler"),
        (grpc.StatusCode.DEADLINE_EXCEEDED, CallFailed, "timeout"),
        (grpc.StatusCode.ABORTED, CallFailed, "handler error"),
    ],
)
async def test_a_refusal_is_raised_in_this_packages_terms(
    sidecar, code: grpc.StatusCode, raised: type[Exception], kind: str | None
) -> None:
    service, _ = sidecar
    service.operations.refuse = (code, "because")
    plugin = await connected(sidecar)
    try:
        with pytest.raises(raised) as caught:
            await plugin.record_holdings_statement(source="snaptrade", expected_rows=1)
    finally:
        await plugin.leave()
    assert "RecordHoldingsStatement" in str(caught.value)
    if kind is not None:
        assert caught.value.kind == kind  # type: ignore[attr-defined]


def _coded(reason: int) -> tuple[tuple[str, bytes], ...]:
    """What the sidecar sends beside a refusal to say which it is."""
    return (("meridian-refusal-bin", sidecar_pb2.Refusal(reason=reason).SerializeToString()),)


async def test_an_unlinked_external_account_is_told_by_its_code(sidecar) -> None:
    service, _ = sidecar
    service.operations.refuse = (
        grpc.StatusCode.FAILED_PRECONDITION,
        "worded any way at all",
    )
    service.operations.refuse_metadata = _coded(
        sidecar_pb2.REFUSAL_REASON_EXTERNAL_ACCOUNT_NOT_LINKED
    )
    plugin = await connected(sidecar)
    try:
        with pytest.raises(NotLinked) as caught:
            await plugin.record_holding(quantity=1, external_account_id="st-acct-9902")
    finally:
        await plugin.leave()
    # Still what a plugin catching a refusal caught before the code.
    assert isinstance(caught.value, CallFailed)
    assert caught.value.kind == "refused"
    assert caught.value.detail == "worded any way at all"
    assert "RecordHolding" in str(caught.value)


@pytest.mark.parametrize(
    "metadata",
    [(), _coded(sidecar_pb2.REFUSAL_REASON_UNSPECIFIED)],
    ids=["no code", "unspecified"],
)
async def test_the_words_alone_never_make_a_refusal_not_linked(sidecar, metadata) -> None:
    # Not registered is the same status, and a refusal is told by its code.
    service, _ = sidecar
    service.operations.refuse = (
        grpc.StatusCode.FAILED_PRECONDITION,
        "external account st-acct-9902 is not linked to an account",
    )
    service.operations.refuse_metadata = metadata
    plugin = await connected(sidecar)
    try:
        with pytest.raises(CallFailed) as caught:
            await plugin.record_holding(quantity=1, external_account_id="st-acct-9902")
    finally:
        await plugin.leave()
    assert not isinstance(caught.value, NotLinked)
    assert caught.value.kind == "refused"


async def test_a_command_carries_the_person_it_is_sent_for_as_it_was_handed_over(
    sidecar,
) -> None:
    """W4.9: the Meridian-Caller header the plugin received, handed back as the
    assertion it encodes. Verified by the sidecar, not here."""
    import base64

    from meridian.v1 import sidecar_pb2

    handed = sidecar_pb2.CallerAssertion(
        claims=b"claims", signature=b"sig", key_id="dashboard-1"
    )
    header = base64.urlsafe_b64encode(handed.SerializeToString()).decode().rstrip("=")
    service, _ = sidecar
    plugin = await connected(sidecar)
    try:
        holding = {
            "statement_id": "S-1",
            "quantity": Decimal(1),
            "market_value": Money(Decimal(1), "USD"),
            "external_account_id": "ext-1",
        }
        await plugin.record_holding(**holding, acting_for=header)
        await plugin.record_holding(**holding)
    finally:
        await plugin.leave()
    for_ada, as_itself = service.operations.sent
    assert for_ada.acting_for == handed
    assert not as_itself.HasField("acting_for"), "unset, the plugin acts as itself"


def test_commands_and_the_deployments_accounts_are_sent_for_a_person() -> None:
    """Reads carry no person (decisions/014): a plugin reads as itself. The one
    exception is the deployment's configuration, which a plugin reads only
    acting for a deployment admin (W4.9, W6.4)."""
    for sent_for in ("record_holding", "link_external_account", "read_accounts_for_linking"):
        assert "acting_for" in inspect.signature(getattr(meridian.Plugin, sent_for)).parameters
    assert "acting_for" not in inspect.signature(meridian.Plugin.resolve_identifier).parameters
    assert "acting_for" not in inspect.signature(meridian.Plugin.report_sync_status).parameters


def _header() -> tuple[object, str]:
    """An assertion as the plugin was handed it, and as its header."""
    import base64

    from meridian.v1 import sidecar_pb2

    handed = sidecar_pb2.CallerAssertion(
        claims=b"claims", signature=b"sig", key_id="dashboard-1"
    )
    return handed, base64.urlsafe_b64encode(handed.SerializeToString()).decode().rstrip("=")


async def test_a_link_names_an_account_a_new_one_or_neither_for_the_admin(sidecar) -> None:
    """W6.4: from the plugin's own admin page, for the deployment admin viewing
    it. Whether they are one, whether the plugin reported the account, and
    that a link names one account or the other, are the sidecar's and the
    conductor's to hold; this is what the SDK sends."""
    handed, header = _header()
    service, _ = sidecar
    plugin = await connected(sidecar)
    try:
        existing = await plugin.link_external_account(
            external_account_id="st-acct-4471", account_id="ACC-1", acting_for=header
        )
        created = await plugin.link_external_account(
            external_account_id="st-acct-4471",
            new_account_name="Fidelity Brokerage",
            new_account_custodian="Fidelity",
            new_account_type="Roth IRA",
            new_account_owner="Fund I",
            new_account_note="Linked from SnapTrade.",
            acting_for=header,
        )
        removed = await plugin.link_external_account(
            external_account_id="st-acct-4471", acting_for=header
        )
    finally:
        await plugin.leave()
    assert (existing.account_id, created.account_id, removed.account_id) == (
        "ACC-1",
        "ACC-NEW",
        "",
    )
    to_existing, to_new, unlink = service.operations.sent
    assert isinstance(to_existing, operations_pb2.LinkExternalAccountParams)
    assert (to_existing.account_id, to_existing.new_account_name) == ("ACC-1", "")
    assert (to_new.account_id, to_new.new_account_name) == ("", "Fidelity Brokerage")
    # A new account's custodian, type, owner and note (W6.3), as the plugin
    # pre-filled them from the venue; sent only when asked.
    assert (
        to_new.new_account_custodian,
        to_new.new_account_type,
        to_new.new_account_owner,
        to_new.new_account_note,
    ) == ("Fidelity", "Roth IRA", "Fund I", "Linked from SnapTrade.")
    assert (to_existing.new_account_custodian, to_existing.new_account_type) == ("", "")
    assert (unlink.account_id, unlink.new_account_name) == ("", "")
    assert all(sent.acting_for == handed for sent in (to_existing, to_new, unlink))
    # The sidecar stamps the plugin; the plugin cannot name another.
    offered = operations_pb2.LinkExternalAccountParams.DESCRIPTOR.fields_by_name
    assert "plugin_instance_id" not in offered


async def test_the_deployments_accounts_are_read_for_the_admin(sidecar) -> None:
    """W6.4: each account's identifier, name, state, custodian, type, owner
    and note, to offer beside each external account the plugin reached."""
    handed, header = _header()
    service, _ = sidecar
    plugin = await connected(sidecar)
    try:
        read = await plugin.read_accounts_for_linking(acting_for=header)
    finally:
        await plugin.leave()
    assert [(a.account_id, a.name) for a in read.accounts] == [("ACC-1", "Growth")]
    assert read.accounts[0].state == operations_pb2.ACCOUNT_STATE_OPEN
    growth = read.accounts[0]
    assert (growth.custodian, growth.account_type, growth.owner, growth.note) == (
        "Fidelity",
        "Roth IRA",
        "Fund I",
        "Rollover, 2026.",
    )
    (sent,) = service.operations.sent
    assert sent.acting_for == handed


# ── The account side (spec/the-account-side-fits-every-venue) ───────────────


async def test_what_the_venue_did_not_report_is_sent_unset_and_never_as_zero(
    sidecar,
) -> None:
    """A market value and a settle-date quantity are optional: SnapTrade and
    Kalshi report no value, and most venues no settle-date quantity."""
    service, _ = sidecar
    plugin = await connected(sidecar)
    try:
        await plugin.record_holding(
            quantity=Decimal("12.5"), side=meridian.HoldingSide.HOLDING_SIDE_LONG
        )
        await plugin.record_holding(
            quantity=Decimal("12.5"),
            side=meridian.HoldingSide.HOLDING_SIDE_LONG,
            settle_date_quantity=Decimal("0"),
            market_value=Money(Decimal("0"), "USD"),
        )
    finally:
        await plugin.leave()
    unreported, zero = service.operations.sent
    assert not unreported.HasField("market_value")
    assert not unreported.HasField("settle_date_quantity")
    # A zero the venue did say is sent, and is not the same thing.
    assert zero.HasField("market_value") and zero.HasField("settle_date_quantity")


async def test_a_holding_carries_its_side_its_settled_quantity_and_an_assumed_currency(
    sidecar,
) -> None:
    """E*TRADE's shape: a signed short with a value in a currency the venue
    did not state, so the connector says it assumed it."""
    service, _ = sidecar
    plugin = await connected(sidecar)
    try:
        await plugin.record_holding(
            instrument_id="INS-TSLA",
            side=meridian.HoldingSide.HOLDING_SIDE_SHORT,
            quantity=Decimal("-100"),
            settle_date_quantity=Decimal("-60"),
            market_value=Money(Decimal("-18250.00"), "USD"),
            currency_assumed=True,
            external_account_id="84001234",
        )
    finally:
        await plugin.leave()
    (sent,) = service.operations.sent
    assert sent.side == meridian.HoldingSide.HOLDING_SIDE_SHORT
    assert meridian.as_decimal(sent.quantity) == Decimal("-100")
    assert str(meridian.as_decimal(sent.settle_date_quantity)) == "-60"
    assert sent.currency_assumed


@pytest.mark.parametrize(
    ("field", "value", "refusal", "says"),
    [
        ("settle_date_quantity", 0.5, TypeError, "settle_date_quantity is a Decimal or an int"),
        ("settle_date_quantity", Decimal("1e-19"), ValueError, "settle_date_quantity has 19"),
        ("market_value", Money(0.5, "USD"), TypeError, "market_value is a Decimal or an int"),
    ],
)
async def test_an_optional_number_is_refused_like_any_other_when_it_is_given(
    sidecar, field: str, value: object, refusal: type[Exception], says: str
) -> None:
    service, _ = sidecar
    plugin = await connected(sidecar)
    try:
        with pytest.raises(refusal, match=says):
            await plugin.record_holding(quantity=Decimal(1), **{field: value})
    finally:
        await plugin.leave()
    assert service.operations.sent == []


async def test_a_statement_carries_the_venues_figures_as_reported(sidecar) -> None:
    service, _ = sidecar
    plugin = await connected(sidecar)
    try:
        await plugin.record_holdings_statement(
            source="etrade",
            external_statement_id="84001234/1757376000000000000",
            expected_rows=1,
            buying_power=Money(Decimal("41250.00"), "USD"),
            margin_requirement=Money(Decimal("18250.00"), "USD"),
            currency_assumed=True,
        )
        with pytest.raises(TypeError, match="maintenance_excess is a meridian.Money"):
            await plugin.record_holdings_statement(
                source="etrade",
                maintenance_excess=Decimal("1"),
            )
    finally:
        await plugin.leave()
    (sent,) = service.operations.sent
    assert str(meridian.as_money(sent.buying_power).amount) == "41250.00"
    assert sent.HasField("margin_requirement")
    assert not sent.HasField("maintenance_excess"), "not reported, so unset"
    assert sent.currency_assumed


async def test_a_connector_reports_the_accounts_it_reaches(sidecar) -> None:
    service, _ = sidecar
    plugin = await connected(sidecar)
    try:
        published = await plugin.report_external_accounts(
            accounts=[
                meridian.ExternalAccount(
                    external_account_id="SNAP-ACC-1",
                    name="Individual Brokerage 1234",
                    venue_account_type="Individual",
                )
            ]
        )
    finally:
        await plugin.leave()
    assert published.message_id == "msg-0"
    (sent,) = service.operations.sent
    assert [a.venue_account_type for a in sent.accounts] == ["Individual"]


async def test_a_sync_status_says_why_and_how_fresh(sidecar) -> None:
    service, _ = sidecar
    plugin = await connected(sidecar)
    try:
        await plugin.report_sync_status(
            source="etrade",
            external_account_id="84001234",
            state=meridian.SyncState.SYNC_STATE_NEEDS_SIGN_IN,
            holdings_as_of_ns=1_757_289_600_000_000_000,
            history_as_of_ns=1_757_203_200_000_000_000,
        )
    finally:
        await plugin.leave()
    (sent,) = service.operations.sent
    assert sent.state == meridian.SyncState.SYNC_STATE_NEEDS_SIGN_IN
    assert sent.holdings_as_of_ns > sent.history_as_of_ns


async def test_a_statement_names_its_account_and_its_figures_per_segment(sidecar) -> None:
    service, _ = sidecar
    plugin = await connected(sidecar)
    try:
        await plugin.record_holdings_statement(
            source="pb-standin",
            external_account_id="PB-7781",
            institution="the prime broker",
            expected_rows=0,
            figures=[
                meridian.StatementFigures(
                    segment="",
                    margin_requirement=Money(Decimal("310000.00"), "USD"),
                    collateral=[
                        meridian.ReportedCollateral(
                            direction="posted",
                            instrument_id="INS-UST10Y",
                            quantity=Decimal("500000"),
                            haircut=Decimal("0.02"),
                            held_at="the prime broker",
                        )
                    ],
                ),
                meridian.StatementFigures(
                    segment="commodities",
                    initial_margin=Money(Decimal("8800.00"), "USD"),
                ),
            ],
        )
    finally:
        await plugin.leave()
    (sent,) = service.operations.sent
    assert sent.external_account_id == "PB-7781"
    assert sent.institution == "the prime broker"
    assert [figures.segment for figures in sent.figures] == ["", "commodities"]
    (collateral,) = sent.figures[0].collateral
    assert collateral.direction == operations_pb2.COLLATERAL_DIRECTION_POSTED
    assert integer_and_scale(collateral.haircut) == (2, 2)
    assert not collateral.HasField("value"), "not reported, so unset"
    assert not sent.figures[1].HasField("buying_power")
    assert not sent.HasField("buying_power"), "nothing flat"


async def test_a_holding_carries_its_cost_and_lots_as_reported(sidecar) -> None:
    service, _ = sidecar
    plugin = await connected(sidecar)
    try:
        await plugin.record_holding(
            quantity=Decimal("-100"),
            average_cost=Money(Decimal("189.00"), "USD"),
            lots=[
                meridian.ReportedLot(
                    quantity=Decimal("-100"),
                    cost=Money(Decimal("-18900.00"), "USD"),
                    acquired_date="2026-09-02",
                ),
                meridian.ReportedLot(quantity=0),
            ],
            external_account_id="ext-1",
        )
    finally:
        await plugin.leave()
    (sent,) = service.operations.sent
    assert not sent.HasField("cost_basis"), "a per-unit average is not a total"
    assert str(meridian.as_money(sent.average_cost).amount) == "189.00"
    assert str(meridian.as_money(sent.lots[0].cost).amount) == "-18900.00", "sign as reported"
    assert sent.lots[0].acquired_date == "2026-09-02"
    assert not sent.lots[1].HasField("cost")


@pytest.mark.parametrize(
    ("given", "refusal", "says"),
    [
        (
            {"lots": [meridian.ReportedLot(quantity=Decimal("0.0000000000000000001"))]},
            ValueError,
            r"lots\[0\]\.quantity has 19 decimal places",
        ),
        (
            {"lots": [meridian.ReportedLot(quantity=1.5)]},  # type: ignore[arg-type]
            TypeError,
            r"lots\[0\]\.quantity is a Decimal or an int, not float",
        ),
        (
            {"lots": [{"quantity": Decimal("1")}]},
            TypeError,
            r"lots\[0\] is a meridian\.ReportedLot, not dict",
        ),
    ],
)
async def test_a_number_inside_a_lot_is_refused_naming_its_path(
    sidecar, given: dict, refusal: type[Exception], says: str
) -> None:
    service, _ = sidecar
    plugin = await connected(sidecar)
    try:
        with pytest.raises(refusal, match=says):
            await plugin.record_holding(
                quantity=Decimal(1), external_account_id="ext-1", **given
            )
    finally:
        await plugin.leave()
    assert service.operations.sent == []


@pytest.mark.parametrize(
    ("given", "says"),
    [
        (
            {
                "figures": [
                    meridian.StatementFigures(segment="securities"),
                    meridian.StatementFigures(segment="securities"),
                ]
            },
            r'figures\[1\]\.segment "securities" is named twice',
        ),
        (
            {
                "figures": [
                    meridian.StatementFigures(
                        collateral=[meridian.ReportedCollateral(quantity=Decimal(1))]
                    )
                ]
            },
            r"figures\[0\]\.collateral\[0\]\.direction is unspecified",
        ),
        (
            {
                "buying_power": Money(Decimal("25000.00"), "USD"),
                "figures": [meridian.StatementFigures(segment="")],
            },
            "buying_power is read from a plugin before v7; send it in figures",
        ),
        (
            {
                "figures": [
                    meridian.StatementFigures(
                        collateral=[meridian.ReportedCollateral(direction="lent", quantity=1)]
                    )
                ]
            },
            r"figures\[0\]\.collateral\[0\]\.direction is 'lent'",
        ),
    ],
)
async def test_a_statement_the_sidecar_would_refuse_is_refused_before_sending(
    sidecar, given: dict, says: str
) -> None:
    service, _ = sidecar
    plugin = await connected(sidecar)
    try:
        with pytest.raises(ValueError, match=says):
            await plugin.record_holdings_statement(external_account_id="ext-1", **given)
    finally:
        await plugin.leave()
    assert service.operations.sent == []


async def test_the_street_is_read_within_the_scope_the_sidecar_stamps(sidecar) -> None:
    service, _ = sidecar

    class Street:
        def positions(self, request):
            return operations_pb2.ListCustodialPositionsResult(
                positions=[operations_pb2.CustodialPosition(account_id="ACC-1")]
            )

        def statements(self, request):
            return operations_pb2.ListStatementsResult()

    service.operations.store = Street()
    plugin = await connected(sidecar)
    try:
        read = await plugin.list_custodial_positions(account_id="ACC-1", page_size=10)
        await plugin.list_statements(since=operations_pb2.Watermark())
    finally:
        await plugin.leave()
    assert [held.account_id for held in read.positions] == ["ACC-1"]
    asked, statements = service.operations.reads
    assert asked.account_id == "ACC-1" and asked.page_size == 10
    assert statements.HasField("since")
