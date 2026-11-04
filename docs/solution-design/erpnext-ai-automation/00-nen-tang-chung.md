# 00 — Nền tảng chung: thiết kế kỹ thuật chi tiết

> Thuộc bộ: [AI tự động hóa thao tác ERPNext](../erpnext-ai-automation.md) · Mục lục chi tiết: [README](./README.md)
> Phạm vi: các thành phần **dùng chung** cho mọi use case (UC-01 → UC-07). Tài liệu từng use case chỉ mô tả phần riêng và tham chiếu về đây.

## 1. Mục tiêu thiết kế

| # | Mục tiêu | Cách đạt |
|---|---|---|
| G1 | Mọi thao tác ghi vào ERPNext đều kiểm soát được | Chỉ đi qua `erpnext-mcp`, mỗi tool call qua Policy engine, ghi `AI Action Log` |
| G2 | Không sinh chứng từ trùng khi chạy lại | `idempotency_key` ở mức job + field `ai_request_id` ở mức chứng từ |
| G3 | Chạy lại từng bước được, không phải chạy lại cả luồng | Job có state machine, kết quả từng bước lưu lại (step checkpoint) |
| G4 | Thay model / provider không ảnh hưởng tích hợp ERP | Lớp `llm/` trừu tượng; tool chuẩn MCP |
| G5 | Đo được chất lượng trước khi tăng mức tự động | Eval harness chạy trong CI, metrics theo use case |
| G6 | Không sửa mã nguồn ERPNext | Mọi tùy biến nằm trong Frappe app `ai_ops` |

## 2. Cấu trúc mã nguồn đề xuất

```text
ai-erp/                          # monorepo của lớp AI (ngoài ERPNext)
├── services/
│   ├── gateway/                 # FastAPI: webhook ERPNext, email, chat, callback duyệt
│   ├── worker/                  # Celery worker: chạy pipeline từng use case
│   │   ├── pipelines/           # uc01_purchase_invoice.py, uc02_sales_order.py, ...
│   │   ├── steps/               # bước dùng chung: fetch_attachment, extract, match_party ...
│   │   └── state.py             # state machine của Job
│   ├── erpnext_mcp/             # MCP server (tool hẹp quanh Frappe REST API)
│   │   ├── tools/               # read.py, write.py, reports.py, sensitive.py
│   │   ├── frappe_client.py     # HTTP client: auth, retry, chuẩn hóa lỗi
│   │   └── field_filter.py      # allowlist DocType/field, che dữ liệu
│   ├── policy/                  # Policy engine (thư viện + HTTP endpoint)
│   │   ├── rules/policy.yaml
│   │   ├── facts.py             # tính "fact" bằng code (khớp PO, tổng tiền ...)
│   │   └── engine.py
│   └── docai/                   # Document AI: parser XML HĐĐT, PDF, OCR/VLM
├── libs/
│   ├── llm/                     # client trừu tượng, structured output, retry, cache
│   ├── schemas/                 # Pydantic model dùng chung (Job, ExtractedInvoice ...)
│   └── telemetry/               # OpenTelemetry, logger chuẩn
├── evals/                       # bộ dữ liệu đánh giá + runner cho từng UC
├── deploy/                      # docker-compose.yml, helm chart, .env.example
└── frappe-app/ai_ops/           # Frappe app cài vào site ERPNext
```

Ngôn ngữ: **Python 3.11+** cho toàn bộ lớp AI (cùng hệ với Frappe, dễ chia sẻ kiến thức đội ERPNext).

## 3. Job — đơn vị xử lý chung

### 3.1 Schema

```python
# libs/schemas/job.py
class Job(BaseModel):
    id: UUID
    use_case: Literal["UC01", "UC02", "UC03", "UC04", "UC05", "UC06", "UC07"]
    source: Literal["email", "chat", "webhook", "schedule", "upload"]
    idempotency_key: str            # sha256(source + id gốc + nội dung chính)
    requested_by: str               # email user ERPNext (hoặc user dịch vụ)
    company: str | None             # Company trong ERPNext
    payload: dict                   # dữ liệu thô: message_id, file_ids, text ...
    state: JobState
    autonomy_level: Literal["L0", "L1", "L2", "L3"]
    steps: list[StepResult] = []    # checkpoint từng bước
    erp_refs: list[ErpRef] = []     # chứng từ đã tạo/tác động
    trace_id: str
    created_at: datetime
    updated_at: datetime
```

