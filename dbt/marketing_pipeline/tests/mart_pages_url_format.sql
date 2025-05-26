-- tests/mart_pages_url_format.sql
-- page_url should start with http or https
select *
from {{ ref('mart_pages') }}
where page_url not like 'http%'
