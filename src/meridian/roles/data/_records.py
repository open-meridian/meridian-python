"""The data role's page records: each common page's tool's answer, which a
plugin extends with its own (spec/plugin-pages-follow-their-role)."""

from __future__ import annotations

from dataclasses import dataclass, field

from .._latency import SessionLatency
from .._trading import Credential as Credential  # the data role's, re-exported
from .._trading import TradingRead
from ._reading import Endpoint


@dataclass(frozen=True)
class ConnectionRead:
    """Connection's common fields (`read_connection`'s answer), which a
    plugin extends with its own: `mode` (Live, Sandbox, Sample data or No
    key); each credential, set or not; what the vendor serves this key; the
    vendor's limit and this plugin's share, in words; calls since start and
    how many were rate-limited and waited out; the last call, ISO 8601; the
    last error; and the streaming sessions open, None for a source that
    does not stream. From 0.32.0 (contract v27) each open session's
    latency (`session_latency`, `roles.Latency.session_latency()`), the
    Sessions section's rows; empty for none measured; and where the plugin
    holds connectivity too, connectivity's Trading (`trading`)."""

    mode: str
    credentials: list[Credential] = field(default_factory=list)
    entitled_at_vendor: str = ""
    limit: str = ""
    calls: int = 0
    rate_limited: int = 0
    last_call_at: str = ""
    last_error: str = ""
    sessions: int | None = None
    session_latency: list[SessionLatency] = field(default_factory=list)
    #: Where the plugin holds connectivity too (0.32.0; 457): its Trading
    #: page's record, drawn as Connection's further sections, one page for
    #: both roles (`connectivity.connection_pages`); None otherwise.
    trading: TradingRead | None = None


@dataclass(frozen=True)
class VenueConnection(ConnectionRead):
    """Connection for a source of one venue (0.30.0): the common fields, then
    the venue's name, the venue master's ID it resolved and whether the
    deployment holds it (the role's Venue row), whether the venue answers,
    the endpoints, what the venue allows and what the plugin spends of it,
    and the calls that failed."""

    venue: str = ""
    venue_id: str = ""
    venue_held: bool = False
    healthy: bool = False
    endpoints: list[Endpoint] = field(default_factory=list)
    allowed: str = ""
    spent: str = ""
    failures: int = 0


@dataclass(frozen=True)
class Served:
    """One dataset it serves, as its catalogue declares it ("Served")."""

    dataset: str
    data: str = ""
    arrives: str = ""
    day: str = ""
    default_terms: str = ""
    entitled_at_vendor: str = ""
    recorded: int = 0
    declined: int = 0
    last_recorded: str = ""
    licensed: bool = False


@dataclass(frozen=True)
class Want:
    """One want it answered, or a standing want it keeps current ("Wants")."""

    dataset: str
    asked: str = ""
    subjects: int = 0
    recorded: int = 0
    declined: int = 0
    state: str = ""


@dataclass(frozen=True)
class WantHeard(Want):
    """A want as `want_rows` lists it (0.30.0): the role's row, with the
    want's ID and whether it is kept current."""

    want_id: str = ""
    kept_current: bool = False


@dataclass(frozen=True)
class DatasetsRead:
    """Datasets' common fields (`read_datasets`'s answer): each dataset
    served, each want, and ("Subjects") whether the deployment lets it read
    an instrument's record (W3.6)."""

    served: list[Served] = field(default_factory=list)
    wants: list[Want] = field(default_factory=list)
    reads_instruments: bool = True
