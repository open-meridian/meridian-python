"""Contract v23's last items (approved 2026-10-13): a linked account's
currency supplied by the plugin's admin, with its provenance; and a
value-date roll the book keeps unplaced."""

from __future__ import annotations

import meridian
from meridian.edge import supplied_currency
from meridian.plugin.v1 import operations_pb2 as ops

ADMIN = "local|admin"
ROWS = (
    {"external_account": "", "currency": "usd", "changed_by": ADMIN, "changed_at": "1"},
    {
        "external_account": "ACC-EU",
        "currency": "EUR",
        "changed_by": "local|ops",
        "changed_at": "2",
    },
)


def test_the_account_currency_is_a_common_setting_with_a_plugin_wide_default() -> None:
    declared = meridian.account_currency()
    assert (declared.name, declared.kind, declared.label) == (
        "account_currency",
        list,
        "Account currency",
    )
    assert [(c.name, c.kind, c.required) for c in declared.columns] == [
        ("external_account", "external_account", False),
        ("currency", "text", True),
    ]
    declared._declared()  # registration takes it as it is

    @meridian.settings
    class Config:
        account_currency: list = meridian.account_currency(roles=("custody",))

    (held,) = Config.declared()
    assert held.name == "account_currency" and held.roles == ("custody",)
    assert Config.label("account_currency") == "Account currency"


def test_an_accounts_currency_is_its_own_row_else_the_plugin_wide_one() -> None:
    own = supplied_currency(ROWS, "ACC-EU", "market_value.currency_code")
    assert own is not None
    code, provenance = own
    assert code == "EUR"
    assert provenance.kind == "PROVENANCE_KIND_SUPPLIED"
    assert (provenance.field, provenance.person) == ("market_value.currency_code", "local|ops")

    default = supplied_currency(ROWS, "ACC-US", "average_cost.currency_code")
    assert default is not None
    assert default[0] == "USD" and default[1].person == ADMIN


def test_no_currency_is_given_until_one_is_set_and_never_a_guess() -> None:
    assert supplied_currency((), "ACC-US", "market_value.currency_code") is None
    only_eu = (ROWS[1],)
    assert supplied_currency(only_eu, "ACC-US", "market_value.currency_code") is None
    not_a_code = ({"external_account": "", "currency": "dollars", "changed_by": ADMIN},)
    assert supplied_currency(not_a_code, "ACC-US", "market_value.currency_code") is None
    unstamped = ({"external_account": "", "currency": "USD"},)
    assert supplied_currency(unstamped, "ACC-US", "market_value.currency_code") is None


def test_a_roll_the_book_cannot_apply_is_carried_unplaced() -> None:
    arm = ops.UnplacedFact.DESCRIPTOR.fields_by_name["value_date_roll"]
    assert arm.number == 14
    assert arm.containing_oneof.name == "fact"
    assert arm.message_type.name == "ReportValueDateRollRequest"
    assert ops.UNPLACED_REASON_NOTHING_PENDING == 4
    kept = ops.UnplacedFact(
        fact_kind="value-date-roll",
        reason=ops.UNPLACED_REASON_NOTHING_PENDING,
        value_date_roll=ops.ReportValueDateRollRequest(
            venue_account_code="101-001-1234567-001",
            pair=["INS-01J8XQ4M7K00000000CASHEUR", "INS-01J8XQ4M7K00000000CASHUSD"],
        ),
    )
    assert kept.WhichOneof("fact") == "value_date_roll"
