from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="Company",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=120, unique=True)),
                ("slug", models.SlugField(max_length=140, unique=True)),
                ("tagline", models.CharField(max_length=180)),
                ("description", models.TextField()),
                ("evaluation_style", models.TextField()),
                ("benchmark_description", models.TextField()),
                ("pass_threshold", models.PositiveSmallIntegerField(default=70)),
                ("accent_color", models.CharField(default="#8fb8ff", max_length=24)),
                ("order", models.PositiveSmallIntegerField(default=0)),
                ("is_active", models.BooleanField(default=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={
                "ordering": ["order", "name"],
                "indexes": [
                    models.Index(fields=["slug"], name="companies_c_slug_45751b_idx"),
                    models.Index(fields=["is_active", "order"], name="companies_c_is_acti_ed5c1c_idx"),
                ],
            },
        ),
        migrations.CreateModel(
            name="InterviewTrack",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=140)),
                ("slug", models.SlugField(max_length=160)),
                ("description", models.TextField()),
                ("is_active", models.BooleanField(default=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("company", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="tracks", to="companies.company")),
            ],
            options={
                "ordering": ["company__order", "name"],
                "indexes": [
                    models.Index(fields=["slug"], name="companies_i_slug_418c39_idx"),
                    models.Index(fields=["is_active"], name="companies_i_is_acti_e362a7_idx"),
                ],
                "unique_together": {("company", "slug")},
            },
        ),
    ]
