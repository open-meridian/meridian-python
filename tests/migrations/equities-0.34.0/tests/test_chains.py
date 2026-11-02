"""The chains' own work, with no deployment."""

from equities.chains import SERIES, Chains


def test_a_series_is_sent_again_only_when_its_terms_changed() -> None:
    chains = Chains(lake=None)
    assert chains.fresh("equities-1:options", [("A", "1"), ("B", "1")]) == ["A", "B"]
    assert chains.fresh("equities-1:options", [("A", "1"), ("B", "2")]) == ["B"]
    assert SERIES == "meridian.v1.ListedSeries"
