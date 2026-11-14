"""Standard-library client for an explicitly configured real tool-calling model."""
from __future__ import annotations

import json
import os
import urllib.error
import urllib.request

from .common import ROOT


def load_env():
    path = ROOT / ".env"
    if path.exists():
        for line in path.read_text(encoding="utf-8-sig").splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, value = line.split("=", 1)
                os.environ.setdefault(key.strip(), value.strip().strip("\"'"))


class ModelClient:
    def __init__(self):
        load_env()
        self.base_url = os.getenv("RAG_BASE_URL", "http://127.0.0.1:11434/v1").rstrip("/")
        self.model = os.getenv("RAG_MODEL", "")
        self.key = os.getenv("RAG_API_KEY", "")
        self.timeout = float(os.getenv("RAG_TIMEOUT", "120"))
        self.input_rate = os.getenv("RAG_INPUT_USD_PER_MILLION")
        self.output_rate = os.getenv("RAG_OUTPUT_USD_PER_MILLION")
        if not self.model:
            raise RuntimeError("RAG_MODEL is missing. Configure a real tool-calling model in .env; no mock fallback.")

    def chat(self, messages, tools, tool_choice="auto"):
        payload = {"model": self.model, "messages": messages, "tools": tools,
                   "tool_choice": tool_choice, "temperature": 0, "max_tokens": 1000, "parallel_tool_calls": False}
        headers = {"Content-Type": "application/json"}
        if self.key:
            headers["Authorization"] = "Bearer " + self.key
        request = urllib.request.Request(self.base_url + "/chat/completions", data=json.dumps(payload).encode(), headers=headers)
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                result = json.load(response)
        except urllib.error.HTTPError as exc:
            # Provider bodies can contain account details. Preserve status without credentials.
            raise RuntimeError(f"Model HTTP {exc.code}; verify endpoint/model/tool support") from None
        except urllib.error.URLError:
            raise ConnectionError("Cannot reach model endpoint; verify RAG_BASE_URL and local server") from None
        message = result["choices"][0]["message"]
        usage = result.get("usage", {})
        cost = usage.get("cost")
        if cost is None and self.input_rate is not None and self.output_rate is not None and "prompt_tokens" in usage and "completion_tokens" in usage:
            cost = (usage["prompt_tokens"] * float(self.input_rate) + usage["completion_tokens"] * float(self.output_rate)) / 1_000_000
        return message, {"model": result.get("model", self.model), "usage": usage, "cost_usd": cost}
