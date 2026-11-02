"""The chains' own work, with no deployment."""

from meridian.suites import Recorder

from equities.lake import Lake


def test_the_chains_are_the_sdks_feed_answering_the_options_dataset() -> None:
    lake = Recorder("equities-1").bind(Lake(None))
    assert lake.chains.serves("equities-1:options")
    assert not lake.chains.serves("equities-1:live_delayed")
    assert lake.dataset("live") == "equities-1:live_delayed"
