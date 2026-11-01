"""A plugin's process: its role classes registered on one connection and run
(SDK 0.35; spec/each-role-is-one-generated-class, rulings 1005 and 1009 to
1015).

    meridian.run(
        declaration=DECLARATION,
        roles=[Lake(state), Trading(state)],
        pages=pages,
        port=PORT,
        on_settings=state.configure,
        figures=state.figures,
    )

`run` handles SIGTERM and SIGINT, connects (`meridian.connect`, the
declaration registered and the classes whose roles the instance holds
registered on it), and then:

1. delivers the settings to `on_settings`, now and on every change, each an
   instance of the declaration's `@meridian.settings` class where it has
   one;
2. calls each class's `on_start()`, in the order given;
3. opens the one stream for the union of the rows the classes hear --
   each role's required events and the optional ones a class overrides --
   seeding a row for the classes whose `seed` is true, naming the union of
   their `subjects()`, and handing each delivery to every class hearing
   its row, in order; a class's `hear_again()` opens it again;
4. starts each class's `run()`, restarted after a backoff
   (`meridian.helpers.sessions.Backoff`) when it raises, the failure logged
   and said on the plugin's health;
5. serves `pages` on `port`, sets the figures `figures()` answers on every
   heartbeat, and reports the plugin healthy, "started";

and, when it is stopped, cancels the `run()`s and the stream, calls each
class's `on_stop()` and leaves. `run_async` is the same as a coroutine.
"""

from __future__ import annotations

import asyncio
import contextlib
import logging
import signal
from collections.abc import Awaitable, Callable, Sequence
from typing import TYPE_CHECKING, Any

from .helpers.sessions import Backoff

if TYPE_CHECKING:
    from .client import Plugin
    from .declaration import Declaration
    from .figures import Figure
    from .pages import Pages
    from .receive import Heard
    from .roles._role import RoleBase

__all__ = ["run", "run_async"]

log = logging.getLogger("meridian.run")

#: How often the figures `figures()` answers are set: each heartbeat's.
FIGURES_SECONDS = 10.0


def run(
    declaration: Declaration,
    roles: Sequence[RoleBase],
    *,
    pages: Pages | None = None,
    port: int | None = None,
    on_settings: Callable[[Any], Awaitable[None] | None] | None = None,
    figures: Callable[[], Sequence[Figure]] | None = None,
) -> None:
    """The plugin's process, until it is stopped (see the module)."""
    asyncio.run(
        run_async(
            declaration,
            roles,
            pages=pages,
            port=port,
            on_settings=on_settings,
            figures=figures,
        )
    )


async def run_async(
    declaration: Declaration,
    roles: Sequence[RoleBase],
    *,
    pages: Pages | None = None,
    port: int | None = None,
    on_settings: Callable[[Any], Awaitable[None] | None] | None = None,
    figures: Callable[[], Sequence[Figure]] | None = None,
) -> None:
    """`run`, as a coroutine: until it is cancelled, or the process is sent
    SIGTERM or SIGINT."""
    from .client import connect

    # Before anything else: a stop that arrives while connecting is still a
    # stop, and without these the default handler kills the process before
    # it has left its sidecar cleanly.
    stopped = asyncio.Event()
    loop = asyncio.get_running_loop()
    handled: list[signal.Signals] = []
    for stop in (signal.SIGTERM, signal.SIGINT):
        with contextlib.suppress(NotImplementedError, RuntimeError, ValueError):
            loop.add_signal_handler(stop, stopped.set)
            handled.append(stop)
    try:
        async with await connect(declaration=declaration, roles=roles) as plugin:
            log.info(
                "registered as %s, roles %s",
                plugin.identity.instance_id,
                ", ".join(plugin.identity.roles) or "none",
            )
            await _Running(
                plugin,
                declaration,
                pages=pages,
                port=port,
                on_settings=on_settings,
                figures=figures,
            ).until(stopped)
    finally:
        for stop in handled:
            with contextlib.suppress(Exception):
                loop.remove_signal_handler(stop)


class _Hearing:
    """The one stream the registered classes hear through (requirement 7)."""

    def __init__(self, plugin: Plugin, roles: Sequence[RoleBase]) -> None:
        self.plugin = plugin
        self.roles = roles
        self.reopen = asyncio.Event()
        self.hearers: dict[str, list[tuple[RoleBase, str]]] = {}
        for role in roles:
            for row in type(role).heard_rows():
                self.hearers.setdefault(row, []).append((role, role.EVENTS[row]))
            role._bind(plugin, self.reopen.set)

    @property
    def seeded(self) -> set[str]:
        """The rows at least one class hearing it seeds."""
        return {row for row, hearing in self.hearers.items() if any(r.seed for r, _ in hearing)}

    def subjects(self) -> tuple[str, ...]:
        """The union of what each class's `subjects()` answers now."""
        return tuple(dict.fromkeys(s for role in self.roles for s in role.subjects()))

    def handler(self, row: str) -> Callable[[Heard[Any]], Awaitable[None]]:
        from .receive import seeding

        hearing = self.hearers[row]

        async def handed(heard: Heard[Any]) -> None:
            for role, method in hearing:
                if seeding.get() and not role.seed:
                    continue
                await getattr(role, method)(heard)

        return handed

    async def follow(self) -> None:
        from .receive import follow

        await follow(
            self.plugin,
            {row: self.handler(row) for row in self.hearers},
            seed=self.seeded,
            subjects=self.subjects,
            reopen=self.reopen,
        )


