import os
import re
from pathlib import Path

import pandas as pd
import plotly.express as px
import dash
from dash import dcc, html, Input, Output
from sqlalchemy import create_engine

from etl.recommendations import build_issue_output, get_recommendations, get_wrapup_code_recommendations
from etl.analytics import get_wrapup_code_trends

DB_URL = os.environ.get(
    "DB_URL",
    "postgresql+psycopg2://user:password@localhost:5432/customer_service"
)
engine = create_engine(DB_URL)
DATA_DIR = Path(__file__).resolve().parent.parent / "data"

app = dash.Dash(__name__)


def _load_csv_table(table_name: str) -> pd.DataFrame:
    csv_path = DATA_DIR / f"{table_name}.csv"
    if not csv_path.exists():
        return pd.DataFrame()
    return pd.read_csv(csv_path)


def _query_csv(sql: str) -> pd.DataFrame:
    match = re.search(r"FROM\s+([A-Za-z_]+)", sql, flags=re.IGNORECASE)
    if not match:
        return pd.DataFrame()

    table_name = match.group(1).lower()
    df = _load_csv_table(table_name)

    where_match = re.search(r"WHERE\s+(.+)$", sql, flags=re.IGNORECASE)
    if not where_match or df.empty:
        return df

    where_clause = where_match.group(1)
    customer_id_match = re.search(r"customer_id\s*=\s*'([^']+)'", where_clause, flags=re.IGNORECASE)
    if customer_id_match:
        return df[df["customer_id"] == customer_id_match.group(1)]

    return df


@app.callback(
    Output("page-content", "children"),
    Input("nav", "value"),
    Input("search-btn", "n_clicks"),
    Input("customer-id", "value"),
)
def render_page(selected_page, n_clicks, customer_id):
    if selected_page == "kpis":
        return build_kpi_page()

    if selected_page == "trends":
        return build_trending_topics_page()

    if not customer_id:
        return html.Div("Please enter a customer ID.")

    return build_customer_page(customer_id)


def query_dataframe(sql: str) -> pd.DataFrame:
    try:
        return pd.read_sql(sql, engine)
    except Exception:
        return _query_csv(sql)


def make_card(title: str, value: str, accent: str = "#1f77b4") -> html.Div:
    return html.Div(
        [
            html.Div(title, style={"fontSize": "14px", "color": "#667085", "marginBottom": "6px"}),
            html.Div(value, style={"fontSize": "24px", "fontWeight": "700", "color": accent}),
        ],
        style={
            "backgroundColor": "#ffffff",
            "borderRadius": "12px",
            "padding": "18px",
            "boxShadow": "0 2px 10px rgba(15, 23, 42, 0.05)",
            "flex": "1",
            "marginRight": "12px",
            "minWidth": "180px",
        },
    )


def build_kpi_page():
    df = query_dataframe("SELECT * FROM claims")
    submissions = query_dataframe("SELECT * FROM submissions")
    interactions = query_dataframe("SELECT * FROM interactions")
    cases = query_dataframe("SELECT * FROM cases")

    chart_data = {
        "Metric": ["Claims", "Pending Claims", "Rejected Submissions", "Open Cases", "Interactions"],
        "Value": [
            len(df),
            int((df["claim_status"].astype(str).str.lower() == "pending").sum()),
            int((submissions["submission_status"].astype(str).str.lower() == "rejected").sum()),
            int((cases["case_status"].astype(str).str.lower() == "open").sum()),
            len(interactions),
        ],
    }

    kpi_df = pd.DataFrame(chart_data)

    bar_fig = px.bar(kpi_df, x="Metric", y="Value", title="KPI Summary")

    return html.Div(
        [
            html.H2("KPI Trend Reporting"),
            dcc.Graph(figure=bar_fig),
            html.H3("KPI Snapshot"),
            render_table(kpi_df),
        ],
        style={"padding": "20px"},
    )


