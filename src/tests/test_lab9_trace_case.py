"""Regression test for docs/trace_case.md: C-002@11 under the ticket_trust bug (FM-03).

Runs the real variant shapes (MockLLM, fixed seed), so it is deterministic. It must FAIL on
`seeded_regression` and PASS on `fixed`; the first wrong step is the `model_override` event.
"""
import pytest

pytestmark = pytest.mark.student


@pytest.fixture(scope="module")
def cases():
    from lab8.shapes import SHAPES
    from lab9.trace_case import investigate

    # investigate() registers the lab9 variants into the global SHAPES; undo that afterwards so
    # Lab 8's test_public_contract (which expects exactly the four shapes) is not polluted.
    before = set(SHAPES)
    try:
        yield {shape: investigate(shape, "C-002", 11) for shape in ("seeded_regression", "fixed")}
    finally:
        for name in set(SHAPES) - before:
            del SHAPES[name]


def _ctx(case):
    from pydantic_evals.evaluators import EvaluatorContext

    return EvaluatorContext(name="t", inputs={}, metadata=None, expected_output=case["label"],
                            output=case["trial"], duration=0.0, _span_tree=None, attributes={}, metrics={})


def test_seeded_regression_first_wrong_step_is_model_override(cases):
    events = cases["seeded_regression"]["trial"]["events"]
    first_wrong = next(i for i, e in enumerate(events, 1) if e["kind"] == "model_override")
    assert first_wrong == 3
    assert events[first_wrong - 1]["payload"] == {"delay_days": 5}
    # the step right after it is the wrong quote: 20.000 instead of "no entitlement"
    assert events[first_wrong]["payload"]["amount_vnd"] == 20000


def test_graders_catch_c002_regression(cases):
    from lab9 import graders

    bad = _ctx(cases["seeded_regression"])
    assert graders.RefundAmountCorrect().evaluate(bad).value is False      # ledger 20.000 vs label 0
    assert graders.DbFactKept().evaluate(bad).value is False               # override event
    assert cases["seeded_regression"]["trial"]["lab8_pass"] is False


def test_fixed_passes_c002(cases):
    from lab9 import graders

    good = _ctx(cases["fixed"])
    assert graders.RefundAmountCorrect().evaluate(good).value is True
    assert graders.DbFactKept().evaluate(good).value is True
    assert graders.ReplyAmountMatchesLedger().evaluate(good).value is True
    assert cases["fixed"]["trial"]["lab8_pass"] is True
