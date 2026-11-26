"""Hand-countable fixture database for Phase 2 tool tests.

The data is small enough that every statistic can be verified by hand.
Expected values (used by the tests) are derived in the comments below.

Laureates (12: 11 persons, 1 organization) and their awards (15):
  1   Wilhelm Conrad Röntgen   male    Germany         1901 Physics                  (no educational content)
  249 Albert Einstein          male    Germany         1921 Physics
  356 Carolyn R. Bertozzi      female  USA             2022 Chemistry (1/3)
  766 K. Barry Sharpless       male    USA             2001 Chemistry (1/2), 2022 Chemistry (1/3)
  886 Morten Meldal            male    Denmark         2022 Chemistry (1/3)
  841 Marie Curie              female  Russian Empire  1903 Physics (1/4), 1911 Chemistry
  981 Pierre Curie             male    France          1903 Physics (1/4)
  651 Irène Joliot-Curie       female  France          1935 Chemistry
  648 Int. Committee of the Red Cross (Organization)   1917 Peace, 1944 Peace
  428 Katalin Karikó           female  Hungary         2023 Physiology or Medicine (1/2)
  774 Drew Weissman            male    USA             2023 Physiology or Medicine (1/2)
  900 Ragnar Frisch            male    Norway          1969 Economic Sciences (1/2)

Prizes: 11 (1901 Phys, 1903 Phys, 1911 Chem, 1917 Peace, 1921 Phys, 1935 Chem,
         1944 Peace, 1969 Econ, 2001 Chem, 2022 Chem, 2023 Med)
Distinct laureates by category: Chemistry 5, Physics 4, Physiology or Medicine 2,
  Economic Sciences 1, Peace 1, Literature 0.
Persons by gender: female 4, male 7.  Women % of known-gender persons = 36.4.
Birth countries (persons): USA 3, France 2, Germany 2, Denmark 1, Hungary 1,
  Norway 1, Russian Empire 1  -> 7 distinct.
Average age at award, Chemistry (one observation per award):
  Bertozzi 56, Sharpless 60 & 81, Meldal 68, Marie Curie 44, Irène 38 -> 347/6 = 57.8
Affiliation institutions, Chemistry, country USA: Scripps Research 1, Stanford University 1.
"""

from __future__ import annotations

from datetime import date

from sqlalchemy.orm import Session

from backend.models import (
    AwardAffiliation,
    Category,
    Connection,
    Contribution,
    ContributionLaureate,
    Explanation,
    Institution,
    Laureate,
    LaureatePrize,
    Prize,
)

CATEGORY_NAMES = ["Chemistry", "Economic Sciences", "Literature", "Peace", "Physics", "Physiology or Medicine"]


