from __future__ import annotations
import base64
import json
from pathlib import Path
from typing import Any
import httpx
from ..settings import get_settings


class NimUnavailable(RuntimeError):
    pass


class NimClient:
    def __init__(self) -> None:
        self.settings = get_settings()
        self.base_url = self.settings.nvidia_nim_base_url.rstrip("/")
        self.headers = {
            "Authorization": f"Bearer {self.settings.nvidia_nim_api_key}",
            "Content-Type": "application/json",
        }

    @property
    def enabled(self) -> bool:
        return bool(self.settings.nvidia_nim_api_key)

    async def chat(self, model: str, messages: list[dict[str, Any]], response_json: bool = False) -> str:
        if not self.enabled:
            raise NimUnavailable("NVIDIA_NIM_API_KEY가 설정되지 않았습니다.")
        payload: dict[str, Any] = {
            "model": model,
            "messages": messages,
            "temperature": 0.1,
            "max_tokens": 4096,
        }
        if response_json:
            payload["response_format"] = {"type": "json_object"}
        last_error: Exception | None = None
        for _ in range(max(1, self.settings.nvidia_nim_max_retries + 1)):
            try:
                async with httpx.AsyncClient(timeout=self.settings.nvidia_nim_timeout_seconds) as client:
                    response = await client.post(f"{self.base_url}/chat/completions", headers=self.headers, json=payload)
                    response.raise_for_status()
                    data = response.json()
                    return data["choices"][0]["message"]["content"]
            except Exception as exc:  # network/model errors are surfaced as issues by caller
                last_error = exc
        raise RuntimeError(f"NIM 호출 실패: {last_error}")

    async def extract_json(self, model: str, system: str, user: str, fallback: dict[str, Any]) -> dict[str, Any]:
        try:
            raw = await self.chat(
                model=model,
                response_json=True,
                messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
            )
            return json.loads(raw)
        except Exception:
            return fallback

    async def vision_json(self, model: str, image_path: Path, prompt: str, fallback: dict[str, Any]) -> dict[str, Any]:
        try:
            mime = "image/png" if image_path.suffix.lower() == ".png" else "image/jpeg"
            encoded = base64.b64encode(image_path.read_bytes()).decode("ascii")
            messages = [{
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {"type": "image_url", "image_url": {"url": f"data:{mime};base64,{encoded}"}},
                ],
            }]
            raw = await self.chat(model=model, messages=messages, response_json=True)
            return json.loads(raw)
        except Exception:
            return fallback

    async def vision_text(self, model: str, image_path: Path, prompt: str, fallback: str = "") -> str:
        try:
            mime = "image/png" if image_path.suffix.lower() == ".png" else "image/jpeg"
            encoded = base64.b64encode(image_path.read_bytes()).decode("ascii")
            messages = [{
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {"type": "image_url", "image_url": {"url": f"data:{mime};base64,{encoded}"}},
                ],
            }]
            return await self.chat(model=model, messages=messages, response_json=False)
        except Exception:
            return fallback


nim_client = NimClient()
