{% 
  set batch_date = var('batch_date', run_started_at.strftime('%Y-%m-%d')) 
%}

{{ 
  config(
    materialized = 'incremental',
    unique_key   = 'contact_id',
    incremental_strategy  = 'merge',
    on_schema_change = 'sync_all_columns'
  ) 
}}

with raw as (

  select
    contact_id  ::  string as contact_id,
    first_name  ::  string as first_name,
    last_name ::  string as last_name,
    email ::  string as email,
    company ::  string as company,
    industry  ::  string as industry,
    lead_source ::  string as lead_source,
    job_title ::  string as job_title,
    country ::  string as country,
    opted_in  ::  boolean as opted_in,
    signup_date ::  timestamp_ntz as signup_date

  from {{ source('raw_minio','contacts') }}

)

select * from raw

{% if is_incremental() %}
  where signup_date = to_date('{{ batch_date }}')
{% endif %}
