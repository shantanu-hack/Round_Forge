from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("interviews", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="FinalReport",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("readiness_percent", models.DecimalField(decimal_places=2, max_digits=5)),
                ("round_analysis", models.JSONField(default=list)),
                ("strengths", models.JSONField(default=list)),
                ("weaknesses", models.JSONField(default=list)),
                ("company_alignment", models.TextField()),
                ("ai_generated_analysis", models.TextField()),
                ("improvement_roadmap", models.JSONField(default=list)),
                ("recommended_resources", models.JSONField(default=list)),
                ("retry_recommendation", models.TextField()),
                ("readiness_timeline", models.CharField(max_length=180)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("simulation", models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name="final_report", to="interviews.simulationsession")),
                ("user", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="final_reports", to=settings.AUTH_USER_MODEL)),
            ],
            options={
                "ordering": ["-created_at"],
                "indexes": [
                    models.Index(fields=["user", "created_at"], name="reports_fin_user_id_78ef1b_idx"),
                    models.Index(fields=["readiness_percent"], name="reports_fin_readine_92cf4b_idx"),
                ],
            },
        ),
    ]
