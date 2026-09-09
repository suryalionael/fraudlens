with transactions as (
    select * from {{ ref('stg_transactions') }}
),

-- Calculate sender-level cumulative stats (ordered by timestamp)
sender_cumulative as (
    select
        transaction_id,
        sender_account,
        timestamp,
        amount_ngn,
        avg(amount_ngn) over (
            partition by sender_account
            order by timestamp
            rows between unbounded preceding and 1 preceding
        ) as customer_avg_amount_prior,
        stddev(amount_ngn) over (
            partition by sender_account
            order by timestamp
            rows between unbounded preceding and 1 preceding
        ) as customer_std_amount_prior,
        max(amount_ngn) over (
            partition by sender_account
            order by timestamp
            rows between unbounded preceding and 1 preceding
        ) as customer_max_amount_prior,
        count(*) over (
            partition by sender_account
            order by timestamp
            rows between unbounded preceding and 1 preceding
        ) as customer_transaction_count_prior
    from transactions
),

-- Calculate merchant-level cumulative stats
merchant_cumulative as (
    select
        transaction_id,
        merchant_category,
        count(*) over (
            partition by merchant_category
            order by timestamp
            rows between unbounded preceding and 1 preceding
        ) as merchant_transaction_count_prior,
        sum(case when is_fraud then 1 else 0 end) over (
            partition by merchant_category
            order by timestamp
            rows between unbounded preceding and 1 preceding
        )::float / nullif(count(*) over (
            partition by merchant_category
            order by timestamp
            rows between unbounded preceding and 1 preceding
        ), 0) as merchant_fraud_rate_prior
    from transactions
),

-- Calculate location-level cumulative stats
location_cumulative as (
    select
        transaction_id,
        location,
        count(*) over (
            partition by location
            order by timestamp
            rows between unbounded preceding and 1 preceding
        ) as location_transaction_count_prior,
        sum(case when is_fraud then 1 else 0 end) over (
            partition by location
            order by timestamp
            rows between unbounded preceding and 1 preceding
        )::float / nullif(count(*) over (
            partition by location
            order by timestamp
            rows between unbounded preceding and 1 preceding
        ), 0) as location_fraud_rate_prior
    from transactions
),

-- Calculate device-level cumulative stats
device_cumulative as (
    select
        transaction_id,
        device_hash,
        sender_account,
        count(*) over (
            partition by device_hash
            order by timestamp
            rows between unbounded preceding and 1 preceding
        ) as device_transaction_count_prior,
        case
            when row_number() over (partition by device_hash, sender_account order by timestamp) = 1
            then true
            else false
        end as device_first_seen
    from transactions
)

-- Join all features
select
    t.*,
    -- Customer features
    coalesce(sc.customer_transaction_count_prior, 0) as customer_transaction_count_prior,
    coalesce(sc.customer_avg_amount_prior, 0) as customer_avg_amount_prior,
    coalesce(sc.customer_std_amount_prior, 0) as customer_std_amount_prior,
    coalesce(sc.customer_max_amount_prior, 0) as customer_max_amount_prior,
    -- Amount features
    case
        when sc.customer_avg_amount_prior > 0
        then t.amount_ngn / sc.customer_avg_amount_prior
        else 1.0
    end as amount_ratio_to_avg,
    case
        when sc.customer_std_amount_prior > 0
        then (t.amount_ngn - sc.customer_avg_amount_prior) / sc.customer_std_amount_prior
        else 0
    end as amount_zscore,
    -- Merchant features
    coalesce(mc.merchant_transaction_count_prior, 0) as merchant_transaction_count_prior,
    coalesce(mc.merchant_fraud_rate_prior, 0) as merchant_fraud_rate_prior,
    -- Location features
    coalesce(lc.location_transaction_count_prior, 0) as location_transaction_count_prior,
    coalesce(lc.location_fraud_rate_prior, 0) as location_fraud_rate_prior,
    -- Device features
    coalesce(dc.device_transaction_count_prior, 0) as device_transaction_count_prior,
    coalesce(dc.device_first_seen, true) as device_first_seen
from transactions t
left join sender_cumulative sc on t.transaction_id = sc.transaction_id
left join merchant_cumulative mc on t.transaction_id = mc.transaction_id
left join location_cumulative lc on t.transaction_id = lc.transaction_id
left join device_cumulative dc on t.transaction_id = dc.transaction_id
