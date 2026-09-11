from sqlalchemy.orm import Session

from backend.database.connection import SessionLocal
from backend.repositories import (
    category_repository,
    connection_repository,
    contribution_repository,
    explanation_repository,
    laureate_prize_repository,
    laureate_repository,
    prize_repository,
    quiz_question_repository,
)
from backend.schemas.connection import ConnectionCreate, ConnectionUpdate
from backend.schemas.contribution import ContributionCreate, ContributionUpdate
from backend.schemas.explanation import ExplanationCreate, ExplanationUpdate
from backend.schemas.quiz_question import QuizQuestionCreate, QuizQuestionUpdate
from backend.services import (
    connection_service,
    contribution_service,
    explanation_service,
    quiz_question_service,
)


BERTOZZI_NOBEL_ID = "1015"
MELDAL_NOBEL_ID = "1016"
SHARPLESS_NOBEL_ID = "743"

NOBEL_2022_SUMMARY_URL = "https://www.nobelprize.org/prizes/chemistry/2022/summary/"
NOBEL_2022_PRESS_RELEASE_URL = "https://www.nobelprize.org/prizes/chemistry/2022/press-release/"
NOBEL_2022_ADVANCED_URL = "https://www.nobelprize.org/prizes/chemistry/2022/advanced-information/"

# Sourcing intentionally stays on NobelPrize.org's own 2022 Chemistry
# materials (summary, press release, advanced information), matching the
# approach already used for the 2023 Medicine contribution -- avoids citing
# secondary institutional URLs that cannot be verified from this
# environment.
SOURCE_AUDIT = {
    "Click Chemistry and Bioorthogonal Chemistry": (
        "NobelPrize.org documents the 2022 Chemistry award to Bertozzi, "
        "Meldal, and Sharpless for the development of click chemistry and "
        "bioorthogonal chemistry.",
        NOBEL_2022_SUMMARY_URL,
    ),
    "Visualizing Biomolecules in Living Systems": (
        "NobelPrize.org's popular science background describes how "
        "bioorthogonal chemistry lets researchers label and visualize "
        "biomolecules, including cell-surface glycans, in living systems.",
        NOBEL_2022_SUMMARY_URL,
    ),
    "Building Better Medicines": (
        "NobelPrize.org's press release and advanced information describe "
        "click chemistry's practical use in pharmaceutical development.",
        NOBEL_2022_ADVANCED_URL,
    ),
    "Targeted Cancer Research": (
        "NobelPrize.org's advanced scientific background discusses "
        "bioorthogonal chemistry's role in biomedical research, including "
        "strategies relevant to targeted cancer therapeutics.",
        NOBEL_2022_ADVANCED_URL,
    ),
}


