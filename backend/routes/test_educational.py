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

        invalid_level_response = client.get(
            f"/contributions/{contribution.contribution_id}/explanations",
            params={"level": "NotALevel"},
        )
        assert invalid_level_response.status_code == 422

        invalid_quiz_level_response = client.get(
            f"/contributions/{contribution.contribution_id}/quiz",
            params={"level": "NotALevel"},
        )
        assert invalid_quiz_level_response.status_code == 422
    finally:
        app.dependency_overrides.clear()
        db.rollback()
        db.close()


def test_quiz_answer_check_endpoint():
    db = SessionLocal()
    try:
        category = Category(name="Quiz Check Test Physics")
        prize = Prize(year=1930, category=category)
        laureate = Laureate(
            nobel_laureate_id="TEST-QUIZ-CHECK-001",
            full_name="Quiz Check Test Laureate",
            laureate_type="Person",
            featured=False,
        )
        laureate_prize = LaureatePrize(laureate=laureate, prize=prize)
        contribution = Contribution(
            laureate=laureate,
            laureate_prize=laureate_prize,
            contribution_type="NOBEL_LINKED",
            title="Quiz Check Contribution",
        )
        question = QuizQuestion(
            contribution=contribution,
            level="Simple",
            question="Which choice is correct?",
            choice_a="First",
            choice_b="Second",
            choice_c="Third",
            choice_d="Fourth",
            correct_answer="B",
            answer_explanation="Second is correct because of X.",
        )
        db.add_all([category, question])
        db.flush()

        def override_get_db():
            yield db

        app.dependency_overrides[get_db] = override_get_db
        client = TestClient(app)

        # correct answer
        correct_response = client.post(
            f"/quiz-questions/{question.question_id}/check",
            json={"selected_answer": "B"},
        )
        assert correct_response.status_code == 200
        correct_body = correct_response.json()
        assert correct_body == {
            "question_id": question.question_id,
            "correct": True,
            "correct_answer": "B",
            "answer_explanation": "Second is correct because of X.",
        }

        # incorrect answer
        incorrect_response = client.post(
            f"/quiz-questions/{question.question_id}/check",
            json={"selected_answer": "A"},
        )
        assert incorrect_response.status_code == 200
        incorrect_body = incorrect_response.json()
        assert incorrect_body["correct"] is False
        assert incorrect_body["correct_answer"] == "B"

        # invalid answer letter
        invalid_answer_response = client.post(
            f"/quiz-questions/{question.question_id}/check",
            json={"selected_answer": "Z"},
        )
        assert invalid_answer_response.status_code == 422

        # nonexistent question
        missing_response = client.post(
            "/quiz-questions/999999999/check",
            json={"selected_answer": "A"},
        )
        assert missing_response.status_code == 404

        # the public GET response must still never expose the answer key
        public_response = client.get(
            f"/contributions/{contribution.contribution_id}/quiz"
        )
        assert public_response.status_code == 200
        public_question = public_response.json()[0]
        assert "correct_answer" not in public_question
        assert "answer_explanation" not in public_question
    finally:
        app.dependency_overrides.clear()
        db.rollback()
        db.close()


def test_contributions_catalog_reflects_real_content():
    db = SessionLocal()
    try:
        category = Category(name="Educational Catalog Test Physics")
        prize = Prize(year=1954, category=category)
        laureate = Laureate(
            nobel_laureate_id="TEST-EDU-CATALOG-001",
            full_name="Catalog Test Laureate",
            laureate_type="Person",
            image_url="https://example.com/catalog-laureate.jpg",
            featured=False,
        )
        laureate_prize = LaureatePrize(laureate=laureate, prize=prize)

        nobel_linked = Contribution(
            laureate=laureate,
            laureate_prize=laureate_prize,
            contribution_type="NOBEL_LINKED",
            title="Catalog Nobel-Linked Contribution",
            summary="A nobel-linked summary.",
        )
        beyond_nobel = Contribution(
            laureate=laureate,
            contribution_type="BEYOND_NOBEL",
            title="Catalog Beyond-Nobel Contribution",
            summary="A beyond-nobel summary.",
        )

        simple_explanation = Explanation(
            contribution=nobel_linked,
            level="Simple",
            explanation_text="Simple text",
        )
        explore_explanation = Explanation(
            contribution=nobel_linked,
            level="Explore",
            explanation_text="Explore text",
        )
        beyond_explanation = Explanation(
            contribution=beyond_nobel,
            level="Simple",
            explanation_text="Simple beyond text",
        )

        quiz = QuizQuestion(
            contribution=nobel_linked,
            level="Simple",
            question="Catalog quiz question?",
            choice_a="A",
            choice_b="B",
            choice_c="C",
            choice_d="D",
            correct_answer="A",
        )

        db.add_all(
            [
                category,
                laureate,
                nobel_linked,
                beyond_nobel,
                simple_explanation,
                explore_explanation,
                beyond_explanation,
                quiz,
            ]
        )
        db.flush()

        def override_get_db():
            yield db

        app.dependency_overrides[get_db] = override_get_db
        client = TestClient(app)

        response = client.get("/contributions")
        assert response.status_code == 200

        catalog = response.json()
        by_id = {item["contribution_id"]: item for item in catalog}

        nobel_item = by_id[nobel_linked.contribution_id]
        assert nobel_item["title"] == "Catalog Nobel-Linked Contribution"
        assert nobel_item["summary"] == "A nobel-linked summary."
        assert nobel_item["contribution_type"] == "NOBEL_LINKED"
        assert nobel_item["laureate_id"] == laureate.laureate_id
        assert nobel_item["laureate_name"] == "Catalog Test Laureate"
        assert nobel_item["image_url"] == "https://example.com/catalog-laureate.jpg"
        assert nobel_item["category"] == "Educational Catalog Test Physics"
        assert nobel_item["prize_year"] == 1954
        assert nobel_item["available_levels"] == ["Simple", "Explore"]
        assert nobel_item["quiz_available"] is True

        beyond_item = by_id[beyond_nobel.contribution_id]
        assert beyond_item["contribution_type"] == "BEYOND_NOBEL"
        assert beyond_item["category"] is None
        assert beyond_item["prize_year"] is None
        assert beyond_item["available_levels"] == ["Simple"]
        assert beyond_item["quiz_available"] is False

        # every catalog item must expose the full expected shape
        expected_keys = {
            "contribution_id",
            "title",
            "summary",
            "contribution_type",
            "laureate_id",
            "laureate_name",
            "image_url",
            "category",
            "prize_year",
            "available_levels",
            "quiz_available",
        }
        assert expected_keys.issubset(nobel_item.keys())
    finally:
        app.dependency_overrides.clear()
        db.rollback()
        db.close()
