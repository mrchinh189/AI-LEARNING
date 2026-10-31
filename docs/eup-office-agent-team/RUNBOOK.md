# Sổ tay triển khai từng bước — AI Agent Team quản lý tiến độ (EuP)

> Dành cho người triển khai lần đầu. Làm **lần lượt từ trên xuống**; mỗi bước có **Kết quả đúng** để tự kiểm tra trước khi sang bước sau.
> Mã nguồn: [`projects/eup-agents`](../../projects/eup-agents) · Thiết kế giải pháp: [README.md](./README.md)

## Bản đồ các giai đoạn

| Giai đoạn | Việc | Thời gian ước tính | Ai làm |
|---|---|---|---|
| 0 | Chuẩn bị: phê duyệt, site ERP TEST, tài khoản Claude API, máy chạy | 3–5 ngày (chờ duyệt là chính) | Bạn + IT/ERP |
| 1 | Cấu hình ERP TEST: user kỹ thuật, API key, custom field, dữ liệu mẫu | ½ ngày | Bạn + quản trị ERP |
| 2 | Cài mã nguồn, chạy test, kiểm tra kết nối | ½ ngày | Bạn |
| 3 | Chạy thử từng agent ở chế độ **chỉ đọc** (DRY_RUN) | 1 ngày | Bạn |
| 4 | Bật ghi thật trên ERP TEST | ½ ngày | Bạn |
| 5 | Chạy tự động theo lịch (cron hoặc n8n) | ½–1 ngày | Bạn + IT |
| 6 | Lên PROD cho 1 phòng pilot: chạy "bóng" 1 tuần → chạy thật | 6 tuần | Bạn + trưởng phòng pilot |

**Nguyên tắc an toàn xuyên suốt**

1. Luôn làm trên **site TEST** trước; chỉ đưa lên erp.eup.vn ở giai đoạn 6.
2. `DRY_RUN=true` (mặc định) nghĩa là agent **chỉ đọc**, mọi thứ định ghi/gửi chỉ in ra màn hình. Chỉ đổi sang `false` khi đã kiểm tra kết quả chạy thử.
3. Agent không có quyền Submit/Hủy chứng từ: code chỉ cho ghi `Task`, `Comment`, `Notification Log` (xem `eup_agents/guard.py`), và user kỹ thuật cũng không được cấp quyền đó.
4. API key/secret chỉ nằm trong file `.env` trên máy chạy — không gửi qua chat, không commit lên git.

---

## Giai đoạn 0 — Chuẩn bị

### Bước 0.1 · Xin phê duyệt phạm vi pilot

Gửi BGĐ/trưởng phòng một email ngắn (mẫu):

> **V/v: Thử nghiệm AI agent nhắc việc và báo cáo tiến độ trên ERP — Phòng [Tài chính – Kế toán]**
> - Phạm vi: 1 phòng, 1 pháp nhân, 6 tuần, bắt đầu [ngày].
> - Agent chỉ: nhắc việc theo hạn, làm báo cáo tuần, phát hiện chứng từ nháp/tồn đọng và tạo việc **nháp** để người xác nhận. Không sửa, không duyệt chứng từ.
> - Dữ liệu gửi tới Claude API: tiêu đề việc, nội dung email giao việc. Không gửi dữ liệu lương/HCNS.
> - Đề nghị: (1) duyệt phạm vi; (2) IT cấp site ERP TEST và 1 user kỹ thuật; (3) duyệt hạn mức chi phí API [x] USD/tháng.

**Kết quả đúng:** có email/biên bản đồng ý, biết tên phòng + tên pháp nhân pilot **đúng như trên ERP**.

### Bước 0.2 · Xin site ERP TEST

Nhờ IT/đội ERP tạo một bản sao của erp.eup.vn (VD `erp-test.eup.vn`) có dữ liệu gần đây. Hỏi IT 3 câu và ghi lại:

| Câu hỏi | Ghi câu trả lời |
|---|---|
| URL site TEST là gì? | |
| Phiên bản Frappe/ERPNext (Help › About)? | |
| Máy chạy agent có truy cập được site TEST và erp.eup.vn không (tường lửa/VPN)? | |

