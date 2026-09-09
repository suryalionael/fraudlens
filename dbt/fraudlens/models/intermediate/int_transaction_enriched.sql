with transactions as (
    select * from {{ ref('stg_transactions') }}
),

-- Calculate sender-level aggregates (historical only - no future leakage)
sender_stats as (
    select
        sender_account,
        count(*) as total_transactions,
        sum(case when is_fraud then 1 else 0 end) as fraud_count,
        round(100.0 * sum(case when is_fraud then 1 else 0 end) / count(*), 4)::numeric as fraud_rate,
        round(avg(amount_ngn), 2)::numeric as avg_amount,
        round(stddev(amount_ngn), 2)::numeric as std_amount,
        min(timestamp) as first_seen,
        max(timestamp) as last_seen
    from transactions
    group by sender_account
),

-- Calculate merchant-level aggregates
merchant_stats as (
    select
        merchant_category,
        count(*) as total_transactions,
        sum(case when is_fraud then 1 else 0 end) as fraud_count,
        round(100.0 * sum(case when is_fraud then 1 else 0 end) / count(*), 4)::numeric as fraud_rate,
        round(avg(amount_ngn), 2)::numeric as avg_amount
    from transactions
    group by merchant_category
),

-- Calculate location-level aggregates
location_stats as (
    select
        location,
        count(*) as total_transactions,
        sum(case when is_fraud then 1 else 0 end) as fraud_count,
        round(100.0 * sum(case when is_fraud then 1 else 0 end) / count(*), 4)::numeric as fraud_rate
    from transactions
    group by location
),

-- Calculate device-level aggregates
device_stats as (
    select
        device_used,
        count(*) as total_transactions,
        sum(case when is_fraud then 1 else 0 end) as fraud_count,
        round(100.0 * sum(case when is_fraud then 1 else 0 end) / count(*), 4)::numeric as fraud_rate
    from transactions
    group by device_used
)

-- Join all stats back to transactions
select
    t.*,
    s.total_transactions as sender_total_transactions,
    s.fraud_count as sender_fraud_count,
    s.fraud_rate as sender_fraud_rate,
    s.avg_amount as sender_avg_amount,
    s.std_amount as sender_std_amount,
    m.total_transactions as merchant_total_transactions,
    m.fraud_count as merchant_fraud_count,
    m.fraud_rate as merchant_fraud_rate,
    m.avg_amount as merchant_avg_amount,
    l.total_transactions as location_total_transactions,
    l.fraud_count as location_fraud_count,
    l.fraud_rate as location_fraud_rate,
    d.total_transactions as device_total_transactions,
    d.fraud_count as device_fraud_count,
    d.fraud_rate as device_fraud_rate
from transactions t
left join sender_stats s on t.sender_account = s.sender_account
left join merchant_stats m on t.merchant_category = m.merchant_category
left join location_stats l on t.location = l.location
left join device_stats d on t.device_used = d.device_used
