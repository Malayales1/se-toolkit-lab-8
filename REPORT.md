# Lab 8 — Report

Paste your checkpoint evidence below. Add screenshots as image files in the repo and reference them with `![description](path)`.

## Task 1A — Bare agent

Prompt: `What is the agentic loop?`

> The agentic loop is the fundamental cycle that autonomous AI agents follow to accomplish tasks: perceive, reason/plan, act, observe, and repeat. Nanobot uses that loop to read context, decide on the next action, execute tools, observe results, and iterate until the request is complete.

Prompt: `What labs are available in our LMS?`

> I can see from the LMS skill documentation that tools like `lms_labs` should exist, but they are not configured in the bare-agent setup. Without those MCP tools, I cannot reliably query the live LMS and should not guess the available labs.

## Task 1B — Agent with LMS tools

Prompt: `What labs are available?`

> Here are the available labs in the LMS:
>
> 1. Lab 01 – Products, Architecture & Roles
> 2. Lab 02 — Run, Fix, and Deploy a Backend Service
> 3. Lab 03 — Backend API: Explore, Debug, Implement, Deploy
> 4. Lab 04 — Testing, Front-end, and AI Agents
> 5. Lab 05 — Data Pipeline and Analytics Dashboard
> 6. Lab 06 — Build Your Own Agent
> 7. Lab 07 — Build a Client with an AI Coding Agent
> 8. lab-08

Prompt: `Describe the architecture of the LMS system`

> The LMS platform consists of several containerized services:
> `caddy` as the public gateway and reverse proxy, `backend` as the FastAPI API service, `postgres` as the relational database, `qwen-code-api` as the OpenAI-compatible LLM proxy, and the observability stack of `otel-collector`, `victorialogs`, and `victoriatraces`. The high-level flow is user request -> caddy -> backend -> postgres, with telemetry flowing through OTel into VictoriaLogs and VictoriaTraces.

## Task 1C — Skill prompt

Prompt: `Show me the scores`

> There are 8 labs available. Which lab would you like to see scores for?
>
> 1. Lab 01 – Products, Architecture & Roles
> 2. Lab 02 — Run, Fix, and Deploy a Backend Service
> 3. Lab 03 — Backend API: Explore, Debug, Implement, Deploy
> 4. Lab 04 — Testing, Front-end, and AI Agents
> 5. Lab 05 — Data Pipeline and Analytics Dashboard
> 6. Lab 06 — Build Your Own Agent
> 7. Lab 07 — Build a Client with an AI Coding Agent
> 8. lab-08
>
> Please specify which lab (for example, `lab-04`).

## Task 2A — Deployed agent

Startup log excerpt from the VM:

```text
nanobot-1  | Using config: /app/nanobot/config.resolved.json
nanobot-1  | 🐈 Starting nanobot gateway version 0.1.4.post5 on port 18790...
nanobot-1  | WebChat channel enabled
nanobot-1  | MCP server 'lms': connected, 9 tools registered
nanobot-1  | Agent loop started
```

## Task 2B — Web client

Web client deployment checks from the VM:

```text
HTTP/1.1 200 OK
Content-Type: text/html; charset=utf-8
<base href="/flutter/">
<title>Nanobot</title>
```

WebSocket conversation transcript:

Prompt: `What labs are available?`

> Available labs: Lab 01 – Products, Architecture & Roles, Lab 02 — Run, Fix, and Deploy a Backend Service, Lab 03 — Backend API: Explore, Debug, Implement, Deploy, Lab 04 — Testing, Front-end, and AI Agents, Lab 05 — Data Pipeline and Analytics Dashboard, Lab 06 — Build Your Own Agent, Lab 07 — Build a Client with an AI Coding Agent, lab-08.

## Task 3A — Structured logging

Happy-path log excerpt:

```text
backend-1  | 2026-03-27 17:03:34,481 INFO [app.main] [main.py:60] [trace_id=538dbe85c612086ddfedbdbbb651c656 ...] - request_started
backend-1  | 2026-03-27 17:03:34,482 INFO [app.auth] [auth.py:30] [trace_id=538dbe85c612086ddfedbdbbb651c656 ...] - auth_success
backend-1  | 2026-03-27 17:03:34,482 INFO [app.db.items] [items.py:16] [trace_id=538dbe85c612086ddfedbdbbb651c656 ...] - db_query
backend-1  | 2026-03-27 17:03:34,494 INFO [app.main] [main.py:68] [trace_id=538dbe85c612086ddfedbdbbb651c656 ...] - request_completed
```

