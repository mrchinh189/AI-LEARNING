---
name: solution-design
description: Viết tài liệu thiết kế giải pháp (solution design) tiếng Việt cho một repo GitHub đã fork, theo template 12 mục của kho AI-LEARNING, dựa trên mã nguồn thật tại một commit cụ thể, rồi thêm vào danh mục. Dùng khi người dùng nói "phân tích repo X", "viết solution design cho X", "thêm repo mới vào tài liệu", "tài liệu kiến trúc cho repo đã fork", hoặc đưa link GitHub và muốn hiểu kiến trúc.
---

# Viết tài liệu thiết kế giải pháp cho repo đã fork

Đầu ra: `docs/solution-design/<repo>.md` + một dòng trong bảng danh mục `docs/solution-design/README.md`. Tài liệu mẫu tốt để đối chiếu văn phong: `docs/solution-design/markitdown.md`, `docs/solution-design/crawl4ai.md`.

## Quy trình

### 1. Xác định repo
- Fork nằm dưới `mrchinh189/<repo>`; tìm upstream từ trang fork (trường "forked from") hoặc hỏi người dùng nếu không rõ.
- Bỏ qua repo dạng `awesome-*`, skill pack, prompt, khóa học — nằm ngoài phạm vi bộ tài liệu (xem README danh mục).
- Kiểm tra file `docs/solution-design/<repo>.md` đã tồn tại chưa; nếu có thì đây là việc **cập nhật**, giữ cấu trúc và ghi commit mới.

### 2. Lấy mã nguồn tại một commit cố định
Clone nông vào scratchpad (không clone vào repo này):

```bash
git clone --depth 1 https://github.com/mrchinh189/<repo>.git <scratchpad>/<repo>
git -C <scratchpad>/<repo> rev-parse --short HEAD
```

Nếu clone bị chặn, dùng GitHub MCP (`get_file_contents`) để đọc từng file. Ghi lại sha ngắn — đây là **Commit đã phân tích**.

### 3. Đọc mã nguồn theo thứ tự
1. `README*`, `docs/`, `ARCHITECTURE*`, `CONTRIBUTING*` — mục đích, khái niệm.
2. Manifest (`pyproject.toml`, `package.json`, `Cargo.toml`, `go.mod`, `Dockerfile`, `docker-compose*`) — tech stack, entry point, extras.
3. Entry point (CLI `__main__`, `bin/`, server `main`) → lần theo luồng chính đến lõi.
4. Các interface/base class, registry, plugin loader — đây là nguồn cho mục 4, 6, 10.
5. `LICENSE` — ghi đúng SPDX; nêu điều khoản đặc biệt bằng chú thích `*`.

Với repo lớn, giao việc đọc từng vùng cho subagent `Explore` và chỉ giữ kết luận + đường dẫn file.

### 4. Viết theo template
Copy `docs/solution-design/_TEMPLATE.md` và điền đủ 12 mục, giữ nguyên tên mục:

| Mục | Yêu cầu |
|---|---|
| Header | Fork, Upstream (link), Nhóm (một trong: Web scraping, AI Agent, AI coding agent, Xử lý tài liệu, Nền tảng workflow, Code intelligence), Ngôn ngữ chính, License, sha |
| 1. Tóm tắt | 2–4 câu: bài toán, cho ai, điểm khác biệt cốt lõi |
| 2. Bài toán & yêu cầu | 4 gạch đầu dòng: Bài toán / chức năng / phi chức năng / ngoài phạm vi |
| 3. Kiến trúc tổng thể | `flowchart` có `subgraph` theo lớp, nhãn ghi kèm đường dẫn file (`<br/>`), + 1 đoạn giải thích |
| 4. Thành phần chính | Bảng Thành phần / Vị trí / Trách nhiệm với **đường dẫn thật**, rồi mô tả sâu 3–5 thành phần quan trọng nhất |
| 5. Luồng xử lý chính | 1–2 `sequenceDiagram` cho luồng tiêu biểu |
| 6. Mô hình dữ liệu & giao diện | Data class/schema, API, CLI flag, file cấu hình, giao thức (REST/MCP/JSON-RPC) |
| 7. Tech stack | Bảng Lớp / Công nghệ / Vai trò |
| 8. Quyết định & đánh đổi | Bảng Quyết định / Lý do / Đánh đổi — cột Đánh đổi không được trống |
| 9. Triển khai & vận hành | Cài đặt, Docker, cấu hình, quan sát, giới hạn đã biết |
| 10. Điểm mở rộng | Plugin/hook/provider và cách thêm mới |
| 11. Bài học & cách áp dụng | Pattern in đậm + cách tái dùng cho dự án riêng |
| 12. Tham khảo | README, manifest, file nguồn chính, link upstream |

Quy tắc viết:
- Tiếng Việt, câu ngắn; tên class/hàm/file/flag để trong backtick, giữ nguyên tiếng Anh.
- Chỉ viết điều đã thấy trong mã. Không chắc thì ghi "(chưa xác minh)" thay vì đoán.
- Nếu fork chậm hơn upstream đáng kể (version cũ), ghi chú ở mục 9.

### 5. Cập nhật danh mục
Trong `docs/solution-design/README.md`:
- Thêm một dòng vào bảng đúng nhóm: `| [Tên](./<repo>.md) | owner/repo | Ngôn ngữ | License | Tóm tắt 1 câu |`.
- Tăng số "của N repo" ở đầu file và ở `README.md` gốc.
- Nếu repo thuộc nhóm có bảng "So sánh nhanh", thêm một cột; nếu repo thể hiện một pattern trong "Các pattern thiết kế lặp lại", thêm tên repo vào pattern đó.

### 6. Kiểm tra
Chạy skill `kiem-tra-tai-lieu` (script `check_docs.mjs`) cho toàn bộ thư mục; phải ra `✓ N tài liệu hợp lệ.` trước khi commit.

### 7. Commit
Một commit cho mỗi repo (hoặc mỗi nhóm), message theo lịch sử kho: `docs: add solution design for <repo>`.
