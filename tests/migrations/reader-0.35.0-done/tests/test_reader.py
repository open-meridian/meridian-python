"""The reader's reads against the suites' recorder."""

import asyncio

from meridian.suites import Recorder

from reader.report import Report


def test_the_closes_are_read_for_the_subjects_held() -> None:
    recorder = Recorder("reader-1")
    report = recorder.bind(Report(["INS-1"]))
    assert asyncio.run(report.closes(["INS-1"], "2026-10-30")) == 0
    (asked,) = recorder.on("ListPrices")
    assert [each.entity_id for each in asked.subjects] == ["INS-1"]
    assert report.subjects() == ["INS-1"]
