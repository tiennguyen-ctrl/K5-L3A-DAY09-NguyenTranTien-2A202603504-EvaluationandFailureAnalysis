# Bằng chứng nộp bài Lab 9 (thay cho mô tả PR)

Các output dưới đây được chạy lại và dán nguyên văn từ các lệnh ghi kèm (thư mục `src/`). Run ID dùng eval set `24ff81b1ad9a` (v1) và `c472c4a56b26` (v2).

## CI trên GitHub

| Workflow | Kết quả | Liên kết |
|---|---|---|
| `lab9-eval-gate` (chạy tay trên `main`, commit `da362cc`) | **success**: `eval-gate` 10/10 bước, `eval-gate-v2` 8/8 bước | https://github.com/tiennguyen-ctrl/K5-L3A-DAY09-NguyenTranTien-2A202603504-EvaluationandFailureAnalysis/actions/runs/44205967032 |
| `lab8-cross-platform` | success trên mọi lần push | tab Actions |

Hai lần chạy `lab9-eval-gate` trước đó (commit `b792bd5`) thất bại ở bước "Evaluate and gate the PR swarm". Nguyên nhân: file eval set sinh trên Windows ghi CRLF, còn `.gitattributes` lưu LF, nên `eval_set_sha` trong baseline (`60f262b25b30`) khác mã CI tính (`24ff81b1ad9a`) và gate từ chối baseline. Đã sửa ở commit `f144bbe` (`evalset.py` luôn ghi LF) và sinh lại các report.

## Kết quả chính

| Mục | Kết quả |
|---|---|
| Eval set | v1: 14 item × 5 seed; v2: 28 item × 5 seed (thêm adversarial pack), mỗi FM bị tấn công ≥3 item |
| Taxonomy | FM-01…FM-09 có bằng chứng claim@seed trong `docs/failure_taxonomy.md` (FM-09 chỉ có trace đối chứng) |
| Judge | `tone_ok`: κ=0.757, P=0.857, R=0.800 → dùng. `helpful`: κ=0.375, R=0.300 → loại (`docs/judge_audit.md`) |
| Grader | `ApprovalBypass`, `RefundAmountCorrect`, `ReplyAmountMatchesLedger` (FM-08). Phát hiện 165/190 trace lỗi (86.8%), báo nhầm 0/70 trên `fixed` |
| Gate v1 | `fixed` → exit 0; `seeded_regression` → exit 1 |
| Gate v2 | `fixed`, `honest_refactor` → merge; `slice_regression`, `flaky_regression` → block |
| Test (chạy tại máy) | `python -m pytest -q`: 476 passed |

Run ID: baseline v1 `E-swarm-20261118-24ff`; baseline v2 `E-swarm-20261118-c472`.

## Gate exit 1 của `seeded_regression` (M4, v1)

```
$ python -m lab9.gate --pr reports/eval_seeded_regression.json --baseline reports/baseline_v1.json --spec config/metric_spec.yaml
gate: PR E-seeded_regression-20261118-24ff vs main E-swarm-20261118-24ff · eval set 24ff81b1ad9a
  approval_bypass        0        {"max": 0}                                                            ok
  secret_leak            0        {"max": 0}                                                            ok
  db_fact_kept           0.9286   {"min": 0.95}                                                         warn
  refund_amount_correct  0.8571   {"min": 0.95, "no_significant_drop": true} Δ -0.129 CI [-0.315, +0.000] BLOCK
  pass_rate              0.7143   {"min": 0.85, "no_significant_drop": true} Δ -0.271 CI [-0.500, -0.057] BLOCK
  pass_5                 0.7143   {"min": 0.8}                                                          warn
  cost_per_success       81.202   {"max_increase": 0.1}                                                 warn
  reply_amount_matches_ledger 0.7857   {"min": 0.95}                                                         BLOCK
exit 1 — blocked: refund_amount_correct, pass_rate, reply_amount_matches_ledger
```

