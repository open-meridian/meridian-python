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
from meridian import CallFailed, Identifier, Money, NotGranted
from meridian.plugin.v1 import operations_pb2


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


def test_only_commands_are_sent_for_a_person() -> None:
    """Reads carry no person (decisions/014): a plugin reads as itself."""
    assert "acting_for" in inspect.signature(meridian.Plugin.record_holding).parameters
    assert "acting_for" not in inspect.signature(meridian.Plugin.resolve_identifier).parameters
    assert "acting_for" not in inspect.signature(meridian.Plugin.report_sync_status).parameters
