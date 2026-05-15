import json
import re
from collections import Counter

from django.conf import settings


REQUIRED_KEYS = {
    "score",
    "decision",
    "detailed_scores",
    "strengths",
    "weaknesses",
    "feedback",
    "improvement_roadmap",
    "company_benchmark",
}

GENERIC_PHRASES = {
    "i will do my best",
    "i am a hard worker",
    "good communication",
    "team player",
    "process oriented",
    "strong alignment",
    "values communication",
    "i am passionate",
    "i can handle pressure",
    "i will learn",
}

NON_ATTEMPT_PHRASES = {
    "i don't know",
    "i dont know",
    "no idea",
    "not sure",
    "can't answer",
    "cannot answer",
    "skip",
    "n/a",
    "asdf",
    "lorem ipsum",
}

URL_RE = re.compile(r"https?://\S+|www\.\S+", flags=re.IGNORECASE)

EXAMPLE_MARKERS = {
    "for example",
    "for instance",
    "in my project",
    "i built",
    "i implemented",
    "when i",
    "we used",
    "one case",
    "scenario",
    "example",
}
REASONING_MARKERS = {
    "because",
    "therefore",
    "so that",
    "tradeoff",
    "trade-off",
    "root cause",
    "constraint",
    "risk",
    "assumption",
    "edge case",
    "if",
    "then",
}
PRACTICAL_MARKERS = {
    "test",
    "metric",
    "monitor",
    "deploy",
    "debug",
    "rollback",
    "latency",
    "scale",
    "complexity",
    "database",
    "api",
    "index",
    "cache",
    "queue",
    "hash",
    "set",
    "map",
    "o(n)",
    "duplicate",
    "stream",
    "memory",
    "throughput",
    "backpressure",
}
STRUCTURE_MARKERS = {"first", "second", "finally", "step", "approach", "plan", "before", "after", "then", "next"}
VAGUE_WORDS = {"things", "stuff", "something", "good", "better", "nice", "proper", "various", "etc"}


def _strip_json_fence(text):
    text = (text or "").strip()
    text = re.sub(r"^```(?:json)?", "", text, flags=re.IGNORECASE).strip()
    text = re.sub(r"```$", "", text).strip()
    match = re.search(r"\{.*\}", text, flags=re.DOTALL)
    return match.group(0) if match else text


def _bounded(value, lower=0, upper=100):
    return max(lower, min(upper, value))


def _count_markers(text, markers):
    return sum(1 for marker in markers if marker in text)


def _count_non_attempts(text):
    return sum(1 for marker in NON_ATTEMPT_PHRASES if re.search(rf"(^|\W){re.escape(marker)}($|\W)", text))


def _answer_features(answers):
    joined = " ".join(answer.answer_text for answer in answers).strip()
    lowered = joined.lower()
    without_urls = URL_RE.sub(" ", lowered)
    words = re.findall(r"[a-zA-Z0-9+#.]+", lowered)
    content_words = re.findall(r"[a-zA-Z0-9+#.]+", without_urls)
    sentences = [item.strip() for item in re.split(r"[.!?\n]+", lowered) if item.strip()]
    starts = [sentence.split(" ", 3)[0] for sentence in sentences if sentence]
    repeated_starts = sum(count - 1 for count in Counter(starts).values() if count > 1)
    unique_ratio = len(set(words)) / len(words) if words else 0
    vague_hits = sum(1 for word in words if word in VAGUE_WORDS)
    generic_hits = _count_markers(lowered, GENERIC_PHRASES)
    example_hits = _count_markers(lowered, EXAMPLE_MARKERS)
    reasoning_hits = _count_markers(lowered, REASONING_MARKERS)
    practical_hits = _count_markers(lowered, PRACTICAL_MARKERS)
    structure_hits = _count_markers(lowered, STRUCTURE_MARKERS)
    numeric_hits = len(re.findall(r"\b\d+(?:\.\d+)?%?\b", lowered))
    url_hits = len(URL_RE.findall(lowered))
    repeated_token_hits = sum(count - 1 for count in Counter(words).values() if count >= 4)
    return {
        "joined": joined,
        "lowered": lowered,
        "word_count": len(words),
        "content_word_count": len(content_words),
        "unique_ratio": unique_ratio,
        "vague_hits": vague_hits,
        "generic_hits": generic_hits,
        "non_attempt_hits": _count_non_attempts(lowered),
        "example_hits": example_hits,
        "reasoning_hits": reasoning_hits,
        "practical_hits": practical_hits,
        "structure_hits": structure_hits,
        "numeric_hits": numeric_hits,
        "url_hits": url_hits,
        "repeated_token_hits": repeated_token_hits,
        "repeated_starts": repeated_starts,
    }


