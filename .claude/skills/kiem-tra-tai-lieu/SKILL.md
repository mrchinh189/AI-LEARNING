---
name: kiem-tra-tai-lieu
description: Kiểm tra chất lượng tài liệu thiết kế giải pháp trong docs/solution-design — header, đủ 12 mục đúng thứ tự, sơ đồ Mermaid parse được bằng mermaid@11, bảng danh mục README đồng bộ. Dùng khi người dùng nói "kiểm tra tài liệu", "check mermaid", "validate docs", "rà soát solution design", hoặc ngay sau khi tạo/sửa một file trong docs/solution-design.
---

# Kiểm tra tài liệu thiết kế giải pháp

## Chạy script

Lần đầu trong một môi trường mới, cài dependency (mermaid@11 + jsdom, nằm riêng trong thư mục script, đã được gitignore):

```bash
npm install --prefix .claude/skills/kiem-tra-tai-lieu/scripts
```

Kiểm tra toàn bộ (gồm cả đồng bộ danh mục):

```bash
node .claude/skills/kiem-tra-tai-lieu/scripts/check_docs.mjs
```

Kiểm tra một vài file (bỏ qua bước đồng bộ danh mục):

```bash
node .claude/skills/kiem-tra-tai-lieu/scripts/check_docs.mjs docs/solution-design/<repo>.md
```

Mã thoát `0` = hợp lệ, `1` = có lỗi; mỗi lỗi in một dòng `✗ <file>: <mô tả>`.

## Script kiểm tra những gì

1. Dòng 1 dạng `# <Tên> — Tài liệu thiết kế giải pháp`.
2. Header có đủ **Fork**, **Upstream**, **Nhóm**, **Ngôn ngữ chính**, **License**, **Commit đã phân tích** (sha trong backtick), không còn placeholder `<...>`.
3. Đúng 12 mục `## 1. Tóm tắt` … `## 12. Tham khảo` theo `_TEMPLATE.md`.
4. Mọi khối ```` ```mermaid ```` parse được; có ít nhất một sơ đồ.
5. (Chạy toàn bộ) mọi tài liệu có link trong bảng danh mục `docs/solution-design/README.md`, không có link chết, và số "của N repo" khớp số tài liệu.

## Sửa lỗi Mermaid thường gặp

- Nhãn có ký tự đặc biệt (`()`, `:`, `/`, `#`, dấu tiếng Việt kèm ngoặc) → bọc trong `"..."`: `A["convert() / stream"]`.
- Xuống dòng trong nhãn dùng `<br/>`, không dùng `\n`.
- Mũi tên flowchart hợp lệ: `-->`, `-.->`, `==>`, `-- "nhãn" -->`, `-. "nhãn" .->`. `-->>` chỉ hợp lệ trong `sequenceDiagram`.
- `sequenceDiagram`: tên participant có khoảng trắng phải khai báo alias `participant W as Worker pool`.
- Không dùng từ khoá `end` trần làm id node (đổi thành `End` hoặc `done`).

## Ngoài script — rà soát thủ công

Script chỉ kiểm tra hình thức. Khi người dùng yêu cầu rà soát nội dung, kiểm tra thêm:

- Đường dẫn file trong mục 4 và 12 có thật trong repo ở commit đã ghi (nếu có thể clone).
- Bảng mục 8 có đủ 3 cột Quyết định / Lý do / Đánh đổi, không để trống "Đánh đổi".
- Mục 11 là bài học có thể áp dụng được, không lặp lại mục 1.
- Văn phong tiếng Việt nhất quán; thuật ngữ kỹ thuật giữ tiếng Anh trong backtick.

Báo kết quả: số lỗi, danh sách lỗi đã sửa, và output cuối của script (phải là `✓ N tài liệu hợp lệ.`).
