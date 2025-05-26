import os
import glob
import tempfile
import snowflake.connector
from typing import Dict
from pathlib import Path
from upload_to_minio import get_minio_client
from logging_config import get_logger

logger = get_logger(__name__)

# ------------------------------------------------------------------------------
# --- CONFIGURATION
# ------------------------------------------------------------------------------

# Map each entity to its Snowflake table, file format, and extension
ENTITIES: Dict[str,Dict[str,str]] = {
    "contacts": {
        "stage_table": "contacts",
        "raw_table":   "RAW.contacts",
        "file_format": "RAW.csv_fmt",
        "ext":         ".csv",
        "stage" : "RAW_CONTACTS_STAGE",
    },
    "form_fills": {
        "stage_table": "form_fills",
        "raw_table":   "RAW.form_fills",
        "file_format": "RAW.parquet_fmt",
        "ext":         ".parquet",
        "stage" : "RAW_FORM_FILLS_STAGE",
    },
    "website_activity": {
        "stage_table": "website_activity",
        "raw_table":   "RAW.website_activity",
        "file_format": "RAW.json_fmt",
        "ext":         ".json",
        "stage" : "RAW_WEBSITE_ACTIVITY_STAGE",
    },
    "campaigns": {
        "stage_table": "campaigns",
        "raw_table":   "RAW.campaigns",
        "file_format": "RAW.json_fmt",
        "ext":         ".json",
        "stage" : "RAW_CAMPAIGNS_STAGE",
    },
    "forms": {
        "stage_table": "forms",
        "raw_table":   "RAW.forms",
        "file_format": "RAW.json_fmt",
        "ext":         ".json",
        "stage" : "RAW_FORMS_STAGE",
    },
    "pages": {
        "stage_table": "pages",
        "raw_table":   "RAW.pages",
        "file_format": "RAW.json_fmt",
        "ext":         ".json",
        "stage" : "RAW_PAGES_STAGE",
    },
}

# ------------------------------------------------------------------------------
# SNOWFLAKE CONNECTION
# ------------------------------------------------------------------------------

def get_snowflake_connection(sch='RAW'):

    return snowflake.connector.connect(
        user='DBT_USER',
        password='Pass@Snowflake872',
        account='uw98118.ap-southeast-1',
        warehouse='DBT_WH',
        database='MARKETING_DB',
        schema=sch
    )

# ------------------------------------------------------------------------------
# --- LOADING FUNCTIONS
# ------------------------------------------------------------------------------

def load_entity_for_date(entity: str, date_str: str):
    """
    1) Lists objects under MINIO_BUCKET/MINIO_PREFIX/<entity>/<date_str>/
    2) Downloads them to a temp folder
    3) PUTs that folder/*.ext into @Snowflake_Managed_Stage
    4) COPY INTO <raw_table>
    """
    MINIO_BUCKET = 'marketing-bucket'
    meta = ENTITIES[entity]
    prefix = f"valid-data/{entity}/{date_str}/"
    client = get_minio_client()
    objs = list(client.list_objects(MINIO_BUCKET, prefix=prefix, recursive=True))
    files = [o.object_name for o in objs if o.object_name.lower().endswith(meta["ext"])]
    if not files:
        print(f"[WARN] no {meta['ext']} under {prefix}, skipping {entity}")
        return

    # download into a temp dir
    with tempfile.TemporaryDirectory() as td:
        for obj_name in files:
            local_path = os.path.join(td, os.path.basename(obj_name))
            client.fget_object(MINIO_BUCKET, obj_name, local_path)
            logger.info(f"[⏬] downloaded {obj_name} → {local_path}")

        # open SF cursor once per entity
        conn = get_snowflake_connection()
        try:
            cursor = conn.cursor()

            # PUT all files at once
            #stage_ref = f"@%{meta['stage_table']}"
            #put_sql = f"PUT file://{td}/*{meta['ext']} {stage_ref} OVERWRITE = TRUE"
            #logger.info(f"[INFO] running: {put_sql}")
            #cursor.execute(put_sql)

            stage_ref = f"@{meta['stage']}/{date_str}/"
            cursor.execute(f"LIST {stage_ref}")
            staged = {row[0].split('/')[-1] for row in cursor.fetchall()}

            for f in os.listdir(td):
                if f not in staged:
                    put_sql = f"PUT file://{td}/{f} {stage_ref}"
                    cursor.execute(put_sql)
                    logger.info(f"[INFO] running: {put_sql}")

            # COPY into raw table
            copy_sql = f"""
                COPY INTO {meta['raw_table']}
                FROM {stage_ref}
                FILE_FORMAT = (FORMAT_NAME = '{meta['file_format']}')
                ON_ERROR = 'CONTINUE'
                FORCE = FALSE
                ;
            """
            logger.info(f"[INFO] running COPY INTO {meta['raw_table']}")
            cursor.execute(copy_sql)

            logger.info(f"[✅] loaded {entity} for {date_str}")
            
        finally:
            cursor.close()
            conn.close()

def load_to_snowflake(ds: str, **kwargs):
    for entity in ENTITIES:
        load_entity_for_date(entity, ds)