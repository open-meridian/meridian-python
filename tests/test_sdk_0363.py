"""SDK 0.36.3: the holder of each series' first valid time made public
(`option_chains.SeriesTimes`), so a plugin running its own chain machine
keeps the row-key rule (spec/the-lake rule 5: a row key fixes its valid time
and its first subject) without importing or copying the SDK's private code;
`option_chains.Feed` built on it."""

from __future__ import annotations

import datetime as dt
import json
from pathlib import Path
from typing import Any

import pytest

from meridian.errors import CallFailed
from meridian.helpers import chains
from meridian.plugin.v1 import operations_pb2 as ops
from meridian.receive import Heard
from meridian.roles.data import option_chains
from meridian.roles.data.option_chains import SeriesTimes
from meridian.suites import Recorder

NS = 1_000_000_000
DAY_NS = 24 * 3600 * NS
OSI = "SPY   261120C00500000"
PUT = "SPY   261120P00500000"
DATASET = "chains-1:options"
#: Midnight beginning 2026-11-11 in New York (EST, UTC-5), in ns.
NOV_11_NY = int(dt.datetime(2026, 11, 11, 5, tzinfo=dt.UTC).timestamp()) * NS
NOV_12 = dt.date(2026, 11, 12)


def _builder(osi: str = OSI, subject: str = "INS-SPY", shares: int = 100) -> Any:
    """The plugin's `option_series` closure for one series."""

    def build(valid_from_ns: int, adjusted_on: dt.date | None) -> Any:
        return chains.option_series(
            subject, osi, template_id="TPL-listed-option", template_version="1",
            dataset=DATASET, currency="USD", exercise_style="EXERCISE_STYLE_AMERICAN",
            settlement_method="SETTLEMENT_METHOD_PHYSICAL",
            deliverable=[(subject, shares)], valid_from_ns=valid_from_ns,
            adjusted_on=adjusted_on,
        )  # fmt: skip

    return build


def _decide(
    times: SeriesTimes,
    *,
    osi: str = OSI,
    subject: str = "INS-SPY",
    shares: int = 100,
    now_ns: int = NOV_11_NY + 34 * 3600 * NS,
    today: dt.date = NOV_12,
    waiting: bool = False,
) -> Any:
    return times.series(
        _builder(osi, subject, shares), dataset=DATASET, osi=osi, subject=subject,
        now_ns=now_ns, today=today, waiting=waiting,
    )  # fmt: skip


class _Lake:
    """The plugin's `send_batch`: each batch kept, a refusal where `refuse`
    says one."""

    def __init__(self, refuse: Any = None) -> None:
        self.batches: list[list[str]] = []
        self.refuse = refuse

    async def __call__(self, batch: list[Any]) -> Any:
        keys = [row.meta.row_key for row in batch]
        self.batches.append(keys)
        if self.refuse is not None:
            self.refuse(keys)
        return ops.RecordSeriesResult(recorded=len(keys))


def _refused_at(osi: str, *, row: bool = True) -> Any:
    def refuse(keys: list[str]) -> None:
        if osi in keys:
            field = f"series[{keys.index(osi)}].meta.valid_from_ns" if row else "valid_from_ns"
            raise CallFailed(
                "RecordSeries", "invalid", "a row key fixes its valid time", fields=(field,)
            )

    return refuse


# ── series(): the per-series decision ────────────────────────────────────


async def test_a_series_first_seen_is_built_now_and_held_once_the_lake_has_it(
    tmp_path: Path,
) -> None:
    times = SeriesTimes(tmp_path / "series.json")
    now = NOV_11_NY + 34 * 3600 * NS
    row = _decide(times, now_ns=now)
    assert (row.meta.row_key, row.meta.valid_from_ns) == (OSI, now)
    assert not (tmp_path / "series.json").exists(), "staged until the lake has it"
    assert await times.record(_Lake(), [row], NOV_12) == 0
    held = json.loads((tmp_path / "series.json").read_text())["series"][DATASET][OSI]
    assert held["valid_from_ns"] == now and held["subject"] == "INS-SPY"
    assert held["adjusted_on"] == "" and len(held["terms"]) == 32


async def test_terms_as_held_are_sent_again_only_to_a_reader_waiting() -> None:
    times = SeriesTimes()
    first = NOV_11_NY + 34 * 3600 * NS
    await times.record(_Lake(), [_decide(times, now_ns=first)], NOV_12)
    later = first + 3 * DAY_NS
    assert _decide(times, now_ns=later) is None
    again = _decide(times, now_ns=later, waiting=True)
    assert (again.meta.row_key, again.meta.valid_from_ns) == (OSI, first)


