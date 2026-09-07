from fastapi.testclient import TestClient

from backend.database.connection import SessionLocal, get_db
from backend.main import app
from backend.models.category import Category
from backend.models.connection import Connection
from backend.models.contribution import Contribution
from backend.models.explanation import Explanation
from backend.models.laureate import Laureate
from backend.models.laureate_prize import LaureatePrize
from backend.models.prize import Prize
from backend.models.quiz_question import QuizQuestion


def test_educational_read_endpoints_and_quiz_safety():
    db = SessionLocal()
    try:
        category = Category(name="Educational Route Test Physics")
        prize = Prize(year=1921, category=category)
        related_prize = Prize(year=2017, category=category)
        laureate = Laureate(
            nobel_laureate_id="TEST-EDU-ROUTE-001",
            full_name="Educational Route Laureate",
            laureate_type="Person",
            featured=False,
        )
        laureate_prize = LaureatePrize(laureate=laureate, prize=prize)
        contribution = Contribution(
            laureate=laureate,
            laureate_prize=laureate_prize,
            contribution_type="NOBEL_LINKED",
            title="Photoelectric Test",
        )
        explanation = Explanation(
            contribution=contribution,
            level="Simple",
            explanation_text="Simple test explanation",
        )
        connection = Connection(
            contribution=contribution,
            connection_type="SCIENTIFIC_LEGACY",
            related_prize=related_prize,
            title="Later legacy",
        )
        question = QuizQuestion(
            contribution=contribution,
            level="Simple",
            question="Which answer is correct?",
            choice_a="First",
            choice_b="Second",
            choice_c="Third",
            choice_d="Fourth",
            correct_answer="A",
            answer_explanation="First is correct.",
        )
        db.add_all([category, related_prize, explanation, connection, question])
        db.flush()

        def override_get_db():
            yield db

        app.dependency_overrides[get_db] = override_get_db
        client = TestClient(app)

        laureate_response = client.get(
            f"/laureates/{laureate.laureate_id}/contributions"
        )
        assert laureate_response.status_code == 200
        assert laureate_response.json()[0]["title"] == "Photoelectric Test"

        detail_response = client.get(
            f"/contributions/{contribution.contribution_id}"
        )
        assert detail_response.status_code == 200
        assert detail_response.json()["explanations"][0]["level"] == "Simple"
        assert detail_response.json()["connections"][0]["related_prize"] == {
            "prize_id": related_prize.prize_id,
            "year": 2017,
            "category": "Educational Route Test Physics",
        }

        explanations_response = client.get(
            f"/contributions/{contribution.contribution_id}/explanations",
            params={"level": "Simple"},
        )
        assert explanations_response.status_code == 200
        assert len(explanations_response.json()) == 1

        level_response = client.get(
            f"/contributions/{contribution.contribution_id}/explanations/Simple"
        )
        assert level_response.status_code == 200

        connections_response = client.get(
            f"/contributions/{contribution.contribution_id}/connections"
        )
        assert connections_response.status_code == 200
        assert connections_response.json()[0]["related_prize_id"] == related_prize.prize_id

        quiz_response = client.get(
            f"/contributions/{contribution.contribution_id}/quiz"
        )
        assert quiz_response.status_code == 200
        public_question = quiz_response.json()[0]
        assert public_question["question"] == "Which answer is correct?"
        assert "correct_answer" not in public_question
        assert "answer_explanation" not in public_question

        missing_response = client.get("/contributions/999999999")
        assert missing_response.status_code == 404
    finally:
        app.dependency_overrides.clear()
        db.rollback()
        db.close()
