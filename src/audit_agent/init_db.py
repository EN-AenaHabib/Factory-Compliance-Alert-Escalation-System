"""
src/audit_agent/init_db.py

Entry point matching the call in scripts/setup.sh:
    python3 -m src.audit_agent.init_db
"""
from src.audit_agent.db import init_db
from src.common.logging_utils import get_logger

logger = get_logger(__name__)

if __name__ == "__main__":
    init_db()
    logger.info("Audit database schema initialized.")
