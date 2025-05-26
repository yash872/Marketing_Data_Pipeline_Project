import sqlite3
from datetime import datetime
from pathlib import Path
import os
import re
from contextlib import contextmanager
from logging_config import get_logger

logger = get_logger(__name__)

# Path to your SQLite metadata database
METADATA_DB = Path(os.getenv("METADATA_DB_PATH", "/opt/airflow/data/metadata.db"))

@contextmanager
def get_db_connection():
    """Yield a SQLite connection with row factory enabled."""
    conn = sqlite3.connect(METADATA_DB)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()


def init_metadata_db(**kwargs):
    """
    Create metadata tables:
      • file_metadata --> per-stage timestamps
      • dq_checks     --> raw audit of each DQ check call (PASS/WARN/FAIL)
      • dq_signature  --> deterministic hash of row-level failures
    """
    logger.info("🔧 Initializing metadata database...")
    with get_db_connection() as conn:
        c = conn.cursor()
        # 1) File metadata
        c.execute("""
            CREATE TABLE IF NOT EXISTS file_metadata (
                file_name    TEXT PRIMARY KEY,
                dataset_type TEXT,
                file_date    TEXT,
                generated_at TEXT NULL,
                validated_at TEXT NULL,
                uploaded_at  TEXT NULL
            );
        """)
        # 2) DQ audit log
        c.execute("""
            CREATE TABLE IF NOT EXISTS dq_checks (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                file_name   TEXT,
                file_date   TEXT,
                check_name  TEXT,
                status      TEXT,
                details     TEXT,
                timestamp   DATETIME DEFAULT CURRENT_TIMESTAMP
            );
        """)
        # 3) DQ failure signature for idempotent alerting
        c.execute("""
            CREATE TABLE IF NOT EXISTS dq_signature (
                file_name    TEXT    NOT NULL,
                dataset_type TEXT    NOT NULL,
                file_date    TEXT    NOT NULL,
                signature    TEXT    NOT NULL,
                last_ts      TEXT    NOT NULL,
                PRIMARY KEY(file_name, dataset_type, file_date)
            );
        """)
        conn.commit()
    logger.info("✅ Metadata DB initialized.")


def log_stage(file_name: str, dataset_type: str, file_date: str, stage: str):
    """
    Upsert the UTC timestamp for the specified stage
    ('generated', 'validated', or 'uploaded') in file_metadata.
    """
    if stage not in ('generated', 'validated', 'uploaded'):
        raise ValueError(f"Invalid stage '{stage}'")

    ts = datetime.utcnow().isoformat()
    with get_db_connection() as conn:
        c = conn.cursor()
        # Does the row already exist?
        c.execute("SELECT 1 FROM file_metadata WHERE file_name = ?", (file_name,))
        exists = c.fetchone() is not None

        if exists:
            # Only update the one stage column
            c.execute(f"UPDATE file_metadata SET {stage}_at = ? WHERE file_name = ?", (ts, file_name))
        else:
            # Insert a new row, filling only this stage
            data = {
                'file_name':   file_name,
                'dataset_type': dataset_type,
                'file_date':    file_date,
                'generated_at': None,
                'validated_at': None,
                'uploaded_at':  None
            }
            data[f"{stage}_at"] = ts
            c.execute("""
                INSERT INTO file_metadata
                (file_name, dataset_type, file_date, generated_at, validated_at, uploaded_at)
                VALUES (:file_name, :dataset_type, :file_date,
                        :generated_at, :validated_at, :uploaded_at)
            """, data)
        conn.commit()
    logger.info(f"📝 Logged stage '{stage}' for {file_name} at {ts}")


def check_stage_complete(file_name: str, stage: str) -> bool:
    """
    Return True if the specified stage column is non-null in file_metadata.
    """
    if stage not in ('generated', 'validated', 'uploaded'):
        raise ValueError(f"Invalid stage '{stage}'")

    with get_db_connection() as conn:
        c = conn.cursor()
        c.execute(f"SELECT {stage}_at FROM file_metadata WHERE file_name = ?", (file_name,))
        row = c.fetchone()

    completed = bool(row and row[0])
    logger.debug(f"🔍 Stage '{stage}' complete for '{file_name}'? {completed}")
    return completed


