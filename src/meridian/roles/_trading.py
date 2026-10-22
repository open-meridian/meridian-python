"""The records connectivity's Trading page answers, beside the credential row
every role's connection page shows: kept apart from both roles' modules so
the data role's Connection can carry connectivity's sections where one
plugin holds both (0.32.0; 457) without either importing the other."""

from __future__ import annotations

from dataclasses import dataclass, field

from ._latency import SessionLatency


@dataclass(frozen=True)
class Credential:
    """One credential as Connection's "Key" row shows it: its label, in the
    vendor's words, and whether it is set -- never its value."""

    label: str
    set: bool


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
    the last error. Counts and codes only: no account's data.

    From 0.32.0 the agents' demo-only guard's second key beside its first
    (contract v26; SDK-wide from Alpaca's and Tradier's records): the
    environment the session reached (`live`, `paper` or `sandbox`, empty
    before anything is reached) and the badge both keys make
    (`meridian.connection_badge`); a saved Environment this version refused
    (`environment_to_save`, SDK 0.31.1); and each open session's latency
    (contract v27, `session_latency`)."""

    credentials: list[Credential] = field(default_factory=list)
    environment: str = ""
    accounts: list[AccountTrading] = field(default_factory=list)
    working: int = 0
    held: int = 0
    unknown: int = 0
    last_poll: str = ""
    updates: str = ""
    error: str = ""
    reached_environment: str = ""
    badge: str = ""
    environment_to_save: str = ""
    session_latency: list[SessionLatency] = field(default_factory=list)
