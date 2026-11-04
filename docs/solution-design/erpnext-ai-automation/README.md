# AI tự động hóa thao tác ERPNext — Thiết kế kỹ thuật chi tiết

Thư mục này đi sâu vào thiết kế kỹ thuật của từng thành phần và từng giải pháp (use case) trong tài liệu tổng quan [AI tự động hóa thao tác ERPNext](../erpnext-ai-automation.md).

Đọc theo thứ tự: tài liệu tổng quan → **00 Nền tảng chung** → tài liệu use case cần triển khai.

## Danh mục

| Mã | Tài liệu | Mức tự động (khởi đầu → mục tiêu) | DocType chính |
|---|---|---|---|
| 00 | [Nền tảng chung](./00-nen-tang-chung.md) | — | AI Job, AI Action Log, AI Mapping, AI Settings |
| UC01 | [Nhập hóa đơn mua hàng](./01-nhap-hoa-don-mua-hang.md) | L1 → L2 | Purchase Invoice, Purchase Receipt, Purchase Order |
| UC02 | [Tạo đơn bán hàng từ PO khách hàng](./02-don-ban-hang-tu-po.md) | L1 → L2 | Quotation, Sales Order |
| UC03 | [Hỏi đáp số liệu qua chat](./03-hoi-dap-so-lieu.md) | L0 | Báo cáo AR/AP, Stock Balance, Sales Analytics |
| UC04 | [Đối soát ngân hàng](./04-doi-soat-ngan-hang.md) | L1 → L2 | Bank Transaction, Payment Entry |
| UC05 | [Nhắc công nợ](./05-nhac-cong-no.md) | L1 → L2 | Dunning, Communication |
| UC06 | [Làm sạch master data](./06-lam-sach-master-data.md) | L0 / L1 | Customer, Supplier, Item |
| UC07 | [Tóm tắt & hỗ trợ duyệt, phản ứng sự kiện](./07-tom-tat-ho-tro-duyet.md) | L0 + duyệt | Purchase Order, Material Request, Workflow |

## Cấu trúc mỗi tài liệu use case

1. Mục tiêu & KPI · 2. Phạm vi, đầu vào/đầu ra, điều kiện tiên quyết · 3. Luồng xử lý chi tiết · 4. Thiết kế dữ liệu · 5. Thuật toán & quy tắc nghiệp vụ · 6. Agent (tool, prompt) · 7. Policy · 8. Xử lý ngoại lệ · 9. Giao diện người dùng · 10. Kiểm thử & eval · 11. Kế hoạch triển khai & ước lượng công · 12. Rủi ro còn mở

## Quy ước dùng chung

- Tên tool theo [00 §6.2](./00-nen-tang-chung.md#62-danh-mục-tool); tool mới được ghi rõ là "tool bổ sung".
- Trạng thái job theo state machine ở [00 §3.2](./00-nen-tang-chung.md#32-state-machine).
- Mức tự động L0–L3 theo [tài liệu tổng quan §4.3](../erpnext-ai-automation.md#43-mức-độ-tự-động-autonomy-level).
- Tên field, tên hàm ERPNext viết theo Frappe/ERPNext v15; chỗ nào ghi "cần đối chiếu phiên bản" phải kiểm tra lại trên site đang chạy trước khi lập trình.
