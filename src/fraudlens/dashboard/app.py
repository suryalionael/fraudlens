"""Streamlit dashboard for FraudLens.

All pages use real data from PostgreSQL/dbt marts.
No random/fabricated data is used in production pages.
"""

from __future__ import annotations

import json
import os
from typing import Any

import pandas as pd


def create_dashboard() -> Any:
    try:
        import streamlit as st
    except ImportError:
        raise ImportError("Streamlit is required. Install with: pip install streamlit")

    st.set_page_config(
        page_title="FraudLens Dashboard",
        page_icon="\U0001f50d",
        layout="wide",
        initial_sidebar_state="expanded",
    )

    st.title("\U0001f50d FraudLens \u2014 Financial Transaction Risk Intelligence")

    db_available = _check_db_connection()

    st.sidebar.header("Navigation")
    page = st.sidebar.radio(
        "Select Page",
        [
            "Executive Overview",
            "Risk Monitoring",
            "Investigation Queue",
            "Fraud Analysis",
            "Model Performance",
        ],
    )

    if not db_available:
        st.warning(
            "PostgreSQL is not available. Dashboard requires a running database. "
            "Start PostgreSQL and run ingestion first."
        )

    if page == "Executive Overview":
        _render_executive_overview(db_available)
    elif page == "Risk Monitoring":
        _render_risk_monitoring(db_available)
    elif page == "Investigation Queue":
        _render_investigation_queue(db_available)
    elif page == "Fraud Analysis":
        _render_fraud_analysis(db_available)
    elif page == "Model Performance":
        _render_model_performance()

    return st


def _check_db_connection() -> bool:
    try:
        from fraudlens.dashboard.data.connection import get_connection

        conn = get_connection()
        conn.close()
        return True
    except Exception:
        return False


def _parse_json_list(val):
    if isinstance(val, list):
        return val
    if isinstance(val, str):
        try:
            return json.loads(val)
        except (json.JSONDecodeError, TypeError):
            return [val] if val else []
    return []


# Page 1: Executive Overview


def _render_executive_overview(db_available: bool) -> None:
    import streamlit as st

    st.header("Executive Overview")

    if not db_available:
        st.info("Database not available. Run ingestion to populate data.")
        return

    from fraudlens.dashboard.data.executive import (
        get_kpi_summary,
        get_fraud_trend,
        get_fraud_by_dimension,
    )

    kpi = get_kpi_summary()
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Total Transactions", f"{kpi['total_transactions']:,}")
    with col2:
        st.metric("Fraudulent Transactions", f"{kpi['fraud_count']:,}")
    with col3:
        st.metric("Fraud Rate", f"{kpi['fraud_rate']:.2f}%")
    with col4:
        st.metric("Total Value", f"N{ kpi['total_value']:,.0f}")

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Fraudulent Value", f"N{ kpi['fraud_value']:,.0f}")
    with col2:
        st.metric("Avg Transaction", f"N{ kpi['avg_amount']:,.0f}")

    st.divider()

    st.subheader("Fraud Volume & Rate Over Time")
    trend = get_fraud_trend()
    if not trend.empty:
        trend_display = trend.set_index("date")[["total_transactions", "fraud_count"]]
        st.line_chart(trend_display)

        st.subheader("Fraud Rate Over Time")
        rate_display = trend.set_index("date")[["fraud_rate"]]
        st.line_chart(rate_display)
    else:
        st.info("No transaction data available.")

    col1, col2 = st.columns(2)
    with col1:
        st.subheader("Fraud by Merchant Category")
        by_merchant = get_fraud_by_dimension("merchant_category")
        if not by_merchant.empty:
            st.bar_chart(by_merchant.set_index("category")["fraud_rate"])

    with col2:
        st.subheader("Fraud by Location")
        by_location = get_fraud_by_dimension("location")
        if not by_location.empty:
            st.bar_chart(by_location.set_index("category")["fraud_rate"])

    st.subheader("Fraud by Transaction Type")
    by_type = get_fraud_by_dimension("transaction_type")
    if not by_type.empty:
        st.bar_chart(by_type.set_index("category")["fraud_rate"])


