from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("companies", "0001_initial"),
        ("reports", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="ReadinessAnalytics",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("total_simulations", models.PositiveIntegerField(default=0)),
                ("average_readiness", models.DecimalField(decimal_places=2, default=0, max_digits=5)),
                ("strongest_area", models.CharField(blank=True, max_length=160)),
                ("weakest_area", models.CharField(blank=True, max_length=160)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("company", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="readiness_analytics", to="companies.company")),
                ("last_report", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to="reports.finalreport")),
                ("user", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="readiness_analytics", to=settings.AUTH_USER_MODEL)),
            ],
            options={
                "verbose_name_plural": "Readiness analytics",
                "indexes": [
                    models.Index(fields=["user", "company"], name="analytics_r_user_id_3e80eb_idx"),
                    models.Index(fields=["average_readiness"], name="analytics_r_average_770849_idx"),
                ],
                "unique_together": {("user", "company")},
            },
        ),
    ]