CLICK_CHEMISTRY_EXPLANATIONS = [
    {
        "level": "Simple",
        "explanation_text": (
            "Imagine building something with LEGO pieces. Instead of making "
            "every piece from scratch, you choose pieces that easily snap "
            "together.\n\n"
            "Click chemistry works in a similar way. Chemists use molecular "
            "building blocks that can join together quickly and reliably.\n\n"
            "Barry Sharpless helped introduce this way of thinking about "
            "chemistry, and Sharpless and Morten Meldal developed an "
            "especially useful click reaction.\n\n"
            "Carolyn Bertozzi then found ways to perform special chemical "
            "reactions in living systems without disturbing the normal "
            "chemistry of cells. These are called bioorthogonal reactions.\n\n"
            "This lets scientists attach chemical tags to molecules in "
            "living systems so they can study what those molecules are "
            "doing."
        ),
        "key_concepts": (
            "Molecules\n"
            "Building blocks\n"
            "Click chemistry\n"
            "Living cells\n"
            "Chemical tags"
        ),
    },
    {
        "level": "Explore",
        "explanation_text": (
            "Chemists often need to connect molecules together, but "
            "traditional synthesis can require many reaction steps and can "
            "produce unwanted products.\n\n"
            "Click chemistry focuses on reactions that are simple, reliable "
            "and efficient.\n\n"
            "One particularly important example joins an azide with an "
            "alkyne. Morten Meldal and Barry Sharpless independently "
            "developed a copper-catalyzed version of this reaction that "
            "efficiently forms a stable triazole connection.\n\n"
            "Carolyn Bertozzi faced another challenge: how could scientists "
            "perform useful chemical reactions inside living systems?\n\n"
            "Because copper can be harmful to cells, her work helped "
            "establish bioorthogonal chemistry—reactions designed to occur "
            "in biological environments without interfering with the "
            "cell's normal chemistry.\n\n"
            "Scientists can use these reactions to label and follow "
            "biomolecules inside living systems."
        ),
        "key_concepts": (
            "Azide\n"
            "Alkyne\n"
            "Copper catalyst\n"
            "Triazole\n"
            "Bioorthogonal chemistry"
        ),
    },
    {
        "level": "Advanced",
        "explanation_text": (
            "A landmark click reaction is the copper(I)-catalyzed "
            "azide–alkyne cycloaddition (CuAAC). An azide and terminal "
            "alkyne react in the presence of Cu(I) to efficiently form a "
            "1,2,3-triazole.\n\n"
            "The reaction became powerful because chemical groups "
            "containing azides and alkynes can be attached to many "
            "different molecular structures and then selectively "
            "connected.\n\n"
            "However, CuAAC presents a problem for experiments in living "
            "systems because copper can be toxic.\n\n"
            "Bertozzi's work helped overcome this limitation through "
            "bioorthogonal chemistry. One important strategy uses strained "
            "cyclooctynes, whose ring strain makes them reactive enough to "
            "undergo azide–alkyne cycloaddition without a copper "
            "catalyst.\n\n"
            "This copper-free reaction can therefore be used to label "
            "biomolecules in biological environments.\n\n"
            "Bertozzi applied bioorthogonal approaches particularly to the "
            "study of glycans, complex carbohydrates found on cell "
            "surfaces."
        ),
        "key_concepts": (
            "CuAAC\n"
            "1,2,3-Triazole\n"
            "Cyclooctyne\n"
            "Ring strain\n"
            "Glycans"
        ),
    },
    {
        "level": "Expert",
        "explanation_text": (
            "CuAAC transformed the classical azide–alkyne cycloaddition "
            "into a highly useful synthetic transformation. Cu(I) "
            "catalysis greatly accelerates the reaction and provides "
            "strong regioselectivity toward the 1,4-disubstituted "
            "1,2,3-triazole.\n\n"
            "Its utility comes partly from the chemical compatibility of "
            "azides and alkynes: they can often function as relatively "
            "unobtrusive reactive handles within molecules containing many "
            "other functional groups.\n\n"
            "Applying CuAAC directly to living systems, however, is "
            "limited by copper-associated toxicity.\n\n"
            "Bioorthogonal chemistry addresses a broader challenge: "
            "designing mutually reactive chemical partners that can react "
            "selectively in complex biological environments while "
            "remaining largely inert toward endogenous biomolecules.\n\n"
            "Bertozzi and colleagues developed copper-free approaches "
            "including strain-promoted azide–alkyne cycloaddition (SPAAC). "
            "Ring strain in cyclooctyne derivatives increases their "
            "reactivity toward azides, allowing cycloaddition without "
            "Cu(I).\n\n"
            "This strategy enabled metabolic labeling approaches in which "
            "cells incorporate appropriately designed chemical reporters "
            "into biomolecules such as glycans. A complementary "
            "bioorthogonal probe can then react with that reporter, "
            "enabling visualization or tracking of biological processes."
        ),
        "key_concepts": (
            "SPAAC\n"
            "Chemoselectivity\n"
            "Metabolic labeling\n"
            "Chemical reporter\n"
            "Cyclooctyne"
        ),
    },
]


