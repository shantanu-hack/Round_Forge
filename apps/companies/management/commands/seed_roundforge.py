from django.core.management.base import BaseCommand
from django.utils.text import slugify

from apps.companies.models import Company, InterviewTrack
from apps.interviews.models import InterviewRound, Question


DATA = [
    {
        "name": "Mercedes-Benz",
        "tagline": "Precision-led engineering readiness across logic, fundamentals, systems, and behavior.",
        "description": "A demanding simulation track for analytical, systems-oriented candidates who need to show engineering depth, structured tradeoffs, and precision under time pressure.",
        "evaluation_style": "Analytical, systems-oriented, engineering-heavy, precision-driven, and difficult. Answers should expose reasoning, tradeoffs, correctness, and disciplined communication.",
        "benchmark_description": "Mercedes-Benz benchmark favors precise reasoning, strong fundamentals, scalable design instincts, and thoughtful behavioral evidence.",
        "pass_threshold": 72,
        "accent_color": "#9fbfff",
        "order": 1,
        "rounds": [
            ("Aptitude + Logic", "aptitude", 10, 70, "Solve concise reasoning prompts with clear steps and no guesswork.", [
                ("A production line improves throughput by 20%, then loses 10% due to rework. Explain the net throughput change and reasoning.", "aptitude", "Looks for percentage reasoning and clarity."),
                ("You have three sensors reporting inconsistent values. How would you identify the most reliable signal?", "logic", "Looks for hypothesis testing, validation, and systematic elimination."),
            ]),
            ("Technical Fundamentals", "technical", 12, 72, "Explain fundamentals with correctness and engineering context.", [
                ("Explain indexing in databases and when an index can make performance worse.", "dbms", "Looks for tradeoffs, writes, storage, and selectivity."),
                ("Describe how HTTP differs from WebSockets and when each is appropriate.", "networking", "Looks for protocol understanding and use-case mapping."),
            ]),
            ("DSA + Problem Solving", "dsa", 14, 72, "State approach, complexity, and edge cases.", [
                ("Given an array of integers, explain how you would detect whether any pair sums to a target in better than O(n^2).", "dsa", "Looks for hash-set approach, complexity, and duplicates."),
                ("How would you find the first non-repeating character in a stream-like input?", "dsa", "Looks for data structure choice and streaming constraints."),
            ]),
            ("System Design", "system_design", 16, 74, "Design for reliability, observability, and tradeoffs.", [
                ("Design a telemetry ingestion service for connected vehicles sending periodic health data.", "system design", "Looks for ingestion, queues, storage, scale, and reliability."),
                ("How would you make a vehicle diagnostics dashboard resilient during traffic spikes?", "system design", "Looks for caching, backpressure, graceful degradation, and monitoring."),
            ]),
            ("HR + Behavioral", "hr", 10, 70, "Use structured examples and reflective judgment.", [
                ("Tell us about a time you found a defect late and how you handled the communication.", "communication", "Looks for ownership, clarity, and prevention."),
                ("How do you balance speed and precision when an engineering deadline is tight?", "behavioral", "Looks for decision-making and stakeholder communication."),
            ]),
        ],
    },
    {
        "name": "Infosys",
        "tagline": "Structured enterprise-readiness simulation for communication, fundamentals, and process clarity.",
        "description": "A focused simulation track for candidates who need clear communication, scalable enterprise thinking, and process-oriented delivery.",
        "evaluation_style": "Communication-focused, structured, scalable enterprise style, and process-oriented. Answers should be clear, organized, and grounded in practical implementation.",
        "benchmark_description": "Infosys benchmark favors clear articulation, solid fundamentals, process discipline, and dependable client-facing communication.",
        "pass_threshold": 68,
        "accent_color": "#7de8c9",
        "order": 2,
        "rounds": [
            ("Aptitude", "aptitude", 10, 66, "Show structured quantitative and logical reasoning.", [
                ("A task takes 12 people 8 days. Explain how you estimate the time for 16 people assuming ideal scaling.", "aptitude", "Looks for proportional reasoning and assumptions."),
                ("A client report has conflicting totals. What steps would you take before escalating?", "logic", "Looks for validation, reconciliation, and communication."),
            ]),
            ("Technical", "technical", 12, 68, "Explain fundamentals in a clean enterprise delivery style.", [
                ("Explain the difference between a primary key and a foreign key with a practical example.", "dbms", "Looks for relational clarity and example quality."),
                ("How would you debug a Django page that is slow after a database query change?", "technical", "Looks for measurement, query inspection, indexing, and caching."),
            ]),
            ("HR", "hr", 10, 68, "Use clear examples and professional communication.", [
                ("Describe a time you learned a new technology quickly for a project.", "communication", "Looks for learning structure and execution."),
                ("How would you handle unclear requirements from a client or project lead?", "process", "Looks for clarification, documentation, and alignment."),
            ]),
        ],
    },
]


class Command(BaseCommand):
    help = "Seed Round Forge with the two supported company simulations."

    def handle(self, *args, **options):
        supported_slugs = [slugify(item["name"]) for item in DATA]
        Company.objects.exclude(slug__in=supported_slugs).update(is_active=False)

        for company_data in DATA:
            rounds = company_data["rounds"]
            company_defaults = {key: value for key, value in company_data.items() if key != "rounds"}
            company, _ = Company.objects.update_or_create(
                slug=slugify(company_data["name"]),
                defaults={**company_defaults, "is_active": True},
            )
            track, _ = InterviewTrack.objects.update_or_create(
                company=company,
                slug="primary",
                defaults={
                    "name": f"{company.name} Readiness Track",
                    "description": f"Company-specific readiness flow for {company.name}.",
                    "is_active": True,
                },
            )
            for order, (name, round_type, minutes, pass_score, instructions, questions) in enumerate(rounds, start=1):
                interview_round, _ = InterviewRound.objects.update_or_create(
                    track=track,
                    round_order=order,
                    defaults={
                        "name": name,
                        "round_type": round_type,
                        "instructions": instructions,
                        "time_limit_minutes": minutes,
                        "pass_score": pass_score,
                        "max_questions": 2,
                    },
                )
                existing = list(interview_round.questions.order_by("id"))
                for index, (prompt, competency, expected_signal) in enumerate(questions):
                    if index < len(existing):
                        question = existing[index]
                        question.prompt = prompt
                        question.competency = competency
                        question.expected_signal = expected_signal
                        question.difficulty = "medium"
                        question.is_active = True
                        question.save()
                    else:
                        Question.objects.create(
                            round=interview_round,
                            prompt=prompt,
                            competency=competency,
                            difficulty="medium",
                            expected_signal=expected_signal,
                        )
                interview_round.questions.exclude(prompt__in=[item[0] for item in questions]).update(is_active=False)
            self.stdout.write(self.style.SUCCESS(f"Seeded {company.name}"))

        self.stdout.write(self.style.SUCCESS("Round Forge seed complete."))
