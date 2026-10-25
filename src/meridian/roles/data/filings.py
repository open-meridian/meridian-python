"""The lake's filings slice (contract v28; spec/a-public-rates-and-filings-data-plugin
§6, FDP stage 2; W10.4).

What a filings source publishes, as rows of the lake, each under a company
or a security with its role on the row:

- `Filing`: a filing's accession number and form, its kind, items and
  dates, under its filer (`filing`);
- `ReportedFact`: one value a filing reports for a concept and a period,
  an amount or a value with its unit; a later filing restating it, or
  repeating it, is the next version of the same row key, naming that filing
  (`fact`);
- `HoldingsReport` and `Holding`: a 13F, 13D or 13G and each holding it
  lists, the holder and the held security, a 13F's whole report marked
  complete (`holdings_report`, `holding`);
- `CorporateActionAnnounced`: a cash dividend declared, with its dates and
  the rule that found them (`dividend`);
- `RatingAction`: an agency's action on an issuer or an issue, the agency
  as the `rater` (`rating_action`).

A filer, holder or issuer is a company record (`ENT-`), resolved by the
identifiers the source states (a CIK, an LEI) with `ResolveCompany`, once
per identifier per process (`Companies`); a security named by CUSIP alone
is resolved as any instrument is, by its identifiers. A company or a
security that does not resolve is kept raw on the row (`unconverted`) and
reported as any miss is. Each kind is recorded in the lake's batches
through `Wants.record` (`filings`, `reported_facts`, `holdings_reports`,
`holdings`, `corporate_actions`, `rating_actions`).
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from typing import Any

from ...errors import CallFailed
from ...operations import (
    CorporateActionAnnounced,
    Filing,
    Holding,
    HoldingsReport,
    Money,
    ObservationMeta,
    RatingAction,
    ReportedFact,
    SourceTime,
    SubjectRef,
    UnitValue,
)
from ...plugin.v1 import operations_pb2 as ops

#: The SEC's Central Index Key and the Legal Entity Identifier, as schemes.
CIK = "cik"
LEI = "lei"
CUSIP = "cusip"


def cik(value: str | int) -> str:
    """A CIK as the scheme holds it: ten digits, zero padded."""
    digits = str(value).strip()
    if not digits.isdigit() or len(digits) > 10:
        raise ValueError(f"{value!r} is not a CIK")
    return digits.zfill(10)


@dataclass
class Companies:
    """Company records resolved by an identifier the source states, each
    asked once per process; a miss remembered as empty."""

    plugin: Any
    held: dict[tuple[str, str], str] = field(default_factory=dict)

    async def resolve(self, scheme: str, value: str) -> str:
        """The company's `ENT-` ID, or empty where none resolves."""
        key = (scheme, value)
        if key not in self.held:
            try:
                answer = await self.plugin.resolve_company(
                    identifiers=[ops.Identifier(scheme=scheme, value=value)]
                )
                self.held[key] = answer.company_id
            except CallFailed:  # none held: the row keeps the filer as reported
                self.held[key] = ""
        return self.held[key]

    async def filer(self, number: str | int) -> str:
        """A filer by its CIK."""
        return await self.resolve(CIK, cik(number))


def meta(
    row_key: str,
    subjects: Sequence[tuple[str, str]],
    *,
    dataset: str,
    valid_from_ns: int = 0,
    published_ns: int = 0,
    raw: ops.RawRecordRef | None = None,
    unconverted: Sequence[ops.AsReported] = (),
) -> ObservationMeta:
    """A filings row's envelope: each subject an ID and its role (filer,
    holder, held, subject, issuer, rater), the source's published time."""
    return ObservationMeta(
        row_key=row_key[:128],
        subjects=[
            SubjectRef(entity_id=entity, role=role) for entity, role in subjects if entity
        ],
        source=ops.Source(dataset=dataset),
        valid_from_ns=valid_from_ns,
        source_times=[SourceTime(kind="published", at_ns=published_ns)] if published_ns else (),
        raw=raw,
        unconverted=tuple(unconverted),
    )


def ref(accession_number: str, form: str) -> ops.FilingRef:
    return ops.FilingRef(accession_number=accession_number, form=form)


def filing(
    filer_id: str,
    accession_number: str,
    form: str,
    kind: str,
    filed_date: date | str,
    *,
    dataset: str,
    items: Sequence[str] = (),
    period_of_report: date | str = "",
    **at: Any,
) -> Filing:
    """A filing under its filer, keyed by its accession number."""
    return Filing(
        meta=meta(accession_number, [(filer_id, "filer")], dataset=dataset, **at),
        filing=ref(accession_number, form),
        kind=kind,
        items=tuple(items),
        period_of_report=period_of_report,
        filed_date=filed_date,
    )


