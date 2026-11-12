# 4S Ranch Men's Soccer

Django proof of concept for a season-based league website. The current local POC provides a responsive layout and the requested navigation: Home, Teams, Schedule, Standings, Coaches, Admin, and Rules. Data, login, and score workflows are planned in [TODO.md](TODO.md).

## Local development

Requires Python 3.10 or newer.

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python manage.py migrate
python manage.py runserver
```

Open <http://127.0.0.1:8000/>. Django's development server reloads when source files change. Use `Ctrl+C` to stop it; run `deactivate` to leave the virtual environment.

The POC uses local SQLite and has no production credentials or external services. Do not deploy it as-is. The SQLite database is ignored by Git and can be recreated with `python manage.py migrate`.

## E2E tests

The project will use Playwright with its Python pytest plugin. Once the E2E setup task is complete, install the test dependencies and browser, then run the suite:

```bash
python -m pip install -r requirements-dev.txt
python -m playwright install chromium
pytest
```

The GitHub Actions pull-request workflow is tracked in [TODO.md](TODO.md) and will be added with the first meaningful browser flow.
