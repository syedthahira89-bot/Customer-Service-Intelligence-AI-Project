from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Dict

import pandas as pd
from sqlalchemy import create_engine, text

from etl.ingestion_utils import log_error, retry

TARGET_DB_URL = os.environ.get(
    "DB_URL",
    "postgresql+psycopg2://postgres:postgres@localhost:5432/customer_service"
)

TARGET_ENGINE = create_engine(TARGET_DB_URL)


@dataclass
class SourceConfig:
    source_name: str
    connection_string: str
    query: str
    target_table: str
    column_mapping: Dict[str, str]
    primary_key: str
    watermark_column: str | None = None


class QualityCheckError(Exception):
    pass


def build_source_map() -> Dict[str, SourceConfig]:
    return {
        "genesys": SourceConfig(
            source_name="Genesys",
            connection_string=os.environ.get(
                "GENESYS_DB_URL",
                "postgresql+psycopg2://postgres:postgres@localhost:5432/genesys"
            ),
            query="""
                SELECT
                    interaction_id,
                    customer_id,
                    call_reason,
                    call_start_ts AS interaction_timestamp,
                    call_duration_seconds,
                    agent_id,
                    outcome,
                    notes,
                    'Genesys' AS source_system
                FROM public.gen_interactions
            """.strip(),
            target_table="interactions",
            column_mapping={
                "interaction_id": "interaction_id",
                "customer_id": "customer_id",
                "call_reason": "call_reason",
                "interaction_timestamp": "interaction_timestamp",
                "call_duration_seconds": "call_duration_seconds",
                "agent_id": "agent_id",
                "outcome": "outcome",
                "notes": "notes",
                "source_system": "source_system",
            },
            primary_key="interaction_id",
            watermark_column="interaction_timestamp",
        ),
        "juris": SourceConfig(
            source_name="JURIS",
            connection_string=os.environ.get(
                "JURIS_DB_URL",
                "postgresql+psycopg2://postgres:postgres@localhost:5432/juris"
            ),
            query="""
                SELECT
                    claim_id,
                    customer_id,
                    claim_number,
                    claim_status,
                    claim_type,
                    claim_date,
                    adjudication_status,
                    total_amount,
                    claim_date AS interaction_timestamp
                FROM public.claims_detail
            """.strip(),
            target_table="claims",
            column_mapping={
                "claim_id": "claim_id",
                "customer_id": "customer_id",
                "claim_number": "claim_number",
                "claim_status": "claim_status",
                "claim_type": "claim_type",
                "claim_date": "claim_date",
                "adjudication_status": "adjudication_status",
                "total_amount": "total_amount",
            },
            primary_key="claim_id",
            watermark_column="interaction_timestamp",
        ),
        "tams": SourceConfig(
            source_name="TAMS",
            connection_string=os.environ.get(
                "TAMS_DB_URL",
                "postgresql+psycopg2://postgres:postgres@localhost:5432/tams"
            ),
            query="""
                SELECT
                    case_id,
                    claim_id,
                    customer_id,
                    case_status,
                    case_type,
                    assigned_agent_id,
                    priority,
                    created_at,
                    updated_at AS interaction_timestamp
                FROM public.case_master
            """.strip(),
            target_table="cases",
            column_mapping={
                "case_id": "case_id",
                "claim_id": "claim_id",
                "customer_id": "customer_id",
                "case_status": "case_status",
                "case_type": "case_type",
                "assigned_agent_id": "assigned_agent_id",
                "priority": "priority",
                "created_at": "created_at",
                "updated_at": "updated_at",
            },
            primary_key="case_id",
            watermark_column="interaction_timestamp",
        ),
        "sir": SourceConfig(
            source_name="SIR",
            connection_string=os.environ.get(
                "SIR_DB_URL",
                "postgresql+psycopg2://postgres:postgres@localhost:5432/sir"
            ),
            query="""
                SELECT
                    ppw_id,
                    claim_id,
                    customer_id,
                    medical_record_id,
                    ppw_status,
                    ppw_received_date,
                    ppw_review_status,
                    notes,
                    ppw_received_date AS interaction_timestamp
                FROM public.ppw_master
            """.strip(),
            target_table="ppw_records",
            column_mapping={
                "ppw_id": "ppw_id",
                "claim_id": "claim_id",
                "customer_id": "customer_id",
                "medical_record_id": "medical_record_id",
                "ppw_status": "ppw_status",
                "ppw_received_date": "ppw_received_date",
                "ppw_review_status": "ppw_review_status",
                "notes": "notes",
            },
            primary_key="ppw_id",
            watermark_column="interaction_timestamp",
        ),
        "infosource": SourceConfig(
            source_name="Infosource",
            connection_string=os.environ.get(
                "INFOSOURCE_DB_URL",
                "postgresql+psycopg2://postgres:postgres@localhost:5432/infosource"
            ),
            query="""
                SELECT
                    policy_id,
                    vendor_name,
                    policy_category,
                    policy_title,
                    policy_text,
                    effective_date,
                    version_no,
                    effective_date AS interaction_timestamp
                FROM public.vendor_policy_master
            """.strip(),
            target_table="vendor_policies",
            column_mapping={
                "policy_id": "policy_id",
                "vendor_name": "vendor_name",
                "policy_category": "policy_category",
                "policy_title": "policy_title",
                "policy_text": "policy_text",
                "effective_date": "effective_date",
                "version_no": "version_no",
            },
            primary_key="policy_id",
            watermark_column="interaction_timestamp",
        ),
        "smartly": SourceConfig(
            source_name="Smartly",
            connection_string=os.environ.get(
                "SMARTLY_DB_URL",
                "postgresql+psycopg2://postgres:postgres@localhost:5432/smartly"
            ),
            query="""
                SELECT
                    submission_id,
                    claim_id,
                    customer_id,
                    submission_status,
                    submitted_at,
                    document_count,
                    error_code,
                    rejection_reason,
                    submitted_at AS interaction_timestamp
                FROM public.claim_submission_master
            """.strip(),
            target_table="submissions",
            column_mapping={
                "submission_id": "submission_id",
                "claim_id": "claim_id",
                "customer_id": "customer_id",
                "submission_status": "submission_status",
                "submitted_at": "submitted_at",
                "document_count": "document_count",
                "error_code": "error_code",
                "rejection_reason": "rejection_reason",
            },
            primary_key="submission_id",
            watermark_column="interaction_timestamp",
        ),
    }