> Không có site TEST? Vẫn làm được giai đoạn 1–3 trên PROD **với `DRY_RUN=true`** (chỉ đọc), nhưng bỏ qua bước tạo custom field cho tới khi IT đồng ý.

### Bước 0.3 · Tạo tài khoản Claude API

1. Vào https://console.anthropic.com → đăng ký bằng email công ty → tạo **Organization** "EuP Group".
2. **Billing**: nạp tiền/thêm thẻ; vào **Limits** đặt hạn mức chi tiêu tháng (VD bằng mức BGĐ duyệt).
3. **API Keys › Create Key** → đặt tên `eup-agents-test` → sao chép key (bắt đầu `sk-ant-...`). Key chỉ hiện **một lần** — dán ngay vào trình quản lý mật khẩu.

**Kết quả đúng:** có 1 API key và hạn mức chi tiêu đã đặt.

### Bước 0.4 · Chuẩn bị máy chạy

Cho thử nghiệm, dùng máy tính của bạn là đủ. Cho chạy thật, xin IT một máy chủ Linux (Ubuntu 22.04/24.04, 2 vCPU, 4 GB RAM, 20 GB ổ đĩa) đặt trong mạng công ty.

Cài phần mềm (Ubuntu):

```bash
sudo apt update && sudo apt install -y git python3 python3-venv python3-pip
```

Cài Docker (cần ở giai đoạn 5 nếu dùng n8n): làm theo https://docs.docker.com/engine/install/ubuntu/

Windows/macOS: cài Python 3.11+ từ python.org và Git từ git-scm.com; dùng Terminal/PowerShell cho các lệnh bên dưới.

**Kết quả đúng:** lệnh `python3 --version` in ra 3.11 trở lên; `git --version` chạy được.

---

## Giai đoạn 1 — Cấu hình ERP TEST

> Cần một người có quyền **System Manager** trên site TEST (bạn hoặc quản trị ERP).

### Bước 1.1 · Tạo vai trò (Role) chỉ đủ quyền cho agent

1. Vào `/app/role/new` → **Role Name** `EuP Agent` → giữ tick **Desk Access** → **Lưu**.
2. Vào `/app/permission-manager` (Role Permissions Manager). Với từng Document Type dưới đây, bấm **Add a New Rule** → chọn Role `EuP Agent` → tick đúng cột:

| Document Type | Read | Write | Create | Ghi chú |
|---|---|---|---|---|
| Task | ✔ | ✔ | ✔ | Sổ việc |
| Comment | ✔ | | ✔ | Ghi chú lên Task |
| Notification Log | ✔ | | ✔ | Chuông thông báo (nếu dùng `NOTIFY_BACKEND=erp_bell`) |
| Purchase Order, Purchase Invoice, Sales Invoice, Journal Entry, Purchase Receipt, Sales Order | ✔ | | | **Chỉ đọc** |
| Company, Department, Holiday List, User, Project | ✔ | | | Danh mục |

**Tuyệt đối không tick** Submit, Cancel, Amend, Delete ở bất kỳ dòng nào.

### Bước 1.2 · Tạo user kỹ thuật và API key

1. `/app/user/new` → Email `agent@eup.vn`, First Name `EuP Agent` → **Lưu**.
2. Tab **Roles**: chỉ tick `EuP Agent` → **Lưu**.
3. Giới hạn theo pháp nhân pilot: `/app/user-permission/new` → User `agent@eup.vn` · Allow `Company` · For Value `<tên công ty pilot>` → **Lưu**.
4. Mở lại user → tab **Settings** → mục **API Access** → **Generate Keys**. Màn hình hiện **API Secret** đúng một lần → sao chép ngay. **API Key** xem lại được ở cùng mục.

**Kết quả đúng:** có cặp `API Key` + `API Secret` của `agent@eup.vn`.

### Bước 1.3 · Kiểm tra form Task có đủ trường chuẩn

Mở `/app/task/new` và kiểm tra form có các trường **Company**, **Department**, **Expected End Date**, **Priority**. (ERPNext bản 14/15 có sẵn.) Nếu thiếu Company/Department, ghi lại để báo IT — agent vẫn chạy nhưng báo cáo sẽ không chia theo phòng.

