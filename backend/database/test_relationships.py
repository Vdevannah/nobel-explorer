from backend.database.connection import SessionLocal
from backend.models import (
    Category,
    Prize,
    Laureate,
    LaureatePrize,
    Discovery,
    Application,
    Explanation,
    QuizQuestion,
)


def test_relationships():
    db = SessionLocal()

    try:
        category = Category(
            name="Test Chemistry",
            description="Temporary test category",
        )

        prize = Prize(
            year=2023,
            motivation="Temporary test motivation",
            category=category,
        )

        laureate = Laureate(
            full_name="Test Laureate",
            birth_country="Test Country",
            featured=True,
        )

        laureate_prize = LaureatePrize(
            laureate=laureate,
            prize=prize,
            prize_share="1/2",
        )

        discovery = Discovery(
            laureate_prize=laureate_prize,
            title="Test Discovery",
            summary="Temporary discovery used for ORM testing",
        )

        application = Application(
            discovery=discovery,
            title="Test Application",
            description="Temporary real-world application",
        )

        explanation = Explanation(
            application=application,
            level="Simple",
            explanation_text="Temporary explanation",
        )

        quiz_question = QuizQuestion(
            discovery=discovery,
            level="Simple",
            question="What is being tested?",
            choice_a="ORM relationships",
            choice_b="HTML",
            choice_c="CSS",
            choice_d="JavaScript",
            correct_answer="A",
        )

        db.add(category)
        db.commit()

        print("Category:", category.name)
        print("Prize:", category.prizes[0].year)
        print("Prize category:", prize.category.name)
        print("Laureate:", prize.laureate_prizes[0].laureate.full_name)
        print("Discovery:", laureate_prize.discoveries[0].title)
        print("Application:", discovery.applications[0].title)
        print("Explanation:", application.explanations[0].explanation_text)
        print("Quiz:", discovery.quiz_questions[0].question)

        print("\nORM relationships are working successfully.")

    finally:
        db.rollback()
        db.close()


if __name__ == "__main__":
    test_relationships()