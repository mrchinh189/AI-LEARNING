"""Các việc chạy theo lịch: daily (đối chiếu + tính toán + cảnh báo), checkin (nhắc việc), report, publish."""

from __future__ import annotations

import html
import logging
from collections import defaultdict
from datetime import date, datetime, timedelta

from .config import Settings
from .engine import ProjectResult, evaluate_project, fmt_date, fmt_num, fmt_pct
from .erp import ErpClient, ErpError
from .evidence import verify_task
from .llm import NarrativeError, write_narrative
from .loader import active_projects, calendar_for, load_task_docs, parse_date, to_task_data

log = logging.getLogger("eup_pm.jobs")


# ---------------------------------------------------------------- tính toán một dự án

def analyse_project(erp: ErpClient, settings: Settings, project: dict, today: date,
                    verify: bool = True) -> tuple[ProjectResult, list[dict]]:
    docs = load_task_docs(erp, project["name"])
    overrides = {}
    if verify:
        rejected_values = settings.rules.get("evidence", {}).get("rejected_values", [])
        for d in docs:
            r = verify_task(erp, d, rejected_values, today)
            if r is not None:
                overrides[d["name"]] = r
                if r[0] and d.get("status") != "Completed":
                    d["status"], d["progress"] = "Completed", 100
    tasks = [to_task_data(d, overrides) for d in docs]
    cal = calendar_for(erp, project.get("company"))
    deadline = parse_date(project.get("custom_baseline_end")) or parse_date(project.get("expected_end_date"))
    result = evaluate_project(tasks, cal, today, settings.rules, deadline)
    return result, docs


# ---------------------------------------------------------------- daily

def run_daily(erp: ErpClient, settings: Settings, only: str | None = None, today: date | None = None):
    today = today or date.today()
    projects = active_projects(erp, only)
    if not projects:
        log.warning("Không có Project nào ở trạng thái Open và bật 'Bật AI agent'")
        return []
    summary = []
    for p in projects:
        try:
            res, docs = analyse_project(erp, settings, p, today)
        except ErpError as e:
            log.error("Dự án %s lỗi khi đọc ERP: %s", p["name"], e)
            continue
        subjects = {d["name"]: d.get("subject") for d in docs}
        erp.update("Project", p["name"], {
            "custom_rag": res.rag,
            "custom_spi": round(res.spi, 3) if res.spi is not None else 0,
            "custom_forecast_end": res.forecast_end.isoformat() if res.forecast_end else None,
            "custom_last_agent_run": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        })
        for err in res.data_errors:
            log.warning("Dự án %s – lỗi dữ liệu: %s", p["name"], err)
        if res.data_errors:
            _notify_data_errors(erp, p, res.data_errors)
        created = create_alerts(erp, settings, p, res, today)
        summary.append((p["name"], res, created))
        log.info("%s | RAG %s | KH %s | TT %s | SPI %s | dự báo %s | %d cảnh báo mới (%d task)",
                 p["name"], res.rag, fmt_pct(res.planned_pct), fmt_pct(res.actual_pct),
                 fmt_num(res.spi, 2), fmt_date(res.forecast_end), created, len(subjects))
    return summary


