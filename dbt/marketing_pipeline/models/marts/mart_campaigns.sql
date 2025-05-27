{{ 
  config(
    materialized = 'incremental',
    unique_key = 'campaign_id',
    incremental_strategy = 'merge',
    on_schema_change = 'sync_all_columns'
  )
}}

select
  campaign_id,
  campaign_name,
  dim_date
from {{ ref('stg_campaigns') }}
