"""Resolve container environment into nanobot config, then start the gateway."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from pathlib import Path
from urllib.request import urlopen


APP_DIR = Path("/app")
PROJECT_DIR = APP_DIR / "nanobot"
CONFIG_PATH = PROJECT_DIR / "config.json"
RESOLVED_CONFIG_PATH = PROJECT_DIR / "config.resolved.json"
WORKSPACE_PATH = PROJECT_DIR / "workspace"
FALLBACK_PORT = int(os.environ.get("NANOBOT_FALLBACK_LLM_PORT", "8787"))


def _require(name: str) -> str:
    value = os.environ.get(name, "").strip()
    if not value:
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value


def _require_int(name: str) -> int:
    return int(_require(name))


def _start_fallback_llm(
    *,
    upstream_base_url: str,
    upstream_api_key: str,
    backend_url: str,
    backend_api_key: str,
    logs_base_url: str,
    traces_base_url: str,
    model: str,
) -> None:
    env = os.environ.copy()
    env["FALLBACK_LLM_HOST"] = "127.0.0.1"
    env["FALLBACK_LLM_PORT"] = str(FALLBACK_PORT)
    env["FALLBACK_LLM_UPSTREAM_BASE_URL"] = upstream_base_url
    env["FALLBACK_LLM_UPSTREAM_API_KEY"] = upstream_api_key
    env["FALLBACK_LLM_BACKEND_URL"] = backend_url
    env["FALLBACK_LLM_BACKEND_API_KEY"] = backend_api_key
    env["FALLBACK_LLM_LOGS_BASE_URL"] = logs_base_url
    env["FALLBACK_LLM_TRACES_BASE_URL"] = traces_base_url
    env["FALLBACK_LLM_MODEL"] = model

    subprocess.Popen(
        [sys.executable, str(PROJECT_DIR / "fallback_llm.py")],
        env=env,
    )

    health_url = f"http://127.0.0.1:{FALLBACK_PORT}/health"
    last_error: Exception | None = None
    for _ in range(50):
        try:
            with urlopen(health_url, timeout=1):
                return
        except Exception as exc:  # pragma: no cover - startup loop
            last_error = exc
            time.sleep(0.1)
    raise RuntimeError(f"Fallback LLM did not start: {last_error}")


def main() -> None:
    config = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    upstream_base_url = _require("LLM_API_BASE_URL")
    upstream_api_key = _require("LLM_API_KEY")
    backend_url = _require("NANOBOT_LMS_BACKEND_URL")
    backend_api_key = _require("NANOBOT_LMS_API_KEY")
    logs_base_url = os.environ.get("NANOBOT_LOGS_BASE_URL", "http://localhost:42010")
    traces_base_url = os.environ.get(
        "NANOBOT_TRACES_BASE_URL", "http://localhost:42011"
    )
    model = _require("LLM_API_MODEL")

    _start_fallback_llm(
        upstream_base_url=upstream_base_url,
        upstream_api_key=upstream_api_key,
        backend_url=backend_url,
        backend_api_key=backend_api_key,
        logs_base_url=logs_base_url,
        traces_base_url=traces_base_url,
        model=model,
    )

    config.setdefault("providers", {}).setdefault("custom", {})
    config["providers"]["custom"]["apiKey"] = upstream_api_key
    config["providers"]["custom"]["apiBase"] = f"http://127.0.0.1:{FALLBACK_PORT}/v1"

    defaults = config.setdefault("agents", {}).setdefault("defaults", {})
    defaults["model"] = model
    defaults["workspace"] = str(WORKSPACE_PATH)

    gateway = config.setdefault("gateway", {})
    gateway["host"] = _require("NANOBOT_GATEWAY_CONTAINER_ADDRESS")
    gateway["port"] = _require_int("NANOBOT_GATEWAY_CONTAINER_PORT")

    channels = config.setdefault("channels", {})
    webchat = channels.setdefault("webchat", {})
    webchat["enabled"] = True
    webchat["host"] = _require("NANOBOT_WEBCHAT_CONTAINER_ADDRESS")
    webchat["port"] = _require_int("NANOBOT_WEBCHAT_CONTAINER_PORT")
    webchat.setdefault("allowFrom", ["*"])

    mcp_server = (
        config.setdefault("tools", {})
        .setdefault("mcpServers", {})
        .setdefault("lms", {})
    )
    mcp_server["command"] = "python"
    mcp_server["args"] = ["-m", "mcp_lms", backend_url]
    mcp_env = mcp_server.setdefault("env", {})
    mcp_env["PYTHONPATH"] = str(APP_DIR / "mcp")
    mcp_env["NANOBOT_LMS_BACKEND_URL"] = backend_url
    mcp_env["NANOBOT_LMS_API_KEY"] = backend_api_key
    mcp_env["NANOBOT_LOGS_BASE_URL"] = logs_base_url
    mcp_env["NANOBOT_TRACES_BASE_URL"] = traces_base_url

    RESOLVED_CONFIG_PATH.write_text(
        json.dumps(config, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    os.execvp(
        "nanobot",
        [
            "nanobot",
            "gateway",
            "--config",
            str(RESOLVED_CONFIG_PATH),
            "--workspace",
            str(WORKSPACE_PATH),
        ],
    )


if __name__ == "__main__":
    main()
