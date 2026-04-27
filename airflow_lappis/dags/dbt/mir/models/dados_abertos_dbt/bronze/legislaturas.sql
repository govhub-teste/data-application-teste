{{ config(materialized="table") }}

with
    legislaturas_raw as (
        select
            id::integer as id,
            data_inicio::date as data_inicio,
            data_fim::date as data_fim,
            data_eleicao::date as data_eleicao,
            (dt_ingest || '-03:00')::timestamptz as dt_ingest
        from {{ source("senado_federal", "legislaturas") }}
    )

select *
from legislaturas_raw
