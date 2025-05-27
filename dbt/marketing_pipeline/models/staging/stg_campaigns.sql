{% 
  set batch_date = var('batch_date', run_started_at.strftime('%Y-%m-%d')) 
%}

{{ 
  config(
    materialized='incremental',
    unique_key='campaign_id',
    incremental_strategy  = 'merge'
  ) 
}}

with raw as (
  select
    data
  from {{ source('raw_minio','campaigns') }}
),

parsed as (
  select
    data:"campaign_id"        :: string        as campaign_id,
    data:"campaign_name"      :: string        as campaign_name,
    data:"dim_date"      :: string        as dim_date
  from raw
)

select * from parsed

{% if is_incremental() %}
  where dim_date = '{{ batch_date }}'
{% endif %}