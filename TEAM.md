# Team

## Thông tin nhóm

- Tên nhóm: DongDong
- Lớp: L3A
- Repo nhóm: `K5-L3A-DAY08-DongDong-FromWorkflowsToAgents` (xem [SUBMISSION.md](SUBMISSION.md))
- URL repo, nhánh nộp, commit chốt: https://github.com/dnphuc04/K5-L3A-DAY08-DongDong-FromWorkflowsToAgents
- Nhánh nộp: `main`; commit dẫn chứng thống nhất ADR: `526a6ae2df4653f6c59f62bbdf1d4a7cef6efb2c`. Bản rà soát CP5 được bổ sung bằng commit tài liệu tiếp theo; JSON thực nghiệm gốc ở `0f13675`.

## Thành viên

| STT | Họ tên | MSSV | Email | GitHub | Vai trò |
| --: | ------ | ---- | ----- | ------ | ------- |
|   1 |    Đồng Ngọc Phúc    |  2A202603399    |    dnphuc04@gmail.com   |    dnphuc04    | Workflow + tích hợp + chốt bài nộp |
|   2 |   Nguyễn Trần Tiến     |   2A202603504   |    nguyentien2004abc@gmail.com   |    tiennguyen-ctrl    | Single agent + ReAct + budget |
|   3 |   Nguyễn Việt Hưng    |   2A202603411   | robinnguyen2004@gmail.com      | robinnguyen2004       | Orchestrator + handoff + trace an toàn |
|   4 |    Nguyễn Huy Hoàng    |  2A202603366    | nguyenhuyhoangtuho@gmail.com | nguyen-huy-hoang-1708 | Kiểm thử policy/durability + benchmark + đánh giá |

## Phân công thực hiện

Bảng sau ghi phạm vi đã phân công. Trạng thái bàn giao được đối chiếu bằng commit, test trong bảng đóng góp và báo cáo cá nhân; kết quả tích hợp cuối được tổng hợp trong báo cáo nhóm.

| Thành viên | Phần việc chính | Test cần thêm hoặc sửa | Sản phẩm và tiêu chí bàn giao |
| --- | --- | --- | --- |
| Đồng Ngọc Phúc | Viết `src/lab8/shapes/workflow.py`; tích hợp ba shape; giữ cổng host xanh; tổng hợp báo cáo nhóm và checklist nộp | `src/tests/test_team_workflow.py`: kiểm tra ticket mâu thuẫn dữ kiện đơn không làm đổi quote, và thiếu order không ghi refund | Workflow qua 62 test student; dùng quote đầy đủ, `finish()` và truyền `crash_at`; tổng hợp `group_report.md`, thông tin nhóm và commit chốt sau khi có kết quả |
| Nguyễn Trần Tiến | Viết `src/lab8/shapes/single.py` bằng `run_react`, tối đa 8 bước; chỉ cho model chọn tool đọc; tính đủ budget | `src/tests/test_team_single.py`: kiểm tra giới hạn vòng lặp và model không thể chọn tool ghi refund | Single qua 62 test student; tiền do code tính, host ghi; viết phần Single và ranh giới code/model trong mục 3 báo cáo nhóm |
| Nguyễn Việt Hưng | Viết `src/lab8/shapes/orchestrator.py`; dựng handoff bằng `make_handoff`; investigator chỉ đọc; trace theo allowlist | `src/tests/test_team_orchestrator.py`: kiểm tra handoff loại secret và tool ghi, trace không lộ dữ liệu nhạy cảm | Orchestrator qua 62 test student; viết phần Orchestrator, handoff và trace trong mục 3 báo cáo nhóm |
| Nguyễn Huy Hoàng | Kiểm thử tích hợp approval, trần theo đơn, idempotency, crash; chạy benchmark bốn shape và tự kiểm hidden khi có dữ liệu; phân tích số liệu | `src/tests/test_team_safety.py`: kiểm tra approval sai claim và crash/resume không tạo refund trùng trên ba shape | Sinh `src/reports/crash.json` đạt 20/20 và `benchmark.json` đủ bốn shape, năm seed; soạn `decision_adr.md`, `research_card.md`, mục 4 và 7 báo cáo nhóm từ số liệu thật |

### Thứ tự phối hợp

1. **CP1:** Phúc kiểm tra smoke và host test; cả bốn đọc business rules/contract, tự cài môi trường. Thông tin thành viên được tổng hợp trong bảng trên.
2. **CP2:** Phúc, Tiến, Hưng triển khai ba shape trong ba file riêng. Hoàng chuẩn bị test an toàn và lệnh đánh giá; không sửa host, policy, dữ liệu hay config.
3. **CP3:** Mỗi chủ shape xử lý idempotency/crash của shape mình. Hưng kiểm tra handoff/trace; Hoàng kiểm thử chéo. Phúc tích hợp và chạy lại cổng host.
4. **CP4:** Hoàng chạy crash suite và kiểm approval/secret; lỗi thuộc shape nào giao chủ shape đó sửa. Chỉ bàn giao khi test liên quan xanh.
5. **CP5:** Hoàng chạy benchmark và soạn phân tích; cả nhóm cùng thống nhất shape từ bằng chứng. Phúc tổng hợp báo cáo, chạy `check_submission` và chốt bài nộp.

