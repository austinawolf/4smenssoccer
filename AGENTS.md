# Project Primer for Coding Agents

## Read first

Before changing the project, read `README.md`, `ARCHITECTURE.md`, and `TODO.md`. Keep implementation aligned with the architecture and update TODO checkboxes when a milestone is complete.

## Project at a glance

- This is a server-rendered Django website for the 4S Ranch Men's Soccer League. Do not add a separate frontend framework without updating the architecture first.
- `config/` contains Django settings, URL routing, and WSGI setup.
- `siteapp/models.py` defines seasons, teams, roster memberships, players, matches, rules, awards, and gallery records.
- `siteapp/admin.py` exposes league data to Django's built-in admin at `/django-admin/`.
- `siteapp/views.py` selects the active/public season and builds standings and the player leaderboard.
- `siteapp/templates/siteapp/section.html` renders the public sections; `siteapp/static/siteapp/site.css` contains their responsive styles.
- `siteapp/fixtures/local_demo.json` contains a partial public-data snapshot for local development. See README for its sources and limitations.
- `ARCHITECTURE.md` describes the planned coach score reporting and admin approval workflow. Those staff workflows are not implemented yet.

## Python and local data

Use `uv` and the committed lockfile. In this managed workspace, set the local uv cache before running project commands:

```bash
export UV_CACHE_DIR="$PWD/.uv-cache"
uv sync --locked
```

The local database uses SQLite. Apply migrations and, when demo data is needed, load the fixture:

```bash
uv run --locked python manage.py migrate
uv run --locked python manage.py loaddata siteapp/fixtures/local_demo.json
```

Create a local admin account with `uv run --locked python manage.py createsuperuser`. The website admin is at `/django-admin/`; the public Admin tab is at `/admin/`.

## Show and verify completed changes

After each task, try to bring up the site with the completed changes so the user can see them. Django's runserver reloads Python and template changes automatically; if it has stopped, restart it. Prefer reusing the existing server on port 8000 instead of starting a duplicate:

```bash
ss -ltnp | rg ':8000'
uv run --locked python manage.py runserver 0.0.0.0:8000
```

Use <http://127.0.0.1:8000/> on the development machine. For a phone on the same Wi-Fi, use `http://<development-machine-Wi-Fi-IP>:8000/` (on Linux, find the Wi-Fi address with `hostname -I`). After changes, check the affected page in a browser and make sure it responds successfully. For UI changes, also run the Playwright smoke checks against the running site:

```bash
uv run --locked pytest
```

These browser checks expect the local server to be running and demo data to be loaded. Report the local URL and what was checked when handing the task back.