CLICK_CHEMISTRY_CONNECTIONS = [
    {
        "connection_type": "APPLICATION",
        "title": "Visualizing Biomolecules in Living Systems",
        "description": (
            "Bioorthogonal chemical tags allow researchers to label "
            "biomolecules and observe where they appear and how they "
            "change in living systems. Bertozzi's work was especially "
            "important for making previously difficult-to-study "
            "cell-surface glycans visible."
        ),
        "source_name": "NobelPrize.org",
        "source_url": NOBEL_2022_SUMMARY_URL,
    },
    {
        "connection_type": "APPLICATION",
        "title": "Building Better Medicines",
        "description": (
            "Click chemistry provides a practical, reliable way to connect "
            "molecular building blocks, including targeting or delivery "
            "features such as antibodies or sugars. This has made it "
            "useful in pharmaceutical development, helping researchers "
            "build and modify drug candidates on the path toward new "
            "medicines."
        ),
        "source_name": "NobelPrize.org",
        "source_url": NOBEL_2022_ADVANCED_URL,
        "match_title": "Building Pharmaceuticals and New Materials",
    },
    {
        "connection_type": "APPLICATION",
        "title": "Targeted Cancer Research",
        "description": (
            "Bioorthogonal chemistry has contributed to research "
            "strategies for improving how cancer therapeutics can be "
            "targeted and activated. This is an area of biomedical "
            "research and therapeutic development, not a claim that "
            "bioorthogonal chemistry itself is a cancer cure."
        ),
        "source_name": "NobelPrize.org",
        "source_url": NOBEL_2022_ADVANCED_URL,
    },
]


