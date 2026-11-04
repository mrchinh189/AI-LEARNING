#!/usr/bin/env node
// Kiểm tra tài liệu thiết kế giải pháp trong docs/solution-design:
//  1. Khối header (Fork / Upstream / Nhóm / Ngôn ngữ / License / Commit)
//  2. Đủ 12 mục "## N. ..." đúng thứ tự
//  3. Mọi khối ```mermaid parse được bằng mermaid@11
//  4. Mọi tài liệu đều có dòng trong bảng danh mục README.md và ngược lại
//
// Cách dùng:
//   npm install --prefix .claude/skills/kiem-tra-tai-lieu/scripts   (lần đầu)
//   node .claude/skills/kiem-tra-tai-lieu/scripts/check_docs.mjs [file.md ...]
// Không truyền file => kiểm tra toàn bộ thư mục. Mã thoát 1 nếu có lỗi.

import { readFileSync, readdirSync, existsSync } from 'node:fs';
import { join, basename, resolve, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';

const here = dirname(fileURLToPath(import.meta.url));
const repoRoot = resolve(here, '../../../..');
const docDir = join(repoRoot, 'docs/solution-design');

const SECTIONS = [
  'Tóm tắt', 'Bài toán & yêu cầu', 'Kiến trúc tổng thể', 'Thành phần chính',
  'Luồng xử lý chính', 'Mô hình dữ liệu & giao diện', 'Tech stack',
  'Quyết định thiết kế & đánh đổi', 'Triển khai & vận hành', 'Điểm mở rộng',
  'Bài học & cách áp dụng', 'Tham khảo',
];
const HEADER_KEYS = ['**Fork:**', '**Upstream:**', '**Nhóm:**', '**Ngôn ngữ chính:**', '**License:**', '**Commit đã phân tích:**'];

let mermaid = null;
try {
  const { JSDOM } = await import('jsdom');
  const dom = new JSDOM('<!doctype html><html><body></body></html>');
  globalThis.window = dom.window;
  globalThis.document = dom.window.document;
  mermaid = (await import('mermaid')).default;
} catch {
  console.warn('⚠ Chưa cài mermaid/jsdom — bỏ qua kiểm tra Mermaid.\n  Chạy: npm install --prefix .claude/skills/kiem-tra-tai-lieu/scripts\n');
}

const args = process.argv.slice(2);
const files = args.length
  ? args.map((f) => resolve(f))
  : readdirSync(docDir).filter((f) => f.endsWith('.md') && f !== 'README.md' && !f.startsWith('_')).map((f) => join(docDir, f));

let errors = 0;
const err = (file, msg) => { errors++; console.log(`✗ ${basename(file)}: ${msg}`); };

for (const file of files) {
  const text = readFileSync(file, 'utf8');
  const lines = text.split('\n');

  if (!/^# .+ — Tài liệu thiết kế giải pháp$/.test(lines[0])) err(file, 'dòng 1 phải là "# <Tên> — Tài liệu thiết kế giải pháp"');
  const head = lines.slice(0, 8).join('\n');
  for (const k of HEADER_KEYS) if (!head.includes(k)) err(file, `header thiếu ${k}`);
  const sha = head.match(/\*\*Commit đã phân tích:\*\*\s*`([0-9a-f]{7,40})`/);
  if (!sha) err(file, 'commit đã phân tích phải là sha trong backtick');
  if (/<[^>\s]+>/.test(head.replace(/<br\/?>/g, ''))) err(file, 'header còn placeholder <...>');

  const found = lines.filter((l) => /^## \d+\. /.test(l)).map((l) => l.replace(/^## /, ''));
  SECTIONS.forEach((name, i) => {
    const want = `${i + 1}. ${name}`;
    if (found[i] !== want) err(file, `mục ${i + 1} phải là "## ${want}" (đang là "${found[i] ?? 'thiếu'}")`);
  });

  if (mermaid) {
    const re = /```mermaid\n([\s\S]*?)```/g;
    let m; let n = 0;
    while ((m = re.exec(text))) {
      n++;
      const line = text.slice(0, m.index).split('\n').length;
      try { await mermaid.parse(m[1]); } catch (e) { err(file, `Mermaid #${n} (dòng ${line}) lỗi: ${String(e.message).split('\n').slice(0, 3).join(' | ')}`); }
    }
    if (n === 0) err(file, 'không có sơ đồ Mermaid nào (mục 3 và 5 cần sơ đồ)');
  }
}

// Đồng bộ danh mục chỉ khi kiểm tra toàn bộ
if (!args.length) {
  const index = readFileSync(join(docDir, 'README.md'), 'utf8');
  const linked = new Set([...index.matchAll(/\]\(\.\/([\w.-]+\.md)\)/g)].map((m) => m[1]));
  for (const f of files) if (!linked.has(basename(f))) err(f, 'chưa có dòng trong bảng danh mục docs/solution-design/README.md');
  for (const l of linked) if (!existsSync(join(docDir, l)) ) { errors++; console.log(`✗ README.md: link tới file không tồn tại ${l}`); }
  const m = index.match(/của (\d+) repo/);
  if (m && Number(m[1]) !== files.length) { errors++; console.log(`✗ README.md: ghi ${m[1]} repo nhưng có ${files.length} tài liệu`); }
}

console.log(errors ? `\n${errors} lỗi trong ${files.length} tài liệu.` : `✓ ${files.length} tài liệu hợp lệ.`);
process.exit(errors ? 1 : 0);
