import pandas as pd
import pyarrow.parquet as pq
import json
import re
import os
import shutil
import hashlib
from pathlib import Path
from datetime import datetime
from utils import capture_metrics
from airflow.operators.python import get_current_context
from metadata import (
    log_stage,
    check_stage_complete,
    log_dq_result,
    log_dq_signature,
    has_failure_delta,
)
from logging_config import get_logger

logger = get_logger(__name__)

RAW_DIR        = Path("/opt/airflow/data/raw_data")
VALID_DIR      = Path("/opt/airflow/data/validated_data")
QUARANTINE_DIR = Path("/opt/airflow/data/quarantine_data")
for d in (RAW_DIR, VALID_DIR, QUARANTINE_DIR):
    d.mkdir(parents=True, exist_ok=True)


def quarantine_file(filename: str):
    """Move an invalid file slice to quarantine directory."""
    logger.warning(f"Quarantining invalid rows for: {filename}")
    src = RAW_DIR / filename
    dest = QUARANTINE_DIR / filename
    shutil.move(str(src), str(dest))
    logger.warning(f"Quarantining invalid rows → {dest}")



def validate_schema_and_format(df: pd.DataFrame, required_cols: set, filename: str):
    missing = required_cols - set(df.columns)
    if missing:
        log_dq_result(filename, "schema_format", "FAIL", f"Missing {missing}")
        raise ValueError(f"{filename}: Missing cols {missing}")
    log_dq_result(filename, "schema_format", "PASS", f"Got cols {list(df.columns)}")


def validate_freshness(df: pd.DataFrame, ds: str, filename: str, history_pct: float = 0.2):
    DATE_RE = re.compile(r"_(\d{4}-\d{2}-\d{2})\.")
    m = DATE_RE.search(filename)
    if not m:
        raise ValueError(f"Couldn’t parse date from filename {filename!r}")
    file_date = datetime.strptime(m.group(1), "%Y-%m-%d").date()
    expected  = datetime.strptime(ds, "%Y-%m-%d").date()
    if file_date != expected:
        log_dq_result(filename, "freshness", "FAIL", f"{file_date} ≠ {expected}")
        raise ValueError(f"{filename}: Not fresh ({file_date} vs {expected})")
    log_dq_result(filename, "freshness", "PASS", f"File date {file_date}")


def validate_row_count(df: pd.DataFrame, filename: str, avg: int = 1000, pct: float = 0.2):
    cnt = len(df)
    low, high = avg * (1 - pct), avg * (1 + pct)
    if not (low <= cnt <= high):
        raise ValueError(f"Row count {cnt} not in [{low:.0f},{high:.0f}]")
    log_dq_result(filename, "row_count", "PASS", f"Count={cnt}, avg≈{avg}")


def _validate_generic(
    filename: str,
    ds: str,
    reader_fn,
    pk_cols: list,
    required_cols: set,
    file_type: str
):
    path = RAW_DIR / filename
    if not path.exists():
        raise FileNotFoundError(f"{filename} not found")

    # 1) Read raw data and initialize flags
    df = reader_fn(path)
    rows_in = len(df)
    file_failures = False
    file_fail_msg = ""

    # 2) File-level checks
    try:
        validate_schema_and_format(df, required_cols, filename)
        validate_freshness(df, ds, filename)
    except Exception as e:
        file_failures = True
        file_fail_msg = str(e)
        log_dq_result(filename, 'file-level', "FAIL", file_fail_msg)
        quarantine_file(filename)

    # 3) Row-level checks (only if file passed)
    if not file_failures:
        # Optional row-count warning
        try:
            validate_row_count(df, filename)
        except ValueError as warn:
            log_dq_result(filename, "row_count", "WARN", str(warn))

        null_mask = df[pk_cols].isnull().any(axis=1)
        dup_mask  = df.duplicated(subset=pk_cols, keep=False)
        invalid_mask = null_mask | dup_mask

        df_valid   = df[~invalid_mask]
        df_invalid = df[invalid_mask]
    else:
        # On file-level failure, mark all rows invalid
        df_valid   = pd.DataFrame(columns=df.columns)
        df_invalid = df

    rows_out       = len(df_valid)
    invalid_count  = len(df_invalid)

    # 4) Write slices out
    VALID_DIR.mkdir(parents=True, exist_ok=True)
    if filename.endswith('.csv'):
        df_valid.to_csv (VALID_DIR/filename, index=False)
    elif filename.endswith('.json'):
        df_valid.to_json(VALID_DIR/filename, orient='records', lines=True)
    elif filename.endswith('.parquet'):
        df_valid.to_parquet(VALID_DIR/filename)
    logger.info(f"Valid Data for {filename} created in {VALID_DIR}")

    QUARANTINE_DIR.mkdir(parents=True, exist_ok=True)
    if invalid_count > 0:
        if filename.endswith('.csv'):
            df_invalid.to_csv (QUARANTINE_DIR/filename, index=False)
        elif filename.endswith('.json'):
            df_invalid.to_json(QUARANTINE_DIR/filename, orient='records', lines=True)
        elif filename.endswith('.parquet'):
            df_invalid.to_parquet(QUARANTINE_DIR/filename)
        logger.info(f"Invalid Data for {filename} created in {QUARANTINE_DIR}")

    # Remove raw_data file for clean up
    if path.exists():
        os.remove(path)
        logger.info(f"Removed {path} from raw_data folder")

    # 5) Compute deterministic failure signature
    failure_keys = []
    for idx in df_invalid.index:
        row_pk = "::".join(str(df.at[idx, col]) for col in pk_cols)
        if not file_failures and null_mask.iloc[idx]:
            failure_keys.append(f"{row_pk}::null")
        if not file_failures and dup_mask.iloc[idx]:
            failure_keys.append(f"{row_pk}::dup")

    signature = ""
    if failure_keys:
        sig_src   = "|".join(sorted(failure_keys))
        signature = hashlib.md5(sig_src.encode('utf-8')).hexdigest()

    # 6) Persist signature and push DQ-fail flag
    log_dq_signature(filename, file_type, ds, signature)
    ti = get_current_context()['ti']
    new_failure = bool(signature and has_failure_delta(filename, file_type, ds, signature))
    ti.xcom_push(key='new_dq_failures', value=new_failure)
    if new_failure:
        logger.warning(f"🔔 New DQ failures for {filename}: {invalid_count} rows")

    # 7) Overall DQ outcome and stage logging
    status = "PASS" if (not file_failures and invalid_count == 0) else "FAIL"
    details = file_fail_msg if file_failures else f"in={rows_in}, out={rows_out}, failures={invalid_count}"
    log_dq_result(filename, file_type, status, details)
    log_stage(filename, file_type, ds, "validated")

    return rows_in, rows_out


