{% macro generate_schema_name(custom_schema_name, node, root_project) -%}
  {%- if custom_schema_name -%}
    {{ custom_schema_name }}
  {%- else -%}
    {{ target.schema }}
  {%- endif -%}
{%- endmacro %}