### Quy ước bàn giao

- Mọi lệnh Python chạy trong `src/`. Mỗi chủ shape chạy `python -m pytest -q -m student -o addopts= -k <shape>` trước khi bàn giao; khi tích hợp chạy toàn bộ student suite và `python -m pytest -q`.
- Test nhóm bổ sung phải kiểm tra hành vi hoặc ranh giới an toàn có ý nghĩa, không đổi nhãn/thước đo để test xanh. Các file test đã bàn giao và kết quả tương ứng được ghi trong bảng đóng góp.
- Không sửa `metrics.py`, `durability.py`, `policy.py`, `src/config/*.yaml`, `src/data/*`; không sửa tay JSON report. Báo lỗi host cho cả nhóm thay vì tự sửa thước đo.
- Mỗi người có commit kỹ thuật, ít nhất một test đã thêm hoặc sửa, và báo cáo cá nhân theo mẫu `report/team/MSSV_HoTen.md`. Không ghi trước kết quả, run id hoặc hash chưa có.
- Phúc điều phối bài nộp chung; từng thành viên tự nộp link repo lên LMS.

## Bảng đóng góp

Mỗi dòng dưới đây liên kết phần việc với commit kỹ thuật và test đã bổ sung. Bảng được `lab8.check_submission` dùng để kiểm tra cấu trúc bài nộp.

| Người | Vai | Commit | Test đã thêm hoặc sửa |
| --- | --- | --- | --- |
| Đồng Ngọc Phúc | Workflow + tích hợp | [dd59b0e — Completed CP2](https://github.com/dnphuc04/K5-L3A-DAY08-DongDong-FromWorkflowsToAgents/commit/dd59b0eef515dfabec26b271f743df483b00eb79) | `src/tests/test_team_workflow.py`: `test_workflow_uses_order_facts_not_ticket` (4 ca), `test_workflow_does_not_infer_missing_order_from_ticket`, `test_workflow_unknown_claim_returns_failed_trace`; 6 ca đạt; student workflow 62/62 đạt |
| Nguyễn Trần Tiến | Single agent + ReAct | [2849887 — feat(single): implement ReAct single-agent shape with team tests](https://github.com/dnphuc04/K5-L3A-DAY08-DongDong-FromWorkflowsToAgents/commit/2849887c98cb43ccb5ecee4666855c8902785bf1) | `src/tests/test_team_single.py`: `test_react_loop_stops_at_eight_steps`; `test_single_never_exceeds_eight_loop_steps` (14 claim); `test_model_cannot_pick_a_write_tool` (`issue_refund`, `append_audit`); `test_single_only_ever_calls_read_tools`; `test_single_trace_has_no_secret_or_raw_rows`; 19 ca đạt; student single 62/62 đạt |
| Nguyễn Việt Hưng | Orchestrator + handoff + trace | [1c04b12 — Update orchestrator](https://github.com/dnphuc04/K5-L3A-DAY08-DongDong-FromWorkflowsToAgents/commit/1c04b121fb71ba5aa18fff0da21cacec817b3a45) | `src/tests/test_team_orchestrator.py`: handoff thật chỉ có allowlist + tool đọc, không lộ secret/PII (14 claim); cấp `issue_refund` cho investigator bị `HandoffError` chặn; trace đúng contract và sạch (14 claim × 2 seed); crash/resume chỉ 1 refund; ticket không ghi đè DB (C-002, 5 seed); 47 ca đạt; student orchestrator 62/62 đạt |
| Nguyễn Huy Hoàng | Kiểm thử an toàn + đánh giá | [0f13675 — cross-shape safety suite + crash/benchmark/ablation reports](https://github.com/dnphuc04/K5-L3A-DAY08-DongDong-FromWorkflowsToAgents/commit/0f13675dd9cc24832dc466fe465a47c07ae97a18) | `src/tests/test_team_safety.py` (55 ca, chạy trên workflow/single/orchestrator): approval của claim khác / thiếu / hết hạn không refund; ticket injection C-009 bị `denied`; crash 3 điểm × 3 claim rồi resume bằng seed khác chỉ 1 refund + 1 audit; 4 claim cùng đơn O-107 tổng ≤ 35.000; 3 shape cùng store chạy C-014 chỉ 1 refund; kiểm đột biến 16/18 và 10/18 ca fail; `crash.json` 20/20, `benchmark.json` 4 shape × 14 claim × 5 seed |

## Báo cáo cá nhân

- [Đồng Ngọc Phúc](report/team/2A202603399_DongNgocPhuc.md)
- [Nguyễn Trần Tiến](report/team/2A202603504_NguyenTranTien.md)
- [Nguyễn Việt Hưng](report/team/2A202603411_NguyenVietHung.md)
- [Nguyễn Huy Hoàng](report/team/2A202603366_NguyenHuyHoang.md)
