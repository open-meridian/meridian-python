"""The reader's process: its reporting class, registered on one connection
(its findings done by hand: `connect-to-run`, `receive-not-rewritten`)."""

import meridian

from .declaration import DECLARATION
from .report import Report


def main() -> None:
    meridian.run(declaration=DECLARATION, roles=[Report(["INS-1", "INS-2"])])


if __name__ == "__main__":
    main()