class _Running:
    """The lifecycle, once connected (see the module)."""

    def __init__(
        self,
        plugin: Plugin,
        declaration: Declaration,
        *,
        pages: Pages | None,
        port: int | None,
        on_settings: Callable[[Any], Awaitable[None] | None] | None,
        figures: Callable[[], Sequence[Figure]] | None,
    ) -> None:
        self.plugin = plugin
        self.declaration = declaration
        self.pages = pages
        self.port = port
        self.on_settings = on_settings
        self.figures = figures
        self.failing: dict[str, str] = {}

    async def until(self, stopped: asyncio.Event) -> None:
        plugin = self.plugin
        roles = plugin._roles
        tasks: list[asyncio.Task[None]] = []
        served: Any = None
        started: list[RoleBase] = []
        try:
            if self.on_settings is not None:
                tasks.append(asyncio.create_task(self._settings(self.on_settings)))
            for role in roles:
                await role.on_start()
                started.append(role)
            hearing = _Hearing(plugin, roles)
            if hearing.hearers:
                tasks.append(asyncio.create_task(self._keep("hearing", hearing.follow)))
            for role in roles:
                tasks.append(asyncio.create_task(self._keep(_named(role), role.run)))
            if self.figures is not None:
                tasks.append(asyncio.create_task(self._figures(self.figures)))
            if self.pages is not None:
                port = self.port
                if port is None and self.declaration.interface is not None:
                    port = self.declaration.interface.port
                if port is None:
                    raise ValueError("pages are given and no port: name the port they serve on")
                served = self.pages.serve(plugin, port)
                log.info("serving its pages on 127.0.0.1:%d", port)
            await plugin.report(healthy=True, detail="started")
            await stopped.wait()
            log.info("stopping")
        finally:
            for task in tasks:
                task.cancel()
            for task in tasks:
                with contextlib.suppress(asyncio.CancelledError, Exception):
                    await task
            if served is not None:
                served.shutdown()
            for role in reversed(started):
                try:
                    await role.on_stop()
                except Exception:
                    log.exception("%s's on_stop failed", _named(role))

    async def _settings(self, apply: Callable[[Any], Awaitable[None] | None]) -> None:
        typed = getattr(self.declaration, "_typed", None)
        stream = self.plugin.settings(typed)
        async for now in stream:
            done = apply(now)
            if done is not None:
                await done

    async def _figures(self, figures: Callable[[], Sequence[Figure]]) -> None:
        while True:
            try:
                self.plugin.figures = figures()
            except Exception:
                log.exception("the plugin's figures could not be set")
            await asyncio.sleep(FIGURES_SECONDS)

    async def _keep(self, name: str, work: Callable[[], Awaitable[None]]) -> None:
        """`work` run, and run again after a backoff each time it raises
        (ruling 1012); returning ends it. Once a restarted `work` has run
        steadily for the backoff's `steady_s`, the plugin is healthy again."""
        backoff = Backoff()
        while True:
            running = asyncio.ensure_future(work())
            try:
                if name in self.failing:
                    done, _ = await asyncio.wait({running}, timeout=backoff.steady_s)
                    if not done:
                        backoff.steady()
                        await self._recovered(name)
                await running
                if name in self.failing:
                    await self._recovered(name)
                return
            except asyncio.CancelledError:
                raise
            except Exception as failed:
                wait = backoff.failed()
                log.exception("%s failed; starting it again in %.1f s", name, wait)
                self.failing[name] = f"{name} failed ({type(failed).__name__}: {failed})"
                with contextlib.suppress(Exception):
                    await self.plugin.report(
                        healthy=False, detail="; ".join(self.failing.values())[:200]
                    )
                await asyncio.sleep(wait)
            finally:
                if not running.done():
                    running.cancel()
                    with contextlib.suppress(asyncio.CancelledError, Exception):
                        await running

    async def _recovered(self, name: str) -> None:
        self.failing.pop(name, None)
        with contextlib.suppress(Exception):
            if self.failing:
                await self.plugin.report(
                    healthy=False, detail="; ".join(self.failing.values())[:200]
                )
            else:
                await self.plugin.report(healthy=True, detail="started")


def _named(role: RoleBase) -> str:
    return f"{type(role).__name__} ({role.role})"
