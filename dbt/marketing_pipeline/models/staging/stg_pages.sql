{% 
  set batch_date = var('batch_date', run_started_at.strftime('%Y-%m-%d')) 
%}

{{ 
  config(
    materialized='incremental',
    unique_key='page_id',
    incremental_strategy  = 'merge'
  ) 
}}

with raw as (
  select
    data
  from {{ source('raw_minio','pages') }}
),

parsed as (
  select
    data:"page_id"        :: string        as page_id,
    data:"page_url"       :: string        as page_url,
    data:"page_title"      :: string        as page_title,
    data:"dim_date"      :: string        as dim_date
  from raw
)

select * from parsed

{% if is_incremental() %}
  where dim_date = '{{ batch_date }}'
{% endif %}