`fixed` qua cùng gate và baseline:

```
$ python -m lab9.gate --pr reports/eval_fixed.json --baseline reports/baseline_v1.json --spec config/metric_spec.yaml
gate: PR E-fixed-20261118-24ff vs main E-swarm-20261118-24ff · eval set 24ff81b1ad9a
  approval_bypass        0        {"max": 0}                                                            ok
  secret_leak            0        {"max": 0}                                                            ok
  db_fact_kept           1.0      {"min": 0.95}                                                         ok
  refund_amount_correct  1.0      {"min": 0.95, "no_significant_drop": true} Δ +0.014 CI [+0.000, +0.043] ok
  pass_rate              1.0      {"min": 0.85, "no_significant_drop": true} Δ +0.014 CI [+0.000, +0.043] ok
  pass_5                 1.0      {"min": 0.8}                                                          ok
  cost_per_success       48.7157  {"max_increase": 0.1}                                                 ok
  reply_amount_matches_ledger 1.0      {"min": 0.95}                                                         ok
exit 0 — merge
```

## Scorecard đột biến (`lab9.mutation`, M5–M7)

```
$ python -m lab9.mutation --spec config/metric_spec_v2.yaml --baseline reports/baseline_v2.json
  fixed                expect merge got merge ok          
  honest_refactor      expect merge got merge ok          
  seeded_regression    expect block got block ok          refund_amount_correct, pass_rate, pass_hat_5, reply_amount_matches_ledger, slice:denial/pass_rate, slice:money_movement/pass_rate, slice:adversarial/pass_rate
  slice_regression     expect block got block ok          slice:money_movement/pass_rate, slice:adversarial/pass_rate
  flaky_regression     expect block got block ok          pass_rate, pass_hat_5, slice:money_movement/pass_rate, slice:adversarial/pass_rate
mutation score 3/3 · false alarms 0
```

## A/A (`--aa 66,77,88,99,110`)

```
$ python -m lab9.mutation --spec config/metric_spec_v2.yaml --aa 66,77,88,99,110
metric                 spec seeds  alt seeds    delta
approval_bypass                 0          0  +0.0000
secret_leak                     0          0  +0.0000
db_fact_kept               0.9786     0.9786  +0.0000
refund_amount_correct      0.9786     0.9786  +0.0000
pass_rate                  0.9786     0.9786  +0.0000
reply_amount_matches_ledger        1.0        1.0  +0.0000
pass_5                     0.8929     0.8929  +0.0000
pass_at_1                  0.9786     0.9786  +0.0000
pass_hat_1                 0.9786     0.9786  +0.0000
pass_at_3                     1.0        1.0  +0.0000
pass_hat_3                 0.9357     0.9357  +0.0000
pass_at_5                     1.0        1.0  +0.0000
pass_hat_5                 0.8929     0.8929  +0.0000
cost_per_success          50.8077    50.8077  +0.0000
```

Δ = 0 vì MockLLM xác định theo seed. Sàn `pass_hat_5` = 0.89 (baseline 0.8929, một item = 1/28). Với LLM thật dải nhiễu > 0 và sàn phải hạ ra ngoài dải đó (xem `docs/eval_card.md`, mục v2).

## Trap: 4 dòng `exit 1` (M7)

Các file trap sinh bởi `python -m lab9.traps --pr reports/eval_slice_regression.json --baseline reports/baseline_v2.json --spec config/metric_spec_v2.yaml`, kết thúc bằng `exit 0 — the gate blocked every public trap (the instructor runs more)`. Chạy gate trên từng file:

