from __future__ import annotations

from typing import Dict, List, Tuple

try:
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.linear_model import LogisticRegression
except Exception:
    TfidfVectorizer = None
    LogisticRegression = None


LABELS = [
    "Claim Status Inquiry",
    "Submission / Documentation Issue",
    "Medical PPW / Documentation Gap",
    "Vendor Policy / Procedure Guidance",
    "Escalation Required",
    "General Service Inquiry",
]

TRAINING_TEXT = {
    "Claim Status Inquiry": [
        "claim pending review status update",
        "customer asks claim status",
        "claim under review follow up",
        "status of claim is pending",
    ],
    "Submission / Documentation Issue": [
        "submission rejected missing documents",
        "claim failed in smartly",
        "submission pending error code",
        "documents missing from submission",
    ],
    "Medical PPW / Documentation Gap": [
        "medical ppw missing documentation",
        "provider records missing",
        "medical review incomplete ppw",
        "ppw pending medical records",
    ],
    "Vendor Policy / Procedure Guidance": [
        "policy guideline vendor procedure",
        "needs vendor rule clarification",
        "eligibility policy review",
        "procedure reference from infosource",
    ],
    "Escalation Required": [
        "high priority open case escalation",
        "urgent escalated customer complaint",
        "requires senior review",
    ],
    "General Service Inquiry": [
        "general customer support question",
        "service inquiry update request",
        "customer asked for help",
        "general operational support",
    ],
}


def _build_profile_text(profile: Dict) -> str:
    parts: List[str] = []

    customer = profile.get("customer", {})
    if customer is not None:
        parts.append(f"customer {customer.get('customer_name', '')} {customer.get('member_id', '')}")

    for key in ["claims", "cases", "submissions", "ppw", "interactions"]:
        df = profile.get(key, None)
        if df is None or df.empty:
            continue

        for col in ["claim_status", "case_status", "submission_status", "ppw_status", "call_reason", "outcome", "priority"]:
            if col in df.columns:
                text_values = [str(x) for x in df[col].dropna() if str(x).strip()]
                parts.extend(text_values)

    policies = profile.get("policies", None)
    if policies is not None and not policies.empty:
        for col in ["policy_title", "policy_text", "policy_category", "vendor_name"]:
            if col in policies.columns:
                text_values = [str(x) for x in policies[col].dropna() if str(x).strip()]
                parts.extend(text_values)

    return " ".join(parts).lower()


def _rule_based_scores(profile: Dict) -> Dict[str, int]:
    scores = {label: 0 for label in LABELS}

    claims = profile.get("claims")
    cases = profile.get("cases")
    submissions = profile.get("submissions")
    ppw = profile.get("ppw")
    interactions = profile.get("interactions")
    policies = profile.get("policies")

    if claims is not None and not claims.empty:
        claim_statuses = [str(x).lower() for x in claims["claim_status"].dropna() if x]
        if any("pending" in s or "review" in s for s in claim_statuses):
            scores["Claim Status Inquiry"] += 2
        if any("approved" in s for s in claim_statuses):
            scores["General Service Inquiry"] += 1

    if submissions is not None and not submissions.empty:
        statuses = [str(x).lower() for x in submissions["submission_status"].dropna() if x]
        if any("rejected" in s or "failed" in s for s in statuses):
            scores["Submission / Documentation Issue"] += 3
        elif any("pending" in s for s in statuses):
            scores["Submission / Documentation Issue"] += 1

    if ppw is not None and not ppw.empty:
        statuses = [str(x).lower() for x in ppw["ppw_status"].dropna() if x]
        if any("missing" in s or "pending" in s for s in statuses):
            scores["Medical PPW / Documentation Gap"] += 3
        elif any("received" in s for s in statuses):
            scores["Medical PPW / Documentation Gap"] += 1

    if cases is not None and not cases.empty:
        cases_status = cases["case_status"].astype(str).str.lower()
        cases_priority = cases["priority"].astype(str).str.lower()
        if ((cases_status == "open") & (cases_priority == "high")).any():
            scores["Escalation Required"] += 2

    if interactions is not None and not interactions.empty:
        call_reasons = [str(x).lower() for x in interactions["call_reason"].dropna() if x]
        vendor_keywords = ["policy", "procedure", "vendor", "eligibility", "guidance"]
        if any(any(keyword in reason for keyword in vendor_keywords) for reason in call_reasons):
            scores["Vendor Policy / Procedure Guidance"] += 2

    if policies is not None and not policies.empty:
        scores["Vendor Policy / Procedure Guidance"] += 1

    return scores


