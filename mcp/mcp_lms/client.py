"""Async clients, models, and formatters for LMS and observability APIs."""

import json
import os
from collections import Counter
from typing import Any

import httpx
from pydantic import BaseModel


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------


class HealthResult(BaseModel):
    status: str
    item_count: int | str = "unknown"
    error: str = ""


class Item(BaseModel):
    id: int | None = None
    type: str = "step"
    parent_id: int | None = None
    title: str = ""
    description: str = ""


class Learner(BaseModel):
    id: int | None = None
    external_id: str = ""
    student_group: str = ""


class PassRate(BaseModel):
    task: str
    avg_score: float
    attempts: int


class TimelineEntry(BaseModel):
    date: str
    submissions: int


class GroupPerformance(BaseModel):
    group: str
    avg_score: float
    students: int


class TopLearner(BaseModel):
    learner_id: int
    avg_score: float
    attempts: int


class CompletionRate(BaseModel):
    lab: str
    completion_rate: float
    passed: int
    total: int


class SyncResult(BaseModel):
    new_records: int
    total_records: int


class LogEntry(BaseModel):
    timestamp: str = ""
    message: str = ""
    severity: str = ""
    service: str = ""
    event: str = ""
    trace_id: str = ""
    span_id: str = ""
    path: str = ""
    error: str = ""
    raw: dict[str, Any] = {}


class ErrorCount(BaseModel):
    service: str
    count: int


class TraceSummary(BaseModel):
    trace_id: str
    root_operation: str = ""
    span_count: int = 0
    services: list[str] = []
    start_time: int = 0


class TraceDetail(BaseModel):
    trace_id: str
    services: list[str]
    span_count: int
    operations: list[str]
    errors: list[str]
    raw: dict[str, Any]


# ---------------------------------------------------------------------------
# HTTP client
# ---------------------------------------------------------------------------


class LMSClient:
    """Client for the LMS backend API."""

    def __init__(self, base_url: str, api_key: str):
        self.base_url = base_url.rstrip("/")
        self._headers = {"Authorization": f"Bearer {api_key}"}

    def _client(self) -> httpx.AsyncClient:
        return httpx.AsyncClient(headers=self._headers, timeout=10.0)

    async def health_check(self) -> HealthResult:
        async with self._client() as c:
            try:
                r = await c.get(f"{self.base_url}/items/")
                r.raise_for_status()
                items = [Item.model_validate(i) for i in r.json()]
                return HealthResult(status="healthy", item_count=len(items))
            except httpx.ConnectError:
                return HealthResult(
                    status="unhealthy", error=f"connection refused ({self.base_url})"
                )
            except httpx.HTTPStatusError as e:
                return HealthResult(
                    status="unhealthy", error=f"HTTP {e.response.status_code}"
                )
            except Exception as e:
                return HealthResult(status="unhealthy", error=str(e))

    async def get_items(self) -> list[Item]:
        async with self._client() as c:
            r = await c.get(f"{self.base_url}/items/")
            r.raise_for_status()
            return [Item.model_validate(i) for i in r.json()]

    async def get_learners(self) -> list[Learner]:
        async with self._client() as c:
            r = await c.get(f"{self.base_url}/learners/")
            r.raise_for_status()
            return [Learner.model_validate(i) for i in r.json()]

    async def get_pass_rates(self, lab: str) -> list[PassRate]:
        async with self._client() as c:
            r = await c.get(
                f"{self.base_url}/analytics/pass-rates", params={"lab": lab}
            )
            r.raise_for_status()
            return [PassRate.model_validate(i) for i in r.json()]

    async def get_timeline(self, lab: str) -> list[TimelineEntry]:
        async with self._client() as c:
            r = await c.get(f"{self.base_url}/analytics/timeline", params={"lab": lab})
            r.raise_for_status()
            return [TimelineEntry.model_validate(i) for i in r.json()]

    async def get_groups(self, lab: str) -> list[GroupPerformance]:
        async with self._client() as c:
            r = await c.get(f"{self.base_url}/analytics/groups", params={"lab": lab})
            r.raise_for_status()
            return [GroupPerformance.model_validate(i) for i in r.json()]

    async def get_top_learners(self, lab: str, limit: int = 5) -> list[TopLearner]:
        async with self._client() as c:
            r = await c.get(
                f"{self.base_url}/analytics/top-learners",
                params={"lab": lab, "limit": limit},
            )
            r.raise_for_status()
            return [TopLearner.model_validate(i) for i in r.json()]

    async def get_completion_rate(self, lab: str) -> CompletionRate:
        async with self._client() as c:
            r = await c.get(
                f"{self.base_url}/analytics/completion-rate", params={"lab": lab}
            )
            r.raise_for_status()
            return CompletionRate.model_validate(r.json())

    async def sync_pipeline(self) -> SyncResult:
        async with self._client() as c:
            r = await c.post(f"{self.base_url}/pipeline/sync")
            r.raise_for_status()
            return SyncResult.model_validate(r.json())


