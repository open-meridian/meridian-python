"""Quality states at the edge (contract v28, ruling 424; W10.4).

Every row a data plugin records carries the edge's judgement of it on its
envelope: `ObservationMeta.quality` (`valid`, `suspicious`, `invalid`; unset
read as valid) and `quality_reasons`. The lake keeps what the source said
and the state says what the edge judged: an invalid row is recorded, never
dropped, and a default read leaves it out. These are the checks every data
plugin makes the same, whatever its venue, so they are made here once, in
`Wants.record` (each row recorded unasked or for a standing want, as the
feed delay is):

- `crossed_quote`: a quote whose bid is above its ask beyond the dataset's
  `crossed_tolerance` is invalid; a locked quote (bid equal to ask) is valid;
- `duplicate`: a row whose content -- its subjects, its values and its source
  times -- is the same as the last row of its subject in its dataset, under
  a new row key, is suspicious;
- `sequence_gap`: the rows of a dataset whose source sequence skipped are
  suspicious until it is resynced (`EdgeChecks.sequenced`,
  `EdgeChecks.resynced`, which a stream with a contiguous sequence calls);
- `out_of_order`: a row whose source time is earlier than its subject's last
  beyond `out_of_order_tolerance` is suspicious;
- `stale`: a row that arrived past the dataset's `stale_after` is suspicious;
- `implausible_timestamp`: a row whose source time is ahead of the clock
  beyond `future_skew_max` is invalid.

A row the plugin already judged keeps its state where that is the higher,
and keeps its reasons: states only escalate. `schema` is the sidecar's: it
refuses a row that fails its dictionary bound, and the plugin keeps the raw
record.

The tolerances are the data plugin admin's `dataset_thresholds` (its v28
columns `crossed_tolerance`, `out_of_order_tolerance` and `future_skew_max`,
beside `stale_after`), plugin settings and not contract: `thresholds_from`
reads that setting's rows into `Thresholds` per dataset key.

A `signal` plugin escalates a recorded row's state with its own record,
`RecordQualityAssessments` (W10.12): `Baseline`, a robust rolling baseline
(median and MAD with a sigma floor and a warm-up), judges a close against
its subject's recent ones, and `assessment` writes what it found. Its
thresholds are its admin's `quality_thresholds` (`quality_thresholds()`).
"""

from __future__ import annotations

import dataclasses
import statistics
import time
from collections import deque
from collections.abc import Callable, Iterable, Mapping, Sequence
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any, cast

from ...operations import QualityAssessment
from ...plugin.v1 import operations_pb2 as ops

VALID = "valid"
SUSPICIOUS = "suspicious"
INVALID = "invalid"

#: The states in the order they escalate, by the wire's value and name.
_RANK = {
    0: 0,
    ops.QUALITY_STATE_VALID: 0,
    ops.QUALITY_STATE_SUSPICIOUS: 1,
    ops.QUALITY_STATE_INVALID: 2,
}
_STATE = {VALID: ops.QUALITY_STATE_VALID, SUSPICIOUS: ops.QUALITY_STATE_SUSPICIOUS,
          INVALID: ops.QUALITY_STATE_INVALID}  # fmt: skip

NANOS_PER_SECOND = 1_000_000_000


@dataclass(frozen=True)
class Thresholds:
    """One dataset's tolerances, from its row of `dataset_thresholds`: how
    far a bid may sit above its ask before the quote is invalid (in the
    quote's own price, 0 by default), how far back a source time may step
    before a row is out of order (1 second by default, so a snapshot read
    beside a stream does not flag the stream), how far ahead of our clock a source time
    may be (1 second by default), and how old a row may arrive before it is
    stale (0: not judged)."""

    crossed_tolerance: Decimal = Decimal(0)
    out_of_order_tolerance_ns: int = NANOS_PER_SECOND
    future_skew_max_ns: int = NANOS_PER_SECOND
    stale_after_ns: int = 0


def thresholds_from(rows: Iterable[Mapping[str, Any]] | None) -> dict[str, Thresholds]:
    """`dataset_thresholds`' rows as `Thresholds` by dataset key: seconds to
    nanoseconds, a tolerance a Decimal; a column left empty its default."""
    found: dict[str, Thresholds] = {}
    for row in rows or ():
        key = str(row.get("dataset") or "")
        if not key:
            continue

        def seconds(name: str, default: int, row: Mapping[str, Any] = row) -> int:
            value = row.get(name)
            if value in (None, ""):
                return default
            return int(Decimal(str(value)) * NANOS_PER_SECOND)

        crossed = row.get("crossed_tolerance")
        found[key] = Thresholds(
            crossed_tolerance=Decimal(str(crossed))
            if crossed not in (None, "")
            else Decimal(0),
            out_of_order_tolerance_ns=seconds("out_of_order_tolerance", NANOS_PER_SECOND),
            future_skew_max_ns=seconds("future_skew_max", NANOS_PER_SECOND),
            stale_after_ns=seconds("stale_after", 0),
        )
    return found


