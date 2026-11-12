"""A plugin's side of every case contract 30 adds to the role suites, each
through the SDK: a standing figure held (`analytics.Jobs.standing`: `RunJob`
naming the job standing, its `DerivedSeriesUpdated` heard into a `LiveView`),
in the reporting, portfolio, compliance and signal suites; and the source
priorities read (`list_source_priorities`, the operation's own name, 454) by
the eight roles that read the lake.

`PRODUCERS` holds both, which tests/order_path_cases.py's map carries for
tests/test_v22.py to run in each suite holding them.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from decimal import Decimal

from meridian import analytics
from meridian.operations import _decimal
from meridian.plugin.v1 import operations_pb2 as ops
from meridian.suites import Recorder

Producer = Callable[[Recorder], Awaitable[None]]

JOB = "JOB-01JC30STANDING000000000001"
ACCOUNT = "ACC-01JC30STANDING00000000001"


def figure(value: str) -> ops.Figure:
    return ops.Figure(
        measure=ops.MeasureRef(definition="exposure", version=1),
        account_id=ACCOUNT,
        value=_decimal(Decimal(value), "value"),
    )


async def holds_a_standing_figure(recorder: Recorder) -> None:
    """An exposure kept current: registered standing, each measure naming
    its refresh, and its update heard into the view."""
    recorder.answer("RunJob", lambda _: ops.RunJobResult(answered_inline=True, job_id=JOB))
    recorder.answer(
        "ReadJobAnswer", lambda _: ops.ReadJobAnswerResult(job_id=JOB, figures=[figure("100")])
    )
    recorder.answer(
        "DerivedSeriesUpdated",
        lambda _: ops.DerivedSeriesUpdatedEvent(
            job_id=JOB, figures=[figure("125")], sequence=1
        ),
    )
    job = analytics.job(
        analytics.measure("exposure", refresh="per_change"), accounts=[ACCOUNT], standing=True
    )
    view = await analytics.Jobs().standing(recorder, job)
    try:
        (held,) = view.rows().values()
        assert held.value == _decimal(Decimal("125"), "value"), held
    finally:
        await view.close()


async def reads_the_source_priorities(recorder: Recorder) -> None:
    """Which source a default read takes for a data type, and which next,
    as answered to the plugin: within its entitlements (454), never assumed
    to be every priority the deployment set."""
    recorder.answer(
        "ListSourcePriorities",
        lambda _: ops.ListSourcePrioritiesResult(
            priorities=[
                ops.SourcePriority(
                    data_type="meridian.v1.Quote", datasets=["truefx-1:live", "oanda-1:quotes"]
                )
            ]
        ),
    )
    read = await recorder.list_source_priorities()
    assert {p.data_type: list(p.datasets) for p in read.priorities} == {
        "meridian.v1.Quote": ["truefx-1:live", "oanda-1:quotes"]
    }


PRODUCERS: dict[str, Producer] = {
    "holds-a-standing-figure": holds_a_standing_figure,
    "reads-the-source-priorities": reads_the_source_priorities,
}
