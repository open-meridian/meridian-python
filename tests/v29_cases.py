"""A plugin's side of every case contract v29 adds to the role suites, each
through the SDK's v29 helpers (`meridian.roles.debt`): an agency's factor
recorded under the pool's record (`debt.factor`, `RecordFactors`), and a
reader's pool's factor history read (`debt.read_factors`, `ListFactors`)
and each new month heard (`FactorsRecorded`).

`DATA` holds the data suite's, which tests/test_lake.py's toy plugin maps;
`PRODUCERS` every other role's, which tests/order_path_cases.py's map
carries for tests/test_v22.py to run in each suite holding it.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable

from meridian.plugin.v1 import operations_pb2 as ops
from meridian.roles import debt
from meridian.suites import Recorder

Producer = Callable[[Recorder], Awaitable[None]]

POOL = "INS-01JC29UMBS0000000000000001"


# ── The data suite ───────────────────────────────────────────────────────


async def records_a_pools_factor(recorder: Recorder) -> None:
    """The agency's factor for a pool the deployment holds, for its month,
    as published: under the pool's record, never minting one."""
    row = debt.factor(
        POOL, "0.84123456", "2026-10", dataset=f"{recorder.identity.instance_id}:factors",
        published="2026-11-04", record_date="2026-10-31", payment_date="2026-11-25",
        wac="6.512", wam=331, wala=27,
    )  # fmt: skip
    await recorder.record_factors(factors=[row])


DATA: dict[str, Producer] = {
    "records-a-pools-factor": records_a_pools_factor,
}


# ── The readers ──────────────────────────────────────────────────────────


async def reads_a_pools_factors(recorder: Recorder) -> None:
    await debt.read_factors(recorder, [POOL], "2025-11-01", "2026-11-30")


async def hears_a_factor_recorded(recorder: Recorder) -> None:
    recorder.answer(
        "FactorsRecorded",
        lambda _: ops.FactorsRecordedEvent(factor=ops.Factor(factor_month="202610")),
    )
    heard: list[str] = []

    async def kept(change: object) -> None:
        heard.append(change.message.factor.factor_month)

    await recorder.receive(factors_recorded=kept, subjects=[POOL])
    assert heard == ["202610"]


PRODUCERS: dict[str, Producer] = {
    "reads-a-pools-factors": reads_a_pools_factors,
    "hears-a-factor-recorded": hears_a_factor_recorded,
}
