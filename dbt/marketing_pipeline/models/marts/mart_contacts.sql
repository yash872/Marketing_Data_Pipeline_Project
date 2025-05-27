{{ 
  config(
    materialized = 'incremental',
    unique_key = 'contact_id',
    incremental_strategy = 'merge',
    on_schema_change = 'sync_all_columns'
  )
}}

select
  contact_id,
  first_name,
  last_name,
  email,
  company,
  industry,
  lead_source,
  job_title,
  country,
  opted_in,
  signup_date
from {{ ref('stg_contacts') }}
