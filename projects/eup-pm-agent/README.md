# eup-pm-agent — bộ khởi đầu AI agent quản lý tiến độ trên ERP EuP

Bản chạy được đầu tiên (MVP) của giải pháp trong [AI Agent Team quản lý tiến độ dự án](../../docs/ai-agent-team/quan-ly-tien-do-du-an-eup.md).
Hướng dẫn cài đặt và chạy từng bước cho người mới: [Hướng dẫn triển khai từng bước](../../docs/ai-agent-team/huong-dan-trien-khai-tung-buoc.md).

## Bản này làm được gì

| Lệnh | Tương ứng agent trong thiết kế | Việc làm |
|---|---|---|
| `setup-erp` | — | Tạo Role, 3 doctype `Nx …` và các custom field trên Project/Task |
| `compute` | Engine tính toán | In ra % kế hoạch, % thực tế, SPI, đường găng, cảnh báo. Không ghi gì |
| `daily` | ④ Đối chiếu chứng từ + ⑤ (phần quy tắc) | Đối chiếu chứng từ, tự hoàn thành Task, ghi RAG/SPI lên Project, tạo Nx Project Alert, email cảnh báo Đỏ cho PM |
| `checkin` | ③ Thu thập + ⑦ Giao tiếp (qua email) | Mỗi người phụ trách nhận 1 email/ngày liệt kê việc cần cập nhật |
| `report` | ⑥ Báo cáo | Soạn Nx Project Status Report nháp; số liệu do engine tính, phần nhận định do Claude viết |
| `publish` | ⑦ Giao tiếp | Gửi báo cáo PM đã chuyển sang "Đã phát hành" |

Chưa có trong bản này (làm ở Giai đoạn 3): kênh Zalo/Google Chat, đọc câu trả lời tự do của người phụ trách, Agent Lập kế hoạch, Agent Điều phối.

## Chạy nhanh (máy đã có Python 3.10+)

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/python -m pytest -q          # chạy thử trên ERP giả, không cần mạng
cp .env.example .env                   # rồi điền ERP_URL, ERP_API_KEY, ERP_API_SECRET
.venv/bin/python -m eup_pm ping
```

## An toàn

- `DRY_RUN=1` (mặc định): không ghi gì lên ERP, không gửi email, chỉ in ra những gì sẽ làm.
- Agent chỉ được ghi các doctype và field trong `WRITE_ALLOWLIST` (`eup_pm/erp.py`). Chứng từ nghiệp vụ luôn chỉ đọc.
- Mỗi Comment do agent ghi có tiền tố `[AI-Agent]`. Log mỗi ngày nằm ở `logs/`.