Quy tắc tạo `idempotency_key`:

| Nguồn | Công thức |
|---|---|
| Email | `sha256("email:" + Message-ID + ":" + sha256(file))` cho từng file đính kèm |
| Webhook ERPNext | `sha256("wh:" + doctype + ":" + name + ":" + event + ":" + modified)` |
| Chat | `sha256("chat:" + channel + ":" + message_ts)` |
| Lịch | `sha256("cron:" + use_case + ":" + ngày chạy + ":" + company)` |

### 3.2 State machine

```mermaid
stateDiagram-v2
    [*] --> RECEIVED
    RECEIVED --> DUPLICATE: idempotency_key đã tồn tại
    RECEIVED --> PREPARING
    PREPARING --> PLANNING: trích xuất / thu thập dữ liệu xong
    PREPARING --> NEEDS_HUMAN: không đọc được dữ liệu
    PLANNING --> EXECUTING: policy = allow
    PLANNING --> AWAITING_APPROVAL: policy = require_approval
    PLANNING --> NEEDS_HUMAN: không đủ thông tin / độ tin cậy thấp
    AWAITING_APPROVAL --> EXECUTING: duyệt
    AWAITING_APPROVAL --> REJECTED: từ chối
    AWAITING_APPROVAL --> EXPIRED: quá hạn duyệt
    EXECUTING --> DONE
    EXECUTING --> PLANNING: lỗi validate, còn lượt tự sửa
    EXECUTING --> FAILED: hết lượt retry / lỗi hệ thống
    NEEDS_HUMAN --> PLANNING: người bổ sung thông tin
    DONE --> [*]
    DUPLICATE --> [*]
    REJECTED --> [*]
    EXPIRED --> [*]
    FAILED --> [*]
```

- Trạng thái lưu ở PostgreSQL của lớp AI (bảng `jobs`, `job_steps`) và được **phản chiếu** sang DocType `AI Job` trong ERPNext để người dùng nghiệp vụ xem được.
- Mỗi bước (`StepResult`) lưu `name`, `input_hash`, `output`, `status`, `duration_ms`. Khi chạy lại job, bước nào có `input_hash` không đổi và `status=ok` thì bỏ qua (học từ cache theo input của ComfyUI).
- Retry: lỗi mạng/5xx → retry tối đa 5 lần, backoff mũ (2s, 4s, 8s, 16s, 32s). Lỗi validate (4xx từ ERPNext) → quay về `PLANNING` cho agent tự sửa, tối đa **3 lượt**, sau đó `NEEDS_HUMAN`.
- Hạn duyệt mặc định 48 giờ (cấu hình theo UC); trước hạn 4 giờ nhắc lại người duyệt.

## 4. Gateway

| Endpoint | Phương thức | Mô tả | Xác thực |
|---|---|---|---|
| `/hooks/erpnext/{event}` | POST | Nhận ERPNext Webhook | HMAC `X-Frappe-Webhook-Signature` (base64 HMAC-SHA256 của body với `webhook_secret`) |
| `/hooks/email` | POST | Nhận email từ Gmail Pub/Sub / Graph subscription / poller IMAP nội bộ | Token nội bộ |
| `/hooks/chat/{provider}` | POST | Sự kiện chat (tin nhắn, bấm nút trên thẻ duyệt) | Chữ ký của nền tảng chat |
| `/approvals/{token}` | GET/POST | Trang duyệt dạng web (dự phòng khi kênh chat không hỗ trợ thẻ) | Action token ký HMAC + SSO |
| `/jobs/{id}` | GET | Tra trạng thái job | Token nội bộ |
| `/healthz`, `/metrics` | GET | Health check, Prometheus | Nội bộ |