def get_last_watermark(source_name: str):
    with TARGET_ENGINE.begin() as conn:
        row = conn.execute(
            text(
                "SELECT last_watermark FROM ingestion_watermarks WHERE source_name = :source_name"
            ),
            {"source_name": source_name},
        ).fetchone()
    return row[0] if row else None


def save_last_watermark(source_name: str, watermark_value):
    if watermark_value is None:
        return

    with TARGET_ENGINE.begin() as conn:
        conn.execute(
            text(
                """
                INSERT INTO ingestion_watermarks (source_name, last_watermark, updated_at)
                VALUES (:source_name, :watermark_value, NOW())
                ON CONFLICT (source_name)
                DO UPDATE SET last_watermark = EXCLUDED.last_watermark,
                              updated_at = NOW()
                """
            ),
            {
                "source_name": source_name,
                "watermark_value": watermark_value,
            },
        )


def fetch_source_data(config: SourceConfig, watermark_value=None) -> pd.DataFrame:
    def _fetch():
        source_engine = create_engine(config.connection_string)
        query = config.query

        if config.watermark_column and watermark_value is not None:
            query = f"{query} WHERE {config.watermark_column} > :watermark_value"

        params = {"watermark_value": watermark_value} if watermark_value is not None else {}
        return pd.read_sql_query(text(query), con=source_engine, params=params)

    return retry(_fetch)


def validate_dataframe(df: pd.DataFrame, config: SourceConfig):
    required_columns = list(config.column_mapping.values())
    missing_columns = [col for col in required_columns if col not in df.columns]
    if missing_columns:
        raise QualityCheckError(
            f"Schema validation failed for {config.source_name}: missing columns {missing_columns}"
        )

    if df.empty:
        return df

    pk_values = df[config.primary_key].dropna()
    if pk_values.empty:
        raise QualityCheckError(
            f"Schema validation failed for {config.source_name}: primary key column {config.primary_key} is empty"
        )

    duplicate_pks = df[df[config.primary_key].duplicated(keep=False)]
    if not duplicate_pks.empty:
        raise QualityCheckError(
            f"Quality check failed for {config.source_name}: duplicate primary keys detected"
        )

    null_target_columns = [col for col in required_columns if df[col].isnull().all()]
    if null_target_columns:
        raise QualityCheckError(
            f"Quality check failed for {config.source_name}: all values are null for {null_target_columns}"
        )

    return df


def normalize_columns(df: pd.DataFrame, mapping: Dict[str, str]) -> pd.DataFrame:
    df = df.rename(columns=mapping)
    return df


def upsert_dataframe(df: pd.DataFrame, target_table: str, primary_key: str):
    if df.empty:
        return 0

    columns = list(df.columns)
    column_sql = ", ".join(f'"{column}"' for column in columns)
    value_sql = ", ".join(f":{column}" for column in columns)

    assignments = ", ".join(
        f'"{column}" = EXCLUDED."{column}"'
        for column in columns
        if column != primary_key
    )

    sql = text(
        f"""
        INSERT INTO \"{target_table}\" ({column_sql})
        VALUES ({value_sql})
        ON CONFLICT (\"{primary_key}\")
        DO UPDATE SET {assignments}
        """
    )

    with TARGET_ENGINE.begin() as conn:
        for row in df.to_dict(orient="records"):
            conn.execute(sql, row)

    return len(df)


def run_ingestion() -> Dict[str, int]:
    results: Dict[str, int] = {}

    for name, config in build_source_map().items():
        try:
            watermark_value = get_last_watermark(name)
            source_df = fetch_source_data(config, watermark_value)

            if source_df.empty:
                print(f"[{config.source_name}] no new rows since watermark {watermark_value}")
                results[name] = 0
                continue

            normalized_df = normalize_columns(source_df, config.column_mapping)
            validated_df = validate_dataframe(normalized_df, config)

            loaded_rows = upsert_dataframe(validated_df, config.target_table, config.primary_key)

            watermark_max = validated_df[config.watermark_column].max() if config.watermark_column and config.watermark_column in validated_df.columns else None
            if watermark_max is not None:
                save_last_watermark(name, watermark_max)

            results[name] = loaded_rows
            print(
                f"[{config.source_name}] loaded {loaded_rows} rows into {config.target_table}; updated watermark to {watermark_max}"
            )
        except Exception as exc:
            log_error(
                source_name=name,
                target_table=config.target_table,
                error_type=type(exc).__name__,
                error_message=str(exc),
                raw_payload={"source_name": name, "target_table": config.target_table},
            )
            print(f"[{config.source_name}] ingestion failed: {exc}")
            results[name] = 0

    return results


def main():
    print("Starting production-oriented ingestion for real source systems...")
    run_ingestion()
    print("Ingestion completed.")


if __name__ == "__main__":
    main()
