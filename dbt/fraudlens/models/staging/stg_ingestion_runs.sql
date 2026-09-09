with source as (
    select * from {{ source('raw', 'ingestion_runs') }}
),

renamed as (
    select
        ingestion_run_id,
        source_name,
        source_version,
        source_file,
        source_sha256,
        started_at,
        completed_at,
        rows_read,
        rows_loaded,
        fraud_count,
        fraud_rate,
        status,
        notes
    from source
)

select * from renamed
