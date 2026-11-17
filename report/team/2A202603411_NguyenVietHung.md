# Báo cáo cá nhân — 2A202603411_NguyenVietHung

## 1. Thông tin thành viên

- Họ tên: Nguyễn Việt Hưng
- MSSV: 2A202603411
- Email: robinnguyen2004@gmail.com
- GitHub: robinnguyen2004

## 2. Phần việc phụ trách

Shape C `orchestrator` (orchestrator + investigator chỉ đọc): file `src/lab8/shapes/orchestrator.py`, test nhóm `src/tests/test_team_orchestrator.py` và mục 3.3 (Orchestrator, handoff, trace) trong `report/team/group_report.md`.

Hai ranh giới mà shape này phải giữ:

- **Ranh giới quyền:** investigator chỉ nhận 4 tool đọc (`lookup_order`, `lookup_policy`, `lookup_refund_history`, `compute_compensation`) và chạy qua `dispatch(worker=True)`. Chỉ orchestrator gọi `durability.issue_refund`.
- **Ranh giới dữ liệu:** handoff được tạo bằng `make_handoff` (allowlist trong code). Trace chỉ ghi handoff đã sanitize và các field đã lọc, không ghi ngữ cảnh gốc.

## 3. Đóng góp cụ thể

Commit chính: [1c04b12 — Update orchestrator](https://github.com/dnphuc04/K5-L3A-DAY08-DongDong-FromWorkflowsToAgents/commit/1c04b121fb71ba5aa18fff0da21cacec817b3a45)

Code đã viết trong `src/lab8/shapes/orchestrator.py`:

- Đọc claim bằng `get_claim_view`, không `SELECT *` vì claim row chứa `parent_secret` và `raw_headers`. Claim không tồn tại trả `failed`, thiếu `order_id` trả `needs_info`.
- Tạo handoff `handoff.v1` với `facts={}` và chỉ tool đọc. Không đưa ticket hay claim row vào handoff, vì ticket là dữ liệu khách tự viết, có thể sai hoặc chứa lệnh chèn.
- Gọi `run_readonly_investigators` với `principal_id` của claim. Đơn không thấy hoặc thuộc principal khác trả `escalated`.
- Lấy quote đầy đủ từ `compute_compensation` của investigator, tức là tính từ order row trong DB, không dùng `parse_delay_days(ticket)`. Quote bằng 0 trả `denied` và không gọi host.
- Quote dương thì truyền **quote đầy đủ** vào `issue_refund`, kèm `crash_at`. `InjectedCrash` được ghi vào trace, flush rồi ném lại. Host tự lo approval, trần theo đơn, trừ phần đã hoàn và idempotency.
- Mọi nhánh return đi qua hàm phụ `done()` → `common.finish()`, nên luôn có trace mới, còn `refund_effects` và `committed_audit_count` được lấy từ ledger.

Test đã viết trong `src/tests/test_team_orchestrator.py` (47 ca):

- `INVESTIGATOR_TOOLS` là tập con của `READONLY_TOOLS`, không giao với `WRITE_TOOLS`.
- Dùng `monkeypatch` bắt **handoff thật** mà orchestrator gửi cho investigator trên 14 claim public: chỉ có trường trong `ALLOWED_FIELDS`, đúng `claim_id`, scope `owner_order_only`, chỉ tool đọc, không chứa canary, secret, header, SĐT, địa chỉ, ghi chú nội bộ, tên hàng hay ticket.
- Lỡ thêm `issue_refund` cho investigator thì `make_handoff` ném `HandoffError` và ledger không có dòng nào.
- Trace của 14 claim × 2 seed (11, 55) đúng contract v1 (`run_id` khớp, `events` không rỗng, event cuối là `decision`) và không lộ giá trị nhạy cảm nào.
- Claim không tồn tại vẫn có trace hợp lệ và sạch.
- Crash ở `after_effect_before_checkpoint`: trace được flush với event cuối `crash` và vẫn sạch. Chạy lại cho đúng kết quả và ledger chỉ có 1 dòng.
- C-002 (ticket ghi trễ 5 ngày, đơn ghi 2 ngày): cả 5 seed đều theo DB, trả `denied` và không hoàn tiền.

Để chắc test bắt được lỗi thật, tôi cố tình sửa orchestrator cho ghi nguyên claim row vào trace: 29/47 test fail. Sau khi khôi phục, 47/47 pass.

Quyết định kỹ thuật:

- `facts={}`: orchestrator chưa đọc đơn nên không có dữ kiện đáng tin để chuyển tiếp. Investigator tự tra DB.
- Trace chỉ ghi `has_order_id` (bool), `order_visible`/`order_reason`, lịch sử hoàn tiền dạng số (`refund_count`, `refunded_vnd`), quote và quyết định.
- Mỗi lần chạy gọi MockLLM `complete()` một lần (`purpose="draft"`) để mô phỏng soạn phản hồi khách. Model không quyết định số tiền hay trạng thái.

Giới hạn đã biết:

- `tool_calls` là 6 với claim có đơn hợp lệ, vì orchestrator đọc `get_claim_view` một lần và `run_readonly_investigators` đọc lại một lần nữa. Lần đọc đầu cần để biết `principal_id` và `order_id` trước khi tạo handoff.
- Benchmark và crash suite của nhóm đã được Hoàng bổ sung tại `0f13675`: orchestrator đạt 70/70 trial public, cost/success mô phỏng 56.65 VND; crash suite đạt 20/20. Lần rà soát tích hợp trên Python 3.12.14 xác nhận 429 test pass và tái lập các chỉ số benchmark. Đây là kết quả nhóm, phân biệt với lần chạy cá nhân ở mục 4.

## 4. Bằng chứng

Kết quả chạy trên máy (Python 3.13.14, Windows) trong thư mục `src/`, trên code sau commit `1c04b12`:

- `python -m lab8.smoke`: `manifest 1.1 | MockLLM seeded | swarm C-001 refund 35000 | trace clean`.
- `python -m pytest -q -m student -o addopts= -k orchestrator`: 62 passed (T01–T14 trên 5 seed, T11, T12).
- `python -m pytest -q tests/test_team_orchestrator.py`: 47 passed.
- `python -m pytest -q` (cổng host + test nhóm): 126 passed, 248 deselected.
- `python -m pytest -q -m student -o addopts=` (cả 4 shape): 248 passed.

Một số lần chạy mẫu (seed 11):

| Claim | run_id | status | proposal_amount | Ledger | model_calls | tool_calls | error_reason |
| --- | --- | --- | --: | --- | --: | --: | --- |
| C-001 | `R-orchestrator-C-001-s11` | resolved | 35000 | 35000 | 1 | 6 | — |
| C-002 | `R-orchestrator-C-002-s11` | denied | 0 | — | 1 | 6 | no_entitlement |
| C-005 | `R-orchestrator-C-005-s11` | escalated | 0 | — | 1 | 5 | outside_principal_scope |
| C-013 | `R-orchestrator-C-013-s11` | denied | 35000 | — | 1 | 6 | order_already_refunded |
| C-014 | `R-orchestrator-C-014-s11` | resolved | 150000 | 120000 | 1 | 6 | — |

C-014 cho thấy shape truyền quote đầy đủ 150.000 VND, còn host trừ 30.000 VND đã hoàn trước đó và chỉ ghi 120.000 VND.

## 5. Công cụ AI đã dùng

- **Claude Code (Claude Opus 5.5)** trong VS Code: đọc repo và contract, giải thích các module host (`handoff`, `runtime`, `durability`, `trace`), viết `orchestrator.py` và `test_team_orchestrator.py`, kiểm tra ngược.
- **Cách tự kiểm tra:** chạy lại các lệnh ở mục 4; đối chiếu từng nhánh trạng thái với bảng output contract trong `docs/contracts.md`; không sửa `metrics.py`, `durability.py`, `policy.py`, `config/`, `data/`.

## 6. Tự đánh giá

- **Đã làm được:** hoàn thiện `src/lab8/shapes/orchestrator.py`, đạt 62/62 test student (gồm T11 retry và T12 crash/resume). Shape giữ được hai ranh giới mà phần việc yêu cầu: investigator chỉ có tool đọc, còn handoff và trace chỉ chứa dữ liệu đã qua allowlist. Vì quote luôn tính từ order row trong DB, orchestrator xử lý đúng C-002 ở cả 5 seed, ca mà swarm tham chiếu thua ở seed 55. Viết 47 test trong `test_team_orchestrator.py` và kiểm tra ngược: khi cố tình cho orchestrator ghi claim row vào trace, 29 ca fail. Kết quả cho thấy bộ test phát hiện được lỗi rò rỉ được chủ động đưa vào để kiểm chứng.
- **Hạn chế và hướng cải thiện:** Mỗi claim có đơn hợp lệ tốn 6 tool call vì `get_claim_view` bị đọc hai lần; chi phí đọc trùng đã được ghi nhận nhưng chưa tối ưu. Cần tự đọc kỹ thêm `durability.issue_refund` và `policy.authorize` để giải thích chắc chắn cách host áp trần theo đơn.
