with transactions as (
    select * from {{ ref('stg_transactions') }}
),

-- Fraud summary by transaction type
fraud_by_type as (
    select
        transaction_type,
        count(*) as total_transactions,
        sum(case when is_fraud then 1 else 0 end) as fraud_count,
        round(100.0 * sum(case when is_fraud then 1 else 0 end) / count(*), 4)::numeric as fraud_rate,
        round(avg(amount_ngn), 2)::numeric as avg_amount,
        round(avg(case when is_fraud then amount_ngn end), 2)::numeric as avg_fraud_amount
    from transactions
    group by transaction_type
),

-- Fraud summary by merchant category
fraud_by_merchant as (
    select
        merchant_category,
        count(*) as total_transactions,
        sum(case when is_fraud then 1 else 0 end) as fraud_count,
        round(100.0 * sum(case when is_fraud then 1 else 0 end) / count(*), 4)::numeric as fraud_rate,
        round(avg(amount_ngn), 2)::numeric as avg_amount
    from transactions
    group by merchant_category
),

-- Fraud summary by location
fraud_by_location as (
    select
        location,
        count(*) as total_transactions,
        sum(case when is_fraud then 1 else 0 end) as fraud_count,
        round(100.0 * sum(case when is_fraud then 1 else 0 end) / count(*), 4)::numeric as fraud_rate
    from transactions
    group by location
)

select
    'BY_TYPE' as report_type,
    transaction_type as category,
    total_transactions,
    fraud_count,
    fraud_rate,
    avg_amount,
    avg_fraud_amount as additional_metric
from fraud_by_type

union all

select
    'BY_MERCHANT' as report_type,
    merchant_category as category,
    total_transactions,
    fraud_count,
    fraud_rate,
    avg_amount,
    NULL::numeric as additional_metric
from fraud_by_merchant

union all

select
    'BY_LOCATION' as report_type,
    location as category,
    total_transactions,
    fraud_count,
    fraud_rate,
    NULL::numeric as avg_amount,
    NULL::numeric as additional_metric
from fraud_by_location