Error-path log excerpt:

```text
backend-1  | 2026-03-27 17:30:22,802 INFO [app.main] [main.py:60] [trace_id=95b11f5b02b91c065cb881fd2faf85cf ...] - request_started
backend-1  | 2026-03-27 17:30:22,804 INFO [app.auth] [auth.py:30] [trace_id=95b11f5b02b91c065cb881fd2faf85cf ...] - auth_success
backend-1  | 2026-03-27 17:30:22,804 INFO [app.db.items] [items.py:16] [trace_id=95b11f5b02b91c065cb881fd2faf85cf ...] - db_query
backend-1  | 2026-03-27 17:30:22,989 ERROR [app.db.items] [items.py:20] [trace_id=95b11f5b02b91c065cb881fd2faf85cf ...] - db_query
backend-1  | 2026-03-27 17:30:22,990 INFO [app.main] [main.py:68] [trace_id=95b11f5b02b91c065cb881fd2faf85cf ...] - request_completed
```

VictoriaLogs query evidence:

```text
query: db_query AND _time:30m
result: latest error log contains severity=ERROR, event=db_query, and trace_id=95b11f5b02b91c065cb881fd2faf85cf
```

## Task 3B — Traces

Healthy trace summary:

```text
trace_id: 538dbe85c612086ddfedbdbbb651c656
span_count: 8
operations: SELECT db-lab-8, GET /items/ http send, connect, GET /items/, BEGIN;, ROLLBACK;
```

Error trace summary:

```text
trace_id: 95b11f5b02b91c065cb881fd2faf85cf
span_count: 5
operations: GET /items/ http send, connect, GET /items/
```

VictoriaTraces evidence:

```text
service: Learning Management Service
recent traces in lookback=1h: 5
latest error trace id: 95b11f5b02b91c065cb881fd2faf85cf
```

## Task 3C — Observability MCP tools

Normal-condition response:

> I found 1 error log entry in the last hour. The latest one is `db_query` at `2026-03-27T17:16:27.118041856Z` with severity `ERROR`. Error: `(sqlalchemy.dialects.postgresql.asyncpg.InterfaceError) <class 'asyncpg.exceptions._base.InterfaceError'>: connection is closed ...` Related trace `58ef79c0fcb613f284a1d4a6645840c8` contains 6 spans in VictoriaTraces.

Failure-condition response after stopping PostgreSQL and triggering a request:

> I found 2 error log entries in the last hour. The latest one is `db_query` at `2026-03-27T17:30:01.415208192Z` with severity `ERROR`. Error: `[Errno -2] Name or service not known` Related trace id: `2525663497bcfddb5cc017464e569962`.

## Task 4A — Multi-step investigation

Prompt: `What went wrong?`

> I checked the latest backend error logs first and then followed the related trace. The newest failure is a `db_query` error from `Learning Management Service`, and the message shows the database request failed while PostgreSQL was unavailable. The error is still recent, so this is an active backend/database incident. The related trace confirms the request reached `GET /items/` and then failed in the backend database path before completing successfully.

## Task 4B — Proactive health check

Prompt: `Create a health check every 2 minutes in this chat`

> Created job `Check system health for this chat. Review backend errors from the last 2 minutes, inspect a trace if needed, and post a short summary. If there are no recent errors, say the system looks healthy.` (id: `...`)

Proactive report after a failure:

> I checked the last 2 minutes of logs. The newest error is still a backend `db_query` failure caused by the database being unavailable, and the related trace shows the request entering `GET /items/` before failing on the DB access path.

Proactive report after recovery:

> I checked the recent logs and there are no fresh backend errors. The system looks healthy right now.

## Task 4C — Bug fix and recovery

Root cause:

> `GET /items/` in `backend/app/routers/items.py` was catching every exception and incorrectly rewriting real infrastructure failures into `404 Items not found`, which hid the actual database outage from both the API client and the observability investigation flow.

Fix:

> I removed the broad `try/except` in `get_items()` so database failures now propagate to the global exception handler and preserve the real backend error.

Post-fix `What went wrong?` response:

> The latest failure is a real backend/database error, not a fake missing-items 404. The newest `db_query` error shows the DB request failed while PostgreSQL was down, and the related trace points to the `/items/` request failing on the database access path.

Healthy follow-up:

> After PostgreSQL was started again, the next health-check cycle reported no fresh errors, so the system is healthy again.
