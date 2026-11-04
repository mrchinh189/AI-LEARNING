# Sáu nguyên tắc xây đội AI agent

Rút ra từ buổi phỏng vấn của Peter Yang với Lauren Tan (Head of Engineering) và Peng Zheng (Lead Design) — đội Grok Bot, xAI. Dùng file này để giải thích cho người dùng *vì sao* đội được thiết kế như vậy, và để đánh giá một thiết kế đội họ đề xuất.

## Ba cấp độ dùng AI

1. Tự làm thủ công.
2. Giao việc lẻ cho AI, vẫn tự nối các bước và giám sát từng bước.
3. Thiết kế một hệ thống AI: đội bot có tên, vai trò, trí nhớ, tự phối hợp. Người dùng thành người vận hành.

Skill này đưa người dùng từ cấp 2 lên cấp 3 — nhưng từng bước (nguyên tắc 6).

## 1. Bot quản lý nhận cả chuỗi việc

Ví dụ của Peng: chụp ảnh micro cũ, giao một lệnh cho bot "Chief of Staff": tra giá mới chính hãng → dò giá rẻ nhất khu vực → nhờ bot giữ văn phong viết tin → đăng → không ai mua thì giảm giá mỗi tuần. Bot quản lý biết hỏi bot khác.

**Trong code:** bot `manager` trong `team.json`, tool `delegate`. Viết `task` khi giao việc phải đủ bối cảnh vì bot con không thấy hội thoại của bot cha.

## 2. Mỗi bot có tên, vai trò, trí nhớ — họp được trong nhóm

Bot là nhân sự lâu dài, không phải phiên chat dùng một lần. Phần dùng lại được (văn phong, quy ước) nằm trong trí nhớ của bot; mỗi dự án có phòng/phiên riêng. Group chat: ném ý tưởng vào, các bot PM/designer/engineer tự bàn và phản biện; `@tên` để hỏi riêng.

Lauren có "Dr. X" chuyên thiết kế bot khác: nhồi quá nhiều chức năng vào một bot làm trí nhớ loãng, làm việc lộn xộn — nên tách.

**Trong code:** `role` hẹp, `memory/<bot>.md`, nhật ký việc gần đây trong system prompt, `room.py`, `doctor.py`.

## 3. Việc lặp lại → quy trình

Việc làm tay lần thứ 3–4 là tín hiệu cần dựng quy trình. Ví dụ của Peng: ảnh địa điểm → ảnh đất sét 3D sáng/tối → xoá nền → đăng lên website, chỉ bằng một tin nhắn.

**Trong code:** skill Markdown (`## Mô tả`, `## Các bước`, `## Tiêu chí đạt`), `--skill`, `load_skill`, `save_skill`.

## 4. Bot tự kiểm tra trước khi nộp (Lauren coi là quan trọng nhất)

Nếu phải tự đọc soát từng chữ thì AI chưa tiết kiệm được gì. Lauren cho bot tự chạy máy ảo để kiểm tra; khi sửa skill thì chạy eval nhiều model, chỉ "land" khi đạt mục tiêu.

**Trong code:** grader độc lập chấm theo rubric, chưa đạt thì bot tự sửa (tối đa 3 lần). Rubric tốt = mỗi dòng một tiêu chí kiểm được ("dưới 300 chữ", "có nguồn cho mọi con số"), không phải "viết hay".

## 5. Trưởng nhóm chỉ phân việc — "bếp Michelin"

Bot tech lead của Lauren có quy tắc "không bao giờ tự code", chỉ chia việc cho bot kỹ sư và theo dõi. Lauren không thích chữ "software factory" (gợi hàng loạt, kém chất lượng): hình mẫu là bếp Michelin — chất lượng thủ công ở quy mô 50–100 khách. Chốt tiêu chuẩn chất lượng trước rồi mới tăng số lượng.

**Trong code:** `delegate_only: true` — không cấp tool làm việc, chặn khi nạp cấu hình và khi chạy.

## 6. Trao quyền từng bước

Không có ngày "bật công tắc một lần là xong". Lauren nhờ bot đặt vé máy bay + khách sạn nhưng yêu cầu đề xuất trước, chưa được đặt khi chưa duyệt. Công thức: quan sát bot làm → sửa ngay khi lệch → đóng gói thành skill → lặp đến khi một lệnh ra kết quả đúng → mới cho chạy tự động. Giống nhận nhân viên mới.

**Trong code:** cổng duyệt cho `publish`, `purchase`, `save_skill` ở tầng code; `ask_human`; lộ trình 5 giai đoạn (chuẩn bị → quan sát → đóng gói → mở rộng đội → tự động).

## Bài tập khởi đầu cho người dùng

Đừng dựng 10 bot một lúc. Chọn **một** quy trình làm hằng tuần, viết ra:

1. Các bước cụ thể từ A đến Z.
2. Thế nào là kết quả đạt — đây chính là rubric để bot tự chấm.
