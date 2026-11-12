# 4S Ranch Men's Soccer

Django proof of concept for a season-based league website. The current local POC provides a responsive layout and the requested navigation: Home, Teams, Schedule, Standings, Coaches, Admin, and Rules. Data, login, and score workflows are planned in [TODO.md](TODO.md).

## Local development

Requires Python 3.10 or newer and [uv](https://docs.astral.sh/uv/).

In this workspace, point uv's cache at the project because the default user cache is not writable:

```bash
export UV_CACHE_DIR="$PWD/.uv-cache"
```

Keep that shell open for the commands below. The cache is local and ignored by Git.

```bash
uv sync --locked
uv run --locked python manage.py migrate
uv run --locked python manage.py createsuperuser
uv run --locked python manage.py runserver
```

Open <http://127.0.0.1:8000/> on the development machine. To view it from a phone on the same Wi-Fi, start the server on all network interfaces:

```bash
uv run --locked python manage.py runserver 0.0.0.0:8000
```

Then open `http://<development-machine-Wi-Fi-IP>:8000/` on the phone. On Linux, `hostname -I` lists local addresses; use the address for the Wi-Fi network (for example, `192.168.0.63`), not a Docker address. Django's development server reloads when source files change. Use `Ctrl+C` to stop it.

The POC uses local SQLite and has no production credentials or external services. Do not deploy it as-is. The SQLite database is ignored by Git and can be recreated with `uv run --locked python manage.py migrate`.

After creating a superuser, open <http://127.0.0.1:8000/django-admin/> and add a published season, mark it active, then add its teams, rosters, fixtures, and season rules. The public tabs will read from those records. Local image uploads are stored under the ignored `media/` directory.

## E2E tests

The proof of concept uses Playwright with its Python pytest plugin. `uv sync --locked` installs the development dependencies. Install Chromium once:

```bash
uv run --locked playwright install chromium
```

Start the website in one terminal:

```bash
uv run --locked python manage.py runserver
```

Then run the browser checks in another terminal:

```bash
uv run --locked pytest
```

The smoke checks cover all seven tabs and check that the mobile layout fits a 390-pixel viewport. The GitHub Actions pull-request workflow is tracked in [TODO.md](TODO.md).

Add or update project dependencies with `uv add <package>` and development dependencies with `uv add --dev <package>`. Commit both `pyproject.toml` and `uv.lock` so local and CI installs use the same resolved versions.
