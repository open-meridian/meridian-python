"""SDK 0.35.2: a typed delivery of the settings keeps the settings the SDK
declares beside the class -- each storage kind's `<kind>_window_days` and
`<kind>_past_window` -- which 0.35.1 dropped, so `RawStore.tend` could not
read them through `meridian.run(on_settings=...)` without the plugin
declaring its settings untyped (`settings=Config.declared()`).

Each test here fails on 0.35.1 (main 61be509): a typed delivery had no
`.values`, and `tend` took no `settings`.
"""

from __future__ import annotations

import asyncio
from datetime import date
from pathlib import Path
from typing import Any

import pytest

import meridian
from conftest import FakeSidecar
from meridian.declaration import Declaration, RecordKind, Storage
from meridian.edge import RawStore
from meridian.roles import custody
from meridian.v1 import sidecar_pb2


@meridian.settings
class Config:
    """A plugin's own settings, typed; the storage's are the SDK's."""

    api_key: str = meridian.setting("API key", secret=True)
    poll_seconds: int = meridian.setting("Read every", default=300, at_least=60)
    sample_data: bool = meridian.sample_data()


DECLARATION = Declaration(
    settings=Config,
    storage=Storage(kinds=[RecordKind("responses", "Raw responses", window_days=30)]),
)

DAY_NS = 86_400 * 1_000_000_000
OCT_1 = 1_790_812_800 * 1_000_000_000


def _delivery(**values: str) -> sidecar_pb2.SettingsDelivery:
    return sidecar_pb2.SettingsDelivery(
        values=[sidecar_pb2.SettingValue(name=n, value=v) for n, v in values.items()]
    )


class _Book(custody.Role):
    """A class for `run` to start; it does nothing of its own."""


async def _delivered_through_run(
    service: FakeSidecar, address: str, monkeypatch: pytest.MonkeyPatch, **values: str
) -> Any:
    """What `meridian.run(on_settings=...)` hands the plugin, first."""
    monkeypatch.setenv("MERIDIAN_SIDECAR_ADDRESS", address)
    service.settings = [_delivery(**values)]
    applied: list[Any] = []
    task = asyncio.create_task(
        meridian.run_async(DECLARATION, [_Book()], on_settings=applied.append)
    )
    try:
        for _ in range(300):
            if applied:
                break
            await asyncio.sleep(0.01)
    finally:
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task
    assert applied, "run delivered no settings"
    return applied[0]


async def test_run_delivers_the_typed_class_with_the_storage_windows_beside_its_fields(
    sidecar: tuple[FakeSidecar, str], monkeypatch: pytest.MonkeyPatch
) -> None:
    service, address = sidecar
    config = await _delivered_through_run(
        service,
        address,
        monkeypatch,
        api_key="k-1",
        poll_seconds="10",
        responses_window_days="90",
        responses_past_window="deleted",
    )
    assert isinstance(config, Config)
    assert config.api_key == "k-1" and config.poll_seconds == 60  # held to at_least
    assert config.values["responses_window_days"] == 90
    assert config.values["responses_past_window"] == "deleted"
    # The class's own fields, as typed on the instance, are among them.
    assert config.values["poll_seconds"] == 60 and config.values["sample_data"] is False
    assert list(config.values) == [
        "api_key",
        "poll_seconds",
        "sample_data",
        "responses_window_days",
        "responses_past_window",
    ]


async def test_the_windows_are_delivered_at_their_defaults_when_nothing_is_saved(
    sidecar: tuple[FakeSidecar, str], monkeypatch: pytest.MonkeyPatch
) -> None:
    service, address = sidecar
    config = await _delivered_through_run(service, address, monkeypatch)
    assert config.values["responses_window_days"] == 30  # the kind's own
    assert config.values["responses_past_window"] == "kept"  # no archive given


async def test_tend_reads_the_windows_from_the_typed_delivery(
    sidecar: tuple[FakeSidecar, str], monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    service, address = sidecar
    config = await _delivered_through_run(
        service,
        address,
        monkeypatch,
        responses_window_days="3",
        responses_past_window="archived",
    )
    store, mover = _kept(tmp_path), _Mover()
    await store.tend(mover, settings=config, today=date(2026, 10, 10))
    assert [m[:2] for m in mover.moved] == [
        ("archived", f"responses/2026-10-0{d}") for d in range(1, 7)
    ]


async def test_a_secrets_value_is_never_in_the_deliverys_values_repr(
    sidecar: tuple[FakeSidecar, str], monkeypatch: pytest.MonkeyPatch
) -> None:
    service, address = sidecar
    config = await _delivered_through_run(service, address, monkeypatch, api_key="k-secret")
    assert config.values["api_key"] == "k-secret"
    assert "k-secret" not in repr(config.values) and "k-secret" not in repr(config)


async def test_plugin_settings_given_the_class_carries_them_too(
    sidecar: tuple[FakeSidecar, str],
) -> None:
    """`first_settings` and `settings(Config)` are the same delivery as `run`'s."""
    service, address = sidecar
    service.settings = [_delivery(responses_window_days="45")]
    async with await meridian.connect(
        address, heartbeat=False, declaration=DECLARATION, roles=[]
    ) as plugin:
        config = await plugin.first_settings(Config)
    assert config.values["responses_window_days"] == 45


# ── tend, given the settings ───────────────────────────────────────────


class _Mover:
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
        store.keep("candles", "BTC-USD", {"received_at_ns": OCT_1 + day * DAY_NS, "body": "[]"})
    return store


@pytest.mark.parametrize(
    "settings",
    [
        meridian.Settings(
            values={"responses_window_days": 8, "responses_past_window": "deleted"}
        ),
        {"responses_window_days": 8, "responses_past_window": "deleted"},
    ],
    ids=["untyped", "values"],
)
async def test_tend_reads_them_alike_from_an_untyped_delivery_or_its_values(
    tmp_path: Path, settings: Any
) -> None:
    store, mover = _kept(tmp_path), _Mover()
    await store.tend(mover, settings=settings, today=date(2026, 10, 10))
    assert mover.moved == [("deleted", "responses/2026-10-01", 1)]


async def test_a_window_given_is_kept_over_the_settings(tmp_path: Path) -> None:
    store, mover = _kept(tmp_path), _Mover()
    held = {"responses_window_days": 8, "responses_past_window": "deleted"}
    await store.tend(mover, past="kept", settings=held, today=date(2026, 10, 10))
    assert not mover.moved


async def test_tend_refuses_settings_holding_no_window_for_its_kind(tmp_path: Path) -> None:
    store = RawStore(tmp_path, kind="session")
    with pytest.raises(ValueError, match="session_window_days"):
        await store.tend(_Mover(), settings=Config._of({}), today=date(2026, 10, 10))
    with pytest.raises(TypeError, match="settings="):
        await store.tend(_Mover(), today=date(2026, 10, 10))


def test_no_field_takes_a_name_the_delivery_holds() -> None:
    with pytest.raises(TypeError, match="values"):

        @meridian.settings
        class Clashing:
            values: str = meridian.setting("Values")