def fact(
    filer_id: str,
    concept: str,
    period_end: date | str,
    filed_in: ops.FilingRef,
    *,
    dataset: str,
    row_key: str,
    amount: Money | None = None,
    value: UnitValue | None = None,
    period_start: date | str = "",
    **at: Any,
) -> ReportedFact:
    """One reported value of a concept for a period, an amount or a value,
    naming the filing that reported it; the same `row_key` for the same
    concept, unit and period, so a restatement or a repeat is its next
    version."""
    if (amount is None) == (value is None):
        raise ValueError("a fact carries an amount or a value")
    return ReportedFact(
        meta=meta(row_key, [(filer_id, "filer")], dataset=dataset, **at),
        concept=concept,
        amount=amount,
        value=value,
        period_start=period_start,
        period_end=period_end,
        filing=filed_in,
    )


def holdings_report(
    holder_id: str,
    filed_in: ops.FilingRef,
    kind: str,
    report_date: date | str,
    *,
    dataset: str,
    complete: bool = False,
    **at: Any,
) -> HoldingsReport:
    """A 13F, 13D or 13G under its holder, keyed by its accession number;
    a 13F listing every holding `complete`."""
    return HoldingsReport(
        meta=meta(filed_in.accession_number, [(holder_id, "holder")], dataset=dataset, **at),
        kind=kind,
        report_date=report_date,
        complete=complete,
        filing=filed_in,
    )


def holding(
    report: HoldingsReport,
    held_id: str,
    held_key: str,
    *,
    shares: Decimal | int | None = None,
    market_value: Money | None = None,
    percent_of_class: Decimal | None = None,
    unconverted: Sequence[ops.AsReported] = (),
) -> Holding:
    """One holding of a report: the holder, the held security (empty where
    it did not resolve, kept as reported in `unconverted`), its shares, its
    value and, on a 13D or 13G, its percent of the class; keyed by the
    report and the security as the report names it (a CUSIP)."""
    assert report.meta is not None
    holder = report.meta.subjects[0].entity_id if report.meta.subjects else ""
    return Holding(
        meta=meta(
            f"{report.meta.row_key}:{held_key}",
            [(holder, "holder"), (held_id, "held")],
            dataset=report.meta.source.dataset if report.meta.source else "",
            valid_from_ns=report.meta.valid_from_ns,
            raw=report.meta.raw,
            unconverted=unconverted,
        ),
        report_row_key=report.meta.row_key,
        quantity=None if shares is None else UnitValue(value=shares, unit="shares"),
        market_value=market_value,
        percent_of_class=(
            None
            if percent_of_class is None
            else UnitValue(value=percent_of_class, unit="percent")
        ),
    )


def dividend(
    security_id: str,
    issuer_id: str,
    amount_per_share: Money,
    *,
    dataset: str,
    row_key: str,
    ex_date: date | str,
    declared_date: date | str = "",
    record_date: date | str = "",
    payment_date: date | str = "",
    rule: tuple[str, int],
    filed_in: ops.FilingRef | None = None,
    **at: Any,
) -> CorporateActionAnnounced:
    """A cash dividend declared on a security by its issuer, with its dates
    and the rule (definition and version) that found them."""
    definition, version = rule
    return CorporateActionAnnounced(
        meta=meta(row_key, [(security_id, "subject"), (issuer_id, "issuer")], dataset=dataset,
                  **at),
        kind="cash_dividend",
        amount_per_share=amount_per_share,
        declared_date=declared_date,
        ex_date=ex_date,
        record_date=record_date,
        payment_date=payment_date,
        rule=ops.MeasureRef(definition=definition, version=version),
        filing=filed_in,
    )  # fmt: skip


def rating_action(
    rated_id: str,
    rater_id: str,
    rating: str,
    rating_class: str,
    action: str,
    *,
    dataset: str,
    row_key: str,
    rated_role: str = "subject",
    **at: Any,
) -> RatingAction:
    """An agency's action on an issuer (`subject`) or an issue (`held`), the
    agency the `rater`; refused without one."""
    if not rater_id:
        raise ValueError("a rating action names its rater")
    return RatingAction(
        meta=meta(
            row_key, [(rated_id, rated_role), (rater_id, "rater")], dataset=dataset, **at
        ),
        rating=rating,
        rating_class=rating_class,
        action=action,
    )
