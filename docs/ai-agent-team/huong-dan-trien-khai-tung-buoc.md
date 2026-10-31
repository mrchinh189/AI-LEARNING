# Hướng dẫn triển khai từng bước — AI agent quản lý tiến độ trên ERP EuP

> **Dành cho:** người triển khai lần đầu, chưa từng dựng AI agent.
> **Kết quả cuối:** mỗi ngày hệ thống tự đối chiếu chứng từ ERP, tính tiến độ, tạo cảnh báo và nhắc việc qua email. Mỗi thứ Sáu hệ thống soạn báo cáo tuần để PM duyệt rồi gửi Ban Giám đốc. Áp dụng cho 2–3 dự án thí điểm trên ERP EuP.
> **Phần 2 (Bước 13–18):** bật agent team. Xem [agent-team-giai-phap.md](./agent-team-giai-phap.md).
> **Đi kèm:** thiết kế tổng thể [quan-ly-tien-do-du-an-eup.md](./quan-ly-tien-do-du-an-eup.md) và code chạy được [`projects/eup-pm-agent`](../../projects/eup-pm-agent/README.md).

## Cách đọc tài liệu này

- Làm **đúng thứ tự** từ Bước 0 đến Bước 12. Mỗi bước có mục **✅ Xong khi**: chưa đạt thì đừng sang bước sau.
- Khối `bash` là lệnh gõ trên máy chủ Linux, mỗi khối copy và chạy riêng.
- **Luôn làm trên site UAT trước.** Chỉ lên PROD ở Bước 12.
- Có lỗi thì xem [Phụ lục A — Lỗi thường gặp](#phụ-lục-a--lỗi-thường-gặp).

## Tổng quan lộ trình

| Bước | Việc | Ai làm | Thời gian |
|---|---|---|---|
| 0 | Chuẩn bị người, quyền, dự án thí điểm | Bạn + Trưởng PMO | 2–3 ngày |
| 1 | Có site UAT và bật module Projects | IT/Frappe dev | 1–2 ngày |
| 2 | Chuẩn bị máy chạy agent, cài code, chạy test | Bạn | 0,5 ngày |
| 3 | Kết nối ERP UAT (API key tạm của quản trị) | Bạn + IT | 1 giờ |
| 4 | Tạo doctype, custom field trên ERP | Bạn | 1 giờ |
| 5 | Tạo tài khoản riêng cho agent, phân quyền tối thiểu | Bạn + IT | 2 giờ |
| 6 | Nhập kế hoạch dự án thí điểm lên ERP | PM thí điểm + bạn | 2–3 ngày |
| 7 | Chạy thử tính toán và đối chiếu với tính tay | Bạn + PM | 0,5 ngày |
| 8 | Bật đối chiếu chứng từ và cảnh báo hằng ngày | Bạn | 0,5 ngày |
| 9 | Bật nhắc việc qua email | Bạn + IT | 0,5 ngày |
| 10 | Bật báo cáo tuần có Claude viết nhận định | Bạn | 0,5 ngày |
| 11 | Đặt lịch chạy tự động | Bạn | 1 giờ |
| 12 | Thí điểm 4 tuần, đo kết quả, lên PROD | Bạn + PMO | 4–5 tuần |

---

## Bước 0 — Chuẩn bị

### 0.1 Người cần có

| Vai trò | Ai | Cần họ làm gì |
|---|---|---|
| Người bảo trợ | 1 thành viên Ban Giám đốc | Đồng ý phạm vi; nhận báo cáo tuần |
| Trưởng PMO (chủ chương trình) | | Duyệt quy tắc cảnh báo, quyết định mở rộng |
| PM thí điểm | 2–3 người | Nhập kế hoạch, duyệt báo cáo, đánh giá cảnh báo đúng/sai |
| IT / Frappe dev của EuP | 1 người | Tạo site UAT, cấp quyền quản trị tạm, cấu hình email ERP |
| Bạn (người triển khai) | | Làm theo tài liệu này |

### 0.2 Chọn dự án thí điểm

Chọn 2–3 dự án **đang chạy**, còn ít nhất 6 tuần nữa mới kết thúc, có 15–60 đầu việc. Nên có:

- ít nhất 1 dự án đầu tư hoặc cải tạo (`DT`), vì loại này có nhiều chứng từ mua hàng làm bằng chứng;
- ít nhất 1 dự án đơn hàng xuất khẩu (`XK`) hoặc triển khai ERP (`ERP`).

### 0.3 Thu thập thông tin trước

Điền bảng này trước khi sang Bước 1:

| # | Thông tin | Giá trị |
|---|---|---|
| 1 | Địa chỉ site UAT (VD `https://uat.erp.eup.vn`) | |
| 2 | Phiên bản Frappe/ERPNext (xem ở `/app/about` hoặc hỏi IT) | |
| 3 | Module Projects đã bật chưa | |
| 4 | Email Account gửi đi của ERP đã chạy chưa (ERP có gửi được email thông báo không) | |
| 5 | Mã Project và PM của các dự án thí điểm | |
| 6 | Máy chủ chạy agent (VM Linux nội bộ, hoặc tạm dùng máy cá nhân trong lúc thử) | |
| 7 | Tài khoản Claude Console của công ty để lấy API key (Bước 10) | |

### 0.4 Đo hiện trạng (để sau này so sánh)

Nhờ mỗi PM thí điểm ghi lại trong 2 tuần:

- số giờ mỗi tuần dùng để gom số liệu và viết báo cáo;
- số mốc bị trễ, và trễ bao nhiêu ngày thì mới biết.

✅ **Xong khi:** đủ người, đã chọn dự án thí điểm, bảng 0.3 điền xong ít nhất mục 1–5.

---

## Bước 1 — Có site UAT và bật module Projects

Không bao giờ thử agent trên PROD. Nhờ IT:

1. **Tạo site UAT** bằng cách sao chép PROD gần nhất (bench `backup` → `restore` sang site mới). Tắt gửi email thật trên UAT, hoặc đổi email người dùng thành địa chỉ test, để agent không gửi nhầm cho người thật.
2. **Bật module Projects:** đăng nhập UAT bằng Administrator, mở `/app/user/<user của bạn>` → tab *Modules* → đánh dấu **Projects**. Mở `/app/projects` để thấy workspace Projects.
3. **Kiểm tra Holiday List:** mở `/app/company/<mã công ty>` → trường **Default Holiday List** phải có giá trị, và danh sách đó phải có các ngày lễ Tết năm nay. Agent dùng danh sách này để tính ngày làm việc.

> Lưu ý: agent mặc định chỉ nghỉ **Chủ nhật** và các ngày trong Holiday List, tức là coi Thứ Bảy là ngày làm việc. Nếu khối văn phòng nghỉ Thứ Bảy, hãy thêm các ngày Thứ Bảy vào Holiday List của Company đó.

✅ **Xong khi:** đăng nhập được UAT, mở được `/app/project` và `/app/task`, Company có Holiday List.

---

## Bước 2 — Chuẩn bị máy chạy agent và cài code

### 2.1 Máy cần gì

- Linux (Ubuntu 22.04 hoặc 24.04). Lúc thử có thể dùng macOS hoặc WSL trên Windows.
- 2 vCPU, 4 GB RAM là đủ cho thí điểm.
- Có Python 3.10 trở lên, git, và mạng tới được site UAT và `api.anthropic.com`.
- Múi giờ `Asia/Ho_Chi_Minh`.

### 2.2 Cài đặt

Kiểm tra Python và múi giờ:

```bash
python3 --version && timedatectl | grep "Time zone"
```

Nếu sai múi giờ:

```bash
sudo timedatectl set-timezone Asia/Ho_Chi_Minh
```

Cài công cụ (Ubuntu):

```bash
sudo apt update && sudo apt install -y git python3-venv
```

Lấy code về `/opt`:

```bash
sudo git clone https://github.com/mrchinh189/AI-LEARNING.git /opt/AI-LEARNING && sudo chown -R "$USER" /opt/AI-LEARNING
```

Tạo lối tắt cho thư mục ứng dụng (các bước sau đều dùng đường dẫn này):

```bash
sudo ln -s /opt/AI-LEARNING/projects/eup-pm-agent /opt/eup-pm-agent
```

Tạo môi trường Python riêng và cài thư viện:

```bash
cd /opt/eup-pm-agent && python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
```

### 2.3 Chạy bộ test (chưa cần ERP)

Bộ test dùng một ERP giả có sẵn dự án mẫu "Lắp dây chuyền ép số 3", để kiểm tra code trên máy bạn chạy đúng:

```bash
cd /opt/eup-pm-agent && .venv/bin/python -m pytest -q
```

Kết quả đúng: `26 passed`.

✅ **Xong khi:** pytest báo toàn bộ test passed.

---

## Bước 3 — Kết nối ERP UAT

### 3.1 Lấy API key tạm của tài khoản quản trị

Bước 4 phải tạo doctype nên cần quyền **System Manager**. Nhờ IT làm trên UAT:

1. Mở `/app/user/<tài khoản System Manager>` → tab **Settings** (ở một số phiên bản là mục **API Access** ở cuối trang) → bấm **Generate Keys**.
2. Hộp thoại hiện **API Secret** đúng **một lần**. Sao chép ngay. **API Key** xem lại được trên form.

> Đây là key tạm. Bước 5 sẽ thay bằng key của tài khoản agent có quyền hẹp, rồi thu hồi key này.

### 3.2 Tạo file cấu hình `.env`

```bash
cd /opt/eup-pm-agent && cp .env.example .env && chmod 600 .env && nano .env
```

Điền 3 dòng, giữ nguyên `DRY_RUN=1`:

```text
ERP_URL=https://uat.erp.eup.vn
ERP_API_KEY=<API Key>
ERP_API_SECRET=<API Secret>
DRY_RUN=1
```

### 3.3 Thử kết nối

```bash
cd /opt/eup-pm-agent && .venv/bin/python -m eup_pm ping
```

Kết quả đúng: dòng `Kết nối https://uat.erp.eup.vn thành công, tài khoản: …`. Dòng tiếp theo có thể báo lỗi field `custom_agent_enabled` không tồn tại. Lỗi này bình thường vì Bước 4 mới tạo field đó.

✅ **Xong khi:** `ping` in ra đúng tài khoản.

---

## Bước 4 — Tạo doctype và custom field trên ERP

Lệnh `setup-erp` tạo:

- Role `EuP Project Agent`;
- 3 doctype mới trong module Projects: `Nx Task Evidence` (bảng con), `Nx Project Alert`, `Nx Project Status Report`;
- các custom field trên **Project** (mục *AI Agent*) và **Task** (mục *Theo dõi tiến độ*, *Chứng từ bằng chứng*).

### 4.1 Xem trước (chưa ghi gì)

```bash
cd /opt/eup-pm-agent && .venv/bin/python -m eup_pm setup-erp
```

Màn hình liệt kê các dòng `[CHẠY THỬ] tạo DocType …`, `[CHẠY THỬ] tạo Custom Field …`. Đọc lướt để biết sẽ tạo những gì.

### 4.2 Tạo thật

Mở `.env`, đổi `DRY_RUN=1` thành `DRY_RUN=0`, rồi chạy lại:

```bash
cd /opt/eup-pm-agent && .venv/bin/python -m eup_pm setup-erp
```

Lệnh này chạy lại nhiều lần vẫn an toàn: cái nào đã có thì bỏ qua.

**Đổi lại `DRY_RUN=1` ngay sau khi chạy xong.**

### 4.3 Kiểm tra trên giao diện

1. Mở một Project bất kỳ → cuối form có mục **AI Agent** với các trường *Bật AI agent*, *Loại dự án EuP*, *PM phụ trách*, *Email nhận báo cáo*…
2. Mở một Task → có mục **Theo dõi tiến độ** và bảng **Chứng từ bằng chứng**.
3. Mở `/app/nx-project-alert` và `/app/nx-project-status-report`: danh sách trống, không báo lỗi.

Nếu chưa thấy field mới: bấm `Ctrl+Shift+R` để tải lại trang, hoặc nhờ IT chạy `bench --site <site> clear-cache`.

✅ **Xong khi:** thấy đủ field và 2 danh sách mới.

---

## Bước 5 — Tạo tài khoản riêng cho agent

Agent không được dùng tài khoản quản trị. Phần này giới hạn agent chỉ đọc chứng từ nghiệp vụ và chỉ ghi vào nhóm dự án.

### 5.1 Phân quyền cho Role `EuP Project Agent`

Mở `/app/permission-manager` (Role Permissions Manager). Với từng doctype dưới đây, chọn **Document Type** → **Add a New Rule** → Role `EuP Project Agent` → tích quyền như bảng:

| Doctype | Read | Write | Create | Email | Ghi chú |
|---|---|---|---|---|---|
| Project | ✓ | ✓ | | ✓ | Agent ghi RAG, SPI, ngày dự báo |
| Task | ✓ | ✓ | | ✓ | Agent ghi tiến độ, trạng thái bằng chứng |
| Comment | ✓ | | ✓ | | Ghi chú `[AI-Agent]` |
| Communication | ✓ | | ✓ | ✓ | Để gửi email |
| Company, Holiday List, User | ✓ | | | | Đọc lịch làm việc, người phụ trách |
| Purchase Order, Material Request, Purchase Receipt, Payment Entry, Delivery Note, Sales Invoice | ✓ | | | | **Chỉ Read.** Chứng từ làm bằng chứng |
| Các doctype custom dùng làm bằng chứng: Customs declaration, Yeu cau san xuat, De nghi thanh toan, Nx Request For Advance, Container Load Plan… | ✓ | | | | **Chỉ Read** |

`Nx Project Alert` và `Nx Project Status Report` đã được `setup-erp` cấp quyền sẵn.

**Tuyệt đối không tích** Submit, Cancel, Amend, Delete trên bất kỳ chứng từ nghiệp vụ nào.

### 5.2 Tạo user cho agent

1. `/app/user/new`: Email `ai-agent-pm@eup.vn` (hoặc địa chỉ IT cấp), First Name `AI Agent PMO`, **User Type** = System User.
2. Tab **Roles**: chỉ tích `EuP Project Agent`. Bỏ hết role khác.
3. **User Permissions** (`/app/user-permission/new`): User = agent, Allow = **Company**, For Value = công ty của dự án thí điểm. Thêm một dòng cho mỗi công ty cần theo dõi. Bước này giúp agent không đọc được dữ liệu của pháp nhân khác.
4. Lưu, rồi **Generate Keys** cho user này như ở Bước 3.1.

### 5.3 Đổi key trong `.env` và thu hồi key quản trị

Thay `ERP_API_KEY` và `ERP_API_SECRET` trong `.env` bằng key của agent, rồi chạy:

```bash
cd /opt/eup-pm-agent && .venv/bin/python -m eup_pm ping
```

Kết quả đúng: tài khoản hiện là `ai-agent-pm@eup.vn`, dòng `Số Project đang Open và bật AI agent: 0` (vì chưa bật dự án nào).

Sau đó nhờ IT mở lại user quản trị → **Generate Keys** lần nữa để key cũ mất hiệu lực.

### 5.4 Thử quyền chặn

Đăng nhập UAT **bằng user agent** (đặt mật khẩu tạm), mở một Purchase Order đã duyệt: không được thấy nút **Hủy bỏ** và không sửa được. Thấy nút thì quay lại 5.1, bỏ quyền thừa.

✅ **Xong khi:** `ping` chạy bằng user agent; user agent không sửa được chứng từ nghiệp vụ; key quản trị đã thu hồi.

---

## Bước 6 — Nhập kế hoạch dự án thí điểm lên ERP

Đây là bước tốn công nhất và quyết định chất lượng của toàn bộ hệ thống. Kế hoạch sai thì cảnh báo cũng sai.

### 6.1 Điền thông tin Project

Mở Project thí điểm → mục **AI Agent**:

| Trường | Điền |
|---|---|
| Bật AI agent | ✓ |
| Loại dự án EuP | `DT` / `ERP` / `XK` / `SP` / `IT` |
| PM phụ trách | User của PM, người nhận cảnh báo và duyệt báo cáo |
| Người bảo trợ | User của lãnh đạo phụ trách |
| Email nhận báo cáo | Email Ban Giám đốc, cách nhau bằng dấu phẩy |
| Ngày kết thúc baseline | Ngày kết thúc đã cam kết |

Trường **% Complete Method** của Project chọn `Task Weight`.

### 6.2 Tạo Task theo quy tắc

Mỗi Task phải có:

| Trường trên Task | Quy tắc |
|---|---|
| **Subject** | Động từ + kết quả. VD "Đặt mua máy ép", "Thông quan lô máy" |
| **Project** | Dự án thí điểm |
| **Expected Start Date / Expected End Date** | Bắt buộc. Một Task không dài quá 10 ngày làm việc; việc dài hơn thì tách nhỏ |
| **Bắt đầu baseline / Kết thúc baseline** | Lúc đầu điền bằng đúng ngày kế hoạch. Từ đó chỉ đổi khi Trưởng PMO đồng ý đổi baseline |
| **Depends On** (bảng phụ thuộc) | Việc phải xong trước. Mọi Task, trừ Task đầu tiên, nên có ít nhất 1 phụ thuộc |
| **Is Milestone** | Tích cho các mốc quan trọng (thường là Task 1 ngày) |
| **Assign To** (nút giao việc ở thanh bên trái của form) | Người phụ trách. Agent gửi email nhắc theo người này |
| **Task Weight** | Bỏ trống thì agent tự lấy số ngày làm việc của Task làm trọng số |

Có nhiều Task thì nhập bằng **Data Import** (`/app/data-import/new` → Import Type *Insert New Records* → Document Type *Task* → **Download Template** → điền Excel → tải lên). Bảng phụ thuộc và giao việc nên làm thêm trên form sau khi nhập.

### 6.3 Gắn chứng từ bằng chứng

Với Task có chứng từ ERP chứng minh đã xong, mở Task → bảng **Chứng từ bằng chứng** → **Add Row**:

| Cột | Ví dụ |
|---|---|
| Loại chứng từ | `Purchase Order` |
| Số chứng từ | `PO-2611-0042` |
| Trường kiểm tra | `workflow_state` (chứng từ có workflow duyệt), `docstatus` (đã Chốt = `1`), hoặc `status` |
| Giá trị cần đạt | `Approved` / `1` / … |

Bảng gợi ý nằm ở mục 7.4 của [tài liệu thiết kế](./quan-ly-tien-do-du-an-eup.md#74-bản-đồ-chứng-từ-bằng-chứng-theo-loại-dự-án-gợi-ý-ban-đầu). **Giá trị cần đạt phải ghi đúng như ERP lưu**, không phải nhãn tiếng Việt trên giao diện. Cách xem: đang đăng nhập UAT, mở trên trình duyệt địa chỉ `https://uat.erp.eup.vn/api/resource/Purchase Order/PO-2611-0042` (thay bằng một chứng từ đã đạt), rồi đọc giá trị của `workflow_state`, `docstatus` hoặc `status` trong nội dung JSON hiện ra.

Chứng từ chưa phát sinh (VD Phiếu nhập hàng chưa có) thì để trống, khi chứng từ được tạo thì PM thêm dòng.

✅ **Xong khi:** mỗi dự án thí điểm có Project đã bật AI agent, mọi Task có ngày, baseline, người phụ trách, phần lớn Task có phụ thuộc.

---

## Bước 7 — Chạy thử tính toán và đối chiếu với tính tay

Lệnh `compute` chỉ đọc, không ghi gì.

```bash
cd /opt/eup-pm-agent && .venv/bin/python -m eup_pm compute
```

Kết quả mẫu:

```text
=== PROJ-0001 — Lắp dây chuyền ép số 3 ===
RAG Đỏ | KH 46% | TT 39% | SPI 0,85 | baseline 12/12/2026 | dự báo 19/12/2026
  Task           Găng   Float    KH    TT  Dự báo xong  Việc
  TASK-0012      x          0  100%   90%  06/11/2026   Đặt mua máy ép
  TASK-0013      x          0   30%   40%  18/11/2026   Hàng về kho
  ...
  [Đỏ] R01 TASK-0013: Việc trên đường găng 'Hàng về kho' dự báo xong 18/11/2026, trễ 4 ngày làm việc so với hạn 12/11/2026.
```

Cách đọc:

| Cột | Ý nghĩa |
|---|---|
| Găng `x` | Việc nằm trên đường găng: việc này trễ thì cả dự án trễ |
| Float | Số ngày làm việc việc này có thể trễ mà không ảnh hưởng ngày kết thúc dự án |
| KH / TT | % kế hoạch tới hôm nay / % thực tế (Task có bằng chứng chưa đạt thì tối đa 90%) |
| Dự báo xong | Tính theo phụ thuộc và ngày "Dự kiến xong" mới nhất |

**Cùng PM kiểm tra 3 điều:**

1. Đường găng có giống PM nghĩ không? Không giống thì thường là thiếu phụ thuộc: sửa ở Bước 6.
2. Ngày dự báo kết thúc có hợp lý không?
3. Mỗi cảnh báo có đúng không?

Có dòng `LỖI DỮ LIỆU` (Task thiếu ngày, phụ thuộc vòng lặp) thì sửa trên ERP rồi chạy lại.

Muốn xem như ở một ngày khác, thêm `--date`:

```bash
cd /opt/eup-pm-agent && .venv/bin/python -m eup_pm compute --date 2026-11-20
```

✅ **Xong khi:** PM đồng ý đường găng và ngày dự báo của mỗi dự án thí điểm là hợp lý.

---

## Bước 8 — Bật đối chiếu chứng từ và cảnh báo hằng ngày

Lệnh `daily` làm 4 việc:

1. Đối chiếu từng chứng từ bằng chứng. Task có đủ chứng từ đạt điều kiện thì tự chuyển **Completed**, kèm Comment `[AI-Agent]` ghi rõ chứng từ.
2. Tính toán như `compute`.
3. Ghi **RAG**, **SPI**, **Dự báo kết thúc** lên Project.
4. Tạo **Nx Project Alert** cho từng cảnh báo mới (không lặp lại cảnh báo giống hệt trong 3 ngày). Có cảnh báo Đỏ thì email cho PM.

Chạy thử trước (`DRY_RUN=1`):

```bash
cd /opt/eup-pm-agent && .venv/bin/python -m eup_pm daily
```

Đọc các dòng `[CHẠY THỬ] sửa Task …` và `[CHẠY THỬ] tạo Nx Project Alert …`. Nếu hợp lý, đổi `DRY_RUN=0` trong `.env` rồi chạy lại cho riêng một dự án:

```bash
cd /opt/eup-pm-agent && .venv/bin/python -m eup_pm daily --project PROJ-0001
```

Kiểm tra trên UAT:

- Project có RAG và SPI.
- `/app/nx-project-alert?project=PROJ-0001` có cảnh báo.
- Task có bằng chứng đã đạt chuyển **Completed** và có Comment `[AI-Agent]`.

**PM xử lý cảnh báo:** mở Alert → đổi **Trạng thái** (`Đã xem` / `Đã xử lý` / `Bỏ qua`), chọn **PM đánh giá** (`Đúng` / `Sai` / `Thừa`) → **Lưu**. Trường đánh giá là số liệu để tinh chỉnh ngưỡng ở Bước 12.

> Nếu ERP báo không cho Completed vì task phụ thuộc chưa xong, agent ghi Comment giải thích và để nguyên trạng thái. Đó là quy tắc của ERPNext, PM cần hoàn tất các task phụ thuộc trước.

✅ **Xong khi:** chạy `daily` với `DRY_RUN=0` trên 1 dự án, kết quả trên ERP đúng như bản chạy thử.

---

## Bước 9 — Bật nhắc việc qua email

Lệnh `checkin` gửi **mỗi người phụ trách đúng 1 email/ngày**. Email liệt kê các việc có hạn trong 14 ngày tới hoặc quá 3 ngày làm việc chưa cập nhật, mỗi việc có link mở thẳng trên ERP. Người phụ trách bấm link, sửa **% Tiến độ** (Progress), **Dự kiến xong**, **Vướng mắc**, rồi **Lưu**. Việc chưa giao người sẽ được liệt kê gửi PM.

Điều kiện: ERP UAT gửi được email (Email Account mặc định có tick **Default Outgoing**). Nhờ IT kiểm tra ở `/app/email-account`.

Chạy thử:

```bash
cd /opt/eup-pm-agent && .venv/bin/python -m eup_pm checkin
```

Kết quả: các dòng `[CHẠY THỬ] gửi email tới …`. Khi `DRY_RUN=0`, xem email đã đi ở `/app/email-queue`.

Trước khi bật cho người thật, **báo trước cho người phụ trách** (qua họp giao ban hoặc tin nhắn của PM): "Từ tuần sau, mỗi chiều 16:00 anh/chị sẽ nhận 1 email nhắc cập nhật việc; mất khoảng 2 phút". Thông báo trước giúp giảm cảm giác "bị AI giám sát" (rủi ro K6 trong thiết kế).

✅ **Xong khi:** người phụ trách thử nhận email, bấm link, cập nhật được Task.

---

## Bước 10 — Bật báo cáo tuần có Claude viết nhận định

### 10.1 Chạy không dùng Claude trước

```bash
cd /opt/eup-pm-agent && .venv/bin/python -m eup_pm report --no-llm
```

Màn hình in nội dung báo cáo HTML: dòng RAG/KH/TT/SPI, mốc 2 tuần tới, cảnh báo, việc đã xong trong tuần. Mọi số liệu này do engine tính, chưa dùng AI.

### 10.2 Lấy API key Claude

1. Đăng nhập Claude Console của công ty (platform.claude.com) → **API Keys** → **Create Key**, đặt tên `eup-pm-agent-uat`.
2. Đặt hạn mức chi tiêu hằng tháng cho workspace. Thí điểm 3 dự án, mỗi tuần 1 báo cáo, chi phí rất nhỏ.
3. Điền vào `.env`:

```text
ANTHROPIC_API_KEY=<key vừa tạo>
EUP_AGENT_MODEL=<mã model Claude>
EUP_AGENT_EFFORT=medium
EUP_AGENT_FALLBACKS=default
```

Mã model lấy ở trang danh sách model trong tài liệu Claude (platform.claude.com/docs → *Models overview*). Nên chọn model mới nhất của dòng Opus. `EUP_AGENT_FALLBACKS=default` nghĩa là: nếu model chính từ chối trả lời, API tự chạy lại bằng model dự phòng phù hợp. Nếu chọn model không hỗ trợ cơ chế này và gặp lỗi 400, đổi thành `off`.

### 10.3 Chạy có Claude

```bash
cd /opt/eup-pm-agent && .venv/bin/python -m eup_pm report --project PROJ-0001
```

Phần đầu báo cáo có thêm 3 mục **KẾT LUẬN**, **QUYẾT ĐỊNH CẦN LÃNH ĐẠO**, **NHẬN ĐỊNH RỦI RO** do Claude viết. Hai cơ chế bảo vệ:

- Claude chỉ nhận số liệu đã tính sẵn và được dặn không tự tính.
- Sau khi Claude trả lời, code kiểm tra lại: có con số nào **không có** trong dữ liệu thì bỏ toàn bộ phần nhận định, ghi cảnh báo vào log, và báo cáo vẫn được tạo với phần số liệu. Vì vậy báo cáo không bao giờ chứa số do AI bịa.

### 10.4 Quy trình duyệt và phát hành

Khi `DRY_RUN=0`:

1. `report` tạo **Nx Project Status Report** ở trạng thái **Nháp** và email cho PM kèm link.
2. PM mở bản nháp, sửa phần **Nội dung** nếu cần, ghi **Ý kiến PM**, rồi đổi **Trạng thái** thành `Đã phát hành` → **Lưu**.
3. Trong vòng 30 phút, `publish` gửi báo cáo tới **Email nhận báo cáo** và **Người bảo trợ** của Project, rồi đánh dấu **Đã gửi**.

Chạy tay lệnh gửi:

```bash
cd /opt/eup-pm-agent && .venv/bin/python -m eup_pm publish
```

> Sau thí điểm, nếu muốn có nút **Phê duyệt / Từ chối** đúng kiểu ERP EuP, nhờ Frappe dev tạo **Workflow** cho `Nx Project Status Report` với *Workflow State Field* = `status`, các trạng thái Nháp → Chờ PM duyệt → Đã phát hành / Từ chối. Code không cần sửa vì vẫn đọc trường `status`.

✅ **Xong khi:** một báo cáo đi đủ vòng: nháp → PM duyệt → email tới người nhận.

---

## Bước 11 — Đặt lịch chạy tự động

Mở file mẫu `deploy/crontab.example` để xem lịch:

| Giờ | Lệnh |
|---|---|
| Thứ Hai – Thứ Bảy 16:00 | `checkin` |
| Thứ Hai – Thứ Bảy 17:30 | `daily` |
| Thứ Sáu 14:00 | `report` |
| Giờ hành chính, 30 phút/lần | `publish` |

Cấp quyền chạy cho script:

```bash
chmod +x /opt/eup-pm-agent/deploy/run.sh
```

Mở crontab của user đang chạy agent:

```bash
crontab -e
```

Dán toàn bộ nội dung `deploy/crontab.example` vào cuối, lưu lại. Kiểm tra:

```bash
crontab -l
```

Ngày hôm sau, xem log:

```bash
tail -n 50 /opt/eup-pm-agent/logs/cron.log
```

Mỗi ngày còn có một file log chi tiết `logs/YYYY-MM-DD.log`.

✅ **Xong khi:** sau 1 ngày, `cron.log` có kết quả của `checkin` và `daily`, không có dòng `ERROR`.

---

## Bước 12 — Thí điểm 4 tuần, đo kết quả, lên PROD

### 12.1 Nhịp thí điểm hằng tuần

| Khi | Việc |
|---|---|
| Hằng ngày | PM xem email cảnh báo Đỏ, xử lý và đánh giá Alert |
| Thứ Sáu | PM duyệt báo cáo tuần trước 17:00 |
| Thứ Hai | Bạn họp 30 phút với các PM thí điểm: cảnh báo nào sai hoặc thừa, chỉnh `config/rules.yaml` |
| Cuối mỗi tuần | Bạn ghi 4 số: tỷ lệ Task cập nhật trong 7 ngày, số Alert Đúng / Sai / Thừa, giờ PM làm báo cáo, số báo cáo phát hành đúng hạn |

Đếm nhanh Alert theo đánh giá: mở `/app/nx-project-alert/view/report?feedback=Sai`.

**Chỉnh ngưỡng:** sửa `config/rules.yaml`, ví dụ tăng `R06_stale_task.threshold_wd` từ 5 lên 7 nếu cảnh báo "lâu chưa cập nhật" quá nhiều. Lần chạy sau tự áp dụng, không cần khởi động lại gì. Các quy tắc R03, R07 đang tắt; bật lên (`enabled: true`) sau 2 tuần khi dữ liệu đã ổn định.

### 12.2 Tiêu chí để lên PROD

Đủ 4 điều sau sau 4 tuần:

- [ ] ≥ 80% Task đang mở được cập nhật trong 7 ngày gần nhất.
- [ ] ≥ 70% Alert được PM đánh giá **Đúng**.
- [ ] 4 báo cáo tuần liên tiếp được phát hành đúng hạn.
- [ ] Không lần nào phải khôi phục dữ liệu do agent ghi sai.

### 12.3 Lên PROD

1. Làm lại **Bước 4** (setup-erp, cần key quản trị tạm), **Bước 5** (user agent và phân quyền) trên PROD.
2. Tạo `.env` mới cho PROD (`ERP_URL=https://erp.eup.vn`) với key của user agent trên PROD; tạo API key Claude riêng tên `eup-pm-agent-prod`.
3. Nhập kế hoạch dự án thí điểm lên PROD (Data Import), bật **Bật AI agent**.
4. Chạy `compute`, rồi `daily` với `DRY_RUN=1`, so với kết quả UAT, rồi mới `DRY_RUN=0`.
5. Bật crontab cho PROD và tắt crontab UAT.
6. Mở rộng thêm 3–5 dự án mỗi 2 tuần. Mỗi dự án mới đi lại Bước 6–7.

### 12.4 Các bước tiếp theo (Giai đoạn 3 của thiết kế)

| Mở rộng | Làm gì |
|---|---|
| Nhắc việc qua Zalo / Google Chat | Dựng n8n, nhận và gửi tin; người phụ trách trả lời bằng tin nhắn, agent dùng Claude đọc câu trả lời thành % tiến độ, ngày dự kiến xong, vướng mắc |
| Agent Rủi ro viết phương án | Dùng Claude viết phần "Phương án" cho từng Alert Đỏ, PM duyệt |
| Agent Lập kế hoạch | Sinh WBS nháp từ Project Template và lưu đồ ERP cho dự án mới |
| Dashboard | Dashboard + Number Card trên ERP: RAG theo dự án, số Alert mở, SPI |


---

# Phần 2 — Bật agent team

Phần 1 (Bước 0–12) dựng phần nền chạy theo lịch. Phần 2 bật lần lượt 4 agent: Rủi ro, Thu thập, Lập kế hoạch, Điều phối. Giải pháp chi tiết xem [agent-team-giai-phap.md](./agent-team-giai-phap.md).

**Điều kiện:** đã xong ít nhất Bước 10 (đã có `ANTHROPIC_API_KEY` và `EUP_AGENT_MODEL` trong `.env`) và đã chạy thí điểm phần nền ≥ 2 tuần, để dữ liệu kế hoạch đủ tin cậy.

## Bước 13 — Cập nhật ERP và kiểm tra code

1. Lấy bản code mới:

```bash
cd /opt/AI-LEARNING && git pull
```

2. Cài lại thư viện và chạy test. Kết quả đúng: `26 passed`.

```bash
cd /opt/eup-pm-agent && .venv/bin/pip install -r requirements.txt && .venv/bin/python -m pytest -q
```

3. Chạy lại `setup-erp` để thêm doctype **Nx Plan Draft** và mục **Phân tích của Agent Rủi ro** trên Nx Project Alert. Giống Bước 4, lệnh này cần API key **System Manager** tạm thời và `DRY_RUN=0`. Xong thì trả lại key của agent và `DRY_RUN=1`.

```bash
cd /opt/eup-pm-agent && .venv/bin/python -m eup_pm setup-erp
```

4. Mở `/app/permission-manager`, cấp cho Role `EuP Project Agent` quyền **Read** trên doctype **Comment** (agent đọc ghi chú gần đây của Task), nếu Bước 5.1 chưa cấp.

✅ **Xong khi:** test passed; mở một Nx Project Alert thấy mục *Phân tích của Agent Rủi ro*; mở được `/app/nx-plan-draft`.

## Bước 14 — Bật Agent Rủi ro

Chọn một cảnh báo **Đỏ** có thật trên UAT (mở `/app/nx-project-alert?severity=Đỏ`, chép mã, VD `ALERT-2611-0003`). Chạy thử với `DRY_RUN=1`:

```bash
cd /opt/eup-pm-agent && .venv/bin/python -m eup_pm risk --alert ALERT-2611-0003
```

Màn hình in kết quả JSON: `root_cause`, `impact`, `options`… Log ghi agent đã gọi tool nào (`get_task`, `get_predecessors`, `get_document`…). Xem chi tiết từng bước trong audit log:

```bash
tail -n 20 /opt/eup-pm-agent/logs/audit-$(date +%F).jsonl
```

**Cùng PM đánh giá:** nguyên nhân gốc có đúng không? Phương án có làm được không? Nếu đúng, đặt `DRY_RUN=0` và chạy lại để ghi vào Alert.

Từ đây, mỗi lần `daily` chạy (cron 17:30), Agent Rủi ro tự phân tích tối đa 3 cảnh báo Đỏ mới cho mỗi dự án. Muốn tắt: `agents.risk.auto_after_daily: false` trong `config/rules.yaml`, hoặc chạy `daily --no-agents`.

✅ **Xong khi:** 5 phân tích liên tiếp được PM đánh giá là dùng được.

## Bước 15 — Bật Agent Thu thập tiến độ

Ở bước này người phụ trách vẫn nhận email nhắc như Bước 9. Khác biệt: họ có thể **trả lời bằng một câu tự nhiên** thay vì mở ERP. Lúc đầu, bạn chép câu trả lời vào lệnh `reply` để thử:

```bash
cd /opt/eup-pm-agent && .venv/bin/python -m eup_pm reply --from kythuat@eup.vn --text "hang ve 60%, chac 13/11 xong, dang cho kiem hoa"
```

Kết quả `kind: updated` kèm danh sách Task đã cập nhật, hoặc `kind: clarify` kèm câu hỏi lại nếu tin nhắn mơ hồ. Khi `DRY_RUN=0`, Task được cập nhật (*Nguồn tiến độ* = Tự khai) và có Comment trích nguyên văn, đồng thời người gửi nhận email xác nhận.

Thử thêm 3 trường hợp để chắc agent an toàn:

| Thử | Kết quả đúng |
|---|---|
| Tin nhắn mơ hồ: `"sắp xong rồi"` | `clarify`, không ghi gì |
| Người gửi báo về việc **không phải của mình** | Bị từ chối, không ghi |
| Báo `"xong"` cho việc có chứng từ bằng chứng | Chỉ ghi 90%; Completed khi chứng từ đạt |

**Tiết kiệm chi phí:** agent này chạy nhiều nhất. Đặt model nhỏ hơn riêng cho nó trong `.env`: `EUP_AGENT_MODEL_TRACKER=<mã model nhỏ>`, giữ `EUP_AGENT_FALLBACKS_TRACKER=off`.

✅ **Xong khi:** 20 tin nhắn thật được xử lý, PM kiểm tra thấy ≥ 90% cập nhật đúng.

## Bước 16 — Bật Agent Lập kế hoạch

Dùng cho dự án **mới**, chưa có Task. Trên ERP, tạo Project, điền mục *AI Agent* như Bước 6.1. Thêm vào **Notes** của Project mô tả phạm vi (thiết bị gì, ở nhà máy nào, yêu cầu đặc biệt). Rồi chạy:

```bash
cd /opt/eup-pm-agent && .venv/bin/python -m eup_pm plan --project PROJ-0009
```

Agent đọc WBS mẫu trong `kb/`, soạn danh sách việc, gọi engine kiểm tra lịch, rồi lưu **Nx Plan Draft** (khi `DRY_RUN=0`) và email cho PM.

**PM duyệt:** mở `/app/nx-plan-draft/<mã>` → đọc *Tóm tắt*, *Giả định*, xem *Kế hoạch (JSON)* → ghi *Ý kiến PM* → đổi **Trạng thái** thành `Đã duyệt` (hoặc `Từ chối` rồi chạy lại `plan`) → **Lưu**.

**Bạn áp dụng** (lệnh của người, agent không tự làm được):

```bash
cd /opt/eup-pm-agent && .venv/bin/python -m eup_pm apply-plan --draft KH-2611-0001
```

Task được tạo theo thứ tự phụ thuộc, có baseline. Sau đó PM giao người phụ trách (Assign To) và thêm chứng từ bằng chứng khi chứng từ phát sinh, như Bước 6.

**Nâng chất lượng kế hoạch:** sửa và bổ sung file trong `projects/eup-pm-agent/kb/`, như thời lượng thực tế và bản text các lưu đồ ERP. Xem `kb/README.md`.

✅ **Xong khi:** PM đồng ý dùng ≥ 70% kế hoạch nháp mà không phải sửa lớn.

## Bước 17 — Bật Agent Điều phối

PM, hoặc bạn thay PM, hỏi tự do:

```bash
cd /opt/eup-pm-agent && .venv/bin/python -m eup_pm ask "Dự án dây chuyền ép số 3 sao rồi, vì sao trễ, cần tôi quyết gì?"
```

Điều phối tự tra cứu, và khi cần thì giao Agent Rủi ro phân tích, Agent Lập kế hoạch soạn kế hoạch, hoặc Agent Báo cáo soạn báo cáo. Câu trả lời in ra màn hình. Nếu câu trả lời có con số không kiểm chứng được từ ERP, cuối câu trả lời có dòng ⚠.

✅ **Xong khi:** 10 câu hỏi thật của PM được trả lời đúng.

## Bước 18 — Kết nối kênh chat (Giai đoạn 3)

Để người phụ trách trả lời qua Zalo hoặc email mà không cần ai chép tay:

1. Tạo token cho webhook và điền `EUP_WEBHOOK_TOKEN` trong `.env`:

```bash
python3 -c "import secrets; print(secrets.token_urlsafe(32))"
```

2. Chạy webhook (nên đặt thành service systemd để tự khởi động):

```bash
cd /opt/eup-pm-agent && .venv/bin/python -m eup_pm serve
```

Kiểm tra: `curl http://127.0.0.1:8787/health` trả `{"ok": true}`.

3. Trong n8n (cùng máy), dựng workflow: **trigger** (Zalo OA webhook / IMAP email) → **xác thực người gửi** (map Zalo ID hoặc email sang user ERP; không khớp thì bỏ) → **HTTP Request** `POST http://127.0.0.1:8787/event`, header `X-Agent-Token`, body `{"type":"reply","from":"<email user ERP>","text":"<nội dung>"}` → gửi `reply` trong kết quả về lại kênh.
4. Webhook nhận cả `{"type":"ask", ...}` (PM hỏi qua chat) và `{"type":"new_project","project":"..."}` (gọi từ Webhook của ERP khi tạo Project).

> Không mở cổng 8787 ra Internet. Nếu n8n ở máy khác, đặt webhook sau reverse proxy có HTTPS và giới hạn IP.

✅ **Xong khi:** một tin Zalo hoặc email trả lời thật cập nhật được Task trên UAT.

---

## Phụ lục A — Lỗi thường gặp

| Hiện tượng | Nguyên nhân thường gặp | Cách xử lý |
|---|---|---|
| `Thiếu ERP_URL, ERP_API_KEY hoặc ERP_API_SECRET` | Chưa có `.env` hoặc chạy lệnh ngoài thư mục ứng dụng | `cd /opt/eup-pm-agent`, kiểm tra `.env` |
| `HTTP 401` / `HTTP 403` | Key sai, key đã bị tạo lại, hoặc user thiếu quyền | Generate Keys lại; kiểm tra Bước 5.1 |
| `HTTP 417` kèm `Field not permitted in query: custom_agent_enabled` | Chưa chạy `setup-erp` hoặc user agent chưa có quyền đọc Project | Chạy Bước 4; kiểm tra quyền Project |
| `HTTP 404` khi đối chiếu chứng từ | Gõ sai số chứng từ trong bảng bằng chứng, hoặc agent không có quyền đọc doctype đó | Sửa số chứng từ; thêm quyền Read ở Bước 5.1 |
| Task có bằng chứng mãi không tự hoàn thành | **Giá trị cần đạt** không khớp giá trị ERP lưu (VD ghi `Đã duyệt` thay vì `Approved`) | Đọc giá trị thật như hướng dẫn ở 6.3 |
| `Cannot complete task … dependant task … not completed` | Quy tắc của ERPNext | Hoàn tất task phụ thuộc trước; agent sẽ tự thử lại lần chạy sau |
| `LỖI DỮ LIỆU: … chưa có ngày kết thúc kế hoạch` / `vòng lặp` | Kế hoạch thiếu ngày hoặc phụ thuộc vòng tròn | Sửa Task trên ERP |
| Không có email nào tới | Đang `DRY_RUN=1`, hoặc Email Account chưa bật gửi, hoặc UAT chặn email | Xem `/app/email-queue` và `/app/error-log` |
| `Không có phần nhận định AI (Chưa đặt EUP_AGENT_MODEL…)` | Thiếu cấu hình Claude | Bước 10.2 |
| `Nhận định chứa con số không có trong dữ liệu` | Claude tự đưa số; cơ chế bảo vệ đã chặn | Không cần xử lý: báo cáo vẫn tạo, PM tự viết phần nhận định. Lặp lại thường xuyên thì gửi log cho người phát triển để chỉnh prompt |
| `Claude API lỗi 400` khi bật `EUP_AGENT_FALLBACKS=default` | Model đang chọn không hỗ trợ fallback | Đổi `EUP_AGENT_FALLBACKS=off` hoặc dùng model dòng Opus mới nhất |
| `Không kết nối được Claude API` | Máy chủ chặn mạng ra ngoài | Nhờ IT mở HTTPS tới `api.anthropic.com` |
| Cron không chạy | Sai đường dẫn, chưa `chmod +x`, sai múi giờ | `crontab -l`, xem `logs/cron.log`, `timedatectl` |
| `Agent … KHÔNG xong — Hết N lượt` | Agent tra cứu mãi chưa đủ căn cứ (thường do kế hoạch thiếu phụ thuộc hoặc chứng từ chưa gắn project) | Xem audit log để biết agent kẹt ở đâu; bổ sung dữ liệu; có thể tăng `max_turns` trong `rules.yaml` |
| `Bị từ chối: các con số sau không có trong dữ liệu` (trong audit log) | Agent định đưa số tự nghĩ ra; policy đã chặn | Bình thường, agent tự sửa và nộp lại. Lặp nhiều lần thì bổ sung dữ liệu (VD chi phí) vào ERP hoặc `kb/` |
| `Agent không được tạo Task` | Gọi tạo Task ngoài lệnh `apply-plan` | Đúng thiết kế: Task chỉ tạo qua `apply-plan` sau khi PM duyệt |
| `Agent … đang tắt trong config/rules.yaml` | `agents.<tên>.enabled: false` | Đổi thành `true` nếu muốn bật |
| `Đặt EUP_WEBHOOK_TOKEN …` | Chạy `serve` khi chưa có token | Bước 18.1 |

## Phụ lục B — Tra cứu lệnh nhanh

| Lệnh | Ghi gì lên ERP | Dùng khi |
|---|---|---|
| `python -m eup_pm ping` | Không | Kiểm tra kết nối |
| `python -m eup_pm setup-erp` | Doctype, field, role | Cài lần đầu trên mỗi site |
| `python -m eup_pm compute [--project X] [--date YYYY-MM-DD]` | Không | Xem nhanh tình hình, kiểm tra kế hoạch |
| `python -m eup_pm daily [--project X]` | Task, Project, Alert, email | Hằng ngày (cron) |
| `python -m eup_pm checkin [--project X]` | Email | Hằng ngày (cron) |
| `python -m eup_pm report [--project X] [--no-llm]` | Báo cáo nháp, email cho PM | Thứ Sáu (cron) |
| `python -m eup_pm publish` | Email báo cáo, đánh dấu đã gửi | 30 phút/lần (cron) |
| `python -m eup_pm risk --alert A` / `--project P` | Phân tích vào Nx Project Alert | Phân tích một cảnh báo / các cảnh báo Đỏ mới |
| `python -m eup_pm reply --from e --text "..."` | Task, Comment, email trả lời | Xử lý tin trả lời của người phụ trách |
| `python -m eup_pm plan --project P` | Nx Plan Draft, email PM | Lập kế hoạch nháp cho dự án mới |
| `python -m eup_pm apply-plan --draft KH-…` | Tạo Task | Sau khi PM duyệt kế hoạch |
| `python -m eup_pm ask "câu hỏi"` | Tùy agent được giao | PM hỏi tự do |
| `python -m eup_pm event --json '{...}'` | Tùy loại sự kiện | Thử sự kiện như webhook |
| `python -m eup_pm serve` | Tùy sự kiện | Webhook cho n8n |

Mọi lệnh ghi đều tôn trọng `DRY_RUN`. Thêm `-v` để xem chi tiết.

## Phụ lục C — Tắt khẩn cấp

| Muốn | Làm |
|---|---|
| Dừng agent cho một dự án | Bỏ tích **Bật AI agent** trên Project |
| Dừng toàn bộ việc ghi và gửi | Đặt `DRY_RUN=1` trong `.env` |
| Tắt một agent | `agents.<tên>.enabled: false` trong `config/rules.yaml` |
| Dừng hẳn | `crontab -e`, thêm `#` trước các dòng `run.sh`; dừng `serve` |
| Chặn agent ngay trên ERP | Mở user agent → bỏ tích **Enabled**, hoặc Generate Keys lại để key cũ mất hiệu lực |
| Khôi phục một Task bị ghi sai | Mở Task → mục **Activity / Version** ở cuối form xem giá trị cũ, sửa lại tay |
