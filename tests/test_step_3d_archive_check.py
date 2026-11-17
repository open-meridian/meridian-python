"""Step 3d, from the plugin's side: the archive's bucket asked at start
(PO items 60 to 62).

A cloud's workload identity trusts an account by its name, and an instance
of several pods runs under an account of its own, which a deployment's
administrator must trust for the archive's bucket. Before it registers, a
plugin given a bucket asks it once, under its instance's prefix, for at most
one key. A refusal on auth holds the plugin unregistered -- not Ready, and
never exiting into the kubelet's back-off -- said, and asked again on an
interval, so a trust added later is found without a restart. Anything else
the bucket answers, or a bucket that answers, and the plugin goes on as
before.
"""

from __future__ import annotations

import asyncio
import contextlib
import logging
import sys
import types
from collections.abc import Callable
from typing import Any

import grpc
import pytest

import meridian
import meridian._run as running
import meridian.client as client
import meridian.edge as edge
from conftest import FakeSidecar
from meridian.plugin.v1 import operations_pb2_grpc
from meridian.roles import custody
from meridian.v1 import sidecar_pb2_grpc

_REFUSAL = (
    "the archive's bucket refuses this instance's account: its workload identity must trust "
    "that account (pluginArchive in values.yaml)"
)


# ── What boto3 answers, by shape (botocore is not installed here) ───────────


class ClientError(Exception):
    """botocore's: a service's answer, its code and HTTP status in
    `response`."""

    def __init__(self, status: int, code: str, operation: str = "ListObjectsV2") -> None:
        self.response = {
            "Error": {"Code": code, "Message": f"{code} (test)"},
            "ResponseMetadata": {"HTTPStatusCode": status},
        }
        super().__init__(f"An error occurred ({code}) when calling the {operation} operation")


class NoCredentialsError(Exception):
    """botocore's, where the pod holds no credential at all: an account no
    identity is associated with."""


class EndpointConnectionError(ConnectionError):
    """botocore's, where the bucket's endpoint is not reached."""


class ReadTimeoutError(Exception):
    """botocore's, where the endpoint did not answer in time."""


class _Bucket:
    """boto3's S3 client, answering each list with the next of `answers`
    (the last for every ask after): None for a page, or an exception."""

    def __init__(self, answers: list[Exception | None]) -> None:
        self.answers = answers
        self.asked: list[dict[str, Any]] = []

    def list_objects_v2(self, **asked: Any) -> dict[str, Any]:
        self.asked.append(asked)
        answer = self.answers[min(len(self.asked), len(self.answers)) - 1]
        if answer is not None:
            raise answer
        return {"Contents": [], "KeyCount": 0}


def _given(monkeypatch: pytest.MonkeyPatch, bucket: _Bucket) -> list[str]:
    """`bucket` as boto3's client for the instance's archive, and the
    clients made, one name each."""
    made: list[str] = []

    def made_client(name: str) -> _Bucket:
        made.append(name)
        return bucket

    monkeypatch.setitem(sys.modules, "boto3", types.SimpleNamespace(client=made_client))
    monkeypatch.setenv("MERIDIAN_ARCHIVE_BUCKET", "s3://firm-archive/meridian/custody-1")
    monkeypatch.delenv("MERIDIAN_ARCHIVE_DIR", raising=False)
    return made


class _Session(custody.Role):
    def __init__(self) -> None:
        self.started = 0
        self.running = asyncio.Event()

    async def on_start(self) -> None:
        self.started += 1

    async def run(self) -> None:
        self.running.set()
        await asyncio.Event().wait()


async def _until(check: Callable[[], bool], timeout: float = 5.0) -> None:
    for _ in range(int(timeout / 0.01)):
        if check():
            return
        await asyncio.sleep(0.01)
    assert check(), "not reached in time"


def _refusals(caplog: pytest.LogCaptureFixture) -> list[logging.LogRecord]:
    return [r for r in caplog.records if r.getMessage() == _REFUSAL]


