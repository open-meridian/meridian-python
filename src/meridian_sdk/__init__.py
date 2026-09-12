"""Build Meridian plugins.

A plugin's entire contract with the platform is its sidecar, listening on
loopback. This package is a client for that surface and nothing more: it never
learns the bus address, never holds a broker credential, and never discovers
another plugin.

    async with await connect() as plugin:
        print(plugin.identity.role)
        await plugin.publish("platform.custody.x.event.sync-status", event)
"""

from .errors import CallFailed, MeridianError, NotGranted, NotRegistered, Refused
from .plugin import (
    DEFAULT_ADDRESS,
    SCHEMA_VERSION,
    Delivery,
    Grants,
    Identity,
    Plugin,
    connect,
)

__all__ = [
    "DEFAULT_ADDRESS",
    "SCHEMA_VERSION",
    "CallFailed",
    "Delivery",
    "Grants",
    "Identity",
    "MeridianError",
    "NotGranted",
    "NotRegistered",
    "Plugin",
    "Refused",
    "connect",
]
