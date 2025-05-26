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
    data,
    to_date('{{ batch_date }}') as upload_date
  from {{ source('raw_minio','pages') }}
),

parsed as (
  select
    data:"page_id"        :: string        as page_id,
    data:"page_url"       :: string        as page_url,
    data:"page_title"      :: string        as page_title,
    upload_date
  from raw
)

select * from parsed

{% if is_incremental() %}
  where upload_date = to_date('{{ batch_date }}')
{% endif %}