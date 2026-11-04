---
name: ai-agent-team
description: Dựng, tuỳ biến và vận hành một "đội AI agent" bằng Python + Claude API theo 6 nguyên tắc của đội Grok Bot — bot quản lý (chief of staff) nhận cả chuỗi việc và giao cho bot chuyên môn; mỗi bot có tên, vai trò, trí nhớ riêng; phòng chat nhóm @tên; skill quy trình chuẩn; tự chấm theo rubric trước khi nộp; trưởng nhóm chỉ phân việc; cổng duyệt của người cho đăng bài/mua hàng; Dr. X khám đội. Dùng skill này khi người dùng muốn xây đội bot, đội agent, hệ multi-agent, "bot quản lý giao việc cho bot khác", tự động hoá cả quy trình bán hàng/nội dung/nghiên cứu/sản phẩm bằng nhiều AI phối hợp, thêm bot hoặc skill cho đội ai-team, viết rubric để bot tự kiểm tra, hoặc hỏi làm sao để AI tự làm cả chuỗi việc mà vẫn kiểm soát được — kể cả khi họ không nói chữ "agent" hay "skill".
---

# Đội AI Agent

Skill này mang theo một dự án Python chạy được (`assets/project/`) hiện thực hoá đội AI agent, cùng script dựng dự án và kiểm tra cấu hình. Việc của bạn là giúp người dùng đi từ "dùng AI cho từng việc lẻ" sang "vận hành một đội bot" — **từng bước**, vì niềm tin vào bot phải được xây dần (nguyên tắc 6).

Đội gồm: bot quản lý → (trưởng nhóm) → bot chuyên môn; mọi bot có trí nhớ file Markdown, thấy nhật ký việc gần đây; skill là file Markdown có "Tiêu chí đạt" để bot tự chấm; `publish`/`purchase`/`save_skill` luôn dừng hỏi người.

## Tài nguyên

| Đường dẫn | Khi nào dùng |
|---|---|
| `scripts/scaffold.py <thư-mục> [--preset sales-content\|product\|minimal]` | Tạo dự án mới. |
| `scripts/validate_team.py <thư-mục-dự-án>` | Sau mỗi lần sửa `team.json` hoặc skill. Không cần API key. |
| `references/principles.md` | Giải thích *vì sao* (6 nguyên tắc, ví dụ gốc) hoặc đánh giá thiết kế người dùng đề xuất. |
| `references/team-config.md` | Thiết kế đội, schema `team.json`, tool có sẵn, preset, ví dụ theo lĩnh vực, cách viết skill và rubric. |
| `references/architecture.md` | Sửa code: thêm tool, nối API thật, duyệt khi chạy cron, đổi model, viết test. |
| `assets/project/` | Mã nguồn mẫu (đừng sửa trực tiếp — sửa trong dự án đã scaffold). |

## Quy trình

### 1. Hiểu quy trình của người dùng trước khi dựng gì

Hỏi gọn (bỏ qua câu nào đã rõ từ ngữ cảnh):
- Việc nào họ làm lặp lại hằng tuần, muốn đội bot gánh trước tiên? Chỉ chọn **một** để bắt đầu.
- Các bước từ A đến Z của việc đó.
- Thế nào là kết quả đạt? Lần gần nhất phải sửa kết quả của AI, họ đã sửa gì? (mỗi lần sửa → một tiêu chí rubric)
- Bước nào chạm ra bên ngoài (đăng bài, gửi tin, chi tiền)? Đó là điểm cần duyệt.

Lý do: đội dựng theo quy trình thật thì có ích ngay; đội dựng "cho đủ vai" thì tốn tiền và khó tin.

### 2. Dựng dự án

```bash
python <skill>/scripts/scaffold.py <thư-mục> --preset <preset>
```

Chọn preset gần nhất (`references/team-config.md` mục 4): `minimal` (3 bot) cho người mới hoặc một quy trình đơn; `sales-content` cho bán hàng/nội dung; `product` cho phát triển sản phẩm. Nếu người dùng đã có thư mục dự án `ai-team`, làm việc trên thư mục đó thay vì scaffold mới.

### 3. Thiết kế đội trong `team/team.json`

Đọc `references/team-config.md` rồi sửa preset theo quy trình ở bước 1. Điểm cốt lõi:
- Vai trò hẹp, một kho kiến thức mỗi bot — nhồi nhiều việc làm trí nhớ loãng.
- Tool rủi ro chỉ ở bot quản lý; bot đọc web không cầm tool tác động.
- ≥ 2 bot cùng mảng thì thêm trưởng nhóm `delegate_only`.
- Câu đầu của `role` phải rõ — bot quản lý chọn người giao việc dựa vào câu đó.

