---
name: ap-dung-pattern
description: Thiết kế hoặc review kiến trúc cho dự án riêng của người dùng bằng 8 pattern rút ra từ 18 repo AI mã nguồn mở đã phân tích (Strategy/Plugin, Pipeline + fallback, Graph thực thi, Agent loop + MCP, Lớp an toàn tách riêng, Control plane/worker qua hàng đợi, Biểu diễn trung gian thống nhất, Memory & skills cho agent). Dùng khi người dùng nói "thiết kế kiến trúc cho…", "áp dụng pattern", "học từ repo X để làm Y", "review kiến trúc", "làm sao để mở rộng/ổn định hệ thống AI của tôi".
---

# Áp dụng pattern kiến trúc từ kho đã phân tích

Nguồn: mục "Các pattern thiết kế lặp lại" trong `docs/solution-design/README.md` và mục 8, 10, 11 của từng tài liệu repo. Luôn trích dẫn repo + file cụ thể làm ví dụ tham chiếu.

## Quy trình

1. **Hiểu hệ thống cần thiết kế**: mục tiêu, đầu vào/đầu ra, quy mô, ràng buộc (ngôn ngữ, hạ tầng, đội ngũ). Nếu có code trong repo hiện tại, đọc nó trước.
2. **Chọn pattern** theo dấu hiệu ở bảng dưới — thường chỉ 2–4 pattern là đủ; không áp pattern chỉ để cho đủ.
3. **Đọc tài liệu ví dụ** của pattern đã chọn (mục 4 và 8) để lấy chi tiết hiện thực thật.
4. **Đề xuất thiết kế**: sơ đồ Mermaid `flowchart`, interface/khung code tối thiểu, bảng Quyết định / Lý do / Đánh đổi.

## Bảng pattern

| # | Pattern | Dấu hiệu nên dùng | Ví dụ tham chiếu | Cái giá |
|---|---|---|---|---|
| 1 | Strategy / Plugin ở mọi tầng | Nhiều biến thể của cùng một bước (nhiều nguồn, nhiều định dạng, nhiều LLM) | MarkItDown (`DocumentConverter` + priority), Crawl4AI (strategy cho fetch/markdown/extract), Scrapy (middleware) | Nhiều lớp trừu tượng; khó lần luồng khi debug |
| 2 | Pipeline + fallback | Bước dễ thất bại, có phương án rẻ/kém hơn | Firecrawl (chọn engine theo thứ tự), olmOCR (retry → xoay trang → `pdftotext`) | Kết quả không đồng nhất chất lượng; cần ghi lại phương án đã dùng |
| 3 | Graph thực thi | Luồng nhiều bước, cần hiển thị/lưu/chạy lại một phần | ComfyUI (cache theo input signature), n8n (DAG), DeerFlow (LangGraph) | Cần engine lập lịch, serialize state |
| 4 | Agent loop + tool qua MCP | LLM cần gọi công cụ, công cụ dùng lại giữa nhiều agent | goose, Codex, Gemini CLI, browser-use | Khó dự đoán chi phí/độ trễ; cần giới hạn số vòng |
| 5 | Lớp an toàn tách khỏi agent | Agent chạy lệnh, ghi file, gọi API có tác động | Codex (sandbox OS + approval), Gemini CLI (policy TOML), goose (inspector chain) | Thêm ma sát cho người dùng |
| 6 | Control plane / worker qua hàng đợi | Job dài, tải biến động, cần scale ngang | n8n queue mode (Bull + Redis), Firecrawl (Postgres/RabbitMQ), olmOCR (S3 queue) | Thêm hạ tầng; cần idempotency và retry |
| 7 | Biểu diễn trung gian thống nhất | Nhiều đầu vào × nhiều đầu ra | `DoclingDocument`, Markdown (MarkItDown/Crawl4AI), knowledge graph (codebase-memory-mcp) | Mất thông tin khi chuẩn hoá; schema phải ổn định |
| 8 | Memory & skills cho agent | Agent dùng lâu dài, lặp lại tác vụ | Hermes (memory, tự vá skills, FTS5), DeerFlow (skills Markdown) | Memory sai lệch tích luỹ; cần cơ chế xem/xoá |

## Kết hợp hay gặp

- **Pipeline xử lý tài liệu:** 1 + 2 + 7 (converter registry → fallback OCR → một model tài liệu chung).
- **Dịch vụ cào dữ liệu:** 1 + 2 + 6 (engine thay thế được, fallback, worker qua hàng đợi).
- **Agent nội bộ:** 4 + 5 + 8 (tool MCP, policy chặn hành động nguy hiểm, memory/skills).
- **Nền tảng workflow AI:** 3 + 6 (graph lưu được + worker scale ngang).

## Định dạng đầu ra

1. Tóm tắt 2–3 câu: pattern được chọn và vì sao.
2. Sơ đồ `flowchart` kiến trúc đề xuất.
3. Interface/khung code cho điểm mở rộng chính (ngôn ngữ của dự án).
4. Bảng Quyết định / Lý do / Đánh đổi.
5. Pattern **không** chọn và lý do (ngắn).
6. Link tới tài liệu tham chiếu trong `docs/solution-design/`.

Nếu người dùng muốn lưu thiết kế, ghi vào `docs/` của dự án họ, không ghi vào `docs/solution-design/` (thư mục đó chỉ dành cho repo đã fork).
