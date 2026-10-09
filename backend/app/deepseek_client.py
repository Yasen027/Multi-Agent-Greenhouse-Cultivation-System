"""轻量级 OpenAI 兼容 DeepSeek 客户端，支持 JSON 解析和重试。

客户端使用标准库 urllib，避免后端额外引入 HTTP 依赖；
未配置密钥时，调用方可以使用本地回退逻辑。
"""

import asyncio
import json
import logging
import os
import re
import time
import urllib.error
import urllib.request
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


class DeepSeekError(RuntimeError):
    """DeepSeek 无法返回可用响应时抛出的异常。"""


def _json_from_text(value: str) -> Dict[str, Any]:
    text = (value or "").strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*|\s*```$", "", text, flags=re.I | re.S).strip()
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", text, flags=re.S)
        if not match:
            raise DeepSeekError("DeepSeek returned non-JSON content")
        try:
            parsed = json.loads(match.group(0))
        except json.JSONDecodeError as exc:
            raise DeepSeekError("DeepSeek returned invalid JSON") from exc
    if not isinstance(parsed, dict):
        raise DeepSeekError("DeepSeek JSON response must be an object")
    return parsed


class DeepSeekClient:
    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        model: Optional[str] = None,
        vision_model: Optional[str] = None,
        timeout: Optional[float] = None,
        retries: Optional[int] = None,
    ):
        self.api_key = (
            api_key if api_key is not None else os.getenv("DEEPSEEK_API_KEY", "")
        )
        self.base_url = (
            base_url or os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com/v1")
        ).rstrip("/")
        self.model = model or os.getenv("DEEPSEEK_MODEL", "deepseek-chat")
        self.vision_model = vision_model or os.getenv(
            "DEEPSEEK_VISION_MODEL", self.model
        )
        self.timeout = float(
            timeout if timeout is not None else os.getenv("DEEPSEEK_TIMEOUT", "30")
        )
        self.retries = max(
            0,
            int(retries if retries is not None else os.getenv("DEEPSEEK_RETRIES", "2")),
        )
        self.last_error: Optional[str] = None

    @property
    def available(self) -> bool:
        return bool(self.api_key or os.getenv("DEEPSEEK_API_KEY", ""))

    def complete_json(
        self,
        prompt: str,
        image_url: Optional[str] = None,
        model: Optional[str] = None,
    ) -> Dict[str, Any]:
        if not self.available:
            raise DeepSeekError("DEEPSEEK_API_KEY is not configured")
        content: Any = prompt
        if image_url:
            content = [
                {"type": "text", "text": prompt},
                {"type": "image_url", "image_url": {"url": image_url}},
            ]
        payload = {
            "model": model or (self.vision_model if image_url else self.model),
            "messages": [{"role": "user", "content": content}],
            "temperature": 0.1,
            "response_format": {"type": "json_object"},
        }
        api_key = self.api_key or os.getenv("DEEPSEEK_API_KEY", "")
        request = urllib.request.Request(
            self.base_url + "/chat/completions",
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Authorization": "Bearer " + api_key,
                "Content-Type": "application/json",
                "Accept": "application/json",
            },
            method="POST",
        )
        for attempt in range(self.retries + 1):
            try:
                with urllib.request.urlopen(request, timeout=self.timeout) as response:
                    body = json.loads(response.read().decode("utf-8"))
                message = body.get("choices", [{}])[0].get("message", {})
                content_value = (
                    message.get("content", "") if isinstance(message, dict) else ""
                )
                if isinstance(content_value, list):
                    content_value = "".join(
                        str(part.get("text", ""))
                        for part in content_value
                        if isinstance(part, dict)
                    )
                result = _json_from_text(str(content_value))
                self.last_error = None
                return result
            except (
                urllib.error.URLError,
                urllib.error.HTTPError,
                TimeoutError,
                OSError,
                ValueError,
                DeepSeekError,
            ) as exc:
                self.last_error = str(exc)
                if attempt < self.retries:
                    time.sleep(0.25 * (2**attempt))
                    continue
                logger.warning(
                    "DeepSeek request failed; local fallback will be used: %s", exc
                )
                raise DeepSeekError(str(exc)) from exc
        raise DeepSeekError("DeepSeek request failed")

    async def complete_json_async(
        self,
        prompt: str,
        image_url: Optional[str] = None,
        model: Optional[str] = None,
    ) -> Dict[str, Any]:
        return await asyncio.to_thread(self.complete_json, prompt, image_url, model)


deepseek_client = DeepSeekClient()