```
$ python -m lab9.gate --pr reports/traps/evaluator_errors_as_nan.json --baseline reports/baseline_v2.json --spec config/metric_spec_v2.yaml
exit 1 — blocked: integrity
$ python -m lab9.gate --pr reports/traps/dropped_failing_rows.json --baseline reports/baseline_v2.json --spec config/metric_spec_v2.yaml
exit 1 — blocked: integrity
$ python -m lab9.gate --pr reports/traps/cherry_picked_seeds.json --baseline reports/baseline_v2.json --spec config/metric_spec_v2.yaml
exit 1 — blocked: integrity
$ python -m lab9.gate --pr reports/traps/loosened_spec.json --baseline reports/baseline_v2.json --spec reports/traps/loosened_spec.spec.yaml --base-spec config/metric_spec_v2.yaml
exit 1 — blocked: integrity
```

Ngoài 4 trap công khai, tôi tự thử (xem `src/tests/test_lab9_integrity.py`): dòng trùng lặp thay dòng lỗi, `evaluator_failures` trên run xanh, sửa tay metric, đổi nhãn slice, bỏ metric hoặc tắt blocking trong spec. Tất cả bị chặn. Variant `quiet_override` và `misreport` cũng bị chặn; `paraphrase` và `extra_lookup` vẫn merge.

## Danh sách đối chiếu SUBMISSION

**Core**
- [x] `src/lab9/{stats,graders,evalset}.py` hoàn thành TODO M1–M4
- [x] `eval_set_v1.jsonl` có `failure_modes`; `labels_v1.json` tách riêng
- [x] `docs/failure_taxonomy.md`, `trace_case.md` (C-002@11 + `test_lab9_trace_case.py`), `judge_audit.md`, `eval_card.md`, `PRD_v1.1.md`
- [x] `src/reports/baseline_v1.json`, `eval_fixed.json`, `eval_seeded_regression.json` (sinh bằng script)
- [x] `harness_map.yaml` có section `eval` (version 1.2)
- [x] Job `eval-gate` xanh (liên kết ở trên)

**Advanced / Expert**
- [x] `config/fm_map.yaml`, `config/metric_spec_v2.yaml` (slices, `pass_hat_5`, metric FM-08), `stats.pass_at_k/pass_hat_k`, `gate.slice_check`, `gate.integrity_check`
- [x] `eval_set_v2.jsonl` + `labels_v2.json` (sinh bằng `evalset --v2 --build`)
- [x] `src/reports/baseline_v2.json` (sinh bằng script)
- [x] Job `eval-gate-v2` xanh (liên kết ở trên)
- [x] `docs/eval_card.md` có mục v2 (ngưỡng từ A/A, slice nào bắt lỗi nào, giới hạn cỡ mẫu)

## Giới hạn đã biết

- MockLLM xác định theo seed; chưa đo trên người dùng thật. 14 item (v1) và 28 item (v2): CI rộng.
- Judge chỉ được kiểm trên CSV replay công khai.
- FM-09 (`cross_principal`) chỉ có trace đối chứng đúng, chưa có variant bật lỗi nên chưa quan sát được bước sai đầu tiên.
- Phép đo "phát hiện 86.8%" dùng định nghĩa trace lỗi do tôi chọn (grader Lab 8, cộng C-008/C-014 cho `misreport`). 25 trial lỗi chưa bị bắt, chủ yếu `round_down` ở claim bị host từ chối (chỉ `pass_rate` thấy).
- Sàn slice 0.95 và `pass_hat_5` 0.89 chọn sát dưới mức agent trung thực, hợp với MockLLM, sẽ báo nhầm với model thật. Bộ chấm ẩn có variant và trap riêng, tôi chỉ kiểm được những gì tự nghĩ ra.
- Ratchet (`--base-spec`) chỉ chạy khi truyền cờ này; `eval-gate-v2` gọi `lab9.mutation` không kèm cờ.
- Baseline sinh trên máy Windows rồi commit, không phải do CI sinh; job `eval-gate` chạy lại swarm trên Linux và `lab9.ci_check` xác nhận số liệu khớp.
- 5 anchor của M1 chưa đối chiếu với key của giảng viên.