def _invalid_answer_reason(features):
    text = features["lowered"].strip()
    if not text:
        return "No substantive answer text was submitted."
    if features["url_hits"] and features["content_word_count"] <= 3:
        return "The response was URL-only and did not attempt the interview prompt."
    if features["non_attempt_hits"]:
        return "The response explicitly declined or skipped the prompt."
    if features["word_count"] < 8 and not (features["reasoning_hits"] and features["practical_hits"]):
        return "The response was too short to show reasoning or interview readiness."
    if features["word_count"] >= 8 and features["unique_ratio"] < 0.25:
        return "The response repeated filler text instead of answering the prompt."
    if features["repeated_token_hits"] >= 8 and features["reasoning_hits"] == 0:
        return "The response was repetitive and did not provide meaningful reasoning."
    if not re.search(r"[aeiou]", text) and features["word_count"] >= 4:
        return "The response appeared to be nonsensical text rather than an interview answer."
    return ""


def _evidence_score(features, interview_round):
    invalid_reason = _invalid_answer_reason(features)
    if invalid_reason:
        if features["url_hits"] or features["non_attempt_hits"]:
            return 5
        return 12

    word_count = features["word_count"]
    if word_count < 35:
        score = 38
    elif word_count < 70:
        score = 50
    elif word_count < 120:
        score = 59
    elif word_count < 220:
        score = 66
    else:
        score = 70

    score += min(features["reasoning_hits"], 5) * 3
    score += min(features["example_hits"], 3) * 4
    score += min(features["practical_hits"], 7) * 2.1
    score += min(features["structure_hits"], 4) * 1.5
    score += min(features["numeric_hits"], 3) * 2

    if features["unique_ratio"] < 0.42 and word_count >= 60:
        score -= 6
    if features["example_hits"] == 0:
        score -= 8
    if features["reasoning_hits"] == 0:
        score -= 7
    if features["generic_hits"]:
        score -= min(12, features["generic_hits"] * 4)
    if features["vague_hits"] >= 4:
        score -= min(10, features["vague_hits"])
    if features["repeated_starts"] >= 2:
        score -= min(8, features["repeated_starts"] * 2)
    if interview_round.round_type in {"dsa", "system_design", "technical"} and features["practical_hits"] < 2:
        score -= 5
    if interview_round.round_type in {"dsa", "system_design", "technical"} and features["practical_hits"] >= 4 and features["reasoning_hits"] >= 2:
        score += 5

    return round(_bounded(score, 0, 96), 2)


def _evidence_cap(features):
    if _invalid_answer_reason(features):
        return 15
    if features["word_count"] < 45 or features["reasoning_hits"] == 0:
        return 55
    if features["example_hits"] == 0 or features["practical_hits"] == 0:
        if features["practical_hits"] >= 4 and features["reasoning_hits"] >= 2:
            return 82
        return 70
    if features["word_count"] < 90 and features["specificity_score"] < 5:
        return 82
    if features["reasoning_hits"] >= 3 and features["example_hits"] >= 2 and features["practical_hits"] >= 3:
        return 95
    return 91


def _calibrate_score(raw_score, features, interview_round):
    features = dict(features)
    features["specificity_score"] = features["example_hits"] + features["numeric_hits"] + min(features["practical_hits"], 3)
    evidence = _evidence_score(features, interview_round)
    if _invalid_answer_reason(features):
        return min(evidence, _evidence_cap(features))
    blended = (float(raw_score) * 0.60) + (evidence * 0.40)
    return round(_bounded(blended, 0, _evidence_cap(features)), 2)


def _score_band(score):
    if score < 55:
        return "weak"
    if score < 70:
        return "average"
    if score < 82:
        return "good"
    if score < 91:
        return "excellent"
    return "exceptional"


def _normalise_detail_scores(detail_scores, calibrated_score):
    defaults = {
        "technical_depth": calibrated_score,
        "communication": calibrated_score,
        "logic": calibrated_score,
        "clarity": calibrated_score,
        "confidence": calibrated_score,
        "company_alignment": calibrated_score,
    }
    cleaned = {}
    for key, default in defaults.items():
        value = detail_scores.get(key, default) if isinstance(detail_scores, dict) else default
        cleaned[key] = round(_bounded((float(value) * 0.50) + (calibrated_score * 0.50), 0, 96), 2)
    return cleaned


def _quality_word(score):
    if score >= 91:
        return "exceptional"
    if score >= 82:
        return "excellent"
    if score >= 70:
        return "solid"
    if score >= 55:
        return "developing"
    return "limited"


