# 4S Ranch Men's Soccer Website — Architecture Proposal

**Status:** Initial proposal  
**Date:** 2026-11-11

## Purpose

Replace the current league website with a maintainable Django application that keeps season history and makes public league information easy to browse. Most visitors should not need an account. League admins and coaches will sign in to manage the information they are responsible for.

This document proposes an initial direction for discussion and implementation. It does not commit to importing every historical record or automating league operations in the first release.

## Navigation and current-site requirements

The primary navigation for the new site will be **Home**, **Teams**, **Schedule**, **Standings**, **Coaches**, **Admin**, and **Rules**. Coaches and Admin remain visible navigation destinations, but their workspaces require sign-in and enforce the user's role. The current site at <https://4smenssoccer.com/> provides requirements for the public sections as follows:

- **Home:** league identity and history (established 2005), current-season links, FAQs, eligibility and new-player information, play location/map, contact link, sponsor details and promotional links. Keep copy editable by admins where practical.
- **Teams:** a season-specific directory of teams with badges and team detail pages. The current site includes team rosters/details and a lead official. Public roster visibility should be configurable while requirements are confirmed.
- **Schedule:** season selector; fixtures grouped by month/date or round; home team listed first; team badges, kickoff, venue, score for completed games and a clear scheduled/postponed status for games without scores. Include playoff rounds as distinct stages.
- **Standings:** season-specific regular-season table with position, team, played, wins, draws, losses, goals for/against, goal difference and points. Include a player leaderboard with games, points, points per game, goals, assists and yellow/red cards where the source data is available. Link to a full standings table if a compact summary is shown.
- **Coaches:** staff sign-in and a coach workspace for privileged users. Coaches can find matches involving their assigned team and submit a score after the game. This is a protected workflow; it is not a public listing of coach tools.
- **Admin:** protected admin sign-in/workspace. Admins can review score submissions, approve or reject them, and manage league data/content. Pending submissions must be visible in a review queue.
- **Rules:** current league rules with update date and the rule topics found on the existing site, including eligibility, fees/refunds, match and equipment rules, cards/suspensions, standings, playoffs and tie-breaks. Rules should be date/season aware because they can change.
- **Gallery and champions:** both exist on the old site but are not in the requested primary navigation. Keep them accessible from Home or season pages, or add a navigation item later if desired.

The site must work well on phones as well as desktop. In particular, staff should be able to upload or replace a player's photo directly from a phone camera or photo library.

The league runs multiple seasons (for example, Spring 2026 and Fall 2026). Team membership and statistics belong to a season, while a player's identity may continue across seasons. The replacement should allow visitors to select a season and browse both current and historical information.

The site also describes registration, player eligibility, a sub pool, player ratings/draft, awards, and game rules. These are relevant domain concepts, but the initial application should focus on publishing league information and maintaining its records. Registration payments and a complete draft workflow can be considered separately.

## Goals

1. Make public league information available without login.
2. Store teams, players, fixtures, results and statistics in a relational database.
3. Preserve season history and permit a season to be marked current or archived.
4. Give admins full league-management access and coaches a constrained role.
5. Deploy the Django application on Render with a managed PostgreSQL database.
6. Keep the first implementation small enough to build and operate without a separate frontend service.

## Out of scope for the first release

- Public player accounts, self-service registration, or social login.
- Payment collection, refunds, waivers, or medical/eligibility document storage.
- Automatic player drafts, sub-pool matching, attendance, or team chat.
- Real-time match updates or a native mobile app.
- Automatic synchronization with the existing website. Initial content can be entered or imported through a controlled one-time process.

## Proposed application shape

Use a single Django project with server-rendered HTML templates and progressive enhancement with modest JavaScript where useful. This keeps public pages fast and indexable and avoids maintaining a separate API and frontend before there is a need for them.

```text
Browser
  ├── Public pages (no account required)
  └── Staff pages (Django session authentication)
           │
           ▼
      Django application
      ├── Public views and templates
      ├── Admin/coach management views
      ├── Domain models and validation
      └── Django admin (initial trusted-admin interface)
           │
           ▼
      PostgreSQL on Render
```

Suggested Django apps (split only when useful during implementation):

