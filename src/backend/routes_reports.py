"""
src/backend/routes_reports.py

REST endpoints backing Dashboard View C (Historical Log & Export):
filterable list + JSON/CSV export of the full compliance audit trail.
"""
from fastapi import APIRouter, Query
from fastapi.responses import PlainTextResponse

from src.audit_agent.repository import export_csv, export_json, query_reports, report_to_dict
from src.backend.schemas import ComplianceReportOut

router = APIRouter(prefix="/api/reports", tags=["reports"])


@router.get("", response_model=list[ComplianceReportOut])
def list_reports(
    severity: str | None = Query(default=None),
    behavior_class: str | None = Query(default=None),
    start_date: str | None = Query(default=None),
    end_date: str | None = Query(default=None),
    limit: int = Query(default=500, le=5000),
):
    reports = query_reports(
        severity=severity,
        behavior_class=behavior_class,
        start_date=start_date,
        end_date=end_date,
        limit=limit,
    )
    return [report_to_dict(r) for r in reports]


@router.get("/export/json")
def export_reports_json(
    severity: str | None = Query(default=None),
    behavior_class: str | None = Query(default=None),
    start_date: str | None = Query(default=None),
    end_date: str | None = Query(default=None),
):
    reports = query_reports(
        severity=severity, behavior_class=behavior_class,
        start_date=start_date, end_date=end_date, limit=5000,
    )
    return PlainTextResponse(
        export_json(reports),
        media_type="application/json",
        headers={"Content-Disposition": "attachment; filename=compliance_log.json"},
    )


@router.get("/export/csv")
def export_reports_csv(
    severity: str | None = Query(default=None),
    behavior_class: str | None = Query(default=None),
    start_date: str | None = Query(default=None),
    end_date: str | None = Query(default=None),
):
    reports = query_reports(
        severity=severity, behavior_class=behavior_class,
        start_date=start_date, end_date=end_date, limit=5000,
    )
    return PlainTextResponse(
        export_csv(reports),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=compliance_log.csv"},
    )