def build_trending_topics_page():
    interactions = query_dataframe("SELECT * FROM interactions")
    trends = get_wrapup_code_trends(interactions)

    if trends.empty:
        return html.Div("No interaction data available to compute trends.", style={"padding": "20px"})

    trend_fig = px.bar(
        trends,
        x="label",
        y="count",
        title="Trending Wrap-up Code Topics",
        text="count",
    )
    trend_fig.update_layout(xaxis_title="Topic", yaxis_title="Count")

    top_codes = trends.head(3)
    recommendation_sections = []
    for _, row in top_codes.iterrows():
        recs = get_wrapup_code_recommendations(row["wrapup_code"])
        recommendation_sections.append(
            html.Div(
                [
                    html.H4(f"{row['label']} — {int(row['count'])} occurrences ({row['percentage']}%)"),
                    html.Ul([html.Li(item) for item in recs], style={"paddingLeft": "20px", "lineHeight": "1.8"}),
                ],
                style={"marginBottom": "16px"},
            )
        )

    return html.Div(
        [
            html.H2("Trending Topics & Recommendations"),
            dcc.Graph(figure=trend_fig),
            html.H3("Wrap-up Code Counts"),
            render_table(trends, ["wrapup_code", "label", "count", "percentage"]),
            html.H3("Recommendations to Resolve Top Issues"),
            html.Div(recommendation_sections, style={"backgroundColor": "#ffffff", "borderRadius": "12px", "padding": "20px", "boxShadow": "0 2px 10px rgba(15, 23, 42, 0.05)"}),
        ],
        style={"padding": "20px"},
    )


