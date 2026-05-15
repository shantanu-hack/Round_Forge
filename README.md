# Round Forge

Round Forge is an AI-powered interview readiness simulation platform built with Django, PostgreSQL, and Gemini. It is not a recruitment portal and does not claim hiring authority. It simulates company-specific interview readiness rounds, stores answers, evaluates each round after both answers are submitted, and generates professional improvement reports.

## Architecture

- `config/settings`: split Django settings for development and production.
- `apps/authentication`: custom user model, email/password auth, session login, Google OAuth via django-allauth.
- `apps/companies`: the two supported companies, interview tracks, seed command.
- `apps/interviews`: rounds, questions, simulation sessions, progress locking, answers, round results, Gemini evaluation service.
- `apps/reports`: final readiness reports and curated resource recommendations.
- `apps/analytics`: per-user readiness aggregation.
- `apps/dashboard`: user dashboard and lightweight staff insights.
- `templates` and `static`: server-rendered frontend with a dark premium UI system.

## Supported Companies

Round Forge intentionally supports only:

- Mercedes-Benz: analytical, systems-oriented, engineering-heavy, precision-driven.
- Infosys: communication-focused, structured, enterprise-style, process-oriented.

## Local Setup

1. Create and activate a virtual environment.

```bash
python -m venv venv
venv\Scripts\activate
```

2. Install dependencies.

```bash
pip install -r requirements.txt
```

3. Create a PostgreSQL database.

```sql
CREATE DATABASE roundforge;
CREATE USER roundforge_user WITH PASSWORD 'strong-password';
GRANT ALL PRIVILEGES ON DATABASE roundforge TO roundforge_user;
```

4. Configure environment variables.

```bash
copy .env.example .env
```

Update `.env` with database credentials, `SECRET_KEY`, `GEMINI_API_KEY`, and Google OAuth credentials.

5. Run migrations.

```bash
python manage.py migrate
```

6. Seed companies, rounds, and questions.

```bash
python manage.py seed_roundforge
```

7. Create an admin user.

```bash
python manage.py createsuperuser
```

8. Start the server.

```bash
python manage.py runserver
```

Open `http://127.0.0.1:8000`.

## Gemini Setup

Create a Gemini API key in Google AI Studio and set:

```env
GEMINI_API_KEY=your-key
GEMINI_MODEL=gemini-1.5-flash
```

If the key is missing or Gemini fails, Round Forge uses a deterministic local fallback evaluator so the simulation flow remains stable during development.

## Google OAuth Setup

Create OAuth credentials in Google Cloud Console and add:

```env
GOOGLE_CLIENT_ID=your-client-id
GOOGLE_CLIENT_SECRET=your-client-secret
```

Add this redirect URI in Google Cloud:

```text
http://127.0.0.1:8000/accounts/google/login/callback/
```

For production, replace the host with your deployed domain.

## Interview Flow

1. User signs up or logs in.
2. User opens a company simulation.
3. Backend creates a `SimulationSession` and `ProgressTracking` rows.
4. First round is current; later rounds are locked.
5. Each round exposes at most two stored questions.
6. User answers are saved individually.
7. Gemini evaluates the round only after both answers are stored.
8. Passing unlocks the next round.
9. Failing halts progression and generates an improvement report.
10. Completing all rounds generates a final readiness report.

## Deployment Notes

For Render, Railway, or a VPS:

- Set `DJANGO_SETTINGS_MODULE=config.settings.production`.
- Set `DEBUG=False`.
- Configure `ALLOWED_HOSTS` and `CSRF_TRUSTED_ORIGINS`.
- Use managed PostgreSQL.
- Run `python manage.py collectstatic --noinput`.
- Run `python manage.py migrate`.
- Run `python manage.py seed_roundforge`.
- Start with `gunicorn config.wsgi:application`.

Static files are served through WhiteNoise. Secrets are read only from environment variables.