class ObservabilityClient:
    """Client for VictoriaLogs and VictoriaTraces."""

    def __init__(
        self,
        logs_base_url: str | None = None,
        traces_base_url: str | None = None,
        default_service: str = "Learning Management Service",
    ):
        self.logs_base_url = (
            logs_base_url
            or os.environ.get("NANOBOT_LOGS_BASE_URL", "http://localhost:42010")
        ).rstrip("/")
        self.traces_base_url = (
            traces_base_url
            or os.environ.get("NANOBOT_TRACES_BASE_URL", "http://localhost:42011")
        ).rstrip("/")
        self.default_service = default_service

    @staticmethod
    def _log_entry_from_payload(payload: dict[str, Any]) -> LogEntry:
        return LogEntry(
            timestamp=str(payload.get("_time", "")),
            message=str(payload.get("_msg", payload.get("event", ""))),
            severity=str(payload.get("severity", "")),
            service=str(
                payload.get("service.name", payload.get("otelServiceName", ""))
            ),
            event=str(payload.get("event", "")),
            trace_id=str(payload.get("trace_id", payload.get("otelTraceID", ""))),
            span_id=str(payload.get("span_id", payload.get("otelSpanID", ""))),
            path=str(payload.get("path", "")),
            error=str(payload.get("error", "")),
            raw=payload,
        )

    @staticmethod
    def _trace_detail_from_payload(payload: dict[str, Any]) -> TraceDetail:
        data = payload.get("data", [])
        first = data[0] if data else {}
        spans = first.get("spans", [])
        processes = first.get("processes", {})

        process_services = {
            pid: proc.get("serviceName", "")
            for pid, proc in processes.items()
            if isinstance(proc, dict)
        }
        services = sorted(
            {
                process_services.get(str(span.get("processID", "")), "")
                for span in spans
            }
        )
        services = [service for service in services if service]

        operations: list[str] = []
        errors: list[str] = []
        trace_id = ""
        for span in spans:
            operation = span.get("operationName", "")
            if isinstance(operation, str) and operation:
                operations.append(operation)
            if not trace_id and isinstance(span.get("traceID"), str):
                trace_id = span["traceID"]
            for tag in span.get("tags", []):
                if not isinstance(tag, dict):
                    continue
                if tag.get("key") == "error" and str(tag.get("value")).lower() == "true":
                    errors.append(operation or str(span.get("spanID", "unknown-span")))
                if tag.get("key") == "exception.message" and isinstance(
                    tag.get("value"), str
                ):
                    errors.append(f"{operation}: {tag['value']}")

        return TraceDetail(
            trace_id=trace_id,
            services=services,
            span_count=len(spans),
            operations=operations[:20],
            errors=errors[:20],
            raw=payload,
        )

    async def logs_search(
        self,
        *,
        keyword: str = "",
        service: str = "",
        severity: str = "",
        since_minutes: int = 60,
        limit: int = 20,
    ) -> list[LogEntry]:
        async with httpx.AsyncClient(timeout=20.0) as c:
            r = await c.get(
                f"{self.logs_base_url}/select/logsql/query",
                params={"query": f"_time:{since_minutes}m", "limit": max(limit * 5, limit)},
            )
            r.raise_for_status()

        keyword_text = keyword.strip().lower()
        wanted_service = service.strip()
        wanted_severity = severity.strip().upper()
        entries: list[LogEntry] = []
        for line in r.text.splitlines():
            line = line.strip()
            if not line:
                continue
            payload = json.loads(line)
            entry = self._log_entry_from_payload(payload)
            haystack = " ".join(
                [
                    entry.message,
                    entry.event,
                    entry.path,
                    entry.error,
                    json.dumps(entry.raw, ensure_ascii=False),
                ]
            ).lower()
            if wanted_service and entry.service != wanted_service:
                continue
            if wanted_severity and entry.severity.upper() != wanted_severity:
                continue
            if keyword_text and keyword_text not in haystack:
                continue
            entries.append(entry)
            if len(entries) >= limit:
                break
        return entries

    async def logs_error_count(
        self,
        *,
        since_minutes: int = 60,
        service: str = "",
        limit: int = 200,
    ) -> list[ErrorCount]:
        entries = await self.logs_search(
            service=service,
            severity="ERROR",
            since_minutes=since_minutes,
            limit=limit,
        )
        counts = Counter(entry.service or "unknown" for entry in entries)
        return [
            ErrorCount(service=service_name, count=count)
            for service_name, count in counts.most_common()
        ]

    async def traces_list(
        self,
        *,
        service: str = "",
        limit: int = 10,
        lookback: str = "1h",
    ) -> list[TraceSummary]:
        service_name = service.strip() or self.default_service
        async with httpx.AsyncClient(timeout=20.0) as c:
            r = await c.get(
                f"{self.traces_base_url}/select/jaeger/api/traces",
                params={"service": service_name, "limit": limit, "lookback": lookback},
            )
            r.raise_for_status()
            payload = r.json()

        traces: list[TraceSummary] = []
        for item in payload.get("data", []):
            spans = item.get("spans", [])
            processes = item.get("processes", {})
            process_services = {
                pid: proc.get("serviceName", "")
                for pid, proc in processes.items()
                if isinstance(proc, dict)
            }
            trace_id = ""
            root_operation = ""
            start_time = 0
            services_seen: list[str] = []
            for span in spans:
                if not trace_id and isinstance(span.get("traceID"), str):
                    trace_id = span["traceID"]
                services_seen.append(process_services.get(str(span.get("processID", "")), ""))
                if not span.get("references") and not root_operation:
                    root_operation = str(span.get("operationName", ""))
                    start_time = int(span.get("startTime", 0) or 0)
            traces.append(
                TraceSummary(
                    trace_id=trace_id,
                    root_operation=root_operation,
                    span_count=len(spans),
                    services=sorted({service for service in services_seen if service}),
                    start_time=start_time,
                )
            )
        return traces

    async def traces_get(self, trace_id: str) -> TraceDetail:
        async with httpx.AsyncClient(timeout=20.0) as c:
            r = await c.get(f"{self.traces_base_url}/select/jaeger/api/traces/{trace_id}")
            r.raise_for_status()
            payload = r.json()
        return self._trace_detail_from_payload(payload)


# ---------------------------------------------------------------------------
# Formatters
# ---------------------------------------------------------------------------


def format_health(result: HealthResult) -> str:
    if result.status == "healthy":
        return f"\u2705 Backend is healthy. {result.item_count} items available."
    return f"\u274c Backend error: {result.error or 'Unknown'}"


def format_labs(items: list[Item]) -> str:
    labs = sorted(
        [i for i in items if i.type == "lab"],
        key=lambda x: str(x.id),
    )
    if not labs:
        return "\U0001f4ed No labs available."
    text = "\U0001f4da Available labs:\n\n"
    text += "\n".join(f"\u2022 {lab.title}" for lab in labs)
    return text


def format_scores(lab: str, rates: list[PassRate]) -> str:
    if not rates:
        return f"\U0001f4ed No scores found for {lab}."
    text = f"\U0001f4ca Pass rates for {lab}:\n\n"
    text += "\n".join(
        f"\u2022 {r.task}: {r.avg_score:.1f}% ({r.attempts} attempts)" for r in rates
    )
    return text