- `core`: shared layout, home page, contact and league settings.
- `seasons`: seasons, teams, players, roster membership and awards.
- `matches`: fixtures, results, events and standings/stat calculations.
- `content`: rules, gallery entries and sponsor information.
- `accounts`: staff roles and access checks (can initially be a small module in `core`).

The domain should be organized around league seasons rather than hard-coded pages. Public URLs should remain readable and stable, for example `/seasons/fall-2026/teams/` and `/seasons/fall-2026/schedule/`.

## Data model proposal

Use Django's built-in authentication user model from the start, with a custom user model configured before the first migration if any custom identity fields are needed. Keep login accounts separate from public player records: a player does not need an account to appear on a roster or leaderboard.

Core entities:

| Entity | Key fields / relationships | Notes |
| --- | --- | --- |
| `Season` | name, slug, year, term, start/end dates, status, rules snapshot/reference | A season owns its teams, roster assignments and matches. The admin selects the active website season; only one season may be active at a time. |
| `Team` | name, slug, badge, description | Reusable identity; a team may participate in many seasons. |
| `SeasonTeam` | season, team, coach assignments, display order | Resolves the many-to-many relationship; supports a team's name/badge snapshot if historical branding needs to be preserved. |
| `Player` | display name, optional public profile/photo, rank (private) | Rank is an internal player assessment and must never be displayed publicly or included in public exports. Avoid collecting sensitive personal data unless a real workflow requires it. |
| `RosterMembership` | player, season team, jersey number, position, status | Membership details are season-specific. If player rank is season-dependent, store it here instead of on `Player`; confirm during implementation. |
| `Match` | season, home/away season teams, kickoff, venue, status, round/stage, approved scores | Supports scheduled, postponed, completed and cancelled fixtures, plus playoff rounds. |
| `ScoreSubmission` | match, submitted by, home/away score, status, submitted/reviewed timestamps, reviewer, decision note | One report per assigned team/coach as appropriate. Submissions do not alter public results until an admin approves the resolved score. Preserve submission and review history. |
| `MatchAppearance` | match, player/roster membership, played flag/minutes (optional) | Enables player games-played stats if recorded consistently. |
| `MatchEvent` | match, player, event type, minute, assist (optional), notes | Goals and cards can power player leaderboards. Keep corrections traceable. |
| `Award` | season, player or team, award type, citation/notes | Covers champions, MVP, Golden Boot, Golden Gloves and other league-defined honors. |
| `RuleSet` / `Rule` | season or effective date, title, body/order | Rules change over time; archived seasons should retain the applicable rules. |
| `GalleryItem` | season (optional), image, caption, taken/published date | Media can be hosted in object storage rather than PostgreSQL. |
| `LeagueSetting` | contact details, venue/map link, sponsor and home-page copy | Keep frequently edited public copy out of templates. |

Use foreign keys and uniqueness constraints to prevent duplicate season slugs, duplicate roster entries, and a team playing itself. Store match event data as the source for player goals/cards where practical; compute derived totals rather than maintaining multiple independently editable copies. Standings can be calculated from completed match results at first. If performance later requires caching, treat it as a rebuildable projection.

## Roles and access

All routes are public unless explicitly listed as staff-only. Use Django authentication, CSRF protection and server-side permission checks for every write action.

| Capability | Anonymous visitor | Coach | Admin |
| --- | --- | --- | --- |
| View public seasons, teams, rosters, schedule, results, standings, stats, rules, awards and gallery | Yes | Yes | Yes |
| Sign in to staff area | No | Yes | Yes |
| Submit a score for a match involving an assigned team | No | Yes; creates a pending submission | Yes |
| Resolve conflicting coach score submissions | No | Yes; see reconciliation workflow below | Yes |
| Review score submissions and set active website season | No | No | Yes; approve/reject and select active season |
| Manage league seasons, teams, player identities/photos/ranks, all matches/results, rules, content, staff accounts and roles | No | No | Yes |

Coach scope must be enforced in the server-side query and mutation layer, not only by hiding controls. A coach can submit only for matches involving a team to which they are assigned in that season. Admin means a trusted league administrator, distinct from Django's `is_superuser`; reserve superuser access for technical maintenance. Initially, Django admin can manage records, while the Coaches and Admin navigation items lead to purpose-built staff pages. Avoid granting coaches unrestricted Django admin access.