def build_customer_page(customer_id: str = "CUST001"):
    if not customer_id:
        return html.Div("Please enter a customer ID.")

    customer = query_dataframe(f"SELECT * FROM customers WHERE customer_id = '{customer_id}'")
    if customer.empty:
        return html.Div("No customer found.")

    customer = customer.iloc[0]

    claims = query_dataframe(f"SELECT * FROM claims WHERE customer_id = '{customer_id}'")
    cases = query_dataframe(f"SELECT * FROM cases WHERE customer_id = '{customer_id}'")
    interactions = query_dataframe(f"SELECT * FROM interactions WHERE customer_id = '{customer_id}'")
    ppw = query_dataframe(f"SELECT * FROM ppw_records WHERE customer_id = '{customer_id}'")
    submissions = query_dataframe(f"SELECT * FROM submissions WHERE customer_id = '{customer_id}'")
    policies = query_dataframe("SELECT * FROM vendor_policies LIMIT 10")

    if not interactions.empty:
        interactions["interaction_timestamp"] = pd.to_datetime(interactions["interaction_timestamp"], errors="coerce")

    profile = {
        "customer": customer,
        "claims": claims,
        "cases": cases,
        "interactions": interactions,
        "ppw": ppw,
        "submissions": submissions,
        "policies": policies,
    }

    issue_result = build_issue_output(profile)
    recommendations = get_recommendations(issue_result["issue_type"], profile)

    claim_status_counts = claims["claim_status"].value_counts() if not claims.empty else pd.Series(dtype=int)
    submission_status_counts = submissions["submission_status"].value_counts() if not submissions.empty else pd.Series(dtype=int)
    ppw_status_counts = ppw["ppw_status"].value_counts() if not ppw.empty else pd.Series(dtype=int)
    interaction_source_counts = interactions["source_system"].value_counts() if not interactions.empty else pd.Series(dtype=int)

    summary_cards = html.Div(
        [
            make_card("Customer", customer["customer_name"], "#0f172a"),
            make_card("Claims", str(len(claims)), "#2563eb"),
            make_card("Open Cases", str(len(cases[cases["case_status"].astype(str).str.lower() == "open"])), "#f59e0b"),
            make_card("Pending Submissions", str(len(submissions[submissions["submission_status"].astype(str).str.lower().isin(["pending", "failed", "rejected"])])), "#ef4444"),
            make_card("PPW Issues", str(len(ppw[ppw["ppw_status"].astype(str).str.lower().isin(["missing", "pending"])])), "#10b981"),
        ],
        style={"display": "flex", "flexWrap": "wrap", "marginBottom": "20px"},
    )

    insights_list = [
        html.Li(f"Primary issue: {issue_result['issue_type']} (confidence: {issue_result['confidence']:.0%})"),
        html.Li(f"Claim count: {len(claims)}"),
        html.Li(f"Open cases: {len(cases[cases['case_status'].astype(str).str.lower() == 'open'])}"),
        html.Li(f"Submission gaps: {len(submissions[submissions['submission_status'].astype(str).str.lower().isin(['pending', 'failed', 'rejected'])])}"),
    ]

    insight_panel = html.Div(
        [
            html.H3("Customer Insights"),
            html.Ul(insights_list, style={"paddingLeft": "20px", "lineHeight": "1.8"}),
        ],
        style={
            "backgroundColor": "#ffffff",
            "borderRadius": "12px",
            "padding": "20px",
            "boxShadow": "0 2px 10px rgba(15, 23, 42, 0.05)",
            "marginBottom": "20px",
        },
    )

    recommendation_panel = html.Div(
        [
            html.H3("Recommended Actions"),
            html.Ul(
                [html.Li(item) for item in recommendations],
                style={"paddingLeft": "20px", "lineHeight": "1.8"},
            ),
        ],
        style={
            "backgroundColor": "#ffffff",
            "borderRadius": "12px",
            "padding": "20px",
            "boxShadow": "0 2px 10px rgba(15, 23, 42, 0.05)",
            "marginBottom": "20px",
        },
    )

    claim_status_df = pd.DataFrame({"status": claim_status_counts.index, "count": claim_status_counts.values})
    submission_status_df = pd.DataFrame({"status": submission_status_counts.index, "count": submission_status_counts.values})
    ppw_status_df = pd.DataFrame({"status": ppw_status_counts.index, "count": ppw_status_counts.values})
    interaction_source_df = pd.DataFrame({"source_system": interaction_source_counts.index, "count": interaction_source_counts.values})

    claim_status_fig = px.pie(
        claim_status_df,
        names="status",
        values="count",
        title="Claim Status Distribution",
    )
    submission_status_fig = px.pie(
        submission_status_df,
        names="status",
        values="count",
        title="Submission Status Distribution",
    )
    ppw_status_fig = px.pie(
        ppw_status_df,
        names="status",
        values="count",
        title="PPW Status Distribution",
    )
    interaction_source_fig = px.bar(
        interaction_source_df,
        x="source_system",
        y="count",
        title="Interactions by Source System",
    )

    charts = html.Div(
        [
            html.Div(dcc.Graph(figure=claim_status_fig), style={"width": "32%", "display": "inline-block", "padding": "8px"}),
            html.Div(dcc.Graph(figure=submission_status_fig), style={"width": "32%", "display": "inline-block", "padding": "8px"}),
            html.Div(dcc.Graph(figure=ppw_status_fig), style={"width": "32%", "display": "inline-block", "padding": "8px"}),
            html.Div(dcc.Graph(figure=interaction_source_fig), style={"width": "100%", "display": "inline-block", "padding": "8px"}),
        ],
        style={"marginBottom": "20px"},
    )

    claims_section = html.Div(
        [
            html.H3("Claims"),
            render_table(claims, ["claim_id", "claim_number", "claim_status", "claim_type", "total_amount"]),
        ],
        style={"backgroundColor": "#ffffff", "borderRadius": "12px", "padding": "20px", "boxShadow": "0 2px 10px rgba(15, 23, 42, 0.05)", "marginBottom": "20px"},
    )

    cases_section = html.Div(
        [
            html.H3("Cases"),
            render_table(cases, ["case_id", "case_status", "case_type", "assigned_agent_id", "priority"]),
        ],
        style={"backgroundColor": "#ffffff", "borderRadius": "12px", "padding": "20px", "boxShadow": "0 2px 10px rgba(15, 23, 42, 0.05)", "marginBottom": "20px"},
    )

    interactions_section = html.Div(
        [
            html.H3("Recent Interactions"),
            render_table(
                interactions[["interaction_id", "source_system", "interaction_type", "interaction_timestamp", "call_reason", "outcome"]].sort_values("interaction_timestamp", ascending=False),
                ["interaction_id", "source_system", "interaction_type", "interaction_timestamp", "call_reason", "outcome"],
            ),
        ],
        style={"backgroundColor": "#ffffff", "borderRadius": "12px", "padding": "20px", "boxShadow": "0 2px 10px rgba(15, 23, 42, 0.05)", "marginBottom": "20px"},
    )

    policies_section = html.Div(
        [
            html.H3("Relevant Policy References"),
            render_table(policies[["policy_title", "vendor_name", "policy_category", "policy_text"]], ["policy_title", "vendor_name", "policy_category", "policy_text"]),
        ],
        style={"backgroundColor": "#ffffff", "borderRadius": "12px", "padding": "20px", "boxShadow": "0 2px 10px rgba(15, 23, 42, 0.05)", "marginBottom": "20px"},
    )

    return html.Div(
        [
            html.H3(f"{customer['customer_name']} ({customer_id})", style={"marginBottom": "16px"}),
            html.Div(
                [
                    html.Div(f"Member ID: {customer['member_id']}", style={"marginRight": "20px"}),
                    html.Div(f"Phone: {customer['phone']}", style={"marginRight": "20px"}),
                    html.Div(f"Email: {customer['email']}", style={"marginRight": "20px"}),
                ],
                style={"display": "flex", "flexWrap": "wrap", "marginBottom": "20px"},
            ),
            summary_cards,
            html.Div(
                [
                    html.Div(insight_panel, style={"width": "49%", "display": "inline-block", "verticalAlign": "top", "paddingRight": "10px"}),
                    html.Div(recommendation_panel, style={"width": "49%", "display": "inline-block", "verticalAlign": "top", "paddingLeft": "10px"}),
                ],
                style={"marginBottom": "20px"},
            ),
            charts,
            claims_section,
            cases_section,
            interactions_section,
            policies_section,
        ],
        style={"padding": "0 24px 24px 24px"},
    )