def create_alerts(erp: ErpClient, settings: Settings, project: dict, res: ProjectResult,
                  today: date) -> int:
    cooldown = settings.rules.get("alerts", {}).get("same_alert_cooldown_days", 3)
    since = (today - timedelta(days=cooldown)).isoformat()
    existing = erp.get_list("Nx Project Alert", filters=[
        ["project", "=", project["name"]],
        ["creation", ">=", since],
        ["status", "in", ["Mới", "Đã xem"]],
    ], fields=["task", "rule_code"])
    seen = {(e.get("task") or "", e.get("rule_code")) for e in existing}
    created = 0
    for a in res.alerts:
        if (a.task or "", a.rule_code) in seen:
            continue
        erp.insert("Nx Project Alert", {
            "project": project["name"],
            "task": a.task,
            "severity": a.severity,
            "rule_code": a.rule_code,
            "facts": a.facts,
            "status": "Mới",
        })
        created += 1
    if created and project.get("custom_pmo_owner"):
        red = [a for a in res.alerts if a.severity == "Đỏ"]
        if red:
            items = "".join(f"<li>{html.escape(a.facts)}</li>" for a in red)
            erp.send_email([project["custom_pmo_owner"]],
                           f"[Cảnh báo ĐỎ] {project.get('project_name') or project['name']}",
                           f"<p>Hệ thống phát hiện:</p><ul>{items}</ul>"
                           f"<p><a href='{erp.base_url}/app/nx-project-alert?project="
                           f"{project['name']}'>Mở danh sách cảnh báo</a></p>",
                           "Project", project["name"])
    return created


def _notify_data_errors(erp: ErpClient, project: dict, errors: list[str]):
    if not project.get("custom_pmo_owner"):
        return
    items = "".join(f"<li>{html.escape(e)}</li>" for e in errors)
    erp.send_email([project["custom_pmo_owner"]],
                   f"[Cần sửa kế hoạch] {project.get('project_name') or project['name']}",
                   f"<p>Kế hoạch trên ERP có lỗi nên chưa tính được cảnh báo tiến độ:</p><ul>{items}</ul>",
                   "Project", project["name"])


# ---------------------------------------------------------------- checkin (nhắc việc)

def run_checkin(erp: ErpClient, settings: Settings, only: str | None = None, today: date | None = None):
    """Gửi mỗi người phụ trách 1 email/ngày, gom các việc sắp đến hạn hoặc lâu chưa cập nhật."""
    today = today or date.today()
    cfg = settings.rules.get("checkin", {})
    horizon = today + timedelta(days=cfg.get("due_within_days", 14))
    stale_wd = cfg.get("stale_after_wd", 3)

    per_owner: dict[str, list[tuple[dict, dict]]] = defaultdict(list)
    unassigned: dict[str, list[dict]] = defaultdict(list)
    for p in active_projects(erp, only):
        cal = calendar_for(erp, p.get("company"))
        for d in load_task_docs(erp, p["name"]):
            t = to_task_data(d)
            if t.done or t.is_group:
                continue
            due_soon = t.exp_end is not None and t.exp_end <= horizon
            stale = t.last_update is not None and cal.offset(t.last_update, today) > stale_wd
            if not (due_soon or stale):
                continue
            if not t.owners:
                unassigned[p["name"]].append(d)
                continue
            for o in t.owners:
                per_owner[o].append((p, d))

    for owner, items in per_owner.items():
        rows = "".join(
            f"<tr><td>{html.escape(p.get('project_name') or p['name'])}</td>"
            f"<td><a href='{erp.link('Task', d['name'])}'>{html.escape(d.get('subject') or d['name'])}</a></td>"
            f"<td>{fmt_date(parse_date(d.get('exp_end_date')))}</td>"
            f"<td>{fmt_num(float(d.get('progress') or 0))}%</td></tr>"
            for p, d in items)
        body = (
            "<p>Chào anh/chị,</p><p>Nhờ anh/chị cập nhật các việc dưới đây trên ERP "
            "(mở việc → sửa <b>% Tiến độ</b>, <b>Dự kiến xong</b>, <b>Vướng mắc</b> → <b>Lưu</b>):</p>"
            "<table border='1' cellpadding='4' cellspacing='0'>"
            "<tr><th>Dự án</th><th>Việc</th><th>Hạn</th><th>Tiến độ hiện tại</th></tr>"
            f"{rows}</table><p>Cảm ơn anh/chị. — AI Agent PMO</p>")
        erp.send_email([owner], f"[Cập nhật tiến độ] {len(items)} việc cần cập nhật", body)
        log.info("Nhắc %s: %d việc", owner, len(items))

    for pname, docs in unassigned.items():
        p = next((x for x in active_projects(erp, pname)), None)
        if p and p.get("custom_pmo_owner"):
            items = "".join(f"<li><a href='{erp.link('Task', d['name'])}'>"
                            f"{html.escape(d.get('subject') or d['name'])}</a></li>" for d in docs)
            erp.send_email([p["custom_pmo_owner"]], f"[Chưa giao người] {p.get('project_name') or pname}",
                           f"<p>Các việc sắp đến hạn nhưng chưa giao người phụ trách:</p><ul>{items}</ul>")
    return per_owner


