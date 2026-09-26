"""What goes wrong, in terms a plugin author can act on.

Every one of these carries the sidecar's own words rather than a code. A plugin
author reading a log line should be able to tell whether the fix is theirs, the
operator's, or nobody's, and a bare status does not say.
"""

from __future__ import annotations


class MeridianError(Exception):
    """Base for everything this package raises."""


class Refused(MeridianError):
    """Registration was refused.

    Not retried. A refusal is a statement about configuration -- access control
    has not loaded, the role carries no grants, the schema does not match -- and
    none of those resolve by asking again. The plugin stops and the operator
    reads why.
    """

    def __init__(self, reason: str) -> None:
        super().__init__(reason or "refused without a reason")
        self.reason = reason


class NoSidecar(MeridianError):
    """No sidecar answered in time.

    Distinct from `Refused`: a sidecar that refused is running and has said
    why, and asking again changes nothing; one that never answered may still
    be starting, or may not be there at all, and the address is worth
    checking. `connect` has already waited for it.
    """

    def __init__(self, address: str, waited_seconds: float) -> None:
        super().__init__(f"no sidecar answered at {address} within {waited_seconds:g} seconds")
        self.address = address
        self.waited_seconds = waited_seconds


class NotRegistered(MeridianError):
    """An operation was attempted before registering, or after leaving."""


class NotGranted(MeridianError):
    """A publish or subscribe the deployment did not grant.

    Carries the topic as well as the sidecar's reason, because the reason names
    the missing grant and the topic names what wanted it, and a plugin author
    debugging this needs both.
    """

    def __init__(self, topic: str, reason: str) -> None:
        super().__init__(f"{topic}: {reason}")
        self.topic = topic
        self.reason = reason


class CallFailed(MeridianError):
    """A call did not produce an answer.

    `kind` distinguishes a timeout from a refusal from a handler that answered
    with an error, because the caller's next move differs for each: retry, stop,
    or report. Collapsing them into one exception is how a plugin ends up
    retrying something that will never succeed.
    """

    def __init__(self, topic: str, kind: str, detail: str) -> None:
        super().__init__(f"{topic}: {kind}{f': {detail}' if detail else ''}")
        self.topic = topic
        self.kind = kind
        self.detail = detail