### Score submission, reconciliation and approval

1. Each authenticated coach opens the Coaches section and sees scheduled/recent matches involving their assigned team(s), including whether their team has reported a result.
2. A coach submits the match score from their team's perspective. Store the entered home and away values consistently against the match's home/away teams, along with submitter and timestamp.
3. When reports from both teams match, the match enters the Admin approval queue as a matched report. An admin can approve the shared score.
4. When reports differ, the match enters a reconciliation state. Provide a coach-facing UI showing both reports and asking a coach to select the true home/away score (or enter a corrected score) and submit that resolution. Preserve both original reports.
5. The reconciled score remains pending until admin approval. If coaches cannot resolve the disagreement, the admin can decide or request clarification; this is visible in the review history.
6. Public schedule, standings and player statistics use only the last admin-approved result (or show no result for a new match) while a submission or reconciliation is pending.
7. On approval, the score becomes official and standings are recalculated. A rejection includes an explanation and returns the match to a coach correction or admin resolution state.
8. Record the full history: all submitted values, submitters, reconciliation choice, reviewer, timestamps, outcomes and notes. Prevent duplicate reports by the same team for the same match while a report is active, and allow a clear correction/resubmission path.

Both teams' coaches are expected to report a score so the system can compare them. Automatic approval is not proposed: matching reports still require admin approval, as requested.

### Active season and player photos

- Admins choose the single active season in the Admin workspace. Public Home, Teams, Schedule, Standings and Rules default to that season; visitors may still switch to archived seasons.
- Changing the active season must not alter or move historical data. The update should be an atomic operation that clears the former active season and sets the new one.
- Player photo upload/replacement is a staff action available to admins and assigned coaches. On phones, the upload form should allow camera capture or selecting an existing image, show a preview, and clearly indicate when the new photo is saved.
- Store image files in persistent object/media storage and keep only file metadata/reference in PostgreSQL. Validate file type and size, generate appropriately sized display variants, and ensure uploaded images are not publicly writable.
- Public photo display follows roster/profile visibility settings. Internal ranks remain private regardless of photo visibility.

## Public pages and behavior

- **Home:** league introduction, current season links, location, FAQs, sponsor and contact details.
- **Season selector:** current season by default, with access to archived seasons.
- **Teams:** season-specific team directory and detail pages with public roster information.
- **Schedule:** fixtures grouped by month/date or round, with venue, kickoff, score/status and a visible indication that a submitted result is pending review for signed-in staff only.
- **Standings:** derived only from admin-approved regular-season results using the season's point system and tie-break rules.
- **Player stats:** season leaderboard for appearances, goals, assists and cards where data is maintained.
- **Champions and awards:** historical winners and season awards.
- **Rules:** current and historical rule sets.
- **Gallery:** season-filtered image collection.

The current site contains some inconsistent season labels and historical content. The new site should show the selected season explicitly and avoid silently mixing records from different seasons.

### Mobile and accessibility requirements

- Use responsive layouts starting with narrow phone screens; schedule cards, team lists and standings tables must remain usable without horizontal page scrolling.
- Provide a compact mobile navigation with all seven requested sections and clear signed-in state for staff.
- Make score entry and photo upload controls touch-friendly, with labels, validation messages and confirmation states that work with screen readers and keyboard navigation.
- Use responsive/compressed images and avoid loading full-resolution gallery or player images into small-screen views.

## Data integrity and domain rules

- A match references two different teams participating in that match's season.
- A player can have one roster membership per season unless an explicit transfer/exception is recorded.
- Standings include only completed regular-season matches; playoff results are presented separately unless league policy says otherwise.
- Standings points and tie-break order should be season-configurable or versioned with the rules, not embedded as undocumented constants.
- Player ratings, contact data, and internal notes remain staff-only.
- Player rank is private staff data and must not be rendered in templates, public API responses, metadata, or public exports.
- Only the admin-selected active season is the default for public pages; archived seasons remain directly browsable.
- A public match result changes only after admin approval, whether coach reports matched or were reconciled.
- Results and match events can be corrected by authorized staff; record who changed them and when through Django admin logs or an audit mechanism.

