# OPC-OS — Tài liệu thiết kế giải pháp chi tiết

File chính: [`opc-os-thiet-ke-giai-phap.docx`](./opc-os-thiet-ke-giai-phap.docx) (≈ 42 trang A4, mã OPC-SDD-001 v1.0).

Thiết kế kỹ thuật cho nền tảng vận hành One Person Company bằng AI agent, bổ sung cho tài liệu chiến lược [`../giai-phap-one-person-company.docx`](../giai-phap-one-person-company.docx).

Nội dung: kiểm soát tài liệu · giới thiệu & phạm vi · mục tiêu đo lường, nguyên tắc kiến trúc · use case, FR/NFR · kiến trúc C4 (context, container) & ADR · thiết kế 10 thành phần · luồng xử lý (sequence, state) · dữ liệu (ERD, từ điển dữ liệu, DDL, phân loại) · REST API, CloudEvents, danh mục tool MCP · thiết kế agent (AgentSpec, model routing, eval) · bảo mật (STRIDE + LLM) · hạ tầng, CI/CD, sao lưu · SLO, cảnh báo, runbook · kiểm thử · kế hoạch triển khai 10 tuần · rủi ro · chi phí · phụ lục (compose, Rego, truy vết yêu cầu, cấu trúc repo).

## Sinh lại

```bash
# 1. Render sơ đồ (cần mermaid: npm pack mermaid@10.9.1 rồi giải nén, hoặc npm i mermaid@10.9.1)
MERMAID_JS=/path/to/mermaid.min.js node render.js   # diagrams/*.mmd -> img/*.png
# 02-container.png được chụp từ diagrams/02-container.html bằng Playwright
# 2. Tạo docx
node build-sdd.js opc-os-thiet-ke-giai-phap.docx
```
