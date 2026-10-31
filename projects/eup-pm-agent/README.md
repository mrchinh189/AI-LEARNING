# eup-pm-agent — bộ khởi đầu AI agent quản lý tiến độ trên ERP EuP

Bản chạy được đầu tiên (MVP) của giải pháp trong [AI Agent Team quản lý tiến độ dự án](../../docs/ai-agent-team/quan-ly-tien-do-du-an-eup.md).
Hướng dẫn cài đặt và chạy từng bước cho người mới: [Hướng dẫn triển khai từng bước](../../docs/ai-agent-team/huong-dan-trien-khai-tung-buoc.md).

## Bản này làm được gì

| Lệnh | Tương ứng agent trong thiết kế | Việc làm |
|---|---|---|
| `setup-erp` | — | Tạo Role, 4 doctype `Nx …` và các custom field trên Project/Task (chạy lại an toàn, tự thêm field mới) |
| `compute` | Engine tính toán | In ra % kế hoạch, % thực tế, SPI, đường găng, cảnh báo. Không ghi gì |
| `daily` | ④ Đối chiếu chứng từ + ⑤ (phần quy tắc) | Đối chiếu chứng từ, tự hoàn thành Task, ghi RAG/SPI lên Project, tạo Nx Project Alert, email cảnh báo Đỏ cho PM |
| `checkin` | ③ Thu thập + ⑦ Giao tiếp (qua email) | Mỗi người phụ trách nhận 1 email/ngày liệt kê việc cần cập nhật |
| `report` | ⑥ Báo cáo | Soạn Nx Project Status Report nháp; số liệu do engine tính, phần nhận định do Claude viết |
| `publish` | ⑦ Giao tiếp | Gửi báo cáo PM đã chuyển sang "Đã phát hành" |

### Agent team (`eup_pm/agents/`)

Bốn agent là vòng lặp tool-use với Claude, mỗi agent có bộ tool, quyền và ngân sách riêng. Giải pháp: [agent-team-giai-phap.md](../../docs/ai-agent-team/agent-team-giai-phap.md).

| Lệnh | Agent | Việc làm |
|---|---|---|
| `ask "câu hỏi"` | ① Điều phối | Trả lời PM, tự giao việc cho agent khác khi cần |
| `plan --project P` → PM duyệt → `apply-plan --draft KH-…` | ② Lập kế hoạch | Soạn WBS nháp từ `kb/`, engine kiểm tra lịch; Task chỉ được tạo sau khi PM duyệt |
| `reply --from e --text "..."` | ③ Thu thập | Đọc tin trả lời tự do, cập nhật đúng Task của người gửi, hỏi lại khi mơ hồ |
| `risk --alert A` (và tự động sau `daily`) | ⑤ Rủi ro | Lần theo phụ thuộc và chứng từ, ghi nguyên nhân gốc và phương án vào Alert |
| `event --json '{...}'`, `serve` | Bộ định tuyến | Đưa sự kiện từ n8n/webhook tới đúng agent |

Mỗi lần gọi tool được ghi vào `logs/audit-YYYY-MM-DD.jsonl`.

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
