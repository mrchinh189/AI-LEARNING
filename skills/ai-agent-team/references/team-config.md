# Thiết kế đội và viết skill

## Mục lục
1. Schema `team/team.json`
2. Tool có sẵn
3. Quy tắc thiết kế đội
4. Ba preset
5. Ví dụ đội theo lĩnh vực
6. Viết skill và rubric

## 1. Schema `team/team.json`

| Trường | Bắt buộc | Ghi chú |
|---|---|---|
| `manager` | có | Bot đầu mối mặc định của `ask`. |
| `charter` | có | Hiến chương chung, đứng đầu mọi system prompt. Đặt quy tắc chung ở đây (ngôn ngữ, không bịa số liệu, hành động rủi ro phải đề xuất trước). |
| `bots[].name` | có | `^[a-z0-9_]+$` — dùng cho `@tên` trong phòng chat. |
| `bots[].title` | có | Chức danh hiển thị. |
| `bots[].role` | có | Vai trò hẹp. Câu đầu tiên xuất hiện trong danh sách đồng đội của bot quản lý — viết câu đầu thật rõ. |
| `bots[].effort` | không | `low`/`medium`/`high`/`xhigh`/`max`, mặc định `medium`. Bot quản lý/lập kế hoạch: `high`. Bot làm việc đơn giản: `low` để tiết kiệm. |
| `bots[].tools` | không | Xem mục 2. |
| `bots[].delegates` | không | Bot được phép giao việc. Có thì bot tự có tool `delegate`. |
| `bots[].delegate_only` | không | `true` = chỉ phân việc; không được có tool làm việc. |

## 2. Tool có sẵn

Mọi bot luôn có: `remember`, `load_skill`, `ask_human`. Có `delegates` thì có `delegate`.

| Tool | Cần người duyệt | Ghi chú |
|---|---|---|
| `write_file`, `read_file` | không | Chỉ trong `workspace/outputs/`. |
| `web_search` | không | Server tool của Anthropic. Chỉ cấp cho bot nghiên cứu (nội dung web có thể chứa prompt injection — bot đọc web không nên có tool tác động). |
| `publish` | **có** | Prototype ghi `outputs/published/`. Nối API thật ở `agent.py` `_tool_publish`. |
| `purchase` | **có** | Prototype ghi `outputs/purchases.jsonl`. |
| `save_skill` | **có** | Lưu skill mới vào `workspace/skills/`. |

Thêm tool mới: xem `architecture.md` mục "Thêm tool".

## 3. Quy tắc thiết kế đội

- **Vai trò hẹp, một kho kiến thức.** "Viết mô tả sản phẩm" tốt hơn "làm marketing". Nếu mô tả vai trò cần chữ "và" nhiều lần, cân nhắc tách bot.
- **Ít quyền nhất.** Tool rủi ro (`publish`, `purchase`, `save_skill`) thường chỉ ở bot quản lý. Bot đọc web không cầm tool tác động.
- **Trưởng nhóm khi ≥ 2 bot cùng mảng.** Ví dụ `content_lead` (delegate_only) quản `copywriter` + `scriptwriter`; bot quản lý chỉ cần giao cho trưởng nhóm.
- **Chuỗi giao việc ≤ 3 tầng** (giới hạn `max_depth=3`): người vận hành → bot quản lý → trưởng nhóm → bot chuyên môn.
- **Bắt đầu nhỏ.** 3 bot (preset `minimal`) cho quy trình đầu tiên; thêm bot khi Dr. X hoặc người dùng thấy bot nào quá tải.
- **Bot cho phòng chat** (pm/designer/engineer...) có thể không nằm trong chuỗi giao việc — validator sẽ cảnh báo, chấp nhận được nếu chủ ý.

## 4. Ba preset

| Preset | Bot | Dùng khi |
|---|---|---|
| `sales-content` (mặc định) | chief_of_staff, researcher, writer, content_lead → copywriter/scriptwriter, ads_analyst, pm, designer, engineer | Chủ shop, creator, marketing. |
| `product` | chief_of_staff, researcher, pm, designer, tech_lead → frontend/backend | Đội phát triển sản phẩm, đánh giá ý tưởng, đặc tả. |
| `minimal` | chief_of_staff, researcher, writer | Quy trình đầu tiên, học cách vận hành. |

## 5. Ví dụ đội theo lĩnh vực

**Phòng khám nha khoa (chăm sóc khách hàng):**
- `chief_of_staff` → `scheduler` (đề xuất lịch hẹn, không tự đặt), `reminder_writer` (tin nhắc lịch theo văn phong phòng khám), `review_responder` (trả lời đánh giá Google), `researcher`.
- Skill: `appointment-reminder`, `review-reply` (rubric: xin lỗi cụ thể, không tiết lộ thông tin bệnh nhân, dưới 80 chữ).

**Tuyển dụng nhỏ:**
- `chief_of_staff` → `jd_writer`, `screener` (đọc CV trong outputs/, chấm theo tiêu chí), `interview_designer`.
- Lưu ý: không để bot tự gửi email từ chối — đặt `publish` (hoặc tool email) ở bot quản lý, có duyệt.

**Nghiên cứu / báo cáo:**
- `chief_of_staff` → `research_lead` (delegate_only) → `web_researcher`, `data_analyst`; `editor` viết báo cáo cuối.
- Skill `weekly-brief` (rubric: mỗi nhận định có nguồn; ≤ 1 trang; có mục "việc cần làm").

## 6. Viết skill và rubric

File `team/skills/<ten-skill>.md` (chữ thường, số, gạch ngang):

```markdown
# Skill: <Tên dễ đọc>

## Mô tả
<Một dòng — dòng này hiện trong danh sách skill của mọi bot, viết sao cho bot biết khi nào dùng.>

## Các bước
1. <Bước cụ thể, nói rõ giao cho bot nào nếu cần>
2. ...
N. Đối chiếu với tiêu chí đạt, sửa cho đến khi đạt rồi mới nộp.

## Tiêu chí đạt
- <Tiêu chí kiểm được, có con số hoặc điều kiện rõ>
- ...
```

Rubric tốt:

| Mơ hồ (grader khó chấm) | Kiểm được |
|---|---|
| Bài viết hay, hấp dẫn | Câu đầu là hook dưới 15 chữ, chạm một nỗi đau cụ thể |
| Giá hợp lý | Giá đề xuất nằm giữa giá đồ cũ thấp nhất khu vực và 70% giá mới, có nêu lý do |
| Nghiên cứu kỹ | Mỗi con số có nguồn kèm ngày truy cập; ghi "chưa kiểm chứng" nếu không tìm được |
| Đúng văn phong | Xưng "mình", câu ≤ 20 chữ, không dùng từ trong danh sách cấm ở trí nhớ của writer |

Mục "Tiêu chí đạt" được code đọc nguyên văn để chấm — giữ đúng tên heading. Không có mục này thì skill vẫn chạy nhưng bot không tự chấm.

Lấy rubric từ người dùng: hỏi "lần gần nhất anh/chị phải sửa kết quả, anh/chị đã sửa gì?" — mỗi lần sửa là một tiêu chí.
