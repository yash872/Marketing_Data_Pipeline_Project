-- tests/mart_no_orphan_form_fills.sql
-- All form_fills must join back to a mart_contacts row
select f.fill_id
from {{ ref('mart_form_fills') }} f
left join {{ ref('mart_contacts') }} c
  on f.contact_id = c.contact_id
where c.contact_id is null
