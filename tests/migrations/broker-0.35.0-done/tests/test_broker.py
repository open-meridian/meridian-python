"""The broker's lake and book against the suites' recorder."""

import asyncio

from meridian.plugin.v1 import operations_pb2 as ops
from meridian.receive import Heard
from meridian.suites import Recorder

from broker.book import Book
from broker.lake import Lake


def test_a_want_for_a_subject_not_listed_is_declined() -> None:
    recorder = Recorder("broker-1")
    lake = recorder.bind(Lake())
    want = ops.ObservationsWantedEvent(
        want_id="WNT-1",
        dataset="broker-1:daily",
        subjects=[ops.SubjectRef(entity_id="INS-1")],
    )
    asyncio.run(lake.on_observations_wanted(Heard(row="ObservationsWanted", message=want)))
    (declined,) = recorder.on("DeclineWant")
    assert declined.want_id == "WNT-1"


def test_the_book_reports_the_account_the_broker_reaches() -> None:
    recorder = Recorder("broker-1")
    asyncio.run(recorder.bind(Book()).on_start())
    (reported,) = recorder.on("ReportExternalAccounts")
    assert reported.accounts[0].external_account_id == "BRK-1"
