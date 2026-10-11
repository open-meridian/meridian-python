"""A data plugin's common part (spec/plugin-pages-follow-their-role, "data, a
data plugin"), and its restart's backfill (contract v20, W10.6).

**First-use path.** Enter the key (Settings); check the connection
(Connection); have its datasets licensed and entitled (a deployment admin, on
Data sources); see data arrive (Datasets). Prices are seen in a reading
plugin's pages, never here.

**Settings**, in this order: `meridian.environment()` where the vendor has
more than one; the credentials, each a required secret labelled in the
vendor's words and gated on the environment where they differ by it; the
vendor's own; `meridian.sample_data()`.

**Pages**, Manage only, in this order:

    @pages.page("/", "Connection", levels="admin", answers=data.ConnectionRead,
                name="read_connection")
    async def connection(request):
        return pages.answer("meridian/roles/data/connection.html", ConnectionRead(...))

    @pages.page("/datasets", "Datasets", levels="admin", answers=data.DatasetsRead,
                name="read_datasets")

Connection's sections are "Key", "Limits and use" and "Stream"; Datasets'
"Served", "Wants" and "Subjects". From contract v20 a data plugin reads its
own declared datasets' licences (`plugin.list_datasets()`, its `licences`),
so Datasets says "Licensed" or "Not licensed yet" exactly.

**Figures**, the role's first: "Connection", "Entitled at the vendor",
"Stream", "Last recorded", "Rate use" (`figures(...)`); three places remain
for the vendor's.

**A restart's gap** (`backfill_restart`): on start, before resuming its
stream, a data plugin that records trades reads the last trade its own
instance recorded of each subject it streams (`list_trades(...,
latest_recorded=True)`), reads the venue's history from each, and records
what it missed; a trade recorded again is answered unchanged by its row key,
so the overlap costs nothing.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable, Sequence
from dataclasses import dataclass, field
from typing import Any

from ..figures import Figure
from ..operations import Trade
from ..plugin.v1 import operations_pb2 as ops
from ._figures import Value, ordered

__all__ = [
    "ConnectionRead",
    "Credential",
    "DatasetsRead",
    "Served",
    "Want",
    "backfill_restart",
    "figures",
]


@dataclass(frozen=True)
class Credential:
    """One credential as Connection's "Key" row shows it: its label, in the
    vendor's words, and whether it is set -- never its value."""

    label: str
    set: bool


@dataclass(frozen=True)
class ConnectionRead:
    """Connection's common fields (`read_connection`'s answer), which a
    plugin extends with its own: `mode` (Live, Sandbox, Sample data or No
    key); each credential, set or not; what the vendor serves this key; the
    vendor's limit and this plugin's share, in words; calls since start and
    how many were rate-limited and waited out; the last call, ISO 8601; the
    last error; and the streaming sessions open, None for a source that
    does not stream."""

    mode: str
    credentials: list[Credential] = field(default_factory=list)
    entitled_at_vendor: str = ""
    limit: str = ""
    calls: int = 0
    rate_limited: int = 0
    last_call_at: str = ""
    last_error: str = ""
    sessions: int | None = None


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
class DatasetsRead:
    """Datasets' common fields (`read_datasets`'s answer): each dataset
    served, each want, and ("Subjects") whether the deployment lets it read
    an instrument's record (W3.6)."""

    served: list[Served] = field(default_factory=list)
    wants: list[Want] = field(default_factory=list)
    reads_instruments: bool = True


def _connection(value: Any) -> str | None:
    return {"Not answering": "error", "No key": "warn"}.get(str(value))


def figures(
    *,
    connection: Value,
    entitled_at_vendor: Value = None,
    stream: Value = None,
    last_recorded: Value = None,
    rate_use: Value = None,
) -> list[Figure]:
    """The data role's figures, in its order, each a plain value or a
    `meridian.Figure` carrying its state and why: "Connection" ("Answering",
    "Not answering", an error, "No key", a warning, or "Sample data");
    "Entitled at the vendor" ("3 of 4 datasets", warn when fewer than
    declared, why naming those not served); "Stream" ("12 listings", "Off" or
    "Does not stream"); "Last recorded" (a time, error when the last
    recording failed); "Rate use" ("41 of 100 a minute", warn at four fifths
    of the limit). None leaves one out. Follow them with the vendor's own."""
    return ordered(
        [
            ("Connection", connection, _connection),
            ("Entitled at the vendor", entitled_at_vendor, None),
            ("Stream", stream, None),
            ("Last recorded", last_recorded, None),
            ("Rate use", rate_use, None),
        ]
    )


#: What `backfill_restart` asks of the plugin: the trades the venue's history
#: states after the last one recorded, given as the lake answered it (its
#: subject, dataset, venue and time in `meta`).
_History = Callable[[ops.Trade], Awaitable[Sequence[Trade]]]

#: Subjects a read names, and trades a batch records, at most (W10.4, W10.6).
_MOST = 500


async def backfill_restart(plugin: Any, subjects: Sequence[str], history: _History) -> int:
    """Backfill a restart's gap (contract v20, W10.6), before resuming the
    stream: read the last trade this instance recorded of each subject in
    `subjects` (`list_trades(..., latest_recorded=True)`, its own rows only,
    per dataset and venue), ask `history` for the trades the venue states
    after each, and record them in batches of 500. A trade recorded again is
    answered unchanged by its row key. A subject never recorded answers
    nothing and starts from the stream; a venue whose history reaches back
    less far leaves the rest missing, for the plugin's Datasets page to say.
    Answers how many trades were sent."""
    sent = 0
    for start in range(0, len(subjects), _MOST):
        asked = [ops.SubjectRef(entity_id=each) for each in subjects[start : start + _MOST]]
        cursor = ""
        while True:
            answer = await plugin.list_trades(
                subjects=asked, latest_recorded=True, cursor=cursor
            )
            for last in answer.trades:
                missed = list(await history(last))
                for at in range(0, len(missed), _MOST):
                    batch = missed[at : at + _MOST]
                    await plugin.record_trades(trades=batch)
                    sent += len(batch)
            cursor = answer.next_cursor
            if not cursor:
                break
    return sent
