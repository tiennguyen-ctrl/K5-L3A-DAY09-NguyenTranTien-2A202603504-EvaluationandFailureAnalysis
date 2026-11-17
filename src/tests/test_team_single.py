"""Team tests for shape B (single ReAct agent).

Two boundaries matter here:
1. The loop is bounded: it stops at 8 steps and cannot spin forever.
2. The model can only pick read tools. Writing a refund stays with the host.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from lab8 import runtime
from lab8.db import connect
from lab8.handoff import READONLY_TOOLS, WRITE_TOOLS
from lab8.schemas import Budget
from lab8.shapes import single
from tests.conftest import CLAIMS


def _ledger_rows(store: Path, claim_id: str) -> int:
    conn = connect(store)
    try:
        return conn.execute(
            "SELECT COUNT(*) AS n FROM refund_ledger WHERE claim_id = ?", (claim_id,)
        ).fetchone()["n"]
    finally:
        conn.close()


def test_react_loop_stops_at_eight_steps(public_db):
    """A model that never returns `final` is cut off at exactly 8 tool steps."""
    conn = connect(public_db)
    try:
        budget = Budget()
        calls = {"n": 0}

        def never_final(_seen):
            calls["n"] += 1
            return {"tool": "lookup_policy", "args": {}}

        result = runtime.run_react(
            conn, budget, observation={"claim": {"claim_id": "C-001"}}, decide=never_final, max_steps=8
        )
    finally:
        conn.close()

    assert result["stopped"] == "step_cap"
    assert result["final"]["error_reason"] == "step_cap"
    assert calls["n"] == 8
    assert budget.tool_calls == 8


@pytest.mark.parametrize("claim", CLAIMS, ids=[c["claim_id"] for c in CLAIMS])
def test_single_never_exceeds_eight_loop_steps(tmp_path, claim):
    """On every public claim the single shape finishes inside the 8-step cap."""
    from lab8.db import init_store
    from tests.conftest import WORLD

    store = tmp_path / "s.sqlite"
    init_store(store, WORLD, CLAIMS).close()
    result = single.run_claim(claim["claim_id"], seed=11, store_path=str(store))

    assert result.status != "failed" or result.error_reason != "step_cap"
    # model calls inside the loop never exceed the cap (one extra draft call is outside it)
    assert result.model_calls <= 8 + 1


@pytest.mark.parametrize("tool", sorted(WRITE_TOOLS))
def test_model_cannot_pick_a_write_tool(public_db, tool):
    """If decide asks for a write tool the loop rejects it and nothing is written."""
    conn = connect(public_db)
    try:

        def wants_to_write(_seen):
            return {"tool": tool, "args": {"claim_id": "C-001", "amount_vnd": 35000}}

        with pytest.raises(runtime.ToolRejected):
            runtime.run_react(
                conn, Budget(), observation={"claim": {"claim_id": "C-001"}}, decide=wants_to_write
            )
    finally:
        conn.close()

    assert _ledger_rows(public_db, "C-001") == 0


def test_single_only_ever_calls_read_tools(public_db, monkeypatch):
    """Record every tool the single shape dispatches: all must be read-only."""
    seen_tools: list[str] = []
    real_dispatch = runtime.dispatch

    def recording_dispatch(conn, budget, name, args, *, worker):
        seen_tools.append(name)
        return real_dispatch(conn, budget, name, args, worker=worker)

    monkeypatch.setattr(runtime, "dispatch", recording_dispatch)
    monkeypatch.setattr(single, "dispatch", recording_dispatch)

    result = single.run_claim("C-001", seed=11, store_path=str(public_db))

    assert result.status == "resolved"
    assert seen_tools, "single should have called at least one tool"
    assert set(seen_tools) <= READONLY_TOOLS
    assert not set(seen_tools) & WRITE_TOOLS
    # the refund itself came from the host, not from a model-chosen tool
    assert _ledger_rows(public_db, "C-001") == 1


def test_single_trace_has_no_secret_or_raw_rows(public_db):
    """The trace is a security boundary: no canary secret, phone or address."""
    result = single.run_claim("C-001", seed=11, store_path=str(public_db))
    body = Path(result.trace_path).read_text(encoding="utf-8")
    data = json.loads(body)

    assert data["run_id"] == result.run_id
    assert isinstance(data["events"], list)
    assert "CANARY_SECRET" not in body
    for field in ("phone", "address", "internal_note", "item_name", "parent_secret"):
        assert field not in body
