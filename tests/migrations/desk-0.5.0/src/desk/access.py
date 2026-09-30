"""What the person asking may see and do here, from their access tag by tag."""

from __future__ import annotations

import meridian


def readable(caller: meridian.Caller) -> set[str]:
    """Every account the person may read through the plugin, over its tags."""
    return {account for held in caller.access for account in held.read}


def writable(caller: meridian.Caller) -> frozenset[str]:
    """Every account the person may write through the plugin."""
    return frozenset().union(*(held.write for held in caller.access))


def may_show(caller: meridian.Caller, account: str) -> bool:
    return any(account in held.read for held in caller.access)


def may_act(caller: meridian.Caller, account: str) -> bool:
    # Writing includes reading, tag by tag.
    return any(account in held.write for held in caller.access)


def granted_anything(caller: meridian.Caller) -> bool:
    return any(held.read for held in caller.access)


def files_statements(caller: meridian.Caller) -> bool:
    """Whether the person holds the statements tag, and may write through it."""
    return any(held.tag == "statements" and held.write for held in caller.access)
