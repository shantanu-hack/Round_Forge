from decimal import Decimal

from django.core.exceptions import ObjectDoesNotExist, PermissionDenied, ValidationError
from django.db import transaction
from django.utils import timezone

from apps.interviews.models import ProgressTracking, Question, RoundResult, SimulationSession, UserAnswer
from apps.interviews.services.ai_service import evaluate_round
from apps.reports.services import build_final_report


STALE_INTERVIEW_MESSAGE = "Interview session updated in another tab."


def start_simulation(user, track, retry_of=None):
    rounds = list(track.rounds.prefetch_related("questions").order_by("round_order"))
    if not rounds:
        raise ValidationError("This company track has no configured interview rounds.")

    with transaction.atomic():
        now = timezone.now()
        simulation = SimulationSession.objects.create(
            user=user,
            company=track.company,
            track=track,
            current_round=rounds[0],
            retry_of=retry_of,
        )
        for index, interview_round in enumerate(rounds):
            ProgressTracking.objects.create(
                user=user,
                simulation=simulation,
                round=interview_round,
                state=ProgressTracking.State.CURRENT if index == 0 else ProgressTracking.State.LOCKED,
                unlocked_at=now if index == 0 else None,
                started_at=now if index == 0 else None,
            )
    return simulation


def retry_simulation(user, simulation):
    if simulation.user_id != user.id:
        raise PermissionDenied("You cannot retry another user's simulation.")
    return start_simulation(user, simulation.track, retry_of=simulation)


def _round_questions(interview_round):
    return list(Question.objects.filter(round=interview_round, is_active=True).order_by("id")[: interview_round.max_questions])


def _stale_interview_error():
    return ValidationError(STALE_INTERVIEW_MESSAGE)


def _ensure_round_started(progress):
    if progress.started_at:
        return
    progress.started_at = progress.unlocked_at or timezone.now()
    progress.save(update_fields=["started_at", "updated_at"])


def _elapsed_seconds(progress, now=None):
    _ensure_round_started(progress)
    now = now or timezone.now()
    return max(0, int((now - progress.started_at).total_seconds()))


def _is_timed_out(progress, now=None):
    _ensure_round_started(progress)
    now = now or timezone.now()
    return now >= progress.expires_at


def _create_timeout_result(progress):
    questions = _round_questions(progress.round)
    answers = list(progress.answers.select_related("question").filter(question__in=questions).order_by("question_id"))
    answered_count = len(answers)
    required_count = len(questions)
    feedback = (
        f"Round expired before completion. {answered_count} of {required_count} required "
        "answers were submitted before the server-side timer ended."
    )
    result, _ = RoundResult.objects.update_or_create(
        progress=progress,
        defaults={
            "simulation": progress.simulation,
            "round": progress.round,
            "decision": RoundResult.Decision.FAILED,
            "score": Decimal("0"),
            "detailed_scores": {
                "technical_depth": 0,
                "communication": 0,
                "logic": 0,
                "clarity": 0,
                "confidence": 0,
                "company_alignment": 0,
            },
            "strengths": ["Submitted answers were preserved for review."] if answered_count else [],
            "weaknesses": ["round time management", "incomplete submission"],
            "feedback": feedback,
            "improvement_roadmap": [
                "Practice completing all required answers within the round timer.",
                "Prioritize concise structure before adding supporting detail.",
            ],
            "company_benchmark": progress.simulation.company.benchmark_description,
            "ai_raw_response": {
                "provider": "server_timeout",
                "answered_count": answered_count,
                "required_count": required_count,
            },
        },
    )
    return result


def _finalize_timed_out_progress(progress):
    if progress.state == ProgressTracking.State.EXPIRED:
        return {"expired": True, "result": progress.result, "simulation_closed": True}

    result = _create_timeout_result(progress)
    now = timezone.now()
    progress.state = ProgressTracking.State.EXPIRED
    progress.completed_at = now
    progress.save(update_fields=["state", "completed_at", "updated_at"])
    progress.simulation.mark_completed(SimulationSession.Status.HALTED)
    build_final_report(progress.simulation)
    return {"expired": True, "result": result, "simulation_closed": True}


@transaction.atomic
def expire_current_round_if_needed(user, simulation_id):
    simulation = (
        SimulationSession.objects.select_related("company", "track", "current_round")
        .select_for_update(of=("self",))
        .get(id=simulation_id)
    )
    if simulation.user_id != user.id:
        raise PermissionDenied("This simulation belongs to another user.")
    if simulation.status not in {SimulationSession.Status.ACTIVE, SimulationSession.Status.PAUSED}:
        return {"expired": False}

    progress = (
        ProgressTracking.objects.select_for_update()
        .filter(
            simulation=simulation,
            round=simulation.current_round,
            state=ProgressTracking.State.CURRENT,
        )
        .select_related("round")
        .first()
    )
    if not progress:
        return {"expired": False}

    progress.simulation = simulation
    _ensure_round_started(progress)
    if not _is_timed_out(progress):
        return {"expired": False, "remaining": progress.seconds_remaining}
    return _finalize_timed_out_progress(progress)


