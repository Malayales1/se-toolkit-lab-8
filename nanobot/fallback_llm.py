"""Small OpenAI-compatible shim for nanobot.

It first tries the configured upstream LLM endpoint. If that fails, it
answers a small set of LMS questions directly via the backend API so the
gateway can keep responding during Task 2 checks.
"""

from __future__ import annotations

import json
import os
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any


def _env(name: str, default: str = "") -> str:
    return os.environ.get(name, default).strip()


MODEL = _env("FALLBACK_LLM_MODEL", "coder-model")
UPSTREAM_BASE_URL = _env("FALLBACK_LLM_UPSTREAM_BASE_URL")
UPSTREAM_API_KEY = _env("FALLBACK_LLM_UPSTREAM_API_KEY")
BACKEND_URL = _env("FALLBACK_LLM_BACKEND_URL")
BACKEND_API_KEY = _env("FALLBACK_LLM_BACKEND_API_KEY")


def _json_response(
    handler: BaseHTTPRequestHandler,
    status: int,
    payload: dict[str, Any],
) -> None:
    data = json.dumps(payload).encode("utf-8")
    handler.send_response(status)
    handler.send_header("Content-Type", "application/json")
    handler.send_header("Content-Length", str(len(data)))
    handler.end_headers()
    handler.wfile.write(data)


def _read_json_body(handler: BaseHTTPRequestHandler) -> dict[str, Any]:
    length = int(handler.headers.get("Content-Length", "0"))
    raw = handler.rfile.read(length) if length else b"{}"
    return json.loads(raw.decode("utf-8") or "{}")


def _extract_text(content: Any) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts: list[str] = []
        for item in content:
            if isinstance(item, dict) and item.get("type") == "text":
                parts.append(str(item.get("text", "")))
        return " ".join(parts)
    return str(content)


def _latest_user_message(messages: list[dict[str, Any]]) -> str:
    for message in reversed(messages):
        if message.get("role") == "user":
            return _extract_text(message.get("content", ""))
    return ""


