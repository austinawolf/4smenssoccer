# 4S Ranch Men's Soccer

Django proof of concept for a season-based league website. The current local POC provides a responsive layout and the requested navigation: Home, Teams, Schedule, Standings, Coaches, Admin, and Rules. Data, login, and score workflows are planned in [TODO.md](TODO.md).

## Local development

Requires Python 3.10 or newer and [uv](https://docs.astral.sh/uv/).

In this workspace, point uv's cache at the project because the default user cache is not writable:

```bash
export UV_CACHE_DIR="$PWD/.uv-cache"
```

Keep that shell open for the commands below. The cache is local and ignored by Git.

To start the regular local website, run:

```bash
./start.sh
```

It applies database migrations and starts the site at <http://127.0.0.1:8000/>. For a brand-new local database, load the full demo data once before starting:

```bash
export UV_CACHE_DIR="$PWD/.uv-cache"
uv sync --locked
uv run --locked python manage.py loaddata siteapp/fixtures/local_demo.json
```

Open <http://127.0.0.1:8000/> on the development machine. To view it from a phone on the same Wi-Fi, start the server on all network interfaces:

```bash
uv run --locked python manage.py runserver 0.0.0.0:8000
```

Then open `http://<development-machine-Wi-Fi-IP>:8000/` on the phone. On Linux, `hostname -I` lists local addresses; use the address for the Wi-Fi network (for example, `192.168.0.63`), not a Docker address. Django's development server reloads when source files change. Use `Ctrl+C` to stop it.

For a separate, smaller staff-workflow demo, run `./start-simple-demo.sh` and open <http://127.0.0.1:8001/>. It uses `siteapp/fixtures/local_demo_simple.json` and an isolated `.simple-demo.sqlite3`, reset from that fixture each time it starts, so it does not replace the full demo database. It has two teams with three players each, one past game with matching reports waiting for approval, one past unreported game and one future game. Sign in at `/staff/login/` with `admin` / `admin`, `coach_rovers` / `coach`, or `coach_athletic` / `coach`.

On Render, the web service start command is `uv run --locked gunicorn config.wsgi:application`. The project must include Gunicorn in `pyproject.toml` and `uv.lock` for that command to work; the local start scripts use Django's development server instead. Set `SECRET_KEY` to a unique secret in Render. `DJANGO_DEBUG` defaults to false on Render, and the `RENDER_EXTERNAL_HOSTNAME` provided by Render is automatically added to allowed hosts and trusted HTTPS CSRF origins. For a custom domain, add its hostname to `DJANGO_ALLOWED_HOSTS` and its full `https://` origin to `CSRF_TRUSTED_ORIGINS` (comma-separated if there are multiple).

To configure staff access, open `/django-admin/`, edit a user and add a Staff profile inline with role **Coach** or **League administrator**. Give league administrators Django's **Staff status** too if they need direct Django admin access. Add each coach's season-specific team assignment in **Coach assignments**. Staff sign in at `/staff/login/`. A coach saves a score and player contributions as a pending team report, then submits it or cancels it. Reports from both teams are compared, and an administrator approves or rejects the resulting score. Player events affect public stats only after approval. The same workspace provides phone-friendly player photo uploads. Django admin manages league records and the single **Homepage and sponsor content** record.

The POC uses local SQLite and has no production credentials or external services. Do not deploy it as-is. The SQLite database is ignored by Git and can be recreated with `uv run --locked python manage.py migrate`.

The optional `siteapp/fixtures/local_demo.json` fixture is based on the old site's public [Fall 2026 teams](https://4smenssoccer.com/teams/), [schedule](https://4smenssoccer.com/schedule/), and [rules](https://4smenssoccer.com/league-rules/) pages, captured November 11, 2026. It includes seven real team names, the player names listed on their team pages, all 35 published regular-season fixtures (with scores where published), and a shortened rules summary. The old public pages did not provide player ranks or photos, so those fields are blank; match-by-match player appearances and scoring events are not inferred. This is a partial season snapshot, not a full historical import. Connor Swartout appears on both Hufflepuff and Up Your ARSEnal team pages; the fixture assigns him to Up Your ARSEnal, consistent with the September 13 match page. After creating a superuser, open <http://127.0.0.1:8000/django-admin/> to edit the local records. Local image uploads are stored under the ignored `media/` directory.

The fixture also seeds local-only staff logins: `admin` / `admin` (superuser) and one coach per team (`coach_grassholes`, `coach_pinkponyclub`, `coach_hufflepuff`, `coach_seaurchins`, `coach_purpletippedcobras`, `coach_smurfturf`, `coach_upyourarsenal`), each with password `coach`. Use them at `/staff/login/`. These public demo credentials are for local development only; do not expose or deploy them.

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