def log_dq_result(file_name: str, check_name: str, status: str, details: str = None):
    """
    Insert a new row into dq_checks for the given DQ check outcome.
    """
    DATE_RE = re.compile(r"_(\d{4}-\d{2}-\d{2})\.")
    m = DATE_RE.search(file_name)
    file_date = m.group(1)

    with get_db_connection() as conn:
        c = conn.cursor()
        c.execute("""
            INSERT INTO dq_checks (file_name, file_date, check_name, status, details)
            VALUES (?, ?, ?, ?, ?);
        """, (file_name, file_date, check_name, status, details))
        conn.commit()
    logger.info(f"🧪 DQ Check logged: {file_name} | {check_name} = {status}")


def log_dq_signature(file_name: str, dataset_type: str, file_date: str, signature: str):
    """
    Upsert the DQ-failure signature (an MD5 of sorted failure keys)
    for this file/date. Later we compare it to detect truly new failures.
    """
    ts = datetime.utcnow().isoformat()
    with get_db_connection() as conn:
        c = conn.cursor()
        c.execute("""
            INSERT INTO dq_signature
              (file_name, dataset_type, file_date, signature, last_ts)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(file_name, dataset_type, file_date) DO UPDATE
              SET signature = excluded.signature,
                  last_ts   = excluded.last_ts;
        """, (file_name, dataset_type, file_date, signature, ts))
        conn.commit()
    logger.info(f"🔑 Logged DQ signature for {file_name}: {signature}")


def has_failure_delta(file_name: str, dataset_type: str, file_date: str, signature: str) -> bool:
    """
    Return True if the stored signature differs from the current one.
    Only meaningful when `signature` (i.e. failure signature) is non-empty.
    """
    with get_db_connection() as conn:
        c = conn.cursor()
        c.execute("""
            SELECT signature FROM dq_signature
            WHERE file_name = ? AND dataset_type = ? AND file_date = ?
        """, (file_name, dataset_type, file_date))
        row = c.fetchone()

    if row is None:
        # No prior run → any failure is “new”
        return bool(signature)

    prev_sig = row["signature"]
    return prev_sig != signature


def get_all_metadata():
    """Retrieve all file metadata records, ordered by file_date and file_name."""
    with get_db_connection() as conn:
        c = conn.cursor()
        c.execute("SELECT * FROM file_metadata ORDER BY file_date DESC, file_name")
        results = c.fetchall()
    logger.debug(f"📦 Retrieved all metadata entries: {len(results)} rows")
    return results


def get_metadata_for_date(ds: str):
    """Retrieve file metadata for a specific date (file_date == ds)."""
    with get_db_connection() as conn:
        c = conn.cursor()
        c.execute(
            "SELECT * FROM file_metadata WHERE file_date = ? ORDER BY file_name",
            (ds,)
        )
        results = c.fetchall()
    logger.debug(f"📅 Retrieved metadata for {ds}: {len(results)} rows")
    return results


def print_metadata(ds: str, **kwargs):
    """Print file metadata and DQ checks for a given date to the console."""
    with get_db_connection() as conn:
        c = conn.cursor()

        # File metadata section
        print(f"\n=== File Metadata for {ds} ===")
        print("file_name | dataset_type | file_date | generated_at | validated_at | uploaded_at")
        print("-" * 80)
        c.execute(
            "SELECT file_name, dataset_type, file_date, generated_at, validated_at, uploaded_at"
            " FROM file_metadata WHERE file_date = ?",
            (ds,)
        )
        rows = c.fetchall()
        if rows:
            for row in rows:
                print(" | ".join(str(row[h]) for h in
                      ["file_name","dataset_type","file_date","generated_at","validated_at","uploaded_at"]))
        else:
            print("(no file metadata records)")

        # DQ checks section
        print(f"\n=== DQ Checks for {ds} ===")
        print("file_name | check_name | status | details | timestamp")
        print("-" * 80)
        c.execute(
            "SELECT file_name, file_date, check_name, status, details, timestamp"
            " FROM dq_checks WHERE file_date = ?",
            (ds,)
        )
        dq_rows = c.fetchall()
        if dq_rows:
            for row in dq_rows:
                print(" | ".join(str(row[h]) for h in
                      ["file_name","check_name","status","details","timestamp"]))
        else:
            print("(no DQ records)")

    print()
    logger.info(f"🖨️ Metadata printed for {ds}")