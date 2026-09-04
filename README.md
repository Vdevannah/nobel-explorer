# Nobel Explorer

Nobel Explorer is an educational application for exploring Nobel Prize data. It
includes a FastAPI REST API, a MySQL database accessed through SQLAlchemy, and an
ETL pipeline that imports raw Laureate data from the official Nobel Prize API.
The API exposes Laureates, Prizes, award-time institutional affiliations, and
analytics-ready Nobel data.

## Current status

The database, ETL pipeline, repository layer, service layer, and read-only REST
API are implemented. Current capabilities include:

- Extraction from the official Nobel Prize API with pagination
- Laureate, Prize, and award-affiliation transformation for 1901–2025
- Safe handling of partial birth dates without inventing missing values
- U.S. city/state normalization using full state names
- Idempotent repository-based loading into MySQL
- Paginated Laureate, Prize, and Institution endpoints
- Laureate filtering by category, year, birth country, and gender
- Case-insensitive Laureate name search
- Nested Laureate/Prize/Institution relationship responses
- Aggregate analytics for categories, birthplaces, institutions, gender,
  decades, and approximate age at award
- Centralized HTTP 404 handling and automatic FastAPI validation
- Swagger/OpenAPI documentation and integration-style API tests

## Project structure

```text
nobel-explorer/
├── backend/
│   ├── database/
│   │   ├── __init__.py
│   │   ├── connection.py
│   │   ├── create_tables.py
│   │   ├── test_affiliation_relationship.py
│   │   └── test_relationships.py
│   ├── models/
│   │   ├── __init__.py
│   │   ├── application.py
│   │   ├── award_affiliation.py
│   │   ├── category.py
│   │   ├── discovery.py
│   │   ├── explanation.py
│   │   ├── institution.py
│   │   ├── laureate.py
│   │   ├── laureate_prize.py
│   │   ├── prize.py
│   │   └── quiz_question.py
│   ├── routes/
│   │   ├── analytics.py
│   │   ├── categories.py
│   │   ├── health.py
│   │   ├── institutions.py
│   │   ├── laureates.py
│   │   └── prizes.py
│   ├── schemas/
│   │   ├── analytics.py
│   │   ├── category.py
│   │   ├── institution.py
│   │   ├── laureate.py
│   │   └── prize.py
│   ├── services/
│   │   ├── analytics_service.py
│   │   ├── category_service.py
│   │   ├── institution_service.py
│   │   ├── laureate_service.py
│   │   └── prize_service.py
│   ├── __init__.py
│   └── main.py
├── ETL/
│   ├── extract.py
│   ├── transform.py
│   ├── load.py
│   └── run_etl.py
├── .env.example
├── .gitignore
├── requirements.txt
└── README.md
```

## Requirements

- Python 3.12 or later
- MySQL running locally or on an accessible server
- A MySQL database, such as `nobel_explorer`

## Setup

Clone the repository and move into the project directory:

```bash
git clone <repository-url>
cd nobel-explorer
```

Create and activate a virtual environment:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

On Windows PowerShell, activate it with:

```powershell
.venv\Scripts\Activate.ps1
```

Install the project dependencies:

```bash
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

## Database configuration

Create a local environment file from the example:

```bash
cp .env.example .env
```

Set the connection values in `.env`:

```dotenv
DB_HOST=localhost
DB_PORT=3306
DB_NAME=nobel_explorer
DB_USER=your_mysql_user
DB_PASSWORD=your_mysql_password
```

The `.env` file is ignored by Git and should not be committed.

## Database models

The ORM schema connects the educational content as follows:

```text
Category ──< Prize ──< LaureatePrize >── Laureate
                         │
                         ├──< AwardAffiliation >── Institution
                         │
                         └──< Discovery
                                ├──< Application ──< Explanation
                                └──< QuizQuestion