async def test_changed_terms_are_an_adjustment_from_today() -> None:
    times = SeriesTimes()
    await times.record(_Lake(), [_decide(times)], NOV_12)
    adjusted = _decide(times, shares=150, today=dt.date(2026, 11, 13))
    assert adjusted.meta.row_key == f"{OSI}:2026-11-13:ADJ"
    assert adjusted.meta.valid_from_ns == NOV_11_NY + 2 * DAY_NS
    await times.record(_Lake(), [adjusted], dt.date(2026, 11, 13))
    # The adjusted terms as held: sent again to a reader waiting, under the
    # adjustment's key and time.
    assert _decide(times, shares=150, today=dt.date(2026, 11, 14)) is None
    again = _decide(times, shares=150, today=dt.date(2026, 11, 14), waiting=True)
    assert (again.meta.row_key, again.meta.valid_from_ns) == (
        f"{OSI}:2026-11-13:ADJ", NOV_11_NY + 2 * DAY_NS,
    )  # fmt: skip


async def test_another_first_subject_is_not_sent_and_counted() -> None:
    """The key's first subject is fixed (the-lake rule 5); the lake follows a
    replaced or merged record by alias, so skipping it loses nothing."""
    times = SeriesTimes()
    await times.record(_Lake(), [_decide(times)], NOV_12)
    assert _decide(times, subject="INS-SPY-MERGED") is None
    assert _decide(times, subject="INS-SPY-MERGED", waiting=True) is None
    assert times.other_subjects == 2
    assert _decide(times, waiting=True) is not None, "the first subject still answered"


def test_the_plugins_conversion_failure_passes_through() -> None:
    def build(valid_from_ns: int, adjusted_on: dt.date | None) -> Any:
        raise ValueError("not an OSI symbol")

    with pytest.raises(ValueError, match="not an OSI symbol"):
        SeriesTimes().series(
            build, dataset=DATASET, osi="?", subject="INS-SPY", now_ns=1, today=NOV_12,
            waiting=False,
        )  # fmt: skip


# ── record(): batches, refusals, the file ────────────────────────────────


async def test_rows_are_sent_in_the_lakes_batches_and_each_kept_as_it_lands(
    monkeypatch: Any, tmp_path: Path
) -> None:
    monkeypatch.setattr(option_chains, "BATCH", 1)
    times = SeriesTimes(tmp_path / "series.json")
    rows = [_decide(times), _decide(times, osi=PUT)]

    def second_fails(keys: list[str]) -> None:
        if keys == [PUT]:
            raise CallFailed("RecordSeries", "unavailable", "the lake is restarting")

    lake = _Lake(second_fails)
    with pytest.raises(CallFailed):
        await times.record(lake, rows, NOV_12)
    assert lake.batches == [[OSI], [PUT]]
    held = json.loads((tmp_path / "series.json").read_text())["series"][DATASET]
    assert set(held) == {OSI}, "the first batch kept, the second's staging discarded"
    assert _decide(times, osi=PUT) is not None, "first seen again"


async def test_a_full_batch_is_five_hundred() -> None:
    times = SeriesTimes()
    rows = [
        _decide(times, osi=chains.osi_symbol("SPY", dt.date(2026, 11, 20), "call", strike))
        for strike in range(1, 502)
    ]
    lake = _Lake()
    await times.record(lake, rows, NOV_12)
    assert [len(b) for b in lake.batches] == [500, 1]


async def test_a_refusal_of_an_own_keys_valid_time_is_taken_as_recorded(caplog: Any) -> None:
    """The plugin's storage lost: the lake holds the series under another
    first valid time and refuses the re-send naming it; taken as recorded,
    said once per series, the rest of the batch sent, and kept."""
    times = SeriesTimes()
    lake = _Lake(_refused_at(OSI))
    taken = await times.record(lake, [_decide(times), _decide(times, osi=PUT)], NOV_12)
    assert taken == 1 and lake.batches == [[OSI, PUT], [PUT]]
    assert _decide(times) is None, "kept: not sent again unasked"
    taken = await times.record(lake, [_decide(times, waiting=True)], NOV_12)
    assert taken == 1
    said = [r for r in caplog.records if "taken as recorded" in r.getMessage()]
    assert len(said) == 1, "said once per (dataset, OSI)"


async def test_a_refusal_naming_no_row_of_several_is_sent_one_by_one() -> None:
    times = SeriesTimes()
    lake = _Lake(_refused_at(OSI, row=False))
    taken = await times.record(lake, [_decide(times), _decide(times, osi=PUT)], NOV_12)
    assert taken == 1 and lake.batches == [[OSI, PUT], [OSI], [PUT]]


async def test_an_adjustments_refusal_and_any_other_are_raised_nothing_kept() -> None:
    times = SeriesTimes()
    await times.record(_Lake(), [_decide(times)], NOV_12)
    adjusted = _decide(times, shares=150)
    with pytest.raises(CallFailed):
        await times.record(_Lake(_refused_at(adjusted.meta.row_key)), [adjusted], NOV_12)
    assert _decide(times, shares=150).meta.row_key.endswith(":ADJ"), "staging discarded"

    def refuse(keys: list[str]) -> None:
        raise CallFailed("RecordSeries", "invalid", "no", fields=("series[0].template_id",))

    fresh = SeriesTimes()
    with pytest.raises(CallFailed):
        await fresh.record(_Lake(refuse), [_decide(fresh)], NOV_12)
    assert _decide(fresh) is not None, "first seen again"


