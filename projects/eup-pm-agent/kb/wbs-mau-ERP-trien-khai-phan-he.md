# WBS mẫu loại ERP: triển khai hoặc cải tiến một phân hệ ERP EuP

| Key | Việc | Vai trò | Thời lượng | Phụ thuộc | Bằng chứng |
|---|---|---|---|---|---|
| C1 | Khảo sát quy trình hiện tại | BA | 5 | — | — |
| C2 | Dựng lưu đồ thao tác ERP, chốt với phòng ban | BA | 5 | C1 | — |
| C3 | Cấu hình doctype, workflow, quyền trên UAT | Frappe dev | 10 | C2 | — |
| C4 | Chuẩn bị dữ liệu danh mục (master data) | Phòng ban sử dụng | 5 | C2 | — |
| C5 | Kiểm thử chấp nhận (UAT) | Phòng ban sử dụng | 5 | C3, C4 | — |
| C6 | Đào tạo người dùng | BA | 3 | C5 | — |
| C7 | Go-live trên PROD (mốc) | Frappe dev | 1 | C6 | chứng từ đầu tiên của doctype · docstatus = 1 |
| C8 | Hỗ trợ sau go-live | BA | 10 | C7 | — |
