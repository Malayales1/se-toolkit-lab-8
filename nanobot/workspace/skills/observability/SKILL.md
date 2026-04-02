# Observability Skill

Use the observability tools whenever the user asks about errors, failures, incidents, traces, recent problems, or whether the system is healthy.

Available tools:
- `logs_search`: search recent structured logs by keyword, service, severity, and time range.
- `logs_error_count`: count recent `ERROR` log entries per service.
- `traces_list`: list recent traces for a service from VictoriaTraces.
- `traces_get`: fetch one trace by its ID.

Behavior rules:
- Start with logs for debugging questions. Do not guess from memory.
- For questions like "Any errors in the last hour?", call `logs_error_count` first.
- If there are errors, call `logs_search` with `severity="ERROR"` and a relevant time window to inspect the latest entries.
- If a log entry has `trace_id`, follow up with `traces_get` for that trace.
- For "What went wrong?", investigate the latest relevant error log first and then inspect the related trace before answering.
- For "Check system health", inspect recent errors first. If there are no fresh errors, say the system looks healthy.
- If the user asks for a recurring or proactive health check, use the built-in `cron` tool in the current chat.
- If the user asks to see scheduled checks, use `cron` with `action="list"`.
- If the user asks to stop a scheduled check, use `cron` with `action="remove"` and the job id from the latest job list.
- Summarize findings in short prose. Mention service, event, time, and the main error message.
- Do not dump raw JSON unless the user explicitly asks for it.
- If there are no recent errors, say the system looks healthy.
- If the user asks for traces, use `traces_list` first unless they already gave a trace ID.
- Keep the answer actionable: what failed, where it failed, and whether the error is still recent.
