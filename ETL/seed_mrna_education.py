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


KARIKO_NOBEL_ID = "1024"
WEISSMAN_NOBEL_ID = "1025"

NOBEL_2023_SUMMARY_URL = "https://www.nobelprize.org/prizes/medicine/2023/summary/"
NOBEL_2023_PRESS_RELEASE_URL = "https://www.nobelprize.org/prizes/medicine/2023/press-release/"
NOBEL_2023_ADVANCED_URL = "https://www.nobelprize.org/prizes/medicine/2023/advanced-information/"

# All sourcing for this contribution intentionally stays on NobelPrize.org's
# own 2023 Physiology or Medicine materials (summary, press release, advanced
# information) rather than reaching for secondary institutional sources whose
# exact current URLs cannot be verified from this environment -- consistent
# with "Primary source: Official Nobel Prize 2023 Physiology or Medicine
# materials" and "do not overstate causality."
SOURCE_AUDIT = {
    "Nucleoside Base Modifications and mRNA Vaccines": (
        "NobelPrize.org documents the 2023 Physiology or Medicine award to "
        "Karikó and Weissman for discoveries concerning nucleoside base "
        "modifications that enabled effective mRNA vaccines against COVID-19.",
        NOBEL_2023_SUMMARY_URL,
    ),
    "mRNA Vaccines": (
        "NobelPrize.org's press release frames how the nucleoside-modification "
        "discovery became one of the enabling technologies behind mRNA "
        "vaccines deployed against COVID-19.",
        NOBEL_2023_PRESS_RELEASE_URL,
    ),
    "Therapeutic mRNA / Future Medicines": (
        "NobelPrize.org's advanced scientific background discusses the "
        "broader therapeutic potential of nucleoside-modified mRNA beyond "
        "vaccines.",
        NOBEL_2023_ADVANCED_URL,
    ),
    "Understanding Innate Immune Recognition of RNA": (
        "NobelPrize.org's popular science summary explains how the innate "
        "immune system's RNA-sensing pathways respond differently to "
        "modified versus unmodified synthetic RNA.",
        NOBEL_2023_SUMMARY_URL,
    ),
}


