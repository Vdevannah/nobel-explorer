# Nobel Explorer

Nobel Explorer is an educational application for exploring Nobel Prize data. The
current repository contains a FastAPI backend, MySQL connectivity, health check
endpoints, and a SQLAlchemy ORM data model for prizes, laureates, award-time
institutional affiliations, discoveries, real-world applications, explanations,
and quizzes.

## Current phase

The database foundation is now in place. This phase includes:

- Ten SQLAlchemy ORM models with typed columns and bidirectional relationships
- A many-to-many laureate/prize association model with prize-share data
- Institution and award-affiliation models that preserve where a laureate was
  affiliated when a specific prize was awarded
- Laureate type and structured birth location fields
- MySQL engine and session management through environment-based configuration
- A utility for creating all model tables
- Integration scripts for the educational-content and institutional-affiliation
  relationship graphs

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
│   │   ├── __init__.py
│   │   └── health.py
│   ├── __init__.py
│   └── main.py
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

The test currently commits its sample records to the configured database. Use a
development database when running it repeatedly.

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

Example database health response:

```json
{
  "status": "healthy",
  "database": "nobel_explorer"
}
```

## Development notes

- Run commands from the repository root so imports such as `backend.main` resolve
  correctly.
- Prefer `python -m uvicorn` to ensure Uvicorn uses the active virtual environment.
- If port `8000` is occupied, use another port:

  ```bash
  python -m uvicorn backend.main:app --reload --port 8001
  ```
