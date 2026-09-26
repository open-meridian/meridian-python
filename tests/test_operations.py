"""The typed operations, from the plugin's side (spec/typed-sidecar-operations).

Against the fake sidecar: what these hold is the client's half -- the params
each operation sends, amounts scaled exactly or refused, the sidecar's fields
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
from meridian import CallFailed, Identifier, NotGranted
from meridian.plugin.v1 import operations_pb2


async def connected(sidecar: tuple[FakeSidecar, str]) -> meridian.Plugin:
    _, address = sidecar
    return await meridian.connect(address, heartbeat=False)


async def test_an_amount_crosses_as_a_scaled_integer_exactly(sidecar) -> None:
    service, _ = sidecar
    plugin = await connected(sidecar)
    try:
        result = await plugin.record_holding(
            statement_id="S-1",
            quantity=Decimal("12.5"),
            market_value=Decimal("20000.00000001"),
            currency="USD",
            external_account_id="ext-1",
        )
    finally:
        await plugin.leave()
    assert result.holding_id == "H-1"
    (sent,) = service.operations.sent
    assert isinstance(sent, operations_pb2.RecordHoldingParams)
    assert sent.quantity_scaled_1e8 == 1_250_000_000
    assert sent.market_value_scaled_1e8 == 2_000_000_000_001
    assert sent.external_account_id == "ext-1"


@pytest.mark.parametrize(
    ("quantity", "refusal", "says"),
    [
        (Decimal("0.123456789"), ValueError, "eight decimal places"),
        (Decimal("NaN"), ValueError, "not a finite amount"),
        (Decimal("Infinity"), ValueError, "not a finite amount"),
        (Decimal("1e20"), ValueError, "too large"),
        (0.1, TypeError, "is a Decimal"),
    ],
)
async def test_an_amount_that_cannot_cross_exactly_is_refused_before_anything_is_sent(
    sidecar, quantity: object, refusal: type[Exception], says: str
) -> None:
    service, _ = sidecar
    plugin = await connected(sidecar)
    try:
        with pytest.raises(refusal, match=says):
            await plugin.record_holding(
                quantity=quantity,  # type: ignore[arg-type]
                market_value=Decimal(0),
            )
    finally:
        await plugin.leave()
    assert service.operations.sent == [], "nothing is sent for a refused amount"


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
