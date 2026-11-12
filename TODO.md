# Implementation TODO

Implement in order, keeping each step small and locally runnable. Update this list as tasks are completed.

## Proof of concept

- [x] Create a minimal Django project and responsive shell with Home, Teams, Schedule, Standings, Coaches, Admin, and Rules navigation.
- [ ] Run the POC locally and confirm every tab and the mobile layout work in a browser.
- [ ] Add a short smoke E2E test for navigation using Playwright.

## Core league data

- [ ] Add database-backed seasons and an admin-controlled single active season; make public pages default to it.
- [ ] Add teams, season-team entries, players, season rosters, player photos, and private player rank.
- [ ] Add matches, schedule display, approved results, and season-specific rules.
- [ ] Calculate standings from approved regular-season results and publish the season leaderboard from recorded match stats.
- [ ] Add champions/awards and gallery pages or links, based on which historical content will be migrated.

## Staff workflows

- [ ] Add staff login and role model for admins and coaches; keep player profiles separate from login accounts.
- [ ] Assign coaches to teams by season and enforce scope on the server for every write.
- [ ] Add coach score reporting so both teams can submit match scores.
- [ ] Add score comparison and coach reconciliation UI when reports disagree.
- [ ] Add admin pending-results queue with approve/reject and review history; only approved results affect public pages.
- [ ] Add phone-friendly player photo upload/replacement for admins and assigned coaches.
- [ ] Add admin editing for rules, homepage content, sponsor information, teams, players and schedule.

## Quality and deployment

- [ ] Add unit tests for model constraints, permissions, score states, active-season switching and standings.
- [ ] Configure Playwright E2E tests with `pytest-playwright`, covering public navigation and the score submission/review flow.
- [ ] Add a GitHub Actions pull-request workflow that installs Python dependencies and Chromium, runs Django checks/unit tests and Playwright E2E tests, and uploads reports on failure.
- [ ] Switch development and production configuration to PostgreSQL and environment-based secrets.
- [ ] Configure persistent media storage, image validation/resizing, and phone upload behavior.
- [ ] Prepare Render deployment, migrations, health check, backups, and production security settings.
- [ ] Choose historical seasons and records to migrate; reconcile source inconsistencies before importing.
