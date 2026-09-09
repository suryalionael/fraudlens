"""Streamlit dashboard for FraudLens.

This module provides an interactive dashboard for fraud analysis
and risk monitoring.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

import numpy as np
import pandas as pd


def create_dashboard() -> Any:
    """Create and configure the Streamlit dashboard.

    Returns:
        Configured Streamlit application.
    """
    try:
        import streamlit as st
    except ImportError:
        raise ImportError("Streamlit is required. Install with: pip install streamlit")

    st.set_page_config(
        page_title="FraudLens Dashboard",
        page_icon="🔍",
        layout="wide",
        initial_sidebar_state="expanded",
    )

    st.title("🔍 FraudLens — Financial Transaction Risk Intelligence")

    # Sidebar
    st.sidebar.header("Navigation")
    page = st.sidebar.radio(
        "Select Page",
        ["Executive Overview", "Risk Monitoring", "Investigation Queue", "Fraud Analysis", "Model Performance"],
    )

    # Main content
    if page == "Executive Overview":
        _render_executive_overview()
    elif page == "Risk Monitoring":
        _render_risk_monitoring()
    elif page == "Investigation Queue":
        _render_investigation_queue()
    elif page == "Fraud Analysis":
        _render_fraud_analysis()
    elif page == "Model Performance":
        _render_model_performance()

    return st


def _render_executive_overview() -> None:
    """Render executive overview page."""
    import streamlit as st

    st.header("Executive Overview")

    # Generate sample data for demonstration
    np.random.seed(42)
    n_transactions = 10000

    data = pd.DataFrame({
        "timestamp": pd.date_range("2023-01-01", periods=n_transactions, freq="min"),
        "amount_ngn": np.random.lognormal(10, 1.5, n_transactions),
        "is_fraud": np.random.choice([True, False], n_transactions, p=[0.036, 0.964]),
        "risk_score": np.random.beta(2, 10, n_transactions) * 100,
        "risk_level": np.random.choice(["low", "medium", "high", "critical"], n_transactions, p=[0.7, 0.2, 0.08, 0.02]),
        "merchant_category": np.random.choice(["retail", "electronics", "groceries", "entertainment", "travel"], n_transactions),
        "location": np.random.choice(["Lagos", "Abuja", "Port Harcourt", "Kano", "Ibadan"], n_transactions),
    })

    # KPIs
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric("Total Transactions", f"{len(data):,}")

    with col2:
        st.metric("Total Value", f"₦{data['amount_ngn'].sum():,.0f}")

    with col3:
        fraud_rate = data["is_fraud"].mean() * 100
        st.metric("Fraud Rate", f"{fraud_rate:.2f}%")

    with col4:
        high_risk = (data["risk_level"].isin(["high", "critical"])).sum()
        st.metric("High-Risk Transactions", f"{high_risk:,}")

    # Charts
    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Fraud Trend")
        daily_fraud = data.groupby(data["timestamp"].dt.date)["is_fraud"].sum()
        st.line_chart(daily_fraud)

    with col2:
        st.subheader("Risk Distribution")
        risk_counts = data["risk_level"].value_counts()
        st.bar_chart(risk_counts)

    # Fraud by category
    st.subheader("Fraud by Merchant Category")
    fraud_by_category = data.groupby("merchant_category")["is_fraud"].mean() * 100
    st.bar_chart(fraud_by_category)


def _render_risk_monitoring() -> None:
    """Render risk monitoring page."""
    import streamlit as st

    st.header("Risk Monitoring")

    # Generate sample data
    np.random.seed(42)
    n_transactions = 5000

    data = pd.DataFrame({
        "timestamp": pd.date_range("2023-01-01", periods=n_transactions, freq="min"),
        "amount_ngn": np.random.lognormal(10, 1.5, n_transactions),
        "risk_score": np.random.beta(2, 10, n_transactions) * 100,
        "risk_level": np.random.choice(["low", "medium", "high", "critical"], n_transactions, p=[0.7, 0.2, 0.08, 0.02]),
        "merchant_category": np.random.choice(["retail", "electronics", "groceries", "entertainment", "travel"], n_transactions),
        "location": np.random.choice(["Lagos", "Abuja", "Port Harcourt", "Kano", "Ibadan"], n_transactions),
        "hour_of_day": np.random.randint(0, 24, n_transactions),
    })

    # Risk score distribution
    st.subheader("Risk Score Distribution")
    st.histogram(data["risk_score"], bins=50)

    # High-risk trend
    st.subheader("High-Risk Transaction Trend")
    high_risk = data[data["risk_level"].isin(["high", "critical"])]
    hourly_high_risk = high_risk.groupby(high_risk["timestamp"].dt.hour).size()
    st.line_chart(hourly_high_risk)

    # Risk by merchant category
    st.subheader("Risk by Merchant Category")
    risk_by_category = data.groupby("merchant_category")["risk_score"].mean()
    st.bar_chart(risk_by_category)

    # Risk by location
    st.subheader("Risk by Location")
    risk_by_location = data.groupby("location")["risk_score"].mean()
    st.bar_chart(risk_by_location)


def _render_investigation_queue() -> None:
    """Render investigation queue page."""
    import streamlit as st

    st.header("Investigation Queue")

    # Generate sample investigation data
    np.random.seed(42)
    n_investigations = 100

    data = pd.DataFrame({
        "transaction_id": [f"T{i:06d}" for i in range(n_investigations)],
        "timestamp": pd.date_range("2023-01-01", periods=n_investigations, freq="h"),
        "amount_ngn": np.random.lognormal(11, 2, n_investigations),
        "risk_score": np.random.uniform(60, 100, n_investigations),
        "risk_level": np.random.choice(["high", "critical"], n_investigations, p=[0.7, 0.3]),
        "fraud_probability": np.random.uniform(0.6, 0.95, n_investigations),
        "risk_factors": [
            np.random.choice([
                "New device",
                "Amount anomaly",
                "High velocity",
                "High-risk merchant",
                "High-risk location",
            ])
            for _ in range(n_investigations)
        ],
        "recommended_action": np.random.choice(["review", "urgent_review"], n_investigations, p=[0.6, 0.4]),
        "status": np.random.choice(["pending", "in_progress", "resolved"], n_investigations, p=[0.5, 0.3, 0.2]),
    })

    # Sort by risk score
    data = data.sort_values("risk_score", ascending=False)

    # Display queue
    st.subheader(f"Top {len(data)} High-Risk Transactions")
    st.dataframe(
        data[["transaction_id", "timestamp", "amount_ngn", "risk_score", "risk_level", "fraud_probability", "risk_factors", "recommended_action", "status"]],
        use_container_width=True,
    )

    # Summary stats
    st.subheader("Queue Statistics")
    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric("Pending", (data["status"] == "pending").sum())

    with col2:
        st.metric("In Progress", (data["status"] == "in_progress").sum())

    with col3:
        st.metric("Resolved", (data["status"] == "resolved").sum())


def _render_fraud_analysis() -> None:
    """Render fraud analysis page."""
    import streamlit as st

    st.header("Fraud Analysis")

    # Generate sample data
    np.random.seed(42)
    n_transactions = 10000

    data = pd.DataFrame({
        "timestamp": pd.date_range("2023-01-01", periods=n_transactions, freq="min"),
        "amount_ngn": np.random.lognormal(10, 1.5, n_transactions),
        "is_fraud": np.random.choice([True, False], n_transactions, p=[0.036, 0.964]),
        "merchant_category": np.random.choice(["retail", "electronics", "groceries", "entertainment", "travel"], n_transactions),
        "location": np.random.choice(["Lagos", "Abuja", "Port Harcourt", "Kano", "Ibadan"], n_transactions),
        "device_used": np.random.choice(["mobile", "web", "atm", "pos"], n_transactions),
        "sender_persona": np.random.choice(["Trader", "Student", "Salary Earner", "Business Owner"], n_transactions),
    })

    # Fraud rate by merchant category
    st.subheader("Fraud Rate by Merchant Category")
    fraud_by_category = data.groupby("merchant_category")["is_fraud"].mean() * 100
    st.bar_chart(fraud_by_category)

    # Fraud rate by location
    st.subheader("Fraud Rate by Location")
    fraud_by_location = data.groupby("location")["is_fraud"].mean() * 100
    st.bar_chart(fraud_by_location)

    # Fraud rate by device
    st.subheader("Fraud Rate by Device")
    fraud_by_device = data.groupby("device_used")["is_fraud"].mean() * 100
    st.bar_chart(fraud_by_device)

    # Fraud rate by sender persona
    st.subheader("Fraud Rate by Sender Persona")
    fraud_by_persona = data.groupby("sender_persona")["is_fraud"].mean() * 100
    st.bar_chart(fraud_by_persona)

    # Transaction amount distribution
    st.subheader("Transaction Amount Distribution")
    st.histogram(data[data["is_fraud"]]["amount_ngn"], bins=50, label="Fraud", alpha=0.7)
    st.histogram(data[~data["is_fraud"]]["amount_ngn"], bins=50, label="Legitimate", alpha=0.7)
    st.legend()


def _render_model_performance() -> None:
    """Render model performance page."""
    import streamlit as st

    st.header("Model Performance")

    # Model comparison
    st.subheader("Model Comparison")

    model_data = pd.DataFrame({
        "model": ["Logistic Regression", "Random Forest", "XGBoost"],
        "pr_auc": [0.85, 0.92, 0.95],
        "roc_auc": [0.88, 0.94, 0.97],
        "precision": [0.78, 0.85, 0.88],
        "recall": [0.82, 0.88, 0.91],
        "f1": [0.80, 0.86, 0.89],
    })

    st.dataframe(model_data, use_container_width=True)

    # Precision@K
    st.subheader("Precision@K")

    precision_at_k = pd.DataFrame({
        "K": [100, 500, 1000, 5000],
        "Logistic Regression": [0.95, 0.88, 0.82, 0.65],
        "Random Forest": [0.98, 0.92, 0.87, 0.72],
        "XGBoost": [0.99, 0.94, 0.89, 0.75],
    })

    st.dataframe(precision_at_k, use_container_width=True)

    # Threshold analysis
    st.subheader("Threshold Analysis")

    threshold_data = pd.DataFrame({
        "threshold": np.arange(0.1, 0.9, 0.1),
        "precision": [0.45, 0.55, 0.65, 0.75, 0.82, 0.88, 0.92, 0.95],
        "recall": [0.95, 0.90, 0.85, 0.78, 0.70, 0.62, 0.55, 0.48],
        "f1": [0.61, 0.68, 0.74, 0.76, 0.76, 0.73, 0.69, 0.64],
    })

    st.line_chart(threshold_data.set_index("threshold"))

    # Confusion matrix
    st.subheader("Confusion Matrix (Optimal Threshold)")

    cm_data = pd.DataFrame({
        "": ["Actual Negative", "Actual Positive"],
        "Predicted Negative": [9500, 180],
        "Predicted Positive": [140, 180],
    })

    st.dataframe(cm_data, use_container_width=True)
