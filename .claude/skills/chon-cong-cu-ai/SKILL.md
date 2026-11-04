---
name: chon-cong-cu-ai
description: Tư vấn chọn công cụ mã nguồn mở phù hợp cho một bài toán AI/dữ liệu (cào web, chuyển tài liệu sang Markdown/OCR, AI agent, deep research, coding agent, workflow automation, sinh ảnh, code intelligence) dựa trên 18 repo đã phân tích trong docs/solution-design. Dùng khi người dùng hỏi "nên dùng tool gì để…", "so sánh X và Y", "crawl/scrape trang này bằng gì", "chuyển PDF sang markdown bằng gì", "chọn agent nào", hoặc cần dựng pipeline kết hợp nhiều công cụ.
---

# Chọn công cụ AI phù hợp từ kho đã phân tích

Nguồn sự thật là thư mục `docs/solution-design/`. Không trả lời từ trí nhớ khi tài liệu có thông tin — đọc tài liệu liên quan trước.

## Quy trình

1. **Làm rõ bài toán** (chỉ hỏi những gì chưa rõ và thực sự ảnh hưởng lựa chọn):
   - Đầu vào: loại nguồn (website tĩnh/JS/có anti-bot, PDF số/scan, Office, ảnh, audio), số lượng, tần suất.
   - Đầu ra: Markdown cho RAG, JSON có schema, file, hành động trên trình duyệt, bài viết…
   - Ràng buộc: tự host hay dùng API, có GPU không, ngân sách LLM, license (dùng thương mại?), ngôn ngữ dự án (Python/TS).
2. **Đọc** `docs/solution-design/README.md` (bảng danh mục, bảng "So sánh nhanh", gợi ý chọn), rồi mở các tài liệu ứng viên — đặc biệt mục 2 (Ngoài phạm vi), 8 (Đánh đổi), 9 (Giới hạn đã biết).
3. **Đề xuất**: một lựa chọn chính + một phương án dự phòng, có lý do bám vào tài liệu.

## Bản đồ nhanh

| Nhu cầu | Ưu tiên | Khi nào chọn khác |
|---|---|---|
| Crawl quy mô lớn, cấu trúc rõ | Scrapy | Cần render JS → thêm Playwright hoặc dùng Crawl4AI |
| Site có anti-bot / hay đổi giao diện | Scrapling | — |
| Nạp web vào RAG/agent, tự host nhẹ | Crawl4AI | Cần API + hàng đợi + crawl phân tán → Firecrawl (lưu ý AGPL-3.0) |
| Trích xuất JSON bằng prompt, ít trang | Scrapegraph-ai | Nhiều trang → crawl bằng Crawl4AI rồi extract |
| Thao tác web như người (đăng nhập, điền form) | browser-use | — |
| Office/HTML/nhiều định dạng → Markdown nhanh | MarkItDown | Cần layout/bảng chính xác → Docling |
| PDF phức tạp: bảng, layout, reading order | Docling | PDF scan số lượng rất lớn, có GPU → olmOCR |
| Báo cáo nghiên cứu sâu nhiều nguồn | DeerFlow | Bài dài kiểu Wikipedia có trích dẫn → STORM |
| Trợ lý cá nhân có memory, chạy qua chat | Hermes Agent | — |
| Coding agent local | Codex CLI (sandbox mạnh) / Gemini CLI (policy TOML) / goose (đa provider, MCP) | Theo model đang dùng |
| Giảm token khi agent đọc codebase lớn | codebase-memory-mcp | — |
| Tự động hoá nghiệp vụ, tích hợp SaaS | n8n (lưu ý license fair-code) | — |
| Sinh ảnh/video bằng pipeline node | ComfyUI (GPL-3.0) | — |

## Pipeline ghép thường gặp

- **Web → RAG:** Crawl4AI/Firecrawl (Markdown) → chunk → vector DB; tài liệu đính kèm trên trang → MarkItDown/Docling.
- **Kho PDF doanh nghiệp → Q&A:** Docling (hoặc olmOCR cho scan) → `DoclingDocument` → chunker → RAG.
- **Agent nghiên cứu có công cụ:** DeerFlow/goose + MCP server của Crawl4AI, MarkItDown, Scrapling.
- **Tự động hoá định kỳ:** n8n gọi HTTP tới Firecrawl/Crawl4AI server, đẩy kết quả sang Sheets/Notion/Slack.

## Định dạng câu trả lời

```
**Khuyến nghị:** <công cụ> — <1 câu lý do>
**Dự phòng:** <công cụ> — khi <điều kiện>
**Lưu ý:** license / hạ tầng (GPU, Redis, Postgres…) / giới hạn đã biết
**Bắt đầu nhanh:** lệnh cài + 5–15 dòng code tối thiểu
**Đọc thêm:** link tới docs/solution-design/<repo>.md#mục
```

Nếu bài toán không khớp repo nào trong kho, nói rõ điều đó, rồi gợi ý công cụ ngoài kho và đề nghị dùng skill `solution-design` để phân tích thêm.
