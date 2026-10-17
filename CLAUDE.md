# Project rules

- Keep HTTP handlers thin; place payment rules in the domain or application layer.
- Keep database and network I/O asynchronous.
- Store and calculate money only as integer kopecks.
- Add persistence changes through Alembic migrations.
- Preserve idempotency under concurrent requests with the database unique constraint.
- Add pytest coverage for business-rule changes and keep Ruff clean.