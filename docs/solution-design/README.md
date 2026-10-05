# Tài liệu thiết kế giải pháp — các repo đã fork

Bộ tài liệu phân tích kiến trúc và thiết kế giải pháp của 18 repo mã nguồn chính mà [mrchinh189](https://github.com/mrchinh189) đã fork. Mỗi tài liệu được viết dựa trên mã nguồn thật tại một commit cụ thể và theo cùng một cấu trúc 12 mục (xem [`_TEMPLATE.md`](./_TEMPLATE.md)):

1. Tóm tắt · 2. Bài toán & yêu cầu · 3. Kiến trúc tổng thể · 4. Thành phần chính · 5. Luồng xử lý chính · 6. Mô hình dữ liệu & giao diện · 7. Tech stack · 8. Quyết định thiết kế & đánh đổi · 9. Triển khai & vận hành · 10. Điểm mở rộng · 11. Bài học & cách áp dụng · 12. Tham khảo

Các repo dạng danh sách (`awesome-*`), skill pack, prompt và khóa học không nằm trong phạm vi bộ tài liệu này.

## Danh mục

### 1. Web scraping / crawling

| Repo | Upstream | Ngôn ngữ | License | Tóm tắt |
|---|---|---|---|---|
| [Scrapling](./scrapling.md) | D4Vinci/Scrapling | Python | BSD-3-Clause | Parser tự định vị lại phần tử khi website đổi giao diện, fetcher HTTP/trình duyệt stealth vượt anti-bot, Spider async có pause/resume và MCP server. |
| [Firecrawl](./firecrawl.md) | firecrawl/firecrawl | TypeScript (+ Rust, Go) | AGPL-3.0 | Web Data API biến website thành Markdown/JSON cho LLM, có chọn engine kèm fallback, pipeline transformer, hàng đợi Postgres/RabbitMQ và crawl phân tán. |
| [Crawl4AI](./crawl4ai.md) | unclecode/crawl4ai | Python | Apache-2.0* | Crawler async trên Playwright, dùng Strategy pattern ở mọi tầng, sinh "fit markdown", trích xuất CSS/LLM, deep crawl và Docker server (REST + MCP). |
| [Scrapegraph-ai](./scrapegraph-ai.md) | ScrapeGraphAI/Scrapegraph-ai | Python | MIT | Trích xuất dữ liệu có cấu trúc bằng prompt, qua graph các node (Fetch → Parse → GenerateAnswer), dùng nhiều LLM provider qua LangChain. |
| [Scrapy](./scrapy.md) | scrapy/scrapy | Python | BSD-3-Clause | Framework crawl bất đồng bộ trên Twisted/asyncio: Engine điều phối Scheduler, Downloader, Spider, Item Pipeline; mở rộng qua middleware, extension và signal. |

### 2. AI Agent / Deep research

| Repo | Upstream | Ngôn ngữ | License | Tóm tắt |
|---|---|---|---|---|
| [browser-use](./browser-use.md) | browser-use/browser-use | Python | MIT | LLM điều khiển Chromium qua CDP theo vòng lặp quan sát → suy luận → hành động, kiến trúc event bus + watchdog. |
| [DeerFlow](./deer-flow.md) | bytedance/deer-flow | Python + TypeScript | MIT | "Super agent harness" trên LangGraph: lead agent điều phối sub-agent, sandbox theo thread, long-term memory và skills để nghiên cứu sâu. |
| [STORM](./storm.md) | stanford-oval/storm | Python | MIT | Dựa trên DSPy, viết bài dài kiểu Wikipedia có trích dẫn bằng hội thoại hỏi–đáp đa góc nhìn; Co-STORM cho người dùng cộng tác cùng agent. |
| [Hermes Agent](./hermes-agent.md) | NousResearch/hermes-agent | Python + TypeScript | MIT | Agent cá nhân "tự cải thiện" trên CLI/TUI và gateway chat, có memory, tự tạo/vá skills, tìm hội thoại cũ bằng FTS5, cron và sub-agent. |

### 3. AI coding agent / CLI

| Repo | Upstream | Ngôn ngữ | License | Tóm tắt |
|---|---|---|---|---|
| [goose](./goose.md) | aaif-goose/goose | Rust + TypeScript | Apache-2.0 | Agent local (CLI, desktop, server) kết nối 15+ LLM provider, toàn bộ tool đến từ MCP extension; có recipe, scheduler, subagent và inspector an toàn. |
| [Codex CLI](./codex.md) | openai/codex | Rust | Apache-2.0 | Coding agent chạy local với sandbox cấp OS (Seatbelt/bubblewrap/Windows), approval policy, core dạng hàng đợi Submission/Event bọc bởi app-server JSON-RPC. |
| [Gemini CLI](./gemini-cli.md) | google-gemini/gemini-cli | TypeScript | Apache-2.0 | Tách `cli` (Ink UI) khỏi `core` (agent loop, scheduler, policy engine TOML, hooks, MCP), sandbox nhiều backend, tích hợp IDE qua ACP. |

### 4. Xử lý tài liệu / Document AI

| Repo | Upstream | Ngôn ngữ | License | Tóm tắt |
|---|---|---|---|---|
| [Docling](./docling.md) | docling-project/docling | Python | MIT | Chuyển PDF, Office, HTML, ảnh, audio thành `DoclingDocument` qua pipeline đa luồng (layout, OCR, table, reading order, VLM), xuất Markdown/JSON/DocTags. |
| [MarkItDown](./markitdown.md) | microsoft/markitdown | Python | MIT | Chuyển nhiều loại file/URL sang Markdown cho LLM bằng chuỗi converter theo priority và nhận diện nội dung bằng Magika; có plugin và MCP server. |
| [olmOCR](./olmocr.md) | allenai/olmocr | Python | Apache-2.0 | VLM 7B (fine-tune Qwen2.5-VL, chạy vLLM) chuyển PDF thành Markdown ở quy mô hàng triệu trang, work queue trên S3, fallback `pdftotext`. |

### 5. Nền tảng workflow & Code intelligence

| Repo | Upstream | Ngôn ngữ | License | Tóm tắt |
|---|---|---|---|---|
| [n8n](./n8n.md) | n8n-io/n8n | TypeScript | Sustainable Use (fair-code) | Workflow automation tự host với 400+ integration và AI agent; mở rộng ngang bằng queue mode (Bull + Redis) với main/worker/webhook tách biệt. |
| [ComfyUI](./comfyui.md) | comfyanonymous/ComfyUI | Python | GPL-3.0 | Engine node graph cho AI sinh ảnh/video/audio, sắp xếp topo và chỉ chạy lại node thay đổi nhờ cache theo input signature, quản lý VRAM thông minh. |
| [codebase-memory-mcp](./codebase-memory-mcp.md) | DeusData/codebase-memory-mcp | C | MIT | MCP server index codebase thành knowledge graph (tree-sitter + LSP, lưu SQLite), cung cấp tool truy vấn cấu trúc giúp coding agent tốn ít token hơn. |

\* Crawl4AI: Apache-2.0 kèm điều khoản bắt buộc ghi công ở cuối `LICENSE`.

## So sánh nhanh theo nhóm

### Web scraping

| Tiêu chí | Scrapy | Scrapling | Crawl4AI | Firecrawl | Scrapegraph-ai |
|---|---|---|---|---|---|
| Hình thức | Framework | Thư viện | Thư viện + server | Dịch vụ API (self-host) | Thư viện |
| Render JS | Qua plugin | Có (stealth browser) | Có (Playwright) | Có (nhiều engine) | Có (qua loader) |
| Đầu ra cho LLM | Không chuyên | Markdown/MCP | Markdown + extraction | Markdown/JSON | JSON theo prompt |
| Dùng LLM trong lõi | Không | Không (tùy chọn qua MCP) | Tùy chọn | Tùy chọn (extract) | Bắt buộc |
| Quy mô | Rất lớn (1 process, async) | Vừa | Vừa (1 node) | Lớn (phân tán, hàng đợi) | Nhỏ |

**Gợi ý chọn:** crawl quy mô lớn có cấu trúc rõ → Scrapy; site có anti-bot hoặc hay đổi giao diện → Scrapling; nạp dữ liệu web vào RAG/agent → Crawl4AI (tự host nhẹ) hoặc Firecrawl (cần API, hàng đợi); trích xuất nhanh bằng prompt cho ít trang → Scrapegraph-ai.

### AI coding agent

| Tiêu chí | Codex CLI | Gemini CLI | goose |
|---|---|---|---|
| Ngôn ngữ lõi | Rust | TypeScript | Rust |
| Model | OpenAI (chính) | Gemini | 15+ provider |
| Tool | Built-in + MCP | Built-in + MCP | Toàn bộ qua MCP extension |
| An toàn | Sandbox OS + approval + execpolicy | Policy engine TOML + sandbox | Inspector chain + permission |
| Giao diện | TUI, IDE, desktop, SDK | Ink TUI, IDE (ACP) | CLI, desktop, server |

## Các pattern thiết kế lặp lại

Đọc chéo 18 tài liệu, có một số pattern xuất hiện nhiều lần và có thể áp dụng cho dự án riêng:

1. **Strategy / Plugin ở mọi tầng**: Crawl4AI, Scrapy, MarkItDown, Docling, ComfyUI. Mỗi bước xử lý là một interface có thể thay thế, nên mở rộng mà không phải sửa lõi.
2. **Pipeline + fallback**: Firecrawl (chọn engine theo thứ tự), olmOCR (retry, xoay trang rồi fallback `pdftotext`), MarkItDown (converter theo priority). Thử phương án tốt nhất trước, lùi dần khi thất bại.
3. **Graph thực thi**: ComfyUI (node graph + cache theo input), Scrapegraph-ai (graph node), DeerFlow (LangGraph), n8n (workflow DAG). Biểu diễn luồng xử lý dưới dạng dữ liệu để dễ hiển thị, lưu và chạy lại một phần.
4. **Agent loop + tool qua MCP**: goose, Codex, Gemini CLI, browser-use, Hermes. Vòng lặp model → tool call → quan sát, tool được chuẩn hóa qua MCP để dùng lại giữa các agent.
5. **Lớp an toàn tách riêng khỏi agent**: sandbox OS (Codex), policy engine (Gemini CLI), inspector chain (goose). Quyết định cho phép hay chặn một hành động nằm ngoài model.
6. **Tách control plane / worker bằng hàng đợi**: n8n (queue mode), Firecrawl (Postgres/RabbitMQ), olmOCR (work queue trên S3). Cách mở rộng ngang phổ biến nhất.
7. **Biểu diễn trung gian thống nhất**: `DoclingDocument`, Markdown trong MarkItDown và Crawl4AI, knowledge graph trong codebase-memory-mcp. Chuẩn hóa đầu vào đa dạng về một model rồi mới xuất ra các định dạng.
8. **Memory & skills cho agent**: Hermes (memory, tự vá skills, FTS5), DeerFlow (long-term memory, skills Markdown), codebase-memory-mcp (bộ nhớ cấu trúc về code).

## Ghi chú

- Mỗi tài liệu ghi rõ **commit đã phân tích**. Fork có thể chậm hơn upstream (ví dụ n8n đang ở bản 1.77.0), nên hãy đối chiếu với upstream trước khi dựa vào chi tiết.
- Toàn bộ sơ đồ Mermaid đã được kiểm tra bằng parser `mermaid@11`.
- Để thêm repo mới: copy [`_TEMPLATE.md`](./_TEMPLATE.md) thành `<repo>.md`, điền theo mã nguồn thật, rồi thêm một dòng vào bảng danh mục ở trên.
