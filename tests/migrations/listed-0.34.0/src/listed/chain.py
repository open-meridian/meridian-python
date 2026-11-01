"""A chain's series, named by their OSI symbols."""

from meridian.helpers import chains
from meridian.roles import Latency  # the role's recorder and the chain's helpers

LATENCY = Latency


def symbols(root: str, expiration: str, strikes: list[str]) -> list[str]:
    return [chains.osi_symbol(root, expiration, "call", strike) for strike in strikes]
