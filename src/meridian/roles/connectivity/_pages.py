"""Connectivity's Trading page (0.30.0): connectivity's state at the venue,
each the same answer as its tool (`read_trading`) -- each credential set or
not, never a value; the environment, said plainly; each account the key
reaches by its venue account code, read-only or with trading enabled, the
order types its catalogue offers and whether its `ems` mapped it here; and
the placements working, held back by a pause or a stop, or of unknown
outcome. Counts and codes only: an admin page shows no account's data.
Drawn by `meridian/roles/connectivity/trading.html`; "Enable trading" on a
read-only account is the connectivity role's admin's (`enable_trading`,
checked by `check_enable_trading`), declared by the plugin on its own pages."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from ...plugin.v1 import operations_pb2 as ops
from ..data import Credential


@dataclass(frozen=True)
class AccountTrading:
    """One account the key reaches, as connectivity trades it: its venue
    account code, whether trading is enabled on it (read-only until the
    connectivity role's admin enables it), the order types its catalogue
    offers, and whether its ems has mapped it on this instance."""

    venue_account_code: str
    trading: bool = False
    order_types: list[str] = field(default_factory=list)
    mapped: bool = False


@dataclass(frozen=True)
class TradingRead:
    """Trading, at Manage: each credential, set or not (never its value), the
    environment the account is in (Paper or Live, said plainly, or sample
    data), each account and its trading, the placements working, held back by
    a pause or a stop, and of unknown outcome, the last read of the orders,
    how its orders are heard (`updates`: a poll, or a stream's state), and
    the last error. Counts and codes only: no account's data."""

    credentials: list[Credential] = field(default_factory=list)
    environment: str = ""
    accounts: list[AccountTrading] = field(default_factory=list)
    working: int = 0
    held: int = 0
    unknown: int = 0
    last_poll: str = ""
    updates: str = ""
    error: str = ""


@dataclass(frozen=True)
class TradingAsked:
    """An account to enable trading on, by its venue account code."""

    venue_account_code: str


@dataclass(frozen=True)
class TradingEnabled:
    """What enabling trading came to, or would."""

    venue_account_code: str
    said: str = ""


def _shown(at: datetime | None) -> str:
    return at.astimezone(UTC).isoformat(timespec="seconds").replace("+00:00", "Z") if at else ""


def trading_read(
    trader: Any, credentials: Sequence[Credential], environment: str, updates: str = ""
) -> TradingRead:
    """Trading's record from the plugin's `Trader` (None before its role is
    held): the accounts it reached, each one's trading and catalogue, and its
    counts; `credentials` and `environment` in the vendor's words, `updates`
    how its orders are heard."""
    mapped = trader.mapped() if trader is not None else frozenset()
    shown = trader.shown if trader is not None else None
    reached: tuple[str, ...] = trader.reached if trader is not None else ()
    return TradingRead(
        credentials=list(credentials),
        environment=environment,
        accounts=[
            AccountTrading(
                venue_account_code=code,
                trading=trader is not None and trader.trading_on(code),
                order_types=[
                    ops.OrderType.Name(t).removeprefix("ORDER_TYPE_").lower()
                    for t, _ in (trader.offered(code) if trader is not None else ())
                ],
                mapped=code in mapped,
            )
            for code in reached
        ],
        working=shown.working if shown else 0,
        held=shown.held if shown else 0,
        unknown=shown.unknown if shown else 0,
        last_poll=_shown(shown.last_poll) if shown else "",
        updates=updates,
        error=shown.error if shown else "",
    )
