# Database migrations

Nobel Explorer uses Alembic as the authoritative mechanism for creating and
evolving its MySQL schema. Alembic records the applied revision in the
`alembic_version` table.

## SQLAlchemy models and Alembic

SQLAlchemy models describe the schema expected by the application. Alembic
migration files describe the ordered operations required to move an existing
database between schema versions. Changing a model does not automatically
change an existing database; the corresponding migration must be created,
reviewed, and applied.

The migration environment reads the same `.env` database settings as the
application. Real credentials must never be placed in `alembic.ini` or committed
to Git.

## Check migration state

```bash
alembic current
alembic history
```

## Create and review a migration

After changing SQLAlchemy models, generate a candidate revision:

```bash
alembic revision --autogenerate -m "describe the schema change"
```

Always inspect the generated file in `migrations/versions/`. Confirm that it
contains only the intended tables, columns, indexes, constraints, and foreign
keys. Autogenerate produces a proposal, not a substitute for review.

## Apply migrations

Back up important development or production data before applying schema
changes. Then run:

```bash
alembic upgrade head
```

For a brand-new empty database, this applies the baseline and every later
migration in order.

## Downgrade policy

To reverse one revision in a disposable development or migration-test database:

```bash
alembic downgrade -1
```

Never downgrade production casually. A downgrade can remove columns, tables,
or data. Review the migration, make a verified backup, and prepare a recovery
plan before any downgrade outside a disposable environment.

## Existing databases

An existing database may be stamped only after its schema has been carefully
verified to match the baseline:

```bash
alembic stamp head
```

Stamping records the revision without executing its schema operations. It must
not be used to hide schema differences.

## Schema-management rules

- Use `alembic upgrade head` for normal fresh-database setup.
- Capture every schema change in an Alembic revision.
- Never manually alter a shared schema without adding the equivalent migration.
- Do not use `Base.metadata.create_all()` as the normal deployment workflow.
- Never commit `.env` or database credentials.
- Test upgrades and downgrades on a disposable database before production use.
