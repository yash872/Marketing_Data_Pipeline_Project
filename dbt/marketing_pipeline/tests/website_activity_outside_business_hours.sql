-- tests/website_activity_outside_business_hours.sql
-- Catch events before 6:00 or after 22:00
select *
from {{ ref('stg_website_activity') }}
where date_part('hour', event_date) not between 6 and 22
