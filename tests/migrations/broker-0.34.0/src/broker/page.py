"""The broker's one page: the accounts a deployment admin may link to."""

from __future__ import annotations

import meridian

pages = meridian.Pages("Broker")


@pages.page("/", "Accounts", levels="admin", roles="custody")
async def accounts(request: meridian.Request) -> str:
    granted = await request.plugin.read_accounts_for_linking(acting_for=request.caller.header)
    return ", ".join(each.account_id for each in granted.accounts)
