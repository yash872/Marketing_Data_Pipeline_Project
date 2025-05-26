-- last_modified_after_created (for stg_contacts)
-- Checks that last_modified_at is never before created_at.

{% test last_modified_after_created(model, column_name) %}
select *
from {{ model }}
where {{ column_name }} < created_at
{% endtest %}
