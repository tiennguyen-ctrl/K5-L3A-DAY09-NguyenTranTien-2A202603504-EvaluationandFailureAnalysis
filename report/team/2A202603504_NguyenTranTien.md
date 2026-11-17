# Báo cáo cá nhân — 2A202603504_NguyenTranTien

## 1. Thông tin thành viên

- Họ tên: Nguyễn Trần Tiến
- MSSV: 2A202603504
- Email: nguyentien2004abc@gmail.com
- GitHub: tiennguyen-ctrl

## 2. Phần việc phụ trách

Shape B `single` (một agent ReAct): file `src/lab8/shapes/single.py`, cùng test nhóm `src/tests/test_team_single.py` và phần Single (ranh giới code/model) trong mục 3 của `group_report.md`.

Ranh giới code và model trong shape này:

- **Chọn tool:** `decide` hiện là chính sách cố định, chọn `lookup_order` rồi `compute_compensation`; mỗi bước ghi nhận một lời gọi MockLLM vào `Budget`. Model không sinh quyết định tool động trong triển khai này.
- **Code** quyết trạng thái và thao tác ghi tiền: số tiền do `compute_compensation` tính, trạng thái (`needs_info`, `escalated`, `denied`, `resolved`, `failed`), và việc ghi refund. Ghi refund chỉ đi qua `durability.issue_refund`, `runtime.dispatch` từ chối tool ghi.
- Số ngày trễ luôn lấy từ order row, không đọc số trong ticket, nên ticket nói quá hoặc chèn lệnh không đổi được quote.

## 3. Đóng góp cụ thể

Commit chính: [2849887 — feat(single): implement ReAct single-agent shape with team tests](https://github.com/dnphuc04/K5-L3A-DAY08-DongDong-FromWorkflowsToAgents/commit/2849887c98cb43ccb5ecee4666855c8902785bf1).

Code và test đã viết:

- `src/lab8/shapes/single.py`: thay stub `not_implemented` bằng vòng `run_react(max_steps=8)`.
  - Có claim, có `order_id`, đơn thuộc đúng principal thì mới tính quote. Thiếu `order_id` trả `needs_info`, không thấy đơn hoặc sai principal trả `escalated`, quote bằng 0 trả `denied` và không gọi `issue_refund`.
  - Quote lớn hơn 0 thì gọi `durability.issue_refund` với **quote đầy đủ**. Host tự trừ phần đã hoàn trước đó, shape không trừ thêm.
  - Truyền `crash_at` vào `issue_refund`. `InjectedCrash` chỉ được ghi vào trace rồi ném lại, không bị nuốt.
  - Mọi nhánh return đi qua `finish()` nên `refund_effects` và `committed_audit_count` lấy từ ledger.
  - Trace chỉ ghi field đã qua allowlist (`claim_id`, có `order_id` hay không, order view đã lọc field, quote). Không ghi ticket, claim row hay order row thô.
- `src/tests/test_team_single.py` (19 test):
  - vòng lặp dừng đúng ở 8 bước khi model không bao giờ `final`;
  - `single` không chạm trần 8 bước trên 14 claim public;
  - `decide` chọn `issue_refund` hoặc `append_audit` thì bị `ToolRejected` và ledger không có dòng nào;
  - mọi tool mà `single` gọi đều là tool đọc, refund ở C-001 do host ghi;
  - trace đúng contract và không chứa `CANARY_SECRET`, SĐT, địa chỉ, ghi chú nội bộ, tên hàng.

Quyết định kỹ thuật:

- Không gọi `lookup_refund_history`: host đã tự trừ phần đã hoàn theo đơn (T13, T14), gọi thêm chỉ tốn chi phí mà không đổi kết quả.
- Dùng MockLLM `complete()` cho mỗi bước `decide` và một lần soạn phản hồi `draft`, để chi phí so sánh được với các shape khác.

Ở mốc triển khai cá nhân chưa có benchmark/crash suite chung. Cập nhật tích hợp CP5: Hoàng đã cung cấp `src/reports/benchmark.json` và `crash.json` tại `0f13675`; single đạt 70/70 trial public, cost/success mô phỏng 29.97 VND. Nhóm rà soát lại trên Python 3.12.14: 429 test pass và crash suite 20/20. Đây là bằng chứng nhóm, không phải xác nhận cá nhân đã tự chạy lại trên máy riêng.

## 4. Bằng chứng

Kết quả đã chạy trên máy (Python 3.13.12, Windows) trong thư mục `src/`:

- `python -m lab8.smoke`: `lab8.smoke pass`.
- `python -m pytest -q -m student -o addopts= -rf`: không có dòng `FAILED` nào của `single` (62/62 test student của `single` xanh, gồm T01–T14 trên 5 seed, T11 và T12). Lọc riêng `single` bằng `Select-String "^FAILED.*single\]"` cho kết quả rỗng.
- `python -m pytest -q tests/test_team_single.py`: 19 passed.
- `python -m pytest -q` (cổng host): 73 passed, 248 deselected, không có `failed`.
- Run id của `single` có dạng `R-single-<claim>-s<seed>`, ví dụ `R-single-C-001-s11` (sinh ra khi chạy `test_team_single.py`).

Link commit: [2849887](https://github.com/dnphuc04/K5-L3A-DAY08-DongDong-FromWorkflowsToAgents/commit/2849887c98cb43ccb5ecee4666855c8902785bf1).

## 5. Công cụ AI đã dùng

- **Claude Code (Claude Sonnet 5.5)** trong VS Code: đọc repo và luật nghiệp vụ, viết bản đầu của `single.py` và `test_team_single.py`, chạy test.
- **Tự kiểm tra:** chạy lại test (`single` đạt 62/62 test student), đối chiếu với `docs/business_rules.md` và `docs/contracts.md`; không sửa các file thước đo (`metrics.py`, `durability.py`, `policy.py`, `config/`, `data/`).
- **Điểm kỹ thuật cốt lõi:**
  - *Truyền quote đầy đủ:* host tự trừ phần đã hoàn theo đơn, kiểm approval và đảm bảo idempotency. Nếu shape tự trừ trước thì host trừ thêm lần nữa và T14 sai.
  - *Không nuốt `InjectedCrash`:* T12 kiểm crash có thật sự xảy ra. Ngoại lệ được ghi vào trace rồi ném lại, đi qua `finally` của `run_claim` để đóng kết nối DB. Chạy lại cùng DB sau đó vẫn chỉ ra một refund nhờ ledger.
  - *Trace an toàn:* chỉ ghi field đã qua allowlist, không ghi ticket, claim row hay order row thô (có SĐT, địa chỉ, ghi chú nội bộ).

## 6. Tự đánh giá

- **Đã làm được:** hoàn thiện `src/lab8/shapes/single.py` với vòng ReAct tối đa 8 bước; phân định rõ code (tính tiền, quyết trạng thái, ghi refund) và model (chỉ chọn tool đọc); viết 19 test trong `test_team_single.py`; đạt 62/62 test student.
- **Cập nhật chốt CP5:** hash đã bổ sung từ lịch sử Git; benchmark/crash đã có bằng chứng nhóm như mục 3. Hidden chưa được kiểm và mỗi thành viên vẫn phải tự nộp link LMS.
- **Khó khăn và cách xử lý:** lệnh `-k single` theo hướng dẫn khớp cả tên hàm `test_public_single_run_cases` nên kéo theo test của workflow và orchestrator, làm kết quả bị lẫn. Tôi xử lý bằng cách lọc dòng `FAILED` theo `single\]` để chỉ xem shape của mình.