### Bước 1.4 · Tạo custom field cho Task

Có 2 cách — **cách A** nhanh hơn, **cách B** không cần dòng lệnh.

**Cách A (script, sau khi xong giai đoạn 2):** dùng API key của một tài khoản **System Manager** (không phải `agent@eup.vn`) đặt tạm vào `.env`, rồi:

```bash
python -m eup_agents setup-erp
```

```bash
python -m eup_agents setup-erp --apply
```

Lệnh đầu chỉ liệt kê trường thiếu; lệnh thứ hai mới tạo. Xong thì **đổi `.env` về key của `agent@eup.vn`**.

**Cách B (giao diện):** `/app/customize-form` → Enter Form Type `Task` → bảng **Fields** → thêm từng dòng theo bảng sau (thêm ngay dưới trường *Description*) → **Update**:

| Label | Fieldname | Type | Options |
|---|---|---|---|
| Theo dõi bởi AI agent | `eup_section` | Section Break | |
| Trạng thái xác nhận | `eup_confirm_state` | Select | 3 dòng: `Chờ xác nhận`, `Đã xác nhận`, `Từ chối` (dòng đầu để trống) |
| Người giao việc | `eup_assigned_by` | Link | `User` |
| Tiêu chí hoàn thành | `eup_definition_of_done` | Small Text | |
| | `eup_col` | Column Break | |
| Nguồn phát sinh | `eup_source` | Select | `Email`, `Chat`, `Họp`, `Công văn`, `ERP tự sinh`, `Thủ công` |
| Tham chiếu nguồn | `eup_source_ref` | Data | |
| Mức leo thang | `eup_escalation_level` | Int | Default `0` |
| Do agent tạo | `eup_agent_created` | Check | Default `0` |

Fieldname phải gõ **đúng y hệt** (code dùng các tên này). Danh sách gốc ở `projects/eup-agents/setup/custom_fields.json`.

**Kết quả đúng:** mở một Task bất kỳ thấy khối "Theo dõi bởi AI agent".

### Bước 1.5 · Tạo dữ liệu mẫu để thử

Trên site TEST tạo 5 Task cho phòng pilot (Company + Department đúng phòng pilot, **Assigned To** là user thật của bạn):

| Task | Expected End Date | Priority | Mục đích thử |
|---|---|---|---|
| Mẫu 1 — sắp đến hạn | hôm nay + 2 ngày | Medium | Nhắc mức 0 |
| Mẫu 2 — đến hạn | hôm nay | Medium | Nhắc mức 1 |
| Mẫu 3 — trễ 1 ngày | hôm qua (ngày làm việc) | Medium | Mức 2, báo trưởng phòng |
| Mẫu 4 — trễ gấp | hôm qua | **Urgent** | Mức 3, báo người giao |
| Mẫu 5 — không hạn | (để trống) | Low | Báo cáo đếm "thiếu hạn" |

Thêm 1 **Purchase Order** để ở trạng thái Nháp (đừng Submit) để thử agent giám sát chứng từ — nếu site TEST có PO nháp cũ hơn 3 ngày thì dùng luôn.

---

## Giai đoạn 2 — Cài mã nguồn

### Bước 2.1 · Lấy mã nguồn

```bash
git clone https://github.com/mrchinh189/AI-LEARNING.git
```

```bash
cd AI-LEARNING/projects/eup-agents
```

### Bước 2.2 · Tạo môi trường Python và cài thư viện

```bash
python3 -m venv .venv
```

```bash
source .venv/bin/activate
```

(Windows PowerShell: `.venv\Scripts\Activate.ps1`)

```bash
pip install -r requirements.txt
```

**Kết quả đúng:** dòng lệnh có tiền tố `(.venv)`; cài không báo lỗi đỏ.

### Bước 2.3 · Chạy test tự động (không cần ERP, không cần API key)

```bash
python -m pytest -q
```

**Kết quả đúng:** `9 passed`. Nếu lỗi ở bước này là do cài đặt Python, chưa liên quan tới ERP.

### Bước 2.4 · Điền cấu hình

```bash
cp .env.example .env
```

```bash
cp config/org.example.json config/org.json
```

Mở `.env` bằng trình soạn thảo, điền:

