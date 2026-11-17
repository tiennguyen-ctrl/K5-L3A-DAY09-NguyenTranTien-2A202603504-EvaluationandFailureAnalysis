# Báo cáo nhóm - Lab 8 LogiX-VN

## 1. Thông tin nhóm

- Nhóm: DongDong - L3A; bốn thành viên và bằng chứng đóng góp: `TEAM.md`.
- Repo: https://github.com/dnphuc04/K5-L3A-DAY08-DongDong-FromWorkflowsToAgents
- Commit chốt: `526a6ae2df4653f6c59f62bbdf1d4a7cef6efb2c`, thống nhất với ADR. Code, test và JSON thực nghiệm có ở `0f13675`; bản tổng hợp báo cáo có ở commit chốt, các cập nhật biên tập được bổ sung sau đó. Bản rà soát CP5 này được bổ sung sau commit chốt theo quy trình ghi hash rồi commit tài liệu.

## 2. Mục tiêu và cách tiếp cận

Nhóm xử lý cùng một claim hoàn tiền bằng workflow, single agent, orchestrator và swarm tham chiếu để chọn kiến trúc ít tự chủ nhất vẫn làm đúng. Database và policy hiệu lực là nguồn sự thật; ticket là dữ liệu không đáng tin. Code tính tiền và host kiểm quyền ghi; model không quyết số tiền hoặc tạo approval.

Phúc phụ trách workflow, tích hợp và báo cáo; Tiến phụ trách single/ReAct; Hưng phụ trách orchestrator/handoff; Hoàng phụ trách kiểm thử an toàn, benchmark và phân tích. Ba shape được viết song song, kiểm thử riêng rồi tích hợp vào main. Nhóm lần lượt kiểm smoke/host, student matrix, retry/crash, bảo mật, benchmark và điều kiện nộp.

Benchmark giữ cùng 14 claim public, năm seed 11,22,33,44,55, MockLLM, bảng giá và evaluator; mỗi trial có SQLite mới. So sánh là giữa các triển khai hiện có: số tool/model call cũng thay đổi cùng kiến trúc, nên không thể tách hoàn toàn tác động topology khỏi chính sách gọi tool.

## 3. Giải pháp

### 3.1. Workflow - Đồng Ngọc Phúc

`workflow.py` chạy các bước Python cố định: `get_claim_view` → `lookup_order` theo principal → `compute_compensation` → host. Claim không tồn tại trả `failed`; thiếu mã đơn trả `needs_info`; đơn không thấy hoặc không thuộc principal trả `escalated`. Không lấy mã đơn hoặc số ngày trễ từ ticket.

Quote bằng 0 trả `denied`, không gọi ghi tiền. Quote dương được truyền đầy đủ vào `durability.issue_refund`. Host kiểm approval, trần theo đơn và idempotency; host từ chối trả `denied`, xung đột amount trả `failed`, chấp nhận trả `resolved`. `proposal_amount` giữ quote đầy đủ: entitlement 150.000, đã hoàn 30.000 thì đề xuất vẫn 150.000, host ghi 120.000. Shape không tự trừ phần đã hoàn.

Workflow không gọi model, cộng budget cho từng tool đọc, truyền `crash_at` và để `InjectedCrash` truyền ra; luôn đóng kết nối bằng `finally`. Mọi nhánh return dùng `finish()` để lấy effect/audit thật từ ledger và ghi trace mới. Trace chỉ có `claim.found`, `order.visible/reason`, quote và decision; không ghi ticket, secret, header hoặc bản ghi claim/order thô. Đường crash không trả RunResult; trace được ghi khi resume hoàn tất.

<!-- pagebreak -->

### 3.2. Single - Nguyễn Trần Tiến

`single.py` dùng `run_react(max_steps=8)`. `decide` chọn tool đọc: lấy order, tính quote rồi kết thúc. `runtime.dispatch` chặn `issue_refund` và `append_audit` từ model. MockLLM ghi nhận model call cho vòng ReAct và soạn phản hồi; code quyết status, quote và việc gọi host. Chính sách chọn tool hiện cố định, không mô phỏng đầy đủ độ bất định của model thật.

