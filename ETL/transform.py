from datetime import datetime


US_STATE_NAMES = {
    "AL": "Alabama",
    "AK": "Alaska",
    "AZ": "Arizona",
    "AR": "Arkansas",
    "CA": "California",
    "CO": "Colorado",
    "CT": "Connecticut",
    "DE": "Delaware",
    "FL": "Florida",
    "GA": "Georgia",
    "HI": "Hawaii",
    "ID": "Idaho",
    "IL": "Illinois",
    "IN": "Indiana",
    "IA": "Iowa",
    "KS": "Kansas",
    "KY": "Kentucky",
    "LA": "Louisiana",
    "ME": "Maine",
    "MD": "Maryland",
    "MA": "Massachusetts",
    "MI": "Michigan",
    "MN": "Minnesota",
    "MS": "Mississippi",
    "MO": "Missouri",
    "MT": "Montana",
    "NE": "Nebraska",
    "NV": "Nevada",
    "NH": "New Hampshire",
    "NJ": "New Jersey",
    "NM": "New Mexico",
    "NY": "New York",
    "NC": "North Carolina",
    "ND": "North Dakota",
    "OH": "Ohio",
    "OK": "Oklahoma",
    "OR": "Oregon",
    "PA": "Pennsylvania",
    "RI": "Rhode Island",
    "SC": "South Carolina",
    "SD": "South Dakota",
    "TN": "Tennessee",
    "TX": "Texas",
    "UT": "Utah",
    "VT": "Vermont",
    "VA": "Virginia",
    "WA": "Washington",
    "WV": "West Virginia",
    "WI": "Wisconsin",
    "WY": "Wyoming",
    "DC": "District of Columbia"
}


def parse_birth_date(raw_date: str | None):
    if not raw_date:
        return None

    try:
        return datetime.strptime(raw_date, "%Y-%m-%d").date()
    except ValueError:
        return None


def normalize_us_city_state(
    city_value: str | None,
    country: str | None
) -> tuple[str | None, str | None]:
    if not city_value:
        return None, None

    if country != "USA":
        return city_value, None

    if "," not in city_value:
        return city_value, None

    city, state = city_value.rsplit(",", 1)
    city = city.strip()
    state_abbreviation = state.strip().upper()

    if city and state_abbreviation in US_STATE_NAMES:
        return city, US_STATE_NAMES[state_abbreviation]

    return city_value, None


def transform_laureate(raw_laureate: dict) -> dict:
    nobel_laureate_id = str(raw_laureate["id"])

    if "fullName" in raw_laureate:
        laureate_type = "Person"
        full_name = (raw_laureate.get("fullName") or {}).get("en")

        birth = raw_laureate.get("birth") or {}
        birth_place = birth.get("place") or {}

        birth_date = parse_birth_date(birth.get("date"))
        raw_birth_city = (birth_place.get("city") or {}).get("en")
        birth_country = (birth_place.get("country") or {}).get("en")
        birth_city, birth_state = normalize_us_city_state(
            raw_birth_city,
            birth_country
        )
        gender = raw_laureate.get("gender")
    elif "orgName" in raw_laureate:
        laureate_type = "Organization"
        full_name = (raw_laureate.get("orgName") or {}).get("en")
        birth_date = None
        birth_city = None
        birth_state = None
        birth_country = None
        gender = None
    else:
        laureate_type = None
        full_name = None
        birth_date = None
        birth_city = None
        birth_state = None
        birth_country = None
        gender = None

    return {
        "nobel_laureate_id": nobel_laureate_id,
        "full_name": full_name,
        "laureate_type": laureate_type,
        "birth_date": birth_date,
        "birth_city": birth_city,
        "birth_state": birth_state,
        "birth_country": birth_country,
        "gender": gender
    }


def transform_prizes(raw_laureate: dict) -> list[dict]:
    transformed_prizes = []

    for raw_prize in raw_laureate.get("nobelPrizes", []) or []:
        try:
            year = int(raw_prize.get("awardYear"))
        except (TypeError, ValueError):
            continue

        if not 1901 <= year <= 2025:
            continue

        transformed_prizes.append({
            "year": year,
            "category": (raw_prize.get("category") or {}).get("en"),
            "motivation": (raw_prize.get("motivation") or {}).get("en"),
            "prize_share": raw_prize.get("portion")
        })

    return transformed_prizes


def transform_affiliations(raw_prize: dict) -> list[dict]:
    transformed_affiliations = []

    for affiliation in raw_prize.get("affiliations", []) or []:
        raw_city = (affiliation.get("city") or {}).get("en")
        country = (affiliation.get("country") or {}).get("en")
        city, state = normalize_us_city_state(raw_city, country)

        transformed_affiliations.append({
            "name": (affiliation.get("name") or {}).get("en"),
            "city": city,
            "state": state,
            "country": country
        })

    return transformed_affiliations


if __name__ == "__main__":
    spence = {
        "id": "745",
        "fullName": {
            "en": "A. Michael Spence"
        },
        "gender": "male",
        "birth": {
            "date": "1943-11-07",
            "place": {
                "city": {
                    "en": "Montclair, NJ"
                },
                "country": {
                    "en": "USA"
                }
            }
        }
    }

    spence_prize = {
        "awardYear": "2001",
        "affiliations": [
            {
                "name": {
                    "en": "Stanford University"
                },
                "city": {
                    "en": "Stanford, CA"
                },
                "country": {
                    "en": "USA"
                }
            }
        ]
    }

    print("U.S. and non-U.S. location normalization:")
    print(normalize_us_city_state("Montclair, NJ", "USA"))
    print(normalize_us_city_state("Stanford, CA", "USA"))
    print(normalize_us_city_state("Boston, MA", "USA"))
    print(normalize_us_city_state("Wilmington, DE", "USA"))
    print(normalize_us_city_state("Washington, DC", "USA"))
    print(normalize_us_city_state("New York", "USA"))
    print(normalize_us_city_state(None, "USA"))
    print(normalize_us_city_state("Cambridge", "United Kingdom"))

    print("\nA. Michael Spence laureate:")
    print(transform_laureate(spence))

    print("\nA. Michael Spence affiliation:")
    print(transform_affiliations(spence_prize))
