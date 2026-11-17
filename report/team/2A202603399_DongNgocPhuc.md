# Báo cáo cá nhân — 2A202603399_DongNgocPhuc

## 1. Thông tin thành viên

- Họ tên: Đồng Ngọc Phúc
- MSSV: 2A202603399
- Email: dnphuc04@gmail.com
- GitHub: dnphuc04
- Nhóm: DongDong — L3A

## 2. Phần việc phụ trách

Phụ trách Workflow, kiểm thử tương ứng, tích hợp các shape và tổng hợp báo cáo nhóm. Đã hoàn thành code, test, bằng chứng đóng góp và rà soát CP5. Các thay đổi đã được đưa lên `main`; việc nộp link LMS do từng thành viên thực hiện và chưa được xác nhận trong báo cáo này.

## 3. Đóng góp cụ thể

Commit triển khai: [dd59b0e — Completed CP2](https://github.com/dnphuc04/K5-L3A-DAY08-DongDong-FromWorkflowsToAgents/commit/dd59b0eef515dfabec26b271f743df483b00eb79), gồm `src/lab8/shapes/workflow.py` và `src/tests/test_team_workflow.py`.

Workflow chạy các bước cố định: đọc claim, kiểm tra mã đơn và quyền xem đơn, tính quote từ dữ kiện đơn rồi gọi host. Model không tham gia quyết định; ticket không được dùng để thay đổi mã đơn, độ trễ hoặc số tiền.

Shape truyền quote đầy đủ cho `durability.issue_refund`. Host tự kiểm approval, áp trần theo đơn và trừ số tiền các claim trước đã nhận. Ví dụ entitlement 150.000 VND, đã hoàn 30.000 VND thì proposal vẫn là 150.000 VND và host chỉ ghi thêm 120.000 VND. Nếu shape tự trừ trước, host sẽ trừ lần nữa và cho kết quả sai.

Mọi nhánh return dùng `finish()` để lấy effect/audit từ ledger và ghi trace mới. Trace chỉ lưu kết quả tìm claim, quyền xem đơn, quote và quyết định; không lưu ticket, secret hoặc dữ liệu nhạy cảm trong bản ghi thô. Shape truyền `crash_at`, để `InjectedCrash` truyền ra ngoài và đóng kết nối bằng `finally`; host/ledger bảo đảm retry không ghi refund trùng.

Ngoài phần code, đã tổng hợp nội dung báo cáo nhóm, điền bằng chứng trong `TEAM.md`, rà lại ADR/research card và kiểm tra tích hợp sau khi đủ ba shape. Bản rà soát CP5 được lưu ở commit `b26d3c9`.

## 4. Bằng chứng kiểm thử

| Test trong `test_team_workflow.py` | Hành vi kiểm tra |
| --- | --- |
| `test_workflow_uses_order_facts_not_ticket` | 4 ca: ticket phóng đại hoặc phủ nhận độ trễ ở seed 11 và 55; kết quả vẫn theo dữ kiện đơn, không gọi model |
| `test_workflow_does_not_infer_missing_order_from_ticket` | Thiếu mã đơn có cấu trúc vẫn trả `needs_info`, không thêm ledger; trace đúng run id và không chứa ticket/canary |
| `test_workflow_unknown_claim_returns_failed_trace` | Claim không tồn tại trả `failed`, không có effect và có trace đúng run id |

Khi hoàn thành Workflow: 6 ca riêng và 62 ca student của workflow đều đạt, gồm T11 retry và T12 crash/resume. Sau khi tích hợp đủ các shape, nhóm kiểm tra trên Windows/Python **3.12.14**: toàn bộ **429 test pass** (181 host/test nhóm + 248 student), smoke pass và crash suite **20/20**. `check_submission` sau commit `b26d3c9` đạt **0 FAIL, 0 WARN**.

Lệnh kiểm tra đầy đủ, chạy trong `src/` sau khi chọn Python và dependencies:

```powershell
python -m pytest -q -o addopts= --tb=short --basetemp=.pytest_cache/cp5-py312-02
python -m lab8.check_submission
```

Lần xác minh Python 3.12 dùng runtime Codex, pytest 8.4.2 và PyYAML 6.0.3 được nạp từ `.venv/Lib/site-packages` qua `PYTHONPATH`. Môi trường ảo Python 3.14 của người dùng được giữ nguyên; đây chưa phải kiểm thử cài sạch hoặc đa nền tảng. Lỗi quyền thư mục tạm ban đầu được xử lý bằng `--basetemp` riêng và quyền truy cập phù hợp.

Benchmark do Hoàng tạo ở `0f13675` được chạy lại trên Python 3.12 vào file tạm. Các chỉ số theo shape và biến kiểm soát trùng report chính thức; crash report chạy lại cũng trùng. Workflow đạt 70/70 trial public, pass rate/pass^5 1.000, variance 0 và cost/success mô phỏng 27.86 VND. Run id ví dụ: `R-workflow-C-001-s11`. Chưa có kết quả hidden.

## 5. Công cụ AI đã dùng

Sử dụng OpenAI Codex để đọc contract, hỗ trợ viết Workflow/test, chạy kiểm thử, đối chiếu Git và biên tập báo cáo. Hành vi được kiểm chứng bằng test, ledger/audit và source code; hash lấy từ lịch sử Git, số liệu benchmark lấy từ JSON do công cụ sinh. Không sửa tay JSON hoặc các file thước đo. Những kết quả chạy với hỗ trợ Codex được ghi rõ là kết quả kiểm tra trên workspace, không thay cho việc thành viên tự giải thích code khi bảo vệ bài.

## 6. Tự đánh giá

Đã hoàn thành Workflow ở CP2, kiểm tra retry/crash ở CP3 và phần tích hợp/tổng hợp báo cáo ở CP5. Workflow đáp ứng luật trên public, không phụ thuộc quyết định model và có cost mô phỏng thấp nhất trong các shape được đo. Kết quả này hỗ trợ lựa chọn Workflow trong ADR nhưng chưa chứng minh độ đúng trên hidden hoặc hiệu năng khi dùng model thật.

Báo cáo nhóm đã được xuất và kiểm tra dưới dạng PDF 5 trang A4. Commit dẫn chứng `526a6ae` thống nhất giữa ADR, báo cáo nhóm và TEAM; JSON thực nghiệm gốc ở `0f13675`, các cập nhật rà soát được bổ sung sau đó. Trạng thái nộp LMS không nằm trong bằng chứng kỹ thuật đã kiểm tra.
