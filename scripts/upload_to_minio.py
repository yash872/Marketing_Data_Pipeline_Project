from minio import Minio
from minio.error import S3Error
from pathlib import Path
import shutil
import os
import re
import mimetypes
from metadata import log_stage, check_stage_complete
from logging_config import get_logger

logger = get_logger(__name__)

VALID_DIR = Path("/opt/airflow/data/validated_data")
UPLOAD_DIR = Path("/opt/airflow/data/uploaded_data")
QUARANTINE_DIR = Path("/opt/airflow/data/quarantine_data")
BUCKET_NAME = "marketing-bucket"

def get_minio_client():
    return Minio(
        endpoint="minio:9000",
        access_key="minioadmin",
        secret_key="minioadmin",
        secure=False
    )

def _ensure_bucket(client, bucket_name: str):
    if not client.bucket_exists(bucket_name):
        client.make_bucket(bucket_name)
        logger.info(f"✅ Created bucket: {bucket_name}")
    else:
        logger.info(f"ℹ️ Bucket '{bucket_name}' already exists")

def infer_object_path(filename: str):
    logger.debug(f"🔍 Inspecting file name for object path: '{filename}'")
    match = re.match(r"(contacts|form_fills|website_activity|campaigns|forms|pages)_(\d{4}-\d{2}-\d{2})\..+", filename)
    if not match:
        raise ValueError(f"Invalid file name format: {filename}")
    file_type, ds = match.groups()
    return file_type, ds

def upload_file_to_minio(client, file_path: Path, bucket: str, object_name: str):
    content_type = mimetypes.guess_type(file_path.name)[0] or 'application/octet-stream'
    client.fput_object(
        bucket_name=bucket,
        object_name=object_name,
        file_path=str(file_path),
        content_type=content_type,
    )

    file_validity = object_name.split('/')[0]
    file_type = object_name.split('/')[1]
    file_date = object_name.split('/')[2]

    # if valid-data then move from VLID_DIR to UPLOAD_DIR, Quarantine file remain in QUARANTINE_DIR for 
    if file_validity == 'valid-data':
        dest = UPLOAD_DIR / file_path.name
        UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
        shutil.move(str(file_path), dest)
    
    log_stage(file_path.name, file_type, file_date, 'uploaded')
    logger.info(f"📤 Uploaded {file_path.name} to {object_name}")

def upload_all_validated_files(**kwargs):
    client = get_minio_client()
    _ensure_bucket(client, BUCKET_NAME)

    for file in VALID_DIR.glob("*"):
        if not file.is_file():
            continue
        if check_stage_complete(file.name, "uploaded"):
            logger.info(f"⏩ Already uploaded: {file.name}")
            continue
        try:
            file_type, ds = infer_object_path(file.name)
            object_name = f"valid-data/{file_type}/{ds}/{file.name}"
            upload_file_to_minio(
                client,
                file,
                bucket=BUCKET_NAME,
                object_name=object_name
            )
        except Exception as e:
            msg = f"❌ Upload failed for {file.name}: {e}"
            logger.error(msg, exc_info=True)
            raise

def upload_all_quarantined_files(**kwargs):
    client = get_minio_client()
    _ensure_bucket(client, BUCKET_NAME)

    for file in QUARANTINE_DIR.glob("*"):
        if not file.is_file():
            continue
        if check_stage_complete(file.name, "uploaded"):
            logger.info(f"⏩ Already uploaded (quarantine): {file.name}")
            continue
        try:
            file_type, ds = infer_object_path(file.name)
            object_name = f"quarantine-data/{file_type}/{ds}/{file.name}"
            upload_file_to_minio(
                client,
                file,
                bucket=BUCKET_NAME,
                object_name=object_name
            )
        except Exception as e:
            msg = f"❌ Failed to upload quarantined {file.name}: {e}"
            logger.error(msg, exc_info=True)
            raise

if __name__ == "__main__":
    upload_all_validated_files()
