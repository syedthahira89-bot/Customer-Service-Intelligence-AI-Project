from __future__ import annotations

import os
from pathlib import Path

import pandas as pd
from sqlalchemy import create_engine, text

from etl.wrapup_codes import apply_wrapup_codes, get_wrapup_code_label

DB_URL = os.environ.get(
    "DB_URL",
    "postgresql+psycopg2://postgres:postgres@localhost:5432/customer_service"
)
engine = create_engine(DB_URL)


def generate_trend_summary() -> dict:
    claims = pd.read_sql("SELECT * FROM claims", engine)
    submissions = pd.read_sql("SELECT * FROM submissions", engine)
    interactions = pd.read_sql("SELECT * FROM interactions", engine)
    cases = pd.read_sql("SELECT * FROM cases", engine)

    summary = {
        "total_claims": len(claims),
        "pending_claims": int((claims["claim_status"].astype(str).str.lower() == "pending").sum()),
        "approved_claims": int((claims["claim_status"].astype(str).str.lower() == "approved").sum()),
        "rejected_submissions": int((submissions["submission_status"].astype(str).str.lower() == "rejected").sum()),
        "open_cases": int((cases["case_status"].astype(str).str.lower() == "open").sum()),
        "total_interactions": len(interactions),
    }

    return summary


def write_kpi_snapshot(output_file: str = "analytics_kpis.csv"):
    summary = generate_trend_summary()
    pd.DataFrame([summary]).to_csv(output_file, index=False)
    print(f"Saved KPI snapshot to {output_file}")


def get_wrapup_code_trends(interactions: pd.DataFrame | None = None) -> pd.DataFrame:
    """Count wrap-up codes across interactions to surface the most common customer issues.

    Returns a DataFrame sorted by count (descending) with columns:
    wrapup_code, label, count, percentage.
    """
    if interactions is None:
        interactions = pd.read_sql("SELECT * FROM interactions", engine)

    if interactions.empty:
        return pd.DataFrame(columns=["wrapup_code", "label", "count", "percentage"])

    interactions = apply_wrapup_codes(interactions)

    counts = interactions["wrapup_code"].value_counts()
    total = int(counts.sum())

    trends = pd.DataFrame({
        "wrapup_code": counts.index,
        "count": counts.values,
    })
    trends["label"] = trends["wrapup_code"].apply(get_wrapup_code_label)
    trends["percentage"] = (trends["count"] / total * 100).round(1)
    trends = trends[["wrapup_code", "label", "count", "percentage"]].sort_values("count", ascending=False).reset_index(drop=True)

    return trends


def write_wrapup_code_trends(output_file: str = "wrapup_code_trends.csv"):
    trends = get_wrapup_code_trends()
    trends.to_csv(output_file, index=False)
    print(f"Saved wrap-up code trend summary to {output_file}")


if __name__ == "__main__":
    write_kpi_snapshot()
    write_wrapup_code_trends()
