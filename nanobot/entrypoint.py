"""Resolve container environment into nanobot config, then start the gateway."""

from __future__ import annotations

import json
import os
from pathlib import Path


APP_DIR = Path("/app")
PROJECT_DIR = APP_DIR / "nanobot"
CONFIG_PATH = PROJECT_DIR / "config.json"
RESOLVED_CONFIG_PATH = PROJECT_DIR / "config.resolved.json"
WORKSPACE_PATH = PROJECT_DIR / "workspace"


def _require(name: str) -> str:
    value = os.environ.get(name, "").strip()
    if not value:
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value


def _require_int(name: str) -> int:
    return int(_require(name))


def main() -> None:
    config = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))

    config.setdefault("providers", {}).setdefault("custom", {})
    config["providers"]["custom"]["apiKey"] = _require("LLM_API_KEY")
    config["providers"]["custom"]["apiBase"] = _require("LLM_API_BASE_URL")

    defaults = config.setdefault("agents", {}).setdefault("defaults", {})
    defaults["model"] = _require("LLM_API_MODEL")
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
    mcp_server["args"] = ["-m", "mcp_lms", _require("NANOBOT_LMS_BACKEND_URL")]
    mcp_env = mcp_server.setdefault("env", {})
    mcp_env["PYTHONPATH"] = str(APP_DIR / "mcp")
    mcp_env["NANOBOT_LMS_BACKEND_URL"] = _require("NANOBOT_LMS_BACKEND_URL")
    mcp_env["NANOBOT_LMS_API_KEY"] = _require("NANOBOT_LMS_API_KEY")

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
