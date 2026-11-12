"""SDK 0.36.1: fixes the event-contract plugins found on 0.36.0.

- A binary event contract's payout stated at ResolveIdentifier when the
  venue's cash has no ISO 4217 code (Polymarket's pUSD): by the cash's
  resolved instrument where its record is held, else the category alone.
"""

from __future__ import annotations

from decimal import Decimal
from typing import Any

import meridian
from fake_venues import NOW_NS, ContractsMarket, contracts_venue
from meridian.operations import _binary_event_contract
from meridian.roles.data import event_contracts as ec
from meridian.roles.data.testing import Lake

PRICE = "meridian.v1.Price"

# ── A payout in a cash with no ISO 4217 code ────────────────────────────

#: The venue's own token, known by its code alone: no ISO 4217 code.
TOKEN = ec.Cash("PUSD", "token", name="Made-up dollar token")


class TokenMarket(ContractsMarket):
    """The made-up venue, its prices and payouts in its own token."""

    cash = TOKEN


def _token_feed(lake: Lake | None = None) -> ec.Feed:
    feed = ec.Feed(TokenMarket(), ec.ContractMap(), clock_ns=lambda: NOW_NS)
    return lake.bind(feed) if lake is not None else feed


def _contract(**kw: Any) -> ec.Contract:
    held: dict[str, Any] = {
        "code": "BASE-1",
        "title": "Will BASE-1 happen?",
        "binary": True,
        "payout": Decimal("1.0000"),
        "closes_at_ns": NOW_NS,
        "category": "politics",
    }
    held.update(kw)
    return ec.Contract(**held)


def test_a_token_payout_is_stated_by_the_cashs_instrument_once_held() -> None:
    feed = _token_feed()
    feed.contracts.cash_id = "INS-PUSD"
    terms = feed.stated_terms(_contract())
    assert terms is not None
    assert terms.payout == meridian.Money(Decimal("1.0000"), instrument_id="INS-PUSD")
    assert (terms.closes_at_ns, terms.category) == (NOW_NS, "politics")
    wire = _binary_event_contract(terms, "stated_binary_event_contract")
    assert wire.payout.instrument_id == "INS-PUSD" and not wire.payout.currency_code


def test_a_token_payout_before_the_cash_resolves_states_the_category_alone() -> None:
    feed = _token_feed()
    assert not feed.contracts.cash_id
    alone = feed.stated_terms(_contract())
    assert alone == meridian.BinaryEventContract(category="politics")
    wire = _binary_event_contract(alone, "stated_binary_event_contract")
    assert not wire.HasField("payout") and wire.category == "politics"
    assert feed.stated_terms(_contract(category="")) is None


def test_a_currency_payout_is_stated_by_its_code_as_before() -> None:
    feed = ec.Feed(ContractsMarket(), ec.ContractMap(), clock_ns=lambda: NOW_NS)
    feed.contracts.cash_id = "INS-USD"
    terms = feed.stated_terms(_contract())
    assert terms is not None and terms.payout == meridian.Money(Decimal("1.0000"), "USD")


async def test_a_token_venues_contract_resolves_and_is_priced() -> None:
    """What 0.36.0 refused at every ResolveIdentifier of a token venue's
    contract ("payout names no asset"): the contract named, its cash
    resolved, its prices recorded in the token."""
    lake = Lake(contracts_venue.VENUE)
    feed = _token_feed(lake)
    subject = await lake.held(feed, "BASE-1")
    declined = await feed.record_live([subject], data_type=PRICE)
    assert not declined and feed.contracts.subjects == {subject: "BASE-1"}
    cash = feed.contracts.cash_id
    assert cash, "the token resolved once a subject was named"
    monies = [r.price for r in lake.rows()]
    assert monies and all((m.instrument_id, m.currency_code) == (cash, "") for m in monies)
    # Stated again now the cash is held, the payout names its instrument.
    terms = feed.stated_terms(feed.contracts.contracts["BASE-1"])
    assert terms is not None and terms.payout.instrument_id == cash