### 4. Viết skill cho quy trình

Tạo `team/skills/<ten-skill>.md` với đúng ba heading `## Mô tả`, `## Các bước`, `## Tiêu chí đạt` (code đọc nguyên văn heading cuối để chấm). Viết tiêu chí kiểm được, có con số hoặc điều kiện cụ thể — grader không chấm được "viết hay". Trong "Các bước", nói rõ bước nào giao cho bot nào và bước nào cần duyệt. Mẫu và bảng "mơ hồ → kiểm được" ở `references/team-config.md` mục 6.

### 5. Kiểm tra

```bash
python <skill>/scripts/validate_team.py <thư-mục-dự-án>
cd <thư-mục-dự-án> && pip install -r requirements.txt pytest && python -m pytest -q
```

Sửa mọi lỗi (✗). Cảnh báo (⚠) thì cân nhắc và giải thích cho người dùng nếu giữ nguyên. Test dùng đội cố định trong `tests/fixtures/` nên không phụ thuộc đội người dùng tuỳ biến; chúng kiểm tra cơ chế (giao việc, duyệt, tự chấm, phòng chat), còn validator kiểm tra cấu hình.

### 6. Chạy thử — nhỏ trước

Cần `ANTHROPIC_API_KEY` (hoặc `ant auth login`). Mỗi lần giao việc và mỗi lần chấm là một lời gọi API riêng; một lệnh qua bot quản lý có thể tốn 8–20 lời gọi. Nói rõ điều này với người dùng trước khi chạy thật.

```bash
python -m ai_team ask --bot <bot-chuyên-môn> --skill <skill> "<việc nhỏ>"   # thử một bot trước
python -m ai_team ask --skill <skill> "<việc cả chuỗi>"                     # rồi mới qua bot quản lý
python -m ai_team chat <phòng> --members a,b,c "<ý tưởng>"                  # phòng chat nhóm
python -m ai_team memory <bot> · skills · doctor
```

Không đề xuất `--auto-approve` trừ khi chỉ demo với tool mô phỏng; tuyệt đối không khi `publish`/`purchase` đã nối API thật.

### 7. Vận hành theo "trao quyền từng bước"

Hướng dẫn người dùng đi qua các giai đoạn, chỉ sang giai đoạn sau khi đạt điều kiện:

| Giai đoạn | Làm gì | Sang tiếp khi |
|---|---|---|
| Quan sát | Giao một quy trình, đọc mọi kết quả, sửa; để bot `remember` sở thích | ~5 lần liên tiếp dùng được với ít chỉnh sửa |
| Đóng gói | Chốt skill + rubric (hoặc bot `save_skill`, có duyệt) | Một lệnh `--skill` đạt rubric ngay lần đầu phần lớn thời gian |
| Mở rộng | Thêm bot, trưởng nhóm `delegate_only`, chạy `doctor` hằng tuần | Tỉ lệ đạt ổn định, Dr. X không báo quá tải |
| Tự động | Cron cho skill đã ổn định; hành động chi tiền vẫn giữ duyệt | — |

Khi chạy cron, hành động cần duyệt sẽ không được thực hiện (không có ai trả lời) — đó là chủ ý; xem `references/architecture.md` để thêm hàng đợi duyệt.

## Khi cần sửa code

Đọc `references/architecture.md`. Thêm tool cần sửa bốn chỗ: `TOOL_SPECS` + `_tool_<tên>` (+ `APPROVAL_REQUIRED` nếu có tác động ra ngoài) trong `agent.py`, `WORK_TOOLS` trong `config.py` và trong `scripts/validate_team.py`, rồi viết test với `FakeLLM`. Giữ các bất biến sau vì chúng là lý do hệ thống an toàn:
- Cổng duyệt nằm ở tầng code, không dựa vào việc model "nhớ" hỏi.
- `delegate_only` chặn ở cả lúc nạp cấu hình lẫn lúc chạy tool.
- Lịch sử hội thoại chỉ nối thêm `response.content` nguyên vẹn.
- Mọi file bot ghi nằm trong `workspace/outputs/`.

## Khi người dùng chỉ hỏi ý tưởng

Không phải câu hỏi nào cũng cần dựng dự án. Nếu họ chỉ muốn hiểu cách tổ chức đội AI hoặc thiết kế trên giấy, trả lời dựa trên `references/principles.md` và `references/team-config.md`, đề xuất sơ đồ đội + một skill đầu tiên kèm rubric, rồi hỏi họ có muốn dựng thành dự án chạy được không. Nếu việc của họ chỉ là một bước đơn (viết một bài, tóm tắt một tài liệu), nói thẳng rằng không cần cả đội — một lời gọi là đủ.