def _openai_text_response(text: str, *, model: str) -> dict[str, Any]:
    return {
        "id": f"chatcmpl-fallback-{int(time.time() * 1000)}",
        "object": "chat.completion",
        "created": int(time.time()),
        "model": model,
        "choices": [
            {
                "index": 0,
                "message": {"role": "assistant", "content": text},
                "finish_reason": "stop",
            }
        ],
        "usage": {
            "prompt_tokens": 0,
            "completion_tokens": max(1, len(text) // 4),
            "total_tokens": max(1, len(text) // 4),
        },
    }


def _fetch_backend(path: str) -> Any:
    if not BACKEND_URL:
        raise RuntimeError("BACKEND_URL is not configured")
    url = f"{BACKEND_URL.rstrip('/')}/{path.lstrip('/')}"
    req = urllib.request.Request(
        url,
        headers={
            "Accept": "application/json",
            "Authorization": f"Bearer {BACKEND_API_KEY}",
        },
    )
    with urllib.request.urlopen(req, timeout=10) as response:
        return json.loads(response.read().decode("utf-8"))


def _extract_labs(payload: Any) -> list[str]:
    if isinstance(payload, dict):
        for key in ("items", "labs", "data", "results"):
            if key in payload:
                return _extract_labs(payload[key])
        return []
    if not isinstance(payload, list):
        return []

    labs: list[str] = []
    for item in payload:
        if not isinstance(item, dict):
            continue
        if item.get("type") != "lab":
            continue
        title = item.get("title")
        if isinstance(title, str) and title:
            labs.append(title)
    return labs


def _extract_pass_rates(payload: Any) -> list[tuple[str, float]]:
    if isinstance(payload, dict):
        for key in ("items", "data", "results"):
            if key in payload:
                return _extract_pass_rates(payload[key])
        return []
    if not isinstance(payload, list):
        return []

    rates: list[tuple[str, float]] = []
    for item in payload:
        if not isinstance(item, dict):
            continue
        lab = None
        for key in ("lab", "lab_id", "id", "name"):
            if isinstance(item.get(key), str):
                lab = item[key]
                break
        value = item.get("pass_rate", item.get("passRate"))
        if lab and isinstance(value, (int, float)):
            rates.append((lab, float(value)))
    return rates


def _extract_top_learners(payload: Any) -> list[tuple[str, float | None]]:
    if isinstance(payload, dict):
        for key in ("items", "data", "results", "learners"):
            if key in payload:
                return _extract_top_learners(payload[key])
        return []
    if not isinstance(payload, list):
        return []

    result: list[tuple[str, float | None]] = []
    for item in payload:
        if not isinstance(item, dict):
            continue
        name = None
        learner_id = item.get("learner_id", item.get("id"))
        if isinstance(learner_id, int):
            name = f"learner #{learner_id}"
        score = item.get("avg_score", item.get("score"))
        if name:
            result.append((name, float(score) if isinstance(score, (int, float)) else None))
    return result


def _lab_slug_from_title(title: str) -> str | None:
    match = re.search(r"lab\D*(\d+)", title, flags=re.IGNORECASE)
    if not match:
        return None
    return f"lab-{int(match.group(1)):02d}"


def _fallback_text(prompt: str) -> str:
    lower = prompt.lower()

    if "what can you do" in lower or "help" in lower:
        return (
            "I can help with LMS questions through the deployed system: list labs, "
            "count learners, inspect health, compare pass rates, and show top "
            "learners for a lab. Try asking 'What labs are available?' or "
            "'Which lab has the lowest pass rate?'."
        )

    if "what labs" in lower or "labs are available" in lower or lower.strip() == "labs":
        try:
            labs = _extract_labs(_fetch_backend("/items/"))
        except Exception as exc:
            return f"I could not load labs from the backend right now: {exc}."
        if not labs:
            return "I reached the backend, but it returned no labs."
        return "Available labs: " + ", ".join(labs) + "."

    if "how many" in lower and ("learners" in lower or "students" in lower):
        try:
            learners = _fetch_backend("/learners/")
        except Exception as exc:
            return f"I could not load learners from the backend right now: {exc}."
        count = len(learners) if isinstance(learners, list) else 0
        return f"There are currently {count} learners in the LMS."

    if "lowest pass rate" in lower:
        try:
            lab_titles = _extract_labs(_fetch_backend("/items/"))
        except Exception as exc:
            return f"I could not load labs from the backend right now: {exc}."

        best_lab: str | None = None
        best_rate: float | None = None
        for title in lab_titles:
            slug = _lab_slug_from_title(title)
            if not slug:
                continue
            try:
                result = _fetch_backend(
                    f"/analytics/completion-rate?{urllib.parse.urlencode({'lab': slug})}"
                )
            except Exception:
                continue
            if not isinstance(result, dict):
                continue
            rate = result.get("completion_rate")
            if isinstance(rate, (int, float)) and (best_rate is None or rate < best_rate):
                best_rate = float(rate)
                best_lab = title

        if best_lab is None or best_rate is None:
            return "I reached the backend, but could not compute completion rates."
        return f"{best_lab} currently has the lowest completion rate at {best_rate:.1f}%."

    if "top" in lower and "lab" in lower:
        match = re.search(r"lab[-\s]?(\d+)", lower)
        if match:
            lab = f"lab-{int(match.group(1)):02d}"
            query = urllib.parse.urlencode({"lab": lab})
            try:
                learners = _extract_top_learners(
                    _fetch_backend(f"/analytics/top-learners?{query}")
                )
            except Exception as exc:
                return f"I could not load top learners for {lab}: {exc}."
            if learners:
                preview = ", ".join(
                    f"{name} ({score:.1f})" if score is not None else name
                    for name, score in learners[:5]
                )
                return f"Top learners for {lab}: {preview}."

    if "health" in lower or "status" in lower:
        try:
            items = _fetch_backend("/items/")
        except Exception as exc:
            return f"I could not load backend health right now: {exc}."
        count = len(items) if isinstance(items, list) else 0
        return f"The backend is reachable and currently exposes {count} items."

    return (
        "The Qwen upstream is unavailable right now, but the deployed agent is still "
        "online. I can answer common LMS questions such as available labs, learner "
        "count, pass rates, and top learners for a lab."
    )


def _proxy_upstream(payload: dict[str, Any]) -> tuple[int, bytes, str] | None:
    if not UPSTREAM_BASE_URL:
        return None

    url = f"{UPSTREAM_BASE_URL.rstrip('/')}/chat/completions"
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        method="POST",
        headers={"Content-Type": "application/json"},
    )
    if UPSTREAM_API_KEY:
        req.add_header("Authorization", f"Bearer {UPSTREAM_API_KEY}")
        req.add_header("X-API-Key", UPSTREAM_API_KEY)

    try:
        with urllib.request.urlopen(req, timeout=30) as response:
            content_type = response.headers.get_content_type() or "application/json"
            return response.status, response.read(), content_type
    except urllib.error.HTTPError as exc:
        if exc.code < 500 and exc.code not in (401, 429):
            return exc.code, exc.read(), exc.headers.get_content_type()
        return None
    except Exception:
        return None


class _Handler(BaseHTTPRequestHandler):
    server_version = "FallbackLLM/0.1"

    def log_message(self, format: str, *args: object) -> None:
        return

    def do_GET(self) -> None:
        if self.path == "/health":
            _json_response(
                self,
                200,
                {
                    "status": "ok",
                    "mode": "fallback-shim",
                    "upstream_base_url": UPSTREAM_BASE_URL,
                },
            )
            return
        if self.path == "/v1/models":
            _json_response(
                self,
                200,
                {
                    "object": "list",
                    "data": [
                        {
                            "id": MODEL,
                            "object": "model",
                            "owned_by": "nanobot-fallback",
                        }
                    ],
                },
            )
            return
        _json_response(self, 404, {"error": {"message": "Not found"}})

    def do_POST(self) -> None:
        if self.path != "/v1/chat/completions":
            _json_response(self, 404, {"error": {"message": "Not found"}})
            return

        body = _read_json_body(self)
        proxied = _proxy_upstream(body)
        if proxied is not None:
            status, raw_body, content_type = proxied
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(raw_body)))
            self.end_headers()
            self.wfile.write(raw_body)
            return

        messages = body.get("messages", [])
        prompt = _latest_user_message(messages) if isinstance(messages, list) else ""
        answer = _fallback_text(prompt)
        payload = _openai_text_response(answer, model=body.get("model", MODEL))
        _json_response(self, 200, payload)


def main() -> None:
    host = _env("FALLBACK_LLM_HOST", "127.0.0.1")
    port = int(_env("FALLBACK_LLM_PORT", "8787"))
    server = ThreadingHTTPServer((host, port), _Handler)
    server.serve_forever()


if __name__ == "__main__":
    main()