# ---------------------------------------------------------------- báo cáo tuần

def build_facts(project: dict, res: ProjectResult, docs: list[dict], erp: ErpClient,
                today: date) -> dict:
    by_name = {d["name"]: d for d in docs}
    week_ago = today - timedelta(days=7)
    horizon = today + timedelta(days=14)

    milestones = []
    for name, tr in res.tasks.items():
        d = by_name[name]
        end = parse_date(d.get("exp_end_date"))
        if d.get("is_milestone") and d.get("status") != "Completed" and end and end <= horizon:
            milestones.append({
                "mốc": d.get("subject"), "hạn": fmt_date(end),
                "dự_báo": fmt_date(tr.early_finish),
                "trên_đường_găng": tr.critical,
            })
    done = []
    for d in docs:
        c = parse_date(d.get("completed_on"))
        if d.get("status") == "Completed" and c and c >= week_ago:
            ev = [f"{r.get('reference_doctype')} {r.get('reference_name')}"
                  for r in d.get("custom_evidence") or []]
            done.append({"việc": d.get("subject"), "bằng_chứng": ev or "tự khai"})
    blockers = [{"việc": d.get("subject"), "vướng": d.get("custom_blocker")}
                for d in docs if d.get("custom_blocker") and d.get("status") != "Completed"]
    return {
        "dự_án": project.get("project_name") or project["name"],
        "mã_dự_án": project["name"],
        "loại": project.get("custom_eup_project_type"),
        "số_liệu_đến_ngày": fmt_date(today),
        "rag": res.rag,
        "kế_hoạch": fmt_pct(res.planned_pct),
        "thực_tế": fmt_pct(res.actual_pct),
        "spi": fmt_num(res.spi, 2),
        "ngày_kết_thúc_baseline": fmt_date(res.deadline),
        "ngày_dự_báo_kết_thúc": fmt_date(res.forecast_end),
        "trễ_ngày_làm_việc": res.slip_wd if res.slip_wd and res.slip_wd > 0 else 0,
        "cảnh_báo_đang_mở": [{"mức": a.severity, "mã": a.rule_code, "nội_dung": a.facts} for a in res.alerts],
        "mốc_2_tuần_tới": milestones,
        "đã_xong_trong_tuần": done,
        "vướng_mắc": blockers,
    }


def render_report_html(facts: dict, narrative: str | None) -> str:
    e = html.escape
    head = (f"<p><b>RAG: {e(facts['rag'])}</b> · Kế hoạch {e(facts['kế_hoạch'])} · "
            f"Thực tế {e(facts['thực_tế'])} · SPI {e(facts['spi'])} · "
            f"Dự báo xong {e(facts['ngày_dự_báo_kết_thúc'])} "
            f"(baseline {e(facts['ngày_kết_thúc_baseline'])})</p>")
    if narrative:
        body = "<p>" + e(narrative).replace("\n\n", "</p><p>").replace("\n", "<br>") + "</p>"
    else:
        body = "<p><i>Chưa có phần nhận định do AI viết. PM bổ sung trước khi duyệt.</i></p>"

    def ul(items, fmt):
        return "<ul>" + "".join(f"<li>{fmt(i)}</li>" for i in items) + "</ul>" if items else "<p>Không có.</p>"

    parts = [
        head, body,
        "<h4>Mốc 2 tuần tới</h4>",
        ul(facts["mốc_2_tuần_tới"], lambda m: f"{e(m['hạn'])} — {e(str(m['mốc']))} — dự báo {e(m['dự_báo'])}"
           + (" ⚠ đường găng" if m["trên_đường_găng"] else "")),
        "<h4>Cảnh báo đang mở</h4>",
        ul(facts["cảnh_báo_đang_mở"], lambda a: f"[{e(a['mức'])}] {e(a['nội_dung'])}"),
        "<h4>Đã xong trong tuần</h4>",
        ul(facts["đã_xong_trong_tuần"], lambda d: f"{e(str(d['việc']))} — {e(str(d['bằng_chứng']))}"),
        f"<p style='color:#666'>Nguồn: ERP EuP, số liệu đến {e(facts['số_liệu_đến_ngày'])}. "
        "Số liệu do engine tính; phần nhận định do AI viết và PM duyệt.</p>",
    ]
    return "\n".join(parts)


