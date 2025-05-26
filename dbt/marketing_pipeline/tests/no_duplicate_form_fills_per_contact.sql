-- tests/no_duplicate_form_fills_per_contact.sql
-- Ensure each contact has at most one fill per day
select
  contact_id,
  date_trunc('day', fill_date) as ds,
  count(*) as cnt
from {{ ref('stg_form_fills') }}
group by 1,2
having cnt > 1