# Page 2: Risk Monitoring


def _render_risk_monitoring(db_available: bool) -> None:
    import streamlit as st

    st.header("Risk Monitoring")

    if not db_available:
        st.info("Database not available.")
        return

    try:
        from fraudlens.dashboard.data.connection import query_scalar

        score_count = query_scalar("SELECT COUNT(*) FROM risk.transaction_scores")
    except Exception:
        score_count = 0

    if not score_count:
        st.warning("No risk scores found. Run batch scoring first.")
        return

    from fraudlens.dashboard.data.risk import (
        get_risk_kpi_summary,
        get_risk_distribution,
        get_risk_trend,
        get_risk_by_dimension,
    )

    kpi = get_risk_kpi_summary()
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Transactions Scored", f"{kpi['total_scored']:,}")
    with col2:
        st.metric("High Risk", f"{kpi['high_risk']:,}")
    with col3:
        st.metric("Critical Risk", f"{kpi['critical_risk']:,}")
    with col4:
        st.metric("Avg Risk Score", f"{kpi['avg_risk_score']:.1f}")

    col1, col2 = st.columns(2)
    with col1:
        st.metric("High/Critical %", f"{kpi['high_risk_pct']:.1f}%")
    with col2:
        st.metric("Requiring Investigation", f"{kpi['review_count']:,}")

    st.divider()

    st.subheader("Risk Level Distribution")
    dist = get_risk_distribution()
    if not dist.empty:
        col1, col2 = st.columns(2)
        with col1:
            st.dataframe(
                dist[["risk_level", "count", "percentage", "avg_score"]],
                use_container_width=True,
                hide_index=True,
            )
        with col2:
            st.bar_chart(dist.set_index("risk_level")["count"])

    st.subheader("Risk Score Trend")
    trend = get_risk_trend()
    if not trend.empty:
        st.line_chart(trend.set_index("date")[["avg_risk_score", "high_risk_pct"]])

    st.subheader("Risk by Merchant Category")
    by_merchant = get_risk_by_dimension("merchant_category")
    if not by_merchant.empty:
        st.bar_chart(by_merchant.set_index("category")["avg_risk_score"])


# Page 3: Investigation Queue


def _render_investigation_queue(db_available: bool) -> None:
    import streamlit as st

    st.header("Investigation Queue")

    if not db_available:
        st.info("Database not available.")
        return

    try:
        from fraudlens.dashboard.data.connection import query_scalar

        score_count = query_scalar("SELECT COUNT(*) FROM risk.transaction_scores")
    except Exception:
        score_count = 0

    if not score_count:
        st.warning("No risk scores found. Run batch scoring first.")
        return

    from fraudlens.dashboard.data.investigations import (
        get_investigation_queue,
        get_investigation_stats,
    )

    stats = get_investigation_stats()
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Total Scored", f"{stats['total_scored']:,}")
    with col2:
        st.metric("High/Critical", f"{stats['high_critical_count']:,}")
    with col3:
        st.metric("Needs Investigation", f"{stats['needs_review_count']:,}")

    st.divider()

    col1, col2 = st.columns(2)
    with col1:
        risk_filter = st.selectbox(
            "Risk Level",
            ["All", "critical", "high", "medium", "low"],
        )
    with col2:
        limit = st.slider("Max results", 10, 500, 100)

    st.subheader("Investigation Queue")
    queue = get_investigation_queue(
        risk_level=risk_filter if risk_filter != "All" else None,
        limit=limit,
    )

    if not queue.empty:
        if "risk_factors" in queue.columns:
            queue["risk_factors_display"] = queue["risk_factors"].apply(
                lambda x: "; ".join(_parse_json_list(x)[:3]) if x else ""
            )
            display_cols = [
                c for c in queue.columns if c not in ("risk_factors", "rule_signals")
            ]
            if "risk_factors_display" in queue.columns:
                display_cols.append("risk_factors_display")
            st.dataframe(queue[display_cols], use_container_width=True, hide_index=True)
        else:
            st.dataframe(queue, use_container_width=True, hide_index=True)
    else:
        st.info("No transactions found matching the selected filters.")


