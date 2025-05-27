{{ 
  config(
    materialized = 'incremental',
    unique_key = 'form_id',
    incremental_strategy = 'merge',
    on_schema_change = 'sync_all_columns'
  )
}}

select
  form_id,
  form_type,
  dim_date
from {{ ref('stg_forms') }}
