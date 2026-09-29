"""Build Meridian plugins.

A plugin's entire contract with the platform is its sidecar, listening on
loopback. This package is a client for that surface and nothing more: it never
learns the bus address, never holds a broker credential, and never discovers
another plugin.

    async with await connect() as plugin:
        print(plugin.identity.roles)
        await plugin.report_sync_status(source="snaptrade", connection_healthy=True,
                                        external_account_id="acct-1")
"""

from .asgi import CallerMiddleware
from .client import (
    DEFAULT_ADDRESS,
    SCHEMA_VERSION,
    AccountScope,
    AppliesWhen,
    Caller,
    Choice,
    Grants,
    Identity,
    Interface,
    Plugin,
    Setting,
    Settings,
    TagAccess,
    connect,
)
from .errors import CallFailed, MeridianError, NoSidecar, NotGranted, NotRegistered, Refused

# An amount of currency as a typed operation takes one, and the two readers of
# a number off the wire, generated with the operations (decisions/023).
from .operations import Money, as_decimal, as_money

# The plugin-facing mirrors a typed operation takes, generated with it.
from .plugin.v1.operations_pb2 import (
    ExternalAccount,
    HoldingSide,
    Identifier,
    MissReason,
    SyncState,
)

__all__ = [
    "DEFAULT_ADDRESS",
    "SCHEMA_VERSION",
    "AccountScope",
    "AppliesWhen",
    "CallFailed",
    "Caller",
    "CallerMiddleware",
    "Choice",
    "ExternalAccount",
    "Grants",
    "HoldingSide",
    "Identifier",
    "Identity",
    "Interface",
    "MeridianError",
    "MissReason",
    "Money",
    "NoSidecar",
    "NotGranted",
    "NotRegistered",
    "Plugin",
    "Refused",
    "Setting",
    "Settings",
    "SyncState",
    "TagAccess",
    "as_decimal",
    "as_money",
    "connect",
]
