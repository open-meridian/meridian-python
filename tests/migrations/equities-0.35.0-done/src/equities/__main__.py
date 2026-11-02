"""The plugin's process: its data class registered on one connection, its
loops the class's own `run()`, restarted by `meridian.run` (its findings done
by hand: `connect-to-run`, and `helper-adopted` for `again`, `licences` and
`timetable`)."""

import meridian

from .declaration import DECLARATION
from .lake import Lake


def main() -> None:
    meridian.run(declaration=DECLARATION, roles=[Lake(None)])


if __name__ == "__main__":
    main()
