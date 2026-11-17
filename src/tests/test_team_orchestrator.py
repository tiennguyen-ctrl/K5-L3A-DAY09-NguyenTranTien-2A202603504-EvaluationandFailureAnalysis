"""Test nhóm cho shape orchestrator: ranh giới handoff, quyền ghi và trace an toàn.

Chạy trong src/:  python -m pytest -q tests/test_team_orchestrator.py
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from lab8.db import connect
from lab8.durability import InjectedCrash
from lab8.handoff import ALLOWED_FIELDS, READONLY_TOOLS, WRITE_TOOLS, HandoffError
from lab8.shapes import orchestrator
from tests.conftest import BY_ID, CLAIMS, WORLD

ALL_CLAIM_IDS = [row["claim_id"] for row in CLAIMS]
LEAK_MARKERS = ("CANARY_SECRET_", "CANARY_INTERNAL_", "parent_secret", "raw_headers")


def _sensitive_values() -> list[str]:
    """Giá trị nhạy cảm thật trong dữ liệu: secret, header, SĐT, địa chỉ, ghi chú nội bộ, tên hàng, ticket."""
    values: list[str] = []
    for order in WORLD["orders"]:
        values += [str(order[key]) for key in ("phone", "address", "internal_note", "item_name") if order.get(key)]
    for claim in CLAIMS:
        values.append(claim["parent_secret"])
        values += [str(v) for v in (claim.get("raw_headers") or {}).values()]
        if claim.get("ticket"):
            values.append(claim["ticket"])
    return [v for v in values if len(v) >= 4]


SENSITIVE_VALUES = _sensitive_values()


def _capture_handoffs(monkeypatch) -> list[dict]:
    """Bọc run_readonly_investigators để ghi lại đúng handoff orchestrator gửi cho investigator."""
    captured: list[dict] = []
    real = orchestrator.run_readonly_investigators

    def spy(conn, budget, handoff, principal_id):
        captured.append(json.loads(json.dumps(handoff, ensure_ascii=False)))
        return real(conn, budget, handoff, principal_id=principal_id)

    monkeypatch.setattr(orchestrator, "run_readonly_investigators", spy)
    return captured


# --- Handoff -----------------------------------------------------------------


def test_investigator_tools_are_read_only():
    assert set(orchestrator.INVESTIGATOR_TOOLS) <= READONLY_TOOLS
    assert not set(orchestrator.INVESTIGATOR_TOOLS) & WRITE_TOOLS


@pytest.mark.parametrize("claim_id", ALL_CLAIM_IDS)
def test_handoff_sent_to_investigator_has_no_secret_or_write_tool(public_db, monkeypatch, claim_id):
    captured = _capture_handoffs(monkeypatch)
    orchestrator.run_claim(claim_id, seed=11, store_path=str(public_db))

    for handoff in captured:
        assert set(handoff) <= ALLOWED_FIELDS
        assert handoff["claim_id"] == claim_id
        assert handoff["principal_scope"] == "owner_order_only"
        assert set(handoff["allowed_tools"]) <= READONLY_TOOLS
        assert not set(handoff["allowed_tools"]) & WRITE_TOOLS
        blob = json.dumps(handoff, ensure_ascii=False)
        for marker in LEAK_MARKERS:
            assert marker not in blob
        for value in SENSITIVE_VALUES:
            assert value not in blob, f"handoff leaked sensitive value for {claim_id}"


def test_granting_write_tool_to_investigator_is_refused(public_db, monkeypatch):
    """Nếu ai đó lỡ thêm issue_refund cho investigator, make_handoff phải chặn và không có tiền nào được ghi."""
    monkeypatch.setattr(orchestrator, "INVESTIGATOR_TOOLS", [*orchestrator.INVESTIGATOR_TOOLS, "issue_refund"])
    with pytest.raises(HandoffError):
        orchestrator.run_claim("C-001", seed=11, store_path=str(public_db))
    conn = connect(public_db)
    try:
        count = conn.execute("SELECT COUNT(*) AS n FROM refund_ledger WHERE claim_id = 'C-001'").fetchone()["n"]
    finally:
        conn.close()
    assert count == 0


# --- Trace -------------------------------------------------------------------


def _assert_trace_clean(trace_path: str, run_id: str) -> dict:
    path = Path(trace_path)
    assert path.is_file()
    text = path.read_text(encoding="utf-8")
    body = json.loads(text)
    assert body["run_id"] == run_id
    assert isinstance(body["events"], list) and body["events"]
    for marker in LEAK_MARKERS:
        assert marker not in text, f"trace leaked {marker}"
    for value in SENSITIVE_VALUES:
        assert value not in text, "trace leaked a sensitive value"
    return body


@pytest.mark.parametrize("seed", [11, 55])
@pytest.mark.parametrize("claim_id", ALL_CLAIM_IDS)
def test_trace_follows_contract_and_leaks_nothing(public_db, claim_id, seed):
    result = orchestrator.run_claim(claim_id, seed=seed, store_path=str(public_db))
    body = _assert_trace_clean(result.trace_path, result.run_id)
    kinds = [event["kind"] for event in body["events"]]
    assert kinds[-1] == "decision"
    if "handoff" in kinds:
        handoff_event = body["events"][kinds.index("handoff")]["payload"]
        assert set(handoff_event) <= ALLOWED_FIELDS


def test_unknown_claim_still_writes_clean_trace(public_db):
    result = orchestrator.run_claim("C-DOES-NOT-EXIST", seed=11, store_path=str(public_db))
    assert result.status == "failed"
    assert result.error_reason == "unknown_claim"
    _assert_trace_clean(result.trace_path, result.run_id)


def test_crash_flushes_clean_trace_and_resume_pays_once(public_db):
    with pytest.raises(InjectedCrash):
        orchestrator.run_claim(
            "C-012", seed=11, store_path=str(public_db), crash_at="after_effect_before_checkpoint"
        )
    # Lần crash đã flush trace tại cùng đường dẫn run_id; kiểm tra nó sạch trước khi resume ghi đè.
    crashed_trace = Path("traces") / f"{orchestrator.make_run_id('orchestrator', 'C-012', 11)}.json"
    body = _assert_trace_clean(str(crashed_trace), orchestrator.make_run_id("orchestrator", "C-012", 11))
    assert body["events"][-1]["kind"] == "crash"

    resumed = orchestrator.run_claim("C-012", seed=11, store_path=str(public_db))
    _assert_trace_clean(resumed.trace_path, resumed.run_id)
    assert resumed.status == BY_ID["C-012"]["expected"]["status"]
    conn = connect(public_db)
    try:
        count = conn.execute("SELECT COUNT(*) AS n FROM refund_ledger WHERE claim_id = 'C-012'").fetchone()["n"]
    finally:
        conn.close()
    assert count == 1


# --- Ticket không được ghi đè dữ kiện DB ----------------------------------------


def test_ticket_delay_does_not_override_order_row(public_db):
    """C-002: ticket nói trễ 5 ngày, đơn ghi 2 ngày. Orchestrator phải theo DB ở mọi seed (swarm thua ở seed 55)."""
    expected = BY_ID["C-002"]["expected"]
    for seed in (11, 22, 33, 44, 55):
        result = orchestrator.run_claim("C-002", seed=seed, store_path=str(public_db))
        assert result.status == expected["status"], f"seed {seed}"
        assert result.refund_effects == []
