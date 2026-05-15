from django.contrib import admin

from apps.interviews.models import InterviewRound, ProgressTracking, Question, RoundResult, SimulationSession, UserAnswer


class QuestionInline(admin.TabularInline):
    model = Question
    extra = 0


@admin.register(InterviewRound)
class InterviewRoundAdmin(admin.ModelAdmin):
    list_display = ("name", "track", "round_order", "round_type", "pass_score")
    list_filter = ("round_type", "track__company")
    inlines = [QuestionInline]


@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    list_display = ("competency", "round", "difficulty", "is_active")
    list_filter = ("difficulty", "is_active", "round__track__company")
    search_fields = ("prompt", "competency")


@admin.register(SimulationSession)
class SimulationSessionAdmin(admin.ModelAdmin):
    list_display = ("user", "company", "status", "total_score", "started_at")
    list_filter = ("status", "company")
    search_fields = ("user__email",)


@admin.register(ProgressTracking)
class ProgressTrackingAdmin(admin.ModelAdmin):
    list_display = ("simulation", "round", "state", "attempt_number")
    list_filter = ("state", "round__track__company")


@admin.register(UserAnswer)
class UserAnswerAdmin(admin.ModelAdmin):
    list_display = ("user", "question", "submitted_at")
    search_fields = ("answer_text", "user__email")


@admin.register(RoundResult)
class RoundResultAdmin(admin.ModelAdmin):
    list_display = ("simulation", "round", "decision", "score", "evaluated_at")
    list_filter = ("decision", "round__track__company")
