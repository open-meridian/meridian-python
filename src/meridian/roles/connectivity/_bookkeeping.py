"""A connectivity plugin's placement bookkeeping (0.30.0; sdk-contract/the-sdk-
carries-each-roles-common-logic): what every connectivity plugin must do the
same to place an order at most once and to say what became of it, whatever
its venue and however it reaches it -- an API, FIX, anything. The plugin
supplies the send and the read of the venue's orders; nothing here speaks to
a venue.

**No double send** (W11.8): a placement is noted in the plugin's own storage
before it is sent (`Sent`), so one the book still holds queued after a restart
is asked about, never sent again. From 0.37.0 the note is a marker of its own,
`trading/sent/<pid>`, created exclusively: of two pods sharing a shard's
folder inside a takeover's lapse, only the one that created it sends:

    sent = connectivity.Sent(storage / "trading" / "sent.json")
    outcome = await connectivity.place_once(
        self, sent, placement.placement_id,      # self: the connectivity role's class
        lambda: venue.place(code, asked),        # the plugin's own send
        source="tradier",
    )
    if outcome.state == "placed":
        record, raw_key = outcome.answer, outcome.raw_key

`place_once` reports what the send itself settles: a refusal the venue
answered (`VenueRefused`, raised by the plugin's send) is the placement
rejected `venue rejected`, its code and words as reported; a send never
answered (`VenueUnanswered`) is outcome unknown, `request unanswered`.

**An unknown outcome resolved** (W11.10): never by sending again, but by
reading the venue's orders and finding the placement's own by the tag it was
sent with, the client order ID (`resolve_unanswered`). A status the plugin's
mapping does not know is outcome unknown, `venue status not mapped`, the
status as reported (`report_status_not_mapped`).

**Fills** (W11.11): a fill read from an order's filled quantity growing is
the same fill however often it is read -- its ID derived from the venue's
order and the quantity it brought the order to (`execution_id`), a bust's
from the fill's (`bust_id`) -- and what the book already holds filled on a
placement is the sum of its fills, each bust taken off (`filled_in_book`).
A fill's price from two averages is `fill_price`.

Which orders a venue offers, how it is asked, and its words for a status
stay the plugin's.
"""

from __future__ import annotations

import contextlib
import hashlib
import json
import os
from collections.abc import Awaitable, Callable, Iterable, Iterator, Sequence
from dataclasses import dataclass
from decimal import ROUND_HALF_EVEN, Decimal
from pathlib import Path
from typing import Any, TypeVar
from urllib.parse import quote, unquote

from ...operations import as_decimal
from ...plugin.v1 import operations_pb2 as ops

__all__ = [
    "Placed",
    "Sent",
    "VenueRefused",
    "VenueUnanswered",
    "bust_id",
    "execution_id",
    "fill_price",
    "filled_in_book",
    "place_once",
    "report_status_not_mapped",
    "resolve_unanswered",
]

Order = TypeVar("Order")


class VenueRefused(Exception):
    """The venue answered a send with a refusal: its code and words, and the
    raw record they are in. Raised by the plugin's own send."""

    def __init__(self, code: str, text: str, raw_key: str) -> None:
        super().__init__(f"{code} {text}".strip())
        self.code, self.text, self.raw_key = code, text, raw_key


class VenueUnanswered(Exception):
    """The venue never answered a send: it may have reached the venue. Raised
    by the plugin's own send, with the raw record of what was asked."""

    def __init__(self, why: str, raw_key: str) -> None:
        super().__init__(why)
        self.raw_key = raw_key


