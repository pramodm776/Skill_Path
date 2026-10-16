# Five-minute live demo script

## Before the demo

1. Start the application with `POLL_INTERVAL_SECONDS=10` and `MONITORING_ENABLED=true`.
2. Use a public GitHub repository you control. It must have an initial commit with API-route evidence, then a planned second commit that adds SQL-query and/or test evidence.
3. Open a real public job/internship posting in a second tab. Paste its real requirements and retain its live URL in the dashboard. If JSearch is configured, you may use its India search only to prefill a candidate; review and save the selected direct URL/text yourself.

## Demo flow

1. **Job source (45 seconds):** Save the title, company, public URL, and description. Point out the preserved URL and source excerpts next to normalized requirements. Do not claim requirements absent from the text.
2. **Repository evidence (75 seconds):** Connect the public repository. Show the default branch, inspected commit SHA, bounded-scan scope, file paths, excerpts, line references, and limitations. Highlight any SQL/testing gaps as **not demonstrated in this inspected scope**.
3. **Automatic monitor (30 seconds):** Show the monitoring card and initial snapshot in history. Explain that the server polls GitHub and snapshots are unique by SHA.
4. **Real GitHub commit (45 seconds):** In the controlled repository, add a real SQL query or automated test, commit, and push it. For example:

   ```powershell
   git add .
   git commit -m "Add parameterized query and route test"
   git push
   ```

5. **Automatic reassessment (60 seconds):** Wait for the 10-second poll; do not press Analyse. Show the reassessment event, new SHA, changed-file metadata, new evidence card, and the before/after Proof Delta comparison. If timing is tight, **Check monitor now** invokes the exact same polling path; it is not a manual assessment rewrite.
6. **Optional Telegram alert (20 seconds):** If configured before the demo, show the paired bot notification after the automatic new-SHA snapshot. It should contain only the commit summary and link, not source excerpts or credentials. Skip this step rather than improvising credentials on stage.
7. **Safety and limits (30 seconds):** Show the source URL, evidence links, safe error state, missing-evidence wording, and footer statement that credentials remain server-side.

## Judge-test notes

- Repeat the monitor check without a new push: history remains unchanged, proving duplicate SHA suppression.
- Use an invalid/private/no-token repository to show the safe GitHub error state.
- Remove `OPENAI_API_KEY` and restart: health/dashboard report deterministic mode, while all factual assessment features still work.