Xử lý chung trong gateway: kiểm tra chữ ký → chuẩn hóa thành `Job` → kiểm tra trùng `idempotency_key` (unique index) → đẩy vào queue `uc-<id>` → trả `202 Accepted` trong < 300 ms. Không gọi LLM trong gateway.

Kiểm tra chữ ký webhook Frappe:

```python
def verify_frappe_signature(body: bytes, header_sig: str, secret: str) -> bool:
    digest = hmac.new(secret.encode(), body, hashlib.sha256).digest()
    return hmac.compare_digest(base64.b64encode(digest).decode(), header_sig)
```

## 5. Hàng đợi & worker

- **Celery + Redis** (broker) và **PostgreSQL** (trạng thái job). Mỗi UC một queue riêng để cô lập tải và giới hạn concurrency riêng (ví dụ UC03 chat cần độ trễ thấp: worker riêng, concurrency cao; UC06 làm sạch dữ liệu chạy đêm: concurrency 1).
- Rate limit gọi ERPNext: tối đa **10 request/giây/site** (token bucket trong `frappe_client.py`) để không ảnh hưởng người dùng đang làm việc.
- Dead-letter queue: job `FAILED` được đẩy sang `dlq` kèm toàn bộ checkpoint, có lệnh `ai-erp replay <job_id>`.
- Phương án thay thế khi có nhiều luồng chờ duyệt dài ngày: **Temporal** (workflow bền vững, chờ signal duyệt). Bắt đầu với Celery; chuyển khi số job chờ duyệt đồng thời > vài nghìn.

## 6. `erpnext-mcp` — đặc tả tool

### 6.1 Quy ước chung

- Transport: MCP qua **stdio** khi chạy cùng worker, **Streamable HTTP** khi dùng chung cho nhiều client (Claude Desktop, IDE...).
- Mỗi tool call nhận ngữ cảnh ẩn (không do model điền): `job_id`, `acting_user`, `trace_id`, `autonomy_level`. Worker truyền qua metadata của request MCP.
- Thứ tự xử lý trong mỗi tool ghi: **validate schema → field filter → policy check → idempotency check → gọi Frappe → ghi AI Action Log → trả kết quả rút gọn**.
- Kết quả luôn là JSON nhỏ gọn. Danh sách mặc định tối đa 20 bản ghi, tối đa 50.

### 6.2 Danh mục tool

| Tool | Tham số chính | Frappe API | Loại |
|---|---|---|---|
| `get_doctype_schema` | `doctype` | `GET /api/method/frappe.desk.form.load.getdoctype` | read |
| `search_documents` | `doctype, filters, fields, order_by, limit` | `GET /api/resource/{doctype}` | read |
| `get_document` | `doctype, name, fields?` | `GET /api/resource/{doctype}/{name}` | read |
| `count_documents` | `doctype, filters` | `GET /api/method/frappe.client.get_count` | read |
| `run_report` | `report_name, filters, columns?` | `POST /api/method/frappe.desk.query_report.run` | read |
| `find_party` | `party_type, query, tax_id?` | `search_documents` + fuzzy ranking ở MCP | read |
| `find_item` | `query, supplier?, customer?` | Item + `Item Supplier` / `Item Customer Detail` + fuzzy | read |
| `get_stock` | `item_codes, warehouse?` | `GET /api/resource/Bin` | read |
| `map_document` | `method, source_name` | `POST /api/method/<erpnext mapper>` (ví dụ `...purchase_order.make_purchase_invoice`) — chỉ trả doc nháp, **không lưu** | read |
| `create_draft` | `doctype, data, idempotency_key` | `POST /api/resource/{doctype}` | write |
| `update_draft` | `doctype, name, patch` | `PUT /api/resource/{doctype}/{name}` (chỉ khi `docstatus=0`) | write |
| `add_comment` | `doctype, name, text` | `POST /api/resource/Comment` | write-light |
| `attach_file` | `doctype, name, file_ref` | `POST /api/method/upload_file` | write-light |
| `save_mapping` | `kind, external_key, erp_value` | `POST /api/resource/AI Mapping` | write-light |
| `submit_document` | `doctype, name` | `POST /api/method/frappe.client.submit` | sensitive |
| `apply_workflow_action` | `doctype, name, action` | `POST /api/method/frappe.model.workflow.apply_workflow` | sensitive |
| `reconcile_bank_transaction` | `bank_transaction, vouchers` | Bank Reconciliation Tool API của ERPNext | sensitive |
| `send_email` | `to, subject, body, reference` | `POST /api/method/frappe.core.doctype.communication.email.make` | sensitive |

