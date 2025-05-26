{{ 
  config(
    materialized = 'incremental',
    unique_key = 'fill_id',
    incremental_strategy = 'merge',
    on_schema_change = 'sync_all_columns'
  )
}}

select
  fill_id,
  form_id,
  contact_id,
  campaign_id,
  form_type,
  fill_date,
  referrer_url,
  user_agent,
  estimated_value,
  upload_date
from {{ ref('stg_form_fills') }}
