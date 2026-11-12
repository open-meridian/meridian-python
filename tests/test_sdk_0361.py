"""SDK 0.36.1: fixes the event-contract plugins found on 0.36.0.

- A binary event contract's payout stated at ResolveIdentifier when the
  venue's cash has no ISO 4217 code (Polymarket's pUSD): by the cash's
  resolved instrument where its record is held, else the category alone.
- The event-contract check admits the contract's own event and series
  (Kalshi states a market's category only on its series, reached through its
  event), and still refuses a venue-wide list.
"""

from __future__ import annotations

from dataclasses import replace
from decimal import Decimal
from types import SimpleNamespace
from typing import Any

import pytest

import meridian
from fake_venues import NOW_NS, ContractsMarket, contracts_venue
from meridian.operations import _binary_event_contract
from meridian.roles.data import event_contracts as ec
from meridian.roles.data.testing import EventContractsChecks, Lake

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


# ── The check admits the contract's own event and series ────────────────

BASE_EVENT, BASE_SERIES = "FAKEV-EV-26DEC", "FAKEV-SER"


class AskedMarket(ContractsMarket):
    """The made-up venue, keeping the URLs it was asked, as a plugin's raw
    records do: each contract by its code and, for BASE-1's category, its
    event and that event's series (as Kalshi's), plus whatever `extra`
    names."""

    extra: tuple[str, ...] = ()
    root = "https://fakev.invalid/v2"

    def __init__(self, now_ns: int = NOW_NS, directory: Any = None) -> None:
        super().__init__(now_ns, directory)
        self.asked: list[str] = []

    def contract(self, code: str, watching: bool = False) -> ec.Contract | None:
        self.asked.append(f"{self.root}/markets/{code}")
        read = super().contract(code, watching)
        if read is None or code != "BASE-1":
            return read
        self.asked.append(f"{self.root}/events/{BASE_EVENT}?with_nested_markets=true")
        self.asked.append(f"{self.root}/series/{BASE_SERIES}")
        self.asked.extend(f"{self.root}{path}" for path in self.extra)
        return replace(read, market=BASE_EVENT, category="economics")

    def event(self, ref: str) -> ec.Event | None:
        if ref != BASE_EVENT:
            return None
        return ec.Event(ref=ref, title="An event", members=("BASE-1",), series=BASE_SERIES)


def _asking(extra: tuple[str, ...] = ()) -> EventContractsChecks:
    market = type("Asked", (AskedMarket,), {"extra": extra})
    checks = EventContractsChecks()
    checks.venue = SimpleNamespace(
        **{
            **vars(contracts_venue),
            "market": lambda now_ns=NOW_NS, directory=None: market(now_ns, directory),
            "calls": lambda market: list(market.asked),
        }
    )
    return checks


async def test_the_check_admits_the_contracts_own_event_and_series() -> None:
    await _asking().test_only_the_contracts_wanted_are_read_never_the_venues_list()


@pytest.mark.parametrize(
    "extra",
    [
        ("/markets",),  # the venue's whole list
        ("/markets?status=open",),
        ("/events",),
        ("/series",),
        ("/events?series_ticker=FAKEV-SER",),  # a list of the series' events
        ("/events/FAKEV-EV-OTHER",),  # another contract's event
        ("/series/FAKEV-OTHER",),  # another series
    ],
)
async def test_the_check_still_refuses_a_venue_wide_list(extra: tuple[str, ...]) -> None:
    with pytest.raises(AssertionError):
        await _asking(extra).test_only_the_contracts_wanted_are_read_never_the_venues_list()
