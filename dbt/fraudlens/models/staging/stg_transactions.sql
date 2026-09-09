with source as (
    select * from {{ source('raw', 'transactions') }}
),

renamed as (
    select
        transaction_id,
        timestamp,
        sender_account,
        receiver_account,
        transaction_type,
        merchant_category,
        location,
        device_used,
        is_fraud,
        fraud_type,
        time_since_last_transaction,
        spending_deviation_score,
        velocity_score,
        geo_anomaly_score,
        payment_channel,
        ip_address,
        device_hash,
        amount_ngn,
        bvn_linked,
        new_device_transaction,
        sender_persona
    from source
)

select * from renamed
