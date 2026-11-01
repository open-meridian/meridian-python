"""listed's helpers, against the SDK."""

import importlib
from datetime import date
from decimal import Decimal

import meridian.roles.chains
from listed import chain, money, servicing, spread
from meridian.roles.chains import osi_terms


def test_a_chains_symbols() -> None:
    (symbol,) = chain.symbols("AAPL", "2026-11-20", ["230"])
    assert symbol == "AAPL  261120C00230000"
    assert osi_terms(symbol) == ("AAPL", date(2026, 11, 20), "C", Decimal("230"))
    assert spread.lazily(symbol) == "AAPL"


def test_a_spreads_legs_in_lowest_terms() -> None:
    legs = spread.vertical("INS-1", "INS-2")
    assert [leg.ratio for leg in legs] == [1, 1]
    assert spread.moneyness([Decimal("100")], Decimal("104")) == [Decimal("4")]


def test_a_pools_money() -> None:
    assert money.cash(Decimal("1000000"), Decimal("101.5")) == Decimal("1015000.000")
    assert money.itm(Decimal("100"), Decimal("97")) == Decimal("3")
    assert servicing.face(Decimal("1000000"), Decimal("0.5")) == Decimal("500000.00")


def test_a_symbol_patched(monkeypatch) -> None:
    # The SDK's own, as meridian.roles.chains names it, patched by its path.
    monkeypatch.setattr("meridian.roles.chains.osi_symbol", lambda *args: "X")
    assert meridian.roles.chains.osi_symbol("A", "2026-01-16", "call", "1") == "X"
    assert chain.symbols("A", "2026-01-16", ["1"]) == ["X"]
    assert importlib.import_module("meridian.roles.debt").percent_of_par(100, 100) == 100
