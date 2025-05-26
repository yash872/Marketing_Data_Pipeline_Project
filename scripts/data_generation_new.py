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

# Initialize Faker and logger
fake = Faker()
logger = get_logger(__name__)

# Scale factor: multiply default volumes via env var
SCALE_FACTOR = int(os.getenv('SCALE_FACTOR', '1'))
BASE_COUNT = 1000 * SCALE_FACTOR

# Directories
RAW_DIR = Path("/opt/airflow/data/raw_data")
VALID_DIR = Path("/opt/airflow/data/validated_data")
UPLOAD_DIR = Path("/opt/airflow/data/uploaded_data")
QUARANTINE_DIR = Path("/opt/airflow/data/quarantine_data")
for d in (RAW_DIR, VALID_DIR, UPLOAD_DIR, QUARANTINE_DIR):
    d.mkdir(parents=True, exist_ok=True)

# Dimension universes for realistic joins
CAMPAIGNS = [
    {"campaign_id": "camp_1", "campaign_name": "Spring Promo"},
    {"campaign_id": "camp_2", "campaign_name": "Holiday Sale"},
    {"campaign_id": "camp_3", "campaign_name": "Webinar November"},
]
FORMS = [
    {"form_id": "form_10", "form_type": "Contact Us"},
    {"form_id": "form_11", "form_type": "Demo Request"},
    {"form_id": "form_12", "form_type": "Newsletter Signup"},
    {"form_id": "form_13", "form_type": "Whitepaper Download"},
]
PAGES = [
    {"page_id": 1, "page_url": "/home", "page_title": "Home Page"},
    {"page_id": 2, "page_url": "/pricing", "page_title": "Pricing Page"},
    {"page_id": 3, "page_url": "/signup", "page_title": "Signup Page"},
    {"page_id": 4, "page_url": "/blog", "page_title": "Blog Page"},
]

# ------------------------------------------------------------------------------------------------------------------
# Generation hooks: dimensions, contacts, form_fills, activity
# ------------------------------------------------------------------------------------------------------------------

def generate_dimension_if_needed(name: str, ds: str, **kwargs):
    """Generate dimension JSON based on name without passing data explicitly."""
    file_name = f"{name}_{ds}.json"
    if check_stage_complete(file_name, "generated"):
        logger.info(f"⏩ Skipping {file_name}, already generated")
        return

    # Select data based on dimension name
    if name == 'campaigns':
        data = CAMPAIGNS
    elif name == 'forms':
        data = FORMS
    elif name == 'pages':
        data = PAGES
    else:
        raise ValueError(f"Unknown dimension: {name}")

    # Write file and log
    with open(RAW_DIR / file_name, "w") as f:
        json.dump(data, f, indent=2)
    log_stage(file_name, name, ds, "generated")
    logger.info(f"✅ Generated {file_name} with {len(data)} records")


def generate_contacts_if_needed(ds: str, **kwargs):
    file_name = f"contacts_{ds}.csv"
    if check_stage_complete(file_name, "generated"):
        logger.info(f"⏩ Skipping {file_name}, already generated")
        return
    generate_contacts(file_name, ds)
    log_stage(file_name, "contacts", ds, "generated")


def generate_form_fills_if_needed(ds: str, **kwargs):
    file_name = f"form_fills_{ds}.parquet"
    if check_stage_complete(file_name, "generated"):
        logger.info(f"⏩ Skipping {file_name}, already generated")
        return
    generate_form_fills(file_name, ds)
    log_stage(file_name, "form_fills", ds, "generated")


def generate_website_activity_if_needed(ds: str, **kwargs):
    file_name = f"website_activity_{ds}.json"
    if check_stage_complete(file_name, "generated"):
        logger.info(f"⏩ Skipping {file_name}, already generated")
        return
    generate_website_activity(file_name, ds)
    log_stage(file_name, "website_activity", ds, "generated")

