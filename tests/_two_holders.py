"""One of two pods holding the same shard at once, as a deposed holder still
writing through a takeover's lapse and the shard's new holder do (PO item
79): run as its own process by test_step_3d_shard_storage, each with its own
fake sidecar answering it shard 0 of 2, on the one shared storage
(MERIDIAN_STORAGE_DIR) and archive (MERIDIAN_ARCHIVE_DIR).

    python _two_holders.py lines <go-file> <name> <count>
    python _two_holders.py archive <go-file> <unit> [<unit> ...]

Each waits for <go-file>, so both write at once, then prints, as JSON, the
keys it was given (`lines`) or the units it archived (`archive`). Its
sidecar takes a moment to record a move, as a real one does, so each
pod's moves overlap the other's."""

from __future__ import annotations

import asyncio
import json
import sys
import time
from pathlib import Path
from typing import Any

import grpc

from conftest import FakeSidecar
from meridian.edge import RawStore, storage_root
from meridian.plugin.v1 import operations_pb2_grpc
from meridian.v1 import sidecar_pb2_grpc
from test_step_3d_shard_storage import AT, FIRST, LAST, _pod


def _wait(go: Path) -> None:
    ends = time.monotonic() + 30
    while not go.exists():
        if time.monotonic() > ends:
            raise TimeoutError(f"{go} never came")
        time.sleep(0.001)


class _Slow(FakeSidecar):
    async def RecordMove(self, request: Any, context: Any) -> Any:  # noqa: N802
        await asyncio.sleep(0.02)
        return await super().RecordMove(request, context)


async def main(mode: str, go: Path, args: list[str]) -> list[str]:
    service = _Slow()
    server = grpc.aio.server()
    sidecar_pb2_grpc.add_SidecarServiceServicer_to_server(service, server)
    operations_pb2_grpc.add_PluginOperationsServicer_to_server(service.operations, server)
    port = server.add_insecure_port("127.0.0.1:0")
    await server.start()
    try:
        plugin = await _pod(service, f"127.0.0.1:{port}", shard=0, shards=2)
        try:
            _wait(go)
            if mode == "lines":
                name, count = args[0], int(args[1])
                store = RawStore(storage_root(), kind="responses")
                return [
                    store.keep_line(
                        "ticker", "BTC-USD", {"received_at_ns": AT + n, "body": f"{name} {n}"}
                    )
                    for n in range(count)
                ]
            for unit in args:
                await plugin.archive_unit(
                    "activity",
                    unit,
                    record_count=1,
                    first_received_ns=FIRST,
                    last_received_ns=LAST,
                )
            return args
        finally:
            await plugin.leave()
    finally:
        await server.stop(grace=None)


if __name__ == "__main__":
    print(json.dumps(asyncio.run(main(sys.argv[1], Path(sys.argv[2]), sys.argv[3:]))))