Thiếu mã đơn hoặc đơn ngoài scope dừng sớm; quote dương đi qua host với quote đầy đủ và `crash_at`. Chạm trần vòng lặp trả `failed/step_cap`; lỗi tool trong vòng lặp cũng trả `failed`. Crash được ghi trace rồi ném lại. Trace lưu quan sát đã lọc, quote, vòng lặp và quyết định; không lưu ticket hoặc dữ liệu nhạy cảm. 19 test riêng kiểm giới hạn 8 bước, tool chỉ đọc, ranh giới ghi tiền và trace.

### 3.3. Orchestrator - Nguyễn Việt Hưng

`orchestrator.py` đọc claim qua view và tạo `handoff.v1` bằng `make_handoff`, với `facts={}` và bốn tool đọc: `lookup_order`, `lookup_policy`, `lookup_refund_history`, `compute_compensation`. Không chuyển ticket hoặc parent context. Allowlist loại field ngoài phạm vi và từ chối tool ghi; tóm tắt bằng LLM không được coi là redaction.

`run_readonly_investigators` chạy trong scope principal. Investigator chỉ đọc; orchestrator tính quyết định từ quote, gọi host với entitlement đầy đủ và giữ proposal trước cap. Có một model call soạn phản hồi, không quyết số tiền. Crash được flush trace rồi ném lại. Trace ghi handoff đã sanitize, trạng thái điều tra, lịch sử refund dạng số, quote và quyết định. 47 test riêng kiểm handoff thật, dữ liệu nhạy cảm, trace, ticket mâu thuẫn và crash/resume.

Orchestrator đọc claim hai lần và chạy nhiều tool hơn workflow; overhead này được tính trong benchmark, không được coi là chi phí bắt buộc của mọi thiết kế multi-agent.

### 3.4. Ranh giới chung và kiểm thử

Host là đường ghi tiền duy nhất: kiểm approval đúng claim, trần theo đơn, khóa `refund:{claim_id}` và transaction ledger/audit. Dữ kiện ticket không ghi đè database. `finish()` đối chiếu kết quả với ledger; trace là ranh giới bảo mật nên chỉ ghi dữ liệu cần cho kiểm toán.

| Bằng chứng | Phạm vi |
| --- | --- |
| Test Workflow (6 ca) | Ticket nói quá/phủ nhận độ trễ ở hai seed; thiếu order không suy từ ticket; claim không tồn tại; trace sạch |
| Test Single (19 ca) | Trần ReAct, chặn tool ghi, giới hạn scope và trace |
| Test Orchestrator (47 ca) | Allowlist, investigator chỉ đọc, chống leak, crash/resume |
| Test an toàn (55 ca) | Approval sai/thiếu/hết hạn, ticket injection, ba điểm crash, trần theo đơn và retry xuyên shape |

<!-- pagebreak -->

## 4. Kết quả và quyết định

Nguồn: `src/reports/benchmark.json`, `crash.json`, `ablation_r1.json`, lưu ở commit `0f13675`. Benchmark có 70 trial mỗi shape (14 claim × 5 seed). Chi phí là VND mô phỏng; latency không đo (`unavailable`).

| Shape | Pass | pass^5 | Seed min-max | Variance | Cost/success |
| --- | --- | --- | --- | --- | --- |
| Workflow | 1.000 | 1.000 | 1.000-1.000 | 0.000000 | 27.86 |
| Single | 1.000 | 1.000 | 1.000-1.000 | 0.000000 | 29.97 |
| Orchestrator | 1.000 | 1.000 | 1.000-1.000 | 0.000000 | 56.65 |
| Swarm | 0.986 | 0.929 | 0.929-1.000 | 0.000816 | 49.57 |