Tool `cancel_document` và `delete_document` **không được cài** trong bản production.

> Tên hàm mapper/reconcile của ERPNext thay đổi giữa các phiên bản. Mỗi tool bọc chúng phải có test hợp đồng (contract test) chạy với site staging cùng phiên bản production.

### 6.3 Ví dụ schema tool (JSON Schema mà model nhìn thấy)

```json
{
  "name": "create_draft",
  "description": "Tạo một chứng từ ERPNext ở trạng thái Draft (docstatus=0). Không bao giờ submit. Trả về name của chứng từ, hoặc lỗi validate để bạn sửa và thử lại.",
  "input_schema": {
    "type": "object",
    "required": ["doctype", "data", "idempotency_key"],
    "properties": {
      "doctype": {"type": "string", "enum": ["Purchase Invoice", "Purchase Receipt", "Sales Order", "Quotation", "Journal Entry", "Material Request", "Dunning"]},
      "data": {"type": "object", "description": "Các field của DocType, child table là mảng (ví dụ items)."},
      "idempotency_key": {"type": "string", "minLength": 16}
    }
  }
}
```

### 6.4 Chuẩn hóa lỗi

| Mã | Khi nào | Agent nên làm gì |
|---|---|---|
| `VALIDATION_ERROR` | ERPNext trả `ValidationError`, `MandatoryError`, `LinkValidationError` | Đọc `message`, sửa dữ liệu, thử lại (≤ 3 lượt) |
| `PERMISSION_DENIED` | 403 / `PermissionError` | Dừng, báo người dùng thiếu quyền |
| `POLICY_DENIED` | Policy chặn | Không thử lại; giải thích cho người dùng |
| `APPROVAL_REQUIRED` | Policy yêu cầu duyệt | Kết thúc lượt; job chuyển `AWAITING_APPROVAL` |
| `NOT_FOUND` | 404 | Tìm lại bằng `search_documents` |
| `DUPLICATE` | Đã có chứng từ cùng `ai_request_id` | Dùng chứng từ có sẵn |
| `UPSTREAM_UNAVAILABLE` | 5xx, timeout | Không cần agent xử lý: worker tự retry |

Thông điệp lỗi từ ERPNext (`_server_messages`, `exception`) được bỏ thẻ HTML và cắt tối đa 1.000 ký tự trước khi trả cho model.

### 6.5 Field filter & che dữ liệu

```yaml
# erpnext_mcp/field_policy.yaml
doctypes:
  Supplier:
    read_fields: [name, supplier_name, tax_id, supplier_group, default_currency, disabled]
  Customer:
    read_fields: [name, customer_name, tax_id, customer_group, territory, default_price_list, credit_limits, disabled]
  Employee:
    deny: true                    # agent không được đọc nhân sự
  Bank Account:
    read_fields: [name, account_name, bank]
    mask: {bank_account_no: last4}
global_deny_fields: [password, api_secret, salary, bank_account_no, iban]
```

## 7. Policy engine

### 7.1 Giao diện

```python
class PolicyInput(BaseModel):
    tool: str
    args: dict
    use_case: str
    autonomy_level: str
    acting_user: str
    facts: dict          # do facts.py tính bằng code, KHÔNG do model cung cấp

class PolicyDecision(BaseModel):
    decision: Literal["allow", "deny", "require_approval"]
    rule_id: str
    reasons: list[str]   # hiển thị trên thẻ duyệt
    approvers_role: str | None = None
```

### 7.2 Fact — tính bằng code, không tin model

