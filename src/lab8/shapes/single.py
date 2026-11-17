"""Shape B — one ReAct agent. Student work.

Use `lab8.runtime.run_react` with max_steps=8. `decide` may pick a read tool.
It must not call `issue_refund`. After the loop, the host validates the quote
and is the only writer.

A decide() that trusts ticket text over the order row will fail hidden claims
where the customer overstates the delay or cites a superseded clause.

Per-order cap: an order may already have been refunded by an earlier claim.
The read tool `lookup_refund_history` shows how much. The host still enforces
the cap, so pass the full quote to `durability.issue_refund`, not a net amount.

Caps: stop at 8 steps. Count model calls in the Budget so cost stays comparable.

Trace contract v1 (docs/contracts.md): return a trace_path to a JSON file written in this run,
{"run_id": <same run_id>, "events": [...]}, on every return path including early
ones. `lab8.trace.Trace` does this; your own tracer is fine if it matches.

Design notes (this implementation)
----------------------------------
* The model (`decide`) only picks read tools: lookup_order, then
  compute_compensation. The ticket text is never parsed for numbers; the delay
  always comes from the order row, so an overstated or injected ticket cannot
  change the quote.
* Money is computed by `compute_compensation` (code), never by MockLLM.
* After the loop the shape calls `durability.issue_refund` with the FULL quote.
  The host applies approval, the per-order cap and idempotency.
* `lookup_refund_history` is not called: the host already subtracts earlier
  refunds on the order, so reading it would only add cost without changing the
  outcome.
* Only allowlisted fields are written to the trace (no claim row, no raw order row).
"""

from __future__ import annotations

import sqlite3
from typing import Any

from lab8.db import connect
from lab8.durability import InjectedCrash, issue_refund
from lab8.mock_llm import complete
from lab8.runtime import dispatch, run_react
from lab8.schemas import Budget, RunResult, make_run_id
from lab8.shapes.common import finish, safe_dump
from lab8.trace import Trace

SHAPE = "single"
MAX_STEPS = 8


def run_claim(
    claim_id: str,
    *,
    seed: int,
    store_path: str,
    crash_at: str | None = None,
) -> RunResult:
    conn = connect(store_path)
    try:
        return _run(conn, claim_id, seed=seed, crash_at=crash_at)
    finally:
        conn.close()


def _run(conn: sqlite3.Connection, claim_id: str, *, seed: int, crash_at: str | None) -> RunResult:
    budget = Budget()
    trace = Trace(make_run_id(SHAPE, claim_id, seed))

    def done(status: str, proposal: int = 0, reason: str | None = None) -> RunResult:
        return finish(
            conn,
            shape=SHAPE,
            claim_id=claim_id,
            seed=seed,
            status=status,
            proposal_amount=proposal,
            budget=budget,
            trace=trace,
            error_reason=reason,
        )

    claim = dispatch(conn, budget, "get_claim_view", {"claim_id": claim_id}, worker=False)
    if not claim.get("found"):
        trace.add("error", {"reason": "unknown_claim"})
        return done("failed", reason="unknown_claim")
    # Allowlisted view only: no ticket text, no secrets.
    view = {k: claim.get(k) for k in ("claim_id", "principal_id", "order_id")}
    trace.add("claim", {"claim_id": claim_id, "has_order_id": bool(view["order_id"])})

    state: dict[str, Any] = {"order_view": None, "quote": None}

    def decide(seen: dict[str, Any]) -> dict[str, Any]:
        """One model call per step. Picks a read tool or returns the final decision."""
        last = seen.get("last_tool")
        complete(budget, seed=seed, purpose="react", prompt=f"step after {last or 'start'}")
        if last is None:
            if not view["order_id"]:
                return {"final": {"status": "needs_info", "error_reason": "missing_order_id"}}
            return {
                "tool": "lookup_order",
                "args": {"order_id": view["order_id"], "principal_id": view["principal_id"]},
            }
        if last == "lookup_order":
            order_view = seen["last_result"]
            state["order_view"] = order_view
            if not order_view.get("visible"):
                trace.add("observation", {"lookup_order": {"visible": False, "reason": order_view.get("reason")}})
                return {"final": {"status": "escalated", "error_reason": order_view.get("reason")}}
            trace.add("observation", {"lookup_order": safe_dump(order_view)})
            return {"tool": "compute_compensation", "args": {"order": order_view["order"]}}
        if last == "compute_compensation":
            state["quote"] = seen["last_result"]
            trace.add("quote", safe_dump(state["quote"]))
            return {"final": {"status": "quoted"}}
        return {"final": {"status": "failed", "error_reason": "unexpected_tool"}}

    try:
        loop = run_react(
            conn,
            budget,
            observation={"claim": view},
            decide=decide,
            max_steps=MAX_STEPS,
            worker=False,
        )
    except Exception as exc:  # a tool error must not escape run_claim
        trace.add("error", {"reason": "react_error", "type": type(exc).__name__})
        return done("failed", reason="react_error")

    trace.add("loop", {"stopped": loop["stopped"], "steps": budget.steps})
    if loop["stopped"] != "final":
        return done("failed", reason="step_cap")

    final = loop["final"]
    status = final.get("status")
    if status in ("needs_info", "escalated", "failed"):
        complete(budget, seed=seed, purpose="draft", prompt=status)
        trace.add("decision", {"status": status})
        return done(status, reason=final.get("error_reason"))

    quote = state["quote"] or {}
    proposal = int(quote.get("amount_vnd", 0))
    complete(budget, seed=seed, purpose="draft", prompt=f"proposal={proposal}")
    if proposal <= 0:
        trace.add("decision", {"status": "denied", "reason": quote.get("reason")})
        return done("denied", reason=quote.get("reason"))

    # Host is the only writer. Pass the FULL quote; the host subtracts prior refunds.
    try:
        outcome = issue_refund(conn, claim_id, proposal, crash_at=crash_at)
    except InjectedCrash:
        trace.add("crash", {"at": crash_at})
        trace.write()
        raise

    trace.add("host", {"ok": outcome["ok"], "reason": outcome["reason"], "conflict": outcome["conflict"]})
    if not outcome["ok"]:
        return done("failed" if outcome["conflict"] else "denied", proposal, outcome["reason"])
    return done("resolved", proposal)