def _clean_list_items(items, score):
    blocked = {"excellent", "exceptional", "elite", "outstanding", "strong alignment", "process-oriented"}
    cleaned = []
    for item in items:
        text = str(item or "").strip()
        if not text:
            continue
        lowered = text.lower()
        if score < 82:
            for word in blocked:
                lowered = lowered.replace(word, "clear" if word in {"excellent", "exceptional", "elite", "outstanding"} else "relevant")
            text = lowered.capitalize()
        if text not in cleaned:
            cleaned.append(text[:160])
    return cleaned[:6]


def _normalise_payload(payload, company, interview_round, answers):
    features = _answer_features(answers)
    raw_score = max(0, min(100, float(payload.get("score", 0))))
    calibrated_score = _calibrate_score(raw_score, features, interview_round)
    invalid_reason = _invalid_answer_reason(features)
    cleaned = {
        "score": calibrated_score,
        "decision": payload.get("decision", "failed"),
        "detailed_scores": _normalise_detail_scores(payload.get("detailed_scores") or {}, calibrated_score),
        "strengths": [] if invalid_reason else _clean_list_items(payload.get("strengths") or [], calibrated_score),
        "weaknesses": [invalid_reason] if invalid_reason else _clean_list_items(payload.get("weaknesses") or [], calibrated_score),
        "feedback": payload.get("feedback") or "Evaluation completed.",
        "improvement_roadmap": payload.get("improvement_roadmap") or [],
        "company_benchmark": payload.get("company_benchmark")
        or f"Measured against {company.name}'s benchmark: {company.benchmark_description}",
    }
    if invalid_reason:
        cleaned["feedback"] = f"Submission could not be evaluated as a valid interview answer. {invalid_reason}"
        cleaned["improvement_roadmap"] = ["Submit a direct answer that explains approach, reasoning, and one concrete example."]
        cleaned["company_benchmark"] = f"The response did not provide enough evidence for {company.name}'s benchmark."
    elif calibrated_score < 82:
        cleaned["feedback"] = re.sub(r"\b(exceptional|excellent|elite|outstanding)\b", _quality_word(calibrated_score), cleaned["feedback"], flags=re.IGNORECASE)
    cleaned["decision"] = "passed" if calibrated_score >= float(interview_round.pass_score) else "failed"
    cleaned["raw"] = {
        **payload,
        "raw_score": raw_score,
        "calibrated_score": calibrated_score,
        "score_band": _score_band(calibrated_score),
        "calibration_features": {
            "word_count": features["word_count"],
            "example_hits": features["example_hits"],
            "reasoning_hits": features["reasoning_hits"],
            "practical_hits": features["practical_hits"],
            "generic_hits": features["generic_hits"],
            "vague_hits": features["vague_hits"],
        },
    }
    return cleaned


def _fallback_evaluation(company, interview_round, answers):
    features = _answer_features(answers)
    features["specificity_score"] = features["example_hits"] + features["numeric_hits"] + min(features["practical_hits"], 3)
    invalid_reason = _invalid_answer_reason(features)
    score = min(_evidence_score(features, interview_round), _evidence_cap(features))
    passed = score >= interview_round.pass_score
    if invalid_reason:
        return {
            "score": score,
            "decision": "failed",
            "detailed_scores": _normalise_detail_scores({}, score),
            "strengths": [],
            "weaknesses": [invalid_reason],
            "feedback": f"Submission could not be evaluated as a valid interview answer. {invalid_reason}",
            "improvement_roadmap": ["Submit a direct answer that explains approach, reasoning, and one concrete example."],
            "company_benchmark": f"The response did not provide enough evidence for {company.name}'s benchmark.",
            "raw": {"provider": "local_fallback", "invalid_reason": invalid_reason},
        }
    weakness = "specific examples" if features["example_hits"] == 0 else interview_round.round_type.replace("_", " ")
    if features["word_count"] < 70:
        weakness = "communication structure"
    elif features["practical_hits"] < 2:
        weakness = "practical implementation detail"
    strength = "clear reasoning path" if features["reasoning_hits"] else "direct attempt at the prompt"
    feedback = (
        f"Local evaluation placed this response in the {_score_band(score)} range with {_quality_word(score)} evidence. "
        f"It found {features['reasoning_hits']} reasoning signal(s), {features['example_hits']} example signal(s), "
        f"and {features['practical_hits']} practical detail signal(s), with penalties for vague or generic wording where present."
    )
    return {
        "score": score,
        "decision": "passed" if passed else "failed",
        "detailed_scores": _normalise_detail_scores(
            {
                "technical_depth": score + (2 if features["practical_hits"] >= 3 else -3),
                "communication": score + (3 if features["structure_hits"] >= 2 else -4),
                "logic": score + (4 if features["reasoning_hits"] >= 2 else -5),
                "clarity": score + (2 if features["unique_ratio"] >= 0.48 else -4),
                "confidence": score - (3 if features["generic_hits"] else 0),
                "company_alignment": score + (3 if features["practical_hits"] >= 2 and features["reasoning_hits"] >= 2 else -3),
            },
            score,
        ),
        "strengths": [strength, "practical details included" if features["practical_hits"] >= 2 else "baseline prompt coverage"],
        "weaknesses": [weakness, "more concrete examples needed"] if features["example_hits"] == 0 else [weakness],
        "feedback": feedback,
        "improvement_roadmap": [
            "Answer with a clear situation, reasoning path, and final decision.",
            "Add one concrete example or measurable detail per response.",
            "Practice under the same timer before retrying the round.",
        ],
        "company_benchmark": (
            f"Against {company.name}'s benchmark, the answer showed "
            f"{'enough' if passed else 'limited'} evidence of {company.benchmark_description.lower()}"
        ),
        "raw": {"provider": "local_fallback"},
    }