MRNA_EXPLANATIONS = [
    {
        "level": "Simple",
        "explanation_text": (
            "Our bodies are made of many kinds of proteins, and cells use temporary "
            "instruction messages called mRNA to know which proteins to build.\n\n"
            "Scientists learned how to make mRNA in a lab so a cell could use it "
            "like a recipe card. But at first, the body's defenses treated "
            "lab-made mRNA like an intruder and attacked it before the cell could "
            "finish reading it.\n\n"
            "Katalin Karikó and Drew Weissman discovered that changing one of the "
            "small building blocks in lab-made mRNA helped the body's defenses "
            "stay calm, so cells could actually read the message and make the "
            "protein it described.\n\n"
            "That discovery helped make effective mRNA vaccines possible, "
            "including the vaccines many people received during the COVID-19 "
            "pandemic."
        ),
        "key_concepts": (
            "mRNA carries temporary instructions for making a protein\n"
            "Lab-made mRNA can trigger an unwanted immune reaction\n"
            "Changing mRNA's building blocks helped make vaccines possible"
        ),
    },
    {
        "level": "Explore",
        "explanation_text": (
            "Cells follow a flow of information: DNA holds the master "
            "instructions, mRNA carries a temporary working copy of one "
            "instruction, and the cell's protein-making machinery reads that "
            "copy to build a specific protein.\n\n"
            "Scientists can manufacture mRNA in a lab -- called in vitro "
            "transcribed mRNA -- to instruct cells to make a chosen protein, "
            "including a piece of a virus the immune system could later "
            "recognize. But early lab-made mRNA triggered a strong, unwanted "
            "reaction from the innate immune system, the body's fast, "
            "general-purpose first line of defense. That reaction often "
            "destroyed the mRNA or shut down the cell's protein-making process "
            "before it could finish.\n\n"
            "Karikó and Weissman discovered that replacing a standard building "
            "block of mRNA, called a nucleoside, with a modified version -- most "
            "notably pseudouridine -- reduced this innate immune over-reaction. "
            "With the modification, cells tolerated the lab-made mRNA well enough "
            "to actually read it and produce the protein it encoded.\n\n"
            "This mattered enormously for vaccines: it meant scientists could "
            "deliver mRNA instructions for a viral protein, like the spike "
            "protein of the virus that causes COVID-19, and have cells produce "
            "that protein safely, training the immune system to recognize the "
            "real virus later."
        ),
        "key_concepts": (
            "DNA carries master instructions; mRNA is a temporary working copy\n"
            "The innate immune system can react strongly to lab-made mRNA\n"
            "Modified nucleosides reduce that reaction so cells can use the mRNA"
        ),
    },
    {
        "level": "Advanced",
        "explanation_text": (
            "In vitro transcribed (IVT) mRNA is synthesized outside a cell using "
            "purified enzymes, then delivered into cells so their own ribosomes "
            "translate it into protein. Early experiments showed that IVT mRNA "
            "delivered to dendritic cells -- key antigen-presenting cells of the "
            "innate immune system -- triggered strong activation and the release "
            "of inflammatory signaling molecules, even before any specific immune "
            "response had developed.\n\n"
            "Karikó and Weissman's experimental logic compared synthetic mRNA "
            "built from standard, unmodified nucleosides against mRNA in which "
            "one nucleoside, uridine, was replaced with a naturally occurring "
            "modified nucleoside, pseudouridine. Pseudouridine-containing mRNA "
            "dramatically reduced activation of dendritic cells and lowered the "
            "release of inflammatory signals, compared to unmodified mRNA.\n\n"
            "The mechanism traced to pattern-recognition receptors the innate "
            "immune system uses to detect foreign RNA, including Toll-like "
            "receptors that normally recognize RNA structures typical of "
            "viruses. Pseudouridine changes the RNA's structure in a way that "
            "reduces recognition by these receptors, dampening the inflammatory "
            "signaling cascade they would otherwise trigger.\n\n"
            "Because pseudouridine-modified mRNA avoided this early, "
            "non-specific attack, more of the delivered mRNA survived long "
            "enough for cells' translation machinery to produce the encoded "
            "protein at meaningfully higher levels. When that protein is an "
            "antigen -- a fragment of a pathogen, such as a viral spike protein "
            "-- its production inside the body's own cells allows the adaptive "
            "immune response to develop specific antibodies and memory T cells "
            "against it. This is the core principle of an mRNA vaccine.\n\n"
            "This discovery was foundational and enabling, but turning the "
            "principle into a deployed vaccine also required later advances "
            "such as lipid nanoparticle delivery and vaccine formulation."
        ),
        "key_concepts": (
            "In vitro transcribed mRNA is synthesized outside the cell, then "
            "translated by it\n"
            "Pseudouridine reduces Toll-like-receptor-driven inflammatory "
            "signaling\n"
            "Lower innate immune activation allows more antigen protein "
            "production for the adaptive response"
        ),
    },
    {
        "level": "Expert",
        "explanation_text": (
            "Innate immune sensing of RNA operates through multiple "
            "pattern-recognition pathways, including endosomal Toll-like "
            "receptors (notably TLR3, TLR7, and TLR8) and cytosolic sensors "
            "such as RIG-I and MDA5, which evolved to detect RNA features "
            "associated with viral infection -- including single-stranded RNA "
            "structural motifs and "
            "unmodified ribonucleosides rarely found unmodified in normal "
            "cellular RNA. In vitro transcribed mRNA, produced by bacteriophage "
            "RNA polymerase from a DNA template, lacks the extensive natural "
            "nucleoside modifications found in endogenous cellular RNA, making "
            "it a strong innate-immune agonist when introduced into cells or "
            "delivered to antigen-presenting cells such as dendritic cells.\n\n"
            "Karikó and Weissman's foundational work demonstrated that "
            "substituting a naturally occurring modified nucleoside -- "
            "pseudouridine (Ψ) -- for uridine in synthetic mRNA substantially "
            "reduced activation of these RNA-sensing pathways and the "
            "downstream inflammatory cytokine response, compared to mRNA built "
            "entirely from standard nucleosides. The licensed COVID-19 mRNA "
            "vaccines from Pfizer-BioNTech and Moderna use a related, "
            "subsequently developed nucleoside, N1-methylpseudouridine (m1Ψ), "
            "rather than unmodified pseudouridine itself -- a further "
            "optimization built on, but distinct from, Karikó and Weissman's "
            "original discovery.\n\n"
            "By dampening this innate immune activation, nucleoside-modified "
            "mRNA persisted longer inside cells and was translated more "
            "efficiently by host ribosomes, yielding substantially higher and "
            "more sustained levels of the encoded protein. When that protein is "
            "a pathogen-derived antigen, its endogenous production drives "
            "antigen presentation and subsequent priming of an adaptive immune "
            "response, generating antigen-specific antibodies and memory "
            "lymphocytes.\n\n"
            "This discovery established the core biochemical feasibility of "
            "mRNA as a vaccine and therapeutic platform: it addressed a "
            "fundamental obstacle -- innate immune destruction and "
            "translational shutdown of exogenous mRNA -- that had limited the "
            "field for years. It is important to be precise about chronology "
            "and scope: the nucleoside-modification discovery, made years "
            "before the COVID-19 pandemic, solved this foundational "
            "immunogenicity and translation problem, but it was one of many "
            "subsequent advances -- including lipid nanoparticle delivery "
            "systems, sequence and untranslated-region optimization, and "
            "large-scale clinical development -- that were separately required "
            "to produce the authorized mRNA vaccines deployed against "
            "COVID-19. The Nobel Prize specifically recognizes the "
            "nucleoside-modification discovery, not the full engineering "
            "effort behind any single vaccine product.\n\n"
            "Beyond vaccines, the same principle -- safely delivering modified "
            "mRNA for cells to translate -- underlies ongoing research into "
            "mRNA-based therapeutics for other diseases, including certain "
            "cancers and protein-deficiency disorders, where the goal is to "
            "have a patient's own cells transiently produce a therapeutic "
            "protein."
        ),
        "key_concepts": (
            "Toll-like receptors and cytosolic sensors detect unmodified RNA "
            "as an innate immune trigger\n"
            "Nucleoside modification (pseudouridine) reduces this immune "
            "activation and improves translation\n"
            "The discovery is foundational, not sufficient alone -- delivery "
            "and formulation advances were also required for deployed vaccines"
        ),
    },
]