# Decorated wrappers to capture metrics and respect idempotency
@capture_metrics("validate_campaigns")
def validate_campaigns_if_needed(ds: str, **kwargs):
    fn = f"campaigns_{ds}.json"
    if check_stage_complete(fn, "validated"):
        logger.info(f"⏩ Already validated: {fn}")
        return 0, 0
    return _validate_generic(
        fn, ds,
        # read JSON as flat records
        lambda p: pd.read_json(p, orient="records"),
        # primary key
        ["campaign_id"],
        # required columns in your dimension
        {"campaign_id", "campaign_name"},
        "campaigns"
    )


@capture_metrics("validate_forms")
def validate_forms_if_needed(ds: str, **kwargs):
    fn = f"forms_{ds}.json"
    if check_stage_complete(fn, "validated"):
        logger.info(f"⏩ Already validated: {fn}")
        return 0, 0
    return _validate_generic(
        fn, ds,
        lambda p: pd.read_json(p, orient="records"),
        ["form_id"],
        {"form_id", "form_type"},
        "forms"
    )


@capture_metrics("validate_pages")
def validate_pages_if_needed(ds: str, **kwargs):
    fn = f"pages_{ds}.json"
    if check_stage_complete(fn, "validated"):
        logger.info(f"⏩ Already validated: {fn}")
        return 0, 0
    return _validate_generic(
        fn, ds,
        lambda p: pd.read_json(p, orient="records"),
        ["page_id"],
        {"page_id", "page_url", "page_title"},
        "pages"
    )


@capture_metrics("validate_contacts")
def validate_contacts_if_needed(ds: str, **kwargs):
    fn = f"contacts_{ds}.csv"
    if check_stage_complete(fn, "validated"):
        logger.info(f"⏩ Already validated: {fn}")
        return 0, 0
    return _validate_generic(
        fn, ds,
        lambda p: pd.read_csv(p),
        ['contact_id'],
        {'contact_id', 'email', 'first_name', 'company'},
        'contacts'
    )


@capture_metrics("validate_form_fills")
def validate_form_fills_if_needed(ds: str, **kwargs):
    fn = f"form_fills_{ds}.parquet"
    if check_stage_complete(fn, "validated"):
        logger.info(f"⏩ Already validated: {fn}")
        return 0, 0
    return _validate_generic(
        fn, ds,
        lambda p: pd.read_parquet(p),
        ['fill_id'],
        {'fill_id', 'form_id', 'contact_id', 'fill_date'},
        'form_fills'
    )


@capture_metrics("validate_website_activity")
def validate_website_activity_if_needed(ds: str, **kwargs):
    fn = f"website_activity_{ds}.json"
    if check_stage_complete(fn, "validated"):
        logger.info(f"⏩ Already validated: {fn}")
        return 0, 0
    return _validate_generic(
        fn, ds,
        lambda p: pd.json_normalize(json.loads(p.read_text())),
        ['session_id'],
        {'session_id', 'contact_id', 'page_url', 'event_date'},
        'website_activity'
    )