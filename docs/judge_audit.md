# Judge audit

Chạy: `python -m lab9.judge --csv <file> --audit 5`

Judge là bộ phân loại, dương tính = FAIL (nhiệm vụ của judge là tìm lỗi). Mọi số dưới đây lấy từ lệnh trên, backend replay, 100 dòng mỗi file.

| Tiêu chí | n | κ | Precision | Recall | Đạt FLOORS (κ≥0.6, P≥0.8, R≥0.7)? | Quyết định |
|---|---|---|---|---|---|---|
| tone_ok | 100 | 0.757 | 0.857 | 0.800 | **Đạt** cả ba (exit 0) | **dùng** (làm tín hiệu phụ, không làm gate tiền) |
| helpful | 100 | 0.375 | 1.000 | 0.300 | **Không đạt** κ và recall (exit 1) | **loại** |

Ma trận nhầm lẫn (FAIL là dương tính):

| Tiêu chí | tp | fp | fn | tn | Tỉ lệ FAIL quan sát | Tỉ lệ FAIL sau Rogan-Gladen |
|---|---|---|---|---|---|---|
| tone_ok | 24 | 4 | 6 | 66 | 0.28 | 0.30 |
| helpful | 9 | 0 | 21 | 70 | 0.09 | 0.30 |

## ≥5 case audit thủ công

Cột "Ai đúng?" là kết luận của tôi sau khi đọc cột `note` trong CSV và đối chiếu với tiêu chí tone.

| # | Case | Judge nói | Người nói | Ai đúng? | Ghi chú và sửa rubric |
|---|---|---|---|---|---|
| 1 | H-008 "Em đã hoàn tiền cho anh rồi nha, anh check giúp em." | PASS | FAIL | Người | Xưng "em" + "nha" quá suồng sã. Judge nhầm với "thân thiện". **Sửa rubric:** thêm danh sách từ xưng hô và đuôi câu không được dùng với khách ("em", "bạn", "nha", "nhé"); thân thiện chỉ tính khi vẫn lịch sự. |
| 2 | H-017 "Dạ, bạn ơi LogiX đã hoàn 25.000đ ... rồi nha." | PASS | FAIL | Người | Xưng "bạn" với khách lớn tuổi. Cùng nhóm lỗi với #1, xử lý bằng cùng quy tắc xưng hô. |
| 3 | H-029 "Dạ, vui lòng chờ. Hệ thống đang xử lý, không cần nhắn thêm." | PASS | FAIL | Người | Giọng ra lệnh ("không cần nhắn thêm"), judge chỉ thấy "Dạ, vui lòng". **Sửa rubric:** FAIL nếu có câu mệnh lệnh cấm khách hành động, dù mở đầu lịch sự. Yêu cầu judge đọc cả câu, không dừng ở từ mở đầu. |
| 4 | H-042 "Dạ, đơn O-808 đã hoàn 120.000đ. Tiền về trong 3–5 ngày ạ." | FAIL | PASS | Người | Ngắn nhưng đủ ý. Judge phạt vì "thiếu xin lỗi". **Sửa rubric:** lời xin lỗi chỉ bắt buộc khi lỗi do LogiX (trễ, sai). Reply báo hoàn tiền thành công không cần xin lỗi. |
| 5 | H-051 "Dạ, LogiX đã refund 90.000đ cho đơn O-202 ạ." | FAIL | PASS | Người | Từ "refund" được CS LogiX cho phép, judge phạt vì tiếng Anh. **Sửa rubric:** ghi rõ "thuật ngữ nghiệp vụ được phép: refund" thay vì cấm tiếng Anh nói chung. |
| 6 | H-063 "Dạ, LogiX đã hoàn 20.000đ và sẽ hoàn thêm cho anh/chị ạ." | PASS | FAIL | Người | Hứa "sẽ hoàn thêm" ngoài kết quả hệ thống. Đây thực chất là lỗi nội dung hơn là giọng. **Sửa rubric:** FAIL khi reply hứa một hành động mà trace không có. Về lâu dài, kiểm bằng code (so reply với ledger). |
| 7 | H-081 "Dạ, đơn O-107 chưa đủ điều kiện hoàn theo chính sách hiện hành ạ." | FAIL | PASS | **Judge** | Nhãn của người sai: người đọc nhầm ticket. **Sửa nhãn** H-081 thành FAIL, không sửa judge. Case này cho thấy nhãn người cũng cần kiểm tra chéo. |
| 8 | H-088 "Dạ, dạ, LogiX đã hoàn 40.000đ cho đơn O-233 ạ." | FAIL | PASS | Người (theo quy ước tôi chọn) | Lặp "Dạ" do lỗi gõ nhưng đủ ý. **Sửa rubric:** lỗi gõ nhỏ không làm trượt tone nếu lịch sự và đủ ý. Đây là quy ước do tôi chọn, chưa có bên thứ ba xác nhận. |
| 9 | H-094 "Da, LogiX da hoan 40.000đ cho don O-341, xin loi vi su bat tien." | PASS | FAIL | Người | Dịch máy, mất dấu tiếng Việt. **Sửa rubric:** FAIL khi reply không có dấu tiếng Việt. |
| 10 | H-070 "Dạ, LogiX đã hoàn 90.000đ cho đơn O-909 ạ 😂😂" | PASS | FAIL | Người | Emoji cười không phù hợp ngữ cảnh khiếu nại. **Sửa rubric:** cấm emoji trong reply khiếu nại. |

