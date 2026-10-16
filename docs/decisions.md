# Decisions and tradeoffs

## Polling rather than webhooks

Polling needs no public tunnel, webhook secret, or deployment during a 24-hour hackathon. It directly meets the brief's request to detect repository changes. The default is 60 seconds; set `POLL_INTERVAL_SECONDS=10` for a short live demo. A manual **Check monitor now** uses the same change-detection path and never rewrites an assessment itself.

## Deterministic evidence first

Repository source claims are verifiable facts, so matching is deterministic. The LLM is optional interpretation only and cannot supply a path, line reference, status, or citation. This keeps controlled no-key mode useful and prevents fabricated evidence from becoming visible.

## Conservative requirements normalization

The engine only normalizes terms directly present in the description into a supported skill catalog. It keeps the matching phrase and excerpt. It does not infer undocumented requirements from a company, title, URL, or broad model guess.

## Missing is scope, not absence

An inspected repository is bounded and may not represent all work. The only allowed missing-evidence wording is **not demonstrated in this inspected scope**. Contextual files such as READMEs or manifests may be shown as weak signals but are not treated as proof of mastery.

## Privacy and safety boundaries

GitHub tokens and OpenAI keys are environment values and never passed by the browser. The GitHub client is read-only and does not execute source code. Likely secret files are excluded. Stored snapshots retain only safe inspection metadata plus selected evidence excerpts rather than a complete mirror of repository contents.

## Bounded agentic orchestration

SkillPath AI is not an autonomous multi-agent swarm. Its agentic flow is a deterministic, auditable orchestrator: normalize real requirements, inspect a bounded GitHub revision, validate citations, persist an immutable snapshot, detect a new SHA, compare the next snapshot, then optionally ask an LLM only to phrase a secondary interpretation of evidence already validated. This is faster to demo and safer to explain than delegating repository conclusions to multiple agents.

## JSearch is discovery, not a source of truth

JSearch is the India-ready discovery provider because it can search with `country=in`. Search output only fills a review step. The user must still choose a direct public posting URL and save returned or pasted description text through the normal ingestion endpoint. This preserves the official requirement to retain a real posting URL and prevents provider results from silently becoming job requirements.

## Controlled LLM fallback

OpenAI is the optional primary interpretation provider. xAI/Grok is attempted only after a retryable network, timeout, rate-limit, or server-side OpenAI failure and only when explicitly enabled with a configured model/key. OpenAI authentication, validation, and configuration errors do not fail over. Neither LLM can change evidence, status, line reference, or fit calculation.

## Telegram is a proof-delta alert, not a chat agent

Telegram pairing uses a short-lived one-time `/start` code stored only as a hash. The bot accepts only `/start` and `/stop`; it discards free-form incoming messages. It sends one brief notice only after the monitor automatically creates a snapshot for a new commit SHA. Notification failure never blocks assessment persistence. This MVP has no user-authentication system, so pairing is an operator/demo feature; production requires account ownership and authorization controls.

## Azure single-service deployment

The dashboard and API deploy together to one Azure Container App. This avoids Firebase hosting and cross-origin configuration while keeping every key on the server. A single always-on replica is intentional because the polling monitor must run and SQLite is not safe for horizontal writers. Azure Files persists the hackathon database; Azure Database for PostgreSQL is the production migration path.