| Shape | Mean/p95 steps | Model calls TB | Tool calls TB |
| --- | --- | --- | --- |
| Workflow | 3.79 / 4 | 0.00 | 2.79 |
| Single | 4.79 / 5 | 3.79 | 2.79 |
| Orchestrator | 4.71 / 5 | 1.00 | 5.57 |
| Swarm | 2.80 / 3 | 3.00 | 4.66 |

Ba shape của nhóm đều đúng trên public. Workflow rẻ nhất; single đắt hơn khoảng 7.6%, orchestrator khoảng 2.03 lần. Số event trace khác nhau giữa các triển khai, nên steps không phải latency hay khối lượng tính toán chuẩn hóa.

Swarm fail 1/70 trial: `R-swarm-C-002-s55`. Ticket nói trễ 5 ngày, database ghi 2 ngày; seed 55 tin ticket nên quote sai và tạo refund 20.000. Approval hợp lệ không chứng minh entitlement đúng: shape vẫn phải dùng dữ kiện có thẩm quyền. Không copy điểm yếu tham chiếu vào workflow.

Crash suite đạt **20/20**. Ma trận student của mỗi shape đạt 62/62, gồm retry và crash/resume. Trên các trial public được chấm không có secret/PII bị phát hiện; test approval không cho ghi refund trái phép. Đây không phải kết quả hidden.

Nhóm chọn **workflow**: độ đúng public ngang single/orchestrator, ít tự chủ nhất và cost thấp nhất. Run id dẫn chứng: `R-workflow-C-001-s11`; toàn bộ 70 trial có trong JSON. Chi tiết quyết định ở `decision_adr.md`.

Ablation R1 so workflow với orchestrator: pass 1.000 → 1.000, cost 27.86 → 56.65, tool calls 2.79 → 5.57. Kết quả phù hợp hướng dự đoán overhead của triển khai investigator; chưa cô lập riêng topology vì tập lời gọi thực tế và model call cũng khác. Research card ghi đầy đủ giả thuyết và giới hạn.

<!-- pagebreak -->

## 5. Kiểm tra tái lập và khó khăn

### 5.1. Xác minh cuối CP5

Kiểm tra tại commit `526a6ae` bằng **Python 3.12.14**, Windows, pytest 8.4.2 và PyYAML 6.0.3. Python lấy từ runtime Codex; dependency Python thuần được nạp qua `PYTHONPATH` từ `.venv/Lib/site-packages` hiện có. Không thay môi trường ảo 3.14 của người dùng. Để tái lập thông thường, tạo venv Python 3.12 và cài `src/requirements.txt`.

Lệnh logic chạy trong `src/` sau khi chọn đúng Python và dependencies:

```powershell
python -m pytest -q -o addopts= --tb=short --basetemp=.pytest_cache/cp5-py312-02
python -m lab8.benchmark --shapes workflow,single,orchestrator,swarm --cases data/public_claims.jsonl --seeds 11,22,33,44,55 --out .pytest_cache/cp5_benchmark_py312.json
python -m lab8.crash_test --count 20 --out .pytest_cache/cp5_crash_py312.json
python -m lab8.check_submission
```

Toàn bộ **429 test pass** (181 host/test nhóm + 248 student); crash chạy lại **20/20**. Benchmark và crash tạm được đối chiếu với JSON chính thức; không sửa tay report. Các kết quả kiểm tra local không thay cho hidden hoặc trạng thái CI.

### 5.2. Khó khăn thực tế

| Vấn đề | Cách xử lý |
| --- | --- |
| `requirements.txt` không thấy khi chạy ở gốc | Chuyển vào `src/` để cài và chạy lab |
| `PermissionError: [WinError 5]` với thư mục tạm pytest | Dùng `--basetemp` riêng, chạy với quyền truy cập phù hợp; không đổi logic/test để né lỗi |
| Xung đột thông tin Tiến/Hưng trong TEAM | Gộp thông tin cả hai, bỏ conflict marker, giữ mỗi người một dòng |
| PR chọn nhầm repo gốc | Đóng PR nhầm, kiểm tra base repository là repo nhóm trước khi merge |
| Python venv ban đầu là 3.14.6 | Xác minh lại đủ test, benchmark và crash trên Python 3.12.14 thuộc dải đề yêu cầu |

