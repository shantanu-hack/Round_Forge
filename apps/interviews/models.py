from django.conf import settings
from django.db import models
from datetime import timedelta

from django.utils import timezone


class InterviewRound(models.Model):
    class RoundType(models.TextChoices):
        APTITUDE = "aptitude", "Aptitude"
        TECHNICAL = "technical", "Technical"
        DSA = "dsa", "DSA"
        SYSTEM_DESIGN = "system_design", "System Design"
        HR = "hr", "HR"

    track = models.ForeignKey("companies.InterviewTrack", on_delete=models.CASCADE, related_name="rounds")
    name = models.CharField(max_length=140)
    round_order = models.PositiveSmallIntegerField()
    round_type = models.CharField(max_length=32, choices=RoundType.choices)
    instructions = models.TextField()
    time_limit_minutes = models.PositiveSmallIntegerField(default=12)
    pass_score = models.PositiveSmallIntegerField(default=70)
    max_questions = models.PositiveSmallIntegerField(default=2)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["track", "round_order"]
        unique_together = ("track", "round_order")
        indexes = [
            models.Index(fields=["track", "round_order"]),
            models.Index(fields=["round_type"]),
        ]

    def __str__(self):
        return f"{self.track.company.name}: {self.name}"


class Question(models.Model):
    round = models.ForeignKey(InterviewRound, on_delete=models.CASCADE, related_name="questions")
    prompt = models.TextField()
    competency = models.CharField(max_length=120)
    difficulty = models.CharField(max_length=40, default="medium")
    expected_signal = models.TextField()
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["id"]
        indexes = [
            models.Index(fields=["round", "is_active"]),
            models.Index(fields=["competency"]),
        ]

    def __str__(self):
        return f"{self.round.name}: {self.competency}"


class SimulationSession(models.Model):
    class Status(models.TextChoices):
        ACTIVE = "active", "Active"
        PAUSED = "paused", "Simulation Paused"
        COMPLETED = "completed", "Completed"
        HALTED = "halted", "Progression Halted"

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="simulations")
    company = models.ForeignKey("companies.Company", on_delete=models.PROTECT, related_name="simulations")
    track = models.ForeignKey("companies.InterviewTrack", on_delete=models.PROTECT, related_name="simulations")
    current_round = models.ForeignKey(InterviewRound, on_delete=models.SET_NULL, null=True, blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.ACTIVE)
    retry_of = models.ForeignKey("self", on_delete=models.SET_NULL, null=True, blank=True, related_name="retries")
    total_score = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    started_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-started_at"]
        indexes = [
            models.Index(fields=["user", "status"]),
            models.Index(fields=["company", "started_at"]),
        ]

    def mark_completed(self, status):
        self.status = status
        self.completed_at = timezone.now()
        self.save(update_fields=["status", "completed_at", "updated_at"])

    def __str__(self):
        return f"{self.user} - {self.company.name} ({self.get_status_display()})"


class ProgressTracking(models.Model):
    class State(models.TextChoices):
        LOCKED = "locked", "Locked"
        UNLOCKED = "unlocked", "Unlocked"
        CURRENT = "current", "Current"
        PASSED = "passed", "Threshold Cleared"
        FAILED = "failed", "Below Company Benchmark"
        EXPIRED = "expired", "Expired"

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="progress_records")
    simulation = models.ForeignKey(SimulationSession, on_delete=models.CASCADE, related_name="progress")
    round = models.ForeignKey(InterviewRound, on_delete=models.CASCADE, related_name="progress_records")
    state = models.CharField(max_length=20, choices=State.choices, default=State.LOCKED)
    attempt_number = models.PositiveSmallIntegerField(default=1)
    unlocked_at = models.DateTimeField(null=True, blank=True)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("simulation", "round")
        ordering = ["round__round_order"]
        indexes = [
            models.Index(fields=["simulation", "state"]),
            models.Index(fields=["user", "state"]),
        ]

    def __str__(self):
        return f"{self.simulation_id}: {self.round.name} - {self.get_state_display()}"

    @property
    def expires_at(self):
        if not self.started_at:
            return None
        return self.started_at + timedelta(minutes=self.round.time_limit_minutes)

    @property
    def seconds_remaining(self):
        if not self.expires_at:
            return 0
        return max(0, int((self.expires_at - timezone.now()).total_seconds()))


class UserAnswer(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="answers")
    simulation = models.ForeignKey(SimulationSession, on_delete=models.CASCADE, related_name="answers")
    progress = models.ForeignKey(ProgressTracking, on_delete=models.CASCADE, related_name="answers")
    question = models.ForeignKey(Question, on_delete=models.PROTECT, related_name="answers")
    answer_text = models.TextField()
    time_spent_seconds = models.PositiveIntegerField(default=0)
    submitted_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("simulation", "question")
        ordering = ["submitted_at"]
        indexes = [
            models.Index(fields=["simulation", "submitted_at"]),
            models.Index(fields=["question"]),
        ]

    def __str__(self):
        return f"{self.user} answer to {self.question_id}"


class RoundResult(models.Model):
    class Decision(models.TextChoices):
        PASSED = "passed", "Threshold Cleared"
        FAILED = "failed", "Below Company Benchmark"

    simulation = models.ForeignKey(SimulationSession, on_delete=models.CASCADE, related_name="round_results")
    progress = models.OneToOneField(ProgressTracking, on_delete=models.CASCADE, related_name="result")
    round = models.ForeignKey(InterviewRound, on_delete=models.PROTECT, related_name="results")
    decision = models.CharField(max_length=20, choices=Decision.choices)
    score = models.DecimalField(max_digits=5, decimal_places=2)
    detailed_scores = models.JSONField(default=dict)
    strengths = models.JSONField(default=list)
    weaknesses = models.JSONField(default=list)
    feedback = models.TextField()
    improvement_roadmap = models.JSONField(default=list)
    company_benchmark = models.TextField()
    ai_raw_response = models.JSONField(default=dict)
    evaluated_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["round__round_order"]
        indexes = [
            models.Index(fields=["simulation", "decision"]),
            models.Index(fields=["round", "score"]),
        ]

    def __str__(self):
        return f"{self.round.name}: {self.score}"
