"""HTTP API để n8n gọi theo lịch.  Chạy:  uvicorn eup_agents.server:app --host 0.0.0.0 --port 8000

Mọi request phải có header  X-Service-Token: <SERVICE_TOKEN trong .env>.
"""

from fastapi import Depends, FastAPI, Header, HTTPException
from pydantic import BaseModel

from .agents import erp_watch, intake, nudge, report
from .config import settings
from .erp import ERPClient

app = FastAPI(title="EuP office agents")


def auth(x_service_token: str = Header(default="")):
    if not settings.service_token or x_service_token != settings.service_token:
        raise HTTPException(status_code=401, detail="Sai hoặc thiếu X-Service-Token")


class IntakeIn(BaseModel):
    text: str
    sender: str
    source: str = "Email"
    source_ref: str = ""


@app.get("/health")
def health():
    return {"ok": True, "dry_run": settings.dry_run}


@app.post("/run/nudge", dependencies=[Depends(auth)])
def run_nudge(slot: str = "morning"):
    return nudge.run(ERPClient(), slot)


@app.post("/run/report", dependencies=[Depends(auth)])
def run_report(send: bool = False):
    return report.run(ERPClient(), send)


@app.post("/run/erp-watch", dependencies=[Depends(auth)])
def run_erp_watch():
    return erp_watch.run(ERPClient())


@app.post("/run/intake", dependencies=[Depends(auth)])
def run_intake(body: IntakeIn):
    return intake.run(ERPClient(), body.text, body.sender, body.source, body.source_ref)
