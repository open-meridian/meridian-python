"""What a version declares beside its roles (W8.1, W4.1, contract v11).

spec/vendor-differences-have-a-place-in-the-contract, requirements 16, 19 and
30, Q6 and Q15: the names of the secret settings it will ask for, so an admin
knows before launch what credentials it needs; what it receives from its
vendor and does not carry, by name only, per role, each with why -- the
evidence the common model may need to grow; and, for a plugin holding an edge
role, the storage it asks for and how long it keeps its raw records
(decisions/028). Nothing about what it supports: its roles say that. Never a
value, an account or an identifier.

Built from the plugin's code, once, and used twice: `connect(declaration=...)`
sends it at registration, and `meridian plugin upload` reads the same one
from the built image, naming it in pyproject.toml's `[tool.meridian]` as
`declaration = "my_plugin.declaration:DECLARATION"`, and running
`meridian-declaration my_plugin.declaration:DECLARATION` there, which prints
it as JSON.

    DECLARATION = Declaration(
        settings=SETTINGS,
        not_carried=[NotCarried("custody", "myvendor:position", "open_pnl",
                                "no_contract_meaning")],
        storage=Storage(retention_days=2555),
    )
"""

from __future__ import annotations

import importlib
import json
import sys
from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import Any, Literal

from .bounds import (
    NOT_CARRIED_NAME_LENGTH,
    NOT_CARRIED_ROLE_LENGTH,
    NOT_CARRIED_SCHEME_LENGTH,
    PLUGIN_DECLARATION_NOT_CARRIED_COUNT,
    STORAGE_DECLARATION_RETENTION_DAYS_RANGE,
)
from .v1 import sidecar_pb2

#: The roles at the edge, which alone may own storage for their raw records
#: (decisions/028).
EDGE_ROLES = frozenset(
    {"ccm", "custody", "dgm", "match", "reporting", "servicing", "settlement"}
)

Reason = Literal["no_contract_meaning", "not_converted"]
_REASONS: dict[str, int] = {
    "no_contract_meaning": sidecar_pb2.NOT_CARRIED_REASON_NO_CONTRACT_MEANING,
    "not_converted": sidecar_pb2.NOT_CARRIED_REASON_NOT_CONVERTED,
}


@dataclass(frozen=True)
class NotCarried:
    """One vendor field, or one code of a vendor's code set, the plugin
    receives in `role` and does not carry: `no_contract_meaning`, a place the
    model may grow, or `not_converted`, a meaning the contract has that the
    plugin does not yet convert to."""

    role: str
    scheme: str
    name: str
    reason: Reason

    def __post_init__(self) -> None:
        for part, text, bound in (
            ("role", self.role, NOT_CARRIED_ROLE_LENGTH),
            ("scheme", self.scheme, NOT_CARRIED_SCHEME_LENGTH),
            ("name", self.name, NOT_CARRIED_NAME_LENGTH),
        ):
            if not bound.least <= len(text) <= bound.most:
                raise ValueError(
                    f"a name not carried's {part} is {bound.least} to {bound.most} characters"
                )
        if self.reason not in _REASONS:
            raise ValueError(
                f"{self.reason!r} is not a reason: no_contract_meaning or not_converted"
            )


@dataclass(frozen=True)
class Storage:
    """The storage a plugin at the edge asks for, for its raw records, and
    how many days it keeps one: the reach of a backfill."""

    retention_days: int

    def __post_init__(self) -> None:
        bound = STORAGE_DECLARATION_RETENTION_DAYS_RANGE
        if not bound.least <= self.retention_days <= bound.most:
            raise ValueError(f"retention_days is {bound.least} to {bound.most}")


@dataclass(frozen=True)
class Declaration:
    """A version's declaration. `settings` are the ones it declares at
    registration (`meridian.Setting`), whose secret ones' names it carries."""

    settings: Sequence[Any] = ()
    not_carried: Sequence[NotCarried] = field(default=())
    storage: Storage | None = None

    def __post_init__(self) -> None:
        if len(self.not_carried) > PLUGIN_DECLARATION_NOT_CARRIED_COUNT.most:
            raise ValueError(
                f"at most {PLUGIN_DECLARATION_NOT_CARRIED_COUNT.most} names not carried"
            )

    @property
    def secret_settings(self) -> list[str]:
        """The names of the secret settings, in their order."""
        return [setting.name for setting in self.settings if getattr(setting, "secret", False)]

    def refused_for(self, roles: Sequence[str]) -> str | None:
        """Why this declaration cannot stand for a version holding `roles`,
        as `meridian plugin check` and the conductor say it, or None."""
        for held in self.not_carried:
            if held.role not in roles:
                return (
                    f"a name not carried is declared in {held.role}, which is not a role held"
                )
        if self.storage is not None and not EDGE_ROLES.intersection(roles):
            return (
                "storage is asked for by a plugin holding no edge role; only "
                + ", ".join(sorted(EDGE_ROLES))
                + " own storage (decisions/028)"
            )
        return None

    def to_wire(self) -> sidecar_pb2.PluginDeclaration:
        """As registration carries it."""
        return sidecar_pb2.PluginDeclaration(
            secret_settings=self.secret_settings,
            not_carried=[
                sidecar_pb2.NotCarried(
                    role=held.role,
                    scheme=held.scheme,
                    name=held.name,
                    reason=_REASONS[held.reason],  # type: ignore[arg-type]
                )
                for held in self.not_carried
            ],
            storage=(
                None
                if self.storage is None
                else sidecar_pb2.StorageDeclaration(retention_days=self.storage.retention_days)
            ),
        )

    def to_json(self) -> dict[str, Any]:
        """As an upload carries it, which the dashboard reads (W8.1)."""
        return {
            "secret_settings": self.secret_settings,
            "not_carried": [
                {
                    "role": held.role,
                    "scheme": held.scheme,
                    "name": held.name,
                    "reason": held.reason,
                }
                for held in self.not_carried
            ],
            "storage": (
                None
                if self.storage is None
                else {"retention_days": self.storage.retention_days}
            ),
        }


def load(named: str) -> Declaration:
    """The declaration `module:attribute` names, imported as the plugin runs."""
    module, _, attribute = named.partition(":")
    if not module or not attribute:
        raise ValueError(f"{named!r} does not name a declaration as module:attribute")
    found = getattr(importlib.import_module(module), attribute)
    if not isinstance(found, Declaration):
        raise TypeError(f"{named} is a {type(found).__name__}, not a meridian Declaration")
    return found


def main(argv: Sequence[str] | None = None) -> int:
    """`meridian-declaration module:attribute`: the declaration as JSON, on
    standard output, for `meridian plugin upload` to send (W8.1)."""
    args = list(sys.argv[1:] if argv is None else argv)
    if len(args) != 1:
        print("usage: meridian-declaration module:attribute", file=sys.stderr)
        return 2
    try:
        declared = load(args[0])
    except (ImportError, AttributeError, TypeError, ValueError) as failed:
        print(f"meridian-declaration: {failed}", file=sys.stderr)
        return 1
    print(json.dumps(declared.to_json(), sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