# Page 4: Fraud Analysis


def _render_fraud_analysis(db_available: bool) -> None:
    import streamlit as st

    st.header("Fraud Analysis")

    if not db_available:
        st.info("Database not available.")
        return

    from fraudlens.dashboard.data.fraud import (
        get_fraud_by_merchant,
        get_fraud_by_location,
        get_fraud_by_transaction_type,
        get_fraud_by_payment_channel,
        get_fraud_volume_vs_rate,
    )

    tab1, tab2, tab3, tab4 = st.tabs(
        ["Merchant", "Geography", "Transaction Type", "Payment Channel"]
    )

    with tab1:
        st.subheader("Fraud by Merchant Category")
        data = get_fraud_by_merchant()
        if not data.empty:
            st.dataframe(data, use_container_width=True, hide_index=True)
            st.bar_chart(
                data.set_index("merchant_category")[
                    ["total_transactions", "fraud_count"]
                ]
            )

    with tab2:
        st.subheader("Fraud by Location")
        data = get_fraud_by_location()
        if not data.empty:
            st.dataframe(data, use_container_width=True, hide_index=True)
            st.bar_chart(
                data.set_index("location")[["total_transactions", "fraud_count"]]
            )

    with tab3:
        st.subheader("Fraud by Transaction Type")
        data = get_fraud_by_transaction_type()
        if not data.empty:
            st.dataframe(data, use_container_width=True, hide_index=True)
            st.bar_chart(
                data.set_index("transaction_type")[
                    ["total_transactions", "fraud_count"]
                ]
            )

    with tab4:
        st.subheader("Fraud by Payment Channel")
        data = get_fraud_by_payment_channel()
        if not data.empty:
            st.dataframe(data, use_container_width=True, hide_index=True)
            st.bar_chart(
                data.set_index("payment_channel")[["total_transactions", "fraud_count"]]
            )

    st.divider()
    st.subheader("Fraud Volume vs Rate (by Merchant)")
    bubble = get_fraud_volume_vs_rate()
    if not bubble.empty:
        st.dataframe(bubble, use_container_width=True, hide_index=True)


# Page 5: Model Performance


def _render_model_performance() -> None:
    import streamlit as st

    st.header("Model Performance")

    model_dir = os.environ.get("FRAUDLENS_MODEL_DIR", "models")
    metadata_files = {
        "Logistic Regression": os.path.join(
            model_dir, "logistic_regression.metadata.json"
        ),
        "Random Forest": os.path.join(model_dir, "random_forest.metadata.json"),
        "XGBoost": os.path.join(model_dir, "xgboost.metadata.json"),
    }

    real_models = []
    for model_name, path in metadata_files.items():
        if os.path.exists(path):
            with open(path) as f:
                meta = json.load(f)
            real_models.append(
                {
                    "model": model_name,
                    **meta.get("evaluation", {}),
                    "model_version": meta.get("model_version", "unknown"),
                    "train_size": meta.get("train_size", 0),
                    "test_size": meta.get("test_size", 0),
                    "features": len(meta.get("feature_columns", [])),
                    "training_timestamp": meta.get("training_timestamp", "unknown"),
                }
            )

    if real_models:
        st.subheader("Trained Model Metrics")
        st.caption("Metrics from actual model training runs.")
        model_data = pd.DataFrame(real_models)
        st.dataframe(model_data, use_container_width=True, hide_index=True)

        for m in real_models:
            with st.expander(f"{m['model']} ({m['model_version']})"):
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("PR-AUC", f"{m.get('pr_auc', 'N/A')}")
                with col2:
                    st.metric("F1", f"{m.get('f1', 'N/A')}")
                with col3:
                    st.metric("Features", f"{m.get('features', 0)}")
                st.text(f"Trained: {m.get('training_timestamp', 'unknown')}")
                st.text(
                    f"Train size: {m.get('train_size', 0):,} | Test size: {m.get('test_size', 0):,}"
                )
    else:
        st.info(
            "No trained model artifacts found. "
            "Train a model first to see evaluation metrics."
        )
