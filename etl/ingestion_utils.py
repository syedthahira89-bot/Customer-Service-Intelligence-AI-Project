from __future__ import annotations

import json
import os
from datetime import datetime
from typing import Any

from sqlalchemy import create_engine, text

TARGET_DB_URL = os.environ.get(
    "DB_URL",
    "postgresql+psycopg2://postgres:postgres@localhost:5432/customer_service"
)

TARGET_ENGINE = create_engine(TARGET_DB_URL)


def log_error(source_name: str, target_table: str, error_type: str, error_message: str, raw_payload: Any | None = None):
    payload = json.dumps(raw_payload) if raw_payload is not None else None

    with TARGET_ENGINE.begin() as conn:
        conn.execute(
            text(
                """
                INSERT INTO ingestion_errors (source_name, target_table, error_type, error_message, raw_payload, created_at)
                VALUES (:source_name, :target_table, :error_type, :error_message, CAST(:raw_payload AS JSONB), NOW())
                """
            ),
            {
                "source_name": source_name,
                "target_table": target_table,
                "error_type": error_type,
                "error_message": error_message,
                "raw_payload": payload,
            },
        )


def retry(operation, max_retries: int = 3, delay_seconds: int = 2):
    last_error = None
    for attempt in range(1, max_retries + 1):
        try:
            return operation()
        except Exception as exc:
            last_error = exc
            if attempt < max_retries:
                import time
                time.sleep(delay_seconds)
                continue
    raise last_error
