with enriched as (
    select * from {{ ref('int_transaction_enriched') }}
),

-- Calculate amount anomaly score (z-score)
amount_stats as (
    select
        sender_account,
        avg(amount_ngn) as avg_amount,
        stddev(amount_ngn) as std_amount
    from enriched
    group by sender_account
),

-- Calculate transaction frequency (transactions per day)
transaction_frequency as (
    select
        sender_account,
        count(*) as total_transactions,
        (date_part('day', max(timestamp) - min(timestamp)) + 1)::int as days_active,
        (count(*) * 1.0 / (date_part('day', max(timestamp) - min(timestamp)) + 1))::numeric(10,2) as transactions_per_day
    from enriched
    group by sender_account
)

select
    e.*,
    -- Amount anomaly (z-score)
    case
        when a.std_amount > 0 then ((e.amount_ngn - a.avg_amount) / a.std_amount)::numeric(10,4)
        else 0::numeric
    end as amount_zscore,
    -- Transaction frequency
    f.total_transactions as sender_total_transactions_freq,
    f.days_active as sender_days_active,
    f.transactions_per_day as sender_transactions_per_day,
    -- Risk indicators
    case
        when e.sender_fraud_rate > 5 then 'HIGH'
        when e.sender_fraud_rate > 2 then 'MEDIUM'
        else 'LOW'
    end as sender_risk_level,
    case
        when e.merchant_fraud_rate > 10 then 'HIGH'
        when e.merchant_fraud_rate > 5 then 'MEDIUM'
        else 'LOW'
    end as merchant_risk_level,
    case
        when e.location_fraud_rate > 10 then 'HIGH'
        when e.location_fraud_rate > 5 then 'MEDIUM'
        else 'LOW'
    end as location_risk_level
from enriched e
left join amount_stats a on e.sender_account = a.sender_account
left join transaction_frequency f on e.sender_account = f.sender_account
