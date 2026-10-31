# eup-agents — MVP AI agent quản lý tiến độ công việc (EuP)

Bản chạy được của giải pháp trong [docs/eup-office-agent-team](../../docs/eup-office-agent-team/README.md).
Hướng dẫn cài đặt và chạy từng bước: **[RUNBOOK.md](../../docs/eup-office-agent-team/RUNBOOK.md)**.

| Lệnh | Agent | Việc làm | Cần LLM? |
|---|---|---|---|
| `python -m eup_agents nudge` | A2 Nhắc việc | Nhắc trước hạn/đến hạn/trễ, leo thang 4 mức, gộp 1 tin/người | Không |
| `python -m eup_agents report` | A5 Báo cáo | Báo cáo tuần theo phòng ra `reports/*.md` | Tùy chọn (phần nhận định) |
| `python -m eup_agents erp-watch` | A3 Giám sát ERP | Chứng từ nháp quá hạn, phiếu nhập chưa có hóa đơn → Task nháp | Không |
| `python -m eup_agents intake --file … --sender …` | A1 Tiếp nhận | Email/tin nhắn → Task nháp chờ xác nhận | Có |
| `uvicorn eup_agents.server:app` | — | HTTP API cho n8n gọi (`/run/<agent>`) | — |

Cấu trúc:

```text
eup_agents/
  config.py      đọc .env và config/org.json
  erp.py         client REST Frappe/ERPNext; mọi lệnh ghi đi qua guard
  guard.py       Lớp Kiểm soát: allowlist ghi + nhật ký logs/agent_actions.jsonl
  llm.py         gọi Claude API; lỗi thì trả None để agent chạy tiếp theo luật
  notify.py      gửi tin: console | erp_bell | webhook (n8n)
  workdays.py    ngày làm việc theo Holiday List của công ty
  agents/        nudge.py · report.py · erp_watch.py · intake.py
  setup_erp.py   tạo custom field cho Task (setup/custom_fields.json)
tests/           test với ERP giả lập — chạy: python -m pytest -q
```

An toàn: `DRY_RUN=true` mặc định (chỉ đọc). Agent chỉ ghi được `Task` (tạo nháp, sửa `eup_escalation_level`, giao việc), `Comment` trên Task và `Notification Log`.
