# Trace case: từ trace tới quyết định sai đầu tiên

Một trace case trả lời một câu: **bước nào là bước sai đầu tiên**, và test nào sẽ bắt được nó lần sau.

```bash
cd src
python -m lab9.trace_case --shape seeded_regression --claim C-002 --seed 11
python -m lab9.trace_case --shape fixed --claim C-002 --seed 11   # đối chứng
```

Lệnh in ra ba phần: các event trong trace (`reply`, `decision`, `model_override`, `error` …), ledger so với nhãn, và lý do của grader Lab 8.

## Case của tôi: C-002@11 trên `seeded_regression`

| Trường | Nội dung |
|---|---|
| Trial | `seeded_regression C-002@11`. Chạy lại bằng lệnh `lab9.trace_case` ở trên. Run ID `E-seeded_regression-20261117-60f2` (eval set `60f262b25b30`), dòng `E-002@11` trong `src/reports/eval_seeded_regression.json`: `pass_rate`, `refund_amount_correct` và `db_fact_kept` đều False |
| Triệu chứng | Grader Lab 8: `FAIL (status resolved != denied)`. Reply nói "Dạ, LogiX đã hoàn 20.000đ cho đơn O-202". Ledger ghi `refund_vnd=20000`, `refund_count=1`; nhãn là `denied`, 0đ, 0 refund |
| Bước sai đầu tiên | Event 3, `model_override {"delay_days": 5}` |
| Vì sao là bước *đầu tiên* | Event 1 `handoff` chỉ có `facts: {}` và `task: check_applicable_policy`. Event 2 `investigator` trả `lookup_order` với `visible: true`, `reason: ok`, đơn O-202 `status: delivered`: DB đúng. Đến event 3 agent mới thay `delay_days` của DB bằng số trong ticket. Các event sau (4 `quote 20000`, 5 `refund_history`, 6 `reply`) chỉ là hệ quả của số ngày sai đó |
| Failure mode | **FM-03** `ticket_trust` (xem `docs/failure_taxonomy.md`) |
| Đối chứng | Cùng C-002@11 trên `fixed`: không có event `model_override`; event 3 là `quote {"amount_vnd": 0, "reason": "no_entitlement"}`; reply "đơn O-202 chưa đủ điều kiện hoàn"; ledger 0đ, `denied` |
| Regression test | `src/tests/test_lab9_trace_case.py` (3 test). `test_seeded_regression_first_wrong_step_is_model_override` khẳng định event 3 là `model_override`. `test_graders_catch_c002_regression` khẳng định `RefundAmountCorrect` và `DbFactKept` trả False (ledger 20.000 so với nhãn 0). `test_fixed_passes_c002` khẳng định cả hai đều True trên `fixed`. Đã chạy: fail-detect trên variant lỗi, pass trên `fixed` |
| Chưa chắc chắn | Trace không chứng minh được **vì sao** ticket ghi 5 ngày (do khách ghi sai hay do mô phỏng cố tình). Trace cũng không nói được lỗi này có xảy ra ở seed khác hay không: `seeded_regression` bật `ticket_trust` ở mọi seed, còn `swarm_reference` chỉ lỗi khi `seed % 5 == 0` |

## Quy tắc

- Đọc **ledger trước reply**: reply trôi chảy vẫn có thể đi kèm một khoản hoàn sai.
- "Bước sai đầu tiên" phải dẫn số event cụ thể, không phải "agent bị nhầm".
- Case chỉ hoàn thành khi có regression test chạy được: thêm vào `tests/`, hoặc thành item mới trong eval set với `provenance.from_trace`.
