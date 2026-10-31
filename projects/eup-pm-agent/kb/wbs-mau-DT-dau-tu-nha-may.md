# WBS mẫu loại DT: đầu tư, lắp đặt dây chuyền / thiết bị tại nhà máy

Thời lượng là ngày làm việc, giả định ban đầu. Việc dài hơn 10 ngày phải tách nhỏ.

| Key | Việc | Vai trò | Thời lượng | Phụ thuộc | Bằng chứng |
|---|---|---|---|---|---|
| A1 | Chốt thông số kỹ thuật thiết bị | Kỹ thuật | 5 | — | — |
| A2 | Lập đề xuất mua sắm | Kỹ thuật | 2 | A1 | Material Request · workflow_state = Approved |
| A3 | Hỏi giá, so sánh nhà cung cấp | Mua hàng | 7 | A2 | — |
| A4 | Đặt hàng thiết bị | Mua hàng | 3 | A3 | Purchase Order · workflow_state = Approved |
| A5 | Tạm ứng đợt 1 | Kế toán | 3 | A4 | Payment Entry · docstatus = 1 |
| A6 | Chuẩn bị mặt bằng, móng máy | Kỹ thuật | 10 | A1 | — |
| A7 | Sản xuất và giao hàng (nhà cung cấp) | Mua hàng | 10 (thường phải tách nhiều đoạn) | A5 | — |
| A8 | Thông quan (hàng nhập khẩu) | Logistics | 5 | A7 | Customs declaration · thông quan |
| A9 | Nhập kho thiết bị | Kho | 1 | A8 | Purchase Receipt · docstatus = 1 |
| A10 | Lắp đặt | Kỹ thuật | 10 | A6, A9 | — |
| A11 | Chạy thử không tải (mốc) | Kỹ thuật | 1 | A10 | — |
| A12 | Đào tạo vận hành | Kỹ thuật | 3 | A10 | — |
| A13 | Chạy thử có tải, nghiệm thu (mốc) | QA | 2 | A11, A12 | — |
| A14 | Thanh toán đợt cuối | Kế toán | 3 | A13 | Payment Entry · docstatus = 1 |

Rủi ro thường gặp: chậm duyệt PO và tạm ứng; hàng nhập bị kiểm hóa; mặt bằng chưa xong khi hàng về.
