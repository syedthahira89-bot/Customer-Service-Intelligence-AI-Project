import os
from pathlib import Path

import pandas as pd
from sqlalchemy import create_engine

DB_URL = os.environ.get(
    "DB_URL",
    "postgresql+psycopg2://user:password@localhost:5432/customer_service"
)
engine = create_engine(DB_URL)
DATA_DIR = Path(__file__).resolve().parent.parent / "data"


def load_csv(file_name: str) -> pd.DataFrame:
    file_path = DATA_DIR / file_name
    if not file_path.exists():
        raise FileNotFoundError(f"Missing data file: {file_path}")
    return pd.read_csv(file_path)


def clean_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df = df.fillna("")
    return df


def upsert(df: pd.DataFrame, table_name: str):
    df.to_sql(
        table_name,
        engine,
        if_exists="append",
        index=False,
    )


def process_customers():
    df = clean_dataframe(load_csv("customers.csv"))
    upsert(df, "customers")


def process_claims():
    df = clean_dataframe(load_csv("claims.csv"))
    upsert(df, "claims")


def process_cases():
    df = clean_dataframe(load_csv("cases.csv"))
    upsert(df, "cases")


def process_interactions():
    df = clean_dataframe(load_csv("interactions.csv"))
    upsert(df, "interactions")


def process_vendor_policies():
    df = clean_dataframe(load_csv("vendor_policies.csv"))
    upsert(df, "vendor_policies")


def process_ppw_records():
    df = clean_dataframe(load_csv("ppw_records.csv"))
    upsert(df, "ppw_records")


def process_submissions():
    df = clean_dataframe(load_csv("submissions.csv"))
    upsert(df, "submissions")


def main():
    process_customers()
    process_claims()
    process_cases()
    process_interactions()
    process_vendor_policies()
    process_ppw_records()
    process_submissions()
    print("ETL pipeline completed successfully.")


if __name__ == "__main__":
    main()
