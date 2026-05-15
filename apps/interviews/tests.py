from datetime import timedelta
from types import SimpleNamespace
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from apps.analytics.models import ReadinessAnalytics
from apps.companies.models import Company, InterviewTrack
from apps.interviews.models import ProgressTracking, Question, RoundResult, UserAnswer
from apps.interviews.services.ai_service import evaluate_round
from apps.interviews.services.progression import retry_simulation, start_simulation
from apps.reports.models import FinalReport


@override_settings(GEMINI_API_KEY="")
class SubmitAnswerViewTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="candidate",
            email="candidate@example.com",
            password="test-pass-123",
        )
        self.company = Company.objects.create(
            name="Acme",
            slug="acme",
            tagline="Build practical systems",
            description="Engineering company",
            evaluation_style="Structured and evidence-driven",
            benchmark_description="Clear tradeoffs, examples, and implementation judgment.",
            pass_threshold=40,
        )
        self.track = InterviewTrack.objects.create(
            company=self.company,
            name="Backend",
            slug="backend",
            description="Backend engineering track",
        )
        self.round_one = self.track.rounds.create(
            name="Technical",
            round_order=1,
            round_type="technical",
            instructions="Answer with tradeoffs.",
            pass_score=40,
            max_questions=2,
        )
        self.round_two = self.track.rounds.create(
            name="System Design",
            round_order=2,
            round_type="system_design",
            instructions="Answer with scale and complexity.",
            pass_score=40,
            max_questions=2,
        )
        self.round_one_questions = [
            Question.objects.create(
                round=self.round_one,
                prompt=f"Technical prompt {index}",
                competency="technical_depth",
                expected_signal="Discuss tradeoffs and testing.",
            )
            for index in range(2)
        ]
        self.round_two_questions = [
            Question.objects.create(
                round=self.round_two,
                prompt=f"Design prompt {index}",
                competency="system_design",
                expected_signal="Discuss scale and complexity.",
            )
            for index in range(2)
        ]
        self.simulation = start_simulation(self.user, self.track)
        self.client.force_login(self.user)

    def _submit(self, question):
        return self.client.post(
            reverse("interviews:submit_answer", args=[self.simulation.id]),
            {
                "question_id": question.id,
                "answer_text": (
                    "I would explain the tradeoff with a concrete example, describe the "
                    "complexity, show how the design scales, and include tests because "
                    "that gives the interviewer a measurable signal."
                ),
                "time_spent_seconds": "90",
            },
        )

    def _answer_for_ai(self):
        progress = ProgressTracking.objects.get(simulation=self.simulation, round=self.round_one)
        return UserAnswer.objects.create(
            user=self.user,
            simulation=self.simulation,
            progress=progress,
            question=self.round_one_questions[0],
            answer_text=(
                "I would explain the tradeoff with a concrete example, describe complexity, "
                "show scale implications, and include tests because that gives clear signal."
            ),
            time_spent_seconds=90,
        )

    def test_submit_answer_saves_answers_unlocks_next_round_and_updates_reports(self):
        first_response = self._submit(self.round_one_questions[0])
        self.assertRedirects(first_response, reverse("interviews:simulation", args=[self.simulation.id]))
        self.assertEqual(UserAnswer.objects.filter(simulation=self.simulation).count(), 1)

        second_response = self._submit(self.round_one_questions[1])
        self.assertRedirects(second_response, reverse("interviews:simulation", args=[self.simulation.id]))

        first_progress = ProgressTracking.objects.get(simulation=self.simulation, round=self.round_one)
        next_progress = ProgressTracking.objects.get(simulation=self.simulation, round=self.round_two)
        self.simulation.refresh_from_db()

        self.assertEqual(first_progress.state, ProgressTracking.State.PASSED)
        self.assertEqual(next_progress.state, ProgressTracking.State.CURRENT)
        self.assertEqual(self.simulation.current_round, self.round_two)
        self.assertEqual(RoundResult.objects.filter(simulation=self.simulation).count(), 1)

        for question in self.round_two_questions:
            response = self._submit(question)
            self.assertRedirects(response, reverse("interviews:simulation", args=[self.simulation.id]))

        self.simulation.refresh_from_db()
        report = FinalReport.objects.get(simulation=self.simulation)
        analytics = ReadinessAnalytics.objects.get(user=self.user, company=self.company)

        self.assertEqual(self.simulation.status, self.simulation.Status.COMPLETED)
        self.assertEqual(RoundResult.objects.filter(simulation=self.simulation).count(), 2)
        self.assertEqual(analytics.last_report, report)
        self.assertEqual(analytics.total_simulations, 1)

        reports_response = self.client.get(reverse("reports:list"))
        analytics_response = self.client.get(reverse("analytics:home"))
        self.assertContains(reports_response, "Acme")
        self.assertContains(analytics_response, "Acme")

    def test_expire_endpoint_finalizes_round_and_updates_reporting(self):
        progress = ProgressTracking.objects.get(simulation=self.simulation, round=self.round_one)
        progress.started_at = timezone.now() - timedelta(minutes=self.round_one.time_limit_minutes, seconds=1)
        progress.save(update_fields=["started_at", "updated_at"])

        response = self.client.post(reverse("interviews:expire_round", args=[self.simulation.id]))
        self.assertRedirects(response, reverse("interviews:simulation", args=[self.simulation.id]))

        progress.refresh_from_db()
        self.simulation.refresh_from_db()
        report = FinalReport.objects.get(simulation=self.simulation)
        analytics = ReadinessAnalytics.objects.get(user=self.user, company=self.company)

        self.assertEqual(progress.state, ProgressTracking.State.EXPIRED)
        self.assertEqual(self.simulation.status, self.simulation.Status.HALTED)
        self.assertEqual(RoundResult.objects.get(simulation=self.simulation).score, 0)
        self.assertEqual(analytics.last_report, report)

    def test_refresh_does_not_reset_expired_timer_and_late_submissions_are_blocked(self):
        progress = ProgressTracking.objects.get(simulation=self.simulation, round=self.round_one)
        original_started_at = timezone.now() - timedelta(minutes=self.round_one.time_limit_minutes, seconds=1)
        progress.started_at = original_started_at
        progress.save(update_fields=["started_at", "updated_at"])

        response = self.client.get(reverse("interviews:simulation", args=[self.simulation.id]))
        self.assertContains(response, "Progression Halted")

        progress.refresh_from_db()
        self.assertEqual(progress.state, ProgressTracking.State.EXPIRED)
        self.assertEqual(progress.started_at, original_started_at)

        late_response = self._submit(self.round_one_questions[0])
        self.assertRedirects(late_response, reverse("interviews:simulation", args=[self.simulation.id]))
        self.assertEqual(UserAnswer.objects.filter(simulation=self.simulation).count(), 0)
        self.assertEqual(RoundResult.objects.filter(simulation=self.simulation).count(), 1)

    def test_stale_previous_round_submission_is_rejected_cleanly(self):
        self._submit(self.round_one_questions[0])
        self._submit(self.round_one_questions[1])

        response = self._submit(self.round_one_questions[0])
        self.assertRedirects(response, reverse("interviews:simulation", args=[self.simulation.id]))

        messages = [message.message for message in response.wsgi_request._messages]
        self.assertIn("Interview session updated in another tab.", messages)
        self.assertEqual(UserAnswer.objects.filter(simulation=self.simulation, question=self.round_one_questions[0]).count(), 1)
        self.assertEqual(RoundResult.objects.filter(simulation=self.simulation).count(), 1)

    def test_duplicate_pending_question_submission_is_rejected_cleanly(self):
        self._submit(self.round_one_questions[0])

        response = self._submit(self.round_one_questions[0])
        self.assertRedirects(response, reverse("interviews:simulation", args=[self.simulation.id]))

        messages = [message.message for message in response.wsgi_request._messages]
        self.assertIn("Interview session updated in another tab.", messages)
        self.assertEqual(UserAnswer.objects.filter(simulation=self.simulation, question=self.round_one_questions[0]).count(), 1)

    def test_missing_current_progress_is_rejected_cleanly(self):
        ProgressTracking.objects.filter(simulation=self.simulation, state=ProgressTracking.State.CURRENT).update(
            state=ProgressTracking.State.PASSED,
            completed_at=timezone.now(),
        )

        response = self._submit(self.round_one_questions[0])
        self.assertRedirects(response, reverse("interviews:simulation", args=[self.simulation.id]))

        messages = [message.message for message in response.wsgi_request._messages]
        self.assertIn("Interview session updated in another tab.", messages)
        self.assertEqual(UserAnswer.objects.filter(simulation=self.simulation).count(), 0)

    @override_settings(GEMINI_API_KEY="test-key", GEMINI_MODEL="gemini-2.5-pro")
    @patch("google.genai.Client")
    def test_evaluate_round_uses_modern_genai_sdk(self, client_mock):
        response = client_mock.return_value.__enter__.return_value.models.generate_content.return_value
        response.text = """
        {
            "score": 84,
            "decision": "passed",
            "detailed_scores": {
                "technical_depth": 84,
                "communication": 82,
                "logic": 85,
                "clarity": 83,
                "confidence": 80,
                "company_alignment": 86
            },
            "strengths": ["structured reasoning"],
            "weaknesses": ["add sharper metrics"],
            "feedback": "Strong readiness signal with clear tradeoffs.",
            "improvement_roadmap": ["Practice concise metrics."],
            "company_benchmark": "Clear tradeoffs and implementation judgment."
        }
        """

        payload = evaluate_round(self.company, self.round_one, [self._answer_for_ai()])

        client_mock.assert_called_once_with(api_key="test-key")
        generate_content = client_mock.return_value.__enter__.return_value.models.generate_content
        self.assertEqual(generate_content.call_args.kwargs["model"], "gemini-2.5-pro")
        self.assertEqual(payload["raw"]["raw_score"], 84)
        self.assertLessEqual(payload["score"], 70)
        self.assertEqual(payload["decision"], "passed")
        self.assertEqual(payload["strengths"], ["Structured reasoning"])
        self.assertEqual(payload["improvement_roadmap"], ["Practice concise metrics."])

    @override_settings(GEMINI_API_KEY="test-key", GEMINI_MODEL="gemini-2.5-pro")
    @patch("google.genai.Client")
    def test_evaluate_round_falls_back_when_genai_fails(self, client_mock):
        client_mock.return_value.__enter__.return_value.models.generate_content.side_effect = RuntimeError("api failed")

        payload = evaluate_round(self.company, self.round_one, [self._answer_for_ai()])

        self.assertEqual(payload["raw"]["provider"], "local_fallback")
        self.assertIn("Gemini evaluation failed gracefully", payload["feedback"])
        self.assertIn("strengths", payload)
        self.assertIn("weaknesses", payload)

    def test_invalid_answers_receive_very_low_scores(self):
        answer = SimpleNamespace(answer_text="https://spam.example.com", time_spent_seconds=4)

        payload = evaluate_round(self.company, self.round_one, [answer])

        self.assertEqual(payload["decision"], "failed")
        self.assertLessEqual(payload["score"], 15)
        self.assertIn("URL-only", payload["weaknesses"][0])

    def test_strong_dsa_answer_can_clear_mercedes_style_threshold(self):
        self.company.name = "Mercedes-Benz"
        self.company.benchmark_description = (
            "Mercedes-Benz benchmark favors precise reasoning, strong fundamentals, scalable design instincts, "
            "and thoughtful behavioral evidence."
        )
        self.round_one.round_type = "dsa"
        self.round_one.pass_score = 72
        answer = SimpleNamespace(
            answer_text=(
                "First I would use a hash set because it gives O(n) lookup while scanning the array once. "
                "For example, for each value x I compute target minus x and check whether that complement already exists. "
                "If it exists, the pair is found; otherwise I insert x into the set and continue. This handles duplicates by "
                "checking before insert, so target 6 with values 3 and 3 only passes when the second 3 appears. The complexity "
                "is O(n) time and O(n) memory, which is a clear tradeoff against the O(n^2) nested-loop approach. I would test "
                "empty input, one element, negative numbers, duplicate values, and large arrays. In production I would also watch "
                "memory pressure and choose sorting plus two pointers if memory is more constrained than latency."
            ),
            time_spent_seconds=120,
        )

        payload = evaluate_round(self.company, self.round_one, [answer])

        self.assertEqual(payload["decision"], "passed")
        self.assertGreater(payload["score"], 72)
        self.assertLess(payload["score"], 96)

    def test_final_report_uses_adaptive_messaging_and_curated_resources(self):
        for question in self.round_one_questions + self.round_two_questions:
            self._submit(question)

        report = FinalReport.objects.get(simulation=self.simulation)
        self.assertIn(
            report.retry_recommendation,
            {
                "Core fundamentals need significant improvement before retrying.",
                "Focus on structured communication and foundational improvement before the next simulation.",
                "Strong progress demonstrated. A short focused revision cycle is recommended.",
                "Excellent readiness demonstrated with strong consistency across rounds.",
            },
        )
        urls = {item["url"] for item in report.recommended_resources}
        self.assertNotIn("https://www.interviewbit.com/", urls)
        self.assertNotIn("https://www.pramp.com/", urls)
        self.assertTrue(any("roadmap.sh" in url or "geeksforgeeks.org" in url or "star" in item["title"].lower() for item in report.recommended_resources for url in [item["url"]]))

    def test_timer_remaining_uses_backend_round_duration_and_retry_resets(self):
        progress = ProgressTracking.objects.select_related("round").get(simulation=self.simulation, round=self.round_one)

        self.assertGreater(progress.seconds_remaining, (self.round_one.time_limit_minutes * 60) - 10)

        expired_start = timezone.now() - timedelta(minutes=self.round_one.time_limit_minutes, seconds=30)
        progress.started_at = expired_start
        progress.save(update_fields=["started_at", "updated_at"])

        response = self.client.get(reverse("interviews:simulation", args=[self.simulation.id]))
        self.assertContains(response, "Progression Halted")

        self.simulation.refresh_from_db()
        retry = retry_simulation(self.user, self.simulation)
        retry_progress = ProgressTracking.objects.select_related("round").get(
            simulation=retry,
            round=retry.current_round,
            state=ProgressTracking.State.CURRENT,
        )

        self.assertIsNotNone(retry_progress.started_at)
        self.assertGreater(retry_progress.seconds_remaining, (retry_progress.round.time_limit_minutes * 60) - 10)
