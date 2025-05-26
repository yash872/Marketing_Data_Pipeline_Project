{% 
  set batch_date = var('batch_date', run_started_at.strftime('%Y-%m-%d')) 
%}

{{ 
  config(
    materialized='incremental',
    unique_key='session_id',
    incremental_strategy  = 'merge'
  )
}}

with raw as (
  select
    data,
    to_date('{{ batch_date }}') as upload_date
  from {{ source('raw_minio','website_activity') }}
),

parsed as (
  select
    data:"session_id"      :: string        as session_id,
    data:"contact_id"      :: string        as contact_id,
    data:"campaign_id"     :: string        as campaign_id,
    data:"page_id"         :: string        as page_id,
    data:"page_url"        :: string        as page_url,
    data:"page_title"      :: string        as page_title,
    data:"event_date"      :: timestamp_ntz as event_date,
    data:"event_type"      :: string        as event_type,
    data:"session_duration" :: decimal      as session_duration,
    data:"pages_viewed"     :: number       as pages_viewed,
    data:"bounce"          :: boolean       as bounce,
    data:"referrer_domain"    :: string     as referrer_domain,
    upload_date
  from raw
)

select * from parsed

{% if is_incremental() %}
  where upload_date = to_date('{{ batch_date }}')
{% endif %}