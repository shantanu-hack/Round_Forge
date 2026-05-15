from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied, ValidationError
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from apps.interviews.models import ProgressTracking, Question, SimulationSession
from apps.interviews.services.progression import expire_current_round_if_needed, retry_simulation, submit_answer


ROUND_TRANSITION_SESSION_KEY = "roundforge_round_transition"


def _format_timer(seconds):
    minutes = seconds // 60
    remainder = str(seconds % 60).zfill(2)
    return f"{minutes}:{remainder}"


def _message_text(exc):
    if isinstance(exc, ValidationError):
        return exc.messages[0] if exc.messages else str(exc)
    return str(exc)


@login_required
def simulation_detail(request, simulation_id):
    try:
        timeout_outcome = expire_current_round_if_needed(request.user, simulation_id)
        if timeout_outcome.get("expired"):
            messages.warning(request, "Round timer expired. The round was finalized and late submissions are locked.")
    except (SimulationSession.DoesNotExist, PermissionDenied, ValidationError):
        pass

    simulation = get_object_or_404(
        SimulationSession.objects.select_related("company", "track", "current_round").prefetch_related(
            "progress__round", "round_results__round"
        ),
        id=simulation_id,
        user=request.user,
    )
    current_progress = (
        simulation.progress.select_related("round")
        .filter(state=ProgressTracking.State.CURRENT)
        .prefetch_related("round__questions", "answers__question")
        .first()
    )
    questions = []
    answered_ids = set()
    timer_remaining_seconds = 0
    timer_display = "0:00"
    if current_progress:
        questions = list(Question.objects.filter(round=current_progress.round, is_active=True).order_by("id")[: current_progress.round.max_questions])
        answered_ids = set(current_progress.answers.values_list("question_id", flat=True))
        timer_remaining_seconds = current_progress.seconds_remaining
        timer_display = _format_timer(timer_remaining_seconds)
    round_transition = request.session.pop(ROUND_TRANSITION_SESSION_KEY, None)
    if round_transition and round_transition.get("simulation_id") != simulation.id:
        round_transition = None
    return render(
        request,
        "interviews/simulation.html",
        {
            "simulation": simulation,
            "current_progress": current_progress,
            "questions": questions,
            "answered_ids": answered_ids,
            "progress_records": simulation.progress.select_related("round").all(),
            "timer_remaining_seconds": timer_remaining_seconds,
            "timer_display": timer_display,
            "round_transition": round_transition,
        },
    )


@login_required
@require_POST
def submit_answer_view(request, simulation_id):
    try:
        outcome = submit_answer(
            request.user,
            simulation_id,
            request.POST.get("question_id"),
            request.POST.get("answer_text", ""),
            request.POST.get("time_spent_seconds", 0),
        )
        if outcome.get("evaluated"):
            result = outcome["result"]
            next_progress = outcome.get("next_progress")
            if next_progress:
                request.session[ROUND_TRANSITION_SESSION_KEY] = {
                    "simulation_id": simulation_id,
                    "result": "pass",
                    "score": str(result.score),
                    "round_name": result.round.name,
                    "next_round": next_progress.round.name,
                    "feedback": result.feedback,
                }
            messages.success(request, f"{result.get_decision_display()} - round score {result.score}%.")
        else:
            messages.info(request, f"Answer stored. {outcome['remaining']} question remains before evaluation.")
    except (ValidationError, PermissionDenied, ValueError) as exc:
        messages.error(request, _message_text(exc))
    return redirect("interviews:simulation", simulation_id=simulation_id)


@login_required
@require_POST
def expire_round_view(request, simulation_id):
    try:
        outcome = expire_current_round_if_needed(request.user, simulation_id)
        if outcome.get("expired"):
            messages.warning(request, "Round timer expired. The round was finalized and late submissions are locked.")
    except (ValidationError, PermissionDenied, ValueError) as exc:
        messages.error(request, _message_text(exc))
    return redirect("interviews:simulation", simulation_id=simulation_id)


@login_required
@require_POST
def retry_view(request, simulation_id):
    simulation = get_object_or_404(SimulationSession, id=simulation_id, user=request.user)
    new_simulation = retry_simulation(request.user, simulation)
    return redirect("interviews:simulation", simulation_id=new_simulation.id)