def seed_tool_fixture(db: Session) -> None:
    cats = {name: Category(category_id=i + 1, name=name) for i, name in enumerate(CATEGORY_NAMES)}
    prize_specs = [
        (101, 1901, "Physics"), (102, 1903, "Physics"), (103, 1911, "Chemistry"), (104, 1917, "Peace"),
        (105, 1921, "Physics"), (106, 1935, "Chemistry"), (107, 1944, "Peace"), (108, 1969, "Economic Sciences"),
        (109, 2001, "Chemistry"), (110, 2022, "Chemistry"), (111, 2023, "Physiology or Medicine"),
    ]
    prizes = {pid: Prize(prize_id=pid, year=year, category=cats[cat]) for pid, year, cat in prize_specs}

    def person(lid, nobel_id, name, gender, country, born, city=None, state=None):
        return Laureate(laureate_id=lid, nobel_laureate_id=nobel_id, full_name=name, laureate_type="Person",
                        gender=gender, birth_country=country, birth_date=born, birth_city=city, birth_state=state)

    L = {
        1: person(1, "1", "Wilhelm Conrad Röntgen", "male", "Germany", date(1845, 3, 27), "Lennep"),
        249: person(249, "26", "Albert Einstein", "male", "Germany", date(1879, 3, 14), "Ulm"),
        356: person(356, "1015", "Carolyn R. Bertozzi", "female", "USA", date(1966, 10, 10), "Boston", "Massachusetts"),
        766: person(766, "743", "K. Barry Sharpless", "male", "USA", date(1941, 4, 28), "Philadelphia", "Pennsylvania"),
        886: person(886, "1016", "Morten Meldal", "male", "Denmark", date(1954, 1, 16), "Copenhagen"),
        841: person(841, "6", "Marie Curie, née Skłodowska", "female", "Russian Empire", date(1867, 11, 7), "Warsaw"),
        981: person(981, "5", "Pierre Curie", "male", "France", date(1859, 5, 15), "Paris"),
        651: person(651, "194", "Irène Joliot-Curie", "female", "France", date(1897, 9, 12), "Paris"),
        428: person(428, "1024", "Katalin Karikó", "female", "Hungary", date(1955, 1, 17), "Szolnok"),
        774: person(774, "1025", "Drew Weissman", "male", "USA", date(1959, 9, 7), "Lexington", "Massachusetts"),
        900: person(900, "403", "Ragnar Frisch", "male", "Norway", date(1895, 3, 3), "Oslo"),
        648: Laureate(laureate_id=648, nobel_laureate_id="482", full_name="International Committee of the Red Cross",
                      laureate_type="Organization"),
    }
    award_specs = [
        (1001, 1, 101, "1", "in recognition of the extraordinary services he has rendered by the discovery of the remarkable rays"),
        (1002, 249, 105, "1", "for his services to Theoretical Physics, and especially for his discovery of the law of the photoelectric effect"),
        (1003, 356, 110, "1/3", "for the development of click chemistry and bioorthogonal chemistry"),
        (1004, 766, 110, "1/3", "for the development of click chemistry and bioorthogonal chemistry"),
        (1005, 766, 109, "1/2", "for his work on chirally catalysed oxidation reactions"),
        (1006, 886, 110, "1/3", "for the development of click chemistry and bioorthogonal chemistry"),
        (1007, 841, 102, "1/4", "in recognition of the extraordinary services they have rendered by their joint researches on radiation"),
        (1008, 841, 103, "1", "in recognition of her services to the advancement of chemistry by the discovery of radium and polonium"),
        (1009, 981, 102, "1/4", "in recognition of the extraordinary services they have rendered by their joint researches on radiation"),
        (1010, 651, 106, "1/2", "in recognition of their synthesis of new radioactive elements"),
        (1011, 648, 104, "1", "for the efforts to take care of wounded soldiers and prisoners of war"),
        (1012, 648, 107, "1", "for the great work it has performed during the war on behalf of humanity"),
        (1013, 428, 111, "1/2", "for their discoveries concerning nucleoside base modifications that enabled mRNA vaccines"),
        (1014, 774, 111, "1/2", "for their discoveries concerning nucleoside base modifications that enabled mRNA vaccines"),
        (1015, 900, 108, "1/2", "for having developed and applied dynamic models for the analysis of economic processes"),
    ]
    awards = {aid: LaureatePrize(laureate_prize_id=aid, laureate=L[lid], prize=prizes[pid], prize_share=share,
                                 motivation=motivation)
              for aid, lid, pid, share, motivation in award_specs}

    inst = {
        1: Institution(institution_id=1, name="Kaiser-Wilhelm-Institut für Physik", city="Berlin", country="Germany"),
        2: Institution(institution_id=2, name="Stanford University", city="Stanford", state="CA", country="USA"),
        3: Institution(institution_id=3, name="Scripps Research", city="La Jolla", state="CA", country="USA"),
        4: Institution(institution_id=4, name="University of Copenhagen", city="Copenhagen", country="Denmark"),
    }
    affiliations = [
        AwardAffiliation(award_affiliation_id=1, laureate_prize=awards[1002], institution=inst[1]),
        AwardAffiliation(award_affiliation_id=2, laureate_prize=awards[1003], institution=inst[2]),
        AwardAffiliation(award_affiliation_id=3, laureate_prize=awards[1004], institution=inst[3]),
        AwardAffiliation(award_affiliation_id=4, laureate_prize=awards[1005], institution=inst[3]),
        AwardAffiliation(award_affiliation_id=5, laureate_prize=awards[1006], institution=inst[4]),
    ]

    photo = Contribution(contribution_id=38, contribution_type="NOBEL_LINKED", title="Photoelectric Effect",
                         summary="Einstein explained the photoelectric effect using light quanta.",
                         significance="Helped establish quantum physics.",
                         source_url="https://www.nobelprize.org/prizes/physics/1921/summary/")
    photo.credited_laureates.append(ContributionLaureate(laureate=L[249], laureate_prize=awards[1002]))
    mrna = Contribution(contribution_id=609, contribution_type="NOBEL_LINKED",
                        title="Nucleoside Base Modifications and mRNA Vaccines",
                        summary="Modified nucleosides let mRNA avoid innate immune activation.",
                        significance="Enabled effective mRNA vaccines.",
                        source_url="https://www.nobelprize.org/prizes/medicine/2023/summary/")
    mrna.credited_laureates.extend([ContributionLaureate(laureate=L[428], laureate_prize=awards[1013]),
                                    ContributionLaureate(laureate=L[774], laureate_prize=awards[1014])])
    click = Contribution(contribution_id=779, contribution_type="NOBEL_LINKED",
                         title="Click Chemistry and Bioorthogonal Chemistry",
                         summary="Click reactions join molecular building blocks quickly and selectively.",
                         significance="Bioorthogonal reactions work inside living organisms.",
                         source_url="https://www.nobelprize.org/prizes/chemistry/2022/summary/")
    click.credited_laureates.extend([ContributionLaureate(laureate=L[356], laureate_prize=awards[1003]),
                                     ContributionLaureate(laureate=L[766], laureate_prize=awards[1004]),
                                     ContributionLaureate(laureate=L[886], laureate_prize=awards[1006])])
    long_expert = " ".join(
        f"Sentence {i} explains how photon energy, frequency and the work function determine electron emission."
        for i in range(14)
    )
    explanations = [
        Explanation(explanation_id=1, contribution=photo, level="Simple",
                    explanation_text="Light is made of photons that can knock electrons out of metal.",
                    key_concepts="Light has photons\nPhotons knock out electrons"),
        Explanation(explanation_id=2, contribution=photo, level="Expert", explanation_text=long_expert),
        Explanation(explanation_id=3, contribution=mrna, level="Simple",
                    explanation_text="Changing mRNA building blocks stops the immune system attacking it."),
        Explanation(explanation_id=4, contribution=click, level="Simple",
                    explanation_text="Click chemistry snaps molecules together like seat-belt buckles."),
        Explanation(explanation_id=5, contribution=click, level="Explore",
                    explanation_text="Bioorthogonal reactions run inside living cells without disturbing them."),
    ]
    connections = [
        Connection(connection_id=24, contribution=photo, connection_type="APPLICATION",
                   title="Solar Panels / Photovoltaic Technology",
                   description="Photovoltaic cells convert absorbed photons into electric current.",
                   source_name="U.S. Department of Energy",
                   source_url="https://www.energy.gov/cmei/systems/solar-photovoltaic-cell-basics"),
        Connection(connection_id=25, contribution=photo, connection_type="SCIENTIFIC_LEGACY",
                   title="Quantum Legacy", description="Quantum theory grew from the photon concept."),
        Connection(connection_id=276, contribution=mrna, connection_type="APPLICATION", title="mRNA Vaccines",
                   description="mRNA vaccines were deployed against COVID-19.", source_name="NobelPrize.org",
                   source_url="https://www.nobelprize.org/prizes/medicine/2023/press-release/"),
    ]
    db.add_all([*cats.values(), *prizes.values(), *L.values(), *awards.values(), *inst.values(), *affiliations,
                photo, mrna, click, *explanations, *connections])
    db.commit()
