"""M7 integrity_check beyond the public vectors: traps the starter's lab9.traps does not build.
Synthetic reports only (no shape run). Run: python -m pytest -q -m student -o addopts= -k integrity"""
import copy
import math

import pytest

pytestmark = pytest.mark.student

SPEC = {
    "eval_set_version": "v2", "seeds": [1, 2],
    "metrics": [
        {"id": "pass_rate", "kind": "capability", "blocking": True, "grader": "g",
         "threshold": {"min": 0.8, "no_significant_drop": True}},
        {"id": "secret_leak", "kind": "safety", "blocking": True, "grader": "g", "threshold": {"max": 0}},
    ],
    "slices": [{"name": "denial", "metric": "pass_rate", "min": 0.9, "no_significant_drop": True, "blocking": True}],
}
ROWS = [{"item_id": f"E-{i:03d}", "seed": s, "pass_rate": True, "secret_leak": False,
         "slices": ["denial"] if i < 2 else []} for i in range(4) for s in (1, 2)]


def report(rows=None, metrics=None, failures=()):
    return {"manifest": {"eval_set_sha": "x", "items": 4, "seeds": [1, 2]},
            "rows": copy.deepcopy(rows if rows is not None else ROWS),
            "metrics": metrics or {"pass_rate": 1.0, "secret_leak": 0},
            "evaluator_failures": list(failures)}


@pytest.fixture(scope="module")
def check():
    from lab9.gate import integrity_check

    return integrity_check


def test_honest_report_and_identical_spec_are_clean(check):
    base = report()
    assert check(base, base, SPEC, SPEC) == []


def test_duplicate_rows_replacing_failures_are_flagged(check):
    base = report()
    rows = copy.deepcopy(ROWS)
    rows[-1] = dict(rows[0])                           # same row count, but (item, seed) is duplicated
    assert check(report(rows), base, SPEC)


def test_evaluator_failure_on_a_green_run_is_flagged(check):
    base = report()
    assert check(report(failures=["E-001@1:SecretLeak:boom"]), base, SPEC)


def test_none_or_missing_row_value_is_flagged(check):
    base = report()
    rows = copy.deepcopy(ROWS)
    rows[3]["pass_rate"] = None
    assert check(report(rows), base, SPEC)
    del rows[3]["pass_rate"]
    assert check(report(rows), base, SPEC)


def test_inf_and_nan_metrics_are_flagged(check):
    base = report()
    for bad in (float("nan"), math.inf):
        assert check(report(metrics={"pass_rate": bad, "secret_leak": 0}), base, SPEC)


def test_hand_edited_metric_is_flagged(check):
    base = report()
    rows = copy.deepcopy(ROWS)
    rows[0]["pass_rate"] = False
    assert check(report(rows, {"pass_rate": 1.0, "secret_leak": 0}), base, SPEC)      # rows say 0.875
    assert check(report(rows, {"pass_rate": 0.875, "secret_leak": 0}), base, SPEC) == []


def test_relabelled_slice_is_flagged(check):
    base = report()
    rows = copy.deepcopy(ROWS)
    rows[0]["slices"] = []
    assert check(report(rows), base, SPEC)


def test_cherry_picked_seeds_are_flagged(check):
    base = report()
    rows = [r for r in ROWS if r["seed"] == 1]
    pr = report(rows)
    pr["manifest"]["seeds"] = [1]
    assert check(pr, base, SPEC)


@pytest.mark.parametrize("edit", [
    lambda s: s["metrics"][0]["threshold"].__setitem__("min", 0.5),
    lambda s: s["metrics"][0]["threshold"].pop("no_significant_drop"),
    lambda s: s["metrics"][0].__setitem__("blocking", False),
    lambda s: s["metrics"][1]["threshold"].__setitem__("max", 3),
    lambda s: s["metrics"].pop(0),
    lambda s: s["slices"][0].__setitem__("min", 0.2),
    lambda s: s["slices"][0].__setitem__("blocking", False),
    lambda s: s.__setitem__("slices", []),
    lambda s: s.__setitem__("seeds", [1]),
])
def test_every_way_of_loosening_the_spec_is_flagged(check, edit):
    base = report()
    loose = copy.deepcopy(SPEC)
    edit(loose)
    assert check(base, base, loose, SPEC)


def test_stricter_spec_and_new_eval_set_version_are_not_flagged(check):
    base = report()
    strict = copy.deepcopy(SPEC)
    strict["metrics"][0]["threshold"]["min"] = 0.95
    strict["slices"][0]["min"] = 0.95
    assert check(base, base, strict, SPEC) == []
    new_version = copy.deepcopy(SPEC)
    new_version["eval_set_version"] = "v3"
    new_version["metrics"][0]["threshold"]["min"] = 0.1      # a new version restarts the ratchet
    assert check(base, base, new_version, SPEC) == []
