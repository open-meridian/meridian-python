"""Contract v23's last items (approved 2026-10-13): a linked account's
currency supplied by the plugin's admin, with its provenance, on a holding
and on ResolveIdentifier; and a value-date roll the book keeps unplaced."""

from __future__ import annotations

from decimal import Decimal

import meridian
from meridian.edge import derived, raw_record, reported, supplied_currency
from meridian.operations import Provenance
from meridian.plugin.v1 import operations_pb2 as ops
from meridian.suites import Recorder, check, suite

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


async def _a_holding_with_no_stated_currency(currency: str, said: list[Provenance]) -> Recorder:
    recorder = Recorder("custody-1")
    await recorder.record_holding(
        statement_id="S",
        instrument_id="LCL-QQQ",
        quantity=10,
        side="long",
        average_cost=meridian.Money(Decimal("412.50"), currency),
        provenance=said,
    )
    await recorder.resolve_identifier(
        identifiers=[meridian.Identifier(scheme="symbol", value="QQQ", source="custody-1")],
    )
    return recorder


async def test_a_currency_not_stated_is_derived_by_a_rule_or_supplied_by_the_admin() -> None:
    """custody's currency-not-stated expects average_cost's currency derived
    by a named rule or supplied by a person (approved 2026-10-13): the
    account's currency its admin set passes the case, said as supplied."""
    case = suite("custody").case("currency-not-stated")
    (holding, resolved) = case.expect
    assert holding.row == "RecordHolding" and len(holding.any_of) == 2
    assert resolved.row == "ResolveIdentifier"

    given = supplied_currency(ROWS, "ACC-US", "average_cost.currency_code")
    assert given is not None
    code, supplied = given
    recorder = await _a_holding_with_no_stated_currency(code, [supplied])
    assert check(case, recorder) is None
    rule = derived("average_cost.currency_code", "the account's base currency")
    assert check(case, await _a_holding_with_no_stated_currency("USD", [rule])) is None
    unsaid = await _a_holding_with_no_stated_currency("USD", [])
    assert "matches none of its ways" in (check(case, unsaid) or "")


def test_the_supplied_currency_is_ready_to_put_on_resolve_identifier() -> None:
    """ResolveIdentifierRequest.provenance (approved 2026-10-13): by default
    the entry names stated_currency."""
    given = supplied_currency(ROWS, "ACC-US")
    assert given is not None
    code, entry = given
    assert code == "USD"
    assert (entry.field, entry.kind, entry.person) == (
        "stated_currency",
        "PROVENANCE_KIND_SUPPLIED",
        ADMIN,
    )
    params = ops.ResolveIdentifierParams(
        stated_currency=code,
        provenance=[
            ops.Provenance(
                field=entry.field, kind=ops.PROVENANCE_KIND_SUPPLIED, person=entry.person
            )
        ],
    )
    assert ops.ResolveIdentifierParams.DESCRIPTOR.fields_by_name["provenance"].number == 9
    assert params.provenance[0].field == "stated_currency"


async def _a_resolve(currency: str, said: list[Provenance]) -> Recorder:
    recorder = Recorder("custody-1")
    await recorder.resolve_identifier(
        identifiers=[meridian.Identifier(scheme="symbol", value="QQQ", source="custody-1")],
        stated_asset_class="ASSET_CLASS_FUND",
        stated_currency=currency,
        provenance=said,
    )
    return recorder


async def test_resolve_gives_the_currency_with_its_provenance() -> None:
    """custody's renamed case (approved 2026-10-13): a currency stated, or
    one supplied or derived with its entry."""
    case = suite("custody").case("resolve-gives-the-currency-with-its-provenance")
    (resolved,) = case.expect
    assert resolved.row == "ResolveIdentifier" and len(resolved.any_of) == 4
    assert case.about == "" and case.about_field == ""

    given = supplied_currency(ROWS, "ACC-EU")
    assert given is not None
    code, entry = given
    assert check(case, await _a_resolve(code, [entry])) is None
    assert check(case, await _a_resolve("USD", [])) is None, "stated, with no entry"
    rule = derived("stated_currency", "the account's only cash currency")
    assert check(case, await _a_resolve("USD", [rule])) is None
    elsewhere = reported("stated_currency", raw_record("accounts/ACC-US", "custody-1"))
    assert check(case, await _a_resolve("USD", [elsewhere])) is None

    unstated = await _a_resolve("", [])
    assert "matches none of its ways" in (check(case, unstated) or "")
    wrong_field = supplied_currency(ROWS, "ACC-US", "average_cost.currency_code")
    assert wrong_field is not None
    misnamed = await _a_resolve("USD", [wrong_field[1]])
    assert "matches none of its ways" in (check(case, misnamed) or "")
    names = {c.name for c in suite("custody").cases}
    assert "resolve-states-what-the-source-states" not in names