def _source_ns(row: Any) -> int:
    meta = getattr(row, "meta", None)
    times = [t.at_ns for t in getattr(meta, "source_times", ()) or () if t.at_ns]
    return max(times) if times else 0


def _amount(money: Any) -> Decimal | None:
    return None if money is None else Decimal(money.amount)


def _content(row: Any) -> tuple[Any, ...]:
    """What a row says, without the row key and the record of where it came
    from: two rows saying the same thing under two keys are a duplicate. A
    row stating an interval -- a bar, a day's close: its valid time to an
    end, or its business date -- says it of that interval (0.33.1), so the
    same values over another hour or day are no duplicate."""
    meta = row.meta
    said = {f.name: getattr(row, f.name) for f in dataclasses.fields(row) if f.name != "meta"}
    over = (
        (meta.valid_from_ns, meta.valid_until_ns, str(meta.business_date))
        if meta.valid_until_ns or meta.business_date
        else ()
    )
    return (
        tuple(s.entity_id for s in meta.subjects),
        tuple((t.kind, t.at_ns) for t in meta.source_times),
        repr(sorted(said.items())),
        over,
    )


def rank(state: Any) -> int:
    """A state's place in the escalation, by its value or name."""
    if isinstance(state, str):
        held = _STATE.get(state.lower())
        state = held if held is not None else ops.QualityState.Value(state)
    return _RANK.get(state or 0, 0)


@dataclass
class EdgeChecks:
    """The edge's quality checks over one plugin's rows (see the module):
    `thresholds` per dataset key, `default` for the rest."""

    thresholds: dict[str, Thresholds] = field(default_factory=dict)
    default: Thresholds = field(default_factory=Thresholds)
    clock_ns: Callable[[], int] = time.time_ns
    #: The datasets whose sequence skipped, until resynced, and each's last.
    gapped: set[str] = field(default_factory=set)
    last_sequence: dict[str, int] = field(default_factory=dict)
    #: Each subject's last row in each dataset: its row key, content and time.
    last: dict[tuple[str, str], tuple[str, tuple[Any, ...], int]] = field(default_factory=dict)
    #: How many rows of each state each dataset has recorded since start.
    counts: dict[str, dict[str, int]] = field(default_factory=dict)

    def of(self, key: str) -> Thresholds:
        return self.thresholds.get(key, self.default)

    # ── A stream's sequence ──────────────────────────────────────────────

    def sequenced(self, key: str, sequence: int) -> bool:
        """The source's sequence number of the dataset `key`'s next message:
        true where it skipped, after which the dataset's rows are suspicious
        until `resynced`. A repeat or a step back is not a gap."""
        before = self.last_sequence.get(key)
        self.last_sequence[key] = max(sequence, before or 0)
        if before is not None and sequence > before + 1:
            self.gapped.add(key)
            return True
        return False

    def resynced(self, key: str) -> None:
        """The dataset's stream resynced (a snapshot taken, the gap read
        back, a new connection numbering afresh): its rows are judged as
        before, its sequence counted again from the next message."""
        self.gapped.discard(key)
        self.last_sequence.pop(key, None)

    # ── Judging rows ─────────────────────────────────────────────────────

    def judge(self, key: str, row: Any) -> tuple[str, tuple[str, ...]]:
        """The edge's state for `row` of the dataset `key`, and its reasons;
        noting the row as its subject's last."""
        meta = getattr(row, "meta", None)
        if meta is None:
            return VALID, ()
        held = self.of(key)
        now = self.clock_ns()
        found: list[tuple[str, str]] = []
        bid, ask = _amount(getattr(row, "bid", None)), _amount(getattr(row, "ask", None))
        if bid is not None and ask is not None and bid - ask > held.crossed_tolerance:
            found.append((INVALID, "crossed_quote"))
        at = _source_ns(row)
        if at and at - now > held.future_skew_max_ns:
            found.append((INVALID, "implausible_timestamp"))
        if at and held.stale_after_ns and now - at > held.stale_after_ns:
            found.append((SUSPICIOUS, "stale"))
        if key in self.gapped:
            found.append((SUSPICIOUS, "sequence_gap"))
        subjects = tuple(s.entity_id for s in meta.subjects)
        if subjects:
            content = _content(row)
            mark = (key, subjects[0])
            last = self.last.get(mark)
            if last is not None:
                last_key, last_content, last_at = last
                if last_key != meta.row_key and last_content == content:
                    found.append((SUSPICIOUS, "duplicate"))
                if at and last_at and last_at - at > held.out_of_order_tolerance_ns:
                    found.append((SUSPICIOUS, "out_of_order"))
            self.last[mark] = (meta.row_key, content, max(at, last[2] if last else 0))
        state = max((s for s, _ in found), key=rank, default=VALID)
        return state, tuple(reason for _, reason in found)

    def judged(self, key: str, rows: Sequence[Any]) -> list[Any]:
        """Each of `rows` with the edge's state on its envelope, escalated
        over any the plugin set (never lowered), and counted."""
        out: list[Any] = []
        counted = self.counts.setdefault(key, {VALID: 0, SUSPICIOUS: 0, INVALID: 0})
        for row in rows:
            state, reasons = self.judge(key, row)
            meta = getattr(row, "meta", None)
            if meta is None:
                out.append(row)
                continue
            held = meta.quality
            kept = tuple(meta.quality_reasons)
            if held is not None and rank(held) > rank(state):
                state_now: Any = held
            else:
                state_now = state if reasons or held is not None else None
            merged = kept + tuple(r for r in reasons if r not in kept)
            name = {0: VALID, 1: SUSPICIOUS, 2: INVALID}[rank(state_now)]
            counted[name] += 1
            if state_now is None:
                out.append(row)
                continue
            out.append(
                dataclasses.replace(
                    row,
                    meta=dataclasses.replace(meta, quality=state_now, quality_reasons=merged),
                )
            )
        return out