Sau commit rà soát CP5 `b26d3c9`, kiểm tra nộp bài đạt `0 FAIL, 0 WARN` và working tree sạch. Repo nhóm công khai; không thấy file SQLite, `.env`, trace hoặc hidden pack được Git theo dõi ở lần rà soát này. Mỗi thành viên vẫn phải tự nộp link LMS.

<!-- pagebreak -->

## 6. Tổng hợp đóng góp

| Thành viên | Sản phẩm chính | Commit kỹ thuật |
| --- | --- | --- |
| Đồng Ngọc Phúc | Workflow, 6 test, tích hợp và tổng hợp báo cáo | `dd59b0e` |
| Nguyễn Trần Tiến | Single/ReAct, 19 test và phần Single | `2849887` |
| Nguyễn Việt Hưng | Orchestrator/handoff, 47 test và phần Orchestrator | `1c04b12` |
| Nguyễn Huy Hoàng | 55 test an toàn; crash/benchmark/ablation; ADR và research card | `0f13675` |

Tên test, link commit và báo cáo cá nhân nằm trong `TEAM.md` và `report/team/`. Các số trên là test nhóm bổ sung, không cộng lẫn với 248 student. Có dùng Codex hỗ trợ; từng thành viên chịu trách nhiệm đọc lại, giải thích và kiểm chứng phần của mình theo RULES.

## 7. Hạn chế và hướng cải thiện

Public chỉ có 14 claim, ba shape đều bão hòa ở pass 1.000. Variance 0 không chứng minh ổn định trên claim khác. Chưa có `student_drop/`, chưa biết hidden pass rate ≥ 0.75 hay chưa.

MockLLM không phản ánh đầy đủ việc model thật chọn tool sai hoặc biến động token. Cost là mô phỏng, không phải hóa đơn API; không đo latency nên không kết luận investigator giúp hay làm chậm. So sánh A/C thay cả pattern gọi tool và model call, vì vậy chưa phải phép cô lập topology thuần túy.

Test an toàn phủ các tình huống đã thiết kế nhưng chưa kiểm hai tiến trình ghi đồng thời. Rà soát không thay thế đánh giá bảo mật đầy đủ. Quy trình trên Python 3.12 dùng dependency thuần từ venv hiện có, chưa phải kiểm tra cài sạch hay xác minh ba hệ điều hành.

Hướng tiếp theo: tự kiểm hidden khi được cấp; thử concurrent writers; giữ model/tool-call policy tương đương để cô lập topology; tối ưu đọc claim trùng nếu chọn orchestrator. Chỉ đổi quyết định khi corpus đại diện cho thấy shape khác cải thiện độ đúng/độ ổn định đủ rõ với chi phí chấp nhận được; ưu tiên cân nhắc single trước.

## 8. Tài liệu tham khảo

- Tài liệu repo: `docs/business_rules.md`, `docs/contracts.md`, `docs/architecture.md`, `docs/metrics.md`, `RULES.md`, `RUBRIC.md`, `SUBMISSION.md`.
- Bằng chứng: `src/reports/benchmark.json`, `crash.json`, `ablation_r1.json`; phân tích: `report/team/decision_adr.md`, `research_card.md`.
- Yubin Kim và Xin Liu, Google Research (28/01/2026), [Towards a science of scaling agent systems: When and why agent systems work](https://research.google/blog/towards-a-science-of-scaling-agent-systems-when-and-why-agent-systems-work/). Nguồn chính thức tóm tắt benchmark về phối hợp agent; nghiên cứu không dùng MockLLM của lab. Lab chỉ đối chiếu một giả thuyết hẹp, không tái lập toàn bộ nghiên cứu.
