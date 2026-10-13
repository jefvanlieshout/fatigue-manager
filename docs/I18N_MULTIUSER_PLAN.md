# Roadmap: English/Dutch and safe multiple users

Status: APPROVED DESIGN DIRECTION / NOT IMPLEMENTED
Created: 2026-10-13
Target: small follow-up releases after the working v0.1.1 activity diary.

## Product rules

- Logging an activity remains the default screen, with the same short workflow: activity, energy before, energy after, save.
- Settings and any later optional features must not clutter the tracker.
- English is the default language for new installations/accounts; Dutch is selectable at any time.
- Every person's data belongs to that person. Different accounts never see one another's records unless a distinct, explicit sharing feature is intentionally designed later.
- No sign-up portal open to strangers, no email service, no third-party account provider, no cloud database, no telemetry, and no GitHub Actions.
- Continue to use the existing FastAPI/Jinja2/SQLite stack in the dedicated Proxmox LXC.

## Release A (proposed v0.2.0): simple language selection

Scope:
1. Create a small centralized translation catalog for English and Dutch (interface, login, validation and messages); use a common template translation helper. Avoid duplicated pages.
2. Set English as the initial default; offer a subtle 'EN / NL' selector in the header or under Settings. Only one compact control, not a settings dashboard.
3. Let visitors switch language even before login. Persist their choice in a locale cookie, then keep it in their profile when multiple accounts are implemented.
4. Translate labels, day navigation, errors, action confirmations and accessibility text. Use understandable dates/times for the chosen language, while keeping stored timestamps in UTC/Europe-Brussels as before.
5. Add automated tests that compile every template, validate that translation keys exist for both languages, and smoke-test login/entry workflows in each language.
6. Keep user-entered activity text as typed: NEVER machine-translate someone's own notes.

Acceptance criteria:
- A first-time visitor sees English, can switch to Dutch without losing page state, and sees consistent translations even on login and error pages.
- Logging, browsing, editing, deleting and CSV export still work.
- The main form is no more complicated.

## Release B (proposed v0.3.0): multiple private accounts

Scope: small family installation (2–10 people). Existing SQLite is sufficient.

### Account and diary data model

Add users table:
- id (stable internal primary key)
- username (unique, case-normalized for lookup)
- display_name (optional friendly label)
- password_hash (per-user salted scrypt or other vetted password KDF; never plaintext)
- preferred_language (en/nl)
- role (admin/member), is_active, created_at

Add user_id to EVERY diary entry, non-null foreign key to users(id). Index diary entries by (user_id, occurred_at). Future calendar/events and any derived aggregates must also be scoped by user_id.

Authorization rules (enforced in DB queries on the server, never only the frontend):
- List for the signed-in user; filter using their server-validated user_id.
- Fetch/edit/delete by both id AND user_id; reject another user's record.
- History, suggestions and CSV export only include the current user's own data.
- No 'switch user' dropdown that silently changes identities.
- An admin may manage accounts, but does NOT automatically gain permission to inspect personal diary entries. Sharing is out of scope.

### Login / account management

- Change login to username + password.
- Never store the user's password or sensitive notes in client-side cookies or logs.
- Replace the old session flag authenticated=true with an authenticated account identity validated against an active user record. Prefer opaque, revocable server-side sessions with expiry and cookie flags HttpOnly, SameSite and Secure under HTTPS.
- Rotate/invalidate legacy sessions on migration; implement logout and optional per-account session revocation.
- Keep CSRF protection on state-changing routes, including login/logout and account management.
- Rate-limit login failures by account and network address without trusting forwarded headers from untrusted clients; bound brute-force attempts.
- For this small family rollout, create accounts and reset passwords via a root-only admin CLI script on the LXC. No public self-registration, mail/SMTP or complicated admin dashboard.
- Account deletion should never silently erase personal data. Initially support deactivation; any permanent deletion/export should be a separate deliberate action with confirmation and backup.
- Keep the UI simple: normal login page and a small Settings menu with language, change password and log out. Avoid role controls on the activity form.

### Safe migration from current v0.1.1

Current database schema version is 1 and there is ONE global set of entries and ONE password hash stored privately in /etc/fatigue-manager.env.

Before upgrading:
1. Take and verify a SQLite online backup, copy it outside the LXC, and capture the current release commit.
2. Explicitly decide which new user owns any existing activities (do not silently attribute another person's entries). Even if currently empty, verify entry count.
3. Within a transactional migration, create users; preserve the current scrypt login credential for the chosen original account without revealing it; add a non-null ownership column to the entry table (rebuild table if SQLite requires it); attach every old entry to the agreed account.
4. Validate counts, referential integrity and version marker (e.g. SQLite PRAGMA user_version=2), and disallow startup if schema and application versions are incompatible.
5. Once deployed, restart the service, invalidate old sessions and log in with the selected username + existing password. Create extra accounts through the admin CLI.
6. If anything goes wrong, stop the service and restore BOTH the matching database backup and known-good code version. Don't rerun a partial migration blindly.

### Security / data separation test matrix

- User A cannot read, edit, delete or export B's entries, including guessing a direct entry URL or requesting B's date range.
- Activity autocomplete, summaries and any upcoming calendar never mix user data.
- Sessions must not work after account deactivation; logout and session revocation work.
- Bad credentials, CSRF failures and excessive login attempts are rejected; server messages don't disclose whether a username exists.
- Password reset/create-account CLI are restricted to authorized administrators, and secrets are never committed to the public repo.
- Migration with zero and multiple legacy entries preserves all data, valid dates and foreign keys.
- English and Dutch accounts may be signed in simultaneously from different devices with independent settings.
- Test on mobile and desktop. Use local pytest and manual scripts; no GitHub Actions.

### Deployment / maintenance

- Keep one FastAPI service, one SQLite database, and the existing Proxmox LXC; no need for one container per user.
- Keep /var/lib/fatigue-manager private and the public GitHub repository free of health data.
- Expose only through trusted private LAN initially. For access from elsewhere, prefer authenticated HTTPS/Tailscale and Secure cookies. Never forward HTTP port 8080 publicly.
- Update the install/update/backup/restore scripts and HANDOVER before release. Backups belong outside the Git repository; restore must be tested.
- Change the tests so the new account rules are verified on every local release.

## Not in these releases

No calendar redesign, extra questionnaires, pain graphs, AI planner, public signup, shared household diary, public account directory, permissions dashboard, email notifications, OAuth or social login. Add features only if the family later requests them, with opt-in UI.

## Order and next checkpoint

1. Ask the family to try the existing v0.1.1 activity form on a real phone and report usability friction.
2. Implement/review v0.2.0 language switch; deploy with backups and local tests.
3. Before v0.3.0 migration, identify owner of any existing entries and choose account names, then implement backend authorization and tests FIRST, before exposing the additional-user feature.
4. Deploy v0.3.0 to the SAME LXC only after backup, staging/test migration, local security tests and a login smoke test.

This file is a design and release plan, NOT a claim that language switching or multi-user support is already available.
