{% test state_in_seed(model, column_name) %}

    select distinct {{ column_name }} as state
    from {{ model }}
    where {{ column_name }} is not null
      and lower(trim({{ column_name }})) not in (
          select distinct state
          from {{ ref("state_zones") }}
      )

{% endtest %}