CLICK_CHEMISTRY_QUIZ = [
    {
        "level": "Simple",
        "question": "What does click chemistry help chemists do?",
        "choice_a": "Join molecular building blocks together quickly and reliably",
        "choice_b": "Break all molecules into individual atoms",
        "choice_c": "Remove color from chemicals",
        "choice_d": "Freeze molecules so they cannot move",
        "correct_answer": "A",
        "answer_explanation": (
            "Click chemistry uses reactions that let building blocks snap "
            "together quickly and reliably, similar to how LEGO pieces fit "
            "together."
        ),
    },
    {
        "level": "Simple",
        "question": "What is a bioorthogonal reaction?",
        "choice_a": "A reaction that destroys living cells",
        "choice_b": "A reaction that can happen inside living systems without disturbing normal cell chemistry",
        "choice_c": "A reaction that only happens in outer space",
        "choice_d": "A reaction that changes a cell's DNA",
        "correct_answer": "B",
        "answer_explanation": (
            "Bioorthogonal reactions are designed to occur in living "
            "systems without interfering with the cell's normal "
            "chemistry."
        ),
    },
    {
        "level": "Simple",
        "question": "Why are chemical tags useful in living systems?",
        "choice_a": "They make cells stop working",
        "choice_b": "They replace a cell's normal food",
        "choice_c": "They let scientists see what certain molecules are doing",
        "choice_d": "They turn cells into a different color permanently",
        "correct_answer": "C",
        "answer_explanation": (
            "Chemical tags attached through bioorthogonal reactions let "
            "scientists study what specific molecules are doing inside "
            "living systems."
        ),
    },
    {
        "level": "Explore",
        "question": "Which two chemical groups are joined in the important click reaction introduced in this lesson?",
        "choice_a": "Alcohol and ketone",
        "choice_b": "Amine and carboxylic acid",
        "choice_c": "Alkene and alcohol",
        "choice_d": "Azide and alkyne",
        "correct_answer": "D",
        "answer_explanation": (
            "An azide and an alkyne are the two partners in the important "
            "click reaction discussed here."
        ),
        "match_question": "What problem can traditional chemical synthesis have that click chemistry tries to avoid?",
    },
    {
        "level": "Explore",
        "question": "What does the copper-catalyzed azide–alkyne reaction form?",
        "choice_a": "A stable triazole connection.",
        "choice_b": "A protein.",
        "choice_c": "A carbohydrate.",
        "choice_d": "DNA.",
        "correct_answer": "A",
        "answer_explanation": (
            "The copper-catalyzed reaction efficiently connects azides and "
            "alkynes through a triazole product."
        ),
        "match_question": "What two chemical groups react together in the click reaction developed by Meldal and Sharpless?",
    },
    {
        "level": "Explore",
        "question": "Why did Bertozzi need an alternative to the copper-catalyzed click reaction for living systems?",
        "choice_a": "Copper makes reactions too slow",
        "choice_b": "Copper can be harmful to living cells",
        "choice_c": "Copper cannot form triazoles",
        "choice_d": "Copper only reacts with metals",
        "correct_answer": "B",
        "answer_explanation": (
            "Copper can be toxic to cells, so Bertozzi's bioorthogonal "
            "chemistry needed reactions that avoid a copper catalyst."
        ),
    },
    {
        "level": "Advanced",
        "question": "What does CuAAC stand for, and what does it require?",
        "choice_a": "A reaction requiring no catalyst at all",
        "choice_b": "A reaction between two alkynes",
        "choice_c": "Copper(I)-catalyzed azide-alkyne cycloaddition",
        "choice_d": "A reaction that only occurs at very high temperatures",
        "correct_answer": "C",
        "answer_explanation": (
            "CuAAC is the copper(I)-catalyzed azide-alkyne cycloaddition, "
            "which efficiently forms a 1,2,3-triazole."
        ),
    },
    {
        "level": "Advanced",
        "question": "What property of cyclooctynes allows azide-alkyne cycloaddition without a copper catalyst?",
        "choice_a": "Their bright color",
        "choice_b": "Their large size",
        "choice_c": "Their high melting point",
        "choice_d": "Their ring strain",
        "correct_answer": "D",
        "answer_explanation": (
            "The ring strain in cyclooctynes makes them reactive enough to "
            "undergo cycloaddition with azides without needing a copper "
            "catalyst."
        ),
    },
    {
        "level": "Advanced",
        "question": "What cell-surface molecules did Bertozzi's bioorthogonal methods particularly help study?",
        "choice_a": "Glycans",
        "choice_b": "Metals",
        "choice_c": "Salts",
        "choice_d": "Solvents",
        "correct_answer": "A",
        "answer_explanation": (
            "Bertozzi applied bioorthogonal chemistry approaches "
            "particularly to the study of glycans, the complex "
            "carbohydrates found on cell surfaces."
        ),
    },
    {
        "level": "Expert",
        "question": "What regiochemical outcome does Cu(I) catalysis favor in the azide-alkyne cycloaddition?",
        "choice_a": "A random mixture of triazole isomers",
        "choice_b": "The 1,4-disubstituted 1,2,3-triazole",
        "choice_c": "The 1,5-disubstituted 1,2,3-triazole exclusively",
        "choice_d": "No triazole forms at all",
        "correct_answer": "B",
        "answer_explanation": (
            "Cu(I) catalysis greatly accelerates the reaction and provides "
            "strong regioselectivity toward the 1,4-disubstituted "
            "1,2,3-triazole."
        ),
    },
    {
        "level": "Expert",
        "question": "What is the core design goal of bioorthogonal chemistry, more broadly defined?",
        "choice_a": "To maximize reactivity with every biomolecule in a cell",
        "choice_b": "To eliminate the need for any chemical labeling",
        "choice_c": "To design mutually reactive chemical partners that react selectively without disturbing endogenous biomolecules",
        "choice_d": "To replace all enzymes in a cell with synthetic catalysts",
        "correct_answer": "C",
        "answer_explanation": (
            "Bioorthogonal chemistry aims to design chemical partners that "
            "react selectively with each other in complex biological "
            "environments while remaining largely inert toward the cell's "
            "own biomolecules."
        ),
    },
    {
        "level": "Expert",
        "question": "In metabolic labeling with SPAAC, what happens after a cell incorporates a chemical reporter into a biomolecule such as a glycan?",
        "choice_a": "The reporter immediately destroys the biomolecule",
        "choice_b": "The cell stops producing that biomolecule",
        "choice_c": "The reporter cannot be detected under any circumstances",
        "choice_d": "A complementary bioorthogonal probe can react with the reporter to enable visualization or tracking",
        "correct_answer": "D",
        "answer_explanation": (
            "A complementary bioorthogonal probe can react selectively "
            "with the incorporated chemical reporter, enabling "
            "visualization or tracking of the biological process."
        ),
    },
]