def _ml_predict(profile_text: str) -> Tuple[str, float]:
    if TfidfVectorizer is None or LogisticRegression is None:
        return "General Service Inquiry", 0.0

    training_texts = []
    training_labels = []

    for label, samples in TRAINING_TEXT.items():
        for sample in samples:
            training_texts.append(sample)
            training_labels.append(label)

    vectorizer = TfidfVectorizer(ngram_range=(1, 2))
    x_train = vectorizer.fit_transform(training_texts)
    model = LogisticRegression(max_iter=500)
    model.fit(x_train, training_labels)

    x_new = vectorizer.transform([profile_text])
    predicted_label = model.predict(x_new)[0]

    probability = model.predict_proba(x_new)[0].max()
    return predicted_label, float(probability)


def build_issue_output(profile: Dict) -> Dict[str, object]:
    profile_text = _build_profile_text(profile)
    rule_scores = _rule_based_scores(profile)

    primary_issue = max(rule_scores.items(), key=lambda item: item[1])[0]
    rule_confidence = rule_scores[primary_issue] / max(1, sum(rule_scores.values()))

    ml_issue, ml_confidence = _ml_predict(profile_text)

    if ml_confidence > 0.2:
        if rule_scores[ml_issue] >= rule_scores[primary_issue]:
            primary_issue = ml_issue
            confidence = ml_confidence
        else:
            confidence = max(rule_confidence, ml_confidence * 0.6)
    else:
        confidence = max(rule_confidence, 0.5)

    reasons = []
    if profile.get("submissions") is not None and not profile["submissions"].empty:
        rejected = profile["submissions"][profile["submissions"]["submission_status"].astype(str).str.lower().isin(["rejected", "failed"]) ]
        if not rejected.empty:
            reasons.append("Submission records show rejected or failed submissions.")
    if profile.get("ppw") is not None and not profile["ppw"].empty:
        pending_ppw = profile["ppw"][profile["ppw"]["ppw_status"].astype(str).str.lower().isin(["missing", "pending"]) ]
        if not pending_ppw.empty:
            reasons.append("PPW records indicate missing or pending medical documentation.")
    if profile.get("interactions") is not None and not profile["interactions"].empty:
        vendor_like = profile["interactions"][profile["interactions"]["call_reason"].astype(str).str.lower().str.contains("policy|procedure|vendor|guidance|eligibility", regex=True)]
        if not vendor_like.empty:
            reasons.append("Recent interactions indicate a policy, procedure, or vendor-guidance question.")

    if not reasons:
        reasons = ["No major issue signals were detected from the available records."]

    return {
        "issue_type": primary_issue,
        "confidence": round(min(0.98, max(0.5, confidence)), 2),
        "reasons": reasons,
    }


def get_recommendations(issue_type: str, profile: Dict) -> List[str]:
    recommendations = []

    if issue_type == "Claim Status Inquiry":
        recommendations = [
            "Review the latest claim status in JURIS/TAMS and confirm the expected next milestone.",
            "Check whether the claim requires supporting documentation or a follow-up action.",
            "Provide the customer with a concise status update and a specific next contact date.",
        ]
    elif issue_type == "Submission / Documentation Issue":
        recommendations = [
            "Inspect Smartly submission logs and capture the rejection or error codes.",
            "Request any missing supporting documents and validate the submission after correction.",
            "Escalate to the submission team if the rejection appears to be system-driven rather than customer-driven.",
        ]
    elif issue_type == "Medical PPW / Documentation Gap":
        recommendations = [
            "Review SIR PPW records for missing provider documentation or incomplete records.",
            "Request missing medical information from the provider and track the pending items.",
            "Notify internal teams when a PPW blockage is preventing claim movement.",
        ]
    elif issue_type == "Vendor Policy / Procedure Guidance":
        recommendations = [
            "Look up the relevant vendor policy or procedure from Infosource.",
            "Use the current policy version and effective date when explaining the service response.",
            "Escalate only if the case requires an exception review or vendor coordination.",
        ]
    elif issue_type == "Escalation Required":
        recommendations = [
            "Escalate the case to the appropriate operational or vendor support queue.",
            "Attach timing-sensitive notes, recent customer interactions, and claim status into the escalation record.",
            "Monitor the escalation closely and update the customer with a clear follow-up plan.",
        ]
    else:
        recommendations = [
            "Review recent interactions to confirm the exact customer ask.",
            "Cross-check claim, PPW, and submission information for any missing or conflicting data.",
            "Capture the customer request in a structured ticket for future trend analysis.",
        ]

    policies = profile.get("policies")
    if policies is not None and not policies.empty:
        policies_text = f"Suggested policy reference: {policies.iloc[0]['policy_title']} ({policies.iloc[0]['vendor_name']})."
        recommendations.append(policies_text)

    return recommendations
