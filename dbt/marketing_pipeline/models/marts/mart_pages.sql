{{ 
  config(
    materialized = 'incremental',
    unique_key = 'page_id',
    incremental_strategy = 'merge',
    on_schema_change = 'sync_all_columns'
  )
}}

select
  page_id,
  page_url,
  page_title,
  upload_date
from {{ ref('stg_pages') }}