| Fact | Cách tính |
|---|---|
| `grand_total` | Đọc lại từ chứng từ Draft trong ERPNext (ERPNext tự tính), không lấy số model đưa |
| `supplier_is_existing` | Supplier tồn tại, `disabled=0`, đã có ≥ 1 Purchase Invoice đã submit |
| `match_with_purchase_order` | Mọi dòng có `purchase_order` + `po_detail`; lệch số lượng ≤ 0, lệch đơn giá ≤ dung sai |
| `price_variance_pct` | max(|rate - rate_PO| / rate_PO) trên các dòng |
| `extraction_confidence` | min(confidence) của các trường bắt buộc từ Document AI |
| `source_is_signed_xml` | Đầu vào là XML hóa đơn điện tử có chữ ký số hợp lệ |
| `is_working_hours` | Theo `Asia/Ho_Chi_Minh` |
| `writes_in_job` | Số tool call ghi đã thực hiện trong job |

### 7.3 Thứ tự đánh giá

1. Luật `deny` toàn cục (tool bị cấm, DocType bị cấm, vượt `max_write_calls_per_job`, ngoài giờ cho tool `sensitive`).
2. Luật theo tool + DocType + use case, **luật đầu tiên khớp thắng** (first-match).
3. Không khớp luật nào → `deny`.
4. Trần theo autonomy level: L0 chặn mọi tool ghi; L1 biến mọi `allow` của tool `sensitive` thành `require_approval`; L2/L3 giữ nguyên.

Mỗi luật có `rule_id`, được kiểm thử bằng bảng ca kiểm thử (table-driven test) trong `policy/tests/`. Thay đổi `policy.yaml` phải qua review của người phụ trách nghiệp vụ (CODEOWNERS).

## 8. Human-in-the-loop (HITL)

### 8.1 Thẻ duyệt (approval card)

```json
{
  "job_id": "7f3c...",
  "title": "Duyệt hóa đơn mua hàng ACC-PINV-2026-00789",
  "summary": "NCC: Công ty TNHH ABC · HĐ 1C26TAA/0001234 · 4.590.000 ₫ · khớp PO-2026-0456",
  "highlights": [
    {"level": "warn", "text": "Đơn giá dòng 2 cao hơn PO 3,2%"},
    {"level": "info", "text": "Nguồn: XML hóa đơn điện tử, chữ ký hợp lệ"}
  ],
  "diff": [{"field": "items[1].rate", "po": 82000, "invoice": 84624}],
  "links": {"erp": "https://erp.example.com/app/purchase-invoice/ACC-PINV-2026-00789", "source_file": "..."},
  "actions": [
    {"id": "approve", "label": "Duyệt & ghi sổ"},
    {"id": "edit", "label": "Mở để sửa"},
    {"id": "reject", "label": "Từ chối", "requires_reason": true}
  ],
  "action_token": "<HMAC(job_id|approver|exp)>",
  "expires_at": "2026-11-06T10:00:00+07:00"
}
```

### 8.2 Quy tắc

- Người bấm duyệt phải là user ERPNext có `approvers_role`; gateway kiểm tra lại quyền qua API trước khi thực thi (không tin thông tin từ nền tảng chat).
- Khi duyệt, tool `sensitive` được gọi **dưới tên người duyệt** (OAuth token của họ) nếu có, để lịch sử `Version` ghi đúng người chịu trách nhiệm; nếu không có, gọi bằng user dịch vụ kèm `approved_by` trong `AI Action Log`.
- "Mở để sửa": người dùng sửa trực tiếp Draft trong ERPNext; webhook `on_update` của Draft đó báo lại để job ghi nhận **phần sửa** (diff giữa bản AI tạo và bản sau khi sửa) — đây là dữ liệu học cho bảng `AI Mapping` và cho eval.
- Kênh hỗ trợ: Raven / Slack (Block Kit) / Microsoft Teams (Adaptive Card) / trang web `/approvals/{token}`; Zalo OA chỉ gửi thông báo kèm link trang web.

## 9. Frappe app `ai_ops`

### 9.1 DocType

