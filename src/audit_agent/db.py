"""
src/audit_agent/db.py

SQLite schema for the compliance audit trail (Module 4). SQLite chosen
over a managed/server database per Green AI analysis: this is a
mostly-append, occasional-filtered-read workload at a scale that doesn't
justify a standalone DB server process. See docs/GREEN_AI.md.
"""
from sqlalchemy import Column, Float, String, create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

from src.common.config import load_config, resolve_path

Base = declarative_base()


class ComplianceReport(Base):
    __tablename__ = "compliance_reports"

    event_id = Column(String, primary_key=True)
    timestamp = Column(String, nullable=False)          # ISO 8601
    clip_id = Column(String, nullable=False)
    zone = Column(String, nullable=False)
    behavior_class = Column(String, nullable=False)
    behavior_label = Column(String, nullable=False)
    policy_rule_ref = Column(String, nullable=False)
    event_description = Column(String, nullable=False)
    severity = Column(String, nullable=False)            # LOW/MEDIUM/HIGH/CRITICAL
    escalation_action = Column(String, nullable=False)
    confidence = Column(Float, nullable=True)
    timestamp_sec_in_clip = Column(Float, nullable=True)


_engine = None
_SessionLocal = None


def get_engine(config: dict | None = None):
    global _engine
    if _engine is None:
        cfg = config or load_config()
        db_path = resolve_path(cfg["paths"]["sqlite_db"])
        _engine = create_engine(f"sqlite:///{db_path}", connect_args={"check_same_thread": False})
    return _engine


def get_session_factory(config: dict | None = None):
    global _SessionLocal
    if _SessionLocal is None:
        _SessionLocal = sessionmaker(bind=get_engine(config))
    return _SessionLocal


def init_db(config: dict | None = None):
    engine = get_engine(config)
    Base.metadata.create_all(engine)
    return engine


if __name__ == "__main__":
    init_db()
    print("Audit database schema initialized.")
