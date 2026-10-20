# Rà soát & hướng dẫn cài AI Skill / Plugin cho Business Analyst

> Hồ sơ công việc: IT BA + BA nghiệp vụ/quy trình + Data/BI + PO/PM.
> Nền tảng: Claude.ai/Desktop, Claude Cowork, Claude Code.
> Nhu cầu: viết tài liệu yêu cầu, vẽ sơ đồ/wireframe, họp & giao tiếp, phân tích dữ liệu.
> Ngày rà soát: 20/10/2026 (đã tải mã nguồn từng repo về đọc).

## 1. Kết quả rà soát

| # | Bộ skill | Nguồn | Giấy phép | Cập nhật | Nội dung chính | Đánh giá an toàn | Khuyến nghị |
|---|---|---|---|---|---|---|---|
| 1 | **Anthropic Knowledge-Work Plugins** (product-management, operations, data, design, productivity) | [anthropics/knowledge-work-plugins](https://github.com/anthropics/knowledge-work-plugins) | Chính thức | Liên tục | Spec/PRD, tổng hợp research, sprint, stakeholder update, tài liệu quy trình, change request, SQL, dashboard | Chính thức của Anthropic | ✅ **Cài trước tiên** |
| 2 | **ClauKit / KitForge – BA Kit** (tác giả Việt, tiếng Việt) | [trungdo9/ClauKit](https://github.com/trungdo9/ClauKit) | MIT | 14/10/2026 | Chuỗi PRD → SRS → FR/NFR/UC/US/AC/TC/CR → truy vết (traceability) → UAT, nghiệm thu, go-live; sơ đồ Mermaid (sequence, flow, state, ERD) | Không thấy mã gọi mạng trong hooks. **Lưu ý:** `ck init` cài thêm hook (chặn lệnh nguy hiểm, bảo vệ branch), statusline và ghi vào `CLAUDE.md`, `.claude/settings.json` | ✅ **Rất hợp với IT BA**, chỉ dùng cho Claude Code |
| 3 | **PM Skills** (Paweł Huryn) – 69 skill, 9 plugin | [phuryn/pm-skills](https://github.com/phuryn/pm-skills) | MIT | 16/10/2026 | `user-stories` (3C + INVEST), `job-stories`, `create-prd`, `test-scenarios`, `stakeholder-map`, `summarize-meeting`, `sql-queries`, `cohort-analysis`, `customer-journey-map`, `user-personas`, `prioritize-features`, `interview-script` | Chỉ có 3 script (kiểm tra plugin), gần như thuần Markdown | ✅ **Cài cho PO/BA** |
| 4 | **PlausibleBA** – 6 skill business architecture | [plausibleba/ba-skills](https://github.com/plausibleba/ba-skills) | CC BY-SA 4.0 | 24/09/2026 | Capability map, concept model, value stream, operating-model context theo BABOK/BIZBOK; xuất XLSX + JSON | Không có script | ✅ **Cài cho BA nghiệp vụ/quy trình** |
| 5 | **Product Manager Skills** (Dean Peters) – 77 skill | [deanpeters/product-manager-skills](https://github.com/deanpeters/product-manager-skills) | CC BY-NC-SA 4.0 (**phi thương mại**) | 15/10/2026 | `user-story`, `user-story-splitting`, `user-story-mapping`, `epic-breakdown-advisor`, `prd-development`, `stakeholder-mapping`, `jobs-to-be-done`, `workshop-facilitation` | Có app Python tuỳ chọn cần API key, không bắt buộc | ⚠️ Tuỳ chọn, xem lại điều kiện giấy phép nếu dùng cho công ty |
| 6 | **b33eep/claude-code-setup – user-stories** | [b33eep/claude-code-setup](https://github.com/b33eep/claude-code-setup) | MIT | 05/10/2026 | User story INVEST + Given-When-Then | Bộ cài đầy đủ dùng `curl \| bash` và cài nhiều thứ cho lập trình viên | ⚠️ Chỉ chép riêng thư mục `skills/user-stories`, **không** chạy installer |
| 7 | Skill chia sẻ trong nhóm Facebook (BA-Kit Hoàng PM, INVEST & Use Case của BA Zone, Product Discovery) | Link trong [README.md](README.md) | Chưa rõ | — | User story, use case, SRS, wireframe | **Chưa rà soát được** (không mở được bài Facebook, không tìm thấy repo công khai) | ⏸️ Lấy link repo từ bài gốc rồi rà soát trước khi cài |

## 2. Bộ cài khuyến nghị theo nhu cầu

| Nhu cầu | Claude.ai / Cowork | Claude Code |
|---|---|---|
| Tài liệu yêu cầu (BRD/SRS/UC/US/AC) | `product-management` (write-spec) + PM Skills `pm-execution` | **ClauKit BA Kit** (`/ba:prd`, `/ba:spec`, `/ba:qc gap`) + PM Skills |
| Sơ đồ / wireframe | Connector Lucid, Mermaid Chart, Figma/FigJam, Miro | ClauKit `/ba:diagram` (Mermaid/HTML) + plugin `figma` |
| Kiến trúc nghiệp vụ / quy trình | PlausibleBA + `operations` (process-doc, process-optimization) | Như bên trái |
| Họp & giao tiếp | `product-management` (stakeholder-update), PM Skills `summarize-meeting`, `stakeholder-map`; connector Google Calendar/Gmail/Slack | Như bên trái |
| Phân tích dữ liệu | Plugin `data` (analyze, write-query, build-dashboard) + PM Skills `pm-data-analytics` | Như bên trái |

## 3. Hướng dẫn cài đặt

### 3.1 Claude Cowork / Claude.ai / Desktop

1. Mở **Customize** (góc dưới bên trái) → **Plugins / Browse plugins**.
2. **Plugin chính thức của Anthropic:** bật `product-management`, `operations`, `data`, `design`, `productivity`.
3. **Thêm marketplace từ GitHub:** **Personal → + → Add marketplace from GitHub**, rồi nhập lần lượt:
   - `phuryn/pm-skills`: chọn tối thiểu `pm-execution`, `pm-product-discovery`, `pm-market-research`, `pm-data-analytics`, `pm-toolkit`.
   - `plausibleba/ba-skills`: chọn **PlausibleBA — Business Architecture Skills**.
4. **Connector** (Settings → Connectors): Lucid hoặc Miro, Figma, Mermaid Chart; thêm Google Drive/Calendar, Gmail, Notion/Confluence, Jira/ClickUp nếu công ty bạn dùng.
5. **Skill lẻ dạng file** (ví dụ `user-stories` của b33eep): nén thư mục skill thành `.zip` → **Settings → Capabilities → Skills → Upload skill**.

> Claude.ai không chạy được ClauKit (bộ này cần Claude Code và Node.js).

### 3.2 Claude Code

```bash
# 1) Plugin chính thức của Anthropic
claude plugin marketplace add anthropics/knowledge-work-plugins
claude plugin install product-management@knowledge-work-plugins
claude plugin install operations@knowledge-work-plugins
claude plugin install data@knowledge-work-plugins
claude plugin install design@knowledge-work-plugins

# 2) PM Skills (Paweł Huryn)
claude plugin marketplace add phuryn/pm-skills
claude plugin install pm-execution@pm-skills
claude plugin install pm-product-discovery@pm-skills
claude plugin install pm-market-research@pm-skills
claude plugin install pm-data-analytics@pm-skills

# 3) PlausibleBA
claude plugin marketplace add plausibleba/ba-skills
claude plugin install plausible-ba@plausible-ba

# 4) ClauKit BA Kit (cần Node.js >= 18), cài theo từng dự án
npm install -g https://github.com/trungdo9/ClauKit.git
cd /duong-dan/du-an-cua-ban
ck init --kit ba
claude      # rồi chạy /ba:plan full <ten-du-an>
```

**Quy trình chuẩn của ClauKit BA Kit:**

```
/ba:plan → /ba:prd prd → /ba:spec fr / us / ac → /ba:spec compose (SRS) → /ba:qc gap → /ba:deliver uat
```

**Lưu ý khi cài ClauKit:**
- Bộ cài ghi vào `.claude/` của dự án, gộp hook vào `.claude/settings.json` và sửa `CLAUDE.md`, `.gitignore`. Hãy commit dự án trước khi chạy để có thể hoàn tác.
- Thư mục hooks có sẵn script gửi thông báo Discord/Telegram nhưng **không** được bật mặc định. Chỉ bật khi bạn chủ động cấu hình.
- Mỗi yêu cầu không có nguồn sẽ bị đánh dấu `[UNVERIFIED]`, giúp hạn chế việc AI bịa yêu cầu.

## 4. Thứ tự cài đề xuất

1. **Tuần 1:** cài plugin chính thức (`product-management`, `operations`, `data`) và PM Skills `pm-execution`, rồi dùng thử vào một tài liệu thật.
2. **Tuần 2:** thêm PlausibleBA và connector vẽ sơ đồ (Lucid/Figma).
3. **Khi dùng Claude Code cho dự án phần mềm:** cài ClauKit BA Kit.
4. **Skill cộng đồng Việt Nam (BA Zone, BA-Kit Hoàng PM):** xin link repo, đưa cho Claude rà soát giống bảng trên rồi mới cài.

## 5. Checklist tự rà soát trước khi cài skill lạ

- [ ] Repo công khai, có giấy phép rõ ràng, có cập nhật gần đây.
- [ ] Đọc `SKILL.md`: không có chỉ dẫn gửi dữ liệu ra ngoài, không yêu cầu API key hay token.
- [ ] Kiểm tra các file `.sh`, `.py`, `.js`: không có `curl | bash`, không gọi URL lạ, không xoá file.
- [ ] Kiểm tra hook trong `settings.json`: biết rõ mỗi hook chạy lệnh gì.
- [ ] Thử trên dự án hoặc dữ liệu mẫu trước, không dùng tài liệu mật của khách hàng.
