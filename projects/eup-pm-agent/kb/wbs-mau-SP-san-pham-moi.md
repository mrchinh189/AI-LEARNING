# WBS mẫu loại SP: phát triển sản phẩm mới cho khách hàng

| Key | Việc | Vai trò | Thời lượng | Phụ thuộc | Bằng chứng |
|---|---|---|---|---|---|
| D1 | Nhận yêu cầu, chốt thông số khách hàng | Kinh doanh | 3 | — | — |
| D2 | Thiết kế, ra bản vẽ | R&D | 10 | D1 | — |
| D3 | Lập BOM nháp, tính giá | R&D | 3 | D2 | — |
| D4 | Mua vật tư mẫu | Mua hàng | 7 | D3 | Purchase Receipt · docstatus = 1 |
| D5 | Sản xuất mẫu | Nhà máy | 5 | D4 | Yeu cau san xuat · hoàn thành |
| D6 | Gửi mẫu khách hàng (mốc) | Logistics | 2 | D5 | Delivery Note · docstatus = 1 |
| D7 | Chỉnh sửa theo góp ý | R&D | 5 | D6 | — |
| D8 | Ban hành BOM chính thức (mốc) | R&D | 1 | D7 | BOM · docstatus = 1 |
