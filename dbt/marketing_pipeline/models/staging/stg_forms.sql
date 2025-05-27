{% 
  set batch_date = var('batch_date', run_started_at.strftime('%Y-%m-%d')) 
%}

{{ 
  config(
    materialized='incremental',
    unique_key='form_id',
    incremental_strategy  = 'merge'
  ) 
}}

with raw as (
  select
    data
  from {{ source('raw_minio','forms') }}
),

parsed as (
  select
    data:"form_id"        :: string        as form_id,
    data:"form_type"       :: string        as form_type,
    data:"dim_date"      :: string        as dim_date
  from raw
)

select * from parsed

{% if is_incremental() %}
  where dim_date = '{{ batch_date }}'
{% endif %}