MRNA_CONNECTIONS = [
    {
        "connection_type": "APPLICATION",
        "title": "mRNA Vaccines",
        "description": (
            "The nucleoside-modification discovery solved a foundational "
            "immunogenicity barrier that had limited synthetic mRNA for years. "
            "It became one of the enabling technologies behind the mRNA "
            "vaccines authorized against COVID-19, alongside separate advances "
            "in lipid nanoparticle delivery and vaccine formulation."
        ),
        "source_name": "NobelPrize.org",
        "source_url": NOBEL_2023_PRESS_RELEASE_URL,
    },
    {
        "connection_type": "APPLICATION",
        "title": "Therapeutic mRNA / Future Medicines",
        "description": (
            "The same principle -- delivering modified mRNA for a patient's "
            "own cells to translate -- is being explored for therapeutic uses "
            "beyond vaccines, including experimental approaches to certain "
            "cancers and protein-deficiency disorders. These applications "
            "remain areas of active research rather than widely available "
            "treatments."
        ),
        "source_name": "NobelPrize.org",
        "source_url": NOBEL_2023_ADVANCED_URL,
    },
    {
        "connection_type": "SCIENTIFIC_LEGACY",
        "title": "Understanding Innate Immune Recognition of RNA",
        "description": (
            "Karikó and Weissman's work clarified how the innate immune "
            "system's RNA-sensing pathways, including Toll-like receptors, "
            "distinguish unmodified synthetic RNA from the body's own RNA. "
            "This mechanistic understanding continues to inform how "
            "researchers design safer and more effective RNA-based therapies."
        ),
        "source_name": "NobelPrize.org",
        "source_url": NOBEL_2023_SUMMARY_URL,
    },
]


# Answer-choice positions below are deliberately varied (not always "A") to
# avoid a guessable pattern, while the underlying scientifically correct
# answer text is unchanged from the reviewed content. Distribution across
# these 12 questions: A x3, B x3, C x3, D x3.
MRNA_QUIZ = [
    {
        "level": "Simple",
        "question": "What is mRNA best described as?",
        "choice_a": "A temporary instruction message a cell can read",
        "choice_b": "A type of vaccine syringe",
        "choice_c": "A permanent part of DNA",
        "choice_d": "A kind of protein",
        "correct_answer": "A",
        "answer_explanation": (
            "mRNA carries temporary instructions that a cell's machinery can "
            "read to build a specific protein."
        ),
    },
    {
        "level": "Simple",
        "question": "What problem did lab-made mRNA have before Karikó and Weissman's discovery?",
        "choice_a": "It was too heavy to inject",
        "choice_b": "The body's defenses often reacted strongly against it",
        # Replaces "It changed a person's DNA": the Simple lesson never
        # mentions DNA, so that distractor could not be ruled out using only
        # what the lesson teaches. This one can -- the lesson states a cell
        # reads mRNA to make the protein, so mRNA making protein "by itself"
        # is directly contradicted by the lesson text.
        "choice_c": "It made the protein by itself without needing a cell to read it",
        "choice_d": "It could not be manufactured at all",
        "correct_answer": "B",
        "answer_explanation": (
            "Unmodified lab-made mRNA often triggered a strong, unwanted "
            "reaction from the body's defenses before cells could use it."
        ),
    },
    {
        "level": "Simple",
        "question": "Why did changing mRNA's building blocks matter for vaccines?",
        "choice_a": "It made the mRNA invisible to cells",
        "choice_b": "It turned the mRNA into a protein directly",
        "choice_c": "It helped the body accept the mRNA so cells could use its instructions",
        "choice_d": "It removed the need for any immune response",
        "correct_answer": "C",
        "answer_explanation": (
            "The modification helped the body's defenses stay calm long "
            "enough for cells to read the mRNA and make the protein it "
            "described, which is how mRNA vaccines work."
        ),
    },
    {
        "level": "Explore",
        "question": "In the flow DNA → mRNA → Protein, what is mRNA's role?",
        "choice_a": "A permanent storage molecule for genetic information",
        "choice_b": "The finished protein itself",
        "choice_c": "A type of antibody",
        "choice_d": "A temporary working copy of instructions that a cell translates into protein",
        "correct_answer": "D",
        "answer_explanation": (
            "mRNA is a temporary working copy of one instruction from DNA, "
            "which the cell's machinery translates into protein."
        ),
    },
    {
        "level": "Explore",
        "question": "What role does the innate immune system play in this discovery?",
        "choice_a": "It is the body's fast, general defense system that can react to unmodified lab-made mRNA",
        "choice_b": "It only responds to bacteria, never to RNA",
        "choice_c": "It permanently disables mRNA production in cells",
        "choice_d": "It manufactures antibodies without any mRNA involved",
        "correct_answer": "A",
        "answer_explanation": (
            "The innate immune system is the body's fast, general-purpose "
            "defense, and it can react strongly to unmodified lab-made mRNA."
        ),
    },
    {
        "level": "Explore",
        "question": "What did modifying mRNA's nucleosides accomplish?",
        "choice_a": "It made the mRNA last forever inside the body",
        "choice_b": "It reduced the unwanted immune reaction so cells could use the mRNA to make protein",
        "choice_c": "It converted mRNA into DNA",
        "choice_d": "It eliminated the need for a cell to translate the message",
        "correct_answer": "B",
        "answer_explanation": (
            "Modified nucleosides, like pseudouridine, reduced the unwanted "
            "immune reaction so cells could actually use the mRNA."
        ),
    },
    {
        "level": "Advanced",
        "question": "In Karikó and Weissman's experiments, what was compared?",
        "choice_a": "Two different vaccines given to the same patient",
        "choice_b": "DNA versus protein directly",
        "choice_c": "mRNA made with standard nucleosides versus mRNA containing pseudouridine",
        "choice_d": "Two unrelated viruses",
        "correct_answer": "C",
        "answer_explanation": (
            "Their key experiments compared synthetic mRNA built from "
            "standard nucleosides against mRNA containing pseudouridine."
        ),
    },
    {
        "level": "Advanced",
        "question": "What was the effect of pseudouridine-containing mRNA on dendritic cells, compared to unmodified mRNA?",
        "choice_a": "It had no measurable effect at all",
        "choice_b": "It permanently destroyed the dendritic cells",
        "choice_c": "It caused dendritic cells to stop recognizing any pathogen",
        "choice_d": "It reduced dendritic cell activation and inflammatory signaling",
        "correct_answer": "D",
        "answer_explanation": (
            "Pseudouridine-containing mRNA reduced dendritic cell activation "
            "and lowered the release of inflammatory signals."
        ),
    },
    {
        "level": "Advanced",
        "question": "Why did reduced innate immune activation lead to more protein production?",
        "choice_a": "Less of the mRNA was destroyed or blocked, so translation could proceed more effectively",
        "choice_b": "The protein was produced without needing any mRNA",
        "choice_c": "The adaptive immune system directly built the protein",
        "choice_d": "Reduced activation had no relationship to protein output",
        "correct_answer": "A",
        "answer_explanation": (
            "With less mRNA destroyed or translationally blocked, the cell's "
            "ribosomes could produce more of the encoded protein."
        ),
    },
    {
        "level": "Expert",
        # Rephrased from a receptor-naming recall question ("Which receptors
        # are implicated...") into a reasoning question: the student must
        # connect innate RNA recognition to *why* it mattered to the
        # discovery, not just recite TLR3/TLR7/TLR8. `match_question` finds
        # the existing row (question_id 341) by its prior text so the ID,
        # and every other row's ID, is preserved across this rename.
        "match_question": "Which receptors are implicated in innate immune recognition of unmodified synthetic RNA?",
        "question": (
            "Why do RNA-sensing innate immune receptors, such as Toll-like "
            "receptors, matter to Karikó and Weissman's discovery?"
        ),
        "choice_a": "They convert mRNA directly into a finished protein",
        "choice_b": (
            "Their recognition of unmodified synthetic RNA triggers the "
            "inflammatory response that nucleoside modification was shown "
            "to reduce"
        ),
        "choice_c": "They are responsible for copying DNA during cell division",
        "choice_d": "They physically destroy every mRNA molecule regardless of its structure",
        "correct_answer": "B",
        "answer_explanation": (
            "RNA-sensing receptors like Toll-like receptors normally flag "
            "unmodified synthetic RNA as foreign, triggering the strong "
            "inflammatory response that limited early mRNA experiments; "
            "Karikó and Weissman showed that nucleoside modification "
            "reduces this recognition, and with it, the inflammatory "
            "response."
        ),
    },
    {
        "level": "Expert",
        # Question stem is unchanged (so the existing row, question_id 342,
        # is still found by text and updated in place) -- only the correct
        # answer's wording and the explanation were tightened to mirror the
        # Expert lesson's own framing (RNA-sensing pathways recognizing a
        # foreign-RNA feature) rather than Advanced's "alters RNA structure"
        # phrasing.
        "question": "Mechanistically, how does pseudouridine substitution reduce innate immune activation?",
        "choice_a": "It physically shields the mRNA from all cells",
        "choice_b": "It converts the mRNA into a different molecule entirely",
        "choice_c": (
            "It removes a feature that RNA-sensing pathways, including "
            "endosomal Toll-like receptors, use to recognize RNA as foreign"
        ),
        "choice_d": "It has no defined molecular mechanism",
        "correct_answer": "C",
        "answer_explanation": (
            "Toll-like receptors and cytosolic sensors detect RNA features "
            "typical of unmodified, non-self RNA; replacing uridine with "
            "pseudouridine removes that recognized feature, reducing "
            "activation of these pathways and the downstream inflammatory "
            "response."
        ),
    },
    {
        "level": "Expert",
        "question": "Which statement most accurately describes the scope of the Nobel-recognized discovery?",
        "choice_a": "It alone was sufficient to produce every deployed COVID-19 mRNA vaccine",
        "choice_b": "It described how DNA replicates",
        "choice_c": "It replaced the need for an adaptive immune response entirely",
        "choice_d": (
            "It solved a foundational immunogenicity and translation "
            "barrier, but additional advances like lipid nanoparticle "
            "delivery were also required for deployed mRNA vaccines"
        ),
        "correct_answer": "D",
        "answer_explanation": (
            "The discovery addressed a key barrier -- immune overreaction to "
            "synthetic mRNA -- but deployed vaccines required many additional "
            "advances, such as lipid nanoparticle delivery systems, developed "
            "separately."
        ),
    },
]


def _require_existing_nobel_data(db: Session):
    kariko = laureate_repository.get_by_nobel_id(db, KARIKO_NOBEL_ID)
    if kariko is None or kariko.full_name != "Katalin Karikó":
        raise RuntimeError("Katalin Karikó Nobel ID 1024 was not found as expected")

    weissman = laureate_repository.get_by_nobel_id(db, WEISSMAN_NOBEL_ID)
    if weissman is None or weissman.full_name != "Drew Weissman":
        raise RuntimeError("Drew Weissman Nobel ID 1025 was not found as expected")

    medicine = category_repository.get_by_name(db, "Physiology or Medicine")
    if medicine is None:
        raise RuntimeError("Physiology or Medicine category was not found")

    prize_2023 = prize_repository.get_by_year_and_category(
        db, 2023, medicine.category_id
    )
    if prize_2023 is None:
        raise RuntimeError("The 2023 Physiology or Medicine prize must already exist")

    kariko_prize = laureate_prize_repository.get_by_laureate_and_prize(
        db, kariko.laureate_id, prize_2023.prize_id
    )
    weissman_prize = laureate_prize_repository.get_by_laureate_and_prize(
        db, weissman.laureate_id, prize_2023.prize_id
    )
    if kariko_prize is None or weissman_prize is None:
        raise RuntimeError(
            "Karikó's and Weissman's 2023 Physiology or Medicine LaureatePrize "
            "rows were not found"
        )

    motivation = (kariko_prize.motivation or "").lower()
    if "nucleoside base modifications" not in motivation:
        raise RuntimeError(
            "Karikó's stored Nobel motivation did not mention nucleoside base "
            "modifications"
        )
    if weissman_prize.prize_id != kariko_prize.prize_id:
        raise RuntimeError(
            "Karikó and Weissman's LaureatePrize rows do not resolve to the "
            "same prize"
        )

    return kariko, kariko_prize, weissman, weissman_prize, prize_2023


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
        data = ConnectionCreate(contribution_id=contribution_id, **row)
        connection = connection_repository.get_by_contribution_type_and_title(
            db, contribution_id, data.connection_type, data.title
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
        # `match_question` lets a row's stem be renamed while the upsert
        # still finds and updates the SAME existing row instead of creating
        # a new one. Look up by the CURRENT (new) text first, since that is
        # what every run after the first rename will find; only fall back to
        # the legacy text for the one-time run that performs the rename
        # itself. Checking new-then-old (rather than only old) is what keeps
        # this idempotent across any number of runs, not just the first.
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


def seed_mrna_education(db: Session) -> dict:
    kariko, kariko_prize, weissman, weissman_prize, prize_2023 = (
        _require_existing_nobel_data(db)
    )

    mrna_contribution = _upsert_contribution(
        db,
        ContributionCreate(
            credited_laureates=[
                {
                    "laureate_id": kariko.laureate_id,
                    "laureate_prize_id": kariko_prize.laureate_prize_id,
                },
                {
                    "laureate_id": weissman.laureate_id,
                    "laureate_prize_id": weissman_prize.laureate_prize_id,
                },
            ],
            contribution_type="NOBEL_LINKED",
            title="Nucleoside Base Modifications and mRNA Vaccines",
            summary=(
                "Karikó and Weissman discovered that modifying nucleosides in "
                "synthetic mRNA reduces unwanted innate immune activation, "
                "enabling cells to translate the mRNA into protein -- the "
                "biochemical breakthrough that enabled effective mRNA vaccines."
            ),
            significance=(
                "This work was the discovery especially identified in the "
                "motivation for the 2023 Physiology or Medicine Prize: "
                "discoveries concerning nucleoside base modifications that "
                "enabled the development of effective mRNA vaccines against "
                "COVID-19. It addressed a foundational immunogenicity barrier; "
                "the deployed COVID-19 vaccines also required many additional, "
                "separately developed advances such as lipid nanoparticle "
                "delivery."
            ),
            source_url=NOBEL_2023_SUMMARY_URL,
        ),
    )

    explanations = _upsert_explanations(
        db, mrna_contribution.contribution_id, MRNA_EXPLANATIONS
    )
    connections = _upsert_connections(
        db, mrna_contribution.contribution_id, MRNA_CONNECTIONS
    )
    quiz = _upsert_quiz(db, mrna_contribution.contribution_id, MRNA_QUIZ)

    return {
        "kariko_id": kariko.laureate_id,
        "kariko_laureate_prize_id": kariko_prize.laureate_prize_id,
        "weissman_id": weissman.laureate_id,
        "weissman_laureate_prize_id": weissman_prize.laureate_prize_id,
        "prize_id": prize_2023.prize_id,
        "mrna_contribution_id": mrna_contribution.contribution_id,
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
        result = seed_mrna_education(db)
        db.commit()
        print("mRNA educational seed complete:", result)
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
