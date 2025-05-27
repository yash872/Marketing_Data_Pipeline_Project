{% 
  set batch_date = var('batch_date', run_started_at.strftime('%Y-%m-%d')) 
%}

{{ 
  config(
    materialized='incremental',
    unique_key='fill_id',
    incremental_strategy  = 'merge'
  ) 
}}

with raw as (
  select
    data
  from {{ source('raw_minio','form_fills') }}
),

parsed as (
  select
    data:"fill_id"        :: string        as fill_id,
    data:"form_id"        :: string        as form_id,
    data:"contact_id"     :: string        as contact_id,
    data:"campaign_id"    :: string        as campaign_id,
    data:"form_type"      :: string        as form_type,
    data:"fill_date"      :: timestamp_ntz as fill_date,
    data:"referrer_url"   :: string        as referrer_url,
    data:"user_agent"     :: string        as user_agent,
    data:"estimated_value" :: string       as estimated_value
  from raw
)

select * from parsed

{% if is_incremental() %}
  where fill_date = to_date('{{ batch_date }}')
{% endif %}
