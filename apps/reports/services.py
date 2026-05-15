from decimal import Decimal

from apps.analytics.services import update_readiness_analytics
from apps.reports.models import FinalReport
from apps.reports.resources import recommend_resources


CONTRADICTION_TERMS = {
    "clear reasoning path": {"communication structure", "reasoning clarity"},
    "practical details included": {"practical implementation detail"},
    "baseline prompt coverage": {"incomplete submission"},
}

REPETITIVE_TOPICS = {
    "structure": {"structured communication", "communication structure", "clear structure"},
    "clarity": {"clarity", "clear articulation", "clear communication"},
    "process": {"process discipline", "process-oriented thinking", "process oriented"},
}


def _timeline_for_score(score):
    if score >= 85:
        return "Ready for a confident simulation retry within 3-5 days."
    if score >= 70:
        return "Likely ready after 1-2 weeks of targeted practice."
    if score >= 50:
        return "Plan for 3-4 weeks of structured preparation before retrying."
    return "Build foundations for 4-6 weeks before attempting a full retry."


def _retry_recommendation_for_score(score):
    if score < 50:
        return "Core fundamentals need significant improvement before retrying."
    if score < 70:
        return "Focus on structured communication and foundational improvement before the next simulation."
    if score < 85:
        return "Solid progress demonstrated. A short focused revision cycle is recommended."
    if score < 91:
        return "High readiness demonstrated with good consistency across rounds."
    return "Exceptional readiness demonstrated with rare consistency across rounds."


def _clean_insights(items, limit):
    cleaned = []
    seen = set()
    used_topics = set()
    for item in items:
        text = str(item or "").strip()
        if not text:
            continue
        normalized = " ".join(text.lower().split())
        if normalized in seen:
            continue
        topic = next((name for name, terms in REPETITIVE_TOPICS.items() if any(term in normalized for term in terms)), "")
        if topic and topic in used_topics:
            continue
        if topic:
            used_topics.add(topic)
        seen.add(normalized)
        cleaned.append(text[:180])
        if len(cleaned) >= limit:
            break
    return cleaned


def _remove_contradictions(strengths, weaknesses):
    weakness_text = {item.lower() for item in weaknesses}
    filtered_strengths = []
    for strength in strengths:
        blocked_terms = CONTRADICTION_TERMS.get(strength.lower(), set())
        if blocked_terms and any(term in weakness_text for term in blocked_terms):
            continue
        filtered_strengths.append(strength)
    return filtered_strengths or strengths[:1]


def _company_focus(company):
    name = company.name.lower()
    if "mercedes" in name:
        return "engineering rigor, precision, systems thinking, and technical depth"
    if "infosys" in name:
        return "process discipline, clear communication, dependable delivery, and client-ready fundamentals"
    return company.benchmark_description.lower()


def _company_alignment(simulation, readiness, strengths, weaknesses):
    if readiness >= simulation.company.pass_threshold:
        posture = "provided enough evidence for"
    else:
        posture = "did not yet provide enough evidence for"
    gap = weaknesses[0] if weaknesses else "sustained interview evidence"
    signal = strengths[0] if strengths else "completion across the evaluated rounds"
    return (
        f"The completed answers {posture} {simulation.company.name}'s expectations around "
        f"{_company_focus(simulation.company)}. The clearest supporting signal was {signal}; "
        f"the main gap to address is {gap}."
    )


def _analysis_summary(readiness, results, strengths, weaknesses):
    completed = len(results)
    strongest = strengths[0] if strengths else "consistent participation"
    weakest = weaknesses[0] if weaknesses else "maintaining consistency under time pressure"
    if readiness >= 91:
        quality = "rarely strong"
    elif readiness >= 85:
        quality = "high-readiness"
    elif readiness >= 70:
        quality = "solid"
    elif readiness >= 55:
        quality = "developing"
    else:
        quality = "limited"
    return (
        f"Round Forge reviewed {completed} completed round evaluation(s). Overall readiness is {readiness}%, a {quality} signal, "
        f"with the clearest positive signal in {strongest} and the highest-leverage improvement area in {weakest}."
    )


def build_final_report(simulation):
    results = list(simulation.round_results.select_related("round").order_by("round__round_order"))
    if not results:
        readiness = Decimal("0")
    else:
        readiness = (sum((result.score for result in results), Decimal("0")) / Decimal(len(results))).quantize(Decimal("0.01"))

    strengths = []
    weaknesses = []
    roadmap = []
    round_analysis = []

    for result in results:
        strengths.extend(result.strengths or [])
        weaknesses.extend(result.weaknesses or [])
        roadmap.extend(result.improvement_roadmap or [])
        round_analysis.append(
            {
                "round": result.round.name,
                "decision": result.get_decision_display(),
                "score": float(result.score),
                "feedback": result.feedback,
                "scores": result.detailed_scores,
            }
        )

    strengths = _clean_insights(strengths, 8)
    weaknesses = _clean_insights(weaknesses, 8)
    strengths = _remove_contradictions(strengths, weaknesses)
    roadmap = _clean_insights(roadmap, 10)
    retry = _retry_recommendation_for_score(readiness)

    report, _ = FinalReport.objects.update_or_create(
        simulation=simulation,
        defaults={
            "user": simulation.user,
            "readiness_percent": readiness,
            "round_analysis": round_analysis,
            "strengths": strengths or ["Consistent participation across the simulated process."],
            "weaknesses": weaknesses or ["No critical weakness detected from the completed rounds."],
            "company_alignment": _company_alignment(simulation, readiness, strengths, weaknesses),
            "ai_generated_analysis": _analysis_summary(readiness, results, strengths, weaknesses),
            "improvement_roadmap": roadmap or ["Repeat timed answers, revise fundamentals, and compare responses with expected signals."],
            "recommended_resources": recommend_resources(weaknesses),
            "retry_recommendation": retry,
            "readiness_timeline": _timeline_for_score(readiness),
        },
    )
    update_readiness_analytics(simulation.user, simulation.company)
    return report