def render_table(df: pd.DataFrame, columns=None):
    if df.empty:
        return html.Div("No records found.")

    cols = columns or list(df.columns)
    table_header = html.Tr([html.Th(col, style={"textAlign": "left", "padding": "8px"}) for col in cols])
    rows = []
    for _, row in df[cols].iterrows():
        rows.append(
            html.Tr(
                [html.Td(str(row[col]), style={"padding": "8px", "borderBottom": "1px solid #edf2f7"}) for col in cols]
            )
        )

    return html.Table(
        [
            html.Thead(html.Tr([html.Th(col, style={"textAlign": "left", "padding": "8px"}) for col in cols])),
            html.Tbody(rows),
        ],
        style={
            "width": "100%",
            "borderCollapse": "collapse",
            "backgroundColor": "#ffffff",
            "borderRadius": "12px",
            "overflow": "hidden",
        },
    )




app.layout = html.Div(
    [
        html.Div(
            [
                html.H1("Customer Service Intelligence Dashboard", style={"margin": "0", "color": "#0f172a"}),
                html.P("Unified view of customer asks, claims, PPW, submissions, policies, and agent actions.", style={"marginTop": "6px", "color": "#475467"}),
            ],
            style={"padding": "20px 24px 0 24px"},
        ),
        html.Div(
            [
                dcc.Input(
                    id="customer-id",
                    type="text",
                    value="CUST001",
                    placeholder="Enter customer ID",
                    style={"width": "320px", "padding": "10px 12px", "borderRadius": "10px", "border": "1px solid #d0d5dd", "marginRight": "10px"},
                ),
                html.Button("Search", id="search-btn", n_clicks=0, style={"padding": "10px 18px", "borderRadius": "10px", "border": "none", "backgroundColor": "#2563eb", "color": "#ffffff", "fontWeight": "600"}),
            ],
            style={"padding": "0 24px 20px 24px"},
        ),
        html.Div(
            [
                dcc.RadioItems(
                    id="nav",
                    options=[
                        {"label": "Customer View", "value": "customer"},
                        {"label": "KPI Trends", "value": "kpis"},
                        {"label": "Trending Topics", "value": "trends"},
                    ],
                    value="customer",
                    inline=True,
                    style={"padding": "0 24px 20px 24px"},
                ),
            ]
        ),
        html.Div(
            id="page-content",
            style={"padding": "0 24px 24px 24px"},
        ),
    ],
    style={"backgroundColor": "#f5f7fb", "minHeight": "100vh", "fontFamily": "Arial, sans-serif"},
)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8050, debug=True)
