{{ 
  config(
    materialized = 'incremental',
    unique_key = 'session_id',
    incremental_strategy = 'merge',
    on_schema_change = 'sync_all_columns'
  )
}}

select
  session_id,
  contact_id,
  campaign_id,
  page_id,
  page_url,
  page_title,
  event_date,
  event_type,
  session_duration,
  pages_viewed,
  bounce,
  referrer_domain
from {{ ref('stg_website_activity') }}
