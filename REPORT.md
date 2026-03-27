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

<!-- Paste a short nanobot startup log excerpt showing the gateway started inside Docker -->

## Task 2B — Web client

<!-- Screenshot of a conversation with the agent in the Flutter web app -->

## Task 3A — Structured logging

<!-- Paste happy-path and error-path log excerpts, VictoriaLogs query screenshot -->

## Task 3B — Traces

<!-- Screenshots: healthy trace span hierarchy, error trace -->

## Task 3C — Observability MCP tools

<!-- Paste agent responses to "any errors in the last hour?" under normal and failure conditions -->

## Task 4A — Multi-step investigation

<!-- Paste the agent's response to "What went wrong?" showing chained log + trace investigation -->

## Task 4B — Proactive health check

<!-- Screenshot or transcript of the proactive health report that appears in the Flutter chat -->

## Task 4C — Bug fix and recovery

<!-- 1. Root cause identified
     2. Code fix (diff or description)
     3. Post-fix response to "What went wrong?" showing the real underlying failure
     4. Healthy follow-up report or transcript after recovery -->