class Sent:
    """The placements sent, by ID, each noted in the plugin's storage before
    its send; None for a test, which keeps them in memory. The same serves
    any set of names a plugin must not lose -- the accounts trading is
    enabled on, say.

    From 0.37.0 (step 3d) each name is a file of its own beside the file
    given, in the folder of its name: `trading/sent/<pid>` for
    `trading/sent.json`. It is created exclusively, so where two pods share
    the folder -- a deposed holder and the one that took its shard, inside
    the takeover's lapse -- one creates it and the other is told it was
    noted (`note` answers False), and a note never drops another's. The
    file given, as an earlier release wrote it whole, is read and never
    written again."""

    def __init__(self, file: Path | None) -> None:
        self._file = file
        self._held: set[str] = set()
        #: The given file's modification time when last read: an earlier
        #: release's pod writing it again (a rollout inside a lapse) is read.
        self._read_at: int | None = None
        self._read_file()

    def _read_file(self) -> None:
        """The names in the given file, as an earlier release wrote it whole."""
        file = self._file
        if file is None:
            return
        try:
            at = file.stat().st_mtime_ns
        except OSError:
            return
        if at == self._read_at:
            return
        self._read_at = at
        with contextlib.suppress(OSError, ValueError):
            held = json.loads(file.read_text())
            if isinstance(held, list):
                self._held |= {str(each) for each in held}

    @property
    def _folder(self) -> Path | None:
        """Where each name is noted: the given file's path without its
        suffix (`<name>.d` for a file given none)."""
        if self._file is None:
            return None
        bare = self._file.with_suffix("")
        return bare if bare != self._file else self._file.with_name(self._file.name + ".d")

    def _marker(self, name: str) -> Path | None:
        folder = self._folder
        return None if folder is None else folder / _marker_name(name)

    def __contains__(self, name: object) -> bool:
        if not isinstance(name, str):
            return False
        if name in self._held:
            return True
        marker = self._marker(name)
        if marker is not None and marker.exists():
            self._held.add(name)
            return True
        self._read_file()
        return name in self._held

    def _noted(self) -> set[str]:
        """Every name noted: the file given, and each marker in the folder,
        another pod's too."""
        names = set(self._held)
        folder = self._folder
        if folder is None or not folder.is_dir():
            return names
        for marker in folder.iterdir():
            if marker.name.startswith(".") or not marker.is_file():
                continue
            if marker.name.startswith(_HASHED):
                with contextlib.suppress(OSError, UnicodeDecodeError):
                    said = marker.read_text(encoding="utf-8")
                    if _marker_name(said) == marker.name:
                        names.add(said)
                continue
            names.add(unquote(marker.name))
        return names

    def __iter__(self) -> Iterator[str]:
        return iter(sorted(self._noted()))

    def __len__(self) -> int:
        return len(self._noted())

    def note(self, name: str) -> bool:
        """Keep `name`, in storage before this returns: True where this
        noted it, False where it was noted already, by this process or
        another sharing the folder."""
        if name in self:
            return False
        marker = self._marker(name)
        if marker is None:
            self._held.add(name)
            return True
        made_folder = not marker.parent.is_dir()
        marker.parent.mkdir(parents=True, exist_ok=True)
        if made_folder:
            _sync_folder(marker.parent.parent)
        try:
            made = os.open(marker, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o644)
        except FileExistsError:
            self._held.add(name)
            return False
        try:
            try:
                os.write(made, name.encode("utf-8"))
                os.fsync(made)
            finally:
                os.close(made)
        except BaseException:
            # Not kept, so nothing was done under it: the marker goes, or it
            # would read as noted with nothing behind it.
            marker.unlink(missing_ok=True)
            raise
        _sync_folder(marker.parent)
        self._held.add(name)
        return True


#: A marker named by its name's digest, the name too long for a file's.
_HASHED = "~"
_MOST_MARKER = 200


def _marker_name(name: str) -> str:
    """A name as its marker's file name: percent-encoded, so any name is one
    file in the folder, a leading dot too (`.`, `..`); a digest where that
    is empty or too long, the name then read from the marker itself."""
    said = quote(name, safe="-_@+=,")
    if said.startswith("."):
        said = "%2E" + said[1:]
    if not said or len(said) > _MOST_MARKER or said.startswith(_HASHED):
        return _HASHED + hashlib.sha256(name.encode("utf-8")).hexdigest()
    return said


def _sync_folder(folder: Path) -> None:
    """The folder's entry for a new marker made durable, where the file
    system allows it."""
    with contextlib.suppress(OSError):
        held = os.open(folder, os.O_RDONLY)
        try:
            os.fsync(held)
        finally:
            os.close(held)


@dataclass(frozen=True)
class Placed:
    """What `place_once` settled: `placed`, the venue's answer and the raw
    record it was read from; `rejected` or `unknown`, each already reported;
    or `sent_before`, nothing sent, the placement to be found among the
    venue's orders (`resolve_unanswered`)."""

    state: str
    answer: Any = None
    raw_key: str = ""


