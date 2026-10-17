"""A connectivity plugin's common logic (0.30.0; sdk-contract/the-sdk-carries-
each-roles-common-logic, ruled 2026-10-13; ruling 206): what every
connectivity plugin must do the same to place an order at most once, say
what became of it and report its fills, whatever its venue and however it
reaches it -- an API, FIX, anything. The plugin supplies its broker's client
and an adapter reading the broker's words into this module's (`Venue`);
nothing here speaks to a venue.

**The bookkeeping** (`Sent`, `place_once`, `resolve_unanswered`,
`report_status_not_mapped`, `execution_id`, `bust_id`, `fill_price`,
`filled_in_book`): a placement noted in storage before it is sent and never
sent twice; an unknown outcome resolved from the venue's orders by the tag it
was sent with, never by sending again; a status not mapped said as reported;
a fill's derived ID, the same however often it is read; a bust's; a fill's
price from two averages; what the book holds filled.

**The whole work** (`Trader`, over a `Venue`): placements heard and sent,
held under a pause or a stop and cancelled under a stop, rejected
`unsupported` where the account or its catalogue does not offer them, their
cancels and replaces, the venue's statuses reported in the contract's
meanings, fills and busts into the book with their settlement dates, the
venue's catalogue published, and fills of orders placed outside the platform
reported on no placement (`Watched`). The values the adapter speaks in:
`Asked`, `Change`, `VenueOrder`, `Fill`, the status categories (`WORKING`,
`FILLED`, `CANCELLED`, `REJECTED`, `EXPIRED`, `SUSPENDED`, `DONE_FOR_DAY`,
`REPLACED`), `VenueRefused` and `VenueUnanswered`; `number` (one function
with `meridian.roles.data.number`) and `moment` read a broker's figures and
times.

**The Trading page** (`TradingRead`, `AccountTrading`, `TradingAsked`,
`TradingEnabled`, `trading_read`, the template
`meridian/roles/connectivity/trading.html`): each credential set or not, the
environment, each account read-only or with trading enabled, and the
placements working, held back or of unknown outcome; counts and codes only.

**A plugin's tests** (`meridian.roles.connectivity.testing`): `Rig`, the
Trader over the suites' recorder and the plugin's own adapter on its fake
broker, and the book's messages as a test builds them. Fakes only.
"""

from ..._numbers import number
from ._bookkeeping import (
    Placed,
    Sent,
    VenueRefused,
    VenueUnanswered,
    bust_id,
    execution_id,
    fill_price,
    filled_in_book,
    place_once,
    report_status_not_mapped,
    resolve_unanswered,
)
from ._pages import AccountTrading, TradingAsked, TradingEnabled, TradingRead, trading_read
from ._trader import (
    CANCELLED,
    DONE_FOR_DAY,
    EXPIRED,
    FILLED,
    PRICE_PLACES,
    REJECTED,
    REPLACED,
    SUSPENDED,
    WORKING,
    Asked,
    Catalogue,
    Change,
    Fill,
    Originated,
    Shown,
    Trader,
    Venue,
    VenueOrder,
    Watched,
    Worked,
    basis_of,
    moment,
    symbol_of,
    trading_files,
)

__all__ = [
    "AccountTrading",
    "TradingAsked",
    "TradingEnabled",
    "TradingRead",
    "trading_read",
    "CANCELLED",
    "DONE_FOR_DAY",
    "EXPIRED",
    "FILLED",
    "PRICE_PLACES",
    "REJECTED",
    "REPLACED",
    "SUSPENDED",
    "WORKING",
    "Asked",
    "Catalogue",
    "Change",
    "Fill",
    "Originated",
    "Placed",
    "Sent",
    "Shown",
    "Trader",
    "Venue",
    "VenueOrder",
    "VenueRefused",
    "VenueUnanswered",
    "Watched",
    "Worked",
    "basis_of",
    "bust_id",
    "execution_id",
    "fill_price",
    "filled_in_book",
    "moment",
    "number",
    "place_once",
    "report_status_not_mapped",
    "resolve_unanswered",
    "symbol_of",
    "trading_files",
]
