"""The plugin's datasets, as 0.34.0 declared them: its licence states no
redistribution."""

import meridian

LIVE = meridian.DatasetDeclaration(
    key="live",
    vendor="Equities",
    data_types=["meridian.v1.Price", "meridian.v1.Quote"],
    modes=["pull", "stream"],
    licence_default=meridian.DatasetLicence(kept=True, derived_use_terms="internal_only"),
    day_time_zone="America/New_York",
    day_end_minute=960,
)

DECLARATION = meridian.Declaration(catalogue=[LIVE])