async def _ended(task: asyncio.Task[None]) -> None:
    task.cancel()
    with contextlib.suppress(asyncio.CancelledError):
        await task


@pytest.fixture
def quick(monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture) -> None:
    monkeypatch.setattr(running, "_ARCHIVE_CHECK_SECONDS", 0.05)
    caplog.set_level(logging.INFO, logger="meridian")


# ── The check before Register ───────────────────────────────────────────────


@pytest.mark.parametrize(
    "refusal",
    [
        ClientError(403, "AccessDenied"),
        ClientError(401, "Unauthorized"),
        # IRSA: the role's trust names another account, so the web identity
        # is not exchanged for a credential (STS answers before S3 is asked).
        ClientError(403, "AccessDenied", "AssumeRoleWithWebIdentity"),
        ClientError(400, "InvalidIdentityToken", "AssumeRoleWithWebIdentity"),
        # EKS Pod Identity: no association for the account, so no credential.
        NoCredentialsError("Unable to locate credentials"),
    ],
    ids=["403", "401", "sts-403", "sts-invalid-identity", "no-credential"],
)
async def test_a_bucket_refusing_the_account_holds_register_says_why_and_never_exits(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
    quick: None,
    sidecar: tuple[FakeSidecar, str],
    refusal: Exception,
) -> None:
    """Refused on auth: the plugin registers nothing and starts nothing,
    says the approved refusal, and keeps asking -- `run_async` neither
    raises nor ends."""
    service, address = sidecar
    service.roles = ("custody",)
    monkeypatch.setenv("MERIDIAN_SIDECAR_ADDRESS", address)
    bucket = _Bucket([refusal])
    _given(monkeypatch, bucket)
    session = _Session()
    task = asyncio.create_task(meridian.run_async(meridian.Declaration(), [session]))
    try:
        await _until(lambda: len(_refusals(caplog)) >= 3 or task.done())
        assert not task.done(), task.exception()
        assert service.registered == [] and session.started == 0
        assert _refusals(caplog)[0].levelno == logging.ERROR
        assert len(bucket.asked) >= 3
    finally:
        await _ended(task)
    # Least privilege, under the instance's own prefix: one key at most.
    assert bucket.asked[0] == {
        "Bucket": "firm-archive",
        "Prefix": "meridian/custody-1/",
        "MaxKeys": 1,
    }


async def test_trust_added_later_is_found_on_the_next_check_and_the_plugin_registers(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
    quick: None,
    sidecar: tuple[FakeSidecar, str],
) -> None:
    """The administrator trusts the account while the plugin waits: the
    next ask answers, and the plugin registers and starts, with no restart.
    Each ask is made with a client made afresh, so no credential refused
    earlier is kept."""
    service, address = sidecar
    service.roles = ("custody",)
    monkeypatch.setenv("MERIDIAN_SIDECAR_ADDRESS", address)
    refused = ClientError(403, "AccessDenied")
    bucket = _Bucket([refused, refused, None])
    made = _given(monkeypatch, bucket)
    session = _Session()
    task = asyncio.create_task(meridian.run_async(meridian.Declaration(), [session]))
    try:
        await asyncio.wait_for(session.running.wait(), timeout=5)
        assert len(service.registered) == 1 and session.started == 1
        assert len(_refusals(caplog)) == 2 and len(bucket.asked) == 3
        assert made == ["s3", "s3", "s3"]
    finally:
        await _ended(task)


async def test_a_bucket_that_answers_is_asked_once_and_the_plugin_registers_as_before(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
    quick: None,
    sidecar: tuple[FakeSidecar, str],
) -> None:
    service, address = sidecar
    service.roles = ("custody",)
    monkeypatch.setenv("MERIDIAN_SIDECAR_ADDRESS", address)
    bucket = _Bucket([None])
    _given(monkeypatch, bucket)
    session = _Session()
    task = asyncio.create_task(meridian.run_async(meridian.Declaration(), [session]))
    try:
        await asyncio.wait_for(session.running.wait(), timeout=5)
        assert len(service.registered) == 1 and len(bucket.asked) == 1
        assert not _refusals(caplog)
    finally:
        await _ended(task)


