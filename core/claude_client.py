"""
Shared Claude API client for all agents and Commander.
Uses Anthropic Messages API via requests (no SDK dependency).

Model tiers:
    SONNET  — assessments, user-facing chat (needs reasoning)
    HAIKU   — step analysis, plan reviews (high-volume, structured decisions)
"""

import json
import requests

MODEL_SONNET = "claude-sonnet-4-5-20250514"
MODEL_HAIKU = "claude-haiku-4-5-20250514"

# Default for backwards compatibility
DEFAULT_MODEL = MODEL_SONNET


# Cost per million tokens by model (input, output)
MODEL_COSTS = {
    MODEL_SONNET: (3.00, 15.00),
    MODEL_HAIKU: (1.00, 5.00),
}


class ClaudeClient:
    """Wraps the Anthropic Messages API with tiered model support and spend tracking."""

    def __init__(self, api_key, model=None):
        self.api_key = api_key
        self.model = model or DEFAULT_MODEL
        self.api_url = "https://api.anthropic.com/v1/messages"
        # Cumulative token/cost tracking (resets when flushed)
        self._spend = {
            "input_tokens": 0,
            "output_tokens": 0,
            "estimated_cost_usd": 0.0,
            "api_calls": 0,
        }

    def get_spend_summary(self):
        """Return current spend counters."""
        return dict(self._spend)

    def flush_spend(self):
        """Return and reset spend counters for the reporting window."""
        summary = dict(self._spend)
        self._spend = {
            "input_tokens": 0,
            "output_tokens": 0,
            "estimated_cost_usd": 0.0,
            "api_calls": 0,
        }
        return summary

    def _track_usage(self, data, model_used):
        """Accumulate token usage and estimated cost from an API response."""
        usage = data.get("usage", {})
        inp = usage.get("input_tokens", 0)
        out = usage.get("output_tokens", 0)
        self._spend["input_tokens"] += inp
        self._spend["output_tokens"] += out
        self._spend["api_calls"] += 1
        # Estimate cost
        costs = MODEL_COSTS.get(model_used, (3.00, 15.00))
        self._spend["estimated_cost_usd"] += (inp / 1_000_000 * costs[0]) + (out / 1_000_000 * costs[1])

    def chat(self, system_prompt, messages, max_tokens=1024, model=None):
        """Send messages to Claude, return raw text response.

        Args:
            system_prompt: System-level instructions.
            messages: List of {"role": "user"|"assistant", "content": str}.
            max_tokens: Max response length.
            model: Override model for this call (e.g., MODEL_HAIKU for cheap tasks).

        Returns:
            str: Claude's text response.

        Raises:
            RuntimeError: On API errors.
        """
        model_used = model or self.model
        payload = {
            "model": model_used,
            "max_tokens": max_tokens,
            "system": system_prompt,
            "messages": messages,
        }
        headers = {
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        }

        resp = requests.post(self.api_url, headers=headers, json=payload, timeout=60)
        if not resp.ok:
            raise RuntimeError(f"Claude API {resp.status_code}: {resp.text[:300]}")

        data = resp.json()
        self._track_usage(data, model_used)
        return data["content"][0]["text"].strip()

    def structured_chat(self, system_prompt, messages, max_tokens=1024, model=None):
        """Send messages to Claude and parse JSON from response.

        Strips markdown code fences if present. Retries once on parse failure
        with an explicit JSON-only request.

        Args:
            model: Override model for this call.

        Returns:
            dict: Parsed JSON response.
        """
        use_model = model or self.model
        text = self.chat(system_prompt, messages, max_tokens, model=use_model)
        parsed = self._try_parse(text)
        if parsed is not None:
            return parsed

        # Retry with explicit JSON instruction (use same model)
        retry_messages = messages + [
            {"role": "assistant", "content": text},
            {"role": "user", "content": "Please respond with valid JSON only, no markdown."},
        ]
        text2 = self.chat(system_prompt, retry_messages, max_tokens, model=use_model)
        parsed = self._try_parse(text2)
        if parsed is not None:
            return parsed

        raise ValueError(f"Could not parse JSON from Claude response: {text2[:200]}")

    @staticmethod
    def _try_parse(text):
        """Attempt to parse JSON, stripping code fences if present."""
        cleaned = text.strip()
        # Strip ```json ... ``` or ``` ... ```
        if cleaned.startswith("```"):
            lines = cleaned.split("\n", 1)
            if len(lines) > 1:
                cleaned = lines[1].rsplit("```", 1)[0].strip()
        try:
            return json.loads(cleaned)
        except (json.JSONDecodeError, ValueError):
            return None
