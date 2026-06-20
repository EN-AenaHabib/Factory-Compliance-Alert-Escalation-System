"""
src/audit_agent/repository.py

Data access layer over the ComplianceReport table. Both the AuditAgent
(writes) and the FastAPI backend (reads/filters/exports) go through this
module rather than touching SQLAlchemy directly, keeping the schema and
query logic in one place.
"""
import csv
import io
import json
import uuid
from datetime import datetime, timezone

from src.audit_agent.db import ComplianceReport, get_session_factory, init_db
from src.common.logging_utils import get_logger

logger = get_logger(__name__)


def now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def write_report(
    clip_id: str,
    zone: str,
    behavior_class: str,
    behavior_label: str,
    policy_rule_ref: str,
    event_description: str,
    severity: str,
    escalation_action: str,
    confidence: float | None = None,
    timestamp_sec_in_clip: float | None = None,
    config: dict | None = None,
) -> ComplianceReport:
    init_db(config)
    Session = get_session_factory(config)
    session = Session()
    try:
        report = ComplianceReport(
            event_id=str(uuid.uuid4()),
            timestamp=now_iso(),
            clip_id=clip_id,
            zone=zone,
            behavior_class=behavior_class,
            behavior_label=behavior_label,
            policy_rule_ref=policy_rule_ref,
            event_description=event_description,
            severity=severity,
            escalation_action=escalation_action,
            confidence=confidence,
            timestamp_sec_in_clip=timestamp_sec_in_clip,
        )
        session.add(report)
        session.commit()
        session.refresh(report)
        return report
    finally:
        session.close()


def query_reports(
    severity: str | None = None,
    behavior_class: str | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
    limit: int = 500,
    config: dict | None = None,
) -> list[ComplianceReport]:
    init_db(config)
    Session = get_session_factory(config)
    session = Session()
    try:
        q = session.query(ComplianceReport)
        if severity:
            q = q.filter(ComplianceReport.severity == severity.upper())
        if behavior_class:
            q = q.filter(ComplianceReport.behavior_class == behavior_class)
        if start_date:
            q = q.filter(ComplianceReport.timestamp >= start_date)
        if end_date:
            q = q.filter(ComplianceReport.timestamp <= end_date)
        q = q.order_by(ComplianceReport.timestamp.desc()).limit(limit)
        return q.all()
    finally:
        session.close()


def report_to_dict(r: ComplianceReport) -> dict:
    return {
        "event_id": r.event_id,
        "timestamp": r.timestamp,
        "clip_id": r.clip_id,
        "zone": r.zone,
        "behavior_class": r.behavior_class,
        "behavior_label": r.behavior_label,
        "policy_rule_ref": r.policy_rule_ref,
        "event_description": r.event_description,
        "severity": r.severity,
        "escalation_action": r.escalation_action,
        "confidence": r.confidence,
        "timestamp_sec_in_clip": r.timestamp_sec_in_clip,
    }


def export_json(reports: list[ComplianceReport]) -> str:
    return json.dumps([report_to_dict(r) for r in reports], indent=2)


def export_csv(reports: list[ComplianceReport]) -> str:
    buf = io.StringIO()
    fieldnames = [
        "event_id", "timestamp", "clip_id", "zone", "behavior_class",
        "behavior_label", "policy_rule_ref", "event_description",
        "severity", "escalation_action", "confidence", "timestamp_sec_in_clip",
    ]
    writer = csv.DictWriter(buf, fieldnames=fieldnames)
    writer.writeheader()
    for r in reports:
        writer.writerow(report_to_dict(r))
    return buf.getvalue()
