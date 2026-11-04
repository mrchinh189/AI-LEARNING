# Skill: Đăng bán đồ cũ trên chợ online

## Mô tả
Từ ảnh/mô tả một món đồ cũ: định giá theo thị trường, viết tin đăng theo văn phong của chủ, đăng (có duyệt) và lên lịch giảm giá.

## Các bước
1. Xác định chính xác model sản phẩm và tình trạng (hỏi người vận hành nếu thiếu).
2. Giao `researcher` tra giá mới niêm yết trên trang chính hãng và giá rao bán đồ cũ thấp nhất trong khu vực; yêu cầu ghi nguồn.
3. Đề xuất giá đăng: thấp hơn mức rẻ nhất khu vực một chút nếu muốn bán nhanh, nêu rõ lý do.
4. Giao `writer` viết tin đăng theo văn phong các tin đăng trước của người vận hành (tiêu đề, mô tả tình trạng, phụ kiện kèm theo, cách giao dịch).
5. Trình bản tin đăng + giá cho người vận hành, rồi gọi `publish` (cần duyệt).
6. Ghi lịch giảm giá vào `outputs/price-schedule.md`: nếu sau 7 ngày chưa bán thì giảm một mức cố định (mặc định 5%), tối đa đến giá sàn người vận hành chấp nhận.

## Tiêu chí đạt
- Có giá mới chính hãng và giá đồ cũ thấp nhất khu vực, kèm nguồn (hoặc ghi rõ là chưa kiểm chứng được).
- Giá đề xuất có lý do dựa trên các mức giá trên.
- Tin đăng có tiêu đề, tình trạng, phụ kiện, cách giao dịch; đúng văn phong người vận hành.
- Có lịch giảm giá với mức giảm và giá sàn cụ thể.
- Không đăng khi chưa được duyệt.
