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

Open <http://127.0.0.1:8000/> on the development machine. To view it from a phone on the same Wi-Fi, start the server on all network interfaces:

```bash
python manage.py runserver 0.0.0.0:8000
```

Then open `http://<development-machine-Wi-Fi-IP>:8000/` on the phone. On Linux, `hostname -I` lists local addresses; use the address for the Wi-Fi network (for example, `192.168.0.63`), not a Docker address. Django's development server reloads when source files change. Use `Ctrl+C` to stop it; run `deactivate` to leave the virtual environment.

The POC uses local SQLite and has no production credentials or external services. Do not deploy it as-is. The SQLite database is ignored by Git and can be recreated with `python manage.py migrate`.

## E2E tests

The proof of concept uses Playwright with its Python pytest plugin. Install the test dependencies and Chromium once:

```bash
python -m pip install -r requirements-dev.txt
python -m playwright install chromium
```

Start the website in one terminal:

```bash
source .venv/bin/activate
python manage.py runserver
```

Then run the browser checks in another terminal:

```bash
source .venv/bin/activate
pytest
```

The smoke checks cover all seven tabs and check that the mobile layout fits a 390-pixel viewport. The GitHub Actions pull-request workflow is tracked in [TODO.md](TODO.md).