| Biến | Giá trị |
|---|---|
| `ERP_URL` | URL site TEST, VD `https://erp-test.eup.vn` (không có `/` ở cuối) |
| `ERP_API_KEY`, `ERP_API_SECRET` | từ Bước 1.2 |
| `DRY_RUN` | giữ `true` |
| `ANTHROPIC_API_KEY` | từ Bước 0.3 |
| `LLM_MODEL` | `claude-opus-5-5` (mặc định). Muốn tiết kiệm có thể thử `claude-sonnet-5-5`; `claude-haiku-5-5` rẻ nhất nhưng viết nhận định kém hơn |
| `NOTIFY_BACKEND` | `erp_bell` (chuông trong ERP) cho pilot |
| `SERVICE_TOKEN` | một chuỗi ngẫu nhiên dài, VD tạo bằng `python -c "import secrets;print(secrets.token_urlsafe(32))"` |

Mở `config/org.json`, sửa cho **khớp đúng tên trên ERP** (sao chép từ màn hình Company/Department):

- `pilot_companies`: tên công ty pilot.
- `department_heads`: `"<tên Department>": "<email trưởng phòng>"`.
- `unassigned_fallback`: email nhận việc chưa có người phụ trách (thường là trưởng phòng).
- `erp_watch.draft_doctypes`, ngưỡng ngày: giữ mặc định, chỉnh sau khi Kế toán góp ý.

### Bước 2.5 · Kiểm tra kết nối

```bash
python -m eup_agents check
```

**Kết quả đúng:**

```text
[OK] Đăng nhập ERP bằng user: agent@eup.vn
[OK] Đọc được Task (5 bản ghi mẫu)
[OK] Claude API trả lời: sẵn sàng
```

