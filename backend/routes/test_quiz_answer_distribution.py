"""Regression coverage for the "every correct answer is A" fix.

Exercises the real, committed Einstein (contributions 38/39), mRNA
(contribution 609), and click chemistry (contribution 779) quiz data through
the actual HTTP routes -- both to prove the balanced A/B/C/D distribution
landed correctly in the seeded data, and to prove answer checking still
works correctly for questions whose correct answer is no longer "A" after
the reordering.
"""
from collections import Counter

from fastapi.testclient import TestClient

from backend.database.connection import SessionLocal
from backend.main import app
from backend.repositories import quiz_question_repository


client = TestClient(app)

DASHBOARD_CONTRIBUTIONS = (38, 39, 609, 779)


def test_every_quiz_question_has_exactly_one_valid_correct_answer():
    db = SessionLocal()
    try:
        for contribution_id in DASHBOARD_CONTRIBUTIONS:
            questions = quiz_question_repository.get_by_contribution(
                db, contribution_id
            )
            assert len(questions) == 12, contribution_id
            for question in questions:
                assert question.correct_answer in {"A", "B", "C", "D"}
                correct_text = getattr(
                    question, f"choice_{question.correct_answer.lower()}"
                )
                assert correct_text and correct_text.strip()
    finally:
        db.close()


def test_each_twelve_question_set_uses_a_balanced_answer_distribution():
    # Deterministic, seed-authored balance: exactly 3 of each letter per
    # 12-question contribution set -- not merely "more than one position".
    db = SessionLocal()
    try:
        for contribution_id in DASHBOARD_CONTRIBUTIONS:
            questions = quiz_question_repository.get_by_contribution(
                db, contribution_id
            )
            distribution = Counter(q.correct_answer for q in questions)
            assert distribution == {"A": 3, "B": 3, "C": 3, "D": 3}, (
                contribution_id,
                distribution,
            )
    finally:
        db.close()


def test_answer_checking_works_for_reordered_non_a_correct_answers():
    db = SessionLocal()
    try:
        # Pick one question per contribution whose correct answer is NOT A,
        # to specifically prove checking survived the reordering (not just
        # the historically-untouched "still A" cases).
        for contribution_id in DASHBOARD_CONTRIBUTIONS:
            questions = quiz_question_repository.get_by_contribution(
                db, contribution_id
            )
            non_a_question = next(
                q for q in questions if q.correct_answer != "A"
            )

            correct_response = client.post(
                f"/quiz-questions/{non_a_question.question_id}/check",
                json={"selected_answer": non_a_question.correct_answer},
            )
            assert correct_response.status_code == 200
            assert correct_response.json()["correct"] is True
            assert (
                correct_response.json()["correct_answer"]
                == non_a_question.correct_answer
            )

            wrong_letter = next(
                letter
                for letter in ("A", "B", "C", "D")
                if letter != non_a_question.correct_answer
            )
            incorrect_response = client.post(
                f"/quiz-questions/{non_a_question.question_id}/check",
                json={"selected_answer": wrong_letter},
            )
            assert incorrect_response.status_code == 200
            assert incorrect_response.json()["correct"] is False
    finally:
        db.close()


def test_public_quiz_api_still_hides_correct_answers_after_reordering():
    for contribution_id in DASHBOARD_CONTRIBUTIONS:
        response = client.get(f"/contributions/{contribution_id}/quiz")
        assert response.status_code == 200
        questions = response.json()
        assert len(questions) == 12
        for question in questions:
            assert "correct_answer" not in question
            assert "answer_explanation" not in question
            assert {
                "question_id",
                "contribution_id",
                "level",
                "question",
                "choice_a",
                "choice_b",
                "choice_c",
                "choice_d",
            } == set(question.keys())
