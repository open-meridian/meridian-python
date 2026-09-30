"""The desk's access, page and recording, with no sidecar."""

from __future__ import annotations

import asyncio
from typing import Any

import pytest
from meridian import CallFailed, Caller, NotLinked

from desk.access import granted_anything, may_act, may_show, readable, writable
from desk.page import render
from desk.record import record

ANN = Caller(
    subject="u-1",
    display_name="Ann",
    read=frozenset({"ACC-1", "ACC-2"}),
    write=frozenset({"ACC-1"}),
    header="h",
)

# Two tags: what she may do is what either gives her.
BOB = Caller(
    subject="u-2",
    display_name="Bob",
    read=frozenset({"ACC-1"}) | frozenset({"ACC-3"}),
    write=frozenset({"ACC-3"}),
    header="h",
)

NOBODY = Caller("u-3", "Cy", header="h")


def test_what_ann_may_read_and_write() -> None:
    assert readable(ANN) == {"ACC-1", "ACC-2"}
    assert writable(ANN) == {"ACC-1"}
    assert may_show(ANN, "ACC-2") and not may_act(ANN, "ACC-2")
    assert may_act(ANN, "ACC-1")


def test_two_tags_give_what_either_gives() -> None:
    assert readable(BOB) == {"ACC-1", "ACC-3"}
    assert writable(BOB) == {"ACC-3"}
    assert may_show(BOB, "ACC-3") and may_act(BOB, "ACC-3") and not may_act(BOB, "ACC-1")


def test_nobody_is_granted_nothing() -> None:
    assert not granted_anything(NOBODY) and readable(NOBODY) == set()
    assert "Nothing is granted to you here." in render(NOBODY)


def test_the_page_says_what_each_account_allows() -> None:
    page = render(ANN)
    assert "<code>ACC-1</code></td><td>read and write" in page
    assert "<code>ACC-2</code></td><td>read</td>" in page
    assert '/.meridian/ui/0.1.0/meridian.css' in page


class Refusing:
    """A plugin whose sidecar refuses every row, as told."""

    def __init__(self, refusal: Exception) -> None:
        self.refusal = refusal

    async def record_holding(self, **params: Any) -> None:
        raise self.refusal


def test_an_unlinked_account_is_said_so() -> None:
    refusal = NotLinked(
        "RecordHolding", "external account acct-9 is not linked to an account"
    )
    said = asyncio.run(record(Refusing(refusal), "st-1", "acct-9"))  # type: ignore[arg-type]
    assert said == "unlinked"


def test_any_other_refusal_is_raised() -> None:
    refusal = CallFailed("RecordHolding", "refused", "no statement st-1")
    with pytest.raises(CallFailed):
        asyncio.run(record(Refusing(refusal), "st-1", "acct-9"))  # type: ignore[arg-type]
