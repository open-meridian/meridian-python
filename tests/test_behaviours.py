"""The behaviour cases every SDK runs (SDK 0.35; spec/each-role-is-one-
generated-class, section 3): this SDK's adapters pass every case, every case
has an adapter, and a case with none fails."""

from __future__ import annotations

from meridian import behaviours


def test_every_behaviour_case_passes_on_this_sdks_adapters() -> None:
    report = behaviours.run(behaviours.ADAPTERS)
    assert report.passed, report.failures
    assert len(report.passed_cases) == len(behaviours.cases())


def test_every_case_has_an_adapter_and_every_adapter_a_case() -> None:
    subjects = {case.subject for case in behaviours.cases()}
    assert subjects == set(behaviours.SUBJECTS) == set(behaviours.ADAPTERS)


def test_a_case_with_no_adapter_fails() -> None:
    report = behaviours.run({})
    assert not report.passed
    assert all(why.startswith("no adapter for ") for why in report.failures.values())


def test_an_adapter_answering_otherwise_fails_its_case() -> None:
    wrong = dict(behaviours.ADAPTERS)
    wrong["helpers.debt.to_cent"] = behaviours.value_case(lambda name, args: "1.01")
    report = behaviours.run(wrong)
    assert "a-cent-is-rounded-half-to-even" in report.failures
