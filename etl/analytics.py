from __future__ import annotations

import os
from pathlib import Path

import pandas as pd
from sqlalchemy import create_engine, text

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


if __name__ == "__main__":
    write_kpi_snapshot()