def build_round_prompt(company, interview_round, answers):
    answer_payload = [
        {
            "question": answer.question.prompt,
            "competency": answer.question.competency,
            "expected_signal": answer.question.expected_signal,
            "answer": answer.answer_text,
            "time_spent_seconds": answer.time_spent_seconds,
        }
        for answer in answers
    ]
    return f"""
You are Round Forge, an interview readiness simulator. Evaluate the user's two answers together.
This is readiness coaching only, not a hiring decision.

Company: {company.name}
Company evaluation style: {company.evaluation_style}
Round: {interview_round.name}
Round type: {interview_round.round_type}
Pass score: {interview_round.pass_score}
Benchmark: {company.benchmark_description}

Answers JSON:
{json.dumps(answer_payload, ensure_ascii=False)}

Evaluate only the answer behavior visible in the JSON. Do not use generic company praise.
Avoid filler phrases such as "strong alignment", "process-oriented", or "{company.name} values communication" unless the answer text proves it.
Use this realistic score distribution:
- Weak: 35-55 for vague, generic, incomplete, or unsupported answers.
- Average: 55-70 for partially structured answers with limited examples or shallow reasoning.
- Good: 70-82 for clear, relevant answers with some specifics and practical thinking.
- Excellent: 82-91 for specific, well-reasoned answers with examples, constraints, tradeoffs, and discipline.
- Exceptional: 91-96 only for consistently precise, technically sound, example-rich answers.

Invalid or spam submissions must receive 0-15 with a direct failure explanation. This includes URL-only answers, nonsense, repeated filler, non-attempts, and extremely short answers without reasoning.
Analyze reasoning quality, communication clarity, structure, technical correctness, specificity, examples, practical thinking, and process discipline.
Company alignment must explain why the answer behavior matched or missed the benchmark.
Avoid "excellent" unless score is 82+, and avoid "exceptional" unless score is 91+.

Return only valid JSON with exactly these fields:
score: number 0-100
decision: "passed" or "failed"
detailed_scores: object with technical_depth, communication, logic, clarity, confidence, company_alignment numbers
strengths: array of short strings
weaknesses: array of short strings
feedback: concise paragraph
improvement_roadmap: array of actionable strings
company_benchmark: concise benchmark explanation
"""


def evaluate_round(company, interview_round, answers):
    answers = list(answers)
    if not settings.GEMINI_API_KEY:
        return _fallback_evaluation(company, interview_round, answers)

    try:
        from google import genai
        from google.genai import types

        model = settings.GEMINI_MODEL or "gemini-1.5-flash"
        with genai.Client(api_key=settings.GEMINI_API_KEY) as client:
            response = client.models.generate_content(
                model=model,
                contents=build_round_prompt(company, interview_round, answers),
                config=types.GenerateContentConfig(response_mime_type="application/json"),
            )
        payload = json.loads(_strip_json_fence(response.text))
        if not REQUIRED_KEYS.issubset(payload):
            missing = ", ".join(sorted(REQUIRED_KEYS - set(payload)))
            raise ValueError(f"Gemini response missing: {missing}")
        return _normalise_payload(payload, company, interview_round, answers)
    except Exception as exc:
    import traceback

    print("\n========== GEMINI ERROR ==========")
    print(exc)
    traceback.print_exc()
    print("==================================\n")

    fallback = _fallback_evaluation(company, interview_round, answers)
    fallback["feedback"] = "AI evaluation temporarily unavailable. Local fallback scoring was used."
    fallback["raw"] = {
        "provider": "local_fallback",
        "error": str(exc),
    }

    return fallback
