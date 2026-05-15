from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("companies", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="InterviewRound",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=140)),
                ("round_order", models.PositiveSmallIntegerField()),
                ("round_type", models.CharField(choices=[("aptitude", "Aptitude"), ("technical", "Technical"), ("dsa", "DSA"), ("system_design", "System Design"), ("hr", "HR")], max_length=32)),
                ("instructions", models.TextField()),
                ("time_limit_minutes", models.PositiveSmallIntegerField(default=12)),
                ("pass_score", models.PositiveSmallIntegerField(default=70)),
                ("max_questions", models.PositiveSmallIntegerField(default=2)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("track", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="rounds", to="companies.interviewtrack")),
            ],
            options={
                "ordering": ["track", "round_order"],
                "indexes": [
                    models.Index(fields=["track", "round_order"], name="interviews__track_i_152717_idx"),
                    models.Index(fields=["round_type"], name="interviews__round_t_485728_idx"),
                ],
                "unique_together": {("track", "round_order")},
            },
        ),
        migrations.CreateModel(
            name="Question",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("prompt", models.TextField()),
                ("competency", models.CharField(max_length=120)),
                ("difficulty", models.CharField(default="medium", max_length=40)),
                ("expected_signal", models.TextField()),
                ("is_active", models.BooleanField(default=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("round", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="questions", to="interviews.interviewround")),
            ],
            options={
                "ordering": ["id"],
                "indexes": [
                    models.Index(fields=["round", "is_active"], name="interviews__round_i_bd69a8_idx"),
                    models.Index(fields=["competency"], name="interviews__compete_243980_idx"),
                ],
            },
        ),
        migrations.CreateModel(
            name="SimulationSession",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("status", models.CharField(choices=[("active", "Active"), ("paused", "Simulation Paused"), ("completed", "Completed"), ("halted", "Progression Halted")], default="active", max_length=20)),
                ("total_score", models.DecimalField(decimal_places=2, default=0, max_digits=5)),
                ("started_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("completed_at", models.DateTimeField(blank=True, null=True)),
                ("company", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="simulations", to="companies.company")),
                ("current_round", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to="interviews.interviewround")),
                ("retry_of", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="retries", to="interviews.simulationsession")),
                ("track", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="simulations", to="companies.interviewtrack")),
                ("user", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="simulations", to=settings.AUTH_USER_MODEL)),
            ],
            options={
                "ordering": ["-started_at"],
                "indexes": [
                    models.Index(fields=["user", "status"], name="interviews__user_id_7922b1_idx"),
                    models.Index(fields=["company", "started_at"], name="interviews__company_1ae37d_idx"),
                ],
            },
        ),
        migrations.CreateModel(
            name="ProgressTracking",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("state", models.CharField(choices=[("locked", "Locked"), ("unlocked", "Unlocked"), ("current", "Current"), ("passed", "Threshold Cleared"), ("failed", "Below Company Benchmark")], default="locked", max_length=20)),
                ("attempt_number", models.PositiveSmallIntegerField(default=1)),
                ("unlocked_at", models.DateTimeField(blank=True, null=True)),
                ("completed_at", models.DateTimeField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("round", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="progress_records", to="interviews.interviewround")),
                ("simulation", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="progress", to="interviews.simulationsession")),
                ("user", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="progress_records", to=settings.AUTH_USER_MODEL)),
            ],
            options={
                "ordering": ["round__round_order"],
                "indexes": [
                    models.Index(fields=["simulation", "state"], name="interviews__simulat_f5bc2c_idx"),
                    models.Index(fields=["user", "state"], name="interviews__user_id_badd1e_idx"),
                ],
                "unique_together": {("simulation", "round")},
            },
        ),
        migrations.CreateModel(
            name="UserAnswer",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("answer_text", models.TextField()),
                ("time_spent_seconds", models.PositiveIntegerField(default=0)),
                ("submitted_at", models.DateTimeField(auto_now_add=True)),
                ("progress", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="answers", to="interviews.progresstracking")),
                ("question", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="answers", to="interviews.question")),
                ("simulation", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="answers", to="interviews.simulationsession")),
                ("user", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="answers", to=settings.AUTH_USER_MODEL)),
            ],
            options={
                "ordering": ["submitted_at"],
                "indexes": [
                    models.Index(fields=["simulation", "submitted_at"], name="interviews__simulat_28d1cb_idx"),
                    models.Index(fields=["question"], name="interviews__questio_adfdb0_idx"),
                ],
                "unique_together": {("simulation", "question")},
            },
        ),
        migrations.CreateModel(
            name="RoundResult",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("decision", models.CharField(choices=[("passed", "Threshold Cleared"), ("failed", "Below Company Benchmark")], max_length=20)),
                ("score", models.DecimalField(decimal_places=2, max_digits=5)),
                ("detailed_scores", models.JSONField(default=dict)),
                ("strengths", models.JSONField(default=list)),
                ("weaknesses", models.JSONField(default=list)),
                ("feedback", models.TextField()),
                ("improvement_roadmap", models.JSONField(default=list)),
                ("company_benchmark", models.TextField()),
                ("ai_raw_response", models.JSONField(default=dict)),
                ("evaluated_at", models.DateTimeField(auto_now_add=True)),
                ("progress", models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name="result", to="interviews.progresstracking")),
                ("round", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="results", to="interviews.interviewround")),
                ("simulation", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="round_results", to="interviews.simulationsession")),
            ],
            options={
                "ordering": ["round__round_order"],
                "indexes": [
                    models.Index(fields=["simulation", "decision"], name="interviews__simulat_da3074_idx"),
                    models.Index(fields=["round", "score"], name="interviews__round_i_9e79eb_idx"),
                ],
            },
        ),
    ]