def run_report(erp: ErpClient, settings: Settings, only: str | None = None,
               today: date | None = None, use_llm: bool = True):
    today = today or date.today()
    out = []
    for p in active_projects(erp, only):
        res, docs = analyse_project(erp, settings, p, today, verify=False)
        facts = build_facts(p, res, docs, erp, today)
        narrative = None
        if use_llm:
            try:
                narrative = write_narrative(settings, facts)
            except NarrativeError as e:
                log.warning("Dự án %s: không có phần nhận định AI (%s)", p["name"], e)
        body = render_report_html(facts, narrative)
        doc = erp.insert("Nx Project Status Report", {
            "project": p["name"],
            "period_end": today.isoformat(),
            "rag": res.rag,
            "planned_pct": round(res.planned_pct * 100, 1),
            "actual_pct": round(res.actual_pct * 100, 1),
            "spi": round(res.spi, 3) if res.spi is not None else 0,
            "forecast_end": res.forecast_end.isoformat() if res.forecast_end else None,
            "body": body,
            "status": "Nháp",
        })
        if p.get("custom_pmo_owner"):
            erp.send_email([p["custom_pmo_owner"]],
                           f"[Cần duyệt] Báo cáo tuần {p.get('project_name') or p['name']}",
                           f"<p>Bản nháp báo cáo tuần đã sẵn sàng. Mở, sửa nếu cần, rồi chuyển trạng thái "
                           f"để phát hành:</p><p><a href='{erp.link('Nx Project Status Report', doc['name'])}'>"
                           f"{html.escape(doc['name'])}</a></p>" + body)
        log.info("Đã tạo báo cáo nháp %s cho %s", doc["name"], p["name"])
        out.append((p["name"], doc["name"], body))
    return out


def run_publish(erp: ErpClient, settings: Settings):
    """Gửi các báo cáo PM đã chuyển sang 'Đã phát hành' mà chưa gửi."""
    reports = erp.get_list("Nx Project Status Report",
                           filters=[["status", "=", "Đã phát hành"], ["sent", "=", 0]],
                           fields=["name", "project", "period_end", "body"])
    for r in reports:
        p = erp.get_doc("Project", r["project"])
        recipients = [x.strip() for x in (p.get("custom_report_emails") or "").replace(";", ",").split(",")
                      if x.strip()]
        if p.get("custom_sponsor"):
            recipients.append(p["custom_sponsor"])
        if not recipients:
            log.warning("Báo cáo %s: Project %s chưa khai 'Email nhận báo cáo'", r["name"], r["project"])
            continue
        erp.send_email(sorted(set(recipients)),
                       f"Báo cáo tiến độ {p.get('project_name') or p['name']} — "
                       f"{fmt_date(parse_date(r['period_end']))}",
                       r["body"], "Nx Project Status Report", r["name"])
        erp.update("Nx Project Status Report", r["name"],
                   {"sent": 1, "sent_on": datetime.now().strftime("%Y-%m-%d %H:%M:%S")})
        log.info("Đã gửi báo cáo %s tới %s", r["name"], ", ".join(recipients))
    return reports