# ── A signal's escalation (W10.12) ───────────────────────────────────────


@dataclass(frozen=True)
class OutlierThresholds:
    """One dataset's row of `quality_thresholds`: suspicious past
    `outlier_sigma` robust deviations, invalid past `invalid_sigma`, the
    deviation never below `sigma_floor` (in the price's own units), and no
    judgement before `warm_up` values are held."""

    outlier_sigma: Decimal = Decimal(5)
    invalid_sigma: Decimal = Decimal(10)
    sigma_floor: Decimal = Decimal(0)
    warm_up: int = 20
    cross_source_tolerance: Decimal = Decimal(0)


#: MAD to a standard deviation, for a normal distribution.
_MAD_SIGMA = Decimal("1.4826")


@dataclass
class Baseline:
    """A robust rolling baseline per subject (the spec's `price_outlier`):
    the median of its last `window` values and their median absolute
    deviation, scaled to a sigma and floored. `judge` answers a value's
    state and reason against it, then holds the value; `reseed` starts a
    subject again after a regime break (a session open, a halt's end)."""

    thresholds: OutlierThresholds = field(default_factory=OutlierThresholds)
    window: int = 100
    held: dict[str, deque[Decimal]] = field(default_factory=dict)

    def reseed(self, subject: str) -> None:
        self.held.pop(subject, None)

    def judge(self, subject: str, value: Decimal) -> tuple[str, tuple[str, ...]]:
        values = self.held.setdefault(subject, deque(maxlen=self.window))
        state, reasons = VALID, cast(tuple[str, ...], ())
        if len(values) >= max(self.thresholds.warm_up, 1):
            median = Decimal(statistics.median(values))
            mad = Decimal(statistics.median(abs(v - median) for v in values))
            sigma = max(mad * _MAD_SIGMA, self.thresholds.sigma_floor)
            if sigma > 0:
                away = abs(value - median) / sigma
                if away > self.thresholds.invalid_sigma:
                    state, reasons = INVALID, ("price_outlier",)
                elif away > self.thresholds.outlier_sigma:
                    state, reasons = SUSPICIOUS, ("price_outlier",)
        if state == VALID:
            values.append(value)  # an outlier never moves the baseline
        return state, reasons


def assessment(row: Any, state: str, reasons: Sequence[str]) -> QualityAssessment:
    """A signal's assessment of a recorded row's version (heard or read):
    its dataset, row key and version, the new state and why."""
    meta = row.meta
    return QualityAssessment(
        dataset=meta.source.dataset,
        row_key=meta.row_key,
        version=int(meta.version),
        state=state,
        reasons=tuple(reasons),
    )