# ------------------------------------------------------------------------------------------------------------------
# Core generators: contacts, form_fills, website_activity with shared keys and enriched columns
# ------------------------------------------------------------------------------------------------------------------

def generate_contacts(file_name: str, ds: str, n: int = BASE_COUNT):
    contacts = []
    for _ in range(n):
        cid = str(uuid.uuid4())
        contacts.append({
            'contact_id': cid,
            'first_name': fake.first_name(),
            'last_name': fake.last_name(),
            'email': fake.email(),
            'company': fake.company(),
            'industry': random.choice(['Technology','Finance','Healthcare','Education','Retail']),
            'lead_source': random.choice(['Web','Email','Event','Referral','Organic Search','Paid Social']),
            'job_title': fake.job(),
            'country': fake.country(),
            'opted_in': random.choice([True, False]),
            'signup_date': ds
        })
    df = pd.DataFrame(contacts)
    df.to_csv(RAW_DIR / file_name, index=False)
    logger.info(f"✅ {file_name} generated ({len(df)} rows)")


def generate_form_fills(file_name: str, ds: str, n: int = BASE_COUNT):
    contacts = pd.read_csv(RAW_DIR / f"contacts_{ds}.csv")['contact_id']
    rows = []
    for _ in range(n):
        rows.append({
            'fill_id': str(uuid.uuid4()),
            'form_id': random.choice([f['form_id'] for f in FORMS]),
            'contact_id': random.choice(contacts),
            'campaign_id': random.choices([c['campaign_id'] for c in CAMPAIGNS], weights=[0.7,0.2,0.1])[0],
            'fill_date': ds,
            'referrer_url': fake.url(),
            'user_agent': fake.user_agent(),
            'estimated_value': round(random.uniform(100.0, 10000.0), 2)
        })
    df = pd.DataFrame(rows)
    pq.write_table(pa.Table.from_pandas(df), RAW_DIR / file_name)
    logger.info(f"✅ {file_name} generated ({len(df)} rows)")


def generate_website_activity(file_name: str, ds: str, n: int = BASE_COUNT):
    contacts = pd.read_csv(RAW_DIR / f"contacts_{ds}.csv")['contact_id']
    pages = PAGES
    activities = []
    for _ in range(n):
        page = random.choice(pages)
        duration = round(random.uniform(5.0, 300.0), 2)  # seconds
        pages_viewed = random.randint(1, 10)
        activities.append({
            'session_id': str(uuid.uuid4()),
            'contact_id': random.choice(contacts),
            'campaign_id': random.choices([c['campaign_id'] for c in CAMPAIGNS], weights=[0.7,0.2,0.1])[0],
            'page_id': page['page_id'],
            'page_url': page['page_url'],
            'page_title': page['page_title'],
            'event_date': ds,
            'event_type': random.choice(['page_view','button_click','form_submit','video_play']),
            'session_duration': duration,
            'pages_viewed': pages_viewed,
            'bounce': pages_viewed == 1,
            'referrer_domain': fake.domain_name()
        })
    with open(RAW_DIR / file_name, 'w') as f:
        json.dump(activities, f, indent=2)
    logger.info(f"✅ {file_name} generated ({len(activities)} rows)")

# ------------------------------------------------------------------------------------------------------------------
# Hook registry: orchestrate generation in order using Airflow tasks
# ------------------------------------------------------------------------------------------------------------------

def register_generation_tasks(ds: str, **kwargs):
    # Dimensions
    generate_dimension_if_needed('campaigns', ds)
    generate_dimension_if_needed('forms', ds)
    generate_dimension_if_needed('pages', ds)
    # Facts
    generate_contacts_if_needed(ds)
    generate_form_fills_if_needed(ds)
    generate_website_activity_if_needed(ds)

# ------------------------------------------------------------------------------------------------------------------
# Note on schema evolution:
# Staging should json_normalize any new fields and log schema changes via log_stage.
# ------------------------------------------------------------------------------------------------------------------
