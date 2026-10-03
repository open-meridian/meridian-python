"""What goes wrong, in terms a plugin author can act on.

Every one of these carries the sidecar's own words. A plugin author reading a
log line should be able to tell whether the fix is theirs, the operator's, or
nobody's, and a bare status does not say. Where a plugin must act on which
refusal it met, the class says so, chosen by the refusal's code
(spec/typed-sidecar-operations, section 7) and never by its words, which may
be reworded at any release.
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


class CommandRefused(CallFailed):
    """A component refused a command with a reason of its own, which the
    plugin acts on by its code (spec/typed-sidecar-operations, section 7;
    contract v8, the fields from v9).

    The book of record's refusals are these: `reason` is the
    `meridian.v1.RefusalReason` the sidecar carried beside the refusal --
    REFUSAL_REASON_OPENING_BALANCE_RECORDED for a second opening balance,
    REFUSAL_REASON_ACTOR_REQUIRED for a justified act sent for nobody,
    REFUSAL_REASON_BREAK_STATE for a break no longer open, and so on -- and
    `reason_name` its name. Match the code, never the words, which may be
    reworded at any release. A `CallFailed` whose `kind` is "refused", so a
    plugin catching that still does. Not retried: the same command meets the
    same refusal, and what to do is the plugin's -- re-read the book and say
    what stands, or ask the person for what was missing.

    `fields` names what was missing (contract v9): for
    REFUSAL_REASON_INCOMPLETE, the book's refusal of an entry lacking what tax
    tracking, valuation, confirmation or settlement need, each field the
    command left out by its path in the call's parameters --
    `positions[0].settled_quantity`, `positions[1].lots[0].terms.cost`,
    `adjustment.lines[0].opens_lot.acquired_date` -- so a plugin shows the
    person, per position, what to supply. Empty for every other refusal.
    From contract v10 they include an instrument whose record lacks its asset
    class or currency -- `positions[0].instrument.asset_class` -- which the
    deployment admin completes at the dashboard's Instruments page.

    `retryable` is true for REFUSAL_REASON_REFERENCE_UNAVAILABLE (contract
    v10): the book could not check the command because the instrument store
    did not answer, nothing was recorded, and the same command may be sent
    again. Every other refusal is not retried.
    """

    def __init__(
        self, topic: str, detail: str, reason: int, *, fields: tuple[str, ...] = ()
    ) -> None:
        super().__init__(topic, "refused", detail)
        self.reason = reason
        self.fields = fields
        from .v1 import sidecar_pb2

        self.retryable = reason == sidecar_pb2.REFUSAL_REASON_REFERENCE_UNAVAILABLE

        try:
            self.reason_name = sidecar_pb2.RefusalReason.Name(reason)
        except ValueError:
            self.reason_name = str(reason)


class NotLinked(CallFailed):
    """A row named an external account nobody has linked to one of the
    deployment's accounts (W6.4), so nothing was recorded for it.

    Raised by the refusal's code, REFUSAL_REASON_EXTERNAL_ACCOUNT_NOT_LINKED,
    never by its words, which a plugin should not match. A `CallFailed` whose
    `kind` is "refused", as this refusal always was, so a plugin that caught
    that still does. Not retried: the next statement after an admin of the plugin
    links the account records it, and which accounts are linked is on
    `Plugin.account_scope()`, in `AccountScope.links`.
    """

    def __init__(self, topic: str, detail: str) -> None:
        super().__init__(topic, "refused", detail)
