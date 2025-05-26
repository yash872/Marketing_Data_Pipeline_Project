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
    data,
    to_date('{{ batch_date }}') as upload_date
  from {{ source('raw_minio','forms') }}
),

parsed as (
  select
    data:"form_id"        :: string        as form_id,
    data:"form_type"       :: string        as form_type,
    upload_date
  from raw
)

select * from parsed

{% if is_incremental() %}
  where upload_date = to_date('{{ batch_date }}')
{% endif %}