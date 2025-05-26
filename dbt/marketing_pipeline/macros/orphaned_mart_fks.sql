{% test orphaned_mart_fks(model, column_name) %}

with orphans as (
  select {{ column_name }} as orphan_key
  from {{ model }}
  where {{ column_name }} is not null
  except
  select contact_id
  from {{ ref('mart_contacts') }}
)

select * from orphans

{% endtest %}
