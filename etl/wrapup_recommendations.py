"""Recommended actions to resolve trending wrap-up code topics."""
from __future__ import annotations

from typing import Dict, List

from etl.wrapup_codes import get_wrapup_code_label

# Recommendations to resolve the most common trending wrap-up code topics.
WRAPUP_CODE_RECOMMENDATIONS: Dict[str, List[str]] = {
    "CLAIM_STATUS": [
        "Publish self-service claim status tracking to reduce repeat status-check calls.",
        "Set up proactive status update notifications at key claim milestones.",
        "Review the most frequently delayed claim stages and address the bottleneck.",
    ],
    "SUBMISSION_ISSUE": [
        "Analyze recurring submission error codes and fix the root cause in the submission workflow.",
        "Provide clearer document checklists upfront to reduce rejected/missing-document submissions.",
        "Add real-time validation on submission forms to catch errors before they reach the queue.",
    ],
    "PPW_GAP": [
        "Coordinate directly with providers to close recurring medical documentation gaps.",
        "Automate reminders to providers/customers when PPW records are outstanding.",
        "Track top providers with repeated PPW gaps and escalate the relationship issue.",
    ],
    "POLICY_GUIDANCE": [
        "Publish an updated, easy-to-find FAQ for the most frequently asked policy questions.",
        "Share recurring policy-clarification themes with the vendor policy team for review.",
        "Train agents on the most commonly misunderstood policy areas.",
    ],
    "ESCALATION": [
        "Identify the top drivers of escalations and address them before they reach agents.",
        "Create a fast-track escalation queue for the most frequent high-priority issue types.",
        "Review escalation resolution times and staff accordingly during peak periods.",
    ],
    "BILLING_ISSUE": [
        "Audit recurring billing/payment error patterns and fix the underlying billing logic.",
        "Provide agents with a quick-reference guide for the most common billing disputes.",
        "Add self-service payment history/invoice lookup to reduce repeat billing calls.",
    ],
    "TECHNICAL_ISSUE": [
        "Log and prioritize recurring portal/technical issues with the engineering team.",
        "Publish known-issue status updates so customers don't need to call in for the same bug.",
        "Add better in-app error messages to reduce confusion-driven contacts.",
    ],
    "GENERAL_INQUIRY": [
        "Review general inquiry notes to identify emerging topics not yet covered by a specific code.",
        "Consider adding a new wrap-up code if a distinct pattern emerges from general inquiries.",
    ],
}


def get_wrapup_code_recommendations(wrapup_code: str) -> List[str]:
    """Recommended actions to resolve the customer issues behind a wrap-up code trend."""
    if wrapup_code in WRAPUP_CODE_RECOMMENDATIONS:
        return WRAPUP_CODE_RECOMMENDATIONS[wrapup_code]

    # Newly learned/dynamic wrap-up code: generate generic, topic-specific guidance.
    label = get_wrapup_code_label(wrapup_code)
    return [
        f"Review recurring '{label}' interactions to identify the root cause.",
        f"Create a knowledge base article or FAQ entry for '{label}' to speed up resolution.",
        f"Monitor '{label}' volume over time to decide if it needs a dedicated process or team.",
    ]
