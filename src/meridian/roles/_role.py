"""What every role's generated base is built on (SDK 0.35;
spec/each-role-is-one-generated-class, rulings 1004, 1005 and 1009 to 1023).

A plugin writes one class per role it holds, extending that role's base,
`meridian.roles.<role>.Role`, which design's generator writes from the
matrix and the suites into `meridian/roles/_generated/<role>.py`. The base
holds the role's acts, bound by name from the one implementation in
`meridian.operations`, and its events as `on_<row>` methods, the ones its
suite requires abstract. This module holds what is not the contract's to
generate:

- `plugin`, the connection the class was registered on (`meridian.run`,
  `meridian.connect(roles=[...])` or the suites' `Recorder.bind`), through
  which the class reaches every plugin-wide item -- its identity, settings,
  health, storage, raw records, tickets and views;
- the lifecycle: `on_start()`, called once the plugin has registered;
  `run()`, its long-running work, started after every class's `on_start`,
  restarted after a backoff when it fails and cancelled at stop; and
  `on_stop()` (ruling 1012);
- hearing: `seed`, whether the SDK hands the class what the store holds on
  start; `subjects()`, the lake's subjects it hears, read at start; and
  `hear_again()`, which reopens the one stream when they change, catching
  up as after a broken stream (ruling 1013);
- which events it hears: the required ones, and each optional one a class
  overrides (ruling 1011), so a row no registered class implements is never
  asked of the sidecar.

A class missing one of its role's required events is refused when it is
made, naming the role and each event: implement it, or register the SDK's
common logic for the role (`connectivity.Trader`, `pricing.Pricer`, a data
feed), which implements it.
"""

from __future__ import annotations

from abc import ABC
from collections.abc import Awaitable, Callable, Mapping, Sequence
from typing import TYPE_CHECKING, Any, ClassVar, TypeVar

from ..errors import NotRegistered

if TYPE_CHECKING:
    from ..client import Plugin

_Answer = TypeVar("_Answer")


class RoleBase(ABC):  # noqa: B024 - abstract through each role's required events
    """The part of every role's base that is not generated (see the module)."""

    #: The role's name, as matrix/roles.tsv names it (generated).
    role: ClassVar[str] = ""
    #: Each event the role hears, by its row, and the method it is handed to
    #: (generated).
    EVENTS: ClassVar[Mapping[str, str]] = {}
    #: The events the role's suite requires (generated).
    REQUIRED: ClassVar[frozenset[str]] = frozenset()
    #: The role's acts, by method (generated).
    ACTS: ClassVar[tuple[str, ...]] = ()

    #: Whether the SDK hands this class what the store holds of each row it
    #: hears when the plugin starts, marked `caught_up`. A class whose own
    #: `on_start` reads the store sets it False (connectivity's `Trader`).
    seed: bool = True

    # Set on registration; kept apart from any attribute a plugin's own class
    # names `plugin` or `_plugin`.
    _role_plugin: Any = None
    _role_hear_again: Callable[[], None] | None = None

    def __new__(cls, *args: Any, **kwargs: Any) -> RoleBase:
        missing = sorted(getattr(cls, "__abstractmethods__", ()))
        if missing:
            events = set(cls.EVENTS.values())
            named = [name for name in missing if name in events]
            other = [name for name in missing if name not in events]
            said = []
            if named:
                many = len(named) > 1
                said.append(
                    f"the {cls.role} role's required event{'s' if many else ''} "
                    f"{', '.join(named)} (its suite requires {'them' if many else 'it'})"
                )
            if other:
                said.append(
                    f"the abstract method{'s' if len(other) > 1 else ''} {', '.join(other)}"
                )
            raise TypeError(
                f"{cls.__name__} is a {cls.role} role class missing {' and '.join(said)}: "
                f"implement each, or register the SDK's common logic for the {cls.role} role"
            )
        return super().__new__(cls)

    # ── The connection ────────────────────────────────────────────────────

    @property
    def plugin(self) -> Plugin:
        """The connection this class was registered on: every plugin-wide
        item is reached through it, never through a role class."""
        if self._role_plugin is None:
            raise NotRegistered(
                f"{type(self).__name__} is not registered: give it to "
                "meridian.run(roles=[...]) or meridian.connect(roles=[...]), or bind it to "
                "the suites' Recorder"
            )
        held: Plugin = self._role_plugin
        return held

    def _bind(self, plugin: Any, hear_again: Callable[[], None] | None = None) -> None:
        self._role_plugin = plugin
        self._role_hear_again = hear_again

    async def _operate(
        self, method: Callable[[Any], Awaitable[_Answer]], params: Any
    ) -> _Answer:
        answer: _Answer = await self.plugin._operate(method, params)
        return answer

    def _operations(self) -> Any:
        return self.plugin._operations()

    # ── The lifecycle ─────────────────────────────────────────────────────

    async def on_start(self) -> None:  # noqa: B027 - optional by design
        """Once the plugin has registered and, where `meridian.run` is given
        `on_settings`, applied its first settings, before the stream opens:
        read what the class needs to start."""

    async def run(self) -> None:  # noqa: B027 - optional by design
        """The class's long-running work -- a poll, a stream -- started after
        every class's `on_start`. One that raises is logged, said on the
        plugin's health and started again after a backoff; it is cancelled
        when the plugin stops. Returning ends it."""

    async def on_stop(self) -> None:  # noqa: B027 - optional by design
        """When the plugin stops, after its `run` is cancelled."""

    # ── Hearing ───────────────────────────────────────────────────────────

    def subjects(self) -> Sequence[str]:
        """The subjects, by entity ID, whose lake rows this class hears:
        read when the stream opens, and again after `hear_again()`."""
        return ()

    def hear_again(self) -> None:
        """Reopen the plugin's one stream, its subjects read again, catching
        up as after a broken stream: call it when `subjects()` changes."""
        if self._role_hear_again is not None:
            self._role_hear_again()

    @classmethod
    def heard_rows(cls) -> tuple[str, ...]:
        """The rows this class hears: its role's required events, and each
        optional one it, or the SDK's common logic beneath it, overrides."""
        base = next(
            (held for held in cls.__mro__ if "EVENTS" in vars(held) and held is not RoleBase),
            None,
        )
        if base is None:
            return ()
        heard = []
        for row, method in cls.EVENTS.items():
            if row in cls.REQUIRED:
                heard.append(row)
                continue
            for held in cls.__mro__:
                if held is base:
                    break
                if method in vars(held):
                    heard.append(row)
                    break
        return tuple(heard)