Gặp lỗi → xem [Phụ lục A](#phụ-lục-a--xử-lý-sự-cố).

---

## Giai đoạn 3 — Chạy thử từng agent (chỉ đọc)

Ở giai đoạn này `DRY_RUN=true`: mọi dòng bắt đầu bằng `[DRY-RUN]` là việc agent **định** làm, chưa có gì ghi lên ERP. Nhật ký nằm ở `logs/agent_actions.jsonl`.

### Bước 3.1 · A2 Nhắc việc

```bash
python -m eup_agents nudge
```

Đối chiếu với dữ liệu mẫu:

- [ ] Bạn nhận **1** tin gộp có Mẫu 1 (Sắp đến hạn), Mẫu 2 (Đến hạn), Mẫu 3, Mẫu 4 (Trễ hạn).
- [ ] Trưởng phòng nhận tin có Mẫu 3 và Mẫu 4; người tạo Mẫu 4 cũng nhận.
- [ ] Có dòng `[DRY-RUN] ... update Task ... eup_escalation_level` cho Mẫu 3 (mức 2) và Mẫu 4 (mức 3).
- [ ] Mẫu 5 không xuất hiện (không có hạn).

Chạy bản buổi chiều (chỉ nhắc việc đến hạn/trễ):

```bash
python -m eup_agents nudge --slot afternoon
```

- [ ] Mẫu 1 không còn trong tin.

### Bước 3.2 · A5 Báo cáo tuần

```bash
python -m eup_agents report
```

Mở file trong thư mục `reports/` (đường dẫn in ở cuối kết quả).

- [ ] Bảng số liệu khớp số Task bạn đếm tay trên ERP (`/app/task?department=...`).
- [ ] Mục "Top việc trễ hạn" có Mẫu 3, Mẫu 4.
- [ ] Mục "Nhận định & đề xuất" do AI viết: đọc kỹ xem có bịa số liệu không. Nếu có, ghi lại để chỉnh prompt (`SYSTEM` trong `eup_agents/agents/report.py`).

### Bước 3.3 · A3 Giám sát chứng từ

```bash
python -m eup_agents erp-watch
```

- [ ] Có dòng `[DRY-RUN] ... create Task "Hoàn tất hoặc hủy Purchase Order nháp ..."` cho PO nháp đã tạo.
- [ ] Số việc định tạo hợp lý. Nếu ra hàng trăm việc (do nhiều chứng từ nháp cũ), tăng `draft_days` trong `config/org.json` hoặc bớt doctype — **đừng** bật thật khi chưa xử lý, sẽ làm phiền người dùng.

### Bước 3.4 · A1 Tiếp nhận việc từ email

Sửa `samples/email-giao-viec.txt` cho có email người nhận thật trên site TEST (VD thêm dòng "Người làm: ten.ban@eup.vn"), rồi:

```bash
python -m eup_agents intake --file samples/email-giao-viec.txt --sender sep.cua.ban@eup.vn
```

- [ ] Agent tách được 2 việc, có hạn (thứ Sáu tuần này) và tiêu chí hoàn thành.
- [ ] Mỗi việc ở trạng thái `Chờ xác nhận`.

### Bước 3.5 · Nghiệm thu chạy thử

Chỉ sang giai đoạn 4 khi **tất cả** ô ở bước 3.1–3.4 đã đánh dấu. Ghi các điểm cần chỉnh vào một file/biên bản.

---

## Giai đoạn 4 — Bật ghi thật trên ERP TEST

1. Sửa `.env`: `DRY_RUN=false`.
2. Chạy lần lượt:

```bash
python -m eup_agents nudge
```

```bash
python -m eup_agents erp-watch
```

```bash
python -m eup_agents intake --file samples/email-giao-viec.txt --sender sep.cua.ban@eup.vn
```

3. Kiểm tra trên site TEST:

- [ ] Biểu tượng **chuông** góc trên ERP của bạn và trưởng phòng có thông báo "Nhắc việc …".
- [ ] Mẫu 3, Mẫu 4: trường **Mức leo thang** = 2 / 3; tab Comment có dòng "[Agent nhắc việc] …".
- [ ] `/app/task?eup_confirm_state=Chờ xác nhận` hiện các việc agent tạo (từ PO nháp và từ email).
- [ ] Chạy lại `erp-watch` lần 2: kết quả `"created": 0` (không tạo trùng).

4. **Tập thao tác của người dùng** (sẽ hướng dẫn lại cho phòng pilot): mở 1 việc `Chờ xác nhận` → kiểm tra tên việc, **Assigned To**, **Expected End Date** → đổi **Trạng thái xác nhận** thành `Đã xác nhận` (hoặc `Từ chối` + Status `Cancelled`) → **Lưu**. Việc đã xác nhận mới được agent nhắc.

---

## Giai đoạn 5 — Chạy tự động theo lịch

Chọn **một** trong hai cách.

### Cách A · Cron (đơn giản nhất, đủ cho pilot)

Trên máy chủ Linux, mở lịch chạy:

```bash
crontab -e
```

Thêm các dòng sau (sửa `/opt/AI-LEARNING` thành thư mục bạn clone; giờ theo múi giờ máy chủ — đặt máy chủ về `Asia/Ho_Chi_Minh` bằng `sudo timedatectl set-timezone Asia/Ho_Chi_Minh`):

```text
# A3 giám sát chứng từ — 07:30 thứ 2–7
30 7 * * 1-6  cd /opt/AI-LEARNING/projects/eup-agents && .venv/bin/python -m eup_agents erp-watch >> logs/cron.log 2>&1
# A2 nhắc việc — 08:00 và 15:00 thứ 2–6, 08:00 thứ 7
0 8 * * 1-6   cd /opt/AI-LEARNING/projects/eup-agents && .venv/bin/python -m eup_agents nudge >> logs/cron.log 2>&1
0 15 * * 1-5  cd /opt/AI-LEARNING/projects/eup-agents && .venv/bin/python -m eup_agents nudge --slot afternoon >> logs/cron.log 2>&1
# A5 báo cáo tuần — 16:00 thứ 6, gửi bản nháp cho trưởng phòng
0 16 * * 5    cd /opt/AI-LEARNING/projects/eup-agents && .venv/bin/python -m eup_agents report --send >> logs/cron.log 2>&1
```

**Kết quả đúng:** sáng hôm sau `logs/cron.log` có kết quả chạy lúc 07:30 và 08:00.

> Ngày lễ: agent đọc **Holiday List** mặc định của công ty trên ERP khi tính ngày trễ. Cron vẫn chạy vào ngày lễ — nếu không muốn nhận tin ngày lễ, nhờ IT thêm điều kiện hoặc tạm tắt cron.

### Cách B · Docker + n8n (khi cần nhận email/chat tự động)

1. Trong thư mục `projects/eup-agents`:

```bash
docker compose up -d --build
```

2. Mở `http://<ip-máy-chủ>:5678` → tạo tài khoản chủ n8n.
3. **Workflow nhắc việc buổi sáng:** **Create Workflow** → node **Schedule Trigger** (Trigger Interval: *Custom (Cron)*, Expression `0 8 * * 1-6`) → node **HTTP Request**:
   - Method `POST`, URL `http://agents:8000/run/nudge?slot=morning`
   - **Send Headers** → Name `X-Service-Token`, Value = `SERVICE_TOKEN` trong `.env`
   - Bấm **Test step** → thấy JSON `{"people_notified": ...}` → **Save** → bật **Active**.
4. Lặp lại cho: `/run/nudge?slot=afternoon` (`0 15 * * 1-5`), `/run/erp-watch` (`30 7 * * 1-6`), `/run/report?send=true` (`0 16 * * 5`).
5. **Workflow tiếp nhận email:** tạo hộp thư `viec@eup.vn` → node **Email Trigger (IMAP)** (điền máy chủ IMAP của công ty) → node **HTTP Request** `POST http://agents:8000/run/intake`, Body *JSON*:

```json
{"text": "{{ $json.subject }}\n\n{{ $json.text }}", "sender": "{{ $json.from.value[0].address }}", "source": "Email", "source_ref": "{{ $json.messageId }}"}
```

6. Muốn gửi nhắc việc qua email/chat thay vì chuông ERP: tạo workflow **Webhook** trong n8n → node gửi email/chat → đặt `NOTIFY_BACKEND=webhook` và `NOTIFY_WEBHOOK_URL=<URL production của node Webhook>` trong `.env` → `docker compose up -d` lại.

> Sau khi chạy ổn, đổi `n8nio/n8n:latest` trong `docker-compose.yml` thành số phiên bản cụ thể đang chạy để tránh tự nâng cấp ngoài ý muốn.

---

## Giai đoạn 6 — Lên PROD cho phòng pilot

| Tuần | Việc | Kiểm tra |
|---|---|---|
| Trước tuần 1 | Lặp **Bước 1.1–1.4 trên erp.eup.vn** (có IT giám sát). Tạo API key mới cho PROD và Claude API key mới `eup-agents-prod`. Đổi `.env` sang PROD, **`DRY_RUN=true`** | `check` báo OK trên PROD |
| Tuần 1 — chạy "bóng" | Cron/n8n chạy nhưng chỉ ghi log. Mỗi chiều, bạn đọc `logs/cron.log` và so với thực tế phòng: agent nhắc đúng việc chưa? Có việc nào nhắc nhầm? | Danh sách lỗi/điều chỉnh |
| Cuối tuần 1 | **Đo baseline** (số việc trễ, % việc có hạn, giờ làm báo cáo tuần) — điền vào bảng KPI ở [README mục 10](./README.md#10-kpi-đo-hiệu-quả). Đào tạo phòng pilot 30 phút: cách xác nhận việc, cập nhật trạng thái, ý nghĩa tin nhắc | Biên bản đào tạo |
| Tuần 2 | `DRY_RUN=false`. Bật **A2 nhắc việc + A5 báo cáo** | Không ai phàn nàn bị nhắc sai |
| Tuần 3–4 | Bật **A3 giám sát chứng từ** (luật R1, R3), rồi **A1 tiếp nhận email** | % việc agent tạo được xác nhận không sửa ≥ 80% |
| Tuần 5–6 | Họp đánh giá với trưởng phòng; so KPI với baseline; quyết định mở rộng | Báo cáo đánh giá pilot cho BGĐ |

**Thói quen vận hành hằng tuần (15 phút, sáng thứ Hai):**

- [ ] Đọc `logs/agent_actions.jsonl`/`logs/cron.log`: có lỗi `error` không?
- [ ] Xem chi phí trên https://console.anthropic.com (Usage) so với hạn mức.
- [ ] Đếm việc `Chờ xác nhận` tồn quá 2 ngày → nhắc trưởng phòng xác nhận.
- [ ] Ghi phản hồi người dùng; chỉnh ngưỡng trong `config/org.json` nếu cần.

**Dừng khẩn cấp:** đặt `DRY_RUN=true` trong `.env` (hoặc tắt cron: `crontab -e` thêm `#` đầu dòng; n8n: tắt **Active**). Agent ngừng ghi/gửi ngay ở lần chạy kế tiếp.

---

## Phụ lục A — Xử lý sự cố

| Thông báo | Nguyên nhân thường gặp | Cách xử lý |
|---|---|---|
| `Không kết nối được https://...` | Sai `ERP_URL`, máy chạy không vào được mạng ERP | Mở URL đó bằng trình duyệt trên chính máy chạy; nhờ IT mở tường lửa/VPN |
| `HTTP 401/403: API key/secret sai hoặc user thiếu quyền` | Dán sai key/secret; secret đã bị tạo lại; Role thiếu quyền | Generate Keys lại ở Bước 1.2; kiểm tra Role Permissions ở Bước 1.1 |
| `HTTP 417` hoặc lỗi nhắc tới `eup_...` | Chưa tạo custom field, gõ sai fieldname | Chạy `python -m eup_agents setup-erp` để xem trường thiếu |
| `HTTP 403` khi gửi chuông | Role `EuP Agent` chưa có quyền Create trên Notification Log | Thêm quyền ở Bước 1.1, hoặc đổi `NOTIFY_BACKEND=webhook` |
| `Chưa cấu hình ANTHROPIC_API_KEY` / `API_KEY sai` | Thiếu/sai key Claude | Kiểm tra `.env`; tạo key mới ở console.anthropic.com. Nhắc việc và báo cáo vẫn chạy, chỉ thiếu phần AI viết |
| `Claude API giới hạn tốc độ` | Gọi quá nhiều trong thời gian ngắn | Chạy lại sau vài phút; nếu thường xuyên, tăng tier trong Console |
| Báo cáo ra "(Chưa gán phòng)" | Task không có Department | Nhắc người dùng chọn Department khi tạo Task; xem lại tên trong `org.json` |
| Không ai nhận tin nhắc | `DRY_RUN=true`; hoặc Task chưa có **Assigned To**; hoặc ở trạng thái `Chờ xác nhận` | Kiểm tra từng điều kiện |
| Không có kết quả nào | `pilot_companies` trong `org.json` không khớp tên Company | Sao chép đúng tên từ `/app/company` |

## Phụ lục B — Lệnh hay dùng

| Mục đích | Lệnh |
|---|---|
| Kiểm tra kết nối | `python -m eup_agents check` |
| Xem trường còn thiếu trên Task | `python -m eup_agents setup-erp` |
| Nhắc việc ngay | `python -m eup_agents nudge` |
| Làm báo cáo tuần ngay | `python -m eup_agents report` |
| Quét chứng từ ngay | `python -m eup_agents erp-watch` |
| Xem 20 hành động gần nhất của agent | `tail -n 20 logs/agent_actions.jsonl` |
| Chạy test sau khi sửa code | `python -m pytest -q` |

## Phụ lục C — Những gì bản MVP này chưa làm

| Hạng mục trong thiết kế | Trạng thái | Kế hoạch |
|---|---|---|
| A4 Họp & biên bản | Chưa có | Làm ở giai đoạn mở rộng (tuần 9+), dùng lại A1 cho phần rút action item |
| A0 Điều phối / hỏi đáp tự do | Chưa có | Sau pilot, khi có kênh chat chính thức |
| Luật R2 (chờ duyệt workflow), R4 (nội bộ một chiều), R6 (logistics) | Chưa có | Cần Kế toán/XNK chốt tên trạng thái workflow và doctype của `eupapp` |
| Doctype `Agent Action Log` trên ERP | Đang ghi ra file `logs/agent_actions.jsonl` | Chuyển vào ERP khi IT tạo doctype |
| Việc định kỳ (`eup_recurring_rule`) | Chưa có | Dùng tạm tính năng Auto Repeat có sẵn của ERPNext cho Task |
