import json
from dataclasses import dataclass

import httpx
from openai import AsyncOpenAI

from shared.config import get_settings

GEMINI_URL = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"


class LLMParseError(Exception):
    """The model output has no valid tool call or final answer."""


@dataclass
class ToolCall:
    tool: str
    args: dict


@dataclass
class Final:
    speech: str
    text: str = ""


def parse_model_output(raw: str) -> ToolCall | Final:
    decoder = json.JSONDecoder()
    obj = None
    pos = raw.find("{")
    while pos != -1:
        try:
            candidate, _ = decoder.raw_decode(raw, pos)
        except ValueError:
            pos = raw.find("{", pos + 1)
            continue
        if isinstance(candidate, dict):
            obj = candidate
            break
        pos = raw.find("{", pos + 1)
    if obj is None:
        raise LLMParseError("no JSON object found")

    final = obj.get("final")
    if isinstance(final, dict) and isinstance(final.get("speech"), str):
        text = final.get("text", "")
        return Final(speech=final["speech"], text=text if isinstance(text, str) else str(text))
    tool = obj.get("tool")
    if isinstance(tool, str) and tool:
        args = obj.get("args", {})
        if not isinstance(args, dict):
            raise LLMParseError("'args' must be an object")
        return ToolCall(tool=tool, args=args)
    raise LLMParseError("JSON must have 'tool' or 'final.speech'")


def _to_gemini_contents(messages: list[dict]) -> list[dict]:
    # Gemma on AI Studio rejects system_instruction: system turns become user turns
    contents: list[dict] = []
    for m in messages:
        role = "model" if m["role"] == "assistant" else "user"
        if contents and contents[-1]["role"] == role:
            contents[-1]["parts"][0]["text"] += "\n\n" + m["content"]
        else:
            contents.append({"role": role, "parts": [{"text": m["content"]}]})
    return contents


class GemmaClient:
    def __init__(self, timeout: float = 60.0):
        self.timeout = timeout
        self._openai: AsyncOpenAI | None = None

    async def chat(self, messages: list[dict]) -> str:
        s = get_settings()
        if s.gemma_base_url:
            return await self._chat_openai(messages)
        url = GEMINI_URL.format(model=s.gemma_model)
        body = {"contents": _to_gemini_contents(messages)}
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            resp = await client.post(url, json=body, headers={"x-goog-api-key": s.gemma_api_key})
            resp.raise_for_status()
        parts = resp.json()["candidates"][0]["content"]["parts"]
        return "".join(p.get("text", "") for p in parts)

    async def _chat_openai(self, messages: list[dict]) -> str:
        s = get_settings()
        if self._openai is None:
            self._openai = AsyncOpenAI(
                base_url=s.gemma_base_url, api_key=s.gemma_api_key or "none", timeout=self.timeout
            )
        resp = await self._openai.chat.completions.create(model=s.gemma_model, messages=messages)
        return resp.choices[0].message.content or ""
