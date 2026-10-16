# SkillPath AI working rules

- Keep GitHub and LLM credentials server-side in environment variables. Never put a token, `.env` value, or request authorization header in frontend code, logs, fixtures, or documentation.
- The GitHub integration is read-only. Do not clone, execute, install, or import inspected repository code.
- An evidence citation must resolve to a path, line range, and excerpt returned by the current bounded inspection. Do not use a filename, README, package manifest, or LLM output alone as proof of a skill.
- Missing evidence must always be described as **not demonstrated in this inspected scope**, never as proof that a student lacks a skill.
- A change assessment must be tied to a new GitHub commit SHA. Do not overwrite an earlier snapshot or fabricate an automatic event.
- Keep the app a single FastAPI service plus SQLite and vanilla HTML/CSS/JavaScript unless the user explicitly authorizes a scope change.
- Read `docs/team-context.md` before changing a cross-cutting module. It is the shared handoff for teammates using Antigravity, Codex, or another IDE.
- Work on a short-lived branch (`feature/<area>-<summary>` or `fix/<area>-<summary>`), keep commits focused, and open a pull request into `main`. Do not force-push or commit `.env`, database files, tokens, or generated local assets.
- Before a merge, run the relevant tests and update the shared contract or team context if an endpoint, persistence shape, security boundary, or demo step changes.
