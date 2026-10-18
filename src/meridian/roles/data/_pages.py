"""The data role's pages filled from the plugin's own bookkeeping (`Wants`)
and catalogue: Datasets' "Served" and "Wants" rows, and the venue's part of
Connection, for a plugin of one venue (spec/plugin-pages-follow-their-role,
"data, a data plugin")."""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any

from ...figures import Figure
from ...v1 import sidecar_pb2
from ._reading import Endpoint, Session, iso_time
from ._records import Served, WantHeard
from ._wants import Venue, Wants


def _terms(licence: Any) -> str:
    """A dataset's default terms in words: kept or served only, for how long,
    displayed or not, one person's."""
    if licence is None:
        return ""
    said = ["kept" if licence.kept else "served, not kept"]
    if licence.retention_days:
        said.append(f"{licence.retention_days} days")
    said.append("display" if licence.display else "no display")
    if licence.personal_use:
        said.append("one person's")
    return ", ".join(said)


def _arrives(mode: object) -> str:
    if isinstance(mode, int):
        named = str(sidecar_pb2.ObservationMode.Name(mode))
        return named.removeprefix("OBSERVATION_MODE_").lower()
    return str(mode)


def served(
    catalogue: Iterable[Any], instance: str, wants: Wants | None, entitled_at_vendor: str
) -> list[Any]:
    """Datasets' "Served": one row per declared dataset (`DatasetDeclaration`),
    named as rows name it, with what was recorded and declined to it, when it
    last recorded and whether a deployment admin has licensed it."""
    rows = []
    for declared in catalogue:
        name = f"{instance}:{declared.key}"
        sent = wants.sent_to(declared.key) if wants is not None else None
        rows.append(
            Served(
                dataset=name,
                data=", ".join(t.removeprefix("meridian.v1.") for t in declared.data_types),
                arrives=", ".join(_arrives(m) for m in declared.modes),
                day=f"{declared.day_time_zone}, ends {declared.day_end_minute // 60:02d}:"
                f"{declared.day_end_minute % 60:02d}",
                default_terms=_terms(declared.licence_default),
                entitled_at_vendor=entitled_at_vendor,
                recorded=sent.recorded if sent else 0,
                declined=sent.declined if sent else 0,
                last_recorded=iso_time(sent.last_ns) if sent else "",
                licensed=wants is not None and name in wants.licensed,
            )
        )
    return rows


def want_rows(wants: Wants) -> list[Any]:
    """Datasets' "Wants": each want heard, once, as last heard, the standing
    ones kept current first (`WantHeard`)."""
    standing = set(wants.standing)
    rows: dict[str, WantHeard] = {}
    for heard in wants.heard:  # newest first: a want heard again is one row, as last heard
        if heard.want_id in rows:
            continue
        kept = heard.want_id in standing
        rows[heard.want_id] = WantHeard(
            dataset=heard.dataset,
            asked=heard.asked,
            subjects=heard.subjects,
            recorded=heard.recorded,
            declined=heard.declined,
            state="Kept current" if kept else "Withdrawn" if heard.standing else "Answered",
            want_id=heard.want_id,
            kept_current=kept,
        )
    return sorted(rows.values(), key=lambda w: w.state != "Kept current")


def mode_of(session: Session) -> str:
    """The role's mode: Live for the venue itself, Sample data for the
    package's synthetic answers and a developer's recorded ones alike."""
    return "Live" if session.mode == "live" else "Sample data"


def connection_fields(
    session: Session, venue_name: str, venue: Venue, entitled_at_vendor: str
) -> dict[str, Any]:
    """The common fields of a one-venue plugin's Connection, and its venue's
    (`VenueConnection`), from its session and the venue it resolved."""
    health = session.health
    return {
        "mode": mode_of(session),
        "credentials": [],
        "entitled_at_vendor": entitled_at_vendor,
        "limit": f"{session.limits.allowed}. This plugin: {session.limits.spent}",
        "calls": health.calls,
        "rate_limited": health.rate_limited,
        "last_call_at": iso_time(max(health.last_ok_ns, health.last_failed_ns)),
        "last_error": health.last_error,
        "venue": venue_name,
        "venue_id": venue.venue_id,
        "venue_held": venue.asked and not venue.missing,
        "healthy": health.healthy,
        "endpoints": [Endpoint(e.name, e.address, e.what) for e in session.endpoints],
        "allowed": session.limits.allowed,
        "spent": session.limits.spent,
        "failures": health.failures,
    }


def connection_figure(mode: str, healthy: bool, last_error: str) -> str | Figure:
    """The role's "Connection" figure: Sample data, Answering, or Not
    answering as an error, why the last error."""
    if mode == "Sample data":
        return "Sample data"
    if healthy:
        return "Answering"
    return Figure("", "Not answering", state="error", why=last_error[:200] or None)
