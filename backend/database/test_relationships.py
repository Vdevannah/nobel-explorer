from backend.models.contribution_laureate import ContributionLaureate
from backend.database.connection import SessionLocal
from backend.models import (
    Category,
    Prize,
    Laureate,
    LaureatePrize,
    Contribution,
    Connection,
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
            category=category,
        )

        laureate = Laureate(
            nobel_laureate_id="TEST-001",
            full_name="Test Laureate",
            laureate_type="Person",
            birth_country="Test Country",
            featured=True,
        )

        laureate_prize = LaureatePrize(
            laureate=laureate,
            prize=prize,
            prize_share="1/2",
            motivation="Temporary test motivation",
        )

        contribution = Contribution(
            credited_laureates=[ContributionLaureate(laureate=laureate, laureate_prize=laureate_prize)],

            contribution_type="NOBEL_LINKED",
            title="Test Contribution",
            summary="Temporary contribution used for ORM testing",
        )

        connection = Connection(
            contribution=contribution,
            connection_type="APPLICATION",
            title="Test Connection",
            description="Temporary real-world application",
        )

        explanation = Explanation(
            contribution=contribution,
            level="Simple",
            explanation_text="Temporary explanation",
        )

        quiz_question = QuizQuestion(
            contribution=contribution,
            level="Simple",
            question="What is being tested?",
            choice_a="ORM relationships",
            choice_b="HTML",
            choice_c="CSS",
            choice_d="JavaScript",
            correct_answer="A",
        )

        db.add(category)
        db.flush()

        print("Category:", category.name)
        print("Prize:", category.prizes[0].year)
        print("Prize category:", prize.category.name)
        print("Laureate:", prize.laureate_prizes[0].laureate.full_name)
        print("Contribution:", laureate_prize.contribution_attributions[0].contribution.title)
        print("Connection:", contribution.connections[0].title)
        print("Explanation:", contribution.explanations[0].explanation_text)
        print("Quiz:", contribution.quiz_questions[0].question)

        print("\nORM relationships are working successfully.")

    finally:
        db.rollback()
        db.close()


if __name__ == "__main__":
    test_relationships()