```

| Model | Purpose |
| --- | --- |
| `Category` | Stores Nobel Prize categories and their descriptions |
| `Prize` | Stores a prize year and category |
| `Laureate` | Stores laureate type, biographical details, and birth location |
| `LaureatePrize` | Connects laureates to prizes and records prize shares and motivations |
| `Institution` | Stores an institution's name and location |
| `AwardAffiliation` | Connects an awarded prize to the laureate's institution at that time |
| `Discovery` | Describes the work associated with a laureate's prize |
| `Application` | Connects a discovery to a real-world use |
| `Explanation` | Provides level-specific educational explanations |
| `QuizQuestion` | Stores multiple-choice questions for a discovery |

The association tables enforce unique relationship pairs:

- `LaureatePrize` prevents duplicate laureate/prize combinations.
- `AwardAffiliation` prevents duplicate laureate-prize/institution combinations.

Keeping affiliation on the award relationship instead of directly on the
laureate allows one laureate to have different institutions for different Nobel
Prizes.

## Create the database tables

Create the MySQL database itself first if it does not already exist:

```sql
CREATE DATABASE nobel_explorer;
```

After configuring `.env`, create all tables from the project root:

```bash
python -m backend.database.create_tables
```

The command imports every model so SQLAlchemy can register the complete schema,
then creates any missing tables. It does not drop, recreate, or alter existing
tables. If you created the schema before adding the new columns or models, use a
migration or recreate the development database before testing the updated schema.

## Verify ORM relationships

Once the tables exist, run the relationship integration script:

```bash
python -m backend.database.test_relationships
```

The script creates a connected sample category, prize, laureate, discovery,
application, explanation, and quiz question. It then traverses their ORM
relationships and prints the results. A successful run ends with:

```text
ORM relationships are working successfully.
```

The test flushes its sample records so relationships and generated IDs can be
verified, then rolls back the transaction. It does not permanently save its
temporary records.

### Test award affiliations

To verify the `LaureatePrize`, `AwardAffiliation`, and `Institution`
relationships, run:

```bash
python -m backend.database.test_affiliation_relationship
```

This script creates a temporary prize and affiliation graph, flushes it to MySQL,
and verifies relationship traversal. A successful run ends with:

```text
Affiliation relationship test passed.
```

The affiliation test rolls back its transaction, so its temporary records are
not permanently saved.

## Run the API

From the project root, start the development server:

```bash
python -m uvicorn backend.main:app --reload
```

The API will be available at <http://127.0.0.1:8000>.

## API documentation

FastAPI generates interactive documentation automatically:

- Swagger UI: <http://127.0.0.1:8000/docs>
- ReDoc: <http://127.0.0.1:8000/redoc>

## Endpoints

| Method | Path | Description |
| --- | --- | --- |
| `GET` | `/` | Confirms that the API is running |
| `GET` | `/health` | Returns the application health status |
| `GET` | `/health/db` | Checks the MySQL connection and returns the selected database |
| `GET` | `/categories` | Lists Nobel Prize categories |
| `GET` | `/categories/{category_id}` | Returns one category |
| `GET` | `/laureates` | Lists, filters, and searches Laureates |
| `GET` | `/laureates/{laureate_id}` | Returns Laureate details and awards |
| `GET` | `/prizes` | Lists Nobel Prizes |
| `GET` | `/prizes/{prize_id}` | Returns Prize details and awarded Laureates |
| `GET` | `/institutions` | Lists award-time institutions |
| `GET` | `/institutions/{institution_id}` | Returns one Institution |
| `GET` | `/institutions/{institution_id}/awards` | Lists an Institution's Nobel affiliations |
| `GET` | `/analytics/summary` | Returns total Laureate and Prize counts |
| `GET` | `/analytics/laureates-by-category` | Counts Laureates by category |
| `GET` | `/analytics/birth-countries` | Counts birth countries for a category |
| `GET` | `/analytics/us-birth-states` | Counts U.S. birth states for a category |
| `GET` | `/analytics/institutions` | Counts award-time institutions by category and country |
| `GET` | `/analytics/gender` | Counts Laureates by gender for a category |
| `GET` | `/analytics/decades` | Counts Laureates by award decade |
| `GET` | `/analytics/average-age` | Returns approximate average age at award |

Example database health response:

```json
{
  "status": "healthy",
  "database": "nobel_explorer"
}
```

### Laureate pagination, filters, and search

`GET /laureates` supports `limit` and `offset`, plus optional `category`,
`year`, `country`, `gender`, and `search` parameters. The `country` parameter
means Laureate birth country.

```text
/laureates?limit=5&offset=0
/laureates?category=Chemistry&gender=female
/laureates?search=Einstein
```

Collection responses include the page items and the total matching record
count:

```json
{
  "items": [],
  "total": 0,
  "limit": 20,
  "offset": 0
}
```

### Analytics semantics

- Birth-country and U.S. birth-state analytics describe where individual
  Laureates were born.
- Institution analytics describe award-time affiliations. They do not describe
  Laureate birthplaces.
- `USA` is the canonical U.S. country value.
- Average age at award is approximate because the database stores award year,
  not an exact award date.

## ETL pipeline

The ETL flow is:

```text
Nobel Prize API → Extract → Transform → Repository-based Load → MySQL
```

The loader looks up existing records before creating them, allowing the same
input to be processed repeatedly without adding duplicate relationship rows.
The normal entry point processes the complete extracted data set:

```bash
python -m ETL.run_etl
```

This command writes Nobel data to the configured database. Use a development
database and verify `.env` before running it. A limited development run remains
available by importing `run_etl` and passing `max_laureates`.

## Run tests

The tests use the configured MySQL database and roll back temporary test data.
Run the complete suite from the project root:

```bash
python -m pytest -v
```

The Phase 7 baseline is 78 passing tests. The exact count may increase as the
project gains additional coverage.

## Development notes

- Run commands from the repository root so imports such as `backend.main` resolve
  correctly.
- Prefer `python -m uvicorn` to ensure Uvicorn uses the active virtual environment.
- If port `8000` is occupied, use another port:

  ```bash
  python -m uvicorn backend.main:app --reload --port 8001
  ```
