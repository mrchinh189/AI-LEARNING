# Tư duy xây "đội AI Agents" — Lauren Tan & Peng Zheng (Grok Bot, xAI)

| | |
|---|---|
| Video | [Tư duy đắt giá khi xây đội AI Agents của Lauren Tan & Peng Zeng (2 kỹ sư Grokbot) — Under30](https://www.youtube.com/watch?v=ToRL6DVKNGY) |
| Kênh | Under30 · đăng 2026-10-08 · 29:24 |
| Nguồn gốc | Bóc tách bài phỏng vấn 45 phút của Peter Yang: *"We Built Grok Bot. Here Are Our 14 Best Bots"* với Peng Zheng (Lead Design) và Lauren Tan (Head of Engineering) |
| Ghi chú lập | 2026-11-04, dựa trên transcript của video |

## 1. Ý chính

Có 3 cấp độ dùng AI:

1. **Tự làm thủ công** mọi thứ.
2. **Giao việc lẻ** cho AI, nhưng vẫn phải ra lệnh và giám sát từng bước — người dùng thành "nhân viên nối các bước" cho AI.
3. **Thiết kế một hệ thống AI**: một đội bot, mỗi bot có tên, vai trò, trí nhớ riêng và tự phối hợp. Con người lùi về vai trò *operator*.

Mục tiêu là chuyển từ "dùng AI cho từng task" sang "thiết kế hệ thống AI".

## 2. Sáu nguyên tắc

### 2.1. Có một bot quản lý ("Chief of Staff") nhận mọi yêu cầu

- Là bot đầu tiên được gọi khi chưa biết giao việc cho ai.
- Giao **cả một chuỗi việc trong một prompt**. Ví dụ của Peng khi bán micro DJI trên Facebook Marketplace: tra giá hàng mới trên trang chính hãng → dò giá rẻ nhất quanh khu vực → viết mô tả theo văn phong cũ của chủ → đăng bài → nếu không ai mua thì tự giảm giá mỗi tuần.
- Bot quản lý **biết hỏi bot khác**: đến bước viết mô tả, nó nhắn "writer bot" để lấy văn phong của Peng.
- Ví dụ khác: mua cuộn nhựa in 3D → tự đặt hàng → cập nhật số lượng tồn kho trong Notion.

### 2.2. Mỗi bot có tên, vai trò, trí nhớ riêng — và họp được trong group chat

- Bot là **"nhân sự" lâu dài** (persistent named agent) có identity, memory, tool riêng, không phải phiên chat dùng một lần rồi bỏ.
- Phần dùng lại được (năng lực, quy tắc phong cách) đưa vào core memory của bot. Mỗi dự án có deadline thì mở một chat riêng với bot đó.
- **Group chat nhiều bot**: Peng thả ý tưởng "app dịch tiếng mèo sang tiếng Anh" vào nhóm có bot PM, designer, engineer; các bot tự thảo luận, phản biện nhau. Tag `@bot` để hỏi riêng một bot; nhắn chung thì mỗi bot tự quyết có trả lời từ góc nhìn của mình hay không.
- Lauren có **"Dr. X bot" chuyên thiết kế bot khác**: định kỳ đọc lịch sử chat với từng bot, báo bot nào yếu ở đâu, cần thêm skill gì, bot nào ôm quá nhiều việc nên tách đôi, lịch chạy nào quá dày gây lãng phí tài nguyên.
- Lý do: nhồi quá nhiều chức năng vào một bot thì memory bị loãng, làm việc lộn xộn.

### 2.3. Việc gì lặp lại thì đóng gói thành quy trình

- Nguyên tắc: việc phải làm tay lần thứ 3–4 là tín hiệu cần dựng quy trình.
- Ví dụ của Peng: chụp một sạp rau ở Chinatown (San Francisco) → biến thành mô hình đất sét 3D → đăng lên website cá nhân. Từ đó dựng pipeline "check-in map": gửi bot ảnh địa điểm + tag tài khoản người đi cùng → bot sinh 2 ảnh (sáng/tối), xoá nền, đăng thẳng lên website.
- Bot tự lấy hướng dẫn quy trình mới nhất từ cơ sở dữ liệu cá nhân, không cần nhắc lại mỗi lần.
- Khung chat với bot trở thành **dashboard chính**, không phải đăng nhập trang admin.

### 2.4. Bot phải tự kiểm tra trước khi nộp (Lauren coi đây là quan trọng nhất)

- Nếu phải tự đọc soát từng chữ thì AI chưa thật sự tiết kiệm công sức.
- Lauren cho bot điều khiển trực tiếp máy ảo Linux trên máy mình: tự cài đặt, tự chạy, tự kiểm tra lỗi.
- Khi cập nhật skill: có một **eval playbook** — agent spawn nhiều subagent chạy các model khác nhau, thử prompt, đối chiếu với mục tiêu ban đầu; chỉ khi đạt mới "land" thay đổi.
- Áp dụng: đưa cho AI **bộ tiêu chí chấm** (VD: hook cuốn hút, dưới 300 chữ, không dùng sáo ngữ) và yêu cầu tự chấm, không đạt thì tự sửa trước khi nộp.

### 2.5. Đội lớn thì bot trưởng chỉ phân việc, không tự làm — "bếp Michelin"

- Bot tech lead của Lauren có quy tắc ghi rõ trong mô tả: **không bao giờ tự code**, chỉ chia nhỏ việc, giao cho các bot kỹ sư và theo dõi tiến độ.
- Luồng: bot văn phòng lập kế hoạch tổng trên Notion → chia giai đoạn → chuyển phần kỹ thuật cho bot lead → bot lead chia tiếp cho đội bot kỹ sư.
- Codebase được thiết kế **agent-friendly** đến mức nhiều PR được auto-merge; Lauren đôi khi chỉ xem PR sau khi đã merge.
- Lauren không thích chữ "software factory" (gợi cảm giác hàng loạt, kém chất lượng). Hình mẫu là **bếp Michelin**: giữ chất lượng thủ công nhưng phục vụ 50–100 khách cùng lúc.
- Bài học: **chốt tiêu chuẩn chất lượng trước, rồi mới tăng quy mô**. Muốn "nhắm mắt cho chạy" thì nền móng (tự kiểm tra, vai trò rõ, workspace gọn) phải thật chắc.

### 2.6. Trao quyền từng bước

- Không có ngày "bật công tắc một lần là xong"; chỉ giao việc tương xứng với mức tin tưởng.
- Ví dụ: Lauren nhờ bot "Suki" đặt vé máy bay và khách sạn cho chuyến công tác London–Amsterdam từ link Slack, yêu cầu **đề xuất trước, chưa được đặt khi chưa duyệt**. Bot lo phần tìm kiếm, so sánh; quyết định chi tiền vẫn ở con người.
- Công thức huấn luyện: **quan sát bot làm → sửa ngay khi lệch → đóng gói thành skill** (VD `/expense-report`) → lặp đến khi gõ một lệnh là ra kết quả đúng → lúc đó mới cho chạy tự động (VD: có email hoá đơn thì tự lập báo cáo chi phí).
- Peng: bắt đầu từ việc đơn giản → việc lặp lại → lên lịch cho bot tự chạy → tối ưu nếu tốn tài nguyên.
- Giống nhận nhân viên mới: không ai đổ cả đống việc rồi bỏ đi ngay.

## 3. Áp dụng thực tế (gợi ý trong video)

Với bán hàng / sáng tạo nội dung, tách bot theo chuyên môn, mỗi bot nhớ đúng một kho kiến thức:

| Bot | Nhiệm vụ |
|---|---|
| Bot mô tả sản phẩm | Viết mô tả bán hàng, giọng chốt đơn |
| Bot kịch bản video | Giỏi tạo hook, kịch tính |
| Bot phân tích quảng cáo | Chỉ đọc và phân tích số liệu ads |
| Bot quản lý | Nhận yêu cầu, chia việc cho các bot trên, kiểm chất lượng |

**Bài tập khởi đầu** (đừng dựng 10 bot một lúc): chọn **một** quy trình làm hàng tuần, viết ra giấy:

1. Các bước cụ thể từ A đến Z để hoàn thành nó.
2. Thế nào là kết quả đạt — đây chính là tiêu chí để AI tự chấm sau này.

## 4. Liên hệ với các repo trong kho này

Những ý tưởng trên đã xuất hiện trong kiến trúc của một số repo đã phân tích ở [`docs/solution-design`](../solution-design/README.md):

| Nguyên tắc | Repo liên quan |
|---|---|
| Bot quản lý điều phối sub-agent (2.1, 2.5) | [DeerFlow](../solution-design/deer-flow.md) (lead agent + sub-agent), [goose](../solution-design/goose.md) (subagent) |
| Agent có memory, tự tạo/vá skill, chạy cron (2.2, 2.6) | [Hermes Agent](../solution-design/hermes-agent.md) |
| Nhiều góc nhìn thảo luận (group chat) (2.2) | [STORM](../solution-design/storm.md) (hỏi–đáp đa góc nhìn, Co-STORM) |
| Đóng gói quy trình lặp lại (2.3) | [n8n](../solution-design/n8n.md), recipe của [goose](../solution-design/goose.md) |
| Approval trước hành động rủi ro (2.6) | [Codex CLI](../solution-design/codex.md) (approval policy), [Gemini CLI](../solution-design/gemini-cli.md) (policy engine) |

## 5. Tham khảo

- Video tóm tắt (tiếng Việt): https://www.youtube.com/watch?v=ToRL6DVKNGY
- Phỏng vấn gốc: Peter Yang — *"We Built Grok Bot. Here Are Our 14 Best Bots | Peng Zheng & Lauren Tan"*