def _require_existing_nobel_data(db: Session):
    bertozzi = laureate_repository.get_by_nobel_id(db, BERTOZZI_NOBEL_ID)
    if bertozzi is None or bertozzi.full_name != "Carolyn R. Bertozzi":
        raise RuntimeError("Carolyn R. Bertozzi Nobel ID 1015 was not found as expected")

    meldal = laureate_repository.get_by_nobel_id(db, MELDAL_NOBEL_ID)
    if meldal is None or meldal.full_name != "Morten Meldal":
        raise RuntimeError("Morten Meldal Nobel ID 1016 was not found as expected")

    sharpless = laureate_repository.get_by_nobel_id(db, SHARPLESS_NOBEL_ID)
    if sharpless is None or sharpless.full_name != "K. Barry Sharpless":
        raise RuntimeError("K. Barry Sharpless Nobel ID 743 was not found as expected")

    chemistry = category_repository.get_by_name(db, "Chemistry")
    if chemistry is None:
        raise RuntimeError("Chemistry category was not found")

    prize_2022 = prize_repository.get_by_year_and_category(
        db, 2022, chemistry.category_id
    )
    if prize_2022 is None:
        raise RuntimeError("The 2022 Chemistry prize must already exist")

    bertozzi_prize = laureate_prize_repository.get_by_laureate_and_prize(
        db, bertozzi.laureate_id, prize_2022.prize_id
    )
    meldal_prize = laureate_prize_repository.get_by_laureate_and_prize(
        db, meldal.laureate_id, prize_2022.prize_id
    )
    sharpless_prize = laureate_prize_repository.get_by_laureate_and_prize(
        db, sharpless.laureate_id, prize_2022.prize_id
    )
    if bertozzi_prize is None or meldal_prize is None or sharpless_prize is None:
        raise RuntimeError(
            "Bertozzi's, Meldal's, and Sharpless's 2022 Chemistry "
            "LaureatePrize rows were not found"
        )

    motivation = (bertozzi_prize.motivation or "").lower()
    if "click chemistry" not in motivation or "bioorthogonal" not in motivation:
        raise RuntimeError(
            "Bertozzi's stored Nobel motivation did not mention click "
            "chemistry and bioorthogonal chemistry"
        )
    if not (
        meldal_prize.prize_id == bertozzi_prize.prize_id
        and sharpless_prize.prize_id == bertozzi_prize.prize_id
    ):
        raise RuntimeError(
            "Bertozzi's, Meldal's, and Sharpless's LaureatePrize rows do "
            "not resolve to the same prize"
        )

    return bertozzi, bertozzi_prize, meldal, meldal_prize, sharpless, sharpless_prize, prize_2022


def _upsert_contribution(db: Session, data: ContributionCreate):
    contribution = contribution_repository.get_by_laureate_type_and_title(
        db, data.credited_laureates[0].laureate_id, data.contribution_type, data.title
    )
    if contribution is None:
        return contribution_service.create_contribution(db, data)
    return contribution_service.update_contribution(
        db,
        contribution.contribution_id,
        ContributionUpdate(**data.model_dump()),
    )


def _upsert_explanations(db: Session, contribution_id: int, rows: list[dict]):
    results = []
    for row in rows:
        data = ExplanationCreate(contribution_id=contribution_id, **row)
        explanation = explanation_repository.get_by_contribution_and_level(
            db, contribution_id, data.level
        )
        if explanation is None:
            explanation = explanation_service.create_explanation(db, data)
        else:
            explanation = explanation_service.update_explanation(
                db,
                explanation.explanation_id,
                ExplanationUpdate(**data.model_dump()),
            )
        results.append(explanation)
    return results


def _upsert_connections(db: Session, contribution_id: int, rows: list[dict]):
    results = []
    for row in rows:
        row = dict(row)
        legacy_title = row.pop("match_title", None)
        data = ConnectionCreate(contribution_id=contribution_id, **row)
        connection = connection_repository.get_by_contribution_type_and_title(
            db, contribution_id, data.connection_type, data.title
        )
        if connection is None and legacy_title is not None:
            connection = connection_repository.get_by_contribution_type_and_title(
                db, contribution_id, data.connection_type, legacy_title
            )
        if connection is None:
            connection = connection_service.create_connection(db, data)
        else:
            connection = connection_service.update_connection(
                db,
                connection.connection_id,
                ConnectionUpdate(**data.model_dump()),
            )
        results.append(connection)
    return results


