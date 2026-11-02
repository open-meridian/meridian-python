"""The broker's one page: the accounts a deployment admin may link to."""

from __future__ import annotations

import meridian

pages = meridian.Pages("Broker")


@pages.page("/accounts", "Accounts", levels="admin", roles="custody")
async def accounts(request: meridian.Request) -> str:
    granted = await request.plugin.read_accounts_for_linking(acting_for=request.caller.header)
    return ", ".join(each.account_id for each in granted.accounts)

# ── The roles' common pages (spec/plugin-pages-follow-their-role) ────────

from meridian.roles import custody, data  # noqa: E402


@pages.page(
    "/", "Connection", levels="admin", answers=data.ConnectionRead, name="read_connection",
    roles="data",
)  # fmt: skip
async def connection(request: meridian.Request) -> meridian.Response:
    return pages.answer("meridian/roles/data/connection.html", data.ConnectionRead(mode="Live"))


@pages.page(
    "/datasets", "Datasets", levels="admin", answers=data.DatasetsRead, name="read_datasets",
    roles="data",
)  # fmt: skip
async def datasets(request: meridian.Request) -> meridian.Response:
    return pages.answer("meridian/roles/data/datasets.html", data.DatasetsRead())


class Source:
    """What the broker's sync holds, as the custody pages read it."""

    vendor = "Broker"
    credential = "key"

    def reached(self) -> list[str]:
        return ["BRK-1"]

    def account(self, number: str) -> custody.ExternalAccountRead:
        return custody.ExternalAccountRead(number, "Margin")

    def custodian(self) -> str:
        return "Broker"

    def account_type(self, number: str) -> str:
        return "Margin"

    def statement(self, number: str) -> tuple[str, str] | None:
        return None

    def activities(self, number: str) -> list[tuple[object, str]]:
        return []

    def links(self) -> list[object]:
        return []


custody.account_pages(pages, Source, what="the broker's statements and activities")
