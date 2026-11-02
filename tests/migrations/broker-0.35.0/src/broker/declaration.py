"""What the plugin declares: its daily dataset and its documentation."""

import meridian

#: The broker's daily closes, pulled when the lake wants them.
DAILY = meridian.DatasetDeclaration(
    key="daily",
    vendor="Broker",
    data_types=["meridian.v1.Price"],
    modes=["pull"],
    day_time_zone="America/New_York",
    day_end_minute=960,
)

DECLARATION = meridian.Declaration(catalogue=[DAILY], documentation="docs")
