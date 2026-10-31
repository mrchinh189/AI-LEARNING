# WBS mẫu loại XK: đơn hàng xuất khẩu theo lô container

Thời lượng là ngày làm việc, giả định ban đầu.

| Key | Việc | Vai trò | Thời lượng | Phụ thuộc | Bằng chứng |
|---|---|---|---|---|---|
| B1 | Chốt đơn bán hàng | Kinh doanh | 2 | — | Sales Order · workflow_state = Approved |
| B2 | Lập yêu cầu sản xuất | Kế hoạch sản xuất | 1 | B1 | Yeu cau san xuat · đã duyệt |
| B3 | Mua nguyên vật liệu thiếu | Mua hàng | 7 | B2 | Purchase Receipt · docstatus = 1 |
| B4 | Sản xuất | Nhà máy | 10 (tách theo lô) | B3 | Yeu cau san xuat · hoàn thành |
| B5 | Kiểm tra chất lượng | QA | 2 | B4 | — |
| B6 | Booking tàu | Logistics | 3 | B1 | — |
| B7 | Lập yêu cầu xuất hàng, xuất kho chờ bán | Kho | 1 | B5 | Stock Entry · docstatus = 1 |
| B8 | Đóng hàng container (mốc) | Logistics | 2 | B6, B7 | Container Load Plan · docstatus = 1 |
| B9 | Tờ khai xuất khẩu | Logistics | 2 | B8 | Customs declaration · thông quan |
| B10 | Giao hàng, xuất hóa đơn (mốc) | Kế toán | 1 | B9 | Sales Invoice · docstatus = 1 |

Rủi ro thường gặp: thiếu nguyên vật liệu; trễ booking; lệch packing list theo container.