@pytest.mark.parametrize(
    "failure",
    [
        EndpointConnectionError("Could not connect to the endpoint URL"),
        ReadTimeoutError("Read timeout on endpoint URL"),
        ClientError(500, "InternalError"),
        ClientError(503, "SlowDown"),
        OSError("network is unreachable"),
    ],
    ids=["no-endpoint", "read-timeout", "500", "503", "os-error"],
)
async def test_a_bucket_not_reached_is_not_an_auth_refusal_and_the_plugin_goes_on(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
    quick: None,
    sidecar: tuple[FakeSidecar, str],
    failure: Exception,
) -> None:
    """A network fault or a 5xx says nothing of the account: the plugin
    registers as it does with no check, and the refusal is never said."""
    service, address = sidecar
    service.roles = ("custody",)
    monkeypatch.setenv("MERIDIAN_SIDECAR_ADDRESS", address)
    bucket = _Bucket([failure])
    _given(monkeypatch, bucket)
    session = _Session()
    task = asyncio.create_task(meridian.run_async(meridian.Declaration(), [session]))
    try:
        await asyncio.wait_for(session.running.wait(), timeout=5)
        assert len(service.registered) == 1 and len(bucket.asked) == 1
        assert not _refusals(caplog)
        assert not any("refuses" in r.getMessage() for r in caplog.records)
    finally:
        await _ended(task)


async def test_a_bucket_that_does_not_answer_in_time_is_not_waited_for(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
    quick: None,
    sidecar: tuple[FakeSidecar, str],
) -> None:
    """An ask that hangs is a network fault: past its bound the plugin goes
    on, as it does with no check."""
    import threading

    service, address = sidecar
    service.roles = ("custody",)
    monkeypatch.setenv("MERIDIAN_SIDECAR_ADDRESS", address)
    monkeypatch.setattr(running, "_ARCHIVE_ASK_SECONDS", 0.1)
    release = threading.Event()

    class Hanging(_Bucket):
        def list_objects_v2(self, **asked: Any) -> dict[str, Any]:
            self.asked.append(asked)
            release.wait(5)
            return {}

    bucket = Hanging([None])
    _given(monkeypatch, bucket)
    session = _Session()
    task = asyncio.create_task(meridian.run_async(meridian.Declaration(), [session]))
    try:
        await asyncio.wait_for(session.running.wait(), timeout=5)
        assert len(service.registered) == 1 and not _refusals(caplog)
    finally:
        release.set()
        await _ended(task)


@pytest.mark.parametrize("given", ["none", "directory"])
async def test_no_bucket_no_check(
    monkeypatch: pytest.MonkeyPatch,
    quick: None,
    sidecar: tuple[FakeSidecar, str],
    given: str,
    tmp_path: Any,
) -> None:
    """With no archive, or one mounted as a directory, nothing is asked and
    no client made: the plugin registers as before."""
    service, address = sidecar
    service.roles = ("custody",)
    monkeypatch.setenv("MERIDIAN_SIDECAR_ADDRESS", address)
    bucket = _Bucket([ClientError(403, "AccessDenied")])
    made = _given(monkeypatch, bucket)
    if given == "none":
        monkeypatch.delenv("MERIDIAN_ARCHIVE_BUCKET")
    else:
        monkeypatch.setenv("MERIDIAN_ARCHIVE_DIR", str(tmp_path))
    session = _Session()
    task = asyncio.create_task(meridian.run_async(meridian.Declaration(), [session]))
    try:
        await asyncio.wait_for(session.running.wait(), timeout=5)
        assert len(service.registered) == 1
        assert made == [] and bucket.asked == []
    finally:
        await _ended(task)


