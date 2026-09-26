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

from .client import (
    DEFAULT_ADDRESS,
    SCHEMA_VERSION,
    AccountScope,
    Caller,
    Grants,
    Identity,
    Interface,
    Plugin,
    Setting,
    Settings,
    TagAccess,
    connect,
)
from .errors import CallFailed, MeridianError, NotGranted, NotRegistered, Refused

# The plugin-facing mirrors a typed operation takes, generated with it.
from .plugin.v1.operations_pb2 import Identifier, MissReason

__all__ = [
    "DEFAULT_ADDRESS",
    "SCHEMA_VERSION",
    "AccountScope",
    "CallFailed",
    "Caller",
    "Grants",
    "Identifier",
    "Identity",
    "Interface",
    "MeridianError",
    "MissReason",
    "NotGranted",
    "NotRegistered",
    "Plugin",
    "Refused",
    "Setting",
    "Settings",
    "TagAccess",
    "connect",
]
