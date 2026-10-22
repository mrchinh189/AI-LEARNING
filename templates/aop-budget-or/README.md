# Bộ template AOP - Budget - OR

File Excel `Template_AOP_Budget_OR.xlsx` dùng để lập **AOP** (Annual Operating Plan - kế hoạch hoạt động năm), **Budget** (ngân sách chi tiết theo tháng) và **OR** (Outlook Revision - ước thực hiện cả năm). Cấu trúc mẫu theo doanh nghiệp FMCG/ngành sữa. Mọi số liệu trong file là **dữ liệu mẫu** để minh họa định dạng, cần thay bằng số thật.

## Ba lớp kế hoạch

| Lớp | Hướng lập | Kỳ | Sheet |
|---|---|---|---|
| AOP | Top-down (HĐQT/Ban TGĐ giao) | Năm | `AOP_MucTieu` |
| Budget | Bottom-up (các BP lập) | 12 tháng | `BG_DoanhThu`, `BG_GiaVon`, `BG_ChiPhi`, `BG_NhanSu`, `BG_Capex` → `BG_PL` |
| OR | Thực tế + dự báo lại | OR1 (3+9), OR2 (6+6), OR3 (9+3) | `ThucTe`, `OR_DuBao` |

`SoSanh` đặt AOP, Budget, OR và lũy kế Thực tế với Budget cạnh nhau, có cột giải trình.

## Luồng dữ liệu

```
GiaDinh (thuế, BH, tăng lương, mùa vụ, KH hiện hữu, số tháng thực tế)
   │
   ├─► BG_DoanhThu  (sản lượng năm × mùa vụ × giá − chiết khấu)
   │        └─► BG_GiaVon (sản lượng × giá thành đơn vị)
   ├─► BG_ChiPhi    (ngân sách năm, phân bổ Đều / Mùa vụ, nhóm BH&MKT / QLDN)
   ├─► BG_NhanSu    (định biên tháng × lương × tăng lương × BH)
   └─► BG_Capex     (nguyên giá → khấu hao đường thẳng + dòng tiền đầu tư)
            │
            ▼
         BG_PL ──► AOP_MucTieu (so Budget với mục tiêu AOP)
            │
ThucTe ─────┼──► OR_DuBao = IF(tháng ≤ số tháng thực tế, Thực tế, Budget + Điều chỉnh)
            ▼
         SoSanh (AOP | Budget | OR | lũy kế TT vs BG | giải trình)
```

## Quy ước

- **Chữ xanh dương** là ô nhập. **Nền vàng** là giả định then chốt hoặc ô bắt buộc nhập. **Chữ đen** là công thức, **chữ xanh lá** là liên kết sang sheet khác, không sửa các ô này.
- Đơn vị là triệu VND, sản lượng tính bằng tấn.
- Trên P&L, chi phí mang dấu âm. Ở mọi cột chênh lệch, số dương là **thuận lợi**.
- Nhân công sản xuất nằm trong *chi phí chuyển đổi* của giá thành. `BG_NhanSu` chỉ gồm khối văn phòng và bán hàng. Khấu hao trình bày riêng một dòng.

## Quy trình lập OR (mỗi quý)

1. Lưu một bản Budget đã duyệt riêng. Sau khi duyệt thì không sửa các sheet `BG_*` nữa.
2. Nhập số thực tế các tháng đã khóa sổ vào `ThucTe`. Phần ghi chú trên sheet có sẵn mapping tài khoản theo TT200.
3. Đặt `GiaDinh!C15` bằng số tháng thực tế (3, 6 hoặc 9).
4. Nhập điều chỉnh cho các tháng dự báo vào khối *Điều chỉnh dự báo* ở `OR_DuBao`, ghi kèm lý do.
5. Rà soát `SoSanh` và giải trình các chênh lệch trọng yếu.

## Sinh lại file

```bash
python build_template.py Template_AOP_Budget_OR.xlsx [đường_dẫn/recalc.py]
```

Nếu truyền thêm script recalc (LibreOffice), script sẽ tính lại công thức và điền số mẫu cho Thực tế T1-T6, TH năm trước và mục tiêu AOP. Muốn đổi danh mục sản phẩm, kênh, BP hoặc dữ liệu mẫu thì sửa các hằng số ở đầu `build_template.py`.