async def test_a_stop_while_refused_ends_the_wait(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    """Held by a refusal, the process still stops when told to, without
    waiting out the interval."""
    monkeypatch.setattr(running, "_ARCHIVE_CHECK_SECONDS", 30.0)
    caplog.set_level(logging.INFO, logger="meridian")
    _given(monkeypatch, _Bucket([ClientError(403, "AccessDenied")]))
    stopped = asyncio.Event()
    waiting = asyncio.create_task(running._archive_trusted(stopped))
    await _until(lambda: bool(_refusals(caplog)))
    assert not waiting.done()
    stopped.set()
    assert await asyncio.wait_for(waiting, timeout=2) is False


# ── After a sidecar lost: asked again before registering again ─────────────


def _free_port() -> int:
    import socket

    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        return int(probe.getsockname()[1])


async def _serving(service: FakeSidecar, port: int) -> grpc.aio.Server:
    server = grpc.aio.server()
    sidecar_pb2_grpc.add_SidecarServiceServicer_to_server(service, server)
    operations_pb2_grpc.add_PluginOperationsServicer_to_server(service.operations, server)
    assert server.add_insecure_port(f"127.0.0.1:{port}") == port
    await server.start()
    return server


class _Serving(FakeSidecar):
    """One serving of the sidecar: as core's, it answers a heartbeat before
    any Register with FAILED_PRECONDITION."""

    async def Heartbeat(self, request, context):  # noqa: N802
        if not self.registered:
            await context.abort(
                grpc.StatusCode.FAILED_PRECONDITION,
                "not registered: call Register before any other operation",
            )
        return await super().Heartbeat(request, context)


async def test_each_register_is_asked_for_again_after_a_sidecar_lost(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture, quick: None
) -> None:
    """The plugin waiting for its sidecar again (PO item 50) registers
    again only once the bucket answers again: a trust withdrawn meanwhile
    holds it as at its first start."""
    port = _free_port()
    monkeypatch.setenv("MERIDIAN_SIDECAR_ADDRESS", f"127.0.0.1:{port}")
    monkeypatch.setattr(client, "HEARTBEAT_SECONDS", 0.05)
    monkeypatch.setattr(running, "_ATTEMPT_SECONDS", 0.2)
    monkeypatch.setattr(running, "_ATTEMPT_PAUSE_SECONDS", 0.05)
    bucket = _Bucket([None, ClientError(403, "AccessDenied")])
    _given(monkeypatch, bucket)
    first = _Serving()
    first.roles = ("custody",)
    server = await _serving(first, port)
    session = _Session()
    task = asyncio.create_task(meridian.run_async(meridian.Declaration(), [session]))
    try:
        await asyncio.wait_for(session.running.wait(), timeout=5)
        session.running.clear()
        await server.stop(grace=None)
        second = _Serving()
        second.roles = ("custody",)
        server = await _serving(second, port)
        await _until(lambda: len(_refusals(caplog)) >= 2 or task.done(), timeout=10)
        assert not task.done(), task.exception()
        assert second.registered == [] and session.started == 1
    finally:
        task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await task
        await server.stop(grace=None)


# ── What counts as a refusal on auth ────────────────────────────────────────


@pytest.mark.parametrize(
    ("answer", "refused"),
    [
        (ClientError(403, "AccessDenied"), True),
        (ClientError(401, "Unauthorized"), True),
        (ClientError(403, "AllAccessDisabled"), True),
        (ClientError(400, "InvalidIdentityToken", "AssumeRoleWithWebIdentity"), True),
        (NoCredentialsError("Unable to locate credentials"), True),
        (ClientError(500, "InternalError"), False),
        (ClientError(503, "SlowDown"), False),
        (ClientError(404, "NoSuchBucket"), False),
        (EndpointConnectionError("Could not connect"), False),
        (ReadTimeoutError("Read timeout"), False),
        (OSError("unreachable"), False),
        (RuntimeError("boto3 is not installed"), False),
    ],
)
def test_what_is_a_refusal_on_auth(answer: Exception, refused: bool) -> None:
    assert edge._refused_on_auth(answer) is refused
