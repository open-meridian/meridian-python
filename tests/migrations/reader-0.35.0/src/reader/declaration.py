"""What the plugin declares: its settings and its documentation."""

import meridian
from meridian.roles import reporting


@meridian.settings
class Settings:
    """The reporting role's common setting."""

    reporting_currency: str = reporting.reporting_currency()


DECLARATION = meridian.Declaration(settings=Settings, documentation="docs")
