from backend.database.connection import SessionLocal

from backend.models.category import Category
from backend.models.prize import Prize
from backend.models.laureate import Laureate
from backend.models.laureate_prize import LaureatePrize
from backend.models.discovery import Discovery
from backend.models.quiz_question import QuizQuestion

from backend.repositories.quiz_question_repository import (
    create,
    get_by_id,
    get_by_discovery,
    get_by_discovery_and_level,
    update,
    delete,
)


def test_quiz_question_repository():
    db = SessionLocal()

    try:
        category = Category(
            name="Repository Test Quiz Category",
            description="Temporary category"
        )

        prize = Prize(
            year=2024,
            motivation="Temporary Nobel prize",
            category=category
        )

        laureate = Laureate(
            full_name="Test Quiz Laureate",
            laureate_type="Person",
            featured=True
        )

        laureate_prize = LaureatePrize(
            laureate=laureate,
            prize=prize,
            prize_share="1/1"
        )

        discovery = Discovery(
            laureate_prize=laureate_prize,
            title="Test Quiz Discovery",
            summary="Temporary discovery",
            significance="Temporary significance"
        )

        db.add(category)
        db.flush()

        # CREATE
        simple_question = QuizQuestion(
            discovery=discovery,
            level="Simple",
            question="What is the main idea?",
            choice_a="Choice A",
            choice_b="Choice B",
            choice_c="Choice C",
            choice_d="Choice D",
            correct_answer="A",
            answer_explanation="Choice A is correct."
        )

        created_simple = create(
            db,
            simple_question
        )

        # Create and persist each child in sequence. Attaching both transient
        # questions to the persistent discovery before adding either child to
        # the session caused SQLAlchemy's relationship warning.
        advanced_question = QuizQuestion(
            discovery=discovery,
            level="Advanced",
            question="What is the advanced concept?",
            choice_a="Choice A",
            choice_b="Choice B",
            choice_c="Choice C",
            choice_d="Choice D",
            correct_answer="B",
            answer_explanation="Choice B is correct."
        )

        created_advanced = create(
            db,
            advanced_question
        )

        print(
            "Created Questions:",
            created_simple.question_id,
            created_advanced.question_id
        )

        # READ BY ID
        found_question = get_by_id(
            db,
            created_simple.question_id
        )

        print(
            "Found Question:",
            found_question.question
        )

        # READ ALL QUESTIONS FOR DISCOVERY
        discovery_questions = get_by_discovery(
            db,
            discovery.discovery_id
        )

        print(
            "Questions found for discovery:",
            len(discovery_questions)
        )

        # READ BY DISCOVERY AND LEVEL
        advanced_questions = get_by_discovery_and_level(
            db,
            discovery.discovery_id,
            "Advanced"
        )

        print(
            "Advanced questions found:",
            len(advanced_questions)
        )

        print(
            "Advanced Question:",
            advanced_questions[0].question
        )

        # UPDATE
        updated_question = update(
            db,
            found_question,
            level="Simple",
            question_text="Updated simple question?",
            choice_a="Updated A",
            choice_b="Updated B",
            choice_c="Updated C",
            choice_d="Updated D",
            correct_answer="C",
            answer_explanation="Updated answer explanation."
        )

        print(
            "Updated Question:",
            updated_question.question
        )

        print(
            "Updated Correct Answer:",
            updated_question.correct_answer
        )

        # DELETE
        delete(
            db,
            updated_question
        )

        deleted_question = get_by_id(
            db,
            updated_question.question_id
        )

        print(
            "Question after delete:",
            deleted_question
        )

        print(
            "\nQuizQuestion repository CRUD test passed."
        )

    finally:
        db.rollback()
        db.close()


if __name__ == "__main__":
    test_quiz_question_repository()
    