async def test_expired_series_are_let_go_when_a_batch_lands(tmp_path: Path) -> None:
    times = SeriesTimes(tmp_path / "series.json")
    await times.record(_Lake(), [_decide(times)], NOV_12)
    after, december = dt.date(2026, 11, 21), "SPY   261218C00500000"
    await times.record(_Lake(), [_decide(times, osi=december, today=after)], after)
    held = json.loads((tmp_path / "series.json").read_text())["series"][DATASET]
    assert set(held) == {december}, "expired 2026-11-20, let go"


async def test_a_restart_keeps_every_series_valid_time(tmp_path: Path) -> None:
    path = tmp_path / "series.json"
    times = SeriesTimes(path)
    first = NOV_11_NY + 34 * 3600 * NS
    rows = [_decide(times, now_ns=first), _decide(times, osi=PUT, now_ns=first + 1)]
    await times.record(_Lake(), rows, NOV_12)
    restarted = SeriesTimes(path)
    later = first + DAY_NS
    assert _decide(restarted, now_ns=later) is None
    assert [
        _decide(restarted, osi=osi, now_ns=later, waiting=True).meta.valid_from_ns
        for osi in (OSI, PUT)
    ] == [first, first + 1]
    assert not path.with_name("series.json.tmp").exists(), "written beside, then put in place"


@pytest.mark.parametrize(
    "body",
    [
        "{not json",
        '{"series": []}',
        '{"series": {"chains-1:options": {"X": {"terms": "ab"}}}}',
        '{"series": {"chains-1:options": {"X": {"terms": 1, "valid_from_ns": 2}}}}',
        '{"series": {"d": {"X": {"terms": "a", "valid_from_ns": 2, "adjusted_on": "no"}}}}',
    ],
)
async def test_a_file_that_does_not_read_is_said_and_started_empty(
    tmp_path: Path, caplog: Any, body: str
) -> None:
    """The review of 0.36.2: a corrupt file never fails the plugin's start."""
    path = tmp_path / "series.json"
    path.write_text(body)
    times = SeriesTimes(path)
    assert any("did not read" in r.getMessage() for r in caplog.records)
    row = _decide(times)
    assert row is not None and row.meta.row_key == OSI, "first seen"
    await times.record(_Lake(), [row], NOV_12)
    assert set(json.loads(path.read_text())["series"][DATASET]) == {OSI}, "written over"


async def test_a_map_written_by_0362_loads_and_holds_the_first_subject_seen(
    tmp_path: Path,
) -> None:
    path = tmp_path / "series.json"
    times = SeriesTimes(path)
    first = NOV_11_NY + 34 * 3600 * NS
    await times.record(_Lake(), [_decide(times, now_ns=first)], NOV_12)
    body = json.loads(path.read_text())
    del body["series"][DATASET][OSI]["subject"]
    path.write_text(json.dumps(body))
    loaded = SeriesTimes(path)
    again = _decide(loaded, waiting=True)
    assert again.meta.valid_from_ns == first
    assert _decide(loaded, subject="INS-OTHER", waiting=True) is None


# ── option_chains.Feed, built on it ───────────────────────────────────────


class _Chain:
    def __init__(self) -> None:
        self.options = [option_chains.ChainOption(OSI, dt.date(2026, 11, 20))]

    def expirations(self, symbol: str) -> list[dt.date]:
        return [dt.date(2026, 11, 20)]

    def chain(self, symbol: str, expiration: dt.date) -> list[option_chains.ChainOption]:
        return self.options


def _want(want_id: str = "WNT-1", subject: str = "INS-SPY") -> Heard[Any]:
    return Heard(
        row="ObservationsWanted",
        message=ops.ObservationsWantedEvent(
            want_id=want_id, dataset=DATASET, data_type=option_chains.SERIES,
            subjects=[ops.SubjectRef(entity_id=subject)],
        ),
    )  # fmt: skip


def _feed(clock: list[int], source: Any = None, **more: Any) -> tuple[Any, Recorder]:
    recorder = Recorder("chains-1")

    async def symbol_of(subject: str) -> str:
        return "SPY"

    feed = recorder.bind(
        option_chains.Feed(
            source or _Chain(), symbol_of=symbol_of, clock_ns=lambda: clock[0], **more
        )
    )
    return feed, recorder


def _sent(recorder: Recorder) -> list[Any]:
    return [s for call in recorder.on("RecordSeries") for s in call.series]


async def test_the_feed_sends_no_series_under_another_first_subject() -> None:
    clock = [NOV_11_NY + 34 * 3600 * NS]
    feed, recorder = _feed(clock)
    await feed.on_observations_wanted(_want())
    await feed.on_observations_wanted(_want(subject="INS-SPY-MERGED"))
    assert [s.meta.subjects[0].entity_id for s in _sent(recorder)] == ["INS-SPY"]
    assert feed._first_times.other_subjects == 1