async def place_once(
    role: Any,
    sent: Sent,
    placement_id: str,
    send: Callable[[], Awaitable[tuple[Any, str]]],
    *,
    source: str,
) -> Placed:
    """Send a placement at most once: noted in `sent` before `send` is called,
    never sent where it was noted before (a restart's queued placement, or
    one another pod noted first on the shard's folder: `sent_before`). A
    `VenueRefused` is reported rejected `venue rejected`, its code and words
    as reported under `<source>:error`; a `VenueUnanswered` outcome unknown,
    `request unanswered`. `send` answers the venue's answer and the raw
    record's key; anything else it raises is raised, the placement noted."""
    if placement_id in sent or not sent.note(placement_id):
        # Noted before: by this process, or by another pod on the shard's
        # folder (a takeover's lapse), whose note alone may send it.
        return Placed("sent_before")
    try:
        answer, raw_key = await send()
    except VenueRefused as refused:
        await role.report_placement(
            placement_id=placement_id,
            event=ops.PLACEMENT_EVENT_REJECTED,
            rejection_reason=ops.REJECTION_REASON_VENUE_REJECTED,
            rejection_as_reported=ops.AsReported(
                scheme=f"{source}:error"[:64],
                code=(refused.code or "?")[:128],
                text=(refused.text or "the venue refused the order")[:256],
            ),
            raw_record=raw_or_unkept(role.plugin, refused.raw_key),
        )
        return Placed("rejected", raw_key=refused.raw_key)
    except VenueUnanswered as lost:
        await role.report_placement(
            placement_id=placement_id,
            event=ops.PLACEMENT_EVENT_OUTCOME_UNKNOWN,
            unknown_reason=ops.UNKNOWN_REASON_REQUEST_UNANSWERED,
            raw_record=raw_or_unkept(role.plugin, lost.raw_key),
        )
        return Placed("unknown", raw_key=lost.raw_key)
    return Placed("placed", answer, raw_key)


def raw_or_unkept(plugin: Any, key: str) -> Any:
    """The raw record a key names, or "unkept" where the venue's exchange
    was kept nowhere: a name for no record, which no shard's prefix is put
    on (step 3d, item 30)."""
    if key:
        return plugin.raw_record(key)
    reference = plugin.raw_record("unkept")
    reference.key = "unkept"
    return reference


def resolve_unanswered(
    unanswered: Iterable[str], orders: Iterable[Order], client_order_id: Callable[[Order], str]
) -> dict[str, Order]:
    """Each placement whose send went unanswered, found among the venue's
    orders by the tag it was sent with -- its placement ID as the client
    order ID; one not found is not among them yet, and is asked about again
    at the next read, never sent again."""
    by_client = {client_order_id(order): order for order in orders if client_order_id(order)}
    return {pid: by_client[pid] for pid in unanswered if pid in by_client}


async def report_status_not_mapped(
    role: Any, placement_id: str, status: str, source: str, raw_key: str
) -> None:
    """A status the plugin's mapping does not know: outcome unknown, `venue
    status not mapped`, the status as reported under `<source>:order-status`."""
    await role.report_placement(
        placement_id=placement_id,
        event=ops.PLACEMENT_EVENT_OUTCOME_UNKNOWN,
        unknown_reason=ops.UNKNOWN_REASON_VENUE_STATUS_NOT_MAPPED,
        status_as_reported=ops.AsReported(
            scheme=f"{source}:order-status"[:64],
            code=status[:128] or "?",
            text=status[:256] or "?",
        ),  # fmt: skip
        raw_record=raw_or_unkept(role.plugin, raw_key),
    )


def execution_id(order_id: str, filled: Decimal) -> str:
    """A fill's derived ID: the venue's order and the filled quantity it
    brought the order to, the same however often, and however, it is read."""
    return f"{order_id}:{filled.normalize():f}"


def bust_id(fill: str) -> str:
    """The ID of the bust taking back the fill `fill`."""
    return f"{fill}:busted"


def fill_price(
    before: Decimal,
    average_before: Decimal | None,
    after: Decimal,
    average_after: Decimal,
    places: int,
) -> tuple[Decimal, bool]:
    """A fill's price from an order's average price before and after it, and
    whether it was rounded: exact where the division is, otherwise rounded
    half-even to `places` places."""
    paid = average_after * after - (average_before or Decimal(0)) * before
    quantity = after - before
    price = paid / quantity
    rounded = price.quantize(Decimal(1).scaleb(-places), rounding=ROUND_HALF_EVEN)
    exact = rounded * quantity == paid
    return (rounded.normalize() if exact else rounded), not exact


def filled_in_book(
    placement_id: str, executions: Sequence[ops.Execution], besides: str = ""
) -> Decimal:
    """What the book holds filled on a placement, each bust taken off; with
    `besides`, only the fills of venue orders other than it (the fills a
    replaced order carried)."""
    busted = {e.supersedes for e in executions if e.supersedes}
    total = Decimal(0)
    for execution in executions:
        if execution.placement_id != placement_id or execution.execution_id in busted:
            continue
        if execution.supersedes:
            continue
        if besides and execution.venue_execution_id.startswith(f"{besides}:"):
            continue
        total += as_decimal(execution.quantity)
    return total
