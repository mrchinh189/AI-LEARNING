# Bản đồ chứng từ bằng chứng: loại việc → chứng từ ERP EuP và điều kiện xong

Dùng cho cột `evidence` của WBS. Dạng ghi: `Doctype · trường = giá trị`.

| Loại việc | Chứng từ (doctype) | Điều kiện xong |
|---|---|---|
| Đề xuất mua sắm | Material Request | workflow_state = Approved |
| Đặt hàng nhà cung cấp | Purchase Order | workflow_state = Approved |
| Tạm ứng cho nhà cung cấp | Nx Request For Advance | trạng thái cuối của workflow (PMO xác nhận tên state) |
| Thanh toán theo đợt | De nghi thanh toan, sau đó Payment Entry | Payment Entry · docstatus = 1 |
| Hàng về kho | Purchase Receipt | docstatus = 1 |
| Thông quan hàng nhập | Customs declaration | trạng thái thông quan (PMO xác nhận tên state) |
| Sản xuất lô hàng | Yeu cau san xuat | trạng thái hoàn thành (PMO xác nhận) |
| Xuất kho chờ bán | Stock Entry (7. Xuất kho chờ bán) | docstatus = 1 |
| Đóng hàng container | Container Load Plan | docstatus = 1 |
| Giao hàng | Delivery Note | docstatus = 1 |
| Xuất hóa đơn | Sales Invoice | docstatus = 1 |
| Ban hành định mức sản phẩm mới | BOM | docstatus = 1 |

Việc không có chứng từ (họp, đào tạo, thiết kế, nghiệm thu) để evidence rỗng; tiến độ do người phụ trách tự khai, PM xác nhận.