@transaction.atomic
def submit_answer(user, simulation_id, question_id, answer_text, time_spent_seconds=0):
    simulation = (
        SimulationSession.objects.select_related("company", "track", "current_round")
        .select_for_update(of=("self",))
        .get(id=simulation_id)
    )
    if simulation.user_id != user.id:
        raise PermissionDenied("This simulation belongs to another user.")
    if simulation.status not in {SimulationSession.Status.ACTIVE, SimulationSession.Status.PAUSED}:
        raise _stale_interview_error()
    if not simulation.current_round_id:
        raise _stale_interview_error()

    progress = (
        ProgressTracking.objects.select_for_update()
        .select_related("round")
        .filter(
            simulation=simulation,
            round=simulation.current_round,
            state=ProgressTracking.State.CURRENT,
        )
        .first()
    )
    if not progress:
        raise _stale_interview_error()
    progress.simulation = simulation
    now = timezone.now()
    if _is_timed_out(progress, now):
        _finalize_timed_out_progress(progress)
        raise ValidationError("Round timer expired. The round was finalized and late submissions are locked.")
    if not answer_text or len(answer_text.strip()) < 20:
        raise ValidationError("Answer must be at least 20 characters for a meaningful evaluation.")

    try:
        question = Question.objects.get(id=question_id, round=progress.round, is_active=True)
    except (ObjectDoesNotExist, ValueError, TypeError):
        raise _stale_interview_error()
    allowed_question_ids = {item.id for item in _round_questions(progress.round)}
    if question.id not in allowed_question_ids:
        raise _stale_interview_error()
    if progress.answers.filter(question=question).exists():
        raise _stale_interview_error()

    UserAnswer.objects.create(
        user=user,
        simulation=simulation,
        progress=progress,
        question=question,
        answer_text=answer_text.strip(),
        time_spent_seconds=_elapsed_seconds(progress, now),
    )
    return evaluate_progress_if_ready(progress)


def evaluate_progress_if_ready(progress):
    questions = _round_questions(progress.round)
    answers = list(progress.answers.select_related("question").filter(question__in=questions).order_by("question_id"))
    if len(answers) < len(questions):
        return {"evaluated": False, "remaining": len(questions) - len(answers)}

    payload = evaluate_round(progress.simulation.company, progress.round, answers)
    decision = RoundResult.Decision.PASSED if payload["decision"] == "passed" else RoundResult.Decision.FAILED
    result, _ = RoundResult.objects.update_or_create(
        progress=progress,
        defaults={
            "simulation": progress.simulation,
            "round": progress.round,
            "decision": decision,
            "score": Decimal(str(payload["score"])),
            "detailed_scores": payload["detailed_scores"],
            "strengths": payload["strengths"],
            "weaknesses": payload["weaknesses"],
            "feedback": payload["feedback"],
            "improvement_roadmap": payload["improvement_roadmap"],
            "company_benchmark": payload["company_benchmark"],
            "ai_raw_response": payload.get("raw", payload),
        },
    )

    progress.state = ProgressTracking.State.PASSED if decision == RoundResult.Decision.PASSED else ProgressTracking.State.FAILED
    progress.completed_at = timezone.now()
    progress.save(update_fields=["state", "completed_at", "updated_at"])

    if decision == RoundResult.Decision.FAILED:
        progress.simulation.mark_completed(SimulationSession.Status.HALTED)
        build_final_report(progress.simulation)
        return {"evaluated": True, "result": result, "simulation_closed": True}

    next_progress = (
        ProgressTracking.objects.select_for_update()
        .filter(simulation=progress.simulation, round__round_order__gt=progress.round.round_order)
        .order_by("round__round_order")
        .first()
    )
    if next_progress:
        now = timezone.now()
        next_progress.state = ProgressTracking.State.CURRENT
        next_progress.unlocked_at = now
        next_progress.started_at = now
        next_progress.save(update_fields=["state", "unlocked_at", "started_at", "updated_at"])
        progress.simulation.current_round = next_progress.round
        progress.simulation.status = SimulationSession.Status.ACTIVE
        progress.simulation.save(update_fields=["current_round", "status", "updated_at"])
        return {"evaluated": True, "result": result, "next_progress": next_progress}

    total = progress.simulation.round_results.count()
    if total:
        score_sum = sum(item.score for item in progress.simulation.round_results.all())
        progress.simulation.total_score = (score_sum / Decimal(total)).quantize(Decimal("0.01"))
    progress.simulation.mark_completed(SimulationSession.Status.COMPLETED)
    progress.simulation.save(update_fields=["total_score", "updated_at"])
    build_final_report(progress.simulation)
    return {"evaluated": True, "result": result, "simulation_closed": True}