| DocType | Loại | Field chính | Mục đích |
|---|---|---|---|
| `AI Job` | Thường | `job_id`, `use_case`, `state`, `source`, `requested_by`, `company`, `erp_refs` (child), `last_error` | Phản chiếu trạng thái job cho người dùng nghiệp vụ |
| `AI Action Log` | Thường, chỉ đọc với người dùng | xem [tài liệu tổng quan §6.2](../erpnext-ai-automation.md#62-custom-doctype-ai-action-log) | Kiểm toán |
| `AI Mapping` | Thường | `kind` (supplier_item, customer_item, uom, tax, account, bank_party), `party`, `external_key`, `erp_value`, `hits`, `source` (human/ai), `confirmed` | Bộ nhớ ánh xạ học từ người dùng |
| `AI Settings` | Single | `enabled_use_cases`, `default_autonomy`, `approval_timeout_hours`, `gateway_url`, `webhook_secret` (Password) | Cấu hình |

`AI Mapping` bổ sung cho `Item Supplier.supplier_part_no` và `Item Customer Detail.ref_code` có sẵn của ERPNext: mapping item được ghi vào **cả hai** — bảng chuẩn của ERPNext (để người dùng thấy trong form Item) và `AI Mapping` (để lưu thêm tên hàng gốc, số lần dùng, độ tin cậy).

### 9.2 Custom field (xuất qua `fixtures`)

| DocType | Field | Kiểu | Thuộc tính |
|---|---|---|---|
| Purchase Invoice, Purchase Receipt, Sales Order, Quotation, Journal Entry, Material Request, Dunning, Payment Entry | `ai_request_id` | Data | read only, no copy, có index |
| (cùng danh sách) | `ai_confidence` | Percent | read only, no copy |
| (cùng danh sách) | `ai_job` | Link → AI Job | read only, no copy |

`no_copy=1` để khi người dùng "Duplicate" hoặc "Amend" chứng từ thì các field này không bị chép sang, tránh đánh dấu sai là do AI tạo.

### 9.3 `hooks.py`

```python
# ai_ops/hooks.py (trích)
fixtures = [{"dt": "Custom Field", "filters": [["module", "=", "AI Ops"]]}]

doc_events = {
    # báo lại cho lớp AI khi người dùng sửa / submit / cancel chứng từ do AI tạo
    "*": {
        "on_update": "ai_ops.events.on_ai_doc_change",
        "on_submit": "ai_ops.events.on_ai_doc_change",
        "on_cancel": "ai_ops.events.on_ai_doc_change",
    },
}

scheduler_events = {
    "cron": {"*/15 * * * *": ["ai_ops.reconcile.enqueue_missed_events"]},
}
```

`on_ai_doc_change` chỉ làm việc khi `doc.get("ai_request_id")` có giá trị, và gửi sự kiện bằng `frappe.enqueue(..., enqueue_after_commit=True)` để không làm chậm thao tác của người dùng.

Webhook (DocType **Webhook**, cấu hình bằng UI hoặc fixtures) dùng cho sự kiện nghiệp vụ không gắn với AI (ví dụ `Bank Transaction` after_insert cho UC04).

### 9.4 API whitelisted riêng

Khi một thao tác cần nhiều bước trong một transaction, viết hàm trong app thay vì để agent gọi nhiều API:

```python
# ai_ops/api.py
@frappe.whitelist()
def create_purchase_invoice_from_po(po_name: str, bill_no: str, bill_date: str,
                                    rate_overrides: str | None = None,
                                    ai_request_id: str | None = None):
    frappe.has_permission("Purchase Invoice", "create", throw=True)
    if ai_request_id and frappe.db.exists("Purchase Invoice", {"ai_request_id": ai_request_id}):
        return frappe.db.get_value("Purchase Invoice", {"ai_request_id": ai_request_id}, "name")
    from erpnext.buying.doctype.purchase_order.purchase_order import make_purchase_invoice
    pi = make_purchase_invoice(po_name)
    pi.bill_no, pi.bill_date, pi.ai_request_id = bill_no, bill_date, ai_request_id
    for ov in frappe.parse_json(rate_overrides or "[]"):
        row = next(r for r in pi.items if r.po_detail == ov["po_detail"])
        row.rate = ov["rate"]
    pi.insert()          # Draft, chạy toàn bộ validate của ERPNext
    return pi.name
```

## 10. Lớp LLM

### 10.1 Định tuyến model

| Loại tác vụ | Model | Ví dụ |
|---|---|---|
| Phân loại, trích xuất trường đơn giản | Model nhỏ, nhanh | Email này là hóa đơn, PO hay thư rác? |
| Lập kế hoạch nhiều bước, tool calling | Model lớn | Khớp hóa đơn với PO, tự sửa lỗi validate |
| Đọc ảnh/PDF scan | Model đa phương thức (vision) hoặc OCR/VLM tự host | Hóa đơn chụp bằng điện thoại |
| Tóm tắt, soạn email | Model trung bình | Thư nhắc nợ |

Cấu hình theo UC trong `libs/llm/routing.yaml`; đổi model là đổi cấu hình, kèm chạy lại eval.

### 10.2 Cấu trúc prompt

```text
[system]
  - Vai trò + giới hạn (chỉ dùng tool được cấp, không tự bịa số liệu, hỏi lại khi mơ hồ)
  - Quy tắc nghiệp vụ của UC (lấy từ SOP, phiên bản có mã: SOP-AP-03 v2)
  - Định dạng đầu ra (JSON schema) nếu có
[context]
  - Company, ngày làm việc, tiền tệ, autonomy level
  - Kết quả RAG: tối đa 5 đoạn SOP + tối đa 10 mapping liên quan
[data]  <<< bọc trong thẻ, đánh dấu là DỮ LIỆU KHÔNG ĐÁNG TIN >>>
  <document source="email" trust="untrusted"> ... </document>
[task]
  - Nhiệm vụ cụ thể của bước này
```

- Nội dung từ email/file **luôn** nằm trong khối `data` có nhãn `untrusted`; system prompt nói rõ không làm theo chỉ dẫn bên trong khối này.
- Prompt được version hóa trong repo (`prompts/uc01/plan.v3.md`); mã phiên bản prompt ghi vào `AI Action Log`.

### 10.3 Structured output & kiểm tra sau

- Mọi đầu ra dạng dữ liệu dùng JSON schema (Pydantic) + validate; sai schema → yêu cầu sửa 1 lần → vẫn sai thì `NEEDS_HUMAN`.
- **Kiểm tra số học bằng code**: tổng dòng, thuế, tổng tiền; ngày hợp lệ; MST đúng định dạng (10 hoặc 13 chữ số, dạng `0123456789-001`).
- Giới hạn ngân sách: tối đa N lượt tool call mỗi job (mặc định 15) và M token; vượt thì dừng, `NEEDS_HUMAN`.

## 11. Xác thực & phân quyền

| Đối tượng | Cơ chế | Quyền |
|---|---|---|
| Worker (UC chạy nền) | API key/secret của user dịch vụ `ai.agent@...` | Role `AI Agent`: Read các DocType cần; Create/Write Draft các DocType được phép; **không** Submit/Cancel/Delete |
| Policy-gated submit | User dịch vụ thứ hai `ai.submitter@...` | Chỉ Submit trên DocType được bật L2; key chỉ policy engine giữ |
| Chat (UC03, UC07) | OAuth 2.0 (Frappe *OAuth Client*, authorization code + PKCE) theo từng người dùng | Đúng quyền của người hỏi |
| Người duyệt | OAuth của người duyệt hoặc xác minh Role qua API | Theo `approvers_role` |

User Permission giới hạn user dịch vụ theo `Company` (và `Warehouse` nếu cần). API secret lưu trong secret manager, xoay vòng 90 ngày.

## 12. Quan sát (observability)

- **Trace:** OpenTelemetry, `trace_id` sinh ở gateway, truyền qua Celery header → worker → MCP (metadata) → header `X-Request-ID` khi gọi ERPNext. Span cho từng bước, từng lần gọi LLM (model, token, latency) và từng tool call.
- **LLM trace & eval:** Langfuse tự host (prompt, output, điểm eval, phản hồi người duyệt).
- **Metrics (Prometheus):**

| Metric | Loại | Nhãn |
|---|---|---|
| `ai_jobs_total` | counter | `use_case`, `final_state` |
| `ai_job_duration_seconds` | histogram | `use_case` |
| `ai_tool_calls_total` | counter | `tool`, `decision`, `result` |
| `ai_llm_tokens_total` | counter | `use_case`, `model`, `direction` |
| `ai_approval_wait_seconds` | histogram | `use_case` |
| `ai_straight_through_ratio` | gauge | `use_case` (tính theo ngày) |
| `ai_field_edit_rate` | gauge | `use_case`, `field` |

- **Cảnh báo:** tỷ lệ `FAILED` > 5%/giờ; DLQ > 0 trong 30 phút; `PERMISSION_DENIED` tăng đột biến; chi phí token/ngày vượt ngân sách; job chờ duyệt quá hạn.

## 13. Eval harness

```text
evals/
├── uc01/
│   ├── cases/           # mỗi ca: input (file/email đã che dữ liệu) + expected.json
│   ├── fixtures/        # dữ liệu master tối thiểu nạp vào site test
│   └── scorer.py        # so sánh theo trường, có dung sai cho số
└── run.py               # ai-erp eval --uc uc01 --model <cấu hình> --report html
```

- Chạy trên **site ERPNext test** (khởi tạo từ fixture, `bench --site test.local reinstall` trước mỗi lần chạy CI hằng đêm), không chạy trên production.
- Chỉ số chung: độ chính xác theo trường, tỷ lệ job đúng hoàn toàn, số tool call trung bình, token trung bình, tỷ lệ chuyển người.
- Cổng chất lượng trong CI: PR thay đổi prompt/model/policy không được làm giảm chỉ số chính quá 1 điểm %.

## 14. Triển khai

```yaml
# deploy/docker-compose.yml (rút gọn)
services:
  gateway:   {image: ai-erp/gateway,   env_file: .env, ports: ["8080:8080"], depends_on: [redis, postgres]}
  worker-uc01: {image: ai-erp/worker, command: celery -A worker worker -Q uc01 -c 4, env_file: .env}
  worker-uc03: {image: ai-erp/worker, command: celery -A worker worker -Q uc03 -c 16, env_file: .env}
  worker-misc: {image: ai-erp/worker, command: celery -A worker worker -Q uc02,uc04,uc05,uc06,uc07 -c 4, env_file: .env}
  beat:      {image: ai-erp/worker, command: celery -A worker beat, env_file: .env}
  erpnext-mcp: {image: ai-erp/erpnext-mcp, env_file: .env.mcp, expose: ["9000"]}
  policy:    {image: ai-erp/policy, expose: ["9100"]}
  redis:     {image: redis:7}
  postgres:  {image: pgvector/pgvector:pg16, volumes: ["pg:/var/lib/postgresql/data"]}
  langfuse:  {image: langfuse/langfuse, depends_on: [postgres]}
volumes: {pg: {}}
```

- Môi trường: `dev` (site ERPNext local) → `staging` (bản sao production đã che dữ liệu, cùng phiên bản ERPNext) → `production`.
- Feature flag theo UC và theo Company trong `AI Settings`; tắt một UC không cần deploy lại.
- Sao lưu: PostgreSQL của lớp AI sao lưu hằng ngày; dữ liệu chính vẫn nằm trong ERPNext (đã có cơ chế backup của bench).

## 15. Checklist bảo mật

- [ ] Nội dung email/file luôn được đánh dấu `untrusted` trong prompt; không có tool chuyển tiền / tạo Payment Entry tự động.
- [ ] `erpnext-mcp` không mở ra Internet; ERPNext API chỉ nhận request từ IP của lớp AI cho user dịch vụ.
- [ ] Field filter áp dụng cho cả kết quả tool **và** thông điệp lỗi.
- [ ] Log không chứa API secret, mật khẩu, số tài khoản đầy đủ.
- [ ] Hợp đồng xử lý dữ liệu với nhà cung cấp LLM (không dùng dữ liệu để huấn luyện, vùng lưu trữ).
- [ ] Kiểm thử prompt injection định kỳ bằng bộ ca tấn công trong `evals/security/`.
- [ ] Xoay vòng API key 90 ngày; thu hồi ngay khi nghi lộ.
