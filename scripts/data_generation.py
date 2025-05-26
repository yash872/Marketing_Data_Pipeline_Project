import os
import json
import uuid
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
from faker import Faker
from pathlib import Path
import random
from metadata import log_stage, check_stage_complete
from logging_config import get_logger

fake = Faker()
logger = get_logger(__name__)

RAW_DIR = Path("/opt/airflow/data/raw_data")
VALID_DIR = Path("/opt/airflow/data/validated_data")
UPLOAD_DIR = Path("/opt/airflow/data/uploaded_data")
QUARANTINE_DIR = Path("/opt/airflow/data/quarantine_data")
for d in (RAW_DIR, VALID_DIR, UPLOAD_DIR, QUARANTINE_DIR):
    d.mkdir(parents=True, exist_ok=True)

def generate_contacts_if_needed(ds: str, **kwargs):
    file_name = f"contacts_{ds}.csv"
    if not check_stage_complete(file_name, "generated"):
        generate_contacts(file_name)
        log_stage(file_name, "contacts", ds, "generated")
    else:
        logger.info(f"⏩ Skipping Generation >>> {file_name} already marked as generated")

def generate_form_fills_if_needed(ds: str, **kwargs):
    file_name = f"form_fills_{ds}.parquet"
    if not check_stage_complete(file_name, "generated"):
        generate_form_fills(file_name)
        log_stage(file_name, "form_fills", ds, "generated")
    else:
        logger.info(f"⏩ Skipping Generation >>> {file_name} already marked as generated")

def generate_website_activity_if_needed(ds: str, **kwargs):
    file_name = f"website_activity_{ds}.json"
    if not check_stage_complete(file_name, "generated"):
        generate_website_activity(file_name)
        log_stage(file_name, "website_activity", ds, "generated")
    else:
        logger.info(f"⏩ Skipping Generation >>> {file_name} already marked as generated")

def generate_contacts(file_name, n=1000):
    industries = ['Technology', 'Finance', 'Healthcare', 'Education', 'Retail']
    job_levels = ['Entry', 'Manager', 'Director', 'VP', 'C-Level']
    lead_sources = ['Web', 'Email', 'Event', 'Referral', 'Organic Search', 'Paid Social']
    data = [{
        "contact_id": str(uuid.uuid4()),
        "first_name": fake.first_name(),
        "last_name": fake.last_name(),
        "email": fake.email(),
        "phone": fake.phone_number(),
        "company_name": fake.company(),
        "industry": random.choice(industries),
        "job_title": fake.job(),
        "job_level": random.choice(job_levels),
        "lead_source": random.choice(lead_sources),
        "utm_campaign": fake.bs(),
        "utm_medium": random.choice(['email', 'cpc', 'organic', 'referral']),
        "utm_source": random.choice(['google', 'facebook', 'linkedin', 'twitter']),
        "linkedin_url": fake.url(),
        "employee_count": random.randint(10, 1000),
        "annual_revenue": round(random.uniform(1e6, 1e8), 2),
        "status": random.choice(['New', 'Engaged', 'MQL', 'SQL']),
        "created_at": fake.date_time_between(start_date='-2y', end_date='-1y'),
        "last_modified_at": fake.date_time_this_year()
    } for _ in range(n)]
    pd.DataFrame(data).to_csv(RAW_DIR / file_name, index=False)
    logger.info(f"✅ {file_name} file generated")

def generate_form_fills(file_name, n=1000):
    form_types = ['Contact Us', 'Demo Request', 'Newsletter Signup', 'Whitepaper Download']
    rows = [{
        "form_id": str(uuid.uuid4()),
        "contact_id": str(uuid.uuid4()),
        "form_type": random.choice(form_types),
        "timestamp": fake.date_time_this_year().isoformat(),
        "referrer_url": fake.url(),
        "user_agent": fake.user_agent(),
        "ip_address": fake.ipv4_public(),
        "project_budget": random.choice(['<10k', '10k-50k', '50k-100k', '>100k']),
        "timeline": random.choice(['Immediately', 'Next 3 months', 'Next 6 months']),
        "needs": fake.sentence()
    } for _ in range(n)]
    pq.write_table(pa.Table.from_pandas(pd.DataFrame(rows)), RAW_DIR / file_name)
    logger.info(f"✅ {file_name} file generated")

def generate_website_activity(file_name, n=1000):
    event_types = ['page_view', 'button_click', 'form_submit', 'video_play']
    activities = [{
        "session_id": str(uuid.uuid4()),
        "contact_id": str(uuid.uuid4()),
        "timestamp": fake.date_time_this_year().isoformat(),
        "page_url": fake.url(),
        "page_title": fake.catch_phrase(),
        "referrer_url": fake.url(),
        "device": random.choice(['desktop', 'mobile', 'tablet']),
        "browser": random.choice(['Chrome', 'Firefox', 'Safari', 'Edge']),
        "os": random.choice(['Windows', 'macOS', 'Linux', 'Android', 'iOS']),
        "event_type": random.choice(event_types),
        "campaign_params": {
            "utm_source": random.choice(['google', 'bing', 'email']),
            "utm_medium": random.choice(['organic', 'cpc', 'referral']),
            "utm_campaign": fake.bs()
        },
        "geo_location": {
            "city": fake.city(),
            "country": fake.country()
        }
    } for _ in range(n)]
    with open(RAW_DIR / file_name, 'w') as f:
        json.dump(activities, f, indent=2)
    logger.info(f"✅ {file_name} file generated")
