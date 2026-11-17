# Decision record

Nhóm chọn kiến trúc dựa trên benchmark public, chi phí mô phỏng và các kiểm tra an toàn. Các trường dưới đây là bằng chứng cho quyết định.

- Shape chọn: workflow
- Commit hash: 526a6ae2df4653f6c59f62bbdf1d4a7cef6efb2c (mốc bài nộp đã có code, test và báo cáo; JSON thực nghiệm được sinh từ `0f13675`; tài liệu rà soát CP5 được commit tiếp theo quy trình trong SUBMISSION.md)
- Run id dẫn chứng: `R-workflow-C-001-s11` … `R-workflow-C-014-s55` (70 trial trong `src/reports/benchmark.json`); đối chứng lỗi swarm `R-swarm-C-002-s55`
- Pass rate / pass^5 / seed min-max / variance: 1.000 / 1.000 / 1.000–1.000 / 0.000000 (14 claim × 5 seed, `src/reports/benchmark.json`)
- Cost per success (mô phỏng, VND): 27.86 (single 29.97, swarm 49.57, orchestrator 56.65)
- Crash safety: 20/20 (`src/reports/crash.json`); thêm 30 ca crash/resume trên ba shape trong `src/tests/test_team_safety.py`
- Secret leak / approval bypass: 0 / 0 (benchmark 70/70 trial workflow pass, không có `forbidden_substring`/`leak_suspect`; test approval sai claim, thiếu, không tồn tại, hết hạn đều không có refund)

## Vì sao shape này

Trên cùng corpus public (14 claim), cùng 5 seed `11,22,33,44,55`, cùng bảng giá mô phỏng và mỗi trial một SQLite riêng, ba shape của nhóm đều đạt pass rate 1.000, pass^5 1.000 và variance 0, còn swarm tham chiếu đạt 0.986 / 0.929 với seed 55 chỉ 0.929 (C-002 bị `resolved` thay vì `denied` vì tin số ngày trễ trong ticket). Khi chất lượng ngang nhau, chi phí và độ tự chủ quyết định: workflow rẻ nhất (27.86 VND/success, 0 model call, 2.79 tool call, 3.79 bước trung bình), single đắt hơn 7.6% vì 3.79 model call mỗi trial, orchestrator đắt gấp 2.03 lần vì đọc lại claim và chạy investigator (5.57 tool call). Bài toán claim là tuần tự và quyết định hoàn toàn bằng luật (dữ kiện đơn + policy + approval), nên không có bước nào cần model suy luận để ra quyết định. Workflow là kiến trúc ít tự chủ nhất mà vẫn làm đủ việc, và không cần thêm ranh giới handoff trong bài toán này.

## Có đáng đổi lấy multi-agent không

Trên bộ public hiện có, chi phí multi-agent chưa mang lại cải thiện độ đúng. Orchestrator giữ nguyên pass rate (1.000 = 1.000) nhưng tăng cost/success từ 27.86 lên 56.65 VND; swarm có kết quả thấp hơn workflow ở cả pass^5 (0.929) lẫn variance (0.000816). Với corpus đại diện hơn, nhóm sẽ đánh giá lại mức cải thiện độ đúng, độ ổn định và chi phí trước khi tăng mức tự chủ. Quyết định sẽ đảo lại khi: (1) corpus đánh giá mở rộng có yêu cầu đọc chứng từ tự do mà workflow hiện tại chưa hỗ trợ và workflow rơi dưới 0.75 trong khi shape khác vượt; (2) có bước điều tra độc lập, song song được, khiến investigator giảm latency thật (hiện latency `unavailable`); hoặc (3) shape agent đạt pass^5 cao hơn rõ rệt với variance không tăng. Khi đó nhóm cân nhắc single (cost chỉ +7.6%) trước orchestrator.

## Trace và bằng chứng

Trace của workflow ghi các event `claim` (chỉ `found`), `order` (chỉ `visible`, `reason`), `quote` (kết quả `compute_compensation`) và `decision` (status, số tiền đề xuất, lý do host). Trace cố ý **không** ghi ticket (dữ liệu khách tự viết, có thể chứa canary hoặc lệnh chèn), claim/order row thô, `parent_secret`, `raw_headers`, SĐT, địa chỉ, ghi chú nội bộ và tên hàng: grader và đội vận hành đọc trace, nên mọi field không cần cho việc kiểm toán quyết định đều là rủi ro rò rỉ. Ranh giới này được kiểm bằng benchmark (`forbid_substrings` trên 70 trial) và bằng test nhóm so với giá trị nhạy cảm thật lấy từ dữ liệu. Việc quét trace được bổ sung bằng kiểm tra thiết kế và test; không dùng kết quả quét trong một thư mục để kết luận về mọi đầu ra: (1) shape chỉ đọc claim qua `get_claim_view`, view không trả `parent_secret` hoặc header cho shape; (2) mọi payload vào trace là field allowlist chọn tay trong code, không dump object; (3) test âm tính cố ý ghi claim row vào trace phải làm test fail (đã thử với orchestrator: 29/47 ca fail); (4) ghi bằng chứng ledger/audit trong SQLite thay vì log tự do.

## Giới hạn

MockLLM và giá mô phỏng không đại diện đầy đủ cho model sản xuất. Latency là `unavailable`. Nhóm không nhận được `student_drop/` nên chưa chạy tự kiểm hidden; kết luận chỉ dựa trên 14 claim public, nơi ba shape của nhóm đều bão hòa ở 1.000, nên benchmark public không phân biệt được chất lượng giữa workflow, single và orchestrator — chỉ phân biệt được cost và độ tự chủ.