def _upsert_quiz(db: Session, contribution_id: int, rows: list[dict]):
    results = []
    for row in rows:
        row = dict(row)
        legacy_question = row.pop("match_question", None)
        data = QuizQuestionCreate(contribution_id=contribution_id, **row)
        question = quiz_question_repository.get_by_contribution_and_question(
            db, contribution_id, data.question
        )
        if question is None and legacy_question is not None:
            question = quiz_question_repository.get_by_contribution_and_question(
                db, contribution_id, legacy_question
            )
        if question is None:
            question = quiz_question_service.create_quiz_question(db, data)
        else:
            question = quiz_question_service.update_quiz_question(
                db,
                question.question_id,
                QuizQuestionUpdate(**data.model_dump()),
            )
        results.append(question)
    return results


def seed_click_chemistry_education(db: Session) -> dict:
    (
        bertozzi,
        bertozzi_prize,
        meldal,
        meldal_prize,
        sharpless,
        sharpless_prize,
        prize_2022,
    ) = _require_existing_nobel_data(db)

    click_chemistry_contribution = _upsert_contribution(
        db,
        ContributionCreate(
            credited_laureates=[
                {
                    "laureate_id": bertozzi.laureate_id,
                    "laureate_prize_id": bertozzi_prize.laureate_prize_id,
                },
                {
                    "laureate_id": meldal.laureate_id,
                    "laureate_prize_id": meldal_prize.laureate_prize_id,
                },
                {
                    "laureate_id": sharpless.laureate_id,
                    "laureate_prize_id": sharpless_prize.laureate_prize_id,
                },
            ],
            contribution_type="NOBEL_LINKED",
            title="Click Chemistry and Bioorthogonal Chemistry",
            summary=(
                "Sharpless and Meldal developed a reliable copper-catalyzed "
                "click reaction joining azides and alkynes, and Bertozzi "
                "developed copper-free bioorthogonal versions that work "
                "safely inside living systems."
            ),
            significance=(
                "This work was recognized by the 2022 Chemistry Prize "
                "motivation: for the development of click chemistry and "
                "bioorthogonal chemistry. Click chemistry provides a "
                "simple, reliable way to connect molecular building "
                "blocks, and bioorthogonal chemistry extended this "
                "principle so equivalent reactions can occur inside living "
                "systems without disturbing normal cell chemistry."
            ),
            source_url=NOBEL_2022_SUMMARY_URL,
        ),
    )

    explanations = _upsert_explanations(
        db, click_chemistry_contribution.contribution_id, CLICK_CHEMISTRY_EXPLANATIONS
    )
    connections = _upsert_connections(
        db, click_chemistry_contribution.contribution_id, CLICK_CHEMISTRY_CONNECTIONS
    )
    quiz = _upsert_quiz(
        db, click_chemistry_contribution.contribution_id, CLICK_CHEMISTRY_QUIZ
    )

    return {
        "bertozzi_id": bertozzi.laureate_id,
        "bertozzi_laureate_prize_id": bertozzi_prize.laureate_prize_id,
        "meldal_id": meldal.laureate_id,
        "meldal_laureate_prize_id": meldal_prize.laureate_prize_id,
        "sharpless_id": sharpless.laureate_id,
        "sharpless_laureate_prize_id": sharpless_prize.laureate_prize_id,
        "prize_id": prize_2022.prize_id,
        "click_chemistry_contribution_id": click_chemistry_contribution.contribution_id,
        "explanations": len(explanations),
        "connections": len(connections),
        "quiz_questions": len(quiz),
    }


def print_source_audit() -> None:
    print("Authoritative source audit:")
    for title, (support, url) in SOURCE_AUDIT.items():
        print(f"- {title}: {support}")
        print(f"  {url}")


def main() -> None:
    print_source_audit()
    db = SessionLocal()
    try:
        result = seed_click_chemistry_education(db)
        db.commit()
        print("Click chemistry educational seed complete:", result)
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
