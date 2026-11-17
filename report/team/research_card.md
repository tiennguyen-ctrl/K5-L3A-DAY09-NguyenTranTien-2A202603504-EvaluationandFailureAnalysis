# Research card

Nhóm chọn R1: kiểm tra chi phí phối hợp khi chuyển từ workflow sang orchestrator trong bài toán claim chủ yếu tuần tự. Phép so sánh giữ cùng môi trường đánh giá và đo hai triển khai cụ thể; giới hạn về việc cô lập topology được nêu ở cuối.

| Câu | Nguồn (thư viện tham khảo, slide 68–69) | Câu hỏi gợi ý cho lab |
| --- | --- | --- |
| R1 · Scaling | Google Research 2026, *Towards a Science of Scaling Agent Systems* | Task claims chủ yếu tuần tự hay song song được? Dự đoán thêm investigator sẽ làm pass rate và cost/success thay đổi thế nào. |
| R2 · Failure taxonomy | MAST, NeurIPS 2025, *Why Do Multi-Agent LLM Systems Fail?* | Các trial fail của swarm (seed 55) thuộc nhóm nào: lỗi giao việc, lệch mục tiêu, hay lỗi kiểm chứng? |
| R3 · Architecture choices | AgentArch, AACL 2026 | Nếu đổi topology mà giữ nguyên mọi thứ khác, biến nào phải cố định để kết luận còn đúng? |
| R4 · Evaluation confounders | EMNLP 2026, *Rethinking Evaluation of MAS Efficiency* | Làm sao chứng minh chênh lệch giữa A/B/C/D là do topology, không phải do prompt, tool hay seed? |

## Phiếu của nhóm

| Field | Hướng dẫn | Nhóm điền |
| --- | --- | --- |
| CÂU | R1 / R2 / R3 / R4 | R1 · Scaling |
| SOURCE | Paper/blog, năm, URL, loại bằng chứng (benchmark, production report, blog kinh nghiệm) | Yubin Kim và Xin Liu, Google Research (28/01/2026), [Towards a science of scaling agent systems](https://research.google/blog/towards-a-science-of-scaling-agent-systems-when-and-why-agent-systems-work/); blog chính thức tóm tắt benchmark có kiểm soát, không phải bằng chứng production |
| CLAIM | Một kết luận gốc của nguồn. Không viết rộng hơn phạm vi paper | Lợi ích của thêm agent phụ thuộc cấu trúc task: task phân rã song song được có thể hưởng lợi, còn task tuần tự chặt thường không tăng chất lượng mà tăng chi phí phối hợp |
| BOUNDARY | Model / dataset / setup giới hạn kết luận đó | Kết luận của nguồn dựa trên LLM thật và các benchmark của họ; lab này dùng MockLLM cố định theo seed, corpus 14 claim public, giá token/tool mô phỏng, không đo latency. Chỉ kiểm được hướng thay đổi của cost và pass rate, không kiểm được độ lớn trên model thật |
| HYPOTHESIS | Nếu đổi shape A→B (hoặc bật/tắt một thành phần), metric X sẽ đổi theo hướng nào, khoảng bao nhiêu | Claim là chuỗi tuần tự claim → order → policy → quote → host. Đổi workflow (A) → orchestrator (C), tức bật investigator, sẽ giữ nguyên pass rate (Δ ≈ 0, cả hai ≈ 1.0) và tăng cost/success khoảng 1.5–2.5 lần do đọc lại dữ kiện và thêm một model call |
| METHOD | Biến giữ cố định: model, tools, seed, corpus, giá, evaluator. Biến duy nhất được thay đổi: … | Cố định: MockLLM, 4 tool đọc + `durability.issue_refund` của host, seed 11,22,33,44,55, `data/public_claims.jsonl`, `config/pricing.yaml`, `lab8.metrics` làm evaluator, mỗi trial một SQLite mới. Thành phần thay đổi: triển khai workflow → orchestrator có investigator chỉ đọc. Registry tool và host được giữ nguyên, nhưng số/tập tool thực gọi và model call khác nhau; chưa cô lập topology thuần túy |
| FAILURE / METRIC | Một lỗi dự kiến và cách đo nó: pass rate, pass^5, variance, cost/success, leak, bypass | Lỗi dự kiến: coordination overhead (đọc trùng dữ kiện, gọi tool lặp) làm tăng cost mà không tăng pass; rủi ro phụ là handoff mang theo dữ liệu nhạy cảm. Đo bằng cost/success và mean tool calls (overhead), pass rate / pass^5 / variance (chất lượng), `leak_suspect`/`forbidden_substring` trên trace (rò rỉ) |

## Kết quả ablation

- Lệnh đã chạy (copy nguyên văn): `python -m lab8.benchmark --shapes workflow,orchestrator --cases data/public_claims.jsonl --seeds 11,22,33,44,55 --out reports/ablation_r1.json`
- Run id / file report: `src/reports/ablation_r1.json` (commit `0f13675`); run id `R-workflow-<claim>-s<seed>` và `R-orchestrator-<claim>-s<seed>`, 70 trial mỗi shape. Số liệu trùng khớp với `src/reports/benchmark.json`.
- Kết quả so với hypothesis (đúng / sai / không kết luận được), kèm số liệu: **Phù hợp với giả thuyết trong hai triển khai được đo.** Pass rate 1.000 → 1.000, pass^5 1.000 → 1.000, variance 0 → 0 (Δ chất lượng = 0). Cost/success 27.86 → 56.65 VND (×2.03, nằm trong khoảng dự đoán 1.5–2.5). Mean tool calls 2.79 → 5.57 (×2.0), model calls 0 → 1, mean steps 3.79 → 4.71. Theo từng claim (seed 11), claim có đơn hợp lệ tốn 30.00 → 60.94 VND vì `get_claim_view` được đọc hai lần và investigator chạy đủ 4 tool đọc; claim thiếu `order_id` (C-004) gần như không đổi (10.00 → 10.92) vì dừng trước handoff. Không có trial nào bị leak ở cả hai shape.
- Giới hạn: MockLLM không phải model sản xuất, latency là `unavailable`. Corpus public chỉ 14 claim và cả hai shape đều bão hòa ở pass 1.000, nên ablation không đo được trường hợp investigator giúp tăng chất lượng; lợi ích song song (giảm latency) cũng không đo được vì không có latency.

### Giới hạn khi diễn giải biến can thiệp

Hai triển khai còn khác số model call, số lần đọc claim và tập tool thực sự được gọi. Do đó phép so sánh đo tác động tổng hợp của hai triển khai, chưa cô lập topology thuần túy. Kết quả phù hợp dự đoán overhead trong lab, chưa chứng minh investigator nói chung làm tăng cost 2.03 lần. Muốn cô lập topology cần giữ tương đương chính sách gọi tool/model và chỉ đổi cách điều phối.
