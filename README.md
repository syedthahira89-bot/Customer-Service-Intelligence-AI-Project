sure# Customer Service Dashboard

## About the Developer

I’m a data and AI-focused professional building practical, business-impacting solutions that turn raw operational data into actionable insights. This project reflects my interest in customer service intelligence, automation, and analytics-driven decision support.

## LinkedIn

Connect with me on LinkedIn: https://www.linkedin.com/in/thahira-syed-2827ba426

## GitHub

Explore more projects and code: https://github.com/yourusername

This project provides a starter architecture for a centralized customer service dashboard that combines six data sources:
- Genesys
- JURIS
- TAMS
- SIR
- Infosource
- Smartly

It includes:
- SQL schema for core entities
- Python ETL pipeline to load source data into PostgreSQL
- Dash dashboard with charts, customer insights, AI-assisted issue classification, and recommended actions
- Wrap-up code trending topics: interactions are auto-classified into standardized reason codes (with new codes learned and persisted for previously unseen topics) so the dashboard can surface the most common customer issues and recommended actions to resolve them

## Folder structure

- `sql/schema.sql` - database schema
- `etl/pipeline.py` - ETL pipeline
- `etl/wrapup_codes.py` - wrap-up code classification and dynamic code learning
- `etl/analytics.py` - KPI and wrap-up code trend aggregation
- `etl/wrapup_recommendations.py` - recommended actions for trending wrap-up code topics
- `etl/issue_classifier.py` - rule-based + ML customer issue classification and recommended actions
- `dashboard/app.py` - Dash dashboard
- `data/` - sample data files
- `tests/` - unit tests (pytest)
- `requirements.txt` - Python dependencies

## Setup

1. Start PostgreSQL with Docker Compose:
   ```bash
   docker compose up -d
   ```
2. Set the `DB_URL` environment variable for the database connection:
   ```bash
   export DB_URL="postgresql+psycopg2://postgres:postgres@localhost:5432/customer_service"
   ```
3. Run the schema:
   ```sql
   \i sql/schema.sql
   ```
4. Run ETL to load sample or source data:
   ```bash
   python etl/pipeline.py
   ```
5. Run the Dash app:
   ```bash
   python dashboard/app.py
   ```

## Running tests

```bash
pip install -r requirements.txt
python -m pytest tests -v
```

Tests cover wrap-up code classification/learning ([tests/test_wrapup_codes.py](tests/test_wrapup_codes.py)) and recommendation generation ([tests/test_wrapup_recommendations.py](tests/test_wrapup_recommendations.py)). CI runs the same suite automatically on push/PR via `.github/workflows/python-tests.yml`.

## Docker Compose

The project includes a PostgreSQL container definition in `docker-compose.yml`.

```bash
docker compose up -d
```

## Connect to real systems

The project also includes a connector starter at `etl/connect_real_sources.py` for mapping the six source systems:
- Genesys
- JURIS
- TAMS
- SIR
- Infosource
- Smartly

Update the connection strings and SQL queries in that file to match your real database/table structure.

## Production-ready source mappings

The source connector file now includes concrete SQL queries and target table mappings for the six source systems.

### 1) Genesys
- Source table: `public.gen_interactions`
- Target table: `interactions`
- Key fields: `interaction_id`, `customer_id`, `call_reason`, `interaction_timestamp`, `call_duration_seconds`, `agent_id`, `outcome`, `notes`
- Ingestion flow: extract call metadata and latency/notes, then standardize into the centralized `interactions` table.

### 2) JURIS
- Source table: `public.claims_detail`
- Target table: `claims`
- Key fields: `claim_id`, `customer_id`, `claim_number`, `claim_status`, `claim_type`, `claim_date`, `adjudication_status`, `total_amount`
- Ingestion flow: load claim status, amount, and claim lifecycle information into the normalized `claims` table.

### 3) TAMS
- Source table: `public.case_master`
- Target table: `cases`
- Key fields: `case_id`, `claim_id`, `customer_id`, `case_status`, `case_type`, `assigned_agent_id`, `priority`
- Ingestion flow: load each case record as a case entity with linkages back to the claim and customer.

### 4) SIR
- Source table: `public.ppw_master`
- Target table: `ppw_records`
- Key fields: `ppw_id`, `claim_id`, `customer_id`, `medical_record_id`, `ppw_status`, `ppw_received_date`, `ppw_review_status`
- Ingestion flow: stage PPW and medical review records into the normalized PPW table so the dashboard can show missing or incomplete medical documentation.

### 5) Infosource
- Source table: `public.vendor_policy_master`
- Target table: `vendor_policies`
- Key fields: `policy_id`, `vendor_name`, `policy_category`, `policy_title`, `policy_text`, `effective_date`, `version_no`
- Ingestion flow: load policy references and procedural guidance that the dashboard can show to agents when resolving a case.

### 6) Smartly
- Source table: `public.claim_submission_master`
- Target table: `submissions`
- Key fields: `submission_id`, `claim_id`, `customer_id`, `submission_status`, `submitted_at`, `document_count`, `error_code`, `rejection_reason`
- Ingestion flow: load claim submission activity so the dashboard can surface rejected or incomplete submissions.

## Production ingestion flow

1. Extract raw data from each source database using the configured SQL query.
2. Normalize the source schema into the curated target tables defined in `sql/schema.sql`.
3. Load rows into the target PostgreSQL database.
4. Run duplicate checks and incremental load logic using the source system primary keys.
5. Publish the curated tables to the Dash dashboard and analytics layer.

In a real production deployment, you should add:
- watermark tracking for incremental loads
- record-level deduplication and upsert logic
- schema validation and row-quality checks
- retries and dead-letter handling for failed loads
- source-specific partitioning or archival policies

## Dashboard features

- Customer search by ID
- Unified customer summary
- Claim, case, interaction, PPW, and submission views
- Charts for claim status, submission status, PPW status, and source-system activity
- AI-assisted issue classification
- Recommended actions for the current customer issue

## AI recommendation engine

The rule-based + ML classifier lives in `etl/issue_classifier.py`.

- Rule-based logic uses claim, submission, PPW, case, and interaction signals
- ML layer uses a trained text classifier for issue type prediction
- Recommendations are generated based on the detected issue type

## Run ETL for real sources

You can update `etl/connect_real_sources.py` and then run:

```bash
python etl/connect_real_sources.py
```

## GitHub

This repository includes a `LICENSE`, GitHub issue templates, a pull request template, and a basic CI workflow for Python.

### Quick publish steps

```bash
git init
git add .
git commit -m "Initial commit"
git branch -M main
git remote add origin https://github.com/YOUR_USERNAME/Customer-Service-Intelligence-AI-Project.git
git push -u origin main
```

### Optional: create the repo from the CLI

```bash
gh auth login
gh repo create Customer-Service-Intelligence-AI-Project --public --source=. --remote=origin --push
```