## Hosting and operations

- **Application:** Django deployed as a Render web service.
- **Database:** Render-managed PostgreSQL; SQLite may be used only for local throwaway development if desired. Development and production should use the same database engine to reduce surprises.
- **Static files:** Django static assets collected during deployment and served through a supported static-file setup/CDN.
- **Media:** team badges and gallery images stored in object storage or a compatible managed media service; save URLs/metadata in PostgreSQL. Do not rely on the Render service filesystem for persistent uploads.
- **Secrets:** database URL, Django secret key, email credentials and storage credentials supplied through Render environment variables.
- **Deployment:** deploy from the repository, run migrations as a controlled release step, then start Gunicorn. Configure HTTPS, allowed hosts, secure cookies, CSRF trusted origins, health checks and database backups.
- **Email:** optional for initial release; add transactional email only when password reset or staff invitations are implemented.

Render's current Django deployment guidance and product details should be checked when implementation begins, since hosting configuration can change.

## Security and privacy

- Require strong passwords for staff and provide password reset only through verified email.
- Use Django's built-in password hashing, sessions, CSRF protection and permission system.
- Give each staff account the least access needed; deactivate access promptly when a coach role ends.
- Do not expose player ratings, email/phone, registration status, or internal notes on public views.
- Collect the minimum player data needed for league administration and define a retention policy before storing sensitive eligibility or waiver records.
- Keep production secrets out of source control and ensure database backups and restore procedures are available.

## Automated end-to-end testing

Use **Playwright with the `pytest-playwright` Python plugin**. It keeps browser tests in the project's Python ecosystem and supports Chromium, Firefox, WebKit, and mobile emulation. Begin with Chromium on GitHub Actions pull requests; expand browser coverage if issues or usage justify the extra runtime. Use Django's test client or focused unit tests for model and permission details, and reserve E2E tests for critical user journeys.

Initial browser journeys should cover public navigation and responsive rendering, coach login and score submission, conflicting-score reconciliation, and admin approval. Run Django checks and the relevant unit tests in the same pull-request workflow. Upload Playwright reports/traces as workflow artifacts when a run fails.

Reference: [Playwright for Python introduction](https://playwright.dev/python/docs/intro), [Playwright Python CI guide](https://playwright.dev/python/docs/ci-intro), and [GitHub Actions CI guide](https://playwright.dev/docs/ci-intro).

## Initial delivery phases

1. **Foundation:** Django project, custom user decision, PostgreSQL configuration, base layout, season model, deployment skeleton.
2. **Public league pages:** season selector, teams/rosters, schedule/results, derived standings and player stats, rules, awards and gallery.
3. **Admin operations:** secure staff login, admin management for seasons and records, active-season control, pending score review queue with approve/reject actions, audit trail and content editing.
4. **Coach workflows:** secure sign-in, assigned-team match list, paired score submissions and mismatch resolution UI, plus scoped player photo upload/replacement.
5. **Historical content:** import selected seasons from the old site, reconcile inconsistencies, and validate totals before public launch.
6. **Later options:** player registration, sub-pool, attendance, draft support, notifications, or payment integration based on league priorities.

The first implementation task is a small local Django proof of concept with responsive navigation. Automated browser checks should be added as soon as the first stable user journey exists, then run on GitHub Actions pull requests.

## Decisions to make during implementation

- Which seasons and player statistics should be migrated first, and what source data is available beyond the public site?
- Can a player move between teams during a season, and how should that appear in stats?
- Which match events will staff reliably record (goals, assists, appearances, yellow/red cards)?
- Should a coach resolve a disagreement by choosing the submitted home/away score or by entering a final score with an explanation? The UI should support either policy without losing original reports.
- Should roster names be public, and should player photos/profiles be optional?
- What is the canonical policy for season-specific rules and standings tie-breaks?
- Which Render plan and media-storage provider fit expected traffic and image volume?

## Reference

- Existing site reviewed on 2026-11-11: <https://4smenssoccer.com/> (home, teams, schedule, standings, rules and champions pages).
- Render deployment configuration will be verified against the then-current official documentation during implementation.
