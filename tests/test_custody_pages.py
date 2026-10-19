"""Custody's pages, the SDK's from 0.31.0 (ruling 213): Account links under
Manage, Statements and History under Open and View, each the same answer as
its tool, an account shown only to a person who may read the account it is
linked to, and linking held to what the credential reaches and what a
deployment admin granted."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from decimal import Decimal
from typing import Any

import meridian
from meridian.plugin.v1 import operations_pb2 as ops
from meridian.roles import custody
from meridian.suites import Recorder
from meridian.testing import PageClient

NUMBER, OTHER = "VEN-1001", "VEN-1002"
ACCOUNT = "ACC-01JAE000000000000000000001"


@dataclass(frozen=True)
class Activity:
    external_activity_id: str
    kind: int
    trade_date: str
    units: Decimal | None
    amount: meridian.Money | None
    description: str


class Source:
    vendor = "Brokerage"
    credential = "token"

    def reached(self) -> Sequence[str]:
        return [NUMBER, OTHER]

    def account(self, number: str) -> custody.ExternalAccountRead:
        return custody.ExternalAccountRead(number, f"Brokerage {number}", "Brokerage, margin")

    def custodian(self) -> str:
        return "Brokerage"

    def account_type(self, number: str) -> str:
        return "margin"

    def statement(self, number: str) -> tuple[str, str] | None:
        return ("2026-10-16", "Closed (Current)") if number == NUMBER else None

    def activities(self, number: str) -> Sequence[tuple[Any, str]]:
        dividend = Activity(
            "act-1", meridian.ActivityKind.ACTIVITY_KIND_DIVIDEND, "2026-09-15", None,
            meridian.Money(Decimal("0.75"), "USD"), "Cash dividend",
        )  # fmt: skip
        return [(dividend, "INS-AAPL")] if number == NUMBER else []

    def links(self) -> Sequence[Any]:
        return (meridian.LinkedExternalAccount(NUMBER, ACCOUNT, "Growth"),)


def client(**caller: Any) -> tuple[PageClient, Recorder]:
    pages = meridian.Pages("Brokerage")
    custody.account_pages(pages, Source, what="This plugin brings brokerage accounts in")
    recorder = Recorder("brokerage-1")
    recorder.answer(
        "ReadAccountsForLinking",
        lambda _: ops.ReadAccountsForLinkingResult(
            accounts=[ops.AccountRecord(account_id=ACCOUNT, name="Growth")]
        ),
    )
    return PageClient(pages, recorder, **caller), recorder


def test_the_three_pages_are_declared_with_their_tools() -> None:
    pages, _ = client()
    assert pages.get(custody.ACCOUNT_LINKS, "admin").status == 200
    assert pages.get(custody.ACCOUNT_LINKS, "write").status == 403
    links = pages.call_tool("read_account_links", level="admin").data
    assert [a["external_account_id"] for a in links["external_accounts"]] == [NUMBER, OTHER]
    assert links["accounts"] == [{"account_id": ACCOUNT, "name": "Growth"}]


def test_statements_and_history_show_a_linked_account_to_its_readers_alone() -> None:
    reader, _ = client(read=[ACCOUNT])
    statements = reader.call_tool("read_statements", level="read").data["statements"]
    assert statements == [
        {"account": "Growth", "custodian": "Brokerage", "as_of": "2026-10-16",
         "state": "Closed (Current)"}
    ]  # fmt: skip
    history = reader.call_tool("read_account_activities", level="read").data["activities"]
    assert [(a["kind"], a["amount"], a["instrument_id"]) for a in history] == [
        ("dividend", "0.75", "INS-AAPL")
    ]
    stranger, _ = client(read=["ACC-SOMEONE-ELSE"])
    assert stranger.call_tool("read_statements", level="read").data["statements"] == []


def test_linking_is_held_to_what_the_token_reaches_and_what_was_granted() -> None:
    admin, recorder = client()
    unreached = admin.call_tool(
        "check_link_account", {"external_account_id": "VEN-9"}, level="admin"
    )
    assert unreached.outcome == "refused" and "token reaches no such account" in str(
        unreached.json
    )
    stranger = admin.call_tool(
        "check_link_account",
        {"external_account_id": NUMBER, "account_id": "ACC-NOT-GRANTED"},
        level="admin",
    )
    assert stranger.outcome == "refused"
    creating = admin.call_tool(
        "check_link_account",
        {"external_account_id": OTHER, "intent": "create", "new_account_name": "Income"},
        level="admin",
    )
    assert creating.outcome == "refused", "only a deployment admin creates an account"
    assert recorder.on("LinkExternalAccount") == []


def test_a_deployment_admin_creates_and_links_with_the_custodian_and_type_filled() -> None:
    admin, recorder = client(deployment_admin=True)
    made = admin.call_tool(
        "link_account",
        {"external_account_id": OTHER, "intent": "create", "new_account_name": "Income"},
        level="admin",
    )
    assert made.status == 200
    (sent,) = recorder.on("LinkExternalAccount")
    assert (sent.new_account_custodian, sent.new_account_type) == ("Brokerage", "margin")