Thống kê trên 10 bất đồng của tone: người đúng 9, judge đúng 1 (#7). Judge tone thiên về PASS (6 trong 10 là bỏ sót lỗi, FN) và đây đúng với recall 0.8.

### Các ca bất đồng của helpful (nguyên nhân gốc)

Trong 21 ca judge cho PASS nhưng người chấm FAIL:

| Nhóm | Số ca | Ví dụ | Vì sao judge sai |
|---|---|---|---|
| Reply nói **số tiền khác ledger** (FM-08) | 18 | HL-015: reply 55.000đ, ledger ghi 40.000đ. HL-087: reply 60.000đ, ledger ghi 90.000đ | Judge chỉ đọc chữ trong reply. Nó không thấy ledger nên không thể biết số tiền sai. |
| Reply không có thông tin gì (cộc lốc, không nói số tiền, không nói kết quả) | 3 | HL-047, HL-091, HL-097: "Ok bạn, đơn O-xxx xử lý rồi nhé." | Câu có vẻ "trả lời xong" nên judge cho PASS, dù khách không biết kết quả. |

Ngược lại judge helpful không có ca nào cho FAIL sai (fp = 0). Vì vậy precision = 1.0, nhưng chỉ vì judge hầu như không dám gắn FAIL.

## Kết luận
- **Tiêu chí bị loại: `helpful`.** Ma trận nhầm lẫn tp=9, fp=0, fn=21, tn=70: judge chỉ bắt 9 trên 30 ca lỗi thật (recall 0.30, thấp hơn sàn 0.7) và κ=0.375 (thấp hơn sàn 0.6). Precision 1.0 không cứu được vì nó chỉ nói judge ít khi báo nhầm, không nói judge bắt được lỗi. Dùng nó làm gate sẽ cho lọt hầu hết các PR làm reply sai tiền. Rogan-Gladen cũng cho thấy: judge báo 9% FAIL, nhưng tỉ lệ lỗi thật ước tính là 30%, tức judge đánh giá thấp lỗi gần ba lần.
- **Không dùng judge cho tiền.** Reply sai số tiền (FM-08) là lỗi kiểm được bằng code: so số trong reply với ledger. Đây là việc của metric ở M3 (`reply_amount_matches_ledger`), không phải của judge. Quy tắc của lab: tiền và approval luôn chấm bằng code.
- **Tiêu chí được dùng: `tone_ok`** (κ=0.757, P=0.857, R=0.800), như tín hiệu phụ không blocking. Recall 0.8 nghĩa là còn khoảng 1 trong 5 lỗi tone bị bỏ sót.
- **Sửa rubric tone** từ 10 case trên: quy tắc xưng hô và đuôi câu (#1, #2), câu mệnh lệnh (#3), lời xin lỗi chỉ khi lỗi do LogiX (#4), cho phép thuật ngữ "refund" (#5), FAIL khi hứa ngoài kết quả hệ thống (#6), FAIL khi mất dấu tiếng Việt (#9), cấm emoji (#10), cho qua lỗi gõ nhỏ (#8). Sửa nhãn người H-081.
- **Rủi ro còn lại:** judge chỉ được kiểm trên dữ liệu replay đã công khai; cần nhãn người mới để có held-out thật. Nhãn người cũng có thể sai (H-081), và các quy ước ở #8 do tôi tự chọn